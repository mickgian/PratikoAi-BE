"""
Test suite for PostgreSQL Full-Text Search implementation.
Following TDD principles - these tests are written before implementation.
"""

import asyncio
import time
from datetime import datetime
from typing import List, Optional

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.knowledge import KnowledgeItem
from app.services.search_service import SearchResult, SearchService


class TestPostgreSQLFullTextSearch:
    """Test PostgreSQL Full-Text Search functionality"""

    @pytest.mark.asyncio
    async def test_tsvector_column_exists(self, db_session: AsyncSession):
        """Test that tsvector column exists on knowledge_items table"""
        # Check if the column exists in the database schema
        result = await db_session.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'knowledge_items'
                AND column_name = 'search_vector'
            """)
        )
        column = result.scalar_one_or_none()
        assert column == "search_vector", "search_vector column should exist on knowledge_items table"

    @pytest.mark.asyncio
    async def test_italian_language_configuration(self, db_session: AsyncSession):
        """Test that Italian language configuration is properly set up"""
        # Check if Italian text search configuration exists
        result = await db_session.execute(
            text("""
                SELECT cfgname
                FROM pg_ts_config
                WHERE cfgname = 'italian'
            """)
        )
        config = result.scalar_one_or_none()
        assert config == "italian", "Italian text search configuration should be available"

    @pytest.mark.asyncio
    async def test_gin_index_creation(self, db_session: AsyncSession):
        """Test that GIN index is created on search_vector column"""
        # Check if GIN index exists
        result = await db_session.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'knowledge_items'
                AND indexdef LIKE '%USING gin%'
                AND indexdef LIKE '%search_vector%'
            """)
        )
        index = result.scalar_one_or_none()
        assert index is not None, "GIN index should exist on search_vector column"

    @pytest.mark.asyncio
    async def test_search_with_ranking(self, db_session: AsyncSession):
        """Test search functionality with ts_rank scoring"""
        # Create test data
        test_items = [
            KnowledgeItem(
                title="Guida alla dichiarazione dei redditi",
                content="La dichiarazione dei redditi in Italia richiede attenzione ai dettagli fiscali.",
                category="tax_guide",
                source="test",
                relevance_score=0.9,
            ),
            KnowledgeItem(
                title="IVA e fatturazione elettronica",
                content="L'IVA italiana e la fatturazione elettronica sono obbligatorie per le imprese.",
                category="vat_guide",
                source="test",
                relevance_score=0.8,
            ),
            KnowledgeItem(
                title="Codice fiscale italiano",
                content="Il codice fiscale è necessario per tutte le operazioni fiscali in Italia.",
                category="general",
                source="test",
                relevance_score=0.7,
            ),
        ]

        for item in test_items:
            db_session.add(item)
        await db_session.commit()

        # Test search with ranking
        search_service = SearchService(db_session)
        results = await search_service.search("dichiarazione redditi", limit=10)

        assert len(results) > 0, "Should find results for 'dichiarazione redditi'"
        assert results[0].title == "Guida alla dichiarazione dei redditi", "Most relevant result should be first"
        assert all(r.rank_score > 0 for r in results), "All results should have positive rank scores"
        assert (
            results[0].rank_score > results[-1].rank_score if len(results) > 1 else True
        ), "Results should be ordered by rank"

    @pytest.mark.asyncio
    async def test_accent_insensitive_search(self, db_session: AsyncSession):
        """Test that search is accent-insensitive for Italian text"""
        # Create test data with accented characters
        test_items = [
            KnowledgeItem(
                title="Società a responsabilità limitata",
                content="La società a responsabilità limitata è una forma giuridica molto diffusa.",
                category="business",
                source="test",
                relevance_score=0.9,
            ),
            KnowledgeItem(
                title="Societa a responsabilita limitata",  # Without accents
                content="Versione senza accenti del contenuto precedente.",
                category="business",
                source="test",
                relevance_score=0.8,
            ),
        ]

        for item in test_items:
            db_session.add(item)
        await db_session.commit()

        search_service = SearchService(db_session)

        # Search with accents
        results_with_accents = await search_service.search("società responsabilità", limit=10)
        # Search without accents
        results_without_accents = await search_service.search("societa responsabilita", limit=10)

        assert len(results_with_accents) == 2, "Should find both versions when searching with accents"
        assert len(results_without_accents) == 2, "Should find both versions when searching without accents"

    @pytest.mark.asyncio
    async def test_partial_word_matching(self, db_session: AsyncSession):
        """Test partial word matching functionality"""
        # Create test data
        test_items = [
            KnowledgeItem(
                title="Fatturazione elettronica obbligatoria",
                content="La fatturazione elettronica è diventata obbligatoria per tutte le partite IVA.",
                category="invoice",
                source="test",
                relevance_score=0.9,
            ),
            KnowledgeItem(
                title="Sistema di fatture digitali",
                content="Il sistema delle fatture digitali semplifica la gestione contabile.",
                category="invoice",
                source="test",
                relevance_score=0.8,
            ),
        ]

        for item in test_items:
            db_session.add(item)
        await db_session.commit()

        search_service = SearchService(db_session)

        # Test partial matching
        results = await search_service.search("fattur", limit=10)  # Partial word

        assert len(results) == 2, "Should find results with partial word 'fattur'"
        assert any(
            "fattur" in r.title.lower() or "fattur" in r.content.lower() for r in results
        ), "Results should contain the partial word"

    @pytest.mark.asyncio
    async def test_performance_10k_records(self, db_session: AsyncSession):
        """Test search performance with 10,000 records (<100ms requirement)"""
        # Create 10,000 test records
        batch_size = 100
        total_records = 10000

        for i in range(0, total_records, batch_size):
            batch = []
            for j in range(batch_size):
                idx = i + j
                item = KnowledgeItem(
                    title=f"Documento fiscale numero {idx}",
                    content=f"Contenuto del documento {idx} con informazioni su tasse, IVA, e dichiarazioni.",
                    category="tax_document",
                    source="performance_test",
                    relevance_score=0.5,
                )
                batch.append(item)

            db_session.add_all(batch)
            if (i + batch_size) % 1000 == 0:
                await db_session.commit()
                print(f"Inserted {i + batch_size} records...")

        await db_session.commit()

        # Test search performance
        search_service = SearchService(db_session)

        # Warm up
        await search_service.search("documento fiscale", limit=10)

        # Measure performance
        start_time = time.time()
        results = await search_service.search("tasse IVA dichiarazioni", limit=50)
        end_time = time.time()

        search_time_ms = (end_time - start_time) * 1000

        assert len(results) > 0, "Should find results in large dataset"
        assert search_time_ms < 100, f"Search should complete in <100ms, took {search_time_ms:.2f}ms"
        print(f"Search completed in {search_time_ms:.2f}ms with {len(results)} results")

    @pytest.mark.asyncio
    async def test_search_vector_trigger(self, db_session: AsyncSession):
        """Test that search_vector is automatically updated via trigger"""
        # Create a knowledge item
        item = KnowledgeItem(
            title="Test trigger update",
            content="Initial content for trigger test",
            category="test",
            source="test",
            relevance_score=0.5,
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        # Check initial search vector
        result = await db_session.execute(
            text("""
                SELECT search_vector IS NOT NULL
                FROM knowledge_items
                WHERE id = :id
            """),
            {"id": item.id},
        )
        has_vector = result.scalar_one()
        assert has_vector, "Search vector should be populated on insert"

        # Update the content
        item.content = "Updated content with different keywords like fattura and IVA"
        await db_session.commit()

        # Verify search finds the updated content
        search_service = SearchService(db_session)
        results = await search_service.search("fattura IVA", limit=10)

        assert any(r.id == item.id for r in results), "Should find item with updated content"

    @pytest.mark.asyncio
    async def test_search_result_structure(self, db_session: AsyncSession):
        """Test that search results have correct structure"""
        # Create test data
        item = KnowledgeItem(
            title="Test search result",
            content="Content for testing search result structure with Italian keywords like tasse.",
            category="test",
            source="test",
            relevance_score=0.8,
        )
        db_session.add(item)
        await db_session.commit()

        search_service = SearchService(db_session)
        results = await search_service.search("tasse", limit=1)

        assert len(results) == 1, "Should find one result"
        result = results[0]

        # Check SearchResult structure
        assert hasattr(result, "id"), "Result should have id"
        assert hasattr(result, "title"), "Result should have title"
        assert hasattr(result, "content"), "Result should have content"
        assert hasattr(result, "category"), "Result should have category"
        assert hasattr(result, "rank_score"), "Result should have rank_score"
        assert hasattr(result, "relevance_score"), "Result should have relevance_score"
        assert hasattr(result, "highlight"), "Result should have highlight"

        assert result.rank_score > 0, "Rank score should be positive"
        assert result.title == item.title, "Title should match"
        assert "tasse" in result.highlight.lower(), "Highlight should contain search term"

    @pytest.mark.asyncio
    async def test_empty_search_query(self, db_session: AsyncSession):
        """Test handling of empty search queries"""
        search_service = SearchService(db_session)

        # Test empty string
        results = await search_service.search("", limit=10)
        assert results == [], "Empty search should return empty results"

        # Test whitespace only
        results = await search_service.search("   ", limit=10)
        assert results == [], "Whitespace-only search should return empty results"

    @pytest.mark.asyncio
    async def test_special_characters_handling(self, db_session: AsyncSession):
        """Test handling of special characters in search queries"""
        # Create test data
        item = KnowledgeItem(
            title="Società & Co. S.r.l.",
            content="Informazioni su società e partnership con caratteri speciali.",
            category="business",
            source="test",
            relevance_score=0.7,
        )
        db_session.add(item)
        await db_session.commit()

        search_service = SearchService(db_session)

        # Test with special characters
        results = await search_service.search("Società & Co", limit=10)
        assert len(results) > 0, "Should handle special characters in search"

        # Test with SQL injection attempt (should be safe)
        results = await search_service.search("'; DROP TABLE knowledge_items; --", limit=10)
        # Should not raise an error and table should still exist

        # Verify table still exists
        result = await db_session.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'knowledge_items')")
        )
        table_exists = result.scalar()
        assert table_exists, "Table should still exist after SQL injection attempt"


@pytest.fixture
async def db_session():
    """Provide a transactional database session for tests"""
    async for session in get_async_session():
        async with session.begin():
            yield session
            # Rollback will happen automatically
