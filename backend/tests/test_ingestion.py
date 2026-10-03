import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.ingestion.adapters import GreenhouseAdapter
from app.ingestion.http import FeedHTTP
from app.ingestion.normalization import RawJob, plain_text, salary_text
from app.ingestion.service import ingest
from app.models import IngestionSource, Job


def test_official_http_adapter():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    def handler(request):
        assert request.url.host == "boards-api.greenhouse.io"
        return httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "id": 1,
                        "title": "ML Engineer",
                        "location": {"name": "Remote"},
                        "content": "<p>Python PyTorch</p>",
                        "absolute_url": "https://example.org/job/1",
                    }
                ]
            },
        )

    with Session(engine) as db, httpx.Client(transport=httpx.MockTransport(handler)) as client:
        http = FeedHTTP(db, client=client, sleep=lambda _: None)
        adapter = GreenhouseAdapter(http, {"slug": "acme"})
        rows = adapter.fetch()
        assert adapter.complete and rows[0].salary_min is None
        assert rows[0].description == "Python PyTorch"


def test_dedupe_complete_partial_and_failure():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    class Snapshot:
        complete = True
        rows = [
            RawJob(
                external_id="1",
                title="ML Engineer",
                company="Acme",
                description="Python PyTorch",
                apply_url="https://example.org/1",
                attribution="Test",
                attribution_url="https://example.org/1",
            )
        ]

        def fetch(self):
            return self.rows

    with Session(engine) as db:
        source = IngestionSource(key="a", kind="greenhouse")
        db.add(source)
        db.commit()
        adapter = Snapshot()
        assert ingest(db, source, adapter)["added"] == 1
        assert ingest(db, source, adapter)["added"] == 0
        job = db.scalar(select(Job))
        assert {s.name for s in job.skills} == {"Python", "PyTorch", "Machine Learning"}
        adapter.rows, adapter.complete = [], False
        assert ingest(db, source, adapter)["closed"] == 0
        assert job.active
        adapter.complete = True
        assert ingest(db, source, adapter)["closed"] == 1
        assert not job.active


def test_sanitization_and_unknown_pay():
    assert plain_text("<script>alert(1)</script><b>Python</b>") == "Python"
    assert salary_text("competitive") == {}
    with pytest.raises(ValueError):
        RawJob(
            external_id="x",
            title="Engineer",
            company="Acme",
            description="test",
            apply_url="javascript:alert(1)",
            attribution="x",
            attribution_url="https://example.org",
        )


@pytest.mark.parametrize(
    "kind,payload",
    [
        (
            "lever",
            [
                {
                    "id": "l1",
                    "text": "Python Engineer",
                    "categories": {"location": "Remote"},
                    "descriptionPlain": "Python",
                    "hostedUrl": "https://jobs.lever.co/acme/l1",
                    "createdAt": 1700000000000,
                }
            ],
        ),
        (
            "remotive",
            {
                "jobs": [
                    {
                        "id": 1,
                        "title": "Python Engineer",
                        "company_name": "Acme",
                        "description": "<p>Python</p>",
                        "url": "https://remotive.com/remote-jobs/1",
                        "salary": "USD 100k-150k per year",
                        "job_type": None,
                    }
                ]
            },
        ),
        (
            "arbeitnow",
            {
                "data": [
                    {
                        "slug": "a1",
                        "title": "Python Engineer",
                        "company_name": "Acme",
                        "description": "Python",
                        "url": "https://www.arbeitnow.com/jobs/a1",
                    }
                ],
                "links": {"next": None},
            },
        ),
        (
            "remoteok",
            [
                {"legal": "Attribute Remote OK"},
                {
                    "id": 1,
                    "position": "Python Engineer",
                    "company": "Acme",
                    "description": "Python",
                    "url": "https://remoteok.com/remote-jobs/1",
                    "salary_min": 0,
                    "salary_max": 0,
                },
            ],
        ),
        (
            "adzuna",
            {
                "count": 1,
                "results": [
                    {
                        "id": "1",
                        "title": "Python Engineer",
                        "description": "Python",
                        "redirect_url": "https://www.adzuna.in/details/1",
                        "salary_min": 100,
                        "salary_max": 200,
                        "salary_is_predicted": "1",
                    }
                ],
            },
        ),
    ],
)
def test_all_feed_adapters_mock_http(kind, payload, monkeypatch):
    from app.config import get_settings
    from app.ingestion.adapters import ADAPTERS

    monkeypatch.setattr(get_settings(), "adzuna_app_id", "test-id")
    monkeypatch.setattr(get_settings(), "adzuna_app_key", "test-key")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with (
        Session(engine) as db,
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))) as client,
    ):
        adapter = ADAPTERS[kind](
            FeedHTTP(db, client=client, sleep=lambda _: None), {"slug": "acme", "country": "in"}
        )
        rows = adapter.fetch()
        assert adapter.complete and len(rows) == 1
        assert rows[0].description == "Python"
        if kind == "remotive":
            assert rows[0].salary_min == 100000 and rows[0].salary_currency == "USD"
            assert rows[0].employment_type == "Not specified"
        else:
            assert rows[0].salary_min is None


