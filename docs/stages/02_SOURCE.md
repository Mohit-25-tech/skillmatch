# Stage 02 — complete changed/new source

```text
.env.example
backend/app/config.py
backend/app/ingestion/__init__.py
backend/app/ingestion/adapters.py
backend/app/ingestion/http.py
backend/app/ingestion/normalization.py
backend/app/ingestion/service.py
backend/app/main.py
backend/app/models.py
backend/app/repositories/catalog.py
backend/app/routers/candidates.py
backend/app/routers/ingestion.py
backend/app/seed.py
backend/app/services/embeddings.py
backend/app/services/match_pipeline.py
backend/app/worker.py
backend/app/worker_health.py
backend/migrations/env.py
backend/migrations/versions/ea77977797e7_live_ingestion_vectors_and_work_queue.py
backend/requirements.txt
backend/sources.yaml
backend/tests/test_ingestion.py
docker-compose.yml
docs/stages/02_INGESTION.md
```

## .env.example

````
# Copy to .env and replace every PLACEHOLDER before deployment.
DATABASE_URL=postgresql+psycopg://PLACEHOLDER_USER:PLACEHOLDER_PASSWORD@PLACEHOLDER_NEON_HOST/PLACEHOLDER_DATABASE?sslmode=require
JWT_SECRET=PLACEHOLDER_GENERATE_AT_LEAST_32_RANDOM_CHARACTERS
ENVIRONMENT=development
COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:8080,http://localhost:5173
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

## backend/app/config.py

````
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
    demo_mode: bool = False
    ingestion_config: str = "sources.yaml"
    ingestion_user_agent: str = "SkillMatchAI/2.0 (public API reader; contact: configure INGESTION_USER_AGENT)"
    ingestion_timeout: float = 20
    ingestion_max_pages: int = 20
    ingestion_request_delay: float = 1.0
    worker_poll_seconds: int = 15
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    embedding_dimensions: int = 384
    match_semantic_weight: float = 0.50
    match_skills_weight: float = 0.30
    match_experience_weight: float = 0.15
    match_location_weight: float = 0.05
    insight_cache_seconds: int = 60
    smtp_host: str = ""
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    smtp_from: str = "noreply@example.invalid"
    ollama_enabled: bool = False
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2"
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

## backend/app/ingestion/__init__.py

````
"""Official public-feed adapters and ingestion orchestration."""

````

## backend/app/ingestion/adapters.py

````
"""Official APIs only. No employer-page, LinkedIn, Indeed, or Naukri scraping."""
import re
from abc import ABC, abstractmethod

from app.config import get_settings
from app.ingestion.http import FeedError, FeedHTTP
from app.ingestion.normalization import RawJob, plain_text, salary_text, timestamp


