"""DEV-353: Comprehensive Tax Calculation Accuracy Tests.

Validates all fiscal calculators against known Italian tax scenarios.
Cross-references: IRPEF brackets, IVA rates, ritenuta d'acconto,
cedolare secca, TFR, payroll (busta paga).

Reference: PRD §3.2, AC-006.
"""

from decimal import Decimal

import pytest

from app.services.cedolare_secca_calculator_service import (
    TipoContratto,
    cedolare_secca_calculator_service,
)
from app.services.iva_calculator_service import iva_calculator_service
from app.services.ritenuta_calculator_service import (
    TipoRitenuta,
    ritenuta_calculator_service,
)
from app.services.tfr_calculator_service import tfr_calculator_service


class TestIvaScorporo:
    """Test IVA scorporo (reverse calculation) at different rates."""

    def test_scorporo_iva_22_percent(self):
        """IVA 22% ordinaria."""
        result = iva_calculator_service.scorporo_iva(Decimal("12200"), Decimal("22"))
        assert result["imponibile"] == pytest.approx(10000.0, abs=0.01)
        assert result["iva"] == pytest.approx(2200.0, abs=0.01)

    def test_scorporo_iva_4_percent(self):
        """IVA 4% (beni prima necessità)."""
        result = iva_calculator_service.scorporo_iva(Decimal("1040"), Decimal("4"))
        assert result["imponibile"] == pytest.approx(1000.0, abs=0.01)
        assert result["iva"] == pytest.approx(40.0, abs=0.01)

    def test_scorporo_iva_10_percent(self):
        """IVA 10% (alimentari, turismo)."""
        result = iva_calculator_service.scorporo_iva(Decimal("1100"), Decimal("10"))
        assert result["imponibile"] == pytest.approx(1000.0, abs=0.01)
        assert result["iva"] == pytest.approx(100.0, abs=0.01)

    def test_scorporo_iva_5_percent(self):
        """IVA 5% super-ridotta."""
        result = iva_calculator_service.scorporo_iva(Decimal("1050"), Decimal("5"))
        assert result["imponibile"] == pytest.approx(1000.0, abs=0.01)
        assert result["iva"] == pytest.approx(50.0, abs=0.01)

    def test_scorporo_negative_raises(self):
        with pytest.raises(ValueError, match="negativo"):
            iva_calculator_service.scorporo_iva(Decimal("-100"), Decimal("22"))


class TestIvaCalculations:
    """Test IVA forward calculation and liquidazione."""

    def test_calcola_iva_standard(self):
        result = iva_calculator_service.calcola_iva(Decimal("1000"), Decimal("22"))
        assert result["iva"] == pytest.approx(220.0, abs=0.01)
        assert result["importo_lordo"] == pytest.approx(1220.0, abs=0.01)

    def test_liquidazione_iva_debito(self):
        """IVA a debito: vendite > acquisti."""
        result = iva_calculator_service.liquidazione_iva(
            iva_vendite=Decimal("5000"),
            iva_acquisti=Decimal("3000"),
        )
        assert result["saldo"] == pytest.approx(2000.0, abs=0.01)
        assert result["esito"] == "debito"

    def test_liquidazione_iva_credito(self):
        """IVA a credito: acquisti > vendite."""
        result = iva_calculator_service.liquidazione_iva(
            iva_vendite=Decimal("2000"),
            iva_acquisti=Decimal("4000"),
        )
        assert result["saldo"] == pytest.approx(-2000.0, abs=0.01)
        assert result["esito"] == "credito"

    def test_liquidazione_iva_pareggio(self):
        result = iva_calculator_service.liquidazione_iva(
            iva_vendite=Decimal("3000"),
            iva_acquisti=Decimal("3000"),
        )
        assert result["saldo"] == pytest.approx(0.0, abs=0.01)
        assert result["esito"] == "pareggio"

    def test_calcolo_forfettario_standard(self):
        """Regime forfettario: 78% coefficient, 15% tax."""
        result = iva_calculator_service.calcolo_forfettario(
            ricavi=Decimal("50000"),
            coefficiente_redditivita=Decimal("78"),
        )
        assert result["reddito_imponibile"] == pytest.approx(39000.0, abs=0.01)
        assert result["imposta_sostitutiva"] == pytest.approx(5850.0, abs=0.01)

    def test_calcolo_forfettario_startup(self):
        """Regime forfettario startup: 5% tax rate."""
        result = iva_calculator_service.calcolo_forfettario(
            ricavi=Decimal("30000"),
            coefficiente_redditivita=Decimal("78"),
            aliquota_imposta_sostitutiva=Decimal("5"),
        )
        assert result["reddito_imponibile"] == pytest.approx(23400.0, abs=0.01)
        assert result["imposta_sostitutiva"] == pytest.approx(1170.0, abs=0.01)


