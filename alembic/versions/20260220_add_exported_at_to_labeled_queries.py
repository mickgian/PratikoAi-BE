"""Add exported_at column to labeled_queries table.

Tracks when each labeled query was last included in a training data export.
Used to show "new since last export" count in the labeling UI without
affecting the export itself (which always returns ALL labeled data).

Revision ID: add_exported_at_20260220
Revises: billing_timestamptz_20260214
Create Date: 2026-02-20 10:00:00.000000

"""

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = "add_exported_at_20260220"
down_revision = "billing_timestamptz_20260214"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns " "WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.scalar() is not None


def upgrade() -> None:
    if not _column_exists("labeled_queries", "exported_at"):
        op.add_column(
            "labeled_queries",
            sa.Column("exported_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("labeled_queries", "exported_at"):
        op.drop_column("labeled_queries", "exported_at")
