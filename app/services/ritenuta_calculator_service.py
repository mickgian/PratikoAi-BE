"""DEV-407: Ritenuta d'Acconto Calculator.

Supports:
1. Professionisti — 20% withholding on full amount.
2. Agenti/rappresentanti — 23% on 50% of commissions.
3. Other withholding scenarios (occasionale, etc.).

Reference: PRD FR-007 §3.7.3.
"""

from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any

from app.core.logging import logger


class TipoRitenuta(StrEnum):
    """Withholding tax type."""

    PROFESSIONISTA = "professionista"
    AGENTE = "agente"
    OCCASIONALE = "occasionale"
    AMMINISTRATORE = "amministratore"


# Ritenuta d'acconto rates by type
RITENUTA_RATES: dict[str, dict[str, Decimal]] = {
    TipoRitenuta.PROFESSIONISTA: {
        "aliquota": Decimal("20"),
        "base_imponibile_pct": Decimal("100"),
    },
    TipoRitenuta.AGENTE: {
        "aliquota": Decimal("23"),
        "base_imponibile_pct": Decimal("50"),
    },
    TipoRitenuta.OCCASIONALE: {
        "aliquota": Decimal("20"),
        "base_imponibile_pct": Decimal("100"),
    },
    TipoRitenuta.AMMINISTRATORE: {
        "aliquota": Decimal("20"),
        "base_imponibile_pct": Decimal("100"),
    },
}


class RitenutaCalculatorService:
    """Calculator for Italian withholding tax (ritenuta d'acconto)."""

    @staticmethod
    def calcola_ritenuta(
        compenso_lordo: Decimal,
        tipo: TipoRitenuta = TipoRitenuta.PROFESSIONISTA,
        aliquota_override: Decimal | None = None,
        base_imponibile_pct_override: Decimal | None = None,
    ) -> dict[str, Any]:
        """Calculate ritenuta d'acconto.

        Args:
            compenso_lordo: Gross compensation amount.
            tipo: Type of withholding (professionista, agente, etc.).
            aliquota_override: Custom rate (overrides default for type).
            base_imponibile_pct_override: Custom taxable base percentage.

        Returns:
            Dict with compenso_lordo, base_imponibile, ritenuta, netto_percepito.

        Raises:
            ValueError: If amount is negative.
        """
        if compenso_lordo < 0:
            raise ValueError("Il compenso lordo non può essere negativo")

        rates = RITENUTA_RATES.get(tipo)
        if rates is None:
            raise ValueError(f"Tipo di ritenuta non supportato: {tipo}")

        aliquota = aliquota_override if aliquota_override is not None else rates["aliquota"]
        base_pct = (
            base_imponibile_pct_override if base_imponibile_pct_override is not None else rates["base_imponibile_pct"]
        )

        base_imponibile = (compenso_lordo * base_pct / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        ritenuta = (base_imponibile * aliquota / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        netto = compenso_lordo - ritenuta

        logger.info(
            "ritenuta_calculated",
            tipo=tipo,
            compenso_lordo=float(compenso_lordo),
            ritenuta=float(ritenuta),
        )

        return {
            "compenso_lordo": float(compenso_lordo),
            "tipo_ritenuta": tipo.value if isinstance(tipo, TipoRitenuta) else tipo,
            "aliquota": float(aliquota),
            "base_imponibile_percentuale": float(base_pct),
            "base_imponibile": float(base_imponibile),
            "ritenuta": float(ritenuta),
            "netto_percepito": float(netto),
        }

    @staticmethod
    def calcola_netto_da_lordo(
        compenso_lordo: Decimal,
        tipo: TipoRitenuta = TipoRitenuta.PROFESSIONISTA,
        include_iva: bool = False,
        aliquota_iva: Decimal = Decimal("22"),
    ) -> dict[str, Any]:
        """Calculate net amount from gross including optional IVA.

        For professionisti who issue invoices with IVA + ritenuta.

        Args:
            compenso_lordo: Gross compensation (before IVA).
            tipo: Withholding type.
            include_iva: Whether to add IVA to the invoice.
            aliquota_iva: IVA rate if applicable.

        Returns:
            Dict with full invoice breakdown.
        """
        if compenso_lordo < 0:
            raise ValueError("Il compenso lordo non può essere negativo")

        rates = RITENUTA_RATES.get(tipo)
        if rates is None:
            raise ValueError(f"Tipo di ritenuta non supportato: {tipo}")

        # Calculate ritenuta
        base_pct = rates["base_imponibile_pct"]
        aliquota_rit = rates["aliquota"]
        base_imponibile = (compenso_lordo * base_pct / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        ritenuta = (base_imponibile * aliquota_rit / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Calculate IVA if applicable
        iva = Decimal("0")
        if include_iva:
            iva = (compenso_lordo * aliquota_iva / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        totale_fattura = compenso_lordo + iva
        netto_percepito = totale_fattura - ritenuta

        return {
            "compenso_lordo": float(compenso_lordo),
            "iva": float(iva),
            "totale_fattura": float(totale_fattura),
            "ritenuta": float(ritenuta),
            "netto_percepito": float(netto_percepito),
        }


ritenuta_calculator_service = RitenutaCalculatorService()
