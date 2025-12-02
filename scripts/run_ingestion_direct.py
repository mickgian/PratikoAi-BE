#!/usr/bin/env python3
"""Direct RSS ingestion script to restore knowledge base."""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.ingest.rss_normativa import run_rss_ingestion


async def main():
    """Run RSS ingestion for the 2 active feeds."""
    # RSS feeds to process (from scripts/backfill_rss_dates.py)
    feeds = [
        {
            "url": "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=0753fcb1-1a42-4f8c-f40d-02793c6aefb4",
            "name": "Normativa/Prassi",
            "type": "normativa_prassi",
        },
        {
            "url": "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=79b071d0-a537-4a3d-86cc-7a7d5a36f2a9",
            "name": "News",
            "type": "news",
        },
    ]

    # Convert sync URL to async URL
    postgres_url = settings.POSTGRES_URL
    if postgres_url.startswith("postgresql://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session_maker() as session:
            print("=" * 80)
            print("RSS Knowledge Base Restoration")
            print("=" * 80)
            print(f"Feeds to process: {len(feeds)}")
            print("=" * 80)
            print()

            total_new = 0
            total_items = 0

            for feed in feeds:
                print(f"\n📡 Processing: {feed['name']}")
                print(f"   URL: {feed['url']}")
                print()

                try:
                    stats = await run_rss_ingestion(
                        session=session,
                        feed_url=feed["url"],
                        feed_type=feed["type"],
                        max_items=None,  # Process ALL items
                    )

                    print(f"✅ {feed['name']} completed:")
                    print(f"   Total items: {stats.get('total_items', 0)}")
                    print(f"   New documents: {stats.get('new_documents', 0)}")
                    print(f"   Skipped (existing): {stats.get('skipped_existing', 0)}")
                    print(f"   Failed: {stats.get('failed', 0)}")

                    total_new += stats.get("new_documents", 0)
                    total_items += stats.get("total_items", 0)

                except Exception as e:
                    print(f"❌ Failed: {e}")
                    import traceback

                    traceback.print_exc()

            print()
            print("=" * 80)
            print("Ingestion Complete")
            print("=" * 80)
            print(f"Total items processed: {total_items}")
            print(f"Total new documents: {total_new}")
            print("=" * 80)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
