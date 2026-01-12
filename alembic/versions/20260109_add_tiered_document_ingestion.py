"""Add tiered document ingestion fields ADR-023

Revision ID: add_tiered_ingestion_20260109
Revises: add_proactivity_analytics_20251220
Create Date: 2026-01-09

This migration adds fields to knowledge_items for tiered document ingestion:
- tier: Document importance tier (1=CRITICAL, 2=IMPORTANT, 3=REFERENCE)
- parent_document_id: Foreign key for hierarchical storage (law -> articles)
- article_number: Article identifier for Italian laws (e.g., "Art. 1", "Art. 2-bis")
- topics: Array of topic tags for enhanced search
- document_type: Type of chunk (full_document, article, chunk, allegato)
- parsing_metadata: JSONB for parsing details (cross-references, commi count, etc.)

Related to:
- DEV-242: Response Quality & Suggested Actions Fixes
- ADR-023: Tiered Document Ingestion
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_tiered_ingestion_20260109"
down_revision = "add_proactivity_analytics_20251220"
branch_labels = None
depends_on = None


def upgrade():
    """Add tiered document ingestion fields to knowledge_items."""
    # Add tier field (1=CRITICAL, 2=IMPORTANT, 3=REFERENCE)
    op.add_column(
        "knowledge_items",
        sa.Column("tier", sa.Integer(), nullable=True, server_default="2"),
    )

    # Add parent document reference for hierarchical storage
    op.add_column(
        "knowledge_items",
        sa.Column("parent_document_id", sa.Integer(), nullable=True),
    )

    # Add foreign key constraint for parent_document_id
    op.create_foreign_key(
        "fk_knowledge_items_parent_document",
        "knowledge_items",
        "knowledge_items",
        ["parent_document_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add article metadata
    op.add_column(
        "knowledge_items",
        sa.Column("article_number", sa.String(50), nullable=True),
    )

    # Add topics array for topic tagging
    op.add_column(
        "knowledge_items",
        sa.Column("topics", postgresql.ARRAY(sa.Text()), nullable=True),
    )

    # Add document type (full_document, article, chunk, allegato)
    op.add_column(
        "knowledge_items",
        sa.Column(
            "document_type",
            sa.String(50),
            nullable=True,
            server_default="chunk",
        ),
    )

    # Add parsing metadata JSONB
    op.add_column(
        "knowledge_items",
        sa.Column("parsing_metadata", postgresql.JSONB(), nullable=True),
    )

    # Create indexes for efficient querying
    op.create_index(
        "ix_knowledge_items_tier",
        "knowledge_items",
        ["tier"],
    )
    op.create_index(
        "ix_knowledge_items_parent_document_id",
        "knowledge_items",
        ["parent_document_id"],
    )
    op.create_index(
        "ix_knowledge_items_article_number",
        "knowledge_items",
        ["article_number"],
    )
    op.create_index(
        "ix_knowledge_items_document_type",
        "knowledge_items",
        ["document_type"],
    )
    # GIN index for topics array (supports && overlap operator)
    op.create_index(
        "ix_knowledge_items_topics",
        "knowledge_items",
        ["topics"],
        postgresql_using="gin",
    )

    # Composite index for tiered search
    op.create_index(
        "ix_knowledge_items_tier_document_type",
        "knowledge_items",
        ["tier", "document_type"],
    )

    # Update existing records to tier 2 (default) and document_type chunk
    op.execute("UPDATE knowledge_items SET tier = 2 WHERE tier IS NULL")
    op.execute("UPDATE knowledge_items SET document_type = 'chunk' WHERE document_type IS NULL")


def downgrade():
    """Remove tiered document ingestion fields from knowledge_items."""
    # Drop indexes
    op.drop_index("ix_knowledge_items_tier_document_type", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_topics", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_document_type", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_article_number", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_parent_document_id", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_tier", table_name="knowledge_items")

    # Drop foreign key
    op.drop_constraint(
        "fk_knowledge_items_parent_document",
        "knowledge_items",
        type_="foreignkey",
    )

    # Drop columns
    op.drop_column("knowledge_items", "parsing_metadata")
    op.drop_column("knowledge_items", "document_type")
    op.drop_column("knowledge_items", "topics")
    op.drop_column("knowledge_items", "article_number")
    op.drop_column("knowledge_items", "parent_document_id")
    op.drop_column("knowledge_items", "tier")
