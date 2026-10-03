"""Indexes for cursor discovery, current resumes, match ordering and task polling."""

from alembic import op

revision = "c6f4a1b209d3"
down_revision = "ad18dbabd51a"
branch_labels = None
depends_on = None

INDEXES = [
    ("ix_jobs_active_cursor", "jobs", ["active", "is_demo", "id"]),
    ("ix_resumes_user_latest", "resumes", ["user_id", "id"]),
    ("ix_matches_resume_score", "match_results", ["resume_id", "score"]),
    ("ix_applications_user_updated", "applications", ["user_id", "updated_at"]),
    ("ix_work_items_pending_due", "work_items", ["status", "available_at", "id"]),
]


def upgrade():
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns)


def downgrade():
    for name, table, _ in reversed(INDEXES):
        op.drop_index(name, table_name=table)
