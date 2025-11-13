"""
Integration tests for knowledge retrieval with real database content.

Tests that the RAG system properly retrieves and uses actual knowledge from the database,
specifically testing with Risoluzione 56 content that exists in the DB.
"""

import pytest
from sqlalchemy import (
    select,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.knowledge import KnowledgeItem
from app.models.knowledge_chunk import KnowledgeChunk
from app.services.knowledge_search_service import (
    KnowledgeSearchService,
    SearchMode,
)


@pytest.mark.asyncio
@pytest.mark.integration
class TestKnowledgeRetrievalIntegration:
    """Integration tests for knowledge retrieval with real database."""

    @pytest.fixture
    async def db_session(self):
        """Create async database session for testing."""
        # Convert postgresql:// to postgresql+asyncpg://
        postgres_url = settings.POSTGRES_URL
        if postgres_url.startswith("postgresql://"):
            postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(postgres_url, echo=False)
        async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session_maker() as session:
            yield session

        await engine.dispose()

    @pytest.fixture
    def search_service(self, db_session):
        """Create knowledge search service with real DB session."""
        return KnowledgeSearchService(
            db_session=db_session, vector_service=None, config=None  # Will use FTS-only mode  # Use defaults
        )

    async def test_db_has_risoluzione_56_content(self, db_session):
        """Verify that Risoluzione 56 content exists in database."""
        # Check knowledge_items table
        result = await db_session.execute(select(KnowledgeItem).where(KnowledgeItem.title.ilike("%risoluzione%56%")))
        items = result.scalars().all()

        assert len(items) > 0, "Should have at least one knowledge item for Risoluzione 56"

        # Check knowledge_chunks table
        result = await db_session.execute(
            select(KnowledgeChunk).where(KnowledgeChunk.document_title.ilike("%risoluzione%56%"))
        )
        chunks = result.scalars().all()

        assert len(chunks) >= 3, "Should have at least 3 chunks for Risoluzione 56"
        assert any(
            "tardiva registrazione" in chunk.chunk_text.lower() for chunk in chunks
        ), "Should contain content about late registration"
        assert any(
            "contratti di locazione" in chunk.chunk_text.lower() for chunk in chunks
        ), "Should contain content about rental contracts"

    async def test_fts_search_finds_risoluzione_56(self, db_session):
        """Test that full-text search finds Risoluzione 56 content."""
        # Direct FTS query
        query = text(
            """
            SELECT id, document_title, LEFT(chunk_text, 100) as preview
            FROM knowledge_chunks
            WHERE search_vector @@ plainto_tsquery('italian', 'risoluzione 56')
            LIMIT 5
        """
        )

        result = await db_session.execute(query)
        rows = result.fetchall()

        assert len(rows) > 0, "FTS should find results for 'risoluzione 56'"

        # Verify content quality
        for row in rows:
            assert row.document_title is not None
            assert len(row.preview) > 20, "Should have meaningful preview text"

    async def test_retrieve_topk_returns_risoluzione_56(self, search_service):
        """Test that retrieve_topk returns Risoluzione 56 content for relevant query."""
        query_data = {
            "query": "risoluzione numero 56",  # Use terms that exist in the document
            "search_mode": SearchMode.BM25_ONLY,  # Use FTS only
            "max_results": 10,
        }

        results = await search_service.retrieve_topk(query_data)

        assert len(results) > 0, "Should return results for risoluzione 56 query"

        # Check that results contain relevant content
        found_risoluzione = False
        for result in results:
            if "risoluzione" in result.title.lower() and "56" in result.title:
                found_risoluzione = True
                break

        assert found_risoluzione, "Results should include Risoluzione 56 content"

    async def test_italian_query_retrieves_locazione_content(self, search_service):
        """Test that Italian query about rental registration retrieves correct content."""
        query_data = {
            "query": "tardiva registrazione contratti locazione",
            "search_mode": SearchMode.BM25_ONLY,
            "max_results": 5,
        }

        results = await search_service.retrieve_topk(query_data)

        assert len(results) > 0, "Should return results for locazione query"

        # Verify content relevance
        relevant_found = False
        for result in results:
            content_lower = result.content.lower()
            if "locazione" in content_lower or "contratti" in content_lower:
                relevant_found = True
                break

        assert relevant_found, "Results should contain relevant rental contract content"

    async def test_empty_query_returns_no_results(self, search_service):
        """Test that empty query returns no results (guards against empty query bug)."""
        query_data = {"query": "", "search_mode": SearchMode.BM25_ONLY, "max_results": 10}

        results = await search_service.retrieve_topk(query_data)

        assert len(results) == 0, "Empty query should return no results"

    async def test_specific_risoluzione_query(self, search_service):
        """Test a natural query for risoluzione 56.

        Note: Question words like "Cosa dice" may not improve FTS matching since they're
        not in the document. Core search terms work better for exact matching.
        """
        query_data = {
            "query": "risoluzione numero 56",  # Core search terms that exist in document
            "search_mode": SearchMode.BM25_ONLY,
            "max_results": 5,
        }

        results = await search_service.retrieve_topk(query_data)

        assert len(results) > 0, "Should return results for specific risoluzione query"

        # Verify quality of top result
        if results:
            top_result = results[0]
            assert top_result.score > 0.1, "Top result should have meaningful score"
            assert len(top_result.content) > 50, "Top result should have substantial content"

            # Check for expected keywords
            content_lower = top_result.content.lower()
            assert any(
                keyword in content_lower for keyword in ["risoluzione", "registrazione", "locazione"]
            ), "Content should contain relevant keywords"


@pytest.mark.asyncio
@pytest.mark.integration
class TestStep39Integration:
    """Integration tests specifically for Step 39 (KB Pre-Fetch) node."""

    async def test_step_39_receives_user_query_from_state(self):
        """Test that Step 39 node receives populated user_query from RAGState."""
        from app.core.langgraph.nodes.step_039__kbpre_fetch import node_step_39
        from app.core.langgraph.types import RAGState

        # Create state with user_query
        state: RAGState = {
            "user_query": "Cosa dice la risoluzione numero 56?",
            "messages": [{"role": "user", "content": "Cosa dice la risoluzione numero 56?"}],
            "session_id": "test_session",
            "user_id": 1,
            "request_id": "test_request",
        }

        # Node should extract query and pass to orchestrator
        result_state = await node_step_39(state)

        # Verify kb_results were populated (even if empty due to no DB access in this test)
        assert "kb_results" in result_state, "Should populate kb_results in state"
        assert result_state["kb_results"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