def test_hn_thread_validation_and_no_closure():
    from app.ingestion.adapters import HackerNewsAdapter

    def handler(request):
        if request.url.path.endswith("/100.json"):
            return httpx.Response(
                200, json={"title": "Ask HN: Who is hiring?", "by": "whoishiring", "kids": [101]}
            )
        return httpx.Response(
            200, json={"text": "Acme | Python Engineer | Remote<p>Python</p>", "time": 1700000000}
        )

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db, httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = HackerNewsAdapter(FeedHTTP(db, client=client, sleep=lambda _: None), {"thread_id": 100})
        assert adapter.fetch()[0].company == "Acme"
        assert not adapter.complete


def test_retry_conditional_cache_and_host_restriction():
    from app.ingestion.http import FeedError

    seen = []

    def handler(request):
        seen.append(request)
        if len(seen) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        if len(seen) == 2:
            return httpx.Response(
                200, json={"jobs": []}, headers={"ETag": "abc", "Cache-Control": "no-cache"}
            )
        assert request.headers["If-None-Match"] == "abc"
        return httpx.Response(304, headers={"Cache-Control": "max-age=3600"})

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db, httpx.Client(transport=httpx.MockTransport(handler)) as client:
        http = FeedHTTP(db, client=client, sleep=lambda _: None)
        url = "https://boards-api.greenhouse.io/v1/boards/acme/jobs"
        assert http.get(url) == {"jobs": []}
        assert http.get(url) == {"jobs": []}
        assert http.get(url) == {"jobs": []}
        assert len(seen) == 3
        with pytest.raises(FeedError):
            http.get("http://localhost/internal")


def test_multi_source_closure_and_failed_feed_preserve_rows():
    from app.ingestion.http import FeedError

    class Snapshot:
        complete = True
        rows = [
            RawJob(
                external_id="1",
                title="Python Engineer",
                company="Acme",
                description="Python",
                apply_url="https://example.org/1",
                attribution="Test",
                attribution_url="https://example.org/1",
            )
        ]

        def fetch(self):
            return self.rows

    class Broken:
        def fetch(self):
            raise FeedError("invalid upstream")

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        a, b = IngestionSource(key="a", kind="greenhouse"), IngestionSource(key="b", kind="lever")
        db.add_all([a, b])
        db.commit()
        assert ingest(db, a, Snapshot())["added"] == 1
        assert ingest(db, b, Snapshot())["added"] == 0
        assert ingest(db, b, Broken())["status"] == "error"
        empty = Snapshot()
        empty.rows = []
        assert ingest(db, a, empty)["closed"] == 0
        assert db.scalar(select(Job)).active
        assert ingest(db, b, empty)["closed"] == 1


def test_remotive_defers_repeated_runs_and_does_not_retry_http():
    from unittest.mock import Mock

    from app.ingestion.http import FeedError
    from app.models import utcnow

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        source = IngestionSource(key="remotive", kind="remotive", last_run_at=utcnow())
        db.add(source)
        db.commit()
        adapter = Mock()
        assert ingest(db, source, adapter)["status"] == "deferred"
        adapter.fetch.assert_not_called()
        calls = []

        def unavailable(request):
            calls.append(request)
            return httpx.Response(503)

        with httpx.Client(transport=httpx.MockTransport(unavailable)) as client:
            http = FeedHTTP(db, client=client, sleep=lambda _: None)
            with pytest.raises(FeedError):
                http.get("https://remotive.com/api/remote-jobs")
            assert len(calls) == 1
