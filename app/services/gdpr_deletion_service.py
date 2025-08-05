"""
GDPR Data Deletion Service for PratikoAI.

This module provides comprehensive GDPR Article 17 "Right to be forgotten" compliance
with actual data deletion within 30 days, cascading deletions, audit trail preservation,
and complete erasure across all systems including PostgreSQL, Redis, backups, logs, and Stripe.

Features:
- Complete user data deletion from all tables
- 30-day deadline tracking with automatic execution
- Cascading deletion of related records
- Irreversible deletion with verification
- Audit trail preservation
- Deletion from all systems (PostgreSQL, Redis, backups, logs, Stripe)
- Deletion certificate generation
- Compliance reporting
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy import text, select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import DateTime, String, Boolean, Integer, Text

from app.models.encrypted_user import EncryptedUser
from app.models.session import Session
from app.core.logging import logger
from app.core.config import get_settings
from app.services.database_encryption_service import DatabaseEncryptionService


class DeletionStatus(str, Enum):
    """GDPR deletion request status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeletionPriority(str, Enum):
    """GDPR deletion priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class SystemType(str, Enum):
    """Types of systems for data deletion."""
    DATABASE = "database"
    REDIS = "redis"
    LOGS = "logs"
    BACKUPS = "backups"
    STRIPE = "stripe"
    EXTERNAL_API = "external_api"


@dataclass
class DeletionRequest:
    """GDPR deletion request data structure."""
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


@dataclass
class DeletionResult:
    """Result of GDPR deletion operation."""
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
    verification_result: Optional[Dict[str, Any]] = None


@dataclass
class ComplianceReport:
    """GDPR deletion compliance report."""
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


@dataclass
class DeletionMetrics:
    """GDPR deletion performance metrics."""
    total_requests: int
    completed_deletions: int
    pending_deletions: int
    overdue_deletions: int
    average_processing_time_hours: float
    compliance_rate: float
    last_updated: datetime


@dataclass
class VerificationResult:
    """Result of deletion verification."""
    user_id: int
    is_completely_deleted: bool
    remaining_data_found: List[Dict[str, Any]]
    verification_score: float
    gdpr_compliant: bool
    verification_timestamp: datetime
    systems_verified: List[str]


@dataclass
class DeletionCertificate:
    """GDPR deletion certificate."""
    certificate_id: str
    user_id: int
    is_complete_deletion: bool
    issued_at: datetime
    compliance_attestation: bool
    certificate_text: str
    verification_details: Dict[str, Any]


class GDPRDeletionRequest(SQLModel, table=True):
    """Database model for GDPR deletion requests."""
    
    __tablename__ = "gdpr_deletion_requests"
    
    id: int = Field(default=None, primary_key=True)
    request_id: str = Field(unique=True, index=True, description="Unique request identifier")
    user_id: int = Field(foreign_key="users.id", index=True, description="User to be deleted")
    status: str = Field(default=DeletionStatus.PENDING, description="Current status")
    initiated_by_user: bool = Field(description="Whether user initiated the request")
    admin_user_id: Optional[int] = Field(default=None, description="Admin user who initiated")
    reason: str = Field(description="Reason for deletion")
    priority: str = Field(default=DeletionPriority.NORMAL, description="Request priority")
    
    # Timestamps
    request_timestamp: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc),
        description="When request was created"
    )
    deletion_deadline: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        description="30-day GDPR deadline"
    )
    scheduled_execution: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="When deletion is scheduled"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="When deletion was completed"
    )
    
    # Results
    deletion_certificate_id: Optional[str] = Field(
        default=None,
        description="ID of deletion certificate"
    )
    error_message: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Error message if failed"
    )
    
    # Audit
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )


class GDPRDeletionAuditLog(SQLModel, table=True):
    """Audit log for GDPR deletion operations."""
    
    __tablename__ = "gdpr_deletion_audit_log"
    
    id: int = Field(default=None, primary_key=True)
    request_id: str = Field(index=True, description="Associated deletion request")
    original_user_id: int = Field(description="Original user ID (preserved for audit)")
    anonymized_user_id: Optional[str] = Field(description="Anonymized user identifier")
    
    # Deletion details
    operation: str = Field(description="Type of deletion operation")
    table_name: Optional[str] = Field(description="Table being processed")
    records_deleted: int = Field(default=0, description="Number of records deleted")
    system_type: str = Field(description="System being processed")
    
    # Results
    success: bool = Field(description="Whether operation succeeded")
    error_message: Optional[str] = Field(default=None, description="Error if failed")
    processing_time_ms: float = Field(description="Processing time in milliseconds")
    
    # Audit trail
    deletion_timestamp: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc),
        description="When deletion occurred"
    )
    verification_hash: Optional[str] = Field(
        description="Hash for verification of deletion"
    )


class GDPRDeletionCertificate(SQLModel, table=True):
    """GDPR deletion certificates."""
    
    __tablename__ = "gdpr_deletion_certificates"
    
    id: int = Field(default=None, primary_key=True)
    certificate_id: str = Field(unique=True, index=True, description="Certificate ID")
    request_id: str = Field(index=True, description="Associated deletion request")
    user_id: int = Field(description="User who was deleted")
    
    # Certificate details
    is_complete_deletion: bool = Field(description="Whether deletion was complete")
    compliance_attestation: bool = Field(description="Compliance attestation")
    certificate_text: str = Field(sa_column=Column(Text), description="Certificate content")
    verification_details: str = Field(sa_column=Column(Text), description="Verification details JSON")
    
    # Issuance
    issued_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc),
        description="When certificate was issued"
    )
    issued_by: str = Field(default="PratikoAI-GDPR-System", description="Certificate issuer")


class GDPRDeletionService:
    """
    Comprehensive GDPR deletion service implementing Article 17 compliance.
    
    Features:
    - 30-day deadline tracking and automatic execution
    - Complete data removal across all systems
    - Audit trail preservation
    - Deletion verification and certification
    - Compliance reporting and metrics
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize GDPR deletion service.
        
        Args:
            db_session: Database session for operations
        """
        self.db = db_session
        self.settings = get_settings()
        
        # Service dependencies
        self.user_data_deletor = None
        self.deletion_verifier = None
        self.encryption_service = None
        
        # Performance tracking
        self.metrics = {
            "total_requests": 0,
            "successful_deletions": 0,
            "failed_deletions": 0,
            "average_processing_time": 0.0
        }
    
    async def initialize(self):
        """Initialize service dependencies."""
        try:
            self.user_data_deletor = UserDataDeletor(self.db)
            self.deletion_verifier = DeletionVerifier(self.db)
            self.encryption_service = DatabaseEncryptionService(self.db)
            await self.encryption_service.initialize()
            
            logger.info("GDPR deletion service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize GDPR deletion service: {e}")
            raise
    
    async def create_deletion_request(
        self,
        user_id: int,
        initiated_by_user: bool,
        reason: str,
        admin_user_id: Optional[int] = None,
        priority: DeletionPriority = DeletionPriority.NORMAL
    ) -> DeletionRequest:
        """
        Create a new GDPR deletion request.
        
        Args:
            user_id: ID of user to delete
            initiated_by_user: Whether user initiated the request
            reason: Reason for deletion
            admin_user_id: Admin user ID if admin-initiated
            priority: Request priority level
            
        Returns:
            DeletionRequest object
            
        Raises:
            ValueError: If user doesn't exist or request already exists
        """
        try:
            # Validate user exists
            user = await self.db.get(EncryptedUser, user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} does not exist")
            
            # Check for existing pending request
            existing_request = await self.db.execute(
                select(GDPRDeletionRequest).where(
                    GDPRDeletionRequest.user_id == user_id,
                    GDPRDeletionRequest.status.in_([
                        DeletionStatus.PENDING,
                        DeletionStatus.IN_PROGRESS
                    ])
                )
            )
            
            if existing_request.fetchone():
                raise ValueError(f"Deletion request already exists for user {user_id}")
            
            # Generate request ID
            request_id = f"gdpr_del_{uuid.uuid4().hex[:12]}"
            
            # Calculate 30-day deadline
            request_time = datetime.now(timezone.utc)
            deletion_deadline = request_time + timedelta(days=30)
            
            # Create database record
            db_request = GDPRDeletionRequest(
                request_id=request_id,
                user_id=user_id,
                status=DeletionStatus.PENDING,
                initiated_by_user=initiated_by_user,
                admin_user_id=admin_user_id,
                reason=reason,
                priority=priority,
                request_timestamp=request_time,
                deletion_deadline=deletion_deadline
            )
            
            self.db.add(db_request)
            await self.db.commit()
            await self.db.refresh(db_request)
            
            # Create return object
            deletion_request = DeletionRequest(
                request_id=request_id,
                user_id=user_id,
                status=DeletionStatus.PENDING,
                initiated_by_user=initiated_by_user,
                admin_user_id=admin_user_id,
                reason=reason,
                priority=priority,
                request_timestamp=request_time,
                deletion_deadline=deletion_deadline,
                scheduled_execution=None,
                completed_at=None,
                deletion_certificate_id=None,
                error_message=None
            )
            
            # Log request creation
            await self._audit_log(
                request_id=request_id,
                original_user_id=user_id,
                operation="deletion_request_created",
                system_type=SystemType.DATABASE,
                success=True,
                records_deleted=0
            )
            
            logger.info(
                f"Created GDPR deletion request {request_id} for user {user_id} "
                f"(deadline: {deletion_deadline.isoformat()})"
            )
            
            return deletion_request
            
        except Exception as e:
            logger.error(f"Failed to create deletion request for user {user_id}: {e}")
            raise
    
    async def get_overdue_deletion_requests(self) -> List[DeletionRequest]:
        """
        Get all deletion requests that are overdue (past 30-day deadline).
        
        Returns:
            List of overdue DeletionRequest objects
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            result = await self.db.execute(
                select(GDPRDeletionRequest).where(
                    GDPRDeletionRequest.deletion_deadline <= current_time,
                    GDPRDeletionRequest.status == DeletionStatus.PENDING
                ).order_by(GDPRDeletionRequest.deletion_deadline)
            )
            
            overdue_requests = []
            for db_request in result.scalars():
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
                overdue_requests.append(deletion_request)
            
            logger.info(f"Found {len(overdue_requests)} overdue deletion requests")
            return overdue_requests
            
        except Exception as e:
            logger.error(f"Failed to get overdue deletion requests: {e}")
            raise
    
    async def execute_overdue_deletions(self) -> List[DeletionResult]:
        """
        Execute all overdue deletion requests automatically.
        
        Returns:
            List of DeletionResult objects
        """
        try:
            overdue_requests = await self.get_overdue_deletion_requests()
            
            if not overdue_requests:
                logger.info("No overdue deletion requests found")
                return []
            
            logger.info(f"Executing {len(overdue_requests)} overdue deletion requests")
            
            results = []
            for request in overdue_requests:
                try:
                    # Update status to in progress
                    await self._update_request_status(
                        request.request_id,
                        DeletionStatus.IN_PROGRESS
                    )
                    
                    # Execute deletion
                    result = await self._execute_single_deletion(request)
                    results.append(result)
                    
                    # Update status based on result
                    if result.success:
                        await self._update_request_status(
                            request.request_id,
                            DeletionStatus.COMPLETED,
                            completion_time=datetime.now(timezone.utc),
                            certificate_id=result.deletion_certificate_id
                        )
                    else:
                        await self._update_request_status(
                            request.request_id,
                            DeletionStatus.FAILED,
                            error_message=result.error_message
                        )
                    
                except Exception as e:
                    logger.error(f"Failed to execute deletion for request {request.request_id}: {e}")
                    
                    # Create failed result
                    failed_result = DeletionResult(
                        request_id=request.request_id,
                        user_id=request.user_id,
                        success=False,
                        total_records_deleted=0,
                        tables_affected=[],
                        systems_processed=[],
                        audit_records_preserved=0,
                        deletion_certificate_id=None,
                        processing_time_seconds=0.0,
                        error_message=str(e)
                    )
                    results.append(failed_result)
                    
                    # Update request status
                    await self._update_request_status(
                        request.request_id,
                        DeletionStatus.FAILED,
                        error_message=str(e)
                    )
            
            logger.info(f"Completed {len(results)} deletion executions")
            return results
            
        except Exception as e:
            logger.error(f"Failed to execute overdue deletions: {e}")
            raise
    
    async def _execute_single_deletion(self, request: DeletionRequest) -> DeletionResult:
        """Execute deletion for a single request."""
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"Executing deletion for request {request.request_id}, user {request.user_id}")
            
            if not self.user_data_deletor:
                await self.initialize()
            
            # Step 1: Delete user data
            deletion_result = await self.user_data_deletor.delete_user_data(
                request.user_id,
                preserve_audit_trail=True
            )
            
            if not deletion_result.success:
                raise Exception(f"Data deletion failed: {deletion_result.error_message}")
            
            # Step 2: Verify deletion
            if not self.deletion_verifier:
                await self.initialize()
            
            verification_result = await self.deletion_verifier.verify_user_deletion(
                request.user_id
            )
            
            # Step 3: Generate certificate if deletion is complete
            certificate_id = None
            if verification_result.is_completely_deleted:
                certificate = await self.deletion_verifier.generate_deletion_certificate(
                    verification_result
                )
                certificate_id = certificate.certificate_id
            
            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()
            
            result = DeletionResult(
                request_id=request.request_id,
                user_id=request.user_id,
                success=True,
                total_records_deleted=deletion_result.total_records_deleted,
                tables_affected=deletion_result.tables_affected,
                systems_processed=deletion_result.systems_processed,
                audit_records_preserved=deletion_result.audit_records_preserved,
                deletion_certificate_id=certificate_id,
                processing_time_seconds=processing_time,
                error_message=None,
                verification_result=asdict(verification_result)
            )
            
            # Log successful deletion
            await self._audit_log(
                request_id=request.request_id,
                original_user_id=request.user_id,
                operation="deletion_completed",
                system_type=SystemType.DATABASE,
                success=True,
                records_deleted=deletion_result.total_records_deleted,
                processing_time_ms=processing_time * 1000
            )
            
            logger.info(
                f"Successfully executed deletion for request {request.request_id}: "
                f"{deletion_result.total_records_deleted} records in {processing_time:.1f}s"
            )
            
            return result
            
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()
            
            # Log failed deletion
            await self._audit_log(
                request_id=request.request_id,
                original_user_id=request.user_id,
                operation="deletion_failed",
                system_type=SystemType.DATABASE,
                success=False,
                records_deleted=0,
                processing_time_ms=processing_time * 1000,
                error_message=str(e)
            )
            
            result = DeletionResult(
                request_id=request.request_id,
                user_id=request.user_id,
                success=False,
                total_records_deleted=0,
                tables_affected=[],
                systems_processed=[],
                audit_records_preserved=0,
                deletion_certificate_id=None,
                processing_time_seconds=processing_time,
                error_message=str(e)
            )
            
            logger.error(f"Failed to execute deletion for request {request.request_id}: {e}")
            return result
    
    async def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> ComplianceReport:
        """
        Generate GDPR deletion compliance report for a date range.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            ComplianceReport object
        """
        try:
            report_id = f"gdpr_report_{uuid.uuid4().hex[:12]}"
            report_period_days = (end_date - start_date).days
            
            # Get deletion request statistics
            result = await self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_requests,
                    COUNT(*) FILTER (WHERE initiated_by_user = true) as user_initiated,
                    COUNT(*) FILTER (WHERE initiated_by_user = false) as admin_initiated,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE deletion_deadline < NOW() AND status = 'pending') as overdue,
                    AVG(EXTRACT(EPOCH FROM (completed_at - request_timestamp))/3600) 
                        FILTER (WHERE completed_at IS NOT NULL) as avg_completion_hours
                FROM gdpr_deletion_requests
                WHERE request_timestamp >= :start_date 
                  AND request_timestamp <= :end_date
            """), {
                "start_date": start_date,
                "end_date": end_date
            })
            
            stats = result.fetchone()
            
            # Calculate compliance score
            total_requests = stats[0] if stats[0] else 0
            completed_deletions = stats[3] if stats[3] else 0
            overdue_deletions = stats[6] if stats[6] else 0
            
            if total_requests > 0:
                completion_rate = completed_deletions / total_requests
                overdue_rate = overdue_deletions / total_requests
                compliance_score = max(0, 100 - (overdue_rate * 50))  # Penalty for overdue
            else:
                completion_rate = 1.0
                compliance_score = 100.0
            
            report = ComplianceReport(
                report_id=report_id,
                report_period_days=report_period_days,
                total_deletion_requests=total_requests,
                user_initiated_requests=stats[1] if stats[1] else 0,
                admin_initiated_requests=stats[2] if stats[2] else 0,
                completed_deletions=completed_deletions,
                failed_deletions=stats[4] if stats[4] else 0,
                pending_deletions=stats[5] if stats[5] else 0,
                overdue_deletions=overdue_deletions,
                average_completion_time_hours=float(stats[7]) if stats[7] else 0.0,
                compliance_score=compliance_score,
                generated_at=datetime.now(timezone.utc)
            )
            
            logger.info(f"Generated compliance report {report_id} for {report_period_days} days")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            raise
    
    async def get_deletion_metrics(self) -> DeletionMetrics:
        """
        Get current GDPR deletion metrics.
        
        Returns:
            DeletionMetrics object
        """
        try:
            # Get overall statistics
            result = await self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_requests,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE deletion_deadline < NOW() AND status = 'pending') as overdue,
                    AVG(EXTRACT(EPOCH FROM (completed_at - request_timestamp))/3600) 
                        FILTER (WHERE completed_at IS NOT NULL) as avg_processing_hours
                FROM gdpr_deletion_requests
            """))
            
            stats = result.fetchone()
            
            total_requests = stats[0] if stats[0] else 0
            completed_deletions = stats[1] if stats[1] else 0
            
            # Calculate compliance rate
            compliance_rate = (completed_deletions / total_requests * 100) if total_requests > 0 else 100.0
            
            metrics = DeletionMetrics(
                total_requests=total_requests,
                completed_deletions=completed_deletions,
                pending_deletions=stats[2] if stats[2] else 0,
                overdue_deletions=stats[3] if stats[3] else 0,
                average_processing_time_hours=float(stats[4]) if stats[4] else 0.0,
                compliance_rate=compliance_rate,
                last_updated=datetime.now(timezone.utc)
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get deletion metrics: {e}")
            raise
    
    async def check_deadline_compliance(self) -> Dict[str, Any]:
        """
        Check compliance with 30-day deletion deadlines.
        
        Returns:
            Dict with compliance status information
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # Get deadline statistics
            result = await self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_active,
                    COUNT(*) FILTER (WHERE deletion_deadline - NOW() <= INTERVAL '7 days' 
                                   AND deletion_deadline > NOW()) as approaching_deadline,
                    COUNT(*) FILTER (WHERE deletion_deadline <= NOW()) as overdue
                FROM gdpr_deletion_requests
                WHERE status IN ('pending', 'in_progress')
            """))
            
            stats = result.fetchone()
            
            total_active = stats[0] if stats[0] else 0
            approaching_deadline = stats[1] if stats[1] else 0
            overdue_requests = stats[2] if stats[2] else 0
            
            # Calculate compliance rate
            if total_active > 0:
                compliance_rate = ((total_active - overdue_requests) / total_active) * 100
            else:
                compliance_rate = 100.0
            
            return {
                "timestamp": current_time.isoformat(),
                "total_active_requests": total_active,
                "approaching_deadline": approaching_deadline,
                "overdue_requests": overdue_requests,
                "compliance_rate": compliance_rate,
                "deadline_compliance_status": "compliant" if overdue_requests == 0 else "non_compliant"
            }
            
        except Exception as e:
            logger.error(f"Failed to check deadline compliance: {e}")
            raise
    
    async def _update_request_status(
        self,
        request_id: str,
        status: DeletionStatus,
        completion_time: Optional[datetime] = None,
        certificate_id: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update deletion request status."""
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.now(timezone.utc)
            }
            
            if completion_time:
                update_data["completed_at"] = completion_time
            
            if certificate_id:
                update_data["deletion_certificate_id"] = certificate_id
            
            if error_message:
                update_data["error_message"] = error_message
            
            await self.db.execute(
                update(GDPRDeletionRequest)
                .where(GDPRDeletionRequest.request_id == request_id)
                .values(**update_data)
            )
            
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to update request status for {request_id}: {e}")
            raise
    
    async def _audit_log(
        self,
        request_id: str,
        original_user_id: int,
        operation: str,
        system_type: SystemType,
        success: bool,
        records_deleted: int = 0,
        table_name: Optional[str] = None,
        processing_time_ms: Optional[float] = None,
        error_message: Optional[str] = None
    ):
        """Create audit log entry for deletion operation."""
        try:
            # Generate anonymized user ID for audit trail
            anonymized_user_id = f"user_{original_user_id}_deleted_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
            
            # Create verification hash
            import hashlib
            verification_data = f"{request_id}:{original_user_id}:{operation}:{datetime.now(timezone.utc).isoformat()}"
            verification_hash = hashlib.sha256(verification_data.encode()).hexdigest()[:16]
            
            audit_entry = GDPRDeletionAuditLog(
                request_id=request_id,
                original_user_id=original_user_id,
                anonymized_user_id=anonymized_user_id,
                operation=operation,
                table_name=table_name,
                records_deleted=records_deleted,
                system_type=system_type.value,
                success=success,
                error_message=error_message,
                processing_time_ms=processing_time_ms or 0.0,
                verification_hash=verification_hash
            )
            
            self.db.add(audit_entry)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to create audit log entry: {e}")
            # Don't raise - audit logging shouldn't break main operation


# Export main components
__all__ = [
    'GDPRDeletionService',
    'DeletionRequest',
    'DeletionResult',
    'ComplianceReport',
    'DeletionMetrics',
    'VerificationResult',
    'DeletionCertificate',
    'DeletionStatus',
    'DeletionPriority',
    'SystemType'
]