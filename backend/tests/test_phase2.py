from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.ingestion.normalization import infer_country, infer_experience_level
from app.models import Application, Job, MatchResult, Resume, Skill, User, utcnow
from app.repositories.catalog import jobs_page, resume_public
from app.services.matching import calculate_match
from app.services.parsing import generate_parse_warnings
from app.services.product import ats_report, latest_resume


def test_infer_experience_level():
    assert infer_experience_level("Software Engineering Intern", "Summer internship role", None) == "intern"
    assert infer_experience_level("Junior Backend Engineer", "Entry-level role for freshers", 0.0) == "entry"
    assert infer_experience_level("Senior Frontend Engineer", "Requires 6+ years experience", 6.0) == "senior"
    assert infer_experience_level("Staff Platform Architect", "Principal role", 10.0) == "senior"
    assert infer_experience_level("Software Engineer II", "Requires 3 years of building systems", 3.0) == "mid"


def test_infer_country():
    assert infer_country("Bangalore, Karnataka, India") == "India"
    assert infer_country("Bengaluru, India") == "India"
    assert infer_country("Hyderabad, Telangana") == "India"
    assert infer_country("Pune, Maharashtra") == "India"
    assert infer_country("Gurgaon, Haryana") == "India"
    assert infer_country("Noida, Delhi NCR") == "India"
    assert infer_country("San Francisco, CA, USA") == "United States"
    assert infer_country("London, UK") == "United Kingdom"
    assert infer_country("Berlin, Germany") == "Germany"
    assert infer_country("Toronto, ON, Canada") == "Canada"
    assert infer_country("Fully Remote (Global)") == "Remote"


def test_fresher_matching_logic():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(name="Fresher Student", email="fresher@example.com", password_hash="x", role="candidate")
        db.add(user)
        db.flush()

        s_py = Skill(name="Python")
        s_fastapi = Skill(name="FastAPI")
        s_sql = Skill(name="PostgreSQL")
        db.add_all([s_py, s_fastapi, s_sql])
        db.flush()

        # Resume with 0 years experience (fresh grad) but good skills
        resume = Resume(
            user_id=user.id,
            filename="fresher_resume.pdf",
            text="Recent Computer Science Graduate with projects in Python and FastAPI.",
            skills=[s_py, s_fastapi, s_sql],
            is_primary=True,
        )
        db.add(resume)

        # Entry-level job requesting 0-1 years
        entry_job = Job(
            title="Junior Software Engineer",
            company="Indian Startup",
            location="Bangalore",
            country="India",
            experience_level="entry",
            experience_min=0.0,
            skills=[s_py, s_fastapi, s_sql],
            description="Great opportunity for fresh engineering graduates.",
            active=True,
        )
        db.add(entry_job)
        db.flush()

        # Calculate match (experience(resume.text) evaluates to 0.0 for fresher)
        match = calculate_match(resume, entry_job)
        assert match["score"] >= 50.0  # smoothing & skills give strong match
        assert match["components"]["experience"]["score"] == 100.0  # 0 years is valid fit for entry role!
        assert any("Fresher/student state" in r for r in match["reasons"])


def test_parse_warnings_generation():
    # Bad text with missing contact and no skills
    bad_text = "Experienced in building systems. Did lots of things."
    warnings = generate_parse_warnings(bad_text, [])
    assert any("contact email" in w.lower() for w in warnings)
    assert any("skill" in w.lower() for w in warnings)
    assert any("experience, projects, or internships" in w.lower() for w in warnings)

    # Good text with Projects section and email
    good_text = (
        "John Doe\njohn@example.com\n+91 98765 43210\n"
        "Education: B.Tech Computer Science, 2026\n"
        "Projects: Built a microservices architecture using Python, FastAPI, and Docker.\n"
        "Technical Skills: Python, FastAPI, Docker, SQL, Git, Linux.\n"
        "Internships: Software Intern at Tech Corp for 3 months.\n"
        * 10  # Repeat to meet length threshold
    )
    good_warnings = generate_parse_warnings(good_text, ["Python", "FastAPI", "Docker", "SQL"])
    assert len(good_warnings) == 0


