#!/usr/bin/env python3
"""Backfill text_quality scores for knowledge items.

This script calculates and populates text_quality for documents that have
NULL text_quality values (typically HTML-sourced documents or older entries).

Uses the same text_metrics() algorithm as PDF extraction:
- quality_score = 0.5 * printable_ratio + 0.5 * alpha_ratio

Usage:
    python scripts/backfill_text_quality.py [--dry-run] [--batch-size N]

Environment variables:
    DATABASE_URL: PostgreSQL connection string (or uses docker default)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.text.extract_pdf import text_metrics


async def get_db_session() -> AsyncSession:
    """Create async database session."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://aifinance:devpass@localhost:5433/aifinance",  # pragma: allowlist secret
    )

    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    return async_session()


async def count_missing_quality(db: AsyncSession) -> int:
    """Count documents with missing text_quality."""
    result = await db.execute(text("SELECT COUNT(*) FROM knowledge_items WHERE text_quality IS NULL"))
    return result.scalar() or 0


async def count_total_documents(db: AsyncSession) -> int:
    """Count total documents."""
    result = await db.execute(text("SELECT COUNT(*) FROM knowledge_items"))
    return result.scalar() or 0


async def get_documents_missing_quality(db: AsyncSession, batch_size: int, offset: int) -> list[tuple[int, str]]:
    """Get batch of documents missing text_quality.

    Returns:
        List of (id, content) tuples
    """
    result = await db.execute(
        text("""
            SELECT id, content
            FROM knowledge_items
            WHERE text_quality IS NULL
            ORDER BY id
            LIMIT :batch_size OFFSET :offset
        """),
        {"batch_size": batch_size, "offset": offset},
    )
    return [(row.id, row.content) for row in result.fetchall()]


async def update_text_quality(db: AsyncSession, doc_id: int, quality_score: float) -> None:
    """Update text_quality for a single document."""
    await db.execute(
        text("""
            UPDATE knowledge_items
            SET text_quality = :quality_score
            WHERE id = :doc_id
        """),
        {"doc_id": doc_id, "quality_score": quality_score},
    )


async def main():
    """Run text_quality backfill."""
    parser = argparse.ArgumentParser(description="Backfill text_quality scores for knowledge items")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate but don't update database",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of documents to process per batch (default: 100)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("TEXT QUALITY BACKFILL SCRIPT")
    print("=" * 70)

    db = await get_db_session()

    try:
        # Get counts
        total_docs = await count_total_documents(db)
        missing_count = await count_missing_quality(db)
        existing_count = total_docs - missing_count

        print(f"\nTotal documents: {total_docs}")
        print(f"With text_quality: {existing_count}")
        print(f"Missing text_quality: {missing_count}")

        if missing_count == 0:
            print("\n✅ All documents already have text_quality scores!")
            return 0

        if args.dry_run:
            print("\n🔍 DRY RUN - Will calculate but not update database")

        print(f"\n{'=' * 70}")
        print(f"Processing {missing_count} documents...")
        print("=" * 70)

        processed = 0
        updated = 0
        quality_sum = 0.0
        high_quality_count = 0  # >= 0.8
        low_quality_count = 0  # < 0.5

        offset = 0
        while True:
            # Get batch of documents
            batch = await get_documents_missing_quality(db, args.batch_size, offset)
            if not batch:
                break

            for doc_id, content in batch:
                # Calculate text quality using the same algorithm as PDF extraction
                metrics = text_metrics(content or "")
                quality_score = metrics["quality_score"]

                # Track statistics
                quality_sum += quality_score
                if quality_score >= 0.8:
                    high_quality_count += 1
                elif quality_score < 0.5:
                    low_quality_count += 1

                # Update database (unless dry run)
                if not args.dry_run:
                    await update_text_quality(db, doc_id, quality_score)
                    updated += 1

                processed += 1

                # Progress indicator every 100 docs
                if processed % 100 == 0:
                    avg_quality = quality_sum / processed
                    print(f"  Processed {processed}/{missing_count} " f"(avg quality: {avg_quality:.3f})")

            # Commit batch
            if not args.dry_run:
                await db.commit()

            offset += args.batch_size

        # Final statistics
        avg_quality = quality_sum / processed if processed > 0 else 0.0

        print(f"\n{'=' * 70}")
        print("RESULTS")
        print("=" * 70)
        print(f"\nProcessed: {processed} documents")
        if not args.dry_run:
            print(f"Updated: {updated} documents")

        print("\nQuality Statistics:")
        print(f"  Average quality: {avg_quality:.3f}")
        print(f"  High quality (≥0.8): {high_quality_count} ({high_quality_count/processed*100:.1f}%)")
        print(f"  Low quality (<0.5): {low_quality_count} ({low_quality_count/processed*100:.1f}%)")

        if args.dry_run:
            print("\n⚠️  DRY RUN - No changes were made to the database")
            print("   Run without --dry-run to apply updates")
        else:
            print(f"\n✅ Successfully updated {updated} documents with text_quality scores")

        # Verify update
        if not args.dry_run:
            new_missing = await count_missing_quality(db)
            print(f"\nVerification: {new_missing} documents still missing text_quality")

        print("\n" + "=" * 70 + "\n")

        return 0

    finally:
        await db.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
