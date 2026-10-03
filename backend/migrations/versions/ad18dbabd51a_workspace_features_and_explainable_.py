"""workspace features and explainable matching"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "ad18dbabd51a"
down_revision = "ea77977797e7"
branch_labels = None
depends_on = None


def resume_fk():
    if op.get_context().as_sql:
        return "applications_resume_id_fkey"
    for row in sa.inspect(op.get_bind()).get_foreign_keys("applications"):
        if row["constrained_columns"] == ["resume_id"]:
            return row["name"] or "fk_applications_resume_id"
    raise RuntimeError("Missing application resume foreign key")


def status_check():
    if op.get_context().as_sql:
        return "applications_status_check"
    for row in sa.inspect(op.get_bind()).get_check_constraints("applications"):
        if "status" in row["sqltext"]:
            return row["name"] or "ck_applications_status"
    raise RuntimeError("Missing application status check")


def upgrade():
    op.create_table(
        "insight_cache",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "insight_snapshots",
        sa.Column("day", sa.String(length=10), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("day"),
    )
    op.create_table(
        "learning_resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("skill_id", "url", name="uq_resource_skill_url"),
    )
    with op.batch_alter_table("learning_resources", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_learning_resources_skill_id"), ["skill_id"], unique=False)

    op.create_table(
        "saved_searches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("alerts", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("saved_searches", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_saved_searches_user_id"), ["user_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("search_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=250), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("emailed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["search_id"], ["saved_searches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "search_id", "job_id", name="uq_notification_search_job"),
    )
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_notifications_user_id"), ["user_id"], unique=False)

    op.create_table(
        "application_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("application_events", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_application_events_application_id"), ["application_id"], unique=False
        )

    with op.batch_alter_table(
        "applications",
        schema=None,
        naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s", "ck": "ck_%(table_name)s_status"},
    ) as batch_op:
        batch_op.drop_constraint(status_check(), type_="check")
        batch_op.create_check_constraint(
            "ck_applications_status",
            "status IN ('Saved','Applied','Reviewing','Interview','Offer','Rejected','Hired')",
        )
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=False, server_default=""))
        batch_op.add_column(
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
        )
        batch_op.alter_column("resume_id", existing_type=sa.INTEGER(), nullable=True)
        batch_op.drop_constraint(resume_fk(), type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_applications_resume_id", "resumes", ["resume_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table(
        "match_results",
        schema=None,
        table_args=(sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_match_score"),),
    ) as batch_op:
        batch_op.add_column(sa.Column("components", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("reasons", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("improvements", sa.JSON(), nullable=False, server_default="[]"))

    with op.batch_alter_table("resumes", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("embedding", sa.JSON().with_variant(Vector(384), "postgresql"), nullable=True)
        )
        batch_op.add_column(sa.Column("embedding_model", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("experience_years", sa.Float(), nullable=True))

    with op.batch_alter_table(
        "users",
        schema=None,
        table_args=(sa.CheckConstraint("role IN ('candidate','recruiter','admin')", name="ck_users_role"),),
    ) as batch_op:
        batch_op.add_column(sa.Column("preferences", sa.JSON(), nullable=False, server_default="{}"))

    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(
            "CREATE INDEX ix_jobs_search_fts ON jobs USING gin (to_tsvector('english', title || ' ' || company || ' ' || description))"
        )
        op.execute("CREATE INDEX ix_jobs_title_trgm ON jobs USING gin (title gin_trgm_ops)")
    op.create_index("ix_notifications_user_unread", "notifications", ["user_id", "read_at", "id"])


def downgrade():
    if (
        not op.get_context().as_sql
        and op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM applications WHERE resume_id IS NULL OR status IN ('Saved','Offer')"
            )
        )
        .scalar()
    ):
        raise RuntimeError(
            "Downgrade cannot represent saved jobs, offers or applications without resumes; export and resolve them first."
        )
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_jobs_search_fts")
        op.execute("DROP INDEX IF EXISTS ix_jobs_title_trgm")

    with op.batch_alter_table(
        "users",
        schema=None,
        table_args=(sa.CheckConstraint("role IN ('candidate','recruiter','admin')", name="ck_users_role"),),
    ) as batch_op:
        batch_op.drop_column("preferences")

    with op.batch_alter_table("resumes", schema=None) as batch_op:
        batch_op.drop_column("experience_years")
        batch_op.drop_column("embedding_model")
        batch_op.drop_column("embedding")

    with op.batch_alter_table(
        "match_results",
        schema=None,
        table_args=(sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_match_score"),),
    ) as batch_op:
        batch_op.drop_column("improvements")
        batch_op.drop_column("reasons")
        batch_op.drop_column("components")

    with op.batch_alter_table(
        "applications",
        schema=None,
        naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s", "ck": "ck_%(table_name)s_status"},
    ) as batch_op:
        batch_op.drop_constraint("ck_applications_status", type_="check")
        batch_op.create_check_constraint(
            "ck_applications_status", "status IN ('Applied','Reviewing','Interview','Rejected','Hired')"
        )
        batch_op.drop_constraint("fk_applications_resume_id", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_applications_resume_id", "resumes", ["resume_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.alter_column("resume_id", existing_type=sa.INTEGER(), nullable=False)
        batch_op.drop_column("updated_at")
        batch_op.drop_column("notes")

    with op.batch_alter_table("application_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_application_events_application_id"))

    op.drop_table("application_events")
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_notifications_user_id"))

    op.drop_table("notifications")
    with op.batch_alter_table("saved_searches", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_saved_searches_user_id"))

    op.drop_table("saved_searches")
    with op.batch_alter_table("learning_resources", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_learning_resources_skill_id"))

    op.drop_table("learning_resources")
    op.drop_table("insight_snapshots")
    op.drop_table("insight_cache")
