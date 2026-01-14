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

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = "add_tiered_ingestion_20260109"
down_revision = "add_proactivity_analytics_20251220"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table_name AND column_name = :column_name
            )
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar()


def index_exists(index_name: str, alt_index_name: str | None = None) -> bool:
    """Check if an index exists (checks both primary and alternative names).

    The model and migration may create indexes with different naming patterns:
    - Model: idx_knowledge_tier
    - Migration: ix_knowledge_items_tier
    """
    conn = op.get_bind()
    names_to_check = [index_name]
    if alt_index_name:
        names_to_check.append(alt_index_name)

    for name in names_to_check:
        result = conn.execute(
            sa.text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes WHERE indexname = :index_name
                )
                """
            ),
            {"index_name": name},
        )
        if result.scalar():
            return True
    return False


def constraint_exists(constraint_name: str) -> bool:
    """Check if a constraint exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = :constraint_name
            )
            """
        ),
        {"constraint_name": constraint_name},
    )
    return result.scalar()


def upgrade():
    """Add tiered document ingestion fields to knowledge_items.

    This migration is idempotent - it checks if columns/indexes exist before creating them.
    This is necessary because init_db_tables.py may have already created them from the model.
    """
    # Add tier field (1=CRITICAL, 2=IMPORTANT, 3=REFERENCE)
    if not column_exists("knowledge_items", "tier"):
        op.add_column(
            "knowledge_items",
            sa.Column("tier", sa.Integer(), nullable=True, server_default="2"),
        )

    # Add parent document reference for hierarchical storage
    if not column_exists("knowledge_items", "parent_document_id"):
        op.add_column(
            "knowledge_items",
            sa.Column("parent_document_id", sa.Integer(), nullable=True),
        )

    # Add foreign key constraint for parent_document_id
    if not constraint_exists("fk_knowledge_items_parent_document"):
        op.create_foreign_key(
            "fk_knowledge_items_parent_document",
            "knowledge_items",
            "knowledge_items",
            ["parent_document_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # Add article metadata
    if not column_exists("knowledge_items", "article_number"):
        op.add_column(
            "knowledge_items",
            sa.Column("article_number", sa.String(50), nullable=True),
        )

    # Add topics array for topic tagging
    if not column_exists("knowledge_items", "topics"):
        op.add_column(
            "knowledge_items",
            sa.Column("topics", postgresql.ARRAY(sa.Text()), nullable=True),
        )

    # Add document type (full_document, article, chunk, allegato)
    if not column_exists("knowledge_items", "document_type"):
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
    if not column_exists("knowledge_items", "parsing_metadata"):
        op.add_column(
            "knowledge_items",
            sa.Column("parsing_metadata", postgresql.JSONB(), nullable=True),
        )

    # Create indexes for efficient querying (check existence first)
    # Note: Also check for model-created indexes with different naming pattern (idx_knowledge_*)
    if not index_exists("ix_knowledge_items_tier", "idx_knowledge_tier"):
        op.create_index(
            "ix_knowledge_items_tier",
            "knowledge_items",
            ["tier"],
        )
    if not index_exists("ix_knowledge_items_parent_document_id", "idx_knowledge_parent_document_id"):
        op.create_index(
            "ix_knowledge_items_parent_document_id",
            "knowledge_items",
            ["parent_document_id"],
        )
    if not index_exists("ix_knowledge_items_article_number", "idx_knowledge_article_number"):
        op.create_index(
            "ix_knowledge_items_article_number",
            "knowledge_items",
            ["article_number"],
        )
    if not index_exists("ix_knowledge_items_document_type", "idx_knowledge_document_type"):
        op.create_index(
            "ix_knowledge_items_document_type",
            "knowledge_items",
            ["document_type"],
        )
    # GIN index for topics array (supports && overlap operator)
    if not index_exists("ix_knowledge_items_topics", "idx_knowledge_topics"):
        op.create_index(
            "ix_knowledge_items_topics",
            "knowledge_items",
            ["topics"],
            postgresql_using="gin",
        )

    # Composite index for tiered search
    if not index_exists("ix_knowledge_items_tier_document_type", "idx_knowledge_tier_document_type"):
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