def test_ats_report_accepts_projects_internships():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(name="Candidate", email="cand@example.com", password_hash="x", role="candidate")
        db.add(user)
        db.flush()

        s_py = Skill(name="Python")
        db.add(s_py)
        db.flush()

        # Text with Projects and Internships instead of traditional 'Experience' heading
        text = (
            "Alex Smith\nalex@example.com\n"
            "Education: B.Tech Computer Engineering\n"
            "Academic Projects:\n"
            "- Designed real-time web portal with bullet points\n"
            "- Improved latency by 30%\n"
            "Skills: Python, Git\n"
            + ("Achievement details and project documentation for testing readability length. " * 30)
        )
        resume = Resume(user_id=user.id, filename="resume.pdf", text=text, skills=[s_py])
        db.add(resume)
        db.flush()

        report = ats_report(resume)
        assert report["sections"]["experience"] is True
        assert report["sections"]["education"] is True
        assert report["sections"]["skills"] is True
        assert report["sections"]["contact"] is True


def test_multi_resume_primary_order():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(name="User", email="user@example.com", password_hash="x", role="candidate")
        db.add(user)
        db.flush()

        r1 = Resume(user_id=user.id, filename="v1.pdf", text="first", is_primary=False)
        r2 = Resume(user_id=user.id, filename="v2.pdf", text="second", is_primary=True)
        r3 = Resume(user_id=user.id, filename="v3.pdf", text="third", is_primary=False)
        db.add_all([r1, r2, r3])
        db.flush()

        # latest_resume should select r2 because is_primary is True
        assert latest_resume(db, user.id).id == r2.id

        # Switch primary to r3
        r2.is_primary = False
        r3.is_primary = True
        db.flush()
        assert latest_resume(db, user.id).id == r3.id


def test_jobs_page_phase2_filters():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        j1 = Job(title="India Remote Dev", company="A", location="Bangalore", country="India", remote=True, salary_min=100000, experience_level="entry", description="Remote Python role", active=True)
        j2 = Job(title="US Onsite Dev", company="B", location="San Francisco", country="United States", remote=False, salary_min=None, experience_level="senior", description="US Onsite role", active=True)
        j3 = Job(title="India Intern", company="C", location="Pune", country="India", remote=False, salary_min=None, experience_level="intern", description="Internship role in Pune", active=True)
        db.add_all([j1, j2, j3])
        db.flush()

        # Filter by country India
        india_jobs, count = jobs_page(db, "", "", "", 1, 10, country="India")
        assert count == 2
        assert {j.id for j in india_jobs} == {j1.id, j3.id}

        # Filter by remote
        remote_jobs, count = jobs_page(db, "", "", "", 1, 10, remote=True)
        assert count == 1
        assert remote_jobs[0].id == j1.id

        # Filter by salary disclosed
        sal_jobs, count = jobs_page(db, "", "", "", 1, 10, salary_disclosed=True)
        assert count == 1
        assert sal_jobs[0].id == j1.id

        # Filter by experience_level
        intern_jobs, count = jobs_page(db, "", "", "", 1, 10, experience_level="intern")
        assert count == 1
        assert intern_jobs[0].id == j3.id


def test_manual_application_model():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(name="User", email="cand@example.com", password_hash="x", role="candidate")
        db.add(user)
        db.flush()

        follow_date = utcnow() + timedelta(days=7)
        app = Application(
            user_id=user.id,
            job_id=None,
            custom_company="BrowserStack",
            custom_title="Frontend Engineer",
            custom_url="https://browserstack.com/careers/123",
            status="Applied",
            notes="Submitted referral via employee.",
            follow_up_at=follow_date,
        )
        db.add(app)
        db.flush()

        loaded = db.get(Application, app.id)
        assert loaded.job_id is None
        assert loaded.custom_company == "BrowserStack"
        assert loaded.follow_up_at is not None
        assert loaded.status == "Applied"
