"""TDD Tests for DEV-190: ParallelRetrievalService.

Tests for parallel hybrid retrieval with RRF fusion per Section 13.7.
"""

import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRetrievalResultSchema:
    """Tests for RetrievalResult and RankedDocument schemas."""

    def test_ranked_document_creation(self):
        """Test creating RankedDocument with all fields."""
        from app.services.parallel_retrieval import RankedDocument

        doc = RankedDocument(
            document_id="doc_123",
            content="Contenuto del documento...",
            score=0.85,
            rrf_score=0.042,
            source_type="legge",
            source_name="Legge 104/1992",
            published_date=datetime(2024, 6, 15),
            metadata={"articolo": "Art. 3"},
        )

        assert doc.document_id == "doc_123"
        assert doc.score == 0.85
        assert doc.rrf_score == 0.042
        assert doc.source_type == "legge"

    def test_retrieval_result_creation(self):
        """Test creating RetrievalResult with documents."""
        from app.services.parallel_retrieval import RankedDocument, RetrievalResult

        docs = [
            RankedDocument(
                document_id="doc_1",
                content="Content 1",
                score=0.9,
                rrf_score=0.05,
                source_type="legge",
                source_name="Legge 1",
                published_date=datetime.now(),
                metadata={},
            ),
            RankedDocument(
                document_id="doc_2",
                content="Content 2",
                score=0.8,
                rrf_score=0.04,
                source_type="circolare",
                source_name="Circolare 1",
                published_date=datetime.now(),
                metadata={},
            ),
        ]

        result = RetrievalResult(
            documents=docs,
            total_found=100,
            search_time_ms=150.5,
        )

        assert len(result.documents) == 2
        assert result.total_found == 100
        assert result.search_time_ms == 150.5


class TestRRFFusion:
    """Tests for RRF (Reciprocal Rank Fusion) implementation."""

    @pytest.fixture
    def mock_search_service(self):
        """Create a mock search service."""
        service = MagicMock()
        return service

    def test_rrf_formula_k60(self):
        """Test RRF uses k=60 constant."""
        from app.services.parallel_retrieval import RRF_K

        assert RRF_K == 60

    def test_rrf_combines_all_searches(self):
        """Test that RRF combines results from all search types."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        # Mock results from different searches
        bm25_results = [
            {"document_id": "doc_1", "rank": 1},
            {"document_id": "doc_2", "rank": 2},
        ]
        vector_results = [
            {"document_id": "doc_2", "rank": 1},
            {"document_id": "doc_3", "rank": 2},
        ]
        hyde_results = [
            {"document_id": "doc_1", "rank": 1},
            {"document_id": "doc_3", "rank": 2},
        ]

        # RRF should combine and rank
        combined = service._rrf_fusion([bm25_results, vector_results, hyde_results])

        # doc_1 appears in BM25 (rank 1) and HyDE (rank 1)
        # doc_2 appears in BM25 (rank 2) and Vector (rank 1)
        # doc_3 appears in Vector (rank 2) and HyDE (rank 2)
        assert len(combined) == 3
        # All documents should be present
        doc_ids = [d["document_id"] for d in combined]
        assert "doc_1" in doc_ids
        assert "doc_2" in doc_ids
        assert "doc_3" in doc_ids

    def test_rrf_weights_applied(self):
        """Test that search type weights are applied correctly."""
        from app.services.parallel_retrieval import SEARCH_WEIGHTS

        # Weights per Section 13.7.2
        assert SEARCH_WEIGHTS["bm25"] == 0.3
        assert SEARCH_WEIGHTS["vector"] == 0.4
        assert SEARCH_WEIGHTS["hyde"] == 0.3


class TestRecencyBoost:
    """Tests for recency boost functionality."""

    def test_recency_boost_recent_doc(self):
        """Test that docs <12 months get +50% boost."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        # Recent document (6 months old)
        recent_date = datetime.now() - timedelta(days=180)
        boost = service._calculate_recency_boost(recent_date)

        assert boost == 1.5  # +50%

    def test_recency_boost_old_doc(self):
        """Test that docs >12 months get no boost."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        # Old document (18 months old)
        old_date = datetime.now() - timedelta(days=540)
        boost = service._calculate_recency_boost(old_date)

        assert boost == 1.0  # No boost

    def test_recency_boost_just_under_12_months(self):
        """Test edge case just under 12 months."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        # Just under 12 months ago (364 days)
        edge_date = datetime.now() - timedelta(days=364)
        boost = service._calculate_recency_boost(edge_date)

        # Just under 12 months should get boost
        assert boost == 1.5


