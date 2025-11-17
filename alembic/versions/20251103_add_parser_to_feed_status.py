"""Add parser column to feed_status table

Revision ID: add_parser_feed_status_20251103
Revises: fts_unaccent_weights_20251103
Create Date: 2025-11-03

This migration adds a parser column to feed_status to specify which
parser function to use for each RSS feed. This supports:
- Explicit parser selection per feed
- Health checking with correct parser
- DB-driven feed configuration
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_parser_feed_status_20251103"
down_revision = "fts_unaccent_weights_20251103"
branch_labels = None
depends_on = None


def upgrade():
    """Add parser column to feed_status"""
    # Add parser column (idempotent - using raw SQL with IF NOT EXISTS check)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='feed_status' AND column_name='parser'
            ) THEN
                ALTER TABLE feed_status ADD COLUMN parser TEXT;
            END IF;
        END $$;
    """
    )

    # Backfill known parsers based on source and feed_type
    # agenzia_normativa: For Agenzia Entrate normativa/prassi feeds
    op.execute(
        """
        UPDATE feed_status
        SET parser = 'agenzia_normativa'
        WHERE source = 'agenzia_entrate'
          AND feed_type = 'normativa_prassi'
          AND parser IS NULL;
    """
    )

    # generic: For Agenzia Entrate news and other generic feeds
    op.execute(
        """
        UPDATE feed_status
        SET parser = 'generic'
        WHERE source = 'agenzia_entrate'
          AND feed_type = 'news'
          AND parser IS NULL;
    """
    )

    # inps: For INPS feeds
    op.execute(
        """
        UPDATE feed_status
        SET parser = 'inps'
        WHERE source = 'inps'
          AND parser IS NULL;
    """
    )

    # gazzetta_ufficiale: For Gazzetta Ufficiale feeds
    op.execute(
        """
        UPDATE feed_status
        SET parser = 'gazzetta_ufficiale'
        WHERE source = 'gazzetta_ufficiale'
          AND parser IS NULL;
    """
    )

    # generic: For governo and any other feeds
    op.execute(
        """
        UPDATE feed_status
        SET parser = 'generic'
        WHERE parser IS NULL;
    """
    )

    # Create index on parser column for faster lookups
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_feed_status_parser
        ON feed_status(parser);
    """
    )


def downgrade():
    """Remove parser column from feed_status"""
    # Drop index
    op.execute("DROP INDEX IF EXISTS idx_feed_status_parser;")

    # Drop column
    op.execute(
        """
        ALTER TABLE feed_status DROP COLUMN IF EXISTS parser;
    """
    )
