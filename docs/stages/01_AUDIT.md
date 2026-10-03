# Stage 1 — audit and matching root cause

The existing visual design is preserved. This audit distinguishes working code from presentation fixtures.

| Area | Evidence in existing code | Finding / follow-up |
| --- | --- | --- |
| One scored job | `routers/candidates.py` upload only parsed; `POST /matches` accepted a single job ID | **Root cause:** no catalog-wide scoring trigger. Add upload-triggered latest-resume matching and a historical backfill command. |
| ML recognition | `services/parsing.py` only six aliases; extraction depended on already-seeded skill rows | Add an independently provisioned shared taxonomy, case-insensitive canonicalization, ML/NLP/LLM/RAG aliases, and cached spaCy matchers. |
| Matches/Insights | Queries included all resumes but only explicitly analyzed jobs | Aggregate latest-resume matches across the active catalog; do not double-count historical resumes. |
| Demo jobs | `app/seed_data.py` generates 200 synthetic jobs; `seed.py` auto-enables via example env | Mark legacy catalog rows as demo, hide by default, and require `--demo` to create synthetic jobs. |
| Browser fixtures | `frontend/src/lib/demo.ts`, default `demo=true`, fabricated scores/applications/identity | Stage 4 must replace the default sample workspace with API-driven state. No UI rewrite. |
| Trends and gauge | `main.ts` unconditional `trending-up` icons; fixed gauge value 86 | Decorative arrows do not represent a measured trend; remove/wire in stage 4. |
| Time labels | `jobAge()` rounds `created_at` to days; all same-day records say “New opportunity” | It is computed, not a constant, but uses ingestion time rather than publisher time and lacks hour/minute precision. New backend supplies nullable `posted_at`. |
| Logos | `companyLogo()` recognizes a few demo brands and uses the same fallback icon | Backend supplies deterministic initials/gradient avatar metadata; stage 4 renders it. |
| Header search | Link to jobs plus `/` keyboard shortcut | Navigates, but does not perform global search. Backend command-search endpoint added in stage 3; UI wiring in stage 4. |
| Bell | Click only shows a canned toast | Persisted notifications, unread counts, and SSE added in stage 3. |
| Live badge | Label depends only on demo/auth state | It is not a worker/API health signal. Backend ingestion health is added in stage 2. |
| “Empty checkbox” | Header contains `<kbd>/</kbd>`, not a checkbox input | Likely the small shortcut key. No theme toggle exists. Stage 3 persists theme preferences; stage 4 replaces the shortcut presentation. |
| Learning links | `match_public()` fabricates a freeCodeCamp search URL per missing skill | Replace with curated database resources and role counts in stage 3. |
| Salaries | Generated seed values and non-null integer columns | Make live salary values nullable; preserve units/currency, discard estimated salaries, never synthesize unknown pay. |
| Credentials | `.env.example` contained a real connection string | Replaced with placeholders. No connection using that credential was attempted. Owner must rotate it; do not reproduce it in source exports. |

## Stage 1 commands

From `backend/` with the virtual environment active:

```sh
python -m app.services.match_pipeline
pytest -q tests/test_stage1_matching.py
```

No stage 1 schema migration is necessary. Historical data is reprocessed only by the explicit backfill command. Later stages add durable worker tasks and database-backed vectors without editing the original migration.
