"""Natural Language Search: converts conversational queries into structured job filters."""

import json
import logging
import re
from typing import Any

from app.services.ai_provider import get_ai_provider

log = logging.getLogger(__name__)


def coerce_bool(val: Any) -> bool | None:
    """Coerce string/int/bool values to a strict Python bool or None."""
    if val is None or val == "":
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        v = val.strip().casefold()
        if v in ("true", "yes", "1", "t", "y"):
            return True
        if v in ("false", "no", "0", "f", "n"):
            return False
    return None


def parse_nl_query_heuristic(query: str) -> dict[str, Any]:
    """Extract structured filters from natural language using robust patterns and clean keywords."""
    text = query.strip()
    low = text.casefold()

    # 1. Experience Level mapping
    exp_level = None
    if re.search(r"\b(interns?|internships?|trainees?|co-ops?)\b", low):
        exp_level = "intern"
    elif re.search(r"\b(entry|junior|fresher|freshers?|graduate|graduates?|new\s+grads?|entry[-\s]*level|associate)\b", low):
        exp_level = "entry"
    elif re.search(r"\b(mid|mid[-\s]*level|intermediate)\b", low):
        exp_level = "mid"
    elif re.search(r"\b(senior|seniors?|lead|leads?|principal|staff|architects?)\b", low):
        exp_level = "senior"

    # 2. Remote mapping
    remote = None
    if re.search(r"\b(remote|work\s+from\s+home|wfh|anywhere)\b", low):
        remote = True
    elif re.search(r"\b(onsite|on[-\s]*site|in[-\s]*office)\b", low):
        remote = False

    # 3. Country / Location mapping
    country = None
    if re.search(r"\b(united states|usa|u\.s\.a?|america|new york|sf|san francisco)\b", low):
        country = "United States"
    elif re.search(r"\b(germany|deutschland|berlin|munich)\b", low):
        country = "Germany"
    elif re.search(r"\b(united kingdom|uk|u\.k\.|london|britain|england)\b", low):
        country = "United Kingdom"
    elif re.search(r"\b(india|bharat|bangalore|bengaluru|delhi|hyderabad|mumbai|pune|gurgaon|noida|chennai)\b", low):
        country = "India"

    # 4. Salary Disclosed
    salary_disclosed = False
    if re.search(r"\b(paying|salary|salaries|compensation|package|ctc|lpa|\$|₹|eur)\b", low):
        salary_disclosed = True

    # 5. Extract remaining keywords for q, stripping intent keywords and filler words
    cleaned = re.sub(
        r"\b(find|search|show|me|looking\s+for|jobs?|openings?|positions?|roles?|remote|work\s+from\s+home|wfh|anywhere|onsite|on[-\s]*site|internships?|interns?|trainees?|co-ops?|entry[-\s]*level|juniors?|freshers?|new\s+grads?|graduates?|associates?|mid[-\s]*level|intermediates?|seniors?|leads?|principals?|staff|architects?|paying|salary|salaries|compensation|in|at|for|with|and|the|a|an)\b",
        " ",
        text,
        flags=re.I,
    )
    # Strip location names if matched as country filter
    if country == "India":
        cleaned = re.sub(r"\b(india|bharat|bangalore|bengaluru|delhi|hyderabad|mumbai|pune|gurgaon|noida|chennai)\b", " ", cleaned, flags=re.I)
    elif country == "United States":
        cleaned = re.sub(r"\b(united states|usa|u\.s\.a?|america|new york|sf|san francisco)\b", " ", cleaned, flags=re.I)

    tokens = [w.strip() for w in re.split(r"[,\s]+", cleaned) if len(w.strip()) > 1]
    q = " ".join(tokens).strip()

    return {
        "q": q or text,
        "experience_level": exp_level,
        "remote": remote,
        "country": country,
        "salary_disclosed": salary_disclosed,
        "original_query": text,
    }


def parse_nl_query(query: str) -> dict[str, Any]:
    """Parse query with LLM structured prompt and fallback to robust heuristics."""
    heuristic = parse_nl_query_heuristic(query)

    ai = get_ai_provider()
    if ai.settings.openai_api_key or ai.settings.ollama_enabled:
        prompt = (
            f"Convert this job search query into a JSON object with keys: q, experience_level, remote, country, salary_disclosed.\n"
            f"Query: \"{query}\"\n"
            f"Return ONLY valid JSON matching this schema:\n"
            f"{{\n"
            f'  "q": "search keywords or skills",\n'
            f'  "experience_level": "intern" | "entry" | "mid" | "senior" | null,\n'
            f'  "remote": true | false | null,\n'
            f'  "country": "India" | "United States" | null,\n'
            f'  "salary_disclosed": true | false\n'
            f"}}"
        )
        try:
            res = ai.generate(prompt, system="You are an expert search query parser. Respond only in valid JSON.")
            text = res.get("text", "").strip()
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                return {
                    "q": parsed.get("q") or heuristic["q"],
                    "experience_level": parsed.get("experience_level") or heuristic["experience_level"],
                    "remote": coerce_bool(parsed.get("remote")) if parsed.get("remote") is not None else heuristic["remote"],
                    "country": parsed.get("country") or heuristic["country"],
                    "salary_disclosed": bool(parsed.get("salary_disclosed", heuristic["salary_disclosed"])),
                    "original_query": query,
                    "parsed_by": res.get("provider", "llm"),
                }
        except Exception as err:
            log.debug("LLM query parsing failed (%s), using heuristic", err)

    heuristic["parsed_by"] = "heuristic"
    return heuristic
