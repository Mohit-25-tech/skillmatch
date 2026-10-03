"""Career assistant chat engine with RAG over jobs and user resume, Pydantic tool args validation,
savepoints, isolated memory persistence, guardrails, and SSE streaming.
"""

import json
import logging
import re
import time
from collections.abc import Generator
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    Application,
    ChatMessage,
    Job,
    LearningResource,
    MatchResult,
    Resume,
    ResumeChunk,
    Skill,
    User,
)
from app.services.ai_provider import get_ai_provider
from app.services.embeddings import encode_many
from app.services.matching import calculate_match
from app.services.narrative import generate_why_match_narrative
from app.services.nl_search import coerce_bool, parse_nl_query_heuristic
from app.services.product import latest_resume
from app.services.retrieval import hybrid_search_jobs
from app.services.taxonomy import ALIASES
from app.services.vectorstore import get_vector_store

log = logging.getLogger(__name__)


class ToolResultList(list):
    """A list that also provides dictionary-like access to metadata for backward compatibility."""

    def __init__(self, iterable=None, **meta):
        super().__init__(iterable or [])
        self.__dict__.update(meta)

    def __getitem__(self, item):
        if isinstance(item, str):
            if item in self.__dict__:
                return self.__dict__[item]
            if item in {"jobs", "sections", "curated_resources"}:
                return list(self)
            if item == "count":
                return len(self)
            return None
        return super().__getitem__(item)

    def get(self, key: str, default: Any = None) -> Any:
        if key in self.__dict__:
            return self.__dict__[key]
        if key in {"jobs", "sections", "curated_resources"}:
            return list(self)
        if key == "count":
            return len(self)
        return default


# --- Tool Argument Validation Models ---


class SearchJobsArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    q: str = ""
    remote: bool | None = None
    experience_level: Literal["intern", "entry", "mid", "senior"] | None = None
    country: str | None = None
    limit: int = 10

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return {}
        d = dict(data)
        if "query" in d and not d.get("q"):
            d["q"] = d.pop("query")
        if "remote" in d:
            d["remote"] = coerce_bool(d["remote"])
        if "limit" in d:
            if d["limit"] is None or d["limit"] == "":
                d["limit"] = 10
            else:
                try:
                    d["limit"] = max(1, min(50, int(d["limit"])))
                except (ValueError, TypeError):
                    d["limit"] = 10
        if "experience_level" in d and d["experience_level"]:
            lvl = str(d["experience_level"]).lower().strip()
            if "intern" in lvl:
                d["experience_level"] = "intern"
            elif any(x in lvl for x in ("entry", "fresher", "junior", "graduate")):
                d["experience_level"] = "entry"
            elif "senior" in lvl or "lead" in lvl or "principal" in lvl:
                d["experience_level"] = "senior"
            elif "mid" in lvl:
                d["experience_level"] = "mid"
            else:
                d["experience_level"] = None
        return d


class RetrieveResumeContextArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query: str = ""
    top_k: int = 4

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return {}
        d = dict(data)
        val = d.get("top_k")
        if val is None or val == "":
            d["top_k"] = 4
        else:
            try:
                d["top_k"] = max(1, min(10, int(val)))
            except (ValueError, TypeError):
                d["top_k"] = 4
        return d


class GetJobDetailsArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    job_id: int

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return {"job_id": 0}
        d = dict(data)
        try:
            d["job_id"] = int(d.get("job_id", 0))
        except (ValueError, TypeError):
            d["job_id"] = 0
        return d


class ExplainMatchArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    job_id: int

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return {"job_id": 0}
        d = dict(data)
        try:
            d["job_id"] = int(d.get("job_id", 0))
        except (ValueError, TypeError):
            d["job_id"] = 0
        return d


class SuggestLearningArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    skill: str

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return {"skill": ""}
        d = dict(data)
        d["skill"] = str(d.get("skill") or d.get("query") or "").strip()
        return d


class AddToTrackerArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    job_id: int
    status: str = "Saved"
    notes: str = ""

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return {"job_id": 0}
        d = dict(data)
        try:
            d["job_id"] = int(d.get("job_id", 0))
        except (ValueError, TypeError):
            d["job_id"] = 0
        d["status"] = str(d.get("status") or "Saved")
        d["notes"] = str(d.get("notes") or "")
        return d


class AnalyzeSkillGapsArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    target_role: str | None = None


ASSISTANT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_skill_gaps",
            "description": "Analyze missing skills, gaps, and strengths across candidate's top scored jobs or for a target role. Call this when user asks what skills are missing in their resume, what they need to learn, or how to bridge gaps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_role": {
                        "type": "string",
                        "description": "Optional target role or domain (e.g. 'Machine Learning', 'Backend', 'Software Engineer').",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_resume_context",
            "description": "Retrieve relevant sections from candidate's uploaded resume using semantic search. Use whenever answering questions about candidate's background, skills, experience, or projects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Specific search query or skill to find in the resume.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of resume sections to retrieve (default: 4).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_jobs",
            "description": "Search active job openings by keyword, role, location, remote status, or seniority level using hybrid search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Keywords, job title, technology stack, or company name.",
                    },
                    "country": {
                        "type": "string",
                        "description": "Country filter, e.g. 'India' or 'United States'.",
                    },
                    "remote": {
                        "type": "boolean",
                        "description": "True to filter for remote roles only.",
                    },
                    "experience_level": {
                        "type": "string",
                        "enum": ["intern", "entry", "mid", "senior"],
                        "description": "Seniority: intern, entry, mid, senior.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of jobs to return (default: 10).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_job_details",
            "description": "Retrieve comprehensive details, description, and skill requirements for a specific job by its numeric ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "integer",
                        "description": "The numeric ID of the job.",
                    },
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_match",
            "description": "Explain why the candidate matches a specific job, including match score, matched skills, missing skills, and narrative analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "integer",
                        "description": "The numeric ID of the job.",
                    },
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_learning",
            "description": "Get verified free learning roadmaps and documentation resources for a technical skill, plus resume coverage context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill": {
                        "type": "string",
                        "description": "The technical skill to learn (e.g. 'Docker', 'FastAPI', 'PostgreSQL').",
                    },
                },
                "required": ["skill"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_tracker",
            "description": "Save a job to the candidate's Kanban application tracker or update its status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "integer",
                        "description": "The numeric ID of the job to save or update.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["Saved", "Applied", "Reviewing", "Interview", "Offer", "Rejected", "Hired"],
                        "description": "Kanban column status (default: 'Saved').",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes or reminders about this application.",
                    },
                },
                "required": ["job_id"],
            },
        },
    },
]


