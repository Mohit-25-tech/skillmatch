"""Phase 2 usefulness, tracker, and security additions.

Revision ID: e8c9f2a410b5
Revises: d7a5b3c108e4
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa

revision = "e8c9f2a410b5"
down_revision = "d7a5b3c108e4"
branch_labels = None
depends_on = None


def upgrade():
    # users
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("verification_token", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("reset_token", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True))

    # resumes
    with op.batch_alter_table("resumes") as batch_op:
        batch_op.add_column(sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("parse_warnings", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))

    # jobs
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.add_column(sa.Column("experience_level", sa.String(30), nullable=True))
        batch_op.add_column(sa.Column("country", sa.String(60), nullable=True))
        batch_op.create_index("ix_jobs_experience_level", ["experience_level"])
        batch_op.create_index("ix_jobs_country", ["country"])

    # applications
    with op.batch_alter_table("applications") as batch_op:
        batch_op.alter_column("job_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("custom_company", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("custom_title", sa.String(150), nullable=True))
        batch_op.add_column(sa.Column("custom_url", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table("applications") as batch_op:
        batch_op.drop_column("follow_up_at")
        batch_op.drop_column("custom_url")
        batch_op.drop_column("custom_title")
        batch_op.drop_column("custom_company")
        batch_op.alter_column("job_id", existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_index("ix_jobs_country")
        batch_op.drop_index("ix_jobs_experience_level")
        batch_op.drop_column("country")
        batch_op.drop_column("experience_level")

    with op.batch_alter_table("resumes") as batch_op:
        batch_op.drop_column("parse_warnings")
        batch_op.drop_column("is_primary")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("reset_token_expires_at")
        batch_op.drop_column("reset_token")
        batch_op.drop_column("verification_token")
        batch_op.drop_column("email_verified")
