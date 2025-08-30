"""Add OAuth fields to User model

Revision ID: 20250811_add_user_oauth_fields
Revises: 20250805_add_gdpr_deletion_system
Create Date: 2025-08-11 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250811_add_user_oauth_fields'
down_revision = '20250805_add_gdpr_deletion_system'
branch_labels = None
depends_on = None


def upgrade():
    """Add OAuth support fields to users table."""
    
    # Add OAuth profile fields
    op.add_column('users', sa.Column('name', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(512), nullable=True))
    op.add_column('users', sa.Column('provider', sa.String(50), nullable=False, default='email'))
    op.add_column('users', sa.Column('provider_id', sa.String(255), nullable=True))
    
    # Make hashed_password nullable for OAuth users
    op.alter_column('users', 'hashed_password', nullable=True)
    
    # Create indexes for OAuth fields
    op.create_index('ix_users_provider', 'users', ['provider'])
    op.create_index('ix_users_provider_id', 'users', ['provider_id'])
    
    # Add composite unique constraint for provider + provider_id to prevent duplicates
    op.create_unique_constraint(
        'uq_users_provider_provider_id',
        'users',
        ['provider', 'provider_id']
    )
    
    # Add check constraint for valid providers
    op.create_check_constraint(
        'ck_users_provider_valid',
        'users',
        sa.text("provider IN ('email', 'google', 'linkedin')"),
    )
    
    # Add check constraint to ensure OAuth users have provider_id
    op.create_check_constraint(
        'ck_users_oauth_provider_id',
        'users',
        sa.text("(provider = 'email' AND provider_id IS NULL) OR (provider != 'email' AND provider_id IS NOT NULL)"),
    )
    
    # Add check constraint to ensure email users have password or OAuth users don't require it
    op.create_check_constraint(
        'ck_users_auth_method',
        'users',
        sa.text("(provider = 'email' AND hashed_password IS NOT NULL) OR (provider != 'email')"),
    )
    
    # Add comments for documentation
    op.execute("COMMENT ON COLUMN users.name IS 'User full name from OAuth provider or manual registration'")
    op.execute("COMMENT ON COLUMN users.avatar_url IS 'URL to user profile picture from OAuth provider'")
    op.execute("COMMENT ON COLUMN users.provider IS 'Authentication provider: email, google, linkedin'")
    op.execute("COMMENT ON COLUMN users.provider_id IS 'Unique user ID from OAuth provider'")


def downgrade():
    """Remove OAuth fields from users table."""
    
    # Drop constraints
    op.drop_constraint('ck_users_auth_method', 'users', type_='check')
    op.drop_constraint('ck_users_oauth_provider_id', 'users', type_='check')
    op.drop_constraint('ck_users_provider_valid', 'users', type_='check')
    op.drop_constraint('uq_users_provider_provider_id', 'users', type_='unique')
    
    # Drop indexes
    op.drop_index('ix_users_provider_id', 'users')
    op.drop_index('ix_users_provider', 'users')
    
    # Make hashed_password not nullable again
    op.alter_column('users', 'hashed_password', nullable=False)
    
    # Drop OAuth columns
    op.drop_column('users', 'provider_id')
    op.drop_column('users', 'provider')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'name')