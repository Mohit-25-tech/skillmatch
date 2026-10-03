from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Application, Job, MatchResult, Resume, Skill, User, job_skills
from app.repositories.catalog import job_public
from app.schemas import UserUpdate
from app.security import current_user, roles, user_public
from app.services.product import candidate_matches_summary

router = APIRouter(tags=["Analytics & administration"])


@router.get("/analytics")
def analytics(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    latest = select(func.max(Resume.id)).group_by(Resume.user_id)
    match_stmt = (
        select(MatchResult)
        .join(Job)
        .where(MatchResult.resume_id.in_(latest), Job.active.is_(True), Job.is_demo.is_(False))
    )
    app_stmt = select(Application).where(Application.status != "Saved")
    matches_count = 0
    average_score = 0.0
    if user.role == "candidate":
        summary = candidate_matches_summary(db, user.id)
        matches_count = summary["total_matches"]
        average_score = summary["average_score"]
        match_stmt = match_stmt.join(Resume).where(Resume.user_id == user.id)
        app_stmt = app_stmt.where(Application.user_id == user.id)
    elif user.role == "recruiter":
        match_stmt = match_stmt.where(Job.recruiter_id == user.id)
        app_stmt = app_stmt.join(Job).where(Job.recruiter_id == user.id)
    matches = list(db.scalars(match_stmt).all())
    if user.role != "candidate":
        matches_count = len(matches)
        average_score = round(sum(m.score for m in matches) / len(matches), 1) if matches else 0.0
    applications = list(db.scalars(app_stmt).all())
    demand = db.execute(
        select(Skill.name, func.count(job_skills.c.job_id))
        .join(job_skills)
        .join(Job, Job.id == job_skills.c.job_id)
        .where(Job.active.is_(True), Job.is_demo.is_(False))
        .group_by(Skill.name)
        .order_by(func.count(job_skills.c.job_id).desc())
        .limit(6)
    ).all()
    return {
        "matches": matches_count,
        "average_score": average_score,
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
            "jobs": db.scalar(select(func.count(Job.id)).where(Job.active.is_(True), Job.is_demo.is_(False))),
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
                .where(Job.active.is_(True), Job.is_demo.is_(False))
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


@router.post("/admin/re-embed")
def admin_reembed(user: User = Depends(roles("admin")), db: Session = Depends(get_db)) -> dict:
    from app.services.enrichment import reembed_all

    stats = reembed_all(db)
    return {"status": "ok", **stats}
