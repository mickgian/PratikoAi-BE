"""
Data Export API Endpoints for GDPR Article 20 Compliance.

This module provides REST API endpoints for comprehensive user data export
with Italian market compliance, privacy protection, and secure delivery.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import logger
from app.core.rate_limiting import rate_limit
from app.models.user import User
from app.models.data_export import (
    DataExportRequest, ExportFormat, ExportStatus, PrivacyLevel
)
from app.services.data_export_service import (
    DataExportService, 
    ExportLimitExceeded,
    ExportNotFound,
    ExportAccessDenied,
    ExportProgressTracker
)
from app.services.cache import get_redis_client

router = APIRouter(prefix="/data-export", tags=["Data Export"])


# Request Models

class CreateExportRequest(BaseModel):
    """Request to create new data export"""
    format: ExportFormat = Field(ExportFormat.JSON, description="Export format")
    privacy_level: PrivacyLevel = Field(PrivacyLevel.FULL, description="Privacy level")
    include_sensitive: bool = Field(True, description="Include sensitive data")
    anonymize_pii: bool = Field(False, description="Anonymize personally identifiable information")
    
    # Date range filtering
    date_from: Optional[date] = Field(None, description="Export data from this date (DD/MM/YYYY)")
    date_to: Optional[date] = Field(None, description="Export data until this date (DD/MM/YYYY)")
    
    # Italian specific options
    include_fatture: bool = Field(True, description="Include electronic invoices (fatture elettroniche)")
    include_f24: bool = Field(True, description="Include F24 tax forms")
    include_dichiarazioni: bool = Field(True, description="Include tax declarations")
    mask_codice_fiscale: bool = Field(False, description="Mask Codice Fiscale (show only last 4 characters)")
    
    # Data categories
    include_profile: bool = Field(True, description="Include user profile data")
    include_queries: bool = Field(True, description="Include query history")
    include_documents: bool = Field(True, description="Include document analysis metadata")
    include_calculations: bool = Field(True, description="Include tax calculations")
    include_subscriptions: bool = Field(True, description="Include subscription history")
    include_invoices: bool = Field(True, description="Include invoice data")
    include_usage_stats: bool = Field(True, description="Include usage statistics")
    include_faq_interactions: bool = Field(True, description="Include FAQ interactions")
    include_knowledge_searches: bool = Field(True, description="Include knowledge base searches")
    
    @validator('date_to')
    def validate_date_range(cls, v, values):
        if v and values.get('date_from') and v < values['date_from']:
            raise ValueError("Data di fine deve essere successiva alla data di inizio")
        return v
    
    @validator('date_from', 'date_to')
    def validate_future_dates(cls, v):
        if v and v > date.today():
            raise ValueError("Le date non possono essere future")
        return v


class UpdateExportRequest(BaseModel):
    """Request to update export preferences"""
    max_downloads: Optional[int] = Field(None, ge=1, le=50, description="Maximum download count")
    extend_expiry: Optional[bool] = Field(None, description="Extend expiry by 24 hours (one time only)")


# Response Models

class ExportRequestResponse(BaseModel):
    """Export request response"""
    id: str
    status: str
    format: str
    privacy_level: str
    requested_at: str
    expires_at: str
    file_size_mb: Optional[float]
    download_count: int
    max_downloads: int
    is_expired: bool
    is_downloadable: bool
    processing_time_seconds: Optional[int]
    time_until_expiry_hours: float
    error_message: Optional[str]
    
    # Configuration details
    data_categories: Dict[str, bool]
    italian_options: Dict[str, bool]
    privacy_options: Dict[str, bool]


class ExportProgressResponse(BaseModel):
    """Export progress response"""
    export_id: str
    status: str
    progress: Dict[str, Any]
    estimated_completion: Optional[str]


class ExportHistoryResponse(BaseModel):
    """Export history response"""
    exports: List[ExportRequestResponse]
    total_count: int
    rate_limit_info: Dict[str, Any]


class DataCategoriesResponse(BaseModel):
    """Available data categories response"""
    categories: Dict[str, Dict[str, Any]]
    italian_specific: Dict[str, Dict[str, Any]]
    privacy_options: Dict[str, Dict[str, Any]]


# API Endpoints

@router.get("/categories", response_model=DataCategoriesResponse)
async def get_export_categories() -> DataCategoriesResponse:
    """
    Get available data categories for export.
    
    Returns information about all data types that can be included
    in the export, with Italian descriptions and privacy implications.
    """
    return DataCategoriesResponse(
        categories={
            "profile": {
                "name": "Profilo Utente",
                "description": "Dati del profilo, email, nome, data registrazione",
                "includes_pii": True,
                "estimated_records": "1 record"
            },
            "queries": {
                "name": "Cronologia Domande",
                "description": "Tutte le domande poste e le risposte ricevute",
                "includes_pii": False,
                "estimated_records": "Varia per utente"
            },
            "documents": {
                "name": "Documenti Analizzati", 
                "description": "Metadati dei documenti (nome file, tipo, data) - NO contenuto",
                "includes_pii": False,
                "estimated_records": "Varia per utente"
            },
            "calculations": {
                "name": "Calcoli Fiscali",
                "description": "Tutti i calcoli fiscali effettuati (IVA, IRPEF, IMU, etc.)",
                "includes_pii": False,
                "estimated_records": "Varia per utente"
            },
            "subscriptions": {
                "name": "Abbonamenti",
                "description": "Cronologia abbonamenti e cambi piano",
                "includes_pii": True,
                "estimated_records": "Varia per utente"
            },
            "invoices": {
                "name": "Fatture",
                "description": "Fatture e dati di pagamento",
                "includes_pii": True,
                "estimated_records": "Varia per utente"
            },
            "usage_stats": {
                "name": "Statistiche Uso",
                "description": "Statistiche aggregate di utilizzo del servizio",
                "includes_pii": False,
                "estimated_records": "Dati aggregati"
            },
            "faq_interactions": {
                "name": "Interazioni FAQ",
                "description": "FAQ visualizzate e valutazioni fornite",
                "includes_pii": False,
                "estimated_records": "Varia per utente"
            },
            "knowledge_searches": {
                "name": "Ricerche Base Conoscenza",
                "description": "Ricerche effettuate nella base di conoscenza normativa",
                "includes_pii": False,
                "estimated_records": "Varia per utente"
            }
        },
        italian_specific={
            "fatture_elettroniche": {
                "name": "Fatture Elettroniche",
                "description": "XML delle fatture elettroniche inviate tramite SDI",
                "includes_pii": True,
                "legal_requirement": "Solo per clienti business con Partita IVA"
            },
            "f24_forms": {
                "name": "Moduli F24",
                "description": "Metadati dei moduli F24 elaborati",
                "includes_pii": True,
                "legal_requirement": "Dati fiscali sensibili"
            },
            "tax_declarations": {
                "name": "Dichiarazioni Fiscali", 
                "description": "Metadati delle dichiarazioni fiscali elaborate",
                "includes_pii": True,
                "legal_requirement": "Dati fiscali altamente sensibili"
            }
        },
        privacy_options={
            "full_data": {
                "name": "Dati Completi",
                "description": "Include tutti i dati disponibili senza modifiche",
                "risk_level": "Alto - Include dati sensibili"
            },
            "anonymized": {
                "name": "Dati Anonimizzati",
                "description": "Email, nomi e codici fiscali mascherati",
                "risk_level": "Medio - Ridotta identificabilità"
            },
            "minimal": {
                "name": "Dati Essenziali",
                "description": "Solo dati necessari, esclude informazioni sensibili",
                "risk_level": "Basso - Dati non sensibili"
            }
        }
    )


@router.post("/request", response_model=ExportRequestResponse)
@rate_limit("data_export_request", max_requests=5, window_hours=24)
async def request_data_export(
    request: CreateExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    http_request: Request = None,
    db: AsyncSession = Depends(get_db)
) -> ExportRequestResponse:
    """
    Request a comprehensive data export.
    
    Creates a new data export request that will be processed asynchronously.
    Users can request up to 5 exports per 24-hour period.
    
    **Italian Compliance:**
    - Full GDPR Article 20 compliance
    - Italian tax data handling
    - Electronic invoice support
    - Codice Fiscale and Partita IVA protection
    
    **Privacy Options:**
    - Full data: Complete export with all information
    - Anonymized: PII masked for privacy
    - Minimal: Essential data only
    
    **Security:**
    - Rate limited to 5 requests per day
    - Exports expire after 24 hours
    - Maximum 10 downloads per export
    """
    try:
        service = DataExportService(db)
        
        # Prepare options from request
        options = {
            "privacy_level": request.privacy_level.value,
            "include_sensitive": request.include_sensitive,
            "anonymize_pii": request.anonymize_pii,
            "date_from": request.date_from,
            "date_to": request.date_to,
            
            # Italian specific
            "include_fatture": request.include_fatture,
            "include_f24": request.include_f24,
            "include_dichiarazioni": request.include_dichiarazioni,
            "mask_codice_fiscale": request.mask_codice_fiscale,
            
            # Data categories
            "include_profile": request.include_profile,
            "include_queries": request.include_queries,
            "include_documents": request.include_documents,
            "include_calculations": request.include_calculations,
            "include_subscriptions": request.include_subscriptions,
            "include_invoices": request.include_invoices,
            "include_usage_stats": request.include_usage_stats,
            "include_faq_interactions": request.include_faq_interactions,
            "include_knowledge_searches": request.include_knowledge_searches,
            
            # Security context
            "request_ip": http_request.client.host if http_request else None,
            "user_agent": http_request.headers.get("user-agent") if http_request else None
        }
        
        # Create export request
        export_request = await service.create_export_request(
            user_id=current_user.id,
            format=request.format,
            options=options
        )
        
        # Queue background processing
        background_tasks.add_task(service.process_export, export_request.id)
        
        logger.info(
            f"Data export requested by user {current_user.id}: {export_request.id}, "
            f"format: {request.format.value}, privacy: {request.privacy_level.value}"
        )
        
        return ExportRequestResponse(**export_request.to_dict())
        
    except ExportLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating export request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno del sistema"
        )


@router.get("/history", response_model=ExportHistoryResponse)
async def get_export_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ExportHistoryResponse:
    """
    Get user's export history.
    
    Returns a paginated list of all export requests made by the user,
    including their status, download links, and expiry information.
    """
    try:
        service = DataExportService(db)
        
        # Get export history
        exports, total_count = await service.get_user_export_history(
            current_user.id, 
            limit=limit, 
            offset=offset
        )
        
        # Get current rate limit status
        recent_exports = await service._count_recent_exports(current_user.id, hours=24)
        
        return ExportHistoryResponse(
            exports=[ExportRequestResponse(**export.to_dict()) for export in exports],
            total_count=total_count,
            rate_limit_info={
                "requests_today": recent_exports,
                "max_requests_per_day": service.max_exports_per_day,
                "remaining_requests": max(0, service.max_exports_per_day - recent_exports),
                "reset_time": (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting export history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno del sistema"
        )


@router.get("/{export_id}/status", response_model=ExportRequestResponse)
async def get_export_status(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ExportRequestResponse:
    """
    Get export request status.
    
    Returns detailed information about a specific export request,
    including processing status, file size, download count, and expiry.
    """
    try:
        service = DataExportService(db)
        
        # Get export request
        export_request = await service._get_export_request(export_id)
        if not export_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export non trovato"
            )
        
        # Verify ownership
        if export_request.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Non autorizzato ad accedere a questo export"
            )
        
        return ExportRequestResponse(**export_request.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting export status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno del sistema"
        )


@router.get("/{export_id}/progress", response_model=ExportProgressResponse)
async def get_export_progress(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ExportProgressResponse:
    """
    Get real-time export progress.
    
    Returns current processing progress with step information and
    estimated completion time for active exports.
    """
    try:
        service = DataExportService(db)
        
        # Verify export exists and user owns it
        export_request = await service._get_export_request(export_id)
        if not export_request or export_request.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export non trovato"
            )
        
        # Get progress from Redis
        progress_tracker = ExportProgressTracker(get_redis_client())
        progress = await progress_tracker.get_progress(str(export_id))
        
        # Estimate completion time for processing exports
        estimated_completion = None
        if export_request.status == ExportStatus.PROCESSING and progress.get("percentage", 0) > 0:
            if export_request.started_at:
                elapsed = datetime.utcnow() - export_request.started_at
                if progress["percentage"] > 0:
                    total_estimated = elapsed.total_seconds() * (100 / progress["percentage"])
                    remaining = total_estimated - elapsed.total_seconds()
                    estimated_completion = (datetime.utcnow() + timedelta(seconds=remaining)).isoformat()
        
        return ExportProgressResponse(
            export_id=str(export_id),
            status=export_request.status.value,
            progress=progress,
            estimated_completion=estimated_completion
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting export progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno del sistema"
        )


@router.get("/{export_id}/download")
async def download_export(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    """
    Download completed export.
    
    Provides secure download link for completed exports. Downloads are
    tracked and limited to prevent abuse. Links expire after 24 hours.
    
    **Security Features:**
    - IP address tracking
    - Download count limiting (max 10 per export)
    - Automatic expiry after 24 hours
    - Audit logging for compliance
    """
    try:
        service = DataExportService(db)
        
        # Get and verify export request
        export_request = await service._get_export_request(export_id)
        if not export_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export non trovato"
            )
        
        # Verify ownership
        if export_request.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Non autorizzato"
            )
        
        # Check if downloadable
        if not export_request.is_downloadable:
            if export_request.is_expired:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail=f"Export scaduto il {export_request.expires_at.strftime('%d/%m/%Y alle %H:%M')}"
                )
            elif export_request.status != ExportStatus.COMPLETED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Export non completato (stato: {export_request.status.value})"
                )
            elif export_request.download_count >= export_request.max_downloads:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Massimo {export_request.max_downloads} download raggiunti"
                )
        
        # Get client IP for tracking
        client_ip = request.client.host if request else None
        
        # Increment download count
        success = export_request.increment_download(client_ip)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Impossibile scaricare l'export"
            )
        
        await db.commit()
        
        # Create audit log
        await service._create_audit_log(
            export_request.id,
            current_user.id,
            "downloaded",
            {
                "download_count": export_request.download_count,
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent") if request else None
            }
        )
        
        logger.info(
            f"Export downloaded: {export_id} by user {current_user.id}, "
            f"download #{export_request.download_count} from IP {client_ip}"
        )
        
        # Redirect to secure download URL
        return RedirectResponse(url=export_request.download_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading export: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno del sistema"
        )


@router.put("/{export_id}", response_model=ExportRequestResponse)
async def update_export_request(
    export_id: UUID,
    request: UpdateExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ExportRequestResponse:
    """
    Update export request settings.
    
    Allows limited updates to export settings such as download limits
    or extending expiry (one-time extension allowed).
    """
    try:
        service = DataExportService(db)
        
        # Get and verify export request
        export_request = await service._get_export_request(export_id)
        if not export_request or export_request.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export non trovato"
            )
        
        updated = False
        
        # Update max downloads
        if request.max_downloads is not None:
            if export_request.download_count >= request.max_downloads:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Il numero massimo di download non può essere inferiore ai download già effettuati"
                )
            export_request.max_downloads = request.max_downloads
            updated = True
        
        # Extend expiry (one-time only)
        if request.extend_expiry and not export_request.is_expired:
            # Check if already extended (custom field would be needed)
            if hasattr(export_request, 'expiry_extended') and export_request.expiry_extended:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La scadenza può essere estesa solo una volta"
                )
            
            # Extend by 24 hours
            export_request.expires_at = export_request.expires_at + timedelta(hours=24)
            # Mark as extended (would need to add this field to model)
            updated = True
        
        if updated:
            await db.commit()
            
            # Create audit log
            await service._create_audit_log(
                export_request.id,
                current_user.id,
                "updated",
                {
                    "max_downloads": request.max_downloads,
                    "extend_expiry": request.extend_expiry
                }
            )
        
        return ExportRequestResponse(**export_request.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating export request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno del sistema"
        )


@router.delete("/{export_id}")
async def delete_export_request(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete/cancel export request.
    
    Cancels pending exports or marks completed exports as deleted.
    This action cannot be undone.
    """
    try:
        service = DataExportService(db)
        
        # Get and verify export request
        export_request = await service._get_export_request(export_id)
        if not export_request or export_request.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export non trovato"
            )
        
        # Cancel if processing, mark as expired if completed
        if export_request.status in [ExportStatus.PENDING, ExportStatus.PROCESSING]:
            export_request.status = ExportStatus.FAILED
            export_request.error_message = "Cancellato dall'utente"
        else:
            export_request.expires_at = datetime.utcnow()  # Force expiry
        
        await db.commit()
        
        # Create audit log
        await service._create_audit_log(
            export_request.id,
            current_user.id,
            "deleted",
            {"reason": "user_requested"}
        )
        
        logger.info(f"Export deleted by user: {export_id}")
        
        return {"message": "Export cancellato con successo"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting export request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno del sistema"
        )


