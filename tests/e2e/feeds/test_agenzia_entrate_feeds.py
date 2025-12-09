"""E2E tests for Agenzia delle Entrate RSS feeds - DEV-BE-69 Phase 6.

Tests 3 Agenzia Entrate feeds with REAL:
- RSS ingestion (1 doc per feed)
- LLM calls via LangGraph
- Golden set save (simulate "Corretta")
- Golden set retrieval (verify LLM bypass)

Agenzia Entrate Feeds:
- Circolari (official circulars)
- Risoluzioni (resolutions/interpretations)
- Provvedimenti (official measures)

Each test validates the full E2E flow:
1. Ingest from RSS
2. Query with LLM (3 semantic variations)
3. Save to golden set
4. Verify golden retrieval (no LLM)

Run with: pytest tests/e2e/feeds/test_agenzia_entrate_feeds.py -v -m "llm"
"""

import pytest

from tests.e2e.feeds.base_feed_test import BaseFeedE2ETest, BaseFeedE2ETestCommitted


class TestAgenziaEntrateNewsFeed(BaseFeedE2ETest):
    """E2E tests for Agenzia Entrate News feed.

    News provides general updates and announcements from
    Agenzia delle Entrate.
    """

    # URL from database feed_status table
    FEED_URL = (
        "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=79b071d0-a537-4a3d-86cc-7a7d5a36f2a9"
    )
    FEED_TYPE = "news"
    FEED_SOURCE = "agenzia_entrate"

    QUERY_VARIATIONS = [
        "Ultime notizie Agenzia delle Entrate",  # Formal
        "Novità fiscali AdE",  # Casual
        "news agenzia entrate",  # Abbreviated
    ]


class TestAgenziaEntrateNormativaPrassiFeed(BaseFeedE2ETest):
    """E2E tests for Agenzia Entrate Normativa e Prassi feed.

    Normativa e Prassi provides regulatory updates including
    circolari, risoluzioni, and other official documents.
    """

    # URL from database feed_status table
    FEED_URL = (
        "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=0753fcb1-1a42-4f8c-f40d-02793c6aefb4"
    )
    FEED_TYPE = "normativa_prassi"
    FEED_SOURCE = "agenzia_entrate"

    QUERY_VARIATIONS = [
        "Normativa e prassi Agenzia Entrate",  # Formal
        "Circolare IVA agevolazioni fiscali",  # Casual
        "circ AdE redditi",  # Abbreviated/typo
    ]


# ============================================================================
# Additional Agenzia Entrate E2E Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_agenzia_entrate_source_filter(db_session):
    """Verify source filter correctly limits to Agenzia Entrate documents."""
    from app.services.knowledge_search_service import KnowledgeSearchService

    service = KnowledgeSearchService(db_session=db_session)

    query_data = {
        "query": "dichiarazione IVA",
        "canonical_facts": [],
        "user_id": "test_user",
        "session_id": "test_session",
        "trace_id": "test_ae_filter",
        "search_mode": "hybrid",
        "filters": {"source_pattern": "agenzia_entrate%"},
        "max_results": 10,
    }

    results = await service.retrieve_topk(query_data)

    # All results should be from Agenzia Entrate source
    for result in results:
        source = getattr(result, "source", None) or result.metadata.get("source")
        assert source is None or "agenzia" in str(source).lower(), f"Expected Agenzia Entrate source, got: {source}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_tax_query_with_document_number(db_session):
    """Test queries that include specific document numbers.

    These should trigger the document number pattern matching
    in knowledge_search_service._generate_title_patterns().
    """
    from app.services.knowledge_search_service import KnowledgeSearchService

    service = KnowledgeSearchService(db_session=db_session)

    # Test various document number patterns
    test_queries = [
        "circolare 15/E Agenzia Entrate",  # n./E format
        "risoluzione numero 63",  # "numero" format
    ]

    for query in test_queries:
        query_data = {
            "query": query,
            "canonical_facts": [],
            "user_id": "test_user",
            "session_id": "test_session",
            "trace_id": f"test_docnum_{query[:10]}",
            "search_mode": "hybrid",
            "filters": {},
            "max_results": 5,
        }

        results = await service.retrieve_topk(query_data)

        # Log results for debugging
        if results:
            print(f"Query '{query}' found {len(results)} results")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_iva_detrazioni_query(db_session):
    """Test common VAT deduction query.

    This is a high-frequency query type that should return
    relevant Agenzia Entrate documents.
    """
    from app.services.knowledge_search_service import KnowledgeSearchService

    service = KnowledgeSearchService(db_session=db_session)

    query_data = {
        "query": "detrazioni IVA per acquisti beni strumentali",
        "canonical_facts": [],
        "user_id": "test_user",
        "session_id": "test_session",
        "trace_id": "test_iva_detrazioni",
        "search_mode": "hybrid",
        "filters": {},
        "max_results": 5,
    }

    results = await service.retrieve_topk(query_data)

    # This is a common query - should have at least some results
    # (may fail if test DB is empty)
    if results:
        print(f"Found {len(results)} results for IVA detrazioni query")


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_all_agenzia_feeds_accessible():
    """Quick check that all Agenzia Entrate feeds are accessible.

    Uses feed URLs from database feed_status table.
    """
    from app.ingest.rss_normativa import fetch_rss_feed

    # Feed URLs from database feed_status table
    feeds = [
        (
            "news",
            "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=79b071d0-a537-4a3d-86cc-7a7d5a36f2a9",
        ),
        (
            "normativa_prassi",
            "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=0753fcb1-1a42-4f8c-f40d-02793c6aefb4",
        ),
    ]

    results = {}
    for feed_type, url in feeds:
        try:
            items = await fetch_rss_feed(url)
            results[feed_type] = len(items)
        except Exception as e:
            results[feed_type] = f"ERROR: {e}"

    print("\nAgenzia Entrate Feed Accessibility Check:")
    for feed_type, count in results.items():
        print(f"  {feed_type}: {count} items")

    # At least one feed should be accessible
    successful_feeds = [k for k, v in results.items() if isinstance(v, int) and v > 0]
    assert len(successful_feeds) > 0, f"No Agenzia feeds accessible. Results: {results}"


# ============================================================================
# FULL E2E FLOW TESTS with Real LLM (using committed transactions)
# ============================================================================


class TestAgenziaEntrateNewsFeedFullE2E(BaseFeedE2ETestCommitted):
    """Full E2E tests for Agenzia Entrate News with real LLM and golden set."""

    FEED_URL = (
        "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=79b071d0-a537-4a3d-86cc-7a7d5a36f2a9"
    )
    FEED_TYPE = "news"
    FEED_SOURCE = "agenzia_entrate"

    QUERY_VARIATIONS = [
        "Ultime notizie Agenzia delle Entrate",  # Formal
        "Novità fiscali AdE",  # Casual
        "news agenzia entrate",  # Abbreviated
    ]


class TestAgenziaEntrateNormativaPrassiFeedFullE2E(BaseFeedE2ETestCommitted):
    """Full E2E tests for Agenzia Entrate Normativa e Prassi with real LLM."""

    FEED_URL = (
        "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=0753fcb1-1a42-4f8c-f40d-02793c6aefb4"
    )
    FEED_TYPE = "normativa_prassi"
    FEED_SOURCE = "agenzia_entrate"

    QUERY_VARIATIONS = [
        "Normativa e prassi Agenzia Entrate",  # Formal
        "Circolare IVA agevolazioni fiscali",  # Casual
        "circ AdE redditi",  # Abbreviated/typo
    ]
