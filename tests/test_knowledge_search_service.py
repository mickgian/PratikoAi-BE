"""
Test suite for RAG STEP 39 - Knowledge Search Service.

This module tests the knowledge search service that implements BM25 text search,
vector semantic search, and recency boost for retrieving top-k knowledge items.

Based on Mermaid diagram: KBPreFetch (KnowledgeSearch.retrieve_topk BM25 and vectors and recency boost)
"""

import asyncio
from dataclasses import asdict
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.knowledge_search_service import (
    KnowledgeSearchConfig,
    KnowledgeSearchService,
    SearchMode,
    SearchResult,
)


class TestKnowledgeSearchService:
    """Test knowledge search service with BM25 and vector search capabilities."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def mock_vector_service(self):
        """Create mock vector service."""
        vector_service = Mock()
        vector_service.is_available.return_value = True
        vector_service.create_embedding.return_value = [0.1] * 384  # Mock embedding
        vector_service.search_similar.return_value = [
            {"id": "vec1", "score": 0.95, "metadata": {"title": "Vector Match", "category": "tax"}},
            {"id": "vec2", "score": 0.88, "metadata": {"title": "Vector Match 2", "category": "legal"}},
        ]
        return vector_service

    @pytest.fixture
    def search_config(self):
        """Create search configuration for testing."""
        return KnowledgeSearchConfig(
            bm25_weight=0.4,
            vector_weight=0.4,
            recency_weight=0.2,
            max_results=10,
            min_score_threshold=0.1,
            recency_decay_days=90,
        )

    @pytest.fixture
    def knowledge_service(self, mock_db_session, mock_vector_service, search_config):
        """Create knowledge search service instance for testing."""
        return KnowledgeSearchService(
            db_session=mock_db_session, vector_service=mock_vector_service, config=search_config
        )

    @pytest.fixture
    def sample_query_data(self):
        """Sample query data for testing."""
        return {
            "query": "Aliquote IVA ordinarie in Italia",
            "canonical_facts": ["aliquote", "iva", "ordinarie", "italia"],
            "user_id": "test_user_123",
            "session_id": "session_456",
            "trace_id": "trace_789",
            "context": {"domain": "tax", "language": "it"},
        }

    @pytest.fixture
    def mock_bm25_results(self):
        """Mock BM25 search results from PostgreSQL."""
        return [
            {
                "id": "bm25_1",
                "title": "Aliquote IVA Ordinarie",
                "content": "Le aliquote IVA ordinarie in Italia sono del 22%...",
                "category": "tax",
                "source": "official_docs",
                "rank_score": 0.85,
                "relevance_score": 0.9,
                "updated_at": datetime.now(UTC) - timedelta(days=10),
            },
            {
                "id": "bm25_2",
                "title": "IVA Ridotte",
                "content": "Le aliquote IVA ridotte sono del 4% e 10%...",
                "category": "tax",
                "source": "faq",
                "rank_score": 0.78,
                "relevance_score": 0.85,
                "updated_at": datetime.now(UTC) - timedelta(days=30),
            },
        ]

    @pytest.mark.asyncio
    async def test_retrieve_topk_hybrid_search(self, knowledge_service, sample_query_data, mock_bm25_results):
        """Test hybrid search combining BM25 and vector search with recency boost."""
        with (
            patch("app.services.knowledge_search_service.KnowledgeSearchService._perform_bm25_search") as mock_bm25,
            patch(
                "app.services.knowledge_search_service.KnowledgeSearchService._perform_vector_search"
            ) as mock_vector,
            patch("app.observability.rag_logging.rag_step_log") as mock_log,
        ):
            # Setup mocks
            mock_bm25.return_value = mock_bm25_results
            mock_vector.return_value = [
                SearchResult(
                    id="vec1",
                    title="Vector Tax Match",
                    content="Content from vector search...",
                    category="tax",
                    score=0.92,
                    source="kb",
                    updated_at=datetime.now(UTC) - timedelta(days=5),
                )
            ]

            # Execute search
            results = await knowledge_service.retrieve_topk(sample_query_data)

            # Verify results
            assert len(results) > 0
            assert all(isinstance(r, SearchResult) for r in results)

            # Verify hybrid scoring (should combine BM25, vector, and recency)
            top_result = results[0]
            assert top_result.score > 0
            assert hasattr(top_result, "bm25_score")
            assert hasattr(top_result, "vector_score")
            assert hasattr(top_result, "recency_score")

            # Verify structured logging (rag_step_timer logs with positional args and level)
            mock_log.assert_called()
            call_args = mock_log.call_args
            assert call_args[0][0] == 39  # step
            assert (
                call_args[0][1] == "RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost"
            )  # step_id
            assert call_args[0][2] == "KBPreFetch"  # node_label
            assert call_args[1]["query"] == sample_query_data["query"]
            assert call_args[1]["search_mode"] == "hybrid"
            assert call_args[1]["trace_id"] == "trace_789"
            assert "latency_ms" in call_args[1]

    @pytest.mark.asyncio
    async def test_bm25_only_search_mode(self, knowledge_service, sample_query_data, mock_bm25_results):
        """Test BM25-only search mode."""
        with patch("app.services.knowledge_search_service.KnowledgeSearchService._perform_bm25_search") as mock_bm25:
            mock_bm25.return_value = mock_bm25_results

            # Force BM25-only mode
            sample_query_data["search_mode"] = SearchMode.BM25_ONLY

            results = await knowledge_service.retrieve_topk(sample_query_data)

            assert len(results) == 2
            assert all(r.search_method == "bm25" for r in results)
            mock_bm25.assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_only_search_mode(self, knowledge_service, sample_query_data):
        """Test vector-only search mode."""
        with patch(
            "app.services.knowledge_search_service.KnowledgeSearchService._perform_vector_search"
        ) as mock_vector:
            mock_vector.return_value = [
                SearchResult(
                    id="vec1",
                    title="Vector Result",
                    content="Vector search content",
                    category="tax",
                    score=0.88,
                    source="kb",
                    updated_at=datetime.now(UTC),
                )
            ]

            # Force vector-only mode
            sample_query_data["search_mode"] = SearchMode.VECTOR_ONLY

            results = await knowledge_service.retrieve_topk(sample_query_data)

            assert len(results) == 1
            assert all(r.search_method == "vector" for r in results)
            mock_vector.assert_called_once()

    @pytest.mark.asyncio
    async def test_recency_boost_calculation(self, knowledge_service):
        """Test that recency boost is correctly calculated and applied."""
        datetime.now(UTC)

        # Test documents with different ages
        old_doc = datetime.now(UTC) - timedelta(days=100)
        recent_doc = datetime.now(UTC) - timedelta(days=5)
        very_recent_doc = datetime.now(UTC) - timedelta(hours=2)

        old_boost = knowledge_service._calculate_recency_boost(old_doc)
        recent_boost = knowledge_service._calculate_recency_boost(recent_doc)
        very_recent_boost = knowledge_service._calculate_recency_boost(very_recent_doc)

        # Verify recency decay - newer documents get higher boost
        assert very_recent_boost > recent_boost > old_boost
        assert 0 <= old_boost <= 1
        assert 0 <= recent_boost <= 1
        assert 0 <= very_recent_boost <= 1

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self, knowledge_service, sample_query_data):
        """Test search with category filtering."""
        sample_query_data["filters"] = {"category": "tax"}

        with (
            patch("app.services.knowledge_search_service.KnowledgeSearchService._perform_bm25_search") as mock_bm25,
            patch(
                "app.services.knowledge_search_service.KnowledgeSearchService._perform_vector_search"
            ) as mock_vector,
        ):
            mock_bm25.return_value = []
            mock_vector.return_value = []

            await knowledge_service.retrieve_topk(sample_query_data)

            # Verify category filter is passed to search methods
            mock_bm25.assert_called_once()
            call_args = mock_bm25.call_args[0]
            assert "category" in call_args[3]  # filters parameter

            mock_vector.assert_called_once()
            vector_call_args = mock_vector.call_args[0]
            assert "category" in vector_call_args[2]  # filters parameter

    @pytest.mark.asyncio
    async def test_performance_requirements(self, knowledge_service, sample_query_data):
        """Test that search meets performance requirements."""
        import time

        with (
            patch("app.services.knowledge_search_service.KnowledgeSearchService._perform_bm25_search") as mock_bm25,
            patch(
                "app.services.knowledge_search_service.KnowledgeSearchService._perform_vector_search"
            ) as mock_vector,
        ):
            mock_bm25.return_value = []
            mock_vector.return_value = []

            start_time = time.perf_counter()
            await knowledge_service.retrieve_topk(sample_query_data)
            end_time = time.perf_counter()

            # Should complete in under 500ms for small test data
            elapsed_ms = (end_time - start_time) * 1000
            assert elapsed_ms < 500.0

    @pytest.mark.asyncio
    async def test_error_handling_vector_service_unavailable(self, mock_db_session, search_config):
        """Test graceful degradation when vector service is unavailable."""
        # Create service with unavailable vector service
        mock_vector_service = Mock()
        mock_vector_service.is_available.return_value = False

        service = KnowledgeSearchService(
            db_session=mock_db_session, vector_service=mock_vector_service, config=search_config
        )

        with patch("app.services.knowledge_search_service.KnowledgeSearchService._perform_bm25_search") as mock_bm25:
            mock_bm25.return_value = []

            query_data = {"query": "test query", "trace_id": "test"}
            results = await service.retrieve_topk(query_data)

            # Should fall back to BM25-only search
            assert isinstance(results, list)
            mock_bm25.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, knowledge_service):
        """Test handling of empty or invalid queries."""
        empty_queries = [{"query": ""}, {"query": "   "}, {"query": None}, {}]

        for query_data in empty_queries:
            results = await knowledge_service.retrieve_topk(query_data)
            assert results == []

    @pytest.mark.asyncio
    async def test_result_deduplication(self, knowledge_service, sample_query_data):
        """Test that duplicate results from BM25 and vector search are properly handled."""
        duplicate_result = {
            "id": "duplicate_1",
            "title": "Duplicate Item",
            "content": "Content...",
            "category": "tax",
            "source": "kb",
            "rank_score": 0.8,
            "relevance_score": 0.8,
            "updated_at": datetime.now(UTC),
        }

        with (
            patch("app.services.knowledge_search_service.KnowledgeSearchService._perform_bm25_search") as mock_bm25,
            patch(
                "app.services.knowledge_search_service.KnowledgeSearchService._perform_vector_search"
            ) as mock_vector,
        ):
            # Both searches return the same item
            mock_bm25.return_value = [duplicate_result]
            mock_vector.return_value = [
                SearchResult(
                    id="duplicate_1",
                    title="Duplicate Item",
                    content="Content...",
                    category="tax",
                    score=0.85,
                    source="kb",
                    updated_at=datetime.now(UTC),
                )
            ]

            results = await knowledge_service.retrieve_topk(sample_query_data)

            # Should only return one result after deduplication
            assert len(results) == 1
            result_ids = [r.id for r in results]
            assert result_ids.count("duplicate_1") == 1


class TestKnowledgeSearchConfig:
    """Test knowledge search configuration."""

    def test_config_validation(self):
        """Test that configuration validation works correctly."""
        # Valid configuration
        valid_config = KnowledgeSearchConfig(bm25_weight=0.4, vector_weight=0.4, recency_weight=0.2)
        assert valid_config.bm25_weight + valid_config.vector_weight + valid_config.recency_weight == 1.0

        # Weights should sum to 1.0
        with pytest.raises(ValueError):
            KnowledgeSearchConfig(
                bm25_weight=0.5,
                vector_weight=0.5,
                recency_weight=0.5,  # Sum > 1.0
            )

    def test_config_defaults(self):
        """Test default configuration values."""
        config = KnowledgeSearchConfig()
        assert config.bm25_weight == 0.4
        assert config.vector_weight == 0.4
        assert config.recency_weight == 0.2
        assert config.max_results == 10
        assert config.min_score_threshold == 0.1


class TestSearchResult:
    """Test SearchResult data structure."""

    def test_search_result_creation(self):
        """Test creating SearchResult with all fields."""
        result = SearchResult(
            id="test_1",
            title="Test Result",
            content="Test content",
            category="test",
            score=0.95,
            source="test_source",
            updated_at=datetime.now(UTC),
            bm25_score=0.8,
            vector_score=0.9,
            recency_score=1.0,
        )

        assert result.id == "test_1"
        assert result.score == 0.95
        assert hasattr(result, "bm25_score")
        assert hasattr(result, "vector_score")
        assert hasattr(result, "recency_score")

    def test_search_result_serialization(self):
        """Test that SearchResult can be serialized for logging."""
        result = SearchResult(
            id="test_1", title="Test Result", content="Test content", category="test", score=0.85, source="kb"
        )

        # Should be serializable to dict
        result_dict = asdict(result)
        assert result_dict["id"] == "test_1"
        assert result_dict["score"] == 0.85
        assert "title" in result_dict


# Integration tests for observability
class TestKnowledgeSearchObservability:
    """Test structured logging and observability for knowledge search."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_vector_service(self):
        """Create mock vector service."""
        vector_service = Mock()
        vector_service.is_available.return_value = True
        return vector_service

    @pytest.fixture
    def search_config(self):
        """Create search configuration for testing."""
        return KnowledgeSearchConfig()

    @pytest.fixture
    def knowledge_service(self, mock_db_session, mock_vector_service, search_config):
        """Create knowledge search service instance for testing."""
        return KnowledgeSearchService(
            db_session=mock_db_session, vector_service=mock_vector_service, config=search_config
        )

    @pytest.fixture
    def sample_query_data(self):
        """Sample query data for testing."""
        return {
            "query": "Test query for logging",
            "canonical_facts": ["test", "query"],
            "user_id": "test_user_log",
            "session_id": "session_log",
            "trace_id": "trace_789",
        }

    @pytest.mark.asyncio
    async def test_rag_step_logging(self, knowledge_service, sample_query_data):
        """Test that RAG step logging is called correctly."""
        with (
            patch("app.services.knowledge_search_service.KnowledgeSearchService._perform_bm25_search") as mock_bm25,
            patch(
                "app.services.knowledge_search_service.KnowledgeSearchService._perform_vector_search"
            ) as mock_vector,
            patch("app.observability.rag_logging.rag_step_log") as mock_log,
        ):
            mock_bm25.return_value = []
            mock_vector.return_value = []

            await knowledge_service.retrieve_topk(sample_query_data)

            # Verify rag_step_log was called with correct parameters (rag_step_timer style)
            mock_log.assert_called()
            call_args = mock_log.call_args
            assert call_args[0][0] == 39  # step
            assert (
                call_args[0][1] == "RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost"
            )  # step_id
            assert call_args[0][2] == "KBPreFetch"  # node_label
            assert call_args[1]["trace_id"] == "trace_789"
            assert "latency_ms" in call_args[1]

    @pytest.mark.asyncio
    async def test_performance_logging(self, knowledge_service, sample_query_data):
        """Test that performance metrics are logged correctly."""
        with (
            patch("app.services.knowledge_search_service.KnowledgeSearchService._perform_bm25_search") as mock_bm25,
            patch(
                "app.services.knowledge_search_service.KnowledgeSearchService._perform_vector_search"
            ) as mock_vector,
            patch("app.observability.rag_logging.rag_step_log") as mock_log,
        ):
            mock_bm25.return_value = []
            mock_vector.return_value = []

            await knowledge_service.retrieve_topk(sample_query_data)

            # Check that latency was logged
            call_args = mock_log.call_args[1]
            assert "latency_ms" in call_args
            assert isinstance(call_args["latency_ms"], int | float)
            assert call_args["latency_ms"] >= 0


