"""Regional Tax Service for Italian Tax Calculations.

DEV-393: Enhanced for PratikoAI 2.0 client-context-aware calculations.

This service handles calculations for Italian regional and municipal taxes
including IMU, IRAP, and IRPEF addizionali with location-based variations.

New in DEV-393:
    - National IRPEF bracket calculator (``calculate_irpef_nazionale``).
    - Province-to-Regione mapping from P.IVA prefix (``get_regione_from_piva_prefix``).
    - All 20 Italian regions configured with addizionale regionale rates.
    - Client-context-aware wrapper for combined tax calculations.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.regional_taxes import (
    DEFAULT_REGIONAL_DATA,
    DEFAULT_TAX_RATES,
    ComunalTaxRate,
    Comune,
    RegionalTaxRate,
    Regione,
)
from app.services.cache import CacheService

# ------------------------------------------------------------------
# DEV-393: IRPEF National Brackets (2026 — Legge di Bilancio 2026)
# ------------------------------------------------------------------
IRPEF_BRACKETS: list[tuple[Decimal, Decimal]] = [
    # (upper_bound, rate) — income up to upper_bound is taxed at rate
    (Decimal("28000"), Decimal("0.23")),
    (Decimal("50000"), Decimal("0.35")),
    (Decimal("999999999"), Decimal("0.43")),  # unlimited last bracket
]


def calculate_irpef_nazionale(imponibile: Decimal) -> Decimal:
    """Calculate national IRPEF using progressive brackets.

    Args:
        imponibile: Taxable income in euros.

    Returns:
        Tax amount in euros (``Decimal("0")`` for zero or negative income).
    """
    if imponibile <= 0:
        return Decimal("0")

    tax = Decimal("0")
    previous_bound = Decimal("0")

    for upper_bound, rate in IRPEF_BRACKETS:
        if imponibile <= previous_bound:
            break
        taxable_in_bracket = min(imponibile, upper_bound) - previous_bound
        if taxable_in_bracket > 0:
            tax += taxable_in_bracket * rate
        previous_bound = upper_bound

    return tax


# ------------------------------------------------------------------
# DEV-393: Province code → Regione mapping (P.IVA first 3 digits)
# ------------------------------------------------------------------
PROVINCE_TO_REGIONE: dict[str, str] = {
    # Piemonte
    "001": "Piemonte",
    "002": "Piemonte",
    "003": "Piemonte",
    "004": "Piemonte",
    "005": "Piemonte",
    "006": "Piemonte",
    "096": "Piemonte",
    "103": "Piemonte",
    # Valle d'Aosta
    "007": "Valle d'Aosta",
    # Lombardia
    "012": "Lombardia",
    "013": "Lombardia",
    "014": "Lombardia",
    "015": "Lombardia",
    "016": "Lombardia",
    "017": "Lombardia",
    "018": "Lombardia",
    "019": "Lombardia",
    "020": "Lombardia",
    "097": "Lombardia",
    "098": "Lombardia",
    "108": "Lombardia",
    # Trentino-Alto Adige
    "021": "Trentino-Alto Adige",
    "022": "Trentino-Alto Adige",
    # Veneto
    "023": "Veneto",
    "024": "Veneto",
    "025": "Veneto",
    "026": "Veneto",
    "027": "Veneto",
    "028": "Veneto",
    "029": "Veneto",
    # Friuli-Venezia Giulia
    "030": "Friuli-Venezia Giulia",
    "031": "Friuli-Venezia Giulia",
    "032": "Friuli-Venezia Giulia",
    "093": "Friuli-Venezia Giulia",
    # Liguria
    "008": "Liguria",
    "009": "Liguria",
    "010": "Liguria",
    "011": "Liguria",
    # Emilia-Romagna
    "033": "Emilia-Romagna",
    "034": "Emilia-Romagna",
    "035": "Emilia-Romagna",
    "036": "Emilia-Romagna",
    "037": "Emilia-Romagna",
    "038": "Emilia-Romagna",
    "039": "Emilia-Romagna",
    "040": "Emilia-Romagna",
    "099": "Emilia-Romagna",
    # Toscana
    "045": "Toscana",
    "046": "Toscana",
    "047": "Toscana",
    "048": "Toscana",
    "049": "Toscana",
    "050": "Toscana",
    "051": "Toscana",
    "052": "Toscana",
    "053": "Toscana",
    "100": "Toscana",
    # Umbria
    "054": "Umbria",
    "055": "Umbria",
    # Marche
    "041": "Marche",
    "042": "Marche",
    "043": "Marche",
    "044": "Marche",
    "109": "Marche",
    # Lazio
    "056": "Lazio",
    "057": "Lazio",
    "058": "Lazio",
    "059": "Lazio",
    "060": "Lazio",
    # Abruzzo
    "066": "Abruzzo",
    "067": "Abruzzo",
    "068": "Abruzzo",
    "069": "Abruzzo",
    # Molise
    "070": "Molise",
    "094": "Molise",
    # Campania
    "061": "Campania",
    "062": "Campania",
    "063": "Campania",
    "064": "Campania",
    "065": "Campania",
    # Puglia
    "071": "Puglia",
    "072": "Puglia",
    "073": "Puglia",
    "074": "Puglia",
    "075": "Puglia",
    "110": "Puglia",
    # Basilicata
    "076": "Basilicata",
    "077": "Basilicata",
    # Calabria
    "078": "Calabria",
    "079": "Calabria",
    "080": "Calabria",
    "101": "Calabria",
    "102": "Calabria",
    # Sicilia
    "081": "Sicilia",
    "082": "Sicilia",
    "083": "Sicilia",
    "084": "Sicilia",
    "085": "Sicilia",
    "086": "Sicilia",
    "087": "Sicilia",
    "088": "Sicilia",
    "089": "Sicilia",
    # Sardegna
    "090": "Sardegna",
    "091": "Sardegna",
    "092": "Sardegna",
    "095": "Sardegna",
    "104": "Sardegna",
    "105": "Sardegna",
    "106": "Sardegna",
    "107": "Sardegna",
}


def get_regione_from_piva_prefix(prefix: str) -> str | None:
    """Map the first 3 digits of a P.IVA to the corresponding regione.

    Args:
        prefix: First 3 digits of a Partita IVA (e.g. ``"058"``).

    Returns:
        Region name or ``None`` if the prefix is unknown.
    """
    return PROVINCE_TO_REGIONE.get(prefix)


# Custom Exceptions


class LocationNotFound(Exception):
    """Raised when a location cannot be found by CAP or name"""

    pass


class TaxRateNotFound(Exception):
    """Raised when tax rates are not available for a location/date"""

    pass


class InvalidTaxCalculation(Exception):
    """Raised when tax calculation parameters are invalid"""

    pass


class RegionalTaxService:
    """Service for calculating Italian regional and municipal taxes.

    Handles IMU, IRAP, and IRPEF addizionali calculations with
    support for all Italian regions and municipalities.
    """

    def __init__(self, db: AsyncSession, cache_service: CacheService | None = None):
        self.db = db
        self.cache = cache_service
        self.default_rates = DEFAULT_TAX_RATES

    # Location Services

    async def get_comune_by_cap(self, cap: str) -> Comune | None:
        """Get comune from CAP (postal code).

        Args:
            cap: Italian postal code (5 digits)

        Returns:
            Comune object or None if not found

        Raises:
            ValueError: If CAP format is invalid
        """
        if not cap or len(cap) != 5 or not cap.isdigit():
            raise ValueError(f"CAP non valido: {cap}")

        # Check cache first
        if self.cache:
            cache_key = f"comune:cap:{cap}"
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

        # Query database
        stmt = select(Comune).where(Comune.cap_codes.contains([cap])).options(selectinload(Comune.regione))

        result = await self.db.execute(stmt)
        comune = result.scalar_one_or_none()

        if comune and self.cache:
            await self.cache.set(cache_key, comune, ttl=86400)  # 24 hours

        return comune

    async def get_comune_by_name(self, nome: str, provincia: str | None = None) -> Comune | None:
        """Get comune by name and optionally provincia"""
        stmt = select(Comune).where(Comune.nome.ilike(f"%{nome}%"))

        if provincia:
            stmt = stmt.where(Comune.provincia == provincia.upper())

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_regione_by_name(self, nome: str) -> Regione | None:
        """Get regione by name"""
        stmt = select(Regione).where(Regione.nome.ilike(f"%{nome}%"))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_regione_by_id(self, regione_id: UUID) -> Regione | None:
        """Get regione by ID"""
        stmt = select(Regione).where(Regione.id == regione_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # Tax Rate Retrieval

    async def get_tax_rates(self, comune_id: UUID, tax_type: str, reference_date: date) -> ComunalTaxRate | None:
        """Get municipal tax rates for a specific date.

        Args:
            comune_id: Municipality ID
            tax_type: Type of tax (IMU, ADDIZIONALE_COMUNALE_IRPEF)
            reference_date: Date for which rates apply

        Returns:
            ComunalTaxRate object or None
        """
        stmt = select(ComunalTaxRate).where(
            and_(
                ComunalTaxRate.comune_id == comune_id,
                ComunalTaxRate.tax_type == tax_type,
                ComunalTaxRate.valid_from <= reference_date,
                or_(ComunalTaxRate.valid_to.is_(None), ComunalTaxRate.valid_to >= reference_date),
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_regional_tax_rates(
        self, regione_id: UUID, tax_type: str, reference_date: date
    ) -> RegionalTaxRate | None:
        """Get regional tax rates for a specific date"""
        stmt = select(RegionalTaxRate).where(
            and_(
                RegionalTaxRate.regione_id == regione_id,
                RegionalTaxRate.tax_type == tax_type,
                RegionalTaxRate.valid_from <= reference_date,
                or_(RegionalTaxRate.valid_to.is_(None), RegionalTaxRate.valid_to >= reference_date),
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_regional_addizionale_irpef(self, regione_id: UUID) -> Decimal:
        """Get regional IRPEF surcharge rate"""
        rates = await self.get_regional_tax_rates(regione_id, "ADDIZIONALE_IRPEF", date.today())

        if rates:
            return rates.rate_standard

        # Fallback to default rates
        regione = await self.get_regione_by_id(regione_id)
        if regione and regione.nome in self.default_rates["ADDIZIONALE_REGIONALE"]:
            return Decimal(str(self.default_rates["ADDIZIONALE_REGIONALE"][regione.nome]))

        return Decimal("1.73")  # Default rate

    async def get_municipal_addizionale_irpef(self, comune_id: UUID) -> Decimal:
        """Get municipal IRPEF surcharge rate"""
        rates = await self.get_tax_rates(comune_id, "ADDIZIONALE_COMUNALE_IRPEF", date.today())

        if rates:
            return rates.rate

        # Fallback to default rates
        comune = await self.db.get(Comune, comune_id)
        if comune and comune.nome in self.default_rates["ADDIZIONALE_COMUNALE"]:
            return Decimal(str(self.default_rates["ADDIZIONALE_COMUNALE"][comune.nome]["rate"]))

        return Decimal("0.8")  # Default rate

    # IMU Calculations

    async def calculate_imu(
        self, property_value: Decimal, cap: str, is_prima_casa: bool = False, property_type: str = "standard"
    ) -> dict[str, Any]:
        """Calculate IMU (Imposta Municipale Unica) with regional variations.

        Args:
            property_value: Property value in euros
            cap: Postal code of property location
            is_prima_casa: Whether it's primary residence
            property_type: Type of property (standard, commerciale, industriale, agricolo)

        Returns:
            Dictionary with calculation details

        Raises:
            LocationNotFound: If CAP cannot be found
            ValueError: If property value is invalid
        """
        if property_value <= 0:
            raise ValueError("Il valore dell'immobile non può essere negativo o zero")

        # Get comune information
        comune = await self.get_comune_by_cap(cap)
        if not comune:
            raise LocationNotFound(f"CAP {cap} non trovato")

        # Get current IMU rates
        rates = await self.get_tax_rates(comune.id, "IMU", date.today())

        if not rates:
            # Use default rates if available
            if comune.nome in self.default_rates["IMU"]:
                default = self.default_rates["IMU"][comune.nome]
                rates = type(
                    "obj",
                    (object,),
                    {
                        "esenzione_prima_casa": default.get("esenzione_prima_casa", False),
                        "rate_prima_casa": Decimal(str(default.get("rate_prima_casa", 0.5))),
                        "rate": Decimal(str(default["rate"])),
                        "detrazioni": default.get("detrazioni", {}),
                    },
                )()
            else:
                raise TaxRateNotFound(f"Aliquote IMU non disponibili per {comune.nome}")

        # Check if exempt
        if is_prima_casa and rates.esenzione_prima_casa:
            return {
                "comune": comune.nome,
                "provincia": comune.provincia,
                "aliquota": 0,
                "base_imponibile": 0,
                "imposta_lorda": 0,
                "detrazioni": 0,
                "imposta_dovuta": 0,
                "note": "Abitazione principale esente IMU",
            }

        # Calculate IMU
        base_imponibile = property_value * Decimal("0.63")  # 63% of cadastral value

        # Get appropriate rate
        if hasattr(rates, "get_rate_for_property_type"):
            aliquota = rates.get_rate_for_property_type(property_type, is_prima_casa)
        else:
            aliquota = rates.rate_prima_casa if is_prima_casa else rates.rate

        imposta_lorda = base_imponibile * aliquota / 100

        # Apply deductions
        detrazioni = Decimal(0)
        if is_prima_casa and hasattr(rates, "detrazioni") and rates.detrazioni:
            detrazioni = Decimal(str(rates.detrazioni.get("abitazione_principale", 0)))
        elif is_prima_casa and hasattr(rates, "get_detrazioni_for_category"):
            detrazioni = rates.get_detrazioni_for_category("abitazione_principale")

        imposta_netta = max(imposta_lorda - detrazioni, Decimal(0))

        return {
            "comune": comune.nome,
            "provincia": comune.provincia,
            "aliquota": float(aliquota),
            "base_imponibile": float(base_imponibile),
            "imposta_lorda": float(imposta_lorda),
            "detrazioni": float(detrazioni),
            "imposta_dovuta": float(imposta_netta),
            "note": "Prima casa" if is_prima_casa else f"Altri immobili - {property_type}",
        }

    # IRAP Calculations

    async def calculate_irap(self, revenue: Decimal, region: str, business_type: str = "standard") -> dict[str, Any]:
        """Calculate IRAP (Imposta Regionale sulle Attività Produttive).

        Args:
            revenue: Annual revenue in euros
            region: Name of the Italian region
            business_type: Type of business (standard, banks, insurance, agriculture, cooperatives)

        Returns:
            Dictionary with calculation details

        Raises:
            LocationNotFound: If region cannot be found
            ValueError: If revenue is invalid
        """
        if revenue <= 0:
            raise ValueError("Il fatturato deve essere positivo")

        # Get region information
        regione = await self.get_regione_by_name(region)
        if not regione:
            raise LocationNotFound(f"Regione {region} non trovata")

        # Get current IRAP rates
        rates = await self.get_regional_tax_rates(regione.id, "IRAP", date.today())

        if not rates:
            # Use default rates
            if regione.nome in self.default_rates["IRAP"]:
                default = self.default_rates["IRAP"][regione.nome]
                rates = type(
                    "obj",
                    (object,),
                    {
                        "rate_standard": Decimal(str(default["rate_standard"])),
                        "rate_banks": Decimal(str(default.get("rate_banks", 5.57))),
                        "rate_insurance": Decimal(str(default.get("rate_insurance", 6.82))),
                        "rate_agriculture": Decimal(str(default.get("rate_agriculture", 1.9))),
                        "rate_cooperatives": Decimal(str(default.get("rate_cooperatives", 3.9))),
                    },
                )()
            else:
                rates = type(
                    "obj",
                    (object,),
                    {
                        "rate_standard": Decimal("3.9"),
                        "rate_banks": Decimal("5.57"),
                        "rate_insurance": Decimal("6.82"),
                        "rate_agriculture": Decimal("1.9"),
                        "rate_cooperatives": Decimal("3.9"),
                    },
                )()

        # Select rate based on business type
        rate_map = {
            "standard": rates.rate_standard,
            "banks": getattr(rates, "rate_banks", rates.rate_standard) or Decimal("5.57"),
            "insurance": getattr(rates, "rate_insurance", rates.rate_standard) or Decimal("6.82"),
            "agriculture": getattr(rates, "rate_agriculture", rates.rate_standard) or Decimal("1.9"),
            "cooperatives": getattr(rates, "rate_cooperatives", rates.rate_standard) or rates.rate_standard,
        }

        aliquota = rate_map.get(business_type, rates.rate_standard)

        # IRAP calculation (simplified)
        valore_produzione = revenue * Decimal("0.85")  # Simplified value of production
        imposta = valore_produzione * aliquota / 100

        return {
            "regione": regione.nome,
            "aliquota": float(aliquota),
            "tipo_attivita": business_type,
            "fatturato": float(revenue),
            "valore_produzione": float(valore_produzione),
            "imposta_dovuta": float(imposta),
            "note": f"Aliquota IRAP {regione.nome} - {business_type}",
        }

    # IRPEF Addizionali Calculations

    async def calculate_irpef_addizionali(self, reddito_imponibile: Decimal, cap: str) -> dict[str, Any]:
        """Calculate regional and municipal IRPEF surcharges.

        Args:
            reddito_imponibile: Taxable income in euros
            cap: Postal code of residence

        Returns:
            Dictionary with both regional and municipal surcharges

        Raises:
            LocationNotFound: If CAP cannot be found
            ValueError: If income is invalid
        """
        if reddito_imponibile < 0:
            raise ValueError("Il reddito imponibile non può essere negativo")

        # Get location information
        comune = await self.get_comune_by_cap(cap)
        if not comune:
            raise LocationNotFound(f"CAP {cap} non trovato")

        regione = await self.get_regione_by_id(comune.regione_id)
        if not regione:
            raise LocationNotFound(f"Regione non trovata per comune {comune.nome}")

        # Get rates
        regional_rate = await self.get_regional_addizionale_irpef(regione.id)
        municipal_rate = await self.get_municipal_addizionale_irpef(comune.id)

        # Check for municipal income thresholds
        municipal_rates_obj = await self.get_tax_rates(comune.id, "ADDIZIONALE_COMUNALE_IRPEF", date.today())

        # Apply threshold logic if applicable
        if municipal_rates_obj and hasattr(municipal_rates_obj, "has_income_threshold_exemption"):
            if municipal_rates_obj.has_income_threshold_exemption(reddito_imponibile):
                municipal_rate = Decimal("0")
        elif comune.nome in self.default_rates["ADDIZIONALE_COMUNALE"]:
            threshold = self.default_rates["ADDIZIONALE_COMUNALE"][comune.nome].get("soglie", {}).get("no_tax_under")
            if threshold and reddito_imponibile < Decimal(str(threshold)):
                municipal_rate = Decimal("0")

        # Calculate surcharges
        addizionale_regionale = reddito_imponibile * regional_rate / 100
        addizionale_comunale = reddito_imponibile * municipal_rate / 100

        return {
            "comune": comune.nome,
            "provincia": comune.provincia,
            "regione": regione.nome,
            "reddito_imponibile": float(reddito_imponibile),
            "addizionale_regionale": {"aliquota": float(regional_rate), "importo": float(addizionale_regionale)},
            "addizionale_comunale": {"aliquota": float(municipal_rate), "importo": float(addizionale_comunale)},
            "totale_addizionali": float(addizionale_regionale + addizionale_comunale),
        }

    # Comprehensive Tax Calculations

    async def calculate_total_tax_burden(
        self,
        cap: str,
        income: Decimal,
        property_value: Decimal | None = None,
        is_prima_casa: bool = True,
        business_revenue: Decimal | None = None,
        business_type: str = "standard",
    ) -> dict[str, Any]:
        """Calculate total regional and municipal tax burden.

        Combines IMU, IRPEF addizionali, and optionally IRAP calculations.
        """
        location = await self.get_location_from_cap(cap)
        results = {"location": location, "calculations": {}, "total": Decimal("0")}

        # IRPEF addizionali
        if income > 0:
            irpef_result = await self.calculate_irpef_addizionali(income, cap)
            results["calculations"]["irpef_addizionali"] = irpef_result
            results["total"] += Decimal(str(irpef_result["totale_addizionali"]))

        # IMU
        if property_value and property_value > 0:
            imu_result = await self.calculate_imu(property_value, cap, is_prima_casa)
            results["calculations"]["imu"] = imu_result
            results["total"] += Decimal(str(imu_result["imposta_dovuta"]))

        # IRAP
        if business_revenue and business_revenue > 0:
            irap_result = await self.calculate_irap(business_revenue, location["regione"], business_type)
            results["calculations"]["irap"] = irap_result
            results["total"] += Decimal(str(irap_result["imposta_dovuta"]))

        results["total"] = float(results["total"])
        return results

    async def compare_regional_taxes(
        self, cap1: str, cap2: str, income: Decimal, property_value: Decimal | None = None
    ) -> dict[str, Any]:
        """Compare tax burden between two locations"""
        location1 = await self.calculate_total_tax_burden(cap1, income, property_value)
        location2 = await self.calculate_total_tax_burden(cap2, income, property_value)

        difference = Decimal(str(location2["total"])) - Decimal(str(location1["total"]))
        percentage_diff = (
            (difference / Decimal(str(location1["total"]))) * 100 if location1["total"] > 0 else Decimal("0")
        )

        return {
            "location1": location1,
            "location2": location2,
            "difference": {
                "amount": float(difference),
                "percentage": float(percentage_diff),
                "favors": location1["location"]["comune"] if difference > 0 else location2["location"]["comune"],
            },
        }

    # Helper Methods

    async def get_location_from_cap(self, cap: str) -> dict[str, Any]:
        """Get complete location information from CAP"""
        comune = await self.get_comune_by_cap(cap)
        if not comune:
            raise LocationNotFound(f"CAP {cap} non trovato")

        regione = await self.get_regione_by_id(comune.regione_id)

        return {
            "cap": cap,
            "comune": comune.nome,
            "provincia": comune.provincia,
            "regione": regione.nome if regione else "Unknown",
            "popolazione": comune.popolazione,
            "is_capoluogo": comune.is_capoluogo,
        }

    async def get_all_rates_for_location(self, cap: str) -> dict[str, Any]:
        """Get all applicable tax rates for a location"""
        comune = await self.get_comune_by_cap(cap)
        if not comune:
            raise LocationNotFound(f"CAP {cap} non trovato")

        regione = await self.get_regione_by_id(comune.regione_id)

        # Get all rates
        imu_rates = await self.get_tax_rates(comune.id, "IMU", date.today())
        addizionale_comunale = await self.get_tax_rates(comune.id, "ADDIZIONALE_COMUNALE_IRPEF", date.today())
        irap_rates = await self.get_regional_tax_rates(regione.id, "IRAP", date.today())
        addizionale_regionale = await self.get_regional_tax_rates(regione.id, "ADDIZIONALE_IRPEF", date.today())

        return {
            "location": {"comune": comune.nome, "provincia": comune.provincia, "regione": regione.nome},
            "imu": imu_rates.to_dict() if imu_rates else None,
            "irap": irap_rates.to_dict() if irap_rates else None,
            "addizionale_regionale": float(addizionale_regionale.rate_standard) if addizionale_regionale else None,
            "addizionale_comunale": float(addizionale_comunale.rate) if addizionale_comunale else None,
            "last_updated": datetime.now().isoformat(),
        }

    # Data Management

    async def bulk_update_rates(self, rate_updates: list[dict[str, Any]], effective_date: date) -> dict[str, int]:
        """Bulk update tax rates"""
        updated = 0
        errors = 0

        for _update in rate_updates:
            try:
                # Implementation would create new rate records
                # with appropriate valid_from dates
                updated += 1
            except Exception as e:
                logger.error(f"Error updating rate: {e}")
                errors += 1

        await self.db.commit()

        return {"updated": updated, "errors": errors}

    async def detect_rate_changes(self, reference_date: date) -> list[dict[str, Any]]:
        """Detect rate changes on a specific date"""
        # Query for rates that start on the reference date
        changes = []

        # Check comunal rates
        stmt = (
            select(ComunalTaxRate)
            .where(ComunalTaxRate.valid_from == reference_date)
            .options(selectinload(ComunalTaxRate.comune))
        )

        result = await self.db.execute(stmt)
        new_rates = result.scalars().all()

        for new_rate in new_rates:
            # Find previous rate
            prev_stmt = select(ComunalTaxRate).where(
                and_(
                    ComunalTaxRate.comune_id == new_rate.comune_id,
                    ComunalTaxRate.tax_type == new_rate.tax_type,
                    ComunalTaxRate.valid_to == reference_date - timedelta(days=1),
                )
            )

            prev_result = await self.db.execute(prev_stmt)
            prev_rate = prev_result.scalar_one_or_none()

            if prev_rate:
                changes.append(
                    {
                        "comune": new_rate.comune.nome,
                        "tax_type": new_rate.tax_type,
                        "old_rate": float(prev_rate.rate),
                        "new_rate": float(new_rate.rate),
                        "change_date": reference_date.isoformat(),
                    }
                )

        return changes

    async def validate_tax_rate(self, rate: Decimal, tax_type: str) -> bool:
        """Validate if a tax rate is within acceptable bounds"""
        if rate < 0:
            raise ValueError("L'aliquota non può essere negativa")

        max_rates = {
            "IMU": Decimal("2.0"),  # Max 2%
            "IRAP": Decimal("8.5"),  # Max 8.5%
            "ADDIZIONALE_COMUNALE_IRPEF": Decimal("0.9"),  # Max 0.9%
            "ADDIZIONALE_IRPEF": Decimal("3.33"),  # Max 3.33%
        }

        max_rate = max_rates.get(tax_type, Decimal("10.0"))
        if rate > max_rate:
            raise ValueError(f"L'aliquota {tax_type} non può superare {max_rate}%")

        return True

    async def log_calculation(self, user_id: UUID, tax_type: str, input_data: dict[str, Any], result: dict[str, Any]):
        """Log tax calculation for analytics"""
        # Implementation would log to a calculations table
        logger.info(
            f"Tax calculation - User: {user_id}, Type: {tax_type}, "
            f"Location: {input_data.get('cap', 'N/A')}, "
            f"Amount: {result.get('imposta_dovuta', 0)}"
        )
