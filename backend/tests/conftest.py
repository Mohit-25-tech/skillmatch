import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SEMANTIC_ENABLED"] = "false"
os.environ["ENVIRONMENT"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.limits import limiter
from app.main import app
from app.models import Skill


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [Skill(name=n) for n in ["Python", "React", "TypeScript", "PostgreSQL", "Docker", "FastAPI"]]
        )
        db.commit()

    def override_db():
        with Session(engine, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    limiter.enabled = False
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def account(client, email="candidate@example.com", role="candidate"):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Test Person", "email": email, "password": "a-strong-test-password", "role": role},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}
