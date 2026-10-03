# Stage 06 — complete changed/new source

```text
.env.example
backend/Dockerfile
backend/app/ingestion/normalization.py
backend/app/models.py
backend/app/services/product.py
backend/migrations/versions/c6f4a1b209d3_workspace_query_indexes.py
backend/sources.yaml
docker-compose.yml
docs/stages/06_ENGINEERING.md
frontend/Dockerfile
frontend/nginx.conf
```

## .env.example

````
# Copy to .env and replace every PLACEHOLDER before deployment.
DATABASE_URL=postgresql+psycopg://PLACEHOLDER_USER:PLACEHOLDER_PASSWORD@PLACEHOLDER_NEON_HOST/PLACEHOLDER_DATABASE?sslmode=require
JWT_SECRET=PLACEHOLDER_GENERATE_AT_LEAST_32_RANDOM_CHARACTERS
ENVIRONMENT=development
COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:8080,http://localhost:5173,http://127.0.0.1:5173
SEMANTIC_ENABLED=true
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384
SEED_ON_START=false
DEMO_MODE=false
INGESTION_CONFIG=sources.yaml
INGESTION_USER_AGENT=SkillMatchAI/2.0 (contact: PLACEHOLDER_CONTACT_EMAIL)
INGESTION_TIMEOUT=20
INGESTION_MAX_PAGES=20
INGESTION_REQUEST_DELAY=1
WORKER_POLL_SECONDS=15
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
MATCH_SEMANTIC_WEIGHT=0.50
MATCH_SKILLS_WEIGHT=0.30
MATCH_EXPERIENCE_WEIGHT=0.15
MATCH_LOCATION_WEIGHT=0.05
INSIGHT_CACHE_SECONDS=60
SMTP_HOST=
SMTP_PORT=1025
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_STARTTLS=false
SMTP_FROM=PLACEHOLDER_SENDER@example.invalid
OLLAMA_ENABLED=false
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2
DEV_DB_PASSWORD=PLACEHOLDER_LOCAL_PASSWORD

````

## backend/Dockerfile

````
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch && pip install -r requirements.txt
RUN useradd --create-home --uid 10001 app
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["sh", "-c", "python -m app.wait_db && alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]

````

## backend/app/ingestion/normalization.py

````
import hashlib
import html
import re
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.blocked = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "iframe", "object"}:
            self.blocked += 1
        if tag in {"p", "br", "li", "div", "h1", "h2", "h3"} and not self.blocked:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "iframe", "object"}:
            self.blocked = max(0, self.blocked - 1)
        if tag in {"p", "li", "div"} and not self.blocked:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.blocked:
            self.parts.append(data)


def plain_text(value: str) -> str:
    parser = TextParser()
    parser.feed(html.unescape(value or ""))
    return re.sub(r"\n\s*\n+", "\n\n", "".join(parser.parts)).strip()[:100000]


def safe_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in {"https", "http"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("A public HTTP(S) apply URL is required")
    return value


def timestamp(value) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000 if value > 10**11 else value, timezone.utc)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def normalized(value: str) -> str:
    return " ".join(sorted(re.findall(r"[\w+#]+", unicodedata.normalize("NFKC", value).casefold())))


def fingerprint(title: str, company: str, location: str) -> str:
    return hashlib.sha256("|".join(normalized(v) for v in (title, company, location)).encode()).hexdigest()


