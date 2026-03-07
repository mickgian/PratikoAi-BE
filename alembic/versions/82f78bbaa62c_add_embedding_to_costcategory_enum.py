"""add_embedding_to_costcategory_enum

Revision ID: 82f78bbaa62c
Revises: c1e8314d9b6d
Create Date: 2026-03-07 10:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "82f78bbaa62c"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "c1e8314d9b6d"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add 'embedding' value to costcategory enum if it doesn't exist
    op.execute("ALTER TYPE costcategory ADD VALUE IF NOT EXISTS 'embedding'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    # The 'embedding' value will remain in the enum type.
    pass
