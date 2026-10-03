"""live ingestion vectors and work queue"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "ea77977797e7"
down_revision = "ea131b083c8f"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "feed_cache",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("etag", sa.Text(), nullable=True),
        sa.Column("modified", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "ingestion_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=150), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("stats", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    with op.batch_alter_table("ingestion_sources", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ingestion_sources_next_run_at"), ["next_run_at"], unique=False)

    op.create_table(
        "work_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("work_items", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_work_items_available_at"), ["available_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_work_items_kind"), ["kind"], unique=False)
        batch_op.create_index(batch_op.f("ix_work_items_status"), ["status"], unique=False)

    op.create_table(
        "worker_heartbeats",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("stats", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["ingestion_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ingestion_runs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ingestion_runs_source_id"), ["source_id"], unique=False)

    op.create_table(
        "job_origins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=300), nullable=False),
        sa.Column("apply_url", sa.Text(), nullable=False),
        sa.Column("attribution", sa.String(length=100), nullable=False),
        sa.Column("attribution_url", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["ingestion_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_origin_source_external"),
    )
    with op.batch_alter_table("job_origins", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_job_origins_job_id"), ["job_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_job_origins_source_id"), ["source_id"], unique=False)

    with op.batch_alter_table(
        "jobs",
        schema=None,
        table_args=(
            sa.CheckConstraint("salary_min >= 0 AND salary_max >= salary_min", name="ck_jobs_salary"),
        ),
    ) as batch_op:
        batch_op.add_column(sa.Column("salary_currency", sa.String(length=3), nullable=True))
        batch_op.add_column(sa.Column("salary_interval", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("remote", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("apply_url", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("source", sa.String(length=30), nullable=False, server_default="native")
        )
        batch_op.add_column(sa.Column("external_id", sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("fingerprint", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("embedding", sa.JSON().with_variant(Vector(384), "postgresql"), nullable=True)
        )
        batch_op.add_column(sa.Column("embedding_model", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("content_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("skill_importance", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("experience_min", sa.Float(), nullable=True))
        batch_op.add_column(
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
        )
        batch_op.alter_column("recruiter_id", existing_type=sa.INTEGER(), nullable=True)
        batch_op.alter_column("salary_min", existing_type=sa.INTEGER(), nullable=True)
        batch_op.alter_column("salary_max", existing_type=sa.INTEGER(), nullable=True)
        batch_op.create_index(batch_op.f("ix_jobs_fingerprint"), ["fingerprint"], unique=False)
        batch_op.create_index(batch_op.f("ix_jobs_is_demo"), ["is_demo"], unique=False)
        batch_op.create_index(batch_op.f("ix_jobs_posted_at"), ["posted_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_jobs_source"), ["source"], unique=False)
        batch_op.create_unique_constraint("uq_jobs_source_external", ["source", "external_id"])

    op.execute(
        "UPDATE jobs SET is_demo = true, source = 'demo' WHERE recruiter_id IN (SELECT id FROM users WHERE email = 'catalog@skillmatch.example')"
    )
    op.execute("UPDATE jobs SET posted_at = created_at WHERE source = 'native'")
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX ix_jobs_embedding_hnsw ON jobs USING hnsw (embedding vector_cosine_ops) WHERE embedding IS NOT NULL"
        )


def downgrade():
    if (
        not op.get_context().as_sql
        and op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM jobs WHERE recruiter_id IS NULL OR salary_min IS NULL OR salary_max IS NULL"
            )
        )
        .scalar()
    ):
        raise RuntimeError(
            "Downgrade cannot represent live jobs with unknown salaries or no recruiter; export and resolve these records first."
        )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_jobs_embedding_hnsw")
    with op.batch_alter_table(
        "jobs",
        schema=None,
        table_args=(
            sa.CheckConstraint("salary_min >= 0 AND salary_max >= salary_min", name="ck_jobs_salary"),
        ),
    ) as batch_op:
        batch_op.drop_constraint("uq_jobs_source_external", type_="unique")
        batch_op.drop_index(batch_op.f("ix_jobs_source"))
        batch_op.drop_index(batch_op.f("ix_jobs_posted_at"))
        batch_op.drop_index(batch_op.f("ix_jobs_is_demo"))
        batch_op.drop_index(batch_op.f("ix_jobs_fingerprint"))
        batch_op.alter_column("salary_max", existing_type=sa.INTEGER(), nullable=False)
        batch_op.alter_column("salary_min", existing_type=sa.INTEGER(), nullable=False)
        batch_op.alter_column("recruiter_id", existing_type=sa.INTEGER(), nullable=False)
        batch_op.drop_column("updated_at")
        batch_op.drop_column("experience_min")
        batch_op.drop_column("skill_importance")
        batch_op.drop_column("content_hash")
        batch_op.drop_column("embedding_model")
        batch_op.drop_column("embedding")
        batch_op.drop_column("fingerprint")
        batch_op.drop_column("is_demo")
        batch_op.drop_column("posted_at")
        batch_op.drop_column("external_id")
        batch_op.drop_column("source")
        batch_op.drop_column("apply_url")
        batch_op.drop_column("remote")
        batch_op.drop_column("salary_interval")
        batch_op.drop_column("salary_currency")

    with op.batch_alter_table("job_origins", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_job_origins_source_id"))
        batch_op.drop_index(batch_op.f("ix_job_origins_job_id"))

    op.drop_table("job_origins")
    with op.batch_alter_table("ingestion_runs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ingestion_runs_source_id"))

    op.drop_table("ingestion_runs")
    op.drop_table("worker_heartbeats")
    with op.batch_alter_table("work_items", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_work_items_status"))
        batch_op.drop_index(batch_op.f("ix_work_items_kind"))
        batch_op.drop_index(batch_op.f("ix_work_items_available_at"))

    op.drop_table("work_items")
    with op.batch_alter_table("ingestion_sources", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ingestion_sources_next_run_at"))

    op.drop_table("ingestion_sources")
    op.drop_table("feed_cache")
