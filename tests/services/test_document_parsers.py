"""DEV-365: Document Parser Integration Tests.

Tests BilancioParser and CuParser with various Italian financial documents.
Verifies regex extraction, Italian number parsing, and derived metrics.
"""

import pytest

from app.services.document_parsers.bilancio_parser import BilancioParser, _parse_italian_number
from app.services.document_parsers.cu_parser import CuParser, _parse_number

# ---------------------------------------------------------------------------
# Italian number parsing
# ---------------------------------------------------------------------------


class TestItalianNumberParsing:
    """Tests for _parse_italian_number and _parse_number helpers."""

    def test_standard_italian_format(self) -> None:
        assert _parse_italian_number("1.234,56") == pytest.approx(1234.56)

    def test_no_thousands_separator(self) -> None:
        assert _parse_italian_number("234,56") == pytest.approx(234.56)

    def test_integer_value(self) -> None:
        assert _parse_italian_number("1.000") == pytest.approx(1000.0)

    def test_empty_string(self) -> None:
        assert _parse_italian_number("") is None

    def test_invalid_value(self) -> None:
        assert _parse_italian_number("abc") is None

    def test_cu_parse_number(self) -> None:
        assert _parse_number("25.000,00") == pytest.approx(25000.0)


# ---------------------------------------------------------------------------
# BilancioParser tests
# ---------------------------------------------------------------------------


class TestBilancioParser:
    """Tests for BilancioParser.parse."""

    @pytest.fixture
    def parser(self) -> BilancioParser:
        return BilancioParser()

    def test_empty_content_raises(self, parser: BilancioParser) -> None:
        with pytest.raises(ValueError, match="vuoto"):
            parser.parse("")

    def test_whitespace_only_raises(self, parser: BilancioParser) -> None:
        with pytest.raises(ValueError, match="vuoto"):
            parser.parse("   \n  ")

    def test_extract_fatturato(self, parser: BilancioParser) -> None:
        content = "Bilancio 2025\nFatturato: 1.500.000,00"
        result = parser.parse(content)
        assert result["fatturato"] == pytest.approx(1500000.0)

    def test_extract_ricavi(self, parser: BilancioParser) -> None:
        content = "Ricavi: 800.000,00"
        result = parser.parse(content)
        assert result["fatturato"] == pytest.approx(800000.0)

    def test_extract_utile_netto(self, parser: BilancioParser) -> None:
        content = "Utile netto: 120.000,00"
        result = parser.parse(content)
        assert result["utile_netto"] == pytest.approx(120000.0)

    def test_extract_patrimonio_netto(self, parser: BilancioParser) -> None:
        content = "Patrimonio netto: 500.000,00"
        result = parser.parse(content)
        assert result["patrimonio_netto"] == pytest.approx(500000.0)

    def test_extract_totale_attivo(self, parser: BilancioParser) -> None:
        content = "Totale attivo: 2.000.000,00"
        result = parser.parse(content)
        assert result["totale_attivo"] == pytest.approx(2000000.0)

    def test_extract_debiti(self, parser: BilancioParser) -> None:
        content = "Totale debiti: 300.000,00"
        result = parser.parse(content)
        assert result["debiti"] == pytest.approx(300000.0)

    def test_extract_anno_esercizio(self, parser: BilancioParser) -> None:
        content = "Bilancio 2025\nFatturato: 100.000,00"
        result = parser.parse(content)
        assert result["anno_esercizio"] == 2025

    def test_derived_margine_netto(self, parser: BilancioParser) -> None:
        content = "Fatturato: 1.000.000,00\nUtile netto: 100.000,00"
        result = parser.parse(content)
        assert result["margine_netto_pct"] == pytest.approx(10.0)

    def test_derived_rapporto_patrimonio(self, parser: BilancioParser) -> None:
        content = "Patrimonio netto: 500.000,00\nTotale attivo: 2.000.000,00"
        result = parser.parse(content)
        assert result["rapporto_patrimonio_attivo"] == pytest.approx(25.0)

    def test_no_matching_fields(self, parser: BilancioParser) -> None:
        content = "Documento generico senza dati finanziari."
        result = parser.parse(content)
        assert result == {}

    def test_full_bilancio(self, parser: BilancioParser) -> None:
        content = (
            "Esercizio 2024\n"
            "Fatturato: 2.000.000,00\n"
            "Utile netto: 200.000,00\n"
            "Patrimonio netto: 800.000,00\n"
            "Totale attivo: 3.000.000,00\n"
            "Totale debiti: 500.000,00\n"
            "Costi della produzione: 1.800.000,00\n"
        )
        result = parser.parse(content)
        assert result["fatturato"] == pytest.approx(2000000.0)
        assert result["utile_netto"] == pytest.approx(200000.0)
        assert result["patrimonio_netto"] == pytest.approx(800000.0)
        assert result["totale_attivo"] == pytest.approx(3000000.0)
        assert result["debiti"] == pytest.approx(500000.0)
        assert result["costi_produzione"] == pytest.approx(1800000.0)
        assert result["anno_esercizio"] == 2024
        assert result["margine_netto_pct"] == pytest.approx(10.0)
        assert result["rapporto_patrimonio_attivo"] == pytest.approx(26.67, rel=0.01)


