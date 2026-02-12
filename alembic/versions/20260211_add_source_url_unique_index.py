"""Add partial unique index on source_url (DEV-258).

Creates a partial unique index on knowledge_items.source_url for active
items only. This prevents future URL duplicates while allowing NULL
source_urls and archived/deleted items.

NOTE: Run AFTER the repair script has deduplicated existing URL duplicates,
otherwise this migration will fail on constraint violation.

Revision ID: add_source_url_idx_20260211
Revises: add_content_hash_20260211
Create Date: 2026-02-11 10:30:00.000000

"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "add_source_url_idx_20260211"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "add_content_hash_20260211"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Partial unique index: only active items with non-null source_url
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_source_url_active
            ON knowledge_items (source_url)
            WHERE source_url IS NOT NULL AND status = 'active'
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS idx_knowledge_source_url_active"))
