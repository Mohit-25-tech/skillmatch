# Stage 3: backend product features

Stages follow the **Output format** in the attached brief. Stage 3 implements the backend for the new product features. The existing visual design and frontend application code are preserved; stage 4 will connect and render these APIs. The browser still contains demo fixtures until that stage.

## Delivered APIs

All paths below use `/api/v1`. Private routes require the existing Bearer JWT.

| Capability | Endpoints / behavior |
| --- | --- |
| Job discovery | Public `GET /jobs`, `GET /jobs/{id}`; optional candidate authentication adds a score and breakdown for the latest resume. `cursor` + `size` provide stable descending-ID pagination. Unknown salary and publisher time remain null. Source links and deterministic avatar metadata are returned. |
| Matching | Upload queues catalog-wide matching. Ingestion and native job edits queue changed jobs. `GET /matches` and `/analytics` use the latest resume and all active matches. `GET /matches/status` exposes completion. A missing score on a requested page is computed immediately from available evidence. No resume returns `requires_resume`, never a fabricated score. |
| Explainable scoring | Configurable semantic, importance-weighted skill, experience and location components. Missing components have null scores and zero effective weight; available weights are renormalized. PostgreSQL computes cosine distance using pgvector; SQLite tests use equivalent Python cosine. Required skills weigh 1; explicit nice-to-have skills weigh 0.4. Explicit years-of-experience evidence is used conservatively. |
| Profile | `GET/PUT /profile`: name, preferred roles, locations, remote preference, comparable salary expectation, alert settings, discovery consent, and dark/light/system theme. Location contributes to the configured fit component. Role and comparable salary preferences produce explanation reasons. Updates invalidate stale matches and queue recomputation. |
| Save and tracker | `POST /jobs/{id}/save`, `GET /tracker`, `PATCH /tracker/{id}`, `DELETE /tracker/{id}` for saved bookmarks. Saved, Applied, Reviewing, Interview, Offer, Rejected and Hired states, notes, dates and event timeline. Existing `/applications` converts a bookmark to an application. Saved rows do not count as applications or appear in recruiter pipelines. Deleting a resume retains tracker history. |
| Alerts | `GET/POST /saved-searches`, `PUT/DELETE /saved-searches/{id}`. Filters support keywords, location, kind and minimum match. New eligible jobs generate one notification per saved search/job. |
| Notifications | `GET /notifications?after=ID`, `POST /notifications/{id}/read`, `GET /notifications/stream`. SSE returns unread counts, IDs and `notifications` events; supports `Last-Event-ID` or `after`, checks account revocation and token expiry, and reconnects every minute. Use authenticated fetch streaming; never put JWTs in URLs. |
| Email | Daily 08:00 UTC digest work item. SMTP disabled until configured and the user opts in. Sent markers update only after delivery. Mailpit profile captures local mail. SMTP delivery is at-least-once: a crash after SMTP acceptance but before database commit can duplicate a digest. |
| Resume tools | `GET /resumes/{id}/ats?job_id=ID`, `GET /jobs/{id}/tailoring`: detected sections, keyword coverage, length/readability checks and truthful improvement suggestions. The score is a text heuristic, not an employer ATS prediction; original page layout is not inferred. |
| Optional writing | `POST /jobs/{id}/draft`, rate-limited and disabled unless `OLLAMA_ENABLED=true`. Uses the configured local Ollama endpoint; returns a draft requiring review. No external paid model is required. |
| Learning | `GET /learning-path` aggregates missing skills across every latest-resume match, includes related-job counts, and reads curated free resources from `learning_resources`. Skills without a curated resource return an empty resource list. |
| Market | Public `GET /insights/market`: DB-backed companies, skills, locations, types, salary groups and daily history; shared database cache. Salary groups retain currency and pay interval, exclude unknown units/estimated pay/demo jobs, and report published-range midpoints. History starts when actual snapshots exist; no synthetic trend points. |
| Search | Public `GET /search?q=...`: jobs, companies, skills and navigational pages. PostgreSQL full-text plus trigram search and indexes; escaped LIKE fallback in SQLite. |
| Recruiters | Native jobs use shared extraction and queued embeddings. `GET /jobs/{id}/candidates` returns names, opaque user IDs and scores for opted-in candidates or applicants. Job owners manage the existing application pipeline; resume text is not returned by ranking APIs. |
| Administration | Ingestion CRUD/configuration, source enable/disable, queued run-now, run history and heartbeat under `/admin/ingestion`. Existing trusted CLI creates administrators. |

## Schema and startup

New migrations, in order:

1. `ea77977797e7`: live job metadata, nullable salaries, pgvector(384), ingestion/cache/origin/work/heartbeat tables and HNSW index; marks legacy fixtures as demo.
2. `ad18dbabd51a`: profile preferences, resume vectors, explanations, tracker history, saved searches, notifications, learning resources, insight cache/snapshots and PostgreSQL search indexes.

The original migration remains unchanged. Populated SQLite upgrade tests verify existing application, resume-skill, job-skill and match rows survive. Downgrade refuses records that the old schema cannot represent. Back up a deployed database before migrations.

For Neon, create a project/database in the Neon console, copy its PostgreSQL connection string into `.env` (use the psycopg driver and `sslmode=require`), and use a migration role permitted to enable extensions. The migrations execute:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

See [Neon's pgvector explanation](https://neon.com/blog/understanding-vector-search-and-hnsw-index-with-pgvector). The checked-in `.env.example` contains placeholders, not credentials. Rotate the Neon password previously present in that template; replacing the template does not revoke it.

Local development, from `backend`, with `.env` configured or `DATABASE_URL=sqlite:///./skillmatch.db`:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.seed
..\.venv\Scripts\python.exe -m app.services.match_pipeline
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, from `backend`:

```powershell
..\.venv\Scripts\python.exe -m app.worker
```

`app.seed` provisions taxonomy and resources only. `app.seed --demo` explicitly creates synthetic jobs; `DEMO_MODE=true` exposes them in development. Production rejects demo mode. Create an administrator with `python -m app.create_admin` in a trusted terminal, then configure sources via the API. Source YAML bootstraps missing entries; subsequent changes use the administrator configuration endpoint.

Docker, from the root after copying and configuring `.env`:

```powershell
docker compose up --build
# Optional local PostgreSQL: use --profile dev and DATABASE_URL pointing to dev-db:5432.
# Optional captured mail: use --profile mail, SMTP_HOST=mailpit, SMTP_PORT=1025, SMTP_STARTTLS=false.
```

The API, worker, web and Mailpit run unprivileged. Nginx listens internally on 8080; the browser URL remains http://localhost:8080. Run one worker process; SQLite is a development fallback. Ollama may run separately; set OLLAMA_URL to an address reachable from the worker/API network.

## Verification and boundaries

Run from root:

```powershell
.\.venv\Scripts\python.exe -m ruff check backend/app backend/tests backend/migrations scripts/stage_snapshot.py
.\.venv\Scripts\python.exe -m pytest backend/tests -q
docker compose --env-file .env.example config --no-env-resolution --quiet
```

Regression coverage includes 200-job matching, all seven adapter classes with mocked HTTP, caching/retries, deduplication, partial/failed-feed safety, cross-source closure, candidate/recruiter privacy, cursor scores, latest-resume aggregation, tracker history, settings, ATS, saved-search notifications, SMTP opt-in/failure, durable worker processing, and populated migration preservation. PostgreSQL migrations were compiled offline; no live Neon migration or model download was performed. Docker configuration was validated, but image builds require the stopped Docker engine to be started. SSE rendering, charts, drag-and-drop, header controls and new pages are stage 4 work.

Full changed-file listings and source are in `01_SOURCE.md`, `02_SOURCE.md`, and `03_SOURCE.md`. Stage 1 and 2 snapshots record their stage boundaries; stage 3 contains the final backend and infrastructure integration, including follow-up fixes. These snapshots supersede the older `docs/SOURCE_CODE.md` export for this work.

## Local execution record

Validation: **34 backend tests passed**; Ruff passed; Compose configuration passed; PostgreSQL migration SQL compiled offline. The existing local `backend/skillmatch.db` was backed up to `artifacts/skillmatch-before-stages-20260929-100313.db`, migrated to `ad18dbabd51a`, and provisioned with taxonomy/resources. Its 200 synthetic jobs were retained and marked demo; existing users, resumes and the application were preserved. The non-demo match backfill processed zero jobs because this local database currently contains only demo jobs. No live source was enabled and no Neon database was accessed.