class TestSourceAuthority:
    """Tests for source authority hierarchy."""

    def test_authority_hierarchy_constant(self):
        """Test GERARCHIA_FONTI contains correct weights."""
        from app.services.parallel_retrieval import GERARCHIA_FONTI

        assert GERARCHIA_FONTI["legge"] == 1.3
        assert GERARCHIA_FONTI["circolare"] == 1.15
        assert GERARCHIA_FONTI["faq"] == 1.0

    def test_authority_boost_legge_highest(self):
        """Test that 'legge' source type gets highest boost."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        legge_boost = service._get_authority_boost("legge")
        circolare_boost = service._get_authority_boost("circolare")
        faq_boost = service._get_authority_boost("faq")

        assert legge_boost > circolare_boost > faq_boost

    def test_authority_boost_unknown_type(self):
        """Test that unknown source type gets default boost."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        unknown_boost = service._get_authority_boost("unknown_type")

        assert unknown_boost == 1.0  # Default


class TestDeduplication:
    """Tests for document deduplication."""

    def test_deduplication_by_document_id(self):
        """Test that duplicate documents are removed by document_id."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        docs = [
            {"document_id": "doc_1", "score": 0.9},
            {"document_id": "doc_2", "score": 0.8},
            {"document_id": "doc_1", "score": 0.7},  # Duplicate
            {"document_id": "doc_3", "score": 0.6},
        ]

        deduped = service._deduplicate(docs)

        assert len(deduped) == 3
        doc_ids = [d["document_id"] for d in deduped]
        assert doc_ids.count("doc_1") == 1

    def test_deduplication_keeps_highest_score(self):
        """Test that deduplication keeps the highest scoring version."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        docs = [
            {"document_id": "doc_1", "score": 0.7},
            {"document_id": "doc_1", "score": 0.9},  # Higher score
            {"document_id": "doc_1", "score": 0.8},
        ]

        deduped = service._deduplicate(docs)

        assert len(deduped) == 1
        assert deduped[0]["score"] == 0.9


class TestTopKResults:
    """Tests for top-K result limiting."""

    def test_top_10_returned(self):
        """Test that only top 10 documents are returned."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        # Create 15 documents
        docs = [{"document_id": f"doc_{i}", "rrf_score": 1.0 - (i * 0.05)} for i in range(15)]

        top_docs = service._get_top_k(docs, k=10)

        assert len(top_docs) == 10

    def test_top_k_sorted_by_score(self):
        """Test that top-K results are sorted by score descending."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        docs = [
            {"document_id": "doc_3", "rrf_score": 0.5},
            {"document_id": "doc_1", "rrf_score": 0.9},
            {"document_id": "doc_2", "rrf_score": 0.7},
        ]

        top_docs = service._get_top_k(docs, k=3)

        scores = [d["rrf_score"] for d in top_docs]
        assert scores == sorted(scores, reverse=True)


class TestMetadataPreservation:
    """Tests for metadata preservation through retrieval."""

    def test_metadata_preserved_in_result(self):
        """Test that document metadata is preserved in results."""
        from app.services.parallel_retrieval import RankedDocument

        metadata = {
            "articolo": "Art. 3",
            "comma": "comma 1",
            "section": "Sezione A",
        }

        doc = RankedDocument(
            document_id="doc_1",
            content="Content",
            score=0.9,
            rrf_score=0.05,
            source_type="legge",
            source_name="Legge 104",
            published_date=datetime.now(),
            metadata=metadata,
        )

        assert doc.metadata == metadata
        assert doc.metadata["articolo"] == "Art. 3"


