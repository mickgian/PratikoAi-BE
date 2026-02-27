"""Add billing tables for usage-based billing (DEV-257).

Creates 4 tables:
  - billing_plans: plan definitions (Base, Pro, Premium)
  - usage_windows: rolling window cost tracking
  - user_credits: per-user credit balance
  - credit_transactions: credit transaction log

Also adds billing_plan_slug column to the user table.

Revision ID: add_billing_20260212
Revises: add_source_url_idx_20260211
Create Date: 2026-02-12 12:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "add_billing_20260212"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "add_source_url_idx_20260211"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    def _table_exists(name: str) -> bool:
        result = conn.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :name)"
            ),
            {"name": name},
        )
        return result.scalar()  # type: ignore[return-value]

    def _column_exists(table: str, column: str) -> bool:
        result = conn.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = :column)"
            ),
            {"table": table, "column": column},
        )
        return result.scalar()  # type: ignore[return-value]

    def _index_exists(name: str) -> bool:
        result = conn.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM pg_indexes " "WHERE indexname = :name)"),
            {"name": name},
        )
        return result.scalar()  # type: ignore[return-value]

    # --- billing_plans ---
    if not _table_exists("billing_plans"):
        op.create_table(
            "billing_plans",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("slug", sa.String(50), nullable=False, unique=True, index=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("price_eur_monthly", sa.Float(), nullable=False),
            sa.Column("monthly_cost_limit_eur", sa.Float(), nullable=False),
            sa.Column("window_5h_cost_limit_eur", sa.Float(), nullable=False),
            sa.Column("window_7d_cost_limit_eur", sa.Float(), nullable=False),
            sa.Column("credit_markup_factor", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("stripe_price_id", sa.String(255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", index=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # --- usage_windows ---
    if not _table_exists("usage_windows"):
        op.create_table(
            "usage_windows",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
            ),
            sa.Column("window_type", sa.String(10), nullable=False),
            sa.Column("cost_eur", sa.Float(), nullable=False),
            sa.Column("recorded_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True),
            sa.Column(
                "usage_event_id", sa.Integer(), sa.ForeignKey("usage_events.id", ondelete="SET NULL"), nullable=True
            ),
        )
    if not _index_exists("ix_usage_windows_user_window_time"):
        op.create_index(
            "ix_usage_windows_user_window_time",
            "usage_windows",
            ["user_id", "window_type", "recorded_at"],
        )

    # --- user_credits ---
    if not _table_exists("user_credits"):
        op.create_table(
            "user_credits",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("user.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
                index=True,
            ),
            sa.Column("balance_eur", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("extra_usage_enabled", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # --- credit_transactions ---
    if not _table_exists("credit_transactions"):
        op.create_table(
            "credit_transactions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
            ),
            sa.Column("transaction_type", sa.String(20), nullable=False),
            sa.Column("amount_eur", sa.Float(), nullable=False),
            sa.Column("balance_after_eur", sa.Float(), nullable=False),
            sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True),
            sa.Column(
                "usage_event_id", sa.Integer(), sa.ForeignKey("usage_events.id", ondelete="SET NULL"), nullable=True
            ),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True),
        )

    # --- Add billing_plan_slug to user ---
    if not _column_exists("user", "billing_plan_slug"):
        op.add_column(
            "user",
            sa.Column("billing_plan_slug", sa.String(50), nullable=False, server_default="base", index=True),
        )
    if not _index_exists("ix_user_billing_plan_slug"):
        op.create_index("ix_user_billing_plan_slug", "user", ["billing_plan_slug"])

    # --- Seed the 3 billing plans ---
    op.execute(
        sa.text(
            """
            INSERT INTO billing_plans (slug, name, price_eur_monthly, monthly_cost_limit_eur,
                                       window_5h_cost_limit_eur, window_7d_cost_limit_eur,
                                       credit_markup_factor, is_active)
            VALUES ('base', 'Base', 25.0, 10.0, 0.50, 2.50, 1.50, true),
                   ('pro', 'Pro', 75.0, 30.0, 1.00, 7.50, 1.30, true),
                   ('premium', 'Premium', 150.0, 60.0, 2.00, 15.00, 1.20, true) ON CONFLICT (slug) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_user_billing_plan_slug", table_name="user")
    op.drop_column("user", "billing_plan_slug")
    op.drop_table("credit_transactions")
    op.drop_table("user_credits")
    op.drop_index("ix_usage_windows_user_window_time", table_name="usage_windows")
    op.drop_table("usage_windows")
    op.drop_table("billing_plans")
