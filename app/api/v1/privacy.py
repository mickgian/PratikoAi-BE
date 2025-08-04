"""Privacy and GDPR compliance API endpoints.

This module provides endpoints for privacy management, consent handling,
and GDPR data subject rights.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.privacy.anonymizer import anonymizer
from app.core.privacy.gdpr import gdpr_compliance
from app.models.session import Session
from app.schemas.privacy import (
    PIIDetectionRequest,
    AnonymizationResponse,
    ConsentRequest,
    ConsentResponse,
    ConsentStatusRequest,
    ConsentStatusResponse,
    DataSubjectRequest,
    DataSubjectResponse,
    ComplianceStatusResponse,
    PIIMatchResponse,
)

router = APIRouter()


@router.post("/anonymize", response_model=AnonymizationResponse)
@limiter.limit("20 per minute")
async def anonymize_text(
    request: Request,
    anonymization_request: PIIDetectionRequest,
    session: Session = Depends(get_current_session),
):
    """Anonymize PII in text.
    
    Args:
        request: FastAPI request object
        anonymization_request: Text anonymization request
        session: Current user session
        
    Returns:
        AnonymizationResponse: Anonymized text with PII matches
    """
    try:
        logger.info(
            "anonymization_request_received",
            session_id=session.id,
            text_length=len(anonymization_request.text),
            detect_names=anonymization_request.detect_names
        )
        
        # Anonymize the text
        result = anonymizer.anonymize_text(anonymization_request.text)
        
        # Convert PII matches to response format
        pii_matches = [
            PIIMatchResponse(
                pii_type=match.pii_type.value,
                original_value=match.original_value,
                anonymized_value=match.anonymized_value,
                start_pos=match.start_pos,
                end_pos=match.end_pos,
                confidence=match.confidence
            )
            for match in result.pii_matches
            if match.confidence >= anonymization_request.confidence_threshold
        ]
        
        logger.info(
            "anonymization_completed",
            session_id=session.id,
            pii_matches_found=len(pii_matches),
            original_length=len(anonymization_request.text),
            anonymized_length=len(result.anonymized_text)
        )
        
        return AnonymizationResponse(
            anonymized_text=result.anonymized_text,
            pii_matches=pii_matches,
            anonymization_map=result.anonymization_map,
            timestamp=result.timestamp
        )
        
    except Exception as e:
        logger.error(
            "anonymization_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Anonymization failed")


@router.post("/consent", response_model=ConsentResponse)
@limiter.limit("10 per minute")
async def manage_consent(
    request: Request,
    consent_request: ConsentRequest,
    session: Session = Depends(get_current_session),
):
    """Grant or withdraw consent for data processing.
    
    Args:
        request: FastAPI request object
        consent_request: Consent management request
        session: Current user session
        
    Returns:
        ConsentResponse: Consent operation result
    """
    try:
        # Verify user can only manage their own consent
        if consent_request.user_id != session.user_id:
            raise HTTPException(status_code=403, detail="Cannot manage consent for other users")
        
        logger.info(
            "consent_request_received",
            session_id=session.id,
            user_id=consent_request.user_id,
            consent_type=consent_request.consent_type,
            granted=consent_request.granted
        )
        
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        if consent_request.granted:
            # Grant consent
            consent_id = gdpr_compliance.consent_manager.grant_consent(
                user_id=consent_request.user_id,
                consent_type=consent_request.consent_type,
                ip_address=client_ip,
                user_agent=user_agent,
                expiry_days=consent_request.expiry_days
            )
            
            # Get the granted consent details
            consent_history = gdpr_compliance.consent_manager.get_consent_history(consent_request.user_id)
            consent_record = next(
                (c for c in consent_history if c.consent_id == consent_id),
                None
            )
            
            if not consent_record:
                raise HTTPException(status_code=500, detail="Failed to retrieve consent record")
            
            return ConsentResponse(
                consent_id=consent_id,
                user_id=consent_request.user_id,
                consent_type=consent_request.consent_type,
                granted=True,
                timestamp=consent_record.timestamp,
                expiry_date=consent_record.expiry_date
            )
            
        else:
            # Withdraw consent
            success = gdpr_compliance.consent_manager.withdraw_consent(
                user_id=consent_request.user_id,
                consent_type=consent_request.consent_type,
                ip_address=client_ip
            )
            
            if not success:
                raise HTTPException(status_code=404, detail="No active consent found to withdraw")
            
            return ConsentResponse(
                consent_id="withdrawn",
                user_id=consent_request.user_id,
                consent_type=consent_request.consent_type,
                granted=False,
                timestamp=datetime.utcnow()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "consent_management_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Consent management failed")


@router.get("/consent/status", response_model=ConsentStatusResponse)
@limiter.limit("30 per minute")
async def get_consent_status(
    request: Request,
    user_id: str,
    session: Session = Depends(get_current_session),
):
    """Get current consent status for a user.
    
    Args:
        request: FastAPI request object
        user_id: User identifier
        session: Current user session
        
    Returns:
        ConsentStatusResponse: Current consent status
    """
    try:
        # Verify user can only check their own consent
        if user_id != session.user_id:
            raise HTTPException(status_code=403, detail="Cannot check consent for other users")
        
        logger.info(
            "consent_status_request",
            session_id=session.id,
            user_id=user_id
        )
        
        # Import consent types
        from app.core.privacy.gdpr import ConsentType
        
        # Check all consent types
        consents = {}
        last_updated = None
        
        for consent_type in ConsentType:
            has_consent = gdpr_compliance.consent_manager.has_valid_consent(user_id, consent_type)
            consents[consent_type.value] = has_consent
        
        # Get last update timestamp from consent history
        consent_history = gdpr_compliance.consent_manager.get_consent_history(user_id)
        if consent_history:
            last_updated = max(c.timestamp for c in consent_history)
        
        return ConsentStatusResponse(
            user_id=user_id,
            consents=consents,
            last_updated=last_updated
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "consent_status_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve consent status")


@router.post("/data-subject-request", response_model=DataSubjectResponse)
@limiter.limit("5 per hour")
async def handle_data_subject_request(
    request: Request,
    data_request: DataSubjectRequest,
    session: Session = Depends(get_current_session),
):
    """Handle GDPR data subject requests (access, deletion, portability).
    
    Args:
        request: FastAPI request object
        data_request: Data subject request
        session: Current user session
        
    Returns:
        DataSubjectResponse: Request handling result
    """
    try:
        # Verify user can only request for themselves
        if data_request.user_id != session.user_id:
            raise HTTPException(status_code=403, detail="Cannot request data for other users")
        
        logger.info(
            "data_subject_request_received",
            session_id=session.id,
            user_id=data_request.user_id,
            request_type=data_request.request_type
        )
        
        client_ip = request.client.host if request.client else None
        
        # Handle the request through GDPR compliance system
        result = gdpr_compliance.handle_data_subject_request(
            user_id=data_request.user_id,
            request_type=data_request.request_type,
            ip_address=client_ip,
            session_id=session.id
        )
        
        return DataSubjectResponse(
            request_id=str(uuid.uuid4()),
            user_id=data_request.user_id,
            request_type=data_request.request_type,
            status="processed",
            data=result,
            message=result.get("message")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "data_subject_request_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Data subject request failed")


@router.get("/compliance/status", response_model=ComplianceStatusResponse)
@limiter.limit("10 per minute")
async def get_compliance_status(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get overall GDPR compliance status (admin only).
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        ComplianceStatusResponse: Compliance status information
    """
    try:
        # In a real implementation, you'd check for admin privileges
        # For now, any authenticated user can check compliance status
        
        logger.info(
            "compliance_status_request",
            session_id=session.id,
            user_id=session.user_id
        )
        
        status = gdpr_compliance.get_compliance_status()
        
        return ComplianceStatusResponse(
            consent_records_count=status["consent_records_count"],
            processing_records_count=status["processing_records_count"],
            audit_events_count=status["audit_events_count"],
            retention_policies=status["retention_policies"],
            compliance_features=status["compliance_features"]
        )
        
    except Exception as e:
        logger.error(
            "compliance_status_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance status")


@router.post("/cleanup")
@limiter.limit("1 per hour")
async def trigger_cleanup(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Trigger cleanup of expired consents and data (admin only).
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        JSONResponse: Cleanup results
    """
    try:
        # In a real implementation, you'd check for admin privileges
        logger.info(
            "cleanup_triggered",
            session_id=session.id,
            user_id=session.user_id
        )
        
        cleanup_result = gdpr_compliance.periodic_cleanup()
        
        return JSONResponse({
            "status": "cleanup_completed",
            "results": cleanup_result
        })
        
    except Exception as e:
        logger.error(
            "cleanup_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Cleanup failed")