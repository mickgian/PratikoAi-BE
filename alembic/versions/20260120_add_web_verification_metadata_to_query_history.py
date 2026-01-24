"""DEV-245: Add web_verification_metadata to query_history

Revision ID: add_web_verification_20260120
Revises: add_kb_sources_metadata_20260119
Create Date: 2026-01-20

This migration adds the web_verification_metadata JSON column to query_history
table for persisting web verification results (Brave Search) so they're
available when users return to the chat.

Related to:
- DEV-245: Response Quality Improvement / Parallel Hybrid RAG
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = "add_web_verification_20260120"
down_revision = "add_kb_sources_metadata_20260119"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table_name AND column_name = :column_name
            )
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar()


def upgrade() -> None:
    """Add web_verification_metadata column to query_history table."""
    # Check if column already exists (idempotent migration)
    if not column_exists("query_history", "web_verification_metadata"):
        op.add_column(
            "query_history",
            sa.Column(
                "web_verification_metadata",
                postgresql.JSON(astext_type=sa.Text()),
                nullable=True,
                comment="DEV-245: Web verification results (Brave Search) for Verifica Web display",
            ),
        )


def downgrade() -> None:
    """Remove web_verification_metadata column from query_history table."""
    if column_exists("query_history", "web_verification_metadata"):
        op.drop_column("query_history", "web_verification_metadata")
