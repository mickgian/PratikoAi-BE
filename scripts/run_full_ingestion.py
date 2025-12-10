#!/usr/bin/env python3
"""
CLI Script for Full Knowledge Base Ingestion.

Runs RSS feed ingestion, Gazzetta Ufficiale scraping, and Cassazione court
decision scraping to populate the knowledge base with Italian regulatory documents.

Usage:
    # RSS feeds only (13 configured feeds)
    python scripts/run_full_ingestion.py --source rss

    # Gazzetta Ufficiale only (last 7 days)
    python scripts/run_full_ingestion.py --source gazzetta --days 7

    # Cassazione court decisions (last 30 days)
    python scripts/run_full_ingestion.py --source cassazione --days 30

    # Scrapers only (Gazzetta + Cassazione)
    python scripts/run_full_ingestion.py --source scrapers --days 7 --limit 50

    # Full ingestion: RSS + Gazzetta + Cassazione
    python scripts/run_full_ingestion.py --source all --days 7

    # Dry run (scrape but don't save to DB)
    python scripts/run_full_ingestion.py --source all --days 1 --dry-run
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.ingest.rss_normativa import run_rss_ingestion  # noqa: E402
from app.models.cassazione_data import CourtSection  # noqa: E402
from app.models.regulatory_documents import FeedStatus  # noqa: E402
from app.services.scrapers.cassazione_scraper import CassazioneScraper  # noqa: E402
from app.services.scrapers.gazzetta_scraper import GazzettaScraper  # noqa: E402


async def run_rss_ingestion_all(session: AsyncSession, max_items: int | None = None) -> dict:
    """Run RSS ingestion for all enabled feeds.

    Args:
        session: Database session
        max_items: Maximum items per feed (None for all)

    Returns:
        Aggregate statistics dictionary
    """
    print("\n" + "=" * 80)
    print("RSS FEED INGESTION")
    print("=" * 80)

    # Query all enabled feeds
    query = select(FeedStatus).where(FeedStatus.enabled == True)  # noqa: E712
    result = await session.execute(query)
    feeds = result.scalars().all()

    if not feeds:
        print("❌ No RSS feeds found in feed_status table")
        return {"feeds_processed": 0, "success": False}

    print(f"Found {len(feeds)} enabled feeds")
    print(f"Max items per feed: {max_items if max_items else 'ALL'}")
    print()

    stats = {
        "feeds_processed": 0,
        "feeds_succeeded": 0,
        "feeds_failed": 0,
        "total_items": 0,
        "total_new_documents": 0,
        "total_skipped": 0,
        "total_failed": 0,
    }

    for feed in feeds:
        print(f"📡 Processing feed: [{feed.id}] {feed.source or 'Unknown'}")

        try:
            feed_stats = await run_rss_ingestion(
                session=session,
                feed_url=feed.feed_url,
                feed_type=feed.feed_type,
                max_items=max_items,
            )

            stats["feeds_processed"] += 1
            if feed_stats.get("status") == "success":
                stats["feeds_succeeded"] += 1
            else:
                stats["feeds_failed"] += 1

            stats["total_items"] += feed_stats.get("total_items", 0)
            stats["total_new_documents"] += feed_stats.get("new_documents", 0)
            stats["total_skipped"] += feed_stats.get("skipped_existing", 0)
            stats["total_failed"] += feed_stats.get("failed", 0)

            # Update feed_status
            feed.items_found = feed_stats.get("total_items", 0)
            feed.last_success = datetime.now(UTC)
            feed.consecutive_errors = 0
            feed.status = "healthy"
            session.add(feed)
            await session.commit()

            print(f"   ✅ New: {feed_stats.get('new_documents', 0)}, Skipped: {feed_stats.get('skipped_existing', 0)}")

        except Exception as e:
            print(f"   ❌ Failed: {e}")
            stats["feeds_failed"] += 1

            feed.consecutive_errors += 1
            feed.errors += 1
            feed.last_error = str(e)[:500]
            feed.status = "error"
            session.add(feed)
            await session.commit()

    print()
    print(
        f"RSS Summary: {stats['feeds_succeeded']}/{stats['feeds_processed']} feeds succeeded, "
        f"{stats['total_new_documents']} new documents"
    )

    stats["success"] = stats["feeds_failed"] == 0
    return stats


async def run_gazzetta_scraping(
    session: AsyncSession | None,
    days_back: int,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Run Gazzetta Ufficiale scraping.

    Args:
        session: Database session (None for dry run)
        days_back: Number of days to look back
        limit: Maximum documents to scrape
        dry_run: If True, scrape but don't save to DB

    Returns:
        Scraping statistics dictionary
    """
    print("\n" + "=" * 80)
    print("GAZZETTA UFFICIALE SCRAPING")
    print("=" * 80)
    print(f"Days back: {days_back}")
    print(f"Limit: {limit if limit else 'No limit'}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE (saving to DB)'}")
    print()

    db_session = None if dry_run else session

    try:
        async with GazzettaScraper(db_session=db_session) as scraper:
            result = await scraper.scrape_recent_documents(
                days_back=days_back,
                filter_tax=True,
                filter_labor=True,
                limit=limit,
            )

            print("✅ Gazzetta scraping completed:")
            print(f"   Documents found: {result.documents_found}")
            print(f"   Documents processed: {result.documents_processed}")
            print(f"   Documents saved: {result.documents_saved}")
            print(f"   Errors: {result.errors}")
            print(f"   Duration: {result.duration_seconds}s")

            return {
                "success": result.errors == 0,
                "documents_found": result.documents_found,
                "documents_processed": result.documents_processed,
                "documents_saved": result.documents_saved,
                "errors": result.errors,
                "duration_seconds": result.duration_seconds,
            }

    except Exception as e:
        print(f"❌ Gazzetta scraping failed: {e}")
        return {"success": False, "error": str(e)}


