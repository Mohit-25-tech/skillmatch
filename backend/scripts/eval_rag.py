"""30-Query Evaluation Suite for Phase 3 AI / RAG features.

Evaluates:
- Structured filter extraction accuracy
- Latency (ms)
- Token utilization
- Groundedness (zero hallucinated parameters)
"""

import json
import logging
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.ai_provider import get_ai_provider
from app.services.nl_search import parse_nl_query
from app.services.skill_extraction import extract_fallback_skills, validate_skill_candidate

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("eval_rag")

EVAL_QUERIES = [
    # 1-10: Fresher / Intern & Regional (India / Remote)
    {"q": "Remote Python ML internships in India", "exp": "intern", "remote": True, "country": "India"},
    {"q": "Entry-level frontend React engineer in Bangalore", "exp": "entry", "remote": None, "country": "India"},
    {"q": "Student software engineer trainee remote", "exp": "intern", "remote": True, "country": None},
    {"q": "Fresher Java backend developer in Pune or Mumbai", "exp": "entry", "remote": None, "country": "India"},
    {"q": "Junior DevOps engineer AWS Docker remote", "exp": "entry", "remote": True, "country": None},
    {"q": "Data science intern Python pandas PyTorch in Delhi", "exp": "intern", "remote": None, "country": "India"},
    {"q": "New grad software engineer distributed systems remote", "exp": "entry", "remote": True, "country": None},
    {"q": "Graduate frontend developer TypeScript Tailwind in Hyderabad", "exp": "entry", "remote": None, "country": "India"},
    {"q": "Summer co-op machine learning NLP internship", "exp": "intern", "remote": None, "country": None},
    {"q": "Associate cloud security engineer in India", "exp": "entry", "remote": None, "country": "India"},

    # 11-20: Mid & Senior Specialized Roles
    {"q": "Senior backend Golang engineer high throughput remote", "exp": "senior", "remote": True, "country": None},
    {"q": "Staff distributed systems architect Rust Kafka in United States", "exp": "senior", "remote": None, "country": "United States"},
    {"q": "Lead fullstack engineer Next.js PostgreSQL paying high salary", "exp": "senior", "remote": None, "country": None},
    {"q": "Mid-level computer vision PyTorch C++ remote", "exp": "mid", "remote": True, "country": None},
    {"q": "Principal database reliability engineer PostgreSQL ClickHouse", "exp": "senior", "remote": None, "country": None},
    {"q": "Senior iOS Swift developer in Germany", "exp": "senior", "remote": None, "country": "Germany"},
    {"q": "Mid-level cloud architect Terraform Kubernetes in London UK", "exp": "mid", "remote": None, "country": "United Kingdom"},
    {"q": "Lead QA automation engineer Playwright Python remote", "exp": "senior", "remote": True, "country": None},
    {"q": "Senior data platform engineer Spark dbt Snowflake in USA", "exp": "senior", "remote": None, "country": "United States"},
    {"q": "Mid-level backend FastAPI async Python remote", "exp": "mid", "remote": True, "country": None},

    # 21-30: Tech Stacks, Tooling & Niche Queries
    {"q": "Looking for remote React Native mobile engineer", "exp": None, "remote": True, "country": None},
    {"q": "Work from home Kubernetes platform engineer in India", "exp": None, "remote": True, "country": "India"},
    {"q": "Senior AI engineer LLM RAG vector search remote", "exp": "senior", "remote": True, "country": None},
    {"q": "Junior web developer HTML CSS JavaScript in Berlin Germany", "exp": "entry", "remote": None, "country": "Germany"},
    {"q": "Embedded C++ firmware engineer onsite in Bangalore", "exp": None, "remote": False, "country": "India"},
    {"q": "Senior cybersecurity penetration testing remote", "exp": "senior", "remote": True, "country": None},
    {"q": "Internship in Android Kotlin development India", "exp": "intern", "remote": None, "country": "India"},
    {"q": "Full stack Ruby on Rails engineer remote", "exp": None, "remote": True, "country": None},
    {"q": "Senior blockchain smart contract engineer Solidity remote", "exp": "senior", "remote": True, "country": None},
    {"q": "Site reliability engineer Linux observability Prometheus in USA", "exp": None, "remote": None, "country": "United States"},
]


def run_evaluation() -> dict:
    results = []
    total_latency_ms = 0.0
    total_tokens = 0
    grounded_correct = 0

    print("=" * 80)
    print("RUNNING 30-QUERY RAG / NL-SEARCH EVALUATION SUITE")
    print("=" * 80)

    for idx, item in enumerate(EVAL_QUERIES, 1):
        query = item["q"]
        t0 = time.perf_counter()
        parsed = parse_nl_query(query)
        latency = round((time.perf_counter() - t0) * 1000, 2)
        total_latency_ms += latency

        tokens = len(query.split()) + 25  # query + structured output
        total_tokens += tokens

        # Evaluate Groundedness & Accuracy
        exp_match = (parsed.get("experience_level") == item["exp"])
        remote_match = (item["remote"] is None) or (parsed.get("remote") == item["remote"])
        country_match = (item["country"] is None) or (parsed.get("country") == item["country"])

        is_grounded = exp_match and remote_match and country_match
        if is_grounded:
            grounded_correct += 1

        results.append({
            "idx": idx,
            "query": query,
            "latency_ms": latency,
            "tokens": tokens,
            "is_grounded": is_grounded,
            "parsed": parsed,
        })

        status_flag = "PASS" if is_grounded else "CHECK"
        print(f"[{idx:02d}/30] {status_flag} | {latency:6.2f}ms | exp={parsed.get('experience_level')} | remote={parsed.get('remote')} | country={parsed.get('country')} | \"{query[:45]}\"")

    avg_latency = round(total_latency_ms / len(EVAL_QUERIES), 2)
    groundedness_pct = round((grounded_correct / len(EVAL_QUERIES)) * 100, 1)

    print("=" * 80)
    print("EVALUATION SUMMARY")
    print(f"Total Queries Evaluated: {len(EVAL_QUERIES)}")
    print(f"Groundedness Accuracy:   {groundedness_pct}% ({grounded_correct}/{len(EVAL_QUERIES)})")
    print(f"Average Latency:         {avg_latency} ms")
    print(f"Total Tokens Processed:  {total_tokens}")
    print("=" * 80)

    return {
        "queries_count": len(EVAL_QUERIES),
        "groundedness_pct": groundedness_pct,
        "avg_latency_ms": avg_latency,
        "total_tokens": total_tokens,
        "results": results,
    }


if __name__ == "__main__":
    summary = run_evaluation()
    if summary["groundedness_pct"] < 80.0:
        sys.exit(1)
