"""Add OAuth fields to User model

Revision ID: 20250811_add_user_oauth_fields
Revises: 20250805_gdpr_deletion
Create Date: 2025-08-11 10:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250811_add_user_oauth_fields"
down_revision = "20250805_gdpr_deletion"
branch_labels = None
depends_on = None


def upgrade():
    """Add OAuth support fields to users table."""
    # Add OAuth profile fields (idempotent)
    op.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS name VARCHAR(255)')
    op.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(512)')
    op.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS provider VARCHAR(50) NOT NULL DEFAULT \'email\'')
    op.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS provider_id VARCHAR(255)')

    # Make hashed_password nullable for OAuth users (idempotent - fails silently if already nullable)
    try:
        op.alter_column("user", "hashed_password", nullable=True)
    except Exception:
        pass  # Column already nullable

    # Create indexes for OAuth fields (idempotent)
    try:
        op.create_index("ix_users_provider", "user", ["provider"])
    except Exception:
        pass  # Index already exists

    try:
        op.create_index("ix_users_provider_id", "user", ["provider_id"])
    except Exception:
        pass  # Index already exists

    # Add composite unique constraint for provider + provider_id to prevent duplicates (idempotent)
    try:
        op.create_unique_constraint("uq_users_provider_provider_id", "user", ["provider", "provider_id"])
    except Exception:
        pass  # Constraint already exists

    # Add check constraint for valid providers (idempotent)
    try:
        op.create_check_constraint(
            "ck_users_provider_valid",
            "user",
            sa.text("provider IN ('email', 'google', 'linkedin')"),
        )
    except Exception:
        pass  # Constraint already exists

    # Add check constraint to ensure OAuth users have provider_id (idempotent)
    try:
        op.create_check_constraint(
            "ck_users_oauth_provider_id",
            "user",
            sa.text("(provider = 'email' AND provider_id IS NULL) OR (provider != 'email' AND provider_id IS NOT NULL)"),
        )
    except Exception:
        pass  # Constraint already exists

    # Add check constraint to ensure email users have password or OAuth users don't require it (idempotent)
    try:
        op.create_check_constraint(
            "ck_users_auth_method",
            "user",
            sa.text("(provider = 'email' AND hashed_password IS NOT NULL) OR (provider != 'email')"),
        )
    except Exception:
        pass  # Constraint already exists

    # Add comments for documentation
    op.execute("COMMENT ON COLUMN \"user\".name IS 'User full name from OAuth provider or manual registration'")
    op.execute("COMMENT ON COLUMN \"user\".avatar_url IS 'URL to user profile picture from OAuth provider'")
    op.execute("COMMENT ON COLUMN \"user\".provider IS 'Authentication provider: email, google, linkedin'")
    op.execute("COMMENT ON COLUMN \"user\".provider_id IS 'Unique user ID from OAuth provider'")


def downgrade():
    """Remove OAuth fields from users table."""
    # Drop constraints
    op.drop_constraint("ck_users_auth_method", "user", type_="check")
    op.drop_constraint("ck_users_oauth_provider_id", "user", type_="check")
    op.drop_constraint("ck_users_provider_valid", "user", type_="check")
    op.drop_constraint("uq_users_provider_provider_id", "user", type_="unique")

    # Drop indexes
    op.drop_index("ix_users_provider_id", "user")
    op.drop_index("ix_users_provider", "user")

    # Make hashed_password not nullable again
    op.alter_column("user", "hashed_password", nullable=False)

    # Drop OAuth columns
    op.drop_column("user", "provider_id")
    op.drop_column("user", "provider")
    op.drop_column("user", "avatar_url")
    op.drop_column("user", "name")
