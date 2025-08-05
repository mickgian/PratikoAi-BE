"""
GDPR Deletion Scheduler for PratikoAI.

This module provides scheduled job functionality for automatically executing
overdue GDPR deletion requests within the 30-day legal deadline. Includes
monitoring, alerting, and retry mechanisms.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, asdict

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.services.gdpr_deletion_service import GDPRDeletionService, DeletionStatus
from app.services.user_data_deletor import UserDataDeletor
from app.services.deletion_verifier import DeletionVerifier
from app.core.logging import logger


@dataclass
class ScheduledJobResult:
    """Result of scheduled GDPR deletion job."""
    job_id: str
    execution_timestamp: datetime
    requests_processed: int
    successful_deletions: int
    failed_deletions: int
    total_processing_time_seconds: float
    alerts_generated: List[str]
    next_execution: datetime
    job_status: str  # "success", "partial_failure", "failure"


@dataclass
class DeletionAlert:
    """Alert for GDPR deletion issues."""
    alert_id: str
    alert_type: str  # "overdue_request", "deletion_failure", "compliance_breach"
    severity: str    # "low", "medium", "high", "critical"
    message: str
    affected_users: List[int]
    created_at: datetime
    requires_action: bool


class GDPRDeletionScheduler:
    """
    Scheduled job service for GDPR deletion compliance.
    
    Features:
    - Automatic execution of overdue deletion requests
    - Monitoring and alerting for compliance issues
    - Retry mechanisms for failed deletions
    - Performance tracking and reporting
    - Emergency escalation procedures
    """
    
    def __init__(self):
        """Initialize GDPR deletion scheduler."""
        self.settings = get_settings()
        
        # Job configuration
        self.job_config = {
            "execution_interval_hours": 4,  # Run every 4 hours
            "max_batch_size": 50,          # Maximum deletions per batch
            "retry_failed_deletions": True,
            "max_retry_attempts": 3,
            "alert_threshold_hours": 2,    # Alert if request overdue by 2+ hours
            "critical_threshold_hours": 24 # Critical alert if overdue by 24+ hours
        }
        
        # State tracking
        self.last_execution = None
        self.active_alerts = []
        self.job_history = []
        
        # Database connection
        self.engine = None
        self.async_session = None
    
    async def initialize(self):
        """Initialize scheduler with database connection."""
        try:
            self.engine = create_async_engine(
                self.settings.database_url,
                echo=False,
                pool_pre_ping=True
            )
            
            self.async_session = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("GDPR deletion scheduler initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize GDPR deletion scheduler: {e}")
            raise
    
    async def run_scheduled_deletion_job(self) -> ScheduledJobResult:
        """
        Run scheduled GDPR deletion job.
        
        This is the main entry point for scheduled execution, typically
        called by cron jobs or task schedulers.
        
        Returns:
            ScheduledJobResult with execution details
        """
        job_start_time = datetime.now(timezone.utc)
        job_id = f"gdpr_job_{job_start_time.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting scheduled GDPR deletion job {job_id}")
        
        try:
            if not self.async_session:
                await self.initialize()
            
            requests_processed = 0
            successful_deletions = 0
            failed_deletions = 0
            alerts_generated = []
            
            async with self.async_session() as session:
                gdpr_service = GDPRDeletionService(session)
                await gdpr_service.initialize()
                
                # Step 1: Check for compliance issues and generate alerts
                compliance_alerts = await self._check_compliance_and_alert(gdpr_service)
                alerts_generated.extend(compliance_alerts)
                
                # Step 2: Get overdue deletion requests
                overdue_requests = await gdpr_service.get_overdue_deletion_requests()
                
                if not overdue_requests:
                    logger.info("No overdue deletion requests found")
                else:
                    logger.info(f"Found {len(overdue_requests)} overdue deletion requests")
                    
                    # Step 3: Process overdue requests in batches
                    batch_size = min(self.job_config["max_batch_size"], len(overdue_requests))
                    
                    for i in range(0, len(overdue_requests), batch_size):
                        batch_requests = overdue_requests[i:i + batch_size]
                        batch_results = await self._process_deletion_batch(batch_requests, gdpr_service)
                        
                        requests_processed += len(batch_requests)
                        successful_deletions += sum(1 for r in batch_results if r.success)
                        failed_deletions += sum(1 for r in batch_results if not r.success)
                        
                        # Generate alerts for failures
                        failure_alerts = await self._generate_failure_alerts(batch_results)
                        alerts_generated.extend(failure_alerts)
                
                # Step 4: Retry previously failed deletions if configured
                if self.job_config["retry_failed_deletions"]:
                    retry_results = await self._retry_failed_deletions(gdpr_service)
                    
                    if retry_results:
                        requests_processed += len(retry_results)
                        successful_deletions += sum(1 for r in retry_results if r.success)
                        failed_deletions += sum(1 for r in retry_results if not r.success)
            
            job_end_time = datetime.now(timezone.utc)
            processing_time = (job_end_time - job_start_time).total_seconds()
            
            # Determine job status
            if failed_deletions == 0:
                job_status = "success"
            elif successful_deletions > 0:
                job_status = "partial_failure"
            else:
                job_status = "failure"
            
            # Calculate next execution time
            next_execution = job_start_time + timedelta(hours=self.job_config["execution_interval_hours"])
            
            # Create result
            result = ScheduledJobResult(
                job_id=job_id,
                execution_timestamp=job_start_time,
                requests_processed=requests_processed,
                successful_deletions=successful_deletions,
                failed_deletions=failed_deletions,
                total_processing_time_seconds=processing_time,
                alerts_generated=alerts_generated,
                next_execution=next_execution,
                job_status=job_status
            )
            
            # Update state
            self.last_execution = job_start_time
            self.job_history.append(result)
            
            # Keep only last 100 job results
            if len(self.job_history) > 100:
                self.job_history = self.job_history[-100:]
            
            logger.info(
                f"Completed scheduled GDPR deletion job {job_id}: "
                f"{successful_deletions} successful, {failed_deletions} failed, "
                f"{len(alerts_generated)} alerts in {processing_time:.1f}s"
            )
            
            return result
            
        except Exception as e:
            job_end_time = datetime.now(timezone.utc)
            processing_time = (job_end_time - job_start_time).total_seconds()
            
            logger.error(f"Scheduled GDPR deletion job {job_id} failed: {e}")
            
            # Create failure result
            result = ScheduledJobResult(
                job_id=job_id,
                execution_timestamp=job_start_time,
                requests_processed=0,
                successful_deletions=0,
                failed_deletions=0,
                total_processing_time_seconds=processing_time,
                alerts_generated=[f"Job execution failed: {str(e)}"],
                next_execution=job_start_time + timedelta(hours=self.job_config["execution_interval_hours"]),
                job_status="failure"
            )
            
            return result
    
    async def _check_compliance_and_alert(self, gdpr_service: GDPRDeletionService) -> List[str]:
        """Check for compliance issues and generate alerts."""
        try:
            alerts_generated = []
            current_time = datetime.now(timezone.utc)
            
            # Check deadline compliance
            compliance_status = await gdpr_service.check_deadline_compliance()
            
            # Generate alerts for overdue requests
            if compliance_status["overdue_requests"] > 0:
                alert_severity = "critical" if compliance_status["overdue_requests"] > 5 else "high"
                
                alert = DeletionAlert(
                    alert_id=f"overdue_{current_time.strftime('%Y%m%d_%H%M%S')}",
                    alert_type="overdue_request",
                    severity=alert_severity,
                    message=f"{compliance_status['overdue_requests']} GDPR deletion requests are overdue",
                    affected_users=[],  # Would be populated with specific user IDs
                    created_at=current_time,
                    requires_action=True
                )
                
                self.active_alerts.append(alert)
                alerts_generated.append(alert.message)
                
                logger.warning(f"Generated {alert_severity} alert: {alert.message}")
            
            # Check for requests approaching deadline
            if compliance_status["approaching_deadline"] > 0:
                alert = DeletionAlert(
                    alert_id=f"approaching_{current_time.strftime('%Y%m%d_%H%M%S')}",
                    alert_type="approaching_deadline",
                    severity="medium",
                    message=f"{compliance_status['approaching_deadline']} GDPR deletion requests approaching deadline",
                    affected_users=[],
                    created_at=current_time,
                    requires_action=False
                )
                
                self.active_alerts.append(alert)
                alerts_generated.append(alert.message)
                
                logger.info(f"Generated alert: {alert.message}")
            
            return alerts_generated
            
        except Exception as e:
            logger.error(f"Failed to check compliance and generate alerts: {e}")
            return [f"Compliance check failed: {str(e)}"]
    
    async def _process_deletion_batch(
        self,
        deletion_requests: List,
        gdpr_service: GDPRDeletionService
    ) -> List:
        """Process a batch of deletion requests."""
        try:
            logger.info(f"Processing batch of {len(deletion_requests)} deletion requests")
            
            batch_results = []
            
            for request in deletion_requests:
                try:
                    # Execute single deletion
                    result = await gdpr_service._execute_single_deletion(request)
                    batch_results.append(result)
                    
                    # Update request status
                    if result.success:
                        await gdpr_service._update_request_status(
                            request.request_id,
                            DeletionStatus.COMPLETED,
                            completion_time=datetime.now(timezone.utc),
                            certificate_id=result.deletion_certificate_id
                        )
                    else:
                        await gdpr_service._update_request_status(
                            request.request_id,
                            DeletionStatus.FAILED,
                            error_message=result.error_message
                        )
                    
                    # Add small delay between deletions to avoid overwhelming the system
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to process deletion request {request.request_id}: {e}")
                    
                    # Create failed result
                    from app.services.gdpr_deletion_service import DeletionResult
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
                    batch_results.append(failed_result)
            
            successful_count = sum(1 for r in batch_results if r.success)
            logger.info(f"Batch processing completed: {successful_count}/{len(batch_results)} successful")
            
            return batch_results
            
        except Exception as e:
            logger.error(f"Failed to process deletion batch: {e}")
            return []
    
    async def _generate_failure_alerts(self, deletion_results: List) -> List[str]:
        """Generate alerts for failed deletions."""
        try:
            alerts_generated = []
            failed_results = [r for r in deletion_results if not r.success]
            
            if not failed_results:
                return alerts_generated
            
            current_time = datetime.now(timezone.utc)
            
            # Group failures by error type
            error_groups = {}
            for result in failed_results:
                error_key = result.error_message[:50] if result.error_message else "Unknown error"
                if error_key not in error_groups:
                    error_groups[error_key] = []
                error_groups[error_key].append(result.user_id)
            
            # Generate alerts for each error group
            for error_type, affected_users in error_groups.items():
                alert = DeletionAlert(
                    alert_id=f"failure_{current_time.strftime('%Y%m%d_%H%M%S')}_{len(affected_users)}",
                    alert_type="deletion_failure",
                    severity="high" if len(affected_users) > 1 else "medium",
                    message=f"GDPR deletion failed for {len(affected_users)} users: {error_type}",
                    affected_users=affected_users,
                    created_at=current_time,
                    requires_action=True
                )
                
                self.active_alerts.append(alert)
                alerts_generated.append(alert.message)
                
                logger.error(f"Generated failure alert: {alert.message}")
            
            return alerts_generated
            
        except Exception as e:
            logger.error(f"Failed to generate failure alerts: {e}")
            return [f"Alert generation failed: {str(e)}"]
    
    async def _retry_failed_deletions(self, gdpr_service: GDPRDeletionService) -> List:
        """Retry previously failed deletion requests."""
        try:
            # Get failed requests that haven't exceeded retry limit
            from sqlalchemy import select, and_
            from app.services.gdpr_deletion_service import GDPRDeletionRequest
            
            async with self.async_session() as session:
                result = await session.execute(
                    select(GDPRDeletionRequest).where(
                        and_(
                            GDPRDeletionRequest.status == DeletionStatus.FAILED.value,
                            # Add retry logic here - would need retry_count field
                        )
                    ).limit(10)  # Limit retries per job
                )
                
                failed_requests = result.scalars().all()
                
                if not failed_requests:
                    return []
                
                logger.info(f"Retrying {len(failed_requests)} failed deletion requests")
                
                retry_results = []
                for db_request in failed_requests:
                    # Convert to DeletionRequest object
                    from app.services.gdpr_deletion_service import DeletionRequest, DeletionPriority
                    request = DeletionRequest(
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
                    
                    # Retry execution
                    try:
                        result = await gdpr_service._execute_single_deletion(request)
                        retry_results.append(result)
                        
                        # Update status based on result
                        if result.success:
                            await gdpr_service._update_request_status(
                                request.request_id,
                                DeletionStatus.COMPLETED,
                                completion_time=datetime.now(timezone.utc),
                                certificate_id=result.deletion_certificate_id
                            )
                            logger.info(f"Retry successful for request {request.request_id}")
                        else:
                            logger.warning(f"Retry failed for request {request.request_id}: {result.error_message}")
                    
                    except Exception as e:
                        logger.error(f"Retry failed for request {request.request_id}: {e}")
                
                return retry_results
                
        except Exception as e:
            logger.error(f"Failed to retry failed deletions: {e}")
            return []
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status and metrics."""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Calculate next scheduled execution
            next_execution = None
            if self.last_execution:
                next_execution = self.last_execution + timedelta(
                    hours=self.job_config["execution_interval_hours"]
                )
            
            # Get recent job statistics
            recent_jobs = self.job_history[-10:] if self.job_history else []
            total_processed = sum(job.requests_processed for job in recent_jobs)
            total_successful = sum(job.successful_deletions for job in recent_jobs)
            
            success_rate = (total_successful / total_processed * 100) if total_processed > 0 else 100.0
            
            # Count active alerts by severity
            alert_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
            for alert in self.active_alerts:
                alert_counts[alert.severity] += 1
            
            return {
                "scheduler_status": "active" if self.async_session else "inactive",
                "last_execution": self.last_execution.isoformat() if self.last_execution else None,
                "next_execution": next_execution.isoformat() if next_execution else None,
                "execution_interval_hours": self.job_config["execution_interval_hours"],
                "total_jobs_executed": len(self.job_history),
                "recent_success_rate": success_rate,
                "active_alerts": len(self.active_alerts),
                "alert_breakdown": alert_counts,
                "last_10_jobs": [asdict(job) for job in recent_jobs],
                "configuration": self.job_config,
                "status_timestamp": current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get scheduler status: {e}")
            return {
                "scheduler_status": "error",
                "error": str(e),
                "status_timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def cleanup(self):
        """Cleanup scheduler resources."""
        try:
            if self.engine:
                await self.engine.dispose()
            logger.info("GDPR deletion scheduler cleanup completed")
        except Exception as e:
            logger.error(f"Error during scheduler cleanup: {e}")


# Singleton instance for scheduled jobs
_scheduler_instance = None

async def get_gdpr_scheduler() -> GDPRDeletionScheduler:
    """Get singleton GDPR deletion scheduler instance."""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = GDPRDeletionScheduler()
        await _scheduler_instance.initialize()
    
    return _scheduler_instance


# Utility functions for cron jobs

async def run_gdpr_deletion_job() -> Dict[str, Any]:
    """
    Main entry point for scheduled GDPR deletion job.
    
    This function should be called by cron jobs or task schedulers.
    
    Returns:
        Dict with job execution results
    """
    try:
        scheduler = await get_gdpr_scheduler()
        result = await scheduler.run_scheduled_deletion_job()
        return asdict(result)
        
    except Exception as e:
        logger.error(f"Failed to run GDPR deletion job: {e}")
        return {
            "job_status": "failure",
            "error": str(e),
            "execution_timestamp": datetime.now(timezone.utc).isoformat()
        }


async def get_gdpr_scheduler_status() -> Dict[str, Any]:
    """
    Get GDPR scheduler status for monitoring.
    
    Returns:
        Dict with scheduler status and metrics
    """
    try:
        scheduler = await get_gdpr_scheduler()
        return await scheduler.get_scheduler_status()
        
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        return {
            "scheduler_status": "error",
            "error": str(e),
            "status_timestamp": datetime.now(timezone.utc).isoformat()
        }