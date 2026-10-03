import json
import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.db import SessionLocal
from app.limits import limiter
from app.routers import ai, analytics, auth, candidates, ingestion, jobs, product

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("skillmatch")
settings = get_settings()
app = FastAPI(
    title="SkillMatch AI",
    version="1.0.0",
    description="Resume intelligence and transparent job matching",
    docs_url=None,
    redoc_url=None,
)


@app.get("/docs", include_in_schema=False)
def documentation():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="SkillMatch AI — API documentation",
        swagger_js_url="/docs-assets/swagger-ui-bundle.js",
        swagger_css_url="/docs-assets/swagger-ui.css",
        swagger_favicon_url="/docs-assets/favicon-32x32.png",
        swagger_ui_parameters={"validatorUrl": None},
    )


local_docs = Path(__file__).resolve().parents[2] / "frontend" / "public" / "docs-assets"
if local_docs.exists():
    app.mount("/docs-assets", StaticFiles(directory=local_docs), name="docs-assets")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = uuid.uuid4().hex
    start = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - start) * 1000),
            }
        )
    )
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "This change conflicts with an existing record"})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.exception("unhandled_error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


@app.on_event("startup")
def startup_checks():
    from app.services.embeddings import check_embedder_health

    ok, msg = check_embedder_health()
    if not ok:
        logger.warning("SEMANTIC SEARCH DEGRADED: %s", msg)
    else:
        logger.info("Semantic search backend ready: %s", msg)


@app.get("/api/v1/health", tags=["Health"])
def health():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "database unavailable"})

    from app.services.embeddings import check_embedder_health

    embed_ok, embed_msg = check_embedder_health()
    semantic_status = "healthy" if embed_ok else "degraded"

    return {
        "status": "ok",
        "semantic_search": semantic_status,
        "semantic_message": embed_msg,
        "embed_provider": settings.embed_provider,
        "embed_model": settings.ollama_embed_model if settings.embed_provider == "ollama" else settings.embedding_model,
    }


for router in (
    auth.router,
    jobs.router,
    candidates.router,
    analytics.router,
    ingestion.router,
    product.router,
    ai.router,
):
    app.include_router(router, prefix="/api/v1")
