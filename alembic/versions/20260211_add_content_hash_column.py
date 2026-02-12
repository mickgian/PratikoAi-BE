"""Add content_hash column to knowledge_items (DEV-258).

Adds SHA-256 content hash for deduplication. Backfills existing rows
using PostgreSQL's encode(sha256(...), 'hex').

Revision ID: add_content_hash_20260211
Revises: add_metrics_pending_20260209
Create Date: 2026-02-11 10:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "add_content_hash_20260211"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "add_metrics_pending_20260209"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table_name
                AND column_name = :column_name
            )
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar()


def upgrade() -> None:
    # Add content_hash column
    if not column_exists("knowledge_items", "content_hash"):
        op.add_column(
            "knowledge_items",
            sa.Column("content_hash", sa.String(64), nullable=True),
        )

    # Backfill existing rows with SHA-256 of content
    op.execute(
        sa.text(
            """
            UPDATE knowledge_items
            SET content_hash = encode(sha256(content::bytea), 'hex')
            WHERE content_hash IS NULL
            """
        )
    )

    # Create index on content_hash for fast dedup lookups
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_knowledge_content_hash
            ON knowledge_items (content_hash)
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS idx_knowledge_content_hash"))
    op.drop_column("knowledge_items", "content_hash")