def salary_text(value: str) -> dict:
    """Only explicit two-ended ranges with an identifiable currency; never estimate."""
    match = re.search(
        r"(?P<c>USD|EUR|GBP|INR|US\$|€|£|₹)\s*(?P<lo>[\d,.]+)\s*(?P<lk>[kK]?)\s*[-–—]\s*(?:USD|EUR|GBP|INR|US\$|€|£|₹)?\s*(?P<hi>[\d,.]+)\s*(?P<hk>[kK]?)",
        value or "",
        re.I,
    )
    if not match:
        return {}
    currency = {"US$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}.get(match["c"].upper(), match["c"].upper())
    low = float(match["lo"].replace(",", "")) * (1000 if match["lk"] or match["hk"] else 1)
    high = float(match["hi"].replace(",", "")) * (1000 if match["hk"] else 1)
    if not 0 < low <= high <= 100000000:
        return {}
    period = next(
        (
            p
            for p, pattern in [
                ("hour", r"hour|hourly"),
                ("month", r"month|monthly"),
                ("year", r"year|annual|annum"),
            ]
            if re.search(pattern, value, re.I)
        ),
        None,
    )
    return dict(
        salary_min=round(low), salary_max=round(high), salary_currency=currency, salary_interval=period
    )


class RawJob(BaseModel):
    external_id: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=150)
    company: str = Field(min_length=1, max_length=100)
    location: str = Field(default="Not specified", max_length=100)
    remote: bool = False
    employment_type: str = "Not specified"
    description: str
    apply_url: str
    posted_at: datetime | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    salary_interval: str | None = None
    attribution: str
    attribution_url: str

    _urls = field_validator("apply_url", "attribution_url")(safe_url)
    _description = field_validator("description", mode="before")(plain_text)

    @field_validator("employment_type", mode="before")
    @classmethod
    def job_type(cls, value):
        key = str(value or "").lower().replace("_", "-").replace(" ", "-")
        return {
            "full-time": "Full-time",
            "fulltime": "Full-time",
            "part-time": "Part-time",
            "contract": "Contract",
            "contractor": "Contract",
            "internship": "Internship",
        }.get(key, str(value or "Not specified")[:30])

    @model_validator(mode="after")
    def validate_salary(self):
        if self.salary_min is not None and self.salary_max is not None and self.salary_max < self.salary_min:
            raise ValueError("Invalid salary range")
        if self.salary_currency:
            self.salary_currency = self.salary_currency.upper()
            if not re.fullmatch(r"[A-Z]{3}", self.salary_currency):
                raise ValueError("Expected a three-letter salary currency")
        return self

````

## backend/app/models.py

````
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
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
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
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
    __table_args__ = (Index("ix_resumes_user_latest", "user_id", "id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(JSON().with_variant(Vector(384), "postgresql"))
    embedding_model: Mapped[str | None] = mapped_column(String(150))
    experience_years: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    skills: Mapped[list[Skill]] = relationship(secondary=resume_skills, lazy="selectin")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("salary_min >= 0 AND salary_max >= salary_min"),
        Index("ix_jobs_location_type", "location", "employment_type"),
        Index("ix_jobs_active_cursor", "active", "is_demo", "id"),
        UniqueConstraint("source", "external_id", name="uq_jobs_source_external"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    recruiter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(150), index=True)
    company: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(100))
    employment_type: Mapped[str] = mapped_column(String(30), default="Full-time")
    description: Mapped[str] = mapped_column(Text)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    salary_interval: Mapped[str | None] = mapped_column(String(20))
    remote: Mapped[bool] = mapped_column(default=False)
    apply_url: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(30), default="native", index=True)
    external_id: Mapped[str | None] = mapped_column(String(300))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    is_demo: Mapped[bool] = mapped_column(default=False, index=True)
    fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    embedding: Mapped[list | None] = mapped_column(JSON().with_variant(Vector(384), "postgresql"))
    embedding_model: Mapped[str | None] = mapped_column(String(150))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    skill_importance: Mapped[dict] = mapped_column(JSON, default=dict)
    experience_min: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    active: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    skills: Mapped[list[Skill]] = relationship(secondary=job_skills, lazy="selectin")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),
        Index("ix_applications_user_updated", "user_id", "updated_at"),
        CheckConstraint(
            "status IN ('Saved','Applied','Reviewing','Interview','Offer','Rejected','Hired')",
            name="ck_applications_status",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(30), default="Applied")
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    job: Mapped[Job] = relationship(lazy="joined")
    user: Mapped[User] = relationship(lazy="joined")


class MatchResult(Base):
    __tablename__ = "match_results"
    __table_args__ = (
        UniqueConstraint("resume_id", "job_id", name="uq_match_resume_job"),
        Index("ix_matches_resume_score", "resume_id", "score"),
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
    components: Mapped[dict] = mapped_column(JSON, default=dict)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    improvements: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IngestionSource(Base):
    __tablename__ = "ingestion_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(150), unique=True)
    kind: Mapped[str] = mapped_column(String(30))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(default=False)
    interval_minutes: Mapped[int] = mapped_column(default=360)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="idle")
    last_error: Mapped[str | None] = mapped_column(Text)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)


