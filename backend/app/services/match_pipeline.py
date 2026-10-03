"""Compute coverage across the catalog, including historical resumes."""

import logging
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import engine
from app.models import Job, MatchResult, Resume
from app.services.embeddings import encode_many
from app.services.matching import experience, save_match
from app.services.parsing import extract_skills
from app.services.taxonomy import ensure_taxonomy

log = logging.getLogger(__name__)


def match_resume(
    db: Session, resume: Resume, only_missing: bool = False, job_ids: list[int] | None = None
) -> int:
    taxonomy = ensure_taxonomy(db)
    names = extract_skills(resume.text, [s.name for s in taxonomy])
    resume.skills = [s for s in taxonomy if s.name in names]
    if resume.embedding is None or resume.embedding_model != get_settings().embedding_model:
        resume.embedding = encode_many([resume.text])[0]
        resume.embedding_model = get_settings().embedding_model if resume.embedding is not None else None
    resume.experience_years = experience(resume.text)
    existing = (
        set(db.scalars(select(MatchResult.job_id).where(MatchResult.resume_id == resume.id)))
        if only_missing
        else set()
    )
    count = 0
    query = select(Job).where(Job.active.is_(True))
    if not get_settings().demo_mode:
        query = query.where(Job.is_demo.is_(False))
    if job_ids is not None:
        query = query.where(Job.id.in_(job_ids))
    jobs = db.scalars(query).all()
    total = len(jobs)
    BATCH_SIZE = 50
    for i in range(0, total, BATCH_SIZE):
        batch = jobs[i : i + BATCH_SIZE]
        for job in batch:
            if job.id not in existing:
                save_match(db, resume, job)
                count += 1
        db.commit()
        log.info(
            "match_resume: scored %d/%d jobs for resume %d",
            min(i + len(batch), total),
            total,
            resume.id,
        )
    from app.services.product import create_alerts

    create_alerts(db, resume)
    db.commit()
    return count


def run_resume_matching(resume_id: int, bind=engine) -> None:
    with Session(bind, expire_on_commit=False) as db:
        resume = db.get(Resume, resume_id)
        if resume:
            match_resume(db, resume)


def reindex_all(db: Session, only_missing: bool = False, job_ids: list[int] | None = None) -> int:
    latest = select(func.max(Resume.id)).group_by(Resume.user_id)
    return sum(
        match_resume(db, resume, only_missing, job_ids)
        for resume in db.scalars(select(Resume).where(Resume.id.in_(latest))).all()
    )


if __name__ == "__main__":
    with Session(engine) as session:
        from app.services.enrichment import embed_catalog

        embed_catalog(session)
        print(f"Computed {reindex_all(session)} latest-resume/job matches")
        session.commit()
