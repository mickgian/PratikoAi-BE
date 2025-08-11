"""
GDPR Data Deletion API Endpoints for PratikoAI.

This module provides API endpoints for GDPR Article 17 "Right to be forgotten" compliance,
including user-initiated and admin-initiated deletion requests, status tracking,
and compliance reporting.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator

from app.core.database import get_async_db
from app.core.auth import get_current_user, get_current_admin_user
from app.models.encrypted_user import EncryptedUser
from app.services.gdpr_deletion_service import (
    GDPRDeletionService,
    DeletionRequest,
    DeletionResult,
    ComplianceReport,
    DeletionMetrics,
    DeletionStatus,
    DeletionPriority
)
from app.services.user_data_deletor import UserDataDeletor
from app.services.deletion_verifier import DeletionVerifier, VerificationResult
from app.core.logging import logger

# Initialize router
router = APIRouter(prefix="/gdpr", tags=["GDPR Data Deletion"])
security = HTTPBearer()


# Pydantic models for API requests/responses

class CreateDeletionRequestModel(BaseModel):
    """Request model for creating GDPR deletion request."""
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for deletion request")
    priority: Optional[DeletionPriority] = Field(
        default=DeletionPriority.NORMAL,
        description="Request priority level"
    )
    
    @validator('reason')
    def validate_reason(cls, v):
        if not v.strip():
            raise ValueError("Reason cannot be empty")
        return v.strip()


class AdminCreateDeletionRequestModel(CreateDeletionRequestModel):
    """Request model for admin-initiated deletion request."""
    user_id: int = Field(..., gt=0, description="ID of user to delete")
    priority: DeletionPriority = Field(
        default=DeletionPriority.LOW,
        description="Request priority level"
    )


class DeletionRequestResponse(BaseModel):
    """Response model for deletion request."""
    request_id: str
    user_id: int
    status: DeletionStatus
    initiated_by_user: bool
    admin_user_id: Optional[int]
    reason: str
    priority: DeletionPriority
    request_timestamp: datetime
    deletion_deadline: datetime
    scheduled_execution: Optional[datetime]
    completed_at: Optional[datetime]
    deletion_certificate_id: Optional[str]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class DeletionResultResponse(BaseModel):
    """Response model for deletion result."""
    request_id: str
    user_id: int
    success: bool
    total_records_deleted: int
    tables_affected: List[str]
    systems_processed: List[str]
    audit_records_preserved: int
    deletion_certificate_id: Optional[str]
    processing_time_seconds: float
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class VerificationResultResponse(BaseModel):
    """Response model for deletion verification."""
    user_id: int
    is_completely_deleted: bool
    remaining_data_found: List[Dict[str, Any]]
    verification_score: float
    gdpr_compliant: bool
    verification_timestamp: datetime
    systems_verified: List[str]
    
    class Config:
        from_attributes = True


class ComplianceReportResponse(BaseModel):
    """Response model for compliance report."""
    report_id: str
    report_period_days: int
    total_deletion_requests: int
    user_initiated_requests: int
    admin_initiated_requests: int
    completed_deletions: int
    failed_deletions: int
    pending_deletions: int
    overdue_deletions: int
    average_completion_time_hours: float
    compliance_score: float
    generated_at: datetime
    
    class Config:
        from_attributes = True


class DeletionMetricsResponse(BaseModel):
    """Response model for deletion metrics."""
    total_requests: int
    completed_deletions: int
    pending_deletions: int
    overdue_deletions: int
    average_processing_time_hours: float
    compliance_rate: float
    last_updated: datetime
    
    class Config:
        from_attributes = True


# User-facing endpoints

@router.post(
    "/deletion-request",
    response_model=DeletionRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user deletion request",
    description="Create a GDPR Article 17 deletion request for the current user"
)
async def create_user_deletion_request(
    request_data: CreateDeletionRequestModel,
    current_user: EncryptedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Create a GDPR deletion request for the current user.
    
    This endpoint allows users to exercise their "Right to be forgotten" under
    GDPR Article 17. The deletion will be executed within 30 days as required by law.
    """
    try:
        gdpr_service = GDPRDeletionService(db)
        await gdpr_service.initialize()
        
        deletion_request = await gdpr_service.create_deletion_request(
            user_id=current_user.id,
            initiated_by_user=True,
            reason=request_data.reason,
            priority=request_data.priority
        )
        
        logger.info(f"User {current_user.id} created deletion request {deletion_request.request_id}")
        
        return DeletionRequestResponse(**deletion_request.__dict__)
        
    except ValueError as e:
        logger.warning(f"Invalid deletion request from user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create deletion request for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create deletion request"
        )


