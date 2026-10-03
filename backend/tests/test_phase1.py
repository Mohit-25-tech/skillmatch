from datetime import timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.ingestion.normalization import normalize_location
from app.ingestion.relevance import clean_title_and_badge, is_cse_role
from app.models import Job, MatchResult, Resume, Skill, User, utcnow
from app.repositories.catalog import jobs_page
from app.services.matching import calculate_match
from app.services.product import GENERIC_OR_SOFT_SKILLS, candidate_matches_summary, learning_path, market_insights


def test_cse_relevance_rejects_non_tech():
    # Roles that should be accepted
    assert is_cse_role("Software Engineer") is True
    assert is_cse_role("Backend Developer (Python/Go)") is True
    assert is_cse_role("Fullstack Engineer") is True
    assert is_cse_role("DevOps / Cloud Architect") is True
    assert is_cse_role("Machine Learning Specialist") is True
    assert is_cse_role("Frontend React Developer") is True

    # Roles like Copywriter, Sales, Marketing, Recruiter must be rejected
    assert is_cse_role("Senior Copywriter & Content Creator") is False
    assert is_cse_role("Sales Representative - B2B SaaS") is False
    assert is_cse_role("Digital Marketing Manager") is False
    assert is_cse_role("Technical Recruiter / Talent Acquisition") is False
    assert is_cse_role("Account Executive - Enterprise Sales") is False
    assert is_cse_role("Social Media & Community Specialist") is False
    assert is_cse_role("Office Manager / Administrative Assistant") is False


def test_clean_title_and_badge():
    clean, badge = clean_title_and_badge("Year at Palantir - Software Engineer")
    assert clean == "Software Engineer"
    assert badge == "Year at Palantir"

    clean2, badge2 = clean_title_and_badge("[Summer Internship] Backend Developer")
    assert clean2 == "Backend Developer"
    assert badge2 == "Summer Internship"

    clean3, badge3 = clean_title_and_badge("Data Engineer")
    assert clean3 == "Data Engineer"
    assert badge3 is None


def test_normalize_location():
    # Remote variations
    assert normalize_location("remote - americas", is_remote=True) == "Remote – Americas"
    assert normalize_location("Remote - EMEA / UK", is_remote=False) == "Remote – EMEA / UK"
    assert normalize_location("remote", is_remote=True) == "Remote"
    assert normalize_location("anywhere", is_remote=True) == "Remote"

    # City / State / Country
    assert normalize_location("bangalore, karnataka, india", is_remote=False) == "Bangalore, Karnataka, India"
    assert normalize_location("San Francisco, CA", is_remote=False) == "San Francisco, CA"
    assert normalize_location("", is_remote=True) == "Remote"
    assert normalize_location("", is_remote=False) == "Not specified"


def test_matching_smoothing_and_confidence():
    py, sql, fast = Skill(name="Python"), Skill(name="SQL"), Skill(name="FastAPI")
    resume = Resume(text="Python engineer", skills=[py], experience_years=3)

    # Job with only 1 skill (sparse job): cannot hit 100% due to k=2 smoothing
    job_sparse = Job(title="Python Dev", description="Python only", skills=[py])
    sparse_match = calculate_match(resume, job_sparse)
    # matched_weight = 1.0, total_weight = 1.0, k = 2.0 -> keyword = 100 * 1 / 3 = 33.3%
    assert sparse_match["keyword_score"] == 33.3
    # Less than 3 job skills and no semantic -> Low confidence badge
    assert sparse_match["confidence"] == "low"
    assert sparse_match["confidence_label"] == "Low confidence"

    # Job with 3 skills: High confidence requires semantic embedding
    job_three = Job(title="Fullstack", description="Py SQL FastAPI", skills=[py, sql, fast])
    match_no_semantic = calculate_match(resume, job_three)
    assert match_no_semantic["confidence"] == "low"  # semantic missing -> low confidence

    match_with_semantic = calculate_match(resume, job_three, semantic_value=85.0)
    assert match_with_semantic["confidence"] == "high"
    assert match_with_semantic["confidence_label"] == "High confidence"


