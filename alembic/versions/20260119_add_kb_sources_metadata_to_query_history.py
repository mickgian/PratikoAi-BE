"""DEV-244: Add kb_sources_metadata to query_history

Revision ID: add_kb_sources_metadata_20260119
Revises: add_tiered_ingestion_20260109
Create Date: 2026-01-19

This migration adds the kb_sources_metadata JSON column to query_history table
for persisting Fonti (sources) metadata so it's available when users return
to the chat.

Related to:
- DEV-244: KB Source URLs Display + Suggested Actions Quality
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = "add_kb_sources_metadata_20260119"
down_revision = "add_tiered_ingestion_20260109"
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
    """Add kb_sources_metadata column to query_history table."""
    # Check if column already exists (idempotent migration)
    if not column_exists("query_history", "kb_sources_metadata"):
        op.add_column(
            "query_history",
            sa.Column(
                "kb_sources_metadata",
                postgresql.JSON(astext_type=sa.Text()),
                nullable=True,
                comment="DEV-244: KB source URLs and metadata for Fonti display",
            ),
        )


def downgrade() -> None:
    """Remove kb_sources_metadata column from query_history table."""
    if column_exists("query_history", "kb_sources_metadata"):
        op.drop_column("query_history", "kb_sources_metadata")
