from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Application, Job, MatchResult, Resume, User, WorkItem, utcnow
from app.repositories.catalog import get_skills, job_public, jobs_page
from app.schemas import JobInput
from app.security import optional_user, roles
from app.services.enrichment import enrich_native
from app.services.matching import match_public, save_match
from app.services.nl_search import coerce_bool
from app.services.product import latest_resume

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("")
def list_jobs(
    q: str = Query("", max_length=100),
    location: str = Query("", max_length=100),
    kind: str = "",
    experience_level: str | None = Query(None, max_length=30),
    remote: bool | None = Query(None),
    salary_disclosed: bool | None = Query(None),
    country: str | None = Query(None, max_length=60),
    days: int | None = Query(None, ge=1, le=365),
    sort: str = Query("recent"),
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=50),
    cursor: int | None = Query(None, ge=1),
    min_match: float = Query(0, ge=0, le=100),
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> dict:
    resume = latest_resume(db, user.id) if user and user.role == "candidate" else None
    jobs, total = jobs_page(
        db,
        q,
        location,
        kind,
        page,
        size,
        cursor=cursor,
        min_match=min_match,
        resume_id=resume.id if resume else None,
        days=days,
        sort=sort,
        experience_level=experience_level,
        remote=coerce_bool(remote),
        salary_disclosed=salary_disclosed,
        country=country,
    )
    items = [personalized(db, job, resume, user) for job in jobs]
    db.commit()
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "next_cursor": jobs[-1].id if len(jobs) == size else None,
        "requires_resume": bool(user and user.role == "candidate" and not resume),
    }


@router.get("/mine")
def mine(user: User = Depends(roles("recruiter", "admin")), db: Session = Depends(get_db)) -> dict:
    jobs, total = jobs_page(db, "", "", "", 1, 200, owner=user.id)
    return {"items": [job_public(j) for j in jobs], "total": total}


@router.get("/{job_id}")
def detail(job_id: int, user: User | None = Depends(optional_user), db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if not job or not job.active or (job.is_demo and not get_settings().demo_mode):
        raise HTTPException(404, "Job not found")
    resume = latest_resume(db, user.id) if user and user.role == "candidate" else None
    output = personalized(db, job, resume, user)
    db.commit()
    return output


@router.post("", status_code=201)
def create(
    body: JobInput, user: User = Depends(roles("recruiter", "admin")), db: Session = Depends(get_db)
) -> dict:
    job = Job(**body.model_dump(exclude={"skills"}), recruiter_id=user.id, skills=get_skills(db, body.skills))
    job.posted_at = utcnow()
    job.active = True
    job.is_demo = False
    enrich_native(db, job)
    db.add(job)
    db.flush()
    # Immediate scoring against latest candidate resumes so candidate matches and dashboard show this job right away
    latest_subq = select(func.max(Resume.id).label("max_id")).group_by(Resume.user_id).subquery()
    for resume in db.scalars(select(Resume).where(Resume.id.in_(select(latest_subq.c.max_id)))).all():
        save_match(db, resume, job)
    db.add(WorkItem(kind="catalog", payload={"job_ids": [job.id]}))
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
    enrich_native(db, job)
    db.add(WorkItem(kind="catalog", payload={"job_ids": [job.id]}))
    db.execute(delete(MatchResult).where(MatchResult.job_id == job.id))
    db.commit()
    return job_public(job)


@router.delete("/{job_id}", status_code=204)
def remove(
    job_id: int, user: User = Depends(roles("recruiter", "admin")), db: Session = Depends(get_db)
) -> None:
    owned_job(job_id, user, db).active = False
    db.commit()


def personalized(db, job, resume, user):
    output = job_public(job)
    if user and user.role == "candidate":
        output["saved"] = (
            db.scalar(
                select(Application.id).where(Application.user_id == user.id, Application.job_id == job.id)
            )
            is not None
        )
    if resume:
        result = db.scalar(
            select(MatchResult).where(MatchResult.resume_id == resume.id, MatchResult.job_id == job.id)
        ) or save_match(db, resume, job)
        match_dict = match_public(result, db)
        output["match"] = match_dict
        output["score"] = result.score
        output["confidence"] = match_dict.get("confidence")
        output["confidence_label"] = match_dict.get("confidence_label")
    else:
        output["match"], output["score"], output["confidence"], output["confidence_label"] = None, None, None, None
    return output
