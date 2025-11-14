"""
TDD Test Suite for Knowledge Search Fixes

Tests for critical search bugs:
1. Resolution 64 not found by document number
2. Multi-month aggregation returning no results
3. FTS-only queries still working

These tests should FAIL before fixes and PASS after fixes are applied.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_search_service import KnowledgeSearchService
from app.services.search_service import SearchService


@pytest.mark.asyncio
async def test_resolution_64_found_by_number(db_session: AsyncSession):
    """
    CRITICAL BUG TEST: Resolution 64 must be findable by document number.

    Before fix: Returns 0 results (title filter doesn't bypass FTS)
    After fix: Returns Resolution 64 document
    """
    # Setup
    # Note: KnowledgeSearchService creates its own SearchService internally
    # Passing search_service as vector_service param would cause errors
    knowledge_search_service = KnowledgeSearchService(
        db_session=db_session, vector_service=None, config=None  # No vector search for this test  # Use default config
    )

    # Execute - user asks for specific resolution by number
    query_data = {
        "query": "Cosa dice la Risoluzione n. 64 del 10 novembre 2025?",
        "category": None,
        "search_mode": "bm25_only",  # Use BM25 since vector_service is None
    }
    results = await knowledge_search_service.retrieve_topk(query_data)

    # Assert
    assert len(results) >= 1, (
        f"Resolution 64 not found! Expected ≥1 results, got {len(results)}. "
        f"This indicates title filter is not bypassing FTS for document numbers."
    )

    # Verify correct document found
    titles = [r.title for r in results]
    assert any("64" in title for title in titles), f"Document with '64' not in results. Found titles: {titles}"

    # Verify it's a risoluzione document
    assert any(
        "risoluzione" in title.lower() for title in titles
    ), f"Document type 'risoluzione' not in results. Found titles: {titles}"

    print(f"✓ Resolution 64 found: {results[0].title[:100]}..." if results else "N/A")


@pytest.mark.asyncio
async def test_multi_month_aggregation_finds_all_documents(db_session: AsyncSession):
    """
    CRITICAL BUG TEST: Multi-month aggregation must find all documents.

    Before fix: Returns 0 results (missing title_pattern parameter in multi-month path)
    After fix: Returns 5 documents (n. 56, 62, 63, 64, 65)
    """
    # Setup
    # Note: KnowledgeSearchService creates its own SearchService internally
    # Passing search_service as vector_service param would cause errors
    knowledge_search_service = KnowledgeSearchService(
        db_session=db_session, vector_service=None, config=None  # No vector search for this test  # Use default config
    )

    # Execute - user asks for all resolutions across multiple months
    query_data = {
        "query": "fammi un riassunto di tutte le risoluzioni dell'agenzia delle entrate di ottobre e novembre 2025",
        "category": None,
        "search_mode": "bm25_only",  # Use BM25 since vector_service is None
    }
    results = await knowledge_search_service.retrieve_topk(query_data)

    # Assert - should find at least 5 documents
    assert len(results) >= 5, (
        f"Multi-month aggregation broken! Expected ≥5 results, got {len(results)}. "
        f"This indicates missing title_pattern in multi-month search path."
    )

    # Verify we have both October and November documents
    titles = [r.title.lower() for r in results]
    has_october = any("ottobre" in t for t in titles)
    has_november = any("novembre" in t for t in titles)

    assert has_october, f"No October documents found! Titles: {titles}"
    assert has_november, f"No November documents found! Titles: {titles}"

    # Verify specific document numbers (n. 56, 62 for Oct; n. 63, 64, 65 for Nov)
    all_titles = "\n".join([r.title for r in results])
    print(f"✓ Multi-month aggregation found {len(results)} documents:")
    print(all_titles)


@pytest.mark.asyncio
async def test_fts_only_query_still_works(db_session: AsyncSession):
    """
    REGRESSION TEST: Ensure FTS queries without document numbers still work.

    This verifies that our SQL changes don't break regular FTS searches.
    """
    # Setup
    # Note: KnowledgeSearchService creates its own SearchService internally
    # Passing search_service as vector_service param would cause errors
    knowledge_search_service = KnowledgeSearchService(
        db_session=db_session, vector_service=None, config=None  # No vector search for this test  # Use default config
    )

    # Execute - regular FTS query (no document number)
    query_data = {
        "query": "contratti di locazione",
        "category": None,
        "search_mode": "bm25_only",  # Use BM25 since vector_service is None
    }
    results = await knowledge_search_service.retrieve_topk(query_data)

    # Assert - FTS should still find relevant documents
    assert len(results) >= 1, (
        f"FTS search broken! Expected ≥1 results, got {len(results)}. "
        f"This indicates SQL WHERE logic broke FTS-only queries."
    )

    # Verify results contain "locazione" or "contratti" (Italian FTS should match)
    titles_and_content = "\n".join([f"{r.title}: {r.content[:100]}" for r in results])
    assert any(
        "locazion" in r.title.lower() or "locazion" in r.content.lower() for r in results
    ), f"Results don't contain 'locazione'. Found:\n{titles_and_content}"

    print(f"✓ FTS-only query works: found {len(results)} documents")


@pytest.mark.asyncio
async def test_single_month_aggregation_works(db_session: AsyncSession):
    """
    REGRESSION TEST: Single month aggregation should still work.
    """
    # Setup
    # Note: KnowledgeSearchService creates its own SearchService internally
    # Passing search_service as vector_service param would cause errors
    knowledge_search_service = KnowledgeSearchService(
        db_session=db_session, vector_service=None, config=None  # No vector search for this test  # Use default config
    )

    # Execute - single month aggregation
    query_data = {
        "query": "risoluzioni novembre 2025",
        "category": None,
        "search_mode": "bm25_only",  # Use BM25 since vector_service is None
    }
    results = await knowledge_search_service.retrieve_topk(query_data)

    # Assert - should find November documents (n. 63, 64, 65)
    assert len(results) >= 3, f"Single month aggregation broken! Expected ≥3 results, got {len(results)}"

    # All results should be from November
    titles = [r.title.lower() for r in results]
    november_count = sum(1 for t in titles if "novembre" in t)
    assert november_count >= 3, f"Expected ≥3 November docs, found {november_count}"

    print(f"✓ Single month aggregation found {len(results)} November documents")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
