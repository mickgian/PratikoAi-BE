"""TDD Tests for ResponseQualityScorer Service (DEV-232).

Tests written BEFORE implementation following RED-GREEN-REFACTOR methodology.
Tests cover:
- QualityDimension dataclass
- QualityScore dataclass
- ResponseQualityScorer scoring logic
- Source citation scoring
- Reasoning coherence scoring
- Action relevance scoring
- Risk coverage scoring
- Edge cases (empty data, missing fields)
- Factory function
"""

import pytest

# =============================================================================
# QualityDimension Dataclass Tests
# =============================================================================


class TestQualityDimension:
    """Tests for QualityDimension dataclass."""

    def test_create_dimension_with_required_fields(self) -> None:
        """Test creating a dimension with required fields."""
        from app.services.response_quality_scorer import QualityDimension

        dim = QualityDimension(
            name="source_citation",
            score=0.8,
            weight=0.30,
        )
        assert dim.name == "source_citation"
        assert dim.score == 0.8
        assert dim.weight == 0.30
        assert dim.details is None

    def test_create_dimension_with_details(self) -> None:
        """Test creating a dimension with optional details."""
        from app.services.response_quality_scorer import QualityDimension

        dim = QualityDimension(
            name="reasoning_coherence",
            score=0.75,
            weight=0.25,
            details="Good logical flow",
        )
        assert dim.details == "Good logical flow"

    def test_dimension_to_dict(self) -> None:
        """Test dimension serialization to dict."""
        from app.services.response_quality_scorer import QualityDimension

        dim = QualityDimension(
            name="action_relevance",
            score=0.9,
            weight=0.25,
            details="Actions well grounded",
        )
        result = dim.to_dict()

        assert result["name"] == "action_relevance"
        assert result["score"] == 0.9
        assert result["weight"] == 0.25
        assert result["details"] == "Actions well grounded"


# =============================================================================
# QualityScore Dataclass Tests
# =============================================================================


class TestQualityScore:
    """Tests for QualityScore dataclass."""

    def test_create_score_with_required_fields(self) -> None:
        """Test creating a score with required fields."""
        from app.services.response_quality_scorer import QualityDimension, QualityScore

        dimensions = [
            QualityDimension(name="test", score=0.8, weight=1.0),
        ]
        score = QualityScore(
            overall_score=0.8,
            dimensions=dimensions,
            flags=[],
            recommendation="good",
        )
        assert score.overall_score == 0.8
        assert len(score.dimensions) == 1
        assert score.recommendation == "good"

    def test_score_with_flags(self) -> None:
        """Test score with quality flags."""
        from app.services.response_quality_scorer import QualityDimension, QualityScore

        dimensions = [
            QualityDimension(name="source_citation", score=0.0, weight=0.30),
        ]
        score = QualityScore(
            overall_score=0.5,
            dimensions=dimensions,
            flags=["no_sources_cited", "needs_review"],
            recommendation="review",
        )
        assert "no_sources_cited" in score.flags
        assert "needs_review" in score.flags

    def test_score_to_dict(self) -> None:
        """Test score serialization to dict."""
        from app.services.response_quality_scorer import QualityDimension, QualityScore

        dimensions = [
            QualityDimension(name="test", score=0.7, weight=1.0),
        ]
        score = QualityScore(
            overall_score=0.7,
            dimensions=dimensions,
            flags=["warning"],
            recommendation="review",
        )
        result = score.to_dict()

        assert result["overall_score"] == 0.7
        assert len(result["dimensions"]) == 1
        assert result["flags"] == ["warning"]
        assert result["recommendation"] == "review"


# =============================================================================
# ResponseQualityScorer Initialization Tests
# =============================================================================


