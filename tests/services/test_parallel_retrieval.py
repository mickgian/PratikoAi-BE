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

        # DEV-245: Weights updated to include brave and authority
        # DEV-244: Authority increased from 0.1 to 0.2 to boost official sources
        assert SEARCH_WEIGHTS["bm25"] == 0.3
        assert SEARCH_WEIGHTS["vector"] == 0.35
        assert SEARCH_WEIGHTS["hyde"] == 0.25
        assert SEARCH_WEIGHTS["authority"] == 0.2  # DEV-244: Increased to boost official sources
        assert SEARCH_WEIGHTS["brave"] == 0.3  # DEV-245: Web search (balanced with BM25)


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


class TestRecencyBoostDateTypes:
    """DEV-242: Tests for date vs datetime type handling in recency boost."""

    def test_recency_boost_handles_date_type(self):
        """publication_date as date (not datetime) should work."""
        from datetime import date, timedelta

        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        # Recent date (within 12 months) - using date, not datetime
        recent_date = date.today() - timedelta(days=30)
        boost = service._calculate_recency_boost(recent_date)

        assert boost == 1.5  # Should get recency boost

    def test_recency_boost_handles_datetime_type(self):
        """publication_date as datetime should still work."""
        from datetime import datetime, timedelta

        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        recent_dt = datetime.now() - timedelta(days=30)
        boost = service._calculate_recency_boost(recent_dt)

        assert boost == 1.5

    def test_recency_boost_old_date_type(self):
        """Old date (>12 months) as date type should return 1.0."""
        from datetime import date, timedelta

        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        old_date = date.today() - timedelta(days=400)
        boost = service._calculate_recency_boost(old_date)

        assert boost == 1.0  # No boost for old documents