def slug(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", value):
        raise FeedError("Invalid company slug")
    return value


class Adapter(ABC):
    complete = False

    def __init__(self, http: FeedHTTP, config: dict):
        self.http, self.config = http, config
        self.complete = False

    @abstractmethod
    def fetch(self) -> list[RawJob]:
        """Return a validated snapshot; set complete only after every page succeeds."""
        raise NotImplementedError


class GreenhouseAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        company = slug(self.config["slug"])
        body = self.http.get(f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs", {"content": "true"})
        if not isinstance(body, dict) or not isinstance(body.get("jobs"), list):
            raise FeedError("Invalid Greenhouse feed")
        jobs = []
        for row in body['jobs']:
            location = row.get('location', {}).get('name') or 'Not specified'
            text = plain_text(row.get('content', ''))
            jobs.append(RawJob(external_id=str(row['id']), title=row['title'], company=self.config.get('company', company), location=location[:100], remote='remote' in location.lower(), description=text, apply_url=row['absolute_url'], posted_at=timestamp(row.get('first_published')), attribution='Greenhouse', attribution_url=row['absolute_url'], **salary_text(text)))
        self.complete = True
        return jobs


class LeverAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        company = slug(self.config['slug'])
        host = 'api.eu.lever.co' if self.config.get('region') == 'eu' else 'api.lever.co'
        jobs = []
        for page in range(get_settings().ingestion_max_pages):
            body = self.http.get(f'https://{host}/v0/postings/{company}', {'mode': 'json', 'skip': page * 100, 'limit': 100})
            if not isinstance(body, list):
                raise FeedError('Invalid Lever feed')
            for row in body:
                cats = row.get('categories') or {}
                pay = row.get('salaryRange') or {}
                text = (row.get('descriptionPlain') or row.get('description', '')) + '\n' + '\n'.join(str(x.get('text', '')) + '\n' + x.get('content', '') for x in row.get('lists', []))
                jobs.append(RawJob(external_id=row['id'], title=row['text'], company=self.config.get('company', company), location=(cats.get('location') or 'Not specified')[:100], remote=row.get('workplaceType') == 'remote', employment_type=cats.get('commitment') or 'Not specified', description=text, apply_url=row.get('applyUrl') or row['hostedUrl'], posted_at=timestamp(row.get('createdAt')), salary_min=round(pay['min']) if pay.get('min') is not None else None, salary_max=round(pay['max']) if pay.get('max') is not None else None, salary_currency=pay.get('currency'), salary_interval=pay.get('interval'), attribution='Lever', attribution_url=row['hostedUrl']))
            if len(body) < 100:
                self.complete = True
                break
        return jobs


class RemotiveAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        body = self.http.get('https://remotive.com/api/remote-jobs')
        if not isinstance(body, dict) or not isinstance(body.get('jobs'), list):
            raise FeedError('Invalid Remotive feed')
        result = [RawJob(external_id=str(r['id']), title=r['title'], company=r['company_name'], location=(r.get('candidate_required_location') or 'Not specified')[:100], remote=True, employment_type=r.get('job_type', 'Not specified').replace('_', '-'), description=r['description'], apply_url=r['url'], posted_at=timestamp(r.get('publication_date')), attribution='Remotive', attribution_url=r['url'], **salary_text(r.get('salary', ''))) for r in body['jobs']]
        self.complete = True
        return result


class ArbeitnowAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        jobs = []
        for page in range(1, get_settings().ingestion_max_pages + 1):
            body = self.http.get('https://www.arbeitnow.com/api/job-board-api', {'page': page})
            if not isinstance(body, dict) or not isinstance(body.get('data'), list):
                raise FeedError('Invalid Arbeitnow feed')
            for r in body['data']:
                jobs.append(RawJob(external_id=r['slug'], title=r['title'], company=r['company_name'], location=(r.get('location') or 'Not specified')[:100], remote=bool(r.get('remote')), employment_type=','.join(r.get('job_types', [])) or 'Not specified', description=r['description'], apply_url=r['url'], posted_at=timestamp(r.get('created_at')), attribution='Arbeitnow', attribution_url=r['url']))
            if not body.get('links', {}).get('next'):
                self.complete = True
                break
        return jobs


class RemoteOKAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        body = self.http.get('https://remoteok.com/api')
        if not isinstance(body, list) or not body or not isinstance(body[0], dict) or 'legal' not in body[0]:
            raise FeedError('Invalid Remote OK feed or missing attribution terms')
        jobs = []
        for r in body[1:]:
            jobs.append(RawJob(external_id=str(r['id']), title=r['position'], company=r['company'], location=(r.get('location') or 'Not specified')[:100], remote=True, description=r['description'], apply_url=r['url'], posted_at=timestamp(r.get('date') or r.get('epoch')), salary_min=r.get('salary_min') or None, salary_max=r.get('salary_max') or None, salary_currency=r.get('salary_currency'), salary_interval='year' if r.get('salary_min') else None, attribution='Remote OK', attribution_url=r['url']))
        self.complete = True
        return jobs


class AdzunaAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        settings = get_settings()
        if not settings.adzuna_app_id or not settings.adzuna_app_key or 'PLACEHOLDER' in settings.adzuna_app_key:
            raise FeedError('Configure ADZUNA_APP_ID and ADZUNA_APP_KEY')
        country = self.config.get('country', 'in').lower()
        if country not in {'in', 'gb', 'us', 'au', 'at', 'be', 'br', 'ca', 'ch', 'de', 'es', 'fr', 'it', 'mx', 'nl', 'nz', 'pl', 'sg', 'za'}:
            raise FeedError('Unsupported Adzuna country')
        jobs = []
        for page in range(1, settings.ingestion_max_pages + 1):
            body = self.http.get(f'https://api.adzuna.com/v1/api/jobs/{country}/search/{page}', {'app_id': settings.adzuna_app_id, 'app_key': settings.adzuna_app_key, 'results_per_page': 50, 'what': self.config.get('query', ''), 'content-type': 'application/json'})
            if not isinstance(body, dict) or not isinstance(body.get('results'), list):
                raise FeedError('Invalid Adzuna feed')
            for r in body['results']:
                actual = str(r.get('salary_is_predicted', '1')) == '0'
                jobs.append(RawJob(external_id=str(r['id']), title=plain_text(r['title']), company=r.get('company', {}).get('display_name', 'Not specified'), location=r.get('location', {}).get('display_name', 'Not specified')[:100], remote=bool(re.search(r'\bremote\b', r['title'], re.I)), employment_type=r.get('contract_time', 'Not specified').replace('_', '-'), description=r['description'], apply_url=r['redirect_url'], posted_at=timestamp(r.get('created')), salary_min=round(r['salary_min']) if actual and r.get('salary_min') is not None else None, salary_max=round(r['salary_max']) if actual and r.get('salary_max') is not None else None, salary_currency=r.get('salary_currency'), salary_interval='year' if actual and r.get('salary_min') is not None else None, attribution='Adzuna', attribution_url=r['redirect_url']))
            if len(body['results']) < 50 or len(jobs) >= body.get('count', float('inf')):
                self.complete = True
                break
        return jobs


class HackerNewsAdapter(Adapter):
    def fetch(self) -> list[RawJob]:
        thread_id = int(self.config['thread_id'])
        parent = self.http.get(f'https://hacker-news.firebaseio.com/v0/item/{thread_id}.json')
        if not parent or 'who is hiring' not in parent.get('title', '').lower() or parent.get('by') != 'whoishiring':
            raise FeedError('Configure an official Who is hiring thread ID')
        jobs = []
        ids = parent.get('kids', [])
        limit = int(self.config.get('max_comments', 200))
        for item_id in ids[:limit]:
            row = self.http.get(f'https://hacker-news.firebaseio.com/v0/item/{int(item_id)}.json')
            if not row or row.get('deleted') or row.get('dead') or not row.get('text'):
                continue
            description = plain_text(row['text'])
            first = description.split('\n')[0]
            company = first.split('|')[0].strip()[:100] or 'Not specified'
            url = f'https://news.ycombinator.com/item?id={item_id}'
            jobs.append(RawJob(external_id=str(item_id), title=first[:150], company=company, description=description, remote=bool(re.search(r'\bremote\b', first, re.I)), apply_url=url, posted_at=timestamp(row.get('time')), attribution='Hacker News — Who is hiring', attribution_url=url, **salary_text(description)))
        # A discussion is not an authoritative active-jobs inventory; never close from disappearance.
        self.complete = False
        return jobs


ADAPTERS = {'greenhouse': GreenhouseAdapter, 'lever': LeverAdapter, 'remotive': RemotiveAdapter, 'arbeitnow': ArbeitnowAdapter, 'remoteok': RemoteOKAdapter, 'adzuna': AdzunaAdapter, 'hackernews': HackerNewsAdapter}

````

## backend/app/ingestion/http.py

````
"""Bounded, allowlisted HTTP reads with conditional caching and retries."""
import hashlib
import json
import re
import time
from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import FeedCache, utcnow

HOSTS = {"boards-api.greenhouse.io", "api.lever.co", "api.eu.lever.co", "remotive.com", "www.arbeitnow.com", "remoteok.com", "api.adzuna.com", "hacker-news.firebaseio.com"}


class FeedError(RuntimeError):
    pass


class FeedHTTP:
    def __init__(self, db: Session, client: httpx.Client | None = None, sleep=time.sleep):
        self.db, self.sleep = db, sleep
        self.client = client or httpx.Client(timeout=get_settings().ingestion_timeout, follow_redirects=False)
        self.owned = client is None
        self.last_request = 0.0

    def close(self):
        if self.owned:
            self.client.close()

    def get(self, url: str, params: dict | None = None):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.username or parsed.port not in (None, 443):
            raise FeedError("Only configured official API hosts are permitted")
        key = hashlib.sha256((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
        cached = self.db.get(FeedCache, key)
        now = utcnow()
        if cached and cached.expires_at.replace(tzinfo=timezone.utc) > now:
            return cached.payload
        headers = {"User-Agent": get_settings().ingestion_user_agent, "Accept": "application/json"}
        if cached:
            if cached.etag:
                headers["If-None-Match"] = cached.etag
            if cached.modified:
                headers["If-Modified-Since"] = cached.modified
        for attempt in range(3):
            delay = get_settings().ingestion_request_delay - (time.monotonic() - self.last_request)
            if delay > 0:
                self.sleep(delay)
            try:
                response = self.client.get(url, params=params, headers=headers)
                self.last_request = time.monotonic()
                if response.status_code == 429 or response.status_code >= 500:
                    retry = response.headers.get("Retry-After", "")
                    if retry.isdigit():
                        wait = int(retry)
                    else:
                        try:
                            wait = max(0, (parsedate_to_datetime(retry) - now).total_seconds())
                        except (TypeError, ValueError):
                            wait = 2 ** attempt
                    if wait > 30:
                        raise FeedError("Source requested a longer retry delay; defer to next scheduled run")
                    self.sleep(wait)
                    continue
                if response.status_code == 304 and cached:
                    payload = cached.payload
                else:
                    if response.status_code != 200:
                        raise FeedError(f"Source returned HTTP {response.status_code}")
                    if len(response.content) > 30 * 1024 * 1024:
                        raise FeedError("Feed exceeds the 30 MB response limit")
                    payload = response.json()
                control = response.headers.get("Cache-Control", "")
                max_age = re.search(r"(?:s-maxage|max-age)=(\d+)", control)
                expiry = now + timedelta(seconds=int(max_age[1]) if max_age else 0)
                if not max_age and response.headers.get("Expires"):
                    try:
                        expiry = parsedate_to_datetime(response.headers["Expires"])
                    except (TypeError, ValueError):
                        pass
                if "no-cache" in control:
                    expiry = now
                if "no-store" not in control:
                    cached = cached or FeedCache(key=key)
                    cached.payload, cached.expires_at = payload, expiry
                    cached.etag = response.headers.get("ETag", cached.etag)
                    cached.modified = response.headers.get("Last-Modified", cached.modified)
                    self.db.add(cached)
                    self.db.flush()
                return payload
            except (httpx.TransportError, ValueError):
                if attempt < 2:
                    self.sleep(2 ** attempt)
        raise FeedError("Source unavailable after three attempts")

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

from pydantic import BaseModel, Field, field_validator


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
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=timezone.utc) if not datetime.fromisoformat(str(value).replace("Z", "+00:00")).tzinfo else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, OverflowError, OSError):
        return None


def normalized(value: str) -> str:
    return " ".join(sorted(re.findall(r"[\w+#]+", unicodedata.normalize("NFKC", value).casefold())))


def fingerprint(title: str, company: str, location: str) -> str:
    return hashlib.sha256("|".join(normalized(v) for v in (title, company, location)).encode()).hexdigest()


def salary_text(value: str) -> dict:
    """Only explicit two-ended ranges with an identifiable currency; never estimate."""
    match = re.search(r"(?P<c>USD|EUR|GBP|INR|US\$|€|£|₹)\s*(?P<lo>[\d,.]+)\s*(?P<lk>[kK]?)\s*[-–—]\s*(?:USD|EUR|GBP|INR|US\$|€|£|₹)?\s*(?P<hi>[\d,.]+)\s*(?P<hk>[kK]?)", value or "", re.I)
    if not match:
        return {}
    currency = {"US$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}.get(match['c'].upper(), match['c'].upper())
    low = float(match['lo'].replace(',', '')) * (1000 if match['lk'] or match['hk'] else 1)
    high = float(match['hi'].replace(',', '')) * (1000 if match['hk'] else 1)
    if not 0 < low <= high <= 100000000:
        return {}
    period = next((p for p, pattern in [('hour', r'hour|hourly'), ('month', r'month|monthly'), ('year', r'year|annual|annum')] if re.search(pattern, value, re.I)), None)
    return dict(salary_min=round(low), salary_max=round(high), salary_currency=currency, salary_interval=period)


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

````

## backend/app/ingestion/service.py

````
import hashlib
import json
import logging
from datetime import timedelta
from difflib import SequenceMatcher
from pathlib import Path

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.ingestion.adapters import ADAPTERS
from app.ingestion.http import FeedHTTP
from app.ingestion.normalization import fingerprint, normalized
from app.models import IngestionRun, IngestionSource, Job, JobOrigin, MatchResult, WorkItem, utcnow
from app.services.embeddings import encode_many
from app.services.parsing import extract_skills
from app.services.taxonomy import ensure_taxonomy

log = logging.getLogger(__name__)


def configure_sources(db: Session) -> None:
    path = Path(get_settings().ingestion_config)
    if not path.exists():
        return
    document = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    for item in document.get('sources', []):
        if item['kind'] not in ADAPTERS:
            raise ValueError('Unknown ingestion adapter')
        if not db.scalar(select(IngestionSource).where(IngestionSource.key == item['key'])):
            db.add(IngestionSource(key=item['key'], kind=item['kind'], config=item.get('config', {}), enabled=bool(item.get('enabled', False)), interval_minutes=max(60, int(item.get('interval_minutes', 360)))))
    db.commit()


def find_duplicate(db: Session, raw) -> Job | None:
    fp = fingerprint(raw.title, raw.company, raw.location)
    exact = db.scalar(select(Job).where(Job.fingerprint == fp, Job.is_demo.is_(False)))
    if exact:
        return exact
    candidates = db.scalars(select(Job).where(func.lower(Job.company) == raw.company.casefold(), Job.is_demo.is_(False), Job.source != 'native')).all()
    for job in candidates:
        if normalized(job.location) == normalized(raw.location) and SequenceMatcher(None, normalized(job.title), normalized(raw.title)).ratio() >= .94:
            return job
    return None


def ingest(db: Session, source: IngestionSource, adapter=None) -> dict:
    run = IngestionRun(source_id=source.id)
    source.status, source.last_run_at = 'running', utcnow()
    db.add(run)
    db.commit()
    http = FeedHTTP(db)
    stats = {'added': 0, 'updated': 0, 'closed': 0, 'seen': 0}
    try:
        adapter = adapter or ADAPTERS[source.kind](http, source.config)
        rows = adapter.fetch()  # No mutation of availability before the whole fetch validates.
        taxonomy = {s.name: s for s in ensure_taxonomy(db)}
        seen = set()
        changed = []
        for raw in rows:
            if raw.external_id in seen:
                continue
            seen.add(raw.external_id)
            origin = db.scalar(select(JobOrigin).where(JobOrigin.source_id == source.id, JobOrigin.external_id == raw.external_id))
            job = db.get(Job, origin.job_id) if origin else find_duplicate(db, raw)
            if job is None:
                job = Job(source=source.kind, external_id=f'{source.key}:{raw.external_id}', is_demo=False, active=True)
                db.add(job)
                stats['added'] += 1
            payload = raw.model_dump(exclude={'external_id', 'attribution', 'attribution_url'})
            content_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
            if job.content_hash != content_hash:
                if job.id:
                    stats['updated'] += 1
                for key, value in payload.items():
                    setattr(job, key, value)
                job.fingerprint = fingerprint(raw.title, raw.company, raw.location)
                job.content_hash, job.updated_at = content_hash, utcnow()
                names = extract_skills(raw.title + '\n' + raw.description, list(taxonomy))
                job.skills = [taxonomy[n] for n in names]
                job.skill_importance = {name: 'required' for name in names}
                changed.append(job)
            job.active = True
            db.flush()
            if not origin:
                origin = JobOrigin(job_id=job.id, source_id=source.id, external_id=raw.external_id)
                db.add(origin)
            origin.apply_url, origin.attribution, origin.attribution_url = raw.apply_url, raw.attribution, raw.attribution_url
            origin.active, origin.seen_at = True, utcnow()
        for start in range(0, len(changed), 32):
            batch = changed[start:start + 32]
            vectors = encode_many([j.title + '\n' + j.description for j in batch])
            for job, vector in zip(batch, vectors, strict=True):
                job.embedding, job.embedding_model = vector, get_settings().embedding_model if vector else None
                db.query(MatchResult).filter(MatchResult.job_id == job.id).delete(synchronize_session=False)
        if adapter.complete:
            origins = db.scalars(select(JobOrigin).where(JobOrigin.source_id == source.id, JobOrigin.active.is_(True))).all()
            for origin in origins:
                if origin.external_id not in seen:
                    origin.active = False
                    db.flush()
                    other = db.scalar(select(func.count(JobOrigin.id)).where(JobOrigin.job_id == origin.job_id, JobOrigin.active.is_(True)))
                    job = db.get(Job, origin.job_id)
                    if not other and job.active and job.source != 'native':
                        job.active = False
                        stats['closed'] += 1
        stats['seen'], stats['complete'] = len(seen), adapter.complete
        source.status = run.status = 'success' if adapter.complete else 'partial'
        source.last_success_at, source.last_error = utcnow(), None
        source.stats = run.stats = stats
        if changed:
            db.add(WorkItem(kind='catalog', payload={'job_ids': [j.id for j in changed]}))
        db.commit()
    except Exception as error:
        db.rollback()
        source = db.get(IngestionSource, source.id)
        run = db.get(IngestionRun, run.id)
        source.status = run.status = 'error'
        # Exception text can contain credential-bearing request URLs. Never persist it.
        source.last_error = run.error = f'{type(error).__name__}: feed was not committed; check configuration and source availability'
        log.warning('ingestion_failed source=%s error_type=%s', source.key, type(error).__name__)
    finally:
        http.close()
        source.next_run_at = utcnow() + timedelta(minutes=max(60, source.interval_minutes))
        run.finished_at = utcnow()
        db.commit()
    log.info(json.dumps({'event': 'ingestion_complete', 'source': source.key, 'status': source.status, 'stats': stats}))
    return {'status': source.status, **(source.stats if source.status != 'error' else {})}

````

## backend/app/main.py

````
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
from app.routers import analytics, auth, candidates, ingestion, jobs

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


for router in (auth.router, jobs.router, candidates.router, analytics.router, ingestion.router):
    app.include_router(router, prefix="/api/v1")

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

````

## backend/app/repositories/catalog.py

````
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
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
    if not get_settings().demo_mode:
        stmt = stmt.where(Job.is_demo.is_(False))
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

## backend/app/routers/candidates.py

````
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.limits import limiter
from app.models import Application, Job, MatchResult, Resume, User, WorkItem
from app.repositories.catalog import job_public, resume_public
from app.schemas import MatchInput, StatusInput
from app.security import roles
from app.services.matching import embed, match_public, save_match
from app.services.parsing import MAX_FILE_SIZE, extract_skills, parse_resume
from app.services.taxonomy import ensure_taxonomy

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
    skills = ensure_taxonomy(db)
    names = extract_skills(text, [s.name for s in skills])
    resume = Resume(
        user_id=user.id, filename=filename, text=text, skills=[s for s in skills if s.name in names]
    )
    db.add(resume)
    db.flush()
    db.add(WorkItem(kind='resume', payload={'resume_id': resume.id}))
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

## backend/app/routers/ingestion.py

````
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.ingestion.adapters import ADAPTERS
from app.models import IngestionRun, IngestionSource, User, WorkerHeartbeat, WorkItem
from app.security import roles

router = APIRouter(prefix='/admin/ingestion', tags=['Ingestion administration'])


class SourceInput(BaseModel):
    key: str = Field(pattern=r'^[a-z0-9_-]{1,150}$')
    kind: str
    config: dict = Field(default_factory=dict)
    enabled: bool = False
    interval_minutes: int = Field(default=360, ge=60, le=10080)


class SourceUpdate(BaseModel):
    enabled: bool
    interval_minutes: int | None = Field(default=None, ge=60, le=10080)


def source_public(source: IngestionSource) -> dict:
    return {key: getattr(source, key) for key in ('id', 'key', 'kind', 'config', 'enabled', 'interval_minutes', 'status', 'stats', 'last_run_at', 'last_success_at', 'last_error', 'next_run_at')}


@router.get('')
def sources(user: User = Depends(roles('admin')), db: Session = Depends(get_db)) -> dict:
    heartbeat = db.get(WorkerHeartbeat, 'ingestion')
    return {'items': [source_public(s) for s in db.scalars(select(IngestionSource).order_by(IngestionSource.id))], 'worker_last_seen': heartbeat.seen_at if heartbeat else None}


@router.post('', status_code=201)
def add_source(body: SourceInput, user: User = Depends(roles('admin')), db: Session = Depends(get_db)) -> dict:
    if body.kind not in ADAPTERS:
        raise HTTPException(422, 'Unknown adapter')
    if any(k not in {'slug', 'company', 'region', 'country', 'query', 'thread_id', 'max_comments'} for k in body.config):
        raise HTTPException(422, 'Unsupported configuration key; credentials belong in environment variables')
    if body.kind in {'remotive', 'remoteok'} and body.interval_minutes < 360:
        raise HTTPException(422, 'Use an interval of at least 360 minutes for this source')
    source = IngestionSource(**body.model_dump())
    db.add(source)
    db.commit()
    return source_public(source)


@router.patch('/{source_id}')
def toggle(source_id: int, body: SourceUpdate, user: User = Depends(roles('admin')), db: Session = Depends(get_db)) -> dict:
    source = db.get(IngestionSource, source_id)
    if not source:
        raise HTTPException(404, 'Source not found')
    if body.interval_minutes is not None:
        if source.kind in {'remotive', 'remoteok'} and body.interval_minutes < 360:
            raise HTTPException(422, 'Minimum interval is 360 minutes for this source')
        source.interval_minutes = body.interval_minutes
    source.enabled = body.enabled
    db.commit()
    return source_public(source)


@router.post('/{source_id}/run', status_code=202)
def run_now(source_id: int, user: User = Depends(roles('admin')), db: Session = Depends(get_db)) -> dict:
    source = db.get(IngestionSource, source_id)
    if not source:
        raise HTTPException(404, 'Source not found')
    if not source.enabled:
        raise HTTPException(409, 'Enable the source before running it')
    item = db.scalar(select(WorkItem).where(WorkItem.kind == 'ingestion', WorkItem.status.in_(['pending', 'running']), WorkItem.payload['source_id'].as_integer() == source_id))
    if not item:
        item = WorkItem(kind='ingestion', payload={'source_id': source_id})
        db.add(item)
        db.commit()
    return {'work_item_id': item.id, 'status': item.status}


@router.get('/{source_id}/runs')
def runs(source_id: int, page: int = Query(1, ge=1), user: User = Depends(roles('admin')), db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(IngestionRun).where(IngestionRun.source_id == source_id).order_by(IngestionRun.id.desc()).offset((page - 1) * 25).limit(25)).all()
    return {'items': [{k: getattr(r, k) for k in ('id', 'started_at', 'finished_at', 'status', 'stats', 'error')} for r in rows], 'page': page}

````

## backend/app/seed.py

````
import argparse
import secrets

from sqlalchemy import func, select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Job, Skill, User
from app.security import password_hash
from app.seed_data import generate_jobs
from app.services.taxonomy import ensure_taxonomy


def seed(demo: bool = False) -> None:
    with SessionLocal() as db:
        ensure_taxonomy(db)
        db.commit()
        if not demo or db.scalar(select(func.count(Job.id)).where(Job.is_demo.is_(True))) > 0:
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
            db.add(Job(**data, recruiter_id=owner.id, is_demo=True, source="demo", salary_currency="USD", salary_interval="year", skills=[skills[n] for n in names]))
        db.commit()
        print("Seeded 200 synthetic jobs and 300 skills. No demo credentials were created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--if-enabled", action="store_true")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.demo and get_settings().environment == "production":
        parser.error("Demo seed is disabled in production")
    if not args.if_enabled or get_settings().seed_on_start:
        seed(demo=args.demo)

````

## backend/app/services/embeddings.py

````
"""Batch embedding generation, model identity, and a bounded outage cooldown."""
import logging
import time
from functools import lru_cache

from app.config import get_settings

log = logging.getLogger(__name__)
_retry_after = 0.0


@lru_cache(maxsize=1)
def model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(get_settings().embedding_model)


def encode_many(texts: list[str]) -> list[list[float] | None]:
    global _retry_after
    if not texts:
        return []
    if not get_settings().semantic_enabled or time.monotonic() < _retry_after:
        return [None] * len(texts)
    try:
        vectors = model().encode([t[:12000] for t in texts], batch_size=32, normalize_embeddings=True)
        if vectors.shape[1] != 384:
            raise ValueError('Configured model must have 384 dimensions; changing dimensions requires a migration')
        return [v.tolist() for v in vectors]
    except Exception as error:
        _retry_after = time.monotonic() + 300
        log.warning('embedding_unavailable type=%s retry_in_seconds=300', type(error).__name__)
        return [None] * len(texts)

````

## backend/app/services/match_pipeline.py

````
"""Compute coverage across the catalog, including historical resumes."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import engine
from app.models import Job, MatchResult, Resume
from app.services.matching import save_match
from app.services.parsing import extract_skills
from app.services.taxonomy import ensure_taxonomy


def match_resume(db: Session, resume: Resume, only_missing: bool = False, job_ids: list[int] | None = None) -> int:
    taxonomy = ensure_taxonomy(db)
    names = extract_skills(resume.text, [s.name for s in taxonomy])
    resume.skills = [s for s in taxonomy if s.name in names]
    existing = set(db.scalars(select(MatchResult.job_id).where(MatchResult.resume_id == resume.id))) if only_missing else set()
    count = 0
    query = select(Job).where(Job.active.is_(True))
    if not get_settings().demo_mode:
        query = query.where(Job.is_demo.is_(False))
    if job_ids is not None:
        query = query.where(Job.id.in_(job_ids))
    for job in db.scalars(query).all():
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


def reindex_all(db: Session, only_missing: bool = False, job_ids: list[int] | None = None) -> int:
    latest = select(func.max(Resume.id)).group_by(Resume.user_id)
    return sum(match_resume(db, resume, only_missing, job_ids) for resume in db.scalars(select(Resume).where(Resume.id.in_(latest))).all())


if __name__ == "__main__":
    with Session(engine) as session:
        print(f"Computed {reindex_all(session)} latest-resume/job matches")

````

## backend/app/worker.py

````
"""One worker process: durable SQL task queue + APScheduler timers."""
import logging
import signal
import threading
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select, update

from app.config import get_settings
from app.db import SessionLocal
from app.ingestion.service import configure_sources, ingest
from app.models import IngestionSource, Resume, WorkerHeartbeat, WorkItem, utcnow
from app.services.match_pipeline import match_resume, reindex_all

log = logging.getLogger(__name__)


def heartbeat() -> None:
    with SessionLocal() as db:
        row = db.get(WorkerHeartbeat, 'ingestion') or WorkerHeartbeat(id='ingestion')
        row.seen_at = utcnow()
        db.add(row)
        db.commit()


def process_tasks() -> None:
    with SessionLocal() as db:
        now = utcnow()
        db.execute(update(WorkItem).where(WorkItem.status == 'running', WorkItem.locked_at < now - timedelta(minutes=30)).values(status='pending', available_at=now))
        db.commit()
        item = db.scalar(select(WorkItem).where(WorkItem.status == 'pending', WorkItem.available_at <= now).order_by(WorkItem.id).with_for_update(skip_locked=True).limit(1))
        if not item:
            return
        item.status, item.locked_at, item.attempts = 'running', now, item.attempts + 1
        db.commit()
        try:
            if item.kind == 'resume':
                resume = db.get(Resume, item.payload['resume_id'])
                if resume:
                    match_resume(db, resume)
            elif item.kind == 'catalog':
                reindex_all(db, only_missing=True, job_ids=item.payload.get('job_ids'))
            elif item.kind == 'ingestion':
                source = db.get(IngestionSource, item.payload['source_id'])
                if source and source.enabled:
                    result = ingest(db, source)
                    if result['status'] == 'error':
                        raise RuntimeError('Feed run failed')
            elif item.kind == 'digest':
                from app.services.product import send_digests
                send_digests(db)
            else:
                raise ValueError('Unknown work item type')
            item.status, item.error = 'done', None
        except Exception as error:
            db.rollback()
            item = db.get(WorkItem, item.id)
            item.status = 'failed' if item.attempts >= 3 else 'pending'
            item.available_at = utcnow() + timedelta(seconds=60 * 2 ** item.attempts)
            item.error = type(error).__name__
            log.error('work_item_failed id=%s kind=%s error_type=%s', item.id, item.kind, type(error).__name__)
        db.commit()


def schedule_sources() -> None:
    with SessionLocal() as db:
        now = utcnow()
        for source in db.scalars(select(IngestionSource).where(IngestionSource.enabled.is_(True), IngestionSource.next_run_at <= now)).all():
            claimed = db.execute(update(IngestionSource).where(IngestionSource.id == source.id, IngestionSource.next_run_at <= now).values(next_run_at=now + timedelta(minutes=source.interval_minutes)))
            if claimed.rowcount:
                pending = db.scalar(select(WorkItem.id).where(WorkItem.kind == 'ingestion', WorkItem.status.in_(['pending', 'running']), WorkItem.payload['source_id'].as_integer() == source.id))
                if not pending:
                    db.add(WorkItem(kind='ingestion', payload={'source_id': source.id}))
        db.commit()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logging.getLogger('httpx').setLevel(logging.WARNING)
    with SessionLocal() as db:
        configure_sources(db)
    scheduler = BackgroundScheduler(timezone='UTC')
    scheduler.add_job(heartbeat, 'interval', seconds=30, max_instances=1, next_run_time=utcnow())
    scheduler.add_job(schedule_sources, 'interval', seconds=60, max_instances=1, next_run_time=utcnow())
    scheduler.add_job(process_tasks, 'interval', seconds=get_settings().worker_poll_seconds, max_instances=1, next_run_time=utcnow())
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    scheduler.start()
    stop.wait()
    scheduler.shutdown(wait=True)


if __name__ == '__main__':
    main()

````

## backend/app/worker_health.py

````
from datetime import timedelta, timezone

from app.db import SessionLocal
from app.models import WorkerHeartbeat, utcnow

with SessionLocal() as db:
    row = db.get(WorkerHeartbeat, 'ingestion')
    if not row or row.seen_at.replace(tzinfo=timezone.utc) < utcnow() - timedelta(seconds=120):
        raise SystemExit(1)

````

## backend/migrations/env.py

````
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
        sqlite = connection.dialect.name == "sqlite"
        if sqlite:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()

        if sqlite:
            connection.commit()
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            if connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("Migration left invalid foreign keys")

````

## backend/migrations/versions/ea77977797e7_live_ingestion_vectors_and_work_queue.py

````
"""live ingestion vectors and work queue"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = 'ea77977797e7'
down_revision = 'ea131b083c8f'
branch_labels = None
depends_on = None

def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('feed_cache',
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('etag', sa.Text(), nullable=True),
    sa.Column('modified', sa.Text(), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('key')
    )
    op.create_table('ingestion_sources',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=150), nullable=False),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('config', sa.JSON(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('interval_minutes', sa.Integer(), nullable=False),
    sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('stats', sa.JSON(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    with op.batch_alter_table('ingestion_sources', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ingestion_sources_next_run_at'), ['next_run_at'], unique=False)

    op.create_table('work_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('available_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('work_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_work_items_available_at'), ['available_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_work_items_kind'), ['kind'], unique=False)
        batch_op.create_index(batch_op.f('ix_work_items_status'), ['status'], unique=False)

    op.create_table('worker_heartbeats',
    sa.Column('id', sa.String(length=100), nullable=False),
    sa.Column('seen_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ingestion_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('stats', sa.JSON(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['source_id'], ['ingestion_sources.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('ingestion_runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ingestion_runs_source_id'), ['source_id'], unique=False)

    op.create_table('job_origins',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('external_id', sa.String(length=300), nullable=False),
    sa.Column('apply_url', sa.Text(), nullable=False),
    sa.Column('attribution', sa.String(length=100), nullable=False),
    sa.Column('attribution_url', sa.Text(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('seen_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_id'], ['ingestion_sources.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_id', 'external_id', name='uq_origin_source_external')
    )
    with op.batch_alter_table('job_origins', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_job_origins_job_id'), ['job_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_job_origins_source_id'), ['source_id'], unique=False)

    with op.batch_alter_table('jobs', schema=None, table_args=(sa.CheckConstraint('salary_min >= 0 AND salary_max >= salary_min', name='ck_jobs_salary'),)) as batch_op:
        batch_op.add_column(sa.Column('salary_currency', sa.String(length=3), nullable=True))
        batch_op.add_column(sa.Column('salary_interval', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('remote', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('apply_url', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(length=30), nullable=False, server_default='native'))
        batch_op.add_column(sa.Column('external_id', sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('fingerprint', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('embedding', sa.JSON().with_variant(Vector(384), 'postgresql'), nullable=True))
        batch_op.add_column(sa.Column('embedding_model', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('content_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('skill_importance', sa.JSON(), nullable=False, server_default='{}'))
        batch_op.add_column(sa.Column('experience_min', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
        batch_op.alter_column('recruiter_id',
               existing_type=sa.INTEGER(),
               nullable=True)
        batch_op.alter_column('salary_min',
               existing_type=sa.INTEGER(),
               nullable=True)
        batch_op.alter_column('salary_max',
               existing_type=sa.INTEGER(),
               nullable=True)
        batch_op.create_index(batch_op.f('ix_jobs_fingerprint'), ['fingerprint'], unique=False)
        batch_op.create_index(batch_op.f('ix_jobs_is_demo'), ['is_demo'], unique=False)
        batch_op.create_index(batch_op.f('ix_jobs_posted_at'), ['posted_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_jobs_source'), ['source'], unique=False)
        batch_op.create_unique_constraint('uq_jobs_source_external', ['source', 'external_id'])

    op.execute("UPDATE jobs SET is_demo = true, source = 'demo' WHERE recruiter_id IN (SELECT id FROM users WHERE email = 'catalog@skillmatch.example')")
    op.execute("UPDATE jobs SET posted_at = created_at WHERE source = 'native'")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE INDEX ix_jobs_embedding_hnsw ON jobs USING hnsw (embedding vector_cosine_ops) WHERE embedding IS NOT NULL")

def downgrade():
    if not op.get_context().as_sql and op.get_bind().execute(sa.text("SELECT count(*) FROM jobs WHERE recruiter_id IS NULL OR salary_min IS NULL OR salary_max IS NULL")).scalar():
        raise RuntimeError("Downgrade cannot represent live jobs with unknown salaries or no recruiter; export and resolve these records first.")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_jobs_embedding_hnsw")
    with op.batch_alter_table('jobs', schema=None, table_args=(sa.CheckConstraint('salary_min >= 0 AND salary_max >= salary_min', name='ck_jobs_salary'),)) as batch_op:
        batch_op.drop_constraint('uq_jobs_source_external', type_='unique')
        batch_op.drop_index(batch_op.f('ix_jobs_source'))
        batch_op.drop_index(batch_op.f('ix_jobs_posted_at'))
        batch_op.drop_index(batch_op.f('ix_jobs_is_demo'))
        batch_op.drop_index(batch_op.f('ix_jobs_fingerprint'))
        batch_op.alter_column('salary_max',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.alter_column('salary_min',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.alter_column('recruiter_id',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.drop_column('updated_at')
        batch_op.drop_column('experience_min')
        batch_op.drop_column('skill_importance')
        batch_op.drop_column('content_hash')
        batch_op.drop_column('embedding_model')
        batch_op.drop_column('embedding')
        batch_op.drop_column('fingerprint')
        batch_op.drop_column('is_demo')
        batch_op.drop_column('posted_at')
        batch_op.drop_column('external_id')
        batch_op.drop_column('source')
        batch_op.drop_column('apply_url')
        batch_op.drop_column('remote')
        batch_op.drop_column('salary_interval')
        batch_op.drop_column('salary_currency')

    with op.batch_alter_table('job_origins', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_job_origins_source_id'))
        batch_op.drop_index(batch_op.f('ix_job_origins_job_id'))

    op.drop_table('job_origins')
    with op.batch_alter_table('ingestion_runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ingestion_runs_source_id'))

    op.drop_table('ingestion_runs')
    op.drop_table('worker_heartbeats')
    with op.batch_alter_table('work_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_work_items_status'))
        batch_op.drop_index(batch_op.f('ix_work_items_kind'))
        batch_op.drop_index(batch_op.f('ix_work_items_available_at'))

    op.drop_table('work_items')
    with op.batch_alter_table('ingestion_sources', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ingestion_sources_next_run_at'))

    op.drop_table('ingestion_sources')
    op.drop_table('feed_cache')

````

## backend/requirements.txt

````
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
pgvector>=0.3.6,<1
APScheduler>=3.11,<4
PyYAML>=6.0.2,<7

````

## backend/sources.yaml

````
# Add boards you are permitted to republish. No arbitrary URLs are accepted.
# All sources start disabled until attribution is wired into the stage-4 UI.
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

## backend/tests/test_ingestion.py

````
import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.ingestion.adapters import GreenhouseAdapter
from app.ingestion.http import FeedHTTP
from app.ingestion.normalization import RawJob, plain_text, salary_text
from app.ingestion.service import ingest
from app.models import IngestionSource, Job


def test_official_http_adapter():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    def handler(request):
        assert request.url.host == 'boards-api.greenhouse.io'
        return httpx.Response(200, json={'jobs': [{'id': 1, 'title': 'ML Engineer', 'location': {'name': 'Remote'}, 'content': '<p>Python PyTorch</p>', 'absolute_url': 'https://example.org/job/1'}]})
    with Session(engine) as db, httpx.Client(transport=httpx.MockTransport(handler)) as client:
        http = FeedHTTP(db, client=client, sleep=lambda _: None)
        adapter = GreenhouseAdapter(http, {'slug': 'acme'})
        rows = adapter.fetch()
        assert adapter.complete and rows[0].salary_min is None
        assert rows[0].description == 'Python PyTorch'


def test_dedupe_complete_partial_and_failure():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    class Snapshot:
        complete = True
        rows = [RawJob(external_id='1', title='ML Engineer', company='Acme', description='Python PyTorch', apply_url='https://example.org/1', attribution='Test', attribution_url='https://example.org/1')]
        def fetch(self):
            return self.rows
    with Session(engine) as db:
        source = IngestionSource(key='a', kind='greenhouse')
        db.add(source)
        db.commit()
        adapter = Snapshot()
        assert ingest(db, source, adapter)['added'] == 1
        assert ingest(db, source, adapter)['added'] == 0
        job = db.scalar(select(Job))
        assert {s.name for s in job.skills} == {'Python', 'PyTorch', 'Machine Learning'}
        adapter.rows, adapter.complete = [], False
        assert ingest(db, source, adapter)['closed'] == 0
        assert job.active
        adapter.complete = True
        assert ingest(db, source, adapter)['closed'] == 1
        assert not job.active


def test_sanitization_and_unknown_pay():
    assert plain_text('<script>alert(1)</script><b>Python</b>') == 'Python'
    assert salary_text('competitive') == {}
    with pytest.raises(ValueError):
        RawJob(external_id='x', title='Engineer', company='Acme', description='test', apply_url='javascript:alert(1)', attribution='x', attribution_url='https://example.org')


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

## docs/stages/02_INGESTION.md

````
# Stage 2: ingestion, worker and Docker

The adapter layer supports Greenhouse, Lever, Remotive, Arbeitnow, Remote OK, Adzuna country feeds and an optional explicit Hacker News hiring thread. Feeds validate before modifying availability. Only complete inventories close missing jobs; truncated feeds and HN threads never do. Cross-source origins preserve attribution and prevent premature closure. Unknown or predicted pay stays null.

Sources start disabled in sources.yaml. Configure company slugs and credentials, then enable using the administrator API under /api/v1/admin/ingestion. Keep public feeds disabled until stage 4 renders their required source attribution and outbound links. Remotive listings must remain publicly accessible without registration. Remote OK requires a followed attribution link. API listings are public.

The database stores jobs, origins, feed cache, ingestion runs and a durable work queue. One separate worker schedules sources, retries tasks and exposes a database heartbeat. Job vectors use pgvector(384) on PostgreSQL and JSON for SQLite tests. Model unavailability preserves ingestion and uses structured matching.

Run from backend:

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m alembic upgrade ea77977797e7
..\.venv\Scripts\python.exe -m app.seed
..\.venv\Scripts\python.exe -m app.worker
```

Copy .env.example to .env and replace placeholders, then from root: `docker compose up --build`. The optional local database is `--profile dev`; set DATABASE_URL to its service hostname and matching DEV_DB_PASSWORD. Optional SMTP capture: `docker compose --profile mail up --build`, SMTP_HOST=mailpit, SMTP_STARTTLS=false. Demo jobs require `python -m app.seed --demo` and DEMO_MODE=true to appear. Never enable this in production.

Migration ea77977797e7 enables vector and creates a cosine HNSW index. Existing catalog fixtures are marked demo. No existing migration was edited. The database role must have extension creation permission; otherwise enable vector in the Neon SQL editor first. Downgrade refuses rows the old schema cannot represent instead of deleting live data.

Official source references: [Greenhouse](https://developers.greenhouse.io/job-board-api.html), [Lever](https://github.com/lever/postings-api), [Remotive terms](https://remotive.com/remote-jobs/api), [Arbeitnow terms](https://www.arbeitnow.com/terms), [Remote OK API terms](https://remoteok.com/api), [Adzuna](https://developer.adzuna.com/overview), [HN](https://github.com/HackerNews/API).

Full files and changed-file list are in 02_SOURCE.md. Tests use mocked HTTP and local SQLite; no live feed or production database was modified. Docker execution requires a running Docker engine.

````
