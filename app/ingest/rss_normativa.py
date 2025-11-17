"""RSS Normativa Ingestion for Agenzia Entrate.

Fetches documents from the Normativa/Prassi RSS feed, processes them,
chunks them, generates embeddings, and stores in knowledge_items + knowledge_chunks.
"""

import time
from datetime import (
    UTC,
    datetime,
    timezone,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import feedparser
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.document_ingestion import (
    check_document_exists,
    download_and_extract_document,
    ingest_document_with_chunks,
)

# Target RSS feed
FEED_URL = "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=0753fcb1-1a42-4f8c-f40d-02793c6aefb4"


async def fetch_rss_feed(feed_url: str = FEED_URL) -> list[dict[str, Any]]:
    """Fetch and parse RSS feed.

    Args:
        feed_url: RSS feed URL

    Returns:
        List of feed items with title, link, published, summary
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(feed_url)
            response.raise_for_status()

        feed = feedparser.parse(response.text)

        items = []
        for entry in feed.entries:
            items.append(
                {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "published_parsed": entry.get("published_parsed"),  # Structured time tuple
                    "summary": entry.get("summary", ""),
                }
            )

        return items

    except Exception as e:
        print(f"Error fetching RSS feed: {e}")
        return []


# Note: Functions moved to app/core/document_ingestion.py for reuse
# - download_and_extract_document() - Download and extract PDF/HTML
# - ingest_document_with_chunks() - Complete ingestion with chunking
# - check_document_exists() - Deduplication helper


async def run_rss_ingestion(
    session: AsyncSession,
    feed_url: str | None = None,
    feed_type: str | None = None,
    max_items: int | None = None,
) -> dict[str, Any]:
    """Run the RSS ingestion pipeline.

    Args:
        session: Database session
        feed_url: RSS feed URL (defaults to FEED_URL)
        feed_type: Feed type from feed_status table (e.g., 'news', 'normativa_prassi')
        max_items: Maximum items to process (None = all)

    Returns:
        Summary statistics
    """
    start_time = time.time()

    # Use provided feed_url or default
    url = feed_url or FEED_URL

    # Determine source identifier based on feed_type
    if feed_type == "news":
        source_identifier = "agenzia_entrate_news"
    elif feed_type == "normativa_prassi":
        source_identifier = "agenzia_entrate_normativa"
    else:
        # Fallback for unspecified feed types
        source_identifier = "agenzia_entrate_generic"

    print(f"📥 Fetching RSS feed: {url}")
    feed_items = await fetch_rss_feed(url)

    if not feed_items:
        return {"status": "failed", "error": "No items found in feed"}

    print(f"Found {len(feed_items)} items in feed")

    # Limit if requested
    if max_items:
        feed_items = feed_items[:max_items]

    stats = {
        "total_items": len(feed_items),
        "new_documents": 0,
        "skipped_existing": 0,
        "failed": 0,
        "processing_time": 0,
    }

    for item in feed_items:
        url = item["link"]
        title = item["title"]

        # Check if already exists
        if await check_document_exists(session, url):
            print(f"⏭️  Skipping existing: {title}")
            stats["skipped_existing"] += 1
            continue

        # Download and extract content
        extraction_result = await download_and_extract_document(url)
        if not extraction_result:
            print(f"❌ Failed to download: {title}")
            stats["failed"] += 1
            continue

        # Parse RSS publication date (more reliable than content extraction)
        published_date = None
        if item.get("published_parsed"):
            try:
                import time as time_module

                timestamp = time_module.mktime(item["published_parsed"])
                published_date = datetime.fromtimestamp(timestamp, tz=UTC)
            except Exception as e:
                print(f"⚠️  Failed to parse pubDate for {title}: {e}")

        # Ingest with chunking and embeddings
        result = await ingest_document_with_chunks(
            session=session,
            title=title,
            url=url,
            content=extraction_result["content"],
            extraction_method=extraction_result["extraction_method"],
            text_quality=extraction_result["text_quality"],
            ocr_pages=extraction_result["ocr_pages"],
            published_date=published_date,  # Use RSS pubDate
            source=source_identifier,  # Use feed_type-based source
            category="regulatory_documents",
            subcategory="agenzia_entrate",
        )

        if result:
            stats["new_documents"] += 1
        else:
            stats["failed"] += 1

    stats["processing_time"] = time.time() - start_time
    stats["status"] = "success"

    return stats