def test_minimum_evidence_rule_when_semantic_missing():
    py, sql = Skill(name="Python"), Skill(name="SQL")
    resume_none = Resume(text="No skills", skills=[])
    resume_one = Resume(text="Python only", skills=[py])
    resume_two = Resume(text="Python and SQL", skills=[py, sql])

    job = Job(title="Backend Dev", description="Python and SQL needed", skills=[py, sql])

    # 0 skills matched -> score is 0.0
    res0 = calculate_match(resume_none, job)
    assert res0["score"] == 0.0

    # < 2 skills matched -> score capped at 50%
    res1 = calculate_match(resume_one, job)
    assert res1["score"] <= 50.0

    # >= 2 skills matched -> score evaluated under 65% ceiling
    res2 = calculate_match(resume_two, job)
    assert res2["score"] <= 65.0
    assert any("minimum evidence rule" in r for r in res2["reasons"])


def test_stale_jobs_filter_and_ordering():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        now = utcnow()
        # Active recent job
        j_recent = Job(title="Recent Dev", company="Co A", location="Remote", description="desc", posted_at=now - timedelta(days=2))
        # Job posted 20 days ago
        j_medium = Job(title="Mid Dev", company="Co B", location="Remote", description="desc", posted_at=now - timedelta(days=20))
        # Job posted 60 days ago
        j_older = Job(title="Older Dev", company="Co C", location="Remote", description="desc", posted_at=now - timedelta(days=60))
        # Job closed
        j_closed = Job(title="Closed Dev", company="Co D", location="Remote", description="desc", active=False, posted_at=now)

        db.add_all([j_recent, j_medium, j_older, j_closed])
        db.commit()

        # Closed job is not returned
        all_jobs, count = jobs_page(db, "", "", "", 1, 10, sort="recent")
        assert count == 3
        assert j_closed.id not in [j.id for j in all_jobs]

        # Sorted by recency: recent, medium, older
        assert [j.id for j in all_jobs] == [j_recent.id, j_medium.id, j_older.id]

        # Days filter = 7
        jobs_7, count_7 = jobs_page(db, "", "", "", 1, 10, days=7)
        assert count_7 == 1
        assert [j.id for j in jobs_7] == [j_recent.id]

        # Days filter = 30
        jobs_30, count_30 = jobs_page(db, "", "", "", 1, 10, days=30)
        assert count_30 == 2
        assert [j.id for j in jobs_30] == [j_recent.id, j_medium.id]


def test_learning_path_excludes_soft_skills_and_includes_unlock_message():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        user = User(name="Test", email="test@example.com", password_hash="x", role="candidate")
        db.add(user)
        db.flush()

        s_py = Skill(name="Python")
        s_docker = Skill(name="Docker")
        s_comm = Skill(name="Communication")
        s_cs = Skill(name="Computer Science")
        db.add_all([s_py, s_docker, s_comm, s_cs])
        db.flush()

        resume = Resume(user_id=user.id, filename="r.pdf", text="Python", skills=[s_py])
        db.add(resume)
        db.flush()

        job1 = Job(title="Dev 1", company="A", location="Remote", description="desc", skills=[s_py, s_docker, s_comm])
        job2 = Job(title="Dev 2", company="B", location="Remote", description="desc", skills=[s_py, s_docker, s_cs])
        db.add_all([job1, job2])
        db.flush()

        # Match results with missing skills including soft skills
        db.add(MatchResult(resume_id=resume.id, job_id=job1.id, score=50.0, semantic_score=50.0, keyword_score=50.0, matched=["Python"], missing=["Docker", "Communication"], method="keyword"))
        db.add(MatchResult(resume_id=resume.id, job_id=job2.id, score=50.0, semantic_score=50.0, keyword_score=50.0, matched=["Python"], missing=["Docker", "Computer Science"], method="keyword"))
        db.commit()

        path = learning_path(db, resume)
        # Communication and Computer Science must be excluded
        skill_names = [item["skill"] for item in path]
        assert "Docker" in skill_names
        assert "Communication" not in skill_names
        assert "Computer Science" not in skill_names
        # Check unlock message format
        docker_item = next(item for item in path if item["skill"] == "Docker")
        assert docker_item["related_jobs"] == 2
        assert docker_item["message"] == "Learning Docker unlocks 2 more jobs"


def test_top_companies_capped_with_others():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        # Create 15 companies
        for i in range(15):
            for count in range(i + 1):
                db.add(Job(title=f"Role {i}_{count}", company=f"Company {i}", location="Remote", description="desc", active=True, is_demo=False))
        db.commit()

        insights = market_insights(db, force=True)
        # Should have top 10 companies + "Others"
        assert len(insights["companies"]) <= 11
        assert "Others" in insights["companies"]
        assert insights["companies"]["Others"] > 0