class TestResponseQualityScorerInit:
    """Tests for ResponseQualityScorer initialization."""

    def test_init_with_source_hierarchy(self) -> None:
        """Test initialization with source hierarchy."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        assert scorer.source_hierarchy is hierarchy

    def test_init_default_weights(self) -> None:
        """Test default weights are set correctly."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        assert scorer.weights["source_citation"] == 0.30
        assert scorer.weights["reasoning_coherence"] == 0.25
        assert scorer.weights["action_relevance"] == 0.25
        assert scorer.weights["risk_coverage"] == 0.20

    def test_init_custom_weights(self) -> None:
        """Test initialization with custom weights."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        custom_weights = {
            "source_citation": 0.40,
            "reasoning_coherence": 0.30,
            "action_relevance": 0.20,
            "risk_coverage": 0.10,
        }
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy, weights=custom_weights)

        assert scorer.weights["source_citation"] == 0.40


# =============================================================================
# Source Citation Scoring Tests
# =============================================================================


class TestSourceCitationScoring:
    """Tests for source citation quality dimension."""

    def test_score_with_high_authority_sources(self) -> None:
        """Test scoring with primary law sources (legge, decreto)."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        sources_cited = [
            {"type": "legge", "title": "Legge 289/2002"},
            {"type": "decreto_legislativo", "title": "D.Lgs. 546/92"},
        ]
        kb_sources = sources_cited  # Same sources available in KB

        result = scorer.score(
            response="Test response",
            reasoning_trace={"steps": ["step1"]},
            sources_cited=sources_cited,
            suggested_actions=[{"label": "Action 1"}],
            kb_sources=kb_sources,
            query="Test query",
        )

        # Find source_citation dimension
        source_dim = next(d for d in result.dimensions if d.name == "source_citation")
        assert source_dim.score >= 0.8  # High authority sources

    def test_score_with_no_sources(self) -> None:
        """Test scoring when no sources are cited."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        result = scorer.score(
            response="Test response",
            reasoning_trace={"steps": ["step1"]},
            sources_cited=[],
            suggested_actions=[{"label": "Action 1"}],
            kb_sources=[{"type": "legge", "title": "Source"}],
            query="Test query",
        )

        # Find source_citation dimension
        source_dim = next(d for d in result.dimensions if d.name == "source_citation")
        assert source_dim.score == 0.0
        assert "no_sources_cited" in result.flags

    def test_score_sources_not_in_kb(self) -> None:
        """Test scoring when cited sources not in knowledge base."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        sources_cited = [
            {"type": "legge", "title": "Unknown Law"},
        ]
        kb_sources = [
            {"type": "circolare", "title": "Different Source"},
        ]

        result = scorer.score(
            response="Test response",
            reasoning_trace={"steps": ["step1"]},
            sources_cited=sources_cited,
            suggested_actions=[],
            kb_sources=kb_sources,
            query="Test query",
        )

        # Should have warning flag
        assert "sources_not_grounded" in result.flags


# =============================================================================
# Reasoning Coherence Scoring Tests
# =============================================================================


