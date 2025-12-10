"""RSS Normativa Ingestion for Agenzia Entrate.

Fetches documents from the Normativa/Prassi RSS feed, processes them,
chunks them, generates embeddings, and stores in knowledge_items + knowledge_chunks.
"""

import ssl
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
from urllib.parse import urlparse

import feedparser
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.document_ingestion import (
    check_document_exists,
    download_and_extract_document,
    ingest_document_with_chunks,
)

# Domains that require relaxed SSL settings (older TLS ciphers)
RELAXED_SSL_DOMAINS = {"www.inail.it", "inail.it"}


def _get_ssl_context(url: str) -> ssl.SSLContext | bool:
    """Get appropriate SSL context for a URL.

    Some government sites (e.g., INAIL) use older TLS configurations
    that require relaxed cipher settings.

    Args:
        url: The URL to fetch

    Returns:
        SSLContext for relaxed domains, True for standard SSL verification
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    if hostname in RELAXED_SSL_DOMAINS:
        # Create SSL context with relaxed security level for older servers
        ssl_context = ssl.create_default_context()
        ssl_context.set_ciphers("DEFAULT:@SECLEVEL=1")
        return ssl_context

    return True  # Use default SSL verification


# Target RSS feed
FEED_URL = "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=0753fcb1-1a42-4f8c-f40d-02793c6aefb4"


def _determine_feed_source(feed_url: str) -> tuple[str, str]:
    """Determine source name and subcategory from feed URL.

    Args:
        feed_url: RSS feed URL

    Returns:
        Tuple of (source_name, subcategory)
    """
    url_lower = feed_url.lower()

    if "inps.it" in url_lower:
        return "inps", "inps"
    elif "inail.it" in url_lower:
        return "inail", "inail"
    elif "agenziaentrate" in url_lower:
        return "agenzia_entrate", "agenzia_entrate"
    elif "lavoro.gov.it" in url_lower:
        return "ministero_lavoro", "ministero_lavoro"
    elif "mef.gov.it" in url_lower or "finanze.gov.it" in url_lower:
        return "ministero_economia", "ministero_economia"
    elif "gazzettaufficiale.it" in url_lower:
        return "gazzetta_ufficiale", "gazzetta_ufficiale"
    else:
        return "generic", "other"


async def fetch_rss_feed(feed_url: str = FEED_URL) -> list[dict[str, Any]]:
    """Fetch and parse RSS feed.

    Args:
        feed_url: RSS feed URL

    Returns:
        List of feed items with title, link, published, summary, attachment_url.
        For items without a link, attachment_url is used as fallback.
    """
    try:
        # Get appropriate SSL context (relaxed for some government sites)
        ssl_context = _get_ssl_context(feed_url)
        async with httpx.AsyncClient(timeout=30.0, verify=ssl_context) as client:
            response = await client.get(feed_url)
            response.raise_for_status()

        feed = feedparser.parse(response.text)

        items = []
        for entry in feed.entries:
            # Extract attachment URL (INPS uses attachment1, attachment2, etc.)
            attachment_url = None
            for attr in ["attachment1", "attachment", "enclosure"]:
                if hasattr(entry, attr):
                    val = getattr(entry, attr)
                    if isinstance(val, str) and val.startswith("http"):
                        attachment_url = val
                        break
                    elif hasattr(val, "href"):  # Standard enclosure format
                        attachment_url = val.href
                        break

            # Use attachment URL as fallback when link is missing
            url = entry.get("link", "") or attachment_url

            items.append(
                {
                    "title": entry.get("title", ""),
                    "link": url,
                    "published": entry.get("published", ""),
                    "published_parsed": entry.get("published_parsed"),  # Structured time tuple
                    "summary": entry.get("summary", ""),
                    "attachment_url": attachment_url,  # Keep original for reference
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

    # Determine source and subcategory from feed URL
    source_name, subcategory = _determine_feed_source(url)
    source_identifier = f"{source_name}_{feed_type or 'generic'}"

    print(f"📥 Fetching RSS feed: {url}")
    feed_items = await fetch_rss_feed(url)

    if not feed_items:
        return {"status": "failed", "error": "No items found in feed"}

    print(f"Found {len(feed_items)} items in feed")

    # Limit if requested
    if max_items:
        feed_items = feed_items[:max_items]

    stats: dict[str, Any] = {
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

        # Fallback to RSS summary/description if page content is too short
        # (handles JavaScript-rendered sites like INPS that need a browser)
        content = extraction_result["content"]
        # Check both "summary" (feedparser) and "description" (rss_feed_monitor)
        rss_summary = item.get("summary", "") or item.get("description", "")
        MIN_CONTENT_LENGTH = 500  # Minimum expected for real document content

        if len(content.strip()) < MIN_CONTENT_LENGTH and len(rss_summary.strip()) > 50:
            print(f"⚠️  Page content too short ({len(content)} chars), using RSS summary")
            extraction_result["content"] = rss_summary
            extraction_result["extraction_method"] = "rss_summary_fallback"

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
            subcategory=subcategory,  # Dynamic based on feed source
        )

        if result:
            stats["new_documents"] += 1
        else:
            stats["failed"] += 1

    stats["processing_time"] = time.time() - start_time
    stats["status"] = "success"

    return stats
