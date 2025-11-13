"""Add regulatory documents tables for Dynamic Knowledge Collection System

Revision ID: add_regulatory_documents_20250804
Revises: add_postgresql_fts_20250804
Create Date: 2025-08-04

This migration adds tables to support the Dynamic Knowledge Collection System:
- regulatory_documents: Store documents from Italian authorities
- feed_status: Track RSS feed health and monitoring
- document_processing_log: Log document processing activities
- document_collections: Group related documents

"""

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_regulatory_documents_20250804"
down_revision = "add_postgresql_fts_20250804"
branch_labels = None
depends_on = None


def upgrade():
    """Add regulatory documents tables."""

    # Create regulatory_documents table
    op.create_table(
        "regulatory_documents",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "source", sa.String(length=100), nullable=False, comment="Source authority (agenzia_entrate, inps, etc.)"
        ),
        sa.Column(
            "source_type",
            sa.String(length=100),
            nullable=False,
            comment="Document type (circolari, risoluzioni, etc.)",
        ),
        sa.Column("title", sa.Text(), nullable=False, comment="Document title"),
        sa.Column("url", sa.Text(), nullable=False, comment="Original document URL"),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True, comment="Official publication date"),
        sa.Column("content", sa.Text(), nullable=False, comment="Extracted text content"),
        sa.Column("content_hash", sa.String(length=64), nullable=False, comment="SHA256 hash for duplicate detection"),
        sa.Column("document_number", sa.String(length=50), nullable=True, comment="Official document number"),
        sa.Column("authority", sa.String(length=200), nullable=True, comment="Publishing authority name"),
        sa.Column("metadata", postgresql.JSON(), nullable=True, comment="Additional document metadata"),
        sa.Column("version", sa.Integer(), nullable=False, default=1, comment="Document version number"),
        sa.Column(
            "previous_version_id",
            sa.String(length=100),
            nullable=True,
            comment="ID of previous version if this is an update",
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, default="pending", comment="Current processing status"
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When document was successfully processed",
        ),
        sa.Column("processing_errors", sa.Text(), nullable=True, comment="Any errors encountered during processing"),
        sa.Column("knowledge_item_id", sa.Integer(), nullable=True, comment="Associated knowledge_items record ID"),
        sa.Column("topics", sa.Text(), nullable=True, comment="Comma-separated list of topics/keywords"),
        sa.Column(
            "importance_score",
            sa.Float(),
            nullable=False,
            default=0.5,
            comment="Calculated importance score (0.0-1.0)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
            comment="Record creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
            comment="Last update timestamp",
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True, comment="When document was archived"),
        sa.Column("archive_reason", sa.Text(), nullable=True, comment="Reason for archiving"),
    )

    # Create indexes for regulatory_documents
    op.create_index("idx_regulatory_documents_source", "regulatory_documents", ["source"])
    op.create_index("idx_regulatory_documents_source_type", "regulatory_documents", ["source_type"])
    op.create_index("idx_regulatory_documents_status", "regulatory_documents", ["status"])
    op.create_index("idx_regulatory_documents_published_date", "regulatory_documents", ["published_date"])
    op.create_index("idx_regulatory_documents_content_hash", "regulatory_documents", ["content_hash"])
    op.create_index("idx_regulatory_documents_url", "regulatory_documents", ["url"])
    op.create_index("idx_regulatory_documents_created_at", "regulatory_documents", ["created_at"])
    op.create_index("idx_regulatory_documents_updated_at", "regulatory_documents", ["updated_at"])

    # Create compound indexes for common queries
    op.create_index("idx_regulatory_documents_source_status", "regulatory_documents", ["source", "status"])
    op.create_index("idx_regulatory_documents_status_published", "regulatory_documents", ["status", "published_date"])

    # Create unique constraint on URL (only one active document per URL)
    op.create_index("idx_regulatory_documents_url_unique", "regulatory_documents", ["url"], unique=True)

    # Create feed_status table
    op.create_table(
        "feed_status",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("feed_url", sa.Text(), nullable=False, comment="RSS feed URL"),
        sa.Column("source", sa.String(length=100), nullable=True, comment="Source authority"),
        sa.Column("feed_type", sa.String(length=100), nullable=True, comment="Type of feed"),
        sa.Column(
            "status", sa.String(length=20), nullable=False, comment="Current status (healthy, unhealthy, error)"
        ),
        sa.Column(
            "last_checked",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
            comment="Last health check timestamp",
        ),
        sa.Column(
            "last_success", sa.DateTime(timezone=True), nullable=True, comment="Last successful fetch timestamp"
        ),
        sa.Column("response_time_ms", sa.Float(), nullable=True, comment="Last response time in milliseconds"),
        sa.Column("items_found", sa.Integer(), nullable=True, comment="Number of items in last successful fetch"),
        sa.Column(
            "consecutive_errors", sa.Integer(), nullable=False, default=0, comment="Count of consecutive errors"
        ),
        sa.Column("errors", sa.Integer(), nullable=False, default=0, comment="Total error count"),
        sa.Column("last_error", sa.Text(), nullable=True, comment="Last error message"),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True, comment="Last error timestamp"),
        sa.Column(
            "check_interval_minutes", sa.Integer(), nullable=False, default=240, comment="Check interval in minutes"
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=True, comment="Whether feed monitoring is enabled"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
            comment="Record creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
            comment="Last update timestamp",
        ),
    )

    # Create unique constraint on feed_url
    op.create_index("idx_feed_status_url_unique", "feed_status", ["feed_url"], unique=True)

    # Create indexes for feed_status
    op.create_index("idx_feed_status_source", "feed_status", ["source"])
    op.create_index("idx_feed_status_status", "feed_status", ["status"])
    op.create_index("idx_feed_status_last_checked", "feed_status", ["last_checked"])
    op.create_index("idx_feed_status_enabled", "feed_status", ["enabled"])
    op.create_index("idx_feed_status_errors", "feed_status", ["consecutive_errors"])

    # Create document_processing_log table
    op.create_table(
        "document_processing_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.String(length=100), nullable=True, comment="Associated regulatory document ID"),
        sa.Column("document_url", sa.Text(), nullable=False, comment="Document URL"),
        sa.Column(
            "operation", sa.String(length=50), nullable=False, comment="Operation type (create, update, archive, etc.)"
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, comment="Operation status (success, failed, partial)"
        ),
        sa.Column("processing_time_ms", sa.Float(), nullable=True, comment="Processing time in milliseconds"),
        sa.Column("content_length", sa.Integer(), nullable=True, comment="Extracted content length"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="Error message if operation failed"),
        sa.Column("error_details", postgresql.JSON(), nullable=True, comment="Detailed error information"),
        sa.Column(
            "triggered_by",
            sa.String(length=50),
            nullable=False,
            comment="What triggered this operation (scheduler, manual, api)",
        ),
        sa.Column("feed_url", sa.Text(), nullable=True, comment="Source RSS feed URL"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
            comment="Log entry timestamp",
        ),
    )

    # Create indexes for document_processing_log
    op.create_index("idx_document_processing_log_document_id", "document_processing_log", ["document_id"])
    op.create_index("idx_document_processing_log_operation", "document_processing_log", ["operation"])
    op.create_index("idx_document_processing_log_status", "document_processing_log", ["status"])
    op.create_index("idx_document_processing_log_created_at", "document_processing_log", ["created_at"])
    op.create_index("idx_document_processing_log_triggered_by", "document_processing_log", ["triggered_by"])

    # Create compound index for common queries
    op.create_index("idx_document_processing_log_status_date", "document_processing_log", ["status", "created_at"])

    # Create document_collections table
    op.create_table(
        "document_collections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=200), nullable=False, comment="Collection name"),
        sa.Column("description", sa.Text(), nullable=True, comment="Collection description"),
        sa.Column("source", sa.String(length=100), nullable=False, comment="Primary source authority"),
        sa.Column("document_type", sa.String(length=100), nullable=False, comment="Type of documents in collection"),
        sa.Column("document_count", sa.Integer(), nullable=False, default=0, comment="Number of documents"),
        sa.Column("total_content_length", sa.Integer(), nullable=False, default=0, comment="Total content length"),
        sa.Column(
            "earliest_document",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Publication date of earliest document",
        ),
        sa.Column(
            "latest_document", sa.DateTime(timezone=True), nullable=True, comment="Publication date of latest document"
        ),
        sa.Column("status", sa.String(length=20), nullable=False, default="active", comment="Collection status"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
            comment="Collection creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
            comment="Last update timestamp",
        ),
    )

    # Create indexes for document_collections
    op.create_index("idx_document_collections_source", "document_collections", ["source"])
    op.create_index("idx_document_collections_document_type", "document_collections", ["document_type"])
    op.create_index("idx_document_collections_status", "document_collections", ["status"])
    op.create_index("idx_document_collections_created_at", "document_collections", ["created_at"])

    # Add foreign key constraint from regulatory_documents to document_collections (optional)
    # This is commented out since we might not always have collections
    # op.create_foreign_key(
    #     'fk_regulatory_documents_knowledge_item',
    #     'regulatory_documents',
    #     'knowledge_items',
    #     ['knowledge_item_id'],
    #     ['id'],
    #     ondelete='SET NULL'
    # )

    # Create trigger to update updated_at timestamp for regulatory_documents
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_regulatory_documents_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    op.execute(
        """
        CREATE TRIGGER update_regulatory_documents_updated_at_trigger
        BEFORE UPDATE ON regulatory_documents
        FOR EACH ROW
        EXECUTE FUNCTION update_regulatory_documents_updated_at();
    """
    )

    # Create trigger to update updated_at timestamp for feed_status
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_feed_status_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    op.execute(
        """
        CREATE TRIGGER update_feed_status_updated_at_trigger
        BEFORE UPDATE ON feed_status
        FOR EACH ROW
        EXECUTE FUNCTION update_feed_status_updated_at();
    """
    )

    # Create trigger to update updated_at timestamp for document_collections
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_document_collections_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    op.execute(
        """
        CREATE TRIGGER update_document_collections_updated_at_trigger
        BEFORE UPDATE ON document_collections
        FOR EACH ROW
        EXECUTE FUNCTION update_document_collections_updated_at();
    """
    )

    # Insert initial feed status records for Italian authorities
    # Note: This will be done manually after migration due to NOT NULL constraint issues
    # op.execute("""
    #     INSERT INTO feed_status (feed_url, source, feed_type, status, enabled, consecutive_errors, errors, check_interval_minutes) VALUES
    #     ('https://www.agenziaentrate.gov.it/portale/rss/circolari.xml', 'agenzia_entrate', 'circolari', 'pending', true, 0, 0, 240),
    #     ('https://www.agenziaentrate.gov.it/portale/rss/risoluzioni.xml', 'agenzia_entrate', 'risoluzioni', 'pending', true, 0, 0, 240),
    #     ('https://www.agenziaentrate.gov.it/portale/rss/provvedimenti.xml', 'agenzia_entrate', 'provvedimenti', 'pending', true, 0, 0, 240),
    #     ('https://www.inps.it/rss/circolari.xml', 'inps', 'circolari', 'pending', true, 0, 0, 240),
    #     ('https://www.inps.it/rss/messaggi.xml', 'inps', 'messaggi', 'pending', true, 0, 0, 240),
    #     ('https://www.gazzettaufficiale.it/rss/serie_generale.xml', 'gazzetta_ufficiale', 'serie_generale', 'pending', true, 0, 0, 240),
    #     ('https://www.gazzettaufficiale.it/rss/decreti.xml', 'gazzetta_ufficiale', 'decreti', 'pending', true, 0, 0, 240),
    #     ('https://www.governo.it/rss/decreti-legge.xml', 'governo', 'decreti_legge', 'pending', true, 0, 0, 240),
    #     ('https://www.governo.it/rss/dpcm.xml', 'governo', 'dpcm', 'pending', true, 0, 0, 240)
    # """)


def downgrade():
    """Remove regulatory documents tables."""

    # Drop triggers first
    op.execute("DROP TRIGGER IF EXISTS update_regulatory_documents_updated_at_trigger ON regulatory_documents;")
    op.execute("DROP TRIGGER IF EXISTS update_feed_status_updated_at_trigger ON feed_status;")
    op.execute("DROP TRIGGER IF EXISTS update_document_collections_updated_at_trigger ON document_collections;")

    # Drop trigger functions
    op.execute("DROP FUNCTION IF EXISTS update_regulatory_documents_updated_at();")
    op.execute("DROP FUNCTION IF EXISTS update_feed_status_updated_at();")
    op.execute("DROP FUNCTION IF EXISTS update_document_collections_updated_at();")

    # Drop tables (indexes and constraints will be dropped automatically)
    op.drop_table("document_processing_log")
    op.drop_table("document_collections")
    op.drop_table("feed_status")
    op.drop_table("regulatory_documents")
