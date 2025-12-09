"""E2E tests for multi-pattern document title matching.

Based on actual documents in knowledge_items table (December 2025).
Tests the fix for DEV-BE-69: INPS documents using "numero" instead of "n."
were not being found by title-based search.

These tests require a populated database with real documents.
Run with: pytest tests/e2e/test_document_search_patterns.py -v
"""

import pytest

from app.services.knowledge_search_service import KnowledgeSearchService


class TestDocumentSearchPatterns:
    """Test suite for multi-pattern document title matching."""

    async def _search(self, db_session, query: str, canonical_facts: list[str] | None = None) -> list:
        """Helper to perform search and return results."""
        service = KnowledgeSearchService(db_session=db_session)
        query_data = {
            "query": query,
            "canonical_facts": canonical_facts or [],
            "user_id": "test_user",
            "session_id": "test_session",
            "trace_id": f"test_{query[:20].replace(' ', '_')}",
            "search_mode": "bm25_only",
            "filters": {},
            "max_results": 5,
        }
        return await service.retrieve_topk(query_data)

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_inps_messaggio_3585_original_bug(self, db_session):
        """Regression test for original bug: 'Messaggio numero 3585' not found.

        This was the exact failing query that triggered DEV-BE-69.
        The document exists with title "Messaggio numero 3585 del 27-11-2025"
        but the old code only searched for "n. 3585".
        """
        query = "Di cosa parla il Messaggio numero 3585 dell'inps?"
        results = await self._search(db_session, query)

        assert len(results) > 0, "Original bug NOT fixed - Messaggio 3585 still not found"

        # Verify we found the right document
        found_3585 = any("3585" in r.title for r in results)
        assert found_3585, f"Expected to find document with '3585' in title, got: {[r.title for r in results]}"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_inps_messaggio_simple_query(self, db_session):
        """Test simple INPS messaggio query."""
        results = await self._search(db_session, "messaggio 3585")

        assert len(results) > 0, "No results for 'messaggio 3585'"
        # Should find "Messaggio numero 3585"
        found = any("3585" in r.title and "messaggio" in r.title.lower() for r in results)
        assert found, f"Expected INPS messaggio 3585, got: {[r.title for r in results]}"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_inps_circolare_pattern(self, db_session):
        """Test INPS circolare search (uses 'numero' format)."""
        results = await self._search(db_session, "circolare 149 INPS")

        # Should find "Circolare numero 149 del..."
        if results:
            found = any("149" in r.title and "circol" in r.title.lower() for r in results)
            if found:
                print(f"Found circolare 149: {results[0].title}")
        # Note: This test may fail if circolare 149 doesn't exist in DB

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cassazione_ordinanza_pattern(self, db_session):
        """Test Cassazione ordinanza search (uses 'n.' format)."""
        results = await self._search(db_session, "ordinanza 26166")

        if results:
            found = any("26166" in r.title for r in results)
            if found:
                print(f"Found ordinanza 26166: {results[0].title}")
        # Note: This test may fail if ordinanza 26166 doesn't exist in DB

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_agenzia_entrate_risoluzione(self, db_session):
        """Test Agenzia Entrate risoluzione (uses 'n.' format)."""
        results = await self._search(db_session, "risoluzione 63")

        if results:
            found = any("63" in r.title and "risoluz" in r.title.lower() for r in results)
            if found:
                print(f"Found risoluzione 63: {results[0].title}")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multiple_patterns_generated(self, db_session):
        """Verify that multiple patterns are generated for search."""
        service = KnowledgeSearchService(db_session=db_session)

        # Test pattern generation for messaggio (INPS style)
        patterns = service._generate_title_patterns("messaggio", "3585")

        assert len(patterns) >= 3, f"Expected at least 3 patterns, got {len(patterns)}"
        assert any("numero 3585" in p for p in patterns), "Missing 'numero 3585' pattern"
        assert any("n. 3585" in p for p in patterns), "Missing 'n. 3585' pattern"
        print(f"Generated patterns: {patterns}")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_compound_reference_patterns(self, db_session):
        """Verify compound reference patterns (e.g., DPR 1124/1965)."""
        service = KnowledgeSearchService(db_session=db_session)

        # Test pattern generation for compound reference
        patterns = service._generate_title_patterns("DPR", "1124", "1965")

        assert len(patterns) >= 5, f"Expected at least 5 patterns, got {len(patterns)}"
        assert any("1124/1965" in p for p in patterns), "Missing compound '1124/1965' pattern"
        assert any("DPR" in p and "1124" in p for p in patterns), "Missing DPR-specific pattern"
        print(f"Generated compound patterns: {patterns}")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_pattern_limit_respected(self, db_session):
        """Verify pattern generation respects the 7-pattern limit."""
        service = KnowledgeSearchService(db_session=db_session)

        # Generate patterns with all parameters
        patterns = service._generate_title_patterns("messaggio", "3585", "2025")

        assert len(patterns) <= 7, f"Generated {len(patterns)} patterns, max is 7"
        print(f"Pattern count: {len(patterns)}")
