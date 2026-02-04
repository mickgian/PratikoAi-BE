"""Add labeled_queries table for intent labeling system.

DEV-253: Expert labeling UI for intent classifier training.

Revision ID: add_intent_labeling_20260203
Revises: add_environment_usage_20260124
Create Date: 2026-02-03

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_intent_labeling_20260203"
down_revision = "add_environment_usage_20260124"
branch_labels = None
depends_on = None


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
    """Create labeled_queries table for intent labeling."""
    if table_exists("labeled_queries"):
        return

    op.create_table(
        "labeled_queries",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("predicted_intent", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("all_scores", JSON(), nullable=True),
        sa.Column("expert_intent", sa.String(50), nullable=True),
        sa.Column("labeled_by", sa.Integer(), nullable=True),
        sa.Column("labeled_at", sa.DateTime(), nullable=True),
        sa.Column("labeling_notes", sa.String(500), nullable=True),
        sa.Column("source_query_id", UUID(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("skip_count", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["labeled_by"], ["user.id"], ondelete="SET NULL"),
    )

    # Index for soft delete filtering
    op.create_index(
        "ix_labeled_queries_is_deleted",
        "labeled_queries",
        ["is_deleted"],
    )

    # Composite index for efficient queue queries:
    # WHERE is_deleted = False AND expert_intent IS NULL ORDER BY confidence ASC
    op.create_index(
        "ix_labeled_queries_queue",
        "labeled_queries",
        ["is_deleted", "expert_intent", "confidence"],
    )

    # Index for finding queries by source query ID
    op.create_index(
        "ix_labeled_queries_source_query_id",
        "labeled_queries",
        ["source_query_id"],
    )


def downgrade() -> None:
    """Drop labeled_queries table."""
    if not table_exists("labeled_queries"):
        return

    op.drop_index("ix_labeled_queries_source_query_id", table_name="labeled_queries")
    op.drop_index("ix_labeled_queries_queue", table_name="labeled_queries")
    op.drop_index("ix_labeled_queries_is_deleted", table_name="labeled_queries")
    op.drop_table("labeled_queries")
