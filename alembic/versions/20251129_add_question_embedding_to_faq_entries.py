"""Add question_embedding vector column to faq_entries for semantic search

Revision ID: 20251129_faq_embedding
Revises: 20251129_cascade_fk
Create Date: 2025-11-29

This migration adds the question_embedding column to faq_entries table to enable
semantic search for Golden Set retrieval (Step 24). Uses pgvector for efficient
similarity search with IVFFlat index.

The embedding is a 1536-dimensional vector generated from the question text using
OpenAI's text-embedding-3-small model.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251129_faq_embedding"
down_revision = "20251129_cascade_fk"
branch_labels = None
depends_on = None


def upgrade():
    """Add question_embedding column and index to faq_entries table."""
    # Add question_embedding column (1536 dimensions for text-embedding-3-small)
    op.execute("""
        ALTER TABLE faq_entries
        ADD COLUMN IF NOT EXISTS question_embedding vector(1536);
    """)

    # Create IVFFlat index for efficient similarity search
    # IVFFlat is good for datasets with 1K-1M vectors
    # Using 100 lists (good starting point for < 100K vectors)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_faq_entries_question_embedding_ivfflat
        ON faq_entries USING ivfflat (question_embedding vector_cosine_ops)
        WITH (lists = 100);
    """)


def downgrade():
    """Remove question_embedding column and index from faq_entries table."""
    # Drop index first
    op.execute("""
        DROP INDEX IF EXISTS idx_faq_entries_question_embedding_ivfflat;
    """)

    # Drop column
    op.execute("""
        ALTER TABLE faq_entries
        DROP COLUMN IF EXISTS question_embedding;
    """)
