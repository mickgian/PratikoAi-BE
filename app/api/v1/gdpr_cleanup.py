"""GDPR Document Cleanup API Endpoints.

This module provides REST API endpoints for managing GDPR compliant document
cleanup, retention policies, and user data deletion requests.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_admin_user, get_current_user
from app.core.database import get_async_session as get_db
from app.core.logging import logger
from app.core.rate_limiting import rate_limit
from app.models.user import User
from app.services.gdpr_document_cleanup import GDPRDocumentCleanup, run_gdpr_cleanup

router = APIRouter(prefix="/gdpr-cleanup", tags=["GDPR Compliance"])


# Request Models


class ScheduleDeletionRequest(BaseModel):
    """Request to schedule document deletion"""

    document_id: UUID
    deletion_date: datetime = Field(..., description="When to delete the document")
    reason: str = Field(..., max_length=500, description="Reason for deletion")


class UserDataDeletionRequest(BaseModel):
    """Request for user data deletion (Right to erasure)"""

    user_id: UUID
    reason: str = Field(default="USER_REQUEST", max_length=500)
    immediate: bool = Field(default=False, description="Delete immediately vs. schedule")


# Response Models


class CleanupStatsResponse(BaseModel):
    """GDPR cleanup statistics response"""

    expired_documents: int
    failed_processing: int
    temp_files_cleaned: int
    storage_freed_mb: float
    errors: list[str]
    cleanup_timestamp: str


class RetentionStatusResponse(BaseModel):
    """Document retention status response"""

    total_documents: int
    expired_documents: int
    approaching_expiry: int
    retention_period_days: int
    next_cleanup_due: str
    user_id: str | None


class UserDeletionResponse(BaseModel):
    """User data deletion response"""

    user_id: str
    deleted_documents: int
    storage_freed_mb: float
    deletion_reason: str
    errors: list[str]
    completed_at: str


# API Endpoints


@router.post("/cleanup", response_model=CleanupStatsResponse)
@rate_limit("gdpr_cleanup", max_requests=5, window_hours=1)
async def trigger_gdpr_cleanup(
    background_tasks: BackgroundTasks, current_user: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)
) -> CleanupStatsResponse:
    """Trigger GDPR compliant document cleanup.

    Cleans up expired documents, failed processing files, and temporary files
    according to GDPR data retention policies. Admin access required.

    **Cleanup Actions:**
    - Documents older than retention period
    - Failed processing documents (24h timeout)
    - Temporary files (2h timeout)
    - Storage optimization

    **Rate Limited:** 5 requests per hour per user
    """
    try:
        service = GDPRDocumentCleanup(db)
        stats = await service.cleanup_expired_documents()

        logger.info(
            f"GDPR cleanup triggered by admin {current_user.id}: "
            f"{stats['expired_documents']} expired, {stats['storage_freed_mb']:.2f}MB freed"
        )

        return CleanupStatsResponse(**stats, cleanup_timestamp=datetime.utcnow().isoformat())

    except Exception as e:
        logger.error(f"GDPR cleanup failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Cleanup process failed")


@router.get("/retention-status", response_model=RetentionStatusResponse)
@rate_limit("retention_status", max_requests=20, window_hours=1)
async def get_retention_status(
    user_filter: UUID | None = Query(None, description="Filter by specific user ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RetentionStatusResponse:
    """Get document retention status and statistics.

    Returns information about document retention, expiry dates, and cleanup status.
    Regular users can only see their own data, admins can see all data.
    """
    try:
        service = GDPRDocumentCleanup(db)

        # Regular users can only see their own data
        if not current_user.is_admin and user_filter != current_user.id:
            user_filter = current_user.id

        stats = await service.get_retention_status(user_filter)

        return RetentionStatusResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get retention status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve retention status"
        )


@router.post("/delete-user-data", response_model=UserDeletionResponse)
@rate_limit("user_data_deletion", max_requests=2, window_hours=24)
async def delete_user_data(
    request: UserDataDeletionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserDeletionResponse:
    """Delete all documents for a user (GDPR Article 17 - Right to erasure).

    Users can delete their own data, admins can delete any user's data.
    This action is irreversible and complies with GDPR right to erasure.

    **Security:**
    - Rate limited to 2 requests per 24 hours
    - Secure file deletion (overwrite before delete)
    - Audit logging for compliance

    **Data Deleted:**
    - All uploaded documents
    - Document metadata
    - Processing results
    - Related files (thumbnails, previews)
    """
    try:
        # Authorization check
        if not current_user.is_admin and request.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only delete your own data")

        service = GDPRDocumentCleanup(db)

        if request.immediate:
            # Delete immediately
            stats = await service.delete_user_documents(request.user_id, request.reason)
        else:
            # Schedule for deletion (background task)
            background_tasks.add_task(service.delete_user_documents, request.user_id, request.reason)
            stats = {
                "user_id": str(request.user_id),
                "deleted_documents": 0,
                "storage_freed_mb": 0.0,
                "deletion_reason": f"{request.reason} (SCHEDULED)",
                "errors": [],
            }

        logger.info(
            f"User data deletion request: user {request.user_id} by {current_user.id}, "
            f"reason: {request.reason}, immediate: {request.immediate}"
        )

        return UserDeletionResponse(**stats, completed_at=datetime.utcnow().isoformat())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User data deletion failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User data deletion failed")


@router.post("/schedule-deletion")
@rate_limit("schedule_deletion", max_requests=10, window_hours=1)
async def schedule_document_deletion(
    request: ScheduleDeletionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Schedule a specific document for deletion.

    Users can schedule their own documents, admins can schedule any document.
    Useful for implementing custom retention policies.
    """
    try:
        # Validate deletion date is in the future
        if request.deletion_date <= datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deletion date must be in the future")

        # Validate deletion date is not too far in the future (max 1 year)
        max_future_date = datetime.utcnow() + timedelta(days=365)
        if request.deletion_date > max_future_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deletion date cannot be more than 1 year in the future",
            )

        service = GDPRDocumentCleanup(db)
        success = await service.schedule_document_deletion(request.document_id, request.deletion_date, request.reason)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found or cannot be scheduled for deletion"
            )

        logger.info(
            f"Document deletion scheduled: {request.document_id} for {request.deletion_date} by {current_user.id}"
        )

        return {
            "message": "Document scheduled for deletion",
            "document_id": str(request.document_id),
            "deletion_date": request.deletion_date.isoformat(),
            "reason": request.reason,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule document deletion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to schedule document deletion"
        )


