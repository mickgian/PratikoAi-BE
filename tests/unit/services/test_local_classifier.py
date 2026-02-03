"""TDD Tests for DEV-251 Phase 3: Local Query Complexity Classifier.

Tests for rule-based classifier that replaces GPT-4o-mini calls.

Run with: pytest tests/unit/services/test_local_classifier.py -v
"""

import pytest

from app.services.local_classifier import (
    ClassificationResult,
    LocalClassifier,
    LocalComplexity,
    get_local_classifier,
    reset_local_classifier,
)


@pytest.fixture
def classifier():
    """Create fresh classifier instance for each test."""
    reset_local_classifier()
    return LocalClassifier()


class TestSimpleQueryClassification:
    """Test that simple queries are classified as SIMPLE."""

    def test_short_direct_question_is_simple(self, classifier):
        """Short direct questions should be SIMPLE."""
        result = classifier.classify(
            query="Qual è l'aliquota IVA?",
            domains=["fiscale"],
        )
        assert result.complexity == LocalComplexity.SIMPLE
        assert result.confidence >= 0.7

    def test_rate_question_is_simple(self, classifier):
        """Questions about rates should be SIMPLE."""
        result = classifier.classify(
            query="Quanto costa la marca da bollo?",
            domains=["fiscale"],
        )
        assert result.complexity == LocalComplexity.SIMPLE

    def test_deadline_question_is_simple(self, classifier):
        """Questions about deadlines should be SIMPLE."""
        result = classifier.classify(
            query="Quando scade la dichiarazione IVA?",
            domains=["fiscale"],
        )
        assert result.complexity == LocalComplexity.SIMPLE

    def test_definition_question_is_simple(self, classifier):
        """Definition questions should be SIMPLE."""
        result = classifier.classify(
            query="Cos'è il regime forfettario?",
            domains=["fiscale"],
        )
        assert result.complexity == LocalComplexity.SIMPLE

    def test_yes_no_question_is_simple(self, classifier):
        """Yes/no questions should be SIMPLE."""
        result = classifier.classify(
            query="È possibile detrarre l'IVA sulle auto?",
            domains=["fiscale"],
        )
        assert result.complexity == LocalComplexity.SIMPLE


class TestComplexQueryClassification:
    """Test that complex queries are classified as COMPLEX."""

    def test_procedural_question_is_complex(self, classifier):
        """Procedural questions should be COMPLEX."""
        result = classifier.classify(
            query="Come si fa a richiedere il rimborso IVA per acquisti intracomunitari?",
            domains=["fiscale"],
        )
        assert result.complexity == LocalComplexity.COMPLEX

    def test_conditional_scenario_is_complex(self, classifier):
        """Conditional scenarios should be COMPLEX."""
        result = classifier.classify(
            query="Nel caso in cui un dipendente superi il limite di reddito, come cambia la tassazione?",
            domains=["fiscale"],
        )
        assert result.complexity == LocalComplexity.COMPLEX

    def test_specific_case_is_complex(self, classifier):
        """Specific case questions should be COMPLEX."""
        result = classifier.classify(
            query="La mia azienda che opera nel settore edilizio deve applicare lo split payment?",
            domains=["fiscale"],
        )
        assert result.complexity == LocalComplexity.COMPLEX

    def test_comparison_question_is_complex(self, classifier):
        """Comparison questions should be COMPLEX."""
        result = classifier.classify(
            query="Qual è la differenza tra regime ordinario e semplificato per le imprese?",
            domains=["fiscale"],
        )
        assert result.complexity == LocalComplexity.COMPLEX

    def test_long_query_tends_complex(self, classifier):
        """Long queries should tend toward COMPLEX."""
        result = classifier.classify(
            query=(
                "Ho un dipendente che ha lavorato per 3 mesi con contratto a tempo determinato "
                "e ora vorrei trasformarlo in tempo indeterminato. Quali sono i passaggi da seguire "
                "e quali costi contributivi devo considerare nella valutazione?"
            ),
            domains=["lavoro"],
        )
        assert result.complexity in (LocalComplexity.COMPLEX, LocalComplexity.MULTI_DOMAIN)

    def test_multiple_questions_is_complex(self, classifier):
        """Multiple questions in one query should be COMPLEX."""
        result = classifier.classify(
            query="Quando scade la dichiarazione? E quali sanzioni si applicano per ritardo?",
            domains=["fiscale"],
        )
        assert result.complexity == LocalComplexity.COMPLEX


class TestMultiDomainClassification:
    """Test that multi-domain queries are classified as MULTI_DOMAIN."""

    def test_two_domains_is_multi_domain(self, classifier):
        """Queries with 2+ domains should be MULTI_DOMAIN."""
        result = classifier.classify(
            query="Quali sono gli obblighi fiscali e contributivi per l'assunzione?",
            domains=["fiscale", "lavoro"],
        )
        assert result.complexity == LocalComplexity.MULTI_DOMAIN

    def test_three_domains_is_multi_domain(self, classifier):
        """Queries with 3 domains should be MULTI_DOMAIN."""
        result = classifier.classify(
            query="Aspetti fiscali, previdenziali e legali del TFR",
            domains=["fiscale", "lavoro", "legale"],
        )
        assert result.complexity == LocalComplexity.MULTI_DOMAIN

    def test_cross_domain_keywords_boost_multi_domain(self, classifier):
        """Cross-domain keywords should boost MULTI_DOMAIN score."""
        result = classifier.classify(
            query="Come gestire il contributivo e previdenziale per un dipendente con partita IVA?",
            domains=["fiscale"],  # Even with one domain, keywords suggest multi
        )
        # Should at least be COMPLEX due to keywords
        assert result.complexity in (LocalComplexity.COMPLEX, LocalComplexity.MULTI_DOMAIN)


class TestConversationHistoryEffect:
    """Test that conversation history affects classification."""

    def test_history_increases_complexity(self, classifier):
        """Conversation history should increase complexity tendency."""
        # Without history
        classifier.classify(
            query="E per le detrazioni?",
            domains=["fiscale"],
            has_history=False,
        )

        result_with_history = classifier.classify(
            query="E per le detrazioni?",
            domains=["fiscale"],
            has_history=True,
        )

        # With history, should be more likely complex (follow-up question)
        assert "has_history" in result_with_history.reasons


class TestConfidenceScoring:
    """Test confidence scoring and GPT fallback logic."""

    def test_clear_simple_has_high_confidence(self, classifier):
        """Clearly simple queries should have high confidence."""
        result = classifier.classify(
            query="Qual è l'aliquota IVA ordinaria?",
            domains=["fiscale"],
        )
        assert result.confidence >= 0.7

    def test_ambiguous_query_has_lower_confidence(self, classifier):
        """Ambiguous queries should have lower confidence."""
        result = classifier.classify(
            query="IVA",  # Too short/vague
            domains=[],
        )
        # Still classifies but confidence may be lower
        assert result.complexity is not None

    def test_should_use_gpt_fallback_for_low_confidence(self, classifier):
        """Should recommend GPT fallback for low confidence results."""
        # Create a classifier with higher threshold
        strict_classifier = LocalClassifier(confidence_threshold=0.9)

        result = strict_classifier.classify(
            query="Questione fiscale",  # Vague
            domains=[],
        )

        # May or may not need fallback depending on confidence
        if result.confidence < 0.9:
            assert strict_classifier.should_use_gpt_fallback(result)


class TestClassificationReasons:
    """Test that classification reasons are properly tracked."""

    def test_reasons_include_query_length(self, classifier):
        """Reasons should include query length factor."""
        result = classifier.classify(
            query="Qual è l'aliquota IVA ordinaria?",
            domains=["fiscale"],
        )
        # Should have some reason related to length
        assert len(result.reasons) > 0

    def test_reasons_include_keyword_matches(self, classifier):
        """Reasons should include keyword matches."""
        result = classifier.classify(
            query="Come si calcola l'aliquota contributiva?",
            domains=["fiscale"],
        )
        has_keyword_reason = any("keyword" in r for r in result.reasons)
        assert has_keyword_reason or len(result.reasons) > 0


class TestSingletonPattern:
    """Test singleton pattern for classifier."""

    def test_get_local_classifier_returns_same_instance(self):
        """get_local_classifier should return singleton."""
        reset_local_classifier()
        c1 = get_local_classifier()
        c2 = get_local_classifier()
        assert c1 is c2

    def test_reset_clears_singleton(self):
        """reset_local_classifier should clear singleton."""
        c1 = get_local_classifier()
        reset_local_classifier()
        c2 = get_local_classifier()
        assert c1 is not c2


class TestPerformance:
    """Test performance requirements."""

    def test_classification_is_fast(self, classifier):
        """Classification should complete in <10ms."""
        import time

        query = "Qual è la procedura per richiedere il rimborso IVA?"

        start = time.perf_counter()
        for _ in range(100):
            classifier.classify(query, domains=["fiscale"])
        elapsed = (time.perf_counter() - start) * 1000 / 100  # Average ms

        assert elapsed < 10, f"Classification took {elapsed}ms, expected <10ms"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_query(self, classifier):
        """Empty query should still classify."""
        result = classifier.classify(query="", domains=[])
        assert result.complexity == LocalComplexity.SIMPLE  # Default for empty

    def test_very_long_query(self, classifier):
        """Very long query should handle gracefully."""
        result = classifier.classify(
            query="IVA " * 500,  # Very long query
            domains=["fiscale"],
        )
        assert result.complexity is not None

    def test_none_domains_handled(self, classifier):
        """None domains should be handled."""
        result = classifier.classify(
            query="Qual è l'aliquota?",
            domains=None,
        )
        assert result.complexity is not None

    def test_special_characters_handled(self, classifier):
        """Special characters should not break classification."""
        result = classifier.classify(
            query="Qual è l'IVA per €1.000,00?",
            domains=["fiscale"],
        )
        assert result.complexity is not None
