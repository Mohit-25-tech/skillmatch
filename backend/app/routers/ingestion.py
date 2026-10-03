from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.ingestion.adapters import ADAPTERS
from app.models import IngestionRun, IngestionSource, User, WorkerHeartbeat, WorkItem
from app.security import roles

router = APIRouter(prefix="/admin/ingestion", tags=["Ingestion administration"])


class SourceInput(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9_-]{1,150}$")
    kind: str
    config: dict = Field(default_factory=dict)
    enabled: bool = False
    interval_minutes: int = Field(default=360, ge=60, le=10080)


class SourceUpdate(BaseModel):
    enabled: bool
    interval_minutes: int | None = Field(default=None, ge=60, le=10080)
    config: dict | None = None


def validate_config(config: dict) -> None:
    if config.get("role_scope", "all") not in {"all", "cse"}:
        raise HTTPException(422, "role_scope must be all or cse")
    if any(
        k not in {"slug", "company", "region", "country", "query", "thread_id", "max_comments", "role_scope"}
        for k in config
    ):
        raise HTTPException(422, "Unsupported configuration key; credentials belong in environment variables")
    if any(not isinstance(v, (str, int)) or len(str(v)) > 200 for v in config.values()):
        raise HTTPException(422, "Configuration values must be short strings or integers")
    if "max_comments" in config and (
        not isinstance(config["max_comments"], int) or not 1 <= config["max_comments"] <= 1000
    ):
        raise HTTPException(422, "max_comments must be between 1 and 1000")


def source_public(source: IngestionSource) -> dict:
    return {
        key: getattr(source, key)
        for key in (
            "id",
            "key",
            "kind",
            "config",
            "enabled",
            "interval_minutes",
            "status",
            "stats",
            "last_run_at",
            "last_success_at",
            "last_error",
            "next_run_at",
        )
    }


@router.get("")
def sources(user: User = Depends(roles("admin")), db: Session = Depends(get_db)) -> dict:
    heartbeat = db.get(WorkerHeartbeat, "ingestion")
    return {
        "items": [source_public(s) for s in db.scalars(select(IngestionSource).order_by(IngestionSource.id))],
        "worker_last_seen": heartbeat.seen_at if heartbeat else None,
    }


@router.post("", status_code=201)
def add_source(
    body: SourceInput, user: User = Depends(roles("admin")), db: Session = Depends(get_db)
) -> dict:
    if body.kind not in ADAPTERS:
        raise HTTPException(422, "Unknown adapter")
    validate_config(body.config)
    if any(
        k not in {"slug", "company", "region", "country", "query", "thread_id", "max_comments", "role_scope"}
        for k in body.config
    ):
        raise HTTPException(422, "Unsupported configuration key; credentials belong in environment variables")
    if body.kind in {"remotive", "remoteok"} and body.interval_minutes < 360:
        raise HTTPException(422, "Use an interval of at least 360 minutes for this source")
    source = IngestionSource(**body.model_dump())
    db.add(source)
    db.commit()
    return source_public(source)


@router.patch("/{source_id}")
def toggle(
    source_id: int, body: SourceUpdate, user: User = Depends(roles("admin")), db: Session = Depends(get_db)
) -> dict:
    source = db.get(IngestionSource, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    if body.interval_minutes is not None:
        if source.kind in {"remotive", "remoteok"} and body.interval_minutes < 360:
            raise HTTPException(422, "Minimum interval is 360 minutes for this source")
        source.interval_minutes = body.interval_minutes
    source.enabled = body.enabled
    if body.config is not None:
        validate_config(body.config)
        source.config = body.config
    db.commit()
    return source_public(source)


@router.post("/{source_id}/run", status_code=202)
def run_now(source_id: int, user: User = Depends(roles("admin")), db: Session = Depends(get_db)) -> dict:
    source = db.get(IngestionSource, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    if not source.enabled:
        raise HTTPException(409, "Enable the source before running it")
    item = db.scalar(
        select(WorkItem).where(
            WorkItem.kind == "ingestion",
            WorkItem.status.in_(["pending", "running"]),
            WorkItem.payload["source_id"].as_integer() == source_id,
        )
    )
    if not item:
        item = WorkItem(kind="ingestion", payload={"source_id": source_id})
        db.add(item)
        db.commit()
    return {"work_item_id": item.id, "status": item.status}


@router.get("/{source_id}/runs")
def runs(
    source_id: int,
    page: int = Query(1, ge=1),
    user: User = Depends(roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.scalars(
        select(IngestionRun)
        .where(IngestionRun.source_id == source_id)
        .order_by(IngestionRun.id.desc())
        .offset((page - 1) * 25)
        .limit(25)
    ).all()
    return {
        "items": [
            {k: getattr(r, k) for k in ("id", "started_at", "finished_at", "status", "stats", "error")}
            for r in rows
        ],
        "page": page,
    }
