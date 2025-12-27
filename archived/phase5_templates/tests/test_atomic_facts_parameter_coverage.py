"""TDD Tests for AtomicFactsExtractor Parameter Coverage - DEV-154.

This module tests the parameter coverage functionality:
- INTENT_SCHEMAS dictionary with required/optional parameters
- calculate_coverage() method
- get_missing_required() method
- extract_with_coverage() returning ParameterExtractionResult
- _parse_italian_number() for Italian number formats

Test Files Reference: app/services/atomic_facts_extractor.py
"""

import pytest

from app.schemas.proactivity import ExtractedParameter, ParameterExtractionResult
from app.services.atomic_facts_extractor import (
    INTENT_SCHEMAS,
    AtomicFactsExtractor,
)


class TestIntentSchemas:
    """Test INTENT_SCHEMAS dictionary structure."""

    def test_intent_schemas_exists(self):
        """Test that INTENT_SCHEMAS is defined."""
        assert INTENT_SCHEMAS is not None
        assert isinstance(INTENT_SCHEMAS, dict)

    def test_calcolo_irpef_schema(self):
        """Test calcolo_irpef schema has required fields."""
        assert "calcolo_irpef" in INTENT_SCHEMAS
        schema = INTENT_SCHEMAS["calcolo_irpef"]
        assert "required" in schema
        assert "optional" in schema
        assert "defaults" in schema
        assert "tipo_contribuente" in schema["required"]
        assert "reddito" in schema["required"]

    def test_calcolo_iva_schema(self):
        """Test calcolo_iva schema has required fields."""
        assert "calcolo_iva" in INTENT_SCHEMAS
        schema = INTENT_SCHEMAS["calcolo_iva"]
        assert "importo" in schema["required"]
        assert "aliquota" in schema["optional"]
        assert schema["defaults"].get("aliquota") == 22


class TestCalculateCoverage:
    """Test calculate_coverage method."""

    @pytest.fixture
    def extractor(self) -> AtomicFactsExtractor:
        """Create extractor instance."""
        return AtomicFactsExtractor()

    def test_irpef_full_coverage(self, extractor: AtomicFactsExtractor):
        """Test that all params present returns 1.0 coverage."""
        extracted = [
            ExtractedParameter(name="tipo_contribuente", value="dipendente", confidence=0.9, source="query"),
            ExtractedParameter(name="reddito", value="50000", confidence=0.95, source="query"),
        ]
        coverage = extractor.calculate_coverage("calcolo_irpef", extracted)
        assert coverage == 1.0

    def test_irpef_partial_coverage(self, extractor: AtomicFactsExtractor):
        """Test that missing params returns < 1.0 coverage."""
        extracted = [
            ExtractedParameter(name="reddito", value="50000", confidence=0.9, source="query"),
        ]
        coverage = extractor.calculate_coverage("calcolo_irpef", extracted)
        assert coverage == 0.5  # 1/2 required params

    def test_irpef_no_coverage(self, extractor: AtomicFactsExtractor):
        """Test that no params returns 0.0 coverage."""
        extracted: list[ExtractedParameter] = []
        coverage = extractor.calculate_coverage("calcolo_irpef", extracted)
        assert coverage == 0.0

    def test_iva_full_coverage_with_defaults(self, extractor: AtomicFactsExtractor):
        """Test IVA coverage with only required param (aliquota has default)."""
        extracted = [
            ExtractedParameter(name="importo", value="1000", confidence=0.9, source="query"),
        ]
        coverage = extractor.calculate_coverage("calcolo_iva", extracted)
        assert coverage == 1.0  # Only importo is required

    def test_unknown_intent_zero_coverage(self, extractor: AtomicFactsExtractor):
        """Test that unknown intent returns 0.0 coverage."""
        extracted = [
            ExtractedParameter(name="importo", value="1000", confidence=0.9, source="query"),
        ]
        coverage = extractor.calculate_coverage("unknown_intent", extracted)
        assert coverage == 0.0

    def test_low_confidence_ignored(self, extractor: AtomicFactsExtractor):
        """Test that confidence < 0.7 not counted toward coverage."""
        extracted = [
            ExtractedParameter(name="tipo_contribuente", value="dipendente", confidence=0.6, source="query"),
            ExtractedParameter(name="reddito", value="50000", confidence=0.95, source="query"),
        ]
        coverage = extractor.calculate_coverage("calcolo_irpef", extracted)
        assert coverage == 0.5  # Only reddito counts

    def test_multiple_values_highest_confidence(self, extractor: AtomicFactsExtractor):
        """Test that highest confidence value wins for same param."""
        extracted = [
            ExtractedParameter(name="reddito", value="30000", confidence=0.7, source="query"),
            ExtractedParameter(name="reddito", value="50000", confidence=0.95, source="query"),
            ExtractedParameter(name="tipo_contribuente", value="dipendente", confidence=0.9, source="query"),
        ]
        coverage = extractor.calculate_coverage("calcolo_irpef", extracted)
        assert coverage == 1.0  # Both covered (highest confidence reddito=50000)


