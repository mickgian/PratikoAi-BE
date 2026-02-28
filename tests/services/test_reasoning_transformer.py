"""Tests for ReasoningTransformer service (DEV-230).

Comprehensive test suite targeting 90%+ coverage of
app/services/reasoning_transformer.py (510 lines).

Covers every public and private method:
- Confidence mapping via confidence_to_label
- Source simplification (dicts, strings, max_count, suffix)
- _extract_source_title for str, dict, and other types
- Selection reasoning transformation (None, empty, S1/S2 removal, cleanup)
- Alternative note generation (COT ignored, <=1 hypotheses, >1 hypotheses)
- Risk warning generation (CRITICAL, HIGH, MEDIUM, LOW, None)
- Summary generation (COT 0/1/N sources, TOT 0-1/N hypotheses)
- Full transform pipeline with options
- transform_to_dual returning DualReasoning
- Singleton get_reasoning_transformer / reset_transformer
- TransformOptions dataclass defaults and custom values
"""

import pytest

from app.schemas.reasoning import (
    DualReasoning,
    InternalReasoning,
    PublicExplanation,
    ReasoningType,
    RiskLevel,
)
from app.services.reasoning_transformer import (
    ALTERNATIVE_NOTE_TEMPLATE,
    COT_SUMMARY_MULTIPLE_SOURCES,
    COT_SUMMARY_NO_SOURCES,
    COT_SUMMARY_ONE_SOURCE,
    RISK_WARNING_CRITICAL,
    RISK_WARNING_HIGH,
    TOT_SUMMARY_MULTIPLE,
    TOT_SUMMARY_SINGLE,
    ReasoningTransformer,
    TransformOptions,
    get_reasoning_transformer,
    reset_transformer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_internal(
    reasoning_type: str = ReasoningType.COT.value,
    theme: str = "Calcolo IVA",
    sources_used: list | None = None,
    confidence: float | None = 0.85,
    hypotheses: list | None = None,
    selected_hypothesis: str | None = None,
    selection_reasoning: str | None = None,
    risk_level: str | None = None,
) -> InternalReasoning:
    return InternalReasoning(
        reasoning_type=reasoning_type,
        theme=theme,
        sources_used=sources_used if sources_used is not None else [],
        key_elements=["elem"],
        conclusion="Conclusione",
        hypotheses=hypotheses,
        selected_hypothesis=selected_hypothesis,
        selection_reasoning=selection_reasoning,
        confidence=confidence,
        risk_level=risk_level,
    )


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Ensure singleton is clean before each test."""
    reset_transformer()
    yield
    reset_transformer()


# ===========================================================================
# Confidence mapping
# ===========================================================================


class TestMapConfidence:
    """Tests for map_confidence covering all thresholds and edge cases."""

    def test_high_confidence(self):
        t = ReasoningTransformer()
        assert t.map_confidence(0.85) == "alta"

    def test_boundary_high_exactly_0_8(self):
        t = ReasoningTransformer()
        assert t.map_confidence(0.8) == "alta"

    def test_just_below_high(self):
        t = ReasoningTransformer()
        assert t.map_confidence(0.79) == "media"

    def test_medium_confidence(self):
        t = ReasoningTransformer()
        assert t.map_confidence(0.6) == "media"

    def test_boundary_medium_exactly_0_5(self):
        t = ReasoningTransformer()
        assert t.map_confidence(0.5) == "media"

    def test_just_below_medium(self):
        t = ReasoningTransformer()
        assert t.map_confidence(0.49) == "bassa"

    def test_low_confidence(self):
        t = ReasoningTransformer()
        assert t.map_confidence(0.3) == "bassa"

    def test_zero_confidence(self):
        t = ReasoningTransformer()
        assert t.map_confidence(0.0) == "bassa"

    def test_none_confidence(self):
        t = ReasoningTransformer()
        assert t.map_confidence(None) == "non disponibile"

    def test_max_confidence_1_0(self):
        t = ReasoningTransformer()
        assert t.map_confidence(1.0) == "alta"


# ===========================================================================
# Source simplification / extraction
# ===========================================================================


class TestSimplifySourcesAndExtract:
    """Tests for simplify_sources and _extract_source_title."""

    def test_empty_list(self):
        t = ReasoningTransformer()
        assert t.simplify_sources([]) == []

    def test_string_sources(self):
        t = ReasoningTransformer()
        result = t.simplify_sources(["DPR 633/72", "Art. 16"])
        assert result == ["DPR 633/72", "Art. 16"]

    def test_dict_with_title(self):
        t = ReasoningTransformer()
        result = t.simplify_sources([{"id": "S1", "title": "DPR 633/72"}])
        assert result == ["DPR 633/72"]

    def test_dict_with_ref_fallback(self):
        t = ReasoningTransformer()
        result = t.simplify_sources([{"ref": "Legge 190/2014"}])
        assert result == ["Legge 190/2014"]

    def test_dict_with_id_fallback(self):
        t = ReasoningTransformer()
        result = t.simplify_sources([{"id": "S42"}])
        assert result == ["S42"]

    def test_dict_empty_title_empty_ref_empty_id(self):
        t = ReasoningTransformer()
        result = t.simplify_sources([{"title": "", "ref": "", "id": ""}])
        assert result == []

    def test_dict_no_relevant_keys(self):
        t = ReasoningTransformer()
        result = t.simplify_sources([{"content": "something"}])
        assert result == []

    def test_max_count_truncation_without_suffix(self):
        t = ReasoningTransformer()
        sources = ["A", "B", "C", "D", "E"]
        result = t.simplify_sources(sources, max_count=3, add_suffix=False)
        assert result == ["A", "B", "C"]

    def test_max_count_with_suffix(self):
        t = ReasoningTransformer()
        sources = ["A", "B", "C", "D", "E"]
        result = t.simplify_sources(sources, max_count=2, add_suffix=True)
        assert result == ["A", "B", "e altre 3 fonti"]

    def test_max_count_no_truncation_needed(self):
        t = ReasoningTransformer()
        sources = ["A", "B"]
        result = t.simplify_sources(sources, max_count=5, add_suffix=True)
        assert result == ["A", "B"]

    def test_max_count_equal_to_length(self):
        t = ReasoningTransformer()
        sources = ["A", "B", "C"]
        result = t.simplify_sources(sources, max_count=3, add_suffix=True)
        assert result == ["A", "B", "C"]

    def test_max_count_none_returns_all(self):
        t = ReasoningTransformer()
        sources = ["A", "B", "C"]
        result = t.simplify_sources(sources, max_count=None, add_suffix=True)
        assert result == ["A", "B", "C"]

    def test_mixed_dict_and_string_sources(self):
        t = ReasoningTransformer()
        sources = [{"title": "DPR 633/72"}, "Art. 16", {"ref": "TUIR"}]
        result = t.simplify_sources(sources)
        assert result == ["DPR 633/72", "Art. 16", "TUIR"]

    def test_extract_source_title_non_dict_non_str(self):
        """Non-dict, non-str types return empty string."""
        t = ReasoningTransformer()
        assert t._extract_source_title(12345) == ""  # type: ignore[arg-type]

    def test_extract_source_title_none_type(self):
        t = ReasoningTransformer()
        assert t._extract_source_title(None) == ""  # type: ignore[arg-type]

    def test_extract_source_title_title_priority_over_ref_and_id(self):
        t = ReasoningTransformer()
        result = t._extract_source_title({"title": "T", "ref": "R", "id": "I"})
        assert result == "T"

    def test_extract_source_title_ref_priority_over_id(self):
        t = ReasoningTransformer()
        result = t._extract_source_title({"ref": "R", "id": "I"})
        assert result == "R"

    def test_extract_source_title_numeric_title(self):
        """Title value is numeric; should still convert to string."""
        t = ReasoningTransformer()
        result = t._extract_source_title({"title": 42})
        assert result == "42"

    def test_simplify_sources_filters_empty_titles(self):
        """Dicts with only falsy values produce no entries."""
        t = ReasoningTransformer()
        result = t.simplify_sources([{"title": None, "ref": None}, {"title": "OK"}])
        assert result == ["OK"]


# ===========================================================================
# Selection reasoning transformation
# ===========================================================================


class TestTransformSelectionReasoning:
    """Tests for transform_selection_reasoning."""

    def test_none_returns_none(self):
        t = ReasoningTransformer()
        assert t.transform_selection_reasoning(None) is None

    def test_empty_returns_empty(self):
        t = ReasoningTransformer()
        assert t.transform_selection_reasoning("") == ""

    def test_removes_single_source_id(self):
        t = ReasoningTransformer()
        result = t.transform_selection_reasoning("Source S1 explicitly states 20%")
        assert "S1" not in result
        assert "20%" in result

    def test_removes_multiple_source_ids(self):
        t = ReasoningTransformer()
        result = t.transform_selection_reasoning("S1 and S2 both confirm the rule from S3")
        assert "S1" not in result
        assert "S2" not in result
        assert "S3" not in result
        assert "confirm" in result

    def test_removes_large_source_id_numbers(self):
        t = ReasoningTransformer()
        result = t.transform_selection_reasoning("According to S123 the rule applies")
        assert "S123" not in result

    def test_cleans_double_spaces(self):
        t = ReasoningTransformer()
        result = t.transform_selection_reasoning("Based on S1  the answer is clear")
        assert "  " not in result

    def test_cleans_leading_comma(self):
        t = ReasoningTransformer()
        result = t.transform_selection_reasoning(", S1 confirms the rule")
        assert not result.startswith(",")

    def test_cleans_consecutive_commas(self):
        t = ReasoningTransformer()
        result = t.transform_selection_reasoning("S1, , S2 confirm")
        assert ",," not in result
        assert ", ," not in result

    def test_plain_italian_text_unchanged(self):
        t = ReasoningTransformer()
        text = "La norma principale indica chiaramente il 22%"
        result = t.transform_selection_reasoning(text)
        assert result == text

    def test_only_source_ids_produces_empty_or_cleaned(self):
        t = ReasoningTransformer()
        result = t.transform_selection_reasoning("S1 S2 S3")
        # After removing all IDs and cleaning spaces, should be stripped
        assert result == ""

    def test_preserves_non_source_s_patterns(self):
        """'S' followed by non-digits should not be removed."""
        t = ReasoningTransformer()
        result = t.transform_selection_reasoning("Secondo la norma principale")
        assert "Secondo" in result


# ===========================================================================
# Alternative note generation
# ===========================================================================


class TestGenerateAlternativeNote:
    """Tests for generate_alternative_note."""

    def test_cot_returns_none_even_with_hypotheses(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.COT.value,
            hypotheses=["H1", "H2", "H3"],
        )
        assert t.generate_alternative_note(internal) is None

    def test_tot_no_hypotheses_returns_none(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=None,
        )
        assert t.generate_alternative_note(internal) is None

    def test_tot_empty_hypotheses_returns_none(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=[],
        )
        assert t.generate_alternative_note(internal) is None

    def test_tot_single_hypothesis_returns_none(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=[{"id": "H1"}],
        )
        assert t.generate_alternative_note(internal) is None

    def test_tot_two_hypotheses_returns_note_with_1(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=[{"id": "H1"}, {"id": "H2"}],
        )
        note = t.generate_alternative_note(internal)
        assert note is not None
        assert "1" in note
        assert "interpretazioni alternative" in note

    def test_tot_three_hypotheses_returns_note_with_2(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=[{"id": "H1"}, {"id": "H2"}, {"id": "H3"}],
        )
        note = t.generate_alternative_note(internal)
        assert note is not None
        assert "2" in note

    def test_tot_five_hypotheses_returns_note_with_4(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=[{"id": f"H{i}"} for i in range(5)],
        )
        note = t.generate_alternative_note(internal)
        assert note is not None
        assert "4" in note

    def test_note_matches_template_format(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=[{"id": "H1"}, {"id": "H2"}, {"id": "H3"}],
        )
        note = t.generate_alternative_note(internal)
        expected = ALTERNATIVE_NOTE_TEMPLATE.format(count=2)
        assert note == expected


# ===========================================================================
# Risk warning generation
# ===========================================================================


class TestGenerateRiskWarning:
    """Tests for generate_risk_warning."""

    def test_critical_risk_returns_critical_warning(self):
        t = ReasoningTransformer()
        internal = _make_internal(risk_level=RiskLevel.CRITICAL.value)
        warning = t.generate_risk_warning(internal)
        assert warning == RISK_WARNING_CRITICAL
        assert "sanzioni penali" in warning

    def test_high_risk_returns_high_warning(self):
        t = ReasoningTransformer()
        internal = _make_internal(risk_level=RiskLevel.HIGH.value)
        warning = t.generate_risk_warning(internal)
        assert warning == RISK_WARNING_HIGH
        assert "rischi sanzionatori elevati" in warning

    def test_medium_risk_returns_none(self):
        t = ReasoningTransformer()
        internal = _make_internal(risk_level=RiskLevel.MEDIUM.value)
        assert t.generate_risk_warning(internal) is None

    def test_low_risk_returns_none(self):
        t = ReasoningTransformer()
        internal = _make_internal(risk_level=RiskLevel.LOW.value)
        assert t.generate_risk_warning(internal) is None

    def test_none_risk_returns_none(self):
        t = ReasoningTransformer()
        internal = _make_internal(risk_level=None)
        assert t.generate_risk_warning(internal) is None

    def test_unknown_risk_string_returns_none(self):
        t = ReasoningTransformer()
        internal = _make_internal(risk_level="unknown")
        assert t.generate_risk_warning(internal) is None


# ===========================================================================
# Summary generation
# ===========================================================================


class TestGenerateSummary:
    """Tests for generate_summary (COT and TOT paths)."""

    def test_cot_no_sources_uses_theme(self):
        t = ReasoningTransformer()
        internal = _make_internal(sources_used=[], theme="Detrazione IVA")
        summary = t.generate_summary(internal)
        assert "Detrazione IVA" in summary
        expected = COT_SUMMARY_NO_SOURCES.format(theme="Detrazione IVA")
        assert summary == expected

    def test_cot_no_sources_none_theme_falls_back_to_richiesta(self):
        t = ReasoningTransformer()
        internal = _make_internal(sources_used=[], theme=None)
        summary = t.generate_summary(internal)
        assert "richiesta" in summary

    def test_cot_one_source(self):
        t = ReasoningTransformer()
        internal = _make_internal(sources_used=[{"title": "Art. 1"}])
        summary = t.generate_summary(internal)
        assert summary == COT_SUMMARY_ONE_SOURCE

    def test_cot_two_sources(self):
        t = ReasoningTransformer()
        internal = _make_internal(sources_used=[{"title": "A"}, {"title": "B"}])
        summary = t.generate_summary(internal)
        expected = COT_SUMMARY_MULTIPLE_SOURCES.format(count=2)
        assert summary == expected

    def test_cot_many_sources(self):
        t = ReasoningTransformer()
        internal = _make_internal(sources_used=[{"title": f"S{i}"} for i in range(10)])
        summary = t.generate_summary(internal)
        assert "10" in summary
        assert "fonti normative" in summary

    def test_tot_no_hypotheses(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=None,
        )
        summary = t.generate_summary(internal)
        assert summary == TOT_SUMMARY_SINGLE

    def test_tot_empty_hypotheses(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=[],
        )
        summary = t.generate_summary(internal)
        assert summary == TOT_SUMMARY_SINGLE

    def test_tot_single_hypothesis(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=[{"id": "H1"}],
        )
        summary = t.generate_summary(internal)
        assert summary == TOT_SUMMARY_SINGLE

    def test_tot_multiple_hypotheses(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=[{"id": "H1"}, {"id": "H2"}, {"id": "H3"}],
        )
        summary = t.generate_summary(internal)
        expected = TOT_SUMMARY_MULTIPLE.format(count=3)
        assert summary == expected

    def test_unknown_reasoning_type_defaults_to_cot_summary(self):
        """If reasoning_type is not TOT, _generate_cot_summary is used."""
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type="unknown_type",
            sources_used=[{"title": "A"}],
        )
        summary = t.generate_summary(internal)
        assert summary == COT_SUMMARY_ONE_SOURCE


# ===========================================================================
# Full transform pipeline
# ===========================================================================


class TestTransform:
    """Tests for the full transform method."""

    def test_basic_cot_transform(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            sources_used=[{"title": "DPR 633/72"}, {"title": "TUIR"}],
            confidence=0.9,
        )
        result = t.transform(internal)
        assert isinstance(result, PublicExplanation)
        assert result.confidence_label == "alta"
        assert "DPR 633/72" in result.main_sources
        assert "TUIR" in result.main_sources
        assert result.selected_scenario is None
        assert result.risk_warning is None
        assert result.alternative_note is None

    def test_tot_transform_with_selected_scenario(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=[{"id": "H1"}, {"id": "H2"}, {"id": "H3"}],
            selected_hypothesis="H2",
            selection_reasoning="S1 and S2 confirm this interpretation",
            confidence=0.7,
        )
        result = t.transform(internal)
        assert result.selected_scenario == "H2"
        assert result.confidence_label == "media"
        assert result.alternative_note is not None
        # Source IDs should be removed from why_selected
        assert "S1" not in (result.why_selected or "")
        assert "S2" not in (result.why_selected or "")

    def test_cot_transform_no_selected_scenario(self):
        """COT reasoning should never set selected_scenario."""
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.COT.value,
            selected_hypothesis="H1",  # set even though COT
        )
        result = t.transform(internal)
        assert result.selected_scenario is None

    def test_transform_with_critical_risk_warning(self):
        t = ReasoningTransformer()
        internal = _make_internal(risk_level=RiskLevel.CRITICAL.value)
        result = t.transform(internal)
        assert result.risk_warning is not None
        assert "sanzioni penali" in result.risk_warning

    def test_transform_with_high_risk_warning(self):
        t = ReasoningTransformer()
        internal = _make_internal(risk_level=RiskLevel.HIGH.value)
        result = t.transform(internal)
        assert result.risk_warning is not None
        assert "rischi sanzionatori elevati" in result.risk_warning

    def test_transform_no_risk_warning_for_medium(self):
        t = ReasoningTransformer()
        internal = _make_internal(risk_level=RiskLevel.MEDIUM.value)
        result = t.transform(internal)
        assert result.risk_warning is None

    def test_transform_options_max_sources(self):
        t = ReasoningTransformer()
        internal = _make_internal(sources_used=["A", "B", "C", "D", "E"])
        options = TransformOptions(max_sources=2, add_source_suffix=True)
        result = t.transform(internal, options)
        assert len(result.main_sources) == 3  # 2 + suffix entry
        assert "e altre 3 fonti" in result.main_sources[-1]

    def test_transform_options_disable_alternative_note(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=[{"id": "H1"}, {"id": "H2"}, {"id": "H3"}],
        )
        options = TransformOptions(include_alternative_note=False)
        result = t.transform(internal, options)
        assert result.alternative_note is None

    def test_transform_options_disable_risk_warning(self):
        t = ReasoningTransformer()
        internal = _make_internal(risk_level=RiskLevel.CRITICAL.value)
        options = TransformOptions(include_risk_warning=False)
        result = t.transform(internal, options)
        assert result.risk_warning is None

    def test_transform_default_options_when_none_passed(self):
        t = ReasoningTransformer()
        internal = _make_internal()
        result = t.transform(internal, None)
        assert isinstance(result, PublicExplanation)

    def test_transform_selection_reasoning_none(self):
        t = ReasoningTransformer()
        internal = _make_internal(selection_reasoning=None)
        result = t.transform(internal)
        assert result.why_selected is None

    def test_transform_selection_reasoning_empty(self):
        t = ReasoningTransformer()
        internal = _make_internal(selection_reasoning="")
        result = t.transform(internal)
        assert result.why_selected == ""

    def test_transform_tot_without_hypotheses(self):
        """TOT without hypotheses still works and produces single summary."""
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            hypotheses=None,
            selected_hypothesis="H1",
        )
        result = t.transform(internal)
        assert result.selected_scenario == "H1"
        assert result.alternative_note is None


# ===========================================================================
# transform_to_dual
# ===========================================================================


class TestTransformToDual:
    """Tests for transform_to_dual."""

    def test_returns_dual_reasoning(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            sources_used=[{"title": "Art. 1"}],
            confidence=0.9,
        )
        dual = t.transform_to_dual(internal)
        assert isinstance(dual, DualReasoning)
        assert dual.internal is internal
        assert isinstance(dual.public, PublicExplanation)
        assert dual.public.confidence_label == "alta"

    def test_dual_with_options(self):
        t = ReasoningTransformer()
        internal = _make_internal(
            sources_used=["A", "B", "C", "D"],
            risk_level=RiskLevel.HIGH.value,
        )
        options = TransformOptions(max_sources=1, include_risk_warning=True)
        dual = t.transform_to_dual(internal, options)
        assert dual.public.risk_warning is not None
        # 1 source + suffix
        assert len(dual.public.main_sources) == 2

    def test_dual_public_summary_matches_transform(self):
        t = ReasoningTransformer()
        internal = _make_internal(sources_used=[{"title": "X"}])
        direct = t.transform(internal)
        dual = t.transform_to_dual(internal)
        assert dual.public.summary == direct.summary

    def test_dual_preserves_internal_reference(self):
        t = ReasoningTransformer()
        internal = _make_internal()
        dual = t.transform_to_dual(internal)
        assert dual.internal is internal

    def test_dual_with_none_options(self):
        t = ReasoningTransformer()
        internal = _make_internal()
        dual = t.transform_to_dual(internal, None)
        assert isinstance(dual, DualReasoning)

    def test_dual_has_created_at(self):
        t = ReasoningTransformer()
        internal = _make_internal()
        dual = t.transform_to_dual(internal)
        assert dual.created_at is not None


# ===========================================================================
# Singleton factory functions
# ===========================================================================


class TestSingleton:
    """Tests for get_reasoning_transformer and reset_transformer."""

    def test_get_returns_instance(self):
        instance = get_reasoning_transformer()
        assert isinstance(instance, ReasoningTransformer)

    def test_get_returns_same_instance(self):
        a = get_reasoning_transformer()
        b = get_reasoning_transformer()
        assert a is b

    def test_reset_creates_new_instance(self):
        a = get_reasoning_transformer()
        reset_transformer()
        b = get_reasoning_transformer()
        assert a is not b

    def test_multiple_resets(self):
        reset_transformer()
        reset_transformer()
        instance = get_reasoning_transformer()
        assert isinstance(instance, ReasoningTransformer)


# ===========================================================================
# TransformOptions dataclass
# ===========================================================================


class TestTransformOptions:
    """Tests for TransformOptions default values."""

    def test_defaults(self):
        opts = TransformOptions()
        assert opts.max_sources is None
        assert opts.add_source_suffix is True
        assert opts.include_alternative_note is True
        assert opts.include_risk_warning is True

    def test_custom_values(self):
        opts = TransformOptions(
            max_sources=5,
            add_source_suffix=False,
            include_alternative_note=False,
            include_risk_warning=False,
        )
        assert opts.max_sources == 5
        assert opts.add_source_suffix is False
        assert opts.include_alternative_note is False
        assert opts.include_risk_warning is False

    def test_partial_override(self):
        opts = TransformOptions(max_sources=3)
        assert opts.max_sources == 3
        assert opts.add_source_suffix is True
        assert opts.include_alternative_note is True


# ===========================================================================
# Edge cases and integration
# ===========================================================================


class TestEdgeCases:
    """Edge cases to ensure robust coverage."""

    def test_transform_with_all_options_enabled(self):
        """Full pipeline with TOT, risk, alternatives, source limits."""
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT.value,
            sources_used=[
                {"title": "DPR 633/72"},
                {"title": "TUIR"},
                {"title": "Art. 16"},
                {"title": "Circolare 12/E"},
            ],
            confidence=0.45,
            hypotheses=[{"id": "H1"}, {"id": "H2"}, {"id": "H3"}],
            selected_hypothesis="H1",
            selection_reasoning="S1 is the primary S2 reference",
            risk_level=RiskLevel.CRITICAL.value,
        )
        options = TransformOptions(
            max_sources=2,
            add_source_suffix=True,
            include_alternative_note=True,
            include_risk_warning=True,
        )
        result = t.transform(internal, options)
        assert result.confidence_label == "bassa"
        assert result.selected_scenario == "H1"
        assert result.alternative_note is not None
        assert result.risk_warning is not None
        assert len(result.main_sources) == 3  # 2 + suffix
        assert "S1" not in (result.why_selected or "")

    def test_transform_with_tot_multi_domain_type(self):
        """tot_multi_domain should use TOT path."""
        t = ReasoningTransformer()
        internal = _make_internal(
            reasoning_type=ReasoningType.TOT_MULTI_DOMAIN.value,
            hypotheses=[{"id": "H1"}, {"id": "H2"}],
            selected_hypothesis="H1",
        )
        result = t.transform(internal)
        # TOT_MULTI_DOMAIN is not == TOT.value, so it goes COT path
        # for summary, but selected_scenario is None (not TOT.value)
        assert result.selected_scenario is None

    def test_simplify_sources_with_single_source_and_max_count_1(self):
        t = ReasoningTransformer()
        result = t.simplify_sources(["Only One"], max_count=1, add_suffix=True)
        assert result == ["Only One"]

    def test_source_id_pattern_does_not_match_non_digit_suffix(self):
        t = ReasoningTransformer()
        result = t.transform_selection_reasoning("Secondo art. 16")
        assert "Secondo" in result
        assert "art. 16" in result
