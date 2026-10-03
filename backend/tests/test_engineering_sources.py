import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.ingestion.adapters import AshbyAdapter
from app.ingestion.http import FeedHTTP
from app.ingestion.normalization import RawJob
from app.ingestion.relevance import is_cse_role
from app.ingestion.service import ingest
from app.models import IngestionSource, Job


def test_ashby_public_fields_salary_and_unlisted_privacy():
    row = {
        "title": "Machine Learning Engineer",
        "isListed": True,
        "descriptionHtml": "<p>Python PyTorch</p><script>bad()</script>",
        "location": "London",
        "employmentType": "FullTime",
        "isRemote": False,
        "jobUrl": "https://jobs.ashbyhq.com/acme/job-1",
        "applyUrl": "https://jobs.ashbyhq.com/acme/job-1/apply",
        "publishedAt": "2026-09-01T12:00:00Z",
        "compensation": {
            "summaryComponents": [
                {"compensationType": "EquityPercentage", "minValue": 1, "maxValue": 2},
                {
                    "compensationType": "Salary",
                    "minValue": 80000,
                    "maxValue": 100000,
                    "currencyCode": "GBP",
                    "interval": "1 YEAR",
                },
            ]
        },
    }

    def handler(request):
        assert request.url.host == "api.ashbyhq.com"
        assert request.url.params["includeCompensation"] == "true"
        return httpx.Response(200, json={"jobs": [row, {**row, "isListed": False}]})

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db, httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = AshbyAdapter(FeedHTTP(db, client=client), {"slug": "acme", "company": "Acme"})
        jobs = adapter.fetch()
        assert adapter.complete and len(jobs) == 1
        job = jobs[0]
        assert job.external_id == "job-1"
        assert job.company == "Acme" and job.attribution == "Ashby"
        assert job.description == "Python PyTorch"
        assert (job.salary_min, job.salary_max, job.salary_currency, job.salary_interval) == (
            80000,
            100000,
            "GBP",
            "year",
        )
        assert job.employment_type == "Full-time"


@pytest.mark.parametrize(
    "title,description,expected",
    [
        ("SWE Intern", "", True),
        ("Generative AI Engineer", "", True),
        ("MLOps Engineer", "", True),
        ("Forward Deployed Engineer", "Python and distributed systems", True),
        ("Software Recruiter", "Python and SQL", False),
        ("Account Executive - AI", "Python and machine learning", False),
        ("Mechanical Engineer", "Build cooling systems", False),
    ],
)
def test_cse_selection(title, description, expected):
    assert is_cse_role(title, description) is expected


def test_filtered_snapshot_closes_out_of_scope_roles():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    class Snapshot:
        complete = True

        def fetch(self):
            return [
                RawJob(
                    external_id=str(i),
                    title=title,
                    company="Acme",
                    description="Python SQL",
                    apply_url=f"https://example.org/{i}",
                    attribution="Test",
                    attribution_url=f"https://example.org/{i}",
                )
                for i, title in enumerate(["Software Engineer", "Sales Manager"])
            ]

    with Session(engine) as db:
        source = IngestionSource(key="cse", kind="ashby", config={})
        db.add(source)
        db.commit()
        assert ingest(db, source, Snapshot())["added"] == 2
        source.config = {"role_scope": "cse"}
        result = ingest(db, source, Snapshot())
        assert result["filtered_out"] == 1 and result["closed"] == 1
        assert [j.title for j in db.scalars(select(Job).where(Job.active.is_(True)))] == ["Software Engineer"]
