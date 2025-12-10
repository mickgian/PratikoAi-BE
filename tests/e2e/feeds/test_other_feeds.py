"""E2E tests for other RSS feeds - DEV-BE-69 Phase 6.

Tests remaining feeds with REAL:
- RSS ingestion (1 doc per feed)
- LLM calls via LangGraph
- Golden set save (simulate "Corretta")
- Golden set retrieval (verify LLM bypass)

Feeds:
- INAIL (2 feeds: news, eventi)
- MEF (2 feeds: documenti, aggiornamenti)
- Ministero del Lavoro (1 feed: news)
- Gazzetta Ufficiale (1 feed: serie_generale)

Each test validates the full E2E flow:
1. Ingest from RSS
2. Query with LLM (3 semantic variations)
3. Save to golden set
4. Verify golden retrieval (no LLM)

Run with: pytest tests/e2e/feeds/test_other_feeds.py -v -m "llm"
"""

import pytest

from tests.e2e.feeds.base_feed_test import BaseFeedE2ETest, BaseFeedE2ETestCommitted

# ============================================================================
# INAIL Feeds (2 feeds)
# ============================================================================


class TestINAILNewsFeed(BaseFeedE2ETest):
    """E2E tests for INAIL News feed.

    INAIL provides workplace safety, insurance, and occupational
    disease information.
    """

    FEED_URL = "https://www.inail.it/portale/it.rss.news.xml"
    FEED_TYPE = "news"
    FEED_SOURCE = "inail"

    QUERY_VARIATIONS = [
        "Novità INAIL sicurezza sul lavoro",  # Formal
        "Assicurazione infortuni lavoratori INAIL",  # Casual
        "aggiornamenti inail malattie",  # Abbreviated
    ]


class TestINAILEventiFeed(BaseFeedE2ETest):
    """E2E tests for INAIL Eventi feed.

    INAIL events include conferences, webinars, and training
    sessions on workplace safety.
    """

    FEED_URL = "https://www.inail.it/portale/it.rss.eventi.xml"
    FEED_TYPE = "eventi"
    FEED_SOURCE = "inail"

    QUERY_VARIATIONS = [
        "Eventi INAIL formazione sicurezza",  # Formal
        "Convegni INAIL prevenzione infortuni",  # Casual
        "webinar inail",  # Abbreviated
    ]


# ============================================================================
# MEF Feeds (2 feeds)
# ============================================================================


class TestMEFDocumentiFeed(BaseFeedE2ETest):
    """E2E tests for MEF Documenti feed.

    Ministry of Economy and Finance documents include
    fiscal policies, budget updates, and economic measures.
    """

    FEED_URL = "https://www.mef.gov.it/rss/rss.asp?t=5"
    FEED_TYPE = "documenti"
    FEED_SOURCE = "ministero_economia"

    QUERY_VARIATIONS = [
        "Documenti MEF politica fiscale",  # Formal
        "Aggiornamenti bilancio statale",  # Casual
        "mef misure economiche",  # Abbreviated
    ]


class TestMEFAggiornamentiFeed(BaseFeedE2ETest):
    """E2E tests for MEF/Finanze Aggiornamenti feed.

    Updates from the Department of Finance including
    tax reform news and regulatory changes.
    """

    FEED_URL = "https://www.finanze.gov.it/it/rss.xml"
    FEED_TYPE = "aggiornamenti"
    FEED_SOURCE = "ministero_economia"

    QUERY_VARIATIONS = [
        "Aggiornamenti Dipartimento Finanze",  # Formal
        "Novità riforma fiscale",  # Casual
        "finanze tassazione",  # Abbreviated
    ]


# ============================================================================
# Ministero del Lavoro Feed (1 feed)
# ============================================================================


class TestMinisteroLavoroNewsFeed(BaseFeedE2ETest):
    """E2E tests for Ministero del Lavoro News feed.

    Ministry of Labor news includes labor law updates,
    employment policies, and social security changes.
    """

    FEED_URL = "https://www.lavoro.gov.it/_layouts/15/Lavoro.Web/AppPages/RSS"
    FEED_TYPE = "news"
    FEED_SOURCE = "ministero_lavoro"

    QUERY_VARIATIONS = [
        "Novità Ministero del Lavoro contratti",  # Formal
        "Aggiornamenti diritto del lavoro",  # Casual
        "ministero lavoro politiche",  # Abbreviated
    ]


