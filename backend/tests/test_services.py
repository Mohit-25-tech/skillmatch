from unittest.mock import patch

import pytest

from app.models import Job, Resume, Skill
from app.seed_data import SKILLS, generate_jobs
from app.services.matching import calculate_match
from app.services.parsing import extract_skills, parse_resume


def test_skill_extraction_handles_aliases_and_word_boundaries():
    assert extract_skills(
        "TypeScript with JS and react.js; not a Pythonista.", ["TypeScript", "JavaScript", "React", "Python"]
    ) == ["JavaScript", "React", "TypeScript"]


def test_empty_skill_matching_is_safe():
    result = calculate_match(
        Resume(text="A long professional background", skills=[]),
        Job(title="Engineer", description="Build systems", skills=[]),
    )
    assert result["score"] == 0
    assert result["missing"] == []


def test_semantic_hybrid_weight_and_fallback():
    resume = Resume(text="Python developer", skills=[Skill(name="Python")])
    job = Job(
        title="Engineer", description="Python and SQL", skills=[Skill(name="Python"), Skill(name="SQL")]
    )

    from app.config import Settings

    with patch("app.services.matching.get_settings", return_value=Settings(semantic_enabled=True)):
        result = calculate_match(resume, job, semantic_value=80)
        assert result["score"] == 59.4
        assert calculate_match(resume, job)["method"] == "keyword"


def test_seed_catalog_integrity():
    names = {s["name"] for s in SKILLS}
    assert len(SKILLS) == len(names) == 300
    jobs = generate_jobs()
    assert len(jobs) == 200
    assert all(set(j["skills"]) <= names for j in jobs)
    assert all(j["salary_max"] >= j["salary_min"] >= 0 for j in jobs)


def test_scanned_pdf_rejected():
    with patch("app.services.parsing.pdfplumber.open") as pdf:
        pdf.return_value.__enter__.return_value.pages = []
        with pytest.raises(Exception) as error:
            parse_resume(b"%PDF-1.4", "resume.pdf")
        assert error.value.status_code == 422
