#!/usr/bin/env python3
"""Cleanup irrelevant Gazzetta Ufficiale documents from knowledge base.

DEV-247: Script to remove irrelevant content (concorsi, nomine, graduatorie)
from the knowledge base using conservative blacklist matching.

Usage:
    # Dry run (show what would be deleted without deleting)
    python scripts/cleanup_irrelevant_gazzetta.py --dry-run

    # Actual cleanup (requires confirmation)
    python scripts/cleanup_irrelevant_gazzetta.py

    # Skip confirmation prompt
    python scripts/cleanup_irrelevant_gazzetta.py --yes

    # Limit number of deletions
    python scripts/cleanup_irrelevant_gazzetta.py --limit 100
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.logging import logger  # noqa: E402
from app.ingest.rss_normativa import is_relevant_for_pratikoai  # noqa: E402
from app.models.knowledge import KnowledgeItem  # noqa: E402
from app.models.knowledge_chunk import KnowledgeChunk  # noqa: E402


async def delete_document(
    session: AsyncSession,
    document_id: int,
    dry_run: bool = True,
) -> bool:
    """Delete a document and its chunks from the knowledge base.

    Args:
        session: Database session
        document_id: ID of the document to delete
        dry_run: If True, don't actually delete

    Returns:
        True if deletion succeeded (or would succeed in dry run)
    """
    try:
        # First delete chunks (foreign key constraint)
        chunks_query = delete(KnowledgeChunk).where(KnowledgeChunk.knowledge_item_id == document_id)

        if not dry_run:
            result = await session.execute(chunks_query)
            chunks_deleted = result.rowcount
        else:
            # Count chunks that would be deleted
            count_query = select(KnowledgeChunk).where(KnowledgeChunk.knowledge_item_id == document_id)
            count_result = await session.execute(count_query)
            chunks_deleted = len(count_result.scalars().all())

        # Then delete the document
        doc_query = delete(KnowledgeItem).where(KnowledgeItem.id == document_id)

        if not dry_run:
            await session.execute(doc_query)
            await session.commit()

        logger.info(
            "gazzetta_document_deleted",
            document_id=document_id,
            chunks_deleted=chunks_deleted,
            dry_run=dry_run,
        )

        return True

    except Exception as e:
        logger.error(
            "gazzetta_document_delete_failed",
            document_id=document_id,
            error=str(e),
        )
        if not dry_run:
            await session.rollback()
        return False


async def cleanup_irrelevant_documents(
    session: AsyncSession,
    dry_run: bool = True,
    limit: int | None = None,
) -> dict:
    """Cleanup irrelevant Gazzetta documents from the knowledge base.

    Args:
        session: Database session
        dry_run: If True, only report what would be deleted
        limit: Maximum number of documents to delete

    Returns:
        Cleanup statistics dictionary
    """
    print("\n" + "=" * 80)
    print("GAZZETTA UFFICIALE CLEANUP")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will delete)'}")
    print(f"Limit: {limit if limit else 'No limit'}")
    print(f"Started: {datetime.now(UTC).isoformat()}")
    print()

    # Query all Gazzetta documents
    query = select(KnowledgeItem).where(
        KnowledgeItem.source.like("%gazzetta%")  # type: ignore[union-attr]
        | KnowledgeItem.source_url.like("%gazzettaufficiale%")  # type: ignore[union-attr]
    )
    result = await session.execute(query)
    documents = result.scalars().all()

    print(f"Total Gazzetta documents found: {len(documents)}")
    print()

    # Find irrelevant documents
    irrelevant_docs = []
    for doc in documents:
        if not is_relevant_for_pratikoai(doc.title, ""):
            irrelevant_docs.append(doc)

    print(f"Irrelevant documents identified: {len(irrelevant_docs)}")

    if limit:
        irrelevant_docs = irrelevant_docs[:limit]
        print(f"Documents to process (after limit): {len(irrelevant_docs)}")

    print()

    # Delete documents
    stats = {
        "total_found": len(documents),
        "irrelevant_identified": len(irrelevant_docs),
        "deleted": 0,
        "failed": 0,
        "dry_run": dry_run,
    }

    if irrelevant_docs:
        print("=" * 80)
        print(f"{'DELETING' if not dry_run else 'WOULD DELETE'} DOCUMENTS:")
        print("=" * 80)

        for i, doc in enumerate(irrelevant_docs, 1):
            title = doc.title[:60] + "..." if len(doc.title or "") > 60 else doc.title
            print(f"  [{i}/{len(irrelevant_docs)}] ID={doc.id}: {title}")

            success = await delete_document(session, doc.id, dry_run=dry_run)
            if success:
                stats["deleted"] += 1
            else:
                stats["failed"] += 1

    # Summary
    print()
    print("=" * 80)
    print("CLEANUP SUMMARY")
    print("=" * 80)
    print(f"Total documents scanned: {stats['total_found']}")
    print(f"Irrelevant documents identified: {stats['irrelevant_identified']}")
    print(f"Documents {'deleted' if not dry_run else 'would be deleted'}: {stats['deleted']}")
    print(f"Failures: {stats['failed']}")
    print(f"Completed: {datetime.now(UTC).isoformat()}")
    print("=" * 80)

    return stats


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Cleanup irrelevant Gazzetta Ufficiale documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be deleted without deleting (default)",
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete documents (opposite of --dry-run)",
    )

    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of documents to delete",
    )

    args = parser.parse_args()

    # Determine dry_run mode
    dry_run = not args.execute

    # Confirmation for live mode
    if not dry_run and not args.yes:
        print("\n⚠️  WARNING: This will permanently delete documents from the database!")
        print("Run with --dry-run first to see what would be deleted.")
        response = input("\nType 'DELETE' to proceed: ")
        if response != "DELETE":
            print("Aborted.")
            sys.exit(0)

    # Create async database session
    postgres_url = settings.POSTGRES_URL
    if postgres_url.startswith("postgresql://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session_maker() as session:
            stats = await cleanup_irrelevant_documents(
                session,
                dry_run=dry_run,
                limit=args.limit,
            )

            # Exit code based on results
            if stats["failed"] > 0:
                sys.exit(1)
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)

    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
