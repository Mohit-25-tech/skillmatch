# Stage 4: frontend wiring and new pages

Implemented job detail and similar jobs, persistent save/apply tracking, SortableJS application board with accessible status controls, notes and event timelines, saved searches, SSE bell/read state, ATS and tailoring, optional Ollama controls, database learning resources, Chart.js market insights, command search, profile preferences, theme persistence, recruiter discovery and administrator ingestion controls. Existing visual styling is retained with responsive light-theme styles and reduced-motion support.

Public browsing does not require authentication. Empty/error/loading states replace fake content; `frontend/src/lib/demo.ts` was deleted. Header identity, counts, dates, salary and scores come from API data. Source attribution links remain visible. The API client uses typed jQuery AJAX; authenticated SSE uses fetch streaming so bearer tokens stay out of URLs.

## Changed/new files and full code

[Complete source and file list](04_SOURCE.md). The deleted demo module is intentionally absent from the snapshot. Backend integration changes include minimum-match filters, persisted saved state, capability discovery and avoiding rematches for theme-only updates.

## Run commands

```powershell
cd frontend
npm ci
npm run build
npm run dev
```

Run the API and worker as documented in the root README. This stage adds no migration; stage 6 supplies query indexes. Similar-job vector retrieval requires PostgreSQL and available embeddings; SQLite uses the documented fallback.