class TestReasoningCoherenceScoring:
    """Tests for reasoning coherence quality dimension."""

    def test_score_with_complete_reasoning_trace(self) -> None:
        """Test scoring with complete reasoning trace."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        reasoning_trace = {
            "type": "cot",
            "theme": "Calcolo IVA",
            "steps": ["Identificazione normativa", "Applicazione aliquota", "Calcolo finale"],
            "conclusion": "L'IVA è del 22%",
        }

        result = scorer.score(
            response="L'IVA applicabile è del 22%",
            reasoning_trace=reasoning_trace,
            sources_cited=[{"type": "legge", "title": "DPR 633/72"}],
            suggested_actions=[],
            kb_sources=[{"type": "legge", "title": "DPR 633/72"}],
            query="Quale aliquota IVA si applica?",
        )

        reasoning_dim = next(d for d in result.dimensions if d.name == "reasoning_coherence")
        assert reasoning_dim.score >= 0.7  # Good reasoning trace

    def test_score_with_empty_reasoning_trace(self) -> None:
        """Test scoring with empty reasoning trace."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        result = scorer.score(
            response="Test response",
            reasoning_trace={},
            sources_cited=[{"type": "legge", "title": "Law"}],
            suggested_actions=[],
            kb_sources=[{"type": "legge", "title": "Law"}],
            query="Test query",
        )

        reasoning_dim = next(d for d in result.dimensions if d.name == "reasoning_coherence")
        # Empty reasoning should use default score
        assert reasoning_dim.score == 0.5  # Default score
        assert "empty_reasoning_trace" in result.flags

    def test_score_with_tot_reasoning(self) -> None:
        """Test scoring with Tree of Thoughts reasoning."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        reasoning_trace = {
            "type": "tot",
            "hypotheses": [
                {"id": "H1", "conclusion": "Hypothesis 1", "confidence": 0.8},
                {"id": "H2", "conclusion": "Hypothesis 2", "confidence": 0.6},
            ],
            "selected": "H1",
            "selection_reasoning": "H1 has higher source support",
        }

        result = scorer.score(
            response="Based on H1...",
            reasoning_trace=reasoning_trace,
            sources_cited=[{"type": "legge", "title": "Law"}],
            suggested_actions=[],
            kb_sources=[{"type": "legge", "title": "Law"}],
            query="Complex question",
        )

        reasoning_dim = next(d for d in result.dimensions if d.name == "reasoning_coherence")
        assert reasoning_dim.score >= 0.7  # ToT with selection reasoning scores well


# =============================================================================
# Action Relevance Scoring Tests
# =============================================================================


class TestActionRelevanceScoring:
    """Tests for action relevance quality dimension."""

    def test_score_with_relevant_actions(self) -> None:
        """Test scoring with well-grounded actions."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        suggested_actions = [
            {"label": "Presenta dichiarazione IVA", "grounded": True},
            {"label": "Verifica scadenza trimestrale", "grounded": True},
        ]

        result = scorer.score(
            response="Test response",
            reasoning_trace={"steps": ["step"]},
            sources_cited=[{"type": "legge", "title": "Law"}],
            suggested_actions=suggested_actions,
            kb_sources=[{"type": "legge", "title": "Law"}],
            query="Test query",
        )

        action_dim = next(d for d in result.dimensions if d.name == "action_relevance")
        assert action_dim.score >= 0.7  # Grounded actions score well

    def test_score_with_no_actions(self) -> None:
        """Test scoring with no suggested actions (acceptable for info queries)."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        result = scorer.score(
            response="Test response",
            reasoning_trace={"steps": ["step"]},
            sources_cited=[{"type": "legge", "title": "Law"}],
            suggested_actions=[],
            kb_sources=[{"type": "legge", "title": "Law"}],
            query="What is the VAT rate?",  # Informational query
        )

        action_dim = next(d for d in result.dimensions if d.name == "action_relevance")
        assert action_dim.score == 0.0
        # No actions is acceptable for informational queries - no critical flag
        assert "critical_no_actions" not in result.flags

    def test_score_with_ungrounded_actions(self) -> None:
        """Test scoring with actions not grounded in sources."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        suggested_actions = [
            {"label": "Random action", "grounded": False},
            {"label": "Another random", "grounded": False},
        ]

        result = scorer.score(
            response="Test response",
            reasoning_trace={"steps": ["step"]},
            sources_cited=[{"type": "legge", "title": "Law"}],
            suggested_actions=suggested_actions,
            kb_sources=[{"type": "legge", "title": "Law"}],
            query="Test query",
        )

        action_dim = next(d for d in result.dimensions if d.name == "action_relevance")
        assert action_dim.score < 0.5  # Ungrounded actions score poorly
        assert "actions_not_grounded" in result.flags


# =============================================================================
# Risk Coverage Scoring Tests
# =============================================================================


class TestRiskCoverageScoring:
    """Tests for risk coverage quality dimension."""

    def test_score_with_risk_analysis_present(self) -> None:
        """Test scoring when risk analysis is present."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        reasoning_trace = {
            "steps": ["step"],
            "risk_level": "high",
            "risk_factors": ["omessa dichiarazione"],
        }

        result = scorer.score(
            response="Test response",
            reasoning_trace=reasoning_trace,
            sources_cited=[{"type": "legge", "title": "Law"}],
            suggested_actions=[],
            kb_sources=[{"type": "legge", "title": "Law"}],
            query="What are the penalties?",
        )

        risk_dim = next(d for d in result.dimensions if d.name == "risk_coverage")
        assert risk_dim.score >= 0.8  # Risk analysis present

    def test_score_with_no_risk_analysis(self) -> None:
        """Test scoring when risk analysis is missing."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        reasoning_trace = {"steps": ["step"]}  # No risk fields

        result = scorer.score(
            response="Test response",
            reasoning_trace=reasoning_trace,
            sources_cited=[{"type": "legge", "title": "Law"}],
            suggested_actions=[],
            kb_sources=[{"type": "legge", "title": "Law"}],
            query="Test query",
        )

        risk_dim = next(d for d in result.dimensions if d.name == "risk_coverage")
        # Missing risk analysis skips scoring (neutral)
        assert risk_dim.score == 0.5  # Default neutral score
        assert "no_risk_analysis" in result.flags

    def test_score_risk_with_mitigation_actions(self) -> None:
        """Test scoring when risk has associated mitigation actions."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        reasoning_trace = {
            "steps": ["step"],
            "risk_level": "critical",
            "risk_factors": ["frode fiscale"],
        }
        suggested_actions = [
            {"label": "Consultare avvocato tributarista", "is_mitigation": True},
        ]

        result = scorer.score(
            response="Test response",
            reasoning_trace=reasoning_trace,
            sources_cited=[{"type": "legge", "title": "Law"}],
            suggested_actions=suggested_actions,
            kb_sources=[{"type": "legge", "title": "Law"}],
            query="Is this tax fraud?",
        )

        risk_dim = next(d for d in result.dimensions if d.name == "risk_coverage")
        assert risk_dim.score >= 0.9  # Risk with mitigation scores very well


# =============================================================================
# Overall Score Calculation Tests
# =============================================================================


class TestOverallScoreCalculation:
    """Tests for overall score calculation."""

    def test_weighted_average_calculation(self) -> None:
        """Test that overall score is weighted average of dimensions."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        # Create scenario where we can predict the score
        result = scorer.score(
            response="Test",
            reasoning_trace={"steps": ["step"], "risk_level": "low"},
            sources_cited=[{"type": "legge", "title": "Law"}],
            suggested_actions=[{"label": "Action", "grounded": True}],
            kb_sources=[{"type": "legge", "title": "Law"}],
            query="Query",
        )

        # Overall should be between 0 and 1
        assert 0.0 <= result.overall_score <= 1.0

        # Verify it's calculated from dimensions
        calculated = sum(d.score * d.weight for d in result.dimensions)
        assert abs(result.overall_score - calculated) < 0.01

    def test_recommendation_good(self) -> None:
        """Test 'good' recommendation for high scores."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        # High quality response
        result = scorer.score(
            response="Comprehensive response",
            reasoning_trace={
                "type": "tot",
                "steps": ["step1", "step2", "step3"],
                "hypotheses": [{"id": "H1", "confidence": 0.9}],
                "selected": "H1",
                "selection_reasoning": "Best supported",
                "risk_level": "low",
                "risk_factors": [],
            },
            sources_cited=[
                {"type": "legge", "title": "Primary Law"},
                {"type": "decreto_legislativo", "title": "D.Lgs"},
            ],
            suggested_actions=[
                {"label": "Well grounded action", "grounded": True},
            ],
            kb_sources=[
                {"type": "legge", "title": "Primary Law"},
                {"type": "decreto_legislativo", "title": "D.Lgs"},
            ],
            query="Test",
        )

        # High overall score should give "good" recommendation
        if result.overall_score >= 0.7:
            assert result.recommendation == "good"

    def test_recommendation_review(self) -> None:
        """Test 'review' recommendation for medium scores."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        # Medium quality - some issues
        result = scorer.score(
            response="Partial response",
            reasoning_trace={"steps": ["step"]},
            sources_cited=[{"type": "faq", "title": "Low authority"}],  # Low authority
            suggested_actions=[],
            kb_sources=[{"type": "faq", "title": "Low authority"}],
            query="Test",
        )

        # Medium score should give "review" recommendation
        if 0.4 <= result.overall_score < 0.7:
            assert result.recommendation == "review"

    def test_recommendation_poor(self) -> None:
        """Test 'poor' recommendation for low scores."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        # Poor quality - many issues
        result = scorer.score(
            response="",
            reasoning_trace={},
            sources_cited=[],
            suggested_actions=[],
            kb_sources=[],
            query="Test",
        )

        # Low score should give "poor" recommendation
        if result.overall_score < 0.4:
            assert result.recommendation == "poor"


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_none_reasoning_trace(self) -> None:
        """Test handling of None reasoning trace."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        # Should handle None gracefully
        result = scorer.score(
            response="Test",
            reasoning_trace=None,  # type: ignore
            sources_cited=[{"type": "legge", "title": "Law"}],
            suggested_actions=[],
            kb_sources=[{"type": "legge", "title": "Law"}],
            query="Query",
        )

        # Should still produce a valid score
        assert result is not None
        assert 0.0 <= result.overall_score <= 1.0

    def test_empty_response(self) -> None:
        """Test handling of empty response."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        result = scorer.score(
            response="",
            reasoning_trace={"steps": ["step"]},
            sources_cited=[],
            suggested_actions=[],
            kb_sources=[],
            query="Query",
        )

        assert "empty_response" in result.flags

    def test_malformed_sources(self) -> None:
        """Test handling of malformed source data."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        # Sources without 'type' field
        malformed_sources = [
            {"title": "No type field"},
            {},
        ]

        result = scorer.score(
            response="Test",
            reasoning_trace={"steps": ["step"]},
            sources_cited=malformed_sources,
            suggested_actions=[],
            kb_sources=malformed_sources,
            query="Query",
        )

        # Should handle gracefully with default weight
        assert result is not None

    def test_empty_query(self) -> None:
        """Test handling of empty query."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        result = scorer.score(
            response="Response",
            reasoning_trace={"steps": ["step"]},
            sources_cited=[{"type": "legge", "title": "Law"}],
            suggested_actions=[],
            kb_sources=[{"type": "legge", "title": "Law"}],
            query="",
        )

        assert result is not None


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for get_response_quality_scorer factory function."""

    def test_get_scorer_returns_instance(self) -> None:
        """Test factory function returns scorer instance."""
        from app.services.response_quality_scorer import get_response_quality_scorer

        scorer = get_response_quality_scorer()
        assert scorer is not None

    def test_get_scorer_singleton(self) -> None:
        """Test factory function returns singleton."""
        from app.services.response_quality_scorer import get_response_quality_scorer

        scorer1 = get_response_quality_scorer()
        scorer2 = get_response_quality_scorer()
        assert scorer1 is scorer2

    def test_reset_scorer(self) -> None:
        """Test reset function clears singleton."""
        from app.services.response_quality_scorer import (
            get_response_quality_scorer,
            reset_scorer,
        )

        scorer1 = get_response_quality_scorer()
        reset_scorer()
        scorer2 = get_response_quality_scorer()
        assert scorer1 is not scorer2


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests with related services."""

    def test_score_with_real_source_hierarchy(self) -> None:
        """Test scoring using real SourceHierarchy weights."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import get_source_hierarchy

        hierarchy = get_source_hierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        # Mix of source types
        sources = [
            {"type": "legge", "title": "L. 289/2002"},  # weight 1.0
            {"type": "circolare", "title": "Circ. 10/E"},  # weight 0.6
        ]

        result = scorer.score(
            response="Based on primary law and administrative guidance...",
            reasoning_trace={"steps": ["analysis"]},
            sources_cited=sources,
            suggested_actions=[],
            kb_sources=sources,
            query="Tax question",
        )

        source_dim = next(d for d in result.dimensions if d.name == "source_citation")
        # Average weight should be (1.0 + 0.6) / 2 = 0.8
        assert source_dim.score >= 0.7

    def test_full_quality_pipeline(self) -> None:
        """Test complete quality scoring pipeline."""
        from app.services.response_quality_scorer import ResponseQualityScorer
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        scorer = ResponseQualityScorer(source_hierarchy=hierarchy)

        # Complete, high-quality response
        result = scorer.score(
            response="L'IVA applicabile è del 22% secondo l'art. 16 DPR 633/72.",
            reasoning_trace={
                "type": "cot",
                "theme": "Aliquota IVA",
                "steps": [
                    "Identificazione operazione",
                    "Verifica normativa applicabile",
                    "Determinazione aliquota",
                ],
                "conclusion": "IVA 22%",
                "risk_level": "low",
            },
            sources_cited=[
                {"type": "legge", "title": "DPR 633/72 Art. 16"},
            ],
            suggested_actions=[
                {"label": "Verifica classificazione merceologica", "grounded": True},
            ],
            kb_sources=[
                {"type": "legge", "title": "DPR 633/72 Art. 16"},
            ],
            query="Quale aliquota IVA si applica alla vendita di beni?",
        )

        # All dimensions should be present
        assert len(result.dimensions) == 4
        dimension_names = {d.name for d in result.dimensions}
        assert "source_citation" in dimension_names
        assert "reasoning_coherence" in dimension_names
        assert "action_relevance" in dimension_names
        assert "risk_coverage" in dimension_names

        # Overall score should be reasonable
        assert result.overall_score >= 0.5