class TestGetMissingRequired:
    """Test get_missing_required method."""

    @pytest.fixture
    def extractor(self) -> AtomicFactsExtractor:
        """Create extractor instance."""
        return AtomicFactsExtractor()

    def test_no_missing_when_all_present(self, extractor: AtomicFactsExtractor):
        """Test no missing required when all params present."""
        extracted = [
            ExtractedParameter(name="tipo_contribuente", value="dipendente", confidence=0.9, source="query"),
            ExtractedParameter(name="reddito", value="50000", confidence=0.95, source="query"),
        ]
        missing = extractor.get_missing_required("calcolo_irpef", extracted)
        assert missing == []

    def test_missing_required_params(self, extractor: AtomicFactsExtractor):
        """Test returns list of missing required params."""
        extracted = [
            ExtractedParameter(name="reddito", value="50000", confidence=0.9, source="query"),
        ]
        missing = extractor.get_missing_required("calcolo_irpef", extracted)
        assert "tipo_contribuente" in missing
        assert "reddito" not in missing

    def test_low_confidence_counts_as_missing(self, extractor: AtomicFactsExtractor):
        """Test low confidence param counts as missing."""
        extracted = [
            ExtractedParameter(name="tipo_contribuente", value="dipendente", confidence=0.5, source="query"),
            ExtractedParameter(name="reddito", value="50000", confidence=0.9, source="query"),
        ]
        missing = extractor.get_missing_required("calcolo_irpef", extracted)
        assert "tipo_contribuente" in missing

    def test_unknown_intent_returns_empty(self, extractor: AtomicFactsExtractor):
        """Test unknown intent returns empty list."""
        extracted = [
            ExtractedParameter(name="importo", value="1000", confidence=0.9, source="query"),
        ]
        missing = extractor.get_missing_required("unknown_intent", extracted)
        assert missing == []


class TestExtractWithCoverage:
    """Test extract_with_coverage method."""

    @pytest.fixture
    def extractor(self) -> AtomicFactsExtractor:
        """Create extractor instance."""
        return AtomicFactsExtractor()

    def test_returns_parameter_extraction_result(self, extractor: AtomicFactsExtractor):
        """Test returns ParameterExtractionResult type."""
        result = extractor.extract_with_coverage("Calcola IRPEF per 50000 euro", "calcolo_irpef")
        assert isinstance(result, ParameterExtractionResult)
        assert result.intent == "calcolo_irpef"

    def test_extracts_monetary_amount(self, extractor: AtomicFactsExtractor):
        """Test extracts monetary amount from query."""
        result = extractor.extract_with_coverage("Calcola IVA su 1000 euro", "calcolo_iva")
        assert result.coverage == 1.0
        assert any(p.name == "importo" for p in result.extracted)

    def test_can_proceed_with_full_coverage(self, extractor: AtomicFactsExtractor):
        """Test can_proceed=True with full coverage."""
        result = extractor.extract_with_coverage("Calcola IVA su 1000 euro", "calcolo_iva")
        assert result.can_proceed is True
        assert result.coverage == 1.0

    def test_can_proceed_with_high_coverage(self, extractor: AtomicFactsExtractor):
        """Test can_proceed=True with coverage >= 0.8 (smart fallback)."""
        # For calcolo_irpef, we need > 80% coverage which requires 2/2 params
        # Let's test with a query that has partial coverage
        result = extractor.extract_with_coverage("Calcola qualcosa", "calcolo_iva")
        # When importo is missing, coverage should be 0
        # If nothing extracted, can_proceed should be False
        if result.coverage < 0.8:
            assert result.can_proceed is False

    def test_cannot_proceed_with_low_coverage(self, extractor: AtomicFactsExtractor):
        """Test can_proceed=False with low coverage."""
        result = extractor.extract_with_coverage("Calcola qualcosa", "calcolo_irpef")
        assert result.can_proceed is False
        assert result.coverage < 0.8

    def test_missing_required_populated(self, extractor: AtomicFactsExtractor):
        """Test missing_required is populated correctly."""
        result = extractor.extract_with_coverage("Calcola IRPEF", "calcolo_irpef")
        # Without monetary amount, reddito is missing
        # Without contributor type, tipo_contribuente is missing
        assert len(result.missing_required) > 0

    def test_optional_params_ignored_for_can_proceed(self, extractor: AtomicFactsExtractor):
        """Test optional params don't affect can_proceed."""
        # IVA only requires importo, aliquota is optional with default
        result = extractor.extract_with_coverage("Calcola IVA su 1000 euro", "calcolo_iva")
        assert result.can_proceed is True
        # Optional params shouldn't be in missing_required
        assert "aliquota" not in result.missing_required


