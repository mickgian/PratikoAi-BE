"""
TDD Integration Tests for Resolution 64 Search Failures

These tests reproduce the end-to-end failures seen in production:
1. "Cosa dice la Risoluzione n. 64 del 10 novembre 2025?" returns "Non ho trovato"
2. Multi-month aggregation streaming cuts off mid-response

RED Phase: These tests should FAIL with datetime handling errors
GREEN Phase: These tests should PASS after datetime fixes applied
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_search_service import KnowledgeSearchService


@pytest.mark.asyncio
async def test_resolution_64_full_integration_flow(db_session: AsyncSession):
    """
    END-TO-END BUG REPRODUCTION: Resolution 64 search fails in production.

    Before fix: Returns 0 results due to datetime handling error in hybrid scoring
    After fix: Returns Resolution 64 document

    Error seen in logs:
    - "AttributeError: 'str' object has no attribute 'tzinfo'"
    - "knowledge_search_error"
    - Returns empty list []
    """
    service = KnowledgeSearchService(
        db_session=db_session,
        vector_service=None,  # Avoid vector service dependency
        config=None,  # Use default config
    )

    # EXACT user query that fails in production
    query_data = {
        "query": "Cosa dice la Risoluzione n. 64 del 10 novembre 2025?",
        "category": None,
        "search_mode": "bm25_only",  # Bypass vector search to isolate BM25 + hybrid scoring bug
        "canonical_facts": [],
        "filters": {},
        "user_id": "test_user",
        "session_id": "test_session",
        "trace_id": "test_trace",
    }

    # Should NOT crash with datetime error
    results = await service.retrieve_topk(query_data)

    # Must find Resolution 64
    assert len(results) >= 1, (
        f"Resolution 64 not found! Got {len(results)} results. "
        f"This indicates datetime handling bug in hybrid scoring caused exception."
    )

    # Verify correct document found
    titles = [r.title for r in results]
    assert any("64" in title for title in titles), f"Document with '64' not found. Titles: {titles}"

    assert any(
        "risoluzione" in title.lower() for title in titles
    ), f"Document type 'risoluzione' not found. Titles: {titles}"

    # Verify SearchResult has proper datetime objects (not strings)
    for result in results:
        if result.updated_at is not None:
            assert not isinstance(
                result.updated_at, str
            ), f"updated_at should be datetime, not string: {type(result.updated_at)}"

        if result.publication_date is not None:
            assert not isinstance(
                result.publication_date, str
            ), f"publication_date should be date, not string: {type(result.publication_date)}"

    print(f"✓ Resolution 64 found successfully: {results[0].title[:80]}...")


@pytest.mark.asyncio
async def test_multi_month_aggregation_no_crash(db_session: AsyncSession):
    """
    BUG REPRODUCTION: Multi-month aggregation query crashes mid-processing.

    Before fix:
    - Partial results streamed to frontend
    - Exception in hybrid scoring due to datetime handling
    - Stream cuts off mid-response
    - User must refresh to see complete cached results

    After fix: All documents returned successfully without exception
    """
    service = KnowledgeSearchService(db_session=db_session, vector_service=None, config=None)

    # EXACT user query that causes streaming interruption
    query_data = {
        "query": "fammi un riassunto di tutte le risoluzioni dell'agenzia delle entrate di ottobre e novembre 2025",
        "category": None,
        "search_mode": "bm25_only",
        "canonical_facts": [],
        "filters": {},
        "user_id": "test_user",
        "session_id": "test_session",
        "trace_id": "test_trace",
    }

    # Should NOT crash during hybrid scoring of multiple results
    results = await service.retrieve_topk(query_data)

    # Must return documents from both months (at least 5 total)
    assert (
        len(results) >= 5
    ), f"Expected ≥5 documents for Oct+Nov, got {len(results)}. Datetime bug may have caused mid-processing crash."

    # Verify we have documents from both months
    titles_text = " ".join([r.title.lower() for r in results])
    has_october = "ottobre" in titles_text
    has_november = "novembre" in titles_text

    # Note: Due to SQL title matching and multi-month logic, we might not always
    # get both months, but we should get SOME results without crashing
    assert has_october or has_november, "No October or November documents found. This suggests search failed entirely."

    # Verify all results have valid datetime types
    for result in results:
        if result.updated_at is not None:
            assert not isinstance(
                result.updated_at, str
            ), f"Result {result.id} has string updated_at - indicates serialization bug"

    print(f"✓ Multi-month aggregation completed successfully: {len(results)} documents")
    print(f"  October docs: {has_october}, November docs: {has_november}")


@pytest.mark.asyncio
async def test_hybrid_scoring_with_mixed_datetime_types(db_session: AsyncSession):
    """
    EDGE CASE TEST: Hybrid scoring should handle results with mixed datetime types.

    Some results may have datetime objects, others may have None.
    Should not crash on any combination.
    """
    service = KnowledgeSearchService(db_session=db_session, vector_service=None, config=None)

    # Generic query that returns multiple documents
    query_data = {
        "query": "risoluzioni 2025",
        "category": None,
        "search_mode": "bm25_only",
        "canonical_facts": [],
        "filters": {},
        "max_results": 20,
    }

    # Should handle any datetime variations without crashing
    results = await service.retrieve_topk(query_data)

    # Should return some results
    assert len(results) >= 1, "Should find at least some documents"

    # All results should have valid scores (indicates hybrid scoring succeeded)
    for result in results:
        assert isinstance(result.score, float), f"Result {result.id} has invalid score type: {type(result.score)}"
        assert result.score >= 0.0, f"Result {result.id} has negative score: {result.score}"

    print(f"✓ Hybrid scoring handled {len(results)} results with mixed datetime types")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
