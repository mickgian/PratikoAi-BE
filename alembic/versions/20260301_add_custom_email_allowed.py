"""Add custom_email_allowed column to billing_plans (DEV-444, ADR-034).

The BillingPlan model already had this field but the original
20260212_add_billing_tables migration did not include the column.
This caused a startup crash on QA: column billing_plans.custom_email_allowed
does not exist.

Revision ID: add_custom_email_20260301
Revises: persist_comparison_20260228
Create Date: 2026-03-01 10:49:11.476929

"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "add_custom_email_20260301"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "persist_comparison_20260228"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # Check if column already exists (idempotent)
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'billing_plans' AND column_name = 'custom_email_allowed')"
        )
    )
    if result.scalar():
        return

    op.add_column(
        "billing_plans",
        sa.Column("custom_email_allowed", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Update existing seed rows: Pro and Premium allow custom email
    op.execute(
        sa.text(
            "UPDATE billing_plans SET custom_email_allowed = true "
            "WHERE slug IN ('pro', 'premium')"
        )
    )


def downgrade() -> None:
    op.drop_column("billing_plans", "custom_email_allowed")
