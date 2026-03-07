"""Tests for auto-detection of Excel/CSV column mappings.

TDD: Tests written FIRST before implementation.
Tests cover:
- Tier 1: Exact alias matching (codice_fiscale, nome, etc.)
- Tier 2: Fuzzy matching (cod_fisc → codice_fiscale)
- Tier 3: Data pattern analysis (regex-based CF, P.IVA, email, etc.)
- Confidence scoring (high, medium, low)
- Combined tier priority (exact > fuzzy > pattern)
- Edge cases: empty headers, duplicate matches, no matches
"""

import pytest

from app.services.client_import_service import (
    ClientImportService,
    SuggestedColumnMapping,
)


@pytest.fixture
def svc() -> ClientImportService:
    return ClientImportService()


class TestTier1ExactAliasMatching:
    """Tier 1: Deterministic header matching against known aliases."""

    def test_exact_match_standard_headers(self, svc: ClientImportService) -> None:
        """Headers matching backend field names exactly are detected with confidence 1.0."""
        headers = ["codice_fiscale", "nome", "tipo_cliente", "comune", "provincia"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert "codice_fiscale" in result
        assert result["codice_fiscale"].file_column == "codice_fiscale"
        assert result["codice_fiscale"].confidence == 1.0
        assert result["codice_fiscale"].match_method == "exact_alias"

    def test_alias_ragione_sociale_maps_to_nome(self, svc: ClientImportService) -> None:
        """'ragione_sociale' is a known alias for 'nome'."""
        headers = ["ragione_sociale", "codice_fiscale", "comune", "provincia"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert "nome" in result
        assert result["nome"].file_column == "ragione_sociale"
        assert result["nome"].confidence == 1.0

    def test_alias_case_insensitive(self, svc: ClientImportService) -> None:
        """Alias matching is case-insensitive."""
        headers = ["Codice_Fiscale", "NOME", "Comune", "Provincia"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert "codice_fiscale" in result
        assert "nome" in result
        assert result["codice_fiscale"].confidence == 1.0

    def test_alias_with_spaces_and_dots(self, svc: ClientImportService) -> None:
        """Headers with spaces/dots like 'Codice Fiscale' or 'P.IVA' match."""
        headers = ["Codice Fiscale", "P.IVA", "E-mail"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert "codice_fiscale" in result
        assert "partita_iva" in result
        assert "email" in result

    def test_common_italian_aliases(self, svc: ClientImportService) -> None:
        """Common Italian accounting aliases are recognized."""
        headers = ["denominazione", "cf", "p_iva", "tel", "indirizzo", "cap"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert "nome" in result
        assert result["nome"].file_column == "denominazione"
        assert "codice_fiscale" in result
        assert result["codice_fiscale"].file_column == "cf"
        assert "partita_iva" in result
        assert "phone" in result


class TestTier2FuzzyMatching:
    """Tier 2: Fuzzy string similarity for close-but-not-exact headers."""

    def test_fuzzy_match_codice_fisc(self, svc: ClientImportService) -> None:
        """'codice_fisc' fuzzy-matches 'codice_fiscale' with medium confidence."""
        headers = ["codice_fisc", "nome_cliente"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert "codice_fiscale" in result
        assert result["codice_fiscale"].file_column == "codice_fisc"
        assert result["codice_fiscale"].match_method == "fuzzy"
        assert 0.6 <= result["codice_fiscale"].confidence < 1.0

    def test_fuzzy_match_telefono(self, svc: ClientImportService) -> None:
        """'telefono' fuzzy-matches 'phone' via alias similarity."""
        headers = ["telefono"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert "phone" in result
        assert result["phone"].file_column == "telefono"

    def test_fuzzy_does_not_match_garbage(self, svc: ClientImportService) -> None:
        """Random headers don't fuzzy-match anything."""
        headers = ["xyz_unknown", "random_col"]
        result = svc.auto_detect_column_mapping(headers, [])
        # These should NOT match any field via fuzzy alone
        fuzzy_matches = {k: v for k, v in result.items() if v.match_method == "fuzzy"}
        for m in fuzzy_matches.values():
            assert m.confidence < 0.7


class TestTier3DataPatternAnalysis:
    """Tier 3: Regex-based analysis of actual cell values."""

    def test_pattern_detects_codice_fiscale_persona_fisica(self, svc: ClientImportService) -> None:
        """Column with Italian fiscal codes (16 chars) is detected as codice_fiscale."""
        headers = ["col_a", "col_b"]
        sample_rows = [
            {"col_a": "RSSMRA85M01H501Z", "col_b": "Mario Rossi"},
            {"col_a": "BNCLGU90A01F205X", "col_b": "Luigi Bianchi"},
        ]
        result = svc.auto_detect_column_mapping(headers, sample_rows)
        assert "codice_fiscale" in result
        assert result["codice_fiscale"].file_column == "col_a"
        assert result["codice_fiscale"].match_method == "data_pattern"

    def test_pattern_detects_partita_iva(self, svc: ClientImportService) -> None:
        """Column with 11-digit numbers is detected as partita_iva."""
        headers = ["col_x"]
        sample_rows = [
            {"col_x": "12345678901"},
            {"col_x": "98765432109"},
        ]
        result = svc.auto_detect_column_mapping(headers, sample_rows)
        assert "partita_iva" in result
        assert result["partita_iva"].file_column == "col_x"
        assert result["partita_iva"].match_method == "data_pattern"

    def test_pattern_detects_email(self, svc: ClientImportService) -> None:
        """Column with email addresses is detected as email."""
        headers = ["contact"]
        sample_rows = [
            {"contact": "mario@example.com"},
            {"contact": "luigi@test.it"},
        ]
        result = svc.auto_detect_column_mapping(headers, sample_rows)
        assert "email" in result
        assert result["email"].file_column == "contact"
        assert result["email"].match_method == "data_pattern"

    def test_pattern_detects_cap(self, svc: ClientImportService) -> None:
        """Column with 5-digit CAP codes is detected."""
        headers = ["zipcode"]
        sample_rows = [
            {"zipcode": "00179"},
            {"zipcode": "20121"},
        ]
        result = svc.auto_detect_column_mapping(headers, sample_rows)
        assert "cap" in result
        assert result["cap"].file_column == "zipcode"

    def test_pattern_detects_provincia(self, svc: ClientImportService) -> None:
        """Column with 2-letter codes is detected as provincia."""
        headers = ["prov"]
        sample_rows = [
            {"prov": "RM"},
            {"prov": "MI"},
            {"prov": "BO"},
        ]
        result = svc.auto_detect_column_mapping(headers, sample_rows)
        assert "provincia" in result

    def test_pattern_with_none_values(self, svc: ClientImportService) -> None:
        """Data pattern analysis handles None/empty values gracefully."""
        headers = ["col_a"]
        sample_rows = [
            {"col_a": None},
            {"col_a": ""},
            {"col_a": "RSSMRA85M01H501Z"},
        ]
        result = svc.auto_detect_column_mapping(headers, sample_rows)
        # Should still detect the pattern from the one valid value
        assert "codice_fiscale" in result


class TestConfidenceAndPriority:
    """Test confidence scoring and tier priority."""

    def test_exact_alias_beats_fuzzy(self, svc: ClientImportService) -> None:
        """Exact alias match (Tier 1) takes priority over fuzzy (Tier 2)."""
        headers = ["nome", "nome_completo"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert result["nome"].file_column == "nome"
        assert result["nome"].confidence == 1.0

    def test_all_fields_detected_for_standard_file(self, svc: ClientImportService) -> None:
        """A file with standard headers gets all columns auto-mapped."""
        headers = [
            "codice_fiscale",
            "nome",
            "tipo_cliente",
            "comune",
            "provincia",
            "partita_iva",
            "email",
            "phone",
            "indirizzo",
            "cap",
        ]
        result = svc.auto_detect_column_mapping(headers, [])
        # All backend fields should be detected
        for field in [
            "codice_fiscale",
            "nome",
            "tipo_cliente",
            "comune",
            "provincia",
            "partita_iva",
            "email",
            "phone",
            "indirizzo",
            "cap",
        ]:
            assert field in result, f"Missing auto-detection for {field}"
            assert result[field].confidence == 1.0

    def test_no_duplicate_file_column_assignments(self, svc: ClientImportService) -> None:
        """Each file column is assigned to at most one target field."""
        headers = ["codice_fiscale", "nome", "comune", "provincia"]
        result = svc.auto_detect_column_mapping(headers, [])
        assigned_columns = [v.file_column for v in result.values()]
        assert len(assigned_columns) == len(set(assigned_columns))


class TestEdgeCases:
    """Edge cases for auto-detection."""

    def test_empty_headers(self, svc: ClientImportService) -> None:
        """Empty header list returns empty mapping."""
        result = svc.auto_detect_column_mapping([], [])
        assert result == {}

    def test_no_matching_headers(self, svc: ClientImportService) -> None:
        """Completely unrecognized headers with no data return empty or low-confidence."""
        headers = ["zzz_unknown_1", "zzz_unknown_2"]
        result = svc.auto_detect_column_mapping(headers, [])
        # Should have no high-confidence matches
        high_conf = {k: v for k, v in result.items() if v.confidence >= 0.7}
        assert len(high_conf) == 0

    def test_mixed_detected_and_undetected(self, svc: ClientImportService) -> None:
        """Some headers match, some don't — partial mapping."""
        headers = ["codice_fiscale", "zzz_unknown"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert "codice_fiscale" in result
        assert result["codice_fiscale"].confidence == 1.0
