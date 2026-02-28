"""DEV-361: Tests for CU (Certificazione Unica) Document Parser.

Tests: income extraction, withholding data, year, codice fiscale, edge cases.
"""

import pytest

from app.services.document_parsers.cu_parser import CuParser, _parse_number


@pytest.fixture
def parser():
    return CuParser()


class TestParseNumber:
    def test_italian_format(self):
        assert _parse_number("30.000,00") == pytest.approx(30000.0)

    def test_simple_number(self):
        assert _parse_number("1500") == pytest.approx(1500.0)

    def test_empty(self):
        assert _parse_number("") is None

    def test_invalid(self):
        assert _parse_number("abc") is None


class TestCuParser:
    def test_extract_redditi_lavoro_dipendente(self, parser):
        content = "Redditi di lavoro dipendente: € 35.000,00"
        result = parser.parse(content)
        assert result["redditi_lavoro_dipendente"] == pytest.approx(35000.0)

    def test_extract_redditi_by_punto(self, parser):
        content = "Punto 1: 42.000,00"
        result = parser.parse(content)
        assert result["redditi_lavoro_dipendente"] == pytest.approx(42000.0)

    def test_extract_ritenute_irpef(self, parser):
        content = "Ritenute IRPEF: € 8.500,00"
        result = parser.parse(content)
        assert result["ritenute_irpef"] == pytest.approx(8500.0)

    def test_extract_ritenute_by_punto(self, parser):
        content = "Punto 21: 9.200,00"
        result = parser.parse(content)
        assert result["ritenute_irpef"] == pytest.approx(9200.0)

    def test_extract_addizionale_regionale(self, parser):
        content = "Addizionale regionale: € 500,00"
        result = parser.parse(content)
        assert result["addizionale_regionale"] == pytest.approx(500.0)

    def test_extract_addizionale_comunale(self, parser):
        content = "Addizionale comunale: € 250,00"
        result = parser.parse(content)
        assert result["addizionale_comunale"] == pytest.approx(250.0)

    def test_extract_contributi_previdenziali(self, parser):
        content = "Contributi previdenziali: € 3.500,00"
        result = parser.parse(content)
        assert result["contributi_previdenziali"] == pytest.approx(3500.0)

    def test_extract_contributi_inps(self, parser):
        content = "Contributi INPS: € 4.200,00"
        result = parser.parse(content)
        assert result["contributi_previdenziali"] == pytest.approx(4200.0)

    def test_extract_giorni_lavoro(self, parser):
        content = "Giorni di lavoro: 365"
        result = parser.parse(content)
        assert result["giorni_lavoro"] == pytest.approx(365)

    def test_extract_anno_cu(self, parser):
        content = "Certificazione Unica 2025"
        result = parser.parse(content)
        assert result["anno_cu"] == 2025

    def test_extract_codice_fiscale(self, parser):
        content = "Codice Fiscale: 12345678901 del sostituto"
        result = parser.parse(content)
        assert result["codice_fiscale_sostituto"] == "12345678901"

    def test_empty_content_raises(self, parser):
        with pytest.raises(ValueError, match="vuoto"):
            parser.parse("")

    def test_no_matching_fields(self, parser):
        result = parser.parse("Documento generico senza dati CU")
        assert result == {}

    def test_full_cu_document(self, parser):
        content = """
        Certificazione Unica 2025
        Codice Fiscale: RSSMRA80A01H501Z
        Redditi di lavoro dipendente: € 40.000,00
        Ritenute IRPEF: € 10.200,00
        Addizionale regionale: € 600,00
        Addizionale comunale: € 320,00
        Contributi previdenziali: € 3.800,00
        Giorni di lavoro: 365
        """
        result = parser.parse(content)
        assert result["redditi_lavoro_dipendente"] == pytest.approx(40000.0)
        assert result["ritenute_irpef"] == pytest.approx(10200.0)
        assert result["addizionale_regionale"] == pytest.approx(600.0)
        assert result["addizionale_comunale"] == pytest.approx(320.0)
        assert result["contributi_previdenziali"] == pytest.approx(3800.0)
        assert result["giorni_lavoro"] == pytest.approx(365)
        assert result["anno_cu"] == 2025
        assert result["codice_fiscale_sostituto"] == "RSSMRA80A01H501Z"
