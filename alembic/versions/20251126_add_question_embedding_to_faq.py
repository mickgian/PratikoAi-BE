"""Add question_embedding vector column to expert_faq_candidates

Revision ID: 20251126_add_question_embedding
Revises: 20251124_add_generated_faq_id
Create Date: 2025-11-26

This migration adds a vector(1536) column to store OpenAI ada-002 embeddings
for semantic similarity search in the Golden Set feature. This enables finding
matching FAQs even when questions are phrased differently.

Index Strategy:
- IVFFlat index for fast approximate nearest neighbor search
- Cosine similarity distance function (vector_cosine_ops)
- Lists parameter = 100 (suitable for 10K-100K records)
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251126_add_question_embedding"
down_revision = "20251124_add_generated_faq_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add question_embedding column and vector similarity index"""
    # Check if column already exists (may be created by SQLModel.metadata.create_all in tests)
    conn = op.get_bind()
    col_result = conn.execute(
        sa.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'expert_faq_candidates' AND column_name = 'question_embedding'
        """)
    )
    column_exists = col_result.fetchone() is not None

    # Ensure pgvector extension is enabled (should already be enabled)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    if not column_exists:
        # Add question_embedding column with Vector(1536) type
        # Nullable=True because existing records won't have embeddings initially
        op.add_column(
            "expert_faq_candidates",
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
        CREATE INDEX IF NOT EXISTS idx_expert_faq_question_embedding_ivfflat
        ON expert_faq_candidates
        USING ivfflat (question_embedding vector_cosine_ops)
        WITH (lists = 100);
    """)

    # Run ANALYZE to update planner statistics
    op.execute("ANALYZE expert_faq_candidates;")


def downgrade() -> None:
    """Remove question_embedding column and index"""
    # Drop index first (must drop before dropping column)
    op.execute("DROP INDEX IF EXISTS idx_expert_faq_question_embedding_ivfflat;")

    # Drop the question_embedding column
    op.drop_column("expert_faq_candidates", "question_embedding")

    # Note: We don't drop the vector extension as other tables (knowledge_chunks,
    # knowledge_items) still use it for their embedding columns
