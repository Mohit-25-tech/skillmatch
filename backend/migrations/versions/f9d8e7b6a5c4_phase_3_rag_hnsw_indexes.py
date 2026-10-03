"""phase 3 rag hnsw indexes

Revision ID: f9d8e7b6a5c4
Revises: e8c9f2a410b5
Create Date: 2026-10-02 22:26:00
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f9d8e7b6a5c4"
down_revision = "e8c9f2a410b5"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_jobs_embedding_hnsw ON jobs USING hnsw (embedding vector_cosine_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_resumes_embedding_hnsw ON resumes USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_jobs_embedding_hnsw")
        op.execute("DROP INDEX IF EXISTS ix_resumes_embedding_hnsw")
