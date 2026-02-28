"""DEV-407: Tests for Ritenuta d'Acconto Calculator.

Tests: professional 20%, agent 23% on 50%, edge cases.
"""

from decimal import Decimal

import pytest

from app.services.ritenuta_calculator_service import (
    RitenutaCalculatorService,
    TipoRitenuta,
)


@pytest.fixture
def svc():
    return RitenutaCalculatorService()


class TestCalcolaRitenuta:
    def test_professionista_20_percent(self, svc):
        result = svc.calcola_ritenuta(Decimal("1000"), TipoRitenuta.PROFESSIONISTA)
        assert result["ritenuta"] == 200.0
        assert result["netto_percepito"] == 800.0
        assert result["aliquota"] == 20.0
        assert result["base_imponibile_percentuale"] == 100.0

    def test_agente_23_on_50(self, svc):
        result = svc.calcola_ritenuta(Decimal("10000"), TipoRitenuta.AGENTE)
        # 23% of 50% of 10000 = 23% of 5000 = 1150
        assert result["base_imponibile"] == 5000.0
        assert result["ritenuta"] == 1150.0
        assert result["netto_percepito"] == 8850.0

    def test_occasionale_20_percent(self, svc):
        result = svc.calcola_ritenuta(Decimal("5000"), TipoRitenuta.OCCASIONALE)
        assert result["ritenuta"] == 1000.0
        assert result["netto_percepito"] == 4000.0

    def test_amministratore_20_percent(self, svc):
        result = svc.calcola_ritenuta(Decimal("2000"), TipoRitenuta.AMMINISTRATORE)
        assert result["ritenuta"] == 400.0

    def test_zero_amount(self, svc):
        result = svc.calcola_ritenuta(Decimal("0"))
        assert result["ritenuta"] == 0.0
        assert result["netto_percepito"] == 0.0

    def test_negative_amount_raises(self, svc):
        with pytest.raises(ValueError, match="negativo"):
            svc.calcola_ritenuta(Decimal("-1"))

    def test_custom_aliquota_override(self, svc):
        result = svc.calcola_ritenuta(
            Decimal("1000"),
            TipoRitenuta.PROFESSIONISTA,
            aliquota_override=Decimal("30"),
        )
        assert result["ritenuta"] == 300.0

    def test_custom_base_override(self, svc):
        result = svc.calcola_ritenuta(
            Decimal("1000"),
            TipoRitenuta.PROFESSIONISTA,
            base_imponibile_pct_override=Decimal("50"),
        )
        # 20% of 50% of 1000 = 20% of 500 = 100
        assert result["ritenuta"] == 100.0

    def test_invalid_tipo_raises(self, svc):
        with pytest.raises(ValueError, match="non supportato"):
            svc.calcola_ritenuta(Decimal("1000"), "tipo_inesistente")


class TestCalcolaNettoDaLordo:
    def test_professionista_con_iva(self, svc):
        result = svc.calcola_netto_da_lordo(
            Decimal("1000"),
            TipoRitenuta.PROFESSIONISTA,
            include_iva=True,
        )
        # IVA: 1000 * 22% = 220
        # Totale fattura: 1220
        # Ritenuta: 1000 * 20% = 200
        # Netto: 1220 - 200 = 1020
        assert result["iva"] == 220.0
        assert result["totale_fattura"] == 1220.0
        assert result["ritenuta"] == 200.0
        assert result["netto_percepito"] == 1020.0

    def test_professionista_senza_iva(self, svc):
        result = svc.calcola_netto_da_lordo(
            Decimal("1000"),
            TipoRitenuta.PROFESSIONISTA,
            include_iva=False,
        )
        assert result["iva"] == 0.0
        assert result["totale_fattura"] == 1000.0
        assert result["ritenuta"] == 200.0
        assert result["netto_percepito"] == 800.0

    def test_negative_raises(self, svc):
        with pytest.raises(ValueError, match="negativo"):
            svc.calcola_netto_da_lordo(Decimal("-100"))

    def test_invalid_tipo_raises(self, svc):
        with pytest.raises(ValueError, match="non supportato"):
            svc.calcola_netto_da_lordo(Decimal("1000"), "tipo_inesistente")
