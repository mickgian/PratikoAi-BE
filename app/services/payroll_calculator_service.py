"""DEV-410: Netto in Busta / Costo Azienda Calculator.

Supports:
1. From RAL → net salary (RAL - INPS employee - IRPEF - addizionali).
2. From RAL → employer cost (RAL + INPS employer + INAIL + TFR accrual).

Reference: PRD FR-007 §3.7.3.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.core.logging import logger
from app.services.regional_tax_service import calculate_irpef_nazionale

# Default INPS rates (2026)
INPS_EMPLOYEE_RATE = Decimal("9.19")  # Dipendente quota
INPS_EMPLOYER_RATE = Decimal("23.81")  # Datore quota
INAIL_RATE = Decimal("0.40")  # Average INAIL rate (varies by sector)
TFR_DIVISOR = Decimal("13.5")

# Deduction thresholds for lavoro dipendente (2026)
DETRAZIONI_LAVORO = [
    (Decimal("15000"), Decimal("1955")),
    (Decimal("28000"), Decimal("1910")),
    (Decimal("50000"), Decimal("1190")),
]


def _calcola_detrazione_lavoro_dipendente(reddito: Decimal) -> Decimal:
    """Calculate employee income tax deduction (detrazione lavoro dipendente)."""
    if reddito <= 0:
        return Decimal("0")
    if reddito <= Decimal("15000"):
        return Decimal("1955")
    if reddito <= Decimal("28000"):
        base = Decimal("1910")
        riduzione = base * (reddito - Decimal("15000")) / Decimal("13000")
        return max(base - riduzione, Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if reddito <= Decimal("50000"):
        base = Decimal("1190")
        riduzione = base * (reddito - Decimal("28000")) / Decimal("22000")
        return max(base - riduzione, Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal("0")


class PayrollCalculatorService:
    """Calculator for Italian payroll: net salary and employer cost."""

    @staticmethod
    def calcola_netto_da_ral(
        ral: Decimal,
        *,
        inps_employee_rate: Decimal = INPS_EMPLOYEE_RATE,
        addizionale_regionale_pct: Decimal = Decimal("1.73"),
        addizionale_comunale_pct: Decimal = Decimal("0.8"),
        numero_mensilita: int = 13,
        apply_detrazioni: bool = True,
    ) -> dict[str, Any]:
        """Calculate net salary from RAL (Retribuzione Annua Lorda).

        RAL → -INPS employee → taxable income → -IRPEF → -addizionali → net

        Args:
            ral: Annual gross salary.
            inps_employee_rate: INPS employee rate percentage.
            addizionale_regionale_pct: Regional IRPEF surcharge percentage.
            addizionale_comunale_pct: Municipal IRPEF surcharge percentage.
            numero_mensilita: Number of monthly payments (13 or 14).
            apply_detrazioni: Whether to apply work income deductions.

        Returns:
            Dict with full breakdown.
        """
        if ral < 0:
            raise ValueError("La RAL non può essere negativa")

        # Step 1: INPS employee contribution
        inps_dipendente = (ral * inps_employee_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Step 2: Taxable income
        reddito_imponibile = ral - inps_dipendente

        # Step 3: IRPEF
        irpef_lorda = calculate_irpef_nazionale(reddito_imponibile)

        # Step 4: Deductions
        detrazioni = Decimal("0")
        if apply_detrazioni:
            detrazioni = _calcola_detrazione_lavoro_dipendente(reddito_imponibile)
        irpef_netta = max(irpef_lorda - detrazioni, Decimal("0"))

        # Step 5: Addizionali
        add_regionale = (reddito_imponibile * addizionale_regionale_pct / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        add_comunale = (reddito_imponibile * addizionale_comunale_pct / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Step 6: Net
        netto_annuo = reddito_imponibile - irpef_netta - add_regionale - add_comunale
        netto_mensile = (netto_annuo / Decimal(str(numero_mensilita))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        logger.info(
            "payroll_netto_calculated",
            ral=float(ral),
            netto_annuo=float(netto_annuo),
        )

        return {
            "ral": float(ral),
            "inps_dipendente": float(inps_dipendente),
            "reddito_imponibile": float(reddito_imponibile),
            "irpef_lorda": float(irpef_lorda),
            "detrazioni_lavoro": float(detrazioni),
            "irpef_netta": float(irpef_netta),
            "addizionale_regionale": float(add_regionale),
            "addizionale_comunale": float(add_comunale),
            "netto_annuo": float(netto_annuo),
            "netto_mensile": float(netto_mensile),
            "numero_mensilita": numero_mensilita,
        }

    @staticmethod
    def calcola_costo_azienda(
        ral: Decimal,
        *,
        inps_employer_rate: Decimal = INPS_EMPLOYER_RATE,
        inail_rate: Decimal = INAIL_RATE,
        include_tfr: bool = True,
    ) -> dict[str, Any]:
        """Calculate total employer cost from RAL.

        Employer cost = RAL + INPS employer + INAIL + TFR accrual

        Args:
            ral: Annual gross salary.
            inps_employer_rate: INPS employer rate percentage.
            inail_rate: INAIL insurance rate percentage.
            include_tfr: Whether to include TFR accrual.

        Returns:
            Dict with employer cost breakdown.
        """
        if ral < 0:
            raise ValueError("La RAL non può essere negativa")

        inps_datore = (ral * inps_employer_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        inail = (ral * inail_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tfr_accrual = Decimal("0")
        if include_tfr:
            tfr_accrual = (ral / TFR_DIVISOR).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        costo_totale = ral + inps_datore + inail + tfr_accrual

        logger.info(
            "payroll_costo_azienda_calculated",
            ral=float(ral),
            costo_totale=float(costo_totale),
        )

        return {
            "ral": float(ral),
            "inps_datore": float(inps_datore),
            "inail": float(inail),
            "tfr_accantonamento": float(tfr_accrual),
            "costo_totale_azienda": float(costo_totale),
            "percentuale_maggiorazione": float(
                ((costo_totale - ral) / ral * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if ral > 0
                else Decimal("0")
            ),
        }

    @staticmethod
    def calcola_completo(
        ral: Decimal,
        *,
        addizionale_regionale_pct: Decimal = Decimal("1.73"),
        addizionale_comunale_pct: Decimal = Decimal("0.8"),
    ) -> dict[str, Any]:
        """Full payroll calculation: net salary + employer cost.

        Args:
            ral: Annual gross salary.
            addizionale_regionale_pct: Regional surcharge.
            addizionale_comunale_pct: Municipal surcharge.

        Returns:
            Dict with both employee net and employer cost.
        """
        svc = PayrollCalculatorService()
        netto = svc.calcola_netto_da_ral(
            ral,
            addizionale_regionale_pct=addizionale_regionale_pct,
            addizionale_comunale_pct=addizionale_comunale_pct,
        )
        costo = svc.calcola_costo_azienda(ral)

        return {
            "ral": float(ral),
            "netto_dipendente": netto,
            "costo_azienda": costo,
        }


payroll_calculator_service = PayrollCalculatorService()
