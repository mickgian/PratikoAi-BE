"""
CCNL Integration API endpoints for real-time updates, alerts, contributions, and multilingual support.
"""

from datetime import date, datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel, Field

from app.models.ccnl_data import CCNLSector, WorkerCategory
from app.services.ccnl_update_service import ccnl_update_service, UpdateType, AlertType
from app.services.inps_inail_service import inps_inail_service, RiskClass
from app.services.i18n_service import i18n_service, Language

router = APIRouter(prefix="/ccnl-integration", tags=["CCNL Integration"])


# Pydantic models for API requests/responses

class UpdateCheckRequest(BaseModel):
    """Request to check for CCNL updates."""
    sectors: Optional[List[CCNLSector]] = None
    check_all: bool = True


class UpdateCheckResponse(BaseModel):
    """Response from update check."""
    updates_found: int
    updates: List[Dict[str, Any]]
    last_check: datetime
    next_check: datetime


class AlertResponse(BaseModel):
    """Response for CCNL alerts."""
    id: str
    sector: CCNLSector
    alert_type: AlertType
    title: str
    message: str
    severity: str
    created_at: datetime
    acknowledged: bool


class ContributionCalculationRequest(BaseModel):
    """Request for contribution calculation."""
    gross_salary: Decimal = Field(..., gt=0, description="Monthly gross salary in euros")
    sector: CCNLSector
    worker_category: WorkerCategory
    company_size: str = Field("medium", pattern="^(small|medium|large)$")


class ContributionCalculationResponse(BaseModel):
    """Response for contribution calculation."""
    gross_salary: Decimal
    inps_employee: Decimal
    inps_employer: Decimal
    inail_employer: Decimal
    total_employee_contributions: Decimal
    total_employer_contributions: Decimal
    net_salary: Decimal
    contribution_rates: Dict[str, Decimal]
    risk_class: str
    calculation_date: date


class TranslationRequest(BaseModel):
    """Request for translations."""
    keys: List[str]
    language: Language = Language.ITALIAN
    sector: Optional[CCNLSector] = None


class LocalizedSectorResponse(BaseModel):
    """Localized sector information."""
    sector: CCNLSector
    sector_name: str
    description: str
    typical_companies: str
    language: Language


# Update Management Endpoints