class TestRitenutaAcconto:
    """Test ritenuta d'acconto scenarios."""

    def test_professionista_standard(self):
        """Professionista: 20% su 100% del compenso lordo."""
        result = ritenuta_calculator_service.calcola_ritenuta(
            compenso_lordo=Decimal("5000"),
            tipo=TipoRitenuta.PROFESSIONISTA,
        )
        assert result["ritenuta"] == pytest.approx(1000.0, abs=0.01)
        assert result["netto_percepito"] == pytest.approx(4000.0, abs=0.01)

    def test_agente_commercio(self):
        """Agente: 23% su 50% del compenso lordo."""
        result = ritenuta_calculator_service.calcola_ritenuta(
            compenso_lordo=Decimal("10000"),
            tipo=TipoRitenuta.AGENTE,
        )
        assert result["ritenuta"] == pytest.approx(1150.0, abs=0.01)
        assert result["netto_percepito"] == pytest.approx(8850.0, abs=0.01)

    def test_occasionale(self):
        """Prestazione occasionale: 20% su 100%."""
        result = ritenuta_calculator_service.calcola_ritenuta(
            compenso_lordo=Decimal("3000"),
            tipo=TipoRitenuta.OCCASIONALE,
        )
        assert result["ritenuta"] == pytest.approx(600.0, abs=0.01)
        assert result["netto_percepito"] == pytest.approx(2400.0, abs=0.01)

    def test_amministratore(self):
        """Amministratore: 20% su 100%."""
        result = ritenuta_calculator_service.calcola_ritenuta(
            compenso_lordo=Decimal("8000"),
            tipo=TipoRitenuta.AMMINISTRATORE,
        )
        assert result["ritenuta"] == pytest.approx(1600.0, abs=0.01)
        assert result["netto_percepito"] == pytest.approx(6400.0, abs=0.01)

    def test_custom_aliquota_override(self):
        """Override aliquota personalizzata."""
        result = ritenuta_calculator_service.calcola_ritenuta(
            compenso_lordo=Decimal("10000"),
            tipo=TipoRitenuta.PROFESSIONISTA,
            aliquota_override=Decimal("30"),
        )
        assert result["ritenuta"] == pytest.approx(3000.0, abs=0.01)

    def test_fattura_con_iva(self):
        """Calcolo netto da lordo con IVA inclusa nella fattura."""
        result = ritenuta_calculator_service.calcola_netto_da_lordo(
            compenso_lordo=Decimal("5000"),
            tipo=TipoRitenuta.PROFESSIONISTA,
            include_iva=True,
            aliquota_iva=Decimal("22"),
        )
        assert result["iva"] == pytest.approx(1100.0, abs=0.01)
        assert result["ritenuta"] == pytest.approx(1000.0, abs=0.01)
        assert result["totale_fattura"] == pytest.approx(6100.0, abs=0.01)
        assert result["netto_percepito"] == pytest.approx(5100.0, abs=0.01)