# Test data fixtures for various query scenarios
@pytest.fixture(scope="module")
def test_queries():
    """Test query data for various scenarios."""
    return {
        "tax_query": {
            "query": "Aliquote IVA 2024",
            "expected_categories": ["tax", "iva"],
            "canonical_facts": ["aliquote", "iva", "2024"],
        },
        "legal_query": {
            "query": "Contratto di lavoro subordinato",
            "expected_categories": ["legal", "employment"],
            "canonical_facts": ["contratto", "lavoro", "subordinato"],
        },
        "complex_query": {
            "query": "Come calcolare le detrazioni fiscali per lavoro dipendente nel 2024",
            "expected_categories": ["tax", "employment"],
            "canonical_facts": ["calcolare", "detrazioni", "fiscali", "lavoro", "dipendente", "2024"],
        },
    }


@pytest.mark.asyncio
async def test_various_query_types(test_queries):
    """Test knowledge search for various query types."""
    from app.services.knowledge_search_service import KnowledgeSearchService

    mock_db = AsyncMock()
    mock_vector = Mock()
    mock_vector.is_available.return_value = True
    mock_vector.create_embedding.return_value = [0.1] * 384

    service = KnowledgeSearchService(db_session=mock_db, vector_service=mock_vector)

    for query_type, test_data in test_queries.items():
        query_data = {
            "query": test_data["query"],
            "canonical_facts": test_data["canonical_facts"],
            "user_id": f"test_user_{query_type}",
            "session_id": f"session_{query_type}",
            "trace_id": f"trace_{query_type}",
        }

        with (
            patch("app.services.knowledge_search_service.KnowledgeSearchService._perform_bm25_search") as mock_bm25,
            patch(
                "app.services.knowledge_search_service.KnowledgeSearchService._perform_vector_search"
            ) as mock_vector_search,
        ):
            mock_bm25.return_value = []
            mock_vector_search.return_value = []

            results = await service.retrieve_topk(query_data)

            # Should handle all query types without error
            assert isinstance(results, list)
