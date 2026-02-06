"""Add account_code column to user table (DEV-255).

Revision ID: add_account_code_20260204
Revises: add_intent_labeling_20260203
Create Date: 2026-02-04 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "add_account_code_20260204"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "add_intent_labeling_20260203"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add account_code column and backfill existing users."""
    # Add nullable column
    op.add_column("user", sa.Column("account_code", sa.String(length=20), nullable=True))

    # Create unique index
    op.create_index("ix_user_account_code", "user", ["account_code"], unique=True)

    # Backfill existing users with generated account codes
    # Backfill existing users with email-based account codes
    # Format: {first_3_letters}{hundreds}{2_random}-{id}
    # Example: MGI70021-1 (from michele.giannone@gmail.com)
    op.execute(
        sa.text(
            """
            UPDATE "user"
            SET account_code =
                    CASE
                        WHEN LENGTH(REGEXP_REPLACE(SPLIT_PART(email, '@', 1), '[^a-zA-Z]', '', 'g')) >= 3
                            THEN UPPER(LEFT (REGEXP_REPLACE(SPLIT_PART(email, '@', 1), '[^a-zA-Z]', '', 'g'), 3))
                        ELSE RPAD(UPPER(REGEXP_REPLACE(SPLIT_PART(email, '@', 1), '[^a-zA-Z]', '', 'g')), 3, 'X')
                        END ||
                    ((FLOOR(RANDOM() * 8 + 2)::INT) * 100)::TEXT ||
                   LPAD(FLOOR(RANDOM() * 100)::TEXT, 2, '0') ||
                   '-' || id
            WHERE account_code IS NULL
            """
        )
    )


def downgrade() -> None:
    """Remove account_code column."""
    op.drop_index("ix_user_account_code", table_name="user")
    op.drop_column("user", "account_code")
