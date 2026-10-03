"""Vector store abstraction layer supporting ChromaStore and PgVectorStore.

PostgreSQL remains the primary source of truth; vector store acts as an index.
"""

from abc import ABC, abstractmethod
import json
import logging
import os
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import Job, JobChunk, ResumeChunk
from app.services.embeddings import cosine

log = logging.getLogger(__name__)


class VectorStore(ABC):
    @abstractmethod
    def upsert(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        """Upsert documents, embeddings, and metadata into a named collection."""
        ...

    @abstractmethod
    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query nearest items by vector similarity with optional metadata filter.
        
        Returns: list of dicts with 'id', 'score' (0.0-100.0), 'metadata', and 'document'.
        """
        ...

    @abstractmethod
    def delete_by_filter(self, collection_name: str, filter: dict[str, Any]) -> None:
        """Delete items matching a metadata filter."""
        ...

    @abstractmethod
    def delete(self, collection_name: str, ids: list[str]) -> None:
        """Delete specific items by ID."""
        ...

    @abstractmethod
    def count(self, collection_name: str) -> int:
        """Get total count of vectors in collection."""
        ...


from contextlib import contextmanager

class PgVectorStore(VectorStore):
    """PostgreSQL / SQLite backed vector store storing chunks in relational tables."""

    def __init__(self, db_factory=SessionLocal):
        self.db_factory = db_factory

    @contextmanager
    def _get_session(self):
        if isinstance(self.db_factory, Session):
            yield self.db_factory
        elif callable(self.db_factory):
            res = self.db_factory()
            if hasattr(res, "__enter__") and hasattr(res, "__exit__"):
                with res as sess:
                    yield sess
            else:
                yield res
        else:
            with SessionLocal() as sess:
                yield sess


    def upsert(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        if not ids:
            return

        with self._get_session() as db:
            if collection_name == "job_chunks":
                for cid, emb, meta, doc in zip(ids, embeddings, metadatas, documents, strict=False):
                    existing = db.get(JobChunk, cid)
                    if not existing:
                        existing = JobChunk(id=cid)
                        db.add(existing)
                    existing.job_id = meta.get("job_id")
                    existing.chunk_idx = meta.get("chunk_idx", 0)
                    existing.section = meta.get("section")
                    existing.country = meta.get("country")
                    existing.is_remote = bool(meta.get("is_remote", False))
                    existing.level = meta.get("level")
                    existing.status = meta.get("status", "active")
                    existing.text = doc
                    existing.embedding = emb
                db.commit()

            elif collection_name == "resume_chunks":
                for cid, emb, meta, doc in zip(ids, embeddings, metadatas, documents, strict=False):
                    existing = db.get(ResumeChunk, cid)
                    if not existing:
                        existing = ResumeChunk(id=cid)
                        db.add(existing)
                    existing.resume_id = meta.get("resume_id")
                    existing.user_id = meta.get("user_id")
                    existing.chunk_idx = meta.get("chunk_idx", 0)
                    existing.section = meta.get("section", "Summary")
                    existing.text = doc
                    existing.embedding = emb
                db.commit()

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        filter = filter or {}
        with self._get_session() as db:
            if collection_name == "job_chunks":
                stmt = select(JobChunk).where(JobChunk.embedding.is_not(None))
                if "job_id" in filter:
                    stmt = stmt.where(JobChunk.job_id == filter["job_id"])
                if "status" in filter:
                    stmt = stmt.where(JobChunk.status == filter["status"])
                if "is_remote" in filter:
                    stmt = stmt.where(JobChunk.is_remote == bool(filter["is_remote"]))
                if "country" in filter:
                    stmt = stmt.where(JobChunk.country.ilike(f"%{filter['country']}%"))
                if "level" in filter:
                    stmt = stmt.where(JobChunk.level == filter["level"])

                rows = list(db.scalars(stmt).all())
                scored = []
                for row in rows:
                    if row.embedding:
                        sim = cosine(query_embedding, row.embedding)
                        scored.append({
                            "id": row.id,
                            "score": round(sim, 2),
                            "metadata": {
                                "job_id": row.job_id,
                                "chunk_idx": row.chunk_idx,
                                "section": row.section,
                                "country": row.country,
                                "is_remote": row.is_remote,
                                "level": row.level,
                                "status": row.status,
                            },
                            "document": row.text,
                        })
                scored.sort(key=lambda x: x["score"], reverse=True)
                return scored[:top_k]

            elif collection_name == "resume_chunks":
                stmt = select(ResumeChunk).where(ResumeChunk.embedding.is_not(None))
                if "user_id" in filter:
                    stmt = stmt.where(ResumeChunk.user_id == filter["user_id"])
                if "resume_id" in filter:
                    stmt = stmt.where(ResumeChunk.resume_id == filter["resume_id"])
                if "section" in filter:
                    stmt = stmt.where(ResumeChunk.section == filter["section"])

                rows = list(db.scalars(stmt).all())
                scored = []
                for row in rows:
                    if row.embedding:
                        sim = cosine(query_embedding, row.embedding)
                        scored.append({
                            "id": row.id,
                            "score": round(sim, 2),
                            "metadata": {
                                "resume_id": row.resume_id,
                                "user_id": row.user_id,
                                "chunk_idx": row.chunk_idx,
                                "section": row.section,
                            },
                            "document": row.text,
                        })
                scored.sort(key=lambda x: x["score"], reverse=True)
                return scored[:top_k]

            return []

    def delete_by_filter(self, collection_name: str, filter: dict[str, Any]) -> None:
        if not filter:
            return
        with self._get_session() as db:
            if collection_name == "job_chunks":
                stmt = delete(JobChunk)
                if "job_id" in filter:
                    stmt = stmt.where(JobChunk.job_id == filter["job_id"])
                if "status" in filter:
                    stmt = stmt.where(JobChunk.status == filter["status"])
                db.execute(stmt)
                db.commit()
            elif collection_name == "resume_chunks":
                stmt = delete(ResumeChunk)
                if "resume_id" in filter:
                    stmt = stmt.where(ResumeChunk.resume_id == filter["resume_id"])
                if "user_id" in filter:
                    stmt = stmt.where(ResumeChunk.user_id == filter["user_id"])
                db.execute(stmt)
                db.commit()

    def delete(self, collection_name: str, ids: list[str]) -> None:
        if not ids:
            return
        with self._get_session() as db:
            if collection_name == "job_chunks":
                db.execute(delete(JobChunk).where(JobChunk.id.in_(ids)))
                db.commit()
            elif collection_name == "resume_chunks":
                db.execute(delete(ResumeChunk).where(ResumeChunk.id.in_(ids)))
                db.commit()

    def count(self, collection_name: str) -> int:
        with self._get_session() as db:
            if collection_name == "job_chunks":
                return db.scalar(select(func.count()).select_from(JobChunk)) or 0
            elif collection_name == "resume_chunks":
                return db.scalar(select(func.count()).select_from(ResumeChunk)) or 0
            return 0


class ChromaStore(VectorStore):
    """Chroma vector store using a persistent client with precomputed embeddings."""

    def __init__(self, persist_dir: str | None = None):
        settings = get_settings()
        self.persist_dir = persist_dir or settings.chroma_dir
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = None
        self._fallback = PgVectorStore()

    def _get_client(self):
        if self._client is None:
            try:
                import chromadb

                self._client = chromadb.PersistentClient(path=self.persist_dir)
            except Exception as err:
                log.warning("ChromaDB initialization failed (%s); falling back to PgVectorStore", err)
                return None
        return self._client

    def _get_collection(self, collection_name: str):
        client = self._get_client()
        if client is None:
            return None
        return client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,  # Precomputed embeddings only
        )

    def upsert(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        # Dual-write: always maintain Postgres as source of truth
        self._fallback.upsert(collection_name, ids, embeddings, metadatas, documents)

        coll = self._get_collection(collection_name)
        if coll is None:
            return

        cleaned_metas = []
        for m in metadatas:
            # Chroma requires primitives: str, int, float, bool
            cleaned = {}
            for k, v in m.items():
                if v is None:
                    continue
                if isinstance(v, (str, int, float, bool)):
                    cleaned[k] = v
                else:
                    cleaned[k] = str(v)
            cleaned_metas.append(cleaned)

        try:
            coll.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=cleaned_metas,
                documents=documents,
            )
        except Exception as err:
            log.warning("Chroma upsert failed (%s)", err)

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        coll = self._get_collection(collection_name)
        if coll is None:
            return self._fallback.query(collection_name, query_embedding, top_k, filter)

        where_clause = None
        if filter:
            # Chroma syntax: where={'field': 'val'} or where={'$and': [...]}
            items = []
            for k, v in filter.items():
                if v is not None:
                    items.append({k: v})
            if len(items) == 1:
                where_clause = items[0]
            elif len(items) > 1:
                where_clause = {"$and": items}

        try:
            kwargs: dict[str, Any] = {
                "query_embeddings": [query_embedding],
                "n_results": min(top_k, max(1, coll.count())),
            }
            if where_clause:
                kwargs["where"] = where_clause

            results = coll.query(**kwargs)
            res_ids = results.get("ids", [[]])[0]
            res_docs = results.get("documents", [[]])[0]
            res_metas = results.get("metadatas", [[]])[0]
            res_dists = results.get("distances", [[]])[0] if "distances" in results else [0.0] * len(res_ids)

            output = []
            for cid, doc, meta, dist in zip(res_ids, res_docs, res_metas, res_dists, strict=False):
                # Cosine distance to similarity percentage
                score = max(0.0, min(100.0, round((1.0 - (dist or 0.0)) * 100.0, 2)))
                output.append({
                    "id": cid,
                    "score": score,
                    "metadata": meta or {},
                    "document": doc,
                })
            return output
        except Exception as err:
            log.warning("Chroma query failed (%s); falling back to PgVectorStore", err)
            return self._fallback.query(collection_name, query_embedding, top_k, filter)

    def delete_by_filter(self, collection_name: str, filter: dict[str, Any]) -> None:
        self._fallback.delete_by_filter(collection_name, filter)
        coll = self._get_collection(collection_name)
        if coll is None or not filter:
            return
        try:
            coll.delete(where=filter)
        except Exception as err:
            log.warning("Chroma delete_by_filter failed (%s)", err)

    def delete(self, collection_name: str, ids: list[str]) -> None:
        self._fallback.delete(collection_name, ids)
        coll = self._get_collection(collection_name)
        if coll is None or not ids:
            return
        try:
            coll.delete(ids=ids)
        except Exception as err:
            log.warning("Chroma delete failed (%s)", err)

    def count(self, collection_name: str) -> int:
        coll = self._get_collection(collection_name)
        if coll is None:
            return self._fallback.count(collection_name)
        try:
            return coll.count()
        except Exception:
            return self._fallback.count(collection_name)


_vector_store_instance: VectorStore | None = None


def get_vector_store(backend: str | None = None) -> VectorStore:
    global _vector_store_instance
    target_backend = (backend or get_settings().vector_backend).lower()
    if target_backend == "chroma":
        return ChromaStore()
    return PgVectorStore()
