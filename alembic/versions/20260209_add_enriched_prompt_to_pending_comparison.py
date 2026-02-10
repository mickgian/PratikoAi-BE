"""Add enriched_prompt column to pending_comparison (DEV-256).

Stores the full LLM prompt including KB context, web results, system prompt,
etc. so that comparison models receive identical input to production model.

Revision ID: add_enriched_prompt_20260209
Revises: add_pending_comparison_20260207
Create Date: 2026-02-09 10:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "add_enriched_prompt_20260209"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "add_pending_comparison_20260207"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table_name
                AND column_name = :column_name
            )
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar()


def upgrade() -> None:
    """Add enriched_prompt column to pending_comparison table."""
    if not column_exists("pending_comparison", "enriched_prompt"):
        op.add_column(
            "pending_comparison",
            sa.Column("enriched_prompt", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    """Remove enriched_prompt column from pending_comparison table."""
    if column_exists("pending_comparison", "enriched_prompt"):
        op.drop_column("pending_comparison", "enriched_prompt")
