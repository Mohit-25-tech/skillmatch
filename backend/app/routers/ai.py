"""AI router: natural-language search, career assistant chat, why-match narratives, tailoring, and skill extraction."""

import json
from collections.abc import Generator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Job, User
from app.repositories.catalog import job_public, jobs_page
from app.security import current_user, optional_user
from app.services.assistant import CareerAssistant
from app.services.matching import calculate_match
from app.services.narrative import generate_why_match_narrative
from app.services.nl_search import parse_nl_query
from app.services.product import latest_resume
from app.services.retrieval import cross_encoder_rerank
from app.services.skill_extraction import extract_fallback_skills
from app.services.tailoring import generate_cover_letter, tailor_resume

router = APIRouter(prefix="/ai", tags=["AI & Career Assistant"])


class NLSearchInput(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)


class WhyMatchInput(BaseModel):
    job_id: int


class TailorResumeInput(BaseModel):
    job_id: int


class CoverLetterInput(BaseModel):
    job_id: int


class SkillExtractInput(BaseModel):
    text: str = Field(..., min_length=3, max_length=15000)


class ChatInput(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class RerankInput(BaseModel):
    query: str
    candidates: list[dict[str, Any]]
    top_k: int = 50


@router.post("/nl-search")
def natural_language_search(payload: NLSearchInput, db: Session = Depends(get_db)):
    """Convert natural-language query into structured filters and execute job search."""
    parsed = parse_nl_query(payload.query)
    jobs, total = jobs_page(
        db,
        query=parsed.get("q", ""),
        location="",
        kind="all",
        page=1,
        size=payload.limit,
        country=parsed.get("country"),
        remote=parsed.get("remote"),
        experience_level=parsed.get("experience_level"),
        salary_disclosed=parsed.get("salary_disclosed", False),
    )
    return {
        "parsed_filters": parsed,
        "total": total,
        "items": [job_public(j) for j in jobs],
    }


@router.post("/why-match")
def explain_why_match(
    payload: WhyMatchInput,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Generate grounded 'Why this match' narrative from verified breakdown."""
    job = db.get(Job, payload.job_id)
    if not job or not job.active:
        raise HTTPException(404, "Job not found")

    resume = latest_resume(db, user.id)
    if not resume:
        raise HTTPException(400, "Please upload a resume first to evaluate matches")

    match = calculate_match(resume, job)
    components = match.get("components", {})

    narrative = generate_why_match_narrative(
        job_title=job.title,
        company=job.company,
        match_score=match.get("score", 0.0),
        matched_skills=match.get("matched_skills", []),
        missing_skills=match.get("missing_skills", []),
        candidate_exp=resume.experience_years,
        required_exp=job.experience_min,
        semantic_score=components.get("semantic", {}).get("score"),
    )
    return narrative


@router.post("/tailor-resume")
def get_resume_tailoring(
    payload: TailorResumeInput,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Generate tailored resume suggestions with diff view strictly grounded in resume text."""
    job = db.get(Job, payload.job_id)
    if not job or not job.active:
        raise HTTPException(404, "Job not found")

    resume = latest_resume(db, user.id)
    if not resume or not resume.text:
        raise HTTPException(400, "Please upload a resume first")

    match = calculate_match(resume, job)
    return tailor_resume(
        resume_text=resume.text,
        job_title=job.title,
        company=job.company,
        matched_skills=match.get("matched_skills", []),
        missing_skills=match.get("missing_skills", []),
    )


@router.post("/cover-letter")
def get_cover_letter(
    payload: CoverLetterInput,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Generate targeted cover letter grounded in candidate resume without fabrications."""
    job = db.get(Job, payload.job_id)
    if not job or not job.active:
        raise HTTPException(404, "Job not found")

    resume = latest_resume(db, user.id)
    if not resume or not resume.text:
        raise HTTPException(400, "Please upload a resume first")

    match = calculate_match(resume, job)
    return generate_cover_letter(
        resume_text=resume.text,
        job_title=job.title,
        company=job.company,
        job_description=job.description,
        matched_skills=match.get("matched_skills", []),
    )


@router.post("/extract-skills")
def extract_novel_skills(payload: SkillExtractInput):
    """Extract and strictly validate emerging technical skills from text outside taxonomy."""
    skills = extract_fallback_skills(payload.text)
    return {"skills": skills, "count": len(skills)}


@router.post("/chat")
def career_assistant_chat(
    payload: ChatInput,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Synchronous chat with Career Assistant with tool calling and citations."""
    resume = latest_resume(db, user.id)
    assistant = CareerAssistant(db, user, resume)
    return assistant.process_message(payload.message)


@router.get("/chat/stream")
def career_assistant_stream(
    message: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """SSE Streaming chat with Career Assistant."""
    resume = latest_resume(db, user.id)
    assistant = CareerAssistant(db, user, resume)

    def event_stream() -> Generator[str, None, None]:
        for event in assistant.stream_message(message):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/assistant/context")
def assistant_context(
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
):
    """Provide real-time candidate profile, top matches, and dynamic suggested prompts."""
    if not user:
        return {
            "candidate_name": "Candidate",
            "has_resume": False,
            "resume_filename": None,
            "experience_years": 0,
            "top_skills": [],
            "top_matches": [],
            "suggested_prompts": [
                "Upload your resume to get matched",
                "Search remote software engineering jobs",
                "How do I build an ATS-friendly resume?",
                "What tech skills are most in-demand?",
            ],
        }

    resume = latest_resume(db, user.id)
    top_matches = []
    top_missing_skill = ""
    if resume:
        from app.models import MatchResult
        rows = list(
            db.execute(
                select(MatchResult, Job)
                .join(Job, MatchResult.job_id == Job.id)
                .where(MatchResult.resume_id == resume.id, Job.active.is_(True))
                .order_by(MatchResult.score.desc())
                .limit(3)
            ).all()
        )
        for mr, job in rows:
            top_matches.append({
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "score": mr.score,
                "confidence": (mr.components or {}).get("confidence_label", "High confidence"),
            })
            if not top_missing_skill and mr.missing:
                top_missing_skill = mr.missing[0]

    # Dynamic suggested prompts (B6)
    suggested_prompts = []
    if resume:
        suggested_prompts.append("Search remote Python internships")
        if top_matches:
            top_job = top_matches[0]
            suggested_prompts.append(f"Explain my match for job #{top_job['job_id']}")
        else:
            suggested_prompts.append("What jobs best match my skills?")
        if top_missing_skill:
            suggested_prompts.append(f"How do I learn {top_missing_skill}?")
        else:
            suggested_prompts.append("How do I learn Docker?")
        suggested_prompts.append("Review my resume strengths")
    else:
        suggested_prompts.append("Upload your resume to get matched")
        suggested_prompts.append("Search remote software engineering jobs")
        suggested_prompts.append("How do I build an ATS-friendly resume?")
        suggested_prompts.append("What tech skills are most in-demand?")

    top_skills: list[str] = []
    if resume:
        try:
            top_skills = [getattr(s, "name", str(s)) for s in (resume.skills or [])[:6]]
        except Exception:
            top_skills = []

    return {
        "candidate_name": user.name,
        "has_resume": bool(resume),
        "resume_filename": resume.filename if resume else None,
        "experience_years": resume.experience_years if resume else 0,
        "top_skills": top_skills,
        "top_matches": top_matches,
        "suggested_prompts": suggested_prompts,
    }


@router.get("/chat/history")
def get_chat_history(
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
):
    """Retrieve candidate's conversation history."""
    if not user:
        return {"items": []}
    from app.models import ChatMessage
    messages = list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.user_id == user.id)
            .order_by(ChatMessage.id.asc())
            .limit(50)
        ).all()
    )
    return {
        "items": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "citations": m.citations or [],
                "tool_calls": m.tool_calls or [],
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ]
    }


@router.delete("/chat/history")
def clear_chat_history(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Clear candidate's conversation history for a fresh session."""
    from sqlalchemy import delete
    from app.models import ChatMessage
    db.execute(delete(ChatMessage).where(ChatMessage.user_id == user.id))
    db.commit()
    return {"ok": True, "message": "Chat history cleared."}


@router.post("/rerank")
def rerank_candidates(payload: RerankInput):
    """Rerank candidates using cross-encoder or lexical-semantic ranking."""
    reranked = cross_encoder_rerank(payload.query, payload.candidates, top_k=payload.top_k)
    return {"items": reranked, "count": len(reranked)}

