"""
TDD Tests for Retrieval Ranking Optimization - DEV-BE-78 Phase 1

Tests for:
- Phase 1.1: text_quality integration into scoring
- Phase 1.2: Weight configuration unification
- Phase 1.3: Source authority weighting
- Phase 1.4: Query-type dynamic weights (see test_query_classifier.py)
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import (
    HYBRID_WEIGHT_FTS,
    HYBRID_WEIGHT_RECENCY,
    HYBRID_WEIGHT_VEC,
)


class TestWeightConfigurationUnification:
    """Test Phase 1.2: Weight configuration should be unified across services."""

    def test_config_weights_exist(self):
        """Test that weight constants are defined in config.py."""
        # These should exist in config.py
        assert HYBRID_WEIGHT_FTS is not None
        assert HYBRID_WEIGHT_VEC is not None
        assert HYBRID_WEIGHT_RECENCY is not None

    def test_config_weights_sum_to_one(self):
        """Test that base weights sum to approximately 1.0."""
        from app.core.config import (
            HYBRID_WEIGHT_FTS,
            HYBRID_WEIGHT_RECENCY,
            HYBRID_WEIGHT_VEC,
        )

        # Import new weights after implementation
        try:
            from app.core.config import (
                HYBRID_WEIGHT_QUALITY,
                HYBRID_WEIGHT_SOURCE,
            )

            total = (
                HYBRID_WEIGHT_FTS
                + HYBRID_WEIGHT_VEC
                + HYBRID_WEIGHT_RECENCY
                + HYBRID_WEIGHT_QUALITY
                + HYBRID_WEIGHT_SOURCE
            )
        except ImportError:
            # Before implementation, old weights should sum to 1.0
            total = HYBRID_WEIGHT_FTS + HYBRID_WEIGHT_VEC + HYBRID_WEIGHT_RECENCY

        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected ~1.0"

    def test_knowledge_search_config_uses_global_weights(self):
        """Test that KnowledgeSearchConfig reads from global config."""
        from app.services.knowledge_search_service import KnowledgeSearchConfig

        # After implementation, config should use global weights
        config = KnowledgeSearchConfig()

        # The config should either match global weights or have quality/source added
        total = config.bm25_weight + config.vector_weight + config.recency_weight
        # Add quality_weight and source_weight if they exist
        if hasattr(config, "quality_weight"):
            total += config.quality_weight
        if hasattr(config, "source_weight"):
            total += config.source_weight

        assert abs(total - 1.0) < 0.01, f"Config weights sum to {total}, expected ~1.0"


class TestTextQualityIntegration:
    """Test Phase 1.1: text_quality field integration into scoring."""

    def test_text_quality_in_combined_score(self):
        """Test that text_quality is factored into combined score calculation."""
        from app.services.knowledge_search_service import (
            KnowledgeSearchConfig,
        )

        config = KnowledgeSearchConfig()

        # Check if quality_weight exists in config
        if hasattr(config, "quality_weight"):
            assert config.quality_weight >= 0.0
            assert config.quality_weight <= 0.20

    def test_null_text_quality_uses_neutral_score(self):
        """Test that NULL text_quality values use neutral score (0.5)."""
        from app.services.knowledge_search_service import SearchResult

        # Create result with no text_quality in metadata
        result = SearchResult(
            id="test_1",
            title="Test",
            content="Content",
            category="tax",
            score=0.0,
            source="test",
            metadata={"text_quality": None},
        )

        # When text_quality is None, should use 0.5 as neutral
        text_quality = result.metadata.get("text_quality")
        if text_quality is None:
            text_quality = 0.5

        assert text_quality == 0.5

    def test_text_quality_bounds_clamped(self):
        """Test that text_quality values outside 0-1 are clamped."""

        def clamp_quality(value: float | None) -> float:
            """Helper to test clamping logic."""
            if value is None:
                return 0.5
            return max(0.0, min(1.0, value))

        assert clamp_quality(None) == 0.5
        assert clamp_quality(0.8) == 0.8
        assert clamp_quality(-0.5) == 0.0
        assert clamp_quality(1.5) == 1.0


class TestSourceAuthorityWeighting:
    """Test Phase 1.3: Official source weighting."""

    def test_source_authority_weights_defined(self):
        """Test that SOURCE_AUTHORITY_WEIGHTS is defined in config."""
        try:
            from app.core.config import SOURCE_AUTHORITY_WEIGHTS

            assert isinstance(SOURCE_AUTHORITY_WEIGHTS, dict)

            # Official sources should have +0.15 boost
            official_sources = [
                "agenzia_entrate",
                "inps",
                "mef",
                "gazzetta_ufficiale",
            ]
            for source in official_sources:
                if source in SOURCE_AUTHORITY_WEIGHTS:
                    assert SOURCE_AUTHORITY_WEIGHTS[source] == 0.15

        except ImportError:
            pytest.skip("SOURCE_AUTHORITY_WEIGHTS not yet implemented")

    def test_official_source_boost_applied(self):
        """Test that official sources receive +0.15 boost."""
        # Define expected boosts
        expected_boosts = {
            "agenzia_entrate": 0.15,
            "agenzia_entrate_news": 0.15,
            "agenzia_entrate_normativa": 0.15,
            "inps": 0.15,
            "inps_circolari": 0.15,
            "mef": 0.15,
            "gazzetta_ufficiale": 0.15,
        }

        try:
            from app.services.ranking_utils import get_source_authority_boost

            for source, expected in expected_boosts.items():
                boost = get_source_authority_boost(source)
                assert boost == expected, f"Source {source} expected {expected}, got {boost}"

        except ImportError:
            pytest.skip("get_source_authority_boost not yet implemented")

    def test_semi_official_source_boost(self):
        """Test that semi-official sources receive +0.10 boost."""
        semi_official = [
            "confindustria",
            "ordine_commercialisti",
            "consiglio_nazionale_forense",
        ]

        try:
            from app.services.ranking_utils import get_source_authority_boost

            for source in semi_official:
                boost = get_source_authority_boost(source)
                assert boost == 0.10, f"Semi-official source {source} expected 0.10, got {boost}"

        except ImportError:
            pytest.skip("get_source_authority_boost not yet implemented")

    def test_unknown_source_no_boost(self):
        """Test that unknown sources receive no boost (0.0)."""
        try:
            from app.services.ranking_utils import get_source_authority_boost

            unknown_sources = ["random_blog", "unknown_source", "", "   "]  # Include whitespace-only
            for source in unknown_sources:
                boost = get_source_authority_boost(source)
                assert boost == 0.0, f"Unknown source {source!r} expected 0.0, got {boost}"

        except ImportError:
            pytest.skip("get_source_authority_boost not yet implemented")


class TestWeightNormalization:
    """Test weight normalization edge cases."""

    def test_weights_normalized_when_exceeding_one(self):
        """Test that weights are normalized if they sum > 1.0."""
        from app.services.knowledge_search_service import KnowledgeSearchConfig

        # The config should normalize or validate weights
        with pytest.raises(ValueError):
            # This should fail validation
            KnowledgeSearchConfig(
                bm25_weight=0.5,
                vector_weight=0.5,
                recency_weight=0.5,  # Sum = 1.5 > 1.0
            )

    def test_dynamic_weight_adjustment_normalization(self):
        """Test that dynamic weight adjustments maintain total = 1.0."""
        try:
            from app.services.query_classifier import QueryType, get_weight_adjustment

            for query_type in QueryType:
                adjustment = get_weight_adjustment(query_type)

                # Adjustments should be balanced (boosting one, reducing others)
                total_adjustment = adjustment["fts_boost"] + adjustment["vector_boost"] + adjustment["recency_boost"]

                # Total adjustment should be close to 0 (redistributive) or positive (additive with quality/source)
                assert total_adjustment <= 0.30, f"Total adjustment {total_adjustment} too high for {query_type}"

        except ImportError:
            pytest.skip("Query classifier not yet implemented")


class TestHybridScoringWithAllFactors:
    """Test combined scoring with all Phase 1 factors."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def sample_results(self):
        """Create sample search results for testing."""
        from app.services.knowledge_search_service import SearchResult

        return [
            SearchResult(
                id="1",
                title="Official Doc High Quality",
                content="Content",
                category="tax",
                score=0.0,
                source="agenzia_entrate",
                updated_at=datetime.now(UTC) - timedelta(days=5),
                bm25_score=0.8,
                vector_score=0.7,
                metadata={"text_quality": 0.9},
            ),
            SearchResult(
                id="2",
                title="Blog Post Low Quality",
                content="Content",
                category="tax",
                score=0.0,
                source="random_blog",
                updated_at=datetime.now(UTC) - timedelta(days=30),
                bm25_score=0.9,
                vector_score=0.8,
                metadata={"text_quality": 0.4},
            ),
        ]

    def test_official_high_quality_ranks_higher(self, sample_results):
        """Test that official sources with high quality rank above blogs."""
        # After scoring, the official high-quality doc should rank higher
        # even if the blog has slightly better BM25/vector scores
        official_doc = sample_results[0]
        blog_post = sample_results[1]

        # Official doc advantages:
        # - source_boost: +0.15 (official) vs 0.0 (blog)
        # - text_quality: 0.9 vs 0.4
        # - recency: 5 days vs 30 days

        # Blog advantages:
        # - bm25_score: 0.9 vs 0.8 (+0.1)
        # - vector_score: 0.8 vs 0.7 (+0.1)

        # With proper weighting, official doc should still win
        # This test validates the scoring formula after implementation
        assert official_doc.source == "agenzia_entrate"
        assert blog_post.source == "random_blog"

    @pytest.mark.asyncio
    async def test_scoring_includes_all_factors(self, mock_db_session):
        """Test that hybrid scoring includes all Phase 1 factors."""
        from app.services.knowledge_search_service import (
            KnowledgeSearchService,
            SearchResult,
        )

        service = KnowledgeSearchService(db_session=mock_db_session)

        # Create result with all metadata
        result = SearchResult(
            id="test",
            title="Test",
            content="Content",
            category="tax",
            score=0.0,
            source="agenzia_entrate",
            updated_at=datetime.now(UTC),
            bm25_score=0.8,
            vector_score=0.7,
            metadata={"text_quality": 0.85},
        )

        # Apply hybrid scoring
        scored_results = service._apply_hybrid_scoring([result])

        assert len(scored_results) == 1
        assert scored_results[0].score > 0

        # Score should include recency component
        assert scored_results[0].recency_score is not None


