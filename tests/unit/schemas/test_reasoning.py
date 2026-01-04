"""TDD tests for DualReasoning data structures (DEV-229).

Tests the dual reasoning data structures that separate internal technical
reasoning from public user-friendly explanations.
Tests written BEFORE implementation following TDD methodology.
"""

from datetime import datetime

import pytest


class TestInternalReasoningDataclass:
    """Tests for InternalReasoning dataclass."""

    def test_internal_reasoning_creation(self):
        """InternalReasoning should be creatable with required fields."""
        from app.schemas.reasoning import InternalReasoning

        reasoning = InternalReasoning(
            reasoning_type="cot",
            theme="Calcolo IVA per cessione beni",
            sources_used=[
                {"id": "S1", "type": "legge", "title": "DPR 633/72"},
                {"id": "S2", "type": "circolare", "title": "Circ. 15/2021"},
            ],
            key_elements=["aliquota ordinaria 22%", "esenzioni art. 10"],
            conclusion="L'operazione è soggetta a IVA 22%",
        )
        assert reasoning.reasoning_type == "cot"
        assert reasoning.theme == "Calcolo IVA per cessione beni"
        assert len(reasoning.sources_used) == 2

    def test_internal_reasoning_tot_type(self):
        """InternalReasoning should support ToT reasoning type."""
        from app.schemas.reasoning import InternalReasoning

        reasoning = InternalReasoning(
            reasoning_type="tot",
            theme="Regime forfettario applicabilità",
            sources_used=[],
            key_elements=[],
            conclusion="",
            hypotheses=[
                {"id": "H1", "conclusion": "Applicabile", "confidence": 0.8},
                {"id": "H2", "conclusion": "Non applicabile", "confidence": 0.2},
            ],
            selected_hypothesis="H1",
            selection_reasoning="Maggiore supporto normativo",
        )
        assert reasoning.reasoning_type == "tot"
        assert reasoning.hypotheses is not None
        assert len(reasoning.hypotheses) == 2

    def test_internal_reasoning_optional_fields(self):
        """InternalReasoning optional fields should default to None."""
        from app.schemas.reasoning import InternalReasoning

        reasoning = InternalReasoning(
            reasoning_type="cot",
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion="Test conclusion",
        )
        assert reasoning.hypotheses is None
        assert reasoning.selected_hypothesis is None
        assert reasoning.selection_reasoning is None
        assert reasoning.confidence is None
        assert reasoning.risk_level is None
        assert reasoning.risk_factors is None

    def test_internal_reasoning_with_risk(self):
        """InternalReasoning should capture risk analysis."""
        from app.schemas.reasoning import InternalReasoning

        reasoning = InternalReasoning(
            reasoning_type="tot",
            theme="Deducibilità costi",
            sources_used=[],
            key_elements=[],
            conclusion="Costi parzialmente deducibili",
            risk_level="medium",
            risk_factors=["Documentazione incompleta", "Inerenza non chiara"],
        )
        assert reasoning.risk_level == "medium"
        assert len(reasoning.risk_factors) == 2

    def test_internal_reasoning_with_confidence(self):
        """InternalReasoning should capture confidence score."""
        from app.schemas.reasoning import InternalReasoning

        reasoning = InternalReasoning(
            reasoning_type="cot",
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion="Test",
            confidence=0.85,
        )
        assert reasoning.confidence == 0.85

    def test_internal_reasoning_with_latency(self):
        """InternalReasoning should capture processing latency."""
        from app.schemas.reasoning import InternalReasoning

        reasoning = InternalReasoning(
            reasoning_type="cot",
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion="Test",
            latency_ms=250.5,
        )
        assert reasoning.latency_ms == 250.5


