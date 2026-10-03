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

Python 3.10+ and Node 20+ are used. The local environment requires **4 concurrently running services**:

### 1. Terminal 1 — Backend API (FastAPI)
```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Terminal 2 — Background Worker (Durable Tasks & Ingestion)
```powershell
cd backend
..\.venv\Scripts\python.exe -m app.worker
```

### 3. Terminal 3 — Frontend SPA (Vite + TypeScript)
```powershell
cd frontend
npm run dev
```

### 4. Terminal 4 — Local Ollama Service (Embeddings & Fallback Chat)
Ollama must be running and serving models locally:
```powershell
# Start Ollama server if not already running as a Windows service
ollama serve

# Ensure required local models are pulled
ollama pull all-minilm:l6
ollama pull llama3:latest
```

### Maintenance & Re-embedding CLI
To re-embed all jobs, resumes, and recalculate match scores with the active vector backend:
```powershell
cd backend
..\.venv\Scripts\python.exe -m app.cli re-embed
```
Or use the **Re-embed everything** button in the **Administration** dashboard panel.

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