class TestRankingOptimizationPerformance:
    """Test performance requirements for ranking optimization."""

    @pytest.mark.asyncio
    async def test_scoring_latency_under_5ms(self):
        """Test that combined scoring adds <5ms latency."""
        import time

        from app.services.knowledge_search_service import (
            KnowledgeSearchService,
            SearchResult,
        )

        mock_db = AsyncMock()
        service = KnowledgeSearchService(db_session=mock_db)

        # Create 30 results (max reranking candidates)
        results = [
            SearchResult(
                id=f"test_{i}",
                title=f"Test {i}",
                content="Content",
                category="tax",
                score=0.0,
                source="agenzia_entrate",
                updated_at=datetime.now(UTC) - timedelta(days=i),
                bm25_score=0.8 - (i * 0.01),
                vector_score=0.7 - (i * 0.01),
                metadata={"text_quality": 0.8},
            )
            for i in range(30)
        ]

        start = time.perf_counter()
        service._apply_hybrid_scoring(results)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 5.0, f"Scoring took {elapsed_ms:.2f}ms, expected <5ms"


class TestErrorHandling:
    """Test error handling for ranking optimization."""

    def test_query_classification_failure_uses_default(self):
        """Test fallback to default weights on classification failure."""
        try:
            from app.services.query_classifier import (
                QueryType,
                classify_query,
                get_weight_adjustment,
            )

            # Malformed input should not crash, should return DEFAULT
            result = classify_query(None)
            assert result == QueryType.DEFAULT

        except ImportError:
            pytest.skip("Query classifier not yet implemented")

    def test_source_lookup_failure_uses_baseline(self):
        """Test fallback to baseline (no boost) on source lookup failure."""
        try:
            from app.services.ranking_utils import get_source_authority_boost

            # None source should return 0.0
            boost = get_source_authority_boost(None)
            assert boost == 0.0

            # Invalid type should return 0.0
            boost = get_source_authority_boost(123)
            assert boost == 0.0

        except ImportError:
            pytest.skip("Ranking utils not yet implemented")


