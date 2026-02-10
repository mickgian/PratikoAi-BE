"""Add multi-model LLM comparison tables (DEV-256).

Creates tables for:
- model_comparison_sessions: Comparison session metadata
- model_comparison_responses: Individual model responses
- model_elo_ratings: Elo ratings per model
- user_model_preferences: User preferences for model selection

Revision ID: add_model_comparison_20260206
Revises: add_account_code_20260204
Create Date: 2026-02-06 10:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "add_model_comparison_20260206"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "add_account_code_20260204"  # pragma: allowlist secret
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
    """Create model comparison tables."""
    # 1. Create model_comparison_sessions table
    if not table_exists("model_comparison_sessions"):
        op.create_table(
            "model_comparison_sessions",
            sa.Column("id", UUID(), nullable=False),
            sa.Column("batch_id", sa.String(64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("query_text", sa.String(2000), nullable=False),
            sa.Column("query_hash", sa.String(64), nullable=False),
            sa.Column("models_compared", sa.String(500), nullable=False),
            sa.Column("winner_model", sa.String(100), nullable=True),
            sa.Column("vote_timestamp", sa.DateTime(), nullable=True),
            sa.Column("vote_comment", sa.String(1000), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        )

        # Indexes for model_comparison_sessions
        op.create_index("ix_model_comparison_sessions_id", "model_comparison_sessions", ["id"])
        op.create_index(
            "ix_model_comparison_sessions_batch_id", "model_comparison_sessions", ["batch_id"], unique=True
        )
        op.create_index("ix_model_comparison_sessions_user_id", "model_comparison_sessions", ["user_id"])
        op.create_index("ix_model_comparison_sessions_query_hash", "model_comparison_sessions", ["query_hash"])

    # 2. Create model_comparison_responses table
    if not table_exists("model_comparison_responses"):
        op.create_table(
            "model_comparison_responses",
            sa.Column("id", UUID(), nullable=False),
            sa.Column("session_id", UUID(), nullable=False),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("model_name", sa.String(100), nullable=False),
            sa.Column("response_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("trace_id", sa.String(64), nullable=False),
            sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("cost_eur", sa.Float(), nullable=True),
            sa.Column("input_tokens", sa.Integer(), nullable=True),
            sa.Column("output_tokens", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="success"),
            sa.Column("error_message", sa.String(1000), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["session_id"],
                ["model_comparison_sessions.id"],
                ondelete="CASCADE",
            ),
        )

        # Indexes for model_comparison_responses
        op.create_index("ix_model_comparison_responses_id", "model_comparison_responses", ["id"])
        op.create_index("ix_model_comparison_responses_session_id", "model_comparison_responses", ["session_id"])
        op.create_index("ix_model_comparison_responses_provider", "model_comparison_responses", ["provider"])
        op.create_index("ix_model_comparison_responses_model_name", "model_comparison_responses", ["model_name"])

    # 3. Create model_elo_ratings table
    if not table_exists("model_elo_ratings"):
        op.create_table(
            "model_elo_ratings",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("model_name", sa.String(100), nullable=False),
            sa.Column("elo_rating", sa.Float(), nullable=False, server_default="1500.0"),
            sa.Column("total_comparisons", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_updated", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("provider", "model_name", name="uq_model_elo_ratings_provider_model"),
        )

        # Indexes for model_elo_ratings
        op.create_index("ix_model_elo_ratings_provider", "model_elo_ratings", ["provider"])
        op.create_index("ix_model_elo_ratings_model_name", "model_elo_ratings", ["model_name"])
        op.create_index("ix_model_elo_ratings_elo_rating", "model_elo_ratings", ["elo_rating"])

    # 4. Create user_model_preferences table
    if not table_exists("user_model_preferences"):
        op.create_table(
            "user_model_preferences",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("model_name", sa.String(100), nullable=False),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "user_id", "provider", "model_name", name="uq_user_model_preferences_user_provider_model"
            ),
        )

        # Indexes for user_model_preferences
        op.create_index("ix_user_model_preferences_user_id", "user_model_preferences", ["user_id"])


def downgrade() -> None:
    """Drop model comparison tables."""
    # Drop in reverse order of creation (due to foreign key constraints)
    if table_exists("user_model_preferences"):
        op.drop_index("ix_user_model_preferences_user_id", table_name="user_model_preferences")
        op.drop_table("user_model_preferences")

    if table_exists("model_elo_ratings"):
        op.drop_index("ix_model_elo_ratings_elo_rating", table_name="model_elo_ratings")
        op.drop_index("ix_model_elo_ratings_model_name", table_name="model_elo_ratings")
        op.drop_index("ix_model_elo_ratings_provider", table_name="model_elo_ratings")
        op.drop_table("model_elo_ratings")

    if table_exists("model_comparison_responses"):
        op.drop_index("ix_model_comparison_responses_model_name", table_name="model_comparison_responses")
        op.drop_index("ix_model_comparison_responses_provider", table_name="model_comparison_responses")
        op.drop_index("ix_model_comparison_responses_session_id", table_name="model_comparison_responses")
        op.drop_index("ix_model_comparison_responses_id", table_name="model_comparison_responses")
        op.drop_table("model_comparison_responses")

    if table_exists("model_comparison_sessions"):
        op.drop_index("ix_model_comparison_sessions_query_hash", table_name="model_comparison_sessions")
        op.drop_index("ix_model_comparison_sessions_user_id", table_name="model_comparison_sessions")
        op.drop_index("ix_model_comparison_sessions_batch_id", table_name="model_comparison_sessions")
        op.drop_index("ix_model_comparison_sessions_id", table_name="model_comparison_sessions")
        op.drop_table("model_comparison_sessions")
