"""DEV-406: IVA Calculator (Scorporo + Liquidazione).

Provides:
1. Scorporo IVA — from gross amount extract net + VAT.
2. Liquidazione IVA — sales VAT minus purchase VAT = balance.
3. Forfettario regime coefficient calculation.

References: PRD FR-007 §3.7.3, MVP scope §6.1.
"""

from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any

from app.core.logging import logger

# Standard Italian VAT rates (2026)
ALIQUOTA_ORDINARIA = Decimal("22")
ALIQUOTA_RIDOTTA_10 = Decimal("10")
ALIQUOTA_RIDOTTA_4 = Decimal("4")
ALIQUOTA_SUPER_RIDOTTA_5 = Decimal("5")


class AliquotaIVA(StrEnum):
    """Standard Italian IVA rates."""

    ORDINARIA = "22"
    RIDOTTA_10 = "10"
    RIDOTTA_4 = "4"
    SUPER_RIDOTTA_5 = "5"
    ESENTE = "0"


# Coefficiente di redditività per regime forfettario (by ATECO macro-group)
COEFFICIENTI_FORFETTARIO: dict[str, Decimal] = {
    "commercio": Decimal("40"),
    "servizi_alloggio_ristorazione": Decimal("40"),
    "intermediari_commercio": Decimal("62"),
    "attivita_professionali": Decimal("78"),
    "costruzioni_immobiliari": Decimal("86"),
    "commercio_ambulante_alimentare": Decimal("40"),
    "commercio_ambulante_altro": Decimal("54"),
    "attivita_alimentari": Decimal("40"),
    "altre_attivita": Decimal("67"),
    "industrie_artigianato": Decimal("67"),
}


class IvaCalculatorService:
    """IVA calculation service for Italian VAT operations."""

    @staticmethod
    def scorporo_iva(
        importo_lordo: Decimal,
        aliquota: Decimal = ALIQUOTA_ORDINARIA,
    ) -> dict[str, Any]:
        """Extract net amount and IVA from a gross amount.

        Args:
            importo_lordo: Gross amount (IVA included).
            aliquota: IVA rate percentage (e.g. 22, 10, 4).

        Returns:
            Dict with imponibile (net), iva, importo_lordo, and aliquota.

        Raises:
            ValueError: If amount is negative or rate is invalid.
        """
        if importo_lordo < 0:
            raise ValueError("L'importo lordo non può essere negativo")
        if aliquota < 0 or aliquota > 100:
            raise ValueError("L'aliquota IVA deve essere compresa tra 0 e 100")

        if aliquota == 0:
            return {
                "importo_lordo": float(importo_lordo),
                "imponibile": float(importo_lordo),
                "iva": 0.0,
                "aliquota": 0.0,
            }

        divisore = Decimal("1") + aliquota / Decimal("100")
        imponibile = (importo_lordo / divisore).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        iva = importo_lordo - imponibile

        return {
            "importo_lordo": float(importo_lordo),
            "imponibile": float(imponibile),
            "iva": float(iva),
            "aliquota": float(aliquota),
        }

    @staticmethod
    def calcola_iva(
        imponibile: Decimal,
        aliquota: Decimal = ALIQUOTA_ORDINARIA,
    ) -> dict[str, Any]:
        """Calculate IVA on a net amount (forward calculation).

        Args:
            imponibile: Net taxable amount.
            aliquota: IVA rate percentage.

        Returns:
            Dict with imponibile, iva, importo_lordo, and aliquota.
        """
        if imponibile < 0:
            raise ValueError("L'imponibile non può essere negativo")
        if aliquota < 0 or aliquota > 100:
            raise ValueError("L'aliquota IVA deve essere compresa tra 0 e 100")

        iva = (imponibile * aliquota / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        importo_lordo = imponibile + iva

        return {
            "imponibile": float(imponibile),
            "iva": float(iva),
            "importo_lordo": float(importo_lordo),
            "aliquota": float(aliquota),
        }

    @staticmethod
    def liquidazione_iva(
        iva_vendite: Decimal,
        iva_acquisti: Decimal,
        credito_precedente: Decimal = Decimal("0"),
    ) -> dict[str, Any]:
        """Calculate IVA liquidation balance.

        IVA balance = IVA on sales - IVA on purchases - previous credit.
        Positive = amount to pay; Negative = credit to carry forward.

        Args:
            iva_vendite: Total IVA collected on sales.
            iva_acquisti: Total IVA paid on purchases.
            credito_precedente: IVA credit carried from previous period.

        Returns:
            Dict with iva_vendite, iva_acquisti, credito_precedente, saldo,
            and esito (debito/credito).
        """
        if iva_vendite < 0:
            raise ValueError("L'IVA vendite non può essere negativa")
        if iva_acquisti < 0:
            raise ValueError("L'IVA acquisti non può essere negativa")
        if credito_precedente < 0:
            raise ValueError("Il credito precedente non può essere negativo")

        saldo = iva_vendite - iva_acquisti - credito_precedente
        esito = "debito" if saldo > 0 else "credito" if saldo < 0 else "pareggio"

        return {
            "iva_vendite": float(iva_vendite),
            "iva_acquisti": float(iva_acquisti),
            "credito_precedente": float(credito_precedente),
            "saldo": float(saldo),
            "importo_dovuto": float(max(saldo, Decimal("0"))),
            "credito_residuo": float(abs(min(saldo, Decimal("0")))),
            "esito": esito,
        }

    @staticmethod
    def calcolo_forfettario(
        ricavi: Decimal,
        coefficiente_redditivita: Decimal,
        aliquota_imposta_sostitutiva: Decimal = Decimal("15"),
    ) -> dict[str, Any]:
        """Calculate tax for regime forfettario.

        Forfettario: reddito = ricavi × coefficiente di redditività.
        Tax = reddito × aliquota sostitutiva (15% standard, 5% first 5 years).

        Args:
            ricavi: Total revenue.
            coefficiente_redditivita: Profitability coefficient (percentage).
            aliquota_imposta_sostitutiva: Substitute tax rate (15% or 5%).

        Returns:
            Dict with ricavi, coefficiente, reddito_imponibile, imposta.
        """
        if ricavi < 0:
            raise ValueError("I ricavi non possono essere negativi")
        if coefficiente_redditivita <= 0 or coefficiente_redditivita > 100:
            raise ValueError("Il coefficiente di redditività deve essere tra 0 e 100")
        if aliquota_imposta_sostitutiva not in (Decimal("5"), Decimal("15")):
            raise ValueError("L'aliquota sostitutiva deve essere 5% o 15%")

        reddito = (ricavi * coefficiente_redditivita / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        imposta = (reddito * aliquota_imposta_sostitutiva / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return {
            "ricavi": float(ricavi),
            "coefficiente_redditivita": float(coefficiente_redditivita),
            "reddito_imponibile": float(reddito),
            "aliquota_sostitutiva": float(aliquota_imposta_sostitutiva),
            "imposta_sostitutiva": float(imposta),
            "netto_stimato": float(ricavi - imposta),
        }

    @staticmethod
    def get_coefficiente_by_attivita(tipo_attivita: str) -> Decimal | None:
        """Lookup forfettario profitability coefficient by activity type.

        Args:
            tipo_attivita: Activity type key.

        Returns:
            Coefficient percentage or None if not found.
        """
        return COEFFICIENTI_FORFETTARIO.get(tipo_attivita)


iva_calculator_service = IvaCalculatorService()
