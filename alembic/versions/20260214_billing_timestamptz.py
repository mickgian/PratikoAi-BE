"""Migrate billing datetime columns to TIMESTAMPTZ (DEV-257).

Fixes asyncpg DataError when querying billing tables with timezone-aware
datetimes: columns were created as TIMESTAMP WITHOUT TIME ZONE but
application code uses datetime.now(UTC) (aware). The USING clause treats
existing naive values as UTC — no data loss.

Revision ID: billing_timestamptz_20260214
Revises: seed_test_user_20260213
Create Date: 2026-02-14 10:00:00.000000

"""

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = "billing_timestamptz_20260214"
down_revision = "seed_test_user_20260213"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE billing_plans ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE usage_windows ALTER COLUMN recorded_at TYPE TIMESTAMPTZ USING recorded_at AT TIME ZONE 'UTC'"
    )
    op.execute("ALTER TABLE user_credits ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'")
    op.execute(
        "ALTER TABLE credit_transactions ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE billing_plans ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE usage_windows ALTER COLUMN recorded_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE user_credits ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE credit_transactions ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
