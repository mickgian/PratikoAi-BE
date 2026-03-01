"""Persist model comparison sessions and add expert evaluation (DEV-256).

Adds expert evaluation fields to model_comparison_responses, adds
comparison_used and batch_id to pending_comparison for persistence,
and makes expires_at nullable.

Revision ID: persist_comparison_20260228
Revises: wave5_20260227
Create Date: 2026-02-28 10:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "persist_comparison_20260228"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "wave5_20260227"  # pragma: allowlist secret
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
    """Add expert evaluation and persistence columns."""
    # --- model_comparison_responses: expert evaluation ---
    if not column_exists("model_comparison_responses", "expert_evaluation"):
        op.add_column(
            "model_comparison_responses",
            sa.Column("expert_evaluation", sa.String(20), nullable=True),
        )

    if not column_exists("model_comparison_responses", "expert_evaluation_details"):
        op.add_column(
            "model_comparison_responses",
            sa.Column("expert_evaluation_details", sa.String(2000), nullable=True),
        )

    if not column_exists("model_comparison_responses", "expert_evaluation_user_id"):
        op.add_column(
            "model_comparison_responses",
            sa.Column("expert_evaluation_user_id", sa.Integer(), nullable=True),
        )

    if not column_exists("model_comparison_responses", "expert_evaluation_at"):
        op.add_column(
            "model_comparison_responses",
            sa.Column("expert_evaluation_at", sa.DateTime(), nullable=True),
        )

    # --- pending_comparison: persistence fields ---
    if not column_exists("pending_comparison", "comparison_used"):
        op.add_column(
            "pending_comparison",
            sa.Column("comparison_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.create_index(
            "ix_pending_comparison_comparison_used",
            "pending_comparison",
            ["comparison_used"],
        )

    if not column_exists("pending_comparison", "batch_id"):
        op.add_column(
            "pending_comparison",
            sa.Column("batch_id", sa.String(64), nullable=True),
        )
        op.create_index(
            "ix_pending_comparison_batch_id",
            "pending_comparison",
            ["batch_id"],
        )

    # Make expires_at nullable (was NOT NULL before)
    if column_exists("pending_comparison", "expires_at"):
        op.alter_column(
            "pending_comparison",
            "expires_at",
            existing_type=sa.DateTime(),
            nullable=True,
        )


def downgrade() -> None:
    """Remove expert evaluation and persistence columns."""
    # Restore expires_at NOT NULL
    if column_exists("pending_comparison", "expires_at"):
        op.alter_column(
            "pending_comparison",
            "expires_at",
            existing_type=sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        )

    if column_exists("pending_comparison", "batch_id"):
        op.drop_index("ix_pending_comparison_batch_id", table_name="pending_comparison")
        op.drop_column("pending_comparison", "batch_id")

    if column_exists("pending_comparison", "comparison_used"):
        op.drop_index("ix_pending_comparison_comparison_used", table_name="pending_comparison")
        op.drop_column("pending_comparison", "comparison_used")

    if column_exists("model_comparison_responses", "expert_evaluation_at"):
        op.drop_column("model_comparison_responses", "expert_evaluation_at")

    if column_exists("model_comparison_responses", "expert_evaluation_user_id"):
        op.drop_column("model_comparison_responses", "expert_evaluation_user_id")

    if column_exists("model_comparison_responses", "expert_evaluation_details"):
        op.drop_column("model_comparison_responses", "expert_evaluation_details")

    if column_exists("model_comparison_responses", "expert_evaluation"):
        op.drop_column("model_comparison_responses", "expert_evaluation")
