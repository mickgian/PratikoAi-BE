"""
TDD Tests for Query Classifier - DEV-BE-78 Phase 1.4

Tests for query type detection to enable dynamic weight adjustment
for retrieval ranking optimization.

Query Types:
- DEFINITIONAL: "cos'è", "che cosa significa" → boost FTS +10%
- RECENT: "ultime novità", "2024" → boost recency +10%
- CONCEPTUAL: "come", "perché" → boost vector +10%
- DEFAULT: standard weights
"""

import pytest

from app.services.query_classifier import (
    QueryType,
    classify_query,
    get_weight_adjustment,
)


class TestQueryClassifier:
    """Test suite for query type classification."""

    # ==========================================================================
    # DEFINITIONAL Query Tests
    # ==========================================================================

    @pytest.mark.parametrize(
        "query",
        [
            "Cos'è l'IVA?",
            "Cosa significa cedolare secca?",
            "Che cos'è il TFR?",
            "Definizione di reddito imponibile",
            "Che cosa è l'IRPEF?",
            "cos'e la ritenuta d'acconto",  # typo tolerance
            "Cosa vuol dire deducibile?",
        ],
    )
    def test_definitional_queries(self, query: str):
        """Test that definitional queries are correctly classified."""
        result = classify_query(query)
        assert result == QueryType.DEFINITIONAL, f"Expected DEFINITIONAL for: {query}"

    # ==========================================================================
    # RECENT Query Tests
    # ==========================================================================

    @pytest.mark.parametrize(
        "query",
        [
            "Ultime novità fiscali 2024",
            "Nuove aliquote IVA 2025",
            "Aggiornamenti recenti INPS",
            "Modifiche recenti al codice del lavoro",
            "Ultima circolare Agenzia delle Entrate",
            "Novità normative dicembre 2024",
            "Cosa è cambiato nel 2024?",
            "Nuovi bonus 2025",
        ],
    )
    def test_recent_queries(self, query: str):
        """Test that recent/temporal queries are correctly classified."""
        result = classify_query(query)
        assert result == QueryType.RECENT, f"Expected RECENT for: {query}"

    # ==========================================================================
    # CONCEPTUAL Query Tests
    # ==========================================================================

    @pytest.mark.parametrize(
        "query",
        [
            "Come calcolare le detrazioni fiscali?",
            "Perché devo pagare l'IMU?",
            "Come funziona il bonus ristrutturazione?",
            "In che modo posso ridurre le tasse?",
            "Spiegami il meccanismo della cedolare secca",
            "Qual è la differenza tra deduzioni e detrazioni?",
            "Come si determina il reddito imponibile?",
        ],
    )
    def test_conceptual_queries(self, query: str):
        """Test that conceptual/explanatory queries are correctly classified."""
        result = classify_query(query)
        assert result == QueryType.CONCEPTUAL, f"Expected CONCEPTUAL for: {query}"

    # ==========================================================================
    # DEFAULT Query Tests
    # ==========================================================================

    @pytest.mark.parametrize(
        "query",
        [
            "Risoluzione 64 Agenzia Entrate",
            "Aliquota IVA alimentari",
            "Codice tributo 3918",
            "Scadenza modello 730",
            "Circolare INPS n. 45",  # No year - classified as DEFAULT
        ],
    )
    def test_default_queries(self, query: str):
        """Test that standard queries are classified as DEFAULT."""
        result = classify_query(query)
        assert result == QueryType.DEFAULT, f"Expected DEFAULT for: {query}"

    # ==========================================================================
    # Edge Cases
    # ==========================================================================

    def test_empty_query_returns_default(self):
        """Test that empty query returns DEFAULT type."""
        assert classify_query("") == QueryType.DEFAULT
        assert classify_query("   ") == QueryType.DEFAULT

    def test_case_insensitivity(self):
        """Test that classification is case-insensitive."""
        assert classify_query("COS'È L'IVA?") == QueryType.DEFINITIONAL
        assert classify_query("ULTIME NOVITÀ 2024") == QueryType.RECENT
        assert classify_query("COME CALCOLARE?") == QueryType.CONCEPTUAL

    def test_mixed_signals_priority(self):
        """Test priority when query has multiple signals.

        Priority order: DEFINITIONAL > RECENT > CONCEPTUAL > DEFAULT
        """
        # Both definitional and recent signals - DEFINITIONAL wins
        result = classify_query("Cos'è cambiato nelle novità 2024?")
        assert result == QueryType.DEFINITIONAL

        # Both recent and conceptual signals - RECENT wins
        result = classify_query("Come funzionano le nuove regole 2024?")
        # This should be RECENT because it has temporal markers
        assert result in (QueryType.RECENT, QueryType.CONCEPTUAL)


class TestWeightAdjustment:
    """Test suite for weight adjustment based on query type."""

    def test_definitional_weight_adjustment(self):
        """Test weight adjustment for DEFINITIONAL queries."""
        adjustment = get_weight_adjustment(QueryType.DEFINITIONAL)

        # Should boost FTS by 10%
        assert adjustment["fts_boost"] == 0.10
        assert adjustment["vector_boost"] == 0.0
        assert adjustment["recency_boost"] == 0.0

    def test_recent_weight_adjustment(self):
        """Test weight adjustment for RECENT queries."""
        adjustment = get_weight_adjustment(QueryType.RECENT)

        # Should boost recency by 10%
        assert adjustment["fts_boost"] == 0.0
        assert adjustment["vector_boost"] == 0.0
        assert adjustment["recency_boost"] == 0.10

    def test_conceptual_weight_adjustment(self):
        """Test weight adjustment for CONCEPTUAL queries."""
        adjustment = get_weight_adjustment(QueryType.CONCEPTUAL)

        # Should boost vector by 10%
        assert adjustment["fts_boost"] == 0.0
        assert adjustment["vector_boost"] == 0.10
        assert adjustment["recency_boost"] == 0.0

    def test_default_no_adjustment(self):
        """Test that DEFAULT queries have no weight adjustment."""
        adjustment = get_weight_adjustment(QueryType.DEFAULT)

        assert adjustment["fts_boost"] == 0.0
        assert adjustment["vector_boost"] == 0.0
        assert adjustment["recency_boost"] == 0.0

    def test_adjustment_values_bounded(self):
        """Test that all adjustment values are within valid range."""
        for query_type in QueryType:
            adjustment = get_weight_adjustment(query_type)
            for key, value in adjustment.items():
                assert 0.0 <= value <= 0.20, f"Adjustment {key}={value} out of range for {query_type}"


class TestQueryClassifierPerformance:
    """Test performance requirements for query classifier."""

    def test_classification_speed(self):
        """Test that classification completes in <1ms (regex-based, no LLM)."""
        import time

        queries = [
            "Cos'è l'IVA?",
            "Ultime novità 2024",
            "Come calcolare le tasse?",
            "Risoluzione 64",
        ]

        for query in queries:
            start = time.perf_counter()
            classify_query(query)
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert elapsed_ms < 1.0, f"Classification took {elapsed_ms:.2f}ms, expected <1ms"

    def test_batch_classification_speed(self):
        """Test that 100 classifications complete in <100ms."""
        import time

        queries = [
            "Cos'è l'IVA?",
            "Ultime novità 2024",
            "Come calcolare le tasse?",
            "Risoluzione 64",
        ] * 25  # 100 queries

        start = time.perf_counter()
        for query in queries:
            classify_query(query)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100.0, f"Batch classification took {elapsed_ms:.2f}ms, expected <100ms"
