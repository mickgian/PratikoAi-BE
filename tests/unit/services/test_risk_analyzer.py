"""TDD Tests for RiskAnalyzer Service (DEV-231).

Tests written BEFORE implementation following TDD methodology.
Tests cover:
- Risk level assignment to hypotheses
- High-risk flagging even with low probability
- Risk mitigation action generation
- Italian tax sanction risk categories
"""

from __future__ import annotations

import pytest

from app.schemas.reasoning import RiskLevel

# =============================================================================
# Test: Risk Level Detection
# =============================================================================


class TestRiskLevelDetection:
    """Tests for detecting risk levels from hypothesis content."""

    def test_detects_critical_risk_frode_fiscale(self):
        """Should detect CRITICAL risk for frode fiscale."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "Questa operazione potrebbe configurare frode fiscale",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.risk_level == RiskLevel.CRITICAL.value

    def test_detects_critical_risk_falsa_fatturazione(self):
        """Should detect CRITICAL risk for falsa fatturazione."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "L'emissione di fatture false comporta sanzioni penali",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.risk_level == RiskLevel.CRITICAL.value

    def test_detects_critical_risk_evasione(self):
        """Should detect CRITICAL risk for evasione fiscale."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "Questa configurazione potrebbe essere considerata evasione fiscale",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.risk_level == RiskLevel.CRITICAL.value

    def test_detects_high_risk_omessa_dichiarazione(self):
        """Should detect HIGH risk for omessa dichiarazione."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "L'omessa dichiarazione comporta sanzioni dal 120% al 240%",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.risk_level == RiskLevel.HIGH.value

    def test_detects_high_risk_dichiarazione_infedele(self):
        """Should detect HIGH risk for dichiarazione infedele."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "La dichiarazione infedele è punita con sanzione dal 90% al 180%",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.risk_level == RiskLevel.HIGH.value

    def test_detects_medium_risk_errori_formali(self):
        """Should detect MEDIUM risk for errori formali sostanziali."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "Errori formali nella compilazione possono comportare sanzioni",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.risk_level == RiskLevel.MEDIUM.value

    def test_detects_low_risk_ritardi(self):
        """Should detect LOW risk for ritardi minori."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "Il ritardo nel versamento comporta una sanzione ridotta",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.risk_level == RiskLevel.LOW.value

    def test_defaults_to_low_when_no_risk_detected(self):
        """Should default to LOW when no specific risk detected."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "L'aliquota IVA standard è del 22%",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.risk_level == RiskLevel.LOW.value


# =============================================================================
# Test: Risk Factor Extraction
# =============================================================================


class TestRiskFactorExtraction:
    """Tests for extracting risk factors from hypothesis."""

    def test_extracts_multiple_risk_factors(self):
        """Should extract multiple risk factors from content."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "Questa operazione potrebbe configurare frode fiscale con falsa fatturazione",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert len(result.risk_factors) >= 2
        assert any("frode" in f.lower() for f in result.risk_factors)

    def test_extracts_sanction_range(self):
        """Should extract sanction range as risk factor."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "Sanzione applicabile dal 120% al 240% dell'imposta evasa",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert any("120%" in f or "240%" in f or "sanzione" in f.lower() for f in result.risk_factors)

    def test_empty_factors_for_no_risk(self):
        """Should return empty factors when no risk detected."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "L'operazione è regolare e conforme",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.risk_factors == [] or result.risk_factors is None


# =============================================================================
# Test: Mitigation Actions
# =============================================================================


class TestMitigationActions:
    """Tests for generating risk mitigation actions."""

    def test_generates_actions_for_critical_risk(self):
        """Should generate mitigation actions for CRITICAL risk."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "Questa operazione potrebbe configurare frode fiscale",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.mitigation_actions is not None
        assert len(result.mitigation_actions) > 0

    def test_critical_actions_include_professional_consultation(self):
        """CRITICAL risk should suggest professional consultation."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "Questa potrebbe essere evasione fiscale",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        actions_text = " ".join(result.mitigation_actions).lower()
        assert "professionista" in actions_text or "legale" in actions_text or "consulenza" in actions_text

    def test_high_risk_actions_suggest_regularization(self):
        """HIGH risk should suggest regularization options."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "L'omessa dichiarazione comporta sanzioni",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        actions_text = " ".join(result.mitigation_actions).lower()
        assert "ravvedimento" in actions_text or "regolarizzazione" in actions_text or "sanatoria" in actions_text

    def test_low_risk_has_minimal_or_no_actions(self):
        """LOW risk should have minimal or no mitigation actions."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "L'aliquota IVA standard è del 22%",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        # Low risk may have no actions or minimal ones
        assert result.mitigation_actions is None or len(result.mitigation_actions) <= 1


# =============================================================================
# Test: High-Risk Flagging with Low Probability
# =============================================================================


class TestHighRiskFlagging:
    """Tests for flagging high-risk even with low probability."""

    def test_flags_critical_risk_regardless_of_confidence(self):
        """Should flag CRITICAL risk even with low confidence hypothesis."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "Potrebbe configurare frode fiscale (improbabile)",
            "confidence": 0.2,  # Low confidence
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.risk_level == RiskLevel.CRITICAL.value
        assert result.should_flag is True

    def test_should_flag_true_for_critical(self):
        """should_flag should be True for CRITICAL risk."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "Falsa fatturazione rilevata",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.should_flag is True

    def test_should_flag_true_for_high(self):
        """should_flag should be True for HIGH risk."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "Omessa dichiarazione configurata",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.should_flag is True

    def test_should_flag_false_for_medium(self):
        """should_flag should be False for MEDIUM risk."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "Errori formali nella compilazione",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.should_flag is False

    def test_should_flag_false_for_low(self):
        """should_flag should be False for LOW risk."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypothesis = {
            "id": "H1",
            "conclusion": "Aliquota standard applicata",
            "sources_used": [],
        }
        result = analyzer.analyze_hypothesis(hypothesis)
        assert result.should_flag is False


# =============================================================================
# Test: Batch Analysis
# =============================================================================


class TestBatchAnalysis:
    """Tests for analyzing multiple hypotheses."""

    def test_analyze_all_hypotheses(self):
        """Should analyze all hypotheses in batch."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypotheses = [
            {"id": "H1", "conclusion": "Frode fiscale possibile", "sources_used": []},
            {"id": "H2", "conclusion": "Aliquota IVA standard", "sources_used": []},
            {"id": "H3", "conclusion": "Omessa dichiarazione", "sources_used": []},
        ]
        results = analyzer.analyze_hypotheses(hypotheses)
        assert len(results) == 3

    def test_returns_highest_risk_hypothesis(self):
        """Should identify the highest risk hypothesis."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypotheses = [
            {"id": "H1", "conclusion": "Aliquota IVA standard", "sources_used": []},
            {"id": "H2", "conclusion": "Frode fiscale", "sources_used": []},
            {"id": "H3", "conclusion": "Ritardo lieve", "sources_used": []},
        ]
        results = analyzer.analyze_hypotheses(hypotheses)
        highest = analyzer.get_highest_risk(results)
        assert highest.hypothesis_id == "H2"
        assert highest.risk_level == RiskLevel.CRITICAL.value

    def test_aggregates_risk_summary(self):
        """Should aggregate risk summary for all hypotheses."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        hypotheses = [
            {"id": "H1", "conclusion": "Frode fiscale", "sources_used": []},
            {"id": "H2", "conclusion": "Omessa dichiarazione", "sources_used": []},
        ]
        results = analyzer.analyze_hypotheses(hypotheses)
        summary = analyzer.get_risk_summary(results)

        assert "critical_count" in summary
        assert "high_count" in summary
        assert "has_flagged_risks" in summary
        assert summary["has_flagged_risks"] is True


# =============================================================================
# Test: Risk Result Data Class
# =============================================================================


class TestRiskResult:
    """Tests for RiskResult data class."""

    def test_risk_result_creation(self):
        """Should create RiskResult with all fields."""
        from app.services.risk_analyzer import RiskResult

        result = RiskResult(
            hypothesis_id="H1",
            risk_level=RiskLevel.HIGH.value,
            risk_factors=["omessa dichiarazione"],
            mitigation_actions=["Considerare ravvedimento operoso"],
            should_flag=True,
            sanction_range="120%-240%",
        )
        assert result.hypothesis_id == "H1"
        assert result.risk_level == RiskLevel.HIGH.value
        assert result.should_flag is True

    def test_risk_result_to_dict(self):
        """Should convert RiskResult to dict."""
        from app.services.risk_analyzer import RiskResult

        result = RiskResult(
            hypothesis_id="H1",
            risk_level=RiskLevel.CRITICAL.value,
            risk_factors=["frode fiscale"],
            mitigation_actions=["Consultare un legale"],
            should_flag=True,
            sanction_range=">100% + penale",
        )
        data = result.to_dict()
        assert data["hypothesis_id"] == "H1"
        assert data["risk_level"] == "critical"
        assert data["should_flag"] is True


# =============================================================================
# Test: Factory Function
# =============================================================================


class TestFactoryFunction:
    """Tests for get_risk_analyzer factory."""

    def test_returns_analyzer_instance(self):
        """Should return a RiskAnalyzer instance."""
        from app.services.risk_analyzer import RiskAnalyzer, get_risk_analyzer

        analyzer = get_risk_analyzer()
        assert isinstance(analyzer, RiskAnalyzer)

    def test_returns_singleton(self):
        """Should return the same instance on multiple calls."""
        from app.services.risk_analyzer import get_risk_analyzer, reset_analyzer

        reset_analyzer()
        a1 = get_risk_analyzer()
        a2 = get_risk_analyzer()
        assert a1 is a2

    def test_reset_clears_singleton(self):
        """Should clear singleton on reset."""
        from app.services.risk_analyzer import get_risk_analyzer, reset_analyzer

        reset_analyzer()
        a1 = get_risk_analyzer()
        reset_analyzer()
        a2 = get_risk_analyzer()
        assert a1 is not a2


# =============================================================================
# Test: Italian Keywords
# =============================================================================


class TestItalianKeywords:
    """Tests for Italian-specific risk keywords."""

    def test_recognizes_italian_critical_keywords(self):
        """Should recognize Italian critical risk keywords."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        critical_phrases = [
            "frode fiscale",
            "evasione fiscale",
            "falsa fatturazione",
            "fatture false",
            "reato tributario",
            "occultamento",
        ]
        for phrase in critical_phrases:
            hypothesis = {"id": "H1", "conclusion": phrase, "sources_used": []}
            result = analyzer.analyze_hypothesis(hypothesis)
            assert result.risk_level == RiskLevel.CRITICAL.value, f"Failed for: {phrase}"

    def test_recognizes_italian_high_keywords(self):
        """Should recognize Italian high risk keywords."""
        from app.services.risk_analyzer import RiskAnalyzer

        analyzer = RiskAnalyzer()
        high_phrases = [
            "omessa dichiarazione",
            "dichiarazione infedele",
            "omesso versamento",
            "indebita compensazione",
        ]
        for phrase in high_phrases:
            hypothesis = {"id": "H1", "conclusion": phrase, "sources_used": []}
            result = analyzer.analyze_hypothesis(hypothesis)
            assert result.risk_level == RiskLevel.HIGH.value, f"Failed for: {phrase}"


