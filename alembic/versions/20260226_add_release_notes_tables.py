"""Add release notes tables for versioning system.

Creates 2 tables:
  - release_notes: stores release notes with dual content (technical + user-facing)
  - user_release_note_seen: tracks which users have seen which release notes

Revision ID: add_release_notes_20260226
Revises: rename_golden_set_20260220
Create Date: 2026-02-26 10:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "add_release_notes_20260226"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "rename_golden_set_20260220"  # pragma: allowlist secret
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

    # --- release_notes ---
    if not _table_exists("release_notes"):
        op.create_table(
            "release_notes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("version", sa.String(length=20), nullable=False),
            sa.Column("user_notes", sa.Text(), nullable=False),
            sa.Column("technical_notes", sa.Text(), nullable=False),
            sa.Column(
                "released_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("version"),
        )
        op.create_index("ix_release_notes_version", "release_notes", ["version"])
        op.create_index("ix_release_notes_released_at", "release_notes", ["released_at"])

    # --- user_release_note_seen ---
    if not _table_exists("user_release_note_seen"):
        op.create_table(
            "user_release_note_seen",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("release_note_id", sa.Integer(), nullable=False),
            sa.Column(
                "seen_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["release_note_id"], ["release_notes.id"]),
            sa.UniqueConstraint("user_id", "release_note_id", name="uq_user_release_note"),
        )
        op.create_index(
            "ix_user_release_note_seen_release_note_id",
            "user_release_note_seen",
            ["release_note_id"],
        )


def downgrade() -> None:
    op.drop_table("user_release_note_seen")
    op.drop_table("release_notes")