class TestPublicExplanationDataclass:
    """Tests for PublicExplanation dataclass."""

    def test_public_explanation_creation(self):
        """PublicExplanation should be creatable with required fields."""
        from app.schemas.reasoning import PublicExplanation

        explanation = PublicExplanation(
            summary="La risposta si basa sull'analisi delle normative IVA.",
            main_sources=["DPR 633/72", "Circolare 15/2021"],
            confidence_label="alta",
        )
        assert "normative IVA" in explanation.summary
        assert len(explanation.main_sources) == 2
        assert explanation.confidence_label == "alta"

    def test_public_explanation_with_scenario(self):
        """PublicExplanation should support scenario selection."""
        from app.schemas.reasoning import PublicExplanation

        explanation = PublicExplanation(
            summary="Abbiamo considerato due possibili interpretazioni.",
            selected_scenario="Applicazione aliquota ordinaria",
            why_selected="È la posizione più conservativa e sicura.",
            main_sources=["Legge IVA"],
            confidence_label="media",
        )
        assert explanation.selected_scenario == "Applicazione aliquota ordinaria"
        assert "conservativa" in explanation.why_selected

    def test_public_explanation_confidence_labels(self):
        """PublicExplanation should use Italian confidence labels."""
        from app.schemas.reasoning import PublicExplanation

        # Test alta
        exp_alta = PublicExplanation(
            summary="Test",
            main_sources=[],
            confidence_label="alta",
        )
        assert exp_alta.confidence_label == "alta"

        # Test media
        exp_media = PublicExplanation(
            summary="Test",
            main_sources=[],
            confidence_label="media",
        )
        assert exp_media.confidence_label == "media"

        # Test bassa
        exp_bassa = PublicExplanation(
            summary="Test",
            main_sources=[],
            confidence_label="bassa",
        )
        assert exp_bassa.confidence_label == "bassa"

    def test_public_explanation_optional_fields(self):
        """PublicExplanation optional fields should default to None."""
        from app.schemas.reasoning import PublicExplanation

        explanation = PublicExplanation(
            summary="Test summary",
            main_sources=["Source 1"],
            confidence_label="alta",
        )
        assert explanation.selected_scenario is None
        assert explanation.why_selected is None
        assert explanation.alternative_note is None
        assert explanation.risk_warning is None

    def test_public_explanation_with_risk_warning(self):
        """PublicExplanation should support risk warnings in Italian."""
        from app.schemas.reasoning import PublicExplanation

        explanation = PublicExplanation(
            summary="Test",
            main_sources=[],
            confidence_label="media",
            risk_warning="Attenzione: questa interpretazione comporta rischi sanzionatori.",
        )
        assert "rischi sanzionatori" in explanation.risk_warning

    def test_public_explanation_with_alternative_note(self):
        """PublicExplanation should support alternative interpretation notes."""
        from app.schemas.reasoning import PublicExplanation

        explanation = PublicExplanation(
            summary="Test",
            main_sources=[],
            confidence_label="alta",
            alternative_note="Esiste un'interpretazione alternativa meno supportata.",
        )
        assert "alternativa" in explanation.alternative_note


class TestDualReasoningDataclass:
    """Tests for DualReasoning container dataclass."""

    def test_dual_reasoning_creation(self):
        """DualReasoning should contain both internal and public reasoning."""
        from app.schemas.reasoning import (
            DualReasoning,
            InternalReasoning,
            PublicExplanation,
        )

        internal = InternalReasoning(
            reasoning_type="cot",
            theme="IVA",
            sources_used=[],
            key_elements=[],
            conclusion="22%",
        )
        public = PublicExplanation(
            summary="L'IVA applicabile è del 22%.",
            main_sources=["DPR 633/72"],
            confidence_label="alta",
        )
        dual = DualReasoning(internal=internal, public=public)

        assert dual.internal.reasoning_type == "cot"
        assert dual.public.confidence_label == "alta"

    def test_dual_reasoning_with_timestamp(self):
        """DualReasoning should have created_at timestamp."""
        from app.schemas.reasoning import (
            DualReasoning,
            InternalReasoning,
            PublicExplanation,
        )

        internal = InternalReasoning(
            reasoning_type="cot",
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion="Test",
        )
        public = PublicExplanation(
            summary="Test",
            main_sources=[],
            confidence_label="alta",
        )
        dual = DualReasoning(internal=internal, public=public)

        assert dual.created_at is not None
        assert isinstance(dual.created_at, datetime)