def tool_label(name: str) -> str:
    labels = {
        "analyze_skill_gaps": "Analyzing skill gaps across matches...",
        "retrieve_resume_context": "Searching your resume...",
        "search_jobs": "Searching jobs...",
        "get_job_details": "Fetching job details...",
        "explain_match": "Analyzing match breakdown...",
        "suggest_learning": "Looking up verified learning resources...",
        "add_to_tracker": "Updating application tracker...",
    }
    return labels.get(name, f"Executing {name}...")


def friendly_tool_error(name: str) -> str:
    messages = {
        "analyze_skill_gaps": "I couldn't analyze your skill gaps right now. Try checking your matches on the My Matches page.",
        "search_jobs": "I couldn't search jobs just now. Try again, or use Find jobs.",
        "retrieve_resume_context": "I couldn't access your resume details right now. Please try again or re-upload your resume.",
        "get_job_details": "I couldn't load the job details right now. Try again, or browse the role in Find jobs.",
        "explain_match": "I couldn't calculate the match breakdown right now. Please try again in a moment.",
        "suggest_learning": "I couldn't load learning resources right now. Try again later or search directly in Learning Path.",
        "add_to_tracker": "I couldn't update your application tracker right now. Try saving the job directly from its card.",
    }
    return messages.get(name, "I ran into a temporary issue processing that request. Please try again.")


