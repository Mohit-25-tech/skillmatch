# Stage 05 — complete changed/new source

```text
.github/workflows/ci.yml
README.md
backend/tests/test_product.py
docs/stages/05_VERIFICATION.md
frontend/e2e/live.spec.ts
frontend/e2e/workspace.spec.ts
frontend/playwright.config.ts
frontend/src/lib/api.test.ts
frontend/src/lib/utils.test.ts
frontend/vite.config.ts
scripts/run_e2e_api.py
```

## .github/workflows/ci.yml

````
name: Build and test
on:
  push:
  pull_request:
permissions:
  contents: read
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
          cache-dependency-path: backend/requirements.txt
      - run: pip install --index-url https://download.pytorch.org/whl/cpu torch
      - run: pip install -r backend/requirements.txt
      - run: ruff check backend scripts
      - run: pytest
        working-directory: backend
      - run: alembic upgrade head
        working-directory: backend
        env:
          DATABASE_URL: sqlite:///./migration-test.db
          SEMANTIC_ENABLED: 'false'
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
        working-directory: frontend
      - run: npm test
        working-directory: frontend
      - run: npm run build
        working-directory: frontend
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
          cache-dependency-path: backend/requirements.txt
      - run: pip install --index-url https://download.pytorch.org/whl/cpu torch
      - run: pip install -r backend/requirements.txt
      - run: npx playwright install --with-deps chromium
        working-directory: frontend
      - run: npm run test:e2e
        working-directory: frontend
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: browser-test-results
          path: frontend/test-results
  docker:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: ./backend
          push: false
          cache-from: type=gha,scope=backend
          cache-to: type=gha,mode=max,scope=backend
      - uses: docker/build-push-action@v6
        with:
          context: ./frontend
          push: false
          cache-from: type=gha,scope=frontend
          cache-to: type=gha,mode=max,scope=frontend

````

## README.md

````
# SkillMatch AI

A job discovery and application workspace built with FastAPI, PostgreSQL/pgvector, and TypeScript with jQuery. The existing animated violet interface now reads persisted application data.

## Architecture

```mermaid
flowchart LR
  Browser[TypeScript / jQuery / Chart.js / SortableJS] --> Web[nginx]
  Web --> API[FastAPI / JWT]
  API --> DB[(PostgreSQL / pgvector)]
  Worker[Single scheduler and durable SQL worker] --> DB
  Worker --> Sources[Configured official job APIs]
  Worker --> SMTP[SMTP / optional Mailpit]
  Worker --> Model[Local embedding model]
  API --> Ollama[Optional Ollama]
  API -->|Authenticated SSE| Browser
```

The API persists work items; one worker processes ingestion, enrichment, matching, alerts, digests and insight snapshots. Redis is unnecessary for the current SQL queue. SQLite supports local development with lexical matching/search fallbacks; PostgreSQL enables vector similarity, full-text search and trigram indexes.

## Start with Docker

1. Copy `.env.example` to `.env`. Replace credential placeholders locally; never commit `.env`.
2. Configure a PostgreSQL database as below and generate a unique JWT secret. Set a real contact in `INGESTION_USER_AGENT`.
3. Run `docker compose up --build`.

Open http://localhost:8080. The API container applies migrations and seeds only taxonomy and curated learning resources. No jobs or accounts are invented at startup. Register a candidate or recruiter through the UI. Source administration requires an administrator account provisioned by the database owner; public registration cannot create administrators.

For local SMTP, set `SMTP_HOST=mailpit`, `SMTP_PORT=1025`, `SMTP_STARTTLS=false`, and run `docker compose --profile mail up --build`. Mailpit's inbox is http://localhost:8025. Users must opt into email digests in Settings.

For a disposable local Postgres database, set `DEV_DB_PASSWORD` and use `DATABASE_URL=postgresql+psycopg://skillmatch:YOUR_LOCAL_PASSWORD@dev-db:5432/skillmatch`, then run `docker compose --profile dev up --build`. The API waits for database availability. The optional database uses the official pgvector PostgreSQL image; its entrypoint initializes storage before running PostgreSQL as its database user. API, worker, nginx and Mailpit run without root privileges.

Production requires `ENVIRONMENT=production`, a strong `JWT_SECRET`, PostgreSQL, `COOKIE_SECURE=true`, HTTPS termination and explicit `CORS_ORIGINS`. The example contains no usable credentials. Production rejects demo mode.

## Neon and pgvector

