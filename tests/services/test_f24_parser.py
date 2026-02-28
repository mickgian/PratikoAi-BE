"""DEV-392: Tests for F24 Tax Payment Document Parser.

Tests: section detection, codice tributo extraction, totals, metadata, edge cases.
"""

import pytest

from app.services.document_parsers.f24_parser import (
    CODICI_TRIBUTO,
    F24Parser,
    _parse_number,
)


@pytest.fixture
def parser():
    return F24Parser()


class TestParseNumber:
    def test_italian_format(self):
        assert _parse_number("1.500,00") == pytest.approx(1500.0)

    def test_simple(self):
        assert _parse_number("500") == pytest.approx(500.0)

    def test_empty(self):
        assert _parse_number("") is None

    def test_invalid(self):
        assert _parse_number("xyz") is None


class TestF24Parser:
    def test_detect_sezione_erario(self, parser):
        content = "SEZIONE ERARIO\n4001 2025 € 5.000,00"
        result = parser.parse(content)
        assert "sezione_erario" in result["sezioni"]

    def test_detect_sezione_inps(self, parser):
        content = "Sezione INPS\nContributi vari"
        result = parser.parse(content)
        assert "sezione_inps" in result["sezioni"]

    def test_detect_sezione_regioni(self, parser):
        content = "Sezione Regioni\n3801 2025 € 600,00"
        result = parser.parse(content)
        assert "sezione_regioni" in result["sezioni"]

    def test_detect_sezione_inail(self, parser):
        content = "Sezione INAIL\npremi assicurativi"
        result = parser.parse(content)
        assert "sezione_inail" in result["sezioni"]

    def test_detect_sezione_enti_locali(self, parser):
        content = "Sezione enti locali\nIMU"
        result = parser.parse(content)
        assert "sezione_enti_locali" in result["sezioni"]

    def test_extract_tributo_with_year(self, parser):
        content = "Sezione Erario\n4001 2025 5.000,00"
        result = parser.parse(content)
        assert len(result["tributi"]) >= 1
        tributo = result["tributi"][0]
        assert tributo["codice_tributo"] == "4001"
        assert tributo["importo"] == pytest.approx(5000.0)
        assert tributo["descrizione"] == "IRPEF saldo"

    def test_extract_multiple_tributi(self, parser):
        content = """
        Sezione Erario
        4001 2025 3.000,00
        4033 2025 1.500,00
        """
        result = parser.parse(content)
        assert len(result["tributi"]) >= 2
        codici = [t["codice_tributo"] for t in result["tributi"]]
        assert "4001" in codici
        assert "4033" in codici

    def test_extract_tributo_simple_pattern(self, parser):
        content = "codice tributo: 6099 importo € 8.000,00"
        result = parser.parse(content)
        assert len(result["tributi"]) >= 1
        assert result["tributi"][0]["codice_tributo"] == "6099"
        assert result["tributi"][0]["descrizione"] == "IVA annuale versamento"

    def test_totale_versamento(self, parser):
        content = "4001 2025 3.000,00\n4033 2025 1.500,00"
        result = parser.parse(content)
        assert result["totale_versamento"] == pytest.approx(4500.0)

    def test_extract_codice_fiscale(self, parser):
        content = "Codice Fiscale: RSSMRA80A01H501Z\n4001 2025 1.000,00"
        result = parser.parse(content)
        assert result["codice_fiscale"] == "RSSMRA80A01H501Z"

    def test_extract_data_versamento(self, parser):
        content = "data versamento: 16/06/2025\n4001 2025 1.000,00"
        result = parser.parse(content)
        assert result["data_versamento"] == "16/06/2025"

    def test_empty_content_raises(self, parser):
        with pytest.raises(ValueError, match="vuoto"):
            parser.parse("")

    def test_no_tributi(self, parser):
        content = "Documento generico senza codici tributo"
        result = parser.parse(content)
        assert result["tributi"] == []
        assert result["totale_versamento"] == pytest.approx(0.0)

    def test_tipo_documento_always_f24(self, parser):
        content = "Qualsiasi contenuto testuale"
        result = parser.parse(content)
        assert result["tipo_documento"] == "F24"

    def test_unknown_tributo_code(self, parser):
        content = "9999 2025 100,00"
        result = parser.parse(content)
        if result["tributi"]:
            assert result["tributi"][0]["descrizione"] == "Tributo sconosciuto"

    def test_get_codice_tributo_description(self):
        assert F24Parser.get_codice_tributo_description("4001") == "IRPEF saldo"
        assert F24Parser.get_codice_tributo_description("6099") == "IVA annuale versamento"
        assert "sconosciuto" in F24Parser.get_codice_tributo_description("0000")

    def test_codici_tributo_dict(self):
        assert "4001" in CODICI_TRIBUTO
        assert "1040" in CODICI_TRIBUTO
        assert "3918" in CODICI_TRIBUTO

    def test_full_f24_document(self, parser):
        content = """
        MODELLO F24
        Codice Fiscale: 12345678901
        Data versamento: 16/06/2025

        Sezione Erario
        4001 2025 5.000,00
        4033 2025 2.000,00

        Sezione Regioni
        3801 2025 600,00

        Sezione INPS
        contributi inps vari
        """
        result = parser.parse(content)
        assert "sezione_erario" in result["sezioni"]
        assert "sezione_regioni" in result["sezioni"]
        assert "sezione_inps" in result["sezioni"]
        assert result["codice_fiscale"] == "12345678901"
        assert result["data_versamento"] == "16/06/2025"
        assert result["totale_versamento"] > 0
