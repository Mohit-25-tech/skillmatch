import hashlib
import re
from datetime import timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, object_session

from app.config import get_settings
from app.models import IngestionSource, Job, JobOrigin, MatchResult, Resume, Skill, utcnow
from app.services.nl_search import coerce_bool

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "her", "here",
    "hers", "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "its", "itself",
    "let's", "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "shouldn't", "so", "some", "such",
    "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "were", "weren't", "what", "when", "where", "which",
    "while", "who", "whom", "why", "with", "won't", "would", "wouldn't", "you", "your", "yours", "yourself", "yourselves"
}


def get_skills(db: Session, names: list[str]) -> list[Skill]:
    from app.services.taxonomy import ALIASES, ensure_taxonomy

    canonical = {s.name.casefold(): s.name for s in ensure_taxonomy(db)}
    names = list(
        dict.fromkeys(
            canonical.get(ALIASES.get(name.casefold(), name).casefold(), ALIASES.get(name.casefold(), name))
            for name in names
        )
    )
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
    db: Session,
    query: str,
    location: str,
    kind: str,
    page: int,
    size: int,
    owner: int | None = None,
    cursor: int | None = None,
    min_match: float = 0,
    resume_id: int | None = None,
    days: int | None = None,
    sort: str = "recent",
    experience_level: str | None = None,
    remote: bool | None = None,
    salary_disclosed: bool | None = None,
    country: str | None = None,
) -> tuple[list[Job], int]:
    stmt = select(Job).where(Job.active.is_(True))
    if not get_settings().demo_mode:
        stmt = stmt.where(Job.is_demo.is_(False))
    effective_days = days if (days is not None and days > 0) else get_settings().job_max_age_days
    if effective_days:
        cutoff = utcnow() - timedelta(days=effective_days)
        stmt = stmt.where(func.coalesce(Job.posted_at, Job.created_at) >= cutoff)
    if min_match > 0:
        if resume_id is None:
            return [], 0
        stmt = stmt.join(MatchResult, MatchResult.job_id == Job.id).where(
            MatchResult.resume_id == resume_id, MatchResult.score >= min_match
        )
    tokens: list[str] = []
    if query:
        raw_tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9+#]+", query)]
        tokens = [t for t in raw_tokens if t not in STOP_WORDS]
        if not tokens and raw_tokens:
            tokens = raw_tokens

        def token_match_clause(t: str):
            escaped = t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            return or_(
                Job.title.ilike(pattern, escape="\\"),
                Job.company.ilike(pattern, escape="\\"),
                Job.description.ilike(pattern, escape="\\"),
                Job.skills.any(Skill.name.ilike(pattern, escape="\\")),
            )

        if tokens:
            if len(tokens) <= 3:
                stmt = stmt.where(and_(*[token_match_clause(t) for t in tokens]))
            else:
                stmt = stmt.where(or_(*[token_match_clause(t) for t in tokens]))
    if location:
        loc_raw = [p.strip() for p in re.findall(r"[A-Za-z]+", location) if len(p.strip()) > 1]
        loc_tokens = [t for t in loc_raw if t.lower() not in {"in", "at", "the", "and"}] or loc_raw
        if loc_tokens:
            stmt = stmt.where(or_(*[Job.location.ilike(f"%{t}%") for t in loc_tokens]))
    if kind:
        stmt = stmt.where(Job.employment_type == kind)
    if experience_level:
        stmt = stmt.where(Job.experience_level == experience_level.lower())
    remote_val = coerce_bool(remote)
    if remote_val is not None:
        stmt = stmt.where(Job.remote.is_(remote_val))
    if salary_disclosed is not None:
        if salary_disclosed:
            stmt = stmt.where(or_(Job.salary_min.is_not(None), Job.salary_max.is_not(None)))
        else:
            stmt = stmt.where(Job.salary_min.is_(None), Job.salary_max.is_(None))
    if country:
        c_low = country.strip().lower()
        if c_low in {"india + remote worldwide", "india + remote", "india_remote"}:
            stmt = stmt.where(or_(Job.country.ilike("%India%"), Job.remote.is_(True)))
        else:
            stmt = stmt.where(Job.country.ilike(f"%{country}%"))
    if owner is not None:
        stmt = stmt.where(Job.recruiter_id == owner)
    count = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    if cursor is not None:
        stmt = stmt.where(Job.id < cursor)

    if sort == "relevance" and (query or resume_id):
        all_candidates = list(db.scalars(stmt.limit(200)).all())
        if all_candidates:
            query_vector = None
            if query and get_settings().semantic_enabled:
                from app.services.embeddings import encode_many

                q_vecs = encode_many([query])
                if q_vecs and q_vecs[0] is not None:
                    query_vector = q_vecs[0]

            def score_job(j: Job) -> float:
                score = 0.0
                j_text = f"{j.title} {j.company} {j.description or ''}".casefold()
                for tok in tokens:
                    if tok in j.title.casefold():
                        score += 3.0
                    elif any(tok in s.name.casefold() for s in j.skills):
                        score += 2.0
                    elif tok in j_text:
                        score += 1.0
                if query_vector and j.embedding:
                    from app.services.embeddings import cosine

                    score += (cosine(query_vector, j.embedding) / 100.0) * 5.0
                return score

            all_candidates.sort(key=score_job, reverse=True)
            offset = 0 if cursor is not None else (page - 1) * size
            jobs = all_candidates[offset : offset + size]
            return jobs, count

    order_clause = (
        [func.coalesce(Job.posted_at, Job.created_at).desc(), Job.id.desc()]
        if sort == "recent"
        else [Job.id.desc()]
    )
    jobs = db.scalars(
        stmt.order_by(*order_clause).offset(0 if cursor is not None else (page - 1) * size).limit(size)
    ).all()
    return list(jobs), count


def job_public(job: Job, *, origins: list[JobOrigin] | None = None) -> dict:
    db = object_session(job)
    origins = (
        origins
        if origins is not None
        else (
            db.scalars(select(JobOrigin).where(JobOrigin.job_id == job.id, JobOrigin.active.is_(True))).all()
            if db
            else []
        )
    )
    hue = int(hashlib.sha256(job.company.casefold().encode()).hexdigest()[:8], 16) % 360
    return {
        "avatar": {
            "initials": "".join(word[0] for word in job.company.split()[:2]).upper(),
            "background": f"linear-gradient(135deg, hsl({hue} 60% 35%), hsl({(hue + 50) % 360} 65% 22%))",
        },
        "source": db.get(IngestionSource, origins[0].source_id).kind if origins else job.source,
        "is_demo": job.is_demo,
        "remote": job.remote,
        "program_badge": getattr(job, "program_badge", None),
        "apply_url": origins[0].apply_url if origins else job.apply_url,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "last_seen_at": job.last_seen_at.isoformat() if getattr(job, "last_seen_at", None) else None,
        "salary_currency": job.salary_currency,
        "salary_interval": job.salary_interval,
        "salary_disclosed": job.salary_min is not None or job.salary_max is not None,
        "sources": [
            {"name": o.attribution, "url": o.attribution_url, "apply_url": o.apply_url} for o in origins
        ],
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "country": getattr(job, "country", None),
        "experience_level": getattr(job, "experience_level", None),
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
        "is_primary": getattr(resume, "is_primary", True),
        "parse_warnings": getattr(resume, "parse_warnings", []) or [],
    }
