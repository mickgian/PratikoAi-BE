"""Tests for query normalization models."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models.query_normalization import (
    QueryNormalizationLog,
    QueryNormalizationPattern,
    QueryNormalizationStats,
)


class TestQueryNormalizationLog:
    """Test QueryNormalizationLog model."""

    def test_create_log_minimal(self):
        """Test creating normalization log with required fields."""
        log = QueryNormalizationLog(
            original_query="Come calcolare le tasse?",
            normalized_query="come calcolare tasse",
            query_hash="abc123def456",
            cache_key="cache_key_123",
            processing_time_ms=15.5,
        )

        assert log.original_query == "Come calcolare le tasse?"
        assert log.normalized_query == "come calcolare tasse"
        assert log.query_hash == "abc123def456"
        assert log.cache_key == "cache_key_123"
        assert log.processing_time_ms == 15.5
        assert log.applied_rules == []
        assert log.cache_hit is None
        assert log.cache_hit_after_normalization is None
        assert log.user_id is None
        assert log.session_id is None
        assert log.detected_language == "it"
        assert log.confidence_score == 1.0

    def test_create_log_with_cache_hit(self):
        """Test creating log with cache hit information."""
        log = QueryNormalizationLog(
            original_query="Detrazioni fiscali 2025",
            normalized_query="detrazioni fiscali 2025",
            query_hash="xyz789",
            cache_key="cache_123",
            processing_time_ms=10.0,
            applied_rules=["lowercase", "remove_punctuation", "normalize_whitespace"],
            cache_hit=False,
            cache_hit_after_normalization=True,
        )

        assert log.cache_hit is False
        assert log.cache_hit_after_normalization is True
        assert "lowercase" in log.applied_rules
        assert "normalize_whitespace" in log.applied_rules

    def test_create_log_with_user_context(self):
        """Test creating log with user context."""
        log = QueryNormalizationLog(
            original_query="Query test",
            normalized_query="query test",
            query_hash="hash123",
            cache_key="key123",
            processing_time_ms=12.0,
            user_id="user_456",
            session_id="session_789",
        )

        assert log.user_id == "user_456"
        assert log.session_id == "session_789"

    def test_create_log_with_language_detection(self):
        """Test creating log with language detection."""
        log = QueryNormalizationLog(
            original_query="What are the tax rates?",
            normalized_query="what are tax rates",
            query_hash="eng_hash",
            cache_key="eng_key",
            processing_time_ms=14.0,
            detected_language="en",
            confidence_score=0.95,
        )

        assert log.detected_language == "en"
        assert log.confidence_score == 0.95

    def test_log_timestamp_auto_created(self):
        """Test that timestamp is automatically created."""
        log = QueryNormalizationLog(
            original_query="Test",
            normalized_query="test",
            query_hash="h1",
            cache_key="k1",
            processing_time_ms=5.0,
        )

        assert log.created_at is not None
        assert isinstance(log.created_at, datetime)

    def test_log_with_complex_rules(self):
        """Test log with complex normalization rules."""
        rules = {
            "steps": ["lowercase", "remove_articles", "lemmatization"],
            "transformations": {"tasse": "tassa", "calcolare": "calcolo"},
        }

        log = QueryNormalizationLog(
            original_query="Come calcolare le tasse",
            normalized_query="come calcolo tassa",
            query_hash="complex_hash",
            cache_key="complex_key",
            processing_time_ms=25.5,
            applied_rules=rules,
        )

        assert log.applied_rules == rules
        assert "steps" in log.applied_rules


class TestQueryNormalizationStats:
    """Test QueryNormalizationStats model."""

    def test_create_stats_minimal(self):
        """Test creating stats with required fields."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(hours=1)

        stats = QueryNormalizationStats(
            period_start=period_start,
            period_end=period_end,
            period_type="hourly",
        )

        assert stats.period_start == period_start
        assert stats.period_end == period_end
        assert stats.period_type == "hourly"
        assert stats.total_queries == 0
        assert stats.normalized_queries == 0
        assert stats.avg_processing_time_ms == 0.0
        assert stats.cache_hits_before == 0
        assert stats.cache_hits_after == 0
        assert stats.cache_hit_improvement == 0.0
        assert stats.rule_frequency == {}
        assert stats.common_patterns == {}
        assert stats.avg_confidence_score == 1.0

    def test_create_stats_hourly(self):
        """Test creating hourly statistics."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(hours=1)

        stats = QueryNormalizationStats(
            period_start=period_start,
            period_end=period_end,
            period_type="hourly",
            total_queries=1000,
            normalized_queries=850,
            avg_processing_time_ms=12.5,
            max_processing_time_ms=45.0,
            min_processing_time_ms=3.2,
            cache_hits_before=400,
            cache_hits_after=680,
            cache_hit_improvement=70.0,
        )

        assert stats.total_queries == 1000
        assert stats.normalized_queries == 850
        assert stats.avg_processing_time_ms == 12.5
        assert stats.max_processing_time_ms == 45.0
        assert stats.min_processing_time_ms == 3.2
        assert stats.cache_hits_before == 400
        assert stats.cache_hits_after == 680
        assert stats.cache_hit_improvement == 70.0

    def test_create_stats_daily(self):
        """Test creating daily statistics."""
        period_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)

        stats = QueryNormalizationStats(
            period_start=period_start,
            period_end=period_end,
            period_type="daily",
            total_queries=25000,
            normalized_queries=21000,
        )

        assert stats.period_type == "daily"
        assert stats.total_queries == 25000

    def test_stats_with_rule_frequency(self):
        """Test stats with rule application frequency."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(hours=1)

        rule_freq = {
            "lowercase": 950,
            "remove_punctuation": 800,
            "normalize_whitespace": 920,
            "remove_stopwords": 600,
        }

        stats = QueryNormalizationStats(
            period_start=period_start,
            period_end=period_end,
            period_type="hourly",
            total_queries=1000,
            rule_frequency=rule_freq,
        )

        assert stats.rule_frequency["lowercase"] == 950
        assert stats.rule_frequency["remove_stopwords"] == 600

    def test_stats_with_common_patterns(self):
        """Test stats with common query patterns."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(hours=1)

        patterns = {
            "tax_calculation": {"count": 250, "avg_time": 15.0},
            "deductions": {"count": 180, "avg_time": 12.5},
            "ccnl_queries": {"count": 120, "avg_time": 18.0},
        }

        stats = QueryNormalizationStats(
            period_start=period_start,
            period_end=period_end,
            period_type="hourly",
            common_patterns=patterns,
        )

        assert "tax_calculation" in stats.common_patterns
        assert stats.common_patterns["deductions"]["count"] == 180

    def test_stats_timestamps_auto_created(self):
        """Test that timestamps are automatically created."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(hours=1)

        stats = QueryNormalizationStats(
            period_start=period_start,
            period_end=period_end,
            period_type="hourly",
        )

        assert stats.created_at is not None
        assert stats.updated_at is not None