# ---------------------------------------------------------------------------
# CuParser tests
# ---------------------------------------------------------------------------


class TestCuParser:
    """Tests for CuParser.parse."""

    @pytest.fixture
    def parser(self) -> CuParser:
        return CuParser()

    def test_empty_content_raises(self, parser: CuParser) -> None:
        with pytest.raises(ValueError, match="vuoto"):
            parser.parse("")

    def test_extract_redditi_lavoro(self, parser: CuParser) -> None:
        content = "Redditi di lavoro dipendente: 35.000,00"
        result = parser.parse(content)
        assert result["redditi_lavoro_dipendente"] == pytest.approx(35000.0)

    def test_extract_ritenute_irpef(self, parser: CuParser) -> None:
        content = "Ritenute IRPEF: 8.500,00"
        result = parser.parse(content)
        assert result["ritenute_irpef"] == pytest.approx(8500.0)

    def test_extract_contributi(self, parser: CuParser) -> None:
        content = "Contributi previdenziali: 3.200,00"
        result = parser.parse(content)
        assert result["contributi_previdenziali"] == pytest.approx(3200.0)

    def test_extract_addizionale_regionale(self, parser: CuParser) -> None:
        content = "Addizionale regionale: 500,00"
        result = parser.parse(content)
        assert result["addizionale_regionale"] == pytest.approx(500.0)

    def test_extract_addizionale_comunale(self, parser: CuParser) -> None:
        content = "Addizionale comunale: 200,00"
        result = parser.parse(content)
        assert result["addizionale_comunale"] == pytest.approx(200.0)

    def test_extract_anno_cu(self, parser: CuParser) -> None:
        content = "Certificazione Unica 2025\nRedditi di lavoro dipendente: 30.000,00"
        result = parser.parse(content)
        assert result["anno_cu"] == 2025

    def test_extract_codice_fiscale_sostituto(self, parser: CuParser) -> None:
        content = "CODICE FISCALE: 12345678901\nRedditi di lavoro dipendente: 30.000,00"
        result = parser.parse(content)
        assert result["codice_fiscale_sostituto"] == "12345678901"

    def test_punto_notation(self, parser: CuParser) -> None:
        content = "punto 1: 35.000,00\npunto 21: 8.000,00"
        result = parser.parse(content)
        assert result["redditi_lavoro_dipendente"] == pytest.approx(35000.0)
        assert result["ritenute_irpef"] == pytest.approx(8000.0)

    def test_no_matching_fields(self, parser: CuParser) -> None:
        content = "Documento generico."
        result = parser.parse(content)
        assert result == {}

    def test_full_cu(self, parser: CuParser) -> None:
        content = (
            "Certificazione Unica 2025\n"
            "CODICE FISCALE: 01234567890\n"
            "Redditi di lavoro dipendente: 40.000,00\n"
            "Ritenute IRPEF: 10.000,00\n"
            "Addizionale regionale: 600,00\n"
            "Addizionale comunale: 250,00\n"
            "Contributi previdenziali: 4.000,00\n"
            "Giorni di lavoro: 365\n"
        )
        result = parser.parse(content)
        assert result["anno_cu"] == 2025
        assert result["codice_fiscale_sostituto"] == "01234567890"
        assert result["redditi_lavoro_dipendente"] == pytest.approx(40000.0)
        assert result["ritenute_irpef"] == pytest.approx(10000.0)
        assert result["addizionale_regionale"] == pytest.approx(600.0)
        assert result["addizionale_comunale"] == pytest.approx(250.0)
        assert result["contributi_previdenziali"] == pytest.approx(4000.0)
        assert result["giorni_lavoro"] == pytest.approx(365.0)
