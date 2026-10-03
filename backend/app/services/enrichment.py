"""Native job skill enrichment is immediate; embeddings run in the worker."""

import logging
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Job, MatchResult, Resume
from app.services.embeddings import encode_many
from app.services.matching import experience, importance
from app.services.parsing import extract_skills
from app.services.taxonomy import ensure_taxonomy

log = logging.getLogger(__name__)


def enrich_native(db: Session, job: Job) -> None:
    job.remote = bool(job.remote or "remote" in (job.location or "").casefold())
    taxonomy = {s.name: s for s in ensure_taxonomy(db)}
    names = set(extract_skills(job.title + "\n" + job.description, list(taxonomy))) | {
        s.name for s in job.skills
    }
    job.skills = [taxonomy[name] for name in sorted(names) if name in taxonomy]
    job.skill_importance = importance(job.description, list(names))
    job.experience_min = experience(job.description)
    from app.ingestion.normalization import infer_country, infer_experience_level

    if not job.experience_level:
        job.experience_level = infer_experience_level(job.title, job.description, job.experience_min)
    if not job.country:
        job.country = infer_country(job.location)
    job.embedding, job.embedding_model = None, None
    job.embedding_version = get_settings().embedding_version


def embed_catalog(db: Session, job_ids: list[int] | None = None, force: bool = False) -> int:
    settings = get_settings()
    stmt = select(Job).where(Job.active.is_(True))
    if job_ids is not None:
        stmt = stmt.where(Job.id.in_(job_ids))
    if not force:
        stmt = stmt.where(
            (Job.embedding.is_(None))
            | (Job.embedding_model != settings.embedding_model)
            | (Job.embedding_version != settings.embedding_version)
        )
    rows = list(db.scalars(stmt).all())
    log.info(
        "embed_catalog processing %d jobs (model=%s, v=%d)",
        len(rows),
        settings.embedding_model,
        settings.embedding_version,
    )
    count = 0
    for start in range(0, len(rows), 32):
        batch = rows[start : start + 32]
        vectors = encode_many([f"{j.title}\n{j.description}" for j in batch])
        for job, vector in zip(batch, vectors, strict=True):
            if vector is not None:
                db.execute(delete(MatchResult).where(MatchResult.job_id == job.id))
                job.embedding = vector
                job.embedding_model = settings.embedding_model
                job.embedding_version = settings.embedding_version
                count += 1
        db.commit()
    db.flush()
    return count


def reembed_all(db: Session) -> dict[str, int]:
    """CLI/admin utility: re-embed all jobs, resumes, and recalculate match scores."""
    settings = get_settings()
    log.info(
        "reembed_all starting with provider=%s model=%s v=%d",
        settings.embed_provider,
        settings.embedding_model,
        settings.embedding_version,
    )
    jobs_count = embed_catalog(db, force=True)

    resumes = list(db.scalars(select(Resume)).all())
    res_count = 0
    for r in resumes:
        if r.text:
            vecs = encode_many([r.text])
            if vecs and vecs[0] is not None:
                r.embedding = vecs[0]
                r.embedding_model = settings.embedding_model
                r.embedding_version = settings.embedding_version
                res_count += 1
    db.commit()

    from app.services.match_pipeline import reindex_all
    from app.services.retrieval import index_job_chunks, index_resume_chunks

    job_chunks_count = 0
    active_jobs = list(db.scalars(select(Job).where(Job.active.is_(True))).all())
    for j in active_jobs:
        job_chunks_count += index_job_chunks(db, j)
    db.commit()

    resume_chunks_count = 0
    for r in resumes:
        if r.text:
            resume_chunks_count += index_resume_chunks(db, r)
    db.commit()

    matches_count = reindex_all(db, only_missing=False)
    log.info(
        "reembed_all completed: %d jobs, %d resumes, %d job chunks, %d resume chunks, %d matches reindexed",
        jobs_count,
        res_count,
        job_chunks_count,
        resume_chunks_count,
        matches_count,
    )
    return {
        "jobs_embedded": jobs_count,
        "resumes_embedded": res_count,
        "job_chunks_indexed": job_chunks_count,
        "resume_chunks_indexed": resume_chunks_count,
        "matches_reindexed": matches_count,
    }
