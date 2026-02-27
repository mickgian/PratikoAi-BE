"""add generated_faq_id to expert_feedback

Revision ID: 20251124_add_generated_faq_id
Revises: 20251124_add_user_role
Create Date: 2025-11-24

Links expert feedback to Golden Set entries created from "Corretta" feedback.
When experts mark responses as correct, the system creates FAQ entries and tracks
which FAQ was generated from which feedback for audit trail and quality analysis.

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251124_add_generated_faq_id"
down_revision = "20251124_add_user_role"
branch_labels = None
depends_on = None


def upgrade():
    """Add generated_faq_id column to track Golden Set entries created from expert feedback."""
    from sqlalchemy import inspect

    conn = op.get_bind()

    # Check if column already exists (may be created by SQLModel.metadata.create_all in tests)
    col_result = conn.execute(
        sa.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'expert_feedback' AND column_name = 'generated_faq_id'
        """)
    )
    column_exists = col_result.fetchone() is not None

    if not column_exists:
        # Add generated_faq_id column (matches faq_entries.id type: String(100))
        op.add_column("expert_feedback", sa.Column("generated_faq_id", sa.String(length=100), nullable=True))

    # Check if faq_entries table exists before creating foreign key
    # This makes the migration robust in case FAQ tables migration wasn't applied
    inspector = inspect(conn)
    if "faq_entries" in inspector.get_table_names():
        # Check if FK already exists
        fk_names = [fk["name"] for fk in inspector.get_foreign_keys("expert_feedback")]
        if "fk_expert_feedback_generated_faq_id" not in fk_names:
            # Add foreign key constraint to faq_entries
            op.create_foreign_key(
                "fk_expert_feedback_generated_faq_id",
                "expert_feedback",
                "faq_entries",
                ["generated_faq_id"],
                ["id"],
                ondelete="SET NULL",
            )

    # Create index for efficient lookups (IF NOT EXISTS)
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_expert_feedback_generated_faq_id ON expert_feedback (generated_faq_id)"
        )
    )


def downgrade():
    """Remove generated_faq_id column and related constraints."""
    from sqlalchemy import inspect

    # Drop index
    op.drop_index("idx_expert_feedback_generated_faq_id", "expert_feedback")

    # Check if foreign key exists before dropping
    conn = op.get_bind()
    inspector = inspect(conn)
    fk_names = [fk["name"] for fk in inspector.get_foreign_keys("expert_feedback")]
    if "fk_expert_feedback_generated_faq_id" in fk_names:
        # Drop foreign key
        op.drop_constraint("fk_expert_feedback_generated_faq_id", "expert_feedback", type_="foreignkey")

    # Drop column
    op.drop_column("expert_feedback", "generated_faq_id")
