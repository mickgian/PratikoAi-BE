"""Add metrics columns to pending_comparison (DEV-256).

Stores latency, cost, tokens, and trace_id from main chat response so that
the comparison page can display actual metrics instead of hardcoded zeros.

Revision ID: add_metrics_pending_20260209
Revises: add_enriched_prompt_20260209
Create Date: 2026-02-09 14:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "add_metrics_pending_20260209"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "add_enriched_prompt_20260209"  # pragma: allowlist secret
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
    """Add metrics columns to pending_comparison table."""
    if not column_exists("pending_comparison", "latency_ms"):
        op.add_column(
            "pending_comparison",
            sa.Column("latency_ms", sa.Integer(), nullable=True),
        )

    if not column_exists("pending_comparison", "cost_eur"):
        op.add_column(
            "pending_comparison",
            sa.Column("cost_eur", sa.Float(), nullable=True),
        )

    if not column_exists("pending_comparison", "input_tokens"):
        op.add_column(
            "pending_comparison",
            sa.Column("input_tokens", sa.Integer(), nullable=True),
        )

    if not column_exists("pending_comparison", "output_tokens"):
        op.add_column(
            "pending_comparison",
            sa.Column("output_tokens", sa.Integer(), nullable=True),
        )

    if not column_exists("pending_comparison", "trace_id"):
        op.add_column(
            "pending_comparison",
            sa.Column("trace_id", sa.String(64), nullable=True),
        )


def downgrade() -> None:
    """Remove metrics columns from pending_comparison table."""
    if column_exists("pending_comparison", "trace_id"):
        op.drop_column("pending_comparison", "trace_id")

    if column_exists("pending_comparison", "output_tokens"):
        op.drop_column("pending_comparison", "output_tokens")

    if column_exists("pending_comparison", "input_tokens"):
        op.drop_column("pending_comparison", "input_tokens")

    if column_exists("pending_comparison", "cost_eur"):
        op.drop_column("pending_comparison", "cost_eur")

    if column_exists("pending_comparison", "latency_ms"):
        op.drop_column("pending_comparison", "latency_ms")
