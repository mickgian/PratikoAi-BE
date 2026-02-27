"""DEV-410: Tests for Payroll Calculator (Netto in Busta / Costo Azienda).

Tests: RAL to net, RAL to employer cost, different rates, regional variations.
"""

from decimal import Decimal

import pytest

from app.services.payroll_calculator_service import PayrollCalculatorService


@pytest.fixture
def svc():
    return PayrollCalculatorService()


class TestNettoDaRal:
    def test_standard_ral_30k(self, svc):
        result = svc.calcola_netto_da_ral(Decimal("30000"))
        assert result["ral"] == 30000.0
        assert result["inps_dipendente"] > 0
        assert result["irpef_lorda"] > 0
        assert result["netto_annuo"] > 0
        assert result["netto_mensile"] > 0
        # Net should be less than RAL
        assert result["netto_annuo"] < 30000.0

    def test_standard_ral_50k(self, svc):
        result = svc.calcola_netto_da_ral(Decimal("50000"))
        assert result["netto_annuo"] < 50000.0
        assert result["netto_annuo"] > 0

    def test_14_mensilita(self, svc):
        result_13 = svc.calcola_netto_da_ral(Decimal("30000"), numero_mensilita=13)
        result_14 = svc.calcola_netto_da_ral(Decimal("30000"), numero_mensilita=14)
        assert result_13["netto_annuo"] == result_14["netto_annuo"]
        assert result_14["netto_mensile"] < result_13["netto_mensile"]

    def test_different_regional_rates(self, svc):
        result_low = svc.calcola_netto_da_ral(Decimal("30000"), addizionale_regionale_pct=Decimal("1.23"))
        result_high = svc.calcola_netto_da_ral(Decimal("30000"), addizionale_regionale_pct=Decimal("2.03"))
        assert result_low["netto_annuo"] > result_high["netto_annuo"]

    def test_no_detrazioni(self, svc):
        result_with = svc.calcola_netto_da_ral(Decimal("30000"), apply_detrazioni=True)
        result_without = svc.calcola_netto_da_ral(Decimal("30000"), apply_detrazioni=False)
        assert result_with["netto_annuo"] > result_without["netto_annuo"]

    def test_zero_ral(self, svc):
        result = svc.calcola_netto_da_ral(Decimal("0"))
        assert result["netto_annuo"] == 0.0

    def test_negative_ral_raises(self, svc):
        with pytest.raises(ValueError, match="negativa"):
            svc.calcola_netto_da_ral(Decimal("-1"))


class TestCostoAzienda:
    def test_standard_ral_30k(self, svc):
        result = svc.calcola_costo_azienda(Decimal("30000"))
        assert result["ral"] == 30000.0
        assert result["inps_datore"] > 0
        assert result["inail"] > 0
        assert result["tfr_accantonamento"] > 0
        # Total cost should be > RAL
        assert result["costo_totale_azienda"] > 30000.0

    def test_no_tfr(self, svc):
        with_tfr = svc.calcola_costo_azienda(Decimal("30000"), include_tfr=True)
        without_tfr = svc.calcola_costo_azienda(Decimal("30000"), include_tfr=False)
        assert with_tfr["costo_totale_azienda"] > without_tfr["costo_totale_azienda"]
        assert without_tfr["tfr_accantonamento"] == 0.0

    def test_percentuale_maggiorazione(self, svc):
        result = svc.calcola_costo_azienda(Decimal("30000"))
        # Employer cost should be ~30-35% more than RAL
        assert result["percentuale_maggiorazione"] > 20
        assert result["percentuale_maggiorazione"] < 40

    def test_negative_ral_raises(self, svc):
        with pytest.raises(ValueError, match="negativa"):
            svc.calcola_costo_azienda(Decimal("-1"))


class TestCalcoloCompleto:
    def test_full_calculation(self, svc):
        result = svc.calcola_completo(Decimal("30000"))
        assert "netto_dipendente" in result
        assert "costo_azienda" in result
        assert result["netto_dipendente"]["netto_annuo"] > 0
        assert result["costo_azienda"]["costo_totale_azienda"] > 30000
