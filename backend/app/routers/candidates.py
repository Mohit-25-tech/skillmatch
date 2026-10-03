from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db import get_db
from app.limits import limiter
from app.models import (
    Application,
    ApplicationEvent,
    Job,
    JobOrigin,
    LearningResource,
    MatchResult,
    Resume,
    Skill,
    User,
    WorkItem,
)
from app.repositories.catalog import job_public, resume_public
from app.schemas import MatchInput, StatusInput
from app.security import roles
from app.services.matching import match_public, save_match
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
    # Return useful structured scores immediately, even without a running worker.
    # Keep the request bounded; the durable worker enriches and scores the rest.
    visible = select(Job).where(Job.active.is_(True))
    if not get_settings().demo_mode:
        visible = visible.where(Job.is_demo.is_(False))
    for job in db.scalars(visible.order_by(Job.id.desc())):
        save_match(db, resume, job)
    db.add(WorkItem(kind="resume", payload={"resume_id": resume.id}))
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
    if not job or not job.active or (job.is_demo and not get_settings().demo_mode):
        raise HTTPException(404, "Job not found")
    result = save_match(db, resume, job)
    db.commit()
    return {**match_public(result, db), "job": job_public(job)}


@router.get("/matches")
def matches(
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=50),
    user: User = Depends(roles("candidate")),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.execute(
        select(MatchResult, Job)
        .join(Job)
        .options(selectinload(Job.skills))
        .where(
            MatchResult.resume_id
            == select(func.max(Resume.id)).where(Resume.user_id == user.id).scalar_subquery(),
            Job.active.is_(True),
            Job.is_demo.is_(False),
        )
        .order_by(MatchResult.score.desc(), Job.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    if not rows:
        return []
    origins = db.scalars(
        select(JobOrigin).where(JobOrigin.job_id.in_([job.id for _, job in rows]), JobOrigin.active.is_(True))
    ).all()
    origins_by_job: dict[int, list[JobOrigin]] = {}
    for origin in origins:
        origins_by_job.setdefault(origin.job_id, []).append(origin)
    missing = {skill for result, _ in rows for skill in result.missing}
    resources_by_skill: dict[str, list[dict]] = {}
    if missing:
        for resource, name in db.execute(
            select(LearningResource, Skill.name).join(Skill).where(Skill.name.in_(missing))
        ):
            resources_by_skill.setdefault(name, []).append(
                {"skill": name, "title": resource.title, "url": resource.url, "provider": resource.provider}
            )
    output = []
    for result, job in rows:
        data = match_public(result)
        data["suggestions"] = [item for skill in result.missing for item in resources_by_skill.get(skill, [])]
        output.append({**data, "job": job_public(job, origins=origins_by_job.get(job.id, []))})
    return output


@router.post("/applications", status_code=201)
def apply(body: MatchInput, user: User = Depends(roles("candidate")), db: Session = Depends(get_db)) -> dict:
    resume = own_resume(db, body.resume_id, user)
    job = db.get(Job, body.job_id)
    if not job or not job.active or (job.is_demo and not get_settings().demo_mode):
        raise HTTPException(404, "Job not found")
    save_match(db, resume, job)
    application = db.scalar(
        select(Application).where(Application.user_id == user.id, Application.job_id == job.id)
    )
    if application and application.status != "Saved":
        raise HTTPException(409, "You have already applied for this role")
    if not application:
        application = Application(user_id=user.id, job_id=job.id, resume_id=resume.id)
        db.add(application)
    application.status, application.resume_id = "Applied", resume.id
    db.flush()
    db.add(
        ApplicationEvent(
            application_id=application.id, actor_id=user.id, status="Applied", note="Application recorded"
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "You have already applied for this role") from None
    return {
        "id": application.id,
        "status": application.status,
        "tracking_only": job.source != "native",
        "apply_url": job.apply_url,
    }


@router.get("/applications")
def applications(
    user: User = Depends(roles("candidate", "recruiter", "admin")), db: Session = Depends(get_db)
) -> list[dict]:
    stmt = select(Application)
    if user.role == "candidate":
        stmt = stmt.where(Application.user_id == user.id)
    elif user.role == "recruiter":
        stmt = stmt.join(Job).where(Job.recruiter_id == user.id, Application.status != "Saved")
    rows = db.scalars(stmt.order_by(Application.created_at.desc()).limit(500)).all()
    output = []
    for row in rows:
        result = (
            db.scalar(
                select(MatchResult).where(
                    MatchResult.resume_id == row.resume_id, MatchResult.job_id == row.job_id
                )
            )
            if row.job_id
            else None
        )
        if row.job:
            job_data = job_public(row.job)
        else:
            company_str = row.custom_company or "Direct Application"
            initials = "".join(word[0] for word in company_str.split()[:2]).upper() or "AP"
            job_data = {
                "id": None,
                "title": row.custom_title or "Direct Role",
                "company": company_str,
                "location": "Direct / Custom",
                "employment_type": "Full-time",
                "description": "Manually tracked application",
                "apply_url": row.custom_url or "",
                "skills": [],
                "avatar": {
                    "initials": initials,
                    "background": "linear-gradient(135deg, hsl(210 60% 35%), hsl(260 65% 22%))",
                },
                "salary_disclosed": False,
                "is_demo": False,
                "active": True,
                "created_at": row.created_at.isoformat(),
            }
        output.append(
            {
                "id": row.id,
                "job": job_data,
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
    if application.status == "Saved":
        raise HTTPException(404, "Application not found")
    application.status = body.status
    db.add(
        ApplicationEvent(
            application_id=application.id, actor_id=user.id, status=body.status, note="Pipeline updated"
        )
    )
    db.commit()
    return {"status": application.status}


@router.get("/recruiter/candidates")
@router.get("/candidates")
def list_candidates(
    q: str = Query("", max_length=100),
    skill: str = Query("", max_length=100),
    user: User = Depends(roles("recruiter", "admin")),
    db: Session = Depends(get_db),
) -> list[dict]:
    latest_subq = (
        select(func.max(Resume.id).label("max_id"))
        .group_by(Resume.user_id)
        .subquery()
    )

    stmt = (
        select(User, Resume)
        .join(Resume, Resume.user_id == User.id)
        .where(
            User.role == "candidate",
            User.active.is_(True),
            Resume.id.in_(select(latest_subq.c.max_id)),
        )
    )

    if q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.name.ilike(term), Resume.text.ilike(term)))

    if skill.strip():
        stmt = stmt.where(Resume.skills.any(Skill.name.ilike(f"%{skill.strip()}%")))

    rows = db.execute(stmt).all()

    recruiter_jobs = db.scalars(
        select(Job).where(Job.recruiter_id == user.id, Job.active.is_(True))
    ).all()
    recruiter_job_ids = [j.id for j in recruiter_jobs]

    app_rows = db.scalars(
        select(Application)
        .join(Job)
        .where(Job.recruiter_id == user.id, Application.status != "Saved")
    ).all()
    applied_by_user: dict[int, list[dict]] = {}
    for app in app_rows:
        applied_by_user.setdefault(app.user_id, []).append({
            "application_id": app.id,
            "job_id": app.job_id,
            "job_title": app.job.title if app.job else "Direct Application",
            "status": app.status,
            "applied_at": app.created_at.isoformat(),
        })

    candidates_list = []
    for cand_user, resume in rows:
        score = None
        top_job_title = None
        if recruiter_job_ids:
            top_match = db.scalar(
                select(MatchResult)
                .join(Job, Job.id == MatchResult.job_id)
                .where(
                    MatchResult.resume_id == resume.id,
                    MatchResult.job_id.in_(recruiter_job_ids),
                )
                .order_by(MatchResult.score.desc())
                .limit(1)
            )
            if top_match:
                score = round(top_match.score, 1)
                top_job = db.get(Job, top_match.job_id)
                top_job_title = top_job.title if top_job else None

        if score is None:
            top_match = db.scalar(
                select(MatchResult)
                .join(Job, Job.id == MatchResult.job_id)
                .where(
                    MatchResult.resume_id == resume.id,
                    Job.active.is_(True),
                )
                .order_by(MatchResult.score.desc())
                .limit(1)
            )
            if top_match:
                score = round(top_match.score, 1)
                top_job = db.get(Job, top_match.job_id)
                top_job_title = top_job.title if top_job else None

        skill_names = [s.name for s in resume.skills]
        prefs = cand_user.preferences or {}
        preferred_roles = prefs.get("preferred_roles", [])
        headline = (
            ", ".join(preferred_roles)
            if preferred_roles
            else (f"{skill_names[0]} Specialist" if skill_names else "Candidate")
        )

        clean_lines = [
            line.strip()
            for line in resume.text.splitlines()
            if line.strip() and len(line.strip()) > 20 and not line.strip().startswith("#")
        ]
        snippet = clean_lines[0] if clean_lines else (resume.text[:180] + "...")

        candidates_list.append({
            "id": cand_user.id,
            "name": cand_user.name,
            "email": cand_user.email,
            "headline": headline,
            "experience_years": resume.experience_years or 3.0,
            "skills": skill_names,
            "resume_id": resume.id,
            "resume_filename": resume.filename,
            "resume_text": resume.text,
            "snippet": snippet,
            "match_score": score,
            "matched_job_title": top_job_title,
            "applications": applied_by_user.get(cand_user.id, []),
            "created_at": cand_user.created_at.isoformat(),
        })

    candidates_list.sort(key=lambda c: (c["match_score"] or 0, c["experience_years"] or 0), reverse=True)
    return candidates_list

