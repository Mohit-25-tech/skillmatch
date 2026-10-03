import math
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db import Base
from app.models import Job, MatchResult, Resume, Skill, User
from app.repositories.catalog import jobs_page
from app.services.embeddings import OllamaEmbedder, check_embedder_health, encode_many
from app.services.match_pipeline import match_resume
from app.services.matching import calculate_match, match_public


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([
            Skill(name="Python"),
            Skill(name="FastAPI"),
            Skill(name="Docker"),
            Skill(name="PostgreSQL"),
        ])
        session.commit()
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_ollama_embedder_normalization_and_dim(monkeypatch):
    """Test OllamaEmbedder asserts correct dim and L2-normalizes vectors."""
    monkeypatch.setattr(get_settings(), "semantic_enabled", True)
    embedder = OllamaEmbedder(base_url="http://localhost:11434", model="all-minilm:l6", embed_dim=384)

    mock_raw_vector = [1.0] * 384
    with patch("httpx.Client.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embeddings": [mock_raw_vector]}
        mock_post.return_value = mock_response

        vectors = embedder.embed(["Senior Python Engineer"])
        assert len(vectors) == 1
        vec = vectors[0]
        assert vec is not None
        assert len(vec) == 384
        # L2 norm should be 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-4


def test_ollama_embedder_defensive_truncation(monkeypatch):
    """Test OllamaEmbedder truncates texts longer than 800 chars defensively."""
    monkeypatch.setattr(get_settings(), "semantic_enabled", True)
    embedder = OllamaEmbedder(base_url="http://localhost:11434", model="all-minilm:l6", embed_dim=384)
    long_text = "A" * 1500

    with patch("httpx.Client.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embeddings": [[0.1] * 384]}
        mock_post.return_value = mock_response

        embedder.embed([long_text])
        called_input = mock_post.call_args[1]["json"]["input"]
        assert len(called_input[0]) == 800


def test_health_check_reporting(client):
    """Test /api/v1/health reports semantic search status."""
    with patch("app.services.embeddings.check_embedder_health", return_value=(True, "Ready")):
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["semantic_search"] == "healthy"

    with patch("app.services.embeddings.check_embedder_health", return_value=(False, "run: ollama pull all-minilm:l6")):
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["semantic_search"] == "degraded"
        assert "ollama pull" in data["semantic_message"]


def test_stale_jobs_max_age_search_filter(db_session):
    """Test catalog search excludes jobs older than job_max_age_days (default 120)."""
    now = datetime.now(timezone.utc)
    fresh_job = Job(
        title="Fresh Engineer",
        company="TechCorp",
        location="Bangalore",
        description="Python FastAPI backend",
        active=True,
        posted_at=now - timedelta(days=10),
    )
    stale_job = Job(
        title="Old Engineer",
        company="OldCorp",
        location="Bangalore",
        description="Legacy system",
        active=True,
        posted_at=now - timedelta(days=150),
    )
    db_session.add_all([fresh_job, stale_job])
    db_session.commit()

    jobs, total = jobs_page(db_session, query="", location="", kind="", page=1, size=10)
    job_ids = [j.id for j in jobs]
    assert fresh_job.id in job_ids
    assert stale_job.id not in job_ids


def test_match_resume_idempotent_and_resumable(db_session):
    """Test match_resume handles batches idempotently without duplicating or crashing."""
    skills = db_session.scalars(select(Skill)).all()
    user = User(name="Test Candidate", email="cand@example.com", password_hash="hash", role="candidate")
    db_session.add(user)
    db_session.commit()

    resume = Resume(
        user_id=user.id,
        filename="test.pdf",
        text="Experienced Python and FastAPI backend developer with Docker skills.",
        skills=skills,
    )
    db_session.add(resume)

    jobs = [
        Job(
            title=f"Engineer {i}",
            company="Company",
            location="Remote",
            description="Python FastAPI Docker engineer",
            active=True,
            skills=skills,
        )
        for i in range(5)
    ]
    db_session.add_all(jobs)
    db_session.commit()

    count1 = match_resume(db_session, resume, only_missing=False)
    assert count1 == 5
    matches = db_session.scalars(select(MatchResult).where(MatchResult.resume_id == resume.id)).all()
    assert len(matches) == 5

    # Run again with only_missing=True: should score 0 additional
    count2 = match_resume(db_session, resume, only_missing=True)
    assert count2 == 0
    matches_after = db_session.scalars(select(MatchResult).where(MatchResult.resume_id == resume.id)).all()
    assert len(matches_after) == 5


def test_confidence_badge_logic(db_session):
    """Test high vs low confidence badge logic is consistent."""
    skills = db_session.scalars(select(Skill)).all()
    user = User(name="User", email="u@example.com", password_hash="h", role="candidate")
    db_session.add(user)
    db_session.commit()

    resume = Resume(user_id=user.id, filename="r.pdf", text="Python", skills=skills[:1])
    job_high = Job(
        title="Python Dev",
        company="Co",
        location="Remote",
        description="Python FastAPI Docker PostgreSQL",
        active=True,
        skills=skills,  # 4 skills >= 3
    )
    job_low = Job(
        title="Simple Dev",
        company="Co",
        location="Remote",
        description="Python",
        active=True,
        skills=skills[:1],  # 1 skill < 3
    )
    db_session.add_all([resume, job_high, job_low])
    db_session.commit()

    # With semantic score and >= 3 skills -> High confidence
    high_match = calculate_match(resume, job_high, {}, semantic_value=80.0)
    assert high_match["components"]["confidence"] == "high"
    assert high_match["components"]["confidence_label"] == "High confidence"

    # Missing semantic score -> Low confidence
    low_match_no_semantic = calculate_match(resume, job_high, {}, semantic_value=None)
    assert low_match_no_semantic["components"]["confidence"] == "low"
    assert low_match_no_semantic["components"]["confidence_label"] == "Low confidence"

    # < 3 skills -> Low confidence even with semantic
    low_match_few_skills = calculate_match(resume, job_low, {}, semantic_value=80.0)
    assert low_match_few_skills["components"]["confidence"] == "low"
