import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Job, Resume, Skill, User
from app.security import issue_tokens

@pytest.fixture
def client_and_db():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = Session(engine)

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client, session
    app.dependency_overrides.pop(get_db, None)
    session.close()
    engine.dispose()

def test_recruiter_candidates_and_job_posting(client_and_db):
    client, session = client_and_db

    # Create recruiter and candidates in test db
    recruiter = User(name="Adam Recruiter", email="adam@company.com", password_hash="hash", role="recruiter")
    candidate = User(name="Priya Sharma", email="priya@example.com", password_hash="hash", role="candidate")
    session.add_all([recruiter, candidate])
    session.flush()

    skill_py = Skill(name="Python", category="Technology")
    skill_react = Skill(name="React", category="Technology")
    session.add_all([skill_py, skill_react])
    session.flush()

    resume = Resume(
        user_id=candidate.id,
        filename="priya_resume.pdf",
        text="# Priya Sharma\nSenior Fullstack Engineer with Python and React skills.",
        experience_years=4.5,
        skills=[skill_py, skill_react],
        is_primary=True,
    )
    session.add(resume)
    session.commit()

    from fastapi import Response
    tokens = issue_tokens(recruiter, session, Response())
    token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Test GET /candidates
    r = client.get("/api/v1/candidates", headers=headers)
    assert r.status_code == 200
    candidates = r.json()
    assert len(candidates) >= 1
    cand = candidates[0]
    assert cand["name"] == "Priya Sharma"
    assert "Python" in cand["skills"]
    assert cand["experience_years"] == 4.5

    # 2. Test POST /jobs
    job_payload = {
        "title": "Lead Python Engineer",
        "company": "Recruiter Test Corp",
        "location": "Remote, India",
        "employment_type": "Full-time",
        "remote": True,
        "skills": ["Python", "FastAPI"],
        "description": "We are seeking a senior lead engineer to build out core infrastructure with Python.",
    }
    res_post = client.post("/api/v1/jobs", json=job_payload, headers=headers)
    assert res_post.status_code == 201
    created_job = res_post.json()
    assert created_job["title"] == job_payload["title"]
    assert created_job["active"] is True

    # 3. Test that the created job is visible in jobs query
    res_jobs = client.get("/api/v1/jobs?q=Python")
    assert res_jobs.status_code == 200
    items = res_jobs.json()["items"]
    assert any(j["id"] == created_job["id"] for j in items)