class TestParallelExecution:
    """Tests for parallel search execution."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        return config

    @pytest.mark.asyncio
    async def test_parallel_searches_executed(self, mock_config):
        """Test that all searches are executed in parallel."""
        from app.services.hyde_generator import HyDEResult
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService(
            search_service=MagicMock(),
            embedding_service=MagicMock(),
        )

        queries = QueryVariants(
            bm25_query="keyword query",
            vector_query="semantic query",
            entity_query="entity query",
            original_query="original",
        )

        hyde = HyDEResult(
            hypothetical_document="Hypothetical doc content",
            word_count=100,
            skipped=False,
            skip_reason=None,
        )

        # Mock the search methods
        with (
            patch.object(service, "_search_bm25", new_callable=AsyncMock) as mock_bm25,
            patch.object(service, "_search_vector", new_callable=AsyncMock) as mock_vector,
            patch.object(service, "_search_hyde", new_callable=AsyncMock) as mock_hyde,
        ):
            mock_bm25.return_value = []
            mock_vector.return_value = []
            mock_hyde.return_value = []

            await service._execute_parallel_searches(queries, hyde)

            # All search methods should be called
            assert mock_bm25.called
            assert mock_vector.called
            assert mock_hyde.called


class TestFullRetrievalFlow:
    """Integration tests for full retrieval flow."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        search_service = MagicMock()
        embedding_service = MagicMock()
        return search_service, embedding_service

    @pytest.mark.asyncio
    async def test_retrieve_returns_retrieval_result(self, mock_services):
        """Test that retrieve() returns RetrievalResult."""
        from app.services.hyde_generator import HyDEResult
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService, RetrievalResult

        search_service, embedding_service = mock_services
        service = ParallelRetrievalService(
            search_service=search_service,
            embedding_service=embedding_service,
        )

        queries = QueryVariants(
            bm25_query="test",
            vector_query="test semantic",
            entity_query="test entity",
            original_query="test",
        )

        hyde = HyDEResult(
            hypothetical_document="",
            word_count=0,
            skipped=True,
            skip_reason="test",
        )

        with (
            patch.object(service, "_execute_parallel_searches", new_callable=AsyncMock) as mock_search,
            patch.object(service, "_rrf_fusion") as mock_fusion,
            patch.object(service, "_apply_boosts") as mock_boosts,
            patch.object(service, "_deduplicate") as mock_dedup,
            patch.object(service, "_get_top_k") as mock_topk,
            patch.object(service, "_to_ranked_documents") as mock_convert,
        ):
            mock_search.return_value = [[], [], []]
            mock_fusion.return_value = []
            mock_boosts.return_value = []
            mock_dedup.return_value = []
            mock_topk.return_value = []
            mock_convert.return_value = []

            result = await service.retrieve(queries, hyde)

            assert isinstance(result, RetrievalResult)

    @pytest.mark.asyncio
    async def test_retrieve_handles_empty_results(self, mock_services):
        """Test that retrieve handles no results gracefully."""
        from app.services.hyde_generator import HyDEResult
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService

        search_service, embedding_service = mock_services
        service = ParallelRetrievalService(
            search_service=search_service,
            embedding_service=embedding_service,
        )

        queries = QueryVariants(
            bm25_query="nonexistent",
            vector_query="nonexistent semantic",
            entity_query="nonexistent entity",
            original_query="nonexistent",
        )

        hyde = HyDEResult(
            hypothetical_document="",
            word_count=0,
            skipped=True,
            skip_reason="test",
        )

        with patch.object(service, "_execute_parallel_searches", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [[], [], []]

            result = await service.retrieve(queries, hyde)

            assert len(result.documents) == 0
            assert result.total_found == 0


class TestPerformance:
    """Performance requirement tests."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        search_service = MagicMock()
        embedding_service = MagicMock()
        return search_service, embedding_service

    @pytest.mark.asyncio
    async def test_retrieval_latency_under_450ms_mocked(self, mock_services):
        """Test that retrieval completes under 450ms (mocked)."""
        from app.services.hyde_generator import HyDEResult
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService

        search_service, embedding_service = mock_services
        service = ParallelRetrievalService(
            search_service=search_service,
            embedding_service=embedding_service,
        )

        queries = QueryVariants(
            bm25_query="test",
            vector_query="test",
            entity_query="test",
            original_query="test",
        )

        hyde = HyDEResult(
            hypothetical_document="",
            word_count=0,
            skipped=True,
            skip_reason="test",
        )

        with patch.object(service, "_execute_parallel_searches", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [[], [], []]

            start = time.perf_counter()
            await service.retrieve(queries, hyde)
            elapsed = (time.perf_counter() - start) * 1000

        # With mocked services, should be very fast
        assert elapsed < 450, f"Retrieval took {elapsed:.1f}ms, should be <450ms"
