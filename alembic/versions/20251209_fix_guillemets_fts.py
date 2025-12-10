"""Fix guillemets breaking FTS tokenization

Revision ID: fix_guillemets_fts_20251209
Revises: add_expanded_rss_feeds_20251204
Create Date: 2025-12-09

Bug Fix:
    When PostgreSQL's unaccent() function processes guillemets («»), it converts them
    to double angle brackets (<<>>). The Italian FTS tokenizer then treats the
    surrounding text as an operator/symbol and DROPS it entirely.

Example:
        Input: «Coppa Piacentina»
        After unaccent(): <<Coppa Piacentina>>
        After to_tsvector('italian', ...): EMPTY (no tokens!)

    This caused search failures for Italian DOP products and other quoted terminology.

Solution:
    Replace guillemets with SPACES before calling unaccent() so words are properly
    tokenized as separate terms.

    NEW: replace(replace(text, '«', ' '), '»', ' ')

    Result: "Coppa Piacentina" → 'copp':1 'piacentin':2 ✅
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "fix_guillemets_fts_20251209"
down_revision = "add_expanded_rss_feeds_20251204"
branch_labels = None
depends_on = None


def _normalize_text_for_fts(column_expr: str) -> str:
    """Wrap column in guillemet replacement before unaccent.

    Converts: «text» → text (with spaces for word boundary)
    """
    return f"unaccent(replace(replace(coalesce({column_expr}, ''), '«', ' '), '»', ' '))"


def upgrade():
    """Fix FTS triggers to handle guillemets correctly."""
    # Update trigger function for knowledge_items
    # Replaces guillemets with spaces before unaccent()
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION knowledge_items_tsv_update()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('italian', {_normalize_text_for_fts("NEW.title")}), 'A') ||
                setweight(to_tsvector('italian', {_normalize_text_for_fts("NEW.content")}), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Update trigger function for knowledge_chunks
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION knowledge_chunks_tsv_update()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('italian', {_normalize_text_for_fts("NEW.chunk_text")}), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Backfill ALL rows to regenerate search_vector with fixed tokenization
    print("Backfilling knowledge_items search vectors (guillemet fix)...")
    op.execute(
        f"""
        UPDATE knowledge_items
        SET search_vector =
            setweight(to_tsvector('italian', {_normalize_text_for_fts("title")}), 'A') ||
            setweight(to_tsvector('italian', {_normalize_text_for_fts("content")}), 'B');
    """
    )

    print("Backfilling knowledge_chunks search vectors (guillemet fix)...")
    op.execute(
        f"""
        UPDATE knowledge_chunks
        SET search_vector =
            setweight(to_tsvector('italian', {_normalize_text_for_fts("chunk_text")}), 'B');
    """
    )

    # Run ANALYZE for query planner
    print("Running ANALYZE...")
    op.execute("ANALYZE knowledge_items;")
    op.execute("ANALYZE knowledge_chunks;")


def downgrade():
    """Revert to original trigger functions without guillemet handling."""
    # Restore original knowledge_items trigger
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

    # Restore original knowledge_chunks trigger
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

    # Note: We don't backfill on downgrade since this would reintroduce the bug
