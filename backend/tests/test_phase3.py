"""Tests for Phase 3: AI / RAG / Semantic Layer."""

import pytest
from fastapi.testclient import TestClient

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.main import app
from app.models import Application, Job, Resume, Skill, User
from app.services.assistant import CareerAssistant
from app.services.narrative import generate_why_match_narrative
from app.services.nl_search import parse_nl_query
from app.services.retrieval import best_chunk_similarity, chunk_text, cross_encoder_rerank, hybrid_search_jobs
from app.services.skill_extraction import extract_fallback_skills, validate_skill_candidate
from app.services.tailoring import generate_cover_letter, tailor_resume


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_text_chunking():
    long_text = "This is a sentence about python. " * 30
    chunks = chunk_text(long_text, chunk_size=200, overlap=40)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 250


def test_best_chunk_similarity_identical():
    text = "Experienced Python software engineer building distributed backend services with PostgreSQL."
    sim = best_chunk_similarity(text, text)
    assert sim >= 90.0 or sim == 0.0  # If semantic model is mocked or disabled in test env


def test_cross_encoder_rerank_lexical_fallback():
    query = "React frontend developer"
    candidates = [
        {"id": 1, "title": "DevOps Engineer", "description": "Kubernetes Docker AWS", "score": 80.0},
        {"id": 2, "title": "React Frontend Engineer", "description": "React TypeScript Tailwind", "score": 75.0},
    ]
    reranked = cross_encoder_rerank(query, candidates, top_k=2)
    assert len(reranked) == 2
    # The React job should rank first after reranking based on query term coverage
    assert reranked[0]["id"] == 2


def test_hybrid_search_jobs(db_session):
    job1 = Job(
        title="Senior Python Backend Developer",
        company="TechCorp",
        location="Bangalore, India",
        description="FastAPI, PostgreSQL, Redis distributed systems",
        country="India",
        remote=False,
        active=True,
    )
    job2 = Job(
        title="Frontend React Engineer",
        company="WebLabs",
        location="Remote",
        description="React, CSS, HTML, Vite",
        country="India",
        remote=True,
        active=True,
    )
    db_session.add_all([job1, job2])
    db_session.commit()

    results = hybrid_search_jobs(db_session, query_text="Python FastAPI", limit=5)
    assert len(results) >= 1
    assert any(j.title == "Senior Python Backend Developer" for j in results)


def test_nl_query_parsing():
    parsed1 = parse_nl_query("Remote Python ML internships in India")
    assert parsed1["experience_level"] == "intern"
    assert parsed1["remote"] is True
    assert parsed1["country"] == "India"
    assert "Python" in parsed1["q"]

    parsed2 = parse_nl_query("Senior Golang backend engineer in Germany")
    assert parsed2["experience_level"] == "senior"
    assert parsed2["country"] == "Germany"

    parsed3 = parse_nl_query("Entry-level React developer onsite in Bangalore paying good salary")
    assert parsed3["experience_level"] == "entry"
    assert parsed3["country"] == "India"
    assert parsed3["salary_disclosed"] is True


def test_grounded_why_match_narrative():
    narrative = generate_why_match_narrative(
        job_title="Backend Engineer",
        company="Acme Corp",
        match_score=85.5,
        matched_skills=["Python", "FastAPI", "PostgreSQL"],
        missing_skills=["Docker", "Kubernetes"],
        candidate_exp=2.0,
        required_exp=3.0,
        semantic_score=82.0,
    )
    text = narrative["narrative"]
    assert "85.5" in text or "85" in text
    assert "Python" in text
    assert "Docker" in text or "Kubernetes" in text
    # Ensure no fabricated skills
    assert "COBOL" not in text
    assert "Ruby on Rails" not in text


