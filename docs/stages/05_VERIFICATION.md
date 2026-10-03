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
