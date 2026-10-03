from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def build_engine():
    settings = get_settings()
    raw = settings.database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if raw.startswith("postgresql://"):
        raw = raw.replace("postgresql://", "postgresql+psycopg://", 1)
    url = make_url(raw)
    if url.drivername.startswith("postgresql"):
        if settings.environment == "production" or "neon.tech" in (url.host or ""):
            url = url.update_query_dict({"sslmode": "require"})
        return create_engine(url, poolclass=NullPool, connect_args={"connect_timeout": 15})
    sqlite_engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(sqlite_engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    return sqlite_engine


engine = build_engine()
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as db:
        yield db
