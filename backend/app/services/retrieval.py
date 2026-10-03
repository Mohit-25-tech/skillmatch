"""Retrieval upgrades: section-aware chunking, vector store indexing, hybrid RRF search, and reranking."""

import logging
import math
import re
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Job, JobChunk, Resume, ResumeChunk, utcnow
from app.services.embeddings import cosine, encode_many
from app.services.nl_search import coerce_bool
from app.services.vectorstore import get_vector_store

log = logging.getLogger(__name__)

RESUME_SECTION_PATTERNS = [
    ("Summary", re.compile(r"^(?:professional\s+)?(?:summary|profile|objective|about(?:\s+me)?)\b", re.I)),
    ("Skills", re.compile(r"^(?:technical\s+|core\s+)?(?:skills|competencies|technologies|tools|stack)\b", re.I)),
    ("Experience", re.compile(r"^(?:work\s+|professional\s+|employment\s+)?(?:experience|history|background)\b", re.I)),
    ("Projects", re.compile(r"^(?:key\s+|academic\s+|personal\s+)?projects\b", re.I)),
    ("Education", re.compile(r"^(?:academic\s+)?(?:education|qualifications|academics)\b", re.I)),
    ("Certifications", re.compile(r"^(?:certifications?|certificates?|licenses?|awards?|achievements?)\b", re.I)),
]


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks respecting paragraph and sentence boundaries."""
    if not text or not text.strip():
        return []
    clean = re.sub(r"\r\n|\r", "\n", text).strip()
    if len(clean) <= chunk_size:
        return [clean]

    segments = re.split(r"(\n\n+|\n|\.\s+)", clean)
    chunks = []
    current_chunk = ""

    for seg in segments:
        if not seg:
            continue
        if len(current_chunk) + len(seg) <= chunk_size:
            current_chunk += seg
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + seg
            else:
                current_chunk = seg

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    result = [c for c in chunks if len(c) >= 20]
    return result if result else [clean[:chunk_size]]


def chunk_resume_sections(text: str, max_chunk_size: int = 600, overlap: int = 100) -> list[dict[str, Any]]:
    """Section-aware chunker: Summary, Skills, Experience, Projects, Education, Certifications.
    Falls back to ~600-char paragraph chunks with 100 overlap.
    """
    if not text or not text.strip():
        return []

    lines = text.strip().splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_section = "Summary"
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip().rstrip(":")
        matched_section = None
        if len(stripped) <= 60:
            for sec_name, pattern in RESUME_SECTION_PATTERNS:
                if pattern.match(stripped):
                    matched_section = sec_name
                    break

        if matched_section:
            if current_lines:
                sections.append((current_section, current_lines))
                current_lines = []
            current_section = matched_section
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_section, current_lines))

    # If no headers detected, treat entire text as fallback
    if len(sections) <= 1 and (not sections or len(sections[0][1]) < 2):
        raw_chunks = chunk_text(text, chunk_size=max_chunk_size, overlap=overlap)
        return [{"section": "Summary", "text": c, "chunk_idx": i} for i, c in enumerate(raw_chunks)]

    chunks: list[dict[str, Any]] = []
    idx = 0
    for sec_name, sec_lines in sections:
        sec_text = "\n".join(sec_lines).strip()
        if not sec_text:
            continue
        if len(sec_text) <= max_chunk_size:
            chunks.append({"section": sec_name, "text": sec_text, "chunk_idx": idx})
            idx += 1
        else:
            sub_chunks = chunk_text(sec_text, chunk_size=max_chunk_size, overlap=overlap)
            for sc in sub_chunks:
                chunks.append({"section": sec_name, "text": sc, "chunk_idx": idx})
                idx += 1

    return chunks if chunks else [{"section": "Summary", "text": text[:max_chunk_size], "chunk_idx": 0}]


def chunk_job(job: Job, max_chunk_size: int = 600, overlap: int = 100) -> list[dict[str, Any]]:
    """Break job title, company, requirements, and description into structured chunks."""
    header = f"{job.title} at {job.company} ({job.location}). Type: {job.employment_type}."
    full_body = f"{header}\n\n{job.description or ''}"
    raw_chunks = chunk_text(full_body, chunk_size=max_chunk_size, overlap=overlap)

    chunks = []
    for i, rc in enumerate(raw_chunks):
        section = "overview" if i == 0 else "requirements"
        chunks.append({
            "section": section,
            "text": rc,
            "chunk_idx": i,
        })
    return chunks


def index_resume_chunks(db: Session, resume: Resume) -> int:
    """Index resume into vector store chunks, replacing any existing chunks."""
    chunks = chunk_resume_sections(resume.text)
    if not chunks:
        return 0

    texts = [c["text"] for c in chunks]
    embeddings = encode_many(texts)

    ids = [f"resume_{resume.id}_{c['chunk_idx']}" for c in chunks]
    metadatas = [
        {
            "resume_id": resume.id,
            "user_id": resume.user_id,
            "chunk_idx": c["chunk_idx"],
            "section": c["section"],
        }
        for c in chunks
    ]

    valid_items = [
        (cid, emb, meta, doc)
        for cid, emb, meta, doc in zip(ids, embeddings, metadatas, texts, strict=False)
        if emb is not None
    ]

    if not valid_items:
        return 0

    v_ids = [x[0] for x in valid_items]
    v_embs = [x[1] for x in valid_items]
    v_metas = [x[2] for x in valid_items]
    v_docs = [x[3] for x in valid_items]

    vstore = get_vector_store()
    vstore.delete_by_filter("resume_chunks", {"resume_id": resume.id})
    vstore.upsert("resume_chunks", v_ids, v_embs, v_metas, v_docs)
    log.info("Indexed %d chunks for resume #%d", len(v_ids), resume.id)
    return len(v_ids)


def delete_resume_chunks(db: Session, resume_id: int) -> None:
    """Remove resume chunks from vector store."""
    vstore = get_vector_store()
    vstore.delete_by_filter("resume_chunks", {"resume_id": resume_id})


def index_job_chunks(db: Session, job: Job) -> int:
    """Index job into vector store chunks."""
    chunks = chunk_job(job)
    if not chunks:
        return 0

    texts = [c["text"] for c in chunks]
    embeddings = encode_many(texts)

    ids = [f"job_{job.id}_{c['chunk_idx']}" for c in chunks]
    metadatas = [
        {
            "job_id": job.id,
            "chunk_idx": c["chunk_idx"],
            "section": c["section"],
            "country": job.country or "",
            "is_remote": bool(job.remote),
            "level": job.experience_level or "",
            "status": "active" if job.active else "closed",
        }
        for c in chunks
    ]

    valid_items = [
        (cid, emb, meta, doc)
        for cid, emb, meta, doc in zip(ids, embeddings, metadatas, texts, strict=False)
        if emb is not None
    ]

    if not valid_items:
        return 0

    v_ids = [x[0] for x in valid_items]
    v_embs = [x[1] for x in valid_items]
    v_metas = [x[2] for x in valid_items]
    v_docs = [x[3] for x in valid_items]

    vstore = get_vector_store()
    vstore.upsert("job_chunks", v_ids, v_embs, v_metas, v_docs)
    return len(v_ids)


def remove_job_chunks(db: Session, job_id: int) -> None:
    """Remove or mark closed job chunks."""
    vstore = get_vector_store()
    vstore.delete_by_filter("job_chunks", {"job_id": job_id})


def best_chunk_similarity(text_a: str, text_b: str) -> float:
    """Compute highest cosine similarity across all chunk pairs of text_a and text_b."""
    if not text_a or not text_b:
        return 0.0
    chunks_a = chunk_text(text_a, chunk_size=400, overlap=80)
    chunks_b = chunk_text(text_b, chunk_size=400, overlap=80)

    all_chunks = chunks_a + chunks_b
    vectors = encode_many(all_chunks)

    vecs_a = [v for v in vectors[: len(chunks_a)] if v is not None]
    vecs_b = [v for v in vectors[len(chunks_a) :] if v is not None]

    if not vecs_a or not vecs_b:
        return 0.0

    max_sim = 0.0
    for va in vecs_a:
        for vb in vecs_b:
            sim = cosine(va, vb)
            if sim > max_sim:
                max_sim = sim
    return round(max_sim, 2)


def cross_encoder_rerank(
    query: str, candidates: list[dict[str, Any]], top_k: int = 50
) -> list[dict[str, Any]]:
    """Rerank candidates using SentenceTransformers CrossEncoder only if explicitly enabled, else lexical."""
    if not candidates:
        return []

    settings = get_settings()
    if settings.reranker == "cross-encoder":
        try:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
            pairs = [[query, f"{c.get('title', '')} {c.get('description', '')[:500]}"] for c in candidates]
            scores = model.predict(pairs)
            for cand, score in zip(candidates, scores):
                cand["rerank_score"] = float(score)
            return sorted(candidates, key=lambda x: x.get("rerank_score", 0.0), reverse=True)[:top_k]
        except Exception as err:
            log.debug("CrossEncoder not loaded (%s); using lexical ranker fallback", err)

    # Fast deterministic lexical fallback
    q_tokens = set(re.findall(r"\w+", query.casefold()))
    for c in candidates:
        doc_text = f"{c.get('title', '')} {c.get('company', '')} {c.get('description', '')[:1000]}".casefold()
        match_count = sum(1 for token in q_tokens if token in doc_text)
        term_coverage = (match_count / max(1, len(q_tokens))) * 50.0
        existing_score = float(c.get("score", 0.0) or 0.0)
        c["rerank_score"] = round(existing_score * 0.6 + term_coverage * 0.8, 2)
    return sorted(candidates, key=lambda x: x.get("rerank_score", 0.0), reverse=True)[:top_k]


def hybrid_search_jobs(
    db: Session,
    query_text: str,
    query_vector: list[float] | None = None,
    limit: int = 50,
    filters: dict | None = None,
) -> list[Job]:
    """Perform hybrid search: vector top-k from store -> hydrate from Postgres -> fuse with keyword via RRF."""
    filters = filters or {}
    base_query = select(Job).where(Job.active.is_(True))

    if filters.get("country"):
        c_filter = filters["country"].strip()
        if c_filter.lower() in {"india + remote worldwide", "india + remote", "india_remote"}:
            base_query = base_query.where(or_(Job.country.ilike("%India%"), Job.remote.is_(True)))
        else:
            base_query = base_query.where(Job.country.ilike(f"%{c_filter}%"))
    remote_val = coerce_bool(filters.get("remote"))
    if remote_val is not None:
        base_query = base_query.where(Job.remote.is_(remote_val))
    if filters.get("experience_level"):
        base_query = base_query.where(Job.experience_level == filters["experience_level"])
    if filters.get("salary_disclosed"):
        base_query = base_query.where(or_(Job.salary_min.is_not(None), Job.salary_max.is_not(None)))

    # 1. Text keyword search
    text_results: list[Job] = []
    tokens = [t.strip() for t in re.findall(r"\w+", query_text) if len(t.strip()) > 2]
    if tokens:
        clauses = [
            or_(
                Job.title.ilike(f"%{t}%"),
                Job.description.ilike(f"%{t}%"),
                Job.company.ilike(f"%{t}%"),
            )
            for t in tokens[:6]
        ]
        text_query = base_query.where(or_(*clauses)).limit(limit * 2)
        text_results = list(db.scalars(text_query).all())
    else:
        text_results = list(db.scalars(base_query.limit(limit)).all())

    # 2. Vector search via vector store
    vector_results: list[Job] = []
    if not query_vector and query_text and get_settings().semantic_enabled:
        q_vecs = encode_many([query_text])
        if q_vecs and q_vecs[0] is not None:
            query_vector = q_vecs[0]

    if query_vector:
        vstore = get_vector_store()
        v_filter = {"status": "active"}
        if filters.get("remote") is not None:
            v_filter["is_remote"] = filters["remote"]
        if filters.get("experience_level"):
            v_filter["level"] = filters["experience_level"]

        chunk_hits = vstore.query("job_chunks", query_vector, top_k=limit * 3, filter=v_filter)
        if chunk_hits:
            job_ids = list(
                dict.fromkeys(
                    h["metadata"]["job_id"]
                    for h in chunk_hits
                    if "metadata" in h and "job_id" in h["metadata"]
                )
            )
            if job_ids:
                hydrated = list(db.scalars(base_query.where(Job.id.in_(job_ids))).all())
                hydrated_map = {j.id: j for j in hydrated}
                vector_results = [hydrated_map[jid] for jid in job_ids if jid in hydrated_map]

    # Fallback to direct Job.embedding if chunk index is empty
    if not vector_results and query_vector and get_settings().semantic_enabled:
        jobs_with_vec = list(db.scalars(base_query.where(Job.embedding.is_not(None))).all())
        scored = []
        for j in jobs_with_vec:
            if j.embedding:
                sim = cosine(query_vector, j.embedding)
                scored.append((sim, j))
        scored.sort(key=lambda x: x[0], reverse=True)
        vector_results = [j for _, j in scored[: limit * 2]]

    # 3. Reciprocal Rank Fusion (RRF)
    rrf_scores: dict[int, float] = {}
    job_map: dict[int, Job] = {}

    for rank, job in enumerate(text_results):
        job_map[job.id] = job
        rrf_scores[job.id] = rrf_scores.get(job.id, 0.0) + (1.0 / (60.0 + rank + 1))

    for rank, job in enumerate(vector_results):
        job_map[job.id] = job
        rrf_scores[job.id] = rrf_scores.get(job.id, 0.0) + (1.0 / (60.0 + rank + 1))

    if not rrf_scores:
        return list(db.scalars(base_query.order_by(Job.id.desc()).limit(limit)).all())

    sorted_job_ids = sorted(rrf_scores.keys(), key=lambda jid: rrf_scores[jid], reverse=True)
    return [job_map[jid] for jid in sorted_job_ids[:limit]]
