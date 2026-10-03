# Stage 07 — complete changed/new source

```text
README.md
backend/app/ingestion/adapters.py
backend/app/ingestion/http.py
backend/app/ingestion/normalization.py
backend/app/ingestion/relevance.py
backend/app/ingestion/service.py
backend/app/routers/ingestion.py
backend/sources.yaml
backend/tests/test_engineering_sources.py
docs/ENGINEERING_FEEDS.md
```

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

Vite proxies `/api` to port 8000 by default. Set `API_PROXY_TARGET` in the root `.env` to override this address. Process environment takes precedence, then frontend `.env`, then root `.env`.

If registration returns **404**, verify `/openapi.json` reports **SkillMatch AI**. A different app may occupy port 8000. This workspace uses `API_PROXY_TARGET=http://127.0.0.1:8010`; start its backend with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload` from `backend`. Restart Vite after changing `.env`. For LAN access, add the exact browser origin (for example `http://172.16.0.2:5173`) to `CORS_ORIGINS` and restart the API. The browser continues to use Vite's `/api` proxy; the backend need not be exposed on the LAN. Enable semantic matching when the embedding model is available; its first load can download model weights. API documentation is at `/docs` (see the app's configured documentation routes if serving directly).

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

The curated Together AI (Greenhouse), Palantir (Lever), and Cohere (Ashby) engineering boards are enabled in `backend/sources.yaml`. General feeds remain opt-in. Configure additional permitted company boards/credentials using the administration UI or YAML. Existing database settings take precedence over YAML initialization. Deployment owners must check the source's current terms and permissions before enabling it. The adapters use official endpoints; arbitrary scrape URLs are not accepted.