class TestSourceAuthority:
    """Tests for source authority hierarchy."""

    def test_authority_hierarchy_constant(self):
        """Test GERARCHIA_FONTI contains correct weights (DEV-242 updated values)."""
        from app.services.parallel_retrieval import GERARCHIA_FONTI

        # DEV-242 Phase 17: Increased values to prioritize laws over summaries
        assert GERARCHIA_FONTI["legge"] == 1.8  # Was 1.3
        assert GERARCHIA_FONTI["circolare"] == 1.3  # Was 1.15
        assert GERARCHIA_FONTI["faq"] == 1.0

    def test_authority_boost_legge_highest(self):
        """Test that 'legge' source type gets highest boost."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        # DEV-242 Phase 18: _get_authority_boost now takes source parameter
        legge_boost = service._get_authority_boost("legge", "")
        circolare_boost = service._get_authority_boost("circolare", "")
        faq_boost = service._get_authority_boost("faq", "")

        assert legge_boost > circolare_boost > faq_boost

    def test_authority_boost_unknown_type(self):
        """Test that unknown source type gets default boost."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        # DEV-242 Phase 18: _get_authority_boost now takes source parameter
        unknown_boost = service._get_authority_boost("unknown_type", "")

        assert unknown_boost == 1.0  # Default

    def test_source_authority_boost_gazzetta_ufficiale(self):
        """Test that gazzetta_ufficiale source gets additional boost (DEV-242 Phase 18)."""
        from app.services.parallel_retrieval import SOURCE_AUTHORITY, ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        # gazzetta_ufficiale should get 1.3x source boost
        assert SOURCE_AUTHORITY["gazzetta_ufficiale"] == 1.3

        # Combined boost: legge (1.8) * gazzetta_ufficiale (1.3) = 2.34
        combined_boost = service._get_authority_boost("legge", "gazzetta_ufficiale")
        assert combined_boost == 1.8 * 1.3  # 2.34

        # Summary sources should get penalty
        assert SOURCE_AUTHORITY["ministero_economia_documenti"] == 0.9

    def test_source_authority_combined_boost(self):
        """Test that type and source boosts are multiplicative (DEV-242 Phase 18)."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        # Full law from Gazzetta Ufficiale: legge (1.8) * gazzetta (1.3) = 2.34
        gazzetta_legge = service._get_authority_boost("legge", "gazzetta_ufficiale")

        # Summary from MEF: unknown type (1.0) * mef (0.9) = 0.9
        mef_summary = service._get_authority_boost("", "ministero_economia_documenti")

        # Full law should rank much higher than summary
        assert gazzetta_legge > mef_summary
        assert gazzetta_legge / mef_summary > 2.5  # At least 2.5x higher


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

    def test_top_k_reserves_slots_for_official_sources(self):
        """DEV-244: Test that official sources get reserved slots in top-K."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        # Create docs: 7 news articles with high scores, 3 official with lower scores
        docs = [
            # News articles with higher scores (should normally fill top-10)
            {"document_id": "news_1", "rrf_score": 0.95, "source": "ministero_lavoro_news"},
            {"document_id": "news_2", "rrf_score": 0.90, "source": "ministero_lavoro_news"},
            {"document_id": "news_3", "rrf_score": 0.85, "source": "ministero_lavoro_news"},
            {"document_id": "news_4", "rrf_score": 0.80, "source": "ministero_lavoro_news"},
            {"document_id": "news_5", "rrf_score": 0.75, "source": "ministero_lavoro_news"},
            {"document_id": "news_6", "rrf_score": 0.70, "source": "ministero_lavoro_news"},
            {"document_id": "news_7", "rrf_score": 0.65, "source": "ministero_lavoro_news"},
            # Official sources with lower scores
            {"document_id": "gazzetta_1", "rrf_score": 0.50, "source": "gazzetta_ufficiale"},
            {"document_id": "ade_1", "rrf_score": 0.45, "source": "agenzia_entrate"},
            {"document_id": "inps_1", "rrf_score": 0.40, "source": "inps"},
        ]

        top_docs = service._get_top_k(docs, k=10)

        # All 3 official sources should be in results despite lower scores
        official_ids = {
            d["document_id"] for d in top_docs if d["source"] in {"gazzetta_ufficiale", "agenzia_entrate", "inps"}
        }
        assert "gazzetta_1" in official_ids
        assert "ade_1" in official_ids
        assert "inps_1" in official_ids
        assert len(top_docs) == 10

    def test_top_k_official_sources_respect_max_slots(self):
        """DEV-244: Test that no more than MAX_RESERVED_SLOTS are reserved for official sources."""
        from app.services.parallel_retrieval import (
            MAX_RESERVED_SLOTS,
            ParallelRetrievalService,
        )

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        # Create 4 different official source TYPES (more than MAX_RESERVED_SLOTS=3)
        # and 5 news sources
        docs = [
            {"document_id": "gazzetta_1", "rrf_score": 0.50, "source": "gazzetta_ufficiale"},
            {"document_id": "ade_1", "rrf_score": 0.45, "source": "agenzia_entrate"},
            {"document_id": "inps_1", "rrf_score": 0.40, "source": "inps"},
            {"document_id": "cass_1", "rrf_score": 0.35, "source": "corte_cassazione"},
            # News with higher scores
            {"document_id": "news_1", "rrf_score": 0.90, "source": "ministero_lavoro_news"},
            {"document_id": "news_2", "rrf_score": 0.85, "source": "ministero_lavoro_news"},
            {"document_id": "news_3", "rrf_score": 0.80, "source": "ministero_lavoro_news"},
            {"document_id": "news_4", "rrf_score": 0.75, "source": "ministero_lavoro_news"},
            {"document_id": "news_5", "rrf_score": 0.70, "source": "ministero_lavoro_news"},
        ]

        top_docs = service._get_top_k(docs, k=5)

        # Only top 3 official source TYPES should get reserved slots
        official_in_results = [
            d
            for d in top_docs
            if d["source"]
            in {"gazzetta_ufficiale", "agenzia_entrate", "inps", "corte_cassazione", "agenzia_entrate_riscossione"}
        ]
        assert len(official_in_results) == MAX_RESERVED_SLOTS  # 3
        # Remaining slots go to highest-scoring news
        news_in_results = [d for d in top_docs if d["source"] == "ministero_lavoro_news"]
        assert len(news_in_results) == 2

    def test_top_k_ensures_source_diversity(self):
        """DEV-244: Ensure diverse official sources, not multiple from same source type."""
        from app.services.parallel_retrieval import ParallelRetrievalService

        service = ParallelRetrievalService.__new__(ParallelRetrievalService)

        # Multiple Gazzetta chunks with HIGH scores that would normally crowd out ADeR
        docs = [
            {"document_id": "gaz_1", "rrf_score": 0.50, "source": "gazzetta_ufficiale"},
            {"document_id": "gaz_2", "rrf_score": 0.48, "source": "gazzetta_ufficiale"},
            {"document_id": "gaz_3", "rrf_score": 0.46, "source": "gazzetta_ufficiale"},
            # Single ADeR chunk with LOWER score
            {"document_id": "ader_1", "rrf_score": 0.40, "source": "agenzia_entrate_riscossione"},
            # News with highest score
            {"document_id": "news_1", "rrf_score": 0.90, "source": "ministero_lavoro_news"},
        ]

        top_docs = service._get_top_k(docs, k=5)

        # ADeR MUST be included (diversity) - this was the bug we fixed!
        sources_in_results = {d["source"] for d in top_docs}
        assert "agenzia_entrate_riscossione" in sources_in_results, "ADeR must be included to ensure source diversity"
        assert "gazzetta_ufficiale" in sources_in_results

        # Only 1 Gazzetta chunk (best one, gaz_1), not all 3
        gaz_count = sum(1 for d in top_docs if d["source"] == "gazzetta_ufficiale")
        assert gaz_count == 1, f"Expected 1 Gazzetta chunk (best one), got {gaz_count}"

        # The best Gazzetta should be gaz_1 (score 0.50)
        gaz_docs = [d for d in top_docs if d["source"] == "gazzetta_ufficiale"]
        assert gaz_docs[0]["document_id"] == "gaz_1"


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


