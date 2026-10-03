from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Job, MatchResult, Resume, User
from app.services.match_pipeline import match_resume
from app.services.parsing import extract_skills
from app.services.taxonomy import ensure_taxonomy


def test_ml_aliases_and_every_active_job_gets_a_score():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        user = User(name="ML Candidate", email="ml@example.com", password_hash="unused", role="candidate")
        db.add(user)
        db.flush()
        taxonomy = {s.name: s for s in ensure_taxonomy(db)}
        resume = Resume(
            user_id=user.id,
            filename="ml.pdf",
            text="ML engineer with Python, torch, sklearn, NLP, LLMs, retrieval-augmented generation and MLOps.",
        )
        db.add(resume)
        for i in range(200):
            names = (
                ["Python", "PyTorch", "Machine Learning"]
                if i % 2
                else ["Python", "Scikit-learn", "Natural Language Processing"]
            )
            db.add(
                Job(
                    recruiter_id=user.id,
                    title="ML Engineer" if i % 2 else "Data Scientist",
                    company=f"Team {i}",
                    location="Remote",
                    description="Build machine learning systems",
                    skills=[taxonomy[n] for n in names],
                )
            )
        db.commit()
        assert match_resume(db, resume) == 200
        results = list(db.scalars(select(MatchResult)))
        assert len(results) == 200
        assert all(result.score == 60 for result in results)
        assert {"Large Language Models", "RAG", "MLOps"} <= {s.name for s in resume.skills}
        assert match_resume(db, resume, only_missing=True) == 0


def test_aliases_respect_canonical_case_and_boundaries():
    assert extract_skills("sklearn and JS, not a Pythonista", ["scikit-learn", "JavaScript", "Python"]) == [
        "JavaScript",
        "scikit-learn",
    ]
