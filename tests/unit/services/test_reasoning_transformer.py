"""TDD Tests for ReasoningTransformer Service (DEV-230).

Tests written BEFORE implementation following TDD methodology.
Tests cover:
- Confidence score to Italian label mapping
- Source reference simplification
- Selection reasoning user-friendly transformation
- Full transformation pipeline
"""

from __future__ import annotations

import pytest

from app.schemas.reasoning import (
    InternalReasoning,
    PublicExplanation,
    ReasoningType,
    RiskLevel,
)

# =============================================================================
# Test: Confidence Score Mapping
# =============================================================================


class TestConfidenceMapping:
    """Tests for confidence score to Italian label mapping."""

    def test_high_confidence_maps_to_alta(self):
        """Confidence >= 0.8 should map to 'alta'."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        assert transformer.map_confidence(0.85) == "alta"
        assert transformer.map_confidence(0.8) == "alta"
        assert transformer.map_confidence(1.0) == "alta"

    def test_medium_confidence_maps_to_media(self):
        """Confidence 0.5-0.79 should map to 'media'."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        assert transformer.map_confidence(0.75) == "media"
        assert transformer.map_confidence(0.5) == "media"
        assert transformer.map_confidence(0.65) == "media"

    def test_low_confidence_maps_to_bassa(self):
        """Confidence < 0.5 should map to 'bassa'."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        assert transformer.map_confidence(0.49) == "bassa"
        assert transformer.map_confidence(0.3) == "bassa"
        assert transformer.map_confidence(0.0) == "bassa"

    def test_none_confidence_maps_to_non_disponibile(self):
        """None confidence should map to 'non disponibile'."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        assert transformer.map_confidence(None) == "non disponibile"

    def test_edge_case_exact_threshold(self):
        """Test exact threshold values."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        assert transformer.map_confidence(0.8) == "alta"  # Exactly at high threshold
        assert transformer.map_confidence(0.5) == "media"  # Exactly at medium threshold
        assert transformer.map_confidence(0.79999) == "media"  # Just below high


# =============================================================================
# Test: Source Reference Simplification
# =============================================================================


class TestSourceSimplification:
    """Tests for simplifying source references."""

    def test_extracts_titles_from_dict_sources(self):
        """Should extract titles from source dictionaries."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        sources = [
            {"id": "S1", "type": "legge", "title": "DPR 633/72"},
            {"id": "S2", "type": "circolare", "title": "Circolare 18/E"},
        ]
        simplified = transformer.simplify_sources(sources)
        assert simplified == ["DPR 633/72", "Circolare 18/E"]

    def test_removes_technical_ids(self):
        """Should not include technical IDs in simplified output."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        sources = [{"id": "S1", "title": "Art. 164 TUIR"}]
        simplified = transformer.simplify_sources(sources)
        assert "S1" not in simplified[0]
        assert simplified == ["Art. 164 TUIR"]

    def test_handles_string_sources(self):
        """Should handle plain string sources."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        sources = ["Art. 1 Legge 190/2014", "Circolare 12/E"]
        simplified = transformer.simplify_sources(sources)
        assert simplified == ["Art. 1 Legge 190/2014", "Circolare 12/E"]

    def test_limits_sources_with_max_count(self):
        """Should limit number of sources when max_count specified."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        sources = [
            {"title": "Source 1"},
            {"title": "Source 2"},
            {"title": "Source 3"},
            {"title": "Source 4"},
            {"title": "Source 5"},
        ]
        simplified = transformer.simplify_sources(sources, max_count=3)
        assert len(simplified) == 3
        assert simplified == ["Source 1", "Source 2", "Source 3"]

    def test_adds_suffix_when_truncated(self):
        """Should add 'e altre fonti' suffix when truncating."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        sources = [
            {"title": "Source 1"},
            {"title": "Source 2"},
            {"title": "Source 3"},
            {"title": "Source 4"},
        ]
        simplified = transformer.simplify_sources(sources, max_count=2, add_suffix=True)
        assert len(simplified) == 3
        assert simplified[-1] == "e altre 2 fonti"

    def test_empty_sources(self):
        """Should handle empty source list."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        simplified = transformer.simplify_sources([])
        assert simplified == []

    def test_sources_with_ref_fallback(self):
        """Should use 'ref' field if 'title' is missing."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        sources = [{"id": "S1", "ref": "Art. 164 TUIR"}]
        simplified = transformer.simplify_sources(sources)
        assert simplified == ["Art. 164 TUIR"]

    def test_sources_with_only_id_fallback(self):
        """Should use 'id' as last resort if no title or ref."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        sources = [{"id": "D.Lgs. 471/97"}]
        simplified = transformer.simplify_sources(sources)
        assert simplified == ["D.Lgs. 471/97"]


# =============================================================================
# Test: Selection Reasoning Transformation
# =============================================================================


class TestSelectionReasoningTransform:
    """Tests for making selection reasoning user-friendly."""

    def test_transforms_technical_reasoning(self):
        """Should transform technical reasoning to user-friendly Italian."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        technical = "Source S1 explicitly states 20% for mixed use vehicles"
        user_friendly = transformer.transform_selection_reasoning(technical)
        assert "S1" not in user_friendly  # No technical IDs
        assert user_friendly  # Not empty

    def test_handles_none_reasoning(self):
        """Should handle None selection reasoning gracefully."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        result = transformer.transform_selection_reasoning(None)
        assert result is None or result == ""

    def test_handles_empty_reasoning(self):
        """Should handle empty selection reasoning."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        result = transformer.transform_selection_reasoning("")
        assert result == ""

    def test_preserves_italian_reasoning(self):
        """Should preserve reasoning that's already in Italian."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        italian = "La fonte principale indica chiaramente il 20%"
        result = transformer.transform_selection_reasoning(italian)
        assert result == italian

    def test_removes_source_id_references(self):
        """Should remove source ID references like S1, S2."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        technical = "Based on S1, S2 and S3, the correct interpretation is..."
        result = transformer.transform_selection_reasoning(technical)
        assert "S1" not in result
        assert "S2" not in result
        assert "S3" not in result


