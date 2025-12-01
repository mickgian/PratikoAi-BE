"""Add role field to User model for RBAC

Revision ID: 20251124_add_user_role
Revises: 20250811_add_user_oauth_fields
Create Date: 2025-11-24 12:00:00.000000

Adds role-based access control (RBAC) to the User model.
Replaces trust_score validation with role-based validation for expert feedback.

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251124_add_user_role"
down_revision = "20251121_expert_feedback"
branch_labels = None
depends_on = None


def upgrade():
    """Add role field to users table."""
    # Add role column with default value 'user'
    op.add_column(
        "user",
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
    )

    # Create index on role for performance (role-based queries)
    op.create_index("ix_user_role", "user", ["role"])

    # Add check constraint for valid roles
    op.create_check_constraint(
        "ck_user_role_valid",
        "user",
        sa.text("role IN ('user', 'super_user', 'admin')"),
    )

    # Update admin user to super_user role (example)
    # Note: Update this with actual admin email in production
    # op.execute(
    #     """
    #     UPDATE "user"
    #     SET role = 'super_user'
    #     WHERE email = 'admin@example.com';
    #     """
    # )


def downgrade():
    """Remove role field from users table."""
    # Drop check constraint
    op.drop_constraint("ck_user_role_valid", "user", type_="check")

    # Drop index
    op.drop_index("ix_user_role", "user")

    # Drop role column
    op.drop_column("user", "role")
