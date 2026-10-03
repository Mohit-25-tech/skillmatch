# Stage 2: ingestion, worker and Docker

The adapter layer supports Greenhouse, Lever, Remotive, Arbeitnow, Remote OK, Adzuna country feeds and an optional explicit Hacker News hiring thread. Feeds validate before modifying availability. Only complete inventories close missing jobs; truncated feeds and HN threads never do. Cross-source origins preserve attribution and prevent premature closure. Unknown or predicted pay stays null.

Sources start disabled in sources.yaml. Configure company slugs and credentials, then enable using the administrator API under /api/v1/admin/ingestion. Keep public feeds disabled until stage 4 renders their required source attribution and outbound links. Remotive listings must remain publicly accessible without registration. Remote OK requires a followed attribution link. API listings are public.

The database stores jobs, origins, feed cache, ingestion runs and a durable work queue. One separate worker schedules sources, retries tasks and exposes a database heartbeat. Job vectors use pgvector(384) on PostgreSQL and JSON for SQLite tests. Model unavailability preserves ingestion and uses structured matching.

Run from backend:

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.seed
..\.venv\Scripts\python.exe -m app.worker
```

Copy .env.example to .env and replace placeholders, then from root: `docker compose up --build`. The optional local database is `--profile dev`; set DATABASE_URL to its service hostname and matching DEV_DB_PASSWORD. Optional SMTP capture: `docker compose --profile mail up --build`, SMTP_HOST=mailpit, SMTP_STARTTLS=false. Demo jobs require `python -m app.seed --demo` and DEMO_MODE=true to appear. Never enable this in production.

Migration ea77977797e7 enables vector and creates a cosine HNSW index. Existing catalog fixtures are marked demo. No existing migration was edited. The database role must have extension creation permission; otherwise enable vector in the Neon SQL editor first. Downgrade refuses rows the old schema cannot represent instead of deleting live data.

Official source references: [Greenhouse](https://developers.greenhouse.io/job-board-api.html), [Lever](https://github.com/lever/postings-api), [Remotive terms](https://remotive.com/remote-jobs/api), [Arbeitnow terms](https://www.arbeitnow.com/terms), [Remote OK API terms](https://remoteok.com/api), [Adzuna](https://developer.adzuna.com/overview), [HN](https://github.com/HackerNews/API).

Full files and changed-file list are in 02_SOURCE.md. Tests use mocked HTTP and local SQLite; no live feed or production database was modified. Docker execution requires a running Docker engine.
