"""Add publication_date column to knowledge_items

Revision ID: 20251111_add_pub_date
Revises: extraction_quality_junk_20251103
Create Date: 2025-11-11

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251111_add_pub_date"
down_revision = "extraction_quality_junk_20251103"
branch_labels = None
depends_on = None


def upgrade():
    """Add publication_date column to knowledge_items table."""
    # Add column
    op.execute(
        """
        ALTER TABLE knowledge_items
        ADD COLUMN IF NOT EXISTS publication_date DATE;
    """
    )

    # Add index for publication_date filtering
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ki_publication_date
        ON knowledge_items(publication_date)
        WHERE publication_date IS NOT NULL;
    """
    )

    print("✅ Added publication_date column to knowledge_items")


def downgrade():
    """Remove publication_date column from knowledge_items table."""
    op.execute("DROP INDEX IF EXISTS idx_ki_publication_date;")
    op.execute("ALTER TABLE knowledge_items DROP COLUMN IF EXISTS publication_date;")
    print("✅ Removed publication_date column from knowledge_items")
