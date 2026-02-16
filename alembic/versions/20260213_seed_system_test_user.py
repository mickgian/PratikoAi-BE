"""Seed system test user for E2E test cost tracking (DEV-257).

Inserts a permanent system user (id=50000) used as FK target when
non-numeric user_ids (e.g., "e2e_test_abc") are mapped by UsageTracker.
This allows E2E test LLM costs to be persisted and included in the
daily cost report under environment="test".

ID 50000 is safely below the test cleanup threshold (id >= 99999)
used in tests/conftest.py and well above normal auto-increment IDs.

Revision ID: seed_test_user_20260213
Revises: add_billing_20260212
Create Date: 2026-02-13 10:00:00.000000

"""

from typing import Sequence

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "seed_test_user_20260213"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "add_billing_20260212"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO "user" (id, email, name, provider, hashed_password, role, created_at, billing_plan_slug)
        VALUES (50000,
                'system_test@pratikoai.internal',
                'System Test User',
                'email',
                '$2b$12$systemtestuser000000000000000000000000000000000000000',
                'admin',
                NOW(),
                'base') ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("""DELETE FROM "user" WHERE id = 50000""")
