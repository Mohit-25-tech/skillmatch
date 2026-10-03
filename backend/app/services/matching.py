"""Explainable scores; unavailable components do not silently count as zero."""

import math
import re

from pgvector.sqlalchemy import Vector
from sqlalchemy import cast, literal, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Job, LearningResource, MatchResult, Resume, Skill, User


def experience(text: str) -> float | None:
    values = re.findall(
        r"\b(\d{1,2})(?:\s*[-–]\s*\d{1,2})?\+?\s+years?\s+(?:of\s+)?(?:professional\s+)?experience\b",
        text,
        re.I,
    )
    return float(max(map(int, values))) if values else None


def importance(text: str, names: list[str]) -> dict:
    result = dict.fromkeys(names, "required")
    optional = False
    from app.services.parsing import extract_skills

    for line in text.splitlines():
        if re.search(r"nice.to.have|preferred qualifications|bonus|optional", line, re.I):
            optional = True
        elif re.search(r"required|minimum qualifications|must.have", line, re.I):
            optional = False
        if optional:
            for name in extract_skills(line, names):
                result[name] = "nice-to-have"
    return result


def cosine(left, right) -> float:
    denominator = math.sqrt(sum(x * x for x in left) * sum(x * x for x in right))
    return (
        max(0.0, min(100.0, 100 * sum(a * b for a, b in zip(left, right, strict=True)) / denominator))
        if denominator
        else 0.0
    )


def calculate_match(
    resume: Resume, job: Job, preferences: dict | None = None, semantic_value: float | None = None
) -> dict:
    settings = get_settings()
    preferences = preferences or {}
    have = {s.name.casefold() for s in resume.skills}
    matched = sorted(s.name for s in job.skills if s.name.casefold() in have)
    missing = sorted(s.name for s in job.skills if s.name.casefold() not in have)
    weights = {
        s.name: 0.4 if (job.skill_importance or {}).get(s.name) == "nice-to-have" else 1.0 for s in job.skills
    }
    k = 2.0
    matched_weight = sum(weights[n] for n in matched)
    total_weight = sum(weights.values())
    keyword = 100.0 * matched_weight / (total_weight + k) if (total_weight + k) > 0 else 0.0
    semantic = semantic_value
    if (
        settings.semantic_enabled
        and semantic is None
        and resume.embedding is not None
        and job.embedding is not None
        and resume.embedding_model == job.embedding_model == settings.embedding_model
    ):
        semantic = cosine(resume.embedding, job.embedding)
    years = resume.experience_years if resume.experience_years is not None else experience(resume.text)
    if years is None and (
        getattr(job, "experience_level", None) in ("intern", "entry")
        or bool(re.search(r"\b(student|graduate|fresher|intern|undergraduate|b\.?tech|b\.?e)\b", resume.text, re.I))
    ):
        years = 0.0
    minimum = job.experience_min if job.experience_min is not None else experience(job.description)
    exp_level = getattr(job, "experience_level", None) or ("intern" if "intern" in job.title.casefold() else None)
    fit = None
    if years is not None:
        if years == 0:
            if exp_level in ("intern", "entry") or (minimum is not None and minimum <= 1.0):
                fit = 100.0
            elif minimum and minimum > 1.0:
                fit = max(25.0, round((0.5 / minimum) * 100, 1))
            else:
                fit = 100.0
        elif minimum:
            fit = min(100.0, (years / minimum) * 100)
    locations = preferences.get("locations", [])
    remote = preferences.get("remote_preference", "any")
    location = None
    if locations or remote != "any":
        location_ok = not locations or any(
            place.casefold() in (job.location or "").casefold() for place in locations
        )
        remote_ok = (
            remote == "any" or (remote == "remote" and job.remote) or (remote == "onsite" and not job.remote)
        )
        location = 100.0 if remote_ok and (location_ok or (remote == "remote" and job.remote)) else 0.0
    values = {"semantic": semantic, "skills": keyword, "experience": fit, "location": location}
    configured = dict(
        zip(
            values,
            [
                settings.match_semantic_weight,
                settings.match_skills_weight,
                settings.match_experience_weight,
                settings.match_location_weight,
            ],
        )
    )
    total = sum(configured[k] for k, v in values.items() if v is not None)
    is_high_confidence = len(job.skills) >= 3 and semantic is not None
    confidence = "high" if is_high_confidence else "low"
    confidence_label = "High confidence" if is_high_confidence else "Low confidence"
    components = {
        k: {
            "score": round(v, 1) if v is not None else None,
            "weight": round(configured[k] / total, 4) if v is not None and total else 0,
        }
        for k, v in values.items()
    }
    components["confidence"] = confidence
    components["confidence_label"] = confidence_label
    score = sum(v * configured[k] for k, v in values.items() if v is not None) / total if total else 0
    reasons = [
        f"{len(matched)} of {len(job.skills)} extracted skills matched (required skills carry more weight)."
    ]
    if semantic is not None:
        reasons.append(f"Semantic similarity: {semantic:.1f}%.")
    else:
        # Minimum evidence rule when semantic embedding is missing
        if len(matched) == 0:
            score = 0.0
        elif len(matched) < 2 or len(job.skills) < 2:
            score = min(score, 50.0)
        else:
            score = min(score, 65.0)
        reasons.append("Semantic embedding is missing for this job; score evaluated under minimum evidence rule.")
    if len(job.skills) < 3:
        reasons.append(f"Low confidence: job has {len(job.skills)} extracted skill(s) (>= 3 required for high confidence).")
    if fit is not None:
        if years == 0 and fit == 100.0:
            reasons.append("Fresher/student state: 0 years experience aligns with entry-level and internship requirements.")
        elif years is not None and minimum:
            reasons.append(f"Experience evidence: {years:g} years; job requests {minimum:g}.")
    if location is not None:
        reasons.append(
            "Location preferences match." if location else "Location or remote preference differs."
        )
    roles = preferences.get("preferred_roles", [])
    if roles and any(role.casefold() in job.title.casefold() for role in roles):
        reasons.append("This title matches a preferred role.")
    expectation = preferences.get("salary_expectation")
    if (
        expectation
        and job.salary_currency == preferences.get("salary_currency")
        and job.salary_interval == preferences.get("salary_interval")
        and job.salary_max is not None
    ):
        reasons.append(
            "Published salary can meet your expectation."
            if job.salary_max >= expectation
            else "Published maximum is below your salary expectation."
        )
    improvements = [
        f"If you have {name} experience, add a concrete project or accomplishment demonstrating it."
        for name in missing
    ]
    if years is None and minimum:
        improvements.append(
            "Clarify your years of relevant experience; experience fit is currently unavailable."
        )
    method = (
        "hybrid"
        if semantic is not None
        else ("structured" if fit is not None or location is not None else "keyword")
    )
    return dict(
        score=round(score, 1),
        confidence=confidence,
        confidence_label=confidence_label,
        semantic_score=round(semantic or 0, 1),
        keyword_score=round(keyword, 1),
        matched=matched,
        missing=missing,
        method=method,
        components=components,
        reasons=reasons,
        improvements=improvements,
    )


