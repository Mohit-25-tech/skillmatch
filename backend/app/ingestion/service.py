import hashlib
import json
import logging
from datetime import timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

import yaml
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.ingestion.adapters import ADAPTERS
from app.ingestion.http import FeedHTTP
from app.ingestion.normalization import (
    fingerprint,
    infer_country,
    infer_experience_level,
    normalized,
)
from app.ingestion.relevance import clean_title_and_badge, is_cse_role
from app.models import IngestionRun, IngestionSource, Job, JobOrigin, MatchResult, WorkItem, utcnow
from app.services.embeddings import encode_many
from app.services.matching import experience, importance
from app.services.parsing import extract_skills
from app.services.taxonomy import ensure_taxonomy

log = logging.getLogger(__name__)


def configure_sources(db: Session) -> None:
    path = Path(get_settings().ingestion_config)
    if not path.exists():
        return
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for item in document.get("sources", []):
        if item["kind"] not in ADAPTERS:
            raise ValueError("Unknown ingestion adapter")
        if not db.scalar(select(IngestionSource).where(IngestionSource.key == item["key"])):
            db.add(
                IngestionSource(
                    key=item["key"],
                    kind=item["kind"],
                    config=item.get("config", {}),
                    enabled=bool(item.get("enabled", False)),
                    interval_minutes=max(
                        360 if item["kind"] == "remotive" else 60,
                        int(item.get("interval_minutes", 360)),
                    ),
                )
            )
    db.commit()


def find_duplicate(db: Session, raw) -> Job | None:
    fp = fingerprint(raw.title, raw.company, raw.location)
    exact = db.scalar(select(Job).where(Job.fingerprint == fp, Job.is_demo.is_(False)))
    if exact:
        return exact
    candidates = db.scalars(
        select(Job).where(
            func.lower(Job.company) == raw.company.casefold(), Job.is_demo.is_(False), Job.source != "native"
        )
    ).all()
    for job in candidates:
        if (
            normalized(job.location) == normalized(raw.location)
            and SequenceMatcher(None, normalized(job.title), normalized(raw.title)).ratio() >= 0.94
        ):
            return job
    return None


def ingest(db: Session, source: IngestionSource, adapter=None) -> dict:
    if source.kind == "remotive" and source.last_run_at:
        earliest = source.last_run_at.replace(tzinfo=timezone.utc) + timedelta(hours=6)
        if utcnow() < earliest:
            return {"status": "deferred", "next_run_at": earliest.isoformat()}
    run = IngestionRun(source_id=source.id)
    source.status, source.last_run_at = "running", utcnow()
    db.add(run)
    db.commit()
    http = FeedHTTP(db)
    stats = {"added": 0, "updated": 0, "closed": 0, "seen": 0}
    try:
        adapter = adapter or ADAPTERS[source.kind](http, source.config)
        rows = adapter.fetch()  # No mutation of availability before the whole fetch validates.
        if source.config.get("role_scope") == "cse":
            selected = [r for r in rows if is_cse_role(r.title, r.description)]
            stats["filtered_out"] = len(rows) - len(selected)
            rows = selected
        taxonomy = {s.name: s for s in ensure_taxonomy(db)}
        origins_by_id = {
            o.external_id: o for o in db.scalars(select(JobOrigin).where(JobOrigin.source_id == source.id))
        }
        candidates = list(
            db.scalars(
                select(Job).where(
                    Job.is_demo.is_(False),
                    or_(
                        func.lower(Job.company).in_({r.company.casefold() for r in rows}),
                        Job.fingerprint.in_({fingerprint(r.title, r.company, r.location) for r in rows}),
                        Job.id.in_({o.job_id for o in origins_by_id.values()}),
                    ),
                )
            )
        )
        jobs_by_id = {j.id: j for j in candidates}
        by_fingerprint = {j.fingerprint: j for j in candidates if j.fingerprint}
        seen = set()
        changed = []
        pending_origins = []
        for raw in rows:
            if raw.external_id in seen:
                continue
            seen.add(raw.external_id)
            cleaned_title, badge = clean_title_and_badge(raw.title)
            raw.title = cleaned_title
            if raw.posted_at and raw.posted_at < (utcnow() - timedelta(days=get_settings().job_max_age_days)):
                continue
            origin = origins_by_id.get(raw.external_id)
            fp = fingerprint(raw.title, raw.company, raw.location)
            job = jobs_by_id.get(origin.job_id) if origin else by_fingerprint.get(fp)
            if job is None:
                job = next(
                    (
                        j
                        for j in candidates
                        if j.source != "native"
                        and j.company.casefold() == raw.company.casefold()
                        and normalized(j.location) == normalized(raw.location)
                        and SequenceMatcher(None, normalized(j.title), normalized(raw.title)).ratio() >= 0.94
                    ),
                    None,
                )
            if job is None:
                job = Job(
                    source=source.kind,
                    external_id=f"{source.key}:{raw.external_id}",
                    is_demo=False,
                    active=True,
                    program_badge=badge,
                    last_seen_at=utcnow(),
                )
                db.add(job)
                stats["added"] += 1
                candidates.append(job)
            by_fingerprint[fp] = job
            job.program_badge = badge
            job.last_seen_at = utcnow()
            payload = raw.model_dump(exclude={"external_id", "attribution", "attribution_url"})
            content_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, default=str).encode()
            ).hexdigest()
            if job.content_hash != content_hash:
                if job.id:
                    stats["updated"] += 1
                for key, value in payload.items():
                    setattr(job, key, value)
                job.fingerprint = fingerprint(raw.title, raw.company, raw.location)
                job.content_hash, job.updated_at = content_hash, utcnow()
                names = extract_skills(raw.title + "\n" + raw.description, list(taxonomy))
                job.skills = [taxonomy[n] for n in names]
                job.skill_importance = importance(raw.description, names)
                job.experience_min = experience(raw.description)
                if not job.experience_level:
                    job.experience_level = infer_experience_level(raw.title, raw.description, job.experience_min)
                if not job.country:
                    job.country = infer_country(raw.location)
                changed.append(job)
            if not job.active and job not in changed:
                changed.append(job)
                stats["updated"] += 1
            job.active = True
            pending_origins.append((origin, job, raw))
        db.flush()
        for origin, job, raw in pending_origins:
            if not origin:
                origin = JobOrigin(job_id=job.id, source_id=source.id, external_id=raw.external_id)
                db.add(origin)
            origin.apply_url, origin.attribution, origin.attribution_url = (
                raw.apply_url,
                raw.attribution,
                raw.attribution_url,
            )
            origin.active, origin.seen_at = True, utcnow()
        for start in range(0, len(changed), 32):
            batch = changed[start : start + 32]
            vectors = encode_many([j.title + "\n" + j.description for j in batch])
            for job, vector in zip(batch, vectors, strict=True):
                job.embedding, job.embedding_model = (
                    vector,
                    get_settings().embedding_model if vector else None,
                )
        if changed:
            db.execute(delete(MatchResult).where(MatchResult.job_id.in_([j.id for j in changed])))
        if adapter.complete:
            origins = db.scalars(
                select(JobOrigin).where(JobOrigin.source_id == source.id, JobOrigin.active.is_(True))
            ).all()
            for origin in origins:
                if origin.external_id not in seen:
                    origin.active = False
                    db.flush()
                    other = db.scalar(
                        select(func.count(JobOrigin.id)).where(
                            JobOrigin.job_id == origin.job_id, JobOrigin.active.is_(True)
                        )
                    )
                    job = db.get(Job, origin.job_id)
                    if not other and job.active and job.source != "native":
                        job.active = False
                        stats["closed"] += 1
            max_age_cutoff = utcnow() - timedelta(days=get_settings().job_max_age_days)
            stale_jobs = db.scalars(
                select(Job).where(
                    Job.active.is_(True),
                    Job.source != "native",
                    func.coalesce(Job.posted_at, Job.created_at) < max_age_cutoff,
                )
            ).all()
            for stale in stale_jobs:
                stale.active = False
                stats["closed"] += 1
        stats["seen"], stats["complete"] = len(seen), adapter.complete
        source.status = run.status = "success" if adapter.complete else "partial"
        source.last_success_at, source.last_error = utcnow(), None
        source.stats = run.stats = stats
        if changed:
            db.add(WorkItem(kind="catalog", payload={"job_ids": [j.id for j in changed]}))
        db.commit()
    except Exception as error:
        db.rollback()
        source = db.get(IngestionSource, source.id)
        run = db.get(IngestionRun, run.id)
        source.status = run.status = "error"
        # Exception text can contain credential-bearing request URLs. Never persist it.
        source.last_error = run.error = (
            f"{type(error).__name__}: feed was not committed; check configuration and source availability"
        )
        log.warning("ingestion_failed source=%s error_type=%s", source.key, type(error).__name__)
    finally:
        http.close()
        source.next_run_at = utcnow() + timedelta(
            minutes=max(360 if source.kind == "remotive" else 60, source.interval_minutes)
        )
        run.finished_at = utcnow()
        db.commit()
    log.info(
        json.dumps(
            {"event": "ingestion_complete", "source": source.key, "status": source.status, "stats": stats}
        )
    )
    return {"status": source.status, **(source.stats if source.status != "error" else {})}