Create a project and database in the [Neon console](https://console.neon.tech), then copy the connection string into your private `.env`, using the SQLAlchemy driver prefix `postgresql+psycopg://` and retaining `sslmode=require`. Use a database role permitted to create extensions for migration, and a direct connection when applying migrations.

In Neon's SQL editor run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

The migrations also enable these extensions when permitted. See [Neon PostgreSQL extensions](https://neon.com/docs/extensions/pg-extensions) and [pgvector documentation](https://github.com/pgvector/pgvector). The schema and embedding model use 384 dimensions; changing models requires a deliberate migration and re-embedding.

## Local development

Python 3.12 and Node 22 are used in CI. On Windows:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
# Edit .env: DATABASE_URL=sqlite:///./skillmatch.db and SEMANTIC_ENABLED=false
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m app.seed
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

In another terminal, from `backend`, run `../.venv/Scripts/python.exe -m app.worker`. In a third terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to port 8000. `API_PROXY_TARGET` can override this address. Enable semantic matching when the embedding model is available; its first load can download model weights. API documentation is at `/docs` (see the app's configured documentation routes if serving directly).

## Features

- Public job browsing with cursor pagination, filters, source attribution, original apply links, detail pages and similar jobs.
- Latest-resume match explanations, ATS-style text checks, per-job suggestions, and database-backed skill-gap resources.
- Saved jobs and a persisted application board with drag and drop, keyboard-accessible status selectors, notes and timelines. Dashboard applications/interviews count these records.
- Saved searches, authenticated SSE notifications, unread/read state and optional SMTP digests.
- Market charts based on stored jobs and daily snapshots. Salary charts separate currency and pay period; missing salary stays unknown.
- Ctrl+K and header search across jobs, companies, skills and pages.
- Per-user theme and preferences. Matching considers available location/remote evidence; role and salary preferences also appear in explanations. Missing evidence is disclosed rather than treated as a perfect match.
- Recruiter native jobs, ranked discoverable candidates and application pipeline. Before application, candidate discovery exposes name and score, not resume/contact information.
- Administrator source configuration, scheduling controls and ingestion run history.

Optional writing assistance requires `OLLAMA_ENABLED=true` and a reachable `OLLAMA_URL` with the configured model installed. It drafts text; users review it before use. All other features work without Ollama. ATS checks inspect extracted text and are not a guarantee of compatibility with a particular employer's ATS.

## Data sources and terms

All sources start disabled. Configure real company slugs/credentials and enable permitted sources using the administration UI or `backend/sources.yaml`. Deployment owners must check the source's current terms and permissions before enabling it. The adapters use official endpoints; arbitrary scrape URLs are not accepted.

| Source | API / terms | Configuration |
| --- | --- | --- |
| Greenhouse | [Job Board API](https://developers.greenhouse.io/job-board-api.html), [terms](https://www.greenhouse.com/terms-of-service) | Authorized company board slug |
| Lever | [Postings API and license](https://github.com/lever/postings-api), [terms](https://www.lever.co/terms-of-service/) | Company slug and region |
| Remotive | [Public API and usage terms](https://remotive.com/remote-jobs/api) | Attribution and original link; public browsing remains ungated |
| Arbeitnow | [API](https://www.arbeitnow.com/api/job-board-api), [terms](https://www.arbeitnow.com/terms) | Public feed |
| Remote OK | [API including legal metadata](https://remoteok.com/api) | Preserve source credit and original link |
| Adzuna | [API](https://developer.adzuna.com/overview), [API terms](https://developer.adzuna.com/docs/terms_of_service) | Account keys, country and query; respect account quotas |
| Hacker News | [Official API and license](https://github.com/HackerNews/API), [guidelines](https://news.ycombinator.com/newsguidelines.html) | Optional explicit hiring-thread ID |

Remotive requires source attribution and prohibits requiring signup just to see listings. Adzuna has account-level quotas and permitted-use conditions. Configure cadence to your permitted quota; source retries and page caps do not replace account-level license compliance. No external feed was enabled or fetched during these local browser tests.

## What is real vs demo

| UI data | Origin |
| --- | --- |
| Jobs, companies, salaries and locations | Native recruiter records or configured API ingestion |
| Match scores and missing skills | Latest uploaded resume and persisted job skills/embeddings |
| Application/interview counts, notes, dates | Application records and event timeline |
| Notifications | Saved-search matches, with persisted read state |
| Insight charts | Stored live/native jobs and actual snapshots; no fabricated history |
| Learning resources | Curated database table seeded on setup |
| Marketing copy | Static presentation text |
| Demo jobs | Only explicit `python -m app.seed --demo`; marked `is_demo`, hidden by default |

No frontend demo arrays remain. A fresh database can legitimately show empty states. In development only, set `DEMO_MODE=true` to expose explicit demo rows. Historic synthetic rows are marked by migration rather than deleted. Test fixtures are isolated from the application database. Unknown salary, dates or evidence are displayed as unknown, not estimated.

## Verification and migrations

```powershell
.venv/Scripts/python.exe -m ruff check backend scripts
.venv/Scripts/python.exe -m pytest backend/tests -q
cd frontend
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests start an isolated temporary SQLite API and worker on port 8012 and Vite on 5182. Windows uses installed Chrome; CI uses Chromium. They do not reuse or modify your development database. Tests cover the API client, mocked source adapters, deduplication, matching, authorization, migrations and real browser workflows. GitHub Actions runs Ruff, backend/frontend/browser tests and both Docker image builds.

From `backend`, run `python -m alembic upgrade head`. Latest migration: `c6f4a1b209d3` (five query indexes). Previous migrations are preserved. Back up existing databases before deployment. Run only one worker scheduler in this version. PostgreSQL/vector execution, live provider credentials, real SMTP delivery and model availability require verification in the deployment environment; SQLite tests do not prove those integrations.

## Staged delivery

Each report links a complete source snapshot, changed-file list and run commands:

- [Stage 1: audit and matching](docs/stages/01_AUDIT.md)
- [Stage 2: ingestion and Docker](docs/stages/02_INGESTION.md)
- [Stage 3: backend features](docs/stages/03_BACKEND.md)
- [Stage 4: frontend integration](docs/stages/04_FRONTEND.md)
- [Stage 5: tests, CI and documentation](docs/stages/05_VERIFICATION.md)
- [Stage 6: engineering hardening](docs/stages/06_ENGINEERING.md)

Older source exports are historical snapshots; the working files and latest stage snapshots describe the current implementation.

````

## backend/tests/test_product.py

````
from io import BytesIO
from unittest.mock import patch

from docx import Document
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app
from app.models import Job, Notification, Resume, Skill, WorkItem
from app.services.match_pipeline import match_resume
from app.services.matching import calculate_match
from app.services.product import create_alerts
from tests.conftest import account
from tests.test_api import JOB, resume_file


def upload(client, headers, content=None):
    return client.post(
        "/api/v1/resumes", headers=headers, files={"file": ("resume.docx", content or resume_file())}
    ).json()["id"]


def test_saved_state_match_filter_and_theme_preserves_scores(client):
    owner = account(client, "owner@example.com", "recruiter")
    job_id = client.post("/api/v1/jobs", headers=owner, json=JOB).json()["id"]
    candidate = account(client)
    assert client.get(f"/api/v1/jobs/{job_id}", headers=candidate).json()["saved"] is False
    client.post(f"/api/v1/jobs/{job_id}/save", headers=candidate)
    assert client.get(f"/api/v1/jobs/{job_id}", headers=candidate).json()["saved"] is True
    assert client.get("/api/v1/jobs?min_match=1", headers=candidate).json()["total"] == 0
    upload(client, candidate)
    score = client.get(f"/api/v1/jobs/{job_id}", headers=candidate).json()["score"]
    assert client.get(f"/api/v1/jobs?min_match={score}", headers=candidate).json()["total"] == 1
    assert client.get(f"/api/v1/jobs?min_match={score + 1}", headers=candidate).json()["total"] == 0
    from app.models import MatchResult

    with next(app.dependency_overrides[get_db]()) as db:
        before = list(db.scalars(select(MatchResult.id)))
        tasks = list(db.scalars(select(WorkItem.id)))
    profile = client.get("/api/v1/profile", headers=candidate).json()
    profile["preferences"]["theme"] = "light"
    response = client.put(
        "/api/v1/profile",
        headers=candidate,
        json={"name": profile["name"], "preferences": profile["preferences"]},
    )
    assert response.status_code == 200
    with next(app.dependency_overrides[get_db]()) as db:
        assert list(db.scalars(select(MatchResult.id))) == before
        assert list(db.scalars(select(WorkItem.id))) == tasks


def test_publisher_timestamps_normalize_to_utc():
    from app.ingestion.normalization import timestamp

    assert timestamp("2026-09-29T10:30:00+05:30") == timestamp("2026-09-29T05:00:00Z")
    assert timestamp("2026-09-29T05:00:00") == timestamp("2026-09-29T05:00:00Z")
    assert timestamp("unknown") is None


def test_workspace_scores_latest_resume_and_tracker_privacy(client):
    recruiter = account(client, "owner@example.com", "recruiter")
    ids = [
        client.post("/api/v1/jobs", headers=recruiter, json={**JOB, "title": f"Python Engineer {n}"}).json()[
            "id"
        ]
        for n in range(3)
    ]
    candidate = account(client)
    saved = client.post(f"/api/v1/jobs/{ids[0]}/save", headers=candidate)
    assert saved.status_code == 201, saved.text
    assert client.get("/api/v1/applications", headers=recruiter).json() == []
    assert client.get("/api/v1/analytics", headers=candidate).json()["applications"] == 0
    resume_id = upload(client, candidate)
    jobs = client.get("/api/v1/jobs?size=2", headers=candidate).json()
    assert all(j["score"] == 66.7 for j in jobs["items"])
    rest = client.get("/api/v1/jobs", params={"cursor": jobs["next_cursor"]}, headers=candidate).json()
    assert len(rest["items"]) == 1
    assert len(client.get("/api/v1/matches", headers=candidate).json()) == 3
    applied = client.post(
        "/api/v1/applications", headers=candidate, json={"resume_id": resume_id, "job_id": ids[0]}
    )
    assert applied.status_code == 201, applied.text
    row = client.patch(
        f"/api/v1/tracker/{saved.json()['id']}",
        headers=candidate,
        json={"status": "Offer", "notes": "Follow up Friday"},
    ).json()
    assert [e["status"] for e in row["timeline"]] == ["Saved", "Applied", "Offer"]
    other = account(client, "other@example.com")
    assert (
        client.patch(f"/api/v1/tracker/{row['id']}", headers=other, json={"status": "Rejected"}).status_code
        == 404
    )
    doc = Document()
    doc.add_paragraph("Product manager with stakeholder communication and planning experience.")
    buffer = BytesIO()
    doc.save(buffer)
    latest = upload(client, candidate, buffer.getvalue())
    client.get("/api/v1/jobs", headers=candidate)
    matches = client.get("/api/v1/matches", headers=candidate).json()
    assert len(matches) == 3 and all(m["resume_id"] == latest for m in matches)
    assert client.get("/api/v1/analytics", headers=candidate).json()["matches"] == 3


def test_profile_resume_tools_and_public_discovery(client):
    owner = account(client, "owner@example.com", "recruiter")
    job_id = client.post(
        "/api/v1/jobs", headers=owner, json={**JOB, "salary_min": None, "salary_max": None}
    ).json()["id"]
    candidate = account(client)
    resume_id = upload(client, candidate)
    response = client.put(
        "/api/v1/profile",
        headers=candidate,
        json={
            "name": "Jane Smith",
            "preferences": {"theme": "light", "locations": ["Remote"], "remote_preference": "any"},
        },
    )
    assert response.status_code == 200
    assert client.get("/api/v1/profile", headers=candidate).json()["preferences"]["theme"] == "light"
    assert client.get(f"/api/v1/resumes/{resume_id}/ats", headers=candidate).json()["word_count"] > 0
    tailoring = client.get(f"/api/v1/jobs/{job_id}/tailoring", headers=candidate)
    assert tailoring.status_code == 200, tailoring.text
    assert tailoring.json()["match"]["improvements"]
    assert client.post(f"/api/v1/jobs/{job_id}/draft", headers=candidate).status_code == 503
    assert client.get("/api/v1/search?q=Python").json()["jobs"]
    assert client.get("/api/v1/insights/market").json()["salaries"] == []
    assert client.get("/api/v1/learning-path", headers=candidate).json()["items"][0]["related_jobs"] == 1
    assert client.get(f"/api/v1/jobs/{job_id}/similar").status_code == 200
    # Non-applicants are excluded without discoverability consent.
    assert client.get(f"/api/v1/jobs/{job_id}/candidates", headers=owner).json()["items"] == []
    client.put(
        "/api/v1/profile",
        headers=candidate,
        json={"name": "Jane Smith", "preferences": {"discoverable": True}},
    )
    client.get("/api/v1/jobs", headers=candidate)
    ranked = client.get(f"/api/v1/jobs/{job_id}/candidates", headers=owner).json()["items"]
    assert set(ranked[0]) == {"candidate_id", "name", "score"}


def test_saved_search_notifications_and_ownership(client):
    candidate = account(client)
    search = client.post(
        "/api/v1/saved-searches",
        headers=candidate,
        json={"name": "Python", "filters": {"keywords": "Python", "min_match": 20}},
    )
    assert search.status_code == 201
    owner = account(client, "owner@example.com", "recruiter")
    client.post("/api/v1/jobs", headers=owner, json=JOB)
    upload(client, candidate)
    override = app.dependency_overrides[get_db]
    with next(override()) as db:
        resume = db.scalar(select(Resume))
        match_resume(db, resume)
        create_alerts(db, resume)
        db.commit()
        assert len(db.scalars(select(Notification)).all()) == 1
    notifications = client.get("/api/v1/notifications", headers=candidate).json()
    assert notifications["unread"] == 1
    notification_id = notifications["items"][0]["id"]
    other = account(client, "other@example.com")
    assert client.post(f"/api/v1/notifications/{notification_id}/read", headers=other).status_code == 404
    assert client.delete(f"/api/v1/saved-searches/{search.json()['id']}", headers=other).status_code == 404
    assert client.post(f"/api/v1/notifications/{notification_id}/read", headers=candidate).status_code == 200
    assert client.get("/api/v1/notifications", headers=candidate).json()["unread"] == 0
    assert client.get("/api/v1/notifications/stream").status_code == 401


def test_weighted_experience_location_and_optional_skills():
    python, sql = Skill(name="Python"), Skill(name="SQL")
    resume = Resume(text="3 years of experience", skills=[python], experience_years=3)
    job = Job(
        title="Engineer",
        description="5 years experience",
        skills=[python, sql],
        skill_importance={"SQL": "nice-to-have"},
        experience_min=5,
        location="London",
        remote=False,
    )
    result = calculate_match(resume, job, {"locations": ["London"]})
    assert result["keyword_score"] == 71.4
    assert result["components"]["experience"]["score"] == 60
    assert result["components"]["location"]["score"] == 100
    assert result["components"]["semantic"]["score"] is None
    assert result["score"] == 70.9


def test_worker_durable_resume_task(client):
    owner = account(client, "owner@example.com", "recruiter")
    for n in range(4):
        client.post("/api/v1/jobs", headers=owner, json={**JOB, "title": f"Python Engineer {n}"})
    candidate = account(client)
    resume_id = upload(client, candidate)
    with next(app.dependency_overrides[get_db]()) as db:
        bind = db.get_bind()
        # Prior native catalog tasks are independently exercised by all-task processing.
    from app.worker import process_tasks

    with patch("app.worker.SessionLocal", side_effect=lambda: Session(bind)):
        for _ in range(5):
            process_tasks()
    status = client.get("/api/v1/matches/status", headers=candidate).json()
    assert status["resume_id"] == resume_id and status["scored_jobs"] == 4 and status["pending_jobs"] == 0
    with Session(bind) as db:
        assert set(db.scalars(select(WorkItem.status))) == {"done"}


def test_admin_ingestion_controls_and_digest_opt_in(client):
    import smtplib

    from app.config import get_settings
    from app.models import SavedSearch, User
    from app.services.product import send_digests

    admin = account(client, "admin@example.com")
    with next(app.dependency_overrides[get_db]()) as db:
        db.scalar(select(User).where(User.email == "admin@example.com")).role = "admin"
        db.commit()
    created = client.post(
        "/api/v1/admin/ingestion",
        headers=admin,
        json={"key": "test", "kind": "greenhouse", "config": {"slug": "acme"}},
    )
    assert created.status_code == 201
    source_id = created.json()["id"]
    assert client.post(f"/api/v1/admin/ingestion/{source_id}/run", headers=admin).status_code == 409
    assert (
        client.patch(
            f"/api/v1/admin/ingestion/{source_id}",
            headers=admin,
            json={"enabled": True, "config": {"slug": "new-acme"}},
        ).status_code
        == 200
    )
    first = client.post(f"/api/v1/admin/ingestion/{source_id}/run", headers=admin).json()
    assert (
        client.post(f"/api/v1/admin/ingestion/{source_id}/run", headers=admin).json()["work_item_id"]
        == first["work_item_id"]
    )
    candidate = account(client)
    assert client.get("/api/v1/admin/ingestion", headers=candidate).status_code == 403
    owner = account(client, "owner@example.com", "recruiter")
    job_id = client.post("/api/v1/jobs", headers=owner, json=JOB).json()["id"]
    with next(app.dependency_overrides[get_db]()) as db:
        user = db.scalar(select(User).where(User.email == "candidate@example.com"))
        search = SavedSearch(user_id=user.id, name="All", filters={})
        db.add(search)
        db.flush()
        notification = Notification(user_id=user.id, search_id=search.id, job_id=job_id, title="New job")
        db.add(notification)
        db.commit()
        with (
            patch.object(get_settings(), "smtp_host", "mailpit"),
            patch("app.services.product.smtplib.SMTP") as smtp,
        ):
            assert send_digests(db) == 0
            smtp.assert_not_called()
            user.preferences = {"email_digest": True}
            db.commit()
            smtp.return_value.__enter__.return_value.send_message.side_effect = smtplib.SMTPException(
                "offline"
            )
            import pytest

            with pytest.raises(smtplib.SMTPException):
                send_digests(db)
            assert notification.emailed_at is None
            smtp.return_value.__enter__.return_value.send_message.side_effect = None
            assert send_digests(db) == 1
            assert notification.emailed_at is not None
            assert send_digests(db) == 0

````

## docs/stages/05_VERIFICATION.md

````
# Stage 5: tests, CI and documentation

Added typed-client tests for authentication, concurrent refresh, multipart uploads, errors and streamed SSE frames. Browser tests exercise registration, resume upload, real matching, saving, drag-and-drop and select-based status changes, timeline notes, dashboard counts, ATS, saved searches, live notifications, search, persisted themes, responsive boundaries, administrator source controls and network recovery. Tests use a separate temporary database and test-only worker; no live feeds or application data are touched.

GitHub Actions runs Ruff, pytest, Vitest, production frontend compilation, Playwright and both Docker builds. The README now includes architecture, Neon setup, source/API terms links, environment configuration, deployment commands and a real-versus-demo table.

## Changed/new files and full code

[Complete source and file list](05_SOURCE.md).

## Run commands

```powershell
.venv/Scripts/python.exe -m ruff check backend scripts
.venv/Scripts/python.exe -m pytest backend/tests -q
cd frontend
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

No migration is introduced by this stage. Backend tests exercise upgrades from a populated original schema and empty-database downgrade/re-upgrade. CI configuration is committed as source, but no hosted GitHub Actions run was triggered. PostgreSQL-specific runtime behavior still needs a real PostgreSQL environment.

````

## frontend/e2e/live.spec.ts

````
import { test, expect } from "@playwright/test";
import path from "node:path";
test("real candidate workflow: scores, save, tracker, notes, search, alerts, ATS and theme", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const suffix = Date.now(),
    password = "browser-test-password-2026";
  const recruiter = await (
    await request.post("/api/v1/auth/register", {
      data: {
        name: "Browser Recruiter",
        email: `recruiter${suffix}@example.com`,
        password,
        role: "recruiter",
      },
    })
  ).json();
  const headers = { Authorization: `Bearer ${recruiter.access_token}` };
  const jobData = {
    title: `Python Engineer ${suffix}`,
    company: "Test Studio",
    location: "Remote",
    employment_type: "Full-time",
    description:
      "Build Python FastAPI PostgreSQL services with our collaborative engineering team. Required: Python. Nice to have: Docker.",
    skills: ["Python", "FastAPI", "PostgreSQL"],
    salary_min: null,
    salary_max: null,
  };
  const job = await (
    await request.post("/api/v1/jobs", { headers, data: jobData })
  ).json();
  await page.goto("/#/register");
  await page.getByLabel("Your name").fill("Browser Candidate");
  await page.getByLabel("Email address").fill(`candidate${suffix}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create my account" }).click();
  await expect(
    page.getByRole("heading", { name: "Your next move, Browser." }),
  ).toBeVisible();
  await page.getByRole("link", { name: "My resume", exact: true }).click();
  await page
    .locator("#resume-file")
    .setInputFiles(path.resolve("../artifacts/e2e-stage4-resume.docx"));
  await page.getByRole("button", { name: "Analyze my resume" }).click();
  await expect(page.locator(".resume-file")).toContainText(
    "e2e-stage4-resume.docx",
  );
  await page.goto(`/#/jobs/${job.id}`);
  await expect(page.locator(".big-gauge")).toBeVisible();
  await expect(page.locator(".job-salary")).toContainText("Not disclosed");
  await page.getByRole("button", { name: "Save role", exact: true }).click();
  await expect(page.locator("#toasts")).toContainText(
    "Saved in your application tracker",
  );
  await page.getByRole("link", { name: "Applications", exact: true }).click();
  await expect(page.locator(".kanban-card")).toContainText(jobData.title);
  await page
    .locator(".drag-handle")
    .dragTo(page.locator(".kanban-list[data-status=Applied]"));
  await expect(page.locator(".kanban-list[data-status=Applied]")).toContainText(
    jobData.title,
  );
  await page.locator(".tracker-status").selectOption("Interview");
  await expect(
    page
      .locator(".kanban-column")
      .filter({ has: page.getByRole("heading", { name: "Interview 1" }) }),
  ).toContainText(jobData.title);
  await page.getByRole("button", { name: "Notes & timeline" }).click();
  await page.getByLabel("Notes", { exact: true }).fill("Prepare API examples");
  await page.getByRole("button", { name: "Save notes", exact: true }).click();
  await page.getByRole("button", { name: "Notes & timeline" }).click();
  await expect(page.locator(".timeline")).toContainText("Prepare API examples");
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(
    page.locator(".stat-card").filter({ hasText: "Interviews" }),
  ).toContainText("1");
  await page.getByRole("link", { name: "Resume tools", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Resume readiness." }),
  ).toBeVisible();
  await expect(page.locator(".job-detail")).toContainText("text readiness");
  await page.goto("/#/jobs");
  await page.getByLabel("Job title, company, or skill").fill("Python");
  await page.getByRole("button", { name: "Find roles", exact: true }).click();
  await expect(page.locator(".job-card")).not.toHaveCount(0);
  await page.getByRole("button", { name: "Save this search" }).click();
  await page.getByLabel("Name", { exact: true }).fill("Python opportunities");
  await page.getByRole("button", { name: "Save search", exact: true }).click();
  const next = await request.post("/api/v1/jobs", {
    headers,
    data: { ...jobData, title: `Python Developer ${suffix}` },
  });
  expect(next.ok()).toBeTruthy();
  await expect(page.locator(".unread-count")).toHaveText("1", {
    timeout: 15000,
  });
  await page.getByRole("button", { name: "View notifications" }).click();
  await expect(page.locator(".notification-item")).toContainText(
    "Python Developer",
  );
  await page.getByRole("button", { name: "Mark as read" }).click();
  await expect(page.locator(".unread-count")).toBeHidden();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.keyboard.press("Control+k");
  await page.getByLabel("Jobs, companies, skills or pages").fill("Python");
  await expect(page.locator("#command-results")).toContainText(jobData.title);
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "Toggle light or dark theme" })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "../artifacts/stage4-mobile-light.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});

test("administrator sees real source controls and history", async ({
  page,
}) => {
  await page.goto("/#/login");
  await page.getByLabel("Email address").fill("admin@e2e.example");
  await page
    .getByLabel("Password", { exact: true })
    .fill("e2e-admin-test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("link", { name: "Ingestion", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "test-disabled" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Configure", exact: true }).click();
  await page.getByLabel("Interval in minutes").fill("720");
  await page.getByRole("button", { name: "Save configuration" }).click();
  await page.getByRole("button", { name: "Run history" }).click();
  await expect(page.locator("dialog")).toContainText("No runs yet.");
});

````

## frontend/e2e/workspace.spec.ts

````
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("public landing and jobs have no synthetic workspace", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "Your skills. Your potential. Your next chapter.",
    }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Explore jobs", exact: true }).click();
  await expect(page.locator("#jobs-count")).toContainText(
    "active opportunities",
  );
  await expect(page.locator("body")).not.toContainText("Alex Morgan");
  await page
    .getByLabel("Job title, company, or skill")
    .fill("no-such-role-unique");
  await page.getByRole("button", { name: "Find roles", exact: true }).click();
  await expect(page.locator("#job-results")).toContainText(
    "No matching opportunities yet.",
  );
  await page.screenshot({
    path: "../artifacts/stage4-jobs-empty.png",
    fullPage: true,
  });
  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(axe.violations.filter((v) => v.impact === "critical")).toEqual([]);
});
test("network failure displays retry and recovers", async ({ page }) => {
  await page.route("**/api/v1/jobs?**", (route) =>
    route.fulfill({ status: 503, json: { detail: "Temporarily unavailable" } }),
  );
  await page.goto("/#/jobs");
  await expect(page.locator("#job-results")).toContainText(
    "Temporarily unavailable",
  );
  await page.unroute("**/api/v1/jobs?**");
  await page.getByRole("button", { name: "Retry loading jobs" }).click();
  await expect(page.locator("#jobs-count")).toContainText(
    "active opportunities",
  );
});
test("mobile landing and sign-in retain page boundaries", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.goto("/#/login");
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});

````

## frontend/playwright.config.ts

````
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  use: {
    baseURL: "http://127.0.0.1:5182",
    headless: true,
    channel: process.env.CI ? undefined : "chrome",
    viewport: { width: 1440, height: 1100 },
    reducedMotion: "reduce",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        process.platform === "win32"
          ? "..\\.venv\\Scripts\\python.exe ../scripts/run_e2e_api.py"
          : "python ../scripts/run_e2e_api.py",
      url: "http://127.0.0.1:8012/api/v1/health",
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command: "npm run dev -- --port 5182 --strictPort",
      url: "http://127.0.0.1:5182",
      reuseExistingServer: false,
      timeout: 60000,
      env: { API_PROXY_TARGET: "http://127.0.0.1:8012" },
    },
  ],
  reporter: "list",
});

````

## frontend/src/lib/api.test.ts

````
import { beforeEach, describe, expect, it, vi } from "vitest";
const mock = vi.hoisted(() => ({ ajax: vi.fn() }));
vi.mock("jquery", () => ({ default: { ajax: mock.ajax } }));
import { api, refreshSession, setToken, notificationStream } from "./api";
function response(data: unknown, fail = false) {
  mock.ajax.mockImplementationOnce(() => {
    const chain = {
      done(callback: (value: unknown) => void) {
        if (!fail) queueMicrotask(() => callback(data));
        return chain;
      },
      fail(callback: (value: unknown) => void) {
        if (fail) queueMicrotask(() => callback(data));
        return chain;
      },
    };
    return chain;
  });
}
describe("typed AJAX client", () => {
  beforeEach(() => {
    mock.ajax.mockReset();
    setToken("");
  });
  it("serializes JSON and attaches bearer credentials", async () => {
    setToken("test-token");
    response({ id: 1 });
    expect(await api("/jobs", "POST", { title: "Engineer" })).toEqual({
      id: 1,
    });
    expect(mock.ajax).toHaveBeenCalledWith(
      expect.objectContaining({
        url: "/api/v1/jobs",
        method: "POST",
        data: '{"title":"Engineer"}',
        headers: { Authorization: "Bearer test-token" },
      }),
    );
  });
  it("sends multipart without JSON conversion", async () => {
    const data = new FormData();
    data.append("file", new Blob(["test"]), "cv.docx");
    response({ id: 2 });
    await api("/resumes", "POST", data);
    expect(mock.ajax).toHaveBeenCalledWith(
      expect.objectContaining({ data, contentType: false, processData: false }),
    );
  });
  it("refreshes expired access and retries exactly once", async () => {
    response({ status: 401 }, true);
    response({ access_token: "renewed", user: { id: 7 } });
    response({ items: [] });
    expect(await api("/jobs")).toEqual({ items: [] });
    expect(mock.ajax).toHaveBeenCalledTimes(3);
  });
  it("deduplicates concurrent refresh calls", async () => {
    response({ access_token: "renewed", user: { id: 7 } });
    await Promise.all([refreshSession(), refreshSession()]);
    expect(mock.ajax).toHaveBeenCalledTimes(1);
  });
  it("returns server validation errors without an HTML response", async () => {
    response(
      { status: 422, responseJSON: { detail: [{ msg: "Invalid filter" }] } },
      true,
    );
    await expect(api("/jobs")).rejects.toThrow("Invalid filter");
  });
  it("reports network errors", async () => {
    response({ status: 0 }, true);
    await expect(api("/jobs")).rejects.toThrow("Unable to reach");
  });
  it("parses split SSE frames and cancels the subscription", async () => {
    setToken("stream-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        new ReadableStream({
          start(controller) {
            controller.enqueue(
              new TextEncoder().encode(
                'event: notifications\ndata: {"items":[],"unread":',
              ),
            );
            controller.enqueue(
              new TextEncoder().encode('2,"next_cursor":4}\n\n'),
            );
            controller.close();
          },
        }),
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const data = vi.fn();
    const cancel = notificationStream(data, vi.fn());
    await vi.waitFor(() =>
      expect(data).toHaveBeenCalledWith({
        items: [],
        unread: 2,
        next_cursor: 4,
      }),
    );
    cancel();
    expect(fetchMock.mock.calls[0][0]).not.toContain("token");
    vi.unstubAllGlobals();
  });
});

````

## frontend/src/lib/utils.test.ts

````
import { describe, expect, it } from "vitest";
import {
  escapeHtml,
  initials,
  salary,
  scoreLabel,
  validateFile,
  safeUrl,
  postedAge,
} from "./utils";
describe("safe display and resume validation", () => {
  it("escapes untrusted markup and attributes", () =>
    expect(escapeHtml("<img src=\"x\" onerror='x'>&")).toBe(
      "&lt;img src=&quot;x&quot; onerror=&#39;x&#39;&gt;&amp;",
    ));
  it("rejects unsupported and oversized uploads", () => {
    expect(validateFile({ name: "cv.exe", size: 100 })).toBeTruthy();
    expect(
      validateFile({ name: "cv.pdf", size: 6 * 1024 * 1024 }),
    ).toBeTruthy();
    expect(validateFile({ name: "cv.DOCX", size: 1024 })).toBeNull();
  });
  it("formats salaries and names", () => {
    expect(salary(null, null)).toBe("Not disclosed");
    expect(salary(120000, 160000, "USD", "year")).toContain(new Intl.NumberFormat(undefined,{style:"currency",currency:"USD",maximumFractionDigits:0}).format(120000));
    expect(salary(120000, null)).toContain("currency not supplied");
    expect(safeUrl("javascript:alert(1)")).toBe("");
    expect(safeUrl("https://example.org/job")).toBe("https://example.org/job");
    expect(postedAge(null)).toBe("Posting date not supplied");
    expect(initials(" Alex  Morgan ")).toBe("AM");
  });
  it("labels match scores consistently", () => {
    expect(scoreLabel(90)).toBe("Excellent match");
    expect(scoreLabel(70)).toBe("Strong match");
    expect(scoreLabel(40)).toBe("Room to grow");
  });
});

````

## frontend/vite.config.ts

````
import { defineConfig, loadEnv } from "vite";
export default defineConfig(({ mode }) => ({
  server: {
    proxy: {
      "/api":
        process.env.API_PROXY_TARGET || loadEnv(mode, ".", "").API_PROXY_TARGET || "http://127.0.0.1:8000",
      "^/docs$":
        process.env.API_PROXY_TARGET || loadEnv(mode, ".", "").API_PROXY_TARGET || "http://127.0.0.1:8000",
      "/openapi.json":
        process.env.API_PROXY_TARGET || loadEnv(mode, ".", "").API_PROXY_TARGET || "http://127.0.0.1:8000",
    },
  },
  build: {
    target: "es2022",
    rollupOptions: {
      output: {
        manualChunks: {
          charts: ["chart.js"],
          animation: ["gsap"],
          vendor: ["jquery"],
        },
      },
    },
  },
}));

````

## scripts/run_e2e_api.py

````
"""Isolated browser-test server. Never connects to a configured application database."""

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DATABASE_URL"] = (
    "sqlite:///"
    + (Path(tempfile.mkdtemp(prefix="skillmatch-e2e-")) / "test.db").as_posix()
)
os.environ["ENVIRONMENT"] = "test"
os.environ["SEMANTIC_ENABLED"] = "false"
os.environ["DEMO_MODE"] = "false"
os.environ["COOKIE_SECURE"] = "false"
os.environ["SMTP_HOST"] = ""
os.environ["OLLAMA_ENABLED"] = "false"
os.environ["CORS_ORIGINS"] = "http://127.0.0.1:5182,http://localhost:5182"

import uvicorn
from app.db import Base, SessionLocal, engine
from app.limits import limiter
from app.main import app
from app.models import IngestionSource, User
from app.security import password_hash
from app.seed import seed
from app.worker import heartbeat, process_tasks
from docx import Document

resume = Document()
resume.add_paragraph(
    "Python engineer with 3 years of experience. Skills: Python FastAPI PostgreSQL Docker. Experience building APIs. Education: Computer Science. Contact: test@example.com"
)
(ROOT / "artifacts").mkdir(exist_ok=True)
resume.save(ROOT / "artifacts" / "e2e-stage4-resume.docx")

Base.metadata.create_all(engine)
seed()
limiter.enabled = False
with SessionLocal() as db:
    db.add(
        User(
            name="Test Administrator",
            email="admin@e2e.example",
            password_hash=password_hash.hash("e2e-admin-test-password"),
            role="admin",
        )
    )
    db.add(
        IngestionSource(
            key="test-disabled",
            kind="greenhouse",
            config={"slug": "example"},
            enabled=False,
        )
    )
    db.commit()


def worker():
    while True:
        process_tasks()
        heartbeat()
        time.sleep(0.5)


threading.Thread(target=worker, daemon=True).start()
uvicorn.run(app, host="127.0.0.1", port=8012, log_level="warning")

````
