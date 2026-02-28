"""DEV-408: Tests for Cedolare Secca Calculator.

Tests: 21% rate, 10% reduced, comparison with ordinary IRPEF.
"""

from decimal import Decimal

import pytest

from app.services.cedolare_secca_calculator_service import (
    CedolareSeccaCalculatorService,
    TipoContratto,
)


@pytest.fixture
def svc():
    return CedolareSeccaCalculatorService()


class TestCalcolaCedolareSecca:
    def test_ordinaria_21_percent(self, svc):
        result = svc.calcola_cedolare_secca(Decimal("12000"))
        assert result["aliquota"] == 21.0
        assert result["imposta"] == 2520.0
        assert result["netto"] == 9480.0

    def test_concordato_10_percent(self, svc):
        result = svc.calcola_cedolare_secca(Decimal("12000"), TipoContratto.CONCORDATO)
        assert result["aliquota"] == 10.0
        assert result["imposta"] == 1200.0
        assert result["netto"] == 10800.0

    def test_zero_canone(self, svc):
        result = svc.calcola_cedolare_secca(Decimal("0"))
        assert result["imposta"] == 0.0

    def test_negative_canone_raises(self, svc):
        with pytest.raises(ValueError, match="negativo"):
            svc.calcola_cedolare_secca(Decimal("-1"))


class TestConfrontoConIrpef:
    def test_low_income_cedolare_conviene(self, svc):
        # Low income (23% IRPEF bracket) — cedolare 21% is close
        result = svc.confronto_con_irpef(
            Decimal("12000"),
            Decimal("15000"),
            TipoContratto.LIBERO,
        )
        assert result["cedolare_secca"]["imposta"] == 2520.0
        # IRPEF on full canone at 23% marginal = 2760
        assert result["irpef_ordinaria"]["imposta"] == 2760.0
        assert result["conviene"] == "cedolare_secca"

    def test_high_income_cedolare_conviene_more(self, svc):
        # High income (43% bracket) — cedolare 21% saves a lot
        result = svc.confronto_con_irpef(
            Decimal("12000"),
            Decimal("60000"),
            TipoContratto.LIBERO,
        )
        assert result["cedolare_secca"]["imposta"] == 2520.0
        assert result["irpef_ordinaria"]["aliquota_marginale"] == 43.0
        assert result["conviene"] == "cedolare_secca"

    def test_concordato_irpef_base_reduced(self, svc):
        # With concordato, only 66.5% of canone is taxed for IRPEF
        result = svc.confronto_con_irpef(
            Decimal("10000"),
            Decimal("20000"),
            TipoContratto.CONCORDATO,
        )
        assert result["irpef_ordinaria"]["base_imponibile"] == 6650.0
        assert result["cedolare_secca"]["aliquota"] == 10.0

    def test_negative_canone_raises(self, svc):
        with pytest.raises(ValueError, match="canone"):
            svc.confronto_con_irpef(Decimal("-1"), Decimal("30000"))

    def test_negative_reddito_raises(self, svc):
        with pytest.raises(ValueError, match="reddito"):
            svc.confronto_con_irpef(Decimal("10000"), Decimal("-1"))
