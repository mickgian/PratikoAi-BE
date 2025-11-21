"""Create vector indexes for hybrid RAG retrieval

Revision ID: vector_indexes_20251103
Revises: enable_pgvector_20251103
Create Date: 2025-11-03

This migration creates ivfflat indexes on embedding columns if pgvector is present.
Also runs VACUUM ANALYZE for planner statistics.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "vector_indexes_20251103"
down_revision = "enable_pgvector_20251103"
branch_labels = None
depends_on = None


def upgrade():
    """Create vector indexes if pgvector is available"""
    # Only build indexes if pgvector is present
    op.execute(
        """
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_type WHERE typname='vector') THEN
        -- knowledge_items embedding index (if column exists)
        IF EXISTS (
          SELECT 1 FROM information_schema.columns
          WHERE table_name='knowledge_items' AND column_name='embedding'
        ) THEN
          CREATE INDEX IF NOT EXISTS idx_ki_vec
          ON knowledge_items USING ivfflat (embedding vector_cosine_ops);
        END IF;

        -- knowledge_chunks embedding index (primary retrieval path)
        IF EXISTS (
          SELECT 1 FROM information_schema.columns
          WHERE table_name='knowledge_chunks' AND column_name='embedding'
        ) THEN
          CREATE INDEX IF NOT EXISTS idx_kc_vec
          ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops);
        END IF;
      END IF;
    END$$;
    """
    )

    # Analyze for planner stats (optional, skip if in transaction)
    try:
        op.execute("VACUUM ANALYZE knowledge_items;")
    except Exception:
        pass  # VACUUM cannot run in transaction, skip
    try:
        op.execute("VACUUM ANALYZE knowledge_chunks;")
    except Exception:
        pass  # VACUUM cannot run in transaction, skip


def downgrade():
    """Keep indexes - no downgrade needed"""
    pass
