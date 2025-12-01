"""Add question_embedding vector column to expert_faq_candidates table

Revision ID: 20251126_expert_faq_embedding
Revises: 20251126_faq_candidates_embedding
Create Date: 2025-11-26

This migration adds a vector(1536) column to the expert_faq_candidates table to store
OpenAI text-embedding-ada-002 embeddings for semantic similarity search in the Golden Set.

This enables:
- Finding matching FAQs via semantic similarity (not just exact matches)
- Deduplication detection (avoid creating duplicate FAQs for similar questions)
- Intelligent routing (match user queries to existing FAQ candidates)

Index Strategy:
- IVFFlat index for fast approximate nearest neighbor search
- Cosine similarity distance function (vector_cosine_ops)
- Lists parameter = 50 (suitable for 5K-10K expert FAQ candidates)

Migration Context:
This is part of Phase 2.2c GREEN - Integrate Embedding Generation in Step 127.
Step 127 (app/orchestrators/golden.py) will generate embeddings when experts mark
answers as "correct", storing them in this column for semantic search.

Related Tables:
- expert_faq_candidates: FAQ candidates from expert feedback (THIS TABLE)
- faq_candidates: FAQ candidates from query cluster analysis (SEPARATE TABLE)
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251126_expert_faq_embedding"
down_revision = "20251126_faq_candidates_embedding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add question_embedding column and vector similarity index to expert_faq_candidates"""
    # Ensure pgvector extension is enabled (should already be enabled by earlier migrations)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Add question_embedding column with Vector(1536) type
    # Nullable=True because:
    # 1. Existing records won't have embeddings initially (backfill required)
    # 2. Graceful degradation: if embedding generation fails, FAQ still created
    op.add_column(
        "expert_faq_candidates",
        sa.Column(
            "question_embedding",
            Vector(1536),  # OpenAI text-embedding-ada-002 dimension
            nullable=True,
            comment="Vector embedding of FAQ question for semantic similarity search (OpenAI ada-002, 1536d)",
        ),
    )

    # Create IVFFlat index for fast cosine similarity search
    # Parameters:
    # - lists = 50: Suitable for 5K-10K records (formula: sqrt(rows) for small datasets)
    # - vector_cosine_ops: Use cosine distance (1 - cosine_similarity)
    #
    # Note: Index will be sparse initially (most embeddings NULL). That's OK.
    # PostgreSQL will only index non-NULL values.
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_expert_faq_candidates_question_embedding_ivfflat
        ON expert_faq_candidates
        USING ivfflat (question_embedding vector_cosine_ops)
        WITH (lists = 50);
    """)

    # Update planner statistics so PostgreSQL knows about the new column
    op.execute("ANALYZE expert_faq_candidates;")

    print("✅ Added question_embedding column to expert_faq_candidates")
    print("   - Vector(1536) for OpenAI ada-002 embeddings")
    print("   - IVFFlat index for cosine similarity search (lists=50)")
    print("   - Nullable=True for graceful degradation")
    print("")
    print("⚠️  Next Steps:")
    print("   1. Deploy Step 127 updates (generate embeddings for new FAQs)")
    print(
        "   2. Backfill existing records: UPDATE expert_faq_candidates SET question_embedding = ... WHERE question_embedding IS NULL"
    )
    print("   3. Monitor embedding generation success rate in logs")


def downgrade() -> None:
    """Remove question_embedding column and index from expert_faq_candidates"""
    # Drop index first (must drop before dropping column)
    op.execute("DROP INDEX IF EXISTS idx_expert_faq_candidates_question_embedding_ivfflat;")

    # Drop the question_embedding column
    op.drop_column("expert_faq_candidates", "question_embedding")

    print("✅ Removed question_embedding column and index from expert_faq_candidates")
    print("   ⚠️  WARNING: All stored embeddings have been deleted!")
    print("   To restore functionality, revert this migration and backfill embeddings.")

    # Note: We don't drop the vector extension as other tables still use it
