#!/usr/bin/env python3
"""
CLI Script for Manual RSS Feed Ingestion.

Database-driven RSS ingestion from feed_status table.
Processes all enabled feeds or filters by source/ID.

Usage:
    python scripts/ingest_rss.py --list
    python scripts/ingest_rss.py --limit 5
    python scripts/ingest_rss.py --source agenzia_entrate --all
    python scripts/ingest_rss.py --feed-id 2 --limit 10
"""

import argparse
import asyncio
import sys
from datetime import (
    UTC,
    datetime,
    timezone,
)
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.ingest.rss_normativa import run_rss_ingestion  # noqa: E402
from app.models.regulatory_documents import FeedStatus  # noqa: E402


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest regulatory documents from RSS feeds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all configured feeds
  python scripts/ingest_rss.py --list

  # Ingest 5 items from each enabled feed (default)
  python scripts/ingest_rss.py

  # Ingest 10 items from each feed
  python scripts/ingest_rss.py --limit 10

  # Ingest all items from all feeds
  python scripts/ingest_rss.py --all

  # Process specific source only
  python scripts/ingest_rss.py --source agenzia_entrate --all

  # Process specific feed by ID
  python scripts/ingest_rss.py --feed-id 2 --limit 5
        """,
    )

    parser.add_argument("--limit", type=int, default=5, help="Maximum number of items to process (default: 5)")

    parser.add_argument("--all", action="store_true", help="Process all items from feed (overrides --limit)")

    parser.add_argument(
        "--source", type=str, default=None, help="Filter by source (e.g., agenzia_entrate, inps, gazzetta_ufficiale)"
    )

    parser.add_argument("--feed-id", type=int, default=None, help="Process specific feed by ID")

    parser.add_argument("--list", action="store_true", help="List all configured feeds and exit")

    args = parser.parse_args()

    # Determine max_items (per feed)
    max_items = None if args.all else args.limit

    # Create async database session
    # Convert sync URL to async URL (postgresql:// -> postgresql+asyncpg://)
    postgres_url = settings.POSTGRES_URL
    if postgres_url.startswith("postgresql://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)

    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session_maker() as session:
            # Query feed_status table
            query = select(FeedStatus).where(FeedStatus.enabled is True)  # type: ignore[arg-type]

            # Apply filters
            if args.feed_id:
                query = query.where(FeedStatus.id == args.feed_id)
            if args.source:
                query = query.where(FeedStatus.source == args.source)

            result = await session.execute(query)
            feeds = result.scalars().all()

            if not feeds:
                print("❌ No feeds found matching criteria")
                sys.exit(1)

            # Handle --list flag
            if args.list:
                print("=" * 80)
                print("Configured RSS Feeds")
                print("=" * 80)
                for feed in feeds:
                    print(f"\n[{feed.id}] {feed.source or 'Unknown Source'}")
                    print(f"    Type: {feed.feed_type or 'N/A'}")
                    print(f"    URL: {feed.feed_url}")
                    print(f"    Status: {feed.status}")
                    print(f"    Last Success: {feed.last_success or 'Never'}")
                    print(f"    Items Found: {feed.items_found or 'N/A'}")
                print("\n" + "=" * 80)
                sys.exit(0)

            # Run ingestion for each feed
            print("=" * 80)
            print("RSS Feed Ingestion - Database-Driven CLI")
            print("=" * 80)
            print(f"Feeds to process: {len(feeds)}")
            print(f"Max items per feed: {max_items if max_items else 'ALL'}")
            print("=" * 80)
            print()

            # Aggregate stats
            aggregate_stats = {
                "feeds_processed": 0,
                "feeds_succeeded": 0,
                "feeds_failed": 0,
                "total_items": 0,
                "total_new_documents": 0,
                "total_skipped": 0,
                "total_failed": 0,
            }

            for feed in feeds:
                print(f"\n📡 Processing feed: [{feed.id}] {feed.source or 'Unknown'}")
                print(f"   URL: {feed.feed_url}")
                print()

                try:
                    stats = await run_rss_ingestion(
                        session=session,
                        feed_url=feed.feed_url,
                        feed_type=feed.feed_type,  # Pass feed type for source differentiation
                        max_items=max_items,
                    )

                    aggregate_stats["feeds_processed"] += 1
                    if stats.get("status") == "success":
                        aggregate_stats["feeds_succeeded"] += 1
                    else:
                        aggregate_stats["feeds_failed"] += 1

                    aggregate_stats["total_items"] += stats.get("total_items", 0)
                    aggregate_stats["total_new_documents"] += stats.get("new_documents", 0)
                    aggregate_stats["total_skipped"] += stats.get("skipped_existing", 0)
                    aggregate_stats["total_failed"] += stats.get("failed", 0)

                    # Update feed_status
                    feed.items_found = stats.get("total_items", 0)
                    feed.last_success = datetime.now(UTC)
                    feed.consecutive_errors = 0
                    feed.status = "healthy"
                    # DEV-247: Track filtered items for daily report
                    feed.items_filtered = stats.get("skipped_filtered", 0)
                    filtered_samples = stats.get("filtered_samples", [])
                    if filtered_samples:
                        feed.filtered_samples = {"titles": filtered_samples}
                    session.add(feed)
                    await session.commit()

                except Exception as e:
                    print(f"❌ Feed failed: {e}")
                    aggregate_stats["feeds_failed"] += 1

                    # Update feed_status with error
                    feed.consecutive_errors += 1
                    feed.errors += 1
                    feed.last_error = str(e)[:500]
                    feed.status = "error"
                    session.add(feed)
                    await session.commit()

            # Print aggregate results
            print()
            print("=" * 80)
            print("Ingestion Complete - Aggregate Results")
            print("=" * 80)
            print(f"Feeds Processed: {aggregate_stats['feeds_processed']}")
            print(f"  ✅ Succeeded: {aggregate_stats['feeds_succeeded']}")
            print(f"  ❌ Failed: {aggregate_stats['feeds_failed']}")
            print()
            print(f"Total Items: {aggregate_stats['total_items']}")
            print(f"New Documents: {aggregate_stats['total_new_documents']}")
            print(f"Skipped (Existing): {aggregate_stats['total_skipped']}")
            print(f"Failed Downloads: {aggregate_stats['total_failed']}")
            print("=" * 80)

            # Exit code based on overall success
            if aggregate_stats["feeds_failed"] == 0:
                sys.exit(0)
            elif aggregate_stats["feeds_succeeded"] > 0:
                sys.exit(2)  # Partial success
            else:
                sys.exit(1)  # Complete failure

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)

    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