@router.get("/updates/check", response_model=UpdateCheckResponse)
async def check_ccnl_updates(request: UpdateCheckRequest = Depends()):
    """
    Check for available CCNL updates from official sources.
    
    This endpoint checks government databases, union websites, and employer
    associations for new CCNL versions or updates.
    """
    try:
        updates = await ccnl_update_service.check_for_updates()
        
        if request.sectors:
            # Filter updates by requested sectors
            updates = [u for u in updates if u.sector in request.sectors]
        
        return UpdateCheckResponse(
            updates_found=len(updates),
            updates=[
                {
                    "sector": update.sector.value,
                    "update_type": update.update_type.value,
                    "effective_date": update.effective_date.isoformat(),
                    "changes_summary": update.changes_summary,
                    "impact_level": update.impact_level,
                    "updated_fields": update.updated_fields
                }
                for update in updates
            ],
            last_check=datetime.utcnow(),
            next_check=datetime.utcnow().replace(hour=datetime.utcnow().hour + 4)  # Next check in 4 hours
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking for updates: {str(e)}")


@router.get("/alerts", response_model=List[AlertResponse])
async def get_active_alerts():
    """
    Get all active CCNL alerts.
    
    Returns alerts for expiring contracts, renewal notifications,
    and other important CCNL-related events.
    """
    try:
        alerts = await ccnl_update_service.get_active_alerts()
        
        return [
            AlertResponse(
                id=alert.id,
                sector=alert.sector,
                alert_type=alert.alert_type,
                title=alert.title,
                message=alert.message,
                severity=alert.severity,
                created_at=alert.created_at,
                acknowledged=alert.acknowledged
            )
            for alert in alerts
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str = Path(...)):
    """Acknowledge a CCNL alert."""
    try:
        await ccnl_update_service.acknowledge_alert(alert_id)
        return {"message": "Alert acknowledged successfully", "alert_id": alert_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error acknowledging alert: {str(e)}")


@router.get("/expiration-alerts")
async def generate_expiration_alerts():
    """
    Generate alerts for expiring CCNL agreements.
    
    Checks all CCNL agreements and creates alerts for those
    expiring within 90 days or already expired.
    """
    try:
        alerts = await ccnl_update_service.generate_expiration_alerts()
        
        return {
            "alerts_generated": len(alerts),
            "alerts": [
                {
                    "sector": alert.sector.value,
                    "alert_type": alert.alert_type.value,
                    "title": alert.title,
                    "message": alert.message,
                    "severity": alert.severity
                }
                for alert in alerts
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating expiration alerts: {str(e)}")


# INPS/INAIL Integration Endpoints

@router.post("/contributions/calculate", response_model=ContributionCalculationResponse)
async def calculate_contributions(request: ContributionCalculationRequest):
    """
    Calculate INPS/INAIL contributions for a given salary and sector.
    
    This endpoint calculates:
    - INPS employee contributions
    - INPS employer contributions  
    - INAIL employer contributions
    - Net salary after deductions
    """
    try:
        calculation = await inps_inail_service.calculate_contributions(
            request.gross_salary,
            request.sector,
            request.worker_category,
            request.company_size
        )
        
        rates = await inps_inail_service.get_contribution_rates(
            request.sector,
            request.worker_category
        )
        
        risk_class = await inps_inail_service.get_sector_risk_class(request.sector)
        
        return ContributionCalculationResponse(
            gross_salary=calculation.gross_salary,
            inps_employee=calculation.inps_employee,
            inps_employer=calculation.inps_employer,
            inail_employer=calculation.inail_employer,
            total_employee_contributions=calculation.total_employee_contributions,
            total_employer_contributions=calculation.total_employer_contributions,
            net_salary=calculation.net_salary,
            contribution_rates=rates,
            risk_class=risk_class.value,
            calculation_date=calculation.calculation_date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating contributions: {str(e)}")


@router.get("/contributions/rates")
async def get_contribution_rates(
    sector: CCNLSector = Query(...),
    worker_category: WorkerCategory = Query(...)
):
    """Get current contribution rates for a sector and worker category."""
    try:
        rates = await inps_inail_service.get_contribution_rates(sector, worker_category)
        risk_class = await inps_inail_service.get_sector_risk_class(sector)
        
        return {
            "sector": sector.value,
            "worker_category": worker_category.value,
            "rates": rates,
            "risk_class": risk_class.value,
            "effective_date": date.today().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving contribution rates: {str(e)}")


@router.get("/contributions/annual-summary")
async def get_annual_contribution_summary(
    sector: CCNLSector = Query(...),
    worker_category: WorkerCategory = Query(...),
    annual_salary: Decimal = Query(..., gt=0)
):
    """Get annual contribution summary for planning purposes."""
    try:
        summary = await inps_inail_service.get_annual_contribution_summary(
            sector, worker_category, annual_salary
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating annual summary: {str(e)}")


@router.get("/contributions/history/{sector}")
async def get_contribution_history(sector: CCNLSector = Path(...)):
    """Get historical contribution rates for a sector."""
    try:
        history = await inps_inail_service.get_contribution_history(sector)
        return {
            "sector": sector.value,
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving contribution history: {str(e)}")


# Multilingual Support Endpoints

@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages."""
    return {
        "supported_languages": [lang.value for lang in i18n_service.get_supported_languages()],
        "default_language": i18n_service.default_language.value
    }


@router.post("/translate")
async def translate_keys(request: TranslationRequest):
    """Translate multiple keys to specified language."""
    try:
        translations = {}
        
        for key in request.keys:
            if request.sector:
                # Sector-specific translation
                translations[key] = i18n_service.translate_sector(
                    request.sector, key, request.language
                )
            else:
                # General translation
                translations[key] = i18n_service.translate(key, request.language)
        
        return {
            "language": request.language.value,
            "translations": translations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error translating keys: {str(e)}")


@router.get("/sectors/{sector}/localized", response_model=LocalizedSectorResponse)
async def get_localized_sector_info(
    sector: CCNLSector = Path(...),
    language: Language = Query(Language.ITALIAN)
):
    """Get localized information for a specific sector."""
    try:
        sector_info = i18n_service.get_localized_ccnl_summary(sector, language)
        
        return LocalizedSectorResponse(
            sector=sector,
            sector_name=sector_info["sector_name"],
            description=sector_info["description"],
            typical_companies=sector_info["typical_companies"],
            language=language
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving localized sector info: {str(e)}")


@router.get("/sectors/localized")
async def get_all_localized_sectors(language: Language = Query(Language.ITALIAN)):
    """Get localized information for all sectors."""
    try:
        localized_sectors = []
        
        for sector in CCNLSector:
            try:
                sector_info = i18n_service.get_localized_ccnl_summary(sector, language)
                localized_sectors.append({
                    "sector": sector.value,
                    "sector_name": sector_info["sector_name"],
                    "description": sector_info["description"],
                    "typical_companies": sector_info["typical_companies"]
                })
            except Exception:
                # Skip sectors without translations
                continue
        
        return {
            "language": language.value,
            "sectors": localized_sectors,
            "total_sectors": len(localized_sectors)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving localized sectors: {str(e)}")


@router.get("/translations/export/{language}")
async def export_translations(language: Language = Path(...)):
    """Export all translations for a language (useful for frontend apps)."""
    try:
        translations = i18n_service.export_translations(language)
        return {
            "language": language.value,
            "translations": translations,
            "total_translations": len(translations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting translations: {str(e)}")


# System Status and Statistics

@router.get("/status")
async def get_integration_status():
    """Get overall status of CCNL integration features."""
    try:
        update_stats = await ccnl_update_service.get_update_statistics()
        active_alerts = await ccnl_update_service.get_active_alerts()
        translation_validation = i18n_service.validate_translations()
        
        return {
            "update_service": {
                "status": "active",
                "pending_updates": update_stats["total_pending_updates"],
                "active_alerts": len(active_alerts),
                "last_check": update_stats["last_update_check"]
            },
            "inps_inail_service": {
                "status": "active",
                "supported_sectors": len(CCNLSector),
                "risk_classes": len(RiskClass)
            },
            "i18n_service": {
                "status": "active",
                "supported_languages": len(i18n_service.get_supported_languages()),
                "translation_completeness": translation_validation["translation_completeness"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving integration status: {str(e)}")


@router.get("/statistics")
async def get_integration_statistics():
    """Get detailed statistics about CCNL integration usage."""
    try:
        update_stats = await ccnl_update_service.get_update_statistics()
        return {
            "ccnl_updates": update_stats,
            "contribution_calculations": {
                "total_sectors": len(CCNLSector),
                "risk_classes": len(RiskClass),
                "worker_categories": len(WorkerCategory)
            },
            "multilingual_support": i18n_service.validate_translations()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")
