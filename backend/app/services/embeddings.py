import logging
import math
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)


def cosine(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity percentage between two vectors [0.0 - 100.0]."""
    denominator = math.sqrt(sum(x * x for x in left) * sum(x * x for x in right))
    return (
        max(0.0, min(100.0, 100.0 * sum(a * b for a, b in zip(left, right, strict=True)) / denominator))
        if denominator
        else 0.0
    )


def normalize_l2(vector: list[float]) -> list[float]:
    """L2-normalize a vector so its Euclidean length is 1.0."""
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0.0:
        return [x / norm for x in vector]
    return vector


class Embedder(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float] | None]:
        """Embed a list of texts into 384-dimensional dense vectors."""
        ...

    @abstractmethod
    def check_health(self) -> tuple[bool, str]:
        """Check if backend is reachable and model is ready."""
        ...


class OllamaEmbedder(Embedder):
    """Embedder using Ollama local HTTP API (/api/embed)."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        embed_dim: int = 384,
        batch_size: int = 32,
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_embed_model
        self.embed_dim = embed_dim or settings.embed_dim
        self.batch_size = max(1, min(batch_size, 32))
        self.timeout = timeout
        self.max_retries = max_retries

    def check_health(self) -> tuple[bool, str]:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    return False, f"Ollama returned HTTP {resp.status_code}"
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                # Check for exact match or prefix match (e.g. all-minilm:l6 vs all-minilm:latest)
                target = self.model.casefold()
                found = any(m.casefold() == target or m.casefold().startswith(target.split(":")[0]) for m in models)
                if not found:
                    return False, f"run: ollama pull {self.model}"
                return True, f"Ollama {self.model} ready"
        except Exception as err:
            return False, f"Ollama unreachable at {self.base_url} ({type(err).__name__}). run: ollama pull {self.model}"

    def embed(self, texts: list[str]) -> list[list[float] | None]:
        if not texts:
            return []
        settings = get_settings()
        if not settings.semantic_enabled:
            return [None] * len(texts)

        results: list[list[float] | None] = []
        # Defensively truncate to <= 800 chars because all-minilm context is ~256 tokens
        clean_texts = [t[:800].strip() if t and t.strip() else "empty" for t in texts]

        for i in range(0, len(clean_texts), self.batch_size):
            batch = clean_texts[i : i + self.batch_size]
            batch_vectors: list[list[float] | None] = [None] * len(batch)

            last_exc = None
            for attempt in range(self.max_retries):
                try:
                    with httpx.Client(timeout=self.timeout) as client:
                        resp = client.post(
                            f"{self.base_url}/api/embed",
                            json={
                                "model": self.model,
                                "input": batch,
                                "keep_alive": "30m",
                            },
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            raw_embeddings = data.get("embeddings", [])
                            if len(raw_embeddings) == len(batch):
                                for idx, emb in enumerate(raw_embeddings):
                                    if len(emb) == self.embed_dim:
                                        batch_vectors[idx] = normalize_l2(emb)
                                    else:
                                        raise ValueError(
                                            f"Expected {self.embed_dim} dimensions from Ollama, got {len(emb)}"
                                        )
                                last_exc = None
                                break
                            else:
                                raise ValueError(
                                    f"Expected {len(batch)} embeddings from Ollama, got {len(raw_embeddings)}"
                                )
                        else:
                            raise RuntimeError(f"Ollama embed returned HTTP {resp.status_code}: {resp.text}")
                except Exception as err:
                    last_exc = err
                    wait_time = 0.5 * (2**attempt)
                    log.warning(
                        "ollama_embed_retry attempt=%d/%d error=%s wait=%.2fs",
                        attempt + 1,
                        self.max_retries,
                        type(err).__name__,
                        wait_time,
                    )
                    time.sleep(wait_time)

            if last_exc:
                log.error("ollama_embed_failed error=%s", last_exc)

            results.extend(batch_vectors)

        return results


class SentenceTransformersEmbedder(Embedder):
    """Optional in-process SentenceTransformer embedder."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or get_settings().embedding_model
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def check_health(self) -> tuple[bool, str]:
        try:
            self._load_model()
            return True, f"sentence-transformers {self.model_name} loaded"
        except Exception as err:
            return False, f"Failed to load sentence-transformers: {err}"

    def embed(self, texts: list[str]) -> list[list[float] | None]:
        if not texts:
            return []
        if not get_settings().semantic_enabled:
            return [None] * len(texts)
        try:
            m = self._load_model()
            clean = [t[:800] for t in texts]
            vectors = m.encode(clean, batch_size=32, normalize_embeddings=True)
            if vectors.shape[1] != 384:
                raise ValueError("Configured model must have 384 dimensions")
            return [v.tolist() for v in vectors]
        except Exception as error:
            log.warning("sentence_transformers_unavailable error=%s", error)
            return [None] * len(texts)


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    settings = get_settings()
    if settings.embed_provider == "sentence-transformers":
        log.info("using sentence-transformers embedder: %s", settings.embedding_model)
        return SentenceTransformersEmbedder(settings.embedding_model)
    log.info("using Ollama embedder: %s at %s", settings.ollama_embed_model, settings.ollama_base_url)
    return OllamaEmbedder(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embed_model,
        embed_dim=settings.embed_dim,
    )


def check_embedder_health() -> tuple[bool, str]:
    """Check health of configured embedding backend."""
    return get_embedder().check_health()


def encode_many(texts: list[str]) -> list[list[float] | None]:
    """Module-level entry point used across application services."""
    return get_embedder().embed(texts)
