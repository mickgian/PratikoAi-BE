"""Add CASCADE to query_history foreign key for GDPR compliance

Revision ID: 20251129_cascade_fk
Revises: c1e8314d9b6d
Create Date: 2025-11-29 16:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251129_cascade_fk"
down_revision = "c1e8314d9b6d"
branch_labels = None
depends_on = None


def upgrade():
    """Add ON DELETE CASCADE to query_history.user_id foreign key.

    This ensures GDPR Right to Erasure (Article 17) compliance by automatically
    deleting all chat history when a user is deleted.
    """
    # Drop existing foreign key constraint
    op.drop_constraint("query_history_user_id_fkey", "query_history", type_="foreignkey")

    # Recreate foreign key with CASCADE delete
    op.create_foreign_key(
        "query_history_user_id_fkey", "query_history", "user", ["user_id"], ["id"], ondelete="CASCADE"
    )


def downgrade():
    """Remove CASCADE from query_history.user_id foreign key.

    Reverts to original foreign key without CASCADE behavior.
    """
    # Drop CASCADE foreign key
    op.drop_constraint("query_history_user_id_fkey", "query_history", type_="foreignkey")

    # Recreate original foreign key without CASCADE
    op.create_foreign_key("query_history_user_id_fkey", "query_history", "user", ["user_id"], ["id"])