class TestDocumentReferenceFiltering:
    """ADR-022: Tests for document_references-based search filtering."""

    @pytest.mark.asyncio
    async def test_bm25_uses_document_references_filter(self):
        """ADR-022: BM25 search should use document_references as title_patterns."""
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService
        from app.services.search_service import SearchResult

        # Create mock search service
        mock_search_service = AsyncMock()

        # Mock search result
        mock_result = MagicMock(spec=SearchResult)
        mock_result.id = "doc_1"
        mock_result.knowledge_item_id = 123
        mock_result.content = "Legge 199/2025 content about rottamazione"
        mock_result.rank_score = 0.9
        mock_result.category = "legge"
        mock_result.title = "LEGGE 30 dicembre 2025, n. 199"
        mock_result.source = "gazzetta_ufficiale"
        mock_result.publication_date = None

        mock_search_service.search.return_value = [mock_result]

        service = ParallelRetrievalService(
            search_service=mock_search_service,
            embedding_service=None,
        )

        # Query with document_references
        queries = QueryVariants(
            bm25_query="rottamazione quinquies definizione agevolata",
            vector_query="test",
            entity_query="test",
            original_query="Parlami della rottamazione quinquies",
            document_references=["Legge 199/2025", "LEGGE 30 dicembre 2025, n. 199"],
        )

        # Execute search
        await service._search_bm25(queries)

        # Verify search was called with title_patterns
        mock_search_service.search.assert_called()
        call_kwargs = mock_search_service.search.call_args.kwargs
        assert "title_patterns" in call_kwargs
        # DEV-242 Phase 9: Patterns are now normalized to improve matching
        # Original patterns are preserved, plus normalized variants added
        patterns = call_kwargs["title_patterns"]
        assert "Legge 199/2025" in patterns  # Original preserved
        assert "LEGGE 30 dicembre 2025, n. 199" in patterns  # Original preserved
        assert "n. 199" in patterns  # Normalized from "Legge 199/2025"

    @pytest.mark.asyncio
    async def test_bm25_falls_back_when_filter_returns_empty(self):
        """ADR-022: BM25 should fall back to regular search when document filter finds nothing."""
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService
        from app.services.search_service import SearchResult

        mock_search_service = AsyncMock()

        # First call (with filter) returns empty, second call (without filter) returns results
        mock_result = MagicMock(spec=SearchResult)
        mock_result.id = "doc_fallback"
        mock_result.knowledge_item_id = 456
        mock_result.content = "Fallback result content"
        mock_result.rank_score = 0.7
        mock_result.category = "circolare"
        mock_result.title = "Some other document"
        mock_result.source = "other_source"
        mock_result.publication_date = None

        # First call returns empty, second returns result
        mock_search_service.search.side_effect = [[], [mock_result]]

        service = ParallelRetrievalService(
            search_service=mock_search_service,
            embedding_service=None,
        )

        queries = QueryVariants(
            bm25_query="test query",
            vector_query="test",
            entity_query="test",
            original_query="test",
            document_references=["NonExistent/2025"],  # Filter that won't match anything
        )

        result = await service._search_bm25(queries)

        # Should have called search twice (filtered + fallback)
        assert mock_search_service.search.call_count == 2

        # First call should have title_patterns, second should not
        first_call = mock_search_service.search.call_args_list[0]
        second_call = mock_search_service.search.call_args_list[1]

        assert first_call.kwargs.get("title_patterns") == ["NonExistent/2025"]
        assert second_call.kwargs.get("title_patterns") is None

        # Should return fallback results
        assert len(result) == 1
        assert result[0]["document_id"] == "doc_fallback"  # DEV-242 Phase 27: Now uses chunk_id

    @pytest.mark.asyncio
    async def test_bm25_no_filter_when_document_references_none(self):
        """ADR-022: BM25 should not use filter when document_references is None."""
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService
        from app.services.search_service import SearchResult

        mock_search_service = AsyncMock()

        mock_result = MagicMock(spec=SearchResult)
        mock_result.id = "doc_regular"
        mock_result.knowledge_item_id = 789
        mock_result.content = "Regular search content"
        mock_result.rank_score = 0.8
        mock_result.category = "faq"
        mock_result.title = "FAQ Document"
        mock_result.source = "faq_source"
        mock_result.publication_date = None

        mock_search_service.search.return_value = [mock_result]

        service = ParallelRetrievalService(
            search_service=mock_search_service,
            embedding_service=None,
        )

        queries = QueryVariants(
            bm25_query="test query",
            vector_query="test",
            entity_query="test",
            original_query="test",
            document_references=None,  # No document references
        )

        await service._search_bm25(queries)

        # Should call search only once, without title_patterns
        assert mock_search_service.search.call_count == 1
        call_kwargs = mock_search_service.search.call_args.kwargs
        assert call_kwargs.get("title_patterns") is None

    @pytest.mark.asyncio
    async def test_bm25_no_filter_when_document_references_empty(self):
        """ADR-022: BM25 should not use filter when document_references is empty list."""
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService
        from app.services.search_service import SearchResult

        mock_search_service = AsyncMock()
        mock_result = MagicMock(spec=SearchResult)
        mock_result.id = "doc_1"
        mock_result.knowledge_item_id = 111
        mock_result.content = "Content"
        mock_result.rank_score = 0.5
        mock_result.category = "guida"
        mock_result.title = "Guide"
        mock_result.source = "source"
        mock_result.publication_date = None

        mock_search_service.search.return_value = [mock_result]

        service = ParallelRetrievalService(
            search_service=mock_search_service,
            embedding_service=None,
        )

        queries = QueryVariants(
            bm25_query="test query",
            vector_query="test",
            entity_query="test",
            original_query="test",
            document_references=[],  # Empty list (generic query)
        )

        await service._search_bm25(queries)

        # Should call search only once, without title_patterns
        assert mock_search_service.search.call_count == 1
        call_kwargs = mock_search_service.search.call_args.kwargs
        assert call_kwargs.get("title_patterns") is None


class TestNormalizeDocumentPatterns:
    """Tests for DEV-242 Phase 9: Document pattern normalization."""

    def test_normalizes_legge_slash_year_pattern(self):
        """Test normalizing 'Legge 199/2025' to include 'n. 199'."""
        from app.services.parallel_retrieval import _normalize_document_patterns

        refs = ["Legge 199/2025"]
        result = _normalize_document_patterns(refs)

        assert "Legge 199/2025" in result  # Original preserved
        assert "n. 199" in result  # Normalized pattern
        assert "199" in result  # Number-only fallback

    def test_normalizes_decreto_slash_year_pattern(self):
        """Test normalizing 'DL 145/2023' to include 'n. 145'."""
        from app.services.parallel_retrieval import _normalize_document_patterns

        refs = ["DL 145/2023"]
        result = _normalize_document_patterns(refs)

        assert "DL 145/2023" in result
        assert "n. 145" in result
        assert "145" in result

    def test_preserves_n_pattern(self):
        """Test that 'n. 199' patterns are preserved."""
        from app.services.parallel_retrieval import _normalize_document_patterns

        refs = ["n. 199", "Legge di Bilancio 2026"]
        result = _normalize_document_patterns(refs)

        assert "n. 199" in result
        assert "199" in result  # Number extracted
        assert "Legge di Bilancio 2026" in result

    def test_handles_empty_input(self):
        """Test that empty input returns empty list."""
        from app.services.parallel_retrieval import _normalize_document_patterns

        assert _normalize_document_patterns(None) == []
        assert _normalize_document_patterns([]) == []

    def test_removes_duplicates(self):
        """Test that duplicate patterns are removed."""
        from app.services.parallel_retrieval import _normalize_document_patterns

        refs = ["Legge 199/2025", "n. 199"]  # Both produce "199"
        result = _normalize_document_patterns(refs)

        # Count occurrences of "199"
        assert result.count("199") == 1
        assert result.count("n. 199") == 1

    def test_real_world_rottamazione_quinquies_patterns(self):
        """Test patterns that should match LEGGE 30 dicembre 2025, n. 199."""
        from app.services.parallel_retrieval import _normalize_document_patterns

        # What the LLM might generate
        refs = ["Legge 199/2025", "Legge di Bilancio 2026"]
        result = _normalize_document_patterns(refs)

        # These patterns should match "LEGGE 30 dicembre 2025, n. 199"
        assert "n. 199" in result  # Matches "n. 199" in title
        assert "199" in result  # Matches "199" anywhere


class TestSemanticExpansionsInBM25:
    """DEV-242 Phase 16: Tests for semantic_expansions query expansion in BM25."""

    @pytest.mark.asyncio
    async def test_bm25_expands_query_with_semantic_expansions(self):
        """DEV-242: BM25 search should expand query with semantic_expansions."""
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService
        from app.services.search_service import SearchResult

        mock_search_service = AsyncMock()

        mock_result = MagicMock(spec=SearchResult)
        mock_result.id = "doc_1"
        mock_result.knowledge_item_id = 2080
        mock_result.content = "Pace fiscale 54 rate bimestrali"
        mock_result.rank_score = 0.9
        mock_result.category = "legge"
        mock_result.title = "Principali misure della legge di bilancio 2026"
        mock_result.source = "gazzetta_ufficiale"
        mock_result.publication_date = None

        mock_search_service.search.return_value = [mock_result]

        service = ParallelRetrievalService(
            search_service=mock_search_service,
            embedding_service=None,
        )

        # Query with semantic_expansions
        queries = QueryVariants(
            bm25_query="rottamazione quinquies definizione",
            vector_query="test",
            entity_query="test",
            original_query="Parlami della rottamazione quinquies",
            document_references=["n. 199", "Legge di Bilancio 2026"],
            semantic_expansions=["pace fiscale", "pacificazione fiscale", "definizione agevolata"],
        )

        await service._search_bm25(queries)

        # Verify search was called with expanded query
        mock_search_service.search.assert_called()
        call_kwargs = mock_search_service.search.call_args.kwargs

        # The query should include the semantic expansions
        query_arg = call_kwargs.get("query")
        assert "pace fiscale" in query_arg
        assert "pacificazione fiscale" in query_arg
        assert "definizione agevolata" in query_arg

    @pytest.mark.asyncio
    async def test_bm25_no_expansion_when_semantic_expansions_none(self):
        """DEV-242: BM25 should not modify query when semantic_expansions is None."""
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService
        from app.services.search_service import SearchResult

        mock_search_service = AsyncMock()

        mock_result = MagicMock(spec=SearchResult)
        mock_result.id = "doc_1"
        mock_result.knowledge_item_id = 123
        mock_result.content = "Content"
        mock_result.rank_score = 0.8
        mock_result.category = "faq"
        mock_result.title = "FAQ"
        mock_result.source = "source"
        mock_result.publication_date = None

        mock_search_service.search.return_value = [mock_result]

        service = ParallelRetrievalService(
            search_service=mock_search_service,
            embedding_service=None,
        )

        queries = QueryVariants(
            bm25_query="test bm25 query",
            vector_query="test",
            entity_query="test",
            original_query="test",
            semantic_expansions=None,  # No semantic expansions
        )

        await service._search_bm25(queries)

        # Query should be unchanged
        call_kwargs = mock_search_service.search.call_args.kwargs
        query_arg = call_kwargs.get("query")
        assert query_arg == "test bm25 query"

    @pytest.mark.asyncio
    async def test_bm25_no_expansion_when_semantic_expansions_empty(self):
        """DEV-242: BM25 should not modify query when semantic_expansions is empty."""
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService
        from app.services.search_service import SearchResult

        mock_search_service = AsyncMock()

        mock_result = MagicMock(spec=SearchResult)
        mock_result.id = "doc_1"
        mock_result.knowledge_item_id = 123
        mock_result.content = "Content"
        mock_result.rank_score = 0.8
        mock_result.category = "faq"
        mock_result.title = "FAQ"
        mock_result.source = "source"
        mock_result.publication_date = None

        mock_search_service.search.return_value = [mock_result]

        service = ParallelRetrievalService(
            search_service=mock_search_service,
            embedding_service=None,
        )

        queries = QueryVariants(
            bm25_query="test bm25 query",
            vector_query="test",
            entity_query="test",
            original_query="test",
            semantic_expansions=[],  # Empty list
        )

        await service._search_bm25(queries)

        # Query should be unchanged
        call_kwargs = mock_search_service.search.call_args.kwargs
        query_arg = call_kwargs.get("query")
        assert query_arg == "test bm25 query"

    @pytest.mark.asyncio
    async def test_semantic_expansions_combined_with_document_references(self):
        """DEV-242: Both semantic_expansions and document_references should work together."""
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService
        from app.services.search_service import SearchResult

        mock_search_service = AsyncMock()

        mock_result = MagicMock(spec=SearchResult)
        mock_result.id = "doc_1"
        mock_result.knowledge_item_id = 2080
        mock_result.content = "Pace fiscale 54 rate bimestrali"
        mock_result.rank_score = 0.95
        mock_result.category = "legge"
        mock_result.title = "Principali misure della legge di bilancio 2026"
        mock_result.source = "gazzetta_ufficiale"
        mock_result.publication_date = None

        mock_search_service.search.return_value = [mock_result]

        service = ParallelRetrievalService(
            search_service=mock_search_service,
            embedding_service=None,
        )

        # Query with BOTH semantic_expansions AND document_references
        queries = QueryVariants(
            bm25_query="rottamazione quinquies",
            vector_query="test",
            entity_query="test",
            original_query="Parlami della rottamazione quinquies",
            document_references=["n. 199", "Legge di Bilancio 2026"],
            semantic_expansions=["pace fiscale", "pacificazione fiscale"],
        )

        await service._search_bm25(queries)

        # Both features should be used
        call_kwargs = mock_search_service.search.call_args.kwargs

        # Query should have semantic expansions
        query_arg = call_kwargs.get("query")
        assert "pace fiscale" in query_arg
        assert "pacificazione fiscale" in query_arg

        # Title patterns should also be present
        assert "title_patterns" in call_kwargs
        patterns = call_kwargs["title_patterns"]
        assert "n. 199" in patterns or "Legge di Bilancio 2026" in patterns


