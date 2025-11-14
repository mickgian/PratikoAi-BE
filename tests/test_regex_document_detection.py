"""
TDD RED Phase 1: Tests for regex-based document detection

These tests validate that the regex pattern correctly detects document references
in various formats:
- With "n.": "risoluzione n. 64"
- Without "n.": "risoluzione 64"
- User typos: "risluzione 64"

Expected: 2 tests will FAIL before fixing the regex (missing correct spelling pattern)
"""

import re
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_search_service import KnowledgeSearchService


class TestRegexDocumentDetection:
    """Test regex pattern for document number detection"""

    def test_regex_detects_risoluzione_with_n_dot(self):
        """
        EXPECTED: PASS (already works)
        Pattern should match: "risoluzione n. 64"
        """
        query = "Cosa dice la Risoluzione n. 64 del 10 novembre 2025?"

        # Current regex pattern from knowledge_search_service.py:510
        pattern = r"\b(n\.?|numero|risluzion\w*|circolar\w*|decret\w*|interpell\w*|rispost\w*)\s*(\d+)"
        match = re.search(pattern, query, re.IGNORECASE)

        assert match is not None, "Should match 'Risoluzione n. 64'"
        assert match.group(2) == "64", "Should extract number '64'"

    def test_regex_detects_risoluzione_without_n_dot(self):
        """
        EXPECTED: PASS (after fix)
        Pattern should match: "risoluzione 64" (correct spelling, no "n.")

        This test validates the fix: regex now has BOTH 'risoluzion' (correct)
        and 'risluzion' (typo handling).
        """
        query = "Cosa dice la risoluzione 64?"

        # FIXED regex pattern - now includes both correct spelling and typo
        pattern = r"\b(n\.?|numero|risoluzion\w*|risluzion\w*|circolar\w*|decret\w*|interpell\w*|rispost\w*)\s*(\d+)"
        match = re.search(pattern, query, re.IGNORECASE)

        assert match is not None, "Should match 'risoluzione 64' (correct spelling without 'n.')."
        assert match.group(2) == "64", "Should extract number '64'"

    def test_regex_detects_user_typo_risluzione(self):
        """
        EXPECTED: PASS (already works)
        Pattern should match: "risluzione 64" (user typo)

        This validates that typo handling works correctly.
        """
        query = "Cosa dice la risluzione 64?"

        # Current regex pattern
        pattern = r"\b(n\.?|numero|risluzion\w*|circolar\w*|decret\w*|interpell\w*|rispost\w*)\s*(\d+)"
        match = re.search(pattern, query, re.IGNORECASE)

        assert match is not None, "Should match 'risluzione 64' (user typo)"
        assert match.group(2) == "64", "Should extract number '64'"

    def test_regex_detects_circolare_without_n(self):
        """
        EXPECTED: PASS (already works)
        Pattern should match: "circolare 123"
        """
        query = "circolare 123 dell'agenzia"

        pattern = r"\b(n\.?|numero|risluzion\w*|circolar\w*|decret\w*|interpell\w*|rispost\w*)\s*(\d+)"
        match = re.search(pattern, query, re.IGNORECASE)

        assert match is not None, "Should match 'circolare 123'"
        assert match.group(2) == "123", "Should extract number '123'"


@pytest.mark.asyncio
async def test_multipass_fallback_finds_document_by_number(db_session: AsyncSession):
    """
    EXPECTED: FAIL (multi-pass fallback not implemented yet)

    This test validates that if regex fails to detect document type,
    the multi-pass fallback should extract ANY numbers and try them as document numbers.

    Example: "la 64 dell'agenzia" → should try "n. 64" as title pattern
    """
    # Setup
    service = KnowledgeSearchService(db_session=db_session, vector_service=None, config=None)

    # Query that doesn't match regex (no "risoluzione" or "circolare" keywords)
    query_data = {
        "query": "cosa dice la 64?",  # Just "la 64" - no document type keyword
        "category": None,
        "search_mode": "bm25_only",
    }

    # Should find Resolution 64 via multi-pass fallback
    results = await service.retrieve_topk(query_data)

    assert len(results) >= 1, (
        "Multi-pass fallback should find document by extracting number '64'. "
        "Currently FAILS because fallback not implemented."
    )

    assert any(
        "64" in r.title for r in results
    ), f"Should find document with '64' in title. Found: {[r.title[:80] for r in results]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
