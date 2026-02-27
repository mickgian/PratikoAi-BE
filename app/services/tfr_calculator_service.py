"""DEV-409: TFR (Trattamento Fine Rapporto) Calculator.

Annual accrual = annual retribution / 13.5
Revaluation uses ISTAT index + 1.5% fixed rate.

Reference: PRD FR-007 §3.7.3.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.core.logging import logger

# TFR constants
TFR_DIVISOR = Decimal("13.5")
FIXED_REVALUATION_RATE = Decimal("1.5")  # 1.5% fixed
ISTAT_REVALUATION_SHARE = Decimal("75")  # 75% of ISTAT index


class TfrCalculatorService:
    """Calculator for Italian TFR (severance pay)."""

    @staticmethod
    def calcola_accantonamento_annuo(
        retribuzione_annua: Decimal,
    ) -> dict[str, Any]:
        """Calculate annual TFR accrual.

        TFR annual accrual = RAL / 13.5

        Args:
            retribuzione_annua: Annual gross salary (RAL).

        Returns:
            Dict with retribuzione_annua and accantonamento_annuo.
        """
        if retribuzione_annua < 0:
            raise ValueError("La retribuzione annua non può essere negativa")

        accantonamento = (retribuzione_annua / TFR_DIVISOR).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "retribuzione_annua": float(retribuzione_annua),
            "accantonamento_annuo": float(accantonamento),
        }

    @staticmethod
    def calcola_rivalutazione(
        tfr_accumulato: Decimal,
        indice_istat: Decimal,
    ) -> dict[str, Any]:
        """Calculate TFR revaluation for a year.

        Revaluation = TFR * (1.5% + 75% of ISTAT index)

        Args:
            tfr_accumulato: TFR accumulated at start of year.
            indice_istat: Annual ISTAT consumer price index (percentage).

        Returns:
            Dict with revaluation details.
        """
        if tfr_accumulato < 0:
            raise ValueError("Il TFR accumulato non può essere negativo")
        if indice_istat < 0:
            raise ValueError("L'indice ISTAT non può essere negativo")

        quota_istat = (indice_istat * ISTAT_REVALUATION_SHARE / Decimal("100")).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        tasso_rivalutazione = FIXED_REVALUATION_RATE + quota_istat
        rivalutazione = (tfr_accumulato * tasso_rivalutazione / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return {
            "tfr_accumulato": float(tfr_accumulato),
            "indice_istat": float(indice_istat),
            "quota_istat_75": float(quota_istat),
            "tasso_rivalutazione": float(tasso_rivalutazione),
            "rivalutazione": float(rivalutazione),
            "tfr_rivalutato": float(tfr_accumulato + rivalutazione),
        }

    @staticmethod
    def calcola_tfr_multi_anno(
        retribuzioni_annue: list[Decimal],
        indici_istat: list[Decimal],
    ) -> dict[str, Any]:
        """Calculate TFR accumulation over multiple years.

        Args:
            retribuzioni_annue: List of annual salaries per year.
            indici_istat: List of ISTAT indexes per year (same length).

        Returns:
            Dict with yearly breakdown and total TFR.
        """
        if len(retribuzioni_annue) != len(indici_istat):
            raise ValueError("Le liste retribuzioni e indici ISTAT devono avere la stessa lunghezza")
        if not retribuzioni_annue:
            raise ValueError("Le liste non possono essere vuote")

        tfr_totale = Decimal("0")
        dettaglio_annuale = []

        for anno_idx, (ral, istat) in enumerate(zip(retribuzioni_annue, indici_istat, strict=False), 1):
            if ral < 0:
                raise ValueError(f"La retribuzione dell'anno {anno_idx} non può essere negativa")

            # Revalue existing TFR
            rivalutazione = Decimal("0")
            if tfr_totale > 0 and anno_idx > 1:
                quota_istat = (istat * ISTAT_REVALUATION_SHARE / Decimal("100")).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )
                tasso = FIXED_REVALUATION_RATE + quota_istat
                rivalutazione = (tfr_totale * tasso / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                tfr_totale += rivalutazione

            # Add new accrual
            accantonamento = (ral / TFR_DIVISOR).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            tfr_totale += accantonamento

            dettaglio_annuale.append(
                {
                    "anno": anno_idx,
                    "retribuzione": float(ral),
                    "accantonamento": float(accantonamento),
                    "rivalutazione": float(rivalutazione),
                    "tfr_cumulato": float(tfr_totale),
                }
            )

        return {
            "anni": len(retribuzioni_annue),
            "tfr_totale": float(tfr_totale),
            "dettaglio_annuale": dettaglio_annuale,
        }

    @staticmethod
    def calcola_tfr_parziale(
        retribuzione_annua: Decimal,
        mesi_lavorati: int,
    ) -> dict[str, Any]:
        """Calculate partial-year TFR accrual.

        For employees who don't work a full year (start/end mid-year).
        Fractions >= 15 days count as a full month.

        Args:
            retribuzione_annua: Annual gross salary.
            mesi_lavorati: Months worked (1-12).

        Returns:
            Dict with partial accrual details.
        """
        if retribuzione_annua < 0:
            raise ValueError("La retribuzione non può essere negativa")
        if mesi_lavorati < 0 or mesi_lavorati > 12:
            raise ValueError("I mesi lavorati devono essere tra 0 e 12")

        accantonamento_annuo = (retribuzione_annua / TFR_DIVISOR).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        accantonamento_parziale = (accantonamento_annuo * Decimal(str(mesi_lavorati)) / Decimal("12")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return {
            "retribuzione_annua": float(retribuzione_annua),
            "mesi_lavorati": mesi_lavorati,
            "accantonamento_annuo": float(accantonamento_annuo),
            "accantonamento_parziale": float(accantonamento_parziale),
        }


tfr_calculator_service = TfrCalculatorService()
