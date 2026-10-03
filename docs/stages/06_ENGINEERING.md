# Stage 6: engineering hardening and verification

Added migration `c6f4a1b209d3`, following `ad18dbabd51a`, without editing historical migrations. Five composite indexes cover visible-job cursor scans, latest user resumes, ranked match scores, application updates and due work items. nginx now disables buffering, caching and compression for the authenticated notification stream. Publisher timestamps normalize to UTC before persistence. Insight snapshots retain all observed skills rather than truncating historical evidence to the top list.

The environment example has placeholders only and explicit development CORS origins. Application services have health checks and run without root privileges. Existing authentication/role checks, upload limits, sanitization, rate limits, bounded ingestion, cached insights and batched embeddings remain in place. Source configurations remain disabled until configured by the owner. No Redis service is required for the durable SQL queue.

## Changed/new files and full code

[Complete source and file list](06_SOURCE.md).

## Migration and run commands

```powershell
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head
cd ..
docker compose --env-file .env.example config --no-env-resolution --quiet
# After copying/configuring .env and starting the Docker engine:
docker compose up --build
```

## Local evidence and limits

- Ruff passes; 36 backend tests and 11 frontend unit tests pass.
- Production TypeScript/Vite build passes; all five browser tests pass, including actual drag and drop, live notification delivery and persisted theme.
- Compose configuration validates. Docker engine is stopped, so container builds/startup were not verified locally.
- Local SQLite database upgraded to `c6f4a1b209d3`; all five indexes exist and foreign-key checks pass. Existing 200 demo jobs remain marked and hidden by default.
- Pre-migration backup: `artifacts/skillmatch-before-stage6-20260929-181825.db` (ignored runtime artifact).
- No remote Neon database, live provider credentials, real SMTP delivery or Ollama model was exercised. SQLite and mocked HTTP tests cannot substitute for those deployment checks.
