from datetime import timedelta, timezone

from app.db import SessionLocal
from app.models import WorkerHeartbeat, utcnow

with SessionLocal() as db:
    row = db.get(WorkerHeartbeat, "ingestion")
    if not row or row.seen_at.replace(tzinfo=timezone.utc) < utcnow() - timedelta(seconds=120):
        raise SystemExit(1)
