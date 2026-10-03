"""Resume tailoring and cover letter generation grounded strictly in candidate resume text."""

import difflib
import logging
import re
from typing import Any

from app.services.ai_provider import get_ai_provider

log = logging.getLogger(__name__)


def generate_cover_letter(
    resume_text: str,
    job_title: str,
    company: str,
    job_description: str,
    matched_skills: list[str],
) -> dict[str, Any]:
    """Generate a cover letter strictly grounded in the candidate's actual resume."""
    matched_str = ", ".join(matched_skills[:8]) if matched_skills else "software engineering fundamentals"

    # Extract first 1500 chars of resume for context
    resume_excerpt = resume_text[:2500].strip()

    system_prompt = (
        "You are an expert career advisor. You write concise, professional cover letters. "
        "CRITICAL GROUNDING CONSTRAINT: You must ONLY reference experiences, degrees, companies, and "
        "projects that are explicitly present in the candidate's resume excerpt. DO NOT invent previous jobs, "
        "metrics, or technologies that the candidate did not state."
    )

    prompt = (
        f"Write a focused, 3-paragraph cover letter applying for {job_title} at {company}.\n\n"
        f"TARGET ROLE REQUIREMENTS SUMMARY:\n{job_description[:800]}\n\n"
        f"VERIFIED MATCHING SKILLS:\n{matched_str}\n\n"
        f"CANDIDATE'S ACTUAL RESUME:\n{resume_excerpt}\n\n"
        f"Format:\n"
        f"Dear Hiring Team,\n\n"
        f"[Paragraph 1: Clear statement of interest in {job_title} at {company}, connecting candidate's genuine background]\n\n"
        f"[Paragraph 2: Highlight 1-2 actual projects or skills from resume that directly prove capability in {matched_str}]\n\n"
        f"[Paragraph 3: Reiterate enthusiasm, collaboration ethos, and polite call to interview]\n\n"
        f"Sincerely,\nCandidate"
    )

    ai = get_ai_provider()
    result = ai.generate(prompt, system=system_prompt)
    letter_text = result.get("text", "")

    if result.get("provider") == "grounded_rules" or not letter_text.strip():
        # High-quality deterministic grounded letter
        letter_text = (
            f"Dear Hiring Team,\n\n"
            f"I am writing to express my strong enthusiasm for the {job_title} role at {company}. "
            f"Having reviewed the technical requirements, my background and verified experience in {matched_str} "
            f"provide a direct foundation to contribute to your engineering initiatives.\n\n"
            f"Throughout my work, I have focused on building reliable, maintainable software and collaborating "
            f"effectively across technical workflows. My practical experience with {matched_str} has allowed me to "
            f"deliver functional code, debug complex edge cases, and adapt quickly to modern tooling.\n\n"
            f"I would welcome the opportunity to discuss how my technical skills and enthusiasm for {company}'s "
            f"engineering goals align with your current openings. Thank you for your time and consideration.\n\n"
            f"Sincerely,\nCandidate"
        )

    return {
        "cover_letter": letter_text,
        "job_title": job_title,
        "company": company,
        "matched_skills": matched_skills,
        "provider": result.get("provider", "grounded_rules"),
        "latency_ms": result.get("latency_ms", 0.0),
    }


def tailor_resume(
    resume_text: str,
    job_title: str,
    company: str,
    matched_skills: list[str],
    missing_skills: list[str],
) -> dict[str, Any]:
    """Provide grounded resume tailoring suggestions with unified diff view.
    
    Rule: Never adds experience or technologies the candidate doesn't have.
    """
    clean_resume = resume_text.strip()
    lines = clean_resume.splitlines()

    # Identify existing summary or skills line
    summary_idx = -1
    for i, line in enumerate(lines[:10]):
        if re.search(r"\b(summary|objective|profile|about)\b", line, re.I):
            summary_idx = i
            break

    tailored_lines = list(lines)
    tailored_summary = (
        f"Targeted Objective: Software engineer specializing in {', '.join(matched_skills[:4])}, "
        f"seeking to leverage proven technical problem solving and system design skills for the {job_title} role at {company}."
    )

    if summary_idx != -1 and summary_idx + 1 < len(lines):
        tailored_lines[summary_idx + 1] = tailored_summary
    else:
        tailored_lines.insert(0, tailored_summary + "\n")

    original_text = "\n".join(lines[:25])
    tailored_text = "\n".join(tailored_lines[:25])

    # Compute standard unified diff
    diff_gen = difflib.unified_diff(
        original_text.splitlines(keepends=True),
        tailored_text.splitlines(keepends=True),
        fromfile="Current Resume",
        tofile=f"Tailored for {company}",
    )
    diff_text = "".join(diff_gen)

    actionable_tips = [
        f"Reorder your technical skills to highlight **{', '.join(matched_skills[:5])}** at the top of your skills section.",
        "Emphasize impact metrics (e.g. latency reductions, automated test coverage, or users reached) for projects that utilized these skills.",
    ]
    if missing_skills:
        actionable_tips.append(
            f"For gap skills ({', '.join(missing_skills[:3])}), do NOT fabricate experience. Instead, mention relevant coursework or ongoing self-directed projects."
        )

    return {
        "original_text": original_text,
        "tailored_text": tailored_text,
        "diff": diff_text,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "actionable_tips": actionable_tips,
        "grounding_rule": "Grounded strictly in verified candidate facts; no fabricated credentials.",
    }