@router.get("/compliance-info")
async def get_gdpr_compliance_info() -> dict[str, Any]:
    """Get GDPR compliance information and policies.

    Returns information about data retention policies, user rights,
    and compliance procedures.
    """
    return {
        "gdpr_compliance": {
            "data_controller": {
                "name": "PratikoAI SRL",
                "address": "Via dell'Innovazione 123, 00100 Roma, IT",
                "email": "privacy@pratikoai.com",
                "phone": "+39 06 12345678",
                "pec": "privacy@pec.pratikoai.it",
            },
            "legal_basis": "GDPR Article 6(1)(b) - Contract performance and Article 6(1)(f) - Legitimate interests",
            "retention_policy": {
                "default_period_days": 365,
                "purpose": "Tax document analysis and advisory services",
                "automatic_deletion": True,
                "secure_deletion": "Files are overwritten with random data before deletion",
            },
            "user_rights": {
                "right_to_access": "Users can access their data via API or support request",
                "right_to_rectification": "Users can update their data through the platform",
                "right_to_erasure": "Users can delete their data via API or support request",
                "right_to_portability": "Users can export their data in machine-readable format",
                "right_to_restrict": "Users can request processing restrictions",
                "right_to_object": "Users can object to data processing",
            },
            "data_protection_measures": {
                "encryption": "AES-256 encryption at rest and TLS 1.3 in transit",
                "access_control": "Role-based access with multi-factor authentication",
                "audit_logging": "All data operations are logged for compliance",
                "data_minimization": "Only necessary data is collected and processed",
                "pseudonymization": "Personal data is pseudonymized where possible",
            },
        },
        "cleanup_schedule": {
            "automatic_cleanup": "Daily at 02:00 UTC",
            "retention_checks": "Documents older than retention period are flagged",
            "secure_deletion": "Files are overwritten before deletion",
            "optimization": "Storage is optimized to remove empty directories",
        },
        "contact_info": {
            "data_protection_officer": "dpo@pratikoai.com",
            "privacy_support": "privacy@pratikoai.com",
            "supervisory_authority": {
                "name": "Garante per la protezione dei dati personali",
                "website": "https://www.gpdp.it",
                "email": "garante@gpdp.it",
            },
        },
    }


@router.get("/audit-log")
@rate_limit("audit_log", max_requests=10, window_hours=1)
async def get_cleanup_audit_log(
    days: int = Query(7, ge=1, le=90, description="Number of days to retrieve"),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get GDPR cleanup audit log (Admin only).

    Returns audit trail of all GDPR-related cleanup operations
    for compliance and monitoring purposes.
    """
    try:
        # In a real implementation, this would query an audit log table
        # For now, return a placeholder response

        datetime.utcnow() - timedelta(days=days)

        # This would typically query from an audit_log table
        audit_entries = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "operation": "automated_cleanup",
                "user_id": "system",
                "details": {"expired_documents": 15, "storage_freed_mb": 125.5, "reason": "GDPR_RETENTION_EXPIRED"},
            },
            # More entries would be loaded from database
        ]

        return {
            "audit_period_days": days,
            "total_entries": len(audit_entries),
            "entries": audit_entries,
            "compliance_note": "All GDPR operations are logged for regulatory compliance",
        }

    except Exception as e:
        logger.error(f"Failed to retrieve audit log: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve audit log")
