"""LLM and pattern-based fallback skill extractor with strict validation rules."""

import logging
import re
from typing import Any

from app.services.ai_provider import get_ai_provider

log = logging.getLogger(__name__)

# Stopwords and generic non-technical buzzwords that must never be considered valid CSE skills
BLACKLIST_TERMS = {
    "communication", "teamwork", "leadership", "collaboration", "problem solving",
    "critical thinking", "passionate", "fast learner", "hard worker", "detail oriented",
    "enthusiastic", "experienced", "professional", "responsible", "motivated", "flexible",
    "bachelor", "master", "degree", "diploma", "computer science", "engineering",
    "software engineering", "information technology", "years", "month", "experience",
    "responsibilities", "requirements", "qualifications", "duties", "overview", "summary",
    "management", "development", "building", "developer", "engineer", "scientist",
    "company", "project", "work", "job", "position", "role", "team", "organization",
    "application", "systems", "solutions", "services", "tools", "products", "platforms",
}

# Known valid emerging tech terms outside the core taxonomy
KNOWN_EMERGING_TECH = {
    "langchain", "llamaindex", "chromadb", "weaviate", "pinecone", "qdrant", "milvus",
    "trpc", "prisma", "drizzle", "astro", "solidjs", "sveltekit", "remix", "bun", "deno",
    "vitest", "playwright", "cypress", "tailwind", "shadcn", "turborepo", "nx", "pnpm",
    "fastapi", "litestar", "duckdb", "polars", "dbt", "airflow", "dagster", "prefect",
    "clickhouse", "snowflake", "bigquery", "redshift", "temporal", "surrealdb", "supabase",
    "neon", "vLLM", "ollama", "groq", "huggingface", "onnx", "tensorrt", "deepspeed",
}


def validate_skill_candidate(name: str) -> bool:
    """Validate that candidate string is a genuine, high-quality technical CSE skill."""
    if not name or not isinstance(name, str):
        return False
    clean = name.strip().lower()

    if len(clean) < 2 or len(clean) > 35:
        return False

    if clean in BLACKLIST_TERMS:
        return False

    # Check for single generic English words or purely numeric
    if clean.isdigit():
        return False

    # Check valid characters (alphanumeric, plus, hash, dot, hyphen, space)
    if not re.match(r"^[a-z0-9+#\.\-\s]+$", clean):
        return False

    # Must contain at least one letter
    if not re.search(r"[a-z]", clean):
        return False

    # Reject common phrases like "5 years of experience"
    if re.search(r"\b(years?|months?|experience|proficient|excellent|good|knowledge|understanding)\b", clean):
        return False

    return True


def extract_fallback_skills(
    text: str, existing_skills: set[str] | None = None
) -> list[str]:
    """Extract and strictly validate emerging technical skills not in existing taxonomy."""
    if not text or not text.strip():
        return []
    existing_skills = {s.casefold() for s in (existing_skills or set())}

    candidates = set()

    # 1. Fast regex scanner for known emerging tech terms
    low_text = text.casefold()
    for tech in KNOWN_EMERGING_TECH:
        if tech not in existing_skills and re.search(rf"\b{re.escape(tech)}\b", low_text):
            candidates.add(tech)

    # 2. Pattern recognition for tech frameworks, e.g., name.js, name.py, lib-name
    tech_patterns = re.findall(
        r"\b([a-zA-Z0-9_\-]{2,20}\.(?:js|ts|py|rs|io|ai|dev))\b", text, re.I
    )
    for p in tech_patterns:
        cleaned_p = p.casefold()
        if cleaned_p not in existing_skills and validate_skill_candidate(cleaned_p):
            candidates.add(cleaned_p)

    # 3. LLM extraction for novel terms if available
    ai = get_ai_provider()
    if (ai.settings.openai_api_key or ai.settings.ollama_enabled) and len(text) > 50:
        prompt = (
            "Extract up to 5 specific technical software/hardware tools, frameworks, or programming languages "
            "mentioned in this text that are modern software engineering skills.\n"
            "Return ONLY a comma-separated list of the skill names. Do NOT include soft skills, job titles, or explanations.\n"
            f"Text: {text[:1500]}"
        )
        try:
            res = ai.generate(prompt, system="You are a strict technical skill parser. Output only comma-separated terms.")
            raw_terms = res.get("text", "").split(",")
            for term in raw_terms:
                c = term.strip().lower()
                c = re.sub(r"^[\s\*\-\d\.]+", "", c).strip()
                if c and c not in existing_skills and validate_skill_candidate(c):
                    candidates.add(c)
        except Exception as err:
            log.debug("LLM skill extraction fallback: %s", err)

    # Sort and return normalized title-cased or canonical list
    valid_list = sorted(list(candidates))
    return valid_list
