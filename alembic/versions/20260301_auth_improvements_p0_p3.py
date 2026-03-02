"""Auth improvements P0-P3: email verification, password reset, login attempts, TOTP 2FA.

Adds new tables: email_verification, password_reset, login_attempt, totp_device.
Adds new columns to user: email_verified, failed_login_attempts, account_locked_until, totp_enabled.

Revision ID: auth_improvements_20260301
Revises: persist_comparison_20260228
Create Date: 2026-03-01 12:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "auth_improvements_20260301"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "persist_comparison_20260228"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = :table AND column_name = :col"),
        {"table": table_name, "col": column_name},
    )
    return result.fetchone() is not None


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT to_regclass(:table)"),
        {"table": table_name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    # -- New user columns (P0/P1/P2) --
    if not column_exists("user", "email_verified"):
        op.add_column("user", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"))

    if not column_exists("user", "failed_login_attempts"):
        op.add_column("user", sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))

    if not column_exists("user", "account_locked_until"):
        op.add_column("user", sa.Column("account_locked_until", sa.DateTime(timezone=True), nullable=True))

    if not column_exists("user", "totp_enabled"):
        op.add_column("user", sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"))

    # -- Email verification table (P0) --
    if not table_exists("email_verification"):
        op.create_table(
            "email_verification",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False, index=True),
            sa.Column("token", sa.String(255), nullable=False, unique=True, index=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    # -- Password reset table (P0) --
    if not table_exists("password_reset"):
        op.create_table(
            "password_reset",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False, index=True),
            sa.Column("token_hash", sa.String(255), nullable=False),
            sa.Column("token_prefix", sa.String(8), nullable=False, server_default="", index=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
    else:
        # Add token_prefix column if table exists but column doesn't
        if not column_exists("password_reset", "token_prefix"):
            op.add_column(
                "password_reset",
                sa.Column("token_prefix", sa.String(8), nullable=False, server_default="", index=True),
            )
            op.create_index("ix_password_reset_token_prefix", "password_reset", ["token_prefix"])

    # -- Login attempt table (P2) --
    if not table_exists("login_attempt"):
        op.create_table(
            "login_attempt",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=True, index=True),
            sa.Column("email", sa.String(255), nullable=False, index=True),
            sa.Column("ip_address", sa.String(45), nullable=False, server_default=""),
            sa.Column("user_agent", sa.String(512), nullable=False, server_default=""),
            sa.Column("success", sa.Boolean(), nullable=False, server_default="false", index=True),
            sa.Column("failure_reason", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    # -- TOTP device table (P2) --
    if not table_exists("totp_device"):
        op.create_table(
            "totp_device",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False, index=True),
            sa.Column("secret_encrypted", sa.String(512), nullable=False),
            sa.Column("name", sa.String(100), nullable=False, server_default="Autenticatore"),
            sa.Column("confirmed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("backup_codes_json", sa.String(512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
    else:
        # Rename backup_codes_hash -> backup_codes_json if old column exists
        if column_exists("totp_device", "backup_codes_hash") and not column_exists("totp_device", "backup_codes_json"):
            op.alter_column("totp_device", "backup_codes_hash", new_column_name="backup_codes_json")


def downgrade() -> None:
    op.drop_table("totp_device")
    op.drop_table("login_attempt")
    op.drop_table("password_reset")
    op.drop_table("email_verification")

    op.drop_column("user", "totp_enabled")
    op.drop_column("user", "account_locked_until")
    op.drop_column("user", "failed_login_attempts")
    op.drop_column("user", "email_verified")