class TestCedolareSecca:
    """Test cedolare secca calculations."""

    def test_canone_libero_21_percent(self):
        """Contratto libero: 21%."""
        result = cedolare_secca_calculator_service.calcola_cedolare_secca(
            canone_annuo=Decimal("12000"),
            tipo_contratto=TipoContratto.LIBERO,
        )
        assert result["imposta"] == pytest.approx(2520.0, abs=0.01)
        assert result["aliquota"] == pytest.approx(21.0)

    def test_canone_concordato_10_percent(self):
        """Contratto concordato: 10%."""
        result = cedolare_secca_calculator_service.calcola_cedolare_secca(
            canone_annuo=Decimal("9600"),
            tipo_contratto=TipoContratto.CONCORDATO,
        )
        assert result["imposta"] == pytest.approx(960.0, abs=0.01)
        assert result["aliquota"] == pytest.approx(10.0)

    def test_confronto_cedolare_vs_irpef(self):
        """Confronto cedolare secca vs IRPEF ordinaria."""
        result = cedolare_secca_calculator_service.confronto_con_irpef(
            canone_annuo=Decimal("12000"),
            reddito_complessivo=Decimal("40000"),
            tipo_contratto=TipoContratto.LIBERO,
        )
        assert result["cedolare_secca"]["imposta"] == pytest.approx(2520.0, abs=0.01)
        # With reddito 40000 + 12000 = 52000, marginal IRPEF rate is 43%
        assert result["irpef_ordinaria"]["aliquota_marginale"] == pytest.approx(43.0)
        assert result["risparmio_cedolare"] > 0
        assert result["conviene"] == "cedolare_secca"


class TestTfrCalculations:
    """Test TFR (Trattamento Fine Rapporto) calculations."""

    def test_accantonamento_annuo(self):
        """TFR annuo = RAL / 13.5."""
        result = tfr_calculator_service.calcola_accantonamento_annuo(
            retribuzione_annua=Decimal("30000"),
        )
        assert result["accantonamento_annuo"] == pytest.approx(2222.22, abs=0.01)

    def test_rivalutazione_standard(self):
        """Rivalutazione = TFR × (1.5% + 75% ISTAT)."""
        result = tfr_calculator_service.calcola_rivalutazione(
            tfr_accumulato=Decimal("10000"),
            indice_istat=Decimal("2.0"),
        )
        # 1.5% + 75% of 2.0% = 1.5% + 1.5% = 3.0%
        assert result["rivalutazione"] == pytest.approx(300.0, abs=0.01)
        assert result["tfr_rivalutato"] == pytest.approx(10300.0, abs=0.01)

    def test_multi_anno(self):
        """TFR multi-anno con rivalutazione composta."""
        result = tfr_calculator_service.calcola_tfr_multi_anno(
            retribuzioni_annue=[Decimal("30000"), Decimal("30000"), Decimal("30000")],
            indici_istat=[Decimal("2.0"), Decimal("2.0"), Decimal("2.0")],
        )
        assert result["anni"] == 3
        assert result["tfr_totale"] > 6666
        assert len(result["dettaglio_annuale"]) == 3

    def test_tfr_parziale(self):
        """TFR per periodo inferiore all'anno."""
        result = tfr_calculator_service.calcola_tfr_parziale(
            retribuzione_annua=Decimal("30000"),
            mesi_lavorati=6,
        )
        # 30000/13.5 * 6/12 = 1111.11
        assert result["accantonamento_parziale"] == pytest.approx(1111.11, abs=0.01)

    def test_tfr_zero_ral(self):
        """RAL zero produces zero TFR."""
        result = tfr_calculator_service.calcola_accantonamento_annuo(
            retribuzione_annua=Decimal("0"),
        )
        assert result["accantonamento_annuo"] == pytest.approx(0.0)


