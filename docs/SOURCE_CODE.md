# SkillMatch AI — complete source
Generated from the delivered workspace. Files are grouped by folder. Binary screenshots are listed in the tree and delivered separately.
## Full folder tree
```text
.env.example
.github/workflows/ci.yml
.gitignore
backend/.dockerignore
backend/alembic.ini
backend/app/__init__.py
backend/app/config.py
backend/app/create_admin.py
backend/app/db.py
backend/app/limits.py
backend/app/main.py
backend/app/models.py
backend/app/repositories/__init__.py
backend/app/repositories/catalog.py
backend/app/routers/__init__.py
backend/app/routers/analytics.py
backend/app/routers/auth.py
backend/app/routers/candidates.py
backend/app/routers/jobs.py
backend/app/schemas.py
backend/app/security.py
backend/app/seed.py
backend/app/seed_data.py
backend/app/services/__init__.py
backend/app/services/matching.py
backend/app/services/parsing.py
backend/app/wait_db.py
backend/Dockerfile
backend/migrations/env.py
backend/migrations/script.py.mako
backend/migrations/versions/ea131b083c8f_initial_schema.py
backend/pyproject.toml
backend/requirements.txt
backend/skillmatch.db
backend/tests/__init__.py
backend/tests/conftest.py
backend/tests/test_api.py
backend/tests/test_configuration.py
backend/tests/test_services.py
data/jobs.csv
data/skills.csv
docker-compose.yml
docs/DESIGN_DECISIONS.md
docs/RUN_GUIDE.md
docs/screenshots/dashboard-desktop.png
docs/screenshots/dashboard-mobile.png
docs/screenshots/landing-desktop.png
docs/screenshots/match-result.png
docs/VERIFICATION.md
frontend/.dockerignore
frontend/Dockerfile
frontend/e2e/live.spec.ts
frontend/e2e/workspace.spec.ts
frontend/index.html
frontend/nginx.conf
frontend/package-lock.json
frontend/package.json
frontend/playwright.config.ts
frontend/public/favicon.svg
frontend/scripts/copy-docs.mjs
frontend/src/lib/api.ts
frontend/src/lib/charts.ts
frontend/src/lib/demo.ts
frontend/src/lib/scene.ts
frontend/src/lib/types.ts
frontend/src/lib/utils.test.ts
frontend/src/lib/utils.ts
frontend/src/main.ts
frontend/src/styles/main.css
frontend/src/vite-env.d.ts
frontend/tsconfig.json
frontend/vite.config.ts
GITHUB_COPILOT_LOG.md
notebooks/01_pandas_analysis.ipynb
notebooks/02_matplotlib_visualizations.ipynb
notebooks/requirements.txt
README.md
scripts/execute_notebooks.py
scripts/export_schema.py
scripts/export_source.py
scripts/generate_course_data.py
scripts/prepare_e2e.py
scripts/sqlite_crud.py
sql/01_schema.sql
sql/02_examples.sql
```

## .env.example

````text
DATABASE_URL=postgresql+psycopg://skillmatch:localdev@dev-db:5432/skillmatch?sslmode=disable
JWT_SECRET=replace-with-a-random-secret-at-least-32-characters
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:8080,http://localhost:5173,http://127.0.0.1:8080,http://127.0.0.1:5173
COOKIE_SECURE=false
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
SEMANTIC_ENABLED=true
SEED_ON_START=true

````

## .github/workflows/ci.yml

````yaml
name: Build and test
on:
  push:
  pull_request:
permissions:
  contents: read
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
          cache-dependency-path: backend/requirements.txt
      - run: pip install --index-url https://download.pytorch.org/whl/cpu torch
      - run: pip install -r backend/requirements.txt
      - run: ruff check backend scripts
      - run: pytest
        working-directory: backend
      - run: alembic upgrade head
        working-directory: backend
        env:
          DATABASE_URL: sqlite:///./migration-test.db
          SEMANTIC_ENABLED: 'false'
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
        working-directory: frontend
      - run: npm test
        working-directory: frontend
      - run: npm run build
        working-directory: frontend
  docker:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: ./backend
          push: false
          cache-from: type=gha,scope=backend
          cache-to: type=gha,mode=max,scope=backend
      - uses: docker/build-push-action@v6
        with:
          context: ./frontend
          push: false
          cache-from: type=gha,scope=frontend
          cache-to: type=gha,mode=max,scope=frontend

````

## .gitignore

````text
.env
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
*.pyc
*.db
node_modules/
dist/
coverage/
.ipynb_checkpoints/
artifacts/
test-results/
playwright-report/
frontend/public/docs-assets/

````

## backend/.dockerignore

````text
.venv
__pycache__
.pytest_cache
*.db
.env

````

## backend/alembic.ini

````text
[alembic]
script_location = migrations
prepend_sys_path = .

````

## backend/app/__init__.py

````python
"""SkillMatch AI application."""

````

## backend/app/config.py

````python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./skillmatch.db"
    jwt_secret: str = "development-only-change-before-deploying-12345"
    environment: str = "development"
    cors_origins: str = (
        "http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:8080"
    )
    cookie_secure: bool = False
    semantic_enabled: bool = True
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    seed_on_start: bool = False
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    def validate_production(self) -> None:
        if self.environment == "production":
            if len(self.jwt_secret) < 32 or "change" in self.jwt_secret or "replace" in self.jwt_secret:
                raise ValueError("Set a strong JWT_SECRET for production")
            if not self.database_url.startswith(("postgresql", "postgres://")) or not self.cookie_secure:
                raise ValueError("Production requires PostgreSQL and COOKIE_SECURE=true")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production()
    return settings

````

## backend/app/create_admin.py

````python
"""Create a platform administrator through a trusted local terminal."""

import getpass

from pydantic import TypeAdapter
from pydantic.networks import EmailStr
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import password_hash


def main() -> None:
    email = str(TypeAdapter(EmailStr).validate_python(input("Admin email: ").strip())).lower()
    name = input("Display name: ").strip()
    password = getpass.getpass("Password (at least 12 characters): ")
    if len(password) < 12 or len(password) > 128 or len(name) < 2:
        raise SystemExit("Use a 12–128 character password and a name with at least two characters.")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords did not match.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("That email already exists; no account was modified.")
        db.add(User(name=name, email=email, password_hash=password_hash.hash(password), role="admin"))
        db.commit()
    print("Administrator created.")


if __name__ == "__main__":
    main()

````

## backend/app/db.py

````python
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def build_engine():
    settings = get_settings()
    raw = settings.database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if raw.startswith("postgresql://"):
        raw = raw.replace("postgresql://", "postgresql+psycopg://", 1)
    url = make_url(raw)
    if url.drivername.startswith("postgresql"):
        if settings.environment == "production" or "neon.tech" in (url.host or ""):
            url = url.update_query_dict({"sslmode": "require"})
        return create_engine(url, poolclass=NullPool, connect_args={"connect_timeout": 15})
    sqlite_engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(sqlite_engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    return sqlite_engine


engine = build_engine()
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as db:
        yield db

````

## backend/app/limits.py

````python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

````

## backend/app/main.py

````python
import json
import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.db import SessionLocal
from app.limits import limiter
from app.routers import analytics, auth, candidates, jobs

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("skillmatch")
settings = get_settings()
app = FastAPI(
    title="SkillMatch AI",
    version="1.0.0",
    description="Resume intelligence and transparent job matching",
    docs_url=None,
    redoc_url=None,
)


@app.get("/docs", include_in_schema=False)
def documentation():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="SkillMatch AI — API documentation",
        swagger_js_url="/docs-assets/swagger-ui-bundle.js",
        swagger_css_url="/docs-assets/swagger-ui.css",
        swagger_favicon_url="/docs-assets/favicon-32x32.png",
        swagger_ui_parameters={"validatorUrl": None},
    )


local_docs = Path(__file__).resolve().parents[2] / "frontend" / "public" / "docs-assets"
if local_docs.exists():
    app.mount("/docs-assets", StaticFiles(directory=local_docs), name="docs-assets")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = uuid.uuid4().hex
    start = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - start) * 1000),
            }
        )
    )
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "This change conflicts with an existing record"})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.exception("unhandled_error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


@app.get("/api/v1/health", tags=["Health"])
def health():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "database unavailable"})


for router in (auth.router, jobs.router, candidates.router, analytics.router):
    app.include_router(router, prefix="/api/v1")

````

## backend/app/models.py

````python
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


resume_skills = Table(
    "resume_skills",
    Base.metadata,
    Column("resume_id", ForeignKey("resumes.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)
job_skills = Table(
    "job_skills",
    Base.metadata,
    Column("job_id", ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('candidate','recruiter','admin')"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="candidate")
    active: Mapped[bool] = mapped_column(default=True)
    token_version: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(60), default="Technology")


class Resume(Base):
    __tablename__ = "resumes"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    skills: Mapped[list[Skill]] = relationship(secondary=resume_skills, lazy="selectin")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("salary_min >= 0 AND salary_max >= salary_min"),
        Index("ix_jobs_location_type", "location", "employment_type"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    recruiter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(150), index=True)
    company: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(100))
    employment_type: Mapped[str] = mapped_column(String(30), default="Full-time")
    description: Mapped[str] = mapped_column(Text)
    salary_min: Mapped[int] = mapped_column(Integer, default=0)
    salary_max: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    skills: Mapped[list[Skill]] = relationship(secondary=job_skills, lazy="selectin")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),
        CheckConstraint("status IN ('Applied','Reviewing','Interview','Rejected','Hired')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(30), default="Applied")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    job: Mapped[Job] = relationship(lazy="joined")
    user: Mapped[User] = relationship(lazy="joined")


class MatchResult(Base):
    __tablename__ = "match_results"
    __table_args__ = (
        UniqueConstraint("resume_id", "job_id", name="uq_match_resume_job"),
        CheckConstraint("score >= 0 AND score <= 100"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Float)
    semantic_score: Mapped[float] = mapped_column(Float)
    keyword_score: Mapped[float] = mapped_column(Float)
    matched: Mapped[list[str]] = mapped_column(JSON)
    missing: Mapped[list[str]] = mapped_column(JSON)
    method: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

````

## backend/app/repositories/__init__.py

````python
"""Persistence operations."""

````

## backend/app/repositories/catalog.py

````python
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Job, Resume, Skill


def get_skills(db: Session, names: list[str]) -> list[Skill]:
    skills = []
    for name in names:
        skill = db.scalar(select(Skill).where(func.lower(Skill.name) == name.lower()))
        if not skill:
            skill = Skill(name=name)
            db.add(skill)
            db.flush()
        skills.append(skill)
    return skills


def jobs_page(
    db: Session, query: str, location: str, kind: str, page: int, size: int, owner: int | None = None
) -> tuple[list[Job], int]:
    stmt = select(Job).where(Job.active.is_(True))
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        stmt = stmt.where(
            or_(
                Job.title.ilike(pattern, escape="\\"),
                Job.company.ilike(pattern, escape="\\"),
                Job.skills.any(Skill.name.ilike(pattern, escape="\\")),
            )
        )
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location}%"))
    if kind:
        stmt = stmt.where(Job.employment_type == kind)
    if owner is not None:
        stmt = stmt.where(Job.recruiter_id == owner)
    count = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    jobs = db.scalars(
        stmt.order_by(Job.created_at.desc(), Job.id.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return list(jobs), count


def job_public(job: Job) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "employment_type": job.employment_type,
        "description": job.description,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "skills": [s.name for s in job.skills],
        "created_at": job.created_at.isoformat(),
        "active": job.active,
    }


def resume_public(resume: Resume) -> dict:
    return {
        "id": resume.id,
        "filename": resume.filename,
        "skills": [s.name for s in resume.skills],
        "created_at": resume.created_at.isoformat(),
    }

````

## backend/app/routers/__init__.py

````python
"""HTTP API routers."""

````

## backend/app/routers/analytics.py

````python
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Application, Job, MatchResult, Resume, Skill, User, job_skills
from app.repositories.catalog import job_public
from app.schemas import UserUpdate
from app.security import current_user, roles, user_public

router = APIRouter(tags=["Analytics & administration"])


@router.get("/analytics")
def analytics(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    match_stmt = select(MatchResult)
    app_stmt = select(Application)
    if user.role == "candidate":
        match_stmt = match_stmt.join(Resume).where(Resume.user_id == user.id)
        app_stmt = app_stmt.where(Application.user_id == user.id)
    elif user.role == "recruiter":
        match_stmt = match_stmt.join(Job).where(Job.recruiter_id == user.id)
        app_stmt = app_stmt.join(Job).where(Job.recruiter_id == user.id)
    matches = list(db.scalars(match_stmt).all())
    applications = list(db.scalars(app_stmt).all())
    demand = db.execute(
        select(Skill.name, func.count(job_skills.c.job_id))
        .join(job_skills)
        .join(Job, Job.id == job_skills.c.job_id)
        .where(Job.active.is_(True))
        .group_by(Skill.name)
        .order_by(func.count(job_skills.c.job_id).desc())
        .limit(6)
    ).all()
    return {
        "matches": len(matches),
        "average_score": round(sum(m.score for m in matches) / len(matches), 1) if matches else 0,
        "applications": len(applications),
        "interviews": sum(a.status == "Interview" for a in applications),
        "skill_gaps": dict(Counter(s for m in matches for s in m.missing).most_common(6)),
        "score_distribution": [
            sum(low <= m.score < low + 20 or (low == 80 and m.score == 100) for m in matches)
            for low in range(0, 100, 20)
        ],
        "in_demand": dict(demand),
        "applications_over_time": dict(
            sorted(Counter(a.created_at.strftime("%Y-%m-%d") for a in applications).items())
        ),
    }


@router.get("/admin")
def admin(
    page: int = Query(1, ge=1), user: User = Depends(roles("admin")), db: Session = Depends(get_db)
) -> dict:
    return {
        "stats": {
            "users": db.scalar(select(func.count(User.id))),
            "jobs": db.scalar(select(func.count(Job.id)).where(Job.active.is_(True))),
            "resumes": db.scalar(select(func.count(Resume.id))),
            "applications": db.scalar(select(func.count(Application.id))),
        },
        "users": [
            user_public(u)
            for u in db.scalars(select(User).order_by(User.id).offset((page - 1) * 50).limit(50)).all()
        ],
        "jobs": [
            job_public(j)
            for j in db.scalars(
                select(Job)
                .where(Job.active.is_(True))
                .order_by(Job.id.desc())
                .offset((page - 1) * 50)
                .limit(50)
            ).all()
        ],
        "page": page,
    }


@router.patch("/admin/users/{user_id}")
def update_user(
    user_id: int, body: UserUpdate, user: User = Depends(roles("admin")), db: Session = Depends(get_db)
) -> dict:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    if target.id == user.id:
        raise HTTPException(400, "You cannot disable your own account")
    target.active = body.active
    target.token_version += 1
    db.commit()
    return user_public(target)

````

## backend/app/routers/auth.py

````python
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.limits import limiter
from app.models import RefreshSession, User
from app.schemas import Login, Register
from app.security import (
    DUMMY_HASH,
    check_origin,
    current_user,
    decode_token,
    issue_tokens,
    password_hash,
    user_public,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
def register(request: Request, body: Register, response: Response, db: Session = Depends(get_db)) -> dict:
    user = User(
        name=body.name,
        email=str(body.email).lower(),
        role=body.role,
        password_hash=password_hash.hash(body.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists") from None
    return issue_tokens(user, db, response)


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, body: Login, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    valid = password_hash.verify(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.active:
        raise HTTPException(401, "Email or password is incorrect")
    return issue_tokens(user, db, response)


@router.post("/refresh")
@limiter.limit("30/minute")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    check_origin(request)
    payload = decode_token(request.cookies.get("refresh_token", ""), "refresh")
    user = db.get(User, int(payload["sub"]))
    removed = db.execute(
        delete(RefreshSession).where(
            RefreshSession.id == payload.get("jti"), RefreshSession.user_id == int(payload["sub"])
        )
    )
    if not user or not user.active or user.token_version != payload["ver"] or removed.rowcount != 1:
        db.rollback()
        raise HTTPException(401, "Please sign in again")
    return issue_tokens(user, db, response)


@router.post("/logout", status_code=204)
def logout(
    request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> None:
    check_origin(request)
    user.token_version += 1
    db.execute(delete(RefreshSession).where(RefreshSession.user_id == user.id))
    db.commit()
    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return user_public(user)

````

## backend/app/routers/candidates.py

````python
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.limits import limiter
from app.models import Application, Job, MatchResult, Resume, Skill, User
from app.repositories.catalog import job_public, resume_public
from app.schemas import MatchInput, StatusInput
from app.security import roles
from app.services.matching import embed, match_public, save_match
from app.services.parsing import MAX_FILE_SIZE, extract_skills, parse_resume

router = APIRouter(tags=["Candidates"])


@router.post("/resumes", status_code=201)
@limiter.limit("8/minute")
def upload(
    request: Request,
    file: UploadFile,
    user: User = Depends(roles("candidate")),
    db: Session = Depends(get_db),
) -> dict:
    filename = Path((file.filename or "resume").replace("\\", "/")).name[:255]
    data = file.file.read(MAX_FILE_SIZE + 1)
    file.file.close()
    text = parse_resume(data, filename)
    skills = list(db.scalars(select(Skill)).all())
    names = extract_skills(text, [s.name for s in skills])
    resume = Resume(
        user_id=user.id, filename=filename, text=text, skills=[s for s in skills if s.name in names]
    )
    db.add(resume)
    db.commit()
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

## backend/app/routers/jobs.py

````python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Job, MatchResult, User
from app.repositories.catalog import get_skills, job_public, jobs_page
from app.schemas import JobInput
from app.security import roles

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("")
def list_jobs(
    q: str = Query("", max_length=100),
    location: str = Query("", max_length=100),
    kind: str = "",
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
) -> dict:
    jobs, total = jobs_page(db, q, location, kind, page, size)
    return {"items": [job_public(j) for j in jobs], "total": total, "page": page, "size": size}


@router.get("/mine")
def mine(user: User = Depends(roles("recruiter", "admin")), db: Session = Depends(get_db)) -> dict:
    jobs, total = jobs_page(db, "", "", "", 1, 200, owner=user.id)
    return {"items": [job_public(j) for j in jobs], "total": total}


@router.get("/{job_id}")
def detail(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if not job or not job.active:
        raise HTTPException(404, "Job not found")
    return job_public(job)


@router.post("", status_code=201)
def create(
    body: JobInput, user: User = Depends(roles("recruiter", "admin")), db: Session = Depends(get_db)
) -> dict:
    job = Job(**body.model_dump(exclude={"skills"}), recruiter_id=user.id, skills=get_skills(db, body.skills))
    db.add(job)
    db.commit()
    return job_public(job)


def owned_job(job_id: int, user: User, db: Session) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.recruiter_id != user.id and user.role != "admin":
        raise HTTPException(403, "You can only manage your own jobs")
    return job


@router.put("/{job_id}")
def update(
    job_id: int,
    body: JobInput,
    user: User = Depends(roles("recruiter", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    job = owned_job(job_id, user, db)
    for key, value in body.model_dump(exclude={"skills"}).items():
        setattr(job, key, value)
    job.skills = get_skills(db, body.skills)
    db.execute(delete(MatchResult).where(MatchResult.job_id == job.id))
    db.commit()
    return job_public(job)


@router.delete("/{job_id}", status_code=204)
def remove(
    job_id: int, user: User = Depends(roles("recruiter", "admin")), db: Session = Depends(get_db)
) -> None:
    owned_job(job_id, user, db).active = False
    db.commit()

````

## backend/app/schemas.py

````python
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class Register(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    role: Literal["candidate", "recruiter"] = "candidate"

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("Enter your name")
        return value.strip()


class Login(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class JobInput(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    company: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=100)
    employment_type: Literal["Full-time", "Part-time", "Contract", "Internship"] = "Full-time"
    description: str = Field(min_length=40, max_length=20000)
    salary_min: int = Field(ge=0, le=10000000)
    salary_max: int = Field(ge=0, le=10000000)
    skills: list[str] = Field(min_length=1, max_length=30)

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, values: list[str]) -> list[str]:
        values = list(dict.fromkeys(v.strip() for v in values))
        if any(not v or len(v) > 100 for v in values):
            raise ValueError("Skills must contain 1–100 characters")
        return values

    @model_validator(mode="after")
    def salary_order(self):
        if self.salary_max < self.salary_min:
            raise ValueError("Maximum salary must be at least minimum salary")
        return self


class MatchInput(BaseModel):
    resume_id: int
    job_id: int


class StatusInput(BaseModel):
    status: Literal["Applied", "Reviewing", "Interview", "Rejected", "Hired"]


class UserUpdate(BaseModel):
    active: bool

````

## backend/app/security.py

````python
from datetime import datetime, timedelta, timezone
from secrets import token_hex

import jwt
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import RefreshSession, User

password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
settings = get_settings()
DUMMY_HASH = password_hash.hash("dummy-password-for-timing-consistency")


def decode_token(token: str, kind: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience="skillmatch",
            options={"require": ["exp", "sub", "type", "ver"]},
        )
        if payload["type"] != kind:
            raise ValueError("Wrong token type")
        return payload
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, "Your session has expired. Please sign in again.") from None


def issue_tokens(user: User, db: Session, response: Response) -> dict:
    now = datetime.now(timezone.utc)
    db.execute(delete(RefreshSession).where(RefreshSession.expires_at < now))
    common = {"sub": str(user.id), "ver": user.token_version, "aud": "skillmatch", "iat": now}
    access = jwt.encode(
        {**common, "type": "access", "exp": now + timedelta(minutes=15)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    jti = token_hex(32)
    expires = now + timedelta(days=7)
    refresh = jwt.encode(
        {**common, "type": "refresh", "jti": jti, "exp": expires}, settings.jwt_secret, algorithm="HS256"
    )
    db.add(RefreshSession(id=jti, user_id=user.id, expires_at=expires))
    db.commit()
    response.set_cookie(
        "refresh_token",
        refresh,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=604800,
        path="/api/v1/auth",
    )
    return {"access_token": access, "token_type": "bearer", "user": user_public(user)}


def user_public(user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "active": user.active}


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(401, "Please sign in to continue")
    payload = decode_token(credentials.credentials, "access")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.active or user.token_version != payload["ver"]:
        raise HTTPException(401, "Session is no longer valid")
    return user


def roles(*allowed: str):
    def check(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(403, "This action is not available for your role")
        return user

    return check


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    allowed = settings.cors_origins.split(",")
    if origin and origin not in allowed:
        raise HTTPException(403, "Untrusted request origin")

````

## backend/app/seed.py

````python
import argparse
import secrets

from sqlalchemy import func, select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Job, Skill, User
from app.security import password_hash
from app.seed_data import SKILLS, generate_jobs


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(func.count(Skill.id))) == 0:
            db.add_all(Skill(**s) for s in SKILLS)
            db.commit()
        if db.scalar(select(func.count(Job.id))) > 0:
            return
        owner = db.scalar(select(User).where(User.email == "catalog@skillmatch.example"))
        if not owner:
            owner = User(
                name="SkillMatch Catalog",
                email="catalog@skillmatch.example",
                role="recruiter",
                active=False,
                password_hash=password_hash.hash(secrets.token_urlsafe(32)),
            )
            db.add(owner)
            db.flush()
        skills = {s.name: s for s in db.scalars(select(Skill)).all()}
        for data in generate_jobs():
            names = data.pop("skills")
            db.add(Job(**data, recruiter_id=owner.id, skills=[skills[n] for n in names]))
        db.commit()
        print("Seeded 200 synthetic jobs and 300 skills. No demo credentials were created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--if-enabled", action="store_true")
    args = parser.parse_args()
    if not args.if_enabled or get_settings().seed_on_start:
        seed()

````

## backend/app/seed_data.py

````python
"""Deterministic synthetic career dataset; companies and openings are illustrative."""

import random

SKILL_GROUPS = {
    "Languages": "Python|JavaScript|TypeScript|Java|C|C++|C#|Go|Rust|Ruby|PHP|Swift|Kotlin|Dart|Scala|R|MATLAB|Julia|Perl|Lua|Haskell|Elixir|Clojure|F#|Objective-C|Solidity|Bash|PowerShell|SQL|Assembly",
    "Frontend": "HTML|CSS|React|Vue|Angular|Svelte|Next.js|Nuxt|Astro|Remix|jQuery|Bootstrap|Tailwind CSS|Sass|Less|Webpack|Vite|Rollup|esbuild|Babel|Redux|Zustand|MobX|React Query|GraphQL|Web Components|PWA|Web Accessibility|Responsive Design|Three.js",
    "Backend": "Node.js|Express|FastAPI|Django|Flask|Spring Boot|Laravel|Ruby on Rails|ASP.NET|NestJS|Koa|Hapi|Gin|Fiber|Actix|Phoenix|REST APIs|gRPC|WebSockets|OAuth|JWT|Microservices|Event Sourcing|CQRS|Domain Driven Design|API Design|Celery|RabbitMQ|Kafka|Nginx",
    "Data": "PostgreSQL|MySQL|SQLite|MongoDB|Redis|Elasticsearch|DynamoDB|Cassandra|Neo4j|CouchDB|MariaDB|Oracle|SQL Server|Snowflake|BigQuery|Redshift|Databricks|Apache Spark|Hadoop|Airflow|dbt|Pandas|NumPy|Polars|Dask|ETL|Data Modeling|Data Warehousing|Data Governance|Data Quality",
    "AI & ML": "Machine Learning|Deep Learning|TensorFlow|PyTorch|Scikit-learn|Keras|XGBoost|LightGBM|CatBoost|spaCy|NLTK|Transformers|Computer Vision|Natural Language Processing|Reinforcement Learning|Recommendation Systems|Time Series|Feature Engineering|Model Deployment|MLOps|MLflow|Kubeflow|Hugging Face|LangChain|Vector Databases|Prompt Engineering|RAG|Model Evaluation|Statistics|A/B Testing",
    "Cloud & DevOps": "AWS|Azure|Google Cloud|Docker|Kubernetes|Terraform|Ansible|Pulumi|CloudFormation|Jenkins|GitHub Actions|GitLab CI|CircleCI|Argo CD|Helm|Prometheus|Grafana|Datadog|Linux|Unix|Networking|Load Balancing|Serverless|AWS Lambda|Cloud Security|SRE|Incident Response|Observability|CI/CD|Git",
    "Design": "Figma|Sketch|Adobe XD|Photoshop|Illustrator|InDesign|After Effects|Blender|Cinema 4D|Framer|Webflow|UI Design|UX Research|Interaction Design|Design Systems|Prototyping|Wireframing|Information Architecture|Usability Testing|User Interviews|Journey Mapping|Service Design|Visual Design|Typography|Color Theory|Motion Design|Design Thinking|Product Design|Content Design|Accessibility Audits",
    "Product & Business": "Product Management|Agile|Scrum|Kanban|Jira|Confluence|Notion|Roadmapping|Stakeholder Management|Market Research|Competitive Analysis|Business Analysis|Requirements Gathering|OKRs|KPIs|Product Analytics|Amplitude|Mixpanel|Google Analytics|Looker|Tableau|Power BI|Excel|Financial Modeling|Pricing Strategy|Go-to-Market|Growth Strategy|Customer Success|Salesforce|HubSpot",
    "Testing & Security": "Pytest|Jest|Vitest|Cypress|Playwright|Selenium|JUnit|Mocha|Chai|Testing Library|Test Automation|Unit Testing|Integration Testing|Load Testing|k6|JMeter|Postman|Insomnia|OWASP|Penetration Testing|Threat Modeling|Cryptography|Identity Management|Network Security|SOC 2|ISO 27001|GDPR|Security Auditing|SonarQube|SAST",
    "Professional": "Communication|Leadership|Teamwork|Problem Solving|Critical Thinking|Project Management|Time Management|Mentoring|Technical Writing|Public Speaking|Negotiation|Conflict Resolution|Adaptability|Collaboration|Remote Collaboration|Presentation Skills|Documentation|Code Review|System Design|Algorithms|Data Structures|Object Oriented Programming|Functional Programming|Distributed Systems|Performance Optimization|Debugging|Research|Decision Making|Strategic Planning|Customer Empathy",
}
SKILLS = [
    {"name": name, "category": category}
    for category, names in SKILL_GROUPS.items()
    for name in names.split("|")
]
PROFILES = [
    ("Senior Frontend Developer", ["React", "TypeScript", "JavaScript", "CSS", "Next.js", "Git"]),
    ("Full Stack Engineer", ["React", "Node.js", "TypeScript", "PostgreSQL", "Docker", "REST APIs"]),
    ("Product Designer", ["Figma", "UI Design", "UX Research", "Prototyping", "Design Systems"]),
    ("Python Backend Engineer", ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Pytest"]),
    ("Data Scientist", ["Python", "Pandas", "Machine Learning", "SQL", "Statistics", "Scikit-learn"]),
    ("Machine Learning Engineer", ["Python", "PyTorch", "MLOps", "Docker", "Transformers", "AWS"]),
    ("DevOps Engineer", ["AWS", "Kubernetes", "Terraform", "CI/CD", "Linux", "Docker"]),
    ("Mobile Developer", ["Swift", "Kotlin", "Git", "REST APIs", "Unit Testing"]),
    ("Analytics Engineer", ["SQL", "dbt", "Snowflake", "Python", "Data Modeling"]),
    ("Security Engineer", ["Cloud Security", "Python", "OWASP", "Threat Modeling", "Linux"]),
]
COMPANIES = [
    "Linear",
    "Vercel",
    "Notion",
    "Stripe",
    "Figma",
    "Supabase",
    "Ramp",
    "Arc",
    "Mercury",
    "Raycast",
    "Loom",
    "Webflow",
    "Retool",
    "Resend",
    "Cal.com",
    "Clerk",
    "Neon",
    "PlanetScale",
    "PostHog",
    "Tailscale",
]


def generate_jobs() -> list[dict]:
    rng = random.Random(42)
    jobs = []
    for i in range(200):
        title, skills = PROFILES[i % len(PROFILES)]
        company = COMPANIES[i % len(COMPANIES)]
        minimum = rng.randrange(85, 160, 5) * 1000
        jobs.append(
            {
                "title": title,
                "company": company,
                "location": ["Remote", "San Francisco, CA", "New York, NY", "London, UK", "Bengaluru, IN"][
                    i % 5
                ],
                "employment_type": "Contract" if i % 9 == 0 else "Full-time",
                "salary_min": minimum,
                "salary_max": minimum + 40000,
                "description": f"Join the {company} team as a {title.lower()} and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with {', '.join(skills)}. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",
                "skills": skills,
            }
        )
    return jobs

````

## backend/app/services/__init__.py

````python
"""Domain services."""

````

## backend/app/services/matching.py

````python
import logging
from functools import lru_cache
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Job, MatchResult, Resume

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(get_settings().embedding_model)


@lru_cache(maxsize=512)
def embed(text: str):
    return embedding_model().encode(text[:12000], normalize_embeddings=True)


def calculate_match(resume: Resume, job: Job) -> dict:
    have = {s.name.casefold() for s in resume.skills}
    matched = sorted(s.name for s in job.skills if s.name.casefold() in have)
    missing = sorted(s.name for s in job.skills if s.name.casefold() not in have)
    keyword = 100 * len(matched) / max(1, len(job.skills))
    semantic = 0.0
    method = "keyword"
    if get_settings().semantic_enabled:
        try:
            semantic = max(
                0.0, min(100.0, float(embed(resume.text) @ embed(job.title + "\n" + job.description)) * 100)
            )
            method = "hybrid"
        except Exception:
            logger.warning("semantic_model_unavailable; using keyword overlap", exc_info=True)
    score = 0.65 * semantic + 0.35 * keyword if method == "hybrid" else keyword
    return {
        "score": round(score, 1),
        "semantic_score": round(semantic, 1),
        "keyword_score": round(keyword, 1),
        "matched": matched,
        "missing": missing,
        "method": method,
    }


def save_match(db: Session, resume: Resume, job: Job) -> MatchResult:
    result = db.scalar(
        select(MatchResult).where(MatchResult.resume_id == resume.id, MatchResult.job_id == job.id)
    )
    if not result:
        result = MatchResult(resume_id=resume.id, job_id=job.id)
    for key, value in calculate_match(resume, job).items():
        setattr(result, key, value)
    db.add(result)
    db.commit()
    return result


def match_public(result: MatchResult) -> dict:
    return {
        "id": result.id,
        "resume_id": result.resume_id,
        "job_id": result.job_id,
        "score": result.score,
        "semantic_score": result.semantic_score,
        "keyword_score": result.keyword_score,
        "matched": result.matched,
        "missing": result.missing,
        "method": result.method,
        "suggestions": [
            {
                "skill": name,
                "title": f"Build your {name} skills",
                "url": "https://www.freecodecamp.org/news/search/?query=" + quote(name),
            }
            for name in result.missing
        ],
    }

````

## backend/app/services/parsing.py

````python
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pdfplumber
import spacy
from docx import Document
from fastapi import HTTPException
from spacy.matcher import PhraseMatcher

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


def extract_skills(text: str, names: list[str]) -> list[str]:
    nlp = spacy.blank("en")
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for name in names:
        matcher.add(name, [nlp.make_doc(name)])
    aliases = {
        "js": "JavaScript",
        "ts": "TypeScript",
        "postgres": "PostgreSQL",
        "sklearn": "Scikit-learn",
        "react.js": "React",
        "nodejs": "Node.js",
    }
    for alias, canonical in aliases.items():
        if canonical in names:
            matcher.add(canonical, [nlp.make_doc(alias)])
    return sorted({nlp.vocab.strings[match_id] for match_id, _, _ in matcher(nlp.make_doc(text))})

````

## backend/app/wait_db.py

````python
import time

from sqlalchemy import text

from app.db import engine

if __name__ == "__main__":
    for attempt in range(30):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            break
        except Exception:
            if attempt == 29:
                raise
            time.sleep(2)

````

## backend/Dockerfile

````text
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch && pip install -r requirements.txt
RUN useradd --create-home --uid 10001 app
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["sh", "-c", "python -m app.wait_db && alembic upgrade head && python -m app.seed --if-enabled && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]

````

## backend/migrations/env.py

````python
from alembic import context

from app import models  # noqa: F401
from app.db import Base, engine

target_metadata = Base.metadata
if context.is_offline_mode():
    context.configure(url=engine.url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

````

## backend/migrations/script.py.mako

````text
"""${message}"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade():
    ${upgrades if upgrades else "pass"}

def downgrade():
    ${downgrades if downgrades else "pass"}

````

## backend/migrations/versions/ea131b083c8f_initial_schema.py

````python
"""initial schema"""

import sqlalchemy as sa
from alembic import op

revision = "ea131b083c8f"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_skills_name"), "skills", ["name"], unique=True)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('candidate','recruiter','admin')"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recruiter_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("company", sa.String(length=100), nullable=False),
        sa.Column("location", sa.String(length=100), nullable=False),
        sa.Column("employment_type", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=False),
        sa.Column("salary_max", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("salary_min >= 0 AND salary_max >= salary_min"),
        sa.ForeignKeyConstraint(["recruiter_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_active"), "jobs", ["active"], unique=False)
    op.create_index("ix_jobs_location_type", "jobs", ["location", "employment_type"], unique=False)
    op.create_index(op.f("ix_jobs_recruiter_id"), "jobs", ["recruiter_id"], unique=False)
    op.create_index(op.f("ix_jobs_title"), "jobs", ["title"], unique=False)
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_sessions_user_id"), "refresh_sessions", ["user_id"], unique=False)
    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resumes_user_id"), "resumes", ["user_id"], unique=False)
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('Applied','Reviewing','Interview','Rejected','Hired')"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),
    )
    op.create_index(op.f("ix_applications_job_id"), "applications", ["job_id"], unique=False)
    op.create_index(op.f("ix_applications_user_id"), "applications", ["user_id"], unique=False)
    op.create_table(
        "job_skills",
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id", "skill_id"),
    )
    op.create_table(
        "match_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("semantic_score", sa.Float(), nullable=False),
        sa.Column("keyword_score", sa.Float(), nullable=False),
        sa.Column("matched", sa.JSON(), nullable=False),
        sa.Column("missing", sa.JSON(), nullable=False),
        sa.Column("method", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("score >= 0 AND score <= 100"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resume_id", "job_id", name="uq_match_resume_job"),
    )
    op.create_index(op.f("ix_match_results_job_id"), "match_results", ["job_id"], unique=False)
    op.create_index(op.f("ix_match_results_resume_id"), "match_results", ["resume_id"], unique=False)
    op.create_table(
        "resume_skills",
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("resume_id", "skill_id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_table("resume_skills")
    op.drop_index(op.f("ix_match_results_resume_id"), table_name="match_results")
    op.drop_index(op.f("ix_match_results_job_id"), table_name="match_results")
    op.drop_table("match_results")
    op.drop_table("job_skills")
    op.drop_index(op.f("ix_applications_user_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_job_id"), table_name="applications")
    op.drop_table("applications")
    op.drop_index(op.f("ix_resumes_user_id"), table_name="resumes")
    op.drop_table("resumes")
    op.drop_index(op.f("ix_refresh_sessions_user_id"), table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
    op.drop_index(op.f("ix_jobs_title"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_recruiter_id"), table_name="jobs")
    op.drop_index("ix_jobs_location_type", table_name="jobs")
    op.drop_index(op.f("ix_jobs_active"), table_name="jobs")
    op.drop_table("jobs")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_skills_name"), table_name="skills")
    op.drop_table("skills")
    # ### end Alembic commands ###

````

## backend/pyproject.toml

````text
[tool.ruff]
target-version = "py312"
line-length = 110

[tool.ruff.lint]
select = ["E", "F", "I"]
ignore = ["E501"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

````

## backend/requirements.txt

````text
fastapi>=0.115,<1
uvicorn[standard]>=0.34,<1
SQLAlchemy>=2.0.38,<2.1
alembic>=1.14,<2
psycopg[binary]>=3.2,<4
pydantic-settings>=2.8,<3
email-validator>=2.2,<3
PyJWT>=2.10,<3
pwdlib[argon2]>=0.2,<1
python-multipart>=0.0.20,<1
pdfplumber>=0.11,<1
python-docx>=1.1,<2
spacy>=3.8,<4
sentence-transformers>=3.4,<6
slowapi>=0.1.9,<1
httpx>=0.28,<1
pytest>=8.3,<10
ruff>=0.11,<1

````

## backend/tests/__init__.py

````python
"""Application integration tests."""

````

## backend/tests/conftest.py

````python
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SEMANTIC_ENABLED"] = "false"
os.environ["ENVIRONMENT"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.limits import limiter
from app.main import app
from app.models import Skill


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [Skill(name=n) for n in ["Python", "React", "TypeScript", "PostgreSQL", "Docker", "FastAPI"]]
        )
        db.commit()

    def override_db():
        with Session(engine, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    limiter.enabled = False
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def account(client, email="candidate@example.com", role="candidate"):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Test Person", "email": email, "password": "a-strong-test-password", "role": role},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}

````

## backend/tests/test_api.py

````python
from io import BytesIO

from docx import Document

from tests.conftest import account

JOB = {
    "title": "Python Engineer",
    "company": "Test Studio",
    "location": "Remote",
    "employment_type": "Full-time",
    "description": "Build thoughtful applications with Python, FastAPI, and PostgreSQL alongside our small engineering team.",
    "salary_min": 100000,
    "salary_max": 140000,
    "skills": ["Python", "FastAPI", "PostgreSQL"],
}


def resume_file():
    doc = Document()
    doc.add_paragraph(
        "Experienced Python engineer building reliable FastAPI services. Skilled in Docker, React, and collaborative product development."
    )
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def test_auth_rotation_logout_and_role_boundary(client):
    headers = account(client)
    assert client.get("/api/v1/auth/me", headers=headers).json()["role"] == "candidate"
    assert client.post("/api/v1/jobs", headers=headers, json=JOB).status_code == 403
    old_cookie = client.cookies.get("refresh_token")
    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    new_cookie = client.cookies.get("refresh_token")
    client.cookies.clear()
    client.cookies.set("refresh_token", old_cookie)
    assert client.post("/api/v1/auth/refresh").status_code == 401
    client.cookies.clear()
    client.cookies.set("refresh_token", new_cookie)
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_registration_validation_and_duplicate(client):
    account(client)
    payload = {
        "name": "Another",
        "email": "candidate@example.com",
        "password": "a-strong-test-password",
        "role": "candidate",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409
    payload["role"] = "admin"
    assert client.post("/api/v1/auth/register", json=payload).status_code == 422
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "candidate@example.com", "password": "wrong"}
        ).status_code
        == 401
    )


def test_complete_candidate_and_recruiter_flow(client):
    recruiter = account(client, "recruiter@example.com", "recruiter")
    created = client.post("/api/v1/jobs", headers=recruiter, json=JOB)
    assert created.status_code == 201
    job_id = created.json()["id"]
    candidate = account(client)
    uploaded = client.post(
        "/api/v1/resumes",
        headers=candidate,
        files={
            "file": (
                "resume.docx",
                resume_file(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert uploaded.status_code == 201, uploaded.text
    assert "Python" in uploaded.json()["skills"]
    body = {"resume_id": uploaded.json()["id"], "job_id": job_id}
    matched = client.post("/api/v1/matches", headers=candidate, json=body)
    assert matched.status_code == 200, matched.text
    assert matched.json()["method"] == "keyword"
    assert matched.json()["score"] == 66.7
    assert matched.json()["missing"] == ["PostgreSQL"]
    assert client.post("/api/v1/matches", headers=candidate, json=body).status_code == 200
    application = client.post("/api/v1/applications", headers=candidate, json=body)
    assert application.status_code == 201
    assert client.post("/api/v1/applications", headers=candidate, json=body).status_code == 409
    ranked = client.get("/api/v1/applications", headers=recruiter).json()
    assert ranked[0]["score"] == 66.7
    assert (
        client.patch(
            f"/api/v1/applications/{application.json()['id']}",
            headers=recruiter,
            json={"status": "Interview"},
        ).status_code
        == 200
    )
    analytics = client.get("/api/v1/analytics", headers=candidate).json()
    assert analytics["interviews"] == 1
    assert analytics["skill_gaps"] == {"PostgreSQL": 1}
    other = account(client, "other@example.com")
    assert client.post("/api/v1/matches", headers=other, json=body).status_code == 404
    assert client.delete(f"/api/v1/resumes/{body['resume_id']}", headers=other).status_code == 404
    assert client.delete(f"/api/v1/resumes/{body['resume_id']}", headers=candidate).status_code == 204
    assert client.get("/api/v1/applications", headers=candidate).json() == []


def test_job_search_ownership_and_archive(client):
    recruiter = account(client, "owner@example.com", "recruiter")
    job_id = client.post("/api/v1/jobs", headers=recruiter, json=JOB).json()["id"]
    other = account(client, "other@example.com", "recruiter")
    assert client.put(f"/api/v1/jobs/{job_id}", headers=other, json=JOB).status_code == 403
    assert client.delete(f"/api/v1/jobs/{job_id}", headers=other).status_code == 403
    assert client.get("/api/v1/jobs?q=python&location=Remote").json()["total"] == 1
    assert client.get("/api/v1/jobs?q=unrelated").json()["total"] == 0
    assert client.get("/api/v1/jobs?page=0").status_code == 422
    assert (
        client.put(f"/api/v1/jobs/{job_id}", headers=recruiter, json={**JOB, "salary_max": 1}).status_code
        == 422
    )
    assert client.delete(f"/api/v1/jobs/{job_id}", headers=recruiter).status_code == 204
    assert client.get(f"/api/v1/jobs/{job_id}").status_code == 404


def test_invalid_files_and_admin_access(client):
    headers = account(client)
    assert client.get("/api/v1/admin", headers=headers).status_code == 403
    assert client.get("/api/v1/resumes").status_code == 401
    for filename, data, status in [
        ("cv.txt", b"plain text", 415),
        ("cv.pdf", b"not a PDF", 415),
        ("cv.docx", b"PKbroken", 422),
        ("empty.pdf", b"", 413),
        ("large.pdf", b"%PDF-" + b"x" * (5 * 1024 * 1024), 413),
    ]:
        response = client.post("/api/v1/resumes", headers=headers, files={"file": (filename, data)})
        assert response.status_code == status, response.text


def test_refresh_rejects_untrusted_origin(client):
    account(client)
    assert (
        client.post("/api/v1/auth/refresh", headers={"Origin": "https://untrusted.example"}).status_code
        == 403
    )

````

## backend/tests/test_configuration.py

````python
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.db import build_engine, get_db
from app.main import app
from app.models import User
from tests.conftest import account


def test_production_refuses_insecure_defaults():
    with pytest.raises(ValueError):
        Settings(environment="production").validate_production()


def test_neon_enforces_tls_and_uses_external_pooler():
    settings = Settings(
        database_url="postgresql://user:password@ep-sample-pooler.neon.tech/main?sslmode=disable"
    )
    with patch("app.db.get_settings", return_value=settings):
        engine = build_engine()
    assert engine.url.drivername == "postgresql+psycopg"
    assert engine.url.query["sslmode"] == "require"
    assert isinstance(engine.pool, NullPool)
    engine.dispose()


def test_admin_controls_and_token_revocation(client):
    admin_headers = account(client, "admin@example.com")
    candidate_headers = account(client)
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    admin_user = db.scalar(select(User).where(User.email == "admin@example.com"))
    admin_user.role = "admin"
    admin_id = admin_user.id
    candidate_id = db.scalar(select(User.id).where(User.email == "candidate@example.com"))
    db.commit()
    generator.close()
    assert client.get("/api/v1/admin", headers=admin_headers).status_code == 200
    assert (
        client.patch(
            f"/api/v1/admin/users/{admin_id}", headers=admin_headers, json={"active": False}
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"/api/v1/admin/users/{candidate_id}", headers=admin_headers, json={"active": False}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me", headers=candidate_headers).status_code == 401
    assert (
        client.patch(
            f"/api/v1/admin/users/{candidate_id}", headers=admin_headers, json={"active": True}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me", headers=candidate_headers).status_code == 401

````

## backend/tests/test_services.py

````python
from unittest.mock import patch

import pytest

from app.models import Job, Resume, Skill
from app.seed_data import SKILLS, generate_jobs
from app.services.matching import calculate_match
from app.services.parsing import extract_skills, parse_resume


def test_skill_extraction_handles_aliases_and_word_boundaries():
    assert extract_skills(
        "TypeScript with JS and react.js; not a Pythonista.", ["TypeScript", "JavaScript", "React", "Python"]
    ) == ["JavaScript", "React", "TypeScript"]


def test_empty_skill_matching_is_safe():
    result = calculate_match(
        Resume(text="A long professional background", skills=[]),
        Job(title="Engineer", description="Build systems", skills=[]),
    )
    assert result["score"] == 0
    assert result["missing"] == []


def test_semantic_hybrid_weight_and_fallback():
    resume = Resume(text="Python developer", skills=[Skill(name="Python")])
    job = Job(
        title="Engineer", description="Python and SQL", skills=[Skill(name="Python"), Skill(name="SQL")]
    )

    class Vector:
        def __matmul__(self, other):
            return 0.8

    with patch("app.services.matching.get_settings") as settings:
        settings.return_value.semantic_enabled = True
        with patch("app.services.matching.embed", return_value=Vector()):
            assert calculate_match(resume, job)["score"] == 69.5
        with patch("app.services.matching.embed", side_effect=RuntimeError("offline")):
            assert calculate_match(resume, job)["method"] == "keyword"


def test_seed_catalog_integrity():
    names = {s["name"] for s in SKILLS}
    assert len(SKILLS) == len(names) == 300
    jobs = generate_jobs()
    assert len(jobs) == 200
    assert all(set(j["skills"]) <= names for j in jobs)
    assert all(j["salary_max"] >= j["salary_min"] >= 0 for j in jobs)


def test_scanned_pdf_rejected():
    with patch("app.services.parsing.pdfplumber.open") as pdf:
        pdf.return_value.__enter__.return_value.pages = []
        with pytest.raises(Exception) as error:
            parse_resume(b"%PDF-1.4", "resume.pdf")
        assert error.value.status_code == 422

````

## data/jobs.csv

````text
id,title,company,location,employment_type,salary_min,salary_max,description,skills,posted_date
1,Senior Frontend Developer,Linear,Remote,Contract,135000,175000,"Join the Linear team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-01
2,Full Stack Engineer,Vercel,"San Francisco, CA",Full-time,90000,130000,"Join the Vercel team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-02
3,Product Designer,Notion,"New York, NY",Full-time,85000,125000,"Join the Notion team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-03
4,Python Backend Engineer,Stripe,"London, UK",Full-time,140000,180000,"Join the Stripe team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-04
5,Data Scientist,Figma,"Bengaluru, IN",Full-time,105000,145000,"Join the Figma team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-05
6,Machine Learning Engineer,Supabase,Remote,Full-time,100000,140000,"Join the Supabase team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-06
7,DevOps Engineer,Ramp,"San Francisco, CA",Full-time,100000,140000,"Join the Ramp team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-07
8,Mobile Developer,Arc,"New York, NY",Full-time,95000,135000,"Join the Arc team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-08
9,Analytics Engineer,Mercury,"London, UK",Full-time,140000,180000,"Join the Mercury team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-09
10,Security Engineer,Raycast,"Bengaluru, IN",Contract,90000,130000,"Join the Raycast team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-10
11,Senior Frontend Developer,Loom,Remote,Full-time,135000,175000,"Join the Loom team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-11
12,Full Stack Engineer,Webflow,"San Francisco, CA",Full-time,140000,180000,"Join the Webflow team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-12
13,Product Designer,Retool,"New York, NY",Full-time,155000,195000,"Join the Retool team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-13
14,Python Backend Engineer,Resend,"London, UK",Full-time,125000,165000,"Join the Resend team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-14
15,Data Scientist,Cal.com,"Bengaluru, IN",Full-time,90000,130000,"Join the Cal.com team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-15
16,Machine Learning Engineer,Clerk,Remote,Full-time,130000,170000,"Join the Clerk team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-16
17,DevOps Engineer,Neon,"San Francisco, CA",Full-time,115000,155000,"Join the Neon team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-17
18,Mobile Developer,PlanetScale,"New York, NY",Full-time,85000,125000,"Join the PlanetScale team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-18
19,Analytics Engineer,PostHog,"London, UK",Contract,85000,125000,"Join the PostHog team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-19
20,Security Engineer,Tailscale,"Bengaluru, IN",Full-time,90000,130000,"Join the Tailscale team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-20
21,Senior Frontend Developer,Linear,Remote,Full-time,100000,140000,"Join the Linear team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-21
22,Full Stack Engineer,Vercel,"San Francisco, CA",Full-time,100000,140000,"Join the Vercel team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-22
23,Product Designer,Notion,"New York, NY",Full-time,125000,165000,"Join the Notion team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-23
24,Python Backend Engineer,Stripe,"London, UK",Full-time,130000,170000,"Join the Stripe team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-24
25,Data Scientist,Figma,"Bengaluru, IN",Full-time,85000,125000,"Join the Figma team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-25
26,Machine Learning Engineer,Supabase,Remote,Full-time,125000,165000,"Join the Supabase team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-26
27,DevOps Engineer,Ramp,"San Francisco, CA",Full-time,100000,140000,"Join the Ramp team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-27
28,Mobile Developer,Arc,"New York, NY",Contract,140000,180000,"Join the Arc team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-28
29,Analytics Engineer,Mercury,"London, UK",Full-time,135000,175000,"Join the Mercury team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-01
30,Security Engineer,Raycast,"Bengaluru, IN",Full-time,140000,180000,"Join the Raycast team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-02
31,Senior Frontend Developer,Loom,Remote,Full-time,125000,165000,"Join the Loom team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-03
32,Full Stack Engineer,Webflow,"San Francisco, CA",Full-time,115000,155000,"Join the Webflow team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-04
33,Product Designer,Retool,"New York, NY",Full-time,100000,140000,"Join the Retool team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-05
34,Python Backend Engineer,Resend,"London, UK",Full-time,120000,160000,"Join the Resend team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-06
35,Data Scientist,Cal.com,"Bengaluru, IN",Full-time,130000,170000,"Join the Cal.com team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-07
36,Machine Learning Engineer,Clerk,Remote,Full-time,105000,145000,"Join the Clerk team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-08
37,DevOps Engineer,Neon,"San Francisco, CA",Contract,145000,185000,"Join the Neon team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-09
38,Mobile Developer,PlanetScale,"New York, NY",Full-time,150000,190000,"Join the PlanetScale team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-10
39,Analytics Engineer,PostHog,"London, UK",Full-time,85000,125000,"Join the PostHog team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-11
40,Security Engineer,Tailscale,"Bengaluru, IN",Full-time,145000,185000,"Join the Tailscale team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-12
41,Senior Frontend Developer,Linear,Remote,Full-time,145000,185000,"Join the Linear team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-13
42,Full Stack Engineer,Vercel,"San Francisco, CA",Full-time,95000,135000,"Join the Vercel team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-14
43,Product Designer,Notion,"New York, NY",Full-time,140000,180000,"Join the Notion team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-15
44,Python Backend Engineer,Stripe,"London, UK",Full-time,115000,155000,"Join the Stripe team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-16
45,Data Scientist,Figma,"Bengaluru, IN",Full-time,110000,150000,"Join the Figma team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-17
46,Machine Learning Engineer,Supabase,Remote,Contract,105000,145000,"Join the Supabase team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-18
47,DevOps Engineer,Ramp,"San Francisco, CA",Full-time,95000,135000,"Join the Ramp team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-19
48,Mobile Developer,Arc,"New York, NY",Full-time,100000,140000,"Join the Arc team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-20
49,Analytics Engineer,Mercury,"London, UK",Full-time,145000,185000,"Join the Mercury team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-21
50,Security Engineer,Raycast,"Bengaluru, IN",Full-time,110000,150000,"Join the Raycast team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-22
51,Senior Frontend Developer,Loom,Remote,Full-time,90000,130000,"Join the Loom team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-23
52,Full Stack Engineer,Webflow,"San Francisco, CA",Full-time,90000,130000,"Join the Webflow team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-24
53,Product Designer,Retool,"New York, NY",Full-time,115000,155000,"Join the Retool team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-25
54,Python Backend Engineer,Resend,"London, UK",Full-time,90000,130000,"Join the Resend team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-26
55,Data Scientist,Cal.com,"Bengaluru, IN",Contract,110000,150000,"Join the Cal.com team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-27
56,Machine Learning Engineer,Clerk,Remote,Full-time,150000,190000,"Join the Clerk team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-28
57,DevOps Engineer,Neon,"San Francisco, CA",Full-time,110000,150000,"Join the Neon team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-01
58,Mobile Developer,PlanetScale,"New York, NY",Full-time,130000,170000,"Join the PlanetScale team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-02
59,Analytics Engineer,PostHog,"London, UK",Full-time,105000,145000,"Join the PostHog team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-03
60,Security Engineer,Tailscale,"Bengaluru, IN",Full-time,145000,185000,"Join the Tailscale team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-04
61,Senior Frontend Developer,Linear,Remote,Full-time,85000,125000,"Join the Linear team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-05
62,Full Stack Engineer,Vercel,"San Francisco, CA",Full-time,140000,180000,"Join the Vercel team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-06
63,Product Designer,Notion,"New York, NY",Full-time,120000,160000,"Join the Notion team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-07
64,Python Backend Engineer,Stripe,"London, UK",Contract,125000,165000,"Join the Stripe team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-08
65,Data Scientist,Figma,"Bengaluru, IN",Full-time,90000,130000,"Join the Figma team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-09
66,Machine Learning Engineer,Supabase,Remote,Full-time,155000,195000,"Join the Supabase team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-10
67,DevOps Engineer,Ramp,"San Francisco, CA",Full-time,115000,155000,"Join the Ramp team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-11
68,Mobile Developer,Arc,"New York, NY",Full-time,90000,130000,"Join the Arc team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-12
69,Analytics Engineer,Mercury,"London, UK",Full-time,125000,165000,"Join the Mercury team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-13
70,Security Engineer,Raycast,"Bengaluru, IN",Full-time,105000,145000,"Join the Raycast team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-14
71,Senior Frontend Developer,Loom,Remote,Full-time,150000,190000,"Join the Loom team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-15
72,Full Stack Engineer,Webflow,"San Francisco, CA",Full-time,135000,175000,"Join the Webflow team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-16
73,Product Designer,Retool,"New York, NY",Contract,130000,170000,"Join the Retool team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-17
74,Python Backend Engineer,Resend,"London, UK",Full-time,155000,195000,"Join the Resend team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-18
75,Data Scientist,Cal.com,"Bengaluru, IN",Full-time,150000,190000,"Join the Cal.com team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-19
76,Machine Learning Engineer,Clerk,Remote,Full-time,110000,150000,"Join the Clerk team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-20
77,DevOps Engineer,Neon,"San Francisco, CA",Full-time,130000,170000,"Join the Neon team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-21
78,Mobile Developer,PlanetScale,"New York, NY",Full-time,100000,140000,"Join the PlanetScale team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-22
79,Analytics Engineer,PostHog,"London, UK",Full-time,140000,180000,"Join the PostHog team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-23
80,Security Engineer,Tailscale,"Bengaluru, IN",Full-time,90000,130000,"Join the Tailscale team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-24
81,Senior Frontend Developer,Linear,Remote,Full-time,85000,125000,"Join the Linear team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-25
82,Full Stack Engineer,Vercel,"San Francisco, CA",Contract,135000,175000,"Join the Vercel team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-26
83,Product Designer,Notion,"New York, NY",Full-time,100000,140000,"Join the Notion team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-27
84,Python Backend Engineer,Stripe,"London, UK",Full-time,145000,185000,"Join the Stripe team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-28
85,Data Scientist,Figma,"Bengaluru, IN",Full-time,105000,145000,"Join the Figma team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-01
86,Machine Learning Engineer,Supabase,Remote,Full-time,90000,130000,"Join the Supabase team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-02
87,DevOps Engineer,Ramp,"San Francisco, CA",Full-time,150000,190000,"Join the Ramp team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-03
88,Mobile Developer,Arc,"New York, NY",Full-time,100000,140000,"Join the Arc team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-04
89,Analytics Engineer,Mercury,"London, UK",Full-time,150000,190000,"Join the Mercury team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-05
90,Security Engineer,Raycast,"Bengaluru, IN",Full-time,90000,130000,"Join the Raycast team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-06
91,Senior Frontend Developer,Loom,Remote,Contract,115000,155000,"Join the Loom team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-07
92,Full Stack Engineer,Webflow,"San Francisco, CA",Full-time,105000,145000,"Join the Webflow team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-08
93,Product Designer,Retool,"New York, NY",Full-time,120000,160000,"Join the Retool team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-09
94,Python Backend Engineer,Resend,"London, UK",Full-time,135000,175000,"Join the Resend team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-10
95,Data Scientist,Cal.com,"Bengaluru, IN",Full-time,150000,190000,"Join the Cal.com team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-11
96,Machine Learning Engineer,Clerk,Remote,Full-time,110000,150000,"Join the Clerk team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-12
97,DevOps Engineer,Neon,"San Francisco, CA",Full-time,95000,135000,"Join the Neon team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-13
98,Mobile Developer,PlanetScale,"New York, NY",Full-time,110000,150000,"Join the PlanetScale team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-14
99,Analytics Engineer,PostHog,"London, UK",Full-time,110000,150000,"Join the PostHog team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-15
100,Security Engineer,Tailscale,"Bengaluru, IN",Contract,100000,140000,"Join the Tailscale team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-16
101,Senior Frontend Developer,Linear,Remote,Full-time,135000,175000,"Join the Linear team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-17
102,Full Stack Engineer,Vercel,"San Francisco, CA",Full-time,105000,145000,"Join the Vercel team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-18
103,Product Designer,Notion,"New York, NY",Full-time,140000,180000,"Join the Notion team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-19
104,Python Backend Engineer,Stripe,"London, UK",Full-time,155000,195000,"Join the Stripe team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-20
105,Data Scientist,Figma,"Bengaluru, IN",Full-time,135000,175000,"Join the Figma team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-21
106,Machine Learning Engineer,Supabase,Remote,Full-time,135000,175000,"Join the Supabase team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-22
107,DevOps Engineer,Ramp,"San Francisco, CA",Full-time,90000,130000,"Join the Ramp team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-23
108,Mobile Developer,Arc,"New York, NY",Full-time,130000,170000,"Join the Arc team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-24
109,Analytics Engineer,Mercury,"London, UK",Contract,135000,175000,"Join the Mercury team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-25
110,Security Engineer,Raycast,"Bengaluru, IN",Full-time,95000,135000,"Join the Raycast team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-26
111,Senior Frontend Developer,Loom,Remote,Full-time,125000,165000,"Join the Loom team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-27
112,Full Stack Engineer,Webflow,"San Francisco, CA",Full-time,140000,180000,"Join the Webflow team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-28
113,Product Designer,Retool,"New York, NY",Full-time,100000,140000,"Join the Retool team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-01
114,Python Backend Engineer,Resend,"London, UK",Full-time,95000,135000,"Join the Resend team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-02
115,Data Scientist,Cal.com,"Bengaluru, IN",Full-time,120000,160000,"Join the Cal.com team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-03
116,Machine Learning Engineer,Clerk,Remote,Full-time,115000,155000,"Join the Clerk team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-04
117,DevOps Engineer,Neon,"San Francisco, CA",Full-time,105000,145000,"Join the Neon team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-05
118,Mobile Developer,PlanetScale,"New York, NY",Contract,155000,195000,"Join the PlanetScale team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-06
119,Analytics Engineer,PostHog,"London, UK",Full-time,135000,175000,"Join the PostHog team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-07
120,Security Engineer,Tailscale,"Bengaluru, IN",Full-time,140000,180000,"Join the Tailscale team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-08
121,Senior Frontend Developer,Linear,Remote,Full-time,125000,165000,"Join the Linear team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-09
122,Full Stack Engineer,Vercel,"San Francisco, CA",Full-time,100000,140000,"Join the Vercel team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-10
123,Product Designer,Notion,"New York, NY",Full-time,135000,175000,"Join the Notion team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-11
124,Python Backend Engineer,Stripe,"London, UK",Full-time,110000,150000,"Join the Stripe team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-12
125,Data Scientist,Figma,"Bengaluru, IN",Full-time,150000,190000,"Join the Figma team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-13
126,Machine Learning Engineer,Supabase,Remote,Full-time,145000,185000,"Join the Supabase team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-14
127,DevOps Engineer,Ramp,"San Francisco, CA",Contract,145000,185000,"Join the Ramp team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-15
128,Mobile Developer,Arc,"New York, NY",Full-time,85000,125000,"Join the Arc team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-16
129,Analytics Engineer,Mercury,"London, UK",Full-time,100000,140000,"Join the Mercury team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-17
130,Security Engineer,Raycast,"Bengaluru, IN",Full-time,150000,190000,"Join the Raycast team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-18
131,Senior Frontend Developer,Loom,Remote,Full-time,85000,125000,"Join the Loom team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-19
132,Full Stack Engineer,Webflow,"San Francisco, CA",Full-time,145000,185000,"Join the Webflow team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-20
133,Product Designer,Retool,"New York, NY",Full-time,110000,150000,"Join the Retool team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-21
134,Python Backend Engineer,Resend,"London, UK",Full-time,115000,155000,"Join the Resend team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-22
135,Data Scientist,Cal.com,"Bengaluru, IN",Full-time,105000,145000,"Join the Cal.com team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-23
136,Machine Learning Engineer,Clerk,Remote,Contract,90000,130000,"Join the Clerk team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-24
137,DevOps Engineer,Neon,"San Francisco, CA",Full-time,100000,140000,"Join the Neon team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-25
138,Mobile Developer,PlanetScale,"New York, NY",Full-time,155000,195000,"Join the PlanetScale team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-26
139,Analytics Engineer,PostHog,"London, UK",Full-time,130000,170000,"Join the PostHog team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-27
140,Security Engineer,Tailscale,"Bengaluru, IN",Full-time,155000,195000,"Join the Tailscale team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-28
141,Senior Frontend Developer,Linear,Remote,Full-time,140000,180000,"Join the Linear team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-01
142,Full Stack Engineer,Vercel,"San Francisco, CA",Full-time,110000,150000,"Join the Vercel team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-02
143,Product Designer,Notion,"New York, NY",Full-time,100000,140000,"Join the Notion team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-03
144,Python Backend Engineer,Stripe,"London, UK",Full-time,135000,175000,"Join the Stripe team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-04
145,Data Scientist,Figma,"Bengaluru, IN",Contract,120000,160000,"Join the Figma team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-05
146,Machine Learning Engineer,Supabase,Remote,Full-time,115000,155000,"Join the Supabase team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-06
147,DevOps Engineer,Ramp,"San Francisco, CA",Full-time,155000,195000,"Join the Ramp team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-07
148,Mobile Developer,Arc,"New York, NY",Full-time,155000,195000,"Join the Arc team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-08
149,Analytics Engineer,Mercury,"London, UK",Full-time,135000,175000,"Join the Mercury team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-09
150,Security Engineer,Raycast,"Bengaluru, IN",Full-time,120000,160000,"Join the Raycast team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-10
151,Senior Frontend Developer,Loom,Remote,Full-time,95000,135000,"Join the Loom team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-11
152,Full Stack Engineer,Webflow,"San Francisco, CA",Full-time,105000,145000,"Join the Webflow team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-12
153,Product Designer,Retool,"New York, NY",Full-time,95000,135000,"Join the Retool team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-13
154,Python Backend Engineer,Resend,"London, UK",Contract,100000,140000,"Join the Resend team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-14
155,Data Scientist,Cal.com,"Bengaluru, IN",Full-time,140000,180000,"Join the Cal.com team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-15
156,Machine Learning Engineer,Clerk,Remote,Full-time,125000,165000,"Join the Clerk team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-16
157,DevOps Engineer,Neon,"San Francisco, CA",Full-time,125000,165000,"Join the Neon team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-17
158,Mobile Developer,PlanetScale,"New York, NY",Full-time,105000,145000,"Join the PlanetScale team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-18
159,Analytics Engineer,PostHog,"London, UK",Full-time,140000,180000,"Join the PostHog team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-19
160,Security Engineer,Tailscale,"Bengaluru, IN",Full-time,130000,170000,"Join the Tailscale team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-20
161,Senior Frontend Developer,Linear,Remote,Full-time,115000,155000,"Join the Linear team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-21
162,Full Stack Engineer,Vercel,"San Francisco, CA",Full-time,155000,195000,"Join the Vercel team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-22
163,Product Designer,Notion,"New York, NY",Contract,130000,170000,"Join the Notion team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-23
164,Python Backend Engineer,Stripe,"London, UK",Full-time,115000,155000,"Join the Stripe team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-24
165,Data Scientist,Figma,"Bengaluru, IN",Full-time,110000,150000,"Join the Figma team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-25
166,Machine Learning Engineer,Supabase,Remote,Full-time,100000,140000,"Join the Supabase team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-26
167,DevOps Engineer,Ramp,"San Francisco, CA",Full-time,95000,135000,"Join the Ramp team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-27
168,Mobile Developer,Arc,"New York, NY",Full-time,125000,165000,"Join the Arc team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-28
169,Analytics Engineer,Mercury,"London, UK",Full-time,120000,160000,"Join the Mercury team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-01
170,Security Engineer,Raycast,"Bengaluru, IN",Full-time,90000,130000,"Join the Raycast team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-02
171,Senior Frontend Developer,Loom,Remote,Full-time,145000,185000,"Join the Loom team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-03
172,Full Stack Engineer,Webflow,"San Francisco, CA",Contract,85000,125000,"Join the Webflow team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-04
173,Product Designer,Retool,"New York, NY",Full-time,150000,190000,"Join the Retool team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-05
174,Python Backend Engineer,Resend,"London, UK",Full-time,90000,130000,"Join the Resend team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-06
175,Data Scientist,Cal.com,"Bengaluru, IN",Full-time,95000,135000,"Join the Cal.com team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-07
176,Machine Learning Engineer,Clerk,Remote,Full-time,135000,175000,"Join the Clerk team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-08
177,DevOps Engineer,Neon,"San Francisco, CA",Full-time,95000,135000,"Join the Neon team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-09
178,Mobile Developer,PlanetScale,"New York, NY",Full-time,145000,185000,"Join the PlanetScale team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-10
179,Analytics Engineer,PostHog,"London, UK",Full-time,135000,175000,"Join the PostHog team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-11
180,Security Engineer,Tailscale,"Bengaluru, IN",Full-time,115000,155000,"Join the Tailscale team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-12
181,Senior Frontend Developer,Linear,Remote,Contract,130000,170000,"Join the Linear team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-13
182,Full Stack Engineer,Vercel,"San Francisco, CA",Full-time,90000,130000,"Join the Vercel team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-14
183,Product Designer,Notion,"New York, NY",Full-time,115000,155000,"Join the Notion team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-15
184,Python Backend Engineer,Stripe,"London, UK",Full-time,115000,155000,"Join the Stripe team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-16
185,Data Scientist,Figma,"Bengaluru, IN",Full-time,130000,170000,"Join the Figma team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-17
186,Machine Learning Engineer,Supabase,Remote,Full-time,120000,160000,"Join the Supabase team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-18
187,DevOps Engineer,Ramp,"San Francisco, CA",Full-time,125000,165000,"Join the Ramp team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-19
188,Mobile Developer,Arc,"New York, NY",Full-time,105000,145000,"Join the Arc team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-20
189,Analytics Engineer,Mercury,"London, UK",Full-time,125000,165000,"Join the Mercury team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-21
190,Security Engineer,Raycast,"Bengaluru, IN",Contract,150000,190000,"Join the Raycast team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-22
191,Senior Frontend Developer,Loom,Remote,Full-time,85000,125000,"Join the Loom team as a senior frontend developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, TypeScript, JavaScript, CSS, Next.js, Git. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|TypeScript|JavaScript|CSS|Next.js|Git,2026-09-23
192,Full Stack Engineer,Webflow,"San Francisco, CA",Full-time,135000,175000,"Join the Webflow team as a full stack engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with React, Node.js, TypeScript, PostgreSQL, Docker, REST APIs. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",React|Node.js|TypeScript|PostgreSQL|Docker|REST APIs,2026-09-24
193,Product Designer,Retool,"New York, NY",Full-time,140000,180000,"Join the Retool team as a product designer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Figma, UI Design, UX Research, Prototyping, Design Systems. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Figma|UI Design|UX Research|Prototyping|Design Systems,2026-09-25
194,Python Backend Engineer,Resend,"London, UK",Full-time,90000,130000,"Join the Resend team as a python backend engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, FastAPI, PostgreSQL, Docker, Redis, Pytest. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|FastAPI|PostgreSQL|Docker|Redis|Pytest,2026-09-26
195,Data Scientist,Cal.com,"Bengaluru, IN",Full-time,135000,175000,"Join the Cal.com team as a data scientist and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, Pandas, Machine Learning, SQL, Statistics, Scikit-learn. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|Pandas|Machine Learning|SQL|Statistics|Scikit-learn,2026-09-27
196,Machine Learning Engineer,Clerk,Remote,Full-time,155000,195000,"Join the Clerk team as a machine learning engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Python, PyTorch, MLOps, Docker, Transformers, AWS. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Python|PyTorch|MLOps|Docker|Transformers|AWS,2026-09-28
197,DevOps Engineer,Neon,"San Francisco, CA",Full-time,125000,165000,"Join the Neon team as a devops engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with AWS, Kubernetes, Terraform, CI/CD, Linux, Docker. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",AWS|Kubernetes|Terraform|CI/CD|Linux|Docker,2026-09-01
198,Mobile Developer,PlanetScale,"New York, NY",Full-time,145000,185000,"Join the PlanetScale team as a mobile developer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Swift, Kotlin, Git, REST APIs, Unit Testing. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Swift|Kotlin|Git|REST APIs|Unit Testing,2026-09-02
199,Analytics Engineer,PostHog,"London, UK",Contract,105000,145000,"Join the PostHog team as a analytics engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with SQL, dbt, Snowflake, Python, Data Modeling. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",SQL|dbt|Snowflake|Python|Data Modeling,2026-09-03
200,Security Engineer,Tailscale,"Bengaluru, IN",Full-time,145000,185000,"Join the Tailscale team as a security engineer and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with Cloud Security, Python, OWASP, Threat Modeling, Linux. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",Cloud Security|Python|OWASP|Threat Modeling|Linux,2026-09-04

````

## data/skills.csv

````text
name,category
Python,Languages
JavaScript,Languages
TypeScript,Languages
Java,Languages
C,Languages
C++,Languages
C#,Languages
Go,Languages
Rust,Languages
Ruby,Languages
PHP,Languages
Swift,Languages
Kotlin,Languages
Dart,Languages
Scala,Languages
R,Languages
MATLAB,Languages
Julia,Languages
Perl,Languages
Lua,Languages
Haskell,Languages
Elixir,Languages
Clojure,Languages
F#,Languages
Objective-C,Languages
Solidity,Languages
Bash,Languages
PowerShell,Languages
SQL,Languages
Assembly,Languages
HTML,Frontend
CSS,Frontend
React,Frontend
Vue,Frontend
Angular,Frontend
Svelte,Frontend
Next.js,Frontend
Nuxt,Frontend
Astro,Frontend
Remix,Frontend
jQuery,Frontend
Bootstrap,Frontend
Tailwind CSS,Frontend
Sass,Frontend
Less,Frontend
Webpack,Frontend
Vite,Frontend
Rollup,Frontend
esbuild,Frontend
Babel,Frontend
Redux,Frontend
Zustand,Frontend
MobX,Frontend
React Query,Frontend
GraphQL,Frontend
Web Components,Frontend
PWA,Frontend
Web Accessibility,Frontend
Responsive Design,Frontend
Three.js,Frontend
Node.js,Backend
Express,Backend
FastAPI,Backend
Django,Backend
Flask,Backend
Spring Boot,Backend
Laravel,Backend
Ruby on Rails,Backend
ASP.NET,Backend
NestJS,Backend
Koa,Backend
Hapi,Backend
Gin,Backend
Fiber,Backend
Actix,Backend
Phoenix,Backend
REST APIs,Backend
gRPC,Backend
WebSockets,Backend
OAuth,Backend
JWT,Backend
Microservices,Backend
Event Sourcing,Backend
CQRS,Backend
Domain Driven Design,Backend
API Design,Backend
Celery,Backend
RabbitMQ,Backend
Kafka,Backend
Nginx,Backend
PostgreSQL,Data
MySQL,Data
SQLite,Data
MongoDB,Data
Redis,Data
Elasticsearch,Data
DynamoDB,Data
Cassandra,Data
Neo4j,Data
CouchDB,Data
MariaDB,Data
Oracle,Data
SQL Server,Data
Snowflake,Data
BigQuery,Data
Redshift,Data
Databricks,Data
Apache Spark,Data
Hadoop,Data
Airflow,Data
dbt,Data
Pandas,Data
NumPy,Data
Polars,Data
Dask,Data
ETL,Data
Data Modeling,Data
Data Warehousing,Data
Data Governance,Data
Data Quality,Data
Machine Learning,AI & ML
Deep Learning,AI & ML
TensorFlow,AI & ML
PyTorch,AI & ML
Scikit-learn,AI & ML
Keras,AI & ML
XGBoost,AI & ML
LightGBM,AI & ML
CatBoost,AI & ML
spaCy,AI & ML
NLTK,AI & ML
Transformers,AI & ML
Computer Vision,AI & ML
Natural Language Processing,AI & ML
Reinforcement Learning,AI & ML
Recommendation Systems,AI & ML
Time Series,AI & ML
Feature Engineering,AI & ML
Model Deployment,AI & ML
MLOps,AI & ML
MLflow,AI & ML
Kubeflow,AI & ML
Hugging Face,AI & ML
LangChain,AI & ML
Vector Databases,AI & ML
Prompt Engineering,AI & ML
RAG,AI & ML
Model Evaluation,AI & ML
Statistics,AI & ML
A/B Testing,AI & ML
AWS,Cloud & DevOps
Azure,Cloud & DevOps
Google Cloud,Cloud & DevOps
Docker,Cloud & DevOps
Kubernetes,Cloud & DevOps
Terraform,Cloud & DevOps
Ansible,Cloud & DevOps
Pulumi,Cloud & DevOps
CloudFormation,Cloud & DevOps
Jenkins,Cloud & DevOps
GitHub Actions,Cloud & DevOps
GitLab CI,Cloud & DevOps
CircleCI,Cloud & DevOps
Argo CD,Cloud & DevOps
Helm,Cloud & DevOps
Prometheus,Cloud & DevOps
Grafana,Cloud & DevOps
Datadog,Cloud & DevOps
Linux,Cloud & DevOps
Unix,Cloud & DevOps
Networking,Cloud & DevOps
Load Balancing,Cloud & DevOps
Serverless,Cloud & DevOps
AWS Lambda,Cloud & DevOps
Cloud Security,Cloud & DevOps
SRE,Cloud & DevOps
Incident Response,Cloud & DevOps
Observability,Cloud & DevOps
CI/CD,Cloud & DevOps
Git,Cloud & DevOps
Figma,Design
Sketch,Design
Adobe XD,Design
Photoshop,Design
Illustrator,Design
InDesign,Design
After Effects,Design
Blender,Design
Cinema 4D,Design
Framer,Design
Webflow,Design
UI Design,Design
UX Research,Design
Interaction Design,Design
Design Systems,Design
Prototyping,Design
Wireframing,Design
Information Architecture,Design
Usability Testing,Design
User Interviews,Design
Journey Mapping,Design
Service Design,Design
Visual Design,Design
Typography,Design
Color Theory,Design
Motion Design,Design
Design Thinking,Design
Product Design,Design
Content Design,Design
Accessibility Audits,Design
Product Management,Product & Business
Agile,Product & Business
Scrum,Product & Business
Kanban,Product & Business
Jira,Product & Business
Confluence,Product & Business
Notion,Product & Business
Roadmapping,Product & Business
Stakeholder Management,Product & Business
Market Research,Product & Business
Competitive Analysis,Product & Business
Business Analysis,Product & Business
Requirements Gathering,Product & Business
OKRs,Product & Business
KPIs,Product & Business
Product Analytics,Product & Business
Amplitude,Product & Business
Mixpanel,Product & Business
Google Analytics,Product & Business
Looker,Product & Business
Tableau,Product & Business
Power BI,Product & Business
Excel,Product & Business
Financial Modeling,Product & Business
Pricing Strategy,Product & Business
Go-to-Market,Product & Business
Growth Strategy,Product & Business
Customer Success,Product & Business
Salesforce,Product & Business
HubSpot,Product & Business
Pytest,Testing & Security
Jest,Testing & Security
Vitest,Testing & Security
Cypress,Testing & Security
Playwright,Testing & Security
Selenium,Testing & Security
JUnit,Testing & Security
Mocha,Testing & Security
Chai,Testing & Security
Testing Library,Testing & Security
Test Automation,Testing & Security
Unit Testing,Testing & Security
Integration Testing,Testing & Security
Load Testing,Testing & Security
k6,Testing & Security
JMeter,Testing & Security
Postman,Testing & Security
Insomnia,Testing & Security
OWASP,Testing & Security
Penetration Testing,Testing & Security
Threat Modeling,Testing & Security
Cryptography,Testing & Security
Identity Management,Testing & Security
Network Security,Testing & Security
SOC 2,Testing & Security
ISO 27001,Testing & Security
GDPR,Testing & Security
Security Auditing,Testing & Security
SonarQube,Testing & Security
SAST,Testing & Security
Communication,Professional
Leadership,Professional
Teamwork,Professional
Problem Solving,Professional
Critical Thinking,Professional
Project Management,Professional
Time Management,Professional
Mentoring,Professional
Technical Writing,Professional
Public Speaking,Professional
Negotiation,Professional
Conflict Resolution,Professional
Adaptability,Professional
Collaboration,Professional
Remote Collaboration,Professional
Presentation Skills,Professional
Documentation,Professional
Code Review,Professional
System Design,Professional
Algorithms,Professional
Data Structures,Professional
Object Oriented Programming,Professional
Functional Programming,Professional
Distributed Systems,Professional
Performance Optimization,Professional
Debugging,Professional
Research,Professional
Decision Making,Professional
Strategic Planning,Professional
Customer Empathy,Professional

````

## docker-compose.yml

````yaml
services:
  api:
    build: ./backend
    env_file: .env
    volumes:
      - model-cache:/home/app/.cache
    healthcheck:
      test: [CMD, python, -c, "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
  web:
    build: ./frontend
    ports: ["8080:80"]
    depends_on:
      api:
        condition: service_healthy
    healthcheck:
      test: [CMD, wget, -q, --spider, http://127.0.0.1/]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped
  dev-db:
    image: postgres:17-alpine
    profiles: [dev]
    environment:
      POSTGRES_USER: skillmatch
      POSTGRES_PASSWORD: localdev
      POSTGRES_DB: skillmatch
    volumes: ["dev-data:/var/lib/postgresql/data"]
    healthcheck:
      test: [CMD-SHELL, "pg_isready -U skillmatch"]
      interval: 5s
      retries: 10
volumes:
  model-cache:
  dev-data:

````

## docs/DESIGN_DECISIONS.md

````markdown
# Design decisions for a viva

1. **A workspace first, with a separate landing page.** The default screen demonstrates the product immediately. The public landing page explains the journey, while the dashboard supports repeat use.
2. **Quiet surfaces, focused accents.** Dark neutral cards reduce visual noise. Violet signals actions and skill intelligence; mint marks positive alignment. Color is reinforced by text and icons.
3. **Transparent scores.** A hybrid score combines meaning (65%) with explicit skill evidence (35%). The interface shows components and declares keyword-only fallback. A percentage is an alignment signal, not a probability of getting hired.
4. **A bounded skill dictionary.** spaCy PhraseMatcher makes extraction reproducible and explainable. Aliases improve practical recall without requiring a proprietary language model. This trades open-ended inference for auditability.
5. **Progressive visual enhancement.** CSS creates the base constellation; Three.js enhances it. Reduced-motion and low-power devices retain the same content without WebGL. GPU resources are released on navigation.
6. **Small reusable frontend modules.** TypeScript provides strict contracts, jQuery handles DOM/events/AJAX as required, and dynamic imports separate heavy visuals from the initial page.
7. **Access tokens in memory.** An HttpOnly cookie stores the rotating refresh token. Logout increments an account version to invalidate existing access tokens. Public registration cannot create an administrator.
8. **Managed database, minimal local pooling.** Neon’s pooler handles serverless connections. SQLAlchemy NullPool avoids holding additional idle connections in the API process. SQLite makes tests independent and fast.
9. **Ownership is enforced on the server.** Candidates cannot read others’ resumes; recruiters only manage their own jobs/applicants. UI visibility is a convenience, never the authorization boundary.
10. **Synthetic data is labeled.** The preview provides an immediate experience without inventing actual vacancies, user activity, or live AI results. Course charts explain the limitations of their generated dataset.
11. **Archive jobs; delete private resumes.** Job closure preserves application history. Resume deletion cascades related private records to avoid retaining stale personal material.
12. **Accessibility is part of implementation.** Semantic forms, focus rings, skip navigation, touch controls, named icons, responsive layouts, and reduced-motion handling are built into components rather than added as a separate mode.

````

## docs/RUN_GUIDE.md

````markdown
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

````

## docs/VERIFICATION.md

````markdown
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

````

## frontend/.dockerignore

````text
node_modules
dist
.env

````

## frontend/Dockerfile

````text
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

````

## frontend/e2e/live.spec.ts

````typescript
import { test, expect } from "@playwright/test";
import path from "node:path";

test("real candidate upload, matching, application and recruiter review", async ({
  page,
  request,
}) => {
  test.skip(
    !process.env.LIVE_API,
    "Requires the local API and artifacts/qa-resume.docx.",
  );
  const suffix = Date.now();
  const recruiterEmail = `recruiter${suffix}@example.com`;
  const candidateEmail = `candidate${suffix}@example.com`;
  const password = "skillmatch-test-password-2026";
  const response = await request.post("/api/v1/auth/register", {
    data: {
      name: "QA Recruiter",
      email: recruiterEmail,
      password,
      role: "recruiter",
    },
  });
  expect(response.status()).toBe(201);
  const recruiter = await response.json();
  const created = await request.post("/api/v1/jobs", {
    headers: { Authorization: `Bearer ${recruiter.access_token}` },
    data: {
      title: `QA Frontend Engineer ${suffix}`,
      company: "QA Studio",
      location: "Remote",
      employment_type: "Full-time",
      description:
        "Build accessible React and TypeScript applications with our collaborative team. We value clean CSS and thoughtful product design.",
      salary_min: 120000,
      salary_max: 160000,
      skills: ["React", "TypeScript", "CSS", "Docker"],
    },
  });
  expect(created.status()).toBe(201);
  const job = await created.json();
  await page.goto("/#/register");
  await page.getByLabel("Your name").fill("QA Candidate");
  await page.getByLabel("Email address").fill(candidateEmail);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create my account" }).click();
  await expect(
    page.getByRole("heading", { name: "Your next move, QA." }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Upload resume", exact: true })
    .first()
    .click();
  await page
    .locator("#resume-file")
    .setInputFiles(path.resolve("../artifacts/qa-resume.docx"));
  await page.getByRole("button", { name: "Analyze my resume" }).click();
  await expect(
    page.getByRole("heading", { name: "Your next move, QA." }),
  ).toBeVisible();
  await expect(page.locator(".resume-file")).toContainText("qa-resume.docx");
  await page.goto(`/#/jobs/${job.id}`);
  await page.getByRole("button", { name: "Analyze my match" }).click();
  await expect(
    page.getByRole("heading", { name: "You + QA Studio." }),
  ).toBeVisible();
  await expect(page.locator(".big-gauge")).toContainText("75");
  await page.getByRole("button", { name: "Take the next step" }).click();
  await expect(page.locator(".app-table")).toContainText(job.title);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page.getByLabel("Email address").fill(recruiterEmail);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Find your next great hire." }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Candidates", exact: true }).click();
  await expect(page.locator(".app-table")).toContainText("QA Candidate");
  await page.getByLabel("Application status").selectOption("Interview");
  await expect(page.getByRole("status").last()).toContainText(
    "Application status updated.",
  );
});

````

## frontend/e2e/workspace.spec.ts

````typescript
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("dashboard, filtering, bookmarking, match result and charts work", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Your next move, Alex." }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/dashboard-desktop.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: "Find jobs" }).click();
  await page
    .getByRole("textbox", { name: "Job title, company, or skill" })
    .fill("Linear");
  await page.getByRole("button", { name: "Find my next move" }).click();
  await expect(page.locator(".job-card")).toHaveCount(1);
  await page
    .getByRole("button", { name: "Save Senior Frontend Developer" })
    .click();
  await expect(
    page.getByRole("button", { name: "Save Senior Frontend Developer" }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await page.getByLabel("Saved jobs only").check();
  await expect(page.locator(".job-card")).toHaveCount(1);
  await page
    .getByRole("link", { name: "Senior Frontend Developer", exact: true })
    .click();
  await page.getByRole("button", { name: "Analyze my match" }).click();
  await expect(
    page.getByRole("heading", { name: "You + Linear." }),
  ).toBeVisible();
  await expect(page.locator("#radar-chart")).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/match-result.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: "Insights", exact: true }).click();
  await expect(page.locator("#activity-chart")).toBeVisible();
  await expect(page.locator("#demand-chart")).toBeVisible();
  expect(errors).toEqual([]);
});

test("mobile navigation and page boundaries", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Your next move, Alex." }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/dashboard-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("link", { name: "My resume", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Let your skills speak." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Analyze my resume" }).click();
  await expect(page.getByRole("alert")).toHaveText(
    "Choose a PDF or DOCX resume first.",
  );
  await page.goto("/#/register");
  await expect(
    page.getByRole("heading", { name: "Make your next move." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.goto("/#/missing-page");
  await expect(
    page.getByRole("heading", { name: "A little off the path." }),
  ).toBeVisible();
});

test("landing and dashboard accessibility", async ({ page }) => {
  const violations: unknown[] = [];
  for (const route of ["/#/dashboard", "/#/landing", "/#/login", "/#/upload"]) {
    await page.goto(route);
    await expect(page.locator("h1,h2").first()).toBeVisible();
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    violations.push(
      ...result.violations.map((v) => ({
        route,
        id: v.id,
        nodes: v.nodes.map((n) => n.target),
      })),
    );
  }
  await page.goto("/#/landing");
  await page.screenshot({
    path: "../docs/screenshots/landing-desktop.png",
    fullPage: true,
  });
  expect(violations).toEqual([]);
});

````

## frontend/index.html

````html
<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="theme-color" content="#0d0e14"><meta name="description" content="Find where your skills belong. Understand your strengths, close skill gaps, and discover your next career move with SkillMatch AI."><title>SkillMatch AI — Your next chapter starts here</title><link rel="icon" type="image/svg+xml" href="/favicon.svg"></head><body><a class="skip-link" href="#main-content">Skip to content</a><div id="app"></div><div id="toasts" aria-live="polite" aria-atomic="true"></div><script type="module" src="/src/main.ts"></script></body></html>

````

## frontend/nginx.conf

````text
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    client_max_body_size 6m;
    gzip on;
    gzip_min_length 1024;
    gzip_types text/css application/javascript application/json image/svg+xml;
    gzip_vary on;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    add_header X-Frame-Options DENY always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'" always;
    location /api/ {
        limit_req zone=api_limit burst=30 nodelay;
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 180s;
    }
    location = /docs {
        proxy_pass http://api:8000;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'" always;
        add_header X-Content-Type-Options nosniff always;
    }
    location /openapi.json { proxy_pass http://api:8000; }
    location /assets/ { expires 1y; add_header Cache-Control "public, immutable"; }
    location / { try_files $uri $uri/ /index.html; }
}

````

## frontend/package-lock.json

````json
{
  "name": "skillmatch-ai",
  "version": "1.0.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": {
      "name": "skillmatch-ai",
      "version": "1.0.0",
      "dependencies": {
        "@fontsource/dm-sans": "^5.2.5",
        "@fontsource/manrope": "^5.2.5",
        "@popperjs/core": "^2.11.8",
        "bootstrap": "^5.3.3",
        "chart.js": "^4.4.8",
        "gsap": "^3.12.7",
        "jquery": "^3.7.1",
        "lucide": "^0.468.0",
        "swagger-ui-dist": "^5.33.0",
        "three": "^0.174.0"
      },
      "devDependencies": {
        "@axe-core/playwright": "^4.13.0",
        "@playwright/test": "^1.63.0",
        "@types/jquery": "^3.5.32",
        "@types/three": "^0.174.0",
        "prettier": "^3.9.9",
        "typescript": "^5.7.3",
        "vite": "^6.2.0",
        "vitest": "^4.1.11"
      }
    },
    "node_modules/@axe-core/playwright": {
      "version": "4.13.0",
      "resolved": "https://registry.npmjs.org/@axe-core/playwright/-/playwright-4.13.0.tgz",
      "integrity": "sha512-6YLx+kxXu5GJceG4ozFg+33a2EMTdjYwWGloJ3sb9Kta5pp+ZNS53uxGVog5JetIY8s++P5UrtX+cri+u0VAVg==",
      "dev": true,
      "license": "MPL-2.0",
      "dependencies": {
        "axe-core": "~4.13.0"
      },
      "peerDependencies": {
        "playwright-core": ">= 1.0.0"
      }
    },
    "node_modules/@esbuild/aix-ppc64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/aix-ppc64/-/aix-ppc64-0.25.12.tgz",
      "integrity": "sha512-Hhmwd6CInZ3dwpuGTF8fJG6yoWmsToE+vYgD4nytZVxcu1ulHpUQRAB1UJ8+N1Am3Mz4+xOByoQoSZf4D+CpkA==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "aix"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/android-arm": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/android-arm/-/android-arm-0.25.12.tgz",
      "integrity": "sha512-VJ+sKvNA/GE7Ccacc9Cha7bpS8nyzVv0jdVgwNDaR4gDMC/2TTRc33Ip8qrNYUcpkOHUT5OZ0bUcNNVZQ9RLlg==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/android-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/android-arm64/-/android-arm64-0.25.12.tgz",
      "integrity": "sha512-6AAmLG7zwD1Z159jCKPvAxZd4y/VTO0VkprYy+3N2FtJ8+BQWFXU+OxARIwA46c5tdD9SsKGZ/1ocqBS/gAKHg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/android-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/android-x64/-/android-x64-0.25.12.tgz",
      "integrity": "sha512-5jbb+2hhDHx5phYR2By8GTWEzn6I9UqR11Kwf22iKbNpYrsmRB18aX/9ivc5cabcUiAT/wM+YIZ6SG9QO6a8kg==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/darwin-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/darwin-arm64/-/darwin-arm64-0.25.12.tgz",
      "integrity": "sha512-N3zl+lxHCifgIlcMUP5016ESkeQjLj/959RxxNYIthIg+CQHInujFuXeWbWMgnTo4cp5XVHqFPmpyu9J65C1Yg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/darwin-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/darwin-x64/-/darwin-x64-0.25.12.tgz",
      "integrity": "sha512-HQ9ka4Kx21qHXwtlTUVbKJOAnmG1ipXhdWTmNXiPzPfWKpXqASVcWdnf2bnL73wgjNrFXAa3yYvBSd9pzfEIpA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/freebsd-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/freebsd-arm64/-/freebsd-arm64-0.25.12.tgz",
      "integrity": "sha512-gA0Bx759+7Jve03K1S0vkOu5Lg/85dou3EseOGUes8flVOGxbhDDh/iZaoek11Y8mtyKPGF3vP8XhnkDEAmzeg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "freebsd"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/freebsd-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/freebsd-x64/-/freebsd-x64-0.25.12.tgz",
      "integrity": "sha512-TGbO26Yw2xsHzxtbVFGEXBFH0FRAP7gtcPE7P5yP7wGy7cXK2oO7RyOhL5NLiqTlBh47XhmIUXuGciXEqYFfBQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "freebsd"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-arm": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-arm/-/linux-arm-0.25.12.tgz",
      "integrity": "sha512-lPDGyC1JPDou8kGcywY0YILzWlhhnRjdof3UlcoqYmS9El818LLfJJc3PXXgZHrHCAKs/Z2SeZtDJr5MrkxtOw==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-arm64/-/linux-arm64-0.25.12.tgz",
      "integrity": "sha512-8bwX7a8FghIgrupcxb4aUmYDLp8pX06rGh5HqDT7bB+8Rdells6mHvrFHHW2JAOPZUbnjUpKTLg6ECyzvas2AQ==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-ia32": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-ia32/-/linux-ia32-0.25.12.tgz",
      "integrity": "sha512-0y9KrdVnbMM2/vG8KfU0byhUN+EFCny9+8g202gYqSSVMonbsCfLjUO+rCci7pM0WBEtz+oK/PIwHkzxkyharA==",
      "cpu": [
        "ia32"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-loong64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-loong64/-/linux-loong64-0.25.12.tgz",
      "integrity": "sha512-h///Lr5a9rib/v1GGqXVGzjL4TMvVTv+s1DPoxQdz7l/AYv6LDSxdIwzxkrPW438oUXiDtwM10o9PmwS/6Z0Ng==",
      "cpu": [
        "loong64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-mips64el": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-mips64el/-/linux-mips64el-0.25.12.tgz",
      "integrity": "sha512-iyRrM1Pzy9GFMDLsXn1iHUm18nhKnNMWscjmp4+hpafcZjrr2WbT//d20xaGljXDBYHqRcl8HnxbX6uaA/eGVw==",
      "cpu": [
        "mips64el"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-ppc64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-ppc64/-/linux-ppc64-0.25.12.tgz",
      "integrity": "sha512-9meM/lRXxMi5PSUqEXRCtVjEZBGwB7P/D4yT8UG/mwIdze2aV4Vo6U5gD3+RsoHXKkHCfSxZKzmDssVlRj1QQA==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-riscv64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-riscv64/-/linux-riscv64-0.25.12.tgz",
      "integrity": "sha512-Zr7KR4hgKUpWAwb1f3o5ygT04MzqVrGEGXGLnj15YQDJErYu/BGg+wmFlIDOdJp0PmB0lLvxFIOXZgFRrdjR0w==",
      "cpu": [
        "riscv64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-s390x": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-s390x/-/linux-s390x-0.25.12.tgz",
      "integrity": "sha512-MsKncOcgTNvdtiISc/jZs/Zf8d0cl/t3gYWX8J9ubBnVOwlk65UIEEvgBORTiljloIWnBzLs4qhzPkJcitIzIg==",
      "cpu": [
        "s390x"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-x64/-/linux-x64-0.25.12.tgz",
      "integrity": "sha512-uqZMTLr/zR/ed4jIGnwSLkaHmPjOjJvnm6TVVitAa08SLS9Z0VM8wIRx7gWbJB5/J54YuIMInDquWyYvQLZkgw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/netbsd-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/netbsd-arm64/-/netbsd-arm64-0.25.12.tgz",
      "integrity": "sha512-xXwcTq4GhRM7J9A8Gv5boanHhRa/Q9KLVmcyXHCTaM4wKfIpWkdXiMog/KsnxzJ0A1+nD+zoecuzqPmCRyBGjg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "netbsd"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/netbsd-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/netbsd-x64/-/netbsd-x64-0.25.12.tgz",
      "integrity": "sha512-Ld5pTlzPy3YwGec4OuHh1aCVCRvOXdH8DgRjfDy/oumVovmuSzWfnSJg+VtakB9Cm0gxNO9BzWkj6mtO1FMXkQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "netbsd"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/openbsd-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/openbsd-arm64/-/openbsd-arm64-0.25.12.tgz",
      "integrity": "sha512-fF96T6KsBo/pkQI950FARU9apGNTSlZGsv1jZBAlcLL1MLjLNIWPBkj5NlSz8aAzYKg+eNqknrUJ24QBybeR5A==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "openbsd"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/openbsd-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/openbsd-x64/-/openbsd-x64-0.25.12.tgz",
      "integrity": "sha512-MZyXUkZHjQxUvzK7rN8DJ3SRmrVrke8ZyRusHlP+kuwqTcfWLyqMOE3sScPPyeIXN/mDJIfGXvcMqCgYKekoQw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "openbsd"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/openharmony-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/openharmony-arm64/-/openharmony-arm64-0.25.12.tgz",
      "integrity": "sha512-rm0YWsqUSRrjncSXGA7Zv78Nbnw4XL6/dzr20cyrQf7ZmRcsovpcRBdhD43Nuk3y7XIoW2OxMVvwuRvk9XdASg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "openharmony"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/sunos-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/sunos-x64/-/sunos-x64-0.25.12.tgz",
      "integrity": "sha512-3wGSCDyuTHQUzt0nV7bocDy72r2lI33QL3gkDNGkod22EsYl04sMf0qLb8luNKTOmgF/eDEDP5BFNwoBKH441w==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "sunos"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/win32-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/win32-arm64/-/win32-arm64-0.25.12.tgz",
      "integrity": "sha512-rMmLrur64A7+DKlnSuwqUdRKyd3UE7oPJZmnljqEptesKM8wx9J8gx5u0+9Pq0fQQW8vqeKebwNXdfOyP+8Bsg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/win32-ia32": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/win32-ia32/-/win32-ia32-0.25.12.tgz",
      "integrity": "sha512-HkqnmmBoCbCwxUKKNPBixiWDGCpQGVsrQfJoVGYLPT41XWF8lHuE5N6WhVia2n4o5QK5M4tYr21827fNhi4byQ==",
      "cpu": [
        "ia32"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/win32-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/win32-x64/-/win32-x64-0.25.12.tgz",
      "integrity": "sha512-alJC0uCZpTFrSL0CCDjcgleBXPnCrEAhTBILpeAp7M/OFgoqtAetfBzX0xM00MUsVVPpVjlPuMbREqnZCXaTnA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@fontsource/dm-sans": {
      "version": "5.3.0",
      "resolved": "https://registry.npmjs.org/@fontsource/dm-sans/-/dm-sans-5.3.0.tgz",
      "integrity": "sha512-lYJtMXXO28q1z+yz+z8XKd0s4hXaa9QdkETzkyD760sidCv5heI86weYA0sx0Nc4pAMAQTUuyf4gO44cYKKS9g==",
      "license": "OFL-1.1",
      "funding": {
        "url": "https://github.com/sponsors/ayuhito"
      }
    },
    "node_modules/@fontsource/manrope": {
      "version": "5.3.0",
      "resolved": "https://registry.npmjs.org/@fontsource/manrope/-/manrope-5.3.0.tgz",
      "integrity": "sha512-obJ1Dv3+uCA6HlHgW8u4BGYxJR9In2HW7gjJhlflEvkrj1X1iSEwu0fToL+JYGC/FEKFfIz1sBuPduvcL2gIAA==",
      "license": "OFL-1.1",
      "funding": {
        "url": "https://github.com/sponsors/ayuhito"
      }
    },
    "node_modules/@jridgewell/sourcemap-codec": {
      "version": "1.6.0",
      "resolved": "https://registry.npmjs.org/@jridgewell/sourcemap-codec/-/sourcemap-codec-1.6.0.tgz",
      "integrity": "sha512-T7jf+5zgsZHwNJ4lvQ7/aezbyk0nNX+zJVWpmHA7VYsEx7a7qr5Rg5IbtJFqkgze5Y2sruq1RUY8Q837Od7iFw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@kurkle/color": {
      "version": "0.3.4",
      "resolved": "https://registry.npmjs.org/@kurkle/color/-/color-0.3.4.tgz",
      "integrity": "sha512-M5UknZPHRu3DEDWoipU6sE8PdkZ6Z/S+v4dD+Ke8IaNlpdSQah50lz1KtcFBa2vsdOnwbbnxJwVM4wty6udA5w==",
      "license": "MIT"
    },
    "node_modules/@napi-rs/lzma-linux-x64-gnu": {
      "version": "1.5.1",
      "resolved": "https://registry.npmjs.org/@napi-rs/lzma-linux-x64-gnu/-/lzma-linux-x64-gnu-1.5.1.tgz",
      "integrity": "sha512-oTXEIha4SsuXdTA4Iyskj0kpdx2yVXdhd75c2v3xGrHFfVMsbhTPZU/nMPL4sWKo4pBHm3aucLaqGlF696dTyQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": "^22.20 || ^24.12 || >=25"
      }
    },
    "node_modules/@playwright/test": {
      "version": "1.63.0",
      "resolved": "https://registry.npmjs.org/@playwright/test/-/test-1.63.0.tgz",
      "integrity": "sha512-oxMK4vllB9RK5NQ2l1pq1IfOf2AvnEuj/vYGDj0H2nMtmtZpKtCwt/l00GEO6xjGfpBNAvjovvYdCm50dRQkpQ==",
      "dev": true,
      "license": "Apache-2.0",
      "dependencies": {
        "playwright": "1.63.0"
      },
      "bin": {
        "playwright": "cli.js"
      },
      "engines": {
        "node": ">=20"
      }
    },
    "node_modules/@popperjs/core": {
      "version": "2.11.8",
      "resolved": "https://registry.npmjs.org/@popperjs/core/-/core-2.11.8.tgz",
      "integrity": "sha512-P1st0aksCrn9sGZhp8GMYwBnQsbvAWsZAX44oXNNvLHGqAOcoVxmjZiohstwQ7SqKnbR47akdNi+uleWD8+g6A==",
      "license": "MIT",
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/popperjs"
      }
    },
    "node_modules/@rollup/rollup-android-arm-eabi": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-android-arm-eabi/-/rollup-android-arm-eabi-4.63.5.tgz",
      "integrity": "sha512-J25QJU+B78T4FhhBsNpLJyVWOi31mwtpcMwywHmOKH65Q9IWGA81gPj+dnwlhU8wktVriYE+tFAaQgrnJRzAZg==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ]
    },
    "node_modules/@rollup/rollup-android-arm64": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-android-arm64/-/rollup-android-arm64-4.63.5.tgz",
      "integrity": "sha512-LDopB3zuZM5Ux9TT2luNEBJW/tYbGU2g1d+VpKk6I+gSKDb+/7sYE6M225gRQt4RbMX6MSwMsVR/phdjVUgRLg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ]
    },
    "node_modules/@rollup/rollup-darwin-arm64": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-darwin-arm64/-/rollup-darwin-arm64-4.63.5.tgz",
      "integrity": "sha512-wlJEERGfeuHeBavCL2qVnNacOK43NDoZM4sjkeRPymd04OAE9T1zBqDJgmZ+CIsPTYKwdzpUC8vmOw84dwY4Tg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ]
    },
    "node_modules/@rollup/rollup-darwin-x64": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-darwin-x64/-/rollup-darwin-x64-4.63.5.tgz",
      "integrity": "sha512-4nJJGg5jbo2wwPP4JP+LfEBA3bvP8rU9CLuhp7jWvq9sxEyhjQFTFdrqi+/dHEin/pd8jpT0vcehIpnZtmEdcQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ]
    },
    "node_modules/@rollup/rollup-freebsd-arm64": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-freebsd-arm64/-/rollup-freebsd-arm64-4.63.5.tgz",
      "integrity": "sha512-DrZbyCDF1hneuO6jRbvZ2D7+PIBM6yIwYnJpg2vIk58T+wuFpiaGZrfUr59lDWw45bg+IrpTGLPiNi/Fk4w3Cg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "freebsd"
      ]
    },
    "node_modules/@rollup/rollup-freebsd-x64": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-freebsd-x64/-/rollup-freebsd-x64-4.63.5.tgz",
      "integrity": "sha512-gqfUVMJMB3mehqywxp6hTBFfgtMQykZY19+cfiaYP0toIJLb/1DZRJHVkQQGP13W4TAwfZDWeg1qBcheTRioXQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "freebsd"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm-gnueabihf": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm-gnueabihf/-/rollup-linux-arm-gnueabihf-4.63.5.tgz",
      "integrity": "sha512-CFmhpvAwzSaWMlN3VN7UtmoTihlZNzoP0juQib5TQRnYUyDV8dXeWOp29sobWAT6gXl/hQgAClLlEiYozQG3OQ==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm-musleabihf": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm-musleabihf/-/rollup-linux-arm-musleabihf-4.63.5.tgz",
      "integrity": "sha512-Uc9H8eXCOayV6JLTH5bXKMId6qbhNHa818/BgYjm4jrlq3vZquC9cqyvHBw17xy5Mnj5f+I3gFK5JcEf3hSqrw==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm64-gnu": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm64-gnu/-/rollup-linux-arm64-gnu-4.63.5.tgz",
      "integrity": "sha512-VcPr/szv/1BFw112Kt//fxulXt/JPqzzidU84iW68L2DdjnOO8QFUv2zTSYBEPHD6movBD4z+bbr5y60GYM7Jw==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm64-musl": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm64-musl/-/rollup-linux-arm64-musl-4.63.5.tgz",
      "integrity": "sha512-BnxtJ5/91BrIHYIkGrmjz/lbMhqEHt1dPFqIxIFR+jPn0xVc/oUSCtIT089zfp5ufwGDlYz2UC+Fe1SRBpYFbQ==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-loong64-gnu": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-loong64-gnu/-/rollup-linux-loong64-gnu-4.63.5.tgz",
      "integrity": "sha512-LrYcHZwF+fAMNKHYTOQ5osWM4AZF7YF6D+XtsjDyEvljtt11twc+zHVXBLNEjxVSUnKYsOhvVz4Z213eW02COQ==",
      "cpu": [
        "loong64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-loong64-musl": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-loong64-musl/-/rollup-linux-loong64-musl-4.63.5.tgz",
      "integrity": "sha512-nj7QKQePAAUpCpJHtg0pR0W/b92A9NO17JS3BAQmHDn/yhmkir2p8llrKY9TOhleKIaSzy1JhxS3T9FVld6coA==",
      "cpu": [
        "loong64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-ppc64-gnu": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-ppc64-gnu/-/rollup-linux-ppc64-gnu-4.63.5.tgz",
      "integrity": "sha512-5ylkX6dWMeBKge9nTU+Rxfb+ZfaCIJ9lRqIFaK0eAMcWp7OJbYnLveLgXmm0VrvuLKb8qIK+mHyH0qu88RM+iA==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-ppc64-musl": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-ppc64-musl/-/rollup-linux-ppc64-musl-4.63.5.tgz",
      "integrity": "sha512-oHK4ZHYFDKjZviK34I+NwgfbGxgI7ztrNxj2hPTSSNFgeq1a/lEd7dHV2fdGAuTH4Iym3RHJg+vAbWaWG4B7Zg==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-riscv64-gnu": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-riscv64-gnu/-/rollup-linux-riscv64-gnu-4.63.5.tgz",
      "integrity": "sha512-UcetmHZ6XOXuUByiKZyQmb55ZPr0LABr3Ec/HB9wKZn6CEAFWZkE+hsJErJ9hbPBC7nI0dKuELx7CoV6IM7TMg==",
      "cpu": [
        "riscv64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-riscv64-musl": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-riscv64-musl/-/rollup-linux-riscv64-musl-4.63.5.tgz",
      "integrity": "sha512-C5CmDPQBtvjVo8cgQsBs+w6WB0JLkiixhgi6hVLV11hERWdn/p0XcPU2OUcZzac9BPOFq7SbaHFa8r3SWEysCQ==",
      "cpu": [
        "riscv64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-s390x-gnu": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-s390x-gnu/-/rollup-linux-s390x-gnu-4.63.5.tgz",
      "integrity": "sha512-lHVQHJFKsuuxLMi3MQO9XVL8Tje3JR82CzB+QDKC5NWBcsIWuwsn9uIM5e3lBhI+fF1/s63qnyYqsg65+8rV/w==",
      "cpu": [
        "s390x"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-x64-gnu": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-x64-gnu/-/rollup-linux-x64-gnu-4.63.5.tgz",
      "integrity": "sha512-3W9bTFcQNJn71cSJVM9RKIiZOy8DO/XLDii8Uv/Pm6WKqDRj7JV3ZfuXIEfyuy5LXpIzAbB/1M4Ukp9GKNa7nA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-x64-musl": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-x64-musl/-/rollup-linux-x64-musl-4.63.5.tgz",
      "integrity": "sha512-VDC7rRJlee/scpki96GZ27Omf6yU87s1YXwVTpjE5841faVlDYYT565rgfmoR1U0sqL7z5ivQSDjcsF6VRXyBA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-openbsd-x64": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-openbsd-x64/-/rollup-openbsd-x64-4.63.5.tgz",
      "integrity": "sha512-z86Ok2p4pTdv5xqCKZsTooO7yBEiaJR/HzU3Wx8RmWsPoLppnMKROhJusQob8B3IE1ghC343kUW9rC2r+Wf3ig==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "openbsd"
      ]
    },
    "node_modules/@rollup/rollup-openharmony-arm64": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-openharmony-arm64/-/rollup-openharmony-arm64-4.63.5.tgz",
      "integrity": "sha512-IzQmj+xXwQFGhMAMKMQVXkMwMZN3TqkJgAE0nSsqvVwWWciP4AIPMmWRqOQ2GfX7TUDZr+xqGFcBS36CRPGw0g==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "openharmony"
      ]
    },
    "node_modules/@rollup/rollup-win32-arm64-msvc": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-arm64-msvc/-/rollup-win32-arm64-msvc-4.63.5.tgz",
      "integrity": "sha512-F6qpTaPc9bwBH85kjy0/BLmLSW1uv7AoOXCoRIkg2arlgCYlWYcAbiMkvZuAcaWk9TpCRG//okznLAqLGshkMw==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@rollup/rollup-win32-ia32-msvc": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-ia32-msvc/-/rollup-win32-ia32-msvc-4.63.5.tgz",
      "integrity": "sha512-igoDsTFhhwECBeGbUuLeIk7t8Y1apa+cs6mDWpx2EZ0ch7oEQgzHbFUXN9euoHekCAQzXdXApAGkV6jznS7tWw==",
      "cpu": [
        "ia32"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@rollup/rollup-win32-x64-gnu": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-x64-gnu/-/rollup-win32-x64-gnu-4.63.5.tgz",
      "integrity": "sha512-U3teMeMbXFmaM5D+OTJpsOXd+wV/qftIeYF9kBKL4v73641qyJmoXFtA28DQLsnmlyayEsTe72xpLHrArq6vHw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@rollup/rollup-win32-x64-msvc": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-x64-msvc/-/rollup-win32-x64-msvc-4.63.5.tgz",
      "integrity": "sha512-ypfC34F3RKXvCXBglGqGMsUSMKlgwd1HX9AOAlx9RoZZ6GaI42YHVeKpzg3JG+wpBUJYTG+NNZhqbDWL8tBZkw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@scarf/scarf": {
      "version": "1.4.0",
      "resolved": "https://registry.npmjs.org/@scarf/scarf/-/scarf-1.4.0.tgz",
      "integrity": "sha512-xxeapPiUXdZAE3che6f3xogoJPeZgig6omHEy1rIY5WVsB3H2BHNnZH+gHG6x91SCWyQCzWGsuL2Hh3ClO5/qQ==",
      "hasInstallScript": true,
      "license": "Apache-2.0"
    },
    "node_modules/@standard-schema/spec": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/@standard-schema/spec/-/spec-1.1.0.tgz",
      "integrity": "sha512-l2aFy5jALhniG5HgqrD6jXLi/rUWrKvqN/qJx6yoJsgKhblVd+iqqU4RCXavm/jPityDo5TCvKMnpjKnOriy0w==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@tweenjs/tween.js": {
      "version": "23.1.3",
      "resolved": "https://registry.npmjs.org/@tweenjs/tween.js/-/tween.js-23.1.3.tgz",
      "integrity": "sha512-vJmvvwFxYuGnF2axRtPYocag6Clbb5YS7kLL+SO/TeVFzHqDIWrNKYtcsPMibjDx9O+bu+psAy9NKfWklassUA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/chai": {
      "version": "5.2.3",
      "resolved": "https://registry.npmjs.org/@types/chai/-/chai-5.2.3.tgz",
      "integrity": "sha512-Mw558oeA9fFbv65/y4mHtXDs9bPnFMZAL/jxdPFUpOHHIXX91mcgEHbS5Lahr+pwZFR8A7GQleRWeI6cGFC2UA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@types/deep-eql": "*",
        "assertion-error": "^2.0.1"
      }
    },
    "node_modules/@types/deep-eql": {
      "version": "4.0.2",
      "resolved": "https://registry.npmjs.org/@types/deep-eql/-/deep-eql-4.0.2.tgz",
      "integrity": "sha512-c9h9dVVMigMPc4bwTvC5dxqtqJZwQPePsWjPlpSOnojbor6pGqdk541lfA7AqFQr5pB1BRdq0juY9db81BwyFw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/estree": {
      "version": "1.0.9",
      "resolved": "https://registry.npmjs.org/@types/estree/-/estree-1.0.9.tgz",
      "integrity": "sha512-GhdPgy1el4/ImP05X05Uw4cw2/M93BCUmnEvWZNStlCzEKME4Fkk+YpoA5OiHNQmoS7Cafb8Xa3Pya8m1Qrzeg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/jquery": {
      "version": "3.5.34",
      "resolved": "https://registry.npmjs.org/@types/jquery/-/jquery-3.5.34.tgz",
      "integrity": "sha512-3m3939S3erqmTLJANS/uy0B6V7BorKx7RorcGZVjZ62dF5PAGbKEDZK1CuLtKombJkFA2T1jl8LAIIs7IV6gBQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@types/sizzle": "*"
      }
    },
    "node_modules/@types/sizzle": {
      "version": "2.3.10",
      "resolved": "https://registry.npmjs.org/@types/sizzle/-/sizzle-2.3.10.tgz",
      "integrity": "sha512-TC0dmN0K8YcWEAEfiPi5gJP14eJe30TTGjkvek3iM/1NdHHsdCA/Td6GvNndMOo/iSnIsZ4HuuhrYPDAmbxzww==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/stats.js": {
      "version": "0.17.4",
      "resolved": "https://registry.npmjs.org/@types/stats.js/-/stats.js-0.17.4.tgz",
      "integrity": "sha512-jIBvWWShCvlBqBNIZt0KAshWpvSjhkwkEu4ZUcASoAvhmrgAUI2t1dXrjSL4xXVLB4FznPrIsX3nKXFl/Dt4vA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/three": {
      "version": "0.174.0",
      "resolved": "https://registry.npmjs.org/@types/three/-/three-0.174.0.tgz",
      "integrity": "sha512-De/+vZnfg2aVWNiuy1Ldu+n2ydgw1osinmiZTAn0necE++eOfsygL8JpZgFjR2uHmAPo89MkxBj3JJ+2BMe+Uw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@tweenjs/tween.js": "~23.1.3",
        "@types/stats.js": "*",
        "@types/webxr": "*",
        "@webgpu/types": "*",
        "fflate": "~0.8.2",
        "meshoptimizer": "~0.18.1"
      }
    },
    "node_modules/@types/webxr": {
      "version": "0.5.24",
      "resolved": "https://registry.npmjs.org/@types/webxr/-/webxr-0.5.24.tgz",
      "integrity": "sha512-h8fgEd/DpoS9CBrjEQXR+dIDraopAEfu4wYVNY2tEPwk60stPWhvZMf4Foo5FakuQ7HFZoa8WceaWFervK2Ovg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@vitest/expect": {
      "version": "4.1.11",
      "resolved": "https://registry.npmjs.org/@vitest/expect/-/expect-4.1.11.tgz",
      "integrity": "sha512-VX2x5vNJXET47KAFzwERI+KRMtTTCSWTfSMKsW7JsUsXV4psq++e3DvZpuTDOpHcxytiDs6p2nhVb2tVDiiUYw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@standard-schema/spec": "^1.1.0",
        "@types/chai": "^5.2.2",
        "@vitest/spy": "4.1.11",
        "@vitest/utils": "4.1.11",
        "chai": "^6.2.2",
        "tinyrainbow": "^3.1.0"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/mocker": {
      "version": "4.1.11",
      "resolved": "https://registry.npmjs.org/@vitest/mocker/-/mocker-4.1.11.tgz",
      "integrity": "sha512-2XJVD55d1o5AZous5CCGKS74g/riOj9odEt2bQpCVZeblHyHdnMeFl4jl0XjU21stf4mbjUkew2eXQZt65g5CQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@vitest/spy": "4.1.11",
        "estree-walker": "^3.0.3",
        "magic-string": "^0.30.21"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      },
      "peerDependencies": {
        "msw": "^2.4.9",
        "vite": "^6.0.0 || ^7.0.0 || ^8.0.0"
      },
      "peerDependenciesMeta": {
        "msw": {
          "optional": true
        },
        "vite": {
          "optional": true
        }
      }
    },
    "node_modules/@vitest/pretty-format": {
      "version": "4.1.11",
      "resolved": "https://registry.npmjs.org/@vitest/pretty-format/-/pretty-format-4.1.11.tgz",
      "integrity": "sha512-yiZzPbGTS9Sr/JpFl8zHrcIkAofNbFV6k21vIgQN/cY/oxZeXhJv5sc/MBJ5jFKWmWs+oJHw0UXLZjmf931+Vw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "tinyrainbow": "^3.1.0"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/runner": {
      "version": "4.1.11",
      "resolved": "https://registry.npmjs.org/@vitest/runner/-/runner-4.1.11.tgz",
      "integrity": "sha512-LztvUgdwMNJMIkj3hQnnxiC2Xy1zNxq928W/xhjCLaNCzqTZOudjwbQf6v9IntZGPw132i2Lq2rgTRZHD3JHNw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@vitest/utils": "4.1.11",
        "pathe": "^2.0.3"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/snapshot": {
      "version": "4.1.11",
      "resolved": "https://registry.npmjs.org/@vitest/snapshot/-/snapshot-4.1.11.tgz",
      "integrity": "sha512-pN7ikn1ON7h8ee4gIAp4AzyK+zBtJPzVbqOgu5LCEh4VaJVbPQcgYQYJIMGQPXVeJJq1fnfazis7a5pFNPahog==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@vitest/pretty-format": "4.1.11",
        "@vitest/utils": "4.1.11",
        "magic-string": "^0.30.21",
        "pathe": "^2.0.3"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/spy": {
      "version": "4.1.11",
      "resolved": "https://registry.npmjs.org/@vitest/spy/-/spy-4.1.11.tgz",
      "integrity": "sha512-apNa/prQy2qCeywhnixOHPRCgGNhvg7T4Dapfl1GahLp/R+uhBm5cPyFoNVyqsNd2h1nJxL6BqqdIjiABL60YA==",
      "dev": true,
      "license": "MIT",
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/utils": {
      "version": "4.1.11",
      "resolved": "https://registry.npmjs.org/@vitest/utils/-/utils-4.1.11.tgz",
      "integrity": "sha512-zTCVGpyFsGWBhllOyKlTw/vnr6D9qxsfSDyfbyZmTyjHw5N/VuvzHpHoQjm2ZJzn4RJgx5w4r7V0er69CmLgPQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@vitest/pretty-format": "4.1.11",
        "convert-source-map": "^2.0.0",
        "tinyrainbow": "^3.1.0"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@webgpu/types": {
      "version": "0.1.74",
      "resolved": "https://registry.npmjs.org/@webgpu/types/-/types-0.1.74.tgz",
      "integrity": "sha512-lgiI4hbuLcI9unnm2cL/tvCaQU45dp0xcLWJh5uB/9MBGvIA4F8XIk7nSiBeg+K4xWGYwgZKn80LmERI5CxoTA==",
      "dev": true,
      "license": "BSD-3-Clause"
    },
    "node_modules/assertion-error": {
      "version": "2.0.1",
      "resolved": "https://registry.npmjs.org/assertion-error/-/assertion-error-2.0.1.tgz",
      "integrity": "sha512-Izi8RQcffqCeNVgFigKli1ssklIbpHnCYc6AknXGYoB6grJqyeby7jv12JUQgmTAnIDnbck1uxksT4dzN3PWBA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/axe-core": {
      "version": "4.13.0",
      "resolved": "https://registry.npmjs.org/axe-core/-/axe-core-4.13.0.tgz",
      "integrity": "sha512-UzGt8zg7Ny8djbYMhxl2zuEevVa7r2gJjYY5Lwr1xM7+XU2nd6CkIWFTVcCIbAP63vSz71NaVyyuSk9lHKcy0A==",
      "dev": true,
      "license": "MPL-2.0",
      "engines": {
        "node": ">=4"
      }
    },
    "node_modules/bootstrap": {
      "version": "5.3.8",
      "resolved": "https://registry.npmjs.org/bootstrap/-/bootstrap-5.3.8.tgz",
      "integrity": "sha512-HP1SZDqaLDPwsNiqRqi5NcP0SSXciX2s9E+RyqJIIqGo+vJeN5AJVM98CXmW/Wux0nQ5L7jeWUdplCEf0Ee+tg==",
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/twbs"
        },
        {
          "type": "opencollective",
          "url": "https://opencollective.com/bootstrap"
        }
      ],
      "license": "MIT",
      "peerDependencies": {
        "@popperjs/core": "^2.11.8"
      }
    },
    "node_modules/chai": {
      "version": "6.2.2",
      "resolved": "https://registry.npmjs.org/chai/-/chai-6.2.2.tgz",
      "integrity": "sha512-NUPRluOfOiTKBKvWPtSD4PhFvWCqOi0BGStNWs57X9js7XGTprSmFoz5F0tWhR4WPjNeR9jXqdC7/UpSJTnlRg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/chart.js": {
      "version": "4.5.1",
      "resolved": "https://registry.npmjs.org/chart.js/-/chart.js-4.5.1.tgz",
      "integrity": "sha512-GIjfiT9dbmHRiYi6Nl2yFCq7kkwdkp1W/lp2J99rX0yo9tgJGn3lKQATztIjb5tVtevcBtIdICNWqlq5+E8/Pw==",
      "license": "MIT",
      "dependencies": {
        "@kurkle/color": "^0.3.0"
      },
      "engines": {
        "pnpm": ">=8"
      }
    },
    "node_modules/convert-source-map": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/convert-source-map/-/convert-source-map-2.0.0.tgz",
      "integrity": "sha512-Kvp459HrV2FEJ1CAsi1Ku+MY3kasH19TFykTz2xWmMeq6bk2NU3XXvfJ+Q61m0xktWwt+1HSYf3JZsTms3aRJg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/es-module-lexer": {
      "version": "2.3.2",
      "resolved": "https://registry.npmjs.org/es-module-lexer/-/es-module-lexer-2.3.2.tgz",
      "integrity": "sha512-poHGpORABojJJucnV9KbOavETW8lBVnphkW77ER5/BQ5Fz7oXSoCNek7IH3vR5nRjdsEz926ibFYX8KtLQmdyw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/esbuild": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/esbuild/-/esbuild-0.25.12.tgz",
      "integrity": "sha512-bbPBYYrtZbkt6Os6FiTLCTFxvq4tt3JKall1vRwshA3fdVztsLAatFaZobhkBC8/BrPetoa0oksYoKXoG4ryJg==",
      "dev": true,
      "hasInstallScript": true,
      "license": "MIT",
      "bin": {
        "esbuild": "bin/esbuild"
      },
      "engines": {
        "node": ">=18"
      },
      "optionalDependencies": {
        "@esbuild/aix-ppc64": "0.25.12",
        "@esbuild/android-arm": "0.25.12",
        "@esbuild/android-arm64": "0.25.12",
        "@esbuild/android-x64": "0.25.12",
        "@esbuild/darwin-arm64": "0.25.12",
        "@esbuild/darwin-x64": "0.25.12",
        "@esbuild/freebsd-arm64": "0.25.12",
        "@esbuild/freebsd-x64": "0.25.12",
        "@esbuild/linux-arm": "0.25.12",
        "@esbuild/linux-arm64": "0.25.12",
        "@esbuild/linux-ia32": "0.25.12",
        "@esbuild/linux-loong64": "0.25.12",
        "@esbuild/linux-mips64el": "0.25.12",
        "@esbuild/linux-ppc64": "0.25.12",
        "@esbuild/linux-riscv64": "0.25.12",
        "@esbuild/linux-s390x": "0.25.12",
        "@esbuild/linux-x64": "0.25.12",
        "@esbuild/netbsd-arm64": "0.25.12",
        "@esbuild/netbsd-x64": "0.25.12",
        "@esbuild/openbsd-arm64": "0.25.12",
        "@esbuild/openbsd-x64": "0.25.12",
        "@esbuild/openharmony-arm64": "0.25.12",
        "@esbuild/sunos-x64": "0.25.12",
        "@esbuild/win32-arm64": "0.25.12",
        "@esbuild/win32-ia32": "0.25.12",
        "@esbuild/win32-x64": "0.25.12"
      }
    },
    "node_modules/estree-walker": {
      "version": "3.0.3",
      "resolved": "https://registry.npmjs.org/estree-walker/-/estree-walker-3.0.3.tgz",
      "integrity": "sha512-7RUKfXgSMMkzt6ZuXmqapOurLGPPfgj6l9uRZ7lRGolvk0y2yocc35LdcxKC5PQZdn2DMqioAQ2NoWcrTKmm6g==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@types/estree": "^1.0.0"
      }
    },
    "node_modules/expect-type": {
      "version": "1.4.0",
      "resolved": "https://registry.npmjs.org/expect-type/-/expect-type-1.4.0.tgz",
      "integrity": "sha512-KfYbmpRm0VbLjEvVa9yGwCi9GI34xvi7A/HXYWQO65CSD2u3MczUJSuwXKFIxlGsgBQizV9q5J9NHj4VG0n+pA==",
      "dev": true,
      "license": "Apache-2.0",
      "engines": {
        "node": ">=12.0.0"
      }
    },
    "node_modules/fdir": {
      "version": "6.5.0",
      "resolved": "https://registry.npmjs.org/fdir/-/fdir-6.5.0.tgz",
      "integrity": "sha512-tIbYtZbucOs0BRGqPJkshJUYdL+SDH7dVM8gjy+ERp3WAUjLEFJE+02kanyHtwjWOnwrKYBiwAmM0p4kLJAnXg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=12.0.0"
      },
      "peerDependencies": {
        "picomatch": "^3 || ^4"
      },
      "peerDependenciesMeta": {
        "picomatch": {
          "optional": true
        }
      }
    },
    "node_modules/fflate": {
      "version": "0.8.3",
      "resolved": "https://registry.npmjs.org/fflate/-/fflate-0.8.3.tgz",
      "integrity": "sha512-tbZNuJrLwGUp3zshBtdy4W+ORxZuIh8a5ilyIEQDC5rY1f3U20JMry0Ll3WBzU58EZKsEuJFXhb5gwv8CsPvgA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/fsevents": {
      "version": "2.3.3",
      "resolved": "https://registry.npmjs.org/fsevents/-/fsevents-2.3.3.tgz",
      "integrity": "sha512-5xoDfX+fL7faATnagmWPpbFtwh/R77WmMMqqHGS65C3vvB0YHrgF+B1YmZ3441tMj5n63k0212XNoJwzlhffQw==",
      "dev": true,
      "hasInstallScript": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": "^8.16.0 || ^10.6.0 || >=11.0.0"
      }
    },
    "node_modules/gsap": {
      "version": "3.15.0",
      "resolved": "https://registry.npmjs.org/gsap/-/gsap-3.15.0.tgz",
      "integrity": "sha512-dMW4CWBTUK1AEEDeZc1g4xpPGIrSf9fJF960qbTZmN/QwZIWY5wgliS6JWl9/25fpTGJrMRtSjGtOmPnfjZB+A==",
      "license": "Standard 'no charge' license: https://gsap.com/standard-license."
    },
    "node_modules/jquery": {
      "version": "3.7.1",
      "resolved": "https://registry.npmjs.org/jquery/-/jquery-3.7.1.tgz",
      "integrity": "sha512-m4avr8yL8kmFN8psrbFFFmB/If14iN5o9nw/NgnnM+kybDJpRsAynV2BsfpTYrTRysYUdADVD7CkUUizgkpLfg==",
      "license": "MIT"
    },
    "node_modules/lucide": {
      "version": "0.468.0",
      "resolved": "https://registry.npmjs.org/lucide/-/lucide-0.468.0.tgz",
      "integrity": "sha512-UFbgwji/ZnAV7iTTE4jujyTV7J95AILKyATDUrqOJrMcUGfXvGjw3c1mcuHZUX2oJfkrAGU9KoxkrLQk2jjtiA==",
      "license": "ISC"
    },
    "node_modules/magic-string": {
      "version": "0.30.21",
      "resolved": "https://registry.npmjs.org/magic-string/-/magic-string-0.30.21.tgz",
      "integrity": "sha512-vd2F4YUyEXKGcLHoq+TEyCjxueSeHnFxyyjNp80yg0XV4vUhnDer/lvvlqM/arB5bXQN5K2/3oinyCRyx8T2CQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/sourcemap-codec": "^1.5.5"
      }
    },
    "node_modules/meshoptimizer": {
      "version": "0.18.1",
      "resolved": "https://registry.npmjs.org/meshoptimizer/-/meshoptimizer-0.18.1.tgz",
      "integrity": "sha512-ZhoIoL7TNV4s5B6+rx5mC//fw8/POGyNxS/DZyCJeiZ12ScLfVwRE/GfsxwiTkMYYD5DmK2/JXnEVXqL4rF+Sw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/nanoid": {
      "version": "3.3.19",
      "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-3.3.19.tgz",
      "integrity": "sha512-Y2tUNy4ouw6tq5oDSKeQYGOyhkUBhNOcGV/02KC+6kd9eDGqdZd++mjMiIDilrBYvjEnCYvVtsuHCuP+okSfug==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "bin": {
        "nanoid": "bin/nanoid.cjs"
      },
      "engines": {
        "node": "^10 || ^12 || ^13.7 || ^14 || >=15.0.1"
      }
    },
    "node_modules/obug": {
      "version": "2.2.1",
      "resolved": "https://registry.npmjs.org/obug/-/obug-2.2.1.tgz",
      "integrity": "sha512-XrsrhT5sybtKI6wakr2SPOlGZWWYbUXZ7a0jT8/QOeAPau+1X/bSegNe5YR75oJmEZQbKningirmGOEJCIk61Q==",
      "dev": true,
      "funding": [
        "https://github.com/sponsors/sxzz",
        "https://opencollective.com/debug"
      ],
      "license": "MIT",
      "engines": {
        "node": ">=12.20.0"
      }
    },
    "node_modules/pathe": {
      "version": "2.0.3",
      "resolved": "https://registry.npmjs.org/pathe/-/pathe-2.0.3.tgz",
      "integrity": "sha512-WUjGcAqP1gQacoQe+OBJsFA7Ld4DyXuUIjZ5cc75cLHvJ7dtNsTugphxIADwspS+AraAUePCKrSVtPLFj/F88w==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/picocolors": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/picocolors/-/picocolors-1.1.1.tgz",
      "integrity": "sha512-xceH2snhtb5M9liqDsmEw56le376mTZkEX/jEb/RxNFyegNul7eNslCXP9FDj/Lcu0X8KEyMceP2ntpaHrDEVA==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/picomatch": {
      "version": "4.0.7",
      "resolved": "https://registry.npmjs.org/picomatch/-/picomatch-4.0.7.tgz",
      "integrity": "sha512-qcJu88Q2IWqJsDD529JKMdwGm/dvInW4HvQnRwiH9JtihJvzGOscDtHE3x1pBKeUOTysQ8kVmLnJ2kJu7yhcGA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=12"
      },
      "funding": {
        "url": "https://github.com/sponsors/jonschlinkert"
      }
    },
    "node_modules/playwright": {
      "version": "1.63.0",
      "resolved": "https://registry.npmjs.org/playwright/-/playwright-1.63.0.tgz",
      "integrity": "sha512-+7ziBLidS4NaNCdt57SUDT+wYmmd5fmiQejUic/kb+YsYSCPyOOE9sebzMjNmQrsnNpDJqd4WHvV/8lfKfUDUg==",
      "dev": true,
      "license": "Apache-2.0",
      "dependencies": {
        "playwright-core": "1.63.0"
      },
      "bin": {
        "playwright": "cli.js"
      },
      "engines": {
        "node": ">=20"
      }
    },
    "node_modules/playwright-core": {
      "version": "1.63.0",
      "resolved": "https://registry.npmjs.org/playwright-core/-/playwright-core-1.63.0.tgz",
      "integrity": "sha512-rYCsBF/M5HjUch52bbtVONEFjv6Xu8sm8h72dNlR5bzIE1fvC/bxgspzkjSfU+MweEMmPM8KJebG6nnyxo5mCg==",
      "dev": true,
      "license": "Apache-2.0",
      "bin": {
        "playwright-core": "cli.js"
      },
      "engines": {
        "node": ">=20"
      }
    },
    "node_modules/postcss": {
      "version": "8.5.28",
      "resolved": "https://registry.npmjs.org/postcss/-/postcss-8.5.28.tgz",
      "integrity": "sha512-RRuzqDtt5Y9h3quz5hWhK+TPnsmVs6WwSU6LkJMeY4HstUEDuYTG8UJSdawMRzmzAtV+KEoG8N3Qg2qLy5vM/A==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/postcss/"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/postcss"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "dependencies": {
        "nanoid": "^3.3.18",
        "picocolors": "^1.1.1",
        "source-map-js": "^1.2.1"
      },
      "engines": {
        "node": "^10 || ^12 || >=14"
      }
    },
    "node_modules/prettier": {
      "version": "3.9.9",
      "resolved": "https://registry.npmjs.org/prettier/-/prettier-3.9.9.tgz",
      "integrity": "sha512-Z/CJHIkdujO/OtN7nXUii0Rf3VT5SRuhjBA82Xvu2XhBUgX3nhP67T0LHceBdQLex7OOFGTox+Q5Yg8Jk2Qivg==",
      "dev": true,
      "license": "MIT",
      "bin": {
        "prettier": "bin/prettier.cjs"
      },
      "engines": {
        "node": ">=14"
      },
      "funding": {
        "url": "https://github.com/prettier/prettier?sponsor=1"
      }
    },
    "node_modules/rollup": {
      "version": "4.63.5",
      "resolved": "https://registry.npmjs.org/rollup/-/rollup-4.63.5.tgz",
      "integrity": "sha512-KRWwmNLlPw5M7HcdYfm15oBv9n9LPtjzpzCIxS/phwqvPyxHSoKX6Y2YU3pxSPfy0CLquVgsx/j/hBi6OvH1Nw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@types/estree": "1.0.9"
      },
      "bin": {
        "rollup": "dist/bin/rollup"
      },
      "engines": {
        "node": ">=18.0.0",
        "npm": ">=8.0.0"
      },
      "optionalDependencies": {
        "@napi-rs/lzma-linux-x64-gnu": "1.5.1",
        "@rollup/rollup-android-arm-eabi": "4.63.5",
        "@rollup/rollup-android-arm64": "4.63.5",
        "@rollup/rollup-darwin-arm64": "4.63.5",
        "@rollup/rollup-darwin-x64": "4.63.5",
        "@rollup/rollup-freebsd-arm64": "4.63.5",
        "@rollup/rollup-freebsd-x64": "4.63.5",
        "@rollup/rollup-linux-arm-gnueabihf": "4.63.5",
        "@rollup/rollup-linux-arm-musleabihf": "4.63.5",
        "@rollup/rollup-linux-arm64-gnu": "4.63.5",
        "@rollup/rollup-linux-arm64-musl": "4.63.5",
        "@rollup/rollup-linux-loong64-gnu": "4.63.5",
        "@rollup/rollup-linux-loong64-musl": "4.63.5",
        "@rollup/rollup-linux-ppc64-gnu": "4.63.5",
        "@rollup/rollup-linux-ppc64-musl": "4.63.5",
        "@rollup/rollup-linux-riscv64-gnu": "4.63.5",
        "@rollup/rollup-linux-riscv64-musl": "4.63.5",
        "@rollup/rollup-linux-s390x-gnu": "4.63.5",
        "@rollup/rollup-linux-x64-gnu": "4.63.5",
        "@rollup/rollup-linux-x64-musl": "4.63.5",
        "@rollup/rollup-openbsd-x64": "4.63.5",
        "@rollup/rollup-openharmony-arm64": "4.63.5",
        "@rollup/rollup-win32-arm64-msvc": "4.63.5",
        "@rollup/rollup-win32-ia32-msvc": "4.63.5",
        "@rollup/rollup-win32-x64-gnu": "4.63.5",
        "@rollup/rollup-win32-x64-msvc": "4.63.5",
        "fsevents": "~2.3.2"
      }
    },
    "node_modules/siginfo": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/siginfo/-/siginfo-2.0.0.tgz",
      "integrity": "sha512-ybx0WO1/8bSBLEWXZvEd7gMW3Sn3JFlW3TvX1nREbDLRNQNaeNN8WK0meBwPdAaOI7TtRRRJn/Es1zhrrCHu7g==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/source-map-js": {
      "version": "1.2.1",
      "resolved": "https://registry.npmjs.org/source-map-js/-/source-map-js-1.2.1.tgz",
      "integrity": "sha512-UXWMKhLOwVKb728IUtQPXxfYU+usdybtUrK/8uGE8CQMvrhOpwvzDBwj0QhSL7MQc7vIsISBG8VQ8+IDQxpfQA==",
      "dev": true,
      "license": "BSD-3-Clause",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/stackback": {
      "version": "0.0.2",
      "resolved": "https://registry.npmjs.org/stackback/-/stackback-0.0.2.tgz",
      "integrity": "sha512-1XMJE5fQo1jGH6Y/7ebnwPOBEkIEnT4QF32d5R1+VXdXveM0IBMJt8zfaxX1P3QhVwrYe+576+jkANtSS2mBbw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/std-env": {
      "version": "4.2.0",
      "resolved": "https://registry.npmjs.org/std-env/-/std-env-4.2.0.tgz",
      "integrity": "sha512-oCUKSupKTHX53EyjDtuZQ64pjLJ6yYCtpmEw0goYxtjG9KpbRe8KAsl2tBUGU9DyMcJ0RwJ8GqJAFzMXcXW1Rw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/swagger-ui-dist": {
      "version": "5.33.0",
      "resolved": "https://registry.npmjs.org/swagger-ui-dist/-/swagger-ui-dist-5.33.0.tgz",
      "integrity": "sha512-wpdK+m6BU5yj6pmUdMskZVTSWYG4DLglAx3sIhylloY37i8O37IrH+YEpqdXNfpaTGxILRBFzUqLF2jKqbfI7A==",
      "license": "Apache-2.0",
      "dependencies": {
        "@scarf/scarf": "=1.4.0"
      }
    },
    "node_modules/three": {
      "version": "0.174.0",
      "resolved": "https://registry.npmjs.org/three/-/three-0.174.0.tgz",
      "integrity": "sha512-p+WG3W6Ov74alh3geCMkGK9NWuT62ee21cV3jEnun201zodVF4tCE5aZa2U122/mkLRmhJJUQmLLW1BH00uQJQ==",
      "license": "MIT"
    },
    "node_modules/tinybench": {
      "version": "2.9.0",
      "resolved": "https://registry.npmjs.org/tinybench/-/tinybench-2.9.0.tgz",
      "integrity": "sha512-0+DUvqWMValLmha6lr4kD8iAMK1HzV0/aKnCtWb9v9641TnP/MFb7Pc2bxoxQjTXAErryXVgUOfv2YqNllqGeg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/tinyexec": {
      "version": "1.3.1",
      "resolved": "https://registry.npmjs.org/tinyexec/-/tinyexec-1.3.1.tgz",
      "integrity": "sha512-GCvB3aoys96IuDFBMcTB46JOR6mdMtAToqwiW8JlWhsoh1mhHi/xn9ss/Dg7N555GiJyEt2qzoG/NHCwM6h1EA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/tinyglobby": {
      "version": "0.2.17",
      "resolved": "https://registry.npmjs.org/tinyglobby/-/tinyglobby-0.2.17.tgz",
      "integrity": "sha512-wXR/dYpcqKmfWpEdZjiKJOwCNFndD0DMnrW/cYjVGttEkBfVgcLFHoNrlj47mjOVic9yyNu65alsgF4NQyTa2g==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "fdir": "^6.5.0",
        "picomatch": "^4.0.4"
      },
      "engines": {
        "node": ">=12.0.0"
      },
      "funding": {
        "url": "https://github.com/sponsors/SuperchupuDev"
      }
    },
    "node_modules/tinyrainbow": {
      "version": "3.1.1",
      "resolved": "https://registry.npmjs.org/tinyrainbow/-/tinyrainbow-3.1.1.tgz",
      "integrity": "sha512-yau8yJdTt989Mm0Bd/236QnzEiPf2xLLTqUZRUJOo/3CB078LSwzei343DgtJVmfJKJE3TMINY1u42SQsP6mXw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=14.0.0"
      }
    },
    "node_modules/typescript": {
      "version": "5.9.3",
      "resolved": "https://registry.npmjs.org/typescript/-/typescript-5.9.3.tgz",
      "integrity": "sha512-jl1vZzPDinLr9eUt3J/t7V6FgNEw9QjvBPdysz9KfQDD41fQrC2Y4vKQdiaUpFT4bXlb1RHhLpp8wtm6M5TgSw==",
      "dev": true,
      "license": "Apache-2.0",
      "bin": {
        "tsc": "bin/tsc",
        "tsserver": "bin/tsserver"
      },
      "engines": {
        "node": ">=14.17"
      }
    },
    "node_modules/vite": {
      "version": "6.4.3",
      "resolved": "https://registry.npmjs.org/vite/-/vite-6.4.3.tgz",
      "integrity": "sha512-NTKlcQjlAK7MlQoyb6LgaqHc8sso/pVyUJYWMws3jg21uTJw/LddqIFPcPqP6PzpgbIcZyKI85sFE4HBrQDA8A==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "esbuild": "^0.25.0",
        "fdir": "^6.4.4",
        "picomatch": "^4.0.2",
        "postcss": "^8.5.3",
        "rollup": "^4.34.9",
        "tinyglobby": "^0.2.13"
      },
      "bin": {
        "vite": "bin/vite.js"
      },
      "engines": {
        "node": "^18.0.0 || ^20.0.0 || >=22.0.0"
      },
      "funding": {
        "url": "https://github.com/vitejs/vite?sponsor=1"
      },
      "optionalDependencies": {
        "fsevents": "~2.3.3"
      },
      "peerDependencies": {
        "@types/node": "^18.0.0 || ^20.0.0 || >=22.0.0",
        "jiti": ">=1.21.0",
        "less": "*",
        "lightningcss": "^1.21.0",
        "sass": "*",
        "sass-embedded": "*",
        "stylus": "*",
        "sugarss": "*",
        "terser": "^5.16.0",
        "tsx": "^4.8.1",
        "yaml": "^2.4.2"
      },
      "peerDependenciesMeta": {
        "@types/node": {
          "optional": true
        },
        "jiti": {
          "optional": true
        },
        "less": {
          "optional": true
        },
        "lightningcss": {
          "optional": true
        },
        "sass": {
          "optional": true
        },
        "sass-embedded": {
          "optional": true
        },
        "stylus": {
          "optional": true
        },
        "sugarss": {
          "optional": true
        },
        "terser": {
          "optional": true
        },
        "tsx": {
          "optional": true
        },
        "yaml": {
          "optional": true
        }
      }
    },
    "node_modules/vitest": {
      "version": "4.1.11",
      "resolved": "https://registry.npmjs.org/vitest/-/vitest-4.1.11.tgz",
      "integrity": "sha512-fhACrNXUidIbGSBr5FlbuBkO7VWC1ZyLl0DO4CU2DrQoAPxX84Ysxs+HeGQpii5lZWV1Q4gBZTTu49mF+A6Edw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@vitest/expect": "4.1.11",
        "@vitest/mocker": "4.1.11",
        "@vitest/pretty-format": "4.1.11",
        "@vitest/runner": "4.1.11",
        "@vitest/snapshot": "4.1.11",
        "@vitest/spy": "4.1.11",
        "@vitest/utils": "4.1.11",
        "es-module-lexer": "^2.0.0",
        "expect-type": "^1.3.0",
        "magic-string": "^0.30.21",
        "obug": "^2.1.1",
        "pathe": "^2.0.3",
        "picomatch": "^4.0.3",
        "std-env": "^4.0.0-rc.1",
        "tinybench": "^2.9.0",
        "tinyexec": "^1.0.2",
        "tinyglobby": "^0.2.15",
        "tinyrainbow": "^3.1.0",
        "vite": "^6.0.0 || ^7.0.0 || ^8.0.0",
        "why-is-node-running": "^2.3.0"
      },
      "bin": {
        "vitest": "vitest.mjs"
      },
      "engines": {
        "node": "^20.0.0 || ^22.0.0 || >=24.0.0"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      },
      "peerDependencies": {
        "@edge-runtime/vm": "*",
        "@opentelemetry/api": "^1.9.0",
        "@types/node": "^20.0.0 || ^22.0.0 || >=24.0.0",
        "@vitest/browser-playwright": "4.1.11",
        "@vitest/browser-preview": "4.1.11",
        "@vitest/browser-webdriverio": "4.1.11",
        "@vitest/coverage-istanbul": "4.1.11",
        "@vitest/coverage-v8": "4.1.11",
        "@vitest/ui": "4.1.11",
        "happy-dom": "*",
        "jsdom": "*",
        "vite": "^6.0.0 || ^7.0.0 || ^8.0.0"
      },
      "peerDependenciesMeta": {
        "@edge-runtime/vm": {
          "optional": true
        },
        "@opentelemetry/api": {
          "optional": true
        },
        "@types/node": {
          "optional": true
        },
        "@vitest/browser-playwright": {
          "optional": true
        },
        "@vitest/browser-preview": {
          "optional": true
        },
        "@vitest/browser-webdriverio": {
          "optional": true
        },
        "@vitest/coverage-istanbul": {
          "optional": true
        },
        "@vitest/coverage-v8": {
          "optional": true
        },
        "@vitest/ui": {
          "optional": true
        },
        "happy-dom": {
          "optional": true
        },
        "jsdom": {
          "optional": true
        },
        "vite": {
          "optional": false
        }
      }
    },
    "node_modules/why-is-node-running": {
      "version": "2.3.0",
      "resolved": "https://registry.npmjs.org/why-is-node-running/-/why-is-node-running-2.3.0.tgz",
      "integrity": "sha512-hUrmaWBdVDcxvYqnyh09zunKzROWjbZTiNy8dBEjkS7ehEDQibXJ7XvlmtbwuTclUiIyN+CyXQD4Vmko8fNm8w==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "siginfo": "^2.0.0",
        "stackback": "0.0.2"
      },
      "bin": {
        "why-is-node-running": "cli.js"
      },
      "engines": {
        "node": ">=8"
      }
    }
  }
}

````

## frontend/package.json

````json
{
  "name": "skillmatch-ai",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "predev": "node scripts/copy-docs.mjs",
    "prebuild": "node scripts/copy-docs.mjs",
    "dev": "vite --host 0.0.0.0",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview --host 0.0.0.0",
    "test": "vitest run src",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "@fontsource/dm-sans": "^5.2.5",
    "@fontsource/manrope": "^5.2.5",
    "@popperjs/core": "^2.11.8",
    "bootstrap": "^5.3.3",
    "chart.js": "^4.4.8",
    "gsap": "^3.12.7",
    "jquery": "^3.7.1",
    "lucide": "^0.468.0",
    "swagger-ui-dist": "^5.33.0",
    "three": "^0.174.0"
  },
  "devDependencies": {
    "@axe-core/playwright": "^4.13.0",
    "@playwright/test": "^1.63.0",
    "@types/jquery": "^3.5.32",
    "@types/three": "^0.174.0",
    "prettier": "^3.9.9",
    "typescript": "^5.7.3",
    "vite": "^6.2.0",
    "vitest": "^4.1.11"
  }
}

````

## frontend/playwright.config.ts

````typescript
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  use: {
    baseURL: "http://127.0.0.1:5173",
    headless: true,
    channel: process.env.CI ? undefined : "chrome",
    viewport: { width: 1440, height: 1100 },
    reducedMotion: "reduce",
  },
  webServer: {
    command: "npm run dev -- --port 5173",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
  },
  reporter: "list",
});

````

## frontend/public/favicon.svg

````xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" rx="12" fill="#a38aff"/><path d="m22 7-12 16h9l-2 10 13-17h-10z" fill="#151023"/></svg>

````

## frontend/scripts/copy-docs.mjs

````text
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
const require = createRequire(import.meta.url);
const source = dirname(require.resolve("swagger-ui-dist/package.json"));
const target = resolve("public/docs-assets");
mkdirSync(target, { recursive: true });
for (const file of [
  "swagger-ui-bundle.js",
  "swagger-ui.css",
  "favicon-32x32.png",
]) {
  copyFileSync(resolve(source, file), resolve(target, file));
}

````

## frontend/src/lib/api.ts

````typescript
import $ from "jquery";
import type { User } from "./types";
let accessToken = "";
let refreshPromise: Promise<User> | null = null;
export function setToken(token: string): void {
  accessToken = token;
}
export async function refreshSession(): Promise<User> {
  if (!refreshPromise)
    refreshPromise = new Promise<User>((resolve, reject) => {
      $.ajax({
        url: "/api/v1/auth/refresh",
        method: "POST",
        xhrFields: { withCredentials: true },
      })
        .done((data) => {
          setToken(data.access_token);
          resolve(data.user);
        })
        .fail(() => reject(new Error("Please sign in to continue.")));
    }).finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  retry = true,
): Promise<T> {
  try {
    return await new Promise<T>((resolve, reject) => {
      const isFile = body instanceof FormData;
      $.ajax({
        url: `/api/v1${path}`,
        method,
        data: body ? (isFile ? body : JSON.stringify(body)) : undefined,
        processData: !isFile,
        contentType: isFile ? false : "application/json",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        xhrFields: { withCredentials: true },
      })
        .done(resolve)
        .fail((xhr) => reject(xhr));
    });
  } catch (error) {
    const xhr = error as JQuery.jqXHR;
    if (xhr.status === 401 && retry && !path.startsWith("/auth")) {
      await refreshSession();
      return api<T>(path, method, body, false);
    }
    const detail = xhr.responseJSON?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg: string }) => d.msg).join(". ")
          : xhr.status === 0
            ? "Unable to reach the API. Check that the backend is running."
            : "Something went wrong. Please try again.",
    );
  }
}

````

## frontend/src/lib/charts.ts

````typescript
import { Chart, registerables } from "chart.js";
import type { Analytics, Match } from "./types";
Chart.register(...registerables);
export function mountCharts(
  kind: string,
  data: Analytics,
  match: Match | undefined,
  reduced: boolean,
): () => void {
  const charts: Chart[] = [];
  Chart.defaults.color = "#a396b1";
  Chart.defaults.font.family = "DM Sans";
  Chart.defaults.font.size = 11;
  Chart.defaults.borderColor = "#372b4222";
  const base = {
    responsive: true,
    maintainAspectRatio: false,
    animation: reduced ? (false as const) : { duration: 900 },
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false }, ticks: { color: "#aa9ab5" } },
      y: {
        beginAtZero: true,
        grid: { color: "#3e304333" },
        ticks: { precision: 0 },
      },
    },
  };
  if (kind === "radar" && match) {
    const canvas = document.getElementById(
      "radar-chart",
    ) as HTMLCanvasElement | null;
    if (canvas) {
      const labels =
        match.job.skills.length >= 3
          ? match.job.skills
          : ["Skill overlap", "Semantic fit", "Overall fit"];
      const values =
        match.job.skills.length >= 3
          ? labels.map((s) => (match.matched.includes(s) ? 100 : 0))
          : [match.keyword_score, match.semantic_score, match.score];
      charts.push(
        new Chart(canvas, {
          type: "radar",
          data: {
            labels,
            datasets: [
              {
                label: "Your coverage",
                data: values,
                backgroundColor: "#b59aff22",
                borderColor: "#b59aff",
                pointBackgroundColor: "#8ce1d4",
                pointRadius: 3,
                borderWidth: 2,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: reduced ? false : { duration: 900 },
            plugins: { legend: { display: false } },
            scales: {
              r: {
                min: 0,
                max: 100,
                ticks: { display: false, stepSize: 25 },
                grid: { color: "#63476a44" },
                angleLines: { color: "#63476a44" },
                pointLabels: { color: "#b9a7c9", font: { size: 10 } },
              },
            },
          },
        }),
      );
    }
  } else {
    const configs = [
      {
        id: "gap-chart",
        type: "bar" as const,
        labels: Object.keys(data.skill_gaps),
        values: Object.values(data.skill_gaps),
        color: "#b59aff",
        label: "Roles missing skill",
      },
      {
        id: "distribution-chart",
        type: "bar" as const,
        labels: ["0–19%", "20–39%", "40–59%", "60–79%", "80–100%"],
        values: data.score_distribution,
        color: "#8bcfc3",
        label: "Matches",
      },
      {
        id: "demand-chart",
        type: "bar" as const,
        labels: Object.keys(data.in_demand),
        values: Object.values(data.in_demand),
        color: "#99aedb",
        label: "Active roles",
      },
      {
        id: "activity-chart",
        type: "line" as const,
        labels: Object.keys(data.applications_over_time),
        values: Object.values(data.applications_over_time),
        color: "#c29eed",
        label: "Applications",
      },
    ];
    configs.forEach((c) => {
      const canvas = document.getElementById(c.id) as HTMLCanvasElement | null;
      if (canvas)
        charts.push(
          new Chart(canvas, {
            type: c.type,
            data: {
              labels: c.labels,
              datasets: [
                {
                  label: c.label,
                  data: c.values,
                  backgroundColor: c.type === "line" ? "#b59aff12" : c.color,
                  borderColor: c.color,
                  borderWidth: c.type === "line" ? 2 : 0,
                  borderRadius: c.type === "bar" ? 5 : undefined,
                  tension: 0.35,
                  fill: c.type === "line",
                  pointRadius: 4,
                },
              ],
            },
            options: base,
          }),
        );
    });
  }
  return () => charts.forEach((c) => c.destroy());
}

````

## frontend/src/lib/demo.ts

````typescript
import type { Analytics, Job, Match, Resume } from "./types";
export const demoSkills = [
  "JavaScript",
  "TypeScript",
  "React",
  "HTML",
  "CSS",
  "Git",
  "REST APIs",
  "Figma",
  "Node.js",
  "SQL",
  "Tailwind CSS",
  "Responsive Design",
];
export const demoJobs: Job[] = [
  {
    id: 1,
    title: "Senior Frontend Developer",
    company: "Linear",
    location: "Remote",
    employment_type: "Full-time",
    salary_min: 140000,
    salary_max: 180000,
    skills: ["React", "TypeScript", "Next.js", "CSS", "Git"],
    score: 94,
  },
  {
    id: 2,
    title: "Full Stack Engineer",
    company: "Vercel",
    location: "San Francisco, CA",
    employment_type: "Full-time",
    salary_min: 130000,
    salary_max: 170000,
    skills: ["React", "Node.js", "TypeScript", "PostgreSQL"],
    score: 89,
  },
  {
    id: 3,
    title: "Frontend Engineer",
    company: "Notion",
    location: "Remote",
    employment_type: "Full-time",
    salary_min: 120000,
    salary_max: 160000,
    skills: ["JavaScript", "React", "TypeScript", "GraphQL"],
    score: 86,
  },
  {
    id: 4,
    title: "Design Engineer",
    company: "Figma",
    location: "New York, NY",
    employment_type: "Full-time",
    salary_min: 145000,
    salary_max: 190000,
    skills: ["React", "Figma", "CSS", "Three.js"],
    score: 82,
  },
  {
    id: 5,
    title: "Product Engineer",
    company: "Stripe",
    location: "Remote",
    employment_type: "Full-time",
    salary_min: 135000,
    salary_max: 185000,
    skills: ["TypeScript", "React", "Node.js", "PostgreSQL"],
    score: 79,
  },
  {
    id: 6,
    title: "UI Engineer",
    company: "Supabase",
    location: "Remote",
    employment_type: "Contract",
    salary_min: 110000,
    salary_max: 150000,
    skills: ["React", "Tailwind CSS", "SQL", "Next.js"],
    score: 76,
  },
].map((j) => ({
  ...j,
  created_at: "2026-09-26T12:00:00Z",
  description: `Help ${j.company} build beautifully crafted software that makes work better. As a ${j.title.toLowerCase()}, you'll collaborate with a small, ambitious team to shape thoughtful user experiences, own features end to end, and set a high bar for performance and accessibility.\n\nWhat you'll do\nBuild and ship intuitive interfaces used by thousands of teams. Partner with design to turn complex problems into simple experiences. Write well-tested, maintainable code and mentor your teammates.\n\nWhat you bring\nPractical experience with ${j.skills.join(", ")}. A strong product sense, clear communication, and a love of the details.\n\nWhat we offer\nFlexible working, generous time off, health coverage, and a dedicated learning budget. This opening is sample data for the SkillMatch preview.`,
}));
export const demoResume: Resume = {
  id: 1,
  filename: "Alex_Morgan_Resume.pdf",
  skills: demoSkills,
  created_at: "2026-09-26T12:00:00Z",
};
export function demoMatch(job: Job): Match {
  const matched = job.skills.filter((s) => demoSkills.includes(s));
  const missing = job.skills.filter((s) => !demoSkills.includes(s));
  return {
    id: job.id,
    job_id: job.id,
    resume_id: 1,
    score: job.score ?? 80,
    semantic_score: 93,
    keyword_score: (matched.length / job.skills.length) * 100,
    method: "sample",
    job,
    matched,
    missing,
    suggestions: missing.map((skill) => ({
      skill,
      title: `Build your ${skill} skills`,
      url: `https://www.freecodecamp.org/news/search/?query=${encodeURIComponent(skill)}`,
    })),
  };
}
export const demoAnalytics: Analytics = {
  matches: 24,
  average_score: 86,
  applications: 8,
  interviews: 3,
  skill_gaps: { "Next.js": 8, GraphQL: 6, PostgreSQL: 4, Docker: 3 },
  score_distribution: [1, 2, 4, 7, 10],
  in_demand: { React: 82, TypeScript: 74, Python: 65, "Node.js": 58, SQL: 49 },
  applications_over_time: {
    "Sep 1": 1,
    "Sep 5": 2,
    "Sep 10": 2,
    "Sep 15": 4,
    "Sep 20": 5,
    "Sep 25": 8,
  },
};

````

## frontend/src/lib/scene.ts

````typescript
import * as THREE from "three";
export function createScene(container: HTMLElement): () => void {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: "low-power",
    });
  } catch {
    return () => {};
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  container.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  camera.position.z = 7;
  const group = new THREE.Group();
  scene.add(group);
  const positions: number[] = [];
  const points: THREE.Vector3[] = [];
  for (let i = 0; i < 34; i++) {
    const angle = i * 2.39996;
    const y = 1 - (i / 33) * 2;
    const radius = Math.sqrt(1 - y * y);
    const p = new THREE.Vector3(
      Math.cos(angle) * radius * 2.5,
      y * 1.8,
      Math.sin(angle) * radius * 1.2,
    );
    points.push(p);
    positions.push(p.x, p.y, p.z);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(positions, 3),
  );
  const material = new THREE.PointsMaterial({
    color: 0xc9a4ff,
    size: 0.045,
    transparent: true,
    opacity: 0.75,
  });
  group.add(new THREE.Points(geometry, material));
  const linePositions: number[] = [];
  points.forEach((p, i) =>
    points.slice(i + 1).forEach((q) => {
      if (p.distanceTo(q) < 1.45)
        linePositions.push(p.x, p.y, p.z, q.x, q.y, q.z);
    }),
  );
  const lineGeometry = new THREE.BufferGeometry();
  lineGeometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(linePositions, 3),
  );
  const lineMaterial = new THREE.LineBasicMaterial({
    color: 0x9871c4,
    transparent: true,
    opacity: 0.2,
  });
  group.add(new THREE.LineSegments(lineGeometry, lineMaterial));
  const resize = () => {
    const w = container.clientWidth,
      h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  const observer = new ResizeObserver(resize);
  observer.observe(container);
  resize();
  const pointer = { x: 0, y: 0 };
  const parent = container.parentElement!;
  const move = (ev: PointerEvent) => {
    const rect = parent.getBoundingClientRect();
    pointer.x = (ev.clientX - rect.left) / rect.width - 0.5;
    pointer.y = (ev.clientY - rect.top) / rect.height - 0.5;
  };
  parent.addEventListener("pointermove", move);
  let frame = 0;
  let visible = true;
  let previous = 0;
  const visibility = new IntersectionObserver((entries) => {
    visible = entries[0].isIntersecting;
  });
  visibility.observe(container);
  const tick = (time: number) => {
    frame = requestAnimationFrame(tick);
    if (!visible || document.hidden || time - previous < 32) return;
    previous = time;
    group.rotation.y +=
      (pointer.x * 0.25 + Math.sin(time * 0.00007) * 0.15 - group.rotation.y) *
      0.03;
    group.rotation.x += (pointer.y * 0.15 - group.rotation.x) * 0.03;
    group.rotation.z = time * 0.000015;
    renderer.render(scene, camera);
  };
  frame = requestAnimationFrame(tick);
  return () => {
    cancelAnimationFrame(frame);
    observer.disconnect();
    visibility.disconnect();
    parent.removeEventListener("pointermove", move);
    geometry.dispose();
    material.dispose();
    lineGeometry.dispose();
    lineMaterial.dispose();
    renderer.dispose();
    renderer.domElement.remove();
  };
}

````

## frontend/src/lib/types.ts

````typescript
export interface User {
  id: number;
  name: string;
  email: string;
  role: "candidate" | "recruiter" | "admin";
  active: boolean;
}
export interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  employment_type: string;
  description: string;
  salary_min: number;
  salary_max: number;
  skills: string[];
  created_at: string;
  score?: number;
  active?: boolean;
}
export interface Resume {
  id: number;
  filename: string;
  skills: string[];
  created_at: string;
}
export interface Match {
  id: number;
  job_id: number;
  resume_id: number;
  score: number;
  semantic_score: number;
  keyword_score: number;
  matched: string[];
  missing: string[];
  method: string;
  job: Job;
  suggestions: { skill: string; title: string; url: string }[];
}
export interface Application {
  id: number;
  job: Job;
  candidate: string;
  status: string;
  score: number | null;
  created_at: string;
}
export interface Analytics {
  matches: number;
  average_score: number;
  applications: number;
  interviews: number;
  skill_gaps: Record<string, number>;
  score_distribution: number[];
  in_demand: Record<string, number>;
  applications_over_time: Record<string, number>;
}

````

## frontend/src/lib/utils.test.ts

````typescript
import { describe, expect, it } from "vitest";
import {
  escapeHtml,
  initials,
  salary,
  scoreLabel,
  validateFile,
} from "./utils";
describe("safe display and resume validation", () => {
  it("escapes untrusted markup and attributes", () =>
    expect(escapeHtml("<img src=\"x\" onerror='x'>&")).toBe(
      "&lt;img src=&quot;x&quot; onerror=&#39;x&#39;&gt;&amp;",
    ));
  it("rejects unsupported and oversized uploads", () => {
    expect(validateFile({ name: "cv.exe", size: 100 })).toBeTruthy();
    expect(
      validateFile({ name: "cv.pdf", size: 6 * 1024 * 1024 }),
    ).toBeTruthy();
    expect(validateFile({ name: "cv.DOCX", size: 1024 })).toBeNull();
  });
  it("formats salaries and names", () => {
    expect(salary(120000, 160000)).toBe("$120k – $160k");
    expect(initials(" Alex  Morgan ")).toBe("AM");
  });
  it("labels match scores consistently", () => {
    expect(scoreLabel(90)).toBe("Excellent match");
    expect(scoreLabel(70)).toBe("Strong match");
    expect(scoreLabel(40)).toBe("Room to grow");
  });
});

````

## frontend/src/lib/utils.ts

````typescript
export function escapeHtml(value: unknown): string {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ]!,
  );
}
export function salary(min: number, max: number): string {
  return `$${Math.round(min / 1000)}k – $${Math.round(max / 1000)}k`;
}
export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}
export function validateFile(file: Pick<File, "name" | "size">): string | null {
  if (!/\.(pdf|docx)$/i.test(file.name))
    return "Please choose a PDF or DOCX file.";
  if (file.size === 0 || file.size > 5 * 1024 * 1024)
    return "Your resume must be between 1 byte and 5 MB.";
  return null;
}
export function scoreLabel(score: number): string {
  return score >= 85
    ? "Excellent match"
    : score >= 65
      ? "Strong match"
      : "Room to grow";
}

````

## frontend/src/main.ts

````typescript
import $ from "jquery";
import "bootstrap/dist/css/bootstrap.min.css";
import "@fontsource/manrope/latin-400.css";
import "@fontsource/manrope/latin-500.css";
import "@fontsource/manrope/latin-600.css";
import "@fontsource/manrope/latin-700.css";
import "@fontsource/manrope/latin-800.css";
import "@fontsource/dm-sans/latin-400.css";
import "@fontsource/dm-sans/latin-500.css";
import "@fontsource/dm-sans/latin-600.css";
import {
  createIcons,
  Zap,
  Sparkles,
  LayoutDashboard,
  FileUser,
  SquarePlus,
  BriefcaseBusiness,
  ScanLine,
  Layers,
  ChartNoAxesCombined,
  Shield,
  CircleHelp,
  ArrowUpRight,
  LogIn,
  LogOut,
  Menu,
  ChevronRight,
  Search,
  Bell,
  X,
  CircleAlert,
  CircleCheck,
  Upload,
  ArrowRight,
  Atom,
  Figma,
  Code2,
  Clock3,
  MapPin,
  Bookmark,
  TrendingUp,
  Target,
  Send,
  MessagesSquare,
  Lightbulb,
  FileText,
  FilePenLine,
  Network,
  Triangle,
  CloudUpload,
  ShieldCheck,
  FileScan,
  Route,
  Trash2,
  ArrowLeft,
  Banknote,
  Sprout,
  BookOpen,
  Plus,
  Pencil,
  Eye,
  FileCheck,
  ArrowDown,
} from "lucide";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import "./styles/main.css";
import { api, refreshSession, setToken } from "./lib/api";
import { demoAnalytics, demoJobs, demoMatch, demoResume } from "./lib/demo";
import {
  escapeHtml as e,
  initials,
  salary,
  scoreLabel,
  validateFile,
} from "./lib/utils";
import type {
  Analytics,
  Application,
  Job,
  Match,
  Resume,
  User,
} from "./lib/types";

const icons = {
  Zap,
  Sparkles,
  LayoutDashboard,
  FileUser,
  SquarePlus,
  BriefcaseBusiness,
  ScanLine,
  Layers,
  ChartNoAxesCombined,
  Shield,
  CircleHelp,
  ArrowUpRight,
  LogIn,
  LogOut,
  Menu,
  ChevronRight,
  Search,
  Bell,
  X,
  CircleAlert,
  CircleCheck,
  Upload,
  ArrowRight,
  Atom,
  Figma,
  Code2,
  Clock3,
  MapPin,
  Bookmark,
  TrendingUp,
  Target,
  Send,
  MessagesSquare,
  Lightbulb,
  FileText,
  FilePenLine,
  Network,
  Triangle,
  CloudUpload,
  ShieldCheck,
  FileScan,
  Route,
  Trash2,
  ArrowLeft,
  Banknote,
  Sprout,
  BookOpen,
  Plus,
  Pencil,
  Eye,
  FileCheck,
  ArrowDown,
};
gsap.registerPlugin(ScrollTrigger);
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let user: User | null = null;
let demo = true;
let jobs: Job[] = [...demoJobs];
let resumes: Resume[] = [demoResume];
let matches: Match[] = [];
let analytics: Analytics = demoAnalytics;
let cleanupScene: (() => void) | undefined;
let cleanupCharts: (() => void) | undefined;
let renderId = 0;
let jobPage = 1;
let selectedFile: File | null = null;
function bookmarkKey(): string {
  return demo ? "sm-bookmarks-demo" : `sm-bookmarks-user-${user?.id}`;
}
function readBookmarks(): number[] {
  try {
    const stored: unknown = JSON.parse(
      localStorage.getItem(bookmarkKey()) || "[]",
    );
    return Array.isArray(stored)
      ? stored.filter((id): id is number => Number.isInteger(id) && id > 0)
      : [];
  } catch {
    return [];
  }
}
let bookmarks: number[] = readBookmarks();
const icon = (name: string, cls = "") =>
  `<i data-lucide="${name}" class="${cls}" aria-hidden="true"></i>`;
const link = (path: string, label: string, iconName: string) =>
  `<a href="#/${path}" class="nav-item ${route().split("/")[0] === path ? "active" : ""}">${icon(iconName)}<span>${label}</span>${path === "jobs" ? '<span class="nav-count">' + (demo ? "24" : "Explore") + "</span>" : ""}</a>`;
function route(): string {
  return location.hash.replace(/^#\/?/, "") || "dashboard";
}
function toast(message: string, type = "success"): void {
  const t = $(
    `<div class="app-toast ${type}" role="status">${icon(type === "error" ? "circle-alert" : "circle-check")}<span>${e(message)}</span><button aria-label="Dismiss notification">${icon("x")}</button></div>`,
  );
  $("#toasts").append(t);
  t.find("button").on("click", () => t.remove());
  createIcons({ icons });
  setTimeout(() => t.remove(), 6000);
}
function logo(): string {
  return `<a class="brand" href="#/dashboard" aria-label="SkillMatch AI dashboard"><span class="brand-symbol">${icon("zap")}</span><span>skillmatch<span class="brand-ai">AI</span></span></a>`;
}
function shell(content: string, title = "Overview"): void {
  const name = demo ? "Alex Morgan" : user?.name || "Your account";
  const recruiter = user?.role === "recruiter";
  $("#app").html(
    `<aside class="sidebar">${logo()}<div class="workspace-label">YOUR WORKSPACE</div><nav aria-label="Main navigation">${link(recruiter ? "recruiter" : "dashboard", "Overview", "layout-dashboard")}${!recruiter ? link("upload", "My resume", "file-user") : link("post-job", "Post a job", "square-plus")}${link("jobs", "Find jobs", "briefcase-business")}${link("matches", "My matches", "scan-line")}${link("applications", recruiter ? "Candidates" : "Applications", "layers")}${link("analytics", "Insights", "chart-no-axes-combined")}${user?.role === "admin" ? link("admin", "Administration", "shield") : ""}</nav><div class="sidebar-bottom"><div class="career-card"><span class="tiny-spark">${icon("sparkles")}</span><strong>Your next chapter<br>starts with you.</strong><p>A little clarity. A big step forward.</p><a href="#/upload">Find your potential ${icon("arrow-up-right")}</a></div><a href="#/landing" class="help-link">${icon("circle-help")} How SkillMatch works ${icon("arrow-up-right")}</a><div class="sidebar-profile"><div class="avatar">${e(initials(name))}</div><div><strong>${e(name)}</strong><span>${demo ? "Sample candidate" : e(user?.role || "Candidate")}</span></div><button class="icon-btn" id="account-button" aria-label="${demo ? "Sign in" : "Sign out"}">${icon(demo ? "log-in" : "log-out")}</button></div></div></aside><div class="sidebar-scrim"></div><div class="app-layout"><header class="topbar"><div class="topbar-title"><button class="icon-btn menu-toggle" aria-label="Open navigation">${icon("menu")}</button><span class="breadcrumb-home">Workspace</span>${icon("chevron-right")}<strong>${e(title)}</strong></div><div class="topbar-actions"><a class="top-search" href="#/jobs">${icon("search")}<span>Search your next opportunity</span><kbd>/</kbd></a><span class="demo-badge">${demo ? "Sample workspace" : "Live workspace"}<span></span></span><button class="icon-btn notification-button" aria-label="View notifications">${icon("bell")}<b></b></button><div class="avatar small">${e(initials(name))}</div></div></header><main id="main-content" tabindex="-1">${content}</main><footer class="app-footer"><span>Made for your next move.</span><span>SkillMatch AI <span class="footer-dot">•</span> ${demo ? "You’re exploring sample data" : "Your career, in focus"} ${icon("sparkles")}</span></footer></div>`,
  );
  finish();
}
function jobAge(value: string): string {
  const days = Math.max(
    0,
    Math.floor((Date.now() - new Date(value).getTime()) / 86400000),
  );
  return days === 0
    ? "New opportunity"
    : days === 1
      ? "1 day ago"
      : `${days} days ago`;
}

function finish(): void {
  createIcons({ icons });
  if (!reduced) {
    $(".stat-number").each(function () {
      const element = this;
      const label = element.dataset.value || "0";
      const state = { value: 0 };
      gsap.to(state, {
        value: parseFloat(label),
        duration: 1.1,
        ease: "power2.out",
        onUpdate: () => {
          element.textContent =
            Math.round(state.value) + (label.includes("%") ? "%" : "");
        },
      });
    });
  }
  if (!reduced) {
    gsap.from(".page-heading,.reveal", {
      y: 14,
      opacity: 0,
      duration: 0.55,
      stagger: 0.065,
      ease: "power2.out",
      clearProps: "all",
    });
  }
  $("a,button,input,select")
    .off("keydown.escape")
    .on("keydown.escape", (ev) => {
      if (ev.key === "Escape") $("body").removeClass("nav-open");
    });
}
function heading(
  eyebrow: string,
  title: string,
  subtitle: string,
  action = "",
): string {
  return `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${subtitle}</p></div>${action}</div>`;
}
function sectionTitle(title: string, sub: string, action = ""): string {
  return `<div class="section-title"><div><h2>${title}</h2>${sub ? `<p>${sub}</p>` : ""}</div>${action}</div>`;
}
function companyLogo(company: string): string {
  const key = company.toLowerCase();
  return `<div class="company-logo ${e(key)}">${key === "linear" ? '<span class="linear-mark"></span>' : key === "vercel" ? '<span class="vercel-mark"></span>' : key === "notion" ? '<span class="notion-mark">N</span>' : key === "figma" ? icon("figma") : key === "stripe" ? '<b class="stripe-mark">S</b>' : icon("zap")}</div>`;
}
function chip(skill: string, cls = ""): string {
  return `<span class="skill-chip ${cls}">${e(skill)}</span>`;
}
function jobCard(job: Job, _index = 0): string {
  return `<article class="job-card reveal"><div class="job-card-top"><div class="company-info">${companyLogo(job.company)}<div><strong>${e(job.company)}</strong><span>${e(jobAge(job.created_at))}</span></div></div><button class="icon-btn save-job ${bookmarks.includes(job.id) ? "saved" : ""}" data-id="${job.id}" aria-label="${bookmarks.includes(job.id) ? "Unsave" : "Save"} ${e(job.title)}" aria-pressed="${bookmarks.includes(job.id)}">${icon("bookmark")}</button></div><a class="job-title" href="#/jobs/${job.id}">${e(job.title)}</a><div class="job-meta"><span>${icon("map-pin")}${e(job.location)}</span><span>${icon("clock-3")}${e(job.employment_type)}</span></div><div class="job-skills">${job.skills
    .slice(0, 3)
    .map((s) => chip(s))
    .join(
      "",
    )}${job.skills.length > 3 ? chip("+" + (job.skills.length - 3)) : ""}</div><div class="job-salary">${salary(job.salary_min, job.salary_max)}<span> / year</span></div><div class="job-card-footer"><span class="match-pill">${icon("sparkles")}${job.score !== undefined ? Math.round(job.score) + "% match" : "Explore role"}</span><a href="#/jobs/${job.id}" class="job-arrow" aria-label="View ${e(job.title)}">${icon("arrow-up-right")}</a></div></article>`;
}
function stats(): string {
  const values = [
    [
      "scan-line",
      "Job matches",
      analytics.matches,
      "Roles aligned with your skills",
      "violet",
    ],
    [
      "target",
      "Average match",
      analytics.average_score + "%",
      "Your skills are opening doors",
      "mint",
    ],
    [
      "send",
      "Applications",
      analytics.applications,
      "Every step brings you closer",
      "blue",
    ],
    [
      "messages-square",
      "Interviews",
      analytics.interviews,
      "Great conversations ahead",
      "peach",
    ],
  ];
  return `<div class="stats-grid">${values.map(([ic, label, val, note, color]) => `<div class="stat-card reveal"><div class="stat-heading"><span>${label}</span><span class="stat-icon ${color}">${icon(String(ic))}</span></div><div class="stat-value"><b class="stat-number" data-value="${val}">${val}</b><span>${icon("trending-up")}</span></div><p>${note}</p></div>`).join("")}</div>`;
}
async function loadCandidate(): Promise<void> {
  if (demo) {
    jobs = [...demoJobs];
    resumes = [demoResume];
    analytics = demoAnalytics;
    matches = demoJobs.map(demoMatch);
    return;
  }
  const [j, r, a, m] = await Promise.all([
    api<{ items: Job[] }>("/jobs?size=6"),
    api<Resume[]>("/resumes"),
    api<Analytics>("/analytics"),
    api<Match[]>("/matches"),
  ]);
  jobs = j.items;
  resumes = r;
  analytics = a;
  matches = m;
  jobs = jobs.map((job) => ({
    ...job,
    score: m.find((x) => x.job_id === job.id)?.score,
  }));
}
function dashboard(): void {
  const name = demo ? "Alex" : user?.name.split(" ")[0] || "there";
  shell(
    `${heading("A LITTLE CLARITY. A LOT OF POSSIBILITY.", `Your next move, ${e(name)}<span class="greeting-dot">.</span>`, `Let’s turn what you’re good at into where you’re going.`, `<a href="#/upload" class="btn btn-primary">${icon("upload")} Upload resume</a>`)}<div class="dashboard-hero reveal"><div class="hero-copy"><span class="hero-eyebrow"><span class="live-dot"></span> YOUR POTENTIAL, CONNECTED</span><h2>You bring the skills.<br>We find the <span>possibilities.</span></h2><p>Your experience is more than a document. Discover<br class="desktop-only"> opportunities that see the full picture.</p><a class="btn btn-light" href="#/matches">Explore my matches ${icon("arrow-up-right")}</a><span class="hero-footnote">${icon("sparkles")} A smarter match. A more meaningful next step.</span></div><div class="hero-visual" aria-label="Connected skills constellation"><div class="orbital-glow"></div><div id="skill-scene"></div><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="core-orb">${icon("sparkles")}</div><div class="floating-skill node-react">${icon("atom")} React</div><div class="floating-skill node-typescript"><b>TS</b> TypeScript</div><div class="floating-skill node-design">${icon("figma")} UI design</div><div class="floating-skill node-python"><span>✳</span> Python</div><div class="float-dot dot-one"></div><div class="float-dot dot-two"></div><div class="constellation-caption"><span></span> Connecting your skills to what’s next</div></div></div>${stats()}<div class="dashboard-columns"><section class="recommendations">${sectionTitle("Good things are a match", "Opportunities that feel like your next chapter.", `<a class="text-link" href="#/jobs">View all jobs ${icon("arrow-right")}</a>`)}<div class="jobs-grid">${jobs.slice(0, 3).map(jobCard).join("") || empty("Your next opportunity is on its way", "New jobs will appear here when recruiters post them.", "Browse jobs", "jobs")}</div><div class="skills-panel panel reveal">${sectionTitle("Your skills, at a glance", "A strong foundation. Room to grow.", `<a class="text-link" href="#/analytics">View insights ${icon("arrow-up-right")}</a>`)}<div class="skills-panel-content"><div class="skills-overview"><div class="skill-legend"><span><i class="legend-dot purple"></i> Your strengths</span><span class="subtle">${resumes[0]?.skills.length || 0} skills identified</span></div><div class="strength-chips">${
      (resumes[0]?.skills || [])
        .slice(0, 8)
        .map((s) => chip(s, "strength"))
        .join("") ||
      '<p class="subtle">Upload a resume to discover your strengths.</p>'
    }</div><div class="skills-tip">${icon("lightbulb")}<span>Your next opportunity could be one new skill away.</span></div></div><div class="gap-overview"><div class="skill-legend"><span><i class="legend-dot cyan"></i> Skills worth adding</span><span class="subtle">In your matched roles</span></div>${
      Object.entries(analytics.skill_gaps)
        .slice(0, 3)
        .map(
          ([s, n], i) =>
            `<div class="gap-row"><span>${e(s)}</span><div class="gap-track"><div style="width:${Math.min(100, (n / (Object.values(analytics.skill_gaps)[0] || 1)) * 85)}%;opacity:${1 - i * 0.18}"></div></div><span>${n} roles</span></div>`,
        )
        .join("") ||
      '<p class="subtle">Analyze a job match to see learning priorities.</p>'
    }</div></div></div></section><aside class="right-column"><div class="resume-panel panel reveal"><div class="section-title"><h2>Your resume</h2><span class="status-label"><span></span>${resumes.length ? "Analyzed" : "Get started"}</span></div><div class="resume-file"><span class="file-icon">${icon("file-text")}</span><div><strong>${resumes.length ? e(resumes[0].filename) : "Add your experience"}</strong><span>${resumes.length ? "Your career story, in one place" : "PDF or DOCX · Up to 5 MB"}</span></div></div><div class="resume-divider"></div><div class="resume-score"><div class="mini-gauge" style="--score:${resumes.length ? 86 : 0}"><span>${resumes.length ? resumes[0].skills.length : 0}</span></div><div><strong>${resumes.length ? "You have a strong foundation" : "Let’s find your strengths"}</strong><p>${resumes.length ? "Skills discovered in your resume. Ready for your next move." : "Upload your resume for a personal skill breakdown."}</p></div></div><a href="#/upload" class="btn btn-outline w-100">${icon("file-pen-line")} ${resumes.length ? "Manage resume" : "Upload resume"} ${icon("arrow-right")}</a></div><div class="learning-panel panel reveal"><div class="section-title"><h2>A little learning. A big leap.</h2><span class="tiny-spark">${icon("sparkles")}</span></div><p>Build the skills that open more doors.</p>${Object.keys(
      analytics.skill_gaps,
    )
      .slice(0, 2)
      .map(
        (s, i) =>
          `<a class="learning-item" href="https://www.freecodecamp.org/news/search/?query=${encodeURIComponent(s)}" target="_blank" rel="noopener noreferrer"><span class="learning-logo ${i ? "cyan" : ""}">${icon(i ? "network" : "triangle")}</span><span><strong>${e(s)} fundamentals</strong><small>Explore learning resources</small></span>${icon("arrow-up-right")}</a>`,
      )
      .join(
        "",
      )}<a href="#/analytics" class="text-link learning-link">Explore your skill gaps ${icon("arrow-right")}</a></div><div class="quote-card reveal"><span>“</span><p>The best way to predict your<br>future is to create it.</p><small>YOUR NEXT CHAPTER IS WAITING</small><div class="quote-star">✳</div></div></aside></div>`,
    "Overview",
  );
  mountScene();
}
function empty(
  title: string,
  text: string,
  button = "",
  path = "upload",
): string {
  return `<div class="empty-state">${icon("sparkles")}<h2>${title}</h2><p>${text}</p>${button ? `<a class="btn btn-primary" href="#/${path}">${button}${icon("arrow-right")}</a>` : ""}</div>`;
}
async function mountScene(): Promise<void> {
  const el = document.getElementById("skill-scene");
  if (!el || reduced || navigator.hardwareConcurrency <= 2) return;
  const id = renderId;
  try {
    const { createScene } = await import("./lib/scene");
    if (id === renderId) cleanupScene = createScene(el);
  } catch {
    /* CSS constellation remains available without WebGL. */
  }
}
function uploadPage(): void {
  shell(
    `${heading("YOUR EXPERIENCE. YOUR POTENTIAL.", "Let your skills speak.", "Upload your resume. We’ll connect the dots.")}<div class="upload-layout"><section class="panel upload-panel reveal"><span class="step-label">01 / YOUR RESUME</span><h2>A small upload. A big first step.</h2><p>We’ll extract your skills and help you find the right opportunities.</p><form id="upload-form"><label class="dropzone" for="resume-file" tabindex="0"><span class="upload-orb">${icon("cloud-upload")}</span><strong>Drop your resume here</strong><span>or <b>browse files</b> from your device</span><small>PDF or DOCX · Maximum 5 MB</small><input id="resume-file" name="resume" type="file" accept=".pdf,.docx" class="visually-hidden"></label><div id="selected-file" aria-live="polite"></div><div class="privacy-note">${icon("shield-check")} Your resume is private. Recruiters only see your name and match score when you apply.</div><button class="btn btn-primary w-100" type="submit">Analyze my resume ${icon("sparkles")}</button><div class="form-error" role="alert"></div></form></section><aside><div class="panel upload-explainer reveal"><span class="eyebrow">A CLEARER PICTURE</span><h2>More than keywords.</h2>${[
      [
        "file-scan",
        "Read between the lines",
        "We extract skills from your experience using natural language processing.",
      ],
      [
        "scan-line",
        "Find your fit",
        "Semantic similarity and skill overlap help surface relevant roles.",
      ],
      [
        "route",
        "See a path forward",
        "Understand your gaps and discover what to learn next.",
      ],
    ]
      .map(
        ([ic, t, d], i) =>
          `<div class="explain-step"><span>${icon(ic)}</span><div><small>0${i + 1}</small><h3>${t}</h3><p>${d}</p></div></div>`,
      )
      .join("")}</div>${
      resumes.length
        ? `<div class="panel existing-resume"><h3>Your latest resume</h3><p>${e(resumes[0].filename)}</p><div class="strength-chips">${resumes[0].skills
            .slice(0, 6)
            .map((s) => chip(s, "strength"))
            .join(
              "",
            )}</div>${!demo ? `<button class="text-link danger delete-resume" data-id="${resumes[0].id}">Delete resume ${icon("trash-2")}</button>` : ""}</div>`
        : ""
    }</aside></div>`,
    "My resume",
  );
}
async function jobsPage(): Promise<void> {
  shell(
    `${heading("FIND YOUR NEXT CHAPTER.", "Good work starts with a good fit.", "Explore roles that value what you bring to the table.")}<form id="job-search" class="search-panel panel"><div class="search-field">${icon("search")}<input name="q" aria-label="Job title, company, or skill" placeholder="Job title, company, or skill"></div><div class="search-field location-field">${icon("map-pin")}<select name="location" aria-label="Location"><option value="">All locations</option><option>Remote</option><option>San Francisco</option><option>New York</option><option>London</option><option>Bengaluru</option></select></div><select name="kind" aria-label="Job type"><option value="">All job types</option><option>Full-time</option><option>Part-time</option><option>Contract</option><option>Internship</option></select><button class="btn btn-primary">Find my next move ${icon("arrow-right")}</button></form><div class="jobs-toolbar"><span id="jobs-count">Finding your possibilities…</span><label class="save-filter"><input type="checkbox" id="saved-only"> Saved jobs only</label></div><div id="job-results" class="all-jobs-grid"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div><div id="pagination" class="pagination-controls"></div>`,
    "Find jobs",
  );
  jobPage = 1;
  await searchJobs();
}
async function searchJobs(): Promise<void> {
  const form = $("#job-search");
  const q = String(form.find("[name=q]").val() || "");
  const location = String(form.find("[name=location]").val() || "");
  const kind = String(form.find("[name=kind]").val() || "");
  let total = 0;
  let list: Job[] = [];
  const savedOnly = $("#saved-only").is(":checked");
  const accepts = (job: Job): boolean =>
    `${job.title} ${job.company} ${job.skills.join(" ")}`
      .toLowerCase()
      .includes(q.toLowerCase()) &&
    job.location.includes(location) &&
    (!kind || job.employment_type === kind);
  if (demo) {
    list = demoJobs.filter(
      (j) => accepts(j) && (!savedOnly || bookmarks.includes(j.id)),
    );
    total = list.length;
  } else if (savedOnly) {
    const saved = await Promise.allSettled(
      bookmarks.map((id) => api<Job>(`/jobs/${id}`)),
    );
    list = saved.flatMap((result) =>
      result.status === "fulfilled" && accepts(result.value)
        ? [result.value]
        : [],
    );
    total = list.length;
    list = list.slice((jobPage - 1) * 12, jobPage * 12);
  } else {
    const data = await api<{ items: Job[]; total: number }>(
      `/jobs?${new URLSearchParams({ q, location, kind, page: String(jobPage), size: "12" })}`,
    );
    list = data.items;
    total = data.total;
    jobs = list;
  }
  $("#jobs-count").text(`${total} opportunities to make your next move`);
  $("#job-results").html(
    list.map(jobCard).join("") ||
      empty(
        "A different search, a new possibility.",
        "Try another skill, location, or job type.",
      ),
  );
  $("#pagination").html(
    total > 12
      ? `<button class="btn btn-outline page-prev" ${jobPage === 1 ? "disabled" : ""}>${icon("arrow-left")} Previous</button><span>Page ${jobPage} of ${Math.ceil(total / 12)}</span><button class="btn btn-outline page-next" ${jobPage * 12 >= total ? "disabled" : ""}>Next ${icon("arrow-right")}</button>`
      : "",
  );
  finish();
}
async function jobDetail(id: number): Promise<void> {
  const job = demo
    ? demoJobs.find((j) => j.id === id)
    : await api<Job>(`/jobs/${id}`);
  if (!job) {
    notFound();
    return;
  }
  shell(
    `<a class="back-link" href="#/jobs">${icon("arrow-left")} All opportunities</a><div class="job-detail-layout"><article class="panel job-detail reveal"><div class="detail-company">${companyLogo(job.company)}<span>${e(job.company)}<small>Build something meaningful.</small></span><button class="icon-btn save-job" data-id="${job.id}" aria-label="Save job">${icon("bookmark")}</button></div><h1>${e(job.title)}</h1><div class="detail-meta"><span>${icon("map-pin")}${e(job.location)}</span><span>${icon("clock-3")}${e(job.employment_type)}</span><span>${icon("banknote")}${salary(job.salary_min, job.salary_max)} / year</span></div><hr><h2>About the opportunity</h2><div class="job-description">${e(job.description)}</div><h2>Skills you’ll bring</h2><div class="strength-chips">${job.skills.map((s) => chip(s, "strength")).join("")}</div></article><aside><div class="panel fit-panel"><span class="eyebrow">YOUR NEXT CHAPTER?</span><h2>See how you fit.</h2><p>Your experience deserves the right opportunity. Let’s connect the dots.</p><button class="btn btn-primary w-100 analyze-job" data-id="${job.id}">${icon("sparkles")} Analyze my match</button><button class="btn btn-outline w-100 apply-job" data-id="${job.id}">${icon("send")} Apply for this role</button><small>${demo ? "Sample opening. Sign in to apply to live postings." : "Your latest resume will be used for this application."}</small></div></aside></div>`,
    "Job details",
  );
}
async function matchesPage(): Promise<void> {
  if (!demo) matches = await api<Match[]>("/matches");
  else matches = demoJobs.map(demoMatch);
  shell(
    `${heading("YOUR SKILLS, IN THE RIGHT PLACE.", "A match with more meaning.", "Understand what fits, what’s missing, and what comes next.")}<div class="all-jobs-grid">${matches.map((m) => jobCard({ ...m.job, score: m.score })).join("") || empty("Your first match is one step away.", "Choose a role and analyze how your resume fits.", "Explore opportunities", "jobs")}</div>`,
    "My matches",
  );
}
function matchPage(match: Match): void {
  shell(
    `<a class="back-link" href="#/jobs/${match.job_id}">${icon("arrow-left")} Back to opportunity</a>${heading("CLARITY FOR YOUR NEXT MOVE.", `You + ${e(match.job.company)}.`, `Here’s how your experience aligns with ${e(match.job.title)}.`)}<div class="match-layout"><div class="panel match-score-panel reveal"><div class="big-gauge" style="--score:${match.score}"><span>${Math.round(match.score)}<small>%</small></span></div><span class="match-pill">${icon("sparkles")}${scoreLabel(match.score)}</span><h2>Your potential, in perspective.</h2><p>${match.method === "sample" ? "Illustrative preview score. Upload a real resume to get your own analysis." : match.method === "hybrid" ? "65% semantic similarity + 35% skill overlap. A guide to fit, never a hiring decision." : "Keyword overlap only. The semantic model is unavailable; this score reflects identified skills."}</p><div class="score-breakdown"><span>Skill overlap <b>${Math.round(match.keyword_score)}%</b></span><span>Semantic similarity <b>${match.method === "keyword" ? "Unavailable" : Math.round(match.semantic_score) + "%"}</b></span></div><button class="btn btn-primary w-100 apply-job" data-id="${match.job_id}">Take the next step ${icon("arrow-up-right")}</button></div><div><div class="panel match-skills reveal"><h2>${icon("circle-check")} What you bring</h2><p>Your strengths align with these role requirements.</p><div class="strength-chips">${match.matched.map((s) => chip(s, "strength")).join("") || '<span class="subtle">No exact skill matches identified yet.</span>'}</div><hr><h2>${icon("sprout")} Where you can grow</h2><p>A few new skills could open even more doors.</p><div class="strength-chips">${match.missing.map((s) => chip(s, "missing")).join("") || '<span class="subtle">You have every listed skill. Great alignment!</span>'}</div></div><div class="panel result-radar"><h2>Your fit, at a glance</h2><div class="chart-wrap"><canvas id="radar-chart" aria-label="Skill coverage radar chart" role="img"></canvas></div></div></div></div>${match.suggestions.length ? `<section class="result-learning">${sectionTitle("A path from here to there.", "Free learning resources for your next step.")}<div class="all-jobs-grid">${match.suggestions.map((s) => `<a class="panel course-card" href="${e(s.url)}" target="_blank" rel="noopener noreferrer">${icon("book-open")}<h3>${e(s.title)}</h3><p>Explore tutorials and build something with your new skills.</p><span class="text-link">Start exploring ${icon("arrow-up-right")}</span></a>`).join("")}</div></section>` : ""}`,
    "Match results",
  );
  void renderCharts("radar", match);
  if (!reduced) {
    gsap.fromTo(
      ".big-gauge",
      { "--score": 0 },
      { "--score": match.score, duration: 1.3, ease: "power2.out" },
    );
    gsap.from(".match-skills .skill-chip", {
      opacity: 0,
      y: 15,
      scale: 0.9,
      stagger: 0.08,
      duration: 0.5,
    });
  }
}
async function analyticsPage(): Promise<void> {
  if (!demo) analytics = await api<Analytics>("/analytics");
  shell(
    `${heading("A LITTLE PERSPECTIVE GOES A LONG WAY.", "See how far you’re going.", "Turn your career activity into a clearer plan.")}${stats()}<div class="analytics-grid">${[
      [
        "gap-chart",
        "Your next skills",
        "Most common gaps across analyzed roles",
      ],
      [
        "distribution-chart",
        "Finding your fit",
        "Your match score distribution",
      ],
      [
        "demand-chart",
        "What teams are looking for",
        "Most requested skills in active job postings",
      ],
      [
        "activity-chart",
        "Every application is progress",
        "Applications submitted over time",
      ],
    ]
      .map(
        ([id, t, s]) =>
          `<section class="panel chart-panel reveal">${sectionTitle(t, s)}<div class="chart-wrap"><canvas id="${id}" aria-label="${t}" role="img"></canvas></div></section>`,
      )
      .join("")}</div>`,
    "Insights",
  );
  void renderCharts("analytics");
}
async function renderCharts(kind: string, match?: Match): Promise<void> {
  const id = renderId;
  const { mountCharts } = await import("./lib/charts");
  if (id === renderId)
    cleanupCharts = mountCharts(kind, analytics, match, reduced);
}
async function applicationsPage(): Promise<void> {
  const applications = demo
    ? demoJobs.slice(0, 3).map((j, i) => ({
        id: j.id,
        job: j,
        candidate: "Alex Morgan",
        status: i === 0 ? "Interview" : "Applied",
        score: j.score || 0,
        created_at: "2026-09-26",
      }))
    : await api<Application[]>("/applications");
  const recruiter = user?.role === "recruiter" || user?.role === "admin";
  shell(
    `${heading("ONE STEP CLOSER. EVERY TIME.", recruiter ? "Meet your next great hire." : "Your next chapter, in motion.", recruiter ? "Candidates ranked by resume fit. Use scores as a starting point for a fair, human review." : "Keep track of the opportunities you’ve put yourself forward for.")}<div class="panel table-panel"><div class="table-responsive"><table class="app-table"><thead><tr><th>${recruiter ? "Candidate" : "Opportunity"}</th><th>${recruiter ? "Role" : "Company"}</th><th>Match</th><th>Status</th><th>Applied</th></tr></thead><tbody>${applications.map((a) => `<tr><td><strong>${e(recruiter ? a.candidate : a.job.title)}</strong></td><td>${e(recruiter ? a.job.title : a.job.company)}</td><td><span class="match-pill">${a.score === null ? "Pending" : Math.round(a.score) + "%"}</span></td><td>${recruiter ? `<select class="status-select" data-id="${a.id}" aria-label="Application status">${["Applied", "Reviewing", "Interview", "Rejected", "Hired"].map((s) => `<option ${s === a.status ? "selected" : ""}>${s}</option>`).join("")}</select>` : `<span class="application-status ${a.status.toLowerCase()}">${e(a.status)}</span>`}</td><td>${new Date(a.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</td></tr>`).join("")}</tbody></table></div>${!applications.length ? empty("Your story is still unfolding.", "Apply for a role to start tracking your progress.", "Find opportunities", "jobs") : ""}</div>`,
    recruiter ? "Candidates" : "Applications",
  );
}
function authPage(register = false): void {
  $("#app").html(
    `<main class="auth-layout" id="main-content"><div class="auth-story">${logo()}<div><span class="hero-eyebrow"><span class="live-dot"></span> THE NEXT CHAPTER IS YOURS</span><h1>You’re more than<br>a <span>resume.</span></h1><p>Find the opportunities that see what you bring.<br>And the possibilities you haven’t seen yet.</p><div class="auth-art"><div class="orbit orbit-one"></div><div class="core-orb">${icon("sparkles")}</div><span class="floating-skill node-react">${icon("atom")} Your skills</span><span class="floating-skill node-design">${icon("briefcase-business")} Your next move</span></div></div><span class="auth-story-footer">A little clarity. A big step forward.</span></div><div class="auth-form-side"><a class="back-link" href="#/dashboard">${icon("arrow-left")} Explore the workspace</a><form id="auth-form" data-mode="${register ? "register" : "login"}"><span class="eyebrow">${register ? "POSSIBILITIES START HERE" : "GOOD TO SEE YOU AGAIN"}</span><h2>${register ? "Make your next move." : "Welcome back."}</h2><p>${register ? "A clearer path to work that fits you." : "Your next chapter is right where you left it."}</p>${register ? '<label for="name">Your name</label><input id="name" name="name" required minlength="2" maxlength="100" autocomplete="name" placeholder="Alex Morgan">' : ""}<label for="email">Email address</label><input id="email" name="email" type="email" required autocomplete="email" placeholder="you@example.com"><label for="password">Password</label><div class="password-field"><input id="password" name="password" type="password" required minlength="${register ? 10 : 1}" maxlength="128" autocomplete="${register ? "new-password" : "current-password"}" placeholder="${register ? "At least 10 characters" : "Your password"}"><button type="button" class="icon-btn toggle-password" aria-label="Show password">${icon("eye")}</button></div>${register ? '<label for="role">I’m here to</label><select id="role" name="role"><option value="candidate">Find my next opportunity</option><option value="recruiter">Find great people</option></select>' : ""}<div class="form-error" role="alert"></div><button class="btn btn-primary w-100" type="submit">${register ? "Create my account" : "Sign in"} ${icon("arrow-right")}</button><div class="auth-switch">${register ? "Already part of SkillMatch?" : "New here?"} <a href="#/${register ? "login" : "register"}">${register ? "Sign in" : "Create an account"}</a></div><div class="auth-divider"><span>just looking around?</span></div><a href="#/dashboard" class="btn btn-outline w-100">Explore the sample workspace ${icon("arrow-up-right")}</a></form><small class="auth-privacy">${icon("shield-check")} Your career story stays yours.</small></div></main>`,
  );
  finish();
}
function landing(): void {
  $("#app").html(
    `<div class="landing"><header class="landing-nav">${logo()}<nav aria-label="Public navigation"><a href="#how-it-works" class="scroll-link">How it works</a><a href="#/jobs">Explore jobs</a><a href="#/login">Sign in</a><a href="#/register" class="btn btn-primary">Find my next move ${icon("arrow-up-right")}</a></nav></header><main id="main-content"><section class="landing-hero"><div class="landing-hero-copy"><span class="hero-eyebrow"><span class="live-dot"></span> A LITTLE CLARITY. A WORLD OF POSSIBILITY.</span><h1>Your skills.<br>Your potential.<br><span>Your next chapter.</span></h1><p>You bring more to the table than a list of keywords.<br>Find opportunities that see the full picture.</p><div class="landing-buttons"><a href="#/register" class="btn btn-primary magnetic">Discover where you belong ${icon("arrow-up-right")}</a><a href="#/dashboard" class="btn btn-outline">Take a look around ${icon("arrow-right")}</a></div><div class="landing-proof">${icon("shield-check")} Private by design <span>•</span> Transparent matching <span>•</span> Built around you</div></div><div class="landing-scene"><div id="skill-scene"></div><div class="orbital-glow"></div><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="core-orb">${icon("sparkles")}</div><div class="floating-skill node-react">${icon("atom")} React</div><div class="floating-skill node-typescript"><b>TS</b> TypeScript</div><div class="floating-skill node-design">${icon("figma")} Design</div><div class="floating-skill node-python">${icon("code-2")} Python</div></div><span class="scroll-cue">A clearer path starts here ${icon("arrow-down")}</span></section><section class="landing-companies"><span>EXPLORE THE KIND OF TEAMS YOU COULD JOIN</span><div><b>◒ Linear</b><b>▲ Vercel</b><b>▣ Notion</b><b>stripe</b><b>✳ Figma</b></div><small>Illustrative companies from our sample job catalog.</small></section><section id="how-it-works" class="story-section"><div class="story-heading"><span class="eyebrow">FROM WHAT YOU KNOW TO WHERE YOU GO</span><h2>A clearer path.<br>Three simple steps.</h2><p>Less guesswork. More possibility.</p></div><div class="story-steps">${[
      [
        "01",
        "file-scan",
        "Start with your story.",
        "Upload your resume. We discover the skills woven through your experience.",
      ],
      [
        "02",
        "scan-line",
        "See where you fit.",
        "Understand your match with each role through semantic context and skill overlap.",
      ],
      [
        "03",
        "sprout",
        "Grow into what’s next.",
        "Get a clear picture of your strengths and a practical path to close the gaps.",
      ],
    ]
      .map(
        ([n, i, t, p]) =>
          `<article class="story-step"><span class="story-number">${n}</span><span class="story-icon">${icon(i)}</span><h3>${t}</h3><p>${p}</p></article>`,
      )
      .join(
        "",
      )}</div></section><section class="landing-cta"><span class="eyebrow">YOUR FUTURE ISN’T A KEYWORD.</span><h2>Let’s find where<br>you <span>belong.</span></h2><a href="#/register" class="btn btn-primary">Make my next move ${icon("arrow-up-right")}</a></section></main><footer class="landing-footer">${logo()}<span>Made for your next move.</span><a href="#/dashboard">Explore the workspace ${icon("arrow-up-right")}</a></footer></div>`,
  );
  finish();
  mountScene();
  if (!reduced) {
    gsap.utils.toArray<HTMLElement>(".story-step").forEach((el) =>
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: "top 88%" },
        opacity: 0,
        y: 45,
        duration: 0.8,
      }),
    );
    ScrollTrigger.create({
      trigger: ".story-section",
      start: "top 100px",
      end: "bottom 80%",
      pin: ".story-heading",
      pinSpacing: false,
    });
    gsap.to(".landing-scene", {
      y: 100,
      scrollTrigger: {
        trigger: ".landing-hero",
        start: "top top",
        end: "bottom top",
        scrub: 1,
      },
    });
  }
}
async function recruiterPage(): Promise<void> {
  if (!user) {
    authPage();
    return;
  }
  const [data, a] = await Promise.all([
    api<{ items: Job[] }>("/jobs/mine"),
    api<Analytics>("/analytics"),
  ]);
  analytics = a;
  shell(
    `${heading("GOOD TEAMS START WITH GREAT CONNECTIONS.", "Find your next great hire.", "Connect with people whose skills fit your ambition.", `<a class="btn btn-primary" href="#/post-job">${icon("plus")} Post a job</a>`)}${stats()}${sectionTitle("Your opportunities", "Manage your active job postings.")}<div class="all-jobs-grid">${
      data.items
        .map(
          (j) =>
            `<div class="panel managed-job"><h3>${e(j.title)}</h3><p>${e(j.company)} · ${e(j.location)}</p><div class="strength-chips">${j.skills
              .slice(0, 3)
              .map((s) => chip(s))
              .join(
                "",
              )}</div><div class="manage-actions"><a href="#/post-job/${j.id}" class="text-link">Edit ${icon("pencil")}</a><button class="text-link danger delete-job" data-id="${j.id}">Close role ${icon("x")}</button></div></div>`,
        )
        .join("") ||
      empty(
        "Your next teammate is out there.",
        "Post a role to start connecting.",
        "Post your first job",
        "post-job",
      )
    }</div>`,
    "Recruiter overview",
  );
}
async function postJob(id?: number): Promise<void> {
  if (!user) {
    authPage();
    return;
  }
  const job = id ? await api<Job>(`/jobs/${id}`) : null;
  shell(
    `${heading("MAKE ROOM FOR GREAT PEOPLE.", job ? "Refine your opportunity." : "A great role deserves a great match.", "Tell candidates what they’ll build, learn, and bring to your team.")}<form id="post-job-form" class="panel job-form" data-id="${id || ""}"><div class="row g-4">${[
      ["title", "Job title", "Senior Frontend Developer"],
      ["company", "Company", "Your company"],
      ["location", "Location", "Remote"],
    ]
      .map(
        ([k, l, p]) =>
          `<div class="col-md-6"><label for="${k}">${l}</label><input id="${k}" name="${k}" required maxlength="100" value="${e(job?.[k as keyof Job] || "")}" placeholder="${p}"></div>`,
      )
      .join(
        "",
      )}<div class="col-md-6"><label for="employment_type">Employment type</label><select id="employment_type" name="employment_type">${["Full-time", "Part-time", "Contract", "Internship"].map((t) => `<option ${job?.employment_type === t ? "selected" : ""}>${t}</option>`).join("")}</select></div><div class="col-md-6"><label for="salary_min">Minimum annual salary (USD)</label><input id="salary_min" name="salary_min" type="number" min="0" max="10000000" required value="${job?.salary_min || ""}" placeholder="120000"></div><div class="col-md-6"><label for="salary_max">Maximum annual salary (USD)</label><input id="salary_max" name="salary_max" type="number" min="0" max="10000000" required value="${job?.salary_max || ""}" placeholder="160000"></div><div class="col-12"><label for="skills">Required skills</label><input id="skills" name="skills" required value="${e(job?.skills.join(", ") || "")}" placeholder="React, TypeScript, CSS"><small>Separate each skill with a comma. Up to 30 skills.</small></div><div class="col-12"><label for="description">About the opportunity</label><textarea id="description" name="description" required minlength="40" maxlength="20000" rows="8" placeholder="Describe the work, the team, and what success looks like…">${e(job?.description || "")}</textarea></div></div><div class="form-error" role="alert"></div><button class="btn btn-primary" type="submit">${job ? "Save changes" : "Publish opportunity"} ${icon("arrow-up-right")}</button></form>`,
    job ? "Edit job" : "Post a job",
  );
}
async function adminPage(): Promise<void> {
  if (!user || user.role !== "admin") {
    shell(
      empty(
        "This space is for administrators.",
        "Sign in with an administrator account to manage the platform.",
        "Sign in",
        "login",
      ),
      "Administration",
    );
    return;
  }
  const page =
    Number(new URLSearchParams(location.hash.split("?")[1]).get("page")) || 1;
  const data = await api<{
    stats: Record<string, number>;
    users: User[];
    jobs: Job[];
  }>(`/admin?page=${page}`);
  shell(
    `${heading("THE BIGGER PICTURE.", "Platform overview.", "Manage accounts and keep the opportunity catalog healthy.")}<div class="stats-grid">${Object.entries(
      data.stats,
    )
      .map(
        ([k, v]) =>
          `<div class="stat-card"><span>${e(k)}</span><div class="stat-value">${v}</div></div>`,
      )
      .join(
        "",
      )}</div><div class="panel table-panel"><h2>People on the platform</h2><div class="table-responsive"><table class="app-table"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Account</th></tr></thead><tbody>${data.users.map((u) => `<tr><td>${e(u.name)}</td><td>${e(u.email)}</td><td>${u.role}</td><td><button class="btn btn-outline toggle-user" data-id="${u.id}" data-active="${u.active}" ${u.id === user?.id ? "disabled" : ""}>${u.active ? "Disable" : "Enable"}</button></td></tr>`).join("")}</tbody></table></div></div><div class="panel table-panel admin-jobs"><h2>Active job postings</h2><div class="table-responsive"><table class="app-table"><thead><tr><th>Role</th><th>Company</th><th>Manage</th></tr></thead><tbody>${data.jobs.map((j) => `<tr><td>${e(j.title)}</td><td>${e(j.company)}</td><td><button class="text-link danger delete-job" data-id="${j.id}">Close role</button></td></tr>`).join("")}</tbody></table></div></div><div class="pagination-controls"><a class="btn btn-outline" href="#/admin?page=${Math.max(1, page - 1)}">Previous</a><span>Page ${page}</span><a class="btn btn-outline" href="#/admin?page=${page + 1}">Next</a></div>`,
    "Administration",
  );
}
function notFound(): void {
  shell(
    `<div class="not-found"><span>404</span><h1>A little off the path.</h1><p>This page isn’t here. Your next opportunity still is.</p><a class="btn btn-primary" href="#/dashboard">Back to your workspace ${icon("arrow-right")}</a></div>`,
    "Page not found",
  );
}
async function navigate(): Promise<void> {
  renderId++;
  cleanupScene?.();
  cleanupCharts?.();
  ScrollTrigger.getAll().forEach((t) => t.kill());
  $("body").removeClass("nav-open");
  selectedFile = null;
  const path = route().split("?")[0];
  window.scrollTo(0, 0);
  try {
    if (path === "landing") {
      landing();
      return;
    }
    if (path === "login" || path === "register") {
      authPage(path === "register");
      return;
    }
    if (!demo && !user) {
      authPage();
      return;
    }
    if (
      !demo &&
      user?.role !== "candidate" &&
      ["dashboard", "upload", "matches"].includes(path)
    ) {
      await recruiterPage();
      return;
    }
    if (path === "dashboard") {
      await loadCandidate();
      dashboard();
    } else if (path === "upload") {
      if (!demo) resumes = await api<Resume[]>("/resumes");
      uploadPage();
    } else if (path === "jobs") await jobsPage();
    else if (/^jobs\/\d+$/.test(path))
      await jobDetail(Number(path.split("/")[1]));
    else if (path === "matches") await matchesPage();
    else if (/^matches\/\d+$/.test(path)) {
      const id = Number(path.split("/")[1]);
      let match = demo
        ? demoMatch(demoJobs.find((j) => j.id === id) || demoJobs[0])
        : (await api<Match[]>("/matches")).find((m) => m.job_id === id);
      if (match) matchPage(match);
      else notFound();
    } else if (path === "analytics") await analyticsPage();
    else if (path === "applications") await applicationsPage();
    else if (path === "recruiter") await recruiterPage();
    else if (path.startsWith("post-job"))
      await postJob(Number(path.split("/")[1]) || undefined);
    else if (path === "admin") await adminPage();
    else notFound();
  } catch (err) {
    shell(
      empty(
        "Let’s try that again.",
        e((err as Error).message),
        "Back to overview",
        "dashboard",
      ),
      "Something went wrong",
    );
    toast((err as Error).message, "error");
  }
}
async function busy(
  button: JQuery,
  action: () => Promise<void>,
): Promise<void> {
  const old = button.html();
  button
    .prop("disabled", true)
    .html('<span class="button-spinner"></span> Working…');
  try {
    await action();
  } catch (err) {
    toast((err as Error).message, "error");
    button
      .closest("form")
      .find(".form-error")
      .text((err as Error).message);
  } finally {
    button.prop("disabled", false).html(old);
    createIcons({ icons });
  }
}
function requireAccount(): boolean {
  if (demo) {
    toast("Create an account to use your own resume and apply for live roles.");
    location.hash = "/register";
    return false;
  }
  return true;
}
async function latestResume(): Promise<Resume> {
  if (demo) return demoResume;
  resumes = await api<Resume[]>("/resumes");
  if (!resumes.length) {
    location.hash = "/upload";
    throw new Error("Upload a resume first so we can understand your skills.");
  }
  return resumes[0];
}
function selectFile(file: File): void {
  const error = validateFile(file);
  if (error) {
    toast(error, "error");
    selectedFile = null;
    $("#selected-file").empty();
    return;
  }
  selectedFile = file;
  $("#selected-file").html(
    `<div class="selected-file">${icon("file-check")}<span>${e(file.name)}<small>${(file.size / 1024).toFixed(0)} KB · Ready to analyze</small></span><button type="button" class="icon-btn clear-file" aria-label="Remove selected file">${icon("x")}</button></div>`,
  );
  createIcons({ icons });
}
$(document).on("click", ".menu-toggle,.sidebar-scrim", () =>
  $("body").toggleClass("nav-open"),
);
$(document).on("click", ".notification-button", () =>
  toast(
    demo
      ? "You’re viewing a sample workspace. Create an account to start your own journey."
      : "You’re all caught up. Your latest application statuses are in Applications.",
  ),
);
$(document).on("click", "#account-button", function () {
  if (demo) {
    location.hash = "/login";
    return;
  }
  void busy($(this), async () => {
    await api("/auth/logout", "POST");
    setToken("");
    localStorage.removeItem("sm-session");
    user = null;
    demo = true;
    bookmarks = readBookmarks();
    location.hash = "/login";
  });
});
$(document).on("click", ".save-job", function () {
  const id = Number($(this).data("id"));
  const saved = bookmarks.includes(id);
  bookmarks = saved ? bookmarks.filter((b) => b !== id) : [...bookmarks, id];
  localStorage.setItem(bookmarkKey(), JSON.stringify(bookmarks));
  $(this).toggleClass("saved", !saved).attr("aria-pressed", String(!saved));
  toast(
    saved
      ? "Opportunity removed from saved jobs."
      : "Saved for your next move. Find it in saved jobs.",
  );
});
$(document).on("submit", "#job-search", function (ev) {
  ev.preventDefault();
  jobPage = 1;
  void busy($(this).find("button"), searchJobs);
});
$(document).on("change", "#saved-only", () => {
  jobPage = 1;
  void searchJobs().catch((err) => toast(err.message, "error"));
});
$(document).on("click", ".page-prev,.page-next", function () {
  jobPage += $(this).hasClass("page-next") ? 1 : -1;
  void busy($(this), searchJobs);
});
$(document).on("change", "#resume-file", function () {
  const file = (this as HTMLInputElement).files?.[0];
  if (file) selectFile(file);
});
$(document).on("keydown", ".dropzone", function (ev) {
  if (ev.key === "Enter" || ev.key === " ") {
    ev.preventDefault();
    $("#resume-file").trigger("click");
  }
});
$(document).on("dragover", ".dropzone", function (ev) {
  ev.preventDefault();
  $(this).addClass("dragging");
});
$(document).on("dragleave", ".dropzone", function () {
  $(this).removeClass("dragging");
});
$(document).on("drop", ".dropzone", function (ev) {
  ev.preventDefault();
  $(this).removeClass("dragging");
  const file = (ev.originalEvent as DragEvent).dataTransfer?.files[0];
  if (file) selectFile(file);
});
$(document).on("click", ".clear-file", () => {
  selectedFile = null;
  $("#resume-file").val("");
  $("#selected-file").empty();
});
$(document).on("submit", "#upload-form", function (ev) {
  ev.preventDefault();
  if (!selectedFile) {
    $(this).find(".form-error").text("Choose a PDF or DOCX resume first.");
    return;
  }
  if (!requireAccount()) return;
  const data = new FormData();
  data.append("file", selectedFile);
  void busy($(this).find("[type=submit]"), async () => {
    const resume = await api<Resume>("/resumes", "POST", data);
    resumes.unshift(resume);
    toast(`Your story, understood. We found ${resume.skills.length} skills.`);
    location.hash = "/dashboard";
  });
});
$(document).on("click", ".delete-resume", function () {
  const id = $(this).data("id");
  void busy($(this), async () => {
    await api(`/resumes/${id}`, "DELETE");
    toast("Resume and related analyses deleted.");
    await navigate();
  });
});
$(document).on("submit", "#auth-form", function (ev) {
  ev.preventDefault();
  const form = $(this);
  if (!(this as HTMLFormElement).reportValidity()) return;
  const payload = Object.fromEntries(
    form.serializeArray().map((x) => [x.name, x.value]),
  );
  void busy(form.find("[type=submit]"), async () => {
    const data = await api<{ access_token: string; user: User }>(
      `/auth/${form.data("mode")}`,
      "POST",
      payload,
    );
    setToken(data.access_token);
    user = data.user;
    demo = false;
    bookmarks = readBookmarks();
    localStorage.setItem("sm-session", "active");
    toast(
      `Welcome${form.data("mode") === "login" ? " back" : ""}, ${user.name.split(" ")[0]}.`,
    );
    location.hash =
      user.role === "admin"
        ? "/admin"
        : user.role === "recruiter"
          ? "/recruiter"
          : "/dashboard";
  });
});
$(document).on("click", ".toggle-password", function () {
  const input = $("#password");
  const show = input.attr("type") === "password";
  input.attr("type", show ? "text" : "password");
  $(this).attr("aria-label", show ? "Hide password" : "Show password");
});
$(document).on("click", ".analyze-job", function () {
  const id = Number($(this).data("id"));
  void busy($(this), async () => {
    if (demo) {
      location.hash = `/matches/${id}`;
      return;
    }
    const resume = await latestResume();
    await api<Match>("/matches", "POST", { job_id: id, resume_id: resume.id });
    location.hash = `/matches/${id}`;
  });
});
$(document).on("click", ".apply-job", function () {
  if (!requireAccount()) return;
  const id = Number($(this).data("id"));
  void busy($(this), async () => {
    const resume = await latestResume();
    await api("/applications", "POST", { job_id: id, resume_id: resume.id });
    toast("You’ve made your move. Application submitted.");
    location.hash = "/applications";
  });
});
$(document).on("submit", "#post-job-form", function (ev) {
  ev.preventDefault();
  const form = $(this);
  if (!(this as HTMLFormElement).reportValidity()) return;
  const data: Record<string, unknown> = Object.fromEntries(
    form.serializeArray().map((x) => [x.name, x.value]),
  );
  data.skills = String(data.skills)
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  data.salary_min = Number(data.salary_min);
  data.salary_max = Number(data.salary_max);
  if (Number(data.salary_max) < Number(data.salary_min)) {
    form
      .find(".form-error")
      .text("Maximum salary must be at least the minimum.");
    return;
  }
  void busy(form.find("[type=submit]"), async () => {
    await api(
      form.data("id") ? `/jobs/${form.data("id")}` : "/jobs",
      form.data("id") ? "PUT" : "POST",
      data,
    );
    toast("Your opportunity is ready for its next great match.");
    location.hash = "/recruiter";
  });
});
$(document).on("click", ".delete-job", function () {
  const id = $(this).data("id");
  void busy($(this), async () => {
    await api(`/jobs/${id}`, "DELETE");
    toast("Role closed. Existing applications are retained.");
    await navigate();
  });
});
$(document).on("change", ".status-select", function () {
  const el = $(this);
  void api(`/applications/${el.data("id")}`, "PATCH", { status: el.val() })
    .then(() => toast("Application status updated."))
    .catch((err) => {
      toast(err.message, "error");
      void navigate();
    });
});
$(document).on("click", ".toggle-user", function () {
  const el = $(this);
  void busy(el, async () => {
    await api(`/admin/users/${el.data("id")}`, "PATCH", {
      active: !el.data("active"),
    });
    toast("Account updated.");
    await navigate();
  });
});
$(document).on("click", ".scroll-link", function (ev) {
  ev.preventDefault();
  document
    .getElementById("how-it-works")
    ?.scrollIntoView({ behavior: reduced ? "instant" : "smooth" });
});
$(document).on("keydown", (ev) => {
  if (ev.key === "/" && !$(ev.target).is("input,textarea,select")) {
    ev.preventDefault();
    location.hash = "/jobs";
    setTimeout(() => $("[name=q]").trigger("focus"), 100);
  }
  if (ev.key === "Escape") $("body").removeClass("nav-open");
});
if (!reduced) {
  $(document).on("mousemove", ".magnetic", function (ev) {
    const rect = this.getBoundingClientRect();
    gsap.to(this, {
      x: (ev.clientX - rect.left - rect.width / 2) * 0.1,
      y: (ev.clientY - rect.top - rect.height / 2) * 0.15,
      duration: 0.3,
    });
  });
  $(document).on("mouseleave", ".magnetic", function () {
    gsap.to(this, { x: 0, y: 0, duration: 0.3 });
  });
}
window.addEventListener("hashchange", () => void navigate());
async function start(): Promise<void> {
  if (localStorage.getItem("sm-session") === "active") {
    try {
      user = await refreshSession();
      demo = false;
      bookmarks = readBookmarks();
    } catch {
      localStorage.removeItem("sm-session");
    }
  }
  await navigate();
}
void start();

````

## frontend/src/styles/main.css

````css
:root {
  --bg: #0d0e14;
  --sidebar: #101117;
  --surface: #15161e;
  --surface-2: #1a1b25;
  --border: #282934;
  --text: #f2f1f7;
  --muted: #9695a7;
  --purple: #b59aff;
  --purple-bright: #a485f7;
  --cyan: #8ce1d4;
  --heading: "Manrope", sans-serif;
  --body: "DM Sans", sans-serif;
  --radius: 14px;
  --bs-body-bg: var(--bg);
  --bs-body-color: var(--text);
  --bs-border-color: var(--border);
  --bs-font-sans-serif: var(--body);
  color-scheme: dark;
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: var(--bg);
  font-family: var(--body);
  font-size: 14px;
  line-height: 1.6;
  color: var(--text);
  -webkit-font-smoothing: antialiased;
}
a {
  color: inherit;
  text-decoration: none;
}
button,
input,
select,
textarea {
  font: inherit;
}
button,
a,
input,
select,
textarea {
  touch-action: manipulation;
}
button {
  cursor: pointer;
}
button:disabled {
  cursor: wait;
  opacity: 0.5;
}
h1,
h2,
h3,
h4,
p {
  margin: 0;
}
h1,
h2,
h3,
h4 {
  font-family: var(--heading);
  font-weight: 700;
}
svg {
  width: 18px;
  height: 18px;
  stroke-width: 1.7;
  flex-shrink: 0;
}
button svg,
a svg {
  vertical-align: middle;
}
button {
  color: inherit;
}
a:hover {
  color: var(--purple);
}
:focus-visible {
  outline: 2px solid var(--cyan) !important;
  outline-offset: 4px;
}
::selection {
  background: #66509b;
  color: white;
}
.skip-link {
  position: fixed;
  top: -100px;
  left: 20px;
  z-index: 1000;
  background: var(--purple);
  color: #111;
  padding: 12px;
}
.skip-link:focus {
  top: 10px;
}
.subtle {
  color: var(--muted);
}
.sidebar {
  position: fixed;
  width: 230px;
  top: 0;
  bottom: 0;
  left: 0;
  padding: 33px 20px 0;
  border-right: 1px solid var(--border);
  background: var(--sidebar);
  display: flex;
  flex-direction: column;
  z-index: 30;
}
.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  font-family: var(--heading);
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -1px;
  white-space: nowrap;
}
.brand:hover {
  color: var(--text);
}
.brand-symbol {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 31px;
  height: 35px;
  color: var(--purple);
}
.brand-symbol svg {
  width: 33px;
  height: 33px;
  fill: var(--purple);
  stroke-width: 1.2;
}
.brand-ai {
  font-family: var(--body);
  font-size: 9px;
  letter-spacing: 0.1px;
  font-weight: 600;
  border: 1px solid #5d477e;
  padding: 2px 4px;
  border-radius: 4px;
  color: #c5adff;
  vertical-align: middle;
  margin-left: 6px;
}
.workspace-label {
  font-size: 9px;
  color: #737282;
  font-weight: 600;
  letter-spacing: 1.6px;
  margin: 45px 14px 16px;
}
.sidebar nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 13px;
  color: #a2a1af;
  font-size: 12px;
  padding: 12px 14px;
  border: 1px solid transparent;
  border-radius: 8px;
  min-height: 44px;
  transition: 0.2s;
}
.nav-item svg {
  width: 17px;
  height: 17px;
}
.nav-item:hover {
  background: #1a1923;
}
.nav-item.active {
  color: #c3a9ff;
  background: linear-gradient(100deg, #292135, #1f1b2b);
  border-color: #423151;
}
.nav-count {
  margin-left: auto;
  font-size: 10px;
  background: #24232e;
  padding: 1px 6px;
  border-radius: 4px;
  color: #bebaca;
}
.sidebar-bottom {
  margin-top: auto;
  padding-top: 50px;
}
.career-card {
  position: relative;
  padding: 19px 15px 16px;
  border: 1px solid #353040;
  border-radius: 10px;
  background:
    radial-gradient(ellipse at 100% 0%, #2d224155, transparent 70%), #191720;
  margin-bottom: 23px;
}
.tiny-spark {
  display: inline-flex;
  color: var(--purple);
}
.tiny-spark svg {
  width: 21px;
  height: 21px;
}
.career-card strong {
  display: block;
  font-family: var(--heading);
  font-size: 12px;
  line-height: 1.7;
  margin-top: 10px;
}
.career-card p {
  font-size: 10px;
  color: var(--muted);
  margin-top: 7px;
}
.career-card a {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #bda3f6;
  font-size: 10px;
  margin-top: 17px;
}
.career-card a svg {
  width: 14px;
}
.help-link {
  font-size: 10px;
  display: flex;
  gap: 9px;
  align-items: center;
  color: var(--muted);
  padding: 0 5px 25px;
}
.help-link svg {
  width: 15px;
}
.help-link svg:last-child {
  margin-left: auto;
  width: 12px;
}
.sidebar-profile {
  display: flex;
  gap: 10px;
  align-items: center;
  border-top: 1px solid var(--border);
  padding: 20px 0;
}
.avatar {
  height: 34px;
  width: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid #615748;
  background: linear-gradient(135deg, #c4ad88, #8c7766);
  color: #2d241f;
  font-family: var(--heading);
  font-size: 11px;
  font-weight: 800;
  border-radius: 50%;
  box-shadow: inset 0 0 0 3px #15161e50;
}
.avatar.small {
  width: 30px;
  height: 30px;
  font-size: 10px;
}
.sidebar-profile strong {
  display: block;
  font-size: 11px;
  font-weight: 500;
}
.sidebar-profile span {
  font-size: 9px;
  color: var(--muted);
  text-transform: capitalize;
}
.sidebar-profile .icon-btn {
  margin-left: auto;
}
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: #9391a5;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  flex-shrink: 0;
  transition: 0.2s;
}
.icon-btn:hover {
  color: var(--purple);
  background: #b59aff10;
}
.icon-btn svg {
  width: 17px;
  height: 17px;
}
.app-layout {
  margin-left: 230px;
  min-height: 100vh;
}
.topbar {
  height: 76px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 35px;
  gap: 16px;
  background: #0e0f15;
}
.topbar-title {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 11px;
  white-space: nowrap;
}
.breadcrumb-home {
  color: #777686;
}
.topbar-title svg {
  width: 12px;
  height: 12px;
  color: #656373;
}
.topbar-title strong {
  font-weight: 400;
  color: #c8c5d4;
}
.topbar-actions {
  display: flex;
  align-items: center;
  gap: 19px;
}
.top-search {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #858392;
  font-size: 10px;
}
.top-search svg {
  width: 15px;
}
.top-search kbd {
  font-family: var(--body);
  font-size: 10px;
  background: #191922;
  border: 1px solid #30303c;
  border-radius: 4px;
  margin-left: 20px;
  padding: 0 5px;
}
.demo-badge {
  border: 1px solid #30303b;
  border-radius: 6px;
  padding: 4px 8px;
  color: #aaa7b8;
  font-size: 9px;
  display: flex;
  align-items: center;
  gap: 7px;
}
.demo-badge span {
  width: 5px;
  height: 5px;
  background: var(--cyan);
  border-radius: 50%;
}
.notification-button {
  position: relative;
}
.notification-button b {
  position: absolute;
  width: 4px;
  height: 4px;
  background: var(--purple);
  border-radius: 50%;
  top: 6px;
  right: 7px;
}
.menu-toggle {
  display: none;
}
#main-content {
  padding: 34px 35px 22px;
  max-width: 1800px;
  margin: auto;
  outline: none;
}
.page-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 27px;
}
.eyebrow {
  font-size: 9px;
  letter-spacing: 1.8px;
  font-weight: 600;
  color: #898595;
  margin-bottom: 9px;
}
.page-heading h1 {
  font-size: 29px;
  letter-spacing: -1.1px;
  line-height: 1.4;
  font-weight: 600;
}
.greeting-dot {
  color: var(--purple);
}
.page-heading p {
  color: var(--muted);
  font-size: 12px;
  margin-top: 7px;
}
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  min-height: 40px;
  padding: 10px 17px;
  font-family: var(--body);
  font-size: 11px;
  font-weight: 600;
  border-radius: 7px;
  transition:
    transform 0.2s,
    background 0.2s,
    border-color 0.2s;
  white-space: nowrap;
  box-shadow: none !important;
}
.btn:hover {
  transform: translateY(-2px);
}
.btn svg {
  width: 15px;
  height: 15px;
}
.btn-primary {
  background: #b59af7;
  border: 1px solid #b99ffc;
  color: #1d142f;
}
.btn-primary:hover,
.btn-primary:active,
.btn-primary:focus {
  background: #c8b0ff !important;
  border-color: #cfbaff !important;
  color: #1d142f !important;
}
.btn-outline {
  border: 1px solid #3a3549;
  background: #211d2c;
  color: #c9b4f4;
}
.btn-outline:hover {
  background: #2b243a;
  color: #e0d0ff;
  border-color: #7a609d;
}
.btn-light {
  background: #eee6ff;
  color: #34264c;
  border: 1px solid #f0eaff;
  padding: 10px 17px;
}
.dashboard-hero {
  position: relative;
  min-height: 270px;
  border: 1px solid #41314f;
  background:
    radial-gradient(ellipse at 70% 60%, #34204775, transparent 60%),
    linear-gradient(105deg, #1e192a, #191722 55%, #201b2b);
  border-radius: var(--radius);
  overflow: hidden;
  display: grid;
  grid-template-columns: 1fr 1fr;
}
.hero-copy {
  padding: 30px 32px;
  z-index: 2;
}
.hero-eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 8px;
  font-weight: 600;
  letter-spacing: 1.8px;
  color: #c1afd4;
}
.live-dot {
  width: 5px;
  height: 5px;
  background: #c2a8fa;
  border-radius: 50%;
  box-shadow: 0 0 10px #a57afd;
}
.hero-copy h2 {
  font-size: 28px;
  line-height: 1.35;
  letter-spacing: -0.9px;
  margin: 15px 0 11px;
  font-weight: 500;
}
.hero-copy h2 span {
  color: #c7a9fa;
}
.hero-copy > p {
  font-size: 11px;
  color: #aaa1b6;
  line-height: 1.8;
  margin-bottom: 19px;
}
.hero-footnote {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 8px;
  color: #9d90ac;
  position: absolute;
  bottom: 19px;
  left: 219px;
}
.hero-footnote svg {
  width: 11px;
  height: 11px;
}
.hero-visual {
  position: relative;
  min-height: 270px;
  perspective: 1000px;
  overflow: hidden;
}
.hero-visual:before {
  content: "";
  position: absolute;
  inset: 0;
  background-image: radial-gradient(#ad8cc054 0.7px, transparent 0.7px);
  background-size: 25px 25px;
  mask-image: radial-gradient(ellipse, #0008, transparent 70%);
}
#skill-scene {
  position: absolute;
  inset: 0;
  z-index: 1;
  opacity: 0.65;
}
#skill-scene canvas {
  display: block;
  width: 100%;
  height: 100%;
}
.orbital-glow {
  position: absolute;
  width: 250px;
  height: 250px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: radial-gradient(ellipse, #7a4bcc3b, transparent 67%);
  filter: blur(12px);
}
.core-orb {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) rotate(-8deg);
  width: 82px;
  height: 82px;
  border-radius: 24px;
  display: grid;
  place-items: center;
  border: 1px solid #bd92ff90;
  box-shadow:
    inset 0 0 24px #b17dfe30,
    0 0 45px #9362d03b,
    0 0 0 8px #b78bfc05;
  background: linear-gradient(140deg, #684f9366, #36214688);
  z-index: 3;
  backdrop-filter: blur(6px);
}
.core-orb svg {
  height: 39px;
  width: 39px;
  color: #e3caff;
  stroke-width: 1.2;
  filter: drop-shadow(0 0 5px #d2b1ff);
}
.orbit {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 310px;
  height: 180px;
  border: 1px solid #b092d526;
  border-radius: 50%;
  transform: translate(-50%, -50%) rotate(-25deg);
  pointer-events: none;
}
.orbit-two {
  width: 210px;
  height: 260px;
  transform: translate(-50%, -50%) rotate(-45deg);
  border-color: #b092d518;
}
.floating-skill {
  position: absolute;
  z-index: 4;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 12px;
  font-size: 10px;
  color: #d4c9e4;
  background: linear-gradient(110deg, #332b44dd, #272132dd);
  border: 1px solid #67547c77;
  box-shadow: 0 5px 24px #0002;
  border-radius: 8px;
  transform: rotate(-7deg);
  backdrop-filter: blur(8px);
  animation: float 7s ease-in-out infinite;
}
.floating-skill svg {
  width: 19px;
  height: 19px;
  color: #9ee6e3;
}
.node-react {
  left: 14%;
  top: 22%;
  transform: rotate(-10deg);
}
.node-typescript {
  right: 8%;
  top: 29%;
  transform: rotate(9deg);
  animation-delay: -2s;
}
.node-typescript b {
  display: grid;
  place-items: center;
  background: #4b7199;
  color: #d8edff;
  font-size: 10px;
  width: 19px;
  height: 19px;
  border-radius: 3px;
}
.node-design {
  left: 17%;
  bottom: 17%;
  transform: rotate(5deg);
  animation-delay: -3s;
}
.node-design svg {
  color: #ebaaa3;
}
.node-python {
  right: 12%;
  bottom: 22%;
  animation-delay: -5s;
}
.node-python > span {
  font-size: 24px;
  line-height: 1;
  color: #e0c077;
}
.float-dot {
  position: absolute;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #b58fe1;
  box-shadow: 0 0 12px #c29bf5;
  z-index: 2;
}
.dot-one {
  left: 32%;
  top: 16%;
}
.dot-two {
  right: 31%;
  bottom: 18%;
  width: 4px;
  height: 4px;
  background: var(--cyan);
}
.constellation-caption {
  position: absolute;
  bottom: 15px;
  width: 100%;
  text-align: center;
  font-size: 8px;
  color: #a28bb2;
  letter-spacing: 0.3px;
}
.constellation-caption span {
  display: inline-block;
  width: 4px;
  height: 4px;
  background: #b094ce;
  border-radius: 50%;
  margin-right: 6px;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin: 21px 0 29px;
}
.stat-card {
  padding: 18px 19px 15px;
  background: linear-gradient(135deg, #19192266, #15161e);
  border: 1px solid var(--border);
  border-radius: 11px;
}
.stat-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #b3afc0;
}
.stat-icon {
  width: 28px;
  height: 28px;
  border: 1px solid #b59aff1a;
  border-radius: 7px;
  display: grid;
  place-items: center;
  color: var(--purple);
  background: #b59aff0d;
}
.stat-icon svg {
  width: 14px;
  height: 14px;
}
.stat-icon.mint {
  color: #90d7b2;
  background: #90d7b209;
  border-color: #90d7b21a;
}
.stat-icon.blue {
  color: #91bafa;
  background: #91bafa09;
  border-color: #91bafa1a;
}
.stat-icon.peach {
  color: #e0b598;
  background: #e0b59809;
  border-color: #e0b5981a;
}
.stat-value {
  font-family: var(--heading);
  font-size: 30px;
  line-height: 1.4;
  font-weight: 500;
  margin: 4px 0;
  letter-spacing: -1px;
  display: flex;
  align-items: center;
  gap: 11px;
}
.stat-value > span {
  color: #8dbca2;
  font-size: 10px;
}
.stat-value > span svg {
  width: 14px;
  height: 14px;
}
.stat-card p {
  font-size: 9px;
  color: #83808f;
  margin-top: 4px;
}
.dashboard-columns {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 282px;
  gap: 22px;
}
.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 17px;
}
.section-title h2 {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.3px;
}
.section-title p {
  font-size: 10px;
  color: var(--muted);
  margin-top: 5px;
}
.text-link {
  font-family: var(--body);
  font-size: 10px;
  color: #bea4f5;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: none;
  border: none;
  padding: 0;
  white-space: nowrap;
}
.text-link svg {
  height: 13px;
  width: 13px;
}
.text-link:hover {
  color: #e1d1ff;
}
.jobs-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.job-card {
  border: 1px solid var(--border);
  border-radius: 11px;
  background: linear-gradient(145deg, #191a23, #15161e);
  padding: 17px 15px 0;
  transition:
    border-color 0.25s,
    transform 0.25s;
  min-width: 0;
}
.job-card:hover {
  border-color: #65527d;
  transform: translateY(-4px);
}
.job-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 3px;
  margin-bottom: 15px;
}
.company-info {
  display: flex;
  align-items: center;
  gap: 9px;
}
.company-info strong {
  font-size: 11px;
  font-weight: 500;
  display: block;
}
.company-info > div > span {
  font-size: 8px;
  color: #898593;
  display: block;
  margin-top: 1px;
}
.company-logo {
  width: 33px;
  height: 33px;
  border-radius: 9px;
  border: 1px solid #343140;
  background: #20202b;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.company-logo.linear {
  background: #6960c9;
  border-color: #8c81e2;
}
.linear-mark {
  width: 18px;
  height: 18px;
  display: block;
  border-radius: 50%;
  background: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 2px,
    #f2efff 2px,
    #f2efff 4px
  );
  position: relative;
  overflow: hidden;
}
.linear-mark:after {
  content: "";
  position: absolute;
  background: #f2efff;
  width: 22px;
  height: 20px;
  left: 7px;
  top: -5px;
  transform: rotate(-45deg);
}
.company-logo.vercel {
  background: #060609;
  border-color: #35353b;
}
.vercel-mark {
  border-left: 9px solid transparent;
  border-right: 9px solid transparent;
  border-bottom: 17px solid white;
  display: block;
}
.company-logo.notion {
  background: #eeeef1;
  border-color: #ceced7;
}
.notion-mark {
  color: #16161a;
  font-family: Georgia, serif;
  font-size: 25px;
  font-weight: bold;
  line-height: 22px;
  text-shadow:
    1px 1px 0 #eeeef1,
    2px 2px 0 #16161a;
}
.company-logo.figma {
  color: #e7b0b9;
}
.company-logo.stripe {
  background: #6058e6;
}
.stripe-mark {
  font-size: 22px;
  font-style: italic;
}
.company-logo.supabase {
  color: var(--cyan);
}
.save-job svg {
  width: 14px;
  height: 14px;
}
.save-job.saved {
  color: var(--purple);
}
.save-job.saved svg {
  fill: #b59aff33;
}
.job-title {
  font-family: var(--heading);
  font-weight: 600;
  font-size: 12px;
  letter-spacing: -0.2px;
  display: block;
  min-height: 20px;
  margin-bottom: 10px;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}
.job-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  color: #96919f;
  font-size: 8px;
  row-gap: 4px;
}
.job-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.job-meta svg {
  width: 10px;
  height: 10px;
}
.job-skills {
  display: flex;
  gap: 5px;
  margin: 14px 0 15px;
  flex-wrap: wrap;
  min-height: 24px;
}
.skill-chip {
  display: inline-flex;
  align-items: center;
  font-size: 8px;
  line-height: 1.7;
  background: #22222d;
  border: 1px solid #35323e;
  color: #b6afc3;
  padding: 3px 7px;
  border-radius: 5px;
  white-space: nowrap;
}
.job-salary {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.1px;
}
.job-salary > span {
  color: #898492;
  font-size: 8px;
  font-weight: 400;
}
.job-card-footer {
  border-top: 1px solid #2b2935;
  margin-top: 17px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
}
.match-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 8px;
  color: #9fdbb9;
  background: #72d99e0b;
  padding: 3px 7px;
  border-radius: 4px;
  border: 1px solid #78ce9b16;
  white-space: nowrap;
}
.match-pill svg {
  width: 10px;
  height: 10px;
}
.job-arrow {
  color: #c3bbcf;
}
.job-arrow svg {
  width: 15px;
  height: 15px;
}
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 21px;
}
.skills-panel {
  margin-top: 22px;
  padding: 22px 20px;
}
.skills-panel .section-title h2 {
  font-size: 14px;
}
.skills-panel-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 21px;
}
.skills-overview {
  padding-right: 17px;
  border-right: 1px solid #2a2734;
}
.skill-legend {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 9px;
  margin-bottom: 14px;
}
.skill-legend > span:first-child {
  display: flex;
  gap: 5px;
  align-items: center;
  color: #c4bccd;
}
.skill-legend > .subtle {
  font-size: 8px;
}
.legend-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  display: inline-block;
}
.legend-dot.purple {
  background: #b598f2;
}
.legend-dot.cyan {
  background: #8acbbd;
}
.strength-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.skill-chip.strength {
  background: #b391ef0d;
  border-color: #58426566;
  color: #c2a6e3;
  font-size: 9px;
  padding: 4px 8px;
}
.skills-tip {
  display: flex;
  gap: 7px;
  align-items: center;
  font-size: 8px;
  color: #8b8394;
  margin-top: 16px;
}
.skills-tip svg {
  color: #b8a77c;
  width: 13px;
  height: 13px;
}
.gap-row {
  display: grid;
  grid-template-columns: 65px 1fr 36px;
  gap: 10px;
  align-items: center;
  font-size: 9px;
  margin-bottom: 15px;
  color: #b8b0c5;
}
.gap-row > span:last-child {
  font-size: 8px;
  color: #857e90;
  text-align: right;
}
.gap-track {
  height: 5px;
  background: #24222f;
  border-radius: 4px;
  overflow: hidden;
}
.gap-track > div {
  height: 100%;
  background: linear-gradient(90deg, #7c68a3, #b896f0);
  border-radius: 4px;
}
.right-column {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.resume-panel {
  padding: 18px;
}
.resume-panel .section-title h2,
.learning-panel h2 {
  font-size: 13px;
}
.status-label {
  font-size: 8px;
  color: #95cbb0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.status-label > span {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #9bd3b5;
}
.resume-file {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 23px 0 17px;
}
.file-icon {
  width: 31px;
  height: 36px;
  background: #b594eb10;
  border: 1px solid #7050863b;
  border-radius: 6px;
  display: grid;
  place-items: center;
  color: #b29ace;
}
.file-icon svg {
  width: 17px;
  height: 17px;
}
.resume-file > div {
  min-width: 0;
}
.resume-file strong {
  display: block;
  font-size: 9px;
  font-weight: 500;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}
.resume-file > div > span {
  display: block;
  font-size: 8px;
  color: #8c8498;
  margin-top: 3px;
}
.resume-divider {
  height: 1px;
  background: #2b2835;
}
.resume-score {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 18px 0;
}
.mini-gauge {
  width: 47px;
  height: 47px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  background: conic-gradient(#b899e9 calc(var(--score) * 1%), #302838 0);
  border-radius: 50%;
  position: relative;
}
.mini-gauge:before {
  content: "";
  position: absolute;
  inset: 4px;
  background: var(--surface);
  border-radius: 50%;
}
.mini-gauge > span {
  position: relative;
  font-family: var(--heading);
  font-size: 15px;
  color: #d4bbfa;
}
.resume-score strong {
  font-size: 9px;
  font-weight: 500;
  display: block;
}
.resume-score p {
  font-size: 8px;
  color: #958a9f;
  line-height: 1.7;
  margin-top: 4px;
}
.resume-panel .btn {
  font-size: 9px;
  min-height: 34px;
  padding: 7px 10px;
  justify-content: flex-start;
}
.resume-panel .btn svg:last-child {
  margin-left: auto;
  width: 12px;
}
.learning-panel {
  padding: 19px 18px;
}
.learning-panel .section-title {
  margin-bottom: 5px;
  gap: 7px;
}
.learning-panel .section-title h2 {
  font-size: 11px;
}
.learning-panel .tiny-spark svg {
  width: 16px;
  height: 16px;
}
.learning-panel > p {
  font-size: 9px;
  color: var(--muted);
}
.learning-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 16px 0 0;
}
.learning-logo {
  width: 31px;
  height: 31px;
  display: grid;
  place-items: center;
  background: #28222f;
  border: 1px solid #493951;
  border-radius: 7px;
  color: #c1a7df;
}
.learning-logo svg {
  width: 15px;
  height: 15px;
}
.learning-logo.cyan {
  color: #b0d9d1;
  background: #1e2b2c;
  border-color: #34494a;
}
.learning-item > span:nth-child(2) {
  flex: 1;
  min-width: 0;
}
.learning-item strong {
  display: block;
  font-size: 9px;
  font-weight: 500;
}
.learning-item small {
  display: block;
  font-size: 8px;
  color: #898193;
  margin-top: 2px;
}
.learning-item > svg {
  width: 13px;
  height: 13px;
  color: #b0a1be;
}
.learning-link {
  font-size: 9px;
  margin-top: 19px;
  padding-top: 14px;
  border-top: 1px solid #2e2937;
  display: flex;
  justify-content: space-between;
}
.quote-card {
  position: relative;
  background: linear-gradient(135deg, #1c1b24, #1b1924);
  border: 1px solid #302b3a;
  border-radius: 11px;
  padding: 15px 20px;
  overflow: hidden;
}
.quote-card > span {
  font-family: Georgia, serif;
  font-size: 34px;
  line-height: 0.8;
  color: #8e729f;
}
.quote-card > p {
  font-family: var(--heading);
  font-size: 11px;
  line-height: 1.8;
  color: #bdb1c9;
}
.quote-card > small {
  font-size: 6px;
  letter-spacing: 1.5px;
  color: #7f708c;
  display: block;
  margin-top: 10px;
}
.quote-star {
  position: absolute;
  right: -6px;
  bottom: -28px;
  font-size: 110px;
  font-weight: 300;
  color: #41334c66;
  line-height: 1;
}
.app-footer {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 35px 23px;
  color: #6f687d;
  font-size: 8px;
}
.app-footer > span:last-child {
  display: flex;
  align-items: center;
  gap: 9px;
}
.app-footer svg {
  width: 11px;
  height: 11px;
}
.footer-dot {
  color: #554765;
}
#toasts {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: min(430px, calc(100vw - 32px));
}
.app-toast {
  display: flex;
  gap: 12px;
  align-items: center;
  border: 1px solid #526750;
  background: #212c26;
  color: #d5f2db;
  padding: 15px 16px;
  border-radius: 10px;
  box-shadow: 0 12px 40px #0006;
  font-size: 12px;
  animation: toast-in 0.25s ease;
}
.app-toast.error {
  background: #352329;
  border-color: #724553;
  color: #ffd4df;
}
.app-toast button {
  margin-left: auto;
  border: none;
  background: none;
  color: inherit;
}
.app-toast svg {
  width: 17px;
  height: 17px;
}
.upload-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 1fr);
  gap: 25px;
  max-width: 1100px;
}
.upload-panel {
  padding: 30px;
}
.step-label {
  color: var(--purple);
  letter-spacing: 1.5px;
  font-size: 10px;
}
.upload-panel h2 {
  font-size: 22px;
  margin: 15px 0 8px;
}
.upload-panel > p {
  font-size: 12px;
  color: var(--muted);
}
.dropzone {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  min-height: 255px;
  border: 1px dashed #635277;
  border-radius: 12px;
  background: radial-gradient(ellipse at center, #4c315b2b, transparent);
  margin: 26px 0 16px;
  cursor: pointer;
  transition: 0.2s;
  position: relative;
}
.dropzone.dragging,
.dropzone:hover {
  background: #b398f411;
  border-color: var(--purple);
}
.upload-orb {
  width: 61px;
  height: 61px;
  display: grid;
  place-items: center;
  color: #c9aff3;
  border: 1px solid #5a416d;
  border-radius: 17px;
  background: #32243f;
  margin-bottom: 19px;
  box-shadow: 0 0 30px #8660ab18;
}
.upload-orb svg {
  width: 27px;
  height: 27px;
}
.dropzone strong {
  font-size: 15px;
}
.dropzone > span:not(.upload-orb) {
  font-size: 11px;
  color: var(--muted);
  margin-top: 5px;
}
.dropzone b {
  color: var(--purple);
  font-weight: 500;
}
.dropzone small {
  font-size: 10px;
  color: #877c92;
  margin-top: 20px;
}
.privacy-note {
  font-size: 10px;
  display: flex;
  align-items: center;
  gap: 9px;
  color: #99919f;
  margin: 17px 0 24px;
  line-height: 1.7;
}
.privacy-note svg {
  width: 16px;
  color: #9fc9b1;
}
.upload-explainer {
  padding: 28px;
}
.upload-explainer h2 {
  font-size: 24px;
  margin-bottom: 26px;
}
.explain-step {
  display: flex;
  gap: 16px;
  margin-top: 24px;
}
.explain-step > span {
  width: 35px;
  height: 35px;
  display: grid;
  place-items: center;
  background: #26202f;
  border: 1px solid #3f304b;
  border-radius: 9px;
  color: #bca5d7;
  flex-shrink: 0;
}
.explain-step small {
  font-size: 9px;
  color: #8e789f;
}
.explain-step h3 {
  font-size: 13px;
  margin: 4px 0 7px;
}
.explain-step p {
  color: var(--muted);
  font-size: 11px;
}
.existing-resume {
  margin-top: 20px;
}
.existing-resume h3 {
  font-size: 14px;
}
.existing-resume p {
  font-size: 11px;
  color: var(--muted);
  margin: 10px 0 14px;
}
.existing-resume button {
  margin-top: 20px;
}
.selected-file {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #24202d;
  border: 1px solid #493c59;
  border-radius: 8px;
  padding: 12px;
  color: #d1bcea;
  font-size: 12px;
}
.selected-file small {
  display: block;
  color: var(--muted);
  font-size: 10px;
}
.selected-file button {
  margin-left: auto;
}
.form-error {
  font-size: 12px;
  color: #f1a0b6;
  margin: 12px 0;
  min-height: 5px;
}
.search-panel {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 16px;
}
.search-field {
  display: flex;
  gap: 10px;
  align-items: center;
  flex: 1;
}
.search-field svg {
  color: var(--muted);
  width: 17px;
}
.search-panel input,
.search-panel select {
  border: 0;
  background: none;
  padding: 8px 0;
  font-size: 12px;
  width: 100%;
  outline-offset: 0;
}
.search-field.location-field {
  border-left: 1px solid var(--border);
  padding-left: 18px;
  flex: 0.65;
}
.search-panel > select {
  width: 125px;
}
.jobs-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--muted);
  margin: 24px 0 17px;
}
.save-filter {
  display: flex;
  gap: 8px;
  align-items: center;
}
.save-filter input {
  accent-color: var(--purple);
}
.all-jobs-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}
.all-jobs-grid .job-card {
  padding: 24px 23px 0;
}
.all-jobs-grid .job-title {
  font-size: 16px;
  margin: 21px 0 14px;
}
.all-jobs-grid .company-info strong {
  font-size: 13px;
}
.all-jobs-grid .job-meta {
  font-size: 10px;
  gap: 15px;
}
.all-jobs-grid .skill-chip {
  font-size: 10px;
}
.all-jobs-grid .job-skills {
  margin: 20px 0;
}
.all-jobs-grid .job-salary {
  font-size: 15px;
}
.all-jobs-grid .job-salary span {
  font-size: 10px;
}
.all-jobs-grid .match-pill {
  font-size: 10px;
}
.all-jobs-grid .job-card-footer {
  padding: 17px 0;
}
.all-jobs-grid .company-logo {
  width: 39px;
  height: 39px;
}
.pagination-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin: 30px 0;
  font-size: 12px;
  color: var(--muted);
}
.empty-state {
  text-align: center;
  padding: 55px 25px;
  grid-column: 1/-1;
  width: 100%;
}
.empty-state > svg {
  width: 35px;
  height: 35px;
  color: var(--purple);
  margin-bottom: 22px;
}
.empty-state h2 {
  font-size: 21px;
}
.empty-state p {
  font-size: 13px;
  color: var(--muted);
  margin: 12px 0 25px;
}
.skeleton {
  min-height: 285px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: linear-gradient(
    100deg,
    var(--surface) 20%,
    #252031 50%,
    var(--surface) 80%
  );
  background-size: 200% 100%;
  animation: shimmer 2s infinite;
}
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 26px;
}
.back-link svg {
  width: 15px;
}
.job-detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 25px;
}
.job-detail {
  padding: 34px;
}
.detail-company {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 25px;
}
.detail-company .company-logo {
  width: 47px;
  height: 47px;
}
.detail-company > span {
  font-size: 16px;
  font-weight: 500;
}
.detail-company small {
  font-size: 11px;
  display: block;
  color: var(--muted);
  font-weight: 400;
}
.detail-company button {
  margin-left: auto;
}
.job-detail h1 {
  font-size: 29px;
  letter-spacing: -0.8px;
  line-height: 1.4;
}
.detail-meta {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  margin-top: 20px;
  color: var(--muted);
  font-size: 11px;
}
.detail-meta > span {
  display: flex;
  align-items: center;
  gap: 7px;
}
.detail-meta svg {
  width: 14px;
  height: 14px;
}
hr {
  border: 0;
  border-top: 1px solid var(--border);
  opacity: 1;
  margin: 26px 0;
}
.job-detail h2 {
  font-size: 17px;
  margin-bottom: 17px;
}
.job-description {
  white-space: pre-line;
  font-size: 13px;
  color: #b2aaba;
  line-height: 1.95;
  margin-bottom: 30px;
}
.fit-panel {
  background:
    radial-gradient(ellipse at top right, #6d3c7922, transparent),
    var(--surface);
  padding: 25px;
}
.fit-panel h2 {
  font-size: 24px;
  margin: 15px 0;
}
.fit-panel p {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 25px;
}
.fit-panel .btn {
  margin-bottom: 12px;
}
.fit-panel small {
  display: block;
  color: #8e839b;
  font-size: 10px;
  line-height: 1.7;
  margin-top: 8px;
}
.match-layout {
  display: grid;
  grid-template-columns: 350px minmax(0, 1fr);
  gap: 25px;
}
.match-score-panel {
  padding: 30px;
  text-align: center;
}
.big-gauge {
  width: 185px;
  height: 185px;
  margin: 5px auto 25px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: conic-gradient(
    from 0deg,
    #ab82ed calc(var(--score) * 0.6%),
    #8ce1d4 calc(var(--score) * 1%),
    #302a3c 0
  );
  position: relative;
  box-shadow: 0 0 60px #9f75d010;
}
.big-gauge:before {
  content: "";
  position: absolute;
  inset: 10px;
  background: var(--surface);
  border-radius: 50%;
}
.big-gauge > span {
  position: relative;
  font-family: var(--heading);
  font-size: 60px;
  letter-spacing: -3px;
  color: #e8d8ff;
}
.big-gauge small {
  font-size: 23px;
  letter-spacing: 0;
  color: #a69ab4;
  margin-left: 4px;
}
.match-score-panel .match-pill {
  font-size: 12px;
  padding: 5px 12px;
}
.match-score-panel h2 {
  font-size: 18px;
  margin: 24px 0 12px;
}
.match-score-panel p {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.8;
}
.score-breakdown {
  display: flex;
  flex-direction: column;
  gap: 13px;
  margin: 25px 0;
  padding: 20px 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  font-size: 12px;
  text-align: left;
}
.score-breakdown > span {
  display: flex;
  justify-content: space-between;
  color: var(--muted);
}
.score-breakdown b {
  color: #d6c7e7;
  font-weight: 500;
}
.match-skills h2 {
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 9px;
}
.match-skills h2 svg {
  color: var(--cyan);
}
.match-skills p {
  color: var(--muted);
  font-size: 12px;
  margin: 10px 0 20px;
}
.match-skills .skill-chip {
  font-size: 12px;
  padding: 6px 11px;
}
.skill-chip.missing {
  background: #d5a75c0a;
  border-color: #70543e;
  color: #ddbd91;
}
.result-radar {
  margin-top: 22px;
}
.result-radar h2 {
  font-size: 15px;
}
.result-radar .chart-wrap {
  height: 235px;
}
.result-learning {
  margin-top: 35px;
}
.course-card {
  display: block;
  transition: 0.2s;
}
.course-card > svg {
  width: 26px;
  height: 26px;
  color: var(--purple);
}
.course-card h3 {
  font-size: 16px;
  margin: 20px 0 10px;
}
.course-card p {
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 24px;
}
.course-card:hover {
  border-color: #70558c;
  background: #1b1824;
}
.analytics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 22px;
}
.chart-panel {
  padding: 25px;
}
.chart-wrap {
  height: 265px;
  position: relative;
  margin-top: 25px;
}
.app-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 12px;
  white-space: nowrap;
}
.app-table th {
  font-size: 10px;
  font-weight: 500;
  color: #a297ad;
  border-bottom: 1px solid var(--border);
  padding: 16px 18px;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.app-table td {
  padding: 22px 18px;
  border-bottom: 1px solid #27222f;
  color: #b5aabd;
}
.app-table td strong {
  font-weight: 500;
  color: #e2d8eb;
}
.app-table tbody tr:last-child td {
  border: 0;
}
.app-table .match-pill {
  font-size: 11px;
}
.table-panel h2 {
  font-size: 18px;
  margin: 8px 18px;
}
.application-status {
  font-size: 10px;
  display: inline-block;
  padding: 5px 10px;
  border-radius: 5px;
  background: #b59aff0e;
  color: #baa2d7;
  border: 1px solid #b59aff25;
}
.application-status.interview {
  background: #8ce1d40a;
  border-color: #8ce1d430;
  color: #a0d1c3;
}
.admin-jobs {
  margin-top: 25px;
}
.status-select {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 5px;
  font-size: 11px;
  padding: 7px;
  color: var(--text);
}
.job-form {
  max-width: 850px;
  padding: 30px;
}
.job-form label,
.auth-form-side label {
  font-size: 12px;
  display: block;
  margin: 0 0 8px;
  color: #d5cada;
}
.job-form input,
.job-form select,
.job-form textarea,
.auth-form-side input,
.auth-form-side select {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #3d3449;
  border-radius: 7px;
  background: #18151f;
  color: var(--text);
  font-size: 12px;
}
.job-form small {
  font-size: 10px;
  color: var(--muted);
  display: block;
  margin-top: 6px;
}
.job-form .btn {
  margin-top: 15px;
}
.managed-job h3 {
  font-size: 17px;
  line-height: 1.5;
}
.managed-job p {
  color: var(--muted);
  font-size: 12px;
  margin: 8px 0 20px;
}
.manage-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 25px;
  padding-top: 18px;
  border-top: 1px solid var(--border);
}
.danger {
  color: #e39cb1;
}
.auth-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 100vh;
  padding: 0 !important;
  max-width: none !important;
}
.auth-story {
  background:
    radial-gradient(ellipse at 50% 65%, #4a2b6855, transparent 65%), #17121f;
  padding: 45px 60px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border-right: 1px solid #342940;
  overflow: hidden;
}
.auth-story > .brand {
  font-size: 27px;
}
.auth-story h1 {
  font-size: 65px;
  letter-spacing: -3px;
  line-height: 1.2;
  font-weight: 500;
  margin: 24px 0;
}
.auth-story h1 span {
  color: var(--purple);
}
.auth-story p {
  color: #ada0bb;
  font-size: 14px;
  line-height: 1.9;
}
.auth-art {
  height: 260px;
  position: relative;
  margin-top: 15px;
}
.auth-art .core-orb {
  width: 95px;
  height: 95px;
}
.auth-art .node-react {
  top: 20%;
  left: 13%;
}
.auth-art .node-design {
  left: auto;
  right: 2%;
  bottom: 20%;
}
.auth-story-footer {
  font-size: 11px;
  color: #8e7e9e;
}
.auth-form-side {
  padding: 40px 65px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
}
.auth-form-side > .back-link {
  align-self: flex-end;
  font-size: 11px;
}
.auth-form-side form {
  width: 100%;
  max-width: 365px;
  margin: 30px 0;
}
.auth-form-side h2 {
  font-size: 30px;
  letter-spacing: -1px;
  margin: 12px 0;
}
.auth-form-side form > p {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 32px;
}
.auth-form-side label {
  margin-top: 19px;
}
.auth-form-side .btn {
  min-height: 45px;
  font-size: 12px;
}
.auth-form-side .form-error {
  margin: 20px 0;
}
.password-field {
  position: relative;
}
.password-field input {
  padding-right: 45px;
}
.password-field .icon-btn {
  position: absolute;
  top: 7px;
  right: 8px;
}
.auth-switch {
  text-align: center;
  font-size: 11px;
  margin-top: 22px;
  color: var(--muted);
}
.auth-switch a {
  color: var(--purple);
  margin-left: 4px;
}
.auth-divider {
  position: relative;
  border-top: 1px solid var(--border);
  margin: 32px 0 25px;
  text-align: center;
  line-height: 0;
}
.auth-divider span {
  padding: 0 12px;
  background: var(--bg);
  color: #8b7f96;
  font-size: 10px;
}
.auth-privacy {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 10px;
  color: #8a7e97;
}
.auth-privacy svg {
  width: 13px;
  height: 13px;
}
.landing #main-content {
  padding: 0;
  max-width: none;
}
.landing-nav {
  height: 96px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 7%;
  border-bottom: 1px solid #272030;
}
.landing-nav nav {
  display: flex;
  align-items: center;
  gap: 32px;
  font-size: 12px;
  color: #b0a3bc;
}
.landing-hero {
  position: relative;
  min-height: calc(100svh - 96px);
  display: flex;
  align-items: center;
  padding: 70px 7% 100px;
  overflow: hidden;
  background: radial-gradient(ellipse at 90% 30%, #44305a38, transparent 60%);
}
.landing-hero-copy {
  z-index: 5;
  position: relative;
  width: 60%;
}
.landing-hero h1 {
  font-size: clamp(55px, 6vw, 94px);
  font-weight: 500;
  line-height: 1.13;
  letter-spacing: -4px;
  margin: 29px 0 25px;
}
.landing-hero h1 span {
  background: linear-gradient(110deg, #b092f0, #8cd8d3);
  color: transparent;
  background-clip: text;
}
.landing-hero p {
  font-size: 15px;
  color: #a69ab0;
  line-height: 1.85;
}
.landing-buttons {
  display: flex;
  gap: 15px;
  margin-top: 33px;
}
.landing-buttons .btn {
  min-height: 46px;
  padding: 13px 20px;
}
.landing-proof {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 9px;
  color: #8d7f9b;
  margin-top: 27px;
}
.landing-proof svg {
  width: 13px;
  height: 13px;
}
.landing-scene {
  position: absolute;
  right: 0;
  top: 0;
  width: 55%;
  height: 100%;
  z-index: 1;
}
.landing-scene .core-orb {
  width: 120px;
  height: 120px;
  border-radius: 33px;
}
.landing-scene .core-orb svg {
  width: 60px;
  height: 60px;
}
.landing-scene .orbit-one {
  width: 480px;
  height: 320px;
}
.landing-scene .orbit-two {
  width: 340px;
  height: 470px;
}
.landing-scene .orbital-glow {
  width: 600px;
  height: 600px;
}
.landing-scene .floating-skill {
  font-size: 15px;
  padding: 16px 20px;
}
.landing-scene .node-react {
  top: 26%;
  left: 16%;
}
.landing-scene .node-typescript {
  top: 35%;
  right: 7%;
}
.landing-scene .node-design {
  bottom: 22%;
  left: 20%;
}
.landing-scene .node-python {
  right: 10%;
  bottom: 24%;
}
.scroll-cue {
  position: absolute;
  bottom: 30px;
  left: 7%;
  display: flex;
  align-items: center;
  gap: 20px;
  font-size: 9px;
  letter-spacing: 0.5px;
  color: #85748f;
}
.scroll-cue svg {
  width: 14px;
  height: 14px;
}
.landing-companies {
  border-top: 1px solid #30243b;
  border-bottom: 1px solid #30243b;
  padding: 40px 10%;
  text-align: center;
  background: #131017;
}
.landing-companies > span {
  font-size: 9px;
  color: #9d8aaa;
  letter-spacing: 2px;
}
.landing-companies > div {
  display: flex;
  justify-content: space-around;
  gap: 30px;
  margin-top: 28px;
  color: #aaa0b3;
  font-family: var(--heading);
  font-size: 26px;
  letter-spacing: -1px;
}
.landing-companies small {
  display: block;
  font-size: 9px;
  color: #776b80;
  margin-top: 22px;
}
.story-section {
  padding: 100px 10%;
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 80px;
  position: relative;
}
.story-heading h2 {
  font-size: 45px;
  letter-spacing: -2px;
  line-height: 1.25;
  margin: 20px 0;
}
.story-heading p {
  color: var(--muted);
  font-size: 14px;
}
.story-step {
  position: relative;
  padding: 35px 30px 35px 90px;
  border: 1px solid #3c2f46;
  border-radius: 15px;
  background: linear-gradient(135deg, #211729, #15121b);
  margin-bottom: 25px;
}
.story-number {
  position: absolute;
  left: 25px;
  top: 32px;
  font-size: 12px;
  color: #9781a6;
}
.story-icon {
  width: 45px;
  height: 45px;
  background: #ab85d412;
  border: 1px solid #76519244;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: var(--purple);
  margin-bottom: 25px;
}
.story-step h3 {
  font-size: 23px;
  letter-spacing: -0.7px;
}
.story-step p {
  font-size: 13px;
  color: #a18cac;
  line-height: 1.85;
  margin-top: 15px;
}
.landing-cta {
  text-align: center;
  padding: 80px 30px 110px;
  background: radial-gradient(ellipse at bottom, #47305255, transparent 65%);
  border-top: 1px solid #302339;
}
.landing-cta h2 {
  font-size: 65px;
  line-height: 1.2;
  letter-spacing: -3px;
  font-weight: 500;
  margin: 25px 0 32px;
}
.landing-cta h2 span {
  color: var(--purple);
}
.landing-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 35px 7%;
  border-top: 1px solid #302339;
}
.landing-footer > span,
.landing-footer > a:last-child {
  font-size: 11px;
  color: #9d8aa9;
}
.landing-footer > a:last-child svg {
  width: 13px;
}
.not-found {
  text-align: center;
  padding: 60px 10px 100px;
}
.not-found > span {
  font-size: 130px;
  color: var(--purple);
  font-family: var(--heading);
  letter-spacing: -8px;
  line-height: 1.5;
}
.not-found h1 {
  font-size: 32px;
}
.not-found p {
  color: var(--muted);
  margin: 15px 0 30px;
}
.button-spinner {
  display: inline-block;
  width: 13px;
  height: 13px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
.sidebar-scrim {
  display: none;
}
@keyframes float {
  0%,
  100% {
    translate: 0 0;
  }
  50% {
    translate: 0 -7px;
  }
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@media (min-width: 1600px) {
  #main-content {
    padding: 42px 48px 25px;
  }
  .topbar {
    padding: 0 48px;
  }
  .dashboard-hero {
    min-height: 315px;
  }
  .hero-copy {
    padding: 37px 40px;
  }
  .hero-copy h2 {
    font-size: 35px;
  }
  .hero-copy > p {
    font-size: 13px;
  }
  .hero-footnote {
    left: 238px;
    bottom: 30px;
  }
  .dashboard-columns {
    grid-template-columns: minmax(0, 1fr) 320px;
    gap: 25px;
  }
  .job-title {
    font-size: 15px;
  }
  .job-meta {
    font-size: 10px;
  }
  .job-card {
    padding: 22px 19px 0;
  }
  .skill-chip {
    font-size: 10px;
  }
  .job-salary {
    font-size: 14px;
  }
  .stat-card p {
    font-size: 11px;
  }
  .section-title h2 {
    font-size: 19px;
  }
  .resume-panel .section-title h2 {
    font-size: 15px;
  }
  .resume-file strong {
    font-size: 11px;
  }
  .resume-score strong {
    font-size: 11px;
  }
  .resume-score p {
    font-size: 10px;
  }
  .learning-panel .section-title h2 {
    font-size: 13px;
  }
  .learning-item strong {
    font-size: 11px;
  }
  .learning-item small {
    font-size: 10px;
  }
  .quote-card > p {
    font-size: 13px;
  }
  .skills-panel .section-title h2 {
    font-size: 17px;
  }
  .skill-legend {
    font-size: 11px;
  }
  .gap-row {
    font-size: 11px;
  }
  .skill-chip.strength {
    font-size: 11px;
  }
  .sidebar {
    width: 250px;
  }
  .app-layout {
    margin-left: 250px;
  }
}
@media (max-width: 1250px) {
  .sidebar {
    width: 205px;
    padding: 30px 15px 0;
  }
  .app-layout {
    margin-left: 205px;
  }
  .brand {
    font-size: 20px;
  }
  .topbar {
    padding: 0 25px;
  }
  .top-search {
    display: none;
  }
  #main-content {
    padding: 28px 25px 20px;
  }
  .dashboard-columns {
    grid-template-columns: minmax(0, 1fr) 250px;
    gap: 17px;
  }
  .jobs-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .jobs-grid .job-card:nth-child(3) {
    display: none;
  }
  .hero-footnote {
    display: none;
  }
  .hero-copy h2 {
    font-size: 25px;
  }
  .hero-copy {
    padding: 29px 25px;
  }
  .hero-visual .floating-skill {
    padding: 7px 9px;
    font-size: 8px;
  }
  .node-react {
    left: 5%;
  }
  .node-design {
    left: 7%;
  }
  .node-typescript {
    right: 5%;
  }
  .node-python {
    right: 5%;
  }
  .stat-card {
    padding: 15px;
  }
  .stat-card p {
    font-size: 8px;
  }
  .skills-panel-content {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  .skills-overview {
    border-right: 0;
    padding-right: 0;
  }
  .gap-overview {
    padding-top: 15px;
    border-top: 1px solid var(--border);
  }
  .all-jobs-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .job-detail-layout {
    grid-template-columns: minmax(0, 1fr) 265px;
  }
  .landing-hero h1 {
    font-size: 68px;
  }
  .landing-scene .floating-skill {
    font-size: 11px;
    padding: 12px;
  }
  .auth-story {
    padding: 40px;
  }
  .auth-story h1 {
    font-size: 53px;
  }
  .auth-form-side {
    padding: 35px 40px;
  }
}
@media (max-width: 1000px) {
  .dashboard-columns {
    grid-template-columns: 1fr;
  }
  .jobs-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .jobs-grid .job-card:nth-child(3) {
    display: block;
  }
  .right-column {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
  .quote-card {
    display: none;
  }
  .skills-panel-content {
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }
  .skills-overview {
    border-right: 1px solid var(--border);
    padding-right: 17px;
  }
  .gap-overview {
    border: 0;
    padding-top: 0;
  }
  .stat-card {
    padding: 13px 12px;
  }
  .stat-heading {
    font-size: 9px;
  }
  .stat-value {
    font-size: 26px;
  }
  .stat-card p {
    font-size: 7px;
  }
  .hero-copy h2 {
    font-size: 24px;
  }
  .hero-eyebrow {
    font-size: 7px;
  }
  .hero-visual .floating-skill {
    font-size: 8px;
  }
  .hero-visual .node-react {
    top: 24%;
    left: 2%;
  }
  .hero-visual .node-typescript {
    right: 3%;
    top: 32%;
  }
  .core-orb {
    width: 65px;
    height: 65px;
    border-radius: 18px;
  }
  .hero-visual .node-python {
    right: 5%;
    bottom: 20%;
  }
  .constellation-caption {
    font-size: 7px;
  }
  .job-title {
    font-size: 11px;
  }
  .job-card {
    padding: 14px 12px 0;
  }
  .job-meta {
    font-size: 7px;
    gap: 6px;
  }
  .job-skills .skill-chip {
    font-size: 7px;
    padding: 3px 5px;
  }
  .company-info strong {
    font-size: 10px;
  }
  .page-heading h1 {
    font-size: 25px;
  }
  .page-heading p {
    font-size: 11px;
  }
  .job-detail-layout,
  .upload-layout {
    grid-template-columns: 1fr;
  }
  .fit-panel {
    max-width: none;
  }
  .fit-panel .btn {
    width: auto !important;
    margin-right: 10px;
  }
  .match-layout {
    grid-template-columns: 290px minmax(0, 1fr);
    gap: 18px;
  }
  .match-score-panel {
    padding: 22px;
  }
  .match-skills {
    padding: 20px;
  }
  .analytics-grid {
    gap: 15px;
  }
  .search-panel {
    flex-wrap: wrap;
  }
  .search-field {
    min-width: 180px;
  }
  .search-panel > .btn {
    flex: 1;
  }
  .auth-story h1 {
    font-size: 45px;
  }
  .auth-story {
    padding: 30px;
  }
  .auth-form-side {
    padding: 30px;
  }
  .landing-nav {
    padding: 0 5%;
  }
  .landing-nav nav {
    gap: 20px;
  }
  .landing-hero {
    padding-left: 5%;
    padding-right: 5%;
  }
  .landing-hero h1 {
    font-size: 57px;
    letter-spacing: -3px;
  }
  .landing-hero-copy {
    width: 65%;
  }
  .landing-hero p {
    font-size: 13px;
  }
  .landing-buttons {
    flex-wrap: wrap;
    gap: 10px;
  }
  .landing-scene {
    width: 48%;
    right: -5%;
  }
  .landing-scene .node-react {
    left: 4%;
    top: 23%;
  }
  .landing-scene .node-typescript {
    right: 10%;
    top: 32%;
  }
  .landing-scene .node-python {
    bottom: 24%;
  }
  .landing-scene .node-design {
    left: 1%;
    bottom: 18%;
  }
  .landing-scene .core-orb {
    width: 95px;
    height: 95px;
  }
  .landing-scene .orbit-one {
    width: 350px;
    height: 250px;
  }
  .story-section {
    padding: 80px 6%;
    gap: 30px;
  }
  .story-heading h2 {
    font-size: 35px;
  }
  .story-step {
    padding-left: 60px;
  }
  .story-number {
    left: 20px;
  }
}
@media (max-width: 767px) {
  .sidebar {
    transform: translateX(-100%);
    transition: transform 0.25s;
    width: 230px;
  }
  .nav-open .sidebar {
    transform: translateX(0);
  }
  .nav-open .sidebar-scrim {
    display: block;
    position: fixed;
    inset: 0;
    background: #0009;
    z-index: 25;
    backdrop-filter: blur(3px);
  }
  .app-layout {
    margin-left: 0;
  }
  .menu-toggle {
    display: inline-flex;
  }
  .topbar {
    height: 64px;
    padding: 0 20px;
  }
  .topbar-title {
    gap: 10px;
  }
  .topbar-title .menu-toggle svg {
    width: 20px;
    height: 20px;
  }
  .breadcrumb-home,
  .topbar-title > svg {
    display: none;
  }
  .topbar-actions {
    gap: 13px;
  }
  .demo-badge {
    font-size: 8px;
  }
  .notification-button {
    display: none;
  }
  #main-content {
    padding: 25px 20px 15px;
  }
  .page-heading {
    gap: 12px;
  }
  .page-heading .eyebrow {
    font-size: 7px;
    letter-spacing: 1.3px;
  }
  .page-heading h1 {
    font-size: 25px;
    letter-spacing: -0.9px;
  }
  .page-heading p {
    font-size: 10px;
  }
  .page-heading > .btn {
    font-size: 9px;
    padding: 9px 12px;
    min-height: 36px;
  }
  .page-heading > .btn svg {
    width: 12px;
    height: 12px;
  }
  .hero-copy {
    padding: 26px 23px;
  }
  .hero-copy h2 {
    font-size: 25px;
  }
  .hero-copy > p {
    font-size: 10px;
  }
  .dashboard-hero {
    min-height: 260px;
    grid-template-columns: 1.1fr 1fr;
  }
  .hero-visual {
    min-height: 260px;
  }
  .hero-visual .floating-skill {
    font-size: 7px;
    padding: 7px;
    gap: 5px;
  }
  .hero-visual .floating-skill svg {
    width: 14px;
    height: 14px;
  }
  .hero-visual .node-react {
    left: 2%;
    top: 24%;
  }
  .hero-visual .node-typescript {
    right: 3%;
    top: 37%;
  }
  .hero-visual .node-design {
    left: 0%;
    bottom: 23%;
  }
  .hero-visual .node-python {
    right: 2%;
    bottom: 14%;
  }
  .core-orb {
    width: 62px;
    height: 62px;
  }
  .hero-visual .core-orb {
    left: 48%;
    top: 51%;
  }
  .hero-visual .core-orb svg {
    width: 30px;
    height: 30px;
  }
  .orbit {
    width: 240px;
    height: 155px;
  }
  .orbit-two {
    width: 175px;
    height: 220px;
  }
  .constellation-caption {
    font-size: 6px;
    bottom: 15px;
  }
  .stats-grid {
    gap: 10px;
    margin: 17px 0 25px;
  }
  .stat-heading {
    font-size: 9px;
  }
  .stat-icon {
    height: 24px;
    width: 24px;
  }
  .stat-icon svg {
    width: 12px;
    height: 12px;
  }
  .stat-value {
    font-size: 27px;
  }
  .stat-card p {
    line-height: 1.6;
    font-size: 8px;
  }
  .jobs-grid {
    gap: 10px;
  }
  .job-card {
    padding: 16px 12px 0;
  }
  .company-logo {
    width: 29px;
    height: 29px;
  }
  .job-title {
    font-size: 11px;
  }
  .company-info {
    gap: 7px;
  }
  .job-card-top > .icon-btn {
    width: 23px;
  }
  .skills-panel {
    padding: 20px 17px;
  }
  .gap-row {
    grid-template-columns: 58px 1fr 32px;
    gap: 7px;
    font-size: 8px;
  }
  .skill-legend {
    font-size: 8px;
  }
  .skill-legend > .subtle {
    font-size: 7px;
  }
  .app-footer {
    padding: 20px;
    font-size: 7px;
  }
  .all-jobs-grid {
    gap: 15px;
  }
  .all-jobs-grid .job-card {
    padding: 20px 17px 0;
  }
  .all-jobs-grid .job-title {
    font-size: 14px;
  }
  .job-detail-layout {
    gap: 18px;
  }
  .job-detail {
    padding: 25px;
  }
  .job-detail h1 {
    font-size: 26px;
  }
  .match-layout {
    grid-template-columns: 1fr;
  }
  .match-score-panel {
    padding: 25px;
    max-width: none;
  }
  .big-gauge {
    height: 165px;
    width: 165px;
  }
  .score-breakdown {
    max-width: 350px;
    margin: 25px auto;
  }
  .match-score-panel > .btn {
    max-width: 350px;
  }
  .analytics-grid {
    grid-template-columns: 1fr;
  }
  .chart-wrap {
    height: 240px;
  }
  .auth-layout {
    grid-template-columns: 1fr;
  }
  .auth-story {
    display: none;
  }
  .auth-form-side {
    min-height: 100svh;
    padding: 25px;
  }
  .auth-form-side > .back-link {
    align-self: flex-start;
  }
  .auth-form-side form {
    margin: 25px 0 40px;
  }
  .auth-form-side h2 {
    font-size: 32px;
  }
  .auth-form-side label {
    font-size: 13px;
  }
  .auth-form-side input,
  .auth-form-side select {
    font-size: 14px;
  }
  .landing-nav {
    height: 78px;
    padding: 0 6%;
  }
  .landing-nav nav > a:first-child,
  .landing-nav nav > a:nth-child(2) {
    display: none;
  }
  .landing-nav nav {
    gap: 17px;
  }
  .landing-nav nav > .btn {
    font-size: 9px;
    padding: 9px 12px;
  }
  .landing-nav .brand {
    font-size: 19px;
  }
  .landing-hero {
    min-height: 850px;
    align-items: flex-start;
    padding: 60px 7% 400px;
  }
  .landing-hero-copy {
    width: 100%;
  }
  .landing-hero h1 {
    font-size: 61px;
    letter-spacing: -3px;
  }
  .landing-hero p {
    font-size: 13px;
  }
  .landing-hero .hero-eyebrow {
    font-size: 7px;
    letter-spacing: 1.3px;
  }
  .landing-buttons .btn {
    font-size: 10px;
    padding: 12px 15px;
  }
  .landing-proof {
    font-size: 8px;
    gap: 7px;
  }
  .landing-scene {
    width: 100%;
    height: 400px;
    top: auto;
    bottom: 20px;
    right: 0;
    opacity: 0.85;
  }
  .landing-scene .core-orb {
    height: 92px;
    width: 92px;
    border-radius: 24px;
  }
  .landing-scene .core-orb svg {
    width: 43px;
    height: 43px;
  }
  .landing-scene .orbit-one {
    width: 350px;
    height: 220px;
  }
  .landing-scene .orbit-two {
    width: 250px;
    height: 310px;
  }
  .landing-scene .node-react {
    top: 20%;
    left: 19%;
  }
  .landing-scene .node-typescript {
    top: 28%;
    right: 12%;
  }
  .landing-scene .node-design {
    bottom: 20%;
    left: 19%;
  }
  .landing-scene .node-python {
    bottom: 21%;
    right: 14%;
  }
  .scroll-cue {
    bottom: 22px;
    left: 7%;
    font-size: 8px;
  }
  .landing-companies {
    padding: 30px 6%;
  }
  .landing-companies > div {
    font-size: 17px;
    gap: 18px;
    flex-wrap: wrap;
  }
  .landing-companies > span {
    font-size: 7px;
    letter-spacing: 1.5px;
  }
  .story-section {
    grid-template-columns: 1fr;
    padding: 60px 7%;
    gap: 20px;
  }
  .story-heading {
    position: static !important;
    transform: none !important;
  }
  .story-heading h2 {
    font-size: 37px;
  }
  .story-heading p {
    margin-bottom: 15px;
  }
  .story-step {
    padding: 30px 25px 30px 65px;
  }
  .story-step h3 {
    font-size: 22px;
  }
  .story-step p {
    font-size: 12px;
  }
  .landing-cta h2 {
    font-size: 52px;
  }
  .landing-footer {
    padding: 25px 6%;
    flex-wrap: wrap;
    gap: 20px;
  }
  .landing-footer > .brand {
    font-size: 19px;
  }
  .landing-footer > span {
    display: none;
  }
  .landing-footer > a:last-child {
    font-size: 9px;
  }
  .landing-cta {
    padding: 65px 20px 80px;
  }
}
@media (max-width: 520px) {
  .page-heading {
    align-items: flex-start;
    flex-wrap: wrap;
    margin-bottom: 22px;
  }
  .page-heading h1 {
    font-size: 25px;
  }
  .page-heading > .btn {
    margin-top: 2px;
  }
  .dashboard-hero {
    grid-template-columns: 1fr;
    min-height: 480px;
  }
  .hero-copy {
    padding: 25px 23px;
    position: relative;
  }
  .hero-copy h2 {
    font-size: 28px;
  }
  .hero-copy > p {
    font-size: 11px;
    margin-bottom: 17px;
  }
  .hero-copy .hero-eyebrow {
    font-size: 7px;
  }
  .hero-visual {
    position: absolute;
    bottom: -17px;
    right: -12px;
    width: 100%;
    height: 235px;
    min-height: 0;
    opacity: 0.9;
  }
  .hero-visual .core-orb {
    left: 52%;
    top: 50%;
  }
  .hero-visual .floating-skill {
    font-size: 9px;
    padding: 8px 10px;
  }
  .hero-visual .node-react {
    left: 14%;
    top: 19%;
  }
  .hero-visual .node-typescript {
    right: 10%;
    top: 25%;
  }
  .hero-visual .node-design {
    left: 17%;
    bottom: 25%;
  }
  .hero-visual .node-python {
    right: 13%;
    bottom: 23%;
  }
  .constellation-caption {
    display: none;
  }
  .hero-visual .orbit-one {
    width: 260px;
    height: 150px;
  }
  .hero-visual .orbit-two {
    width: 170px;
    height: 215px;
  }
  .stats-grid {
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
  .stat-card {
    padding: 16px;
  }
  .stat-heading {
    font-size: 11px;
  }
  .stat-value {
    font-size: 30px;
  }
  .stat-card p {
    font-size: 8px;
  }
  .stat-icon {
    width: 27px;
    height: 27px;
  }
  .section-title h2 {
    font-size: 16px;
  }
  .section-title p {
    font-size: 10px;
  }
  .section-title > .text-link {
    font-size: 9px;
  }
  .jobs-grid,
  .all-jobs-grid {
    grid-template-columns: 1fr;
  }
  .jobs-grid .job-card {
    padding: 21px 20px 0;
  }
  .jobs-grid .company-logo {
    width: 37px;
    height: 37px;
  }
  .jobs-grid .company-info strong {
    font-size: 12px;
  }
  .jobs-grid .company-info > div > span {
    font-size: 9px;
  }
  .jobs-grid .job-title {
    font-size: 16px;
    margin: 18px 0 12px;
  }
  .jobs-grid .job-meta {
    font-size: 10px;
    gap: 17px;
  }
  .jobs-grid .job-skills .skill-chip {
    font-size: 10px;
    padding: 4px 8px;
  }
  .jobs-grid .job-salary {
    font-size: 14px;
  }
  .jobs-grid .job-card-footer {
    padding: 15px 0;
  }
  .jobs-grid .match-pill {
    font-size: 10px;
  }
  .skills-panel-content {
    grid-template-columns: 1fr;
  }
  .skills-overview {
    border: 0;
    padding: 0;
  }
  .gap-overview {
    border-top: 1px solid var(--border);
    padding-top: 20px;
  }
  .skill-legend {
    font-size: 10px;
  }
  .skill-legend > .subtle {
    font-size: 9px;
  }
  .gap-row {
    font-size: 10px;
    grid-template-columns: 70px 1fr 40px;
  }
  .gap-row > span:last-child {
    font-size: 9px;
  }
  .skill-chip.strength {
    font-size: 10px;
  }
  .skills-tip {
    font-size: 9px;
  }
  .right-column {
    grid-template-columns: 1fr;
  }
  .resume-panel,
  .learning-panel {
    padding: 22px;
  }
  .resume-panel .section-title h2,
  .learning-panel .section-title h2 {
    font-size: 15px;
  }
  .resume-file strong {
    font-size: 12px;
  }
  .resume-file > div > span {
    font-size: 10px;
  }
  .resume-score strong {
    font-size: 11px;
  }
  .resume-score p {
    font-size: 10px;
  }
  .resume-panel .btn {
    font-size: 11px;
    padding: 10px 12px;
  }
  .learning-panel > p {
    font-size: 11px;
  }
  .learning-item strong {
    font-size: 12px;
  }
  .learning-item small {
    font-size: 10px;
  }
  .learning-logo {
    width: 36px;
    height: 36px;
  }
  .learning-link {
    font-size: 11px;
  }
  .quote-card {
    display: block;
    padding: 22px;
  }
  .quote-card > p {
    font-size: 14px;
  }
  .quote-card > small {
    font-size: 8px;
  }
  .app-footer > span:first-child {
    display: none;
  }
  .app-footer {
    justify-content: center;
  }
  .search-panel {
    gap: 15px;
  }
  .search-field {
    width: 100%;
    flex: auto;
  }
  .search-field.location-field {
    border: 0;
    padding-left: 0;
    flex: 1;
  }
  .search-panel > .btn {
    width: 100%;
    flex: auto;
  }
  .search-panel > select {
    width: 120px;
  }
  .search-panel input,
  .search-panel select {
    font-size: 13px;
  }
  .jobs-toolbar {
    align-items: flex-start;
    gap: 18px;
    font-size: 10px;
  }
  .save-filter {
    white-space: nowrap;
    font-size: 10px;
  }
  .upload-panel,
  .upload-explainer {
    padding: 23px;
  }
  .upload-panel h2 {
    font-size: 20px;
  }
  .dropzone {
    min-height: 230px;
  }
  .privacy-note {
    font-size: 9px;
  }
  .job-detail {
    padding: 22px;
  }
  .job-detail h1 {
    font-size: 24px;
  }
  .detail-meta {
    gap: 12px;
    font-size: 10px;
  }
  .job-description {
    font-size: 12px;
  }
  .fit-panel .btn {
    width: 100% !important;
  }
  .job-form {
    padding: 23px;
  }
  .job-form input,
  .job-form select,
  .job-form textarea {
    font-size: 14px;
  }
  .auth-form-side .eyebrow {
    font-size: 8px;
  }
  .landing-nav nav > a:nth-child(3) {
    display: none;
  }
  .landing-nav .btn {
    font-size: 8px;
  }
  .landing-hero h1 {
    font-size: 51px;
  }
  .landing-hero p {
    font-size: 12px;
  }
  .landing-buttons {
    gap: 10px;
  }
  .landing-buttons .btn {
    font-size: 9px;
    padding: 11px 13px;
    min-height: 42px;
  }
  .landing-proof {
    font-size: 7px;
  }
  .landing-hero {
    padding-top: 50px;
    min-height: 830px;
  }
  .landing-scene {
    height: 360px;
  }
  .landing-scene .node-react {
    left: 10%;
  }
  .landing-scene .node-typescript {
    right: 8%;
  }
  .landing-scene .node-design {
    left: 13%;
  }
  .landing-scene .node-python {
    right: 12%;
  }
  .landing-companies > div {
    font-size: 16px;
  }
  .landing-footer .brand {
    font-size: 17px;
  }
  .landing-footer > a:last-child {
    font-size: 8px;
  }
  .not-found > span {
    font-size: 105px;
  }
  .not-found h1 {
    font-size: 27px;
  }
}
.stat-number {
  font-weight: 500;
}
.workspace-label,
.breadcrumb-home,
.app-footer {
  color: #9990a6;
}
.footer-dot {
  color: #9990a6;
}
.node-typescript b {
  background: #35567b;
  color: #f0f7ff;
}
.landing-companies small {
  color: #a091aa;
}
@media (prefers-reduced-motion: reduce) {
  *,
  *:before,
  *:after {
    animation: none !important;
    transition: none !important;
    scroll-behavior: auto !important;
  }
  .job-card:hover,
  .btn:hover {
    transform: none !important;
  }
}

````

## frontend/src/vite-env.d.ts

````typescript
/// <reference types="vite/client" />

````

## frontend/tsconfig.json

````json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "skipLibCheck": true,
    "noEmit": true,
    "allowImportingTsExtensions": true
  },
  "include": ["src", "vite.config.ts"]
}

````

## frontend/vite.config.ts

````typescript
import { defineConfig, loadEnv } from "vite";
export default defineConfig(({ mode }) => ({
  server: {
    proxy: {
      "/api":
        loadEnv(mode, ".", "").API_PROXY_TARGET || "http://127.0.0.1:8000",
      "^/docs$":
        loadEnv(mode, ".", "").API_PROXY_TARGET || "http://127.0.0.1:8000",
      "/openapi.json":
        loadEnv(mode, ".", "").API_PROXY_TARGET || "http://127.0.0.1:8000",
    },
  },
  build: {
    target: "es2022",
    rollupOptions: {
      output: {
        manualChunks: {
          charts: ["chart.js"],
          animation: ["gsap"],
          vendor: ["jquery"],
        },
      },
    },
  },
}));

````

## GITHUB_COPILOT_LOG.md

````markdown
# GitHub Copilot assistance log

This is a documentation template, not a claim that Copilot was used. Record only assistance that actually occurred. This project was generated with OpenAI Codex; do not misattribute that work to Copilot.

| Date | File / task | Copilot prompt or suggestion | Accepted changes | Verification performed | Student explanation |
| --- | --- | --- | --- | --- | --- |

For each entry, describe the original problem, the relevant suggestion, how you adapted it, and how you verified correctness. Include mistakes you rejected and your reasoning. Never paste credentials, private resumes, or personal information into this log.

## Reflection prompts

1. What did you understand better after reviewing the suggestion?
2. What would you implement differently without an assistant?
3. Which edge case did the suggestion miss?
4. How did you establish that the final implementation was correct?

````

## notebooks/01_pandas_analysis.ipynb

````json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Job market exploration with Pandas\n",
    "This notebook uses the deterministic, synthetic SkillMatch seed dataset. Company names are illustrative; these are not real vacancies. Run all cells from top to bottom.\n"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 1. Load and inspect\n",
    "Read 200 jobs and 300 skills and inspect column types."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 1,
   "metadata": {
    "execution": {
     "iopub.execute_input": "2026-09-28T12:23:20.709691Z",
     "iopub.status.busy": "2026-09-28T12:23:20.708760Z",
     "iopub.status.idle": "2026-09-28T12:23:24.583538Z",
     "shell.execute_reply": "2026-09-28T12:23:24.582620Z"
    }
   },
   "outputs": [
    {
     "data": {
      "text/html": [
       "<div>\n",
       "<style scoped>\n",
       "    .dataframe tbody tr th:only-of-type {\n",
       "        vertical-align: middle;\n",
       "    }\n",
       "\n",
       "    .dataframe tbody tr th {\n",
       "        vertical-align: top;\n",
       "    }\n",
       "\n",
       "    .dataframe thead th {\n",
       "        text-align: right;\n",
       "    }\n",
       "</style>\n",
       "<table border=\"1\" class=\"dataframe\">\n",
       "  <thead>\n",
       "    <tr style=\"text-align: right;\">\n",
       "      <th></th>\n",
       "      <th>id</th>\n",
       "      <th>title</th>\n",
       "      <th>company</th>\n",
       "      <th>location</th>\n",
       "      <th>employment_type</th>\n",
       "      <th>salary_min</th>\n",
       "      <th>salary_max</th>\n",
       "      <th>description</th>\n",
       "      <th>skills</th>\n",
       "      <th>posted_date</th>\n",
       "    </tr>\n",
       "  </thead>\n",
       "  <tbody>\n",
       "    <tr>\n",
       "      <th>0</th>\n",
       "      <td>1</td>\n",
       "      <td>Senior Frontend Developer</td>\n",
       "      <td>Linear</td>\n",
       "      <td>Remote</td>\n",
       "      <td>Contract</td>\n",
       "      <td>135000</td>\n",
       "      <td>175000</td>\n",
       "      <td>Join the Linear team as a senior frontend deve...</td>\n",
       "      <td>React|TypeScript|JavaScript|CSS|Next.js|Git</td>\n",
       "      <td>2026-09-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1</th>\n",
       "      <td>2</td>\n",
       "      <td>Full Stack Engineer</td>\n",
       "      <td>Vercel</td>\n",
       "      <td>San Francisco, CA</td>\n",
       "      <td>Full-time</td>\n",
       "      <td>90000</td>\n",
       "      <td>130000</td>\n",
       "      <td>Join the Vercel team as a full stack engineer ...</td>\n",
       "      <td>React|Node.js|TypeScript|PostgreSQL|Docker|RES...</td>\n",
       "      <td>2026-09-02</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2</th>\n",
       "      <td>3</td>\n",
       "      <td>Product Designer</td>\n",
       "      <td>Notion</td>\n",
       "      <td>New York, NY</td>\n",
       "      <td>Full-time</td>\n",
       "      <td>85000</td>\n",
       "      <td>125000</td>\n",
       "      <td>Join the Notion team as a product designer and...</td>\n",
       "      <td>Figma|UI Design|UX Research|Prototyping|Design...</td>\n",
       "      <td>2026-09-03</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>3</th>\n",
       "      <td>4</td>\n",
       "      <td>Python Backend Engineer</td>\n",
       "      <td>Stripe</td>\n",
       "      <td>London, UK</td>\n",
       "      <td>Full-time</td>\n",
       "      <td>140000</td>\n",
       "      <td>180000</td>\n",
       "      <td>Join the Stripe team as a python backend engin...</td>\n",
       "      <td>Python|FastAPI|PostgreSQL|Docker|Redis|Pytest</td>\n",
       "      <td>2026-09-04</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>4</th>\n",
       "      <td>5</td>\n",
       "      <td>Data Scientist</td>\n",
       "      <td>Figma</td>\n",
       "      <td>Bengaluru, IN</td>\n",
       "      <td>Full-time</td>\n",
       "      <td>105000</td>\n",
       "      <td>145000</td>\n",
       "      <td>Join the Figma team as a data scientist and he...</td>\n",
       "      <td>Python|Pandas|Machine Learning|SQL|Statistics|...</td>\n",
       "      <td>2026-09-05</td>\n",
       "    </tr>\n",
       "  </tbody>\n",
       "</table>\n",
       "</div>"
      ],
      "text/plain": [
       "   id                      title company           location employment_type  \\\n",
       "0   1  Senior Frontend Developer  Linear             Remote        Contract   \n",
       "1   2        Full Stack Engineer  Vercel  San Francisco, CA       Full-time   \n",
       "2   3           Product Designer  Notion       New York, NY       Full-time   \n",
       "3   4    Python Backend Engineer  Stripe         London, UK       Full-time   \n",
       "4   5             Data Scientist   Figma      Bengaluru, IN       Full-time   \n",
       "\n",
       "   salary_min  salary_max                                        description  \\\n",
       "0      135000      175000  Join the Linear team as a senior frontend deve...   \n",
       "1       90000      130000  Join the Vercel team as a full stack engineer ...   \n",
       "2       85000      125000  Join the Notion team as a product designer and...   \n",
       "3      140000      180000  Join the Stripe team as a python backend engin...   \n",
       "4      105000      145000  Join the Figma team as a data scientist and he...   \n",
       "\n",
       "                                              skills posted_date  \n",
       "0        React|TypeScript|JavaScript|CSS|Next.js|Git  2026-09-01  \n",
       "1  React|Node.js|TypeScript|PostgreSQL|Docker|RES...  2026-09-02  \n",
       "2  Figma|UI Design|UX Research|Prototyping|Design...  2026-09-03  \n",
       "3      Python|FastAPI|PostgreSQL|Docker|Redis|Pytest  2026-09-04  \n",
       "4  Python|Pandas|Machine Learning|SQL|Statistics|...  2026-09-05  "
      ]
     },
     "execution_count": 1,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "from pathlib import Path\n",
    "import pandas as pd\n",
    "root = Path.cwd() if (Path.cwd() / 'data').exists() else Path.cwd().parent\n",
    "jobs = pd.read_csv(root / 'data' / 'jobs.csv')\n",
    "skills = pd.read_csv(root / 'data' / 'skills.csv')\n",
    "jobs.head()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 2. Inspect quality\n",
    "Count missing values and duplicate records before cleaning."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 2,
   "metadata": {
    "execution": {
     "iopub.execute_input": "2026-09-28T12:23:24.651829Z",
     "iopub.status.busy": "2026-09-28T12:23:24.651829Z",
     "iopub.status.idle": "2026-09-28T12:23:24.693714Z",
     "shell.execute_reply": "2026-09-28T12:23:24.692341Z"
    }
   },
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "(200, 10) (300, 2)\n",
      "id                  int64\n",
      "title              object\n",
      "company            object\n",
      "location           object\n",
      "employment_type    object\n",
      "salary_min          int64\n",
      "salary_max          int64\n",
      "description        object\n",
      "skills             object\n",
      "posted_date        object\n",
      "dtype: object\n",
      "id                 0\n",
      "title              0\n",
      "company            0\n",
      "location           0\n",
      "employment_type    0\n",
      "salary_min         0\n",
      "salary_max         0\n",
      "description        0\n",
      "skills             0\n",
      "posted_date        0\n",
      "dtype: int64\n",
      "Duplicate IDs: 0\n"
     ]
    }
   ],
   "source": [
    "print(jobs.shape, skills.shape)\n",
    "print(jobs.dtypes)\n",
    "print(jobs.isna().sum())\n",
    "print('Duplicate IDs:', jobs.duplicated(subset=['id']).sum())"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 3. Clean missing values and duplicates\n",
    "Inject a controlled missing location and duplicate row to demonstrate cleaning. Keep the original seed data intact."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 3,
   "metadata": {
    "execution": {
     "iopub.execute_input": "2026-09-28T12:23:24.698400Z",
     "iopub.status.busy": "2026-09-28T12:23:24.697463Z",
     "iopub.status.idle": "2026-09-28T12:23:24.724522Z",
     "shell.execute_reply": "2026-09-28T12:23:24.723612Z"
    }
   },
   "outputs": [
    {
     "data": {
      "text/html": [
       "<div>\n",
       "<style scoped>\n",
       "    .dataframe tbody tr th:only-of-type {\n",
       "        vertical-align: middle;\n",
       "    }\n",
       "\n",
       "    .dataframe tbody tr th {\n",
       "        vertical-align: top;\n",
       "    }\n",
       "\n",
       "    .dataframe thead th {\n",
       "        text-align: right;\n",
       "    }\n",
       "</style>\n",
       "<table border=\"1\" class=\"dataframe\">\n",
       "  <thead>\n",
       "    <tr style=\"text-align: right;\">\n",
       "      <th></th>\n",
       "      <th>id</th>\n",
       "      <th>title</th>\n",
       "      <th>company</th>\n",
       "      <th>location</th>\n",
       "      <th>employment_type</th>\n",
       "      <th>salary_min</th>\n",
       "      <th>salary_max</th>\n",
       "      <th>description</th>\n",
       "      <th>skills</th>\n",
       "      <th>posted_date</th>\n",
       "    </tr>\n",
       "  </thead>\n",
       "  <tbody>\n",
       "    <tr>\n",
       "      <th>0</th>\n",
       "      <td>1</td>\n",
       "      <td>Senior Frontend Developer</td>\n",
       "      <td>Linear</td>\n",
       "      <td>Remote</td>\n",
       "      <td>Contract</td>\n",
       "      <td>135000</td>\n",
       "      <td>175000</td>\n",
       "      <td>Join the Linear team as a senior frontend deve...</td>\n",
       "      <td>React|TypeScript|JavaScript|CSS|Next.js|Git</td>\n",
       "      <td>2026-09-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1</th>\n",
       "      <td>2</td>\n",
       "      <td>Full Stack Engineer</td>\n",
       "      <td>Vercel</td>\n",
       "      <td>Not specified</td>\n",
       "      <td>Full-time</td>\n",
       "      <td>90000</td>\n",
       "      <td>130000</td>\n",
       "      <td>Join the Vercel team as a full stack engineer ...</td>\n",
       "      <td>React|Node.js|TypeScript|PostgreSQL|Docker|RES...</td>\n",
       "      <td>2026-09-02</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2</th>\n",
       "      <td>3</td>\n",
       "      <td>Product Designer</td>\n",
       "      <td>Notion</td>\n",
       "      <td>New York, NY</td>\n",
       "      <td>Full-time</td>\n",
       "      <td>85000</td>\n",
       "      <td>125000</td>\n",
       "      <td>Join the Notion team as a product designer and...</td>\n",
       "      <td>Figma|UI Design|UX Research|Prototyping|Design...</td>\n",
       "      <td>2026-09-03</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>3</th>\n",
       "      <td>4</td>\n",
       "      <td>Python Backend Engineer</td>\n",
       "      <td>Stripe</td>\n",
       "      <td>London, UK</td>\n",
       "      <td>Full-time</td>\n",
       "      <td>140000</td>\n",
       "      <td>180000</td>\n",
       "      <td>Join the Stripe team as a python backend engin...</td>\n",
       "      <td>Python|FastAPI|PostgreSQL|Docker|Redis|Pytest</td>\n",
       "      <td>2026-09-04</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>4</th>\n",
       "      <td>5</td>\n",
       "      <td>Data Scientist</td>\n",
       "      <td>Figma</td>\n",
       "      <td>Bengaluru, IN</td>\n",
       "      <td>Full-time</td>\n",
       "      <td>105000</td>\n",
       "      <td>145000</td>\n",
       "      <td>Join the Figma team as a data scientist and he...</td>\n",
       "      <td>Python|Pandas|Machine Learning|SQL|Statistics|...</td>\n",
       "      <td>2026-09-05</td>\n",
       "    </tr>\n",
       "  </tbody>\n",
       "</table>\n",
       "</div>"
      ],
      "text/plain": [
       "   id                      title company       location employment_type  \\\n",
       "0   1  Senior Frontend Developer  Linear         Remote        Contract   \n",
       "1   2        Full Stack Engineer  Vercel  Not specified       Full-time   \n",
       "2   3           Product Designer  Notion   New York, NY       Full-time   \n",
       "3   4    Python Backend Engineer  Stripe     London, UK       Full-time   \n",
       "4   5             Data Scientist   Figma  Bengaluru, IN       Full-time   \n",
       "\n",
       "   salary_min  salary_max                                        description  \\\n",
       "0      135000      175000  Join the Linear team as a senior frontend deve...   \n",
       "1       90000      130000  Join the Vercel team as a full stack engineer ...   \n",
       "2       85000      125000  Join the Notion team as a product designer and...   \n",
       "3      140000      180000  Join the Stripe team as a python backend engin...   \n",
       "4      105000      145000  Join the Figma team as a data scientist and he...   \n",
       "\n",
       "                                              skills posted_date  \n",
       "0        React|TypeScript|JavaScript|CSS|Next.js|Git  2026-09-01  \n",
       "1  React|Node.js|TypeScript|PostgreSQL|Docker|RES...  2026-09-02  \n",
       "2  Figma|UI Design|UX Research|Prototyping|Design...  2026-09-03  \n",
       "3      Python|FastAPI|PostgreSQL|Docker|Redis|Pytest  2026-09-04  \n",
       "4  Python|Pandas|Machine Learning|SQL|Statistics|...  2026-09-05  "
      ]
     },
     "execution_count": 3,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "dirty = pd.concat([jobs, jobs.iloc[[0]]], ignore_index=True)\n",
    "dirty.loc[1, 'location'] = None\n",
    "clean = dirty.drop_duplicates(subset=['id']).copy()\n",
    "clean['location'] = clean['location'].fillna('Not specified')\n",
    "for column in ['salary_min', 'salary_max']:\n",
    "    clean[column] = pd.to_numeric(clean[column], errors='coerce')\n",
    "    clean[column] = clean[column].fillna(clean[column].median())\n",
    "clean['posted_date'] = pd.to_datetime(clean['posted_date'])\n",
    "assert len(clean) == 200\n",
    "assert clean['location'].isna().sum() == 0\n",
    "clean.head()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 4. Filter and sort\n",
    "Find remote roles with minimum salaries of at least $120,000, ordered by salary."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 4,
   "metadata": {
    "execution": {
     "iopub.execute_input": "2026-09-28T12:23:24.729524Z",
     "iopub.status.busy": "2026-09-28T12:23:24.728522Z",
     "iopub.status.idle": "2026-09-28T12:23:24.757373Z",
     "shell.execute_reply": "2026-09-28T12:23:24.755529Z"
    }
   },
   "outputs": [
    {
     "data": {
      "text/html": [
       "<div>\n",
       "<style scoped>\n",
       "    .dataframe tbody tr th:only-of-type {\n",
       "        vertical-align: middle;\n",
       "    }\n",
       "\n",
       "    .dataframe tbody tr th {\n",
       "        vertical-align: top;\n",
       "    }\n",
       "\n",
       "    .dataframe thead th {\n",
       "        text-align: right;\n",
       "    }\n",
       "</style>\n",
       "<table border=\"1\" class=\"dataframe\">\n",
       "  <thead>\n",
       "    <tr style=\"text-align: right;\">\n",
       "      <th></th>\n",
       "      <th>title</th>\n",
       "      <th>company</th>\n",
       "      <th>salary_min</th>\n",
       "      <th>salary_max</th>\n",
       "    </tr>\n",
       "  </thead>\n",
       "  <tbody>\n",
       "    <tr>\n",
       "      <th>65</th>\n",
       "      <td>Machine Learning Engineer</td>\n",
       "      <td>Supabase</td>\n",
       "      <td>155000</td>\n",
       "      <td>195000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>195</th>\n",
       "      <td>Machine Learning Engineer</td>\n",
       "      <td>Clerk</td>\n",
       "      <td>155000</td>\n",
       "      <td>195000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>55</th>\n",
       "      <td>Machine Learning Engineer</td>\n",
       "      <td>Clerk</td>\n",
       "      <td>150000</td>\n",
       "      <td>190000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>70</th>\n",
       "      <td>Senior Frontend Developer</td>\n",
       "      <td>Loom</td>\n",
       "      <td>150000</td>\n",
       "      <td>190000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>125</th>\n",
       "      <td>Machine Learning Engineer</td>\n",
       "      <td>Supabase</td>\n",
       "      <td>145000</td>\n",
       "      <td>185000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>40</th>\n",
       "      <td>Senior Frontend Developer</td>\n",
       "      <td>Linear</td>\n",
       "      <td>145000</td>\n",
       "      <td>185000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>170</th>\n",
       "      <td>Senior Frontend Developer</td>\n",
       "      <td>Loom</td>\n",
       "      <td>145000</td>\n",
       "      <td>185000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>140</th>\n",
       "      <td>Senior Frontend Developer</td>\n",
       "      <td>Linear</td>\n",
       "      <td>140000</td>\n",
       "      <td>180000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>105</th>\n",
       "      <td>Machine Learning Engineer</td>\n",
       "      <td>Supabase</td>\n",
       "      <td>135000</td>\n",
       "      <td>175000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>175</th>\n",
       "      <td>Machine Learning Engineer</td>\n",
       "      <td>Clerk</td>\n",
       "      <td>135000</td>\n",
       "      <td>175000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>0</th>\n",
       "      <td>Senior Frontend Developer</td>\n",
       "      <td>Linear</td>\n",
       "      <td>135000</td>\n",
       "      <td>175000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>10</th>\n",
       "      <td>Senior Frontend Developer</td>\n",
       "      <td>Loom</td>\n",
       "      <td>135000</td>\n",
       "      <td>175000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>100</th>\n",
       "      <td>Senior Frontend Developer</td>\n",
       "      <td>Linear</td>\n",
       "      <td>135000</td>\n",
       "      <td>175000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>15</th>\n",
       "      <td>Machine Learning Engineer</td>\n",
       "      <td>Clerk</td>\n",
       "      <td>130000</td>\n",
       "      <td>170000</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>180</th>\n",
       "      <td>Senior Frontend Developer</td>\n",
       "      <td>Linear</td>\n",
       "      <td>130000</td>\n",
       "      <td>170000</td>\n",
       "    </tr>\n",
       "  </tbody>\n",
       "</table>\n",
       "</div>"
      ],
      "text/plain": [
       "                         title   company  salary_min  salary_max\n",
       "65   Machine Learning Engineer  Supabase      155000      195000\n",
       "195  Machine Learning Engineer     Clerk      155000      195000\n",
       "55   Machine Learning Engineer     Clerk      150000      190000\n",
       "70   Senior Frontend Developer      Loom      150000      190000\n",
       "125  Machine Learning Engineer  Supabase      145000      185000\n",
       "40   Senior Frontend Developer    Linear      145000      185000\n",
       "170  Senior Frontend Developer      Loom      145000      185000\n",
       "140  Senior Frontend Developer    Linear      140000      180000\n",
       "105  Machine Learning Engineer  Supabase      135000      175000\n",
       "175  Machine Learning Engineer     Clerk      135000      175000\n",
       "0    Senior Frontend Developer    Linear      135000      175000\n",
       "10   Senior Frontend Developer      Loom      135000      175000\n",
       "100  Senior Frontend Developer    Linear      135000      175000\n",
       "15   Machine Learning Engineer     Clerk      130000      170000\n",
       "180  Senior Frontend Developer    Linear      130000      170000"
      ]
     },
     "execution_count": 4,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "remote = clean.loc[(clean['location'] == 'Remote') & (clean['salary_min'] >= 120000)]\n",
    "remote.sort_values(['salary_max', 'title'], ascending=[False, True])[['title', 'company', 'salary_min', 'salary_max']].head(15)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 5. Summarize\n",
    "Group opportunities by role and expand skill lists to count demand."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 5,
   "metadata": {
    "execution": {
     "iopub.execute_input": "2026-09-28T12:23:24.761369Z",
     "iopub.status.busy": "2026-09-28T12:23:24.760821Z",
     "iopub.status.idle": "2026-09-28T12:23:24.803769Z",
     "shell.execute_reply": "2026-09-28T12:23:24.801768Z"
    }
   },
   "outputs": [
    {
     "data": {
      "text/html": [
       "<div>\n",
       "<style scoped>\n",
       "    .dataframe tbody tr th:only-of-type {\n",
       "        vertical-align: middle;\n",
       "    }\n",
       "\n",
       "    .dataframe tbody tr th {\n",
       "        vertical-align: top;\n",
       "    }\n",
       "\n",
       "    .dataframe thead th {\n",
       "        text-align: right;\n",
       "    }\n",
       "</style>\n",
       "<table border=\"1\" class=\"dataframe\">\n",
       "  <thead>\n",
       "    <tr style=\"text-align: right;\">\n",
       "      <th></th>\n",
       "      <th>openings</th>\n",
       "      <th>average_min_salary</th>\n",
       "      <th>average_max_salary</th>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>title</th>\n",
       "      <th></th>\n",
       "      <th></th>\n",
       "      <th></th>\n",
       "    </tr>\n",
       "  </thead>\n",
       "  <tbody>\n",
       "    <tr>\n",
       "      <th>Analytics Engineer</th>\n",
       "      <td>20</td>\n",
       "      <td>124000.0</td>\n",
       "      <td>164000.0</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>Machine Learning Engineer</th>\n",
       "      <td>20</td>\n",
       "      <td>120750.0</td>\n",
       "      <td>160750.0</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>Product Designer</th>\n",
       "      <td>20</td>\n",
       "      <td>120250.0</td>\n",
       "      <td>160250.0</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>Mobile Developer</th>\n",
       "      <td>20</td>\n",
       "      <td>120250.0</td>\n",
       "      <td>160250.0</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>Python Backend Engineer</th>\n",
       "      <td>20</td>\n",
       "      <td>120000.0</td>\n",
       "      <td>160000.0</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>Security Engineer</th>\n",
       "      <td>20</td>\n",
       "      <td>119750.0</td>\n",
       "      <td>159750.0</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>Data Scientist</th>\n",
       "      <td>20</td>\n",
       "      <td>118250.0</td>\n",
       "      <td>158250.0</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>Senior Frontend Developer</th>\n",
       "      <td>20</td>\n",
       "      <td>117250.0</td>\n",
       "      <td>157250.0</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>DevOps Engineer</th>\n",
       "      <td>20</td>\n",
       "      <td>115750.0</td>\n",
       "      <td>155750.0</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>Full Stack Engineer</th>\n",
       "      <td>20</td>\n",
       "      <td>115750.0</td>\n",
       "      <td>155750.0</td>\n",
       "    </tr>\n",
       "  </tbody>\n",
       "</table>\n",
       "</div>"
      ],
      "text/plain": [
       "                           openings  average_min_salary  average_max_salary\n",
       "title                                                                      \n",
       "Analytics Engineer               20            124000.0            164000.0\n",
       "Machine Learning Engineer        20            120750.0            160750.0\n",
       "Product Designer                 20            120250.0            160250.0\n",
       "Mobile Developer                 20            120250.0            160250.0\n",
       "Python Backend Engineer          20            120000.0            160000.0\n",
       "Security Engineer                20            119750.0            159750.0\n",
       "Data Scientist                   20            118250.0            158250.0\n",
       "Senior Frontend Developer        20            117250.0            157250.0\n",
       "DevOps Engineer                  20            115750.0            155750.0\n",
       "Full Stack Engineer              20            115750.0            155750.0"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    },
    {
     "data": {
      "text/plain": [
       "skill\n",
       "Python         100\n",
       "Docker          80\n",
       "React           40\n",
       "Git             40\n",
       "TypeScript      40\n",
       "AWS             40\n",
       "SQL             40\n",
       "REST APIs       40\n",
       "PostgreSQL      40\n",
       "Linux           40\n",
       "JavaScript      20\n",
       "CSS             20\n",
       "Next.js         20\n",
       "Node.js         20\n",
       "Prototyping     20\n",
       "Name: count, dtype: int64"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    },
    {
     "data": {
      "text/plain": [
       "category\n",
       "AI & ML               30\n",
       "Backend               30\n",
       "Cloud & DevOps        30\n",
       "Data                  30\n",
       "Design                30\n",
       "Frontend              30\n",
       "Languages             30\n",
       "Product & Business    30\n",
       "Professional          30\n",
       "Testing & Security    30\n",
       "Name: skill_count, dtype: int64"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "summary = clean.groupby('title').agg(openings=('id', 'count'), average_min_salary=('salary_min', 'mean'), average_max_salary=('salary_max', 'mean')).round(0)\n",
    "display(summary.sort_values('average_max_salary', ascending=False))\n",
    "demand = clean.assign(skill=clean['skills'].str.split('|')).explode('skill')['skill'].value_counts()\n",
    "display(demand.head(15))\n",
    "display(skills.groupby('category').size().rename('skill_count'))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Interpretation\n",
    "These counts describe a balanced synthetic teaching dataset. Do not interpret them as evidence of actual hiring demand or salary levels."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 6,
   "metadata": {
    "execution": {
     "iopub.execute_input": "2026-09-28T12:23:24.806864Z",
     "iopub.status.busy": "2026-09-28T12:23:24.805782Z",
     "iopub.status.idle": "2026-09-28T12:23:24.817466Z",
     "shell.execute_reply": "2026-09-28T12:23:24.816472Z"
    }
   },
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "200 unique jobs, 300 catalog skills, 20 example companies\n"
     ]
    }
   ],
   "source": [
    "print(f'{len(clean)} unique jobs, {len(skills)} catalog skills, {clean.company.nunique()} example companies')"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.10.8"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}

````

## notebooks/02_matplotlib_visualizations.ipynb

````json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Visualizing opportunities with Matplotlib\n",
    "This notebook uses the deterministic, synthetic SkillMatch seed dataset. Company names are illustrative; these are not real vacancies. Run all cells from top to bottom.\n"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 1. Load the same dataset"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 1,
   "metadata": {
    "execution": {
     "iopub.execute_input": "2026-09-28T12:23:27.217521Z",
     "iopub.status.busy": "2026-09-28T12:23:27.216521Z",
     "iopub.status.idle": "2026-09-28T12:23:30.175503Z",
     "shell.execute_reply": "2026-09-28T12:23:30.173492Z"
    }
   },
   "outputs": [],
   "source": [
    "from pathlib import Path\n",
    "import pandas as pd\n",
    "root = Path.cwd() if (Path.cwd() / 'data').exists() else Path.cwd().parent\n",
    "jobs = pd.read_csv(root / 'data' / 'jobs.csv')\n",
    "skills = pd.read_csv(root / 'data' / 'skills.csv')\n",
    "jobs.head()\n",
    "import matplotlib.pyplot as plt\n",
    "plt.style.use('seaborn-v0_8-darkgrid')\n",
    "plt.rcParams.update({'figure.figsize': (10, 5), 'figure.dpi': 110})\n",
    "purple = '#8764c5'\n",
    "cyan = '#399a93'"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 2. Bar chart — most requested skills"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 2,
   "metadata": {
    "execution": {
     "iopub.execute_input": "2026-09-28T12:23:30.179505Z",
     "iopub.status.busy": "2026-09-28T12:23:30.178507Z",
     "iopub.status.idle": "2026-09-28T12:23:30.644710Z",
     "shell.execute_reply": "2026-09-28T12:23:30.643772Z"
    }
   },
   "outputs": [
    {
     "data": {
      "image/png": "iVBORw0KGgoAAAANSUhEUgAABEAAAAIaCAYAAAAgOjjkAAAAOnRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjEwLjksIGh0dHBzOi8vbWF0cGxvdGxpYi5vcmcvJkbTWQAAAAlwSFlzAAAQ6wAAEOsBUJTofAAAY8pJREFUeJzt3QucjHX///HPrkNybK1VlCiFiuRUQpLTXZRuSgdREeFOKqlW5FA5lO6SU0kkx5Bz0lERyvmu7kpKOZdKOiA57P4f7+/9v+Y3u3btYtfsfL2ej8c87MxcM3PNNd8Zc73n8/1cMcnJyckGAAAAAADgsdhIrwAAAAAAAEB2IwABAAAAAADeIwABAAAAAADeIwABAAAAAADeIwABAAAAAADeIwABAAAAAADeIwABAAAAAADeIwABAAAAAADeIwABAAAAAADeIwABAAAAAADeIwABAERMYmKilS9f3p02bdqU7nL9+vVzy9SuXTtb12fz5s3Zev/R4sCBA/bDDz9k2f0tX77cvX5TpkzJsjHz999/p7vMzJkz3TKLFy9O8/yJXp/jHYe6/wceeMB89Ouvv9ru3buzdXum3qZbt251j/HMM89YTnSsn0P169e3m266KcvXBwB8QgACAMgR3nvvvTQvT05OtnfffTfbH/+FF16w1q1b28lu27Ztdt1119mHH35o0apGjRr29NNPW4UKFbL9sW6++Wb3WHny5MmS++vdu7c99NBDdjJYtGiRXX311bZjx45sfZy77rrLnnvuudD5okWLutesadOmltOcTK8/AEQCAQgAIOJKlSqVbgCyZs0a+/nnn91OS3ZatmyZHTp0yE52+nX8+++/t2gfT9dff70VL1482x+rSpUq7rFiY7PmK9WSJUtc6Hcy+Oyzz+z333/P9sfRNg2XP39+95pdcMEFltOcTK8/AEQCAQgAIOIaNWpk//nPf+yXX3457DpVf5QpU8bOO++8iKwbAAAA/EAAAgDIEQFIUlKSLVy48LDr3nnnHfvHP/6R5u1UOt+jRw+rVauWVaxY0a655hobPXr0YZUc77//vrVs2dKqVq3qfrG/9dZbU1ScaO78ihUrXACj3gDDhg1Ld13btGnjTiNHjnT3d9lll7nqkbTW59prr7VJkyalOc1EPR102+rVq1vPnj3tk08+yVSfig0bNqS5jrpdq1at7JJLLnHr1aFDB/viiy9SLKNeC3qsq666yq2f/n388cdt165doV4Zt99+u/u7b9++7nECf/75p/Xv39+uvPJKd1u9ZiNGjHD9QsL99ttvroxf/Vq0rbt27eoqeDJD2+++++6zK664wj1G48aN7dlnn7V9+/Yd8Xa9evVy66rXPnge4dsyM7Rdtc0uv/xyu/jii91rp/vTuDyS1D0r9LrovCppunTpYtWqVXOvh/7WZUei22lsfPrpp+5vPY9wkydPdu8FbRv9q/NpVVW0b9/ePabGgqZ1ffzxx5naBqNGjXLvIT1/jU2t8/r160NjR5d36tTpsNstXbrUre+8efNCz0PbQWM/fH3D3wvabsOHD3d/N2nSxL2nwq1bt87atWvnnoPWRctrbIXLaEwGvT7kzTffdH/rfZVeD5AFCxbYLbfc4satxm+3bt1sy5YtmerZ0b17d/e+121vvPHGw6bt6fnoPV+nTh276KKL3HPStvz6668zfP337NljQ4YMcVN2Kleu7E7NmjWzadOmZWpc6z2ox6tUqZKrfJk+ffphy+mzL/js0nO45557XPVdWuMQAKJZ7kivAAAA2iE488wzXSgR3sRPO/DaIdDO09q1a1NsqO3bt7tltROkHf+zzjrLlY9rp+a///2vPf/88265VatWuR0A7TQ8+OCD7jLtOGjn7pVXXnE7vI8++qj9+9//djvqjz32WIod/7To/rUTpfvT+mnHULfV+uzfv98FLPHx8W7HUAGDppRoJ10UNqhvhNZbYYOm9mh9tGN2rGbPnu12ELWzrZ22vXv32owZM9x6jBs3zu0My/333++2hx5X00S++eYbt1OqnTD9q94Z2il78cUXrUWLFlazZk13O92fdqS1o6cdxLPPPttV7GgnV6+RdjpjYmLcc9d9a6dLr4mW006ltmlGDh486Hbcf/rpJ3cfmr6i11w75T/++KPr2ZCWgQMHuh067VwqwDgW2rFu27at5c6d2/WLKFy4sOtPobGk565Q5mjpOWhcq5/Dt99+67avnsfrr7+e7m30HPV8ChUq5MZn8LrJBx984EK62267za2fgjE1B9b4UR8NUdChbXDuuee624tCCQUJ6oERLJeWl156yYVN//znP922UHPSV1991b3ub7/9tsXFxbnATGGipq0UKVIkdNs33njDTStp2LBh6LJZs2a5UEjrq2UV1ui9oPep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vtnmzZt3QtYXAAAAAICTQW7LAfLnz28JCQmh88WLF7d+/fq5ioh3333X7rjjjuO6/+TkZDsR1q9fb6tWrbJZs2bZhRde6C4788wz7dlnn7WGDRvatGnTrEePHnbo0CFX6XHRRRfZiy++aLly5Qotq+oXPf/HHnvMLrnkEitVqtQJWXcAAAAAAHyWIypA0pI79/+ymbx589q+fftcdUSDBg2sUqVKdv3117vqioAChcGDB9uVV17ppp1cffXVNmXKFHfdzJkzXeggmkai6SSiCotrrrnG3V/Lli1t/Pjx7vqA/h46dKhdddVVVqdOHdu4caPt37/fPc4VV1xhVapUsZtuuslVrQRiY/+3ORctWpQidMmTJ49NnDjR7r77bnd+6dKlrhpEIUgQfoS77777XCXI1KlTs3y7AgAAAABwMsoRFSDp9cZQZYhCDQUF6qHRt29fK126tJvSopBg+PDhrrJi8uTJ9tZbb9lzzz1np59+un3wwQdu2fPPP9+aNGlif/75p7s/hRVFihRx1z/yyCP24IMPul4dn3zySZpTZHS/o0ePdgFLmTJl3PIKLp555pnQ43Tq1MmtR7169ey8885z96ewRuFFrVq1rHr16la7du0UlRyrV692z039TtKSL18+VwmyZs2abN3OAICcJzY2JtKrAGT5eGZcwzeMbfgo9iT4zM4RAcioUaNs7Nix7u+DBw+6SouyZcu6IOGvv/6y999/300VUcgg9957r+uhocsUgGzevNkFCmeddZabPqIGqueee66dc845LkwoVKiQu10wzWbMmDGuSuSuu+5y57WcKjxSN0pVpYkqRGTTpk0ueJk9e7ZdcMEF7rK2bdu69dD9BeumMEThhypM5syZYzNmzHDVHKo2eeKJJ1xvk127drl10uXpOe2002h6CgAnobi4ApFeBSDLMa7hK8Y2fBTn8XeRHBGA3HLLLdamTZvQNBLt/AehxZtvvun+rVatWorb1KhRw/XWEDUYfe+991y1iMIJVVw0bdrU4uPj03w8HWWlcePGh91f6gBE1SaB4CgurVq1OuwIM4ULFw6d15QWLaPT7t27XU8QNThVGKJpMQp14uLiXFWKzqcXgvz+++8p7hcAcHLYtWuPJSWdmN5VQHbTr4j6Is24hm8Y2/BRbBR/ZsfHF4yeAETTUsLDhsxQeBD0CdH0lHfeecdWrFjh+mt8+OGHbuqKprXoSCup6XZJSUkZPoaqR8IfTyZNmmQFCqRMxILeH1qHb7/91v71r3+586r2UGWITkWLFnVHtxFNi1H1yueff+4Of5va33//bZ999pk1a9bsqLYJACD66QtHtH3pADLCuIavGNvwUZLH30VybBPUQNCYVH0zwqmyQj03RA1MFT6o8uPhhx92008uv/zyUPVI6ioL9d749NNPU1ymQ9ceifqJyM8//+zCmuCkJqs6yY8//mgjR460H3744bDbq5ojqEhRb5By5cq5ChZN+REFJ40aNXJHitF9qHrk1ltvPcqtBQAAAAAAcmwFyJGoF4iOxKLD4irIUOgwf/581xdE00nk119/tREjRriKDYUb3333nX311Vd2++23u+vVH0T++9//utCkQ4cO1rFjR1d9oftWuKKjtGQUgGjZPn36WO/evd15NV5V/5KggWqLFi1clYem83Tt2tUdKWbPnj3u/l966SV3u2CajBq2qoeIDvHbuXNn97w0bUfLqNpEzVX13MOtXLnSPbdwQRADAAAAAACiOAARVUro1LNnT/vjjz9c9cSwYcNcxYR06dLF9eJ48sknXYWGmp2qekIhh9SsWdMqV67seo3oMLZqSPr444+78OLf//63O3Suls8oBFFooZNCCvXoOPvss61///6haTaa8qIjx7zwwgsukFEliMIO9SXR46pha0BBzKxZs1wDVYU7qh5RlYgO9asjzKiqRQ1gExMTQ7cJ/zug566msAAAAAAAIH0xyUFzi5OIeoUUK1bMHSkmoJ4cr7/+umummhOo0kOH7Q2qWI7FoA7LsnSdAADZK3F0Ldu5c7e3825xcjbUU2M6xjV8w9iGj2Kj+DM7IeF/B1HxogIkqylYUJ8QTV1RFYemy7z66quHHeElkhTOhAc0AAAAAADg2J2UAYimjezdu9c1TFX/kBIlStidd95p7du3j/SqAQAAAACAbHBSBiB58+a1Xr16uRMAAAAAAPBfjj8MLgAAAAAAwPE6KStAThY004OPork5E5DR2AYAAED2oQIEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4jwAEAAAAAAB4L3ekVwDZZ1CHZWxeAIgiiaNrRXoVAAAAvEUFCAAAAAAA8B4BCAAAAAAA8B4BCAAAAAAA8B4BCAAAAAAA8B4BCAAAAAAA8B4BCAAAAAAA8B4ByHGoX7++DRs2LM3rEhMTrU2bNsdz9wAAAAAAIIvkzqo7Qko9e/a0Q4cOsVkAAAAAAMgBCECySaFChbLrrgEAAAAAwFEiAMkmmgKzbds2mzBhgi1fvtzatm1rL7zwgg0ePNg2btxoZ511lnXv3t0aNmzoltd0mTPPPNMGDRoUuo/wy5544gmbOXOmvfHGG+6yvXv3WvPmze2cc86xF198MbueBgDgBIuNjWGbw7vxzLiGbxjb8FHsSfCZTQBygmg6jMIPTY0pUaKEPfvss/bII4/Y4sWLrUCBAhne/qGHHrKlS5da7969bcyYMS4UUQgycODAE7L+AIATIy4u4/8TgGjDuIavGNvwUZzH30UIQE6g+++/3y6//HL397/+9S97++23bf369ValSpUMb5svXz4XoNxyyy326KOP2qxZs+yVV16xuLi4E7DmAIATZdeuPZaUlMwGhxf0K6K+SDOu4RvGNnwUG8Wf2fHxBTO1HAHICXTuueeG/i5Y8H8v0IEDBzJ9+0qVKlnHjh1txIgRdscdd1jNmjWzZT0BAJGjLxzR9qUDyAjjGr5ibMNHSR5/F+EwuCdQ3rx5D7ssOTn9gXXw4MHDLvviiy8sd+7ctmLFCtu/f3+WryMAAAAAAD4iAMkh8uTJY7t37w6dT0pKsi1btqRY5rXXXrNly5a5qS8//PCDDRs2LAJrCgAAAABA9GEKzHHatGmTa2Saul/H0brkkktcsKH7Kl26tI0bN87++OOPFI/z1FNP2b333muXXnqpa6aqJqr16tWzatWqHe/TAAAAAADAawQgx2nevHnuFE6HqVVIcTTatWtnmzdvtvvuu89NlbnxxhutadOmboqMjiDz8MMPu0Pe3nXXXW75Zs2a2fz5810IMmfOnEwdSQYAAAAAgJNVTPKRmlAgqg3qsCzSqwAAOAqJo2vZzp27vW08hpPziALqzM+4hm8Y2/BRbBR/ZickFMrUcvQAAQAAAAAA3iMAAQAAAAAA3iMAAQAAAAAA3iMAAQAAAAAA3uMoMB6jmR58FM3NmYCMxjYAAACyDxUgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAewQgAAAAAADAe7kjvQLIPoM6LGPzAkAUSRxdK9KrAAAA4C0qQAAAAAAAgPcIQAAAAAAAgPcIQAAAAAAAgPcIQAAAAAAAgPcIQAAAAAAAgPcIQAAAAAAAgPdy9GFw27RpYytWrEhxWZ48eaxYsWJWv359e+ihh+zUU091lycmJtqsWbPSva/XX3/dKlWq5P7+7LPPbMSIEbZ27Vr766+/rGTJkta4cWPr2LGjFSxY0JYvX2633377Eddt4MCB1qJFizSvW7p0qbVr184aNmzoHie18uXLpzgfGxvrHveSSy6x7t27h67Xc9q2bZtNmDDhiOsCAAAAAACiOACRa665xnr27Bk6v3fvXluyZIkLIJKSkqxv376h66pUqWLDhg1L837i4uLcv998840LVlq3bm3dunWz/Pnz21dffeXu79NPP7Xx48e7+9FjBPr3728//vhjivsuVKhQuus8c+ZMO+ecc+zDDz+0HTt22Omnn37YMo8++qg1adLE/a3n8dNPP9mTTz7pgpN33nnHChQocNTbCgAAAAAARGkAki9fPktISEhxWenSpe2///2vvfnmmykCEFWHpF42rXBCt1f1SKBUqVLucTp06GDr1q2zChUqpLgfXZeZ+5Y//vjD3n33XXv88cddoDF9+nTr0qXLYcspQAm/P4UkjzzyiN1666328ccfu+oRAAAAAABwkvcAOeWUUyx37qPPb2JiYty0km+//TbF5bVq1bL58+e7yo3j8cYbb9iBAwesbt26dtVVV7mpN4cOHcrUbYPnkzdv3jSv19SdVq1auQqVGjVq2L333mvbt28/rvUFAAAAAOBkkOMrQFI7ePCgm54yZ84cu+WWW4769jfffLPNmDHDrr32Wtdz49JLL3Vhgv49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YDxGMz34KJqbMwEZjW0AAABkHypAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA9whAAAAAAACA93JHegWQfQZ1WMbmBYAokji6VqRXAQAAwFtUgAAAAAAAAO8RgAAAAAAAAO8RgAAAAAAAAO8RgAAAAAAAAO8RgAAAAAAAAO8RgAAAAAAAAO9xGNyj0KZNG1uxYkWKy/LkyWPFihWz+vXr20MPPWSnnnqqnQirV6+25ORkq169+gl5PAAAAAAAohkVIEfpmmuusSVLloRO8+fPtw4dOti0adPsqaeeshOlVatWtnnz5hP2eAAAAAAARDMqQI5Svnz5LCEhIcVlpUuXtv/+97/25ptvWt++fbPy9QEAAAAAAFmAACSLnHLKKZY79/825/79++3555+3uXPn2u7du+3888+3rl27Wp06dULLT58+3caPH2+bNm2y2NhYu/DCC61Hjx5WqVIld/2BAwds5MiRNnv2bPv111+tbNmy9uCDD1rt2rWtfPnybhktryk5gwYNyqqnAQCIsNjYmEivApDl45lxDd8wtuGj2JPgM5sA5DgdPHjQTYWZM2eO3XLLLaFgYsOGDfbMM8/Y6aefbh988IF16tTJhg8fbvXq1bN3333XHn/8cXvyySddD4+ff/7ZnnjiCevVq5e7H+nfv7+9/fbb1qdPHxeOzJgxw92HrtfjKUx59NFHrUWLFsc/CgAAOUZcXIFIrwKQ5RjX8BVjGz6K8/i7CAHIUZo3b54LJgL79u2zkiVL2l133eUCClV0vPHGG65y44ILLnDLtG3b1tatW2djxoxxAchpp53mAo5mzZq5688880y78cYbXSgiqhp5/fXX7bHHHrOrr77aXfbAAw+4pqe67txzz3WXFSpUyJ0AAP7YtWuPJSUlR3o1gCyhXxH1RZpxDd8wtuGj2Cj+zI6PL5ip5QhAjpKO9tK9e3cXRnz22WcuyKhVq5YLPzQF5ssvvww1KQ2n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VO0hp/v9999d6PHhhx+6vzXVq1u3bu6wocLnNqJNYmKiO3T5hAkTQpdlNI592r8kAAEAAAAAAN5jCgwAAAAAAPAeAQgAAAAAAPAeAQgAAAAAAPAeAQgAAAAAAPAeAQgAAAAAAPAeAQgAAAAAAPAeAQgAAAAAAPAeAQgAAAAAAPAeAQgAAMgS9evXd6fdu3cfdl1iYqK1adMmW7e0HnvYsGGWE3z++ed2zTXXWMWKFe2pp56KyDrs3bvXJk2adEJfAwAAcjICEAAAkGW2bdtmTz/99Em/RUeNGmV58uSxN9980+6+++6IbI+xY8famDFjQud79uyZYwIiAAAigQAEAABkmVKlStnUqVNt2bJlJ/VW/f333+2CCy6ws88+2+Li4iKyDsnJySnOFypUyE477bSIrAsAADkBAQgAAMgyzZo1s8svv9xVG6Q1FSZQvnx5mzlzZrqXqVLhzjvvtOHDh1utWrWsSpUq1rt3b/vhhx+sY8eOVrlyZWvUqJF9+OGHKe7j559/tvbt21ulSpXclJjwKSCyZs0au+222+ziiy+2evXqWb9+/VKsp26jKStNmjSxyy67zFasWJHm+utxb7rpJrdederUsYEDB9q+fftC96HbzZ492z2nrVu3HnZ7Pb9bb73VRowY4R6nevXq1qNHjxTr8ttvv7n1u/LKK9363nLLLbZ8+fLQ9X/99ZfbzrVr13bP95///Ke98847ofvXtlNFTrAO4VNgdD8XXnihLVq0yK699lo3Vefqq6+29957L3T/hw4dsueee849v0suucS6du1q/fv3TzGNRhUmDRs2dLfX89bzSR28AACQUxCAAACALBMTE+N2klUBcby9L1atWmXff/+9CzF69erlKktuvPFG11tDQUnZsmXdTn34Dve0adNcmDB37lxr27atW5d3333XXbdu3Tp32RVXXOGuf+aZZ+yLL76wdu3apbiPiRMnusd7+eWX3Y5/arq/zp07uwBF66GQQlNdunXr5q5//fXXXTCi9VyyZImVKFEi3T4hul5TVRQcrFy50u6///5Q+KD10jYYPHiwe5xy5crZXXfdZZ999plb5vnnn7evv/7aXnrpJff4devWtQceeMCFHbqtTmeccUa666DH0H0rRHnjjTfc/T/yyCO2Z88ed722j7Z5nz59bMaMGZaQkGATJkwI3X7hwoVuqo+ev4KX7t272wsvvOC2LQAAOVHuSK8AAADwy5lnnul2pFWx8Y9//MNVEByLpKQkt3NdsGBBO+ecc9zOes2aNV2lg6iC4oMPPnBVH8WLF3eXqRqhU6dO7m/d5j//+Y8LGFQtomoFVUsE15cpU8b+/e9/u9uoYkOVGKKKC1WdpEeBg+7vX//6V+hxFKDcc8899u2339p5553n+n/ky5fPhQZHCouGDBlip59+ujuv7dWhQwf77rvvbMuWLS6cmTdvngsmRNtCoYmeh8KPzZs3W4ECBdy0o8KFC9t9991nNWrUsCJFirjL8+fPb7ly5TriOihwUcWO6Pm8/fbbtn79eqtQoYJNnjzZVaXouYpCobVr14Zuq8fPmzeve71LlizpTnod9C8AADkRFSAAACDL3XzzzS5s0E7zkabCHEl8fLwLPwLaoVdPjYACBtm/f3/osmrVqqW4D02V+eabb9zfX375pS1evNhVZwQnTdmRDRs2hG5TunTpI66XAoKqVaumuOzSSy8NXZdZCmCC8EOC+9R96KSeHUH4EQQmqm4JHkNhiapaFGAoDFL1hbaPbpdZ5557bujvYFsfOHDAbQ9N6QmvgNHjh29fbTv1N1HI1bRpU1dtIwQgAICcigoQAACQLZ588km77rrrXH+MjBw8ePCwy1RFkVps7JF/u0l9vapIVKUQ/K31CSpAwhUtWvSwYCU9afW40H1L7tyZ/2qV+vlpSoqoaiO9Phq6PHgMBTjq4bF06VL7+OOPXc8RhSCauhNUdWQk2DbpPcaR+nlom82ZM8dVhWgdNNVm/Pjxdu+991qXLl0y9fgAAJxIVIAAAIBsoUoA9ehQTwz1ski98x9eGbJp06YseUxNGwm3evVqO//8893f+ldTVFThEZwUvCigUXPVzFJTUTVTDRc8P/UlySz1N/nzzz9D54PpJWpOqsfQdeEVJQoj9Hw0xUaGDh3qzjdo0MBV2mj6iqbD6N+gYuNYadsoCNIUonCffvpp6G/1+pgyZYqrClGDVPVfadmypetHAgBATkQAAgAAso12iNUDRD0twmlqxfTp0+2rr75yU1P69u2bZjXC0Zo/f77r+aE+GurVoYalQa8ONQXVY6mXhqZ4KHB48MEHbePGjW46SmbpKDNq+jly5EgXYqgPyRNPPGFXXXXVUQUge/futYcfftiFHDps8OOPP+6OPqOeGtpmOoyu1k/9SbS+ul7L3nHHHe722qZqUKrqDx3tRcHH9u3bXWVIMGVIzWi1jprWcjROPfVUd7QXhSw6MozuQ01twwOQv//+212myhM1XlUIpEauweMDAJDTMAUGAACckKkw4RR46KRDyapxphp4/vjjj8f9WDpKigKJZ5991gUJanIaNDdV6KLpIWog2rx5cxcQaKqIGrYeTfiinhe6f003UQiiqSA6lKyqII6GjsyikEOH5dW0F20jHUlFdF5BjgIGTSdRnxMdanbcuHGhvhwKP3T9Qw895A6Zq+er219//fXu+saNG7uqDPXq0JFtjpZeEwUnqi7RIXcV8KjaRMFHEG7pcbUNVEGj5qvaNsFzAAAgp4lJ5mDtAAAAJ9SwYcNs1qxZ7lCyOZWqZzS9Jbw/SnBo3QEDBkR03QAAOBZMgQEAAMBhdLhdTcHRNCVNt1H1ySeffBI6cg4AANGGAAQAAACHeeaZZ6xAgQJ25513uik+8+bNc9OHatasydYCAEQlpsAAAAAAAADvUQECAAAAAAC8RwACAAAAAAC8RwACAAAAAAC8RwACAAAAAAC8RwACAAAAAAC8RwACAAAAAAC8RwACAAAAAAC8RwACAAAAAAC8RwACAAAAAADMd/8Pl0nM++dbx3AAAAAASUVORK5CYII=",
      "text/plain": [
       "<Figure size 1100x550 with 1 Axes>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "demand = jobs.assign(skill=jobs.skills.str.split('|')).explode('skill').skill.value_counts().head(10)\n",
    "fig, ax = plt.subplots()\n",
    "demand.sort_values().plot.barh(ax=ax, color=purple)\n",
    "ax.set(title='Most requested skills in the synthetic catalog', xlabel='Number of postings', ylabel='Skill')\n",
    "fig.tight_layout()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 3. Scatter plot — salary bands"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 3,
   "metadata": {
    "execution": {
     "iopub.execute_input": "2026-09-28T12:23:30.648698Z",
     "iopub.status.busy": "2026-09-28T12:23:30.648698Z",
     "iopub.status.idle": "2026-09-28T12:23:30.880578Z",
     "shell.execute_reply": "2026-09-28T12:23:30.877369Z"
    }
   },
   "outputs": [
    {
     "data": {
      "image/png": "iVBORw0KGgoAAAANSUhEUgAABEAAAAIaCAYAAAAgOjjkAAAAOnRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjEwLjksIGh0dHBzOi8vbWF0cGxvdGxpYi5vcmcvJkbTWQAAAAlwSFlzAAAQ6wAAEOsBUJTofAAAbYlJREFUeJzt3Qd8FNX2wPGTkASQHnovoSNVqhQRBFEEKYqKoIIgoDwUUESMIuKjNxEQRKqCPHlCBKU9QBFQaSIghN5BIBB6C5D9f859/923GxKyWTbJZvb3/XyWbGbuzN6dHXYzZ889N8Bms9kEAAAAAADAwgJTuwMAAAAAAADJjQAIAAAAAACwPAIgAAAAAADA8giAAAAAAAAAyyMAAgAAAAAALI8ACAAAAAAAsDwCIAAAAAAAwPIIgAAAAAAAAMsjAAIAAAAAACyPAAgAAAAAALA8AiAAAKSQQ4cOSZkyZaRcuXJy+vRpt7f77LPPzHYHDhyQlHb16lU5e/ZsqvdFH7N3794p9ngbNmwwj/nNN99Iajt+/Ljpy6hRo8RXLFiwwPTpl19+Se2uAADgNgIgAACkkO+//14eeOABiY2NNReQvu6vv/6SJ554Qnbt2uVY1qRJExkxYoTkzZs3VfsGAACQVARAAABIATabTRYvXiy1a9c235wvXLjQ54/73r1778pUKVu2rDz99NOSOXPmVOsXAACAJwiAAACQArZs2WKGMtSoUUMeffRROXLkiGzcuJFjDwAAkEIIgAAAkAIWLVpkfmoGyGOPPWbu//vf/76r3Z49e6Rbt27y0EMPycMPP2zqPty+fdux/syZM1K+fHkJDw+Pd4iNZpesWbPG5XHbtGkjlSpVklq1asmbb74pR48eddmuUaNG8u6778qgQYOkcuXKUrduXXnrrbfkvffeM+u7du1q2iRUA2T+/PkmK6RKlSpSvXp1efXVV2Xz5s13ZcDMmjVLmjdvLhUrVjSP8f7777vUF1E6POiLL74wQ220z88995xs27bNrWN869YtGT58uNlWH6NevXrSr18/OXnypEu73bt3m3oiur5ChQrmuHTv3t0c+8TqoYwbN848Bz1OemvZsqV8++23Lu06duxobpMmTZJq1aqZ/a9bt84ct+nTp9+137Fjx5q6MKdOnbrn49+5c0dGjx5tzgs91nqcIyMjXdrouTJt2jRp3bq1VK1a1RyHZs2ayZQpU8yxtevfv795TfVYvPLKK2Z/NWvWNK/5+fPnXfZ54sQJc7z0eejr+8EHH8iVK1fiDfLp89b96LHR8y6+cxwAgNQSlGqPDACAn4iJiZFly5ZJoUKFTPBCFSxYUFasWCEffvihYziJFklt3769pE+fXrp06SJBQUGmCKfzBWmePHmkTp068p///EcGDhwowcHBjnU//vij5MyZ0wQXlF6Af/rppybjpG3bthIdHW329+yzz5qL9qJFizq21b5o//QC+NixY9KiRQvJmjWr/Otf/zIX2nohH58lS5aYYIw+xgsvvCDXr1+Xr7/+2lxUa0AmLCzMtNOLZr0Y1v126NDBXFTPmTNHfv/9d7M8R44cpt1HH31kHlODGLqPP//80/x0xyeffGKe14svvmiCDZpxM3v2bNm6davppx6r/fv3y/PPPy/58+eXTp06SZYsWUwQQYM427dvl9WrV0uGDBni3b8GSTQYo6+RPi89nvp4+tyyZ88uTZs2damfoo/ft29f81w1IJA7d27zGnXu3Nllv7pMM4Py5ct3z+c3b948c67o8dBAhwaUtC96/OzHWV+LiIgIadeunXk9NFChr8OYMWMkJCTEPGe7ixcvyssvv2wCIVrrRQMYWpvm2rVr5rxReu7pfi5fviwvvfSSeZ2+++47+eGHH1z6dvjwYRMo0/P6jTfeMOewPi8NcqlnnnnGrdcQAIBkZQMAAMlq+fLlttKlS9uGDRvmWDZ06FCzbN68eY5lb731lq1ixYq2w4cPO5adPXvWVqdOHdN2//79ZllERIT5/eeff3a0i46OtlWoUMH2ySefmN+PHj1qK1eunG3w4MEuffn7779tVatWtfXs2dOx7NFHHzX7c35c9d1335nla9ascSwbP368S1+6du1q9hcbG+tos3v3blvTpk1tP/zwg/l948aNZpsZM2a47P+vv/4yfdRjofbt22crU6aM7f3333dpZ39MPT73UrlyZdtrr73msuybb76xtWjRwnbgwAHz+0cffWSO0+nTp13ajRo1yjzGli1bzO+///67+X3u3Lnm923btpnfp0+f7rKd7leXh4eHO5Z16NDBLFu/fr1LW/trfuTIEceyrVu3mmXz589P8HkdO3bMtNHnd/LkSZfjXLZsWds//vEP83tUVJT5Pe5rfvnyZduDDz5o69Spk2PZ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",
      "text/plain": [
       "<Figure size 1100x550 with 1 Axes>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "fig, ax = plt.subplots()\n",
    "ax.scatter(jobs.salary_min / 1000, jobs.salary_max / 1000, color=cyan, alpha=0.4, s=65)\n",
    "ax.set(title='Advertised salary bands', xlabel='Minimum annual salary (USD thousands)', ylabel='Maximum annual salary (USD thousands)')\n",
    "fig.tight_layout()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 4. Histogram — salary distribution"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 4,
   "metadata": {
    "execution": {
     "iopub.execute_input": "2026-09-28T12:23:30.889685Z",
     "iopub.status.busy": "2026-09-28T12:23:30.888685Z",
     "iopub.status.idle": "2026-09-28T12:23:31.551429Z",
     "shell.execute_reply": "2026-09-28T12:23:31.546158Z"
    }
   },
   "outputs": [
    {
     "data": {
      "image/png": "iVBORw0KGgoAAAANSUhEUgAABEAAAAIaCAYAAAAgOjjkAAAAOnRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjEwLjksIGh0dHBzOi8vbWF0cGxvdGxpYi5vcmcvJkbTWQAAAAlwSFlzAAAQ6wAAEOsBUJTofAAAUO5JREFUeJzt3QmYVWX9B/DfsAgooIgLhiaCW+aKe5qaW1ZaqWmLS5pr/tXcQktNA3FBNFNzS80NK3Mpl8pcsjRXrExzQRG3FFEhERdkmf/zOz13nplhwGEYuXPPfD7Pc5nh3O2957xzZ97v/b3vqauvr68PAAAAgBLrUu0GAAAAAHzcBCAAAABA6QlAAAAAgNITgAAAAAClJwABAAAASk8AAgAAAJSeAAQAAAAoPQEIAAAAUHoCEAAAAKD0BCAAAABA6QlAACit4447LlZbbbUmlzXXXDM222yzOPjgg+PBBx+c4z7nnXdecbvx48fP9/O99NJLrbrdXnvtVbSheTunT58+3885P+3J5zjyyCOjo3rnnXfi8MMPj/XWWy/WX3/9uPPOOz/257zxxhuL/fLXv/41at3WW28du++++3z3v4/DgvS1d999N9588812bxMAdLMLACi7H/zgB9GvX7/i+wwZJk6cGDfffHPss88+ceKJJ8Yee+zRcNvtttsuPvnJT8ayyy47X8/xox/9KJ555pn49a9//ZG3zfBl2rRpbXglC9aeUaNGxcCBA6OjuuCCC+L222+Pb37zm/HpT3861lprrWo3qab88Ic/jB49ekRH0Na+9sQTT8QhhxwSp5xySmyxxRYfS9sA6LwEIACU3rbbbhvLL798k237779/fOc734mRI0cWFQdrrLFGsX311VcvLvPrvvvui6WWWqpVt/24P32fW3u+8pWvREeWgc2iiy4aJ510UtTV1VW7OTXZzzuKtva1cePGxeuvv97u7QGAZAoMAJ1SDrRPP/30qK+vj0suuaTazSEiZsyYURwX4QcA8HEQgADQaQ0aNKio/shqiVmzZs11DZDf/OY3xSfa6667bmywwQax3377xdixYxuuz9v/5z//iccee6z4PteVqGwfPXp0sa5FTufYaqut4u23357rGgyPP/54fOMb3yhum+s5/OxnP4uZM2d+5Pokv/zlL4vtDz300Ee2p/m6DH/5y1+KKUD52nJf5LSgxq+tskZJtufpp58urs/bbrTRRsXUoilTpnzkfs5pR+eee24xvSjXYPnsZz8bP/7xjxvu+8orrxRte/jhh4u1H/L73Edzk9OHjj/++Pjc5z5XPF5+HT58+BxtycfL6UabbLJJMaXmM5/5TBx11FHx6quvzrO9b731VlEZVGlv7pevf/3rc6xJkvvk2GOPLV7LOuusUxzTK6+8smh/TuVp7uijjy7WNpnbWi95/PK+eUxOPvnkot353Pkacr889dRTxX7J58rnvuKKKz5yDZBs86677lrc5/Of/3zcdNNNczxvpV89//zzRVVU3jaPUQaE77///nwdy4rmfS3blv3oD3/4Q/GzlH08j9v5558fs2fPbmhH9ql0wAEHFPepuPjii+MLX/hCrL322rHxxhvHoYceWlSLAMD8EIAA0KmtuuqqxeKbOQhvye9///s44YQTYrnllisGcP/3f/8XL7zwQhEEVIKIXO8g1xjJtUPy+w033LDh/mPGjCkG1PkYOThdfPHF59qWHPQNGDCgeJ5sVw40cy2P+TWv9jSW64MceOCBMXXq1DjssMOKgfbLL78c3/72t+cY7Gdwk9tzP+QgNcOcDFZyoP5RVR053SjDnBy85joVOXi+7rrrirAnH3fJJZcs2jl48ODo06dP8X22ZW6OOOKIuO2222KnnXYqpsvk4+VryUFxxQMPPFAco9z3uaZErvWy+eabF8fzoIMOmutj5wA/A6Hf/e538aUvfal4/H333bfYL/n4uUZFY3/605+KwCj3yVe/+tXissgiixTtayyDhLvvvju23377j1ynI495Du7zdX75y1+OP//5z8VzZzsyWMjnWmKJJeK0006Lv/3tb3N9nFtvvbW4XwYMGfzkfsrj1fw1VGSwl4Hb97///SLM+cUvflEch6ySau2xnJcMePLnIPtOBli5zk6GHhngpXysDJoqbcnHT1mhdfbZZxfPmffP/fDoo4/Gnnvu2aoADgAqrAECQKdWCST++9//xoorrjjH9b/97W9jscUWiwsvvLBhakZWEmRVR1ZEDBkypPhE+6c//WkROjRf+yAHj/npde/evT+yLflJfQ7wUg7Cv/e978UNN9xQDOQzEGmtebWnIl9vfsKfj3v99dc3DMpzIJvBQg6UcxHKHMxXqi6ygiEDk5QD1ddee60ISnJw36tXrxafJ0OSrMTIwfx3v/vd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i7PE5GlzAQAAAGoiAElnn312bLrppnHkkUfGbrvtFv/973+LhVA/8YlPFFUel156aUyYMCF23nnnOP/882PYsGHF9wAAAAA1swhqnz594uSTTy4uLVl77bXj17/+9UJvFwAAAFAOHaICBAAAAODjJAABAAAASk8AAgAAAJSeAAQAAAAovQ6xCCr/07t3j+jWTSb1P3XFv3379oqI+o+1i8ycOTumTZuuGwIAAJSYAKQDyfBj9syISa+8V+2mdBrLLL+o0AkAAKATEIB0MBl+jBn1RLWb0WnsMWzNGDBo0Wo3AwAAgI+Z+RYAAABA6QlAAAAAgNITgAAAAAClJwABAAAASk8AAgAAAJSeAAQAAAAoPQEIAAAAUHoCEAAAAKD0BCAAAABA6QlAAAAAgNITgAAAAAClJwABAAAASk8AAgAAAJSeAAQAAAAoPQEIAAAAUHoCEAAAAKD0BCAAAABA6QlAAAAAgNITgAAAAAClJwABAAAASk8AAgAAAJSeAAQAAAAoPQEIAAAAUHoCEAAAAKD0BCAAAABA6QlAAAAAgNITgAAAAAClJwABAAAASk8AAgAAAJSeAAQAAAAoPQEIAAAAUHoCEAAAAKD0BCAAAABA6QlAAAAAgNITgAAAAAClJwABAAAASk8AAgAAAJSeAAQAAAAoPQEIAAAAUHoCEAAAAKD0BCAAAABA6QlAAAAAgNITgAAAAAClJwABAAAASk8AAgAAAJSeAAQAAAAovW7RAfz3v/+Ns88+O+65556YNm1arLbaanH00UfHBhtsUFy/7777xv3339/kPhtttFFcffXVVWoxAAAAUEs6RABy1FFHxRtvvFGEIP379y+Cjf322y9uuummGDx4cDzzzDNx8sknx7bbbttwn+7du1e1zQAAAEDtqHoA8uKLL8bf/va3uPbaa2P99dcvtp144olx7733xi233BJ77rlnvPXWW7HOOuvE0ksvXe3mAgAAADWo6muA9OvXLy655JJYa621GrbV1dUVl6lTpxbVH/n9SiutVNV2AgAAALWr6hUgffv2jS233LLJtttvv72oDPnhD38Y48aNiz59+sTw4cOLSpFFF100dthhhzjkkENikUUWafEx6+r+F6LUnlpscxnURZcu9v3C3N9UQ/n6eeX1lO110Xb6BJ2jT5TptdSS8v0epczvE3TYAKS5v//97/GDH/wgtt9++9hqq62KEGT69Omx9tprF4uhPvXUUzFq1Kh49dVXi68tWXLJ3jowrda9e9fo37+3PUaplbmf9+u3WLWbQAejT6BP0N7K/HuU//G7o3PoUAHInXfeGcccc0wMHTo0Ro8eXWzLyo9jjz02Fl988eL/q666arEA6pFHHhnDhg2LpZZaao7HmTx5Wk1WgPTt26vaTeiUZsyYFVOnvl/tZnQa+nl1lLGf5yc1+cfKlCnvxuzZ9dVuDh2APkFn6BN+j1ZHGX+PUt73ic6ofysDyg4TgFxzzTUxcuTIYnrLGWec0TC9pVu3bg3hR8Uqq6xSfJ04cWKLAUh9fV5qsfPWYpvLoN6b3ULe31RDeft5vq6yvjbaRp+g3H2iLK+j1pSpD1H+9wk67CKoKc8AM2LEiNhjjz2KU+E2Xttjr732KqbENPb4448XVSCDBg2qQmsBAACAWlP1CpAJEybEqaeeGtttt10cdNBB8eabbzZc17Nnz/j85z9fXJ9rgGy++eZF+JFrf+y3337Ru7d5eAAAAEANBCB5xpcZM2bEHXfcUVwa23nnneP0008v1vO4+uqriyBk6aWXjn322ScOPPDAqrUZAAAAqC1VD0AOPvjg4jIvOTUmLwAAAAA1uwYIAAAAwMdJAAIAAACUngAEAAAAKD0BCAAAAFB6AhAAAACg9AQgAAAAQOkJQAAAAIDSE4AAAAAApScAAQAAAEpPAAIAAACUngAEAAAAKD0BCAAAAFB6AhAAAACg9AQgAAAAQOkJQAAAAIDSE4AAAAAApScAAQAAAEpPAAIAAACUngAEAAAAKD0BCAAAAFB6AhAAAACg9AQgAAAAQOkJQAAAAIDSE4AAAAAApScAAQAAAEpPAAIAAACUngAEAAAAKD0BCAAAAFB6AhAAAACg9AQgAAAAQOm1OQC55ZZbYuLEicX3F1xwQey4447xox/9KKZPn96e7QMAAABYYN3acqcMPC666KK44oor4j//+U+ce+65sdtuu8VDDz0Uo0ePjuOPP37BWwYAMB8WW6xH8bVv314RUW/fLSQzZ86OadN8AAa0n969e0S3bgtrskJd8a/fHdEp3s/bFIDccMMNccYZZ8TQoUPj1FNPjXXXXTdGjBgRY8eOjSOPPFIAAgAsdF27donp78+MSa+8Z+8vJMssv+hCHKQAnUW+r8yeGd7PF6JlOsn7eZsCkEmTJsV6661XfH///ffHDjvsUHy/3HLLxdSpU9u3hQAArZThx5hRT9hfC8kew9aMAYMWtb+Bduf9fOHao5O8n7cpABkwYEBMmDChWO/jueeei80226zYnhUgeR0AAABAzQcg3/jGN+KII46IRRZZJFZbbbWiGmTMmDExatSoOPzww9u/lQAAAAALOwDZb7/9YqWVVoqXX345vvzlLxfb+vbtGyeeeGJ87WtfW5D2AAAAAHSMACRtvfXWTf6/0047tUd7AAAAADpGALLXXntFXd3/ThfUWG7r3r17sQ7IV77yldhwww3bo40AAAAAC6RN57n51Kc+FY888khMmzYtVl999eKSC6I+9NBD0bNnz3jttddi3333jbvuumvBWgcAAABQrQqQiRMnxh577BEnnHBCk+1nnHFGvP7663H++efHFVdcERdddFFss8027dFOAAAAgIVbAXLvvfcWAUhzX//61+PPf/5z8X0GH3mKXAAAAICaDEB69+4dzz///BzbM/Do1atX8f27775bTIcBAAAAqMkpMLvssktxytvJkyfHOuusE7Nnz47HHnsszj333GLx0ylTpsSoUaMsggoAAADUbgDyve99Lz788MMYOXJksfhpfX19Ue2RZ4fJ6+65555477334pRTTmn/FgMAAAAsjACkS5cuceyxxxZhx/jx46Nr164xaNCghikv2267bXEBAAAAqNkAJL3//vsxbty4mDFjRlEB8vjjjzdct+GGG7ZX+wAAAACqE4Dcddddcdxxx8W0adOK8KOxurq6eOqppxa8ZQAAAADVDEBGjx4dm266aRxyyCHRp0+f9moLAAAAQMcJQF555ZW4+OKL45Of/GT7twgAAACgnXVpy51ywdOJEye2d1sAAAAAOk4FyDHHHBMjRoyII488MgYPHhyLLLJIk+s/8YlPtFf7AAAAAKoTgOTaH7NmzSq+5qKnFbkgqkVQAQAAgFIEIJdffnmT4AMAAACgdAHIxhtv3K6N+O9//xtnn3123HPPPcWpdVdbbbU4+uijY4MNNiiuf+CBB+LMM8+M8ePHx3LLLReHHXZYfOlLX2rXNgAAAADl1eoAZO+9947zzz8/+vbtW3w/L1ddddV8NeKoo46KN954owhB+vfvH1dffXXst99+cdNNNxXTag466KDYd999ixAkQ5Jhw4bFkksuWZyKFwAAAKDdApCBAwdGly5dGhY5ba8pMC+++GL87W9/i2uvvTbWX3/9YtuJJ54Y9957b9xyyy3x1ltvFRUhueBqGjJkSDz55JNx6aWXCkAAAACA9g1ATjvttIbvDz/88BgwYEBDIFIxc+bMIpyYH/369YtLLrkk1lprrYZtGa7kZerUqTF27NjYdtttm9xnk002iZEjRzYsutpcbqrNNUpqsc1lUBddutj3C3N/Uw3l6+eV11O210Xb1eSv/lLouO8v5XyfKNNrqSUdt5+Xk31drf3epeT9vE1rgGyzzTZF1UZOQ2nslVdeib322isee+yxVj9WTqnZcsstm2y7/fbbi8qQH/7wh8U0mAxbGltmmWXi/fffjylTpszRhrTkkr1Lf+BoP927d43+/XvbpZRamft5v36LVbsJ0KnVwvuL9wkWVC30c1hQ3TtBP291ADJmzJji7C8pKy923XXXOSpAsmIjp8csiL///e/xgx/8ILbffvvYaqut4oMPPohFFlmkyW0q///www9bfIzJk6fVZAVI3769qt2ETmnGjFkxder71W5Gp6GfV0cZ+3kG3TmomTLl3Zg9u77azaEDWHxxv0eroSO/v5TxfcLv0eroyP28jPTz6phRw/28tcFNqwOQXXbZpai4yPDjZz/7Weywww6x2GJNP3XL/2dw0VZ33nlnHHPMMTF06NAYPXp0sa1Hjx5zBB2V//fq1fIfOvX1/wtpak8ttrkM6kvzR1FtsK+rtd/L2s/zdZX1tTF/avJXfyl0/J/Bcr1PlOV11Joy9aFaYF9Xa7/PLnk/b3UAkmHDoYceWnyf1RV5lpa5BRBtcc011xTremSwcsYZZzRUeeRpbydNmtTktvn/RRddNPr06dNuzw8AAACUV9M5LK2UQUhWg0ybNq34/4MPPhjDhw+PW2+9tU2NyDPAjBgxIvbYY4/iVLiNp7xssMEG8fDDDze5fT5fVok0n4IDAAAA0JI2JQh33HFHMdUlFzt96aWXYv/9948HHnggTjjhhGKtkPkxYcKEOPXUU2O77baLgw46KN5888144403iss777xTLKr6r3/9q5gSM378+GIdkj/+8Y/FcwIAAAB8bGeBueCCC4opMJtuumlceOGFxcKnt912WxFMnHfeeUUlR2vlGV9mzJhRhCp5aWznnXeO008/vXi+M888M6688spYfvnli+/zuQEAAAA+tgAkKzHOP//8YgpKng43T2Ob36+77rrxn//8Z74e6+CDDy4u87LFFlsUFwAAAICFNgWmb9++xfSUvOT0lM985jPF9pwOs8QSS7SpIQAAAAAdqgIkKz5+9KMfFae9zTOxbLbZZnH//ffHySefHFtttVX7txIAAABgYVeAnHjiicVZWPJUtLkGSJ615dFHHy2mwBx77LEL0h4AAACAjlEB0rNnzzjuuOOabDvssMPaq00AAAAA1Q9A0hNPPBGXXXZZjBs3Lrp16xYrr7xyfPvb34611167fVsIAAAAUI0pMA8//HB84xvfiBdffLFY/2PDDTeMCRMmxLe+9a1iKgwAAABAzVeA/OQnP4ldd901fvzjHzfZnv8/55xz4uqrr26v9gEAAABUpwLkySefjL333nuO7XvuuWcxNQYAAACg5gOQfv36xZQpU+bYPnny5OKMMAAAAAA1H4B87nOfixEjRsT48eMbtj333HNxyimnxNZbb92e7QMAAACozhogRxxxROy7776x4447Rp8+fYpt77zzTqy++uoxbNiwBW8VAAAAQLUDkMUXXzyuv/76uPfee+PZZ5+N+vr6WG211WLzzTePLl3aVFQCAAAA0LECkJRBx4orrhjTp08vvl9llVWEHwAAAEB5ApBp06bFUUcdVVSAZPVHqquriy9+8Ytx2mmnWQgVAAAA6FDaNF9l5MiRMWHChLjkkkti7Nix8fDDD8eFF14Y//znP+Pss89u/1YCAAAALOwKkDvvvDMuuOCC2HDDDRu2bbXVVkXlxzHHHBPHHXfcgrQJAAAAoPoVIF27dm04+0tjSy+9dMycObM92gUAAABQ3QBk7733jhEjRsSbb77ZZF2Qc845p7gOAAAAoOanwNx3333x+OOPxzbbbBODBg2Kbt26xQsvvBDvvvtuPPXUU3HTTTc13Pauu+5qz/YCAAAALJwA5DOf+UxxAQAAAChtAHLooYe2f0sAAAAAOtIaIAAAAAC1RAACAAAAlJ4ABAAAACi9Vgcgo0aNirfffrv4/tVXX436+vqPs10AAAAACz8Aueaaa+Kdd94pvs/T306ZMqX9WgEAAADQEc4CM3DgwOLsL5/61KeK6o9TTjklevTo0eJtTzvttPZsIwAAAMDCCUDOPPPMuPjii+M///lP1NXVFdNgunfvvmDPDgAAANCRApA111wzzjvvvOL7rbfeOi688MLo16/fx9k2AAAAgIUbgDR29913F1/Hjx8f48aNKypBhgwZEiuttFL7tAoAAACg2gHIhx9+GEcddVTceeedDdtyWsznPve5OOecc2KRRRZpzzYCAAAALJyzwDR29tlnx7/+9a/42c9+Fo888kg89NBDxfSYJ598smGaDAAAAEBNByC33npr/PjHPy5Oh9unT59YfPHFY9ttt42TTjopbrnllvZvJQAAAMDCDkDefffdGDx48Bzbcw2QyZMnL0h7AAAAADpGALLqqqvGH//4xzm2/+EPf7AQKgAAAFCORVC/+93vxiGHHBJPPfVUDB06tNj26KOPxh133BFnnXVWe7cRAAAAYOEHIFtttVX89Kc/jZ///Odxzz33RH19fay22mrFGWC23377BWsRAAAAQEcIQNJ2221XXAAAAABKuQYIAAAAQC0RgAAAAAClJwABAAAASq9NAcjYsWNjxowZ7d8aAAAAgI4SgBx22GExbty49m8NAAAAQEcJQJZccsl455132r81AAAAAB3lNLhbbLFFHHTQQbHlllvGiiuuGD169Ghy/aGHHtpe7QMAAACoTgBy++23R//+/eOJJ54oLo3V1dUJQAAAAIDaD0Duvvvu9m8JAAAAQEc8De4jjzwSv/rVr2LatGnx3HPPxcyZM9uvZQAAAADVrADJwGO//faLxx57rJjystlmm8Xo0aPjpZdeil/84hex7LLLtlf7AAAAAKpTAXL22WcXwccdd9wRPXv2LLZ9//vfLxZDHTVq1IK3CgAAAKDaAcif//znGDZsWKywwgoN24YMGRI/+tGP4oEHHmjP9gEAAABUJwCZPHlyLL300nNs79u3b7z33nsL3ioAAACAagcga621VvzhD3+YY/uYMWNijTXWaI92AQAAALSbNi2CetRRR8V3vvOd+Ne//lWc+eXCCy+M8ePHx7///e+47LLLFqhBF198cdx3331x9dVXN2w74YQT4je/+U2T2w0cONDpeAEAAICPrwJk6NChxelve/XqFSuuuGL885//jAEDBhQVIBtvvHG0Vd7/nHPOmWP7M888EwcffHARjFQu119/fZufBwAAAOhc2lQBklZfffU488wz26URr7/+epx00knx0EMPxaBBg5pcV19fH88991wceOCBLa47AgAAAPCxVICkO++8M/bYY4/YaKONYvPNNy+m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UHoCEAAAAKD0BCAAAABA6QlAAAAAgNITgAAAAAClJwABAAAASk8AAgAAAJSeAAQAAAAoPQEIAAAAUHoCEAAAAKD0BCAAAABA6QlAAAAAgNKriQBk9uzZce6558ZnP/vZWHfddeOAAw6Il19+udrNAgAAAGpETQQgF1xwQVx77bUxYsSI+NWvflUEIvvvv398+OGH1W4aAAAAUAM6fACSIcfll18ehx9+eGy11Vax+uqrx09+8pOYOHFi/OlPf6p28wAAAIAa0OEDkKeffjrefffd2HTTTRu29e3bN9ZYY4145JFHqto2AAAAoDbU1dfX10cHllUehx12WDz22GPRs2fPhu3f+9734oMPPoiLL754jvu8+eY7UVdXF7Wmb99eMXtmfUx65b1qN6XTGDi4T8z4cJZ9bp+Xmn5uv3cW+rp93hno5/Z5Z6CfL3zLLL9odOlWF1Onvh+1qH//3q26Xbfo4N5//38HYJFFFmmyvUePHvH222+3eJ+lluoTNat7xAqr9K12KzqVHr262ef2eenp5/Z7Z6Gv2+edgX5un3cG+nnHDhJqVYefAlOp+mi+4On06dOjV69eVWoVAAAAUEs6fACy3HLLFV8nTZrUZHv+f9lll61SqwAAAIBa0uEDkDzrS+/eveOhhx5q2DZ16tR48sknY8MNN6xq2wAAAIDa0OHXAMm1P/bcc88YPXp0LLnkkjFw4MA488wzY8CAAbH99ttXu3kAAABADejwAUg6/PDDY+bMmXHCCScUZ37Jyo/LLrssunfvXu2mAQAAADWgw0+BSV27do3vf//78cADD8Q//vGPuOSSS2L55ZevdrNYQHkK47322muO7S+++GKsu+668corr8yx8O2Pf/zj2HTTTWO99daLo48+OiZPnuw4lLxP3H333bHrrrsWx3zrrbeOM844owhCK/SLztcnfv/738dOO+0Ua6+9dmy77bbx85//PBqf0X327Nlx7rnnxmc/+9niveSAAw6Il19+uQqtZ2H+7qjID0vyvaIxfaLz9YnsB6uttlqTS+N+oU90vj6R6wceddRRscEGG8TGG2/c4t+RY8aMiW222ab4/fKtb32rmHJPOftEft/8PaJy+e1vf9twO32ifGoiAKF88s3knHPOmWP7+PHj4zvf+U7D6Y8bO/nkk+O+++6L8847L6688sp4/vnni+ogytsnxo4dG4ceemhst912cdNNN8VJJ51UDH4zCKvQLzpXn7j33nvjmGOOid133z1uu+22GDZsWFxwwQVx1VVXNdwm/3/ttdfGiBEj4le/+lUx0Nl///3nOJsY5fndUXHnnXfGb37zmzm26xOdr08888wzcfDBBxd/N1Qu119/fcP1+kTn6hP5/p9/X7766qvF74v8MPXpp5+OY489tuE2+XfGqFGj4nvf+17ceOONxYet++67rw/bStoncjzR+P0h/77IcGyVVVYp/u5M+kRJ1cNCNHHixPqDDjqoft11163fYYcd6vfcc8+G6y666KJi+84771y/6qqr1r/88stN7rf66qvX33PPPQ3bnn/++eJ2f//73x3DkvaJo48+un6fffZpcvubbrqp/tOf/nT99OnT9YtO2CduuOGG+p/85CdNbn/IIYfUH3DAAcX32S/WW2+9+jFjxjRc//bbb9evvfba9bfccstCfBUsrD5R8frrr9dvsskmxXWf+9znGrbrE52vT8yePbvY/qc//anF++oTnfN3R25/4403Grb99a9/rd9mm23q33nnneL/22+/ff2oUaMarp8xY0b9lltuWfx9Snl/d1RcffXV9WuuuWb9+PHjG7bpE+WkAoSF6t///nexdsvNN98c66yzzhyf3J122mlN0viKRx99tPi6ySabNGxbaaWVilMhP/LIIwuh5VSjT+SnNc37Q5cuXWLGjBkxbdo0/aIT9olddtkljjjiiOL7rOy4//77i/eAzTbbrNiWn+i9++67xVS5ir59+8Yaa6zhvaKkfSLlFKjjjjsuvvKVr8RGG23U5Dp9ovP1iZdeeinee++9GDx4cIv31Sc6X5/IT/jzb8illlqqYVtOk8y/PfNsk2+99Va88MILTX53dOvWragI8HdmeX93VORUqKwQ+e53v9vwvqFPlFdNLIJKeeT82+ZzsysqZcuNT3lc8frrr0e/fv2iR48eTbYvs8wyMXHixI+ptVS7T+SgtbEMPq644opYc801i7NC6Redr09UZBlzlqjmAtmbb755fPOb3yy2V94PlltuuSa3915R7j6R7wtvvPFGXHTRRcU878b0ic7XJ8aNG1d8vfrqq+Ovf/1rEZxvscUWceSRR0afPn30iU7YJyZMmFCEGT/72c+K9R0qvztyjcEMyef1PpGBGeX9eyLlWmI9e/aM/fbbr2GbPlFeKkCoCbkmSJ4SubkMRHIRTMov/1jJ9R6effbZYi2QpF90XvkHa4am+YlN/nGafSNV1g9q/n7hvaK88viff/75ceaZZ7b4e0Kf6HwyAMnQIwevGYpldVBWABxyyCFF5Zg+0flk1WgGH7k2zFlnnRXDhw8vqkizT2QFmT7RufvGddddV4QfjT9o1SfKSwUINSFT2ZYWMMzwo1evXlVpEwv3l1NOe3j44YeLgU6uzp70i84rS5azQigvs2bNKlbzz0/ysk+kfL+ofJ+8V5RTHtdcFDfLlldfffUWb6NPdD7ZH/IMHlk5mlZdddVYeumli8WTH3/8cX2iE8rpLIsuumgRfuSUiLT44ovHbrvtNkefaMzvjvLLaVB53POMg43pE+WlAoSaMGDAgPjvf/87xy+mPKVZrgNCeeUx3mOPPeKf//xnXHbZZbHllls2XKdfdD55ZqB//etfTbblKesqfaVSvpzfN+a9opwee+yxoiosg9E8VXZecgpMTpHK77O/6BOdT1Z/VMKPijyzQ6WsXZ/ofPLvhVw7rhJ+NO4Tr7zyij7RyQOQ/NsyK0sb8z5RXgIQasL6669flK1WFkOtzOfMNSA23HDDqraNj8/bb78d3/72t4vFqfIUZs2PtX7R+eTpC0899dQ5BsH56d6gQYOKKoCsDmm8ltDUqVPjySef9F5RQlkN9qc//Sl+97vfFeXtefnGN75RTH3I73O9IH2i88kpcfvss0+Tbfkpf1p55ZX1iU4o/37I6XIffPDBHGvFrLjiitG/f/8iIGn8uyOn3maI6u/Mcstj3Hjx2wp9orxMgaEmZJXHl770pTjhhBOKwU9Oe8l1IHK1/3XXXbfazeNjkmcFevnll+PSSy8tFj3NRQ4r8v/6ReeTg5o999wzfvKTnxRnhMlgI9d+2HvvvRs+8c3rR48eXfSRgQMHFtfnp3/bb799tZtPO8sS5Ry8NJZl7RmINd6uT3Qun//854u1HbIy6Mtf/nLxgUmu+bDjjjvGkCFDitvoE51LBqP5QUpOl8wptRmMn3zyybHxxhvHpz/96YYzz40cObJ471hrrbXikksuKQKTr33ta9VuPh+T1157LaZMmTLXKZT6RDkJQKgZI0aMKMKPQw89tPh/ruiegQjllOs6/P73vy/O/JJVIM3dddddsfzyy+sXnczQoUOLKQ65+Gme+SNDjvwD5YADDmi4zeGHH158cpfvD/nHa356l9OnGpc+07noE53LNttsU7xH5AA2z+6QZ37ZaaedGk6hnfSJziV/V2QAkh+s5LofuWDytttuWyyQW5FrxLzzzjtF38lp11lB9otf/KK4L+VU+WBtiSWWaPF6faKc6upz6WMAAACAErMGCAAAAFB6AhAAAACg9AQgAAAAQOkJQAAAAIDSE4AAAAAApScAAQAAAEpPAAIAAACUngAEAAAAKD0BCAA1adq0abHOOuvEZz7zmZgxY0Z0RFtvvXWcd9557fZ4+Vj5mHPzyiuvxGqrrRYPPfRQuz3ncccdF3vttVerb//ee+/FmDFj4uPycbzG+elzX/jCF2LixIkfeXxzn+W+q6ivr4+rrroqvvKVr8Taa68d66+/fuyxxx7xxz/+scn98jHz9VUua665Zmy11VZx0kknxeTJk+dr38/vsaslN954Y7F/WuP999+PL37xi/Hqq69+7O0CoGMTgABQk2677bbo379/vPPOO3HHHXdEZ/Cd73wnrr/++oX6nMcff/x8hTiXX355XHbZZVFGo0aNKgbSAwYMmO/7nnvuuXHJJZfEQQcdVPTdX/3qV7HxxhvHEUccEb/97W/nOM733XdfcfnDH/4QJ554YhH47LnnnkV/74z7fkH06tUr9t9//zjhhBOq3RQAqkwAAkBNuuGGG+Kzn/1sbLLJJsVgsjNYbLHFYskll1yoz9mnT59YYoklWn37rHQooxdffLEIKvbee+823f/aa68tBuEZoKywwgqxyiqrxOGHH15UlFx55ZVNbrvooovG0ksvXVzytttss00Rbrz22mtx6aWXdrp93x6y8uaZZ56JBx54oNpNAaCKBCAA1Jzx48fHY489Fptttllsv/32xafjEyZMaDKNID8JP+yww2K99dYrPmk/5ZRTYubMmQ3l89ttt13D15xmsMsuu8Sjjz7a5DGaVz403/ab3/wmdtppp2JKw7rrrhvf+ta34vHHH5+vqRxZDfDVr3411lprraIN+dp+9rOfFVN7Ntpoo/jxj3/cMLBtPgVm3LhxxYA8nztfR/PBXU6BOOqoo2L48OExdOjQ2HTTTeP000+PDz/8sOE2Oag+5phjin2Zj7PffvvF008/3eI0itzPa6yxRvzlL3+JHXfcsdhvO+ywQ9x5550N7Tv//PPjP//5T/Ha8jU2N2vWrDjz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",
      "text/plain": [
       "<Figure size 1100x550 with 1 Axes>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "fig, ax = plt.subplots()\n",
    "ax.hist((jobs.salary_min + jobs.salary_max) / 2000, bins=10, color=purple, edgecolor='white')\n",
    "ax.set(title='Distribution of salary midpoints', xlabel='Annual midpoint salary (USD thousands)', ylabel='Number of postings')\n",
    "fig.tight_layout()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 5. Line chart — postings over time"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 5,
   "metadata": {
    "execution": {
     "iopub.execute_input": "2026-09-28T12:23:31.563272Z",
     "iopub.status.busy": "2026-09-28T12:23:31.560735Z",
     "iopub.status.idle": "2026-09-28T12:23:32.330690Z",
     "shell.execute_reply": "2026-09-28T12:23:32.325684Z"
    }
   },
   "outputs": [
    {
     "data": {
      "image/png": "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joDzDfyAzySgn8DvARDf1AABAAAAAACoLQRAAAAAAABAzCMAAgAAAAAAYh4BEAAAAAAAEPMIgAAAAAAAgJhHAAQAAAAAAMQ8AiAAAAAAACDmEQABAAAAAAAxjwAIAAAAAACIeQRAAAAAAABAzCMAAgAAAAAAYl5cKBQKRbsRAAAAAAAAtYkMEAAAAAAAEPMIgAAAAAAAgJhHAAQAAAAAAMQ8AiAAAAAAACDmEQABAAAAAAAxjwAIAAAAAACIeQRAAB9btGhRtJsAAKgH5s2bZzNmzIh2MwAE3G+//RbtJgCbRQAkCrKzs+3HH3+0UCgUjZdHAPz55592/vnn28knn8yJBJXKysqyhQsXuu/FxcVumfcdkMzMTPvqq69sxYoVVlBQ4JZx7kH5883ll19uxx9/vE2fPp0+gkqPJcuXL2frYLOfXc877zy76KKL3DkHqEhOTo798ccftnbt2tJldf25hABIFNxzzz12/fXX28qVK6Px8vC5W265xQ455BBr3Lixvf/++7bDDjtEu0nwoXHjxtkRRxxhN910k5100kl29913u+Xx8RzWsdFdd91lhx9+uN15550umPrAAw+45XFxcWwiOGPHjrXevXu7D6TbbbedtWrVij6CCt144402fPhwtg42+9m1SZMm9tRTT1nLli3ZUtiEPqseffTRNmzYMPe55OWXX47K55LEOn21ek53ZnVx8uuvv9rcuXNtypQpbucnJrIbYPb333/b1Vdf7e7APffcc7bXXnuV2SyKjnLhAnnnnXfsvffecxe4O+20k3300Uf2xBNPuD508803s5FgL774on3++ecu6NGpUyd7+OGH7ZNPPrEjjzzSdt55Z7ZQPTdp0iR3rNhxxx3t+eeft65du9oBBxxgaWlp0W4afEafPfS1ZMkSl3E4depUFzQDvMygiy++2N3Rf/bZZ92xBKiIrm0mT55st956qwuQvfrqq+6zifrOpZdeWqfXOdwqrEXl03kU/Pj5559dCqE+kI4fP96WLl1am01AgPpI06ZNrWHDhu6DRfv27UuX66JWCH7UX+H9RIHUl156yTp27Gi9evVyJ5EzzjjD/u///s9F0nWRi/rdRzTU5T//+Y/ts88+tt9++1mzZs2sR48etn79emvXrl1U24noy8/Pd8eJa665xl5//XV3wbJgwQJ3jtHdWyCc+oVu2q1Zs8Yd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8uyjjz6KyBYNhUJlfm/cuLE1a9bM93urfLsBAIA/EAABAAARkZiY6L4nJSW57wqGjBs3zvr06WO77767HXfccfbBBx+Urr9hwwa744477KCDDrLddtvNjjjiCHvhhRfcY6+99ppdffXV7mcNs5k+fXqZITDLli1zy/V8J598svt7PfbSSy+VaZOG0Gj5HnvsYeeee6498MADmx1Gs2bNGhs+fLh1797d9ttvP3vyySc3WUfDW/r27euec6+99rLTTz/dvv/+e/fYiBEj7PXXX7dvvvnGtc8LiEyYMMFthz333NNtBzJEAACoewRAAADAVvvzzz/t5ptvdpkhCmjIkCFDbNKkSXb99de7C/5DDz3ULrvsMvv444/d488//7y9//77ds8997hAhmqIjBw50mbOnGlHHXWUXXPNNW49DbPp2rVrha+rITL/93//Z++995717t3b/f3SpUvdY88995x77ksuucTeeOMN22effezBBx/c7Pu4/PLL7bvvvrOHH37YBT+mTp1qv//+e+njym7R+9RQH72mAiz5+fl23XXXucevvfZaO/LII1171W5RGxTY0XZ46623bMCAAa6dah8AAKg7G2/VAAAAVMMjjzxiTzzxhPu5qKjICgoKrGPHji7jY/vtt7fFixfb5MmTXSBBgQkZPHiwzZ8/3y1TMOS3335zAZM2bdq4YTQKgHTo0MHat29vKSkplpqa6v5Ow2wqc84557jMCrniiitcUGHOnDnWtm1be/zxx12w4aSTTnKPX3zxxfbjjz/a3LlzK3yun3/+2QUtFNRQBojcdddddvDBB5euk56ebmPGjLFjjz3W/d66dWv3/AqKiNqstjdo0MC1e/369e757r777tLtsMMOO7igitp3xhln0O8AAKgjBEAAAEC1nXrqqXbWWWe5n+Pj411gwAtYyIIFC9z3vffeu8zf9ejRwwUDRBf/ygZRxsjOO+9sPXv2tKOPPtqaN29e5XYo6OLxXl+zx2gmFgUZNEQlnAIblQVAFi5c6L5ruI5nm222ccGU8PYruKNMEgVMlixZ4t5rcXFxhc+5aNEilyEydOhQt508XtBIw4QUMAEAALWPAAgAAKi2tLQ023HHHav9d6qH4dUKadeunX344YeuXsYXX3zhhpuoVoaGtRx//PFVej6v3khlr1GdgqRxcXHue/lghvdcoiEsqvOhGiCa+leBIAVOvAyQitoiyoxRdktV2g8AAGoHNUAAAEDEeQVAZ82aVWa56nvstNNO7uenn37aBUCU+TFs2DAXXNh///3t3XffLROQqAllg2h4yuzZs8ssL/97OGWhyH//+9/SZX///bcbquN59NFH3ZCXW2+91WWwKCPEqzniBTvC262ghwIomhpYASPv69NPP3VDYMKzQgAAQO0iAwQAAESchqaodoamxlVAQBf977zzjqsLomwIyczMdENJNASkS5cubkjJvHnzXN0OUX0Q+eGHH0qDJtVxwQUX2G233eaCEBqKo+E2KrbaqlWrCtdXbQ7NRKNsDmVmaPiLhutoqIpHf6sAiWqJKMgyZcoUe/bZZ91jWi85Odm1e+XKlS4wouEzyhK59957rUmTJi5rRDPaaPabiy66qEbbFgAA1AwBEAAAUCsUPNCXZkZRJkWnTp3cVLaHHXaYe3zQoEGuXsfo0aNt1apVrmjoaaedVhoY0DS0mjZWAQQFDKpLz5WTk+MCLqoJollgNLSmfFZKOAVM9KWCqhoK079/fxeo8WgmlxtuuMEVbFWQRIGb22+/3a2vqXBVY6Rfv35utphjjjnGZbhoOt+MjAwXBFFgREGUSy+91M0kAwAA6k5cqDqDYwEAAALis88+c5kjmpUmPIChIS1PPfVUVNsGAADqHgNPAQBATHrjjTfskksucXU/NCPMpEmT7M0337Tjjjsu2k0DAABRQAYIAACISdnZ2a5Y6eeff+6G4KgOiabu1bAWAABQ/xAAAQAAAAAAMY8hMAAAAAAAIOYRAAEAAAAAADGPAAgAAAAAAIh5BEAAAAAAAEDMIwACAAAAAABiHgEQAAAAAAAQ8wiAAAAAAACAmEcABAAAAAAAxDwCIAAAAAAAwGLd/wPmhNWKx6W26AAAAABJRU5ErkJggg==",
      "text/plain": [
       "<Figure size 1100x550 with 1 Axes>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "timeline = jobs.groupby(pd.to_datetime(jobs.posted_date)).size().sort_index()\n",
    "fig, ax = plt.subplots()\n",
    "ax.plot(timeline.index, timeline.values, color=cyan, marker='o')\n",
    "ax.set(title='Synthetic postings over September 2026', xlabel='Posting date', ylabel='Number of postings')\n",
    "fig.autofmt_xdate()\n",
    "fig.tight_layout()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 6. Pie chart — employment types"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 6,
   "metadata": {
    "execution": {
     "iopub.execute_input": "2026-09-28T12:23:32.338972Z",
     "iopub.status.busy": "2026-09-28T12:23:32.336979Z",
     "iopub.status.idle": "2026-09-28T12:23:32.642650Z",
     "shell.execute_reply": "2026-09-28T12:23:32.637043Z"
    }
   },
   "outputs": [
    {
     "data": {
      "image/png": "iVBORw0KGgoAAAANSUhEUgAAAnEAAAKICAYAAAAfEKzpAAAAOnRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjEwLjksIGh0dHBzOi8vbWF0cGxvdGxpYi5vcmcvJkbTWQAAAAlwSFlzAAAQ6wAAEOsBUJTofAAAaqhJREFUeJzt3Qd8m9XZ9/FL8t4rzt57hwyygCRkB0gos0CBFmgfeFr6FijdpVCgQIECLR0PtIRZRtkr7JEQQghk723HdmLHdry3Lb2f6wS5juMh21q39PuCPo5lWTo6ui397zNtTqfTKQAAALAUu78LAAAAgI4jxAEAAFgQIQ4AAMCCCHEAAAAWRIgDAACwIEIcAACABRHiAAAALIgQBwAAYEGEOAAAAAsixAEAAFgQIQ6d8vDDD8uIESPavfiaPuaNN94ooaKurk6OHDni1m0PHTokVpWdnW1e2/vvv99j91lRUSEFBQUnHdP79++XYNT09fdGfapjx45JeXl54/e//OUvzePU1NRIoGn++rvrlVdeMc9p1apVXikX0BHhHbo10Mx1110ngwcPpl78ICcnR6655hr57ne/K5deemmbt9XbJSYmyoMPPihWlJqaKvfee68MHz7cI/e3bds2+eEPfyh33nmnzJo1S4KdL17/lStXys9+9jN57rnnJD4+3lz37W9/W2bMmCERERESSELt9UfwIsShS2bOnCnTpk2jFv1AW1MOHjzo1m1Xr14tZ511llhVbGysnHvuuR67vz179kheXp6ECl+8/lu2bJGSkpITrps4caK5BJpQe/0RvOhOBQAAsCBCHHxCxxuNHj1aMjIy5H/+53/M2fn06dPlnnvukfr6elmxYoWcc845MmHCBPnWt74lX3zxxUnjd7Sb5oEHHjCtf5MmTTJdRDt37mz3sTdt2iTf//73ze/o/V9yySXy4YcfntBKofe/fPnyk35Xu59GjRolubm58uWXX5rbabfRbbfdZsqvz0O7lHVsjZbliiuuMI8xd+5ceeKJJ066Px1Hc9lll8kpp5xiyvODH/xAtm/ffsJt9D70snbtWtMdNX78eDnttNPkD3/4g1RXVzeOy7nyyivNv7UsrY0/dNWd0jrWf2vdzp49W5YuXXrS7fX10dv83//9n/len8fNN98sb7zxhixcuNA8t/POO0/ee++9k373wIED8v/+3/+TqVOnmjKff/755jGbe+SRR2TJkiXmNtqKe/3115uWkba0NIZLv9fj6t///rcsWrRIxo4da77q923R3/nVr35l/q31r8+xeTe1Pg99fSZPniw/+tGPzHVN1dbWmvtZsGCBedw5c+aYY7npeLDW6Jg7fVztZtQ60OP+n//8pzgcDvNzPcb1uWmXX3N67OpzdD0PvZ3WjdahllXLrP/W65rWW9PXX49jl4aGBvnb3/5m6mDcuHGybNkyeffddzt83OrYt7/+9a/m39rip8dva2PiCgsL5Xe/+53pxtTjSY/D//znP+IOfQ/Q9wf9PT2G9X50HJ6Lvpc89thj5hjVv019TosXLzbHnKt+23r9161bZ/6e9W97zJgx5r3mpptuksOHD7dZLr3vJ598Us4++2xzPOhrq13LzY8b1+vgeg56/Ohz+s1vfnPScQi4gxCHLikrKzNvoi1dqqqqTrit0+k0b+46vukXv/iFCUePP/64edO84447zBugTko4evSo+SBq+uasHn30UXnppZdMeHF9iHznO9+RvXv3tlo+DVx6Gw0Y+js33HCDKZd+MD/zzDPmNvqGm56eLm+//fZJv6/XnXrqqdKzZ8/G6/SDQ0OH3pd+6H3yySemvFdddZX5wNIPiOTkZLn77rvl888/b/y91157zQRYm81mPhj03xqadDzbhg0bTnhc7SbVMTv6IfTb3/7WfKA89dRT8pe//MX8XMuk9aY0LOl4sbbGkin9ANZ/Dxs2zNS1Pod9+/adcPu33nrLlK9pwFu/fr38+te/NkFFy60fWBpyXn311cbb6Gtw8cUXm+Ch4VqDX1xcnHk9m4ZZfQ01pGh40eeldab3f/nll0tRUZF0lJbh73//u+lq1XoPDw+X22+/3bzurdEPTg3HSsuqz60pfW76HPUY1Q9bfX1dda30Z//7v/9rgoGGa9cHsB5P3/ve90zAa01xcbF5zhrk9LG1DgYMGGDCqYYLpceUan48aiDQE5Lm4Vv/HvQ109Cgx8JHH31kjs3WXv8hQ4Y0/q4GCD0utf71tdXuUP1d7RrtyHGr9an1qrQcTeurKb3/Cy+80JyEaBjV16xPnz5yyy23mCDbFh2/picsKSkp5jH0tdGTC61HV51rfd53333m70bvW4+/qKgoc8xpyGrr9deTG339NGTq356W6fTTTzeh69prr22zbFqeu+66yzwXfVx9HfREUZ9rVlZW4+1eeOEFU6bIyEj56U9/KvPmzTMnZ01PKoEOcQKd8Je//MU5fPjwNi96m+a3v/XWWxuvKykpcY4ePdo5YsQI55YtWxqvf+GFF8xtP/roI/N9VlaW+X7s2LHOjIyMxtvt2bPHOWrUKOcPf/jDxuv0djfccIP5d319vXP27NnOmTNnOouKihpvU11d7TzvvPOc48aNc+bn55vr7r77bvO7mZmZjbfbuHGjue7FF180369du9Z8f8455zjr6uoab3f++eeb65cvX9543cGDB811er+qrKzMOWnSJOd11113Qj3q9WeeeaYpj8vll19ufvftt99uvK6hocE5b9485+mnn954nas8zz77bLuvV9N6Ubt27TLXPfjggyfcbvHixc7LLrus8Xstm97utddea7yusrLSlGX69OmN9XDFFVeYutbX1MXhcDivv/56U8+FhYXmurPOOst59tlnn/CYn376qbn+yy+/bLX8rmPgvvvuO+E56TGRk5Nz0u1uuummNuvj5ZdfNrdbuXLlScfor371qxNu+8tf/tJcv2/fPvP9q6++ar5///33T7jdhx9+aK5/6qmnWn3cFStWmNu88847J9TT1VdffUKZ9XiYM2eO+ZnLI488csIx6irv7373uxMe4xe/+IW5Xo/B1l5/Vz1NmzbthL+NdevWnVDPHTluXeVx1VPTsujfnNL71e9Xr159wvPXY/7UU0911tTUtFhve/fuNe8TP/3pT0+ok5deesncn9ar/i2PHDnSeccdd5xUVj1OrrrqqjZf/x/84AfmvUKP76ZuvPFGc9vc3NwWf/ezzz4z3//mN7854fc2bdpkyux6fyovL3dOnjzZecEFFzhra2sbb/fee++Z39f6BDqKljh0ibZWaGtaSxc9U27O1RWkdLZcWlqa9O7d25w5u/Tr1898zc/PP+F3tfVIWy1ctEXpjDPOMN2hLbV+aEudLr+hLQbaMuaiZ+Z6Bq5dPK5lAlpq/dBWKb1t0zIrPXvWFh+XQYMGma+uloiWnsOaNWtMV5veV9PWSi23dgtpWZsOtNbZfE3vz263m1a+ziyJ0BLXEjDvvPNO43U7duwwLZbNW3q0dcFVPyomJsbUqZZfW4a0BU27obR7TLuzXM9Nr9cuWK1nV4uktmjqY2jXm6vLT5+/1rt2w3aUti7p8ePSt29f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xqCWpmEtSpLSoiSpW5TEJUacFMoIawA8jRAHwOcteNpVaLO33PpUXVEvVRV1Ul3ZIDWV9VJT1SA11Q0mBOq/a6sapLqq3qyBpxcNfQ0NDrOosf5bv7qCpMZB17/DwmwSFmEze4SGh9slzHzV6+zmOm0dC4+wmUkDGtBi4sPNUh16iU2IMMEtKjbMbAZ/0nP65jFae04A4A2EOAABH/iOd9v6LiC5xqQpujoBBCpCHAAAgAWd3C8A+MEVV1whI0aMaPHyxz/+sd3f//LLL81ts7OzG+/vl7/8ZZu/s3fvXvn0008bv9fff+WVVzzwbAAA8L7jCxABAWDJkiXym9/85qTrY2JivPJ41157rZx33nkyZ84c8/3q1aslISHBK48FAICnEeIQMKKjoyU9Pd1vj+/PxwYAoKPoToUltNQ96k6XaWvmzp0rOTk58te//tXcT/PuVL3fn//853LnnXfKlClTZOrUqfKXv/xF9u/fL5dddpmMHz9eli5dKps3b268z7KyMrnllltk+vTpMnnyZLnyyitl69atXXreAAC0hhCHkPTSSy9Jz5495eqrr5aHH364xdusWLFCwsLCTLD73ve+J3/729/kuuuuk2uuuUZefPFFiYqKkt///veNsxl/8IMfSFZWljzyyCPyn//8R0455RS59NJLZceOHT5+dgCAUECIQ8B48803ZeLEiSdcvv/973vlsVJTU01Ai42NleTk5BZvo9f/4he/kP79+5sQp8466yyZN2+eabU7//zzZc+ePeb6tWvXyqZNm+Shhx6SCRMmyJAhQ+Smm24yQe6pp57yynMAAIQ2xsQhYGgX580333zSOLmu0iC4fv36xu+19WzZsmXt/l7fvn3Fbj9+nqNhT/Xr1++EstXV1Zl/b9++3bTGnXnmmSfcR21trdTUsFk8AMDzCHEIGHFxcTJgwAC3b19f795enH/4wx+kurq68fu0tDS3fi8iIuKk61yhrjmHwyHx8fEtLlESGRnp1uMBANARhDhYggaq8vLyE0KTjj9zJ/T16NHDy6UTGT58uCmftswNHTq08frf/va3MnLkSLn88su9XgYAQGhhTBwsQceWff7557Jq1SrJzMyUO+64Q0pLS7vc8peRkSEFBQVdLt8ZZ5who0aNkhtvvNGMj9My3n333aZlTsfHAQDgaYQ4WILOItUJBT/5yU/k4osvNmPUzj777C7dpy4tojs26H13lU6SWL58uYwdO1ZuuOEGM+buq6++MkuYzJgxo8v3DwBAc+ydCgAAYEG0xAEAAFgQIQ4AAMCCCHEAAAAWRIgDAACwIEIcAACABRHiAAAALIgQBwAAYEGEOAAAAAsixAEAAFgQIQ4AAMCCCHEAAAAWRIgDAACwIEIcAACABRHiAAAALIgQBwAAYEGEOAAAAAsixAEAAFgQIQ4AAMCCCHEAAAAWRIgDAACwIEIcAACABRHiAAAALIgQBwAAYEGEOAAAAAsixAEAAFgQIQ4AAMCCCHEAAAAWRIgDAACwIEIcAACABRHiAAAALIgQBwAAYEGEOAAAAAsixAEAAFgQIQ4AAMCCCHEAAAAWRIgDAACwIEIcAACABRHiAAAALIgQBwAAYEGEOAAAAAsixAEAAFgQIQ4AAMCCCHEAAAAWRIgDAACwIEIcAACABRHiAAAALIgQBwAAYEGEOAAAAAsixAEAAFgQIQ4AAMCCCHEAAAAWRIgDAACwIEIcAACABRHiAAAALIgQBwAAYEGEOAAAAAsixAEAAFgQIQ4AAECs5/8DDwtrTPl4vgsAAAAASUVORK5CYII=",
      "text/plain": [
       "<Figure size 770x660 with 1 Axes>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "counts = jobs.employment_type.value_counts()\n",
    "fig, ax = plt.subplots(figsize=(7, 6))\n",
    "ax.pie(counts.values, labels=counts.index, autopct='%1.1f%%', colors=[purple, cyan], startangle=90, wedgeprops={'edgecolor': 'white'})\n",
    "ax.set_title('Employment types in the synthetic catalog')\n",
    "fig.tight_layout()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## What the charts tell us\n",
    "The seed deliberately balances roles and locations. Salary bands are generated with a fixed spread, so the scatter plot is linear by construction. Dates are simulated, not scraped. These plots demonstrate chart selection and labeling, not real market findings."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 7,
   "metadata": {
    "execution": {
     "iopub.execute_input": "2026-09-28T12:23:32.653079Z",
     "iopub.status.busy": "2026-09-28T12:23:32.650647Z",
     "iopub.status.idle": "2026-09-28T12:23:32.703458Z",
     "shell.execute_reply": "2026-09-28T12:23:32.698692Z"
    }
   },
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "Five chart types generated from the shared seed dataset.\n"
     ]
    }
   ],
   "source": [
    "assert len(jobs) == 200\n",
    "print('Five chart types generated from the shared seed dataset.')"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.10.8"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}

````

## notebooks/requirements.txt

````text
pandas>=2.2,<3
matplotlib>=3.9,<4
jupyterlab>=4.3,<5
nbclient>=0.10,<1
ipykernel>=6.29,<7

````

## README.md

````markdown
# SkillMatch AI

**Your skills. Your potential. Your next chapter.**

A full-stack resume analyzer and job-matching application with candidate, recruiter, and administrator workspaces. Built with FastAPI, SQLAlchemy, PostgreSQL, and a TypeScript/jQuery frontend. The interface combines an ink-dark dashboard, violet/cyan accents, self-hosted typography, a lightweight Three.js constellation, GSAP transitions, and Chart.js insights.

The default browser view is a **clearly labeled sample workspace**. It works without an API connection and uses illustrative scores and synthetic openings. Register or sign in to switch to the real database-backed application. Sample uploads and applications never pretend to succeed.

## Project structure

For a single document containing the folder tree followed by every text file’s complete contents, open [the complete source export](docs/SOURCE_CODE.md). Source files are also delivered individually in their folders.

```text
.
├── .github/workflows/ci.yml
├── backend/
│   ├── app/
│   │   ├── routers/            # Authentication, jobs, candidates, analytics/admin
│   │   ├── repositories/       # Catalog persistence and serialization
│   │   ├── services/           # Document parsing, spaCy extraction, matching
│   │   ├── config.py          # Environment validation
│   │   ├── db.py              # Neon/SQLite engine and session dependencies
│   │   ├── models.py          # SQLAlchemy tables, constraints, indexes
│   │   ├── schemas.py         # Pydantic v2 input validation
│   │   ├── security.py        # Argon2, JWTs, rotation, RBAC
│   │   ├── seed_data.py       # Deterministic synthetic catalog
│   │   ├── seed.py            # Idempotent seeding
│   │   ├── create_admin.py    # Trusted administrator bootstrap
│   │   └── main.py
│   ├── migrations/versions/  # Versioned schema
│   ├── tests/                # SQLite-backed API and domain tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── lib/               # API, types, fixtures, charts, 3D, utilities
│   │   ├── styles/main.css    # Design tokens and responsive components
│   │   └── main.ts            # Pages, routing, jQuery events/forms/AJAX
│   ├── e2e/                  # Browser workflows and accessibility checks
│   ├── public/favicon.svg
│   ├── nginx.conf
│   ├── Dockerfile
│   └── package.json
├── data/{jobs,skills}.csv
├── notebooks/                # Pandas and Matplotlib coursework
├── scripts/                  # Dataset export, notebook execution, SQLite CRUD
├── sql/                      # PostgreSQL schema and example queries
├── docs/                     # Run guide, design decisions, verification
├── .env.example
├── docker-compose.yml
└── GITHUB_COPILOT_LOG.md
```

## Architecture

```mermaid
flowchart LR
    Browser[HTML + Bootstrap + TypeScript/jQuery] --> Nginx[Nginx: static frontend / API proxy]
    Nginx --> API[FastAPI routers /api/v1]
    API --> Auth[Argon2 + JWT + role checks]
    API --> Services[Parsing and matching services]
    API --> Repo[Catalog repository / SQLAlchemy sessions]
    Services --> Parser[pdfplumber / python-docx]
    Services --> NLP[spaCy PhraseMatcher]
    Services --> Embeddings[Sentence Transformers / cosine similarity]
    Services --> Repo
    Repo --> Neon[(Neon PostgreSQL / TLS)]
    Browser --> Visuals[Lazy Three.js / GSAP / Chart.js]
```

## Start with Neon and Docker

Prerequisites: Docker Engine with Compose v2, a Neon account, and network access for the first image/model downloads. No production PostgreSQL container is created.

1. Create a project in [Neon](https://console.neon.tech). In the project dashboard, select **Connect**, choose the database and role, and copy the **pooled** PostgreSQL connection string. The hostname contains `-pooler`.
2. Copy `.env.example` to `.env` in the project root.
3. Set `DATABASE_URL` to the Neon connection string. `postgresql://` is normalized to `postgresql+psycopg://`; Neon connections always enforce `sslmode=require`. Passwords in URLs must be percent-encoded.
4. Generate a signing secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and put it in `JWT_SECRET`. Never commit `.env`.
5. For local HTTP access with a Neon database, keep `ENVIRONMENT=development` and `COOKIE_SECURE=false`. For an internet deployment, set `ENVIRONMENT=production`, `COOKIE_SECURE=true`, configure the public HTTPS origin in `CORS_ORIGINS`, and terminate TLS in front of Nginx.
6. Run:

   ```sh
   docker compose up --build
   ```

7. Open **http://localhost:8080**. The API checks database availability, applies Alembic migrations, seeds the catalog when enabled, and starts serving traffic. Create a candidate or recruiter account from the sign-up page.

Neon manages connection pooling. The API uses SQLAlchemy `NullPool` to avoid a second application pool retaining idle serverless connections. A single API worker is intentional: model memory and the in-process rate limiter remain predictable. See [Neon connection guidance](https://neon.com/docs/connect/connection-pooling) and [SQLAlchemy PostgreSQL documentation](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html).

### Fully local Docker option

Use the local database URL already shown in `.env.example`, then run:

```sh
docker compose --profile dev up --build
```

The `dev-db` service exists only in this profile, exposes no host port, and stores data in a named volume. The API waits for database readiness. `sslmode=disable` is only for this isolated development database.

### Local development without Docker

The deployment target is **Python 3.12** and Node.js 22. Use two terminals from the repository root:

```sh
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -r backend/requirements.txt
cd backend
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Without `.env`, development defaults to a local SQLite database. If `.env` contains a Docker/Neon URL, it takes precedence; use the intended database or set `DATABASE_URL=sqlite:///./skillmatch.db` in your shell. SQLite is a development/test convenience; production rejects it.

```sh
cd frontend
npm ci
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` to port 8000. Direct API documentation is at **http://localhost:8000/docs**, with the schema at `/openapi.json`.

The frontend’s `predev` and `prebuild` steps copy Swagger UI assets from npm. Documentation is also available through `http://localhost:5173/docs` and the deployed Nginx `/docs` route, with no CDN dependency. For direct backend documentation, start the backend after those assets have been copied.

### Create an administrator

Administrators cannot self-register through the public API. Run the trusted terminal command, which prompts for credentials without logging passwords:

```sh
docker compose exec api python -m app.create_admin
# Or, from backend/ with the virtual environment active:
python -m app.create_admin
```

## Environment variables

| Variable | Development default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./skillmatch.db` | Neon PostgreSQL URL; Docker sample uses the optional local database |
| `JWT_SECRET` | Development-only key | Use a randomly generated secret in deployment |
| `ENVIRONMENT` | `development` | `production` enforces strong secret, PostgreSQL, secure cookies |
| `CORS_ORIGINS` | Localhost and `127.0.0.1` on ports 5173/8080 | Exact comma-separated browser origins; no wildcard |
| `COOKIE_SECURE` | `false` | Set `true` when served over HTTPS |
| `SEMANTIC_ENABLED` | `true` | Use sentence-transformer embeddings when available |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model identifier |
| `SEED_ON_START` | `false` in code; `true` in Compose example | Insert the synthetic catalog if the database has no jobs |
| `API_PROXY_TARGET` | `http://127.0.0.1:8000` | Optional frontend development proxy override if port 8000 is occupied |

## Features and routes

| Page | Hash route | Behavior |
| --- | --- | --- |
| Candidate overview | `#/dashboard` | Resume, match, application, and learning summaries |
| Landing | `#/landing` | Interactive constellation and scroll-driven explanation |
| Authentication | `#/login`, `#/register` | Candidate/recruiter registration and login |
| Resume | `#/upload` | Drag/drop PDF/DOCX upload, extraction, deletion |
| Opportunities | `#/jobs`, `#/jobs/:id` | Search, location/type filters, pagination, device-local bookmarks |
| Matches | `#/matches`, `#/matches/:jobId` | Fit score, matched/missing skills, radar chart, learning links |
| Applications | `#/applications` | Candidate tracking or recruiter applicant ranking/status updates |
| Insights | `#/analytics` | Skill gaps, score histogram, skill demand, application timeline |
| Recruiter | `#/recruiter`, `#/post-job`, `#/post-job/:id` | Manage owned postings; edit or archive |
| Administrator | `#/admin` | Platform counts, paginated account controls, job moderation |
| Not found | Any unknown route | Accessible recovery page |

### API summary

All product endpoints are under `/api/v1`. Requests use JSON except multipart resume uploads. Errors return `detail`. Access tokens are sent as `Authorization: Bearer <token>`.

| Method | Path | Access |
| --- | --- | --- |
| POST | `/auth/register`, `/auth/login` | Public, rate limited |
| POST | `/auth/refresh` | Rotating HttpOnly refresh cookie; origin checked |
| POST | `/auth/logout` | Authenticated; revokes all user sessions |
| GET | `/auth/me` | Authenticated |
| GET | `/jobs`, `/jobs/{id}` | Public |
| GET | `/jobs/mine` | Recruiter/admin |
| POST | `/jobs` | Recruiter/admin |
| PUT, DELETE | `/jobs/{id}` | Owner or admin; DELETE archives |
| GET, POST | `/resumes` | Candidate; POST parses uploaded file |
| DELETE | `/resumes/{id}` | Resume owner; cascades related analyses/applications |
| GET, POST | `/matches` | Candidate; POST analyzes owned resume against a job |
| GET, POST | `/applications` | Role-scoped listing; candidate application creation |
| PATCH | `/applications/{id}` | Posting owner or admin |
| GET | `/analytics` | Candidate/recruiter scope, platform-wide for admin |
| GET | `/admin` | Admin; 50 users and jobs per page |
| PATCH | `/admin/users/{id}` | Admin; enable/disable account and revoke tokens |
| GET | `/health` | Database readiness |

## Matching and privacy

1. Validate extension, file signature, and size (5 MB); limit PDFs to 20 pages and expanded DOCX contents to 25 MB.
2. Extract text with `pdfplumber` or `python-docx`, including DOCX table cells. Scanned or encrypted documents return an actionable error; OCR is not included.
3. Use a spaCy English tokenizer and case-insensitive `PhraseMatcher` against the 300-skill catalog, with common aliases. A statistical spaCy language-model download is unnecessary. This is deterministic dictionary-backed NLP, not a claim to infer every possible skill.
4. Encode resume/job text using Sentence Transformers. Normalize vectors and compute cosine similarity. The combined percentage is **65% semantic similarity + 35% required-skill overlap**.
5. If the model is disabled or unavailable, return **keyword-only** scoring with an explicit `method` field and corresponding explanation in the UI. First semantic analysis downloads model weights into the persistent model cache; startup does not depend on that download.
6. Store parsed text and skills in the database. Original files are processed in memory and not written to disk. Recruiter screens expose applicant names and match scores, not raw resume text or email addresses. Resume deletion removes the stored text, skills associations, analyses, and applications linked to that resume.

These are alignment indicators, not calibrated probabilities or hiring decisions. Missing exact skill phrases do not prove a person lacks a skill. Recruiters should review candidates holistically. Current matching uses the model’s context window and a bounded input length; long resumes may need future chunking.

Security includes Argon2 password hashing, short-lived access tokens held in browser memory, HttpOnly/SameSite refresh cookies, atomic one-time refresh rotation, account-level token revocation, owner checks, parameterized SQL, request limits, CORS, HTML escaping, and Nginx security headers. The [FastAPI security guide](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) provides background on the JWT and password-hashing primitives.

## Tests and checks

```sh
cd backend
ruff check . ../scripts
pytest -q
alembic upgrade head
cd ../frontend
npm test
npm run build
npx playwright test
```

Browser tests use installed Google Chrome locally. For a CI machine, run `npx playwright install --with-deps chromium` and set `CI=true`. Tests exercise job filtering, saved jobs, match results, charts, mobile navigation, form validation, unknown routes, and axe accessibility rules. API tests cover refresh replay, logout revocation, roles, ownership, parsing, invalid uploads, matching, duplicate applications, analytics, and archival.

The GitHub Actions workflow runs Ruff, pytest, Vitest, TypeScript/Vite builds, and both Docker builds. See [verification notes](docs/VERIFICATION.md) for the checks actually run in the delivery environment; do not confuse configured CI checks with completed deployment verification.

## Course deliverables

- [Pandas notebook](notebooks/01_pandas_analysis.ipynb): loads, inspects, cleans missing values/duplicates, filters, sorts, groups, and summarizes the shared dataset.
- [Matplotlib notebook](notebooks/02_matplotlib_visualizations.ipynb): bar, scatter, histogram, line, and pie charts, with honest interpretation of synthetic data.
- [SQLite CRUD](scripts/sqlite_crud.py): standalone parameterized create/read/update/delete demonstration; run `python scripts/sqlite_crud.py`.
- [PostgreSQL schema](sql/01_schema.sql) and [example SQL](sql/02_examples.sql).
- [Copilot log template](GITHUB_COPILOT_LOG.md): documents genuine Copilot usage without fabricating it.
- [Viva design decisions](docs/DESIGN_DECISIONS.md) and [step-by-step run guide](docs/RUN_GUIDE.md).

Regenerate CSVs and notebook source with `python scripts/generate_course_data.py`. To run the notebooks, install `notebooks/requirements.txt`, then use JupyterLab or `python scripts/execute_notebooks.py` from the repository root. The seed catalog contains exactly 200 synthetic postings and 300 unique skills across ten categories. No shared demo password is created.

## Screenshots

Browser tests write captures into `docs/screenshots/`: `dashboard-desktop.png`, `dashboard-mobile.png`, `match-result.png`, and `landing-desktop.png`. These are actual rendered UI captures when the browser suite completes, not design mockups.

![Candidate dashboard](docs/screenshots/dashboard-desktop.png)

![Match analysis](docs/screenshots/match-result.png)

The live browser test uses a separate database. Run `python scripts/prepare_e2e.py`, start the API with `DATABASE_URL=sqlite:///../artifacts/e2e.db` and `SEMANTIC_ENABLED=false`, then run `npm run test:e2e` with `LIVE_API=true`. If using port 8010, also set `API_PROXY_TARGET=http://127.0.0.1:8010`. Shell environment syntax differs between PowerShell and Bash.

## Design and performance

Manrope headings and DM Sans body text are bundled from npm, so fonts and application assets do not depend on Google Fonts or other CDNs. Bootstrap provides the reset/grid; CSS custom properties define the palette, spacing, radii, and component states. jQuery handles page insertion, form validation, events, and AJAX. No React, Vue, or Angular is used.

Three.js and Chart.js load only when their pages need them. The constellation caps pixel ratio at 1.5, renders at approximately 30 FPS, pauses offscreen/when hidden, and disposes resources on navigation. Reduced-motion and low-core devices keep the CSS fallback. Keyboard focus, semantic structure, ARIA labels, responsive navigation, and reduced-motion behavior are implemented. Lighthouse >85 is a performance target to measure against the production build, not an assumed result.

## Deployment considerations and future improvements

- Terminate HTTPS at the hosting platform/reverse proxy; enable secure cookies and configure the exact public origin.
- Seed and model downloads require outbound network during initial setup. Consider baking model weights into a versioned image for offline deployments.
- Use a shared rate-limit store and background inference workers before scaling beyond one API process. Current limits are intentionally in-process; Nginx also limits requests.
- Add email verification, account recovery, user-managed consent/retention controls, audit logs, and malware scanning before opening registration to an unrestricted audience.
- Add OCR, multilingual extraction, chunked embeddings, a versioned skill taxonomy, and calibrated evaluation datasets.
- Add PostgreSQL integration tests and load tests in staging. SQLite tests do not establish every PostgreSQL concurrency behavior.
- Add persistent cross-device bookmarks, notifications, and learning progress. Current bookmarks are device-local and scoped to the browser.
- External learning links are search-based resource suggestions, not generated course endorsements. Seed company names and salary figures are illustrative.

Neon is the managed PostgreSQL provider required by the brief; the application libraries are open-source, with no paid AI API requirement.

````

## scripts/execute_notebooks.py

````python
"""Execute notebooks using this interpreter and save rendered cell outputs."""

from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
    notebook = nbformat.read(path, as_version=4)
    NotebookClient(
        notebook,
        timeout=180,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    ).execute()
    nbformat.write(notebook, path)
    print(f"Executed {path.name}")

````

## scripts/export_schema.py

````python
"""Export the versioned Alembic schema as PostgreSQL SQL without connecting to a server."""

import io
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]
os.environ["DATABASE_URL"] = "postgresql+psycopg://schema_export@localhost/skillmatch"
os.environ["ENVIRONMENT"] = "development"
os.chdir(ROOT / "backend")
output = io.StringIO()
config = Config("alembic.ini", output_buffer=output)
command.upgrade(config, "head", sql=True)
(ROOT / "sql" / "01_schema.sql").write_text(
    "-- Generated from the versioned Alembic migration. PostgreSQL dialect.\n"
    + output.getvalue(),
    encoding="utf-8",
)
print("Exported PostgreSQL schema from Alembic.")

````

## scripts/export_source.py

````python
"""Export the full deliverable tree and text sources into one reviewable Markdown file."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "test-results",
    "playwright-report",
    "artifacts",
    "docs-assets",
}
TARGET = ROOT / "docs" / "SOURCE_CODE.md"
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".db", ".pyc", ".woff", ".woff2"}
files = sorted(
    p
    for p in ROOT.rglob("*")
    if p.is_file()
    and not (set(p.relative_to(ROOT).parts) & EXCLUDED)
    and p.name != ".env"
    and p != TARGET
)
lines = [
    "# SkillMatch AI — complete source\n",
    "Generated from the delivered workspace. Files are grouped by folder. Binary screenshots are listed in the tree and delivered separately.\n",
    "## Full folder tree\n",
    "```text\n",
]
for path in files:
    lines.append(path.relative_to(ROOT).as_posix() + "\n")
lines.append("```\n")
for path in files:
    if path.suffix in BINARY_SUFFIXES:
        continue
    language = {
        ".py": "python",
        ".ts": "typescript",
        ".css": "css",
        ".json": "json",
        ".ipynb": "json",
        ".yml": "yaml",
        ".sql": "sql",
        ".html": "html",
        ".md": "markdown",
        ".svg": "xml",
    }.get(path.suffix, "text")
    lines.append(f"\n## {path.relative_to(ROOT).as_posix()}\n\n````{language}\n")
    lines.append(path.read_text(encoding="utf-8-sig") + "\n````\n")
TARGET.write_text("".join(lines), encoding="utf-8")
print(f"Exported {len(files)} files to {TARGET.relative_to(ROOT)}")

````

## scripts/generate_course_data.py

````python
"""Export reproducible seed CSVs and create the two executable course notebooks."""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.seed_data import SKILLS, generate_jobs


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def notebook(title: str, sections: list[tuple[str, str]], filename: str) -> None:
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"# {title}\n",
                "This notebook uses the deterministic, synthetic SkillMatch seed dataset. Company names are illustrative; these are not real vacancies. Run all cells from top to bottom.\n",
            ],
        }
    ]
    for description, code in sections:
        cells.append({"cell_type": "markdown", "metadata": {}, "source": [description]})
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": code.splitlines(keepends=True),
            }
        )
    result = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    (ROOT / "notebooks" / filename).write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )


def main() -> None:
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "notebooks").mkdir(exist_ok=True)
    jobs = [
        {
            "id": i + 1,
            **j,
            "skills": "|".join(j["skills"]),
            "posted_date": f"2026-09-{i % 28 + 1:02d}",
        }
        for i, j in enumerate(generate_jobs())
    ]
    write_csv(ROOT / "data" / "jobs.csv", jobs)
    write_csv(ROOT / "data" / "skills.csv", SKILLS)
    load = "from pathlib import Path\nimport pandas as pd\nroot = Path.cwd() if (Path.cwd() / 'data').exists() else Path.cwd().parent\njobs = pd.read_csv(root / 'data' / 'jobs.csv')\nskills = pd.read_csv(root / 'data' / 'skills.csv')\njobs.head()"
    notebook(
        "Job market exploration with Pandas",
        [
            (
                "## 1. Load and inspect\nRead 200 jobs and 300 skills and inspect column types.",
                load,
            ),
            (
                "## 2. Inspect quality\nCount missing values and duplicate records before cleaning.",
                "print(jobs.shape, skills.shape)\nprint(jobs.dtypes)\nprint(jobs.isna().sum())\nprint('Duplicate IDs:', jobs.duplicated(subset=['id']).sum())",
            ),
            (
                "## 3. Clean missing values and duplicates\nInject a controlled missing location and duplicate row to demonstrate cleaning. Keep the original seed data intact.",
                "dirty = pd.concat([jobs, jobs.iloc[[0]]], ignore_index=True)\ndirty.loc[1, 'location'] = None\nclean = dirty.drop_duplicates(subset=['id']).copy()\nclean['location'] = clean['location'].fillna('Not specified')\nfor column in ['salary_min', 'salary_max']:\n    clean[column] = pd.to_numeric(clean[column], errors='coerce')\n    clean[column] = clean[column].fillna(clean[column].median())\nclean['posted_date'] = pd.to_datetime(clean['posted_date'])\nassert len(clean) == 200\nassert clean['location'].isna().sum() == 0\nclean.head()",
            ),
            (
                "## 4. Filter and sort\nFind remote roles with minimum salaries of at least $120,000, ordered by salary.",
                "remote = clean.loc[(clean['location'] == 'Remote') & (clean['salary_min'] >= 120000)]\nremote.sort_values(['salary_max', 'title'], ascending=[False, True])[['title', 'company', 'salary_min', 'salary_max']].head(15)",
            ),
            (
                "## 5. Summarize\nGroup opportunities by role and expand skill lists to count demand.",
                "summary = clean.groupby('title').agg(openings=('id', 'count'), average_min_salary=('salary_min', 'mean'), average_max_salary=('salary_max', 'mean')).round(0)\ndisplay(summary.sort_values('average_max_salary', ascending=False))\ndemand = clean.assign(skill=clean['skills'].str.split('|')).explode('skill')['skill'].value_counts()\ndisplay(demand.head(15))\ndisplay(skills.groupby('category').size().rename('skill_count'))",
            ),
            (
                "## Interpretation\nThese counts describe a balanced synthetic teaching dataset. Do not interpret them as evidence of actual hiring demand or salary levels.",
                "print(f'{len(clean)} unique jobs, {len(skills)} catalog skills, {clean.company.nunique()} example companies')",
            ),
        ],
        "01_pandas_analysis.ipynb",
    )
    notebook(
        "Visualizing opportunities with Matplotlib",
        [
            (
                "## 1. Load the same dataset",
                load
                + "\nimport matplotlib.pyplot as plt\nplt.style.use('seaborn-v0_8-darkgrid')\nplt.rcParams.update({'figure.figsize': (10, 5), 'figure.dpi': 110})\npurple = '#8764c5'\ncyan = '#399a93'",
            ),
            (
                "## 2. Bar chart — most requested skills",
                "demand = jobs.assign(skill=jobs.skills.str.split('|')).explode('skill').skill.value_counts().head(10)\nfig, ax = plt.subplots()\ndemand.sort_values().plot.barh(ax=ax, color=purple)\nax.set(title='Most requested skills in the synthetic catalog', xlabel='Number of postings', ylabel='Skill')\nfig.tight_layout()\nplt.show()",
            ),
            (
                "## 3. Scatter plot — salary bands",
                "fig, ax = plt.subplots()\nax.scatter(jobs.salary_min / 1000, jobs.salary_max / 1000, color=cyan, alpha=0.4, s=65)\nax.set(title='Advertised salary bands', xlabel='Minimum annual salary (USD thousands)', ylabel='Maximum annual salary (USD thousands)')\nfig.tight_layout()\nplt.show()",
            ),
            (
                "## 4. Histogram — salary distribution",
                "fig, ax = plt.subplots()\nax.hist((jobs.salary_min + jobs.salary_max) / 2000, bins=10, color=purple, edgecolor='white')\nax.set(title='Distribution of salary midpoints', xlabel='Annual midpoint salary (USD thousands)', ylabel='Number of postings')\nfig.tight_layout()\nplt.show()",
            ),
            (
                "## 5. Line chart — postings over time",
                "timeline = jobs.groupby(pd.to_datetime(jobs.posted_date)).size().sort_index()\nfig, ax = plt.subplots()\nax.plot(timeline.index, timeline.values, color=cyan, marker='o')\nax.set(title='Synthetic postings over September 2026', xlabel='Posting date', ylabel='Number of postings')\nfig.autofmt_xdate()\nfig.tight_layout()\nplt.show()",
            ),
            (
                "## 6. Pie chart — employment types",
                "counts = jobs.employment_type.value_counts()\nfig, ax = plt.subplots(figsize=(7, 6))\nax.pie(counts.values, labels=counts.index, autopct='%1.1f%%', colors=[purple, cyan], startangle=90, wedgeprops={'edgecolor': 'white'})\nax.set_title('Employment types in the synthetic catalog')\nfig.tight_layout()\nplt.show()",
            ),
            (
                "## What the charts tell us\nThe seed deliberately balances roles and locations. Salary bands are generated with a fixed spread, so the scatter plot is linear by construction. Dates are simulated, not scraped. These plots demonstrate chart selection and labeling, not real market findings.",
                "assert len(jobs) == 200\nprint('Five chart types generated from the shared seed dataset.')",
            ),
        ],
        "02_matplotlib_visualizations.ipynb",
    )
    print("Generated 200 jobs, 300 skills, and two notebooks.")


if __name__ == "__main__":
    main()

````

## scripts/prepare_e2e.py

````python
"""Prepare isolated browser-test fixtures without touching the development database."""

import os
import sys
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
(ROOT / "artifacts").mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = "sqlite:///" + (ROOT / "artifacts" / "e2e.db").as_posix()
os.environ["SEMANTIC_ENABLED"] = "false"
sys.path.insert(0, str(ROOT / "backend"))

from app.db import Base, engine
from app.seed import seed

Base.metadata.create_all(engine)
seed()
document = Document()
document.add_heading("QA Candidate", 0)
document.add_paragraph(
    "Frontend developer building accessible React and TypeScript applications. Experienced with CSS and thoughtful product interfaces. Enjoys collaborating with cross-functional teams."
)
document.save(ROOT / "artifacts" / "qa-resume.docx")
print("Prepared isolated database and synthetic resume in artifacts/.")

````

## scripts/sqlite_crud.py

````python
"""Run a complete, parameterized SQLite CRUD demonstration with no dependencies."""

import sqlite3


def main() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.execute(
            "CREATE TABLE jobs (id INTEGER PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL, salary INTEGER NOT NULL CHECK(salary >= 0))"
        )
        cursor = connection.execute(
            "INSERT INTO jobs(title, company, salary) VALUES (?, ?, ?)",
            ("Python Engineer", "SkillMatch Studio", 120000),
        )
        job_id = cursor.lastrowid
        print("CREATE:", job_id)
        print(
            "READ:",
            connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone(),
        )
        connection.execute("UPDATE jobs SET salary = ? WHERE id = ?", (135000, job_id))
        print(
            "UPDATE:",
            connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone(),
        )
        connection.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        remaining = connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        assert remaining == 0
        print("DELETE: rows remaining =", remaining)


if __name__ == "__main__":
    main()

````

## sql/01_schema.sql

````sql
-- Generated from the versioned Alembic migration. PostgreSQL dialect.
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> ea131b083c8f

CREATE TABLE skills (
    id SERIAL NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    category VARCHAR(60) NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_skills_name ON skills (name);

CREATE TABLE users (
    id SERIAL NOT NULL, 
    email VARCHAR(254) NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    role VARCHAR(20) NOT NULL, 
    active BOOLEAN NOT NULL, 
    token_version INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CHECK (role IN ('candidate','recruiter','admin'))
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE jobs (
    id SERIAL NOT NULL, 
    recruiter_id INTEGER NOT NULL, 
    title VARCHAR(150) NOT NULL, 
    company VARCHAR(100) NOT NULL, 
    location VARCHAR(100) NOT NULL, 
    employment_type VARCHAR(30) NOT NULL, 
    description TEXT NOT NULL, 
    salary_min INTEGER NOT NULL, 
    salary_max INTEGER NOT NULL, 
    active BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CHECK (salary_min >= 0 AND salary_max >= salary_min), 
    FOREIGN KEY(recruiter_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_jobs_active ON jobs (active);

CREATE INDEX ix_jobs_location_type ON jobs (location, employment_type);

CREATE INDEX ix_jobs_recruiter_id ON jobs (recruiter_id);

CREATE INDEX ix_jobs_title ON jobs (title);

CREATE TABLE refresh_sessions (
    id VARCHAR(64) NOT NULL, 
    user_id INTEGER NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_refresh_sessions_user_id ON refresh_sessions (user_id);

CREATE TABLE resumes (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    filename VARCHAR(255) NOT NULL, 
    text TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_resumes_user_id ON resumes (user_id);

CREATE TABLE applications (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    job_id INTEGER NOT NULL, 
    resume_id INTEGER NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CHECK (status IN ('Applied','Reviewing','Interview','Rejected','Hired')), 
    FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE, 
    FOREIGN KEY(resume_id) REFERENCES resumes (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_application_user_job UNIQUE (user_id, job_id)
);

CREATE INDEX ix_applications_job_id ON applications (job_id);

CREATE INDEX ix_applications_user_id ON applications (user_id);

CREATE TABLE job_skills (
    job_id INTEGER NOT NULL, 
    skill_id INTEGER NOT NULL, 
    PRIMARY KEY (job_id, skill_id), 
    FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE, 
    FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE
);

CREATE TABLE match_results (
    id SERIAL NOT NULL, 
    resume_id INTEGER NOT NULL, 
    job_id INTEGER NOT NULL, 
    score FLOAT NOT NULL, 
    semantic_score FLOAT NOT NULL, 
    keyword_score FLOAT NOT NULL, 
    matched JSON NOT NULL, 
    missing JSON NOT NULL, 
    method VARCHAR(30) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CHECK (score >= 0 AND score <= 100), 
    FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE, 
    FOREIGN KEY(resume_id) REFERENCES resumes (id) ON DELETE CASCADE, 
    CONSTRAINT uq_match_resume_job UNIQUE (resume_id, job_id)
);

CREATE INDEX ix_match_results_job_id ON match_results (job_id);

CREATE INDEX ix_match_results_resume_id ON match_results (resume_id);

CREATE TABLE resume_skills (
    resume_id INTEGER NOT NULL, 
    skill_id INTEGER NOT NULL, 
    PRIMARY KEY (resume_id, skill_id), 
    FOREIGN KEY(resume_id) REFERENCES resumes (id) ON DELETE CASCADE, 
    FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE
);

INSERT INTO alembic_version (version_num) VALUES ('ea131b083c8f') RETURNING alembic_version.version_num;

COMMIT;


````

## sql/02_examples.sql

````sql
-- Run after migrations and `python -m app.seed`.
-- Teaching examples use synthetic catalog data, with no shared login credentials.
BEGIN;
INSERT INTO skills (name, category) VALUES ('OpenTelemetry', 'Cloud & DevOps')
ON CONFLICT (name) DO NOTHING;

-- Filter and order jobs, with pagination.
SELECT id, title, company, location, salary_min, salary_max
FROM jobs
WHERE active = true AND location = 'Remote' AND salary_min >= 120000
ORDER BY salary_max DESC, id
LIMIT 10 OFFSET 0;

-- Most frequently requested skills.
SELECT s.name, COUNT(js.job_id) AS job_count
FROM skills s
JOIN job_skills js ON js.skill_id = s.id
JOIN jobs j ON j.id = js.job_id
WHERE j.active = true
GROUP BY s.id, s.name
ORDER BY job_count DESC, s.name
LIMIT 10;

-- Match results with candidate names. In the application this query is owner-scoped.
SELECT j.title, u.name, mr.score, mr.keyword_score, mr.semantic_score, mr.method
FROM match_results mr
JOIN jobs j ON j.id = mr.job_id
JOIN resumes r ON r.id = mr.resume_id
JOIN users u ON u.id = r.user_id
ORDER BY mr.score DESC;

-- Applications by calendar date.
SELECT CAST(created_at AS DATE) AS applied_on, COUNT(*) AS applications
FROM applications
GROUP BY CAST(created_at AS DATE)
ORDER BY applied_on;

-- Average advertised salary by employment type.
SELECT employment_type, COUNT(*) AS openings,
       ROUND(AVG((salary_min + salary_max) / 2.0), 2) AS average_midpoint
FROM jobs WHERE active = true
GROUP BY employment_type;

-- Demonstrate update and delete without modifying the persisted catalog.
UPDATE skills SET category = 'Observability' WHERE name = 'OpenTelemetry';
DELETE FROM skills WHERE name = 'OpenTelemetry';
ROLLBACK;

````
