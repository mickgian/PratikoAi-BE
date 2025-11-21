"""Enable pgvector extension for vector similarity search

Revision ID: enable_pgvector_20251103
Revises: add_regulatory_docs_20250804
Create Date: 2025-11-03

This migration enables the pgvector extension if available on the server.
If pgvector is not installed on the PostgreSQL server, a notice is raised.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "enable_pgvector_20251103"
down_revision = "20250811_add_user_oauth_fields"
branch_labels = None
depends_on = None


def upgrade():
    """Enable pgvector extension if available"""
    # Ensure plpgsql is present (usually is by default)
    op.execute("CREATE EXTENSION IF NOT EXISTS plpgsql;")

    # Enable pgvector if available on server
    op.execute(
        """
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name='vector') THEN
        CREATE EXTENSION IF NOT EXISTS vector;
      ELSE
        RAISE NOTICE 'pgvector extension not available on this server.';
      END IF;
    END$$;
    """
    )


def downgrade():
    """Keep extension installed - no downgrade needed"""
    pass
