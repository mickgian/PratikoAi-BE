"""Improve FTS with unaccent and weighted search

Revision ID: fts_unaccent_weights_20251103
Revises: vector_indexes_20251103
Create Date: 2025-11-03

This migration improves Full-Text Search by:
- Enabling unaccent extension for accent-insensitive search
- Creating weighted FTS trigger functions (title='A', content='B')
- Recreating triggers idempotently
- Ensuring GIN indexes exist
- Backfilling search vectors with new weighted, unaccented logic
- Running VACUUM ANALYZE for planner statistics
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "fts_unaccent_weights_20251103"
down_revision = "vector_indexes_20251103"
branch_labels = None
depends_on = None


def upgrade():
    """Improve FTS with unaccent and weighted search"""
    # Enable unaccent extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")

    # Create or replace trigger function for knowledge_items
    # Uses weighted search: title='A' (highest weight), content='B'
    op.execute(
        """
        CREATE OR REPLACE FUNCTION knowledge_items_tsv_update()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('italian', unaccent(coalesce(NEW.title, ''))), 'A') ||
                setweight(to_tsvector('italian', unaccent(coalesce(NEW.content, ''))), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Create or replace trigger function for knowledge_chunks
    # Uses 'B' weight for chunk text
    op.execute(
        """
        CREATE OR REPLACE FUNCTION knowledge_chunks_tsv_update()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('italian', unaccent(coalesce(NEW.chunk_text, ''))), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Drop existing triggers if they exist, then recreate
    op.execute("DROP TRIGGER IF EXISTS trg_ki_tsv ON knowledge_items;")
    op.execute(
        """
        CREATE TRIGGER trg_ki_tsv
        BEFORE INSERT OR UPDATE ON knowledge_items
        FOR EACH ROW
        EXECUTE FUNCTION knowledge_items_tsv_update();
    """
    )

    op.execute("DROP TRIGGER IF EXISTS trg_kc_tsv ON knowledge_chunks;")
    op.execute(
        """
        CREATE TRIGGER trg_kc_tsv
        BEFORE INSERT OR UPDATE ON knowledge_chunks
        FOR EACH ROW
        EXECUTE FUNCTION knowledge_chunks_tsv_update();
    """
    )

    # Ensure GIN indexes exist (idempotent)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ki_fts
        ON knowledge_items USING GIN (search_vector);
    """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_kc_fts
        ON knowledge_chunks USING GIN (search_vector);
    """
    )

    # Backfill search vectors with weighted, unaccented FTS
    # This is safe to re-run
    print("Backfilling knowledge_items search vectors...")
    op.execute(
        """
        UPDATE knowledge_items
        SET search_vector =
            setweight(to_tsvector('italian', unaccent(coalesce(title, ''))), 'A') ||
            setweight(to_tsvector('italian', unaccent(coalesce(content, ''))), 'B');
    """
    )

    print("Backfilling knowledge_chunks search vectors...")
    op.execute(
        """
        UPDATE knowledge_chunks
        SET search_vector =
            setweight(to_tsvector('italian', unaccent(coalesce(chunk_text, ''))), 'B');
    """
    )

    # Run VACUUM ANALYZE for planner statistics
    # Note: VACUUM cannot run inside a transaction, but ANALYZE can
    # For production, run VACUUM manually outside the migration if needed
    print("Running ANALYZE...")
    op.execute("ANALYZE knowledge_items;")
    op.execute("ANALYZE knowledge_chunks;")


def downgrade():
    """Revert FTS improvements"""
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trg_ki_tsv ON knowledge_items;")
    op.execute("DROP TRIGGER IF EXISTS trg_kc_tsv ON knowledge_chunks;")

    # Drop trigger functions
    op.execute("DROP FUNCTION IF EXISTS knowledge_items_tsv_update();")
    op.execute("DROP FUNCTION IF EXISTS knowledge_chunks_tsv_update();")

    # Note: We don't drop indexes or extension as they may be used elsewhere
    # Note: We don't revert search_vector values as downgrade is rarely needed
