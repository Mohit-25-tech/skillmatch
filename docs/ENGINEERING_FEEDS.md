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
