from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.db import build_engine, get_db
from app.main import app
from app.models import User
from tests.conftest import account


def test_production_refuses_insecure_defaults():
    with pytest.raises(ValueError):
        Settings(environment="production").validate_production()


def test_neon_enforces_tls_and_uses_external_pooler():
    settings = Settings(
        database_url="postgresql://user:password@ep-sample-pooler.neon.tech/main?sslmode=disable"
    )
    with patch("app.db.get_settings", return_value=settings):
        engine = build_engine()
    assert engine.url.drivername == "postgresql+psycopg"
    assert engine.url.query["sslmode"] == "require"
    assert isinstance(engine.pool, NullPool)
    engine.dispose()


def test_admin_controls_and_token_revocation(client):
    admin_headers = account(client, "admin@example.com")
    candidate_headers = account(client)
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    admin_user = db.scalar(select(User).where(User.email == "admin@example.com"))
    admin_user.role = "admin"
    admin_id = admin_user.id
    candidate_id = db.scalar(select(User.id).where(User.email == "candidate@example.com"))
    db.commit()
    generator.close()
    assert client.get("/api/v1/admin", headers=admin_headers).status_code == 200
    assert (
        client.patch(
            f"/api/v1/admin/users/{admin_id}", headers=admin_headers, json={"active": False}
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"/api/v1/admin/users/{candidate_id}", headers=admin_headers, json={"active": False}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me", headers=candidate_headers).status_code == 401
    assert (
        client.patch(
            f"/api/v1/admin/users/{candidate_id}", headers=admin_headers, json={"active": True}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me", headers=candidate_headers).status_code == 401