| Source | API / terms | Configuration |
| --- | --- | --- |
| Greenhouse | [Job Board API](https://developers.greenhouse.io/job-board-api.html), [terms](https://www.greenhouse.com/terms-of-service) | Authorized company board slug |
| Lever | [Postings API and license](https://github.com/lever/postings-api), [terms](https://www.lever.co/terms-of-service/) | Company slug and region |
| Ashby | [Public postings API](https://developers.ashbyhq.com/docs/public-job-posting-api), [terms](https://www.ashbyhq.com/terms) | Company board slug; unlisted roles excluded |
| Remotive | [Public API and usage terms](https://remotive.com/remote-jobs/api) | Attribution and original link; public browsing remains ungated |
| Arbeitnow | [API](https://www.arbeitnow.com/api/job-board-api), [terms](https://www.arbeitnow.com/terms) | Public feed |
| Remote OK | [API including legal metadata](https://remoteok.com/api) | Preserve source credit and original link |
| Adzuna | [API](https://developer.adzuna.com/overview), [API terms](https://developer.adzuna.com/docs/terms_of_service) | Account keys, country and query; respect account quotas |
| Hacker News | [Official API and license](https://github.com/HackerNews/API), [guidelines](https://news.ycombinator.com/newsguidelines.html) | Optional explicit hiring-thread ID |

Remotive requires source attribution and prohibits requiring signup just to see listings. Adzuna has account-level quotas and permitted-use conditions. Configure cadence to your permitted quota; source retries and page caps do not replace account-level license compliance. Browser tests use isolated mock data. The workspace database has separately received real public feed imports.

## Curated engineering sources

The worker imports the Together AI, Palantir and Cohere boards every 12 hours. Their source config uses `role_scope: cse` to select software/SDE/SWE, AI/ML/GenAI, data, platform/cloud, DevOps/SRE and security engineering roles. Selection uses titles plus technical description evidence for generic engineering titles, and excludes sales/recruiting roles. It is a deterministic relevance filter, not a guarantee that every technical role will be recognized. Set `role_scope: all` to import every publicly listed role from an authorized board.

Jobs retain employer, actual location, source attribution and original application links. These sources contain onsite/hybrid roles as well as remote roles; location eligibility must still be checked. No country or experience-level restriction is imposed. Ashby salary summaries are used only when one explicit salary component is available; equity and bonuses are not treated as salary.

New boards use the existing source table and worker; no migration or API key is needed for these public board endpoints. After updating code, restart the API and the single worker. Adzuna remains disabled until its credentials are configured. Employer/source usage terms still apply to any redistribution.

## Remotive setup

The adapter uses `https://remotive.com/api/remote-jobs`; no API key is required for this public feed. In the administrator Ingestion page, enable the existing Remotive source with a 720-minute interval and run the worker. Source settings already stored in the database take precedence over the initial YAML defaults.

The first live import was completed for this workspace and Remotive was enabled in its configured database. Keep `python -m app.worker` running from `backend` for subsequent scheduled imports. The feed is delayed by 24 hours and its returned listing count can differ from the paid website's catalog. Job cards and details retain Remotive source links and public browsing does not require registration. The importer enforces a six-hour minimum between attempts and makes no immediate HTTP retries for Remotive failures.

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

## backend/app/ingestion/adapters.py

````
"""Official APIs only. No employer-page, LinkedIn, Indeed, or Naukri scraping."""

import re
from abc import ABC, abstractmethod

from app.config import get_settings
from app.ingestion.http import FeedError, FeedHTTP
from app.ingestion.normalization import RawJob, plain_text, salary_text, timestamp


def slug(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", value):
        raise FeedError("Invalid company slug")
    return value


class Adapter(ABC):
    complete = False

    def __init__(self, http: FeedHTTP, config: dict):
        self.http, self.config = http, config
        self.complete = False

    @abstractmethod
    def fetch(self) -> list[RawJob]:
        """Return a validated snapshot; set complete only after every page succeeds."""
        raise NotImplementedError


class GreenhouseAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        company = slug(self.config["slug"])
        body = self.http.get(
            f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs", {"content": "true"}
        )
        if not isinstance(body, dict) or not isinstance(body.get("jobs"), list):
            raise FeedError("Invalid Greenhouse feed")
        jobs = []
        for row in body["jobs"]:
            location = row.get("location", {}).get("name") or "Not specified"
            text = plain_text(row.get("content", ""))
            jobs.append(
                RawJob(
                    external_id=str(row["id"]),
                    title=row["title"],
                    company=self.config.get("company", company),
                    location=location[:100],
                    remote="remote" in location.lower(),
                    description=text,
                    apply_url=row["absolute_url"],
                    posted_at=timestamp(row.get("first_published")),
                    attribution="Greenhouse",
                    attribution_url=row["absolute_url"],
                    **salary_text(text),
                )
            )
        self.complete = True
        return jobs


class LeverAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        company = slug(self.config["slug"])
        host = "api.eu.lever.co" if self.config.get("region") == "eu" else "api.lever.co"
        jobs = []
        for page in range(get_settings().ingestion_max_pages):
            body = self.http.get(
                f"https://{host}/v0/postings/{company}", {"mode": "json", "skip": page * 100, "limit": 100}
            )
            if not isinstance(body, list):
                raise FeedError("Invalid Lever feed")
            for row in body:
                cats = row.get("categories") or {}
                pay = row.get("salaryRange") or {}
                text = (
                    (row.get("descriptionPlain") or row.get("description", ""))
                    + "\n"
                    + "\n".join(
                        str(x.get("text", "")) + "\n" + x.get("content", "") for x in row.get("lists", [])
                    )
                )
                jobs.append(
                    RawJob(
                        external_id=row["id"],
                        title=row["text"],
                        company=self.config.get("company", company),
                        location=(cats.get("location") or "Not specified")[:100],
                        remote=row.get("workplaceType") == "remote",
                        employment_type=cats.get("commitment") or "Not specified",
                        description=text,
                        apply_url=row.get("applyUrl") or row["hostedUrl"],
                        posted_at=timestamp(row.get("createdAt")),
                        salary_min=round(pay["min"]) if pay.get("min") is not None else None,
                        salary_max=round(pay["max"]) if pay.get("max") is not None else None,
                        salary_currency=pay.get("currency"),
                        salary_interval=pay.get("interval"),
                        attribution="Lever",
                        attribution_url=row["hostedUrl"],
                    )
                )
            if len(body) < 100:
                self.complete = True
                break
        return jobs


class AshbyAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        board = slug(self.config["slug"])
        body = self.http.get(
            f"https://api.ashbyhq.com/posting-api/job-board/{board}",
            {"includeCompensation": "true"},
        )
        if not isinstance(body, dict) or not isinstance(body.get("jobs"), list):
            raise FeedError("Invalid Ashby feed")
        jobs = []
        for row in body["jobs"]:
            if row.get("isListed") is not True:
                continue
            # Use only the publisher's summary salary, not equity or guessed units.
            salaries = [
                c
                for c in (row.get("compensation") or {}).get("summaryComponents", [])
                if c.get("compensationType") == "Salary"
            ]
            pay = salaries[0] if len(salaries) == 1 else {}
            jobs.append(
                RawJob(
                    external_id=row.get("id") or row["jobUrl"].rstrip("/").rsplit("/", 1)[-1],
                    title=row["title"],
                    company=self.config.get("company", board),
                    location=(row.get("location") or "Not specified")[:100],
                    remote=bool(row.get("isRemote")),
                    employment_type=row.get("employmentType") or "Not specified",
                    description=row.get("descriptionPlain") or row.get("descriptionHtml") or "",
                    apply_url=row.get("applyUrl") or row["jobUrl"],
                    posted_at=timestamp(row.get("publishedAt")),
                    salary_min=round(pay["minValue"]) if pay.get("minValue") is not None else None,
                    salary_max=round(pay["maxValue"]) if pay.get("maxValue") is not None else None,
                    salary_currency=pay.get("currencyCode"),
                    salary_interval={"1 YEAR": "year", "1 MONTH": "month", "1 HOUR": "hour"}.get(
                        pay.get("interval")
                    ),
                    attribution="Ashby",
                    attribution_url=row["jobUrl"],
                )
            )
        self.complete = True
        return jobs


class RemotiveAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        body = self.http.get("https://remotive.com/api/remote-jobs")
        if not isinstance(body, dict) or not isinstance(body.get("jobs"), list):
            raise FeedError("Invalid Remotive feed")
        result = [
            RawJob(
                external_id=str(r["id"]),
                title=r["title"],
                company=r["company_name"],
                location=(r.get("candidate_required_location") or "Not specified")[:100],
                remote=True,
                employment_type=r.get("job_type") or "Not specified",
                description=r["description"],
                apply_url=r["url"],
                posted_at=timestamp(r.get("publication_date")),
                attribution="Remotive",
                attribution_url=r["url"],
                **salary_text(r.get("salary", "")),
            )
            for r in body["jobs"]
        ]
        self.complete = True
        return result


class ArbeitnowAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        jobs = []
        for page in range(1, get_settings().ingestion_max_pages + 1):
            body = self.http.get("https://www.arbeitnow.com/api/job-board-api", {"page": page})
            if not isinstance(body, dict) or not isinstance(body.get("data"), list):
                raise FeedError("Invalid Arbeitnow feed")
            for r in body["data"]:
                jobs.append(
                    RawJob(
                        external_id=r["slug"],
                        title=r["title"],
                        company=r["company_name"],
                        location=(r.get("location") or "Not specified")[:100],
                        remote=bool(r.get("remote")),
                        employment_type=",".join(r.get("job_types", [])) or "Not specified",
                        description=r["description"],
                        apply_url=r["url"],
                        posted_at=timestamp(r.get("created_at")),
                        attribution="Arbeitnow",
                        attribution_url=r["url"],
                    )
                )
            if not body.get("links", {}).get("next"):
                self.complete = True
                break
        return jobs


class RemoteOKAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        body = self.http.get("https://remoteok.com/api")
        if not isinstance(body, list) or not body or not isinstance(body[0], dict) or "legal" not in body[0]:
            raise FeedError("Invalid Remote OK feed or missing attribution terms")
        jobs = []
        for r in body[1:]:
            jobs.append(
                RawJob(
                    external_id=str(r["id"]),
                    title=r["position"],
                    company=r["company"],
                    location=(r.get("location") or "Not specified")[:100],
                    remote=True,
                    description=r["description"],
                    apply_url=r["url"],
                    posted_at=timestamp(r.get("date") or r.get("epoch")),
                    salary_min=r.get("salary_min") or None,
                    salary_max=r.get("salary_max") or None,
                    salary_currency=r.get("salary_currency"),
                    salary_interval="year" if r.get("salary_min") else None,
                    attribution="Remote OK",
                    attribution_url=r["url"],
                )
            )
        self.complete = True
        return jobs


class AdzunaAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        settings = get_settings()
        if (
            not settings.adzuna_app_id
            or not settings.adzuna_app_key
            or "PLACEHOLDER" in settings.adzuna_app_key
        ):
            raise FeedError("Configure ADZUNA_APP_ID and ADZUNA_APP_KEY")
        country = self.config.get("country", "in").lower()
        if country not in {
            "in",
            "gb",
            "us",
            "au",
            "at",
            "be",
            "br",
            "ca",
            "ch",
            "de",
            "es",
            "fr",
            "it",
            "mx",
            "nl",
            "nz",
            "pl",
            "sg",
            "za",
        }:
            raise FeedError("Unsupported Adzuna country")
        jobs = []
        for page in range(1, settings.ingestion_max_pages + 1):
            body = self.http.get(
                f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}",
                {
                    "app_id": settings.adzuna_app_id,
                    "app_key": settings.adzuna_app_key,
                    "results_per_page": 50,
                    "what": self.config.get("query", ""),
                    "content-type": "application/json",
                },
            )
            if not isinstance(body, dict) or not isinstance(body.get("results"), list):
                raise FeedError("Invalid Adzuna feed")
            for r in body["results"]:
                actual = str(r.get("salary_is_predicted", "1")) == "0"
                jobs.append(
                    RawJob(
                        external_id=str(r["id"]),
                        title=plain_text(r["title"]),
                        company=r.get("company", {}).get("display_name", "Not specified"),
                        location=r.get("location", {}).get("display_name", "Not specified")[:100],
                        remote=bool(re.search(r"\bremote\b", r["title"], re.I)),
                        employment_type=r.get("contract_time", "Not specified").replace("_", "-"),
                        description=r["description"],
                        apply_url=r["redirect_url"],
                        posted_at=timestamp(r.get("created")),
                        salary_min=round(r["salary_min"])
                        if actual and r.get("salary_min") is not None
                        else None,
                        salary_max=round(r["salary_max"])
                        if actual and r.get("salary_max") is not None
                        else None,
                        salary_currency=r.get("salary_currency"),
                        salary_interval="year" if actual and r.get("salary_min") is not None else None,
                        attribution="Adzuna",
                        attribution_url=r["redirect_url"],
                    )
                )
            if len(body["results"]) < 50 or len(jobs) >= body.get("count", float("inf")):
                self.complete = True
                break
        return jobs


class HackerNewsAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        thread_id = int(self.config["thread_id"])
        parent = self.http.get(f"https://hacker-news.firebaseio.com/v0/item/{thread_id}.json")
        if (
            not parent
            or "who is hiring" not in parent.get("title", "").lower()
            or parent.get("by") != "whoishiring"
        ):
            raise FeedError("Configure an official Who is hiring thread ID")
        jobs = []
        ids = parent.get("kids", [])
        limit = int(self.config.get("max_comments", 200))
        for item_id in ids[:limit]:
            row = self.http.get(f"https://hacker-news.firebaseio.com/v0/item/{int(item_id)}.json")
            if not row or row.get("deleted") or row.get("dead") or not row.get("text"):
                continue
            description = plain_text(row["text"])
            first = description.split("\n")[0]
            company = first.split("|")[0].strip()[:100] or "Not specified"
            url = f"https://news.ycombinator.com/item?id={item_id}"
            jobs.append(
                RawJob(
                    external_id=str(item_id),
                    title=first[:150],
                    company=company,
                    description=description,
                    remote=bool(re.search(r"\bremote\b", first, re.I)),
                    apply_url=url,
                    posted_at=timestamp(row.get("time")),
                    attribution="Hacker News — Who is hiring",
                    attribution_url=url,
                    **salary_text(description),
                )
            )
        # A discussion is not an authoritative active-jobs inventory; never close from disappearance.
        self.complete = False
        return jobs


ADAPTERS = {
    "ashby": AshbyAdapter,
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "remotive": RemotiveAdapter,
    "arbeitnow": ArbeitnowAdapter,
    "remoteok": RemoteOKAdapter,
    "adzuna": AdzunaAdapter,
    "hackernews": HackerNewsAdapter,
}

````

## backend/app/ingestion/http.py

````
"""Bounded, allowlisted HTTP reads with conditional caching and retries."""

import hashlib
import json
import re
import time
from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import FeedCache, utcnow

HOSTS = {
    "api.ashbyhq.com",
    "boards-api.greenhouse.io",
    "api.lever.co",
    "api.eu.lever.co",
    "remotive.com",
    "www.arbeitnow.com",
    "remoteok.com",
    "api.adzuna.com",
    "hacker-news.firebaseio.com",
}


class FeedError(RuntimeError):
    pass


class FeedHTTP:
    def __init__(self, db: Session, client: httpx.Client | None = None, sleep=time.sleep):
        self.db, self.sleep = db, sleep
        self.client = client or httpx.Client(timeout=get_settings().ingestion_timeout, follow_redirects=False)
        self.owned = client is None
        self.last_request = 0.0

    def close(self):
        if self.owned:
            self.client.close()

    def get(self, url: str, params: dict | None = None):
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in HOSTS
            or parsed.username
            or parsed.port not in (None, 443)
        ):
            raise FeedError("Only configured official API hosts are permitted")
        key = hashlib.sha256((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
        cached = self.db.get(FeedCache, key)
        now = utcnow()
        if cached and cached.expires_at.replace(tzinfo=timezone.utc) > now:
            return cached.payload
        headers = {"User-Agent": get_settings().ingestion_user_agent, "Accept": "application/json"}
        if cached:
            if cached.etag:
                headers["If-None-Match"] = cached.etag
            if cached.modified:
                headers["If-Modified-Since"] = cached.modified
        # Remotive asks for at most four reads daily. Retry on the next run,
        # rather than sending multiple requests when its service is unavailable.
        attempts = 1 if parsed.hostname == "remotive.com" else 3
        for attempt in range(attempts):
            delay = get_settings().ingestion_request_delay - (time.monotonic() - self.last_request)
            if delay > 0:
                self.sleep(delay)
            try:
                response = self.client.get(url, params=params, headers=headers)
                self.last_request = time.monotonic()
                if response.status_code == 429 or response.status_code >= 500:
                    if attempts == 1:
                        raise FeedError("Source unavailable; defer to next scheduled run")
                    retry = response.headers.get("Retry-After", "")
                    if retry.isdigit():
                        wait = int(retry)
                    else:
                        try:
                            wait = max(0, (parsedate_to_datetime(retry) - now).total_seconds())
                        except (TypeError, ValueError):
                            wait = 2**attempt
                    if wait > 30:
                        raise FeedError("Source requested a longer retry delay; defer to next scheduled run")
                    self.sleep(wait)
                    continue
                if response.status_code == 304 and cached:
                    payload = cached.payload
                else:
                    if response.status_code != 200:
                        raise FeedError(f"Source returned HTTP {response.status_code}")
                    if len(response.content) > 30 * 1024 * 1024:
                        raise FeedError("Feed exceeds the 30 MB response limit")
                    payload = response.json()
                control = response.headers.get("Cache-Control", "")
                max_age = re.search(r"(?:s-maxage|max-age)=(\d+)", control)
                expiry = now + timedelta(seconds=int(max_age[1]) if max_age else 0)
                if not max_age and response.headers.get("Expires"):
                    try:
                        expiry = parsedate_to_datetime(response.headers["Expires"])
                    except (TypeError, ValueError):
                        pass
                if "no-cache" in control:
                    expiry = now
                if "no-store" not in control:
                    cached = cached or FeedCache(key=key)
                    cached.payload, cached.expires_at = payload, expiry
                    cached.etag = response.headers.get("ETag", cached.etag)
                    cached.modified = response.headers.get("Last-Modified", cached.modified)
                    self.db.add(cached)
                    self.db.flush()
                elif cached:
                    self.db.delete(cached)
                    self.db.flush()
                return payload
            except (httpx.TransportError, ValueError):
                if attempt < attempts - 1:
                    self.sleep(2**attempt)
        raise FeedError("Source unavailable after bounded attempts")

````

## backend/app/ingestion/normalization.py

````
import hashlib
import html
import re
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.blocked = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "iframe", "object"}:
            self.blocked += 1
        if tag in {"p", "br", "li", "div", "h1", "h2", "h3"} and not self.blocked:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "iframe", "object"}:
            self.blocked = max(0, self.blocked - 1)
        if tag in {"p", "li", "div"} and not self.blocked:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.blocked:
            self.parts.append(data)


def plain_text(value: str) -> str:
    parser = TextParser()
    parser.feed(html.unescape(value or ""))
    return re.sub(r"\n\s*\n+", "\n\n", "".join(parser.parts)).strip()[:100000]


def safe_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in {"https", "http"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("A public HTTP(S) apply URL is required")
    return value


def timestamp(value) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000 if value > 10**11 else value, timezone.utc)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def normalized(value: str) -> str:
    return " ".join(sorted(re.findall(r"[\w+#]+", unicodedata.normalize("NFKC", value).casefold())))


def fingerprint(title: str, company: str, location: str) -> str:
    return hashlib.sha256("|".join(normalized(v) for v in (title, company, location)).encode()).hexdigest()


def salary_text(value: str) -> dict:
    """Only explicit two-ended ranges with an identifiable currency; never estimate."""
    match = re.search(
        r"(?P<c>USD|EUR|GBP|INR|US\$|€|£|₹)\s*(?P<lo>[\d,.]+)\s*(?P<lk>[kK]?)\s*[-–—]\s*(?:USD|EUR|GBP|INR|US\$|€|£|₹)?\s*(?P<hi>[\d,.]+)\s*(?P<hk>[kK]?)",
        value or "",
        re.I,
    )
    if not match:
        return {}
    currency = {"US$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}.get(match["c"].upper(), match["c"].upper())
    low = float(match["lo"].replace(",", "")) * (1000 if match["lk"] or match["hk"] else 1)
    high = float(match["hi"].replace(",", "")) * (1000 if match["hk"] else 1)
    if not 0 < low <= high <= 100000000:
        return {}
    period = next(
        (
            p
            for p, pattern in [
                ("hour", r"hour|hourly"),
                ("month", r"month|monthly"),
                ("year", r"year|annual|annum"),
            ]
            if re.search(pattern, value, re.I)
        ),
        None,
    )
    return dict(
        salary_min=round(low), salary_max=round(high), salary_currency=currency, salary_interval=period
    )


class RawJob(BaseModel):
    external_id: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=150)
    company: str = Field(min_length=1, max_length=100)
    location: str = Field(default="Not specified", max_length=100)
    remote: bool = False
    employment_type: str = "Not specified"
    description: str
    apply_url: str
    posted_at: datetime | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    salary_interval: str | None = None
    attribution: str
    attribution_url: str

    _urls = field_validator("apply_url", "attribution_url")(safe_url)
    _description = field_validator("description", mode="before")(plain_text)

    @field_validator("employment_type", mode="before")
    @classmethod
    def job_type(cls, value):
        key = str(value or "").lower().replace("_", "-").replace(" ", "-")
        return {
            "full-time": "Full-time",
            "fulltime": "Full-time",
            "part-time": "Part-time",
            "parttime": "Part-time",
            "intern": "Internship",
            "contract": "Contract",
            "contractor": "Contract",
            "internship": "Internship",
        }.get(key, str(value or "Not specified")[:30])

    @model_validator(mode="after")
    def validate_salary(self):
        if self.salary_min is not None and self.salary_max is not None and self.salary_max < self.salary_min:
            raise ValueError("Invalid salary range")
        if self.salary_currency:
            self.salary_currency = self.salary_currency.upper()
            if not re.fullmatch(r"[A-Z]{3}", self.salary_currency):
                raise ValueError("Expected a three-letter salary currency")
        return self

````

## backend/app/ingestion/relevance.py

````
"""Conservative engineering-role selection, independent of employer boilerplate."""

import re

NON_TECH = re.compile(
    r"\b(recruiter|recruiting|sales|marketing|account executive|legal|counsel|finance|accountant|people operations|office manager)\b",
    re.I,
)
TECH_TITLE = re.compile(
    r"\b(software|sde|swe|backend|frontend|front.end|back.end|full.stack|machine learning|deep learning|artificial intelligence|generative ai|genai|llm|nlp|computer vision|mlops|devops|sre|data engineer|data scientist|research engineer|research scientist|applied scientist|security engineer|cloud engineer|platform engineer|infrastructure engineer|ai engineer|ml engineer)\b",
    re.I,
)
TECH_EVIDENCE = re.compile(
    r"\b(python|java|typescript|javascript|c\+\+|pytorch|tensorflow|kubernetes|distributed systems|llm|machine learning|sql)\b",
    re.I,
)


def is_cse_role(title: str, description: str) -> bool:
    if NON_TECH.search(title):
        return False
    if TECH_TITLE.search(title):
        return True
    return bool(
        re.search(r"\b(engineer|developer|scientist)\b", title, re.I)
        and len(set(TECH_EVIDENCE.findall(description.lower()))) >= 2
    )

````

## backend/app/ingestion/service.py

````
import hashlib
import json
import logging
from datetime import timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

import yaml
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.ingestion.adapters import ADAPTERS
from app.ingestion.http import FeedHTTP
from app.ingestion.normalization import fingerprint, normalized
from app.ingestion.relevance import is_cse_role
from app.models import IngestionRun, IngestionSource, Job, JobOrigin, MatchResult, WorkItem, utcnow
from app.services.embeddings import encode_many
from app.services.matching import experience, importance
from app.services.parsing import extract_skills
from app.services.taxonomy import ensure_taxonomy

log = logging.getLogger(__name__)


def configure_sources(db: Session) -> None:
    path = Path(get_settings().ingestion_config)
    if not path.exists():
        return
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for item in document.get("sources", []):
        if item["kind"] not in ADAPTERS:
            raise ValueError("Unknown ingestion adapter")
        if not db.scalar(select(IngestionSource).where(IngestionSource.key == item["key"])):
            db.add(
                IngestionSource(
                    key=item["key"],
                    kind=item["kind"],
                    config=item.get("config", {}),
                    enabled=bool(item.get("enabled", False)),
                    interval_minutes=max(
                        360 if item["kind"] == "remotive" else 60,
                        int(item.get("interval_minutes", 360)),
                    ),
                )
            )
    db.commit()


def find_duplicate(db: Session, raw) -> Job | None:
    fp = fingerprint(raw.title, raw.company, raw.location)
    exact = db.scalar(select(Job).where(Job.fingerprint == fp, Job.is_demo.is_(False)))
    if exact:
        return exact
    candidates = db.scalars(
        select(Job).where(
            func.lower(Job.company) == raw.company.casefold(), Job.is_demo.is_(False), Job.source != "native"
        )
    ).all()
    for job in candidates:
        if (
            normalized(job.location) == normalized(raw.location)
            and SequenceMatcher(None, normalized(job.title), normalized(raw.title)).ratio() >= 0.94
        ):
            return job
    return None


def ingest(db: Session, source: IngestionSource, adapter=None) -> dict:
    if source.kind == "remotive" and source.last_run_at:
        earliest = source.last_run_at.replace(tzinfo=timezone.utc) + timedelta(hours=6)
        if utcnow() < earliest:
            return {"status": "deferred", "next_run_at": earliest.isoformat()}
    run = IngestionRun(source_id=source.id)
    source.status, source.last_run_at = "running", utcnow()
    db.add(run)
    db.commit()
    http = FeedHTTP(db)
    stats = {"added": 0, "updated": 0, "closed": 0, "seen": 0}
    try:
        adapter = adapter or ADAPTERS[source.kind](http, source.config)
        rows = adapter.fetch()  # No mutation of availability before the whole fetch validates.
        if source.config.get("role_scope") == "cse":
            selected = [r for r in rows if is_cse_role(r.title, r.description)]
            stats["filtered_out"] = len(rows) - len(selected)
            rows = selected
        taxonomy = {s.name: s for s in ensure_taxonomy(db)}
        origins_by_id = {
            o.external_id: o for o in db.scalars(select(JobOrigin).where(JobOrigin.source_id == source.id))
        }
        candidates = list(
            db.scalars(
                select(Job).where(
                    Job.is_demo.is_(False),
                    or_(
                        func.lower(Job.company).in_({r.company.casefold() for r in rows}),
                        Job.fingerprint.in_({fingerprint(r.title, r.company, r.location) for r in rows}),
                        Job.id.in_({o.job_id for o in origins_by_id.values()}),
                    ),
                )
            )
        )
        jobs_by_id = {j.id: j for j in candidates}
        by_fingerprint = {j.fingerprint: j for j in candidates if j.fingerprint}
        seen = set()
        changed = []
        pending_origins = []
        for raw in rows:
            if raw.external_id in seen:
                continue
            seen.add(raw.external_id)
            origin = origins_by_id.get(raw.external_id)
            fp = fingerprint(raw.title, raw.company, raw.location)
            job = jobs_by_id.get(origin.job_id) if origin else by_fingerprint.get(fp)
            if job is None:
                job = next(
                    (
                        j
                        for j in candidates
                        if j.source != "native"
                        and j.company.casefold() == raw.company.casefold()
                        and normalized(j.location) == normalized(raw.location)
                        and SequenceMatcher(None, normalized(j.title), normalized(raw.title)).ratio() >= 0.94
                    ),
                    None,
                )
            if job is None:
                job = Job(
                    source=source.kind,
                    external_id=f"{source.key}:{raw.external_id}",
                    is_demo=False,
                    active=True,
                )
                db.add(job)
                stats["added"] += 1
                candidates.append(job)
            by_fingerprint[fp] = job
            payload = raw.model_dump(exclude={"external_id", "attribution", "attribution_url"})
            content_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, default=str).encode()
            ).hexdigest()
            if job.content_hash != content_hash:
                if job.id:
                    stats["updated"] += 1
                for key, value in payload.items():
                    setattr(job, key, value)
                job.fingerprint = fingerprint(raw.title, raw.company, raw.location)
                job.content_hash, job.updated_at = content_hash, utcnow()
                names = extract_skills(raw.title + "\n" + raw.description, list(taxonomy))
                job.skills = [taxonomy[n] for n in names]
                job.skill_importance = importance(raw.description, names)
                job.experience_min = experience(raw.description)
                changed.append(job)
            if not job.active and job not in changed:
                changed.append(job)
                stats["updated"] += 1
            job.active = True
            pending_origins.append((origin, job, raw))
        db.flush()
        for origin, job, raw in pending_origins:
            if not origin:
                origin = JobOrigin(job_id=job.id, source_id=source.id, external_id=raw.external_id)
                db.add(origin)
            origin.apply_url, origin.attribution, origin.attribution_url = (
                raw.apply_url,
                raw.attribution,
                raw.attribution_url,
            )
            origin.active, origin.seen_at = True, utcnow()
        for start in range(0, len(changed), 32):
            batch = changed[start : start + 32]
            vectors = encode_many([j.title + "\n" + j.description for j in batch])
            for job, vector in zip(batch, vectors, strict=True):
                job.embedding, job.embedding_model = (
                    vector,
                    get_settings().embedding_model if vector else None,
                )
        if changed:
            db.execute(delete(MatchResult).where(MatchResult.job_id.in_([j.id for j in changed])))
        if adapter.complete:
            origins = db.scalars(
                select(JobOrigin).where(JobOrigin.source_id == source.id, JobOrigin.active.is_(True))
            ).all()
            for origin in origins:
                if origin.external_id not in seen:
                    origin.active = False
                    db.flush()
                    other = db.scalar(
                        select(func.count(JobOrigin.id)).where(
                            JobOrigin.job_id == origin.job_id, JobOrigin.active.is_(True)
                        )
                    )
                    job = db.get(Job, origin.job_id)
                    if not other and job.active and job.source != "native":
                        job.active = False
                        stats["closed"] += 1
        stats["seen"], stats["complete"] = len(seen), adapter.complete
        source.status = run.status = "success" if adapter.complete else "partial"
        source.last_success_at, source.last_error = utcnow(), None
        source.stats = run.stats = stats
        if changed:
            db.add(WorkItem(kind="catalog", payload={"job_ids": [j.id for j in changed]}))
        db.commit()
    except Exception as error:
        db.rollback()
        source = db.get(IngestionSource, source.id)
        run = db.get(IngestionRun, run.id)
        source.status = run.status = "error"
        # Exception text can contain credential-bearing request URLs. Never persist it.
        source.last_error = run.error = (
            f"{type(error).__name__}: feed was not committed; check configuration and source availability"
        )
        log.warning("ingestion_failed source=%s error_type=%s", source.key, type(error).__name__)
    finally:
        http.close()
        source.next_run_at = utcnow() + timedelta(
            minutes=max(360 if source.kind == "remotive" else 60, source.interval_minutes)
        )
        run.finished_at = utcnow()
        db.commit()
    log.info(
        json.dumps(
            {"event": "ingestion_complete", "source": source.key, "status": source.status, "stats": stats}
        )
    )
    return {"status": source.status, **(source.stats if source.status != "error" else {})}

````

## backend/app/routers/ingestion.py

````
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.ingestion.adapters import ADAPTERS
from app.models import IngestionRun, IngestionSource, User, WorkerHeartbeat, WorkItem
from app.security import roles

router = APIRouter(prefix="/admin/ingestion", tags=["Ingestion administration"])


class SourceInput(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9_-]{1,150}$")
    kind: str
    config: dict = Field(default_factory=dict)
    enabled: bool = False
    interval_minutes: int = Field(default=360, ge=60, le=10080)


class SourceUpdate(BaseModel):
    enabled: bool
    interval_minutes: int | None = Field(default=None, ge=60, le=10080)
    config: dict | None = None


def validate_config(config: dict) -> None:
    if config.get("role_scope", "all") not in {"all", "cse"}:
        raise HTTPException(422, "role_scope must be all or cse")
    if any(
        k not in {"slug", "company", "region", "country", "query", "thread_id", "max_comments", "role_scope"}
        for k in config
    ):
        raise HTTPException(422, "Unsupported configuration key; credentials belong in environment variables")
    if any(not isinstance(v, (str, int)) or len(str(v)) > 200 for v in config.values()):
        raise HTTPException(422, "Configuration values must be short strings or integers")
    if "max_comments" in config and (
        not isinstance(config["max_comments"], int) or not 1 <= config["max_comments"] <= 1000
    ):
        raise HTTPException(422, "max_comments must be between 1 and 1000")


def source_public(source: IngestionSource) -> dict:
    return {
        key: getattr(source, key)
        for key in (
            "id",
            "key",
            "kind",
            "config",
            "enabled",
            "interval_minutes",
            "status",
            "stats",
            "last_run_at",
            "last_success_at",
            "last_error",
            "next_run_at",
        )
    }


@router.get("")
def sources(user: User = Depends(roles("admin")), db: Session = Depends(get_db)) -> dict:
    heartbeat = db.get(WorkerHeartbeat, "ingestion")
    return {
        "items": [source_public(s) for s in db.scalars(select(IngestionSource).order_by(IngestionSource.id))],
        "worker_last_seen": heartbeat.seen_at if heartbeat else None,
    }


@router.post("", status_code=201)
def add_source(
    body: SourceInput, user: User = Depends(roles("admin")), db: Session = Depends(get_db)
) -> dict:
    if body.kind not in ADAPTERS:
        raise HTTPException(422, "Unknown adapter")
    validate_config(body.config)
    if any(
        k not in {"slug", "company", "region", "country", "query", "thread_id", "max_comments", "role_scope"}
        for k in body.config
    ):
        raise HTTPException(422, "Unsupported configuration key; credentials belong in environment variables")
    if body.kind in {"remotive", "remoteok"} and body.interval_minutes < 360:
        raise HTTPException(422, "Use an interval of at least 360 minutes for this source")
    source = IngestionSource(**body.model_dump())
    db.add(source)
    db.commit()
    return source_public(source)


@router.patch("/{source_id}")
def toggle(
    source_id: int, body: SourceUpdate, user: User = Depends(roles("admin")), db: Session = Depends(get_db)
) -> dict:
    source = db.get(IngestionSource, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    if body.interval_minutes is not None:
        if source.kind in {"remotive", "remoteok"} and body.interval_minutes < 360:
            raise HTTPException(422, "Minimum interval is 360 minutes for this source")
        source.interval_minutes = body.interval_minutes
    source.enabled = body.enabled
    if body.config is not None:
        validate_config(body.config)
        source.config = body.config
    db.commit()
    return source_public(source)


@router.post("/{source_id}/run", status_code=202)
def run_now(source_id: int, user: User = Depends(roles("admin")), db: Session = Depends(get_db)) -> dict:
    source = db.get(IngestionSource, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    if not source.enabled:
        raise HTTPException(409, "Enable the source before running it")
    item = db.scalar(
        select(WorkItem).where(
            WorkItem.kind == "ingestion",
            WorkItem.status.in_(["pending", "running"]),
            WorkItem.payload["source_id"].as_integer() == source_id,
        )
    )
    if not item:
        item = WorkItem(kind="ingestion", payload={"source_id": source_id})
        db.add(item)
        db.commit()
    return {"work_item_id": item.id, "status": item.status}


@router.get("/{source_id}/runs")
def runs(
    source_id: int,
    page: int = Query(1, ge=1),
    user: User = Depends(roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.scalars(
        select(IngestionRun)
        .where(IngestionRun.source_id == source_id)
        .order_by(IngestionRun.id.desc())
        .offset((page - 1) * 25)
        .limit(25)
    ).all()
    return {
        "items": [
            {k: getattr(r, k) for k in ("id", "started_at", "finished_at", "status", "stats", "error")}
            for r in rows
        ],
        "page": page,
    }

````

## backend/sources.yaml

````
# Add boards you are permitted to republish. No arbitrary URLs are accepted.
# General feeds start disabled; curated engineering boards below are enabled.
sources:
  - key: greenhouse-example
    kind: greenhouse
    enabled: false
    interval_minutes: 360
    config: {slug: YOUR_COMPANY_SLUG, company: YOUR_COMPANY_NAME}
  - key: lever-example
    kind: lever
    enabled: false
    interval_minutes: 360
    config: {slug: YOUR_COMPANY_SLUG, region: global}
  - key: remotive
    kind: remotive
    enabled: false
    interval_minutes: 720
    config: {}
  - key: arbeitnow
    kind: arbeitnow
    enabled: false
    interval_minutes: 360
    config: {}
  - key: remoteok
    kind: remoteok
    enabled: false
    interval_minutes: 720
    config: {}
  - key: adzuna-india
    kind: adzuna
    enabled: false
    interval_minutes: 360
    config: {country: in, query: software}
  - key: adzuna-uk
    kind: adzuna
    enabled: false
    interval_minutes: 360
    config: {country: gb, query: software}
  - key: hackernews
    kind: hackernews
    enabled: false
    interval_minutes: 1440
    config: {thread_id: 0, max_comments: 200}

  # Initial curated engineering boards. Existing DB settings remain authoritative.
  - key: greenhouse-togetherai
    kind: greenhouse
    enabled: true
    interval_minutes: 720
    config: {slug: togetherai, company: Together AI, role_scope: cse}
  - key: lever-palantir
    kind: lever
    enabled: true
    interval_minutes: 720
    config: {slug: palantir, company: Palantir, region: global, role_scope: cse}
  - key: ashby-cohere
    kind: ashby
    enabled: true
    interval_minutes: 720
    config: {slug: cohere, company: Cohere, role_scope: cse}

````

## backend/tests/test_engineering_sources.py

````
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

````

## docs/ENGINEERING_FEEDS.md

````
# Engineering job feeds

Added Ashby public Job Postings API support alongside the existing Greenhouse and Lever adapters. The initial curated boards are Together AI, Cohere and Palantir, selected for software and AI-related roles. Existing Remotive listings remain available. No migration or new environment secret is required.

## Behavior

- Configured boards sync every 720 minutes through the existing worker.
- `role_scope: cse` filters roles by engineering titles and supporting technical description evidence, excluding sales/recruiting titles. `all` disables this filter.
- Public Ashby rows must have `isListed: true`. HTML is sanitized through the existing normalization layer.
- Job URLs, attribution, posting times and declared location restrictions are retained. A remote flag does not imply worldwide eligibility.
- Ashby compensation uses one explicit summary salary component, retaining currency and interval. Missing or ambiguous salary remains unknown.
- Dedupe, complete-snapshot closure, embedding batches, durable matching and alerts use the existing pipeline. Duplicate candidates and origins are preloaded, job writes are batched, and changed-job matches are invalidated with one statement to avoid per-job network round trips.
- Existing database source settings are not overwritten when the worker loads YAML.

## Changed files and complete code

See [source snapshot](stages/07_SOURCE.md) for the full changed-file list and code.

## Run

Restart the API and worker after installing this update. From the backend folder:

```powershell
../.venv/Scripts/python.exe -m app.worker
```

Only one scheduler worker should run. Ingestion administration exposes the source status and run counts. The first imports use saved public API responses so validation and importing do not re-fetch the external source.

## Checks

`python -m ruff check backend scripts` and all 47 backend tests pass, including Ashby privacy, source salary handling, relevance filtering and closure regression tests. No frontend dependency or schema change is required.

## Source documentation

- [Greenhouse](https://docs.greenhouse.io/job-board.html)
- [Lever](https://github.com/lever/postings-api)
- [Ashby](https://developers.ashbyhq.com/docs/public-job-posting-api)

Public API access is distinct from unrestricted redistribution rights; employer and provider terms apply.

````
