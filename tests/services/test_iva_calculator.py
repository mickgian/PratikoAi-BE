"""DEV-406: Tests for IVA Calculator Service.

Tests: scorporo 4%/10%/22%, liquidation positive/negative balance,
forfettario coefficient, edge cases.
"""

from decimal import Decimal

import pytest

from app.services.iva_calculator_service import IvaCalculatorService


@pytest.fixture
def svc():
    return IvaCalculatorService()


# --- Scorporo IVA ---


class TestScorporoIva:
    def test_scorporo_22_percent(self, svc):
        result = svc.scorporo_iva(Decimal("122"))
        assert result["imponibile"] == 100.0
        assert result["iva"] == 22.0
        assert result["aliquota"] == 22.0

    def test_scorporo_10_percent(self, svc):
        result = svc.scorporo_iva(Decimal("110"), Decimal("10"))
        assert result["imponibile"] == 100.0
        assert result["iva"] == 10.0

    def test_scorporo_4_percent(self, svc):
        result = svc.scorporo_iva(Decimal("104"), Decimal("4"))
        assert result["imponibile"] == 100.0
        assert result["iva"] == 4.0

    def test_scorporo_5_percent(self, svc):
        result = svc.scorporo_iva(Decimal("105"), Decimal("5"))
        assert result["imponibile"] == 100.0
        assert result["iva"] == 5.0

    def test_scorporo_zero_rate(self, svc):
        result = svc.scorporo_iva(Decimal("100"), Decimal("0"))
        assert result["imponibile"] == 100.0
        assert result["iva"] == 0.0

    def test_scorporo_zero_amount(self, svc):
        result = svc.scorporo_iva(Decimal("0"))
        assert result["imponibile"] == 0.0
        assert result["iva"] == 0.0

    def test_scorporo_negative_raises(self, svc):
        with pytest.raises(ValueError, match="negativo"):
            svc.scorporo_iva(Decimal("-10"))

    def test_scorporo_invalid_rate_raises(self, svc):
        with pytest.raises(ValueError, match="aliquota"):
            svc.scorporo_iva(Decimal("100"), Decimal("150"))


# --- Calcola IVA (forward) ---


class TestCalcolaIva:
    def test_calcola_iva_22(self, svc):
        result = svc.calcola_iva(Decimal("100"))
        assert result["iva"] == 22.0
        assert result["importo_lordo"] == 122.0

    def test_calcola_iva_10(self, svc):
        result = svc.calcola_iva(Decimal("100"), Decimal("10"))
        assert result["iva"] == 10.0
        assert result["importo_lordo"] == 110.0

    def test_calcola_iva_negative_raises(self, svc):
        with pytest.raises(ValueError, match="negativo"):
            svc.calcola_iva(Decimal("-1"))

    def test_calcola_iva_invalid_rate_raises(self, svc):
        with pytest.raises(ValueError, match="aliquota"):
            svc.calcola_iva(Decimal("100"), Decimal("150"))


# --- Liquidazione IVA ---


class TestLiquidazioneIva:
    def test_positive_balance_debito(self, svc):
        result = svc.liquidazione_iva(Decimal("5000"), Decimal("3000"))
        assert result["saldo"] == 2000.0
        assert result["esito"] == "debito"
        assert result["importo_dovuto"] == 2000.0
        assert result["credito_residuo"] == 0.0

    def test_negative_balance_credito(self, svc):
        result = svc.liquidazione_iva(Decimal("3000"), Decimal("5000"))
        assert result["saldo"] == -2000.0
        assert result["esito"] == "credito"
        assert result["credito_residuo"] == 2000.0
        assert result["importo_dovuto"] == 0.0

    def test_with_previous_credit(self, svc):
        result = svc.liquidazione_iva(Decimal("5000"), Decimal("3000"), Decimal("2500"))
        assert result["saldo"] == -500.0
        assert result["esito"] == "credito"

    def test_pareggio(self, svc):
        result = svc.liquidazione_iva(Decimal("5000"), Decimal("5000"))
        assert result["esito"] == "pareggio"
        assert result["saldo"] == 0.0

    def test_negative_vendite_raises(self, svc):
        with pytest.raises(ValueError, match="vendite"):
            svc.liquidazione_iva(Decimal("-1"), Decimal("0"))

    def test_negative_acquisti_raises(self, svc):
        with pytest.raises(ValueError, match="acquisti"):
            svc.liquidazione_iva(Decimal("0"), Decimal("-1"))

    def test_negative_credito_raises(self, svc):
        with pytest.raises(ValueError, match="credito"):
            svc.liquidazione_iva(Decimal("0"), Decimal("0"), Decimal("-1"))


# --- Forfettario ---


class TestForfettario:
    def test_forfettario_78_percent_coefficient(self, svc):
        result = svc.calcolo_forfettario(Decimal("50000"), Decimal("78"), Decimal("15"))
        assert result["reddito_imponibile"] == 39000.0
        assert result["imposta_sostitutiva"] == 5850.0

    def test_forfettario_5_percent_startup(self, svc):
        result = svc.calcolo_forfettario(Decimal("50000"), Decimal("78"), Decimal("5"))
        assert result["imposta_sostitutiva"] == 1950.0

    def test_forfettario_negative_ricavi_raises(self, svc):
        with pytest.raises(ValueError, match="ricavi"):
            svc.calcolo_forfettario(Decimal("-1"), Decimal("78"))

    def test_forfettario_invalid_aliquota_raises(self, svc):
        with pytest.raises(ValueError, match="aliquota sostitutiva"):
            svc.calcolo_forfettario(Decimal("50000"), Decimal("78"), Decimal("10"))

    def test_forfettario_invalid_coefficiente_zero_raises(self, svc):
        with pytest.raises(ValueError, match="coefficiente"):
            svc.calcolo_forfettario(Decimal("50000"), Decimal("0"))

    def test_forfettario_invalid_coefficiente_over_100_raises(self, svc):
        with pytest.raises(ValueError, match="coefficiente"):
            svc.calcolo_forfettario(Decimal("50000"), Decimal("101"))

    def test_get_coefficiente_attivita_professionali(self, svc):
        coeff = svc.get_coefficiente_by_attivita("attivita_professionali")
        assert coeff == Decimal("78")

    def test_get_coefficiente_unknown(self, svc):
        assert svc.get_coefficiente_by_attivita("sconosciuto") is None
