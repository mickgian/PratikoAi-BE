"""
TDD RED Phase 2-3: Integration tests for QueryNormalizer with KnowledgeSearchService

These tests validate that QueryNormalizer is properly integrated into the search flow:
- Layer 1: Check canonical_facts first (regex-extracted)
- Layer 2: If no doc ref in facts, call QueryNormalizer (LLM)
- Layer 3: Multi-pass fallback if LLM also fails
- Verify end-to-end search with LLM normalization

Expected: ALL tests will FAIL before integration (QueryNormalizer not used in search service)
"""

import json
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_search_service import KnowledgeSearchService
from app.services.query_normalizer import QueryNormalizer


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for query normalization"""

    def _create_response(doc_type: str, doc_number: str):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"type": doc_type, "number": doc_number})
        return mock_response

    return _create_response


@pytest.mark.asyncio
async def test_search_uses_llm_when_canonical_facts_empty(db_session: AsyncSession, mock_llm_response):
    """
    EXPECTED: FAIL (integration not implemented)

    When canonical_facts is empty (no regex match), search service should:
    1. Call QueryNormalizer to extract document reference
    2. Use LLM-extracted reference to build title pattern
    3. Find the document

    Example: "risoluzione sessantaquattro" → LLM extracts {"type": "risoluzione", "number": "64"}
    """
    service = KnowledgeSearchService(db_session=db_session, vector_service=None, config=None)

    # Query with written number - regex won't catch "sessantaquattro"
    query_data = {
        "query": "risoluzione sessantaquattro",
        "canonical_facts": [],  # Empty - forces LLM path
        "search_mode": "bm25_only",
    }

    # Mock QueryNormalizer to return expected extraction
    AsyncMock(return_value=mock_llm_response("risoluzione", "64"))
    with patch("app.services.knowledge_search_service.QueryNormalizer") as MockNormalizer:
        mock_normalizer = MagicMock()
        mock_normalizer.normalize = AsyncMock(return_value={"type": "risoluzione", "number": "64"})
        MockNormalizer.return_value = mock_normalizer

        results = await service.retrieve_topk(query_data)

        # Verify QueryNormalizer was called
        mock_normalizer.normalize.assert_called_once_with("risoluzione sessantaquattro")

        # Verify document was found
        assert (
            len(results) >= 1
        ), "Should find Resolution 64 via LLM normalization. Currently FAILS because integration not implemented."
        assert any(
            "64" in r.title for r in results
        ), f"Should find document with '64' in title. Found: {[r.title[:80] for r in results]}"


@pytest.mark.asyncio
async def test_search_skips_llm_when_canonical_facts_present(db_session: AsyncSession):
    """
    EXPECTED: FAIL (integration not implemented)

    When canonical_facts already contains document reference (from regex),
    search service should NOT call QueryNormalizer (avoid unnecessary LLM cost).

    Example: canonical_facts = [{"doc_type": "risoluzione", "doc_number": "64"}]
    """
    service = KnowledgeSearchService(db_session=db_session, vector_service=None, config=None)

    # Query with canonical_facts already populated (from regex)
    query_data = {
        "query": "risoluzione 64",
        "canonical_facts": ["risoluzione 64"],  # String facts, not dict
        "search_mode": "bm25_only",
    }

    # Mock QueryNormalizer to track calls
    with patch("app.services.knowledge_search_service.QueryNormalizer") as MockNormalizer:
        mock_normalizer = MagicMock()
        mock_normalizer.normalize = AsyncMock(return_value={"type": "risoluzione", "number": "64"})
        MockNormalizer.return_value = mock_normalizer

        results = await service.retrieve_topk(query_data)

        # Verify QueryNormalizer was NOT called (canonical_facts already present)
        mock_normalizer.normalize.assert_not_called()

        # Document should still be found (via existing regex path)
        assert len(results) >= 1, "Should find document via canonical_facts"


@pytest.mark.asyncio
async def test_search_handles_llm_failure_gracefully(db_session: AsyncSession):
    """
    EXPECTED: FAIL (integration not implemented)

    When QueryNormalizer fails (timeout, invalid response, etc.),
    search should:
    1. Log the failure
    2. Fall back to multi-pass number extraction
    3. Continue searching (not crash)

    Example: LLM timeout → extract "64" → try "n. 64" pattern
    """
    service = KnowledgeSearchService(db_session=db_session, vector_service=None, config=None)

    query_data = {
        "query": "cosa dice la 64?",
        "canonical_facts": [],  # Empty - forces LLM path
        "search_mode": "bm25_only",
    }

    # Mock QueryNormalizer to return None (LLM failed)
    with patch("app.services.knowledge_search_service.QueryNormalizer") as MockNormalizer:
        mock_normalizer = MagicMock()
        mock_normalizer.normalize = AsyncMock(return_value=None)  # LLM failed
        MockNormalizer.return_value = mock_normalizer

        results = await service.retrieve_topk(query_data)

        # Verify QueryNormalizer was called
        mock_normalizer.normalize.assert_called_once()

        # Should still find document via multi-pass fallback (extract "64")
        assert len(results) >= 1, (
            "Multi-pass fallback should find document when LLM fails. "
            "Currently FAILS because integration not implemented."
        )
        assert any(
            "64" in r.title for r in results
        ), f"Should find document with '64' in title via fallback. Found: {[r.title[:80] for r in results]}"


@pytest.mark.asyncio
async def test_search_handles_abbreviations(db_session: AsyncSession, mock_llm_response):
    """
    EXPECTED: FAIL (integration not implemented)

    LLM should expand abbreviations that regex can't handle.

    Example: "ris 64" → LLM expands to {"type": "risoluzione", "number": "64"}
    """
    service = KnowledgeSearchService(db_session=db_session, vector_service=None, config=None)

    query_data = {
        "query": "ris 64",  # Abbreviated form
        "canonical_facts": [],  # Force LLM path
        "search_mode": "bm25_only",
    }

    # Mock QueryNormalizer to expand abbreviation
    with patch("app.services.knowledge_search_service.QueryNormalizer") as MockNormalizer:
        mock_normalizer = MagicMock()
        mock_normalizer.normalize = AsyncMock(return_value={"type": "risoluzione", "number": "64"})
        MockNormalizer.return_value = mock_normalizer

        results = await service.retrieve_topk(query_data)

        # Verify abbreviation was handled
        mock_normalizer.normalize.assert_called_once_with("ris 64")
        assert (
            len(results) >= 1
        ), "Should find document with abbreviated query via LLM. Currently FAILS because integration not implemented."


@pytest.mark.asyncio
async def test_search_handles_complex_typos(db_session: AsyncSession, mock_llm_response):
    """
    EXPECTED: FAIL (integration not implemented)

    LLM should correct typos that regex can't handle.

    Example: "risouzione 64" (missing 'luz') → LLM corrects to {"type": "risoluzione", "number": "64"}
    """
    service = KnowledgeSearchService(db_session=db_session, vector_service=None, config=None)

    query_data = {
        "query": "risouzione 64",  # Typo: missing 'luz'
        "canonical_facts": [],  # Force LLM path
        "search_mode": "bm25_only",
    }

    # Mock QueryNormalizer to correct typo
    with patch("app.services.knowledge_search_service.QueryNormalizer") as MockNormalizer:
        mock_normalizer = MagicMock()
        mock_normalizer.normalize = AsyncMock(return_value={"type": "risoluzione", "number": "64"})
        MockNormalizer.return_value = mock_normalizer

        results = await service.retrieve_topk(query_data)

        # Verify typo was handled
        mock_normalizer.normalize.assert_called_once_with("risouzione 64")
        assert (
            len(results) >= 1
        ), "Should find document with typo query via LLM. Currently FAILS because integration not implemented."


@pytest.mark.asyncio
async def test_search_returns_none_for_non_document_query(db_session: AsyncSession):
    """
    EXPECTED: FAIL (integration not implemented)

    When query has no document reference, LLM should return None,
    and search should proceed with normal FTS search (not crash).

    Example: "come calcolare le tasse" → LLM returns None → normal search
    """
    service = KnowledgeSearchService(db_session=db_session, vector_service=None, config=None)

    query_data = {
        "query": "come calcolare le tasse",  # No document reference
        "canonical_facts": [],  # Force LLM path
        "search_mode": "bm25_only",
    }

    # Mock QueryNormalizer to return None (no document found)
    with patch("app.services.knowledge_search_service.QueryNormalizer") as MockNormalizer:
        mock_normalizer = MagicMock()
        mock_normalizer.normalize = AsyncMock(return_value=None)
        MockNormalizer.return_value = mock_normalizer

        # Should not crash - just return normal search results
        results = await service.retrieve_topk(query_data)

        # Verify QueryNormalizer was called but returned None
        mock_normalizer.normalize.assert_called_once_with("come calcolare le tasse")

        # Results may be empty or have general tax info - just verify no crash
        assert isinstance(results, list), "Should return list (not crash)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