class TestSerialization:
    """Tests for serialization of reasoning structures."""

    def test_internal_reasoning_to_dict(self):
        """InternalReasoning should be convertible to dict."""
        from app.schemas.reasoning import InternalReasoning

        reasoning = InternalReasoning(
            reasoning_type="cot",
            theme="Test theme",
            sources_used=[{"id": "S1", "type": "legge"}],
            key_elements=["element1", "element2"],
            conclusion="Test conclusion",
            confidence=0.85,
        )
        d = reasoning.to_dict()

        assert d["reasoning_type"] == "cot"
        assert d["theme"] == "Test theme"
        assert len(d["sources_used"]) == 1
        assert d["confidence"] == 0.85

    def test_public_explanation_to_dict(self):
        """PublicExplanation should be convertible to dict."""
        from app.schemas.reasoning import PublicExplanation

        explanation = PublicExplanation(
            summary="Test summary",
            selected_scenario="Scenario A",
            why_selected="Because reasons",
            main_sources=["Source 1", "Source 2"],
            confidence_label="alta",
        )
        d = explanation.to_dict()

        assert d["summary"] == "Test summary"
        assert d["selected_scenario"] == "Scenario A"
        assert d["confidence_label"] == "alta"

    def test_dual_reasoning_to_dict(self):
        """DualReasoning should be convertible to dict with nested structures."""
        from app.schemas.reasoning import (
            DualReasoning,
            InternalReasoning,
            PublicExplanation,
        )

        internal = InternalReasoning(
            reasoning_type="tot",
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion="Conclusion",
        )
        public = PublicExplanation(
            summary="Summary",
            main_sources=[],
            confidence_label="media",
        )
        dual = DualReasoning(internal=internal, public=public)
        d = dual.to_dict()

        assert "internal" in d
        assert "public" in d
        assert "created_at" in d
        assert d["internal"]["reasoning_type"] == "tot"
        assert d["public"]["confidence_label"] == "media"

    def test_internal_reasoning_from_dict(self):
        """InternalReasoning should be creatable from dict."""
        from app.schemas.reasoning import InternalReasoning

        data = {
            "reasoning_type": "cot",
            "theme": "Test theme",
            "sources_used": [{"id": "S1"}],
            "key_elements": ["elem1"],
            "conclusion": "Conclusion",
            "confidence": 0.9,
        }
        reasoning = InternalReasoning.from_dict(data)

        assert reasoning.reasoning_type == "cot"
        assert reasoning.theme == "Test theme"
        assert reasoning.confidence == 0.9

    def test_public_explanation_from_dict(self):
        """PublicExplanation should be creatable from dict."""
        from app.schemas.reasoning import PublicExplanation

        data = {
            "summary": "Test summary",
            "main_sources": ["Source 1"],
            "confidence_label": "bassa",
            "risk_warning": "Warning text",
        }
        explanation = PublicExplanation.from_dict(data)

        assert explanation.summary == "Test summary"
        assert explanation.confidence_label == "bassa"
        assert explanation.risk_warning == "Warning text"


class TestConfidenceLabelMapping:
    """Tests for confidence score to Italian label mapping."""

    def test_confidence_to_label_alta(self):
        """High confidence (>=0.8) should map to 'alta'."""
        from app.schemas.reasoning import confidence_to_label

        assert confidence_to_label(0.85) == "alta"
        assert confidence_to_label(0.8) == "alta"
        assert confidence_to_label(1.0) == "alta"

    def test_confidence_to_label_media(self):
        """Medium confidence (0.5-0.79) should map to 'media'."""
        from app.schemas.reasoning import confidence_to_label

        assert confidence_to_label(0.6) == "media"
        assert confidence_to_label(0.5) == "media"
        assert confidence_to_label(0.79) == "media"

    def test_confidence_to_label_bassa(self):
        """Low confidence (<0.5) should map to 'bassa'."""
        from app.schemas.reasoning import confidence_to_label

        assert confidence_to_label(0.3) == "bassa"
        assert confidence_to_label(0.49) == "bassa"
        assert confidence_to_label(0.0) == "bassa"

    def test_confidence_to_label_none(self):
        """None confidence should return 'non disponibile'."""
        from app.schemas.reasoning import confidence_to_label

        assert confidence_to_label(None) == "non disponibile"


class TestReasoningTypeEnum:
    """Tests for reasoning type enumeration."""

    def test_reasoning_type_values(self):
        """ReasoningType enum should have correct values."""
        from app.schemas.reasoning import ReasoningType

        assert ReasoningType.COT.value == "cot"
        assert ReasoningType.TOT.value == "tot"
        assert ReasoningType.TOT_MULTI_DOMAIN.value == "tot_multi_domain"

    def test_reasoning_type_from_string(self):
        """ReasoningType should be creatable from string."""
        from app.schemas.reasoning import ReasoningType

        assert ReasoningType("cot") == ReasoningType.COT
        assert ReasoningType("tot") == ReasoningType.TOT