@router.get(
    "/deletion-request/status",
    response_model=Optional[DeletionRequestResponse],
    summary="Get user deletion request status",
    description="Get the status of the current user's deletion request"
)
async def get_user_deletion_status(
    current_user: EncryptedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get the status of the current user's deletion request."""
    try:
        from sqlalchemy import select
        from app.services.gdpr_deletion_service import GDPRDeletionRequest
        
        # Find user's deletion request
        result = await db.execute(
            select(GDPRDeletionRequest).where(
                GDPRDeletionRequest.user_id == current_user.id
            ).order_by(GDPRDeletionRequest.created_at.desc())
        )
        
        db_request = result.scalars().first()
        
        if not db_request:
            return None
        
        deletion_request = DeletionRequest(
            request_id=db_request.request_id,
            user_id=db_request.user_id,
            status=DeletionStatus(db_request.status),
            initiated_by_user=db_request.initiated_by_user,
            admin_user_id=db_request.admin_user_id,
            reason=db_request.reason,
            priority=DeletionPriority(db_request.priority),
            request_timestamp=db_request.request_timestamp,
            deletion_deadline=db_request.deletion_deadline,
            scheduled_execution=db_request.scheduled_execution,
            completed_at=db_request.completed_at,
            deletion_certificate_id=db_request.deletion_certificate_id,
            error_message=db_request.error_message
        )
        
        return DeletionRequestResponse(**deletion_request.__dict__)
        
    except Exception as e:
        logger.error(f"Failed to get deletion status for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get deletion status"
        )


@router.get(
    "/deletion-certificate/{certificate_id}",
    summary="Get deletion certificate",
    description="Download GDPR deletion certificate"
)
async def get_deletion_certificate(
    certificate_id: str = Path(..., description="Certificate ID"),
    current_user: EncryptedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get GDPR deletion certificate."""
    try:
        from sqlalchemy import select
        from app.services.gdpr_deletion_service import GDPRDeletionCertificate
        
        # Find certificate
        result = await db.execute(
            select(GDPRDeletionCertificate).where(
                GDPRDeletionCertificate.certificate_id == certificate_id,
                GDPRDeletionCertificate.user_id == current_user.id
            )
        )
        
        certificate = result.scalars().first()
        
        if not certificate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificate not found"
            )
        
        return {
            "certificate_id": certificate.certificate_id,
            "user_id": certificate.user_id,
            "is_complete_deletion": certificate.is_complete_deletion,
            "compliance_attestation": certificate.compliance_attestation,
            "certificate_text": certificate.certificate_text,
            "issued_at": certificate.issued_at,
            "issued_by": certificate.issued_by
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get certificate {certificate_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get certificate"
        )


# Admin endpoints

@router.post(
    "/admin/deletion-request",
    response_model=DeletionRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create admin deletion request",
    description="Create a GDPR deletion request for any user (admin only)"
)
async def create_admin_deletion_request(
    request_data: AdminCreateDeletionRequestModel,
    current_admin: EncryptedUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a GDPR deletion request for any user (admin only)."""
    try:
        gdpr_service = GDPRDeletionService(db)
        await gdpr_service.initialize()
        
        deletion_request = await gdpr_service.create_deletion_request(
            user_id=request_data.user_id,
            initiated_by_user=False,
            reason=request_data.reason,
            admin_user_id=current_admin.id,
            priority=request_data.priority
        )
        
        logger.info(
            f"Admin {current_admin.id} created deletion request {deletion_request.request_id} "
            f"for user {request_data.user_id}"
        )
        
        return DeletionRequestResponse(**deletion_request.__dict__)
        
    except ValueError as e:
        logger.warning(f"Invalid admin deletion request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create admin deletion request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create deletion request"
        )


@router.get(
    "/admin/deletion-requests",
    response_model=List[DeletionRequestResponse],
    summary="List all deletion requests",
    description="Get all GDPR deletion requests with optional filtering (admin only)"
)
async def list_deletion_requests(
    status_filter: Optional[DeletionStatus] = Query(None, description="Filter by status"),
    priority_filter: Optional[DeletionPriority] = Query(None, description="Filter by priority"),
    user_initiated_only: Optional[bool] = Query(None, description="Filter user-initiated requests"),
    overdue_only: Optional[bool] = Query(False, description="Show only overdue requests"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_admin: EncryptedUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List all GDPR deletion requests with filtering options (admin only)."""
    try:
        from sqlalchemy import select, and_
        from app.services.gdpr_deletion_service import GDPRDeletionRequest
        
        # Build query with filters
        query = select(GDPRDeletionRequest)
        conditions = []
        
        if status_filter:
            conditions.append(GDPRDeletionRequest.status == status_filter.value)
        
        if priority_filter:
            conditions.append(GDPRDeletionRequest.priority == priority_filter.value)
        
        if user_initiated_only is not None:
            conditions.append(GDPRDeletionRequest.initiated_by_user == user_initiated_only)
        
        if overdue_only:
            conditions.append(
                and_(
                    GDPRDeletionRequest.deletion_deadline <= datetime.now(timezone.utc),
                    GDPRDeletionRequest.status == DeletionStatus.PENDING.value
                )
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(GDPRDeletionRequest.created_at.desc()).offset(offset).limit(limit)
        
        result = await db.execute(query)
        db_requests = result.scalars().all()
        
        # Convert to response models
        deletion_requests = []
        for db_request in db_requests:
            deletion_request = DeletionRequest(
                request_id=db_request.request_id,
                user_id=db_request.user_id,
                status=DeletionStatus(db_request.status),
                initiated_by_user=db_request.initiated_by_user,
                admin_user_id=db_request.admin_user_id,
                reason=db_request.reason,
                priority=DeletionPriority(db_request.priority),
                request_timestamp=db_request.request_timestamp,
                deletion_deadline=db_request.deletion_deadline,
                scheduled_execution=db_request.scheduled_execution,
                completed_at=db_request.completed_at,
                deletion_certificate_id=db_request.deletion_certificate_id,
                error_message=db_request.error_message
            )
            deletion_requests.append(DeletionRequestResponse(**deletion_request.__dict__))
        
        return deletion_requests
        
    except Exception as e:
        logger.error(f"Failed to list deletion requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list deletion requests"
        )


@router.post(
    "/admin/execute-overdue",
    response_model=List[DeletionResultResponse],
    summary="Execute overdue deletions",
    description="Execute all overdue GDPR deletion requests (admin only)"
)
async def execute_overdue_deletions(
    current_admin: EncryptedUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Execute all overdue GDPR deletion requests (admin only)."""
    try:
        gdpr_service = GDPRDeletionService(db)
        await gdpr_service.initialize()
        
        deletion_results = await gdpr_service.execute_overdue_deletions()
        
        logger.info(f"Admin {current_admin.id} executed {len(deletion_results)} overdue deletions")
        
        response_results = []
        for result in deletion_results:
            response_results.append(DeletionResultResponse(**result.__dict__))
        
        return response_results
        
    except Exception as e:
        logger.error(f"Failed to execute overdue deletions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute overdue deletions"
        )


@router.post(
    "/admin/verify-deletion/{user_id}",
    response_model=VerificationResultResponse,
    summary="Verify user deletion",
    description="Verify that user data has been completely deleted (admin only)"
)
async def verify_user_deletion(
    user_id: int = Path(..., gt=0, description="User ID to verify"),
    current_admin: EncryptedUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Verify that user data has been completely deleted (admin only)."""
    try:
        verifier = DeletionVerifier(db)
        verification_result = await verifier.verify_user_deletion(user_id)
        
        logger.info(
            f"Admin {current_admin.id} verified deletion for user {user_id}: "
            f"complete={verification_result.is_completely_deleted}"
        )
        
        return VerificationResultResponse(**verification_result.__dict__)
        
    except Exception as e:
        logger.error(f"Failed to verify deletion for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify deletion"
        )


@router.get(
    "/admin/compliance-report",
    response_model=ComplianceReportResponse,
    summary="Generate compliance report",
    description="Generate GDPR deletion compliance report (admin only)"
)
async def generate_compliance_report(
    days: int = Query(30, ge=1, le=365, description="Report period in days"),
    current_admin: EncryptedUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Generate GDPR deletion compliance report (admin only)."""
    try:
        gdpr_service = GDPRDeletionService(db)
        await gdpr_service.initialize()
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        compliance_report = await gdpr_service.generate_compliance_report(start_date, end_date)
        
        logger.info(f"Admin {current_admin.id} generated {days}-day compliance report")
        
        return ComplianceReportResponse(**compliance_report.__dict__)
        
    except Exception as e:
        logger.error(f"Failed to generate compliance report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate compliance report"
        )


@router.get(
    "/admin/metrics",
    response_model=DeletionMetricsResponse,
    summary="Get deletion metrics",
    description="Get current GDPR deletion metrics (admin only)"
)
async def get_deletion_metrics(
    current_admin: EncryptedUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get current GDPR deletion metrics (admin only)."""
    try:
        gdpr_service = GDPRDeletionService(db)
        await gdpr_service.initialize()
        
        metrics = await gdpr_service.get_deletion_metrics()
        
        return DeletionMetricsResponse(**metrics.__dict__)
        
    except Exception as e:
        logger.error(f"Failed to get deletion metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get deletion metrics"
        )


@router.get(
    "/admin/deadline-compliance",
    summary="Check deadline compliance",
    description="Check compliance with 30-day deletion deadlines (admin only)"
)
async def check_deadline_compliance(
    current_admin: EncryptedUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Check compliance with 30-day deletion deadlines (admin only)."""
    try:
        gdpr_service = GDPRDeletionService(db)
        await gdpr_service.initialize()
        
        compliance_status = await gdpr_service.check_deadline_compliance()
        
        return compliance_status
        
    except Exception as e:
        logger.error(f"Failed to check deadline compliance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check deadline compliance"
        )


# System endpoints for scheduled jobs

@router.post(
    "/system/execute-scheduled-deletions",
    response_model=List[DeletionResultResponse],
    summary="Execute scheduled deletions",
    description="Execute scheduled GDPR deletions (system endpoint)"
)
async def execute_scheduled_deletions(
    db: AsyncSession = Depends(get_async_db)
):
    """
    Execute scheduled GDPR deletions (system endpoint).
    
    This endpoint is intended to be called by scheduled jobs/cron tasks
    to automatically process overdue deletion requests.
    """
    try:
        gdpr_service = GDPRDeletionService(db)
        await gdpr_service.initialize()
        
        deletion_results = await gdpr_service.execute_overdue_deletions()
        
        logger.info(f"System job executed {len(deletion_results)} scheduled deletions")
        
        response_results = []
        for result in deletion_results:
            response_results.append(DeletionResultResponse(**result.__dict__))
        
        return response_results
        
    except Exception as e:
        logger.error(f"Failed to execute scheduled deletions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute scheduled deletions"
        )


# Health check endpoint

@router.get(
    "/health",
    summary="GDPR service health check",
    description="Check health of GDPR deletion service"
)
async def gdpr_service_health(
    db: AsyncSession = Depends(get_async_db)
):
    """Check health of GDPR deletion service."""
    try:
        gdpr_service = GDPRDeletionService(db)
        await gdpr_service.initialize()
        
        # Basic health checks
        metrics = await gdpr_service.get_deletion_metrics()
        compliance_status = await gdpr_service.check_deadline_compliance()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service_initialized": True,
            "total_requests": metrics.total_requests,
            "compliance_rate": compliance_status["compliance_rate"],
            "overdue_requests": compliance_status["overdue_requests"]
        }
        
    except Exception as e:
        logger.error(f"GDPR service health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }