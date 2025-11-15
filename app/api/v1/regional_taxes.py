"""Regional Tax API Endpoints for Italian Tax Calculations.

This module provides REST API endpoints for Italian regional and municipal
tax calculations including IMU, IRAP, and IRPEF addizionali.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.database import get_async_session as get_db
from app.core.logging import logger
from app.core.rate_limiting import rate_limit
from app.models.user import User
from app.services.location_service import InvalidCAP, ItalianLocationService, LocationAmbiguous
from app.services.regional_tax_service import (
    InvalidTaxCalculation,
    LocationNotFound,
    RegionalTaxService,
    TaxRateNotFound,
)

router = APIRouter(prefix="/regional-taxes", tags=["Regional Taxes"])


# Request Models


class IMUCalculationRequest(BaseModel):
    """Request for IMU calculation"""

    property_value: float = Field(..., gt=0, description="Valore catastale dell'immobile in euro")
    cap: str = Field(..., pattern=r"^\d{5}$", description="CAP dell'immobile")
    is_prima_casa: bool = Field(False, description="È abitazione principale")
    property_type: str = Field("standard", description="Tipo immobile (standard, commerciale, industriale, agricolo)")

    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v):
        allowed_types = ["standard", "commerciale", "industriale", "agricolo"]
        if v not in allowed_types:
            raise ValueError(f"Tipo immobile deve essere uno di: {', '.join(allowed_types)}")
        return v


class IRAPCalculationRequest(BaseModel):
    """Request for IRAP calculation"""

    revenue: float = Field(..., gt=0, description="Fatturato annuo in euro")
    region: str = Field(..., description="Nome della regione")
    business_type: str = Field("standard", description="Tipo attività")

    @field_validator("business_type")
    @classmethod
    def validate_business_type(cls, v):
        allowed_types = ["standard", "banks", "insurance", "agriculture", "cooperatives"]
        if v not in allowed_types:
            raise ValueError(f"Tipo attività deve essere uno di: {', '.join(allowed_types)}")
        return v


class IRPEFAddizionaliRequest(BaseModel):
    """Request for IRPEF addizionali calculation"""

    taxable_income: float = Field(..., ge=0, description="Reddito imponibile IRPEF in euro")
    cap: str = Field(..., pattern=r"^\d{5}$", description="CAP di residenza")


class CompleteTaxCalculationRequest(BaseModel):
    """Request for complete regional tax calculation"""

    cap: str = Field(..., pattern=r"^\d{5}$", description="CAP di riferimento")
    income: float | None = Field(None, ge=0, description="Reddito imponibile per addizionali IRPEF")
    property_value: float | None = Field(None, gt=0, description="Valore immobile per IMU")
    is_prima_casa: bool = Field(True, description="Immobile è abitazione principale")
    business_revenue: float | None = Field(None, gt=0, description="Fatturato per IRAP")
    business_type: str = Field("standard", description="Tipo attività per IRAP")

    @field_validator("business_type")
    @classmethod
    def validate_business_type(cls, v):
        allowed_types = ["standard", "banks", "insurance", "agriculture", "cooperatives"]
        if v not in allowed_types:
            raise ValueError(f"Tipo attività deve essere uno di: {', '.join(allowed_types)}")
        return v


class LocationSearchRequest(BaseModel):
    """Request for location search"""

    query: str = Field(..., min_length=2, description="Termine di ricerca (comune, provincia)")
    region_filter: str | None = Field(None, description="Filtro per regione")
    limit: int = Field(10, ge=1, le=50, description="Numero massimo risultati")


class AddressValidationRequest(BaseModel):
    """Request for address validation"""

    cap: str = Field(..., pattern=r"^\d{5}$", description="Codice postale")
    comune: str | None = Field(None, description="Nome comune")
    provincia: str | None = Field(None, pattern=r"^[A-Z]{2}$", description="Sigla provincia")
    regione: str | None = Field(None, description="Nome regione")


# Response Models


class LocationResponse(BaseModel):
    """Location information response"""

    cap: str
    comune: str
    provincia: str
    regione: str
    popolazione: int | None
    is_capoluogo: bool
    is_capoluogo_provincia: bool
    area_kmq: float | None
    coordinates: dict[str, float | None] | None


class TaxRatesResponse(BaseModel):
    """Tax rates for a location"""

    location: LocationResponse
    rates: dict[str, Any]
    last_updated: str


class IMUCalculationResponse(BaseModel):
    """IMU calculation result"""

    location: dict[str, str]
    calculation: dict[str, Any]
    timestamp: str


class IRAPCalculationResponse(BaseModel):
    """IRAP calculation result"""

    region_info: dict[str, str]
    calculation: dict[str, Any]
    timestamp: str


class IRPEFAddizionaliResponse(BaseModel):
    """IRPEF addizionali calculation result"""

    location: dict[str, str]
    calculation: dict[str, Any]
    timestamp: str


class CompleteTaxCalculationResponse(BaseModel):
    """Complete tax calculation result"""

    location: dict[str, Any]
    calculations: dict[str, Any]
    total_regional_taxes: float
    timestamp: str


class TaxComparisonResponse(BaseModel):
    """Tax burden comparison between locations"""

    location1: dict[str, Any]
    location2: dict[str, Any]
    difference: dict[str, Any]
    timestamp: str


class LocationSearchResponse(BaseModel):
    """Location search results"""

    results: list[LocationResponse]
    total_count: int
    query: str


class AddressValidationResponse(BaseModel):
    """Address validation result"""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    corrections: dict[str, Any]
    confidence: float


# API Endpoints


@router.get("/rates/{cap}", response_model=TaxRatesResponse)
@rate_limit("regional_tax_rates", max_requests=100, window_hours=1)
async def get_regional_tax_rates(
    cap: str = Path(..., pattern=r"^\d{5}$", description="CAP della località"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaxRatesResponse:
    """Ottieni tutte le aliquote fiscali per una specifica località.

    Restituisce IMU, IRAP, addizionale regionale e comunale IRPEF
    per la località identificata dal CAP fornito.
    """
    try:
        service = RegionalTaxService(db)
        location_service = ItalianLocationService(db)

        # Get location info
        location = await location_service.get_location_from_cap(cap)

        # Get all applicable rates
        rates = await service.get_all_rates_for_location(cap)

        logger.info(f"Tax rates retrieved for CAP {cap} by user {current_user.id}")

        return TaxRatesResponse(
            location=LocationResponse(**location), rates=rates, last_updated=datetime.now().isoformat()
        )

    except LocationNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving tax rates for {cap}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno del sistema")


@router.post("/calculate/imu", response_model=IMUCalculationResponse)
@rate_limit("imu_calculation", max_requests=50, window_hours=1)
async def calculate_imu_tax(
    request: IMUCalculationRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> IMUCalculationResponse:
    """Calcola l'IMU con variazioni regionali.

    L'IMU (Imposta Municipale Unica) varia significativamente tra comuni.
    Alcuni comuni esentano l'abitazione principale, altri applicano
    aliquote ridotte o maggiorate.
    """
    try:
        service = RegionalTaxService(db)

        result = await service.calculate_imu(
            property_value=Decimal(str(request.property_value)),
            cap=request.cap,
            is_prima_casa=request.is_prima_casa,
            property_type=request.property_type,
        )

        # Log calculation
        await service.log_calculation(
            user_id=current_user.id, tax_type="IMU", input_data=request.dict(), result=result
        )

        logger.info(
            f"IMU calculated for user {current_user.id}: "
            f"CAP {request.cap}, value €{request.property_value}, "
            f"tax €{result['imposta_dovuta']}"
        )

        return IMUCalculationResponse(
            location={"comune": result["comune"], "provincia": result["provincia"], "cap": request.cap},
            calculation=result,
            timestamp=datetime.now().isoformat(),
        )

    except LocationNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating IMU: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore nel calcolo IMU")


@router.post("/calculate/irap", response_model=IRAPCalculationResponse)
@rate_limit("irap_calculation", max_requests=50, window_hours=1)
async def calculate_irap_tax(
    request: IRAPCalculationRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> IRAPCalculationResponse:
    """Calcola l'IRAP con variazioni regionali.

    L'IRAP (Imposta Regionale sulle Attività Produttive) varia per regione
    e tipo di attività. Le banche e assicurazioni pagano aliquote maggiori,
    l'agricoltura aliquote ridotte.
    """
    try:
        service = RegionalTaxService(db)

        result = await service.calculate_irap(
            revenue=Decimal(str(request.revenue)), region=request.region, business_type=request.business_type
        )

        # Log calculation
        await service.log_calculation(
            user_id=current_user.id, tax_type="IRAP", input_data=request.dict(), result=result
        )

        logger.info(
            f"IRAP calculated for user {current_user.id}: "
            f"region {request.region}, revenue €{request.revenue}, "
            f"tax €{result['imposta_dovuta']}"
        )

        return IRAPCalculationResponse(
            region_info={"regione": result["regione"], "tipo_attivita": result["tipo_attivita"]},
            calculation=result,
            timestamp=datetime.now().isoformat(),
        )

    except LocationNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating IRAP: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore nel calcolo IRAP")


@router.post("/calculate/irpef-addizionali", response_model=IRPEFAddizionaliResponse)
@rate_limit("irpef_addizionali", max_requests=50, window_hours=1)
async def calculate_irpef_addizionali(
    request: IRPEFAddizionaliRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IRPEFAddizionaliResponse:
    """Calcola le addizionali IRPEF regionali e comunali.

    Le addizionali IRPEF variano significativamente:
    - Regionale: da 1.23% (Bolzano) al 3.33% (massimo)
    - Comunale: da 0% al 0.9% con soglie di esenzione diverse
    """
    try:
        service = RegionalTaxService(db)

        result = await service.calculate_irpef_addizionali(
            reddito_imponibile=Decimal(str(request.taxable_income)), cap=request.cap
        )

        # Log calculation
        await service.log_calculation(
            user_id=current_user.id, tax_type="IRPEF_ADDIZIONALI", input_data=request.dict(), result=result
        )

        logger.info(
            f"IRPEF addizionali calculated for user {current_user.id}: "
            f"CAP {request.cap}, income €{request.taxable_income}, "
            f"total €{result['totale_addizionali']}"
        )

        return IRPEFAddizionaliResponse(
            location={
                "comune": result["comune"],
                "provincia": result["provincia"],
                "regione": result["regione"],
                "cap": request.cap,
            },
            calculation=result,
            timestamp=datetime.now().isoformat(),
        )

    except LocationNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating IRPEF addizionali: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore nel calcolo addizionali IRPEF"
        )


@router.post("/calculate/complete", response_model=CompleteTaxCalculationResponse)
@rate_limit("complete_tax_calculation", max_requests=20, window_hours=1)
async def calculate_complete_regional_taxes(
    request: CompleteTaxCalculationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompleteTaxCalculationResponse:
    """Calcola il carico fiscale regionale e comunale completo.

    Combina IMU, IRAP e addizionali IRPEF per fornire una visione
    completa del carico fiscale territoriale.
    """
    try:
        service = RegionalTaxService(db)

        # Prepare optional parameters
        income = Decimal(str(request.income)) if request.income else None
        property_value = Decimal(str(request.property_value)) if request.property_value else None
        business_revenue = Decimal(str(request.business_revenue)) if request.business_revenue else None

        result = await service.calculate_total_tax_burden(
            cap=request.cap,
            income=income or Decimal("0"),
            property_value=property_value,
            is_prima_casa=request.is_prima_casa,
            business_revenue=business_revenue,
            business_type=request.business_type,
        )

        # Log calculation
        await service.log_calculation(
            user_id=current_user.id, tax_type="COMPLETE_REGIONAL", input_data=request.dict(), result=result
        )

        logger.info(
            f"Complete tax calculation for user {current_user.id}: CAP {request.cap}, total €{result['total']}"
        )

        return CompleteTaxCalculationResponse(
            location=result["location"],
            calculations=result["calculations"],
            total_regional_taxes=result["total"],
            timestamp=datetime.now().isoformat(),
        )

    except LocationNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating complete taxes: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore nel calcolo completo")


@router.get("/compare", response_model=TaxComparisonResponse)
@rate_limit("tax_comparison", max_requests=10, window_hours=1)
async def compare_regional_taxes(
    cap1: str = Query(..., pattern=r"^\d{5}$", description="CAP prima località"),
    cap2: str = Query(..., pattern=r"^\d{5}$", description="CAP seconda località"),
    income: float = Query(..., ge=0, description="Reddito imponibile per confronto"),
    property_value: float | None = Query(None, gt=0, description="Valore immobile (opzionale)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaxComparisonResponse:
    """Confronta il carico fiscale tra due località.

    Utile per valutare la convenienza fiscale nel trasferimento
    di residenza o sede d'impresa.
    """
    try:
        service = RegionalTaxService(db)

        result = await service.compare_regional_taxes(
            cap1=cap1,
            cap2=cap2,
            income=Decimal(str(income)),
            property_value=Decimal(str(property_value)) if property_value else None,
        )

        logger.info(
            f"Tax comparison for user {current_user.id}: "
            f"{cap1} vs {cap2}, difference €{result['difference']['amount']}"
        )

        return TaxComparisonResponse(
            location1=result["location1"],
            location2=result["location2"],
            difference=result["difference"],
            timestamp=datetime.now().isoformat(),
        )

    except LocationNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error comparing taxes: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore nel confronto fiscale")


# Location Services


@router.post("/locations/search", response_model=LocationSearchResponse)
@rate_limit("location_search", max_requests=100, window_hours=1)
async def search_locations(
    request: LocationSearchRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> LocationSearchResponse:
    """Cerca località per nome con filtri opzionali.

    Permette di trovare comuni, province e regioni
    per nome parziale o completo.
    """
    try:
        service = ItalianLocationService(db)

        results = await service.search_locations(
            query=request.query, limit=request.limit, region_filter=request.region_filter
        )

        logger.info(f"Location search by user {current_user.id}: query '{request.query}', {len(results)} results")

        return LocationSearchResponse(
            results=[LocationResponse(**result) for result in results], total_count=len(results), query=request.query
        )

    except Exception as e:
        logger.error(f"Error searching locations: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore nella ricerca località")


@router.post("/locations/validate", response_model=AddressValidationResponse)
@rate_limit("address_validation", max_requests=100, window_hours=1)
async def validate_italian_address(
    request: AddressValidationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddressValidationResponse:
    """Valida un indirizzo italiano completo.

    Verifica la coerenza tra CAP, comune, provincia e regione,
    suggerendo correzioni quando necessario.
    """
    try:
        service = ItalianLocationService(db)

        address_components = {
            "cap": request.cap,
            "comune": request.comune,
            "provincia": request.provincia,
            "regione": request.regione,
        }

        result = await service.validate_italian_address(address_components)

        logger.info(f"Address validation by user {current_user.id}: CAP {request.cap}, valid: {result['is_valid']}")

        return AddressValidationResponse(**result)

    except Exception as e:
        logger.error(f"Error validating address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore nella validazione indirizzo"
        )


@router.get("/locations/{cap}", response_model=LocationResponse)
@rate_limit("location_lookup", max_requests=200, window_hours=1)
async def get_location_by_cap(
    cap: str = Path(..., pattern=r"^\d{5}$", description="CAP della località"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    """Ottieni informazioni complete su una località dal CAP.

    Restituisce comune, provincia, regione, popolazione e
    altre informazioni geografiche e amministrative.
    """
    try:
        service = ItalianLocationService(db)

        location = await service.get_location_from_cap(cap)

        logger.info(f"Location lookup by user {current_user.id}: CAP {cap}")

        return LocationResponse(**location)

    except InvalidCAP as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LocationNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error looking up location: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore nella ricerca località")


@router.get("/locations/{cap}/nearby")
@rate_limit("nearby_locations", max_requests=50, window_hours=1)
async def get_nearby_locations(
    cap: str = Path(..., pattern=r"^\d{5}$", description="CAP di riferimento"),
    radius_km: float = Query(50, ge=1, le=200, description="Raggio di ricerca in km"),
    limit: int = Query(10, ge=1, le=50, description="Numero massimo risultati"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LocationResponse]:
    """Trova località vicine entro un raggio specificato.

    Utile per analizzare le variazioni fiscali nell'area
    geografica di interesse.
    """
    try:
        service = ItalianLocationService(db)

        nearby = await service.get_nearby_locations(cap=cap, radius_km=radius_km, limit=limit)

        logger.info(
            f"Nearby locations search by user {current_user.id}: "
            f"CAP {cap}, radius {radius_km}km, {len(nearby)} results"
        )

        return [LocationResponse(**location) for location in nearby]

    except InvalidCAP as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LocationNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error finding nearby locations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore nella ricerca località vicine"
        )


# Administrative Endpoints


@router.get("/statistics/overview")
@rate_limit("tax_statistics", max_requests=10, window_hours=1)
async def get_regional_tax_overview(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Panoramica delle variazioni fiscali regionali in Italia.

    Fornisce statistiche aggregate su IMU, IRAP e addizionali
    per tutte le regioni italiane.
    """
    try:
        # This would typically query aggregated data
        overview = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "regioni_total": 20,
                "comuni_major": 110,  # Major cities with data
                "range_imu": {"min": 0.8, "max": 1.14, "average": 1.06},
                "range_irap": {"min": 3.9, "max": 4.82, "average": 4.1},
                "range_addizionale_regionale": {"min": 1.23, "max": 3.33, "average": 1.75},
                "range_addizionale_comunale": {"min": 0.0, "max": 0.9, "average": 0.65},
            },
            "regions_highest_taxes": [
                {"regione": "Lazio", "irap": 4.82, "note": "IRAP più alta"},
                {"regione": "Campania", "addizionale_regionale": 2.03, "note": "Addizionale regionale alta"},
            ],
            "regions_lowest_taxes": [
                {"regione": "Lombardia", "irap": 3.9, "note": "IRAP standard"},
                {"regione": "Bolzano", "addizionale_regionale": 1.23, "note": "Addizionale più bassa"},
            ],
            "cities_highest_imu": [
                {"comune": "Napoli", "imu": 1.14},
                {"comune": "Roma", "imu": 1.06},
                {"comune": "Torino", "imu": 1.06},
            ],
            "cities_lowest_imu": [{"comune": "Milano", "imu": 1.04}],
        }

        logger.info(f"Tax overview requested by user {current_user.id}")

        return overview

    except Exception as e:
        logger.error(f"Error generating tax overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore nella generazione panoramica"
        )


@router.get("/compliance/info")
async def get_regional_tax_compliance_info() -> dict[str, Any]:
    """Informazioni sulla conformità e fonti legislative.

    Fornisce riferimenti normativi e informazioni sulla
    conformità del sistema di calcolo fiscale regionale.
    """
    return {
        "legal_framework": {
            "imu": {
                "law": "D.Lgs. 504/1992 e successive modificazioni",
                "authority": "Comuni italiani",
                "last_update": "2024-01-01",
                "variation_range": "0.76% - 1.14%",
                "notes": "Aliquote deliberate annualmente dai consigli comunali",
            },
            "irap": {
                "law": "D.Lgs. 446/1997 e successive modificazioni",
                "authority": "Regioni italiane",
                "last_update": "2024-01-01",
                "variation_range": "3.9% - 4.82%",
                "notes": "Le regioni possono modificare l'aliquota base del 3.9%",
            },
            "addizionale_irpef": {
                "law": "D.Lgs. 360/1998 per regionale, D.Lgs. 504/1992 per comunale",
                "authority": "Regioni e Comuni",
                "last_update": "2024-01-01",
                "variation_range": "Regionale: 1.23% - 3.33%, Comunale: 0% - 0.9%",
                "notes": "Soglie di esenzione variabili per comune",
            },
        },
        "data_sources": [
            "Ministero dell'Economia e delle Finanze",
            "Agenzia delle Entrate",
            "Delibere comunali e regionali pubblicate",
            "ISTAT per dati demografici e geografici",
        ],
        "update_frequency": "Annuale con aggiornamenti straordinari",
        "accuracy_disclaimer": "I calcoli sono indicativi e basati su aliquote standard. Per calcoli definitivi consultare i regolamenti locali vigenti.",
        "support_contact": "support@pratikoai.com",
    }
