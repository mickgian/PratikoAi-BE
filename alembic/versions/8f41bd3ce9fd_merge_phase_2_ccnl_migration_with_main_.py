"""Merge Phase 2 CCNL migration with main branch

Revision ID: 8f41bd3ce9fd
Revises: 20251129_faq_embedding, 6c9df3d39110
Create Date: 2025-12-01 14:51:12.152124

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f41bd3ce9fd"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = ("20251129_faq_embedding", "6c9df3d39110")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