# =============================================================================
# Test: Alternative Note Generation
# =============================================================================


class TestAlternativeNoteGeneration:
    """Tests for generating alternative interpretation notes."""

    def test_generates_note_for_multiple_hypotheses(self):
        """Should generate note when multiple hypotheses were considered."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.TOT.value,
            theme="Deducibilità spese auto",
            sources_used=[],
            key_elements=[],
            conclusion="Deducibilità limitata al 20%",
            hypotheses=[
                {"id": "H1", "name": "Uso esclusivo"},
                {"id": "H2", "name": "Uso promiscuo"},
            ],
            selected_hypothesis="H2",
        )
        note = transformer.generate_alternative_note(internal)
        assert note is not None
        assert "interpretazion" in note.lower() or "scenari" in note.lower()

    def test_no_note_for_single_hypothesis(self):
        """Should not generate note for single hypothesis."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.TOT.value,
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion="Test",
            hypotheses=[{"id": "H1", "name": "Only One"}],
        )
        note = transformer.generate_alternative_note(internal)
        assert note is None

    def test_no_note_for_cot_reasoning(self):
        """Should not generate note for CoT reasoning (no hypotheses)."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="Calcolo IVA",
            sources_used=[],
            key_elements=[],
            conclusion="IVA al 22%",
        )
        note = transformer.generate_alternative_note(internal)
        assert note is None

    def test_mentions_rejected_hypotheses(self):
        """Should mention that other interpretations were considered."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.TOT.value,
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion="Test",
            hypotheses=[
                {"id": "H1", "name": "First"},
                {"id": "H2", "name": "Second"},
                {"id": "H3", "name": "Third"},
            ],
            selected_hypothesis="H2",
        )
        note = transformer.generate_alternative_note(internal)
        assert "altre" in note.lower() or "alternative" in note.lower() or "altri" in note.lower()


# =============================================================================
# Test: Risk Warning Generation
# =============================================================================