# =============================================================================
# Test: Integration with ToT
# =============================================================================


class TestToTIntegration:
    """Tests for integration with TreeOfThoughtsReasoner."""

    def test_analyze_tot_hypothesis_object(self):
        """Should analyze ToTHypothesis objects."""
        from app.services.risk_analyzer import RiskAnalyzer
        from app.services.tree_of_thoughts_reasoner import ToTHypothesis

        analyzer = RiskAnalyzer()
        hypothesis = ToTHypothesis(
            id="H1",
            reasoning_path="Analisi della possibile frode",
            conclusion="Potrebbe configurare frode fiscale",
            confidence=0.6,
            sources_used=[],
            source_weight_score=0.5,
        )
        result = analyzer.analyze_tot_hypothesis(hypothesis)
        assert result.risk_level == RiskLevel.CRITICAL.value
        assert result.hypothesis_id == "H1"

    def test_enrich_hypotheses_with_risk(self):
        """Should enrich hypotheses with risk analysis."""
        from app.services.risk_analyzer import RiskAnalyzer
        from app.services.tree_of_thoughts_reasoner import ToTHypothesis

        analyzer = RiskAnalyzer()
        hypotheses = [
            ToTHypothesis(
                id="H1",
                reasoning_path="Path 1",
                conclusion="Frode fiscale",
                confidence=0.6,
                sources_used=[],
                source_weight_score=0.5,
            ),
            ToTHypothesis(
                id="H2",
                reasoning_path="Path 2",
                conclusion="Aliquota standard",
                confidence=0.8,
                sources_used=[],
                source_weight_score=0.7,
            ),
        ]
        enriched = analyzer.enrich_hypotheses(hypotheses)
        assert len(enriched) == 2
        assert enriched[0].risk_level == RiskLevel.CRITICAL.value
        assert enriched[1].risk_level == RiskLevel.LOW.value
