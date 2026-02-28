"""DEV-409: Tests for TFR Calculator.

Tests: single year, multi-year accrual, revaluation, partial year.
"""

from decimal import Decimal

import pytest

from app.services.tfr_calculator_service import TfrCalculatorService


@pytest.fixture
def svc():
    return TfrCalculatorService()


class TestAccantonamentoAnnuo:
    def test_standard_ral(self, svc):
        result = svc.calcola_accantonamento_annuo(Decimal("30000"))
        # 30000 / 13.5 = 2222.22
        assert result["accantonamento_annuo"] == 2222.22

    def test_zero_ral(self, svc):
        result = svc.calcola_accantonamento_annuo(Decimal("0"))
        assert result["accantonamento_annuo"] == 0.0

    def test_negative_raises(self, svc):
        with pytest.raises(ValueError, match="negativa"):
            svc.calcola_accantonamento_annuo(Decimal("-1"))


class TestRivalutazione:
    def test_standard_revaluation(self, svc):
        # TFR = 10000, ISTAT = 2%
        # Revaluation = 10000 * (1.5 + 75% of 2) / 100 = 10000 * 3.0 / 100 = 300
        result = svc.calcola_rivalutazione(Decimal("10000"), Decimal("2"))
        assert result["tasso_rivalutazione"] == 3.0
        assert result["rivalutazione"] == 300.0
        assert result["tfr_rivalutato"] == 10300.0

    def test_zero_istat(self, svc):
        # Only fixed 1.5% applies
        result = svc.calcola_rivalutazione(Decimal("10000"), Decimal("0"))
        assert result["tasso_rivalutazione"] == 1.5
        assert result["rivalutazione"] == 150.0

    def test_negative_tfr_raises(self, svc):
        with pytest.raises(ValueError, match="TFR"):
            svc.calcola_rivalutazione(Decimal("-1"), Decimal("2"))

    def test_negative_istat_raises(self, svc):
        with pytest.raises(ValueError, match="ISTAT"):
            svc.calcola_rivalutazione(Decimal("10000"), Decimal("-1"))


class TestMultiAnno:
    def test_two_years(self, svc):
        result = svc.calcola_tfr_multi_anno(
            [Decimal("30000"), Decimal("31000")],
            [Decimal("2"), Decimal("1.5")],
        )
        assert result["anni"] == 2
        assert len(result["dettaglio_annuale"]) == 2
        # Year 1: 30000/13.5 = 2222.22
        assert result["dettaglio_annuale"][0]["accantonamento"] == 2222.22
        assert result["dettaglio_annuale"][0]["rivalutazione"] == 0.0
        # Year 2: revaluation on 2222.22 + new accrual from 31000
        assert result["tfr_totale"] > 0

    def test_mismatched_lengths_raises(self, svc):
        with pytest.raises(ValueError, match="stessa lunghezza"):
            svc.calcola_tfr_multi_anno([Decimal("30000")], [])

    def test_empty_list_raises(self, svc):
        with pytest.raises(ValueError, match="vuote"):
            svc.calcola_tfr_multi_anno([], [])

    def test_negative_ral_in_list_raises(self, svc):
        with pytest.raises(ValueError, match="negativa"):
            svc.calcola_tfr_multi_anno(
                [Decimal("-1000")],
                [Decimal("2")],
            )


class TestParziale:
    def test_six_months(self, svc):
        result = svc.calcola_tfr_parziale(Decimal("30000"), 6)
        assert result["accantonamento_annuo"] == 2222.22
        assert result["accantonamento_parziale"] == 1111.11

    def test_full_year(self, svc):
        result = svc.calcola_tfr_parziale(Decimal("30000"), 12)
        assert result["accantonamento_parziale"] == 2222.22

    def test_invalid_months_over_12_raises(self, svc):
        with pytest.raises(ValueError, match="mesi"):
            svc.calcola_tfr_parziale(Decimal("30000"), 13)

    def test_negative_months_raises(self, svc):
        with pytest.raises(ValueError, match="mesi"):
            svc.calcola_tfr_parziale(Decimal("30000"), -1)

    def test_negative_ral_raises(self, svc):
        with pytest.raises(ValueError, match="negativa"):
            svc.calcola_tfr_parziale(Decimal("-1000"), 6)