class TestConfidenceLevelEnum:
    """Tests for confidence level enumeration."""

    def test_confidence_level_values(self):
        """ConfidenceLevel enum should have Italian labels."""
        from app.schemas.reasoning import ConfidenceLevel

        assert ConfidenceLevel.ALTA.value == "alta"
        assert ConfidenceLevel.MEDIA.value == "media"
        assert ConfidenceLevel.BASSA.value == "bassa"


class TestRiskLevelEnum:
    """Tests for risk level enumeration."""

    def test_risk_level_values(self):
        """RiskLevel enum should have correct values."""
        from app.schemas.reasoning import RiskLevel

        assert RiskLevel.CRITICAL.value == "critical"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.LOW.value == "low"


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_internal_from_cot(self):
        """create_internal_from_cot should create InternalReasoning from CoT data."""
        from app.schemas.reasoning import create_internal_from_cot

        cot_data = {
            "tema": "Calcolo imposte",
            "fonti_utilizzate": ["Art. 1 TUIR", "Circ. 10/2020"],
            "elementi_chiave": ["reddito imponibile", "aliquota"],
            "conclusione": "Imposta dovuta: 1000 EUR",
        }
        reasoning = create_internal_from_cot(cot_data)

        assert reasoning.reasoning_type == "cot"
        assert reasoning.theme == "Calcolo imposte"
        assert len(reasoning.sources_used) == 2
        assert "1000 EUR" in reasoning.conclusion

    def test_create_internal_from_tot(self):
        """create_internal_from_tot should create InternalReasoning from ToT data."""
        from app.schemas.reasoning import create_internal_from_tot

        tot_data = {
            "hypotheses": [
                {"id": "H1", "conclusion": "Option A", "confidence": 0.7},
                {"id": "H2", "conclusion": "Option B", "confidence": 0.3},
            ],
            "selected": "H1",
            "selection_reasoning": "Higher source support",
            "confidence": 0.7,
        }
        reasoning = create_internal_from_tot(tot_data, theme="Test theme")

        assert reasoning.reasoning_type == "tot"
        assert reasoning.selected_hypothesis == "H1"
        assert len(reasoning.hypotheses) == 2

    def test_create_public_from_internal(self):
        """create_public_from_internal should create PublicExplanation from InternalReasoning."""
        from app.schemas.reasoning import InternalReasoning, create_public_from_internal

        internal = InternalReasoning(
            reasoning_type="cot",
            theme="Calcolo IVA",
            sources_used=[
                {"id": "S1", "title": "DPR 633/72"},
                {"id": "S2", "title": "Circolare 15"},
            ],
            key_elements=["aliquota 22%"],
            conclusion="IVA 22% applicabile",
            confidence=0.85,
        )
        public = create_public_from_internal(internal)

        assert public.confidence_label == "alta"
        assert len(public.main_sources) == 2
        assert "DPR 633/72" in public.main_sources


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_sources_list(self):
        """Should handle empty sources list."""
        from app.schemas.reasoning import InternalReasoning

        reasoning = InternalReasoning(
            reasoning_type="cot",
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion="No sources available",
        )
        assert reasoning.sources_used == []

    def test_unicode_in_fields(self):
        """Should handle Unicode characters in Italian text."""
        from app.schemas.reasoning import PublicExplanation

        explanation = PublicExplanation(
            summary="L'analisi è basata sull'articolo 1° della Costituzione.",
            main_sources=["Costituzione Italiana"],
            confidence_label="alta",
        )
        assert "è" in explanation.summary
        assert "°" in explanation.summary

    def test_long_conclusion(self):
        """Should handle long conclusions."""
        from app.schemas.reasoning import InternalReasoning

        long_text = "A" * 5000
        reasoning = InternalReasoning(
            reasoning_type="cot",
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion=long_text,
        )
        assert len(reasoning.conclusion) == 5000

    def test_none_values_in_dict(self):
        """to_dict should handle None values properly."""
        from app.schemas.reasoning import InternalReasoning

        reasoning = InternalReasoning(
            reasoning_type="cot",
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion="Test",
        )
        d = reasoning.to_dict()
        # Optional fields should be None or not present
        assert d.get("hypotheses") is None or "hypotheses" not in d or d["hypotheses"] is None