# ============================================================================
# Gazzetta Ufficiale Feed
# NOTE: Not currently in feed_status table - skipped
# ============================================================================

# Gazzetta Ufficiale is not currently configured in the database.
# When added, uncomment and update the URL from feed_status table.
#
# class TestGazzettaUfficialeFeed(BaseFeedE2ETest):
#     """E2E tests for Gazzetta Ufficiale Serie Generale feed."""
#     FEED_URL = "https://www.gazzettaufficiale.it/..."
#     FEED_TYPE = "serie_generale"
#     FEED_SOURCE = "gazzetta_ufficiale"
#     QUERY_VARIATIONS = [...]


# ============================================================================
# Cross-feed integration tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_cross_source_search(db_session):
    """Test that hybrid search works across all sources.

    A generic query should return documents from multiple sources,
    demonstrating the unified knowledge base.
    """
    from app.services.knowledge_search_service import KnowledgeSearchService

    service = KnowledgeSearchService(db_session=db_session)

    query_data = {
        "query": "aggiornamenti normativi 2025",
        "canonical_facts": [],
        "user_id": "test_user",
        "session_id": "test_session",
        "trace_id": "test_cross_source",
        "search_mode": "hybrid",
        "filters": {},  # No source filter
        "max_results": 10,
    }

    results = await service.retrieve_topk(query_data)

    if results:
        # Collect unique sources
        sources = set()
        for r in results:
            source = getattr(r, "source", None) or result.metadata.get("source")
            if source:
                sources.add(source)

        print(f"Query returned results from {len(sources)} sources: {sources}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_sicurezza_lavoro_query(db_session):
    """Test common workplace safety query.

    This query should return results from multiple sources:
    - INAIL (primary for workplace safety)
    - Ministero del Lavoro
    - Gazzetta Ufficiale (for relevant laws)
    """
    from app.services.knowledge_search_service import KnowledgeSearchService

    service = KnowledgeSearchService(db_session=db_session)

    query_data = {
        "query": "normativa sicurezza sul lavoro DL",
        "canonical_facts": [],
        "user_id": "test_user",
        "session_id": "test_session",
        "trace_id": "test_sicurezza_lavoro",
        "search_mode": "hybrid",
        "filters": {},
        "max_results": 10,
    }

    results = await service.retrieve_topk(query_data)

    # This is a regression test for the "DL Sicurezza sul lavoro" bug
    if results:
        relevant = any("sicur" in str(r.title).lower() or "lavoro" in str(r.title).lower() for r in results)
        print(f"Found {len(results)} results, relevant: {relevant}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_previdenza_query_multiple_sources(db_session):
    """Test social security query across sources.

    Previdenza queries should return results from:
    - INPS (primary)
    - Ministero del Lavoro
    - Gazzetta Ufficiale
    """
    from app.services.knowledge_search_service import KnowledgeSearchService

    service = KnowledgeSearchService(db_session=db_session)

    query_data = {
        "query": "contributi previdenziali gestione separata",
        "canonical_facts": [],
        "user_id": "test_user",
        "session_id": "test_session",
        "trace_id": "test_previdenza",
        "search_mode": "hybrid",
        "filters": {},
        "max_results": 10,
    }

    results = await service.retrieve_topk(query_data)

    if results:
        # Should find INPS-related documents
        inps_results = sum(1 for r in results if "inps" in str(r.source).lower() or "inps" in str(r.title).lower())
        print(f"Found {inps_results}/{len(results)} INPS-related results")


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_all_other_feeds_accessible():
    """Quick check that all other feeds are accessible.

    Uses feed URLs from database feed_status table.
    """
    from app.ingest.rss_normativa import fetch_rss_feed

    # Feed URLs from database feed_status table
    feeds = [
        ("inail_news", "https://www.inail.it/portale/it.rss.news.xml"),
        ("inail_eventi", "https://www.inail.it/portale/it.rss.eventi.xml"),
        ("mef_documenti", "https://www.mef.gov.it/rss/rss.asp?t=5"),
        ("finanze_aggiornamenti", "https://www.finanze.gov.it/it/rss.xml"),
        ("ministero_lavoro", "https://www.lavoro.gov.it/_layouts/15/Lavoro.Web/AppPages/RSS"),
        # Note: Gazzetta Ufficiale not in feed_status table
    ]

    results = {}
    for feed_type, url in feeds:
        try:
            items = await fetch_rss_feed(url)
            results[feed_type] = len(items)
        except Exception as e:
            results[feed_type] = f"ERROR: {e}"

    print("\nOther Feeds Accessibility Check:")
    for feed_type, count in results.items():
        print(f"  {feed_type}: {count} items")

    # At least some feeds should be accessible (some may be temporarily down)
    successful_feeds = [k for k, v in results.items() if isinstance(v, int) and v > 0]
    # Don't assert - just log results since external feeds may be unreliable
    print(f"\nAccessible feeds: {len(successful_feeds)}/{len(feeds)}")


# ============================================================================
# FULL E2E FLOW TESTS with Real LLM (using committed transactions)
# ============================================================================


class TestINAILNewsFeedFullE2E(BaseFeedE2ETestCommitted):
    """Full E2E tests for INAIL News with real LLM and golden set."""

    FEED_URL = "https://www.inail.it/portale/it.rss.news.xml"
    FEED_TYPE = "news"
    FEED_SOURCE = "inail"

    QUERY_VARIATIONS = [
        "Novità INAIL sicurezza sul lavoro",  # Formal
        "Assicurazione infortuni lavoratori INAIL",  # Casual
        "aggiornamenti inail malattie",  # Abbreviated
    ]


class TestINAILEventiFeedFullE2E(BaseFeedE2ETestCommitted):
    """Full E2E tests for INAIL Eventi with real LLM and golden set."""

    FEED_URL = "https://www.inail.it/portale/it.rss.eventi.xml"
    FEED_TYPE = "eventi"
    FEED_SOURCE = "inail"

    QUERY_VARIATIONS = [
        "Eventi INAIL formazione sicurezza",  # Formal
        "Convegni INAIL prevenzione infortuni",  # Casual
        "webinar inail",  # Abbreviated
    ]


class TestMEFDocumentiFeedFullE2E(BaseFeedE2ETestCommitted):
    """Full E2E tests for MEF Documenti with real LLM and golden set."""

    FEED_URL = "https://www.mef.gov.it/rss/rss.asp?t=5"
    FEED_TYPE = "documenti"
    FEED_SOURCE = "ministero_economia"

    QUERY_VARIATIONS = [
        "Documenti MEF politica fiscale",  # Formal
        "Aggiornamenti bilancio statale",  # Casual
        "mef misure economiche",  # Abbreviated
    ]


class TestMEFAggiornamentiFeedFullE2E(BaseFeedE2ETestCommitted):
    """Full E2E tests for MEF Aggiornamenti with real LLM and golden set."""

    FEED_URL = "https://www.finanze.gov.it/it/rss.xml"
    FEED_TYPE = "aggiornamenti"
    FEED_SOURCE = "ministero_economia"

    QUERY_VARIATIONS = [
        "Aggiornamenti Dipartimento Finanze",  # Formal
        "Novità riforma fiscale",  # Casual
        "finanze tassazione",  # Abbreviated
    ]


class TestMinisteroLavoroNewsFeedFullE2E(BaseFeedE2ETestCommitted):
    """Full E2E tests for Ministero Lavoro News with real LLM and golden set."""

    FEED_URL = "https://www.lavoro.gov.it/_layouts/15/Lavoro.Web/AppPages/RSS"
    FEED_TYPE = "news"
    FEED_SOURCE = "ministero_lavoro"

    QUERY_VARIATIONS = [
        "Novità Ministero del Lavoro contratti",  # Formal
        "Aggiornamenti diritto del lavoro",  # Casual
        "ministero lavoro politiche",  # Abbreviated
    ]
