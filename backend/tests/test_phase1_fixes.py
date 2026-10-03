from datetime import timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.ingestion.normalization import RawJob, normalize_location
from app.ingestion.relevance import is_cse_role
from app.models import Job, Skill, utcnow
from app.repositories.catalog import STOP_WORDS, jobs_page


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_token_based_search_with_stopwords(db_session: Session):
    s_py = Skill(name="Python")
    s_go = Skill(name="Go")
    db_session.add_all([s_py, s_go])
    db_session.flush()

    job1 = Job(
        title="Software Engineer",
        company="Alpha Corp",
        location="Remote",
        description="Looking for high scale systems development",
        skills=[s_py],
        active=True,
        is_demo=False,
        posted_at=utcnow(),
    )
    job2 = Job(
        title="Software Engineer",
        company="Beta Corp",
        location="Remote",
        description="Looking for go developers",
        skills=[s_go],
        active=True,
        is_demo=False,
        posted_at=utcnow(),
    )
    db_session.add_all([job1, job2])
    db_session.commit()

    # Query with stopword: "engineer in python" -> stripped tokens: ["engineer", "python"] (<= 3: AND mode)
    # job1 has "engineer" in title and "python" in skills -> MATCH
    # job2 has "engineer" in title, but neither in company, desc, nor skills has "python" -> NO MATCH
    results, count = jobs_page(db_session, query="engineer in python", location="", kind="", page=1, size=10)
    assert count == 1
    assert results[0].id == job1.id


def test_location_normalization_query(db_session: Session):
    job_ny = Job(
        title="Backend Engineer",
        company="TechNYC",
        location="New York, USA",
        description="Core services",
        active=True,
        is_demo=False,
        posted_at=utcnow(),
    )
    job_sf = Job(
        title="Frontend Engineer",
        company="SF Tech",
        location="San Francisco, CA",
        description="React UI",
        active=True,
        is_demo=False,
        posted_at=utcnow(),
    )
    db_session.add_all([job_ny, job_sf])
    db_session.commit()

    # User searches "New York, NY" -> tokens ["New", "York", "NY"]
    # matches job_ny ("New York, USA")
    results, count = jobs_page(db_session, query="", location="New York, NY", kind="", page=1, size=10)
    assert count == 1
    assert results[0].id == job_ny.id


def test_country_filter_india_plus_remote(db_session: Session):
    now = utcnow()
    job_india_onsite = Job(
        title="Dev 1",
        company="Company A",
        location="Bangalore",
        country="India",
        remote=False,
        description="desc",
        active=True,
        is_demo=False,
        posted_at=now,
    )
    job_us_remote = Job(
        title="Dev 2",
        company="Company B",
        location="Remote",
        country="United States",
        remote=True,
        description="desc",
        active=True,
        is_demo=False,
        posted_at=now,
    )
    job_us_onsite = Job(
        title="Dev 3",
        company="Company C",
        location="Austin, TX",
        country="United States",
        remote=False,
        description="desc",
        active=True,
        is_demo=False,
        posted_at=now,
    )
    db_session.add_all([job_india_onsite, job_us_remote, job_us_onsite])
    db_session.commit()

    # Filter with "India + Remote worldwide"
    results, count = jobs_page(
        db_session,
        query="",
        location="",
        kind="",
        page=1,
        size=10,
        country="India + Remote worldwide",
    )
    matched_ids = {j.id for j in results}
    assert count == 2
    assert job_india_onsite.id in matched_ids
    assert job_us_remote.id in matched_ids
    assert job_us_onsite.id not in matched_ids


def test_raw_job_remote_auto_detection():
    # 1. Location containing "Anywhere" -> remote True
    rj1 = RawJob(
        external_id="test-1",
        title="Backend Developer",
        company="Test Co",
        location="Anywhere",
        remote=False,
        description="Build microservices",
        apply_url="https://example.com/apply/1",
        attribution="Lever",
        attribution_url="https://example.com/job/1",
    )
    assert rj1.remote is True
    assert rj1.location == "Remote"

    # 2. Location containing "Work from home" -> remote True
    rj2 = RawJob(
        external_id="test-2",
        title="Cloud Engineer",
        company="Test Co",
        location="Work from home, US",
        remote=False,
        description="Maintain AWS infra",
        apply_url="https://example.com/apply/2",
        attribution="Ashby",
        attribution_url="https://example.com/job/2",
    )
    assert rj2.remote is True

    # 3. Title containing "Remote" -> remote True
    rj3 = RawJob(
        external_id="test-3",
        title="Remote Staff Python Engineer",
        company="Test Co",
        location="New York",
        remote=False,
        description="Python services",
        apply_url="https://example.com/apply/3",
        attribution="Arbeitnow",
        attribution_url="https://example.com/job/3",
    )
    assert rj3.remote is True


def test_cse_role_non_tech_exclusions():
    # Tech roles must be accepted
    assert is_cse_role("Staff Platform Engineer") is True
    assert is_cse_role("Site Reliability Engineer") is True
    assert is_cse_role("Senior Deep Learning Researcher") is True

    # Non-tech roles must be rejected
    assert is_cse_role("Senior Copywriter") is False
    assert is_cse_role("Content Marketing Specialist") is False
    assert is_cse_role("Enterprise Account Executive") is False
    assert is_cse_role("Customer Support Representative") is False
    assert is_cse_role("Talent Acquisition Partner") is False


def test_hybrid_relevance_title_weight_over_description(db_session: Session):
    # Job A has "Kubernetes" in title
    job_a = Job(
        title="Kubernetes Specialist",
        company="Alpha",
        location="Remote",
        description="General cloud engineering tasks",
        active=True,
        is_demo=False,
        posted_at=utcnow(),
    )
    # Job B has "Kubernetes" only in description body
    job_b = Job(
        title="Cloud Operations Engineer",
        company="Beta",
        location="Remote",
        description="Experience with Kubernetes and docker clusters",
        active=True,
        is_demo=False,
        posted_at=utcnow(),
    )
    db_session.add_all([job_a, job_b])
    db_session.commit()

    results, count = jobs_page(
        db_session,
        query="Kubernetes",
        location="",
        kind="",
        page=1,
        size=10,
        sort="relevance",
    )
    assert count == 2
    # Job A should be ranked higher due to title weight (3.0 vs 1.0)
    assert results[0].id == job_a.id
    assert results[1].id == job_b.id
