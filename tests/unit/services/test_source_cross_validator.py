"""TDD tests for SourceCrossValidator service.

DEV-242: Tests written FIRST per TDD methodology.
Tests cover source cross-validation, KB matching, and date validation.
"""

import pytest

from app.services.source_cross_validator import (
    CrossValidationResult,
    SourceCrossValidator,
    SourceValidationResult,
)


class TestSourceValidationResult:
    """Test SourceValidationResult dataclass."""

    def test_valid_result_creation(self):
        """Valid result can be created with matched doc."""
        result = SourceValidationResult(
            is_valid=True,
            matched_kb_doc={"title": "DPR 633/72"},
        )
        assert result.is_valid is True
        assert result.matched_kb_doc is not None
        assert result.warning is None

    def test_invalid_result_with_warning(self):
        """Invalid result includes warning."""
        result = SourceValidationResult(
            is_valid=False,
            warning="Fonte non trovata",
        )
        assert result.is_valid is False
        assert result.warning == "Fonte non trovata"


class TestCrossValidationResult:
    """Test CrossValidationResult dataclass."""

    def test_result_creation_with_all_fields(self):
        """Result can be created with all fields."""
        result = CrossValidationResult(
            is_valid=True,
            validated_sources=[{"ref": "Art. 16 DPR 633/72"}],
            unmatched_sources=[],
            warnings=["Test warning"],
            requires_web_fallback=False,
            kb_was_empty=False,
        )
        assert result.is_valid is True
        assert len(result.validated_sources) == 1
        assert result.requires_web_fallback is False


class TestValidateSources:
    """Test validate_sources method."""

    @pytest.fixture
    def validator(self):
        return SourceCrossValidator()

    @pytest.fixture
    def kb_sources(self):
        return [
            {
                "title": "DPR 633/72 - IVA",
                "reference": "DPR 633/72",
                "doc_type": "decreto",
                "key_topics": ["IVA", "aliquote"],
            },
            {
                "title": "D.Lgs. 81/2008 - Sicurezza lavoro",
                "reference": "D.Lgs. 81/2008",
                "doc_type": "decreto legislativo",
                "key_topics": ["sicurezza", "lavoro"],
            },
            {
                "title": "Circolare AdE n. 12/E del 2024",
                "reference": "Circolare 12/E/2024",
                "doc_type": "circolare",
                "key_topics": ["chiarimenti", "IVA"],
            },
        ]

    def test_validates_matching_source(self, validator, kb_sources):
        """Source matching KB is validated."""
        sources_cited = [
            {"ref": "Art. 16 DPR 633/72", "relevance": "principale"},
        ]
        result = validator.validate_sources(sources_cited, kb_sources)

        assert result.is_valid is True
        assert len(result.validated_sources) == 1
        assert len(result.unmatched_sources) == 0

    def test_flags_unmatched_source(self, validator, kb_sources):
        """Source not in KB is flagged."""
        sources_cited = [
            {"ref": "Legge 234/2023 - Non esiste", "relevance": "principale"},
        ]
        result = validator.validate_sources(sources_cited, kb_sources)

        assert len(result.unmatched_sources) == 1
        assert len(result.warnings) >= 1

    def test_empty_kb_triggers_warning(self, validator):
        """Empty KB sources triggers warning and web fallback."""
        sources_cited = [
            {"ref": "Art. 16 DPR 633/72", "relevance": "principale"},
        ]
        result = validator.validate_sources(sources_cited, [])

        assert result.kb_was_empty is True
        assert result.requires_web_fallback is True
        assert any("database" in w.lower() for w in result.warnings)

    def test_no_sources_with_empty_kb_is_valid(self, validator):
        """No sources cited with empty KB is acceptable."""
        result = validator.validate_sources([], [])

        assert result.is_valid is True
        assert result.kb_was_empty is True

    def test_no_sources_with_full_kb_is_valid(self, validator, kb_sources):
        """No sources cited with available KB is valid."""
        result = validator.validate_sources([], kb_sources)

        assert result.is_valid is False  # Should cite available sources
        assert len(result.validated_sources) == 0

    def test_partial_match_reports_both(self, validator, kb_sources):
        """Some sources matched, some not - reports both."""
        sources_cited = [
            {"ref": "Art. 16 DPR 633/72", "relevance": "principale"},
            {"ref": "Legge inventata 999/2099", "relevance": "secondario"},
        ]
        result = validator.validate_sources(sources_cited, kb_sources)

        assert len(result.validated_sources) == 1
        assert len(result.unmatched_sources) == 1
        assert result.is_valid is True  # Partial match is okay

    def test_validates_circolare_reference(self, validator, kb_sources):
        """Circolare references are matched correctly."""
        sources_cited = [
            {"ref": "Circolare AdE n. 12/E del 2024", "relevance": "principale"},
        ]
        result = validator.validate_sources(sources_cited, kb_sources)

        assert len(result.validated_sources) == 1

    def test_validates_dlgs_reference(self, validator, kb_sources):
        """D.Lgs. references are matched correctly."""
        sources_cited = [
            {"ref": "Art. 2, D.Lgs. 81/2008", "relevance": "principale"},
        ]
        result = validator.validate_sources(sources_cited, kb_sources)

        assert len(result.validated_sources) == 1