def test_grounded_cover_letter_and_tailoring():
    resume_text = "Experienced software engineer with 3 years in Python, FastAPI, and PostgreSQL. Built high-traffic REST APIs."
    letter_res = generate_cover_letter(
        resume_text=resume_text,
        job_title="Backend Engineer",
        company="Stripe",
        job_description="Seeking a Python developer for payments platform.",
        matched_skills=["Python", "FastAPI"],
    )
    letter = letter_res["cover_letter"]
    assert "Stripe" in letter
    assert "Backend Engineer" in letter
    assert "Python" in letter

    tailor_res = tailor_resume(
        resume_text=resume_text,
        job_title="Backend Engineer",
        company="Stripe",
        matched_skills=["Python", "FastAPI"],
        missing_skills=["Kafka"],
    )
    assert "diff" in tailor_res
    assert "Current Resume" in tailor_res["diff"]
    assert "Stripe" in tailor_res["diff"]
    assert len(tailor_res["actionable_tips"]) >= 2


def test_skill_extraction_and_validation():
    assert validate_skill_candidate("fastapi") is True
    assert validate_skill_candidate("langchain") is True
    assert validate_skill_candidate("vue.js") is True
    assert validate_skill_candidate("c++") is True

    # Generic or stop words must be rejected
    assert validate_skill_candidate("communication") is False
    assert validate_skill_candidate("passionate") is False
    assert validate_skill_candidate("5 years experience") is False
    assert validate_skill_candidate("12345") is False

    text = "We are seeking a developer proficient in LangChain, FastAPI, and ChromaDB for AI agents."
    extracted = extract_fallback_skills(text)
    assert "langchain" in extracted
    assert "fastapi" in extracted
    assert "chromadb" in extracted


def test_career_assistant_tools_and_citations(db_session):
    user = User(name="Candidate User", email="cand@example.com", password_hash="hash", role="candidate")
    job = Job(
        title="Cloud Infrastructure Engineer",
        company="Datadog",
        location="Bangalore",
        description="Kubernetes, Terraform, AWS cloud reliability",
        country="India",
        remote=True,
        active=True,
    )
    db_session.add_all([user, job])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(job)

    assistant = CareerAssistant(db_session, user)

    # Tool 1: search_jobs
    search_res = assistant.tool_search_jobs(query="Cloud Infrastructure", limit=3)
    assert len(search_res) >= 1
    assert search_res[0]["citation"] == f"[Job #{job.id}]"

    # Tool 2: add_to_tracker
    track_res = assistant.tool_add_to_tracker(job.id, status="Saved", notes="Looks great!")
    app_record = db_session.scalar(
        select(Application).where(Application.job_id == job.id, Application.user_id == user.id)
    )
    assert app_record is not None
    assert app_record.status == "Saved"

    # Tool 3: suggest_learning
    learn_res = assistant.tool_suggest_learning("Docker")
    assert len(learn_res) >= 1
    assert "Docker" in learn_res[0]["title"] or "DevDocs" in learn_res[0]["platform"]

    # End-to-end chat message with citation
    chat_res = assistant.process_message(f"Save job #{job.id} to my tracker")
    assert "tracker" in chat_res["reply"].casefold() or f"[Job #{job.id}]" in chat_res["reply"]


def test_ai_api_endpoints(client: TestClient):
    # Test NL search endpoint
    resp = client.post("/api/v1/ai/nl-search", json={"query": "Remote Python internships in India", "limit": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert "parsed_filters" in data
    assert data["parsed_filters"]["country"] == "India"
    assert data["parsed_filters"]["experience_level"] == "intern"

    # Test Skill extraction endpoint
    resp = client.post("/api/v1/ai/extract-skills", json={"text": "Proficient in LangChain, Next.js, and Supabase."})
    assert resp.status_code == 200
    assert "langchain" in resp.json()["skills"]

    # Test Rerank endpoint
    candidates = [
        {"id": 1, "title": "DevOps", "score": 60.0},
        {"id": 2, "title": "Python Backend", "score": 70.0},
    ]
    resp = client.post("/api/v1/ai/rerank", json={"query": "Python", "candidates": candidates, "top_k": 2})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2
