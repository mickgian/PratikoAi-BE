"""
Backfill publication dates from RSS feeds for existing documents.

Fetches current RSS feeds and updates publication_date for matching documents.
"""

import asyncio
import sys
import time
from datetime import (
    UTC,
    datetime,
    timezone,
)
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import feedparser
import httpx
from sqlalchemy import (
    select,
    update,
)

from app.models.database import AsyncSessionLocal
from app.models.knowledge import KnowledgeItem

# RSS feeds to process
RSS_FEEDS = [
    {
        "url": "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=0753fcb1-1a42-4f8c-f40d-02793c6aefb4",
        "name": "Normativa/Prassi",
    },
    {
        "url": "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=79b071d0-a537-4a3d-86cc-7a7d5a36f2a9",
        "name": "News",
    },
]


async def fetch_feed_dates(feed_url: str) -> dict:
    """
    Fetch RSS feed and extract publication dates by URL.

    Returns:
        dict mapping document URL -> publication_date
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(feed_url)
            response.raise_for_status()

        feed = feedparser.parse(response.text)

        url_to_date = {}
        for entry in feed.entries:
            url = entry.get("link", "")
            published_parsed = entry.get("published_parsed")

            if url and published_parsed:
                try:
                    timestamp = time.mktime(published_parsed)
                    pub_date = datetime.fromtimestamp(timestamp, tz=UTC).date()
                    url_to_date[url] = pub_date
                except Exception:
                    pass

        return url_to_date

    except Exception as e:
        print(f"❌ Error fetching feed {feed_url}: {e}")
        return {}


async def backfill_publication_dates():
    """Backfill publication_date from RSS feeds."""

    # Fetch all RSS feeds
    print("📥 Fetching RSS feeds...")
    all_dates = {}

    for feed_info in RSS_FEEDS:
        print(f"  - {feed_info['name']}: {feed_info['url']}")
        dates = await fetch_feed_dates(feed_info["url"])
        all_dates.update(dates)
        print(f"    Found {len(dates)} entries")

    print(f"\n✅ Total URLs with dates: {len(all_dates)}")

    if not all_dates:
        print("❌ No dates found in RSS feeds")
        return

    # Update database
    async with AsyncSessionLocal() as session:
        # Find documents with URLs in our RSS feeds
        result = await session.execute(
            select(KnowledgeItem).where(KnowledgeItem.source_url.in_(list(all_dates.keys())))
        )
        items = result.scalars().all()

        print(f"\n📊 Found {len(items)} documents in database matching RSS URLs")

        updated = 0
        skipped_same = 0
        skipped_missing = 0

        for item in items:
            url = item.source_url
            rss_date = all_dates.get(url)

            if not rss_date:
                skipped_missing += 1
                continue

            # Check if date is different
            if item.publication_date == rss_date:
                skipped_same += 1
                continue

            # Update
            old_date = item.publication_date
            item.publication_date = rss_date
            updated += 1

            print(f"  ✅ {item.title[:70]}...")
            print(f"     {old_date} → {rss_date}")

        # Commit changes
        await session.commit()

        print("\n✅ Backfill complete:")
        print(f"   - Updated: {updated} documents")
        print(f"   - Skipped (same date): {skipped_same} documents")
        print(f"   - Skipped (no RSS match): {skipped_missing} documents")


if __name__ == "__main__":
    asyncio.run(backfill_publication_dates())
