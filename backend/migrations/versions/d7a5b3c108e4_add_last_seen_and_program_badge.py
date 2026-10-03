"""Add last_seen_at and program_badge to jobs.

Revision ID: d7a5b3c108e4
Revises: c6f4a1b209d3
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa

revision = "d7a5b3c108e4"
down_revision = "c6f4a1b209d3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("program_badge", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("jobs", "program_badge")
    op.drop_column("jobs", "last_seen_at")