class TestExtractRefComponents:
    """Test _extract_ref_components method."""

    @pytest.fixture
    def validator(self):
        return SourceCrossValidator()

    def test_extracts_article_number(self, validator):
        """Extracts article number from reference."""
        components = validator._extract_ref_components("Art. 16 DPR 633/72")
        assert components["article"] == "16"

    def test_extracts_law_type_dpr(self, validator):
        """Extracts DPR law type."""
        components = validator._extract_ref_components("Art. 16 DPR 633/72")
        assert "DPR" in components.get("law_type", "")

    def test_extracts_law_type_dlgs(self, validator):
        """Extracts D.Lgs. law type."""
        components = validator._extract_ref_components("Art. 2 D.Lgs. 81/2008")
        assert "Lgs" in components.get("law_type", "")

    def test_extracts_law_number_and_year(self, validator):
        """Extracts law number and year."""
        components = validator._extract_ref_components("DPR 633/72")
        assert components["law_number"] == "633"
        assert components["year"] == "72"

    def test_extracts_full_year(self, validator):
        """Extracts full year format."""
        components = validator._extract_ref_components("D.Lgs. 81/2008")
        assert components["year"] == "2008"

    def test_extracts_circolare_number(self, validator):
        """Extracts circolare number."""
        components = validator._extract_ref_components("Circolare AdE n. 12/E del 2024")
        assert components.get("circolare_number") == "12"
        assert components.get("is_circolare") is True

    def test_handles_complex_reference(self, validator):
        """Handles complex multi-part references."""
        components = validator._extract_ref_components("Art. 16, comma 3, lett. a) DPR 633/1972")
        assert components["article"] == "16"
        assert components["law_number"] == "633"


class TestMatchesKbSource:
    """Test _matches_kb_source method."""

    @pytest.fixture
    def validator(self):
        return SourceCrossValidator()

    def test_matches_by_law_number_and_year(self, validator):
        """Matches by law number and year."""
        ref_components = {
            "original": "DPR 633/72",
            "law_number": "633",
            "year": "72",
        }
        kb_source = {
            "title": "DPR 633/72 - Disciplina IVA",
            "reference": "DPR 633/72",
        }
        assert validator._matches_kb_source(ref_components, kb_source) is True

    def test_matches_by_article_in_title(self, validator):
        """Matches by article number in title."""
        ref_components = {
            "original": "Art. 16",
            "article": "16",
        }
        kb_source = {
            "title": "Art. 16 - Aliquote IVA",
            "reference": "",
        }
        assert validator._matches_kb_source(ref_components, kb_source) is True

    def test_matches_by_key_topics(self, validator):
        """Matches by key topics."""
        ref_components = {
            "original": "normativa iva",
        }
        kb_source = {
            "title": "Decreto IVA",
            "reference": "",
            "key_topics": ["IVA", "imposte"],
        }
        assert validator._matches_kb_source(ref_components, kb_source) is True

    def test_no_match_for_unrelated_source(self, validator):
        """No match for completely unrelated source."""
        ref_components = {
            "original": "Legge 123/2099",
            "law_number": "123",
            "year": "2099",
        }
        kb_source = {
            "title": "DPR 633/72",
            "reference": "DPR 633/72",
            "key_topics": ["IVA"],
        }
        assert validator._matches_kb_source(ref_components, kb_source) is False


