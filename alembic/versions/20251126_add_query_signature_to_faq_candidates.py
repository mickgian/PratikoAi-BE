"""Add query_signature column to expert_faq_candidates for golden set lookup

Revision ID: 20251126_add_query_signature
Revises: 20251126_add_embedding_to_expert_faq_candidates
Create Date: 2025-11-26 20:00:00.000000

Adds query_signature column to expert_faq_candidates table to enable fast golden set lookups.
This allows the system to retrieve approved FAQ responses without calling the LLM.

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251126_add_query_signature"
down_revision = "20251126_expert_faq_embedding"
branch_labels = None
depends_on = None


def upgrade():
    """Add query_signature column and index to expert_faq_candidates table."""
    # Check if column already exists (may be created by SQLModel.metadata.create_all in tests)
    conn = op.get_bind()
    col_result = conn.execute(
        sa.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'expert_faq_candidates' AND column_name = 'query_signature'
        """)
    )
    column_exists = col_result.fetchone() is not None

    if not column_exists:
        # Add query_signature column (nullable initially to allow existing rows)
        op.add_column(
            "expert_faq_candidates",
            sa.Column("query_signature", sa.String(64), nullable=True),
        )

    # Create index on query_signature for fast golden set lookups (IF NOT EXISTS)
    # This enables Step 24 (golden set match) to quickly find approved responses
    op.execute(
        sa.text('CREATE INDEX IF NOT EXISTS ix_expert_faq_candidates_query_signature ON expert_faq_candidates (query_signature)')
    )


def downgrade():
    """Remove query_signature column and index from expert_faq_candidates table."""
    # Drop index
    op.drop_index("ix_expert_faq_candidates_query_signature", "expert_faq_candidates")

    # Drop query_signature column
    op.drop_column("expert_faq_candidates", "query_signature")