async def run_cassazione_scraping(
    session: AsyncSession | None,
    days_back: int,
    sections: list[str] | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Run Cassazione court decision scraping.

    Args:
        session: Database session (None for dry run)
        days_back: Number of days to look back
        sections: Court sections to scrape
        limit: Maximum decisions to scrape
        dry_run: If True, scrape but don't save to DB

    Returns:
        Scraping statistics dictionary
    """
    print("\n" + "=" * 80)
    print("CASSAZIONE COURT DECISION SCRAPING")
    print("=" * 80)
    print(f"Days back: {days_back}")
    print(f"Sections: {sections if sections else ['tributaria', 'lavoro']}")
    print(f"Limit: {limit if limit else 'No limit'}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE (saving to DB)'}")
    print()

    # Convert section strings to CourtSection enum
    if sections is None:
        sections = ["tributaria", "lavoro"]

    section_map = {
        "tributaria": CourtSection.TRIBUTARIA,
        "lavoro": CourtSection.LAVORO,
        "civile": CourtSection.CIVILE,
        "penale": CourtSection.PENALE,
        "sezioni_unite": CourtSection.SEZIONI_UNITE,
    }
    court_sections = [section_map.get(s.lower(), CourtSection.CIVILE) for s in sections]

    db_session = None if dry_run else session

    try:
        async with CassazioneScraper(db_session=db_session) as scraper:
            result = await scraper.scrape_recent_decisions(
                sections=court_sections,
                days_back=days_back,
                limit=limit,
            )

            print("✅ Cassazione scraping completed:")
            print(f"   Decisions found: {result.decisions_found}")
            print(f"   Decisions processed: {result.decisions_processed}")
            print(f"   Decisions saved: {result.decisions_saved}")
            print(f"   Errors: {result.errors}")
            print(f"   Duration: {result.duration_seconds}s")

            return {
                "success": result.errors == 0,
                "documents_found": result.decisions_found,
                "documents_processed": result.decisions_processed,
                "documents_saved": result.decisions_saved,
                "errors": result.errors,
                "duration_seconds": result.duration_seconds,
            }

    except Exception as e:
        print(f"❌ Cassazione scraping failed: {e}")
        return {"success": False, "error": str(e)}


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Full knowledge base ingestion from RSS feeds and web scrapers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # RSS feeds only
  python scripts/run_full_ingestion.py --source rss

  # Gazzetta Ufficiale only (last 7 days)
  python scripts/run_full_ingestion.py --source gazzetta --days 7

  # Cassazione court decisions (last 30 days)
  python scripts/run_full_ingestion.py --source cassazione --days 30

  # All scrapers (Gazzetta + Cassazione)
  python scripts/run_full_ingestion.py --source scrapers --days 7

  # Full ingestion: RSS + all scrapers
  python scripts/run_full_ingestion.py --source all --days 7

  # Test with limit first
  python scripts/run_full_ingestion.py --source scrapers --days 7 --limit 10

  # Dry run (scrape but don't save)
  python scripts/run_full_ingestion.py --source all --days 1 --dry-run
        """,
    )

    parser.add_argument(
        "--source",
        type=str,
        choices=["rss", "gazzetta", "cassazione", "scrapers", "all"],
        required=True,
        help="Source to ingest from",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back for scrapers (default: 7)",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum documents/decisions to process (default: no limit)",
    )

    parser.add_argument(
        "--rss-limit",
        type=int,
        default=None,
        help="Maximum items per RSS feed (default: no limit)",
    )

    parser.add_argument(
        "--sections",
        type=str,
        default="tributaria,lavoro",
        help="Cassazione sections to scrape (comma-separated, default: tributaria,lavoro)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape but don't save to database",
    )

    args = parser.parse_args()

    # Parse sections
    sections = [s.strip() for s in args.sections.split(",")]

    # Create async database session
    postgres_url = settings.POSTGRES_URL
    if postgres_url.startswith("postgresql://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print()
    print("=" * 80)
    print("PRATIKOAI FULL KNOWLEDGE BASE INGESTION")
    print("=" * 80)
    print(f"Source: {args.source}")
    print(f"Days back: {args.days}")
    print(f"Limit: {args.limit if args.limit else 'No limit'}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Started: {datetime.now(UTC).isoformat()}")
    print("=" * 80)

    results = {}

    try:
        async with async_session_maker() as session:
            # RSS ingestion
            if args.source in ["rss", "all"]:
                results["rss"] = await run_rss_ingestion_all(
                    session=session,
                    max_items=args.rss_limit,
                )

            # Gazzetta scraping
            if args.source in ["gazzetta", "scrapers", "all"]:
                results["gazzetta"] = await run_gazzetta_scraping(
                    session=session,
                    days_back=args.days,
                    limit=args.limit,
                    dry_run=args.dry_run,
                )

            # Cassazione scraping
            if args.source in ["cassazione", "scrapers", "all"]:
                results["cassazione"] = await run_cassazione_scraping(
                    session=session,
                    days_back=args.days,
                    sections=sections,
                    limit=args.limit,
                    dry_run=args.dry_run,
                )

        # Print summary
        print()
        print("=" * 80)
        print("INGESTION SUMMARY")
        print("=" * 80)

        total_documents = 0
        total_saved = 0
        total_errors = 0
        all_success = True

        for source, stats in results.items():
            success = stats.get("success", False)
            all_success = all_success and success

            if source == "rss":
                print("\n📰 RSS Feeds:")
                print(f"   Feeds processed: {stats.get('feeds_processed', 0)}")
                print(f"   New documents: {stats.get('total_new_documents', 0)}")
                print(f"   Status: {'✅ Success' if success else '❌ Failed'}")
                total_documents += stats.get("total_items", 0)
                total_saved += stats.get("total_new_documents", 0)
            else:
                emoji = "📜" if source == "gazzetta" else "⚖️"
                print(f"\n{emoji} {source.title()}:")
                print(f"   Documents found: {stats.get('documents_found', 0)}")
                print(f"   Documents saved: {stats.get('documents_saved', 0)}")
                print(f"   Errors: {stats.get('errors', 0)}")
                print(f"   Status: {'✅ Success' if success else '❌ Failed'}")
                total_documents += stats.get("documents_found", 0)
                total_saved += stats.get("documents_saved", 0)
                total_errors += stats.get("errors", 0)

        print()
        print("=" * 80)
        print(f"Total documents processed: {total_documents}")
        print(f"Total documents saved: {total_saved}")
        print(f"Total errors: {total_errors}")
        print(
            f"Overall status: {'✅ SUCCESS' if all_success else '⚠️  PARTIAL SUCCESS' if total_saved > 0 else '❌ FAILED'}"
        )
        print(f"Completed: {datetime.now(UTC).isoformat()}")
        print("=" * 80)

        # Exit code
        if all_success:
            sys.exit(0)
        elif total_saved > 0:
            sys.exit(2)  # Partial success
        else:
            sys.exit(1)

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