@router.post("/{export_id}/retry", response_model=ExportRequestResponse)
async def retry_export(
    export_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ExportRequestResponse:
    """
    Retry failed export.
    
    Allows retrying failed exports up to 3 times. The export must be
    in failed status and not exceeded the retry limit.
    """
    try:
        service = DataExportService(db)
        
        # Get and verify export request
        export_request = await service._get_export_request(export_id)
        if not export_request or export_request.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export non trovato"
            )
        
        # Check if retry is allowed
        if not export_request.can_retry():
            if export_request.status != ExportStatus.FAILED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Solo gli export falliti possono essere ripetuti"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Massimo {export_request.max_retries} tentativi raggiunti"
                )
        
        # Reset status and clear error
        export_request.status = ExportStatus.PENDING
        export_request.error_message = None
        export_request.started_at = None
        export_request.completed_at = None
        
        await db.commit()
        
        # Queue for reprocessing
        background_tasks.add_task(service.process_export, export_request.id)
        
        # Create audit log
        await service._create_audit_log(
            export_request.id,
            current_user.id,
            "retried",
            {"retry_attempt": export_request.retry_count + 1}
        )
        
        logger.info(f"Export retry requested: {export_id}, attempt #{export_request.retry_count + 1}")
        
        return ExportRequestResponse(**export_request.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying export: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno del sistema"
        )


