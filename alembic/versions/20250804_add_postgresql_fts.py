"""Add PostgreSQL Full-Text Search support

Revision ID: add_postgresql_fts_20250804
Revises: 
Create Date: 2025-08-04

This migration adds:
- search_vector tsvector column to knowledge_items
- GIN index for fast full-text search
- Trigger to automatically update search vectors
- Italian language configuration support
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = 'add_postgresql_fts_20250804'
down_revision = None  # Update this with your latest migration
branch_labels = None
depends_on = None


def upgrade():
    """Add full-text search support to knowledge_items table"""
    
    # Add search_vector column with tsvector type
    op.add_column(
        'knowledge_items',
        sa.Column(
            'search_vector',
            postgresql.TSVECTOR,
            nullable=True,
            comment='Full-text search vector for Italian language'
        )
    )
    
    # Create GIN index for fast full-text search
    op.create_index(
        'idx_knowledge_items_search_vector',
        'knowledge_items',
        ['search_vector'],
        postgresql_using='gin'
    )
    
    # Create or replace function to update search vector
    op.execute("""
        CREATE OR REPLACE FUNCTION update_knowledge_search_vector() 
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('italian', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('italian', COALESCE(NEW.content, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for automatic search vector updates on INSERT and UPDATE
    op.execute("""
        CREATE TRIGGER update_knowledge_search_vector_trigger
        BEFORE INSERT OR UPDATE OF title, content
        ON knowledge_items
        FOR EACH ROW
        EXECUTE FUNCTION update_knowledge_search_vector();
    """)
    
    # Update existing records to populate search_vector
    op.execute("""
        UPDATE knowledge_items
        SET search_vector = 
            setweight(to_tsvector('italian', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('italian', COALESCE(content, '')), 'B')
        WHERE search_vector IS NULL;
    """)
    
    # Create additional indexes for performance
    # Index for category filtering combined with FTS
    op.create_index(
        'idx_knowledge_items_category_search',
        'knowledge_items',
        ['category', 'search_vector'],
        postgresql_using='gin'
    )
    
    # Create Italian-specific text search configuration if it doesn't exist
    # This ensures proper stemming and stop words for Italian
    op.execute("""
        DO $$
        BEGIN
            -- Check if Italian configuration exists
            IF NOT EXISTS (
                SELECT 1 FROM pg_ts_config WHERE cfgname = 'italian'
            ) THEN
                -- If not, create a custom one based on simple configuration
                CREATE TEXT SEARCH CONFIGURATION italian (COPY = simple);
                
                -- Add Italian-specific dictionary mappings if available
                -- This would require Italian dictionary files to be installed
                -- For now, we'll use the simple configuration
            END IF;
        END $$;
    """)
    
    # Add function for unaccent support (accent-insensitive search)
    op.execute("""
        CREATE EXTENSION IF NOT EXISTS unaccent;
    """)
    
    # Create custom search function with unaccent support
    op.execute("""
        CREATE OR REPLACE FUNCTION websearch_to_tsquery_italian(query text)
        RETURNS tsquery AS $$
        BEGIN
            -- Remove accents and convert to tsquery
            RETURN websearch_to_tsquery('italian', unaccent(query));
        EXCEPTION
            WHEN OTHERS THEN
                -- If websearch_to_tsquery fails, fall back to plainto_tsquery
                RETURN plainto_tsquery('italian', unaccent(query));
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
    """)
    
    # Create index on relevance_score for combined ranking
    op.create_index(
        'idx_knowledge_items_relevance_score',
        'knowledge_items',
        ['relevance_score'],
        postgresql_order='DESC'
    )


def downgrade():
    """Remove full-text search support"""
    
    # Drop custom functions
    op.execute("DROP FUNCTION IF EXISTS websearch_to_tsquery_italian(text) CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS update_knowledge_search_vector() CASCADE;")
    
    # Drop trigger
    op.execute("""
        DROP TRIGGER IF EXISTS update_knowledge_search_vector_trigger 
        ON knowledge_items;
    """)
    
    # Drop indexes
    op.drop_index('idx_knowledge_items_relevance_score', 'knowledge_items')
    op.drop_index('idx_knowledge_items_category_search', 'knowledge_items')
    op.drop_index('idx_knowledge_items_search_vector', 'knowledge_items')
    
    # Drop search_vector column
    op.drop_column('knowledge_items', 'search_vector')
    
    # Note: We don't drop the unaccent extension as it might be used elsewhere