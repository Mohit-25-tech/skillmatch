# Stage 01 — complete changed/new source

```text
.env.example
backend/app/routers/candidates.py
backend/app/services/match_pipeline.py
backend/app/services/parsing.py
backend/app/services/taxonomy.py
backend/tests/test_stage1_matching.py
docs/stages/01_AUDIT.md
scripts/stage_snapshot.py
```

## .env.example

````
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@YOUR-NEON-POOLER-HOST/DATABASE?sslmode=require
JWT_SECRET=replace-with-a-random-secret-at-least-32-characters
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:8080,http://localhost:5173,http://127.0.0.1:8080,http://127.0.0.1:5173
COOKIE_SECURE=false
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
SEMANTIC_ENABLED=true
SEED_ON_START=true

````

## backend/app/routers/candidates.py

````
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.limits import limiter
from app.models import Application, Job, MatchResult, Resume, User
from app.repositories.catalog import job_public, resume_public
from app.schemas import MatchInput, StatusInput
from app.security import roles
from app.services.match_pipeline import run_resume_matching
from app.services.matching import embed, match_public, save_match
from app.services.parsing import MAX_FILE_SIZE, extract_skills, parse_resume
from app.services.taxonomy import ensure_taxonomy

router = APIRouter(tags=["Candidates"])


@router.post("/resumes", status_code=201)
@limiter.limit("8/minute")
def upload(
    request: Request,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    user: User = Depends(roles("candidate")),
    db: Session = Depends(get_db),
) -> dict:
    filename = Path((file.filename or "resume").replace("\\", "/")).name[:255]
    data = file.file.read(MAX_FILE_SIZE + 1)
    file.file.close()
    text = parse_resume(data, filename)
    skills = ensure_taxonomy(db)
    names = extract_skills(text, [s.name for s in skills])
    resume = Resume(
        user_id=user.id, filename=filename, text=text, skills=[s for s in skills if s.name in names]
    )
    db.add(resume)
    db.commit()
    background_tasks.add_task(run_resume_matching, resume.id, db.get_bind())
    return resume_public(resume)


@router.get("/resumes")
def resumes(user: User = Depends(roles("candidate")), db: Session = Depends(get_db)) -> list[dict]:
    return [
        resume_public(r)
        for r in db.scalars(select(Resume).where(Resume.user_id == user.id).order_by(Resume.id.desc())).all()
    ]


def own_resume(db: Session, resume_id: int, user: User) -> Resume:
    resume = db.get(Resume, resume_id)
    if not resume or resume.user_id != user.id:
        raise HTTPException(404, "Resume not found")
    return resume


@router.delete("/resumes/{resume_id}", status_code=204)
def delete_resume(
    resume_id: int, user: User = Depends(roles("candidate")), db: Session = Depends(get_db)
) -> None:
    db.delete(own_resume(db, resume_id, user))
    db.commit()
    embed.cache_clear()


@router.post("/matches")
@limiter.limit("15/minute")
def match(
    request: Request,
    body: MatchInput,
    user: User = Depends(roles("candidate")),
    db: Session = Depends(get_db),
) -> dict:
    resume = own_resume(db, body.resume_id, user)
    job = db.get(Job, body.job_id)
    if not job or not job.active:
        raise HTTPException(404, "Job not found")
    return {**match_public(save_match(db, resume, job)), "job": job_public(job)}


@router.get("/matches")
def matches(user: User = Depends(roles("candidate")), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(
        select(MatchResult).join(Resume).where(Resume.user_id == user.id).order_by(MatchResult.score.desc())
    ).all()
    return [{**match_public(r), "job": job_public(db.get(Job, r.job_id))} for r in rows]


@router.post("/applications", status_code=201)
def apply(body: MatchInput, user: User = Depends(roles("candidate")), db: Session = Depends(get_db)) -> dict:
    resume = own_resume(db, body.resume_id, user)
    job = db.get(Job, body.job_id)
    if not job or not job.active:
        raise HTTPException(404, "Job not found")
    save_match(db, resume, job)
    application = Application(user_id=user.id, job_id=job.id, resume_id=resume.id)
    db.add(application)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "You have already applied for this role") from None
    return {"id": application.id, "status": application.status}


@router.get("/applications")
def applications(
    user: User = Depends(roles("candidate", "recruiter", "admin")), db: Session = Depends(get_db)
) -> list[dict]:
    stmt = select(Application)
    if user.role == "candidate":
        stmt = stmt.where(Application.user_id == user.id)
    elif user.role == "recruiter":
        stmt = stmt.join(Job).where(Job.recruiter_id == user.id)
    rows = db.scalars(stmt.order_by(Application.created_at.desc()).limit(500)).all()
    output = []
    for row in rows:
        result = db.scalar(
            select(MatchResult).where(
                MatchResult.resume_id == row.resume_id, MatchResult.job_id == row.job_id
            )
        )
        output.append(
            {
                "id": row.id,
                "job": job_public(row.job),
                "candidate": row.user.name,
                "status": row.status,
                "score": result.score if result else None,
                "created_at": row.created_at.isoformat(),
            }
        )
    return sorted(output, key=lambda x: x["score"] or 0, reverse=True) if user.role != "candidate" else output