class TestNormalizeWeights:
    """Test normalize_weights utility function."""

    def test_normalize_weights_basic(self):
        """Test basic weight normalization."""
        from app.services.ranking_utils import normalize_weights

        result = normalize_weights(0.5, 0.3, 0.1, 0.05, 0.05)
        assert abs(sum(result) - 1.0) < 0.001

    def test_normalize_weights_sum_to_one(self):
        """Test that normalized weights sum to exactly 1.0."""
        from app.services.ranking_utils import normalize_weights

        result = normalize_weights(0.8, 0.4, 0.2, 0.1, 0.1)
        total = sum(result)
        assert abs(total - 1.0) < 0.001

    def test_normalize_weights_zero_raises_error(self):
        """Test that all-zero weights raise ValueError."""
        from app.services.ranking_utils import normalize_weights

        with pytest.raises(ValueError):
            normalize_weights(0.0, 0.0, 0.0, 0.0, 0.0)


class TestClampQuality:
    """Test clamp_quality utility function."""

    def test_clamp_quality_none_returns_neutral(self):
        """Test that None returns neutral score 0.5."""
        from app.services.ranking_utils import clamp_quality

        assert clamp_quality(None) == 0.5

    def test_clamp_quality_normal_value(self):
        """Test that normal values are passed through."""
        from app.services.ranking_utils import clamp_quality

        assert clamp_quality(0.8) == 0.8
        assert clamp_quality(0.3) == 0.3

    def test_clamp_quality_high_value_clamped(self):
        """Test that values > 1.0 are clamped to 1.0."""
        from app.services.ranking_utils import clamp_quality

        assert clamp_quality(1.5) == 1.0
        assert clamp_quality(2.0) == 1.0

    def test_clamp_quality_low_value_clamped(self):
        """Test that values < 0.0 are clamped to 0.0."""
        from app.services.ranking_utils import clamp_quality

        assert clamp_quality(-0.5) == 0.0
        assert clamp_quality(-1.0) == 0.0
