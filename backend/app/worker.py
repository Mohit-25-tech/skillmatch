"""One worker process: durable SQL task queue + APScheduler timers."""

import logging
import signal
import threading
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select, update

from app.config import get_settings
from app.db import SessionLocal
from app.ingestion.service import configure_sources, ingest
from app.models import IngestionSource, Job, Resume, WorkerHeartbeat, WorkItem, utcnow
from app.services.match_pipeline import match_resume, reindex_all
from app.services.product import latest_resume

log = logging.getLogger(__name__)


def heartbeat() -> None:
    with SessionLocal() as db:
        row = db.get(WorkerHeartbeat, "ingestion") or WorkerHeartbeat(id="ingestion")
        row.seen_at = utcnow()
        db.add(row)
        db.commit()


def process_tasks() -> None:
    with SessionLocal() as db:
        now = utcnow()
        db.execute(
            update(WorkItem)
            .where(WorkItem.status == "running", WorkItem.locked_at < now - timedelta(minutes=30))
            .values(status="pending", available_at=now)
        )
        db.commit()
        item = db.scalar(
            select(WorkItem)
            .where(WorkItem.status == "pending", WorkItem.available_at <= now)
            .order_by(WorkItem.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not item:
            return
        item.status, item.locked_at, item.attempts = "running", now, item.attempts + 1
        db.commit()
        try:
            if item.kind == "resume":
                resume = db.get(Resume, item.payload["resume_id"])
                if resume and latest_resume(db, resume.user_id).id == resume.id:
                    from app.services.retrieval import index_resume_chunks

                    index_resume_chunks(db, resume)
                    match_resume(db, resume)
            elif item.kind == "catalog":
                from app.services.enrichment import embed_catalog
                from app.services.retrieval import index_job_chunks

                embed_catalog(db, item.payload.get("job_ids"))
                reindex_all(db, only_missing=True, job_ids=item.payload.get("job_ids"))
                job_ids = item.payload.get("job_ids")
                q = select(Job).where(Job.active.is_(True))
                if job_ids:
                    q = q.where(Job.id.in_(job_ids))
                for j in db.scalars(q).all():
                    index_job_chunks(db, j)
            elif item.kind == "ingestion":
                source = db.get(IngestionSource, item.payload["source_id"])
                if source and source.enabled:
                    result = ingest(db, source)
                    if result["status"] == "error":
                        raise RuntimeError("Feed run failed")
            elif item.kind == "digest":
                from app.services.product import send_digests

                send_digests(db)
            else:
                raise ValueError("Unknown work item type")
            item.status, item.error = "done", None
        except Exception as error:
            db.rollback()
            item = db.get(WorkItem, item.id)
            item.status = "failed" if item.attempts >= 3 else "pending"
            item.available_at = utcnow() + timedelta(seconds=60 * 2**item.attempts)
            item.error = type(error).__name__
            log.error(
                "work_item_failed id=%s kind=%s error_type=%s", item.id, item.kind, type(error).__name__
            )
        db.commit()


def schedule_sources() -> None:
    with SessionLocal() as db:
        now = utcnow()
        for source in db.scalars(
            select(IngestionSource).where(
                IngestionSource.enabled.is_(True), IngestionSource.next_run_at <= now
            )
        ).all():
            claimed = db.execute(
                update(IngestionSource)
                .where(IngestionSource.id == source.id, IngestionSource.next_run_at <= now)
                .values(next_run_at=now + timedelta(minutes=source.interval_minutes))
            )
            if claimed.rowcount:
                pending = db.scalar(
                    select(WorkItem.id).where(
                        WorkItem.kind == "ingestion",
                        WorkItem.status.in_(["pending", "running"]),
                        WorkItem.payload["source_id"].as_integer() == source.id,
                    )
                )
                if not pending:
                    db.add(WorkItem(kind="ingestion", payload={"source_id": source.id}))
        db.commit()


def daily_products():
    from app.services.product import market_insights

    with SessionLocal() as db:
        market_insights(db, force=True)
        pending = db.scalar(
            select(WorkItem.id).where(WorkItem.kind == "digest", WorkItem.status.in_(["pending", "running"]))
        )
        if not pending:
            db.add(WorkItem(kind="digest"))
        db.commit()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    with SessionLocal() as db:
        configure_sources(db)
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(daily_products, "cron", hour=8, max_instances=1)
    scheduler.add_job(heartbeat, "interval", seconds=30, max_instances=1, next_run_time=utcnow())
    scheduler.add_job(schedule_sources, "interval", seconds=60, max_instances=1, next_run_time=utcnow())
    scheduler.add_job(
        process_tasks,
        "interval",
        seconds=get_settings().worker_poll_seconds,
        max_instances=1,
        next_run_time=utcnow(),
    )
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    scheduler.start()
    stop.wait()
    scheduler.shutdown(wait=True)


if __name__ == "__main__":
    main()