@router.patch("/applications/{application_id}")
def status(
    application_id: int,
    body: StatusInput,
    user: User = Depends(roles("recruiter", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(404, "Application not found")
    if application.job.recruiter_id != user.id and user.role != "admin":
        raise HTTPException(403, "Not your job posting")
    application.status = body.status
    db.commit()
    return {"status": application.status}

````

## backend/app/services/match_pipeline.py

````
"""Compute coverage across the catalog, including historical resumes."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import engine
from app.models import Job, MatchResult, Resume
from app.services.matching import save_match
from app.services.parsing import extract_skills
from app.services.taxonomy import ensure_taxonomy


def match_resume(db: Session, resume: Resume, only_missing: bool = False) -> int:
    taxonomy = ensure_taxonomy(db)
    names = extract_skills(resume.text, [s.name for s in taxonomy])
    resume.skills = [s for s in taxonomy if s.name in names]
    existing = set(db.scalars(select(MatchResult.job_id).where(MatchResult.resume_id == resume.id))) if only_missing else set()
    count = 0
    for job in db.scalars(select(Job).where(Job.active.is_(True))).all():
        if job.id not in existing:
            save_match(db, resume, job)
            count += 1
    db.commit()
    return count


def run_resume_matching(resume_id: int, bind=engine) -> None:
    with Session(bind, expire_on_commit=False) as db:
        resume = db.get(Resume, resume_id)
        if resume:
            match_resume(db, resume)


def reindex_all(db: Session) -> int:
    latest = select(func.max(Resume.id)).group_by(Resume.user_id)
    return sum(match_resume(db, resume) for resume in db.scalars(select(Resume).where(Resume.id.in_(latest))).all())


if __name__ == "__main__":
    with Session(engine) as session:
        print(f"Computed {reindex_all(session)} latest-resume/job matches")

````

## backend/app/services/parsing.py

````
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pdfplumber
import spacy
from docx import Document
from fastapi import HTTPException
from spacy.matcher import PhraseMatcher

from app.services.taxonomy import ALIASES

MAX_FILE_SIZE = 5 * 1024 * 1024


def parse_resume(data: bytes, filename: str) -> str:
    if not data or len(data) > MAX_FILE_SIZE:
        raise HTTPException(413, "Upload a non-empty file smaller than 5 MB")
    extension = Path(filename).suffix.lower()
    try:
        if extension == ".pdf" and data.startswith(b"%PDF-"):
            with pdfplumber.open(BytesIO(data)) as pdf:
                if len(pdf.pages) > 20:
                    raise HTTPException(422, "Please use a resume with 20 pages or fewer")
                text = "\n".join((page.extract_text() or "") for page in pdf.pages)
        elif extension == ".docx" and data.startswith(b"PK"):
            with ZipFile(BytesIO(data)) as archive:
                if sum(f.file_size for f in archive.infolist()) > 25 * 1024 * 1024:
                    raise HTTPException(413, "The expanded document is too large")
                if "word/document.xml" not in archive.namelist():
                    raise ValueError("Invalid DOCX")
            doc = Document(BytesIO(data))
            text = "\n".join(
                [p.text for p in doc.paragraphs]
                + [c.text for t in doc.tables for r in t.rows for c in r.cells]
            )
        else:
            raise HTTPException(415, "Only genuine PDF and DOCX files are supported")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, "Unable to read this file. Use an unencrypted PDF or DOCX.") from exc
    if len(text.strip()) < 30:
        raise HTTPException(422, "No readable resume text found. Scanned PDFs need OCR before upload.")
    return text[:100000]


@lru_cache(maxsize=8)
def skill_matcher(names: tuple[str, ...]):
    nlp = spacy.blank("en")
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for name in names:
        matcher.add(name, [nlp.make_doc(name)])
    canonical_names = {name.casefold(): name for name in names}
    for alias, canonical in ALIASES.items():
        if canonical.casefold() in canonical_names:
            matcher.add(canonical_names[canonical.casefold()], [nlp.make_doc(alias)])
    return nlp, matcher


def extract_skills(text: str, names: list[str]) -> list[str]:
    nlp, matcher = skill_matcher(tuple(sorted(set(names))))
    return sorted({nlp.vocab.strings[match_id] for match_id, _, _ in matcher(nlp.make_doc(text))})

````

## backend/app/services/taxonomy.py

````
"""Shared, canonical taxonomy for resume and job extraction."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Skill
from app.seed_data import SKILLS

EXTRA_SKILLS = ["Large Language Models", "Generative AI", "Fine Tuning", "PEFT", "LoRA", "Sentence Transformers", "Vector Search", "Computer Science", "NumPy", "OpenCV", "FastAPI", "Retrieval Augmented Generation"]
ALIASES = {
    "js": "JavaScript", "javascript es6": "JavaScript", "ts": "TypeScript",
    "postgres": "PostgreSQL", "postgresql": "PostgreSQL", "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn", "scikit-learn": "Scikit-learn", "react.js": "React",
    "reactjs": "React", "nodejs": "Node.js", "node js": "Node.js", "pytorch": "PyTorch",
    "torch": "PyTorch", "tensorflow": "TensorFlow", "tf": "TensorFlow",
    "llm": "Large Language Models", "llms": "Large Language Models",
    "large language model": "Large Language Models", "genai": "Generative AI",
    "generative artificial intelligence": "Generative AI", "ml": "Machine Learning",
    "machine-learning": "Machine Learning", "nlp": "Natural Language Processing",
    "natural-language processing": "Natural Language Processing", "ml ops": "MLOps",
    "retrieval augmented generation": "RAG", "retrieval-augmented generation": "RAG",
    "huggingface": "Hugging Face", "hugging face transformers": "Transformers",
    "fine-tuning": "Fine Tuning", "fine tuning": "Fine Tuning", "k8s": "Kubernetes",
    "amazon web services": "AWS", "gcp": "Google Cloud", "ci cd": "CI/CD",
}


def ensure_taxonomy(db: Session) -> list[Skill]:
    existing = {s.name.casefold(): s for s in db.scalars(select(Skill)).all()}
    for item in [*SKILLS, *({"name": n, "category": "AI & ML"} for n in EXTRA_SKILLS)]:
        if item["name"].casefold() not in existing:
            skill = Skill(**item)
            db.add(skill)
            existing[item["name"].casefold()] = skill
    db.flush()
    return list(existing.values())

````

## backend/tests/test_stage1_matching.py

````
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Job, MatchResult, Resume, User
from app.services.match_pipeline import match_resume
from app.services.parsing import extract_skills
from app.services.taxonomy import ensure_taxonomy


def test_ml_aliases_and_every_active_job_gets_a_score():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        user = User(name="ML Candidate", email="ml@example.com", password_hash="unused", role="candidate")
        db.add(user)
        db.flush()
        taxonomy = {s.name: s for s in ensure_taxonomy(db)}
        resume = Resume(user_id=user.id, filename="ml.pdf", text="ML engineer with Python, torch, sklearn, NLP, LLMs, retrieval-augmented generation and MLOps.")
        db.add(resume)
        for i in range(200):
            names = ["Python", "PyTorch", "Machine Learning"] if i % 2 else ["Python", "Scikit-learn", "Natural Language Processing"]
            db.add(Job(recruiter_id=user.id, title="ML Engineer" if i % 2 else "Data Scientist", company=f"Team {i}", location="Remote", description="Build machine learning systems", skills=[taxonomy[n] for n in names]))
        db.commit()
        assert match_resume(db, resume) == 200
        results = list(db.scalars(select(MatchResult)))
        assert len(results) == 200
        assert all(result.score == 100 for result in results)
        assert {"Large Language Models", "RAG", "MLOps"} <= {s.name for s in resume.skills}
        assert match_resume(db, resume, only_missing=True) == 0


def test_aliases_respect_canonical_case_and_boundaries():
    assert extract_skills("sklearn and JS, not a Pythonista", ["scikit-learn", "JavaScript", "Python"]) == ["JavaScript", "scikit-learn"]

````

## docs/stages/01_AUDIT.md

````
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

````

## scripts/stage_snapshot.py

````
"""Write complete, reviewable source snapshots at each stage boundary."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("stage")
parser.add_argument("files", nargs="+")
args = parser.parse_args()
paths = sorted(set(args.files))
output = [f"# Stage {args.stage} — complete changed/new source\n\n", "```text\n", *[p + "\n" for p in paths], "```\n"]
for name in paths:
    file = ROOT / name
    output.extend([f"\n## {name}\n\n````\n", file.read_text(encoding="utf-8-sig"), "\n````\n"])
target = ROOT / "docs" / "stages" / f"{args.stage}_SOURCE.md"
target.write_text("".join(output), encoding="utf-8")
print(f"Wrote {target.relative_to(ROOT)} ({len(paths)} files)")

````
