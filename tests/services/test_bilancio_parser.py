"""DEV-360: Tests for Bilancio Document Parser.

Tests: field extraction, Italian number parsing, derived metrics,
year extraction, empty content, partial data.
"""

import pytest

from app.services.document_parsers.bilancio_parser import (
    BilancioParser,
    _parse_italian_number,
)


@pytest.fixture
def parser():
    return BilancioParser()


class TestParseItalianNumber:
    def test_standard_format(self):
        assert _parse_italian_number("1.234,56") == pytest.approx(1234.56)

    def test_no_thousands_separator(self):
        assert _parse_italian_number("1234,56") == pytest.approx(1234.56)

    def test_integer(self):
        assert _parse_italian_number("1000") == pytest.approx(1000.0)

    def test_empty_string(self):
        assert _parse_italian_number("") is None

    def test_invalid_string(self):
        assert _parse_italian_number("abc") is None


class TestBilancioParser:
    def test_extract_fatturato(self, parser):
        content = "Fatturato: € 1.500.000,00"
        result = parser.parse(content)
        assert result["fatturato"] == pytest.approx(1500000.0)

    def test_extract_ricavi(self, parser):
        content = "Ricavi delle vendite: 500.000,00"
        result = parser.parse(content)
        assert result["fatturato"] == pytest.approx(500000.0)

    def test_extract_utile_netto(self, parser):
        content = "Utile netto: € 120.000,50"
        result = parser.parse(content)
        assert result["utile_netto"] == pytest.approx(120000.50)

    def test_extract_patrimonio_netto(self, parser):
        content = "Patrimonio netto: € 800.000,00"
        result = parser.parse(content)
        assert result["patrimonio_netto"] == pytest.approx(800000.0)

    def test_extract_totale_attivo(self, parser):
        content = "Totale attivo: € 2.000.000,00"
        result = parser.parse(content)
        assert result["totale_attivo"] == pytest.approx(2000000.0)

    def test_extract_debiti(self, parser):
        content = "Totale debiti: € 300.000,00"
        result = parser.parse(content)
        assert result["debiti"] == pytest.approx(300000.0)

    def test_extract_costi_produzione(self, parser):
        content = "Costi della produzione: € 400.000,00"
        result = parser.parse(content)
        assert result["costi_produzione"] == pytest.approx(400000.0)

    def test_extract_year(self, parser):
        content = "Bilancio 2025 - Fatturato: € 100.000,00"
        result = parser.parse(content)
        assert result["anno_esercizio"] == 2025

    def test_extract_year_esercizio(self, parser):
        content = "Esercizio 2024 - Ricavi: 50.000,00"
        result = parser.parse(content)
        assert result["anno_esercizio"] == 2024

    def test_margine_netto_derived(self, parser):
        content = "Fatturato: 1.000.000,00\nUtile netto: 150.000,00"
        result = parser.parse(content)
        assert result["margine_netto_pct"] == pytest.approx(15.0)

    def test_rapporto_patrimonio_attivo(self, parser):
        content = "Patrimonio netto: 500.000,00\nTotale attivo: 1.000.000,00"
        result = parser.parse(content)
        assert result["rapporto_patrimonio_attivo"] == pytest.approx(50.0)

    def test_empty_content_raises(self, parser):
        with pytest.raises(ValueError, match="vuoto"):
            parser.parse("")

    def test_whitespace_only_raises(self, parser):
        with pytest.raises(ValueError, match="vuoto"):
            parser.parse("   ")

    def test_no_matching_fields(self, parser):
        result = parser.parse("Questo documento non contiene dati finanziari.")
        assert result == {}

    def test_full_bilancio(self, parser):
        content = """
        Bilancio 2025
        Ricavi delle vendite: € 2.500.000,00
        Costi della produzione: € 1.800.000,00
        Utile netto: € 350.000,00
        Patrimonio netto: € 1.200.000,00
        Totale attivo: € 3.000.000,00
        Totale debiti: € 1.800.000,00
        """
        result = parser.parse(content)
        assert result["fatturato"] == pytest.approx(2500000.0)
        assert result["utile_netto"] == pytest.approx(350000.0)
        assert result["patrimonio_netto"] == pytest.approx(1200000.0)
        assert result["totale_attivo"] == pytest.approx(3000000.0)
        assert result["debiti"] == pytest.approx(1800000.0)
        assert result["anno_esercizio"] == 2025
        assert "margine_netto_pct" in result
        assert "rapporto_patrimonio_attivo" in result