class TestBM25OrFallback:
    """DEV-244: Tests for OR fallback when AND search returns 0 results."""

    @pytest.mark.asyncio
    async def test_bm25_uses_or_fallback_when_and_returns_zero(self):
        """DEV-244: BM25 should try OR fallback when AND search returns 0 results."""
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService
        from app.services.search_service import SearchResult

        mock_search_service = AsyncMock()

        # Mock result for OR fallback
        mock_result = MagicMock(spec=SearchResult)
        mock_result.id = "doc_from_or_fallback"
        mock_result.knowledge_item_id = 999
        mock_result.content = "Content found via OR fallback"
        mock_result.rank_score = 0.7
        mock_result.category = "legge"
        mock_result.title = "LEGGE 30 dicembre 2025, n. 199"
        mock_result.source = "gazzetta_ufficiale"
        mock_result.publication_date = None
        mock_result.source_url = "https://gazzettaufficiale.it/example"

        # AND search returns empty, OR fallback returns results
        mock_search_service.search.return_value = []
        mock_search_service.search_with_or_fallback.return_value = [mock_result]

        service = ParallelRetrievalService(
            search_service=mock_search_service,
            embedding_service=None,
        )

        # Long query that strict AND matching won't find
        queries = QueryVariants(
            bm25_query="scadenza presentare domanda definizione agevolata 2026 pace fiscale pacificazione",
            vector_query="test",
            entity_query="test",
            original_query="Qual è la scadenza per presentare la domanda per la definizione agevolata 2026?",
            document_references=None,
        )

        result = await service._search_bm25(queries)

        # Both search methods should be called
        mock_search_service.search.assert_called_once()
        mock_search_service.search_with_or_fallback.assert_called_once()

        # Should return results from OR fallback
        assert len(result) == 1
        assert result[0]["document_id"] == "doc_from_or_fallback"

    @pytest.mark.asyncio
    async def test_bm25_skips_or_fallback_when_and_returns_results(self):
        """DEV-244: BM25 should NOT call OR fallback when AND search returns results."""
        from app.services.multi_query_generator import QueryVariants
        from app.services.parallel_retrieval import ParallelRetrievalService
        from app.services.search_service import SearchResult

        mock_search_service = AsyncMock()

        # Mock result for AND search
        mock_result = MagicMock(spec=SearchResult)
        mock_result.id = "doc_from_and"
        mock_result.knowledge_item_id = 100
        mock_result.content = "Content found via AND search"
        mock_result.rank_score = 0.9
        mock_result.category = "legge"
        mock_result.title = "Test Document"
        mock_result.source = "gazzetta_ufficiale"
        mock_result.publication_date = None
        mock_result.source_url = None

        # AND search returns results
        mock_search_service.search.return_value = [mock_result]

        service = ParallelRetrievalService(
            search_service=mock_search_service,
            embedding_service=None,
        )

        queries = QueryVariants(
            bm25_query="short query",
            vector_query="test",
            entity_query="test",
            original_query="short query",
        )

        result = await service._search_bm25(queries)

        # Only AND search should be called
        mock_search_service.search.assert_called_once()
        mock_search_service.search_with_or_fallback.assert_not_called()

        # Should return results from AND search
        assert len(result) == 1
        assert result[0]["document_id"] == "doc_from_and"
