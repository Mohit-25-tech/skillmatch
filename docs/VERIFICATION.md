# Verification record

Verified on Windows on 28 September 2026. Docker targets Python 3.12; the available local interpreter used for API tests was Python 3.10.8. Browser checks used installed Google Chrome.

| Check | Result |
| --- | --- |
| Ruff (`backend`, `scripts`) | Passed |
| Backend pytest suite | 14 passed |
| TypeScript strict checking and Vite production build | Passed |
| Vitest utility tests | 4 passed |
| Playwright browser suite | 4 passed |
| Axe WCAG A/AA scans | No reported violations on dashboard, landing, login, and upload pages |
| Desktop/mobile screenshots | Captured and visually inspected |
| Real browser account workflow | Registration, DOCX upload, extraction, keyword match, application, logout, recruiter login, and status update passed |
| Bookmarks | Save, reload, and saved-only filtering passed; storage is separated by account/sample mode |
| Alembic | Upgrade, downgrade to base, and upgrade again passed against an isolated SQLite database |
| PostgreSQL SQL export | Generated from the frozen Alembic migration using the PostgreSQL dialect |
| Docker Compose configuration | Validated with `docker compose --env-file .env.example config --no-env-resolution --quiet` |
| OpenAPI documentation | `/docs`, local Swagger assets, and `/openapi.json` returned HTTP 200 |
| Seed integrity | Exactly 200 generated jobs and 300 unique skills; all job skills resolve |
| Pandas and Matplotlib notebooks | Both executed and saved with outputs |
| Standalone SQLite CRUD exercise | Completed all four operations and asserted deletion |
| npm dependency audit | Zero reported vulnerabilities after the dependency updates |

The application entry JavaScript bundle is approximately 115 KB minified (40 KB gzip), down from the initial unpruned icon bundle. Three.js and chart code load separately. These sizes are build measurements, not a substitute for a Lighthouse run.

## Remaining environment-dependent verification

- Docker Desktop’s Linux engine was unavailable, so container image builds and a complete Compose launch were not executed locally. The repository includes CI jobs for both image builds.
- No Neon credentials were supplied. Live PostgreSQL connectivity, migrations against Neon, and PostgreSQL concurrency/load behavior remain staging checks. TLS enforcement and the pool configuration are covered by unit tests.
- The sentence-transformer model was not downloaded in this environment. The weighted semantic calculation and error fallback are unit tested with controlled vectors; the browser workflow used explicit keyword-only mode. Real model inference requires installing all backend requirements and allowing the first model download, or pre-populating its cache.
- Lighthouse performance scoring was not run; the requested score above 85 remains a measured deployment target.
- Automated accessibility scans cover the listed pages and do not replace a complete screen-reader/keyboard audit.

One installed Starlette version emitted a TestClient/httpx deprecation warning. The tests completed successfully; this was not suppressed.