class TestValidateDatesInResponse:
    """Test validate_dates_in_response method."""

    @pytest.fixture
    def validator(self):
        return SourceCrossValidator()

    @pytest.fixture
    def kb_sources(self):
        return [
            {
                "title": "Legge di bilancio 2026",
                "reference": "Legge 207/2025",
            },
        ]

    def test_no_warning_for_current_year(self, validator, kb_sources):
        """No warning for current year dates."""
        response = "La scadenza è prevista per il 2026."
        warnings = validator.validate_dates_in_response(response, kb_sources, 2026)
        assert len(warnings) == 0

    def test_no_warning_for_kb_grounded_year(self, validator, kb_sources):
        """No warning for years found in KB."""
        response = "Come previsto dalla Legge 207/2025..."
        warnings = validator.validate_dates_in_response(response, kb_sources, 2026)
        assert len(warnings) == 0

    def test_warning_for_old_ungrounded_year(self, validator, kb_sources):
        """Warning for old year not in KB."""
        response = "La scadenza era nel 2023."
        warnings = validator.validate_dates_in_response(response, kb_sources, 2026)
        assert len(warnings) >= 1
        assert any("2023" in w for w in warnings)

    def test_no_warning_for_previous_year(self, validator, kb_sources):
        """No warning for previous year (within tolerance)."""
        response = "Come accaduto nel 2025..."
        warnings = validator.validate_dates_in_response(response, kb_sources, 2026)
        assert len(warnings) == 0

    def test_warning_for_invented_future_year(self, validator, kb_sources):
        """Warning for far future year not grounded."""
        response = "La scadenza sarà nel 2030."
        warnings = validator.validate_dates_in_response(response, kb_sources, 2026)
        assert len(warnings) >= 1
        assert any("2030" in w for w in warnings)


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def validator(self):
        return SourceCrossValidator()

    def test_handles_none_sources(self, validator):
        """Handles None sources gracefully."""
        result = validator.validate_sources(None, [])  # type: ignore
        assert result.is_valid is True  # Empty is okay with empty KB

    def test_handles_source_without_ref(self, validator):
        """Handles source dict without ref field."""
        sources_cited = [{"relevance": "principale"}]  # Missing ref
        result = validator.validate_sources(sources_cited, [])

        assert len(result.unmatched_sources) == 1
        assert any("senza riferimento" in w for w in result.warnings)

    def test_handles_empty_ref(self, validator):
        """Handles empty ref string."""
        sources_cited = [{"ref": "", "relevance": "principale"}]
        result = validator.validate_sources(sources_cited, [])

        assert len(result.unmatched_sources) == 1

    def test_handles_kb_source_without_title(self, validator):
        """Handles KB source without title field."""
        sources_cited = [{"ref": "Test ref"}]
        kb_sources = [{"reference": "something"}]  # No title

        # Should not raise exception
        result = validator.validate_sources(sources_cited, kb_sources)
        assert result is not None

    def test_handles_special_characters_in_ref(self, validator):
        """Handles special characters in reference."""
        sources_cited = [
            {"ref": "Art. 16, comma 3, lett. a) DPR n. 633/72"},
        ]
        kb_sources = [
            {"title": "DPR 633/72", "reference": "DPR 633/72"},
        ]
        result = validator.validate_sources(sources_cited, kb_sources)

        assert len(result.validated_sources) == 1


class TestIntegration:
    """Integration tests for complete validation flow."""

    @pytest.fixture
    def validator(self):
        return SourceCrossValidator()

    def test_full_validation_with_mixed_results(self, validator):
        """Full validation with some valid and some invalid sources."""
        kb_sources = [
            {
                "title": "DPR 633/72 - IVA",
                "reference": "DPR 633/72",
                "key_topics": ["IVA"],
            },
        ]
        sources_cited = [
            {"ref": "Art. 16 DPR 633/72", "relevance": "principale"},
            {"ref": "Legge inesistente 999/2099", "relevance": "secondario"},
        ]
        response = "L'aliquota IVA è del 22% dal 2023."

        # Validate sources
        source_result = validator.validate_sources(sources_cited, kb_sources)
        assert source_result.is_valid is True
        assert len(source_result.validated_sources) == 1
        assert len(source_result.unmatched_sources) == 1

        # Validate dates
        date_warnings = validator.validate_dates_in_response(response, kb_sources, current_year=2026)
        assert any("2023" in w for w in date_warnings)

    def test_empty_kb_full_flow(self, validator):
        """Full flow with empty KB."""
        sources_cited = [
            {"ref": "Rottamazione quinquies - Legge 207/2025"},
        ]
        response = "La rottamazione quinquies prevede scadenze nel 2026."

        result = validator.validate_sources(sources_cited, [])

        assert result.kb_was_empty is True
        assert result.requires_web_fallback is True
        assert len(result.warnings) >= 1
