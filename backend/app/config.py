from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./skillmatch.db"
    jwt_secret: str = "development-only-change-before-deploying-12345"
    environment: str = "development"
    cors_origins: str = (
        "http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:8080"
    )
    frontend_url: str = "http://localhost:5173"
    cookie_secure: bool = False
    semantic_enabled: bool = True
    embed_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_embed_model: str = "all-minilm:l6"
    embed_dim: int = 384
    embedding_model: str = "all-minilm:l6"
    embedding_version: int = 1
    llm_provider: str = "rules"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_fast_model: str = "llama-3.1-8b-instant"
    vector_backend: str = "pgvector"
    chroma_dir: str = "./data/chroma"
    reranker: str = "lexical"
    seed_on_start: bool = False
    demo_mode: bool = False
    ingestion_config: str = "sources.yaml"
    ingestion_user_agent: str = (
        "SkillMatchAI/2.0 (public API reader; contact: configure INGESTION_USER_AGENT)"
    )
    ingestion_timeout: float = 20
    ingestion_max_pages: int = 20
    ingestion_request_delay: float = 1.0
    worker_poll_seconds: int = 15
    job_max_age_days: int = 120
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    embedding_dimensions: int = 384
    match_semantic_weight: float = 0.50
    match_skills_weight: float = 0.30
    match_experience_weight: float = 0.15
    match_location_weight: float = 0.05
    insight_cache_seconds: int = 60
    smtp_host: str = ""
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    smtp_from: str = "noreply@example.invalid"
    ollama_enabled: bool = True
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3:latest"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    ai_provider: str = "auto"
    assistant_debug: bool = False
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    @model_validator(mode="after")
    def validate_configuration(self):
        weights = [
            self.match_semantic_weight,
            self.match_skills_weight,
            self.match_experience_weight,
            self.match_location_weight,
        ]
        if any(w < 0 or w > 1 for w in weights) or sum(weights) <= 0:
            raise ValueError("Matching weights must be between 0 and 1 with a positive total")
        if self.embed_provider == "ollama":
            self.embedding_model = self.ollama_embed_model
        if self.embed_dim != self.embedding_dimensions:
            self.embedding_dimensions = self.embed_dim
        if self.embedding_dimensions != 384:
            raise ValueError("This schema requires 384-dimensional embeddings")
        if (
            self.ingestion_timeout <= 0
            or not 1 <= self.ingestion_max_pages <= 100
            or self.ingestion_request_delay < 0
            or self.worker_poll_seconds < 1
        ):
            raise ValueError("Invalid ingestion timing or page limit")
        return self

    def validate_production(self) -> None:
        if self.environment == "production":
            if self.demo_mode:
                raise ValueError("Demo mode is disabled in production")
            if (
                len(self.jwt_secret) < 32
                or "change" in self.jwt_secret
                or "replace" in self.jwt_secret
                or "PLACEHOLDER" in self.jwt_secret
            ):
                raise ValueError("Set a strong JWT_SECRET for production")
            if not self.database_url.startswith(("postgresql", "postgres://")) or not self.cookie_secure:
                raise ValueError("Production requires PostgreSQL and COOKIE_SECURE=true")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production()
    return settings
