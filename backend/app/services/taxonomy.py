"""Shared, canonical taxonomy for resume and job extraction."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Skill
from app.seed_data import SKILLS

EXTRA_SKILLS = [
    "Large Language Models",
    "Generative AI",
    "Fine Tuning",
    "PEFT",
    "LoRA",
    "Sentence Transformers",
    "Vector Search",
    "Computer Science",
    "NumPy",
    "OpenCV",
    "FastAPI",
    "Retrieval Augmented Generation",
]
ALIASES = {
    "js": "JavaScript",
    "javascript es6": "JavaScript",
    "ts": "TypeScript",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "scikit-learn": "Scikit-learn",
    "react.js": "React",
    "reactjs": "React",
    "nodejs": "Node.js",
    "node js": "Node.js",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "llm": "Large Language Models",
    "llms": "Large Language Models",
    "large language model": "Large Language Models",
    "genai": "Generative AI",
    "generative artificial intelligence": "Generative AI",
    "ml": "Machine Learning",
    "machine-learning": "Machine Learning",
    "nlp": "Natural Language Processing",
    "natural-language processing": "Natural Language Processing",
    "ml ops": "MLOps",
    "retrieval augmented generation": "RAG",
    "retrieval-augmented generation": "RAG",
    "huggingface": "Hugging Face",
    "hugging face transformers": "Transformers",
    "fine-tuning": "Fine Tuning",
    "fine tuning": "Fine Tuning",
    "k8s": "Kubernetes",
    "amazon web services": "AWS",
    "gcp": "Google Cloud",
    "ci cd": "CI/CD",
}


def ensure_taxonomy(db: Session) -> list[Skill]:
    existing = {s.name.casefold(): s for s in db.scalars(select(Skill)).all()}
    for item in [*SKILLS, *({"name": n, "category": "AI & ML"} for n in EXTRA_SKILLS)]:
        if item["name"].casefold() not in existing:
            skill = Skill(**item)
            db.add(skill)
            existing[item["name"].casefold()] = skill
    db.flush()
    return list(existing.values())