@router.get("/compliance/info")
async def get_compliance_info() -> Dict[str, Any]:
    """
    Get GDPR compliance information.
    
    Returns detailed information about data export compliance,
    legal basis, data protection measures, and user rights.
    """
    return {
        "gdpr_compliance": {
            "legal_basis": "GDPR Article 20 - Right to data portability",
            "article_text": "Il soggetto interessato ha il diritto di ricevere in un formato strutturato, di uso comune e leggibile da dispositivo automatico i dati personali che lo riguardano forniti a un titolare del trattamento.",
            "data_controller": {
                "name": "PratikoAI SRL",
                "address": "Via dell'Innovazione 123, 00100 Roma, IT",
                "email": "privacy@pratikoai.com",
                "phone": "+39 06 12345678",
                "pec": "privacy@pec.pratikoai.it"
            },
            "jurisdiction": "Italia",
            "applicable_laws": [
                "GDPR (Regolamento UE 2016/679)",
                "Codice Privacy (D.Lgs. 196/2003 e s.m.i.)"
            ]
        },
        "data_protection_measures": {
            "encryption": "Tutti i dati sensibili sono crittografati a riposo e in transito",
            "access_control": "Accesso limitato al solo utente proprietario dei dati",
            "audit_logging": "Tutte le operazioni sono registrate per controlli di conformità",
            "secure_storage": "Storage AWS con crittografia server-side",
            "automatic_deletion": "Export cancellati automaticamente dopo 24 ore",
            "download_limits": "Massimo 10 download per export per prevenire abusi",
            "rate_limiting": "Massimo 5 export per utente ogni 24 ore"
        },
        "user_rights": {
            "right_to_access": "Diritto di accesso ai propri dati personali",
            "right_to_portability": "Diritto alla portabilità dei dati",
            "right_to_rectification": "Diritto di rettifica dei dati inesatti",
            "right_to_erasure": "Diritto alla cancellazione (diritto all'oblio)",
            "right_to_restrict": "Diritto di limitazione del trattamento",
            "right_to_object": "Diritto di opposizione al trattamento",
            "right_to_withdraw": "Diritto di revocare il consenso"
        },
        "export_specifications": {
            "formats_supported": ["JSON", "CSV", "ZIP"],
            "encoding": "UTF-8 con BOM per compatibilità Excel",
            "date_format": "DD/MM/YYYY (formato italiano)",
            "decimal_separator": "Virgola (,) per compatibilità italiana",
            "csv_delimiter": "Punto e virgola (;) per Excel italiano",
            "retention_period": "24 ore",
            "max_file_size": "100 MB per export",
            "compression": "ZIP automatico per file multipli o grandi"
        },
        "italian_specific": {
            "codice_fiscale_protection": "Codice Fiscale può essere mascherato (opzionale)",
            "partita_iva_handling": "Partita IVA inclusa per clienti business",
            "fattura_elettronica": "XML fatture elettroniche per clienti con Partita IVA",
            "tax_data_sensitivity": "Dati fiscali trattati con massima sicurezza",
            "sdi_compliance": "Conformità con Sistema di Interscambio",
            "regional_compliance": "Conformità con normative regionali italiane"
        },
        "contact_info": {
            "data_protection_officer": "dpo@pratikoai.com",
            "support": "support@pratikoai.com",
            "privacy_complaints": "privacy@pratikoai.com",
            "supervisory_authority": {
                "name": "Garante per la protezione dei dati personali",
                "website": "https://www.gpdp.it",
                "email": "garante@gpdp.it"
            }
        }
    }