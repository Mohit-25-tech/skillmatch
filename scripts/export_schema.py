"""Export the versioned Alembic schema as PostgreSQL SQL without connecting to a server."""

import io
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]
os.environ["DATABASE_URL"] = "postgresql+psycopg://schema_export@localhost/skillmatch"
os.environ["ENVIRONMENT"] = "development"
os.chdir(ROOT / "backend")
output = io.StringIO()
config = Config("alembic.ini", output_buffer=output)
command.upgrade(config, "head", sql=True)
(ROOT / "sql" / "01_schema.sql").write_text(
    "-- Generated from the versioned Alembic migration. PostgreSQL dialect.\n"
    + output.getvalue(),
    encoding="utf-8",
)
print("Exported PostgreSQL schema from Alembic.")