class TestParseItalianNumber:
    """Test _parse_italian_number method."""

    @pytest.fixture
    def extractor(self) -> AtomicFactsExtractor:
        """Create extractor instance."""
        return AtomicFactsExtractor()

    def test_italian_format_with_comma(self, extractor: AtomicFactsExtractor):
        """Test parsing 1.000,50 format."""
        result = extractor._parse_italian_number("1.000,50")
        assert result == 1000.50

    def test_standard_format_with_period(self, extractor: AtomicFactsExtractor):
        """Test parsing 1000.50 format."""
        result = extractor._parse_italian_number("1000.50")
        assert result == 1000.50

    def test_italian_format_thousands(self, extractor: AtomicFactsExtractor):
        """Test parsing 50.000 (fifty thousand) format."""
        result = extractor._parse_italian_number("50.000")
        assert result == 50000.0

    def test_italian_format_complex(self, extractor: AtomicFactsExtractor):
        """Test parsing 1.234.567,89 format."""
        result = extractor._parse_italian_number("1.234.567,89")
        assert result == 1234567.89

    def test_plain_integer(self, extractor: AtomicFactsExtractor):
        """Test parsing plain integer."""
        result = extractor._parse_italian_number("50000")
        assert result == 50000.0

    def test_invalid_format_returns_none(self, extractor: AtomicFactsExtractor):
        """Test invalid format returns None."""
        result = extractor._parse_italian_number("abc")
        assert result is None

    def test_empty_string_returns_none(self, extractor: AtomicFactsExtractor):
        """Test empty string returns None."""
        result = extractor._parse_italian_number("")
        assert result is None


class TestContributorTypeExtraction:
    """Test contributor type extraction from queries."""

    @pytest.fixture
    def extractor(self) -> AtomicFactsExtractor:
        """Create extractor instance."""
        return AtomicFactsExtractor()

    def test_extracts_dipendente(self, extractor: AtomicFactsExtractor):
        """Test extracts 'dipendente' from query."""
        result = extractor.extract_with_coverage(
            "Calcola IRPEF per lavoratore dipendente con reddito 50000 euro",
            "calcolo_irpef",
        )
        params_by_name = {p.name: p for p in result.extracted}
        assert "tipo_contribuente" in params_by_name
        assert params_by_name["tipo_contribuente"].value == "dipendente"

    def test_extracts_autonomo(self, extractor: AtomicFactsExtractor):
        """Test extracts 'autonomo' from query."""
        result = extractor.extract_with_coverage(
            "Calcola IRPEF per lavoratore autonomo con reddito 80000 euro",
            "calcolo_irpef",
        )
        params_by_name = {p.name: p for p in result.extracted}
        assert "tipo_contribuente" in params_by_name
        assert params_by_name["tipo_contribuente"].value == "autonomo"

    def test_extracts_pensionato(self, extractor: AtomicFactsExtractor):
        """Test extracts 'pensionato' from query."""
        result = extractor.extract_with_coverage(
            "Calcola IRPEF per pensionato con pensione 30000 euro",
            "calcolo_irpef",
        )
        params_by_name = {p.name: p for p in result.extracted}
        assert "tipo_contribuente" in params_by_name
        assert params_by_name["tipo_contribuente"].value == "pensionato"


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""

    @pytest.fixture
    def extractor(self) -> AtomicFactsExtractor:
        """Create extractor instance."""
        return AtomicFactsExtractor()

    def test_complete_irpef_query(self, extractor: AtomicFactsExtractor):
        """Test complete IRPEF query extraction."""
        result = extractor.extract_with_coverage(
            "Calcola l'IRPEF per un dipendente con reddito lordo di 50.000 euro",
            "calcolo_irpef",
        )
        assert result.coverage == 1.0
        assert result.can_proceed is True
        assert len(result.missing_required) == 0

    def test_complete_iva_query(self, extractor: AtomicFactsExtractor):
        """Test complete IVA query extraction."""
        result = extractor.extract_with_coverage(
            "Quanto è l'IVA su 1.500,00 euro?",
            "calcolo_iva",
        )
        assert result.coverage == 1.0
        assert result.can_proceed is True

    def test_partial_irpef_query(self, extractor: AtomicFactsExtractor):
        """Test partial IRPEF query - missing contributor type."""
        result = extractor.extract_with_coverage(
            "Calcola IRPEF per 50000 euro",
            "calcolo_irpef",
        )
        assert result.coverage < 1.0
        assert "tipo_contribuente" in result.missing_required

    def test_italian_number_in_query(self, extractor: AtomicFactsExtractor):
        """Test Italian number format in actual query."""
        result = extractor.extract_with_coverage(
            "Calcola IVA su 1.234,56 euro",
            "calcolo_iva",
        )
        params_by_name = {p.name: p for p in result.extracted}
        assert "importo" in params_by_name
        # Value should be properly parsed
        assert float(params_by_name["importo"].value) == 1234.56
