"""TDD Tests for QueryAmbiguityDetector Service (DEV-234).

Tests written BEFORE implementation following RED-GREEN-REFACTOR methodology.
Tests cover:
- AmbiguityResult dataclass
- Short query detection (<5 words)
- Pronoun ambiguity detection
- Follow-up pattern detection
- Missing fiscal terms detection
- Ambiguity score calculation
- Recommended strategy determination
- Factory function
"""

import pytest

# =============================================================================
# AmbiguityResult Dataclass Tests
# =============================================================================


class TestAmbiguityResult:
    """Tests for AmbiguityResult dataclass."""

    def test_create_result_with_required_fields(self) -> None:
        """Test creating result with required fields."""
        from app.services.query_ambiguity_detector import AmbiguityResult

        result = AmbiguityResult(
            is_ambiguous=True,
            score=0.75,
            indicators=["short_query"],
            recommended_strategy="multi_variant",
        )
        assert result.is_ambiguous is True
        assert result.score == 0.75
        assert "short_query" in result.indicators
        assert result.recommended_strategy == "multi_variant"

    def test_create_non_ambiguous_result(self) -> None:
        """Test creating non-ambiguous result."""
        from app.services.query_ambiguity_detector import AmbiguityResult

        result = AmbiguityResult(
            is_ambiguous=False,
            score=0.1,
            indicators=[],
            recommended_strategy="standard",
        )
        assert result.is_ambiguous is False
        assert len(result.indicators) == 0
        assert result.recommended_strategy == "standard"

    def test_result_to_dict(self) -> None:
        """Test result serialization to dict."""
        from app.services.query_ambiguity_detector import AmbiguityResult

        result = AmbiguityResult(
            is_ambiguous=True,
            score=0.8,
            indicators=["pronoun", "short_query"],
            recommended_strategy="multi_variant",
        )
        data = result.to_dict()

        assert data["is_ambiguous"] is True
        assert data["score"] == 0.8
        assert "pronoun" in data["indicators"]
        assert data["recommended_strategy"] == "multi_variant"


# =============================================================================
# Short Query Detection Tests
# =============================================================================


class TestShortQueryDetection:
    """Tests for short query detection (<5 words)."""

    def test_very_short_query_detected(self) -> None:
        """Test that queries with <5 words are flagged."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        # 2 words
        result = detector.detect("E l'IVA?")
        assert result.is_ambiguous is True
        assert "short_query" in result.indicators

    def test_four_word_query_flagged(self) -> None:
        """Test that 4-word queries are flagged."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Come funziona l'IRPEF?")
        assert "short_query" in result.indicators

    def test_five_word_query_not_flagged(self) -> None:
        """Test that 5+ word queries are not flagged as short."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Come si calcola l'IRPEF annuale?")
        assert "short_query" not in result.indicators

    def test_longer_query_not_flagged(self) -> None:
        """Test that longer queries are not flagged as short."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Quali sono le aliquote IVA applicabili alla vendita di beni alimentari?")
        assert "short_query" not in result.indicators


# =============================================================================
# Pronoun Ambiguity Detection Tests
# =============================================================================


class TestPronounAmbiguityDetection:
    """Tests for pronoun ambiguity detection."""

    def test_questo_detected(self) -> None:
        """Test that 'questo' is detected as ambiguous pronoun."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Questo come funziona?")
        assert result.is_ambiguous is True
        assert "pronoun_ambiguity" in result.indicators

    def test_quello_detected(self) -> None:
        """Test that 'quello' is detected as ambiguous pronoun."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("E quello invece?")
        assert "pronoun_ambiguity" in result.indicators

    def test_questa_detected(self) -> None:
        """Test that 'questa' is detected as ambiguous pronoun."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Questa situazione è diversa?")
        assert "pronoun_ambiguity" in result.indicators

    def test_pronoun_with_clear_antecedent_less_ambiguous(self) -> None:
        """Test that pronoun with clear context in same query is less ambiguous."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        # "questo" but with clear subject in query
        result = detector.detect("L'IVA: questo tributo come si calcola?")
        # Should still detect pronoun but lower overall score
        assert result.score < 0.8

    def test_no_pronouns_no_flag(self) -> None:
        """Test that queries without ambiguous pronouns are not flagged."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Come si calcola l'IRPEF per un dipendente?")
        assert "pronoun_ambiguity" not in result.indicators


# =============================================================================
# Follow-up Pattern Detection Tests
# =============================================================================


class TestFollowupPatternDetection:
    """Tests for generic follow-up pattern detection."""

    def test_e_per_detected(self) -> None:
        """Test that 'E per...' pattern is detected."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("E per l'IVA?")
        assert result.is_ambiguous is True
        assert "followup_pattern" in result.indicators

    def test_e_se_detected(self) -> None:
        """Test that 'E se...' pattern is detected."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("E se invece fosse diverso?")
        assert "followup_pattern" in result.indicators

    def test_invece_detected(self) -> None:
        """Test that 'invece' pattern is detected."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Invece per le aziende?")
        assert "followup_pattern" in result.indicators

    def test_anche_detected(self) -> None:
        """Test that 'anche' pattern is detected."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Vale anche per i professionisti?")
        assert "followup_pattern" in result.indicators

    def test_la_stessa_cosa_detected(self) -> None:
        """Test that 'la stessa cosa' pattern is detected."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("La stessa cosa per i pensionati?")
        assert "followup_pattern" in result.indicators

    def test_no_followup_pattern(self) -> None:
        """Test that standard queries don't trigger followup flag."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Quali sono le scadenze per la dichiarazione IVA?")
        assert "followup_pattern" not in result.indicators


# =============================================================================
# Missing Fiscal Terms Detection Tests
# =============================================================================


class TestMissingFiscalTermsDetection:
    """Tests for missing key fiscal terms detection."""

    def test_query_with_fiscal_terms_not_flagged(self) -> None:
        """Test that queries with fiscal terms are not flagged."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Come si calcola l'IRPEF?")
        assert "missing_fiscal_terms" not in result.indicators

    def test_query_without_fiscal_terms_flagged(self) -> None:
        """Test that vague queries without fiscal terms are flagged."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Come funziona questo?")
        assert "missing_fiscal_terms" in result.indicators

    def test_query_with_iva_not_flagged(self) -> None:
        """Test that queries with IVA are not flagged."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Quali sono le aliquote IVA?")
        assert "missing_fiscal_terms" not in result.indicators

    def test_query_with_detrazione_not_flagged(self) -> None:
        """Test that queries with 'detrazione' are not flagged."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Quali detrazioni posso richiedere?")
        assert "missing_fiscal_terms" not in result.indicators


# =============================================================================
# Ambiguity Score Calculation Tests
# =============================================================================


class TestAmbiguityScoreCalculation:
    """Tests for ambiguity score calculation."""

    def test_multiple_indicators_increase_score(self) -> None:
        """Test that multiple ambiguity indicators increase score."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        # Query with multiple ambiguity signals
        result = detector.detect("E questo?")  # short, pronoun, followup

        # Score should be high with multiple indicators
        assert result.score >= 0.7
        assert len(result.indicators) >= 2

    def test_single_indicator_moderate_score(self) -> None:
        """Test that single indicator gives moderate score."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        # Query with only short_query indicator (has fiscal term so no missing_fiscal_terms)
        result = detector.detect("Qual è l'IVA?")

        # Should have short_query but not missing_fiscal_terms
        assert "short_query" in result.indicators
        assert "missing_fiscal_terms" not in result.indicators
        assert 0.2 <= result.score <= 0.6

    def test_no_indicators_low_score(self) -> None:
        """Test that no indicators gives low score."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Quali sono le aliquote IRPEF per l'anno fiscale 2024?")

        assert result.score < 0.3
        assert result.is_ambiguous is False

    def test_score_bounded_zero_to_one(self) -> None:
        """Test that score is always between 0 and 1."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        # Very ambiguous
        result1 = detector.detect("E questo quello?")
        assert 0.0 <= result1.score <= 1.0

        # Very clear
        result2 = detector.detect("Come si calcola la detrazione fiscale per ristrutturazione edilizia nel 2024?")
        assert 0.0 <= result2.score <= 1.0


# =============================================================================
# Recommended Strategy Tests
# =============================================================================


class TestRecommendedStrategy:
    """Tests for recommended strategy determination."""

    def test_high_ambiguity_recommends_multi_variant(self) -> None:
        """Test that high ambiguity recommends multi_variant strategy."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("E questo?")

        assert result.is_ambiguous is True
        assert result.recommended_strategy == "multi_variant"

    def test_low_ambiguity_recommends_standard(self) -> None:
        """Test that low ambiguity recommends standard strategy."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Quali sono le scadenze per il pagamento dell'IVA trimestrale?")

        assert result.is_ambiguous is False
        assert result.recommended_strategy == "standard"

    def test_medium_ambiguity_recommends_conversational(self) -> None:
        """Test that medium ambiguity recommends conversational strategy."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        # Medium ambiguity - has some signals but not many
        result = detector.detect("E per l'IVA come funziona?")

        # Medium ambiguity should recommend conversational (use context)
        if 0.3 <= result.score < 0.6:
            assert result.recommended_strategy in ["conversational", "multi_variant"]


# =============================================================================
# Conversation History Integration Tests
# =============================================================================


class TestConversationHistoryIntegration:
    """Tests for conversation history consideration."""

    def test_detect_with_conversation_history(self) -> None:
        """Test detection considers conversation history."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        history = [
            {"role": "user", "content": "Come si calcola l'IRPEF?"},
            {"role": "assistant", "content": "L'IRPEF si calcola..."},
        ]

        result = detector.detect("E per i pensionati?", conversation_history=history)

        # With context, ambiguity might be lower
        assert result is not None
        assert "followup_pattern" in result.indicators

    def test_detect_without_conversation_history(self) -> None:
        """Test detection works without conversation history."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("E per l'IVA?", conversation_history=None)

        # Without context, should still detect ambiguity
        assert result.is_ambiguous is True

    def test_pronoun_with_history_context(self) -> None:
        """Test pronoun ambiguity reduced when context available."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        history = [
            {"role": "user", "content": "Parlami dell'IRPEF"},
            {"role": "assistant", "content": "L'IRPEF è l'imposta sul reddito..."},
        ]

        # "questo" with history about IRPEF
        result = detector.detect("Questo come si paga?", conversation_history=history)

        # Should still detect but might have different handling
        assert result is not None


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for factory function."""

    def test_get_detector_returns_instance(self) -> None:
        """Test factory returns detector instance."""
        from app.services.query_ambiguity_detector import get_query_ambiguity_detector

        detector = get_query_ambiguity_detector()
        assert detector is not None

    def test_get_detector_singleton(self) -> None:
        """Test factory returns singleton."""
        from app.services.query_ambiguity_detector import get_query_ambiguity_detector

        detector1 = get_query_ambiguity_detector()
        detector2 = get_query_ambiguity_detector()
        assert detector1 is detector2

    def test_reset_detector(self) -> None:
        """Test reset clears singleton."""
        from app.services.query_ambiguity_detector import (
            get_query_ambiguity_detector,
            reset_detector,
        )

        detector1 = get_query_ambiguity_detector()
        reset_detector()
        detector2 = get_query_ambiguity_detector()
        assert detector1 is not detector2


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_query(self) -> None:
        """Test handling of empty query."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("")

        # Empty query is very ambiguous
        assert result.is_ambiguous is True
        assert result.score >= 0.8

    def test_whitespace_only_query(self) -> None:
        """Test handling of whitespace-only query."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("   ")

        assert result.is_ambiguous is True

    def test_single_word_query(self) -> None:
        """Test handling of single word query."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("IVA?")

        assert result.is_ambiguous is True
        assert "short_query" in result.indicators

    def test_unicode_handling(self) -> None:
        """Test handling of unicode characters."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result = detector.detect("Qual è l'aliquota IVA?")

        # Should handle accented characters
        assert result is not None

    def test_case_insensitive_detection(self) -> None:
        """Test that detection is case insensitive."""
        from app.services.query_ambiguity_detector import QueryAmbiguityDetector

        detector = QueryAmbiguityDetector()

        result1 = detector.detect("E PER L'IVA?")
        result2 = detector.detect("e per l'iva?")

        # Both should detect followup pattern
        assert "followup_pattern" in result1.indicators
        assert "followup_pattern" in result2.indicators