class CareerAssistant:
    def __init__(self, db: Session, user: User, resume: Resume | None = None):
        self.db = db
        self.user = user
        if resume is None and user and getattr(user, "role", None) == "candidate":
            self.resume = latest_resume(db, user.id)
        else:
            self.resume = resume
        self.ai = get_ai_provider()
        self.settings = get_settings()

    # --- Tool Implementations ---

    def tool_analyze_skill_gaps(self, target_role: str | None = None) -> ToolResultList:
        """Aggregate missing skills and gaps across candidate's top matched jobs."""
        if not self.resume:
            self.resume = latest_resume(self.db, self.user.id)
        if not self.resume:
            return ToolResultList(
                [{"error": "No resume uploaded. Please upload a resume first."}],
                status="no_resume",
                error="No resume uploaded. Please upload a resume first.",
            )

        query = (
            select(MatchResult, Job)
            .join(Job, MatchResult.job_id == Job.id)
            .where(MatchResult.resume_id == self.resume.id, Job.active.is_(True))
            .order_by(MatchResult.score.desc())
            .limit(10)
        )
        matches = list(self.db.execute(query).all())

        from collections import Counter
        missing_counts = Counter()
        matched_counts = Counter()
        target_jobs = []

        for mr, job in matches:
            if target_role and (
                target_role.casefold() not in job.title.casefold()
                and target_role.casefold() not in job.description.casefold()
            ):
                continue
            target_jobs.append({
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "score": mr.score,
            })
            for s in (mr.missing or []):
                missing_counts[s] += 1
            for s in (mr.matched or []):
                matched_counts[s] += 1

        top_missing = [
            {"skill": skill, "job_count": count}
            for skill, count in missing_counts.most_common(6)
        ]
        top_strengths = [
            {"skill": skill, "job_count": count}
            for skill, count in matched_counts.most_common(6)
        ]

        results = {
            "candidate_skills": [s.name for s in (self.resume.skills or [])[:15]],
            "total_matched_jobs_analyzed": len(target_jobs) or len(matches),
            "top_missing_skills": top_missing,
            "top_strengths": top_strengths,
            "top_roles": target_jobs[:3],
        }
        return ToolResultList([results], status="ok", analysis=results)

    def tool_retrieve_resume_context(self, query: str = "", top_k: int = 4) -> ToolResultList:
        """Retrieve relevant sections from candidate's resume using vector search.
        
        Strict Privacy: Candidate can only access their own resume chunks.
        Resolved server-side from self.user, never from model-provided ids.
        """
        if self.user.role != "candidate":
            return ToolResultList(
                [{"error": "Resume retrieval is only available for candidate accounts."}],
                status="error",
                error="Resume retrieval is only available for candidate accounts.",
            )
        if not self.resume:
            self.resume = latest_resume(self.db, self.user.id)
        if not self.resume:
            return ToolResultList(
                [{"error": "No resume uploaded. Please upload a resume first."}],
                status="no_resume",
                error="No resume uploaded. Please upload a resume first.",
                message="No resume uploaded. Please upload a resume first.",
            )

        q_clean = (query or "").strip()
        if not q_clean:
            skills_text = ", ".join([s.name for s in self.resume.skills[:12]])
            sec = [
                {
                    "section": "Skills",
                    "citation": "[Resume: Skills]",
                    "text": f"Skills: {skills_text}. Documented experience: {self.resume.experience_years or 0} years.",
                    "score": 100.0,
                }
            ]
            return ToolResultList(sec, status="ok", sections=sec)

        q_vecs = encode_many([q_clean])
        hits: list[dict[str, Any]] = []
        if q_vecs and q_vecs[0] is not None:
            vstore = get_vector_store()
            hits = vstore.query(
                "resume_chunks",
                q_vecs[0],
                top_k=top_k,
                filter={"user_id": self.user.id},
            )

        if not hits:
            db_chunks = list(
                self.db.scalars(
                    select(ResumeChunk)
                    .where(
                        ResumeChunk.user_id == self.user.id,
                        ResumeChunk.text.ilike(f"%{q_clean}%"),
                    )
                    .limit(top_k)
                ).all()
            )
            hits = [
                {
                    "score": 50.0,
                    "metadata": {"section": c.section},
                    "document": c.text,
                }
                for c in db_chunks
            ]

        results = []
        for h in hits:
            sec = h.get("metadata", {}).get("section", "Summary")
            results.append({
                "section": sec,
                "citation": f"[Resume: {sec}]",
                "text": h.get("document", ""),
                "score": h.get("score", 0.0),
            })
        return ToolResultList(results, status="ok", sections=results)

    def tool_search_jobs(
        self,
        query: str = "",
        country: str | None = None,
        remote: bool | None = None,
        experience_level: str | None = None,
        limit: int = 10,
    ) -> ToolResultList:
        """Search active jobs matching query and filters with automatic filter relaxation."""
        parsed = parse_nl_query_heuristic(query)
        q_clean = parsed["q"]
        if remote is None and parsed["remote"] is not None:
            remote = parsed["remote"]
        if experience_level is None and parsed["experience_level"] is not None:
            experience_level = parsed["experience_level"]
        if country is None and parsed["country"] is not None:
            country = parsed["country"]

        filters = {
            "country": country,
            "remote": remote,
            "experience_level": experience_level,
        }
        jobs = hybrid_search_jobs(self.db, query_text=q_clean, limit=limit, filters=filters)
        relaxed_note = ""

        # Filter relaxation if 0 results: drop remote first, then level
        if not jobs and remote is True:
            relaxed_filters = {"country": country, "remote": None, "experience_level": experience_level}
            jobs = hybrid_search_jobs(self.db, query_text=q_clean, limit=limit, filters=relaxed_filters)
            if jobs:
                relaxed_note = f"No remote {q_clean or 'matching'} openings found; showing all locations."
                remote = None

        if not jobs and experience_level is not None:
            relaxed_filters = {"country": country, "remote": remote, "experience_level": None}
            jobs = hybrid_search_jobs(self.db, query_text=q_clean, limit=limit, filters=relaxed_filters)
            if jobs:
                relaxed_note = f"No {experience_level}-level openings found; showing openings across all experience levels."
                experience_level = None

        results = []
        for j in jobs:
            match_score = 0.0
            confidence = "Standard"
            top_missing: list[str] = []
            if self.resume:
                m = calculate_match(self.resume, j)
                match_score = m.get("score", 0.0)
                comp = m.get("components", {})
                confidence = comp.get("confidence_label", "Moderate confidence")
                missing = m.get("missing_skills") or m.get("missing", [])
                top_missing = missing[:2]

            results.append({
                "job_id": j.id,
                "citation": f"[Job #{j.id}]",
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "country": j.country,
                "remote": bool(j.remote),
                "experience_level": j.experience_level,
                "salary": f"{j.salary_min} - {j.salary_max} {j.salary_currency}" if j.salary_min else "Undisclosed",
                "match_score": match_score,
                "confidence": confidence,
                "missing_skills": top_missing,
            })

        return ToolResultList(
            results,
            jobs=results,
            count=len(results),
            relaxed_note=relaxed_note,
        )

    def tool_get_job_details(self, job_id: int) -> dict[str, Any]:
        """Retrieve full details for a specific active job."""
        job = self.db.get(Job, job_id)
        if not job or not job.active:
            return {"error": f"Job #{job_id} not found."}

        return {
            "job_id": job.id,
            "citation": f"[Job #{job.id}]",
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "country": job.country,
            "remote": bool(job.remote),
            "experience_level": job.experience_level,
            "employment_type": job.employment_type,
            "salary": f"{job.salary_min} - {job.salary_max} {job.salary_currency}" if job.salary_min else "Undisclosed",
            "description": (job.description or "")[:1500],
            "required_skills": [s.name for s in job.skills],
            "apply_url": job.apply_url or f"https://example.com/apply/{job.id}",
        }

    def tool_explain_match(self, job_id: int) -> dict[str, Any]:
        """Explain candidate match breakdown for a specific job."""
        job = self.db.get(Job, job_id)
        if not job or not job.active:
            return {"error": f"Job #{job_id} not found."}
        if not self.resume:
            return {"status": "no_resume", "error": "Upload a resume first to see match breakdowns."}

        match = calculate_match(self.resume, job)
        components = match.get("components", {})
        matched_skills = match.get("matched_skills") or match.get("matched", [])
        missing_skills = match.get("missing_skills") or match.get("missing", [])
        narrative = generate_why_match_narrative(
            job_title=job.title,
            company=job.company,
            match_score=match.get("score", 0.0),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            candidate_exp=self.resume.experience_years,
            required_exp=job.experience_min,
            semantic_score=components.get("semantic", {}).get("score"),
        )
        return {
            "job_id": job.id,
            "citation": f"[Job #{job.id}]",
            "title": job.title,
            "company": job.company,
            "score": match.get("score", 0.0),
            "confidence": components.get("confidence_label", "Moderate confidence"),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "narrative": narrative.get("narrative", ""),
        }

    def tool_suggest_learning(self, skill: str) -> ToolResultList:
        """Look up curated free learning resources and provide candidate resume context."""
        clean_skill = re.sub(r"[^\w\s\+\#\.\-]", "", skill).strip()
        canon = ALIASES.get(clean_skill.casefold(), clean_skill)

        query = (
            select(LearningResource)
            .join(Skill, LearningResource.skill_id == Skill.id)
            .where(or_(Skill.name.ilike(canon), Skill.name.ilike(f"%{clean_skill}%")))
            .limit(5)
        )
        resources = list(self.db.scalars(query).all())

        on_resume = False
        jobs_needing_skill = 0
        total_top_jobs = 0

        if self.resume:
            on_resume = any(clean_skill.casefold() in s.name.casefold() for s in self.resume.skills) or (
                self.resume.text and clean_skill.casefold() in self.resume.text.casefold()
            )
            top_matches = list(
                self.db.scalars(
                    select(MatchResult)
                    .where(MatchResult.resume_id == self.resume.id)
                    .order_by(MatchResult.score.desc())
                    .limit(10)
                ).all()
            )
            total_top_jobs = len(top_matches)
            for tm in top_matches:
                missing = tm.missing or []
                matched = tm.matched or []
                if any(clean_skill.casefold() in s.casefold() for s in missing + matched):
                    jobs_needing_skill += 1

        curated = [
            {
                "skill": clean_skill,
                "title": r.title,
                "url": r.url,
                "provider": r.provider,
            }
            for r in resources
        ]
        if not curated:
            curated = [{
                "skill": clean_skill,
                "title": f"Verified documentation for {clean_skill}",
                "url": "",
                "provider": "Self-Directed Learning",
                "guidance": f"We don't have curated direct links for '{clean_skill}' in our verified catalog yet. We recommend consulting the official project documentation.",
            }]

        return ToolResultList(
            curated,
            skill=clean_skill,
            on_resume=on_resume,
            jobs_needing_skill=jobs_needing_skill,
            total_top_jobs=total_top_jobs,
            curated_resources=curated,
        )

    def tool_add_to_tracker(self, job_id: int, status: str = "Saved", notes: str = "") -> dict[str, Any]:
        """Add job to candidate's Kanban application tracker."""
        job = self.db.get(Job, job_id)
        if not job or not job.active:
            return {"error": f"Job #{job_id} not found."}

        status_map = {
            "saved": "Saved",
            "applied": "Applied",
            "reviewing": "Reviewing",
            "interview": "Interview",
            "interviewing": "Interview",
            "offer": "Offer",
            "offered": "Offer",
            "rejected": "Rejected",
            "hired": "Hired",
        }
        normalized_status = status_map.get(status.strip().casefold(), "Saved")

        existing = self.db.scalar(
            select(Application).where(Application.user_id == self.user.id, Application.job_id == job_id)
        )
        if existing:
            existing.status = normalized_status
            if notes:
                existing.notes = notes
            self.db.flush()
            return {
                "job_id": job.id,
                "citation": f"[Job #{job.id}]",
                "message": f"Updated [Job #{job.id}] {job.title} at {job.company} status to '{normalized_status}'.",
                "application_id": existing.id,
                "status": existing.status,
            }

        app_record = Application(
            user_id=self.user.id,
            job_id=job.id,
            resume_id=self.resume.id if self.resume else None,
            status=normalized_status,
            notes=notes,
        )
        self.db.add(app_record)
        self.db.flush()
        return {
            "job_id": job.id,
            "citation": f"[Job #{job.id}]",
            "message": f"Successfully added [Job #{job.id}] {job.title} at {job.company} to your tracker as '{normalized_status}'.",
            "application_id": app_record.id,
            "status": app_record.status,
        }

    # --- Tool Execution Wrapper with Savepoint (Nested Transaction) ---

    def _execute_tool_with_savepoint(self, name: str, raw_args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool inside db.begin_nested() savepoint, validating args with Pydantic."""
        try:
            if name == "retrieve_resume_context":
                args = RetrieveResumeContextArgs(**raw_args)
                with self.db.begin_nested():
                    res = self.tool_retrieve_resume_context(query=args.query, top_k=args.top_k)
                return {"ok": True, "result": res}
            elif name == "search_jobs":
                args = SearchJobsArgs(**raw_args)
                with self.db.begin_nested():
                    res = self.tool_search_jobs(
                        query=args.q,
                        country=args.country,
                        remote=args.remote,
                        experience_level=args.experience_level,
                        limit=args.limit,
                    )
                return {"ok": True, "result": res}
            elif name == "get_job_details":
                args = GetJobDetailsArgs(**raw_args)
                with self.db.begin_nested():
                    res = self.tool_get_job_details(job_id=args.job_id)
                return {"ok": True, "result": res}
            elif name == "explain_match":
                args = ExplainMatchArgs(**raw_args)
                with self.db.begin_nested():
                    res = self.tool_explain_match(job_id=args.job_id)
                return {"ok": True, "result": res}
            elif name == "suggest_learning":
                args = SuggestLearningArgs(**raw_args)
                with self.db.begin_nested():
                    res = self.tool_suggest_learning(skill=args.skill)
                return {"ok": True, "result": res}
            elif name == "analyze_skill_gaps":
                args = AnalyzeSkillGapsArgs(**raw_args)
                with self.db.begin_nested():
                    res = self.tool_analyze_skill_gaps(target_role=args.target_role)
                return {"ok": True, "result": res}
            elif name == "add_to_tracker":
                args = AddToTrackerArgs(**raw_args)
                with self.db.begin_nested():
                    res = self.tool_add_to_tracker(job_id=args.job_id, status=args.status, notes=args.notes)
                return {"ok": True, "result": res}
            else:
                return {"ok": False, "error_code": "UNKNOWN_TOOL", "message": f"Unknown tool '{name}'"}
        except Exception as err:
            log.exception("Tool execution failed for %s: %s", name, err)
            return {"ok": False, "error_code": "TOOL_ERROR", "message": str(err)}

    # --- Guardrails & Sanitization ---

    def _sanitize_internal_mentions(self, text: str) -> str:
        """Sanitize accidental internal tool calling or schema mentions from LLM text."""
        cleaned = re.sub(r"(?i)\bthe\s+([a-z_]+)\s+tool\s+(has\s+)?(provided|returned)\b", "our search found", text)
        cleaned = re.sub(r"(?i)\bthe\s+tool\s+call\s+to\b", "our lookup for", cleaned)
        cleaned = re.sub(r"(?i)\b(in\s+the\s+json\s+object|json\s+response|json\s+properties)\b", "in the verified data", cleaned)
        cleaned = re.sub(r"(?i)\b(tool\s+call|function\s+call)\b", "search", cleaned)
        return cleaned

    def _validate_guardrails(self, text: str) -> bool:
        """Check if output violates guardrails: mentions explicit function calling or invented shell commands."""
        low = text.casefold()
        if re.search(r"\b(tool_call|function_call|json\s+object\s+with|the\s+[a-z_]+\s+tool\s+has\s+provided)\b", low):
            return False
        if re.search(r"```(bash|sh|cmd|powershell)?\s*\n.*?(sudo|apt-get|yum|docker run|curl -s|pip install)\b", text, re.DOTALL | re.I):
            return False
        return True

    # --- Isolated Chat Memory Persistence ---

    def _persist_memory_isolated(
        self,
        user_message: str,
        assistant_reply: str,
        citations: list[str],
        executed_tools: list[dict[str, Any]],
    ) -> None:
        """Persist chat messages in an isolated short-lived session so it can never break replies."""
        try:
            mem_db = Session(self.db.bind, expire_on_commit=False) if (hasattr(self.db, "bind") and self.db.bind is not None) else SessionLocal()
            with mem_db:
                mem_db.add(ChatMessage(user_id=self.user.id, role="user", content=user_message))
                mem_db.add(
                    ChatMessage(
                        user_id=self.user.id,
                        role="assistant",
                        content=assistant_reply,
                        citations=citations,
                        tool_calls=[{"tool": t.get("tool"), "args": t.get("args")} for t in executed_tools],
                    )
                )
                mem_db.commit()
        except Exception as err:
            log.warning("Isolated chat memory persistence error: %s", err)

    # --- Ollama Single-Generation Execution ---

    def _execute_ollama_single_generation(
        self,
        message: str,
    ) -> tuple[str, list[dict[str, Any]], list[str]]:
        """Ollama fallback: exactly ONE generation per message with RAG-first retrieval."""
        executed_tools = []
        valid_citations = []
        low = message.casefold()

        # 1. RAG-first retrieval: always fetch top-4 resume chunks if candidate has resume
        resume_context_text = ""
        if self.resume:
            res_chunks = self.tool_retrieve_resume_context(query=message, top_k=4)
            executed_tools.append({
                "tool": "retrieve_resume_context",
                "args": {"query": message, "top_k": 4},
                "label": tool_label("retrieve_resume_context"),
                "ok": True,
                "result": res_chunks,
            })
            sections = res_chunks.get("sections", [])
            if sections:
                for s in sections:
                    valid_citations.append(s["citation"])
                    resume_context_text += f"{s['citation']}: {s['text']}\n"

        # 2. Deterministic intent detection to execute tool
        tool_data_text = ""
        returned_job_ids: set[int] = set()

        if re.search(r"\b(skill|skills|gap|gaps|missing|improve|strength|strengths)\b", low):
            g_res = self.tool_analyze_skill_gaps()
            executed_tools.append({
                "tool": "analyze_skill_gaps",
                "args": {},
                "label": tool_label("analyze_skill_gaps"),
                "ok": True,
                "result": g_res,
            })
            tool_data_text = "Skill gap and candidate analysis:\n" + json.dumps(list(g_res), indent=2)

        elif re.search(r"\b(learn|study|roadmap|course|tutorial|resources?)\b", low):
            clean = re.sub(r"\b(how|do|i|learn|can|study|roadmap|for|resources?|about|what|is|to)\b", " ", low)
            skill = clean.strip().title() or "Python"
            l_res = self.tool_suggest_learning(skill=skill)
            executed_tools.append({
                "tool": "suggest_learning",
                "args": {"skill": skill},
                "label": tool_label("suggest_learning"),
                "ok": True,
                "result": l_res,
            })
            tool_data_text = f"Learning data for {skill}:\n" + json.dumps(list(l_res), indent=2)

        elif re.search(r"\b(job|jobs|internship|internships|role|roles|openings?|search|find|hiring)\b", low):
            parsed = parse_nl_query_heuristic(message)
            jobs_res = self.tool_search_jobs(
                query=parsed["q"],
                country=parsed["country"],
                remote=parsed["remote"],
                experience_level=parsed["experience_level"],
                limit=5,
            )
            executed_tools.append({
                "tool": "search_jobs",
                "args": parsed,
                "label": tool_label("search_jobs"),
                "ok": True,
                "result": jobs_res,
            })
            jobs_list = jobs_res.get("jobs", [])
            for j in jobs_list:
                returned_job_ids.add(j["job_id"])
                valid_citations.append(j["citation"])
            tool_data_text = f"Job search results:\n" + json.dumps(list(jobs_res), indent=2)

        elif match_id := re.search(r"\b(?:job\s*#?|#)(\d+)\b", low):
            jid = int(match_id.group(1))
            if "explain" in low or "why" in low or "match" in low:
                exp_res = self.tool_explain_match(job_id=jid)
                executed_tools.append({
                    "tool": "explain_match",
                    "args": {"job_id": jid},
                    "label": tool_label("explain_match"),
                    "ok": True,
                    "result": exp_res,
                })
                tool_data_text = f"Match breakdown for Job #{jid}:\n" + json.dumps(exp_res, indent=2)
            else:
                det_res = self.tool_get_job_details(job_id=jid)
                executed_tools.append({
                    "tool": "get_job_details",
                    "args": {"job_id": jid},
                    "label": tool_label("get_job_details"),
                    "ok": True,
                    "result": det_res,
                })
                tool_data_text = f"Job #{jid} details:\n" + json.dumps(det_res, indent=2)
            returned_job_ids.add(jid)
            valid_citations.append(f"[Job #{jid}]")

        # 3. Exactly ONE generation call
        system_rules = (
            "You are SkillMatch AI Career Assistant, an expert, warm, and highly practical career advisor.\n"
            "CRITICAL RULES:\n"
            "1. Answer the user's question directly in plain, friendly language.\n"
            "2. NEVER mention tools, JSON, schemas, function names, or internal errors.\n"
            "3. NEVER invent commands, URLs, skills, employers, or experience.\n"
            "4. Use ONLY links that appear in the provided catalog data, as markdown links.\n"
            "5. Cite jobs strictly as [Job #id] (e.g. [Job #42]).\n"
            "6. Cite candidate resume evidence strictly as [Resume: section].\n"
            "7. Keep answers under ~200 words unless asked.\n"
            "8. For learning questions: provide a structured 3-5 step roadmap personalized to the candidate (what their resume already shows vs what is missing), then the curated links.\n\n"
            f"Candidate Context:\n{resume_context_text}\n\n"
            f"Verified Catalog Context:\n{tool_data_text}"
        )
        messages = [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": message},
        ]
        raw_reply = self.ai._call_ollama_chat(messages)

        # Apply guardrail
        if not self._validate_guardrails(raw_reply) or not raw_reply.strip():
            raw_reply = self._synthesize_grounded_fallback(message, executed_tools)

        # Strip unverified job IDs
        for found_jid in re.findall(r"\[Job #(\d+)\]", raw_reply):
            jid_num = int(found_jid)
            job = self.db.get(Job, jid_num)
            if not job or not job.active:
                raw_reply = re.sub(rf"\[Job #{found_jid}\]", "", raw_reply)
            elif returned_job_ids and jid_num not in returned_job_ids:
                raw_reply = re.sub(rf"\[Job #{found_jid}\]", "", raw_reply)

        return raw_reply.strip(), executed_tools, sorted(set(valid_citations))

    def _get_candidate_context_summary(self, user_query: str = "") -> tuple[str, list[str]]:
        """Build comprehensive candidate context: profile, top matches, skill gaps, and RAG chunks."""
        if not self.resume:
            self.resume = latest_resume(self.db, self.user.id)

        if not self.resume:
            return f"Candidate name: {self.user.name}. (No resume uploaded yet).", []

        skills_list = [s.name for s in (self.resume.skills or [])[:15]]
        skills_str = ", ".join(skills_list)

        # Fetch top matches and missing skills
        query = (
            select(MatchResult, Job)
            .join(Job, MatchResult.job_id == Job.id)
            .where(MatchResult.resume_id == self.resume.id, Job.active.is_(True))
            .order_by(MatchResult.score.desc())
            .limit(5)
        )
        matches = list(self.db.execute(query).all())

        from collections import Counter
        missing_counter = Counter()
        top_matches_text = []
        for mr, job in matches:
            top_matches_text.append(f"- [Job #{job.id}] {job.title} at {job.company} (Match: {mr.score}%)")
            for m_skill in (mr.missing or []):
                missing_counter[m_skill] += 1

        common_gaps = [f"{skill} (needed by {cnt} top roles)" for skill, cnt in missing_counter.most_common(5)]
        gaps_str = ", ".join(common_gaps) if common_gaps else "No major skill gaps detected."
        matches_str = "\n".join(top_matches_text) if top_matches_text else "None scored yet."

        # RAG-first: Pre-retrieve top relevant chunks for the user query if provided
        valid_citations = []
        rag_snippets = []
        if user_query:
            try:
                res_chunks = self.tool_retrieve_resume_context(query=user_query, top_k=3)
                sections = res_chunks.get("sections", []) if hasattr(res_chunks, "get") else res_chunks
                for sec in sections:
                    if isinstance(sec, dict) and "citation" in sec:
                        valid_citations.append(sec["citation"])
                        rag_snippets.append(f"{sec['citation']}: {sec.get('text', '')[:300]}")
            except Exception as e:
                log.debug("Pre-RAG retrieval error: %s", e)

        rag_text = "\n".join(rag_snippets) if rag_snippets else "None"

        summary = (
            f"Candidate Name: {self.user.name}\n"
            f"Documented Resume Skills: {skills_str}\n"
            f"Documented Experience: {self.resume.experience_years or 0} years\n"
            f"Top Scored Job Matches:\n{matches_str}\n"
            f"Top Missing Skills across matches: {gaps_str}\n"
            f"Relevant Resume Excerpts (RAG):\n{rag_text}"
        )
        return summary, valid_citations

    # --- Full Turn Processing ---

    def process_message(self, message: str) -> dict[str, Any]:
        """Process user message with tool calling loop, savepoints, and citation integrity."""
        start_time = time.perf_counter()
        provider_name = self.ai.get_active_provider_name()

        # Load last 10 messages for conversation memory
        history_msgs = list(
            self.db.scalars(
                select(ChatMessage)
                .where(ChatMessage.user_id == self.user.id)
                .order_by(ChatMessage.id.desc())
                .limit(10)
            ).all()
        )
        history_msgs.reverse()

        # If Ollama fallback without native tool calling: use the single-generation flow
        if provider_name == "ollama":
            reply, tools_run, citations = self._execute_ollama_single_generation(message)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            try:
                self.db.add(ChatMessage(user_id=self.user.id, role="user", content=message))
                self.db.add(ChatMessage(user_id=self.user.id, role="assistant", content=reply, citations=citations, tool_calls=[{"tool": t.get("tool"), "args": t.get("args")} for t in tools_run]))
                self.db.commit()
            except Exception:
                self._persist_memory_isolated(message, reply, citations, tools_run)
            return {
                "reply": reply,
                "tool_results": tools_run,
                "citations": citations,
                "provider": "ollama",
                "latency_ms": latency_ms,
            }

        candidate_summary, pre_rag_citations = self._get_candidate_context_summary(user_query=message)

        system_prompt = (
            "You are SkillMatch AI Career Assistant, an expert, warm, and highly practical career advisor.\n"
            "CRITICAL RULES:\n"
            "1. Answer the user's question directly in plain, friendly language.\n"
            "2. NEVER mention tools, JSON, schemas, function names, or internal errors.\n"
            "3. NEVER invent commands, URLs, skills, employers, or experience.\n"
            "4. Use ONLY links that appear in tool results, formatted strictly as markdown links.\n"
            "5. Cite jobs strictly as [Job #id] (e.g. [Job #42]).\n"
            "6. Cite candidate resume evidence strictly as [Resume: section] (e.g. [Resume: Experience]).\n"
            "7. If data is missing or not found, say so briefly.\n"
            "8. Keep answers under ~200 words unless asked.\n"
            "9. For learning questions: provide a structured 3-5 step roadmap personalized to the candidate (noting what their resume already shows vs what is missing), then the curated links.\n"
            "10. For job search answers: summarize top opportunities including match %, confidence level, and top missing skills.\n"
            "11. For open-ended resume or skill gap questions: leverage the Candidate Career Context below to explain their strengths, top missing skills across market matches, and recommended next steps.\n\n"
            f"=== CANDIDATE CAREER CONTEXT ===\n{candidate_summary}"
        )

        llm_messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for hm in history_msgs:
            llm_messages.append({"role": hm.role, "content": hm.content})
        llm_messages.append({"role": "user", "content": message})

        executed_tools: list[dict[str, Any]] = []
        retrieved_job_ids: set[int] = set()
        retrieved_resume_sections: set[str] = set()
        final_reply = ""
        provider_used = provider_name
        had_tool_error = False
        last_failed_tool = ""

        # Tool round loop (max 3 rounds)
        for _ in range(3):
            step = self.ai.chat_step(llm_messages, tools=ASSISTANT_TOOLS)
            provider_used = step.get("provider", provider_used)
            tool_calls = step.get("tool_calls", [])

            if not tool_calls:
                final_reply = step.get("content", "")
                break

            # If provider is grounded rules or ollama without native tool support, break out
            if provider_used in {"grounded_rules", "ollama"}:
                final_reply = step.get("content", "")
                break

            # Append assistant message with tool calls
            raw_tcs = step.get("raw_tool_calls") or [
                {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])}}
                for tc in tool_calls
            ]
            llm_messages.append({
                "role": "assistant",
                "content": step.get("content", "") or None,
                "tool_calls": raw_tcs,
            })

            # Execute tools
            for tc in tool_calls:
                fn_name = tc.get("name", "")
                fn_args = tc.get("args", {})
                call_id = tc.get("id", f"call_{len(executed_tools)}")

                tool_run = self._execute_tool_with_savepoint(fn_name, fn_args)
                is_ok = tool_run.get("ok", False)
                res = tool_run.get("result") if is_ok else {"error": tool_run.get("message", "Tool execution error")}

                if not is_ok:
                    had_tool_error = True
                    last_failed_tool = fn_name

                # Record citations
                if is_ok:
                    if fn_name == "search_jobs":
                        job_list = res.get("jobs") if hasattr(res, "get") else res
                        if isinstance(job_list, list):
                            for j in job_list:
                                if isinstance(j, dict) and "job_id" in j:
                                    retrieved_job_ids.add(j["job_id"])
                    elif fn_name in {"get_job_details", "explain_match", "add_to_tracker"} and isinstance(res, dict):
                        if "job_id" in res:
                            retrieved_job_ids.add(res["job_id"])
                    elif fn_name == "retrieve_resume_context":
                        sec_list = res.get("sections") if hasattr(res, "get") else res
                        if isinstance(sec_list, list):
                            for sec in sec_list:
                                if isinstance(sec, dict) and "section" in sec:
                                    retrieved_resume_sections.add(sec["section"])

                executed_tools.append({
                    "tool": fn_name,
                    "args": fn_args,
                    "label": tool_label(fn_name),
                    "ok": is_ok,
                    "result": res,
                })

                # Append tool result in OpenAI/Groq standard role=tool format
                llm_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": fn_name,
                    "content": json.dumps(res if not isinstance(res, ToolResultList) else list(res)),
                })

        # If exhausted rounds without final text, request answer synthesis
        if not final_reply.strip():
            final_step = self.ai.chat_step(llm_messages, tools=None)
            final_reply = final_step.get("content", "")
            provider_used = final_step.get("provider", provider_used)

        # Handle tool failure: if all tools failed or reply is empty, give friendly error sentence
        if had_tool_error and (not final_reply.strip() or len(executed_tools) == 1):
            final_reply = friendly_tool_error(last_failed_tool)
        elif not final_reply.strip() or provider_used == "grounded_rules":
            final_reply = self._synthesize_grounded_fallback(message, executed_tools)

        # Post-generation guardrails: check for forbidden terms or invented commands
        if not self._validate_guardrails(final_reply):
            log.warning("CareerAssistant output violated guardrails. Regenerating once with reminder.")
            llm_messages.append({
                "role": "user",
                "content": "Reminder: Answer directly in plain friendly text. Do NOT mention tools, JSON, schemas, or invented commands.",
            })
            regen_step = self.ai.chat_step(llm_messages, tools=None)
            candidate_reply = regen_step.get("content", "")
            if self._validate_guardrails(candidate_reply) and candidate_reply.strip():
                final_reply = candidate_reply
            else:
                final_reply = self._synthesize_grounded_fallback(message, executed_tools)

        # Strip unverified [Job #id]
        for jid_str in re.findall(r"\[Job #(\d+)\]", final_reply):
            jid = int(jid_str)
            job = self.db.get(Job, jid)
            if not job or not job.active:
                final_reply = re.sub(rf"\[Job #{jid}\]", "", final_reply)
            elif retrieved_job_ids and jid not in retrieved_job_ids:
                final_reply = re.sub(rf"\[Job #{jid}\]", "", final_reply)
            else:
                retrieved_job_ids.add(jid)

        valid_citations = [f"[Job #{jid}]" for jid in sorted(retrieved_job_ids)]
        valid_citations += [f"[Resume: {sec}]" for sec in sorted(retrieved_resume_sections)]

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Persist to ChatMessage memory (try current session first, fallback to isolated)
        try:
            msg_user = ChatMessage(user_id=self.user.id, role="user", content=message)
            msg_bot = ChatMessage(
                user_id=self.user.id,
                role="assistant",
                content=final_reply,
                citations=valid_citations,
                tool_calls=[{"tool": t.get("tool"), "args": t.get("args")} for t in executed_tools],
            )
            self.db.add(msg_user)
            self.db.add(msg_bot)
            self.db.commit()
        except Exception as err:
            log.warning("Primary session chat persistence failed: %s; using isolated session", err)
            try:
                self.db.rollback()
            except Exception:
                pass
            self._persist_memory_isolated(message, final_reply, valid_citations, executed_tools)

        return {
            "reply": final_reply,
            "tool_results": executed_tools,
            "citations": valid_citations,
            "provider": provider_used,
            "latency_ms": latency_ms,
        }

    # --- Deterministic Grounded Fallback Synthesis ---

    def _synthesize_grounded_fallback(self, message: str, executed_tools: list[dict[str, Any]]) -> str:
        """Construct grounded, helpful markdown when external LLM is unavailable."""
        if not executed_tools:
            low = message.casefold()
            if re.search(r"\b(job|openings|roles|work|search|find|internship)\b", low):
                res = self.tool_search_jobs(query=message, limit=4)
                jobs = res.get("jobs", []) if hasattr(res, "get") else res
                if jobs:
                    lines = [f"Found {len(jobs)} relevant openings:"]
                    for j in jobs:
                        match_info = f" (Match: {j['match_score']}%)" if j.get("match_score") else ""
                        lines.append(f"- **{j['citation']} {j['title']}** at **{j['company']}** ({j['location']}){match_info}")
                    if hasattr(res, "get") and res.get("relaxed_note"):
                        lines.append(f"\n*{res.get('relaxed_note')}*")
                    lines.append("\nWould you like me to explain your match breakdown for any of these roles?")
                    return "\n".join(lines)

            if re.search(r"\b(learn|study|roadmap|docker|fastapi|python|sql)\b", low):
                skill = re.sub(r"[^\w\s]", "", message).replace("how", "").replace("learn", "").replace("do", "").replace("i", "").strip().title() or "Docker"
                l_res = self.tool_suggest_learning(skill)
                lines = [f"### Roadmap to Learn **{skill}**\n"]
                if hasattr(l_res, "get") and l_res.get("on_resume"):
                    lines.append(f"- **Current Background**: {skill} is already listed on your resume [Resume: Skills].")
                elif hasattr(l_res, "get") and l_res.get("jobs_needing_skill", 0) > 0:
                    lines.append(f"- **Market Demand**: {skill} is required by {l_res.get('jobs_needing_skill')} of your top matched jobs.")
                else:
                    lines.append("- **Foundation**: Build core competency with practical hands-on projects.")

                lines.append("\n**Recommended Steps**:")
                lines.append("1. **Core Fundamentals**: Understand architecture, core components, and primary configuration syntax.")
                lines.append("2. **Hands-on Practice**: Build and run small containerized projects locally.")
                lines.append("3. **Production Readiness**: Learn multi-stage builds, persistent volumes, and networking.")
                lines.append("4. **Orchestration**: Explore Docker Compose and integration with CI/CD pipelines.")

                resources = l_res.get("curated_resources", []) if hasattr(l_res, "get") else l_res
                if resources:
                    lines.append("\n**Curated Resources**:")
                    for r in resources:
                        if r.get("url"):
                            lines.append(f"- [{r['title']}]({r['url']}) ({r.get('provider', 'Official')})")
                        else:
                            lines.append(f"- {r['title']}: {r.get('guidance', '')}")
                return "\n".join(lines)

            if re.search(r"\b(skill|skills|gap|gaps|missing|resume|improve|profile|strengths?)\b", low):
                g_res = self.tool_analyze_skill_gaps()
                analysis = g_res.get("analysis", {}) if hasattr(g_res, "get") else (g_res[0] if g_res else {})
                missing = analysis.get("top_missing_skills", [])
                strengths = analysis.get("top_strengths", [])
                roles = analysis.get("top_roles", [])
                lines = ["### Skill Analysis & Gap Review for Your Profile\n"]
                if missing:
                    lines.append("**Top In-Demand Skills Missing from Your Profile:**")
                    for item in missing:
                        lines.append(f"- **{item['skill']}** (required by {item['job_count']} of your top matched jobs)")
                else:
                    lines.append("No critical skill gaps identified across your top matched roles!")

                if strengths:
                    lines.append("\n**Key Matched Strengths:**")
                    strength_names = [s['skill'] for s in strengths[:6]]
                    lines.append(f"- {', '.join(strength_names)} [Resume: Skills]")

                if roles:
                    lines.append("\n**Top Scored Opportunities:**")
                    for r in roles:
                        lines.append(f"- **[Job #{r['job_id']}] {r['title']}** at **{r['company']}** (Match: {r['score']}%)")

                lines.append("\nWould you like a personalized roadmap to learn any of these skills? Just ask: *'How do I learn <skill>?'*")
                return "\n".join(lines)

            return (
                "I am your SkillMatch Career Assistant. I can help you search for jobs, analyze match breakdowns, "
                "track applications on your Kanban board, and identify curated learning paths. How can I assist you today?"
            )

        blocks = []
        for item in executed_tools:
            tool_name = item["tool"]
            res = item.get("result", {})
            if not item.get("ok", True):
                blocks.append(friendly_tool_error(tool_name))
                continue

            if tool_name == "analyze_skill_gaps":
                analysis = res.get("analysis", {}) if hasattr(res, "get") else (res[0] if isinstance(res, list) and res else {})
                missing = analysis.get("top_missing_skills", [])
                strengths = analysis.get("top_strengths", [])
                roles = analysis.get("top_roles", [])
                lines = ["### Skill Analysis & Gap Breakdown\n"]
                if missing:
                    lines.append("**High-Priority Skill Gaps Across Your Matches:**")
                    for it in missing:
                        lines.append(f"- **{it['skill']}** (required by {it['job_count']} target opportunities)")
                if strengths:
                    lines.append("\n**Your Strongest Overlapping Skills:**")
                    strength_names = [s['skill'] for s in strengths[:6]]
                    lines.append(f"- {', '.join(strength_names)} [Resume: Skills]")
                if roles:
                    lines.append("\n**Target Scored Roles:**")
                    for r in roles:
                        lines.append(f"- **[Job #{r['job_id']}] {r['title']}** at **{r['company']}** (Match: {r['score']}%)")
                lines.append("\nAsk *'How do I learn <skill>?'* to get a tailored learning roadmap with curated resources.")
                blocks.append("\n".join(lines))

            if tool_name == "search_jobs":
                jobs = res.get("jobs", []) if hasattr(res, "get") else res
                if jobs:
                    lines = [f"Found {len(jobs)} matching openings:"]
                    for j in jobs:
                        match_text = f" • Match: {j['match_score']}%" if j.get("match_score") else ""
                        lines.append(f"- **{j['citation']} {j['title']}** at **{j['company']}** ({j['location']}){match_text}")
                    if hasattr(res, "get") and res.get("relaxed_note"):
                        lines.append(f"\n*{res.get('relaxed_note')}*")
                    blocks.append("\n".join(lines))
                else:
                    blocks.append("No active openings matched that specific query. Try broadening your keywords.")

            elif tool_name == "get_job_details" and isinstance(res, dict):
                if "error" in res:
                    blocks.append(res["error"])
                else:
                    blocks.append(
                        f"### {res['citation']} {res['title']} at {res['company']}\n"
                        f"- **Location**: {res['location']} | **Remote**: {'Yes' if res['remote'] else 'No'}\n"
                        f"- **Level**: {res['experience_level'].capitalize() if res['experience_level'] else 'Not specified'}\n"
                        f"- **Required Skills**: {', '.join(res['required_skills']) if res['required_skills'] else 'General'}\n\n"
                        f"{res['description'][:400]}..."
                    )

            elif tool_name == "explain_match" and isinstance(res, dict):
                if "error" in res:
                    blocks.append(res["error"])
                else:
                    blocks.append(
                        f"### Match Analysis for {res['citation']} {res['title']} at {res['company']} (Score: {res['score']}%)\n\n"
                        f"{res.get('narrative', '')}"
                    )

            elif tool_name == "suggest_learning":
                skill = res.get("skill", "Skill") if hasattr(res, "get") else "Skill"
                lines = [f"### Learning Roadmap for **{skill}**:"]
                if hasattr(res, "get") and res.get("on_resume"):
                    lines.append(f"- {skill} is already listed on your resume [Resume: Skills].")
                elif hasattr(res, "get") and res.get("jobs_needing_skill", 0) > 0:
                    lines.append(f"- {skill} is required by {res.get('jobs_needing_skill')} of your top matched jobs.")
                lines.append("\n**Curated Resources**:")
                resources = res.get("curated_resources", []) if hasattr(res, "get") else res
                for r in resources:
                    if r.get("url"):
                        lines.append(f"- [{r['title']}]({r['url']}) ({r.get('provider', 'Official')})")
                    else:
                        lines.append(f"- {r['title']}: {r.get('guidance', '')}")
                blocks.append("\n".join(lines))

            elif tool_name == "add_to_tracker" and isinstance(res, dict):
                blocks.append(res.get("message", "Application tracker updated."))

            elif tool_name == "retrieve_resume_context":
                sections = res.get("sections", []) if hasattr(res, "get") else res
                if sections:
                    lines = ["Relevant context from your resume:"]
                    for s in sections:
                        lines.append(f"- **{s['citation']}**: {s['text'][:200]}...")
                    blocks.append("\n".join(lines))

        return "\n\n".join(blocks) if blocks else "I processed your request using the verified catalog data."

    # --- Streaming Generator ---

    def stream_message(self, message: str) -> Generator[str, None, None]:
        """Stream response as SSE events with tool progress indicators, status chips, tokens, and verified citations."""
        result = self.process_message(message)
        reply = result.get("reply", "")
        tool_results = result.get("tool_results", [])
        citations = result.get("citations", [])
        provider = result.get("provider", "grounded_rules")
        latency_ms = result.get("latency_ms", 0.0)

        # 1. Emit tool executions with status chips
        for t in tool_results:
            is_ok = t.get("ok", True)
            yield f"data: {json.dumps({'type': 'tool', 'tool': t.get('tool'), 'label': t.get('label'), 'status': 'done' if is_ok else 'error', 'tools': [t]})}\n\n"

        # 2. Stream tokens (words with whitespace preservation)
        words = reply.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

        # 3. Emit done event (show provider and latency only if assistant_debug is enabled)
        show_debug = bool(self.settings.assistant_debug)
        yield f"data: {json.dumps({'type': 'done', 'citations': citations, 'provider': provider if show_debug else '', 'latency_ms': latency_ms if show_debug else 0, 'tool_results': tool_results})}\n\n"
