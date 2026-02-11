"""Add pending_comparison table for temporary storage (DEV-256).

Stores temporary comparison data from main chat before user navigates
to the comparison page. Includes auto-expiry for cleanup.

Revision ID: add_pending_comparison_20260207
Revises: add_model_comparison_20260206
Create Date: 2026-02-07 10:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "add_pending_comparison_20260207"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "add_model_comparison_20260206"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = :table_name
            )
            """
        ),
        {"table_name": table_name},
    )
    return result.scalar()


def upgrade() -> None:
    """Create pending_comparison table."""
    if not table_exists("pending_comparison"):
        op.create_table(
            "pending_comparison",
            sa.Column("id", UUID(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("query", sa.Text(), nullable=False),
            sa.Column("response", sa.Text(), nullable=False),
            sa.Column("model_id", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        )

        # Index for efficient user lookup and expired record cleanup
        op.create_index("ix_pending_comparison_user_id", "pending_comparison", ["user_id"])
        op.create_index("ix_pending_comparison_expires_at", "pending_comparison", ["expires_at"])


def downgrade() -> None:
    """Drop pending_comparison table."""
    if table_exists("pending_comparison"):
        op.drop_index("ix_pending_comparison_expires_at", table_name="pending_comparison")
        op.drop_index("ix_pending_comparison_user_id", table_name="pending_comparison")
        op.drop_table("pending_comparison")
