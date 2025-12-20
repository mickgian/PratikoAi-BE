"""Add proactivity analytics tables DEV-156

Revision ID: add_proactivity_analytics_20251220
Revises: fix_guillemets_fts_20251209
Create Date: 2025-12-20

This migration creates tables for tracking proactive feature analytics:
- suggested_action_clicks: Tracks when users click suggested actions
- interactive_question_answers: Tracks when users answer interactive questions

Both tables support:
- Anonymous users (nullable user_id)
- GDPR compliance via ON DELETE CASCADE on user_id foreign key
- Analytics and future ML model training
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_proactivity_analytics_20251220"
down_revision = "fix_guillemets_fts_20251209"
branch_labels = None
depends_on = None


def upgrade():
    """Create proactivity analytics tables."""
    # Create suggested_action_clicks table
    op.create_table(
        "suggested_action_clicks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action_template_id", sa.String(), nullable=False),
        sa.Column("action_label", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=True),
        sa.Column("clicked_at", sa.DateTime(), nullable=False),
        sa.Column("context_hash", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="suggested_action_clicks_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_suggested_action_clicks_session_id",
        "suggested_action_clicks",
        ["session_id"],
    )
    op.create_index(
        "ix_suggested_action_clicks_user_id",
        "suggested_action_clicks",
        ["user_id"],
    )
    op.create_index(
        "ix_suggested_action_clicks_action_template_id",
        "suggested_action_clicks",
        ["action_template_id"],
    )
    op.create_index(
        "ix_suggested_action_clicks_domain",
        "suggested_action_clicks",
        ["domain"],
    )

    # Create interactive_question_answers table
    op.create_table(
        "interactive_question_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("question_id", sa.String(), nullable=False),
        sa.Column("selected_option", sa.String(), nullable=False),
        sa.Column("custom_input", sa.String(), nullable=True),
        sa.Column("answered_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="interactive_question_answers_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_interactive_question_answers_session_id",
        "interactive_question_answers",
        ["session_id"],
    )
    op.create_index(
        "ix_interactive_question_answers_user_id",
        "interactive_question_answers",
        ["user_id"],
    )
    op.create_index(
        "ix_interactive_question_answers_question_id",
        "interactive_question_answers",
        ["question_id"],
    )


def downgrade():
    """Drop proactivity analytics tables."""
    op.drop_index(
        "ix_interactive_question_answers_question_id",
        table_name="interactive_question_answers",
    )
    op.drop_index(
        "ix_interactive_question_answers_user_id",
        table_name="interactive_question_answers",
    )
    op.drop_index(
        "ix_interactive_question_answers_session_id",
        table_name="interactive_question_answers",
    )
    op.drop_table("interactive_question_answers")

    op.drop_index(
        "ix_suggested_action_clicks_domain",
        table_name="suggested_action_clicks",
    )
    op.drop_index(
        "ix_suggested_action_clicks_action_template_id",
        table_name="suggested_action_clicks",
    )
    op.drop_index(
        "ix_suggested_action_clicks_user_id",
        table_name="suggested_action_clicks",
    )
    op.drop_index(
        "ix_suggested_action_clicks_session_id",
        table_name="suggested_action_clicks",
    )
    op.drop_table("suggested_action_clicks")
