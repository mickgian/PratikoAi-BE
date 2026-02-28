"""DEV-408: Cedolare Secca Calculator.

Flat-rate tax on rental income:
- 21% ordinary rate.
- 10% reduced rate for canone concordato (agreed-rent) contracts.

Reference: PRD FR-007 §3.7.3.
"""

from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any

from app.core.logging import logger


class TipoContratto(StrEnum):
    """Rental contract type."""

    LIBERO = "libero"
    CONCORDATO = "concordato"


ALIQUOTA_ORDINARIA = Decimal("21")
ALIQUOTA_CONCORDATO = Decimal("10")


class CedolareSeccaCalculatorService:
    """Calculator for cedolare secca (flat-rate rental tax)."""

    @staticmethod
    def calcola_cedolare_secca(
        canone_annuo: Decimal,
        tipo_contratto: TipoContratto = TipoContratto.LIBERO,
    ) -> dict[str, Any]:
        """Calculate cedolare secca on rental income.

        Args:
            canone_annuo: Annual rent amount.
            tipo_contratto: Contract type (libero=21%, concordato=10%).

        Returns:
            Dict with canone_annuo, aliquota, imposta, netto.

        Raises:
            ValueError: If rent is negative.
        """
        if canone_annuo < 0:
            raise ValueError("Il canone annuo non può essere negativo")

        aliquota = ALIQUOTA_CONCORDATO if tipo_contratto == TipoContratto.CONCORDATO else ALIQUOTA_ORDINARIA

        imposta = (canone_annuo * aliquota / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        netto = canone_annuo - imposta

        logger.info(
            "cedolare_secca_calculated",
            tipo_contratto=tipo_contratto,
            canone_annuo=float(canone_annuo),
            imposta=float(imposta),
        )

        return {
            "canone_annuo": float(canone_annuo),
            "tipo_contratto": tipo_contratto.value if isinstance(tipo_contratto, TipoContratto) else tipo_contratto,
            "aliquota": float(aliquota),
            "imposta": float(imposta),
            "netto": float(netto),
        }

    @staticmethod
    def confronto_con_irpef(
        canone_annuo: Decimal,
        reddito_complessivo: Decimal,
        tipo_contratto: TipoContratto = TipoContratto.LIBERO,
    ) -> dict[str, Any]:
        """Compare cedolare secca with ordinary IRPEF taxation.

        Under ordinary IRPEF, rental income is taxed at marginal rate.
        The comparison helps landlords decide which regime is more convenient.

        Args:
            canone_annuo: Annual rent amount.
            reddito_complessivo: Total income (for marginal IRPEF rate).
            tipo_contratto: Contract type.

        Returns:
            Dict with both tax amounts and the more convenient option.
        """
        if canone_annuo < 0:
            raise ValueError("Il canone annuo non può essere negativo")
        if reddito_complessivo < 0:
            raise ValueError("Il reddito complessivo non può essere negativo")

        # Cedolare secca
        aliquota_cs = ALIQUOTA_CONCORDATO if tipo_contratto == TipoContratto.CONCORDATO else ALIQUOTA_ORDINARIA
        imposta_cs = (canone_annuo * aliquota_cs / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # IRPEF marginal rate estimate (2026 brackets)
        reddito_totale = reddito_complessivo + canone_annuo
        if reddito_totale <= Decimal("28000"):
            aliquota_irpef = Decimal("23")
        elif reddito_totale <= Decimal("50000"):
            aliquota_irpef = Decimal("35")
        else:
            aliquota_irpef = Decimal("43")

        # Under ordinary IRPEF for concordato contracts, only 66.5% is taxed
        if tipo_contratto == TipoContratto.CONCORDATO:
            base_irpef = canone_annuo * Decimal("66.5") / Decimal("100")
        else:
            base_irpef = canone_annuo

        imposta_irpef = (base_irpef * aliquota_irpef / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        risparmio = imposta_irpef - imposta_cs
        conviene = "cedolare_secca" if risparmio > 0 else "irpef_ordinaria" if risparmio < 0 else "indifferente"

        return {
            "canone_annuo": float(canone_annuo),
            "tipo_contratto": tipo_contratto.value if isinstance(tipo_contratto, TipoContratto) else tipo_contratto,
            "cedolare_secca": {
                "aliquota": float(aliquota_cs),
                "imposta": float(imposta_cs),
            },
            "irpef_ordinaria": {
                "aliquota_marginale": float(aliquota_irpef),
                "base_imponibile": float(base_irpef),
                "imposta": float(imposta_irpef),
            },
            "risparmio_cedolare": float(risparmio),
            "conviene": conviene,
        }


cedolare_secca_calculator_service = CedolareSeccaCalculatorService()
