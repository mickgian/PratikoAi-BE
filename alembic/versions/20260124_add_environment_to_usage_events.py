"""Add environment and api_type columns to usage_events table.

DEV-246: Track environment for daily cost reporting by environment and user.

Revision ID: add_environment_usage_20260124
Revises: add_filtered_items_20260124
Create Date: 2026-01-24

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_environment_usage_20260124"
down_revision = "add_filtered_items_20260124"
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
    """Add environment and api_type columns to usage_events table."""
    # Add environment column to track which environment the cost occurred in
    if not column_exists("usage_events", "environment"):
        op.add_column(
            "usage_events",
            sa.Column(
                "environment",
                sa.String(),
                nullable=True,
                comment="Environment where cost occurred (development, qa, production)",
            ),
        )
        # Add index for efficient filtering by environment
        op.create_index(
            "ix_usage_events_environment",
            "usage_events",
            ["environment"],
            unique=False,
        )

    # Add api_type column to distinguish third-party API types (e.g., brave_search)
    if not column_exists("usage_events", "api_type"):
        op.add_column(
            "usage_events",
            sa.Column(
                "api_type",
                sa.String(),
                nullable=True,
                comment="API type for third-party costs (brave_search, etc.)",
            ),
        )


def downgrade() -> None:
    """Remove environment and api_type columns from usage_events table."""
    if column_exists("usage_events", "environment"):
        op.drop_index("ix_usage_events_environment", table_name="usage_events")
        op.drop_column("usage_events", "environment")
    if column_exists("usage_events", "api_type"):
        op.drop_column("usage_events", "api_type")
