"""Add items_filtered and filtered_samples columns to feed_status table.

DEV-247: Track filtered content for Gazzetta topic filtering in daily reports.

Revision ID: add_filtered_items_20260124
Revises: add_web_verification_20260120
Create Date: 2026-01-24

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_filtered_items_20260124"
down_revision = "add_web_verification_20260120"
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
    """Add items_filtered and filtered_samples columns to feed_status table."""
    # Add items_filtered column to track count of filtered items
    if not column_exists("feed_status", "items_filtered"):
        op.add_column(
            "feed_status",
            sa.Column(
                "items_filtered",
                sa.Integer(),
                nullable=True,
                comment="Number of items filtered out (irrelevant)",
            ),
        )

    # Add filtered_samples column to store sample titles of filtered items
    if not column_exists("feed_status", "filtered_samples"):
        op.add_column(
            "feed_status",
            sa.Column(
                "filtered_samples",
                postgresql.JSON(astext_type=sa.Text()),
                nullable=True,
                comment="Sample titles of filtered items for review",
            ),
        )


def downgrade() -> None:
    """Remove items_filtered and filtered_samples columns from feed_status table."""
    if column_exists("feed_status", "filtered_samples"):
        op.drop_column("feed_status", "filtered_samples")
    if column_exists("feed_status", "items_filtered"):
        op.drop_column("feed_status", "items_filtered")