def save_match(db: Session, resume: Resume, job: Job) -> MatchResult:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    user = db.get(User, resume.user_id)
    semantic = None
    if (
        get_settings().semantic_enabled
        and db.bind.dialect.name == "postgresql"
        and resume.embedding is not None
        and job.embedding is not None
        and resume.embedding_model == job.embedding_model == get_settings().embedding_model
    ):
        distance = cast(Job.embedding, Vector(384)).cosine_distance(
            literal(list(resume.embedding), type_=Vector(384))
        )
        semantic = max(0, min(100, float(db.scalar(select((1 - distance) * 100).where(Job.id == job.id)))))
    values = calculate_match(resume, job, user.preferences if user else {}, semantic)
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    db_values = {k: v for k, v in values.items() if k not in {"confidence", "confidence_label"}}
    statement = insert(MatchResult).values(resume_id=resume.id, job_id=job.id, **db_values)
    statement = statement.on_conflict_do_update(
        index_elements=["resume_id", "job_id"], set_=db_values
    ).returning(MatchResult)
    # Browsing a job and the worker may score it simultaneously. Persist atomically.
    return db.scalar(statement, execution_options={"populate_existing": True})


def match_public(result: MatchResult, db: Session | None = None) -> dict:
    resources = []
    if db and result.missing:
        resources = db.execute(
            select(LearningResource, Skill.name).join(Skill).where(Skill.name.in_(result.missing))
        ).all()
    comp = result.components or {}
    confidence = comp.get("confidence", "high" if len(result.matched or []) >= 2 else "low")
    confidence_label = comp.get("confidence_label", "High confidence" if confidence == "high" else "Low confidence")
    return {
        **{
            key: getattr(result, key)
            for key in (
                "id",
                "resume_id",
                "job_id",
                "score",
                "semantic_score",
                "keyword_score",
                "matched",
                "missing",
                "method",
                "components",
                "reasons",
                "improvements",
            )
        },
        "confidence": confidence,
        "confidence_label": confidence_label,
        "suggestions": [
            {"skill": name, "title": r.title, "url": r.url, "provider": r.provider} for r, name in resources
        ],
    }