class JobOrigin(Base):
    __tablename__ = "job_origins"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_origin_source_external"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("ingestion_sources.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(300))
    apply_url: Mapped[str] = mapped_column(Text)
    attribution: Mapped[str] = mapped_column(String(100))
    attribution_url: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(default=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("ingestion_sources.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="running")
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)


class FeedCache(Base):
    __tablename__ = "feed_cache"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict | list] = mapped_column(JSON)
    etag: Mapped[str | None] = mapped_column(Text)
    modified: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkItem(Base):
    __tablename__ = "work_items"
    __table_args__ = (Index("ix_work_items_pending_due", "status", "available_at", "id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApplicationEvent(Base):
    __tablename__ = "application_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SavedSearch(Base):
    __tablename__ = "saved_searches"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    alerts: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("user_id", "search_id", "job_id", name="uq_notification_search_job"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    search_id: Mapped[int] = mapped_column(ForeignKey("saved_searches.id", ondelete="CASCADE"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(250))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LearningResource(Base):
    __tablename__ = "learning_resources"
    __table_args__ = (UniqueConstraint("skill_id", "url", name="uq_resource_skill_url"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(100))


class InsightSnapshot(Base):
    __tablename__ = "insight_snapshots"
    day: Mapped[str] = mapped_column(String(10), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)


class InsightCache(Base):
    __tablename__ = "insight_cache"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

````

## backend/app/services/product.py

````
"""Database-backed product services shared by API and worker."""

import re
import smtplib
from collections import Counter, defaultdict
from datetime import timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    InsightCache,
    InsightSnapshot,
    Job,
    LearningResource,
    MatchResult,
    Notification,
    Resume,
    SavedSearch,
    Skill,
    User,
    utcnow,
)


def latest_resume(db: Session, user_id: int):
    return db.scalar(select(Resume).where(Resume.user_id == user_id).order_by(Resume.id.desc()).limit(1))


def visible_jobs():
    return select(Job).where(Job.active.is_(True), Job.is_demo.is_(False))


def create_alerts(db: Session, resume: Resume) -> None:
    user = db.get(User, resume.user_id)
    if not user or not user.preferences.get("job_alerts", True):
        return
    for search in db.scalars(
        select(SavedSearch).where(SavedSearch.user_id == user.id, SavedSearch.alerts.is_(True))
    ).all():
        filters = search.filters
        rows = db.execute(
            select(Job, MatchResult)
            .join(MatchResult, MatchResult.job_id == Job.id)
            .where(
                MatchResult.resume_id == resume.id,
                MatchResult.score >= filters.get("min_match", 0),
                Job.active.is_(True),
                Job.is_demo.is_(False),
                Job.created_at >= search.created_at,
            )
        ).all()
        for job, match in rows:
            if (
                filters.get("keywords", "").casefold()
                not in (job.title + " " + job.company + " " + job.description).casefold()
            ):
                continue
            if filters.get("location", "").casefold() not in job.location.casefold():
                continue
            if filters.get("kind") and filters["kind"] != job.employment_type:
                continue
            if db.scalar(
                select(Notification.id).where(
                    Notification.user_id == user.id,
                    Notification.search_id == search.id,
                    Notification.job_id == job.id,
                )
            ):
                continue
            db.add(
                Notification(
                    user_id=user.id,
                    search_id=search.id,
                    job_id=job.id,
                    title=f"{job.title} at {job.company}"[:250],
                )
            )
    db.flush()


def send_digests(db: Session) -> int:
    settings = get_settings()
    if not settings.smtp_host:
        return 0
    count = 0
    for user in db.scalars(select(User).where(User.active.is_(True))).all():
        if not user.preferences.get("email_digest") or not user.preferences.get("job_alerts", True):
            continue
        rows = db.scalars(
            select(Notification)
            .join(SavedSearch)
            .where(
                Notification.user_id == user.id,
                Notification.emailed_at.is_(None),
                SavedSearch.alerts.is_(True),
            )
            .order_by(Notification.id)
            .limit(100)
        ).all()
        if not rows:
            continue
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = (
            settings.smtp_from,
            user.email,
            "Your SkillMatch job alerts",
        )
        from app.repositories.catalog import job_public

        lines = []
        for item in rows:
            job = db.get(Job, item.job_id)
            if job and job.active:
                public = job_public(job)
                attribution = "\n".join(
                    f"Source: {source['name']} - {source['url']}" for source in public["sources"]
                )
                lines.append(
                    f"{item.title}\n{public['apply_url'] or 'Open your SkillMatch workspace to view this native job.'}\n{attribution}".strip()
                )
        if lines:
            message.set_content("\n\n".join(lines))
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        for item in rows:
            item.emailed_at = utcnow()
        db.commit()
        count += len(lines)
    return count


def ats_report(resume: Resume, job: Job | None = None) -> dict:
    text = resume.text
    words = len(text.split())
    sections = {
        name: bool(re.search(pattern, text, re.I | re.M))
        for name, pattern in {
            "experience": r"\b(experience|employment|work history)\b",
            "education": r"\b(education|degree|university)\b",
            "skills": r"\b(skills|technologies|competencies)\b",
            "contact": r"[\w.+-]+@[\w.-]+\.[a-z]{2,}",
        }.items()
    }
    checks = {
        "readable_length": 250 <= words <= 1500,
        "achievement_bullets": bool(re.search(r"^\s*[-•*]\s+", text, re.M)),
        "no_replacement_characters": "\ufffd" not in text,
    }
    have = {s.name for s in resume.skills}
    required = {s.name for s in job.skills} if job else set()
    coverage = round(100 * len(have & required) / len(required), 1) if required else None
    measured = [100 * sum(sections.values()) / 4, 100 * sum(checks.values()) / 3]
    if coverage is not None:
        measured.append(coverage)
    return {
        "score": round(sum(measured) / len(measured), 1),
        "sections": sections,
        "checks": checks,
        "word_count": words,
        "keyword_coverage": coverage,
        "missing_keywords": sorted(required - have),
        "method": "Text-based heuristic; not a prediction of any employer ATS. Original visual layout is not scored.",
    }


def learning_path(db: Session, resume: Resume | None) -> list:
    if not resume:
        return []
    results = db.scalars(
        select(MatchResult)
        .join(Job)
        .where(MatchResult.resume_id == resume.id, Job.active.is_(True), Job.is_demo.is_(False))
    ).all()
    gaps = Counter(skill for result in results for skill in result.missing)
    resources = defaultdict(list)
    for resource, name in db.execute(select(LearningResource, Skill.name).join(Skill)).all():
        resources[name].append({"title": resource.title, "url": resource.url, "provider": resource.provider})
    return [
        {"skill": name, "related_jobs": count, "resources": resources[name]}
        for name, count in gaps.most_common()
    ]


def seed_resources(db: Session) -> None:
    catalog = [
        ("Python", "Python tutorial", "https://docs.python.org/3/tutorial/", "Python"),
        ("PyTorch", "Learn PyTorch", "https://pytorch.org/tutorials/", "PyTorch"),
        ("TensorFlow", "TensorFlow tutorials", "https://www.tensorflow.org/tutorials", "TensorFlow"),
        (
            "Scikit-learn",
            "Scikit-learn user guide",
            "https://scikit-learn.org/stable/user_guide.html",
            "Scikit-learn",
        ),
        (
            "JavaScript",
            "JavaScript guide",
            "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
            "MDN",
        ),
        (
            "PostgreSQL",
            "PostgreSQL tutorial",
            "https://www.postgresql.org/docs/current/tutorial.html",
            "PostgreSQL",
        ),
        ("Docker", "Get started with Docker", "https://docs.docker.com/get-started/", "Docker"),
        ("FastAPI", "FastAPI tutorial", "https://fastapi.tiangolo.com/tutorial/", "FastAPI"),
        (
            "Large Language Models",
            "Hugging Face LLM course",
            "https://huggingface.co/learn/llm-course/chapter1/1",
            "Hugging Face",
        ),
    ]
    for name, title, url, provider in catalog:
        skill = db.scalar(select(Skill).where(func.lower(Skill.name) == name.lower()))
        if skill and not db.scalar(
            select(LearningResource.id).where(
                LearningResource.skill_id == skill.id, LearningResource.url == url
            )
        ):
            db.add(LearningResource(skill_id=skill.id, title=title, url=url, provider=provider))
    db.flush()


def market_insights(db: Session, force=False) -> dict:
    now = utcnow()
    cached = db.get(InsightCache, "market")
    if not force and cached and cached.expires_at.replace(tzinfo=timezone.utc) > now:
        return cached.data
    jobs = db.scalars(visible_jobs()).all()
    skills = Counter(s.name for j in jobs for s in j.skills)
    salary_groups = defaultdict(list)
    for j in jobs:
        if j.salary_min is not None and j.salary_max is not None and j.salary_currency and j.salary_interval:
            salary_groups[(j.title, j.location, j.salary_currency, j.salary_interval)].append(
                (j.salary_min + j.salary_max) / 2
            )
    data = {
        "active_jobs": len(jobs),
        "skills": dict(skills.most_common(30)),
        "companies": dict(Counter(j.company for j in jobs).most_common(20)),
        "locations": dict(Counter(j.location for j in jobs).most_common(20)),
        "types": dict(Counter(j.employment_type for j in jobs)),
        "salaries": [
            {
                "role": key[0],
                "location": key[1],
                "currency": key[2],
                "interval": key[3],
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "average": round(sum(values) / len(values), 2),
                "values": values[:500],
            }
            for key, values in salary_groups.items()
        ],
        "generated_at": now.isoformat(),
    }
    day = now.date().isoformat()
    snapshot = db.get(InsightSnapshot, day) or InsightSnapshot(day=day)
    snapshot.data = {"skills": dict(skills), "active_jobs": len(jobs)}
    db.add(snapshot)
    db.flush()
    data["history"] = [
        {"day": r.day, **r.data}
        for r in db.scalars(select(InsightSnapshot).order_by(InsightSnapshot.day.desc()).limit(90)).all()
    ][::-1]
    cached = cached or InsightCache(key="market")
    cached.data, cached.expires_at = data, now + timedelta(seconds=get_settings().insight_cache_seconds)
    db.add(cached)
    db.commit()
    return data

````

## backend/migrations/versions/c6f4a1b209d3_workspace_query_indexes.py

````
"""Indexes for cursor discovery, current resumes, match ordering and task polling."""

from alembic import op

revision = "c6f4a1b209d3"
down_revision = "ad18dbabd51a"
branch_labels = None
depends_on = None

INDEXES = [
    ("ix_jobs_active_cursor", "jobs", ["active", "is_demo", "id"]),
    ("ix_resumes_user_latest", "resumes", ["user_id", "id"]),
    ("ix_matches_resume_score", "match_results", ["resume_id", "score"]),
    ("ix_applications_user_updated", "applications", ["user_id", "updated_at"]),
    ("ix_work_items_pending_due", "work_items", ["status", "available_at", "id"]),
]


def upgrade():
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns)


def downgrade():
    for name, table, _ in reversed(INDEXES):
        op.drop_index(name, table_name=table)

````

## backend/sources.yaml

````
# Add boards you are permitted to republish. No arbitrary URLs are accepted.
# Sources start disabled; configure permitted boards and review provider terms before enabling.
sources:
  - key: greenhouse-example
    kind: greenhouse
    enabled: false
    interval_minutes: 360
    config: {slug: YOUR_COMPANY_SLUG, company: YOUR_COMPANY_NAME}
  - key: lever-example
    kind: lever
    enabled: false
    interval_minutes: 360
    config: {slug: YOUR_COMPANY_SLUG, region: global}
  - key: remotive
    kind: remotive
    enabled: false
    interval_minutes: 720
    config: {}
  - key: arbeitnow
    kind: arbeitnow
    enabled: false
    interval_minutes: 360
    config: {}
  - key: remoteok
    kind: remoteok
    enabled: false
    interval_minutes: 720
    config: {}
  - key: adzuna-india
    kind: adzuna
    enabled: false
    interval_minutes: 360
    config: {country: in, query: software}
  - key: adzuna-uk
    kind: adzuna
    enabled: false
    interval_minutes: 360
    config: {country: gb, query: software}
  - key: hackernews
    kind: hackernews
    enabled: false
    interval_minutes: 1440
    config: {thread_id: 0, max_comments: 200}

````

## docker-compose.yml

````
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
    ports: ["8080:8080"]
    depends_on:
      api:
        condition: service_healthy
    healthcheck:
      test: [CMD, wget, -q, --spider, http://127.0.0.1:8080/]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped
  worker:
    build: ./backend
    command: [python, -m, app.worker]
    env_file: .env
    volumes:
      - model-cache:/home/app/.cache
    depends_on:
      api:
        condition: service_healthy
    healthcheck:
      test: [CMD, python, -m, app.worker_health]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped
  mailpit:
    image: axllent/mailpit:v1.27
    profiles: [mail]
    user: "10001:10001"
    ports: ["8025:8025"]
    healthcheck:
      test: [CMD, /mailpit, readyz]
      interval: 30s
      timeout: 5s
      retries: 3
  dev-db:
    image: pgvector/pgvector:pg17
    profiles: [dev]
    environment:
      POSTGRES_USER: skillmatch
      POSTGRES_PASSWORD: ${DEV_DB_PASSWORD:?Set DEV_DB_PASSWORD}
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

## docs/stages/06_ENGINEERING.md

````
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

````

## frontend/Dockerfile

````
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
FROM nginxinc/nginx-unprivileged:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080

````

## frontend/nginx.conf

````
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
server {
    listen 8080;
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
    location = /api/v1/notifications/stream {
        limit_req zone=api_limit burst=10 nodelay;
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_buffering off;
        proxy_cache off;
        gzip off;
        proxy_read_timeout 90s;
    }
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
