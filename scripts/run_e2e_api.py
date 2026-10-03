"""Isolated browser-test server. Never connects to a configured application database."""

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DATABASE_URL"] = (
    "sqlite:///"
    + (Path(tempfile.mkdtemp(prefix="skillmatch-e2e-")) / "test.db").as_posix()
)
os.environ["ENVIRONMENT"] = "test"
os.environ["SEMANTIC_ENABLED"] = "false"
os.environ["DEMO_MODE"] = "false"
os.environ["COOKIE_SECURE"] = "false"
os.environ["SMTP_HOST"] = ""
os.environ["OLLAMA_ENABLED"] = "false"
os.environ["CORS_ORIGINS"] = "http://127.0.0.1:5182,http://localhost:5182"

import uvicorn
from app.db import Base, SessionLocal, engine
from app.limits import limiter
from app.main import app
from app.models import IngestionSource, User
from app.security import password_hash
from app.seed import seed
from app.worker import heartbeat, process_tasks
from docx import Document

resume = Document()
resume.add_paragraph(
    "Python engineer with 3 years of experience. Skills: Python FastAPI PostgreSQL Docker. Experience building APIs. Education: Computer Science. Contact: test@example.com"
)
(ROOT / "artifacts").mkdir(exist_ok=True)
resume.save(ROOT / "artifacts" / "e2e-stage4-resume.docx")

Base.metadata.create_all(engine)
seed()
limiter.enabled = False
with SessionLocal() as db:
    db.add(
        User(
            name="Test Administrator",
            email="admin@e2e.example",
            password_hash=password_hash.hash("e2e-admin-test-password"),
            role="admin",
        )
    )
    db.add(
        IngestionSource(
            key="test-disabled",
            kind="greenhouse",
            config={"slug": "example"},
            enabled=False,
        )
    )
    db.commit()


def worker():
    while True:
        process_tasks()
        heartbeat()
        time.sleep(0.5)


threading.Thread(target=worker, daemon=True).start()
uvicorn.run(app, host="127.0.0.1", port=8012, log_level="warning")
