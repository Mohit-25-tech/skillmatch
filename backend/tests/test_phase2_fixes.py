import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Job, JobChunk, Resume, ResumeChunk, User, utcnow
from app.services.retrieval import (
    chunk_job,
    chunk_resume_sections,
    chunk_text,
    cross_encoder_rerank,
    hybrid_search_jobs,
    index_job_chunks,
    index_resume_chunks,
)
from app.services.vectorstore import ChromaStore, PgVectorStore, get_vector_store


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_chunk_resume_sections_with_headers():
    sample_resume = (
        "John Doe\njohn@example.com\n\n"
        "Professional Summary\n"
        "Passionate full-stack software engineer with 4 years experience building high-scale Python and TypeScript systems.\n\n"
        "Technical Skills\n"
        "Languages: Python, TypeScript, Go, SQL\n"
        "Frameworks: FastAPI, React, Docker, Kubernetes\n\n"
        "Work Experience\n"
        "Senior Software Engineer at Alpha Corp (2022 - Present)\n"
        "- Architected distributed data processing pipeline serving 5M daily users.\n"
        "- Reduced API latencies by 45% via caching and connection pooling.\n\n"
        "Projects\n"
        "Distributed Vector Cache\n"
        "- Open-source vector indexing cache with HNSW search.\n\n"
        "Education\n"
        "B.S. in Computer Science, University of Technology\n\n"
        "Certifications\n"
        "AWS Certified Solutions Architect Associate\n"
    )

    chunks = chunk_resume_sections(sample_resume, max_chunk_size=600, overlap=100)
    sections_found = {c["section"] for c in chunks}

    assert "Summary" in sections_found
    assert "Skills" in sections_found
    assert "Experience" in sections_found
    assert "Projects" in sections_found
    assert "Education" in sections_found
    assert "Certifications" in sections_found
    assert all("text" in c and len(c["text"]) > 0 for c in chunks)


def test_chunk_resume_sections_fallback_without_headers():
    unstructured = (
        "Alice is a backend engineer who specializes in cloud systems. "
        "She has worked extensively with Python, Go, and PostgreSQL. "
        * 15
    )
    chunks = chunk_resume_sections(unstructured, max_chunk_size=400, overlap=80)
    assert len(chunks) > 1
    assert all(c["section"] == "Summary" for c in chunks)


def test_chunk_job():
    job = Job(
        id=42,
        title="Senior Backend Engineer",
        company="Datadog",
        location="Remote",
        employment_type="Full-time",
        country="United States",
        remote=True,
        description="We are seeking an experienced Backend Engineer to lead our telemetry services.\n\n" * 5,
    )
    chunks = chunk_job(job, max_chunk_size=400, overlap=50)
    assert len(chunks) >= 2
    assert chunks[0]["section"] == "overview"
    assert "Datadog" in chunks[0]["text"]
    assert chunks[1]["section"] == "requirements"


def test_pgvector_store_upsert_query_and_delete(db_session: Session):
    def test_db_factory():
        return db_session

    store = PgVectorStore(db_factory=test_db_factory)

    # 1. Upsert resume chunks
    vec_a = [0.1] * 384
    vec_b = [-0.1] * 384
    store.upsert(
        collection_name="resume_chunks",
        ids=["res_1_0", "res_1_1"],
        embeddings=[vec_a, vec_b],
        metadatas=[
            {"resume_id": 1, "user_id": 10, "chunk_idx": 0, "section": "Skills"},
            {"resume_id": 1, "user_id": 10, "chunk_idx": 1, "section": "Experience"},
        ],
        documents=["Python, FastAPI, SQL", "Built distributed systems at TechCorp"],
    )

    assert store.count("resume_chunks") == 2

    # 2. Query with metadata filter
    results = store.query(
        collection_name="resume_chunks",
        query_embedding=vec_a,
        top_k=2,
        filter={"user_id": 10, "section": "Skills"},
    )
    assert len(results) == 1
    assert results[0]["id"] == "res_1_0"
    assert results[0]["score"] > 99.0
    assert results[0]["metadata"]["section"] == "Skills"

    # 3. Delete by filter
    store.delete_by_filter("resume_chunks", {"resume_id": 1})
    assert store.count("resume_chunks") == 0


def test_pgvector_store_job_chunks_and_filtering(db_session: Session):
    def test_db_factory():
        return db_session

    store = PgVectorStore(db_factory=test_db_factory)

    vec_job = [0.2] * 384
    store.upsert(
        collection_name="job_chunks",
        ids=["job_101_0", "job_102_0"],
        embeddings=[vec_job, [-0.2] * 384],
        metadatas=[
            {"job_id": 101, "country": "India", "is_remote": True, "level": "entry", "status": "active"},
            {"job_id": 102, "country": "USA", "is_remote": False, "level": "senior", "status": "active"},
        ],
        documents=["Junior Python Developer in Bangalore", "Senior Architect in SF"],
    )
    assert store.count("job_chunks") == 2

    # Query with is_remote and country filter
    res = store.query(
        collection_name="job_chunks",
        query_embedding=vec_job,
        top_k=5,
        filter={"is_remote": True, "country": "India"},
    )
    assert len(res) == 1
    assert res[0]["metadata"]["job_id"] == 101


def test_hybrid_search_jobs_with_vector_store(db_session: Session, monkeypatch):
    s_py = [0.3] * 384
    job1 = Job(
        title="Python Backend Developer",
        company="Stripe",
        location="Remote",
        description="Write high performance python APIs",
        active=True,
        is_demo=False,
        posted_at=utcnow(),
        embedding=s_py,
    )
    job2 = Job(
        title="Frontend React Engineer",
        company="Vercel",
        location="Remote",
        description="Build user interfaces with Next.js",
        active=True,
        is_demo=False,
        posted_at=utcnow(),
        embedding=[-0.3] * 384,
    )
    db_session.add_all([job1, job2])
    db_session.commit()

    # Index into vector store
    def test_db_factory():
        return db_session

    store = PgVectorStore(db_factory=test_db_factory)
    monkeypatch.setattr("app.services.retrieval.get_vector_store", lambda: store)

    store.upsert(
        collection_name="job_chunks",
        ids=[f"job_{job1.id}_0", f"job_{job2.id}_0"],
        embeddings=[s_py, [-0.3] * 384],
        metadatas=[
            {"job_id": job1.id, "country": "", "is_remote": True, "status": "active"},
            {"job_id": job2.id, "country": "", "is_remote": True, "status": "active"},
        ],
        documents=[job1.description, job2.description],
    )

    results = hybrid_search_jobs(
        db_session,
        query_text="python",
        query_vector=s_py,
        limit=5,
    )
    assert len(results) >= 1
    assert results[0].id == job1.id


def test_cross_encoder_rerank_lexical_fallback():
    candidates = [
        {"title": "Go Developer", "company": "Co A", "description": "Writing Go microservices", "score": 50.0},
        {"title": "Senior Python Engineer", "company": "Co B", "description": "Python, FastAPI, Docker", "score": 40.0},
    ]
    # Lexical ranker gives higher score to candidate with matching query tokens
    reranked = cross_encoder_rerank(query="python fastapi", candidates=candidates, top_k=2)
    assert len(reranked) == 2
    assert reranked[0]["title"] == "Senior Python Engineer"