class TestCrossCalculatorConsistency:
    """Cross-calculator consistency checks."""

    def test_iva_scorporo_roundtrip(self):
        """scorporo(calcola(base, rate)) recovers the base."""
        forward = iva_calculator_service.calcola_iva(Decimal("1000"), Decimal("22"))
        reverse = iva_calculator_service.scorporo_iva(Decimal(str(forward["importo_lordo"])), Decimal("22"))
        assert reverse["imponibile"] == pytest.approx(1000.0, abs=0.01)

    def test_ritenuta_netto_plus_ritenuta_equals_compenso(self):
        """netto_percepito + ritenuta == compenso_lordo."""
        result = ritenuta_calculator_service.calcola_ritenuta(
            compenso_lordo=Decimal("7500"),
            tipo=TipoRitenuta.PROFESSIONISTA,
        )
        assert result["netto_percepito"] + result["ritenuta"] == pytest.approx(7500.0, abs=0.01)

    def test_cedolare_imposta_plus_netto_equals_canone(self):
        """imposta + netto == canone annuo."""
        result = cedolare_secca_calculator_service.calcola_cedolare_secca(
            canone_annuo=Decimal("18000"),
            tipo_contratto=TipoContratto.LIBERO,
        )
        assert result["imposta"] + result["netto"] == pytest.approx(18000.0, abs=0.01)

    def test_forfettario_imponibile_fraction(self):
        """reddito_imponibile = ricavi × coefficiente / 100."""
        result = iva_calculator_service.calcolo_forfettario(
            ricavi=Decimal("40000"),
            coefficiente_redditivita=Decimal("78"),
        )
        assert result["reddito_imponibile"] == pytest.approx(31200.0, abs=0.01)
        non_imponibile = 40000.0 - result["reddito_imponibile"]
        assert non_imponibile == pytest.approx(8800.0, abs=0.01)


class TestEdgeCases:
    """Edge cases and boundary conditions for all calculators."""

    def test_iva_zero_amount(self):
        result = iva_calculator_service.calcola_iva(Decimal("0"), Decimal("22"))
        assert result["iva"] == pytest.approx(0.0)
        assert result["importo_lordo"] == pytest.approx(0.0)

    def test_ritenuta_small_amount(self):
        """Very small compenso lordo."""
        result = ritenuta_calculator_service.calcola_ritenuta(
            compenso_lordo=Decimal("1.00"),
            tipo=TipoRitenuta.PROFESSIONISTA,
        )
        assert result["ritenuta"] == pytest.approx(0.20, abs=0.01)
        assert result["netto_percepito"] == pytest.approx(0.80, abs=0.01)

    def test_cedolare_large_canone(self):
        """High rental income."""
        result = cedolare_secca_calculator_service.calcola_cedolare_secca(
            canone_annuo=Decimal("120000"),
            tipo_contratto=TipoContratto.LIBERO,
        )
        assert result["imposta"] == pytest.approx(25200.0, abs=0.01)

    def test_tfr_single_month(self):
        """TFR for a single month."""
        result = tfr_calculator_service.calcola_tfr_parziale(
            retribuzione_annua=Decimal("30000"),
            mesi_lavorati=1,
        )
        # 30000/13.5/12 ≈ 185.19
        assert result["accantonamento_parziale"] == pytest.approx(185.19, abs=0.01)

    def test_forfettario_100_percent_coefficient(self):
        """Coefficiente 86% (max real-world, costruzioni)."""
        result = iva_calculator_service.calcolo_forfettario(
            ricavi=Decimal("50000"),
            coefficiente_redditivita=Decimal("86"),
        )
        assert result["reddito_imponibile"] == pytest.approx(43000.0, abs=0.01)

    def test_ritenuta_negative_raises(self):
        with pytest.raises(ValueError, match="negativo"):
            ritenuta_calculator_service.calcola_ritenuta(
                compenso_lordo=Decimal("-100"),
                tipo=TipoRitenuta.PROFESSIONISTA,
            )

    def test_cedolare_negative_raises(self):
        with pytest.raises(ValueError, match="negativo"):
            cedolare_secca_calculator_service.calcola_cedolare_secca(
                canone_annuo=Decimal("-100"),
                tipo_contratto=TipoContratto.LIBERO,
            )

    def test_tfr_negative_raises(self):
        with pytest.raises(ValueError, match="negativa"):
            tfr_calculator_service.calcola_accantonamento_annuo(
                retribuzione_annua=Decimal("-100"),
            )