class TestRiskWarningGeneration:
    """Tests for risk warning generation."""

    def test_generates_warning_for_high_risk(self):
        """Should generate warning for high risk level."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="Omessa dichiarazione",
            sources_used=[{"id": "S1", "type": "legge", "title": "D.Lgs. 471/97"}],
            key_elements=["sanzione 120-240%"],
            conclusion="Sanzione applicabile",
            risk_level=RiskLevel.HIGH.value,
            risk_factors=["omissione"],
        )
        warning = transformer.generate_risk_warning(internal)
        assert warning is not None
        assert "attenzione" in warning.lower() or "rischi" in warning.lower()

    def test_generates_warning_for_critical_risk(self):
        """Should generate warning for critical risk level."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="Frode fiscale",
            sources_used=[],
            key_elements=[],
            conclusion="Test",
            risk_level=RiskLevel.CRITICAL.value,
            risk_factors=["frode", "reato penale"],
        )
        warning = transformer.generate_risk_warning(internal)
        assert warning is not None
        assert "penale" in warning.lower() or "professionista" in warning.lower()

    def test_no_warning_for_medium_risk(self):
        """Should not generate warning for medium risk."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion="Test",
            risk_level=RiskLevel.MEDIUM.value,
        )
        warning = transformer.generate_risk_warning(internal)
        assert warning is None

    def test_no_warning_for_low_risk(self):
        """Should not generate warning for low risk."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion="Test",
            risk_level=RiskLevel.LOW.value,
        )
        warning = transformer.generate_risk_warning(internal)
        assert warning is None

    def test_no_warning_for_no_risk(self):
        """Should not generate warning when risk_level is None."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="Calcolo IVA",
            sources_used=[],
            key_elements=[],
            conclusion="IVA al 22%",
            confidence=0.85,
        )
        warning = transformer.generate_risk_warning(internal)
        assert warning is None


# =============================================================================
# Test: Summary Generation
# =============================================================================


class TestSummaryGeneration:
    """Tests for generating user-friendly summaries."""

    def test_cot_summary_mentions_sources(self):
        """CoT summary should mention source count."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="Calcolo IVA",
            sources_used=[
                {"id": "S1", "type": "legge", "title": "DPR 633/72"},
                {"id": "S2", "type": "circolare", "title": "Circolare 18/E/2020"},
            ],
            key_elements=[],
            conclusion="IVA al 22%",
        )
        summary = transformer.generate_summary(internal)
        assert "fonti" in summary.lower() or "fonte" in summary.lower()

    def test_tot_summary_mentions_interpretations(self):
        """ToT summary should mention multiple interpretations."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.TOT.value,
            theme="Deducibilità spese auto",
            sources_used=[],
            key_elements=[],
            conclusion="Deducibilità limitata al 20%",
            hypotheses=[
                {"id": "H1", "name": "Uso esclusivo"},
                {"id": "H2", "name": "Uso promiscuo"},
            ],
        )
        summary = transformer.generate_summary(internal)
        assert "interpretazion" in summary.lower() or "scenari" in summary.lower() or "possibil" in summary.lower()

    def test_summary_is_in_italian(self):
        """Summary should be in Italian."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="Calcolo IVA",
            sources_used=[{"title": "DPR 633/72"}],
            key_elements=[],
            conclusion="IVA al 22%",
        )
        summary = transformer.generate_summary(internal)
        # Check for Italian words
        italian_indicators = ["la", "di", "si", "una", "il", "le", "delle"]
        assert any(word in summary.lower().split() for word in italian_indicators)

    def test_summary_no_sources(self):
        """Should handle reasoning with no sources."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="Test theme",
            sources_used=[],
            key_elements=[],
            conclusion="Test",
        )
        summary = transformer.generate_summary(internal)
        assert summary  # Should not be empty
        assert "tema" in summary.lower() or "analisi" in summary.lower()


# =============================================================================
# Test: Full Transformation Pipeline
# =============================================================================


class TestFullTransformation:
    """Tests for complete transformation pipeline."""

    def test_transform_cot_reasoning(self):
        """Should transform CoT reasoning to public explanation."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="Calcolo IVA",
            sources_used=[
                {"id": "S1", "type": "legge", "title": "DPR 633/72"},
                {"id": "S2", "type": "circolare", "title": "Circolare 18/E/2020"},
            ],
            key_elements=["aliquota ordinaria 22%"],
            conclusion="L'IVA applicabile è del 22%",
            confidence=0.85,
        )
        public = transformer.transform(internal)

        assert isinstance(public, PublicExplanation)
        assert public.summary  # Has summary
        assert public.main_sources  # Has sources
        assert public.confidence_label == "alta"  # 0.85 -> alta

    def test_transform_tot_reasoning(self):
        """Should transform ToT reasoning to public explanation."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.TOT.value,
            theme="Deducibilità spese auto",
            sources_used=[
                {"id": "S1", "type": "legge", "title": "Art. 164 TUIR"},
            ],
            key_elements=[],
            conclusion="Deducibilità limitata al 20%",
            hypotheses=[
                {"id": "H1", "name": "Uso esclusivo"},
                {"id": "H2", "name": "Uso promiscuo"},
            ],
            selected_hypothesis="H2",
            confidence=0.75,
        )
        public = transformer.transform(internal)

        assert isinstance(public, PublicExplanation)
        assert public.summary
        assert public.main_sources
        assert public.confidence_label == "media"  # 0.75 -> media
        assert public.alternative_note is not None  # Has alternative note

    def test_transform_high_risk_reasoning(self):
        """Should include risk warning for high risk."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="Omessa dichiarazione",
            sources_used=[{"id": "S1", "type": "legge", "title": "D.Lgs. 471/97"}],
            key_elements=["sanzione 120-240%"],
            conclusion="Sanzione applicabile",
            confidence=0.9,
            risk_level=RiskLevel.HIGH.value,
            risk_factors=["omissione"],
        )
        public = transformer.transform(internal)

        assert public.risk_warning is not None
        assert "attenzione" in public.risk_warning.lower() or "rischi" in public.risk_warning.lower()

    def test_transform_preserves_scenario_info(self):
        """Should preserve selected scenario information."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.TOT.value,
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion="Test",
            hypotheses=[
                {"id": "H1", "name": "First"},
                {"id": "H2", "name": "Second"},
            ],
            selected_hypothesis="H2",
            selection_reasoning="Based on sources",
        )
        public = transformer.transform(internal)

        # selected_scenario should be set for ToT
        assert public.selected_scenario is not None or public.why_selected is not None

    def test_transform_with_options(self):
        """Should respect transformation options."""
        from app.services.reasoning_transformer import ReasoningTransformer, TransformOptions

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="Calcolo IVA",
            sources_used=[
                {"title": "Source 1"},
                {"title": "Source 2"},
                {"title": "Source 3"},
            ],
            key_elements=[],
            conclusion="Test",
        )
        options = TransformOptions(max_sources=1, include_alternative_note=False)
        public = transformer.transform(internal, options=options)

        assert len(public.main_sources) <= 2  # 1 source + optional suffix


# =============================================================================
# Test: Transform Options
# =============================================================================


class TestTransformOptions:
    """Tests for TransformOptions configuration."""

    def test_default_options(self):
        """Should have sensible default options."""
        from app.services.reasoning_transformer import TransformOptions

        options = TransformOptions()
        assert options.max_sources is None or options.max_sources > 0
        assert options.include_alternative_note is True
        assert options.include_risk_warning is True

    def test_custom_max_sources(self):
        """Should allow custom max_sources setting."""
        from app.services.reasoning_transformer import TransformOptions

        options = TransformOptions(max_sources=3)
        assert options.max_sources == 3

    def test_disable_alternative_note(self):
        """Should allow disabling alternative note."""
        from app.services.reasoning_transformer import TransformOptions

        options = TransformOptions(include_alternative_note=False)
        assert options.include_alternative_note is False

    def test_disable_risk_warning(self):
        """Should allow disabling risk warning."""
        from app.services.reasoning_transformer import TransformOptions

        options = TransformOptions(include_risk_warning=False)
        assert options.include_risk_warning is False


# =============================================================================
# Test: Factory Function
# =============================================================================


class TestFactoryFunction:
    """Tests for get_reasoning_transformer factory."""

    def test_returns_transformer_instance(self):
        """Should return a ReasoningTransformer instance."""
        from app.services.reasoning_transformer import (
            ReasoningTransformer,
            get_reasoning_transformer,
            reset_transformer,
        )

        reset_transformer()
        transformer = get_reasoning_transformer()
        assert isinstance(transformer, ReasoningTransformer)

    def test_returns_singleton(self):
        """Should return the same instance on multiple calls."""
        from app.services.reasoning_transformer import get_reasoning_transformer, reset_transformer

        reset_transformer()
        t1 = get_reasoning_transformer()
        t2 = get_reasoning_transformer()
        assert t1 is t2

    def test_reset_clears_singleton(self):
        """Should clear singleton on reset."""
        from app.services.reasoning_transformer import get_reasoning_transformer, reset_transformer

        reset_transformer()
        t1 = get_reasoning_transformer()
        reset_transformer()
        t2 = get_reasoning_transformer()
        assert t1 is not t2


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_empty_internal_reasoning(self):
        """Should handle minimal internal reasoning."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="",
            sources_used=[],
            key_elements=[],
            conclusion="",
        )
        public = transformer.transform(internal)
        assert isinstance(public, PublicExplanation)
        assert public.confidence_label == "non disponibile"

    def test_handles_mixed_source_types(self):
        """Should handle mixed source types (dict and string)."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        sources = [
            {"title": "Source 1"},
            "Plain string source",
            {"ref": "Source 3"},
        ]
        simplified = transformer.simplify_sources(sources)
        assert len(simplified) == 3

    def test_handles_unicode_in_sources(self):
        """Should handle Unicode characters in sources."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        sources = [{"title": "Art. 1 § 2 — Legge 190/2014"}]
        simplified = transformer.simplify_sources(sources)
        assert simplified == ["Art. 1 § 2 — Legge 190/2014"]

    def test_handles_very_long_reasoning(self):
        """Should handle very long selection reasoning."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        long_reasoning = "Based on " + " and ".join([f"S{i}" for i in range(100)])
        result = transformer.transform_selection_reasoning(long_reasoning)
        assert result  # Should not fail

    def test_handles_none_hypotheses(self):
        """Should handle None hypotheses in ToT reasoning."""
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.TOT.value,
            theme="Test",
            sources_used=[],
            key_elements=[],
            conclusion="Test",
            hypotheses=None,
        )
        note = transformer.generate_alternative_note(internal)
        assert note is None


# =============================================================================
# Test: Integration with DualReasoning
# =============================================================================


class TestDualReasoningIntegration:
    """Tests for integration with DualReasoning structures."""

    def test_creates_valid_dual_reasoning(self):
        """Should create valid DualReasoning with transformed public."""
        from app.schemas.reasoning import DualReasoning
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.COT.value,
            theme="Calcolo IVA",
            sources_used=[{"title": "DPR 633/72"}],
            key_elements=[],
            conclusion="IVA al 22%",
            confidence=0.85,
        )
        public = transformer.transform(internal)
        dual = DualReasoning(internal=internal, public=public)

        assert dual.internal is internal
        assert dual.public is public
        assert dual.to_dict()["internal"] == internal.to_dict()
        assert dual.to_dict()["public"] == public.to_dict()

    def test_transform_and_create_dual(self):
        """Should transform and create DualReasoning in one step."""
        from app.schemas.reasoning import DualReasoning
        from app.services.reasoning_transformer import ReasoningTransformer

        transformer = ReasoningTransformer()
        internal = InternalReasoning(
            reasoning_type=ReasoningType.TOT.value,
            theme="Deducibilità",
            sources_used=[],
            key_elements=[],
            conclusion="Test",
            hypotheses=[
                {"id": "H1", "name": "First"},
                {"id": "H2", "name": "Second"},
            ],
        )
        dual = transformer.transform_to_dual(internal)

        assert isinstance(dual, DualReasoning)
        assert dual.internal is internal
        assert isinstance(dual.public, PublicExplanation)