class TestQueryNormalizationPattern:
    """Test QueryNormalizationPattern model."""

    def test_create_pattern_minimal(self):
        """Test creating pattern with required fields."""
        first_seen = datetime.now(UTC)
        last_seen = first_seen

        pattern = QueryNormalizationPattern(
            pattern_hash="pattern_abc123",
            normalized_form="come calcolare tasse",
            avg_processing_time_ms=14.5,
            first_seen=first_seen,
            last_seen=last_seen,
        )

        assert pattern.pattern_hash == "pattern_abc123"
        assert pattern.normalized_form == "come calcolare tasse"
        assert pattern.frequency == 1
        assert pattern.unique_queries == 1
        assert pattern.example_queries == []
        assert pattern.avg_processing_time_ms == 14.5
        assert pattern.cache_hit_rate == 0.0
        assert pattern.category is None
        assert pattern.complexity == "medium"
        assert pattern.faq_candidate is False
        assert pattern.faq_score == 0.0

    def test_create_pattern_with_high_frequency(self):
        """Test creating frequently occurring pattern."""
        first_seen = datetime.now(UTC) - timedelta(days=30)
        last_seen = datetime.now(UTC)

        examples = [
            {"query": "Come calcolare le tasse?", "count": 50},
            {"query": "Come si calcolano le tasse", "count": 35},
            {"query": "Calcolo tasse come fare", "count": 28},
        ]

        pattern = QueryNormalizationPattern(
            pattern_hash="freq_pattern",
            normalized_form="come calcolare tasse",
            frequency=113,
            unique_queries=3,
            example_queries=examples,
            avg_processing_time_ms=15.2,
            cache_hit_rate=0.85,
            first_seen=first_seen,
            last_seen=last_seen,
        )

        assert pattern.frequency == 113
        assert pattern.unique_queries == 3
        assert len(pattern.example_queries) == 3
        assert pattern.cache_hit_rate == 0.85

    def test_create_pattern_with_category(self):
        """Test creating pattern with category."""
        first_seen = datetime.now(UTC)
        last_seen = first_seen

        pattern = QueryNormalizationPattern(
            pattern_hash="tax_pattern",
            normalized_form="detrazioni fiscali 2025",
            avg_processing_time_ms=12.0,
            category="tax",
            complexity="simple",
            first_seen=first_seen,
            last_seen=last_seen,
        )

        assert pattern.category == "tax"
        assert pattern.complexity == "simple"

    def test_create_pattern_faq_candidate(self):
        """Test creating pattern marked as FAQ candidate."""
        first_seen = datetime.now(UTC) - timedelta(days=60)
        last_seen = datetime.now(UTC)

        pattern = QueryNormalizationPattern(
            pattern_hash="faq_pattern",
            normalized_form="scadenza dichiarazione redditi",
            frequency=250,
            unique_queries=45,
            avg_processing_time_ms=10.5,
            cache_hit_rate=0.92,
            category="tax",
            complexity="simple",
            faq_candidate=True,
            faq_score=0.88,
            first_seen=first_seen,
            last_seen=last_seen,
        )

        assert pattern.faq_candidate is True
        assert pattern.faq_score == 0.88
        assert pattern.frequency == 250

    def test_pattern_complexity_levels(self):
        """Test different complexity levels."""
        first_seen = datetime.now(UTC)
        last_seen = first_seen

        simple = QueryNormalizationPattern(
            pattern_hash="simple_1",
            normalized_form="cosa ccnl",
            avg_processing_time_ms=8.0,
            complexity="simple",
            first_seen=first_seen,
            last_seen=last_seen,
        )

        medium = QueryNormalizationPattern(
            pattern_hash="medium_1",
            normalized_form="come calcolare stipendio netto",
            avg_processing_time_ms=15.0,
            complexity="medium",
            first_seen=first_seen,
            last_seen=last_seen,
        )

        complex_pattern = QueryNormalizationPattern(
            pattern_hash="complex_1",
            normalized_form="calcolo detrazione fiscale immobile prima casa con mutuo",
            avg_processing_time_ms=28.0,
            complexity="complex",
            first_seen=first_seen,
            last_seen=last_seen,
        )

        assert simple.complexity == "simple"
        assert medium.complexity == "medium"
        assert complex_pattern.complexity == "complex"

    def test_pattern_categories(self):
        """Test different pattern categories."""
        first_seen = datetime.now(UTC)
        last_seen = first_seen

        tax_pattern = QueryNormalizationPattern(
            pattern_hash="tax_1",
            normalized_form="detrazioni fiscali",
            avg_processing_time_ms=12.0,
            category="tax",
            first_seen=first_seen,
            last_seen=last_seen,
        )

        legal_pattern = QueryNormalizationPattern(
            pattern_hash="legal_1",
            normalized_form="contratto lavoro subordinato",
            avg_processing_time_ms=14.0,
            category="legal",
            first_seen=first_seen,
            last_seen=last_seen,
        )

        general_pattern = QueryNormalizationPattern(
            pattern_hash="general_1",
            normalized_form="informazioni generali",
            avg_processing_time_ms=10.0,
            category="general",
            first_seen=first_seen,
            last_seen=last_seen,
        )

        assert tax_pattern.category == "tax"
        assert legal_pattern.category == "legal"
        assert general_pattern.category == "general"

    def test_pattern_timestamps_auto_created(self):
        """Test that timestamps are automatically created."""
        first_seen = datetime.now(UTC)
        last_seen = first_seen

        pattern = QueryNormalizationPattern(
            pattern_hash="ts_pattern",
            normalized_form="test pattern",
            avg_processing_time_ms=10.0,
            first_seen=first_seen,
            last_seen=last_seen,
        )

        assert pattern.created_at is not None
        assert pattern.updated_at is not None
        assert isinstance(pattern.created_at, datetime)
        assert isinstance(pattern.updated_at, datetime)
