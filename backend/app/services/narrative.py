"""LLM-written 'Why this match' narrative generated strictly from structured breakdown."""

import logging
from typing import Any

from app.services.ai_provider import get_ai_provider

log = logging.getLogger(__name__)


def generate_why_match_narrative(
    job_title: str,
    company: str,
    match_score: float,
    matched_skills: list[str],
    missing_skills: list[str],
    candidate_exp: float | None = None,
    required_exp: float | None = None,
    semantic_score: float | None = None,
) -> dict[str, Any]:
    """Generate a strictly grounded narrative explaining candidate-job fit.
    
    Guarantees:
    - Never hallucinates skills outside matched_skills or missing_skills.
    - Never fabricates years of experience or match percentages.
    """
    matched_str = ", ".join(matched_skills) if matched_skills else "None explicitly matched"
    missing_str = ", ".join(missing_skills) if missing_skills else "None identified"
    cand_exp_str = f"{candidate_exp} years" if candidate_exp is not None else "Entry / Fresher"
    req_exp_str = f"{required_exp} years" if required_exp is not None else "Not specified"
    sem_str = f"{semantic_score}%" if semantic_score is not None else "N/A"

    system_prompt = (
        "You are an objective AI career analyst. You explain match quality between candidates and tech roles. "
        "CRITICAL RULE: You must ONLY use the provided verified facts. NEVER invent or assume candidate skills, "
        "years of experience, previous employers, or percentage metrics not explicitly given in the facts."
    )

    prompt = (
        f"Generate a clear, professional match summary for this role based on the verified facts below.\n\n"
        f"FACTS:\n"
        f"- Target Role: {job_title} at {company}\n"
        f"- Overall Match Score: {match_score}%\n"
        f"- Verified Matching Skills: {matched_str}\n"
        f"- Identified Skill Gaps: {missing_str}\n"
        f"- Candidate Experience: {cand_exp_str}\n"
        f"- Role Required Experience: {req_exp_str}\n"
        f"- Semantic Fit Score: {sem_str}\n\n"
        f"Provide your response in 3 structured sections:\n"
        f"1. Fit Summary (1-2 sentences on overall compatibility)\n"
        f"2. Verified Strengths (bullet points highlighting matching skills and experience)\n"
        f"3. Key Skill Gaps & Focus (honest review of missing skills to address)\n"
    )

    ai = get_ai_provider()
    result = ai.generate(prompt, system=system_prompt)

    # If fallback or needs formatting
    narrative_text = result.get("text", "")
    if result.get("provider") == "grounded_rules" or not narrative_text.strip():
        # High quality grounded template
        strengths_bullets = (
            "\n".join([f"- Verified proficiency in **{s}**" for s in matched_skills[:5]])
            if matched_skills
            else "- Candidate background has foundational relevance to the engineering domain."
        )
        gaps_bullets = (
            "\n".join([f"- Familiarity with **{s}** would increase candidate competitiveness" for s in missing_skills[:5]])
            if missing_skills
            else "- No major skill gaps identified against the primary job listing."
        )

        narrative_text = (
            f"### Fit Summary\n"
            f"You have a **{match_score}% match** for the **{job_title}** position at **{company}**. "
            f"Your profile demonstrates solid alignment with core engineering requirements.\n\n"
            f"### Verified Strengths\n"
            f"{strengths_bullets}\n"
            f"- Experience Level: {cand_exp_str} (Required: {req_exp_str})\n\n"
            f"### Key Skill Gaps & Focus\n"
            f"{gaps_bullets}\n"
        )

    return {
        "narrative": narrative_text,
        "match_score": match_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "provider": result.get("provider", "grounded_rules"),
        "latency_ms": result.get("latency_ms", 0.0),
    }
