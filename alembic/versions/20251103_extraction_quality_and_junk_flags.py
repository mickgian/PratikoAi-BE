"""Add extraction quality and junk detection fields

Revision ID: extraction_quality_junk_20251103
Revises: add_parser_feed_status_20251103
Create Date: 2025-11-03

This migration adds fields for PDF extraction quality tracking and junk chunk detection:

knowledge_items:
- extraction_method: Track how text was extracted (pdf_text, mixed, ocr)
- text_quality: Document-level quality score (0.0-1.0)
- ocr_pages: JSON array of OCR'd pages with reasons

knowledge_chunks:
- quality_score: Chunk-level quality score (0.0-1.0)
- junk: Boolean flag for corrupted/low-quality chunks
- ocr_used: Boolean flag indicating if OCR was used for this chunk
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "extraction_quality_junk_20251103"
down_revision = "add_parser_feed_status_20251103"
branch_labels = None
depends_on = None


def upgrade():
    """Add extraction quality and junk detection fields"""

    # Add fields to knowledge_items
    op.execute(
        """
        DO $$
        BEGIN
            -- extraction_method: 'pdf_text' | 'mixed' | 'ocr'
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='knowledge_items' AND column_name='extraction_method'
            ) THEN
                ALTER TABLE knowledge_items ADD COLUMN extraction_method TEXT;
            END IF;

            -- text_quality: 0.0-1.0 document-level quality score
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='knowledge_items' AND column_name='text_quality'
            ) THEN
                ALTER TABLE knowledge_items ADD COLUMN text_quality NUMERIC;
            END IF;

            -- ocr_pages: JSON array like [{"page": 3, "reason": "low_quality"}]
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='knowledge_items' AND column_name='ocr_pages'
            ) THEN
                ALTER TABLE knowledge_items ADD COLUMN ocr_pages JSONB;
            END IF;

            -- Ensure kb_epoch exists (should already exist, but check)
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='knowledge_items' AND column_name='kb_epoch'
            ) THEN
                ALTER TABLE knowledge_items ADD COLUMN kb_epoch BIGINT DEFAULT 0;
            END IF;
        END $$;
    """
    )

    # Add fields to knowledge_chunks
    op.execute(
        """
        DO $$
        BEGIN
            -- quality_score: 0.0-1.0 chunk-level quality score
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='knowledge_chunks' AND column_name='quality_score'
            ) THEN
                ALTER TABLE knowledge_chunks ADD COLUMN quality_score NUMERIC;
            END IF;

            -- junk: Boolean flag for corrupted chunks
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='knowledge_chunks' AND column_name='junk'
            ) THEN
                ALTER TABLE knowledge_chunks ADD COLUMN junk BOOLEAN NOT NULL DEFAULT FALSE;
            END IF;

            -- ocr_used: Boolean flag indicating OCR was used
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='knowledge_chunks' AND column_name='ocr_used'
            ) THEN
                ALTER TABLE knowledge_chunks ADD COLUMN ocr_used BOOLEAN NOT NULL DEFAULT FALSE;
            END IF;

            -- Ensure start_char exists (should already exist, but check)
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='knowledge_chunks' AND column_name='start_char'
            ) THEN
                ALTER TABLE knowledge_chunks ADD COLUMN start_char INT;
            END IF;

            -- Ensure end_char exists (should already exist, but check)
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='knowledge_chunks' AND column_name='end_char'
            ) THEN
                ALTER TABLE knowledge_chunks ADD COLUMN end_char INT;
            END IF;
        END $$;
    """
    )

    # Create index on non-junk chunks (for faster retrieval filtering)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_kc_not_junk
        ON knowledge_chunks(knowledge_item_id)
        WHERE junk = FALSE;
    """
    )

    # Create index on extraction_method for reporting
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ki_extraction_method
        ON knowledge_items(extraction_method)
        WHERE extraction_method IS NOT NULL;
    """
    )

    # Create index on text_quality for finding low-quality docs
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ki_text_quality
        ON knowledge_items(text_quality)
        WHERE text_quality IS NOT NULL;
    """
    )


def downgrade():
    """Remove extraction quality and junk detection fields"""

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_kc_not_junk;")
    op.execute("DROP INDEX IF EXISTS idx_ki_extraction_method;")
    op.execute("DROP INDEX IF EXISTS idx_ki_text_quality;")

    # Drop columns from knowledge_chunks
    op.execute(
        """
        ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS quality_score;
        ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS junk;
        ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS ocr_used;
    """
    )

    # Drop columns from knowledge_items
    op.execute(
        """
        ALTER TABLE knowledge_items DROP COLUMN IF EXISTS extraction_method;
        ALTER TABLE knowledge_items DROP COLUMN IF EXISTS text_quality;
        ALTER TABLE knowledge_items DROP COLUMN IF EXISTS ocr_pages;
    """
    )
