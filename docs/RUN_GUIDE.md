# Run SkillMatch AI step by step

## Fastest interface preview

1. Open a terminal in `frontend`.
2. Run `npm ci`.
3. Run `npm run dev`.
4. Open `http://localhost:5173`.
5. Explore the sample dashboard, search jobs, save a role, open its detail, and click **Analyze my match**. The preview explicitly labels the sample data. Creating an account requires the backend.

## Full application with Neon

1. Start Docker Desktop and confirm its Linux engine is running.
2. Create a Neon project and copy its pooled connection string from **Connect**.
3. Copy `.env.example` to `.env`.
4. Replace `DATABASE_URL` with your Neon URL and replace `JWT_SECRET` with a random signing key.
5. Run `docker compose up --build` from the repository root.
6. Wait until the API health check passes and the web service starts.
7. Open `http://localhost:8080/#/register`.
8. Register as a candidate. Upload a text-based PDF or DOCX resume under 5 MB.
9. Open **Find jobs**, choose a role, and click **Analyze my match**. The first semantic analysis can take longer while model weights download. Keyword-only mode is explicitly identified when the model is unavailable.
10. Review matched/missing skills and suggested resources. Click **Take the next step** to apply. Check **Applications** and **Insights**.
11. Sign out and register a recruiter account. Open **Post a job**, publish a role, and manage it from the recruiter overview.
12. Apply to that role with your candidate account. The recruiter can then see the candidate ranking and update application status.
13. Create an administrator with `docker compose exec api python -m app.create_admin`, then sign in to the admin panel.

## Local PostgreSQL instead of Neon

Keep the development connection string from `.env.example` and run `docker compose --profile dev up --build`. This launches the optional local PostgreSQL service. Do not use that connection string for an internet deployment.

## Coursework

1. Run `python scripts/sqlite_crud.py` to see all four CRUD operations.
2. Install `notebooks/requirements.txt` into your virtual environment.
3. Open the two notebooks in JupyterLab, or run `python scripts/execute_notebooks.py`.
4. Use `sql/01_schema.sql` only against a new teaching database. For the application, let Alembic manage the schema.
5. Run `sql/02_examples.sql` after seeding to explore SQL queries. The example transaction ends with a rollback.

## Troubleshooting

| Symptom | Resolution |
| --- | --- |
| Docker daemon connection error | Start Docker Desktop and select Linux containers |
| API remains unhealthy | Inspect `docker compose logs api`; check the database URL and Neon availability |
| Local database host `dev-db` does not resolve | Use the `dev` profile, or replace the URL with Neon |
| Login succeeds but refresh fails | Confirm browser origin is in `CORS_ORIGINS`; secure cookies require HTTPS |
| Resume rejected | Use a genuine, unencrypted PDF/DOCX with selectable text; scanned PDFs need OCR |
| Keyword-only score | Model unavailable or `SEMANTIC_ENABLED=false`; inspect API logs and model-cache connectivity |
| No recruiter applicants | Only candidates who applied to that recruiter’s own roles are shown |
| No candidate score yet | Choose a job and run an analysis; scores are not fabricated for unexamined jobs |
| Notebook cannot find data | Run from the repository root or `notebooks/`; both locations are supported |

Stop services with `docker compose down`. Named database/model volumes remain intact. Do not remove volumes unless you intend to delete that local data.
