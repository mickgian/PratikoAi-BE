"""Add question_embedding vector column to faq_candidates table

Revision ID: 20251126_faq_candidates_embedding
Revises: 20251126_add_question_embedding
Create Date: 2025-11-26

This migration adds a vector(1536) column to the faq_candidates table to store
OpenAI ada-002 embeddings for semantic similarity search in the Golden Set feature.
This enables finding matching FAQs even when questions are phrased differently.

Index Strategy:
- IVFFlat index for fast approximate nearest neighbor search
- Cosine similarity distance function (vector_cosine_ops)
- Lists parameter = 100 (suitable for 10K-100K records)

Note:
This is separate from the expert_faq_candidates table migration. The faq_candidates
table is the main FAQ automation table that stores FAQ candidates generated from
query cluster analysis.
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251126_faq_candidates_embedding"
down_revision = "20251126_add_question_embedding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add question_embedding column and vector similarity index to faq_candidates"""
    # Check if faq_candidates table exists (may not exist yet if running before Phase 3/4 migrations)
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'faq_candidates'
            )
        """)
    )
    table_exists = result.scalar()

    if not table_exists:
        # Table doesn't exist yet - will be created with column by later migration (c1e8314d9b6d)
        print("ℹ️  faq_candidates table doesn't exist yet, skipping (will be created with column by later migration)")
        return

    # Check if column already exists
    col_result = conn.execute(
        sa.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'faq_candidates' AND column_name = 'question_embedding'
        """)
    )
    column_exists = col_result.fetchone() is not None

    # Ensure pgvector extension is enabled (should already be enabled)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    if not column_exists:
        # Add question_embedding column with Vector(1536) type
        # Nullable=True because existing records won't have embeddings initially
        op.add_column(
            "faq_candidates",
            sa.Column(
                "question_embedding",
                Vector(1536),  # OpenAI ada-002 embedding dimension
                nullable=True,
                comment="Vector embedding of the FAQ question for semantic similarity search (OpenAI ada-002, 1536 dimensions)",
            ),
        )

    # Create IVFFlat index for fast similarity search
    # Note: Index will be empty initially and will populate as embeddings are added
    # Formula: lists = rows/100 (for datasets < 1M rows)
    # Starting with lists=100 for expected 10K-100K FAQ candidates
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_faq_candidates_question_embedding_ivfflat
        ON faq_candidates
        USING ivfflat (question_embedding vector_cosine_ops)
        WITH (lists = 100);
    """)

    # Run ANALYZE to update planner statistics
    op.execute("ANALYZE faq_candidates;")


def downgrade() -> None:
    """Remove question_embedding column and index from faq_candidates"""
    # Check if table exists before trying to drop column
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'faq_candidates'
            )
        """)
    )
    table_exists = result.scalar()

    if not table_exists:
        return

    # Drop index first (must drop before dropping column)
    op.execute("DROP INDEX IF EXISTS idx_faq_candidates_question_embedding_ivfflat;")

    # Check if column exists before dropping
    col_result = conn.execute(
        sa.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'faq_candidates' AND column_name = 'question_embedding'
        """)
    )
    if col_result.fetchone() is not None:
        op.drop_column("faq_candidates", "question_embedding")

    # Note: We don't drop the vector extension as other tables (knowledge_chunks,
    # knowledge_items) still use it for their embedding columns
