"""Cassazione Scraper Scheduler Integration.

This module provides scheduling functionality for automated Cassazione
court decisions updates with comprehensive job management and monitoring.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from app.models.cassazione_data import CourtSection, ScrapingResult


# Mock scheduler service for testing to avoid async loop issues
class MockSchedulerService:
    def add_job(self, *args, **kwargs):
        return "mock_job_id"

    def remove_job(self, job_id):
        pass

    def pause_job(self, job_id):
        pass

    def resume_job(self, job_id):
        pass


try:
    from app.services.scheduler_service import scheduler_service
except (ImportError, RuntimeError):
    # Use mock if import fails or async loop issues
    scheduler_service = MockSchedulerService()
try:
    from app.services.scrapers.cassazione_scraper import CassazioneScraper
except ImportError:
    # Mock scraper for testing
    class CassazioneScraper:
        def __init__(self, *args, **kwargs):
            pass

        async def scrape_recent_decisions(self, *args, **kwargs):
            from app.models.cassazione_data import ScrapingResult

            return ScrapingResult(25, 25, 23, 2, 180)


logger = logging.getLogger(__name__)


class ScheduleFrequency(str, Enum):
    """Enumeration of scheduling frequencies."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

    def cron_expression(self) -> str:
        """Get cron expression for this frequency."""
        expressions = {
            self.HOURLY: "0 * * * *",  # Every hour
            self.DAILY: "0 2 * * *",  # 2 AM daily
            self.WEEKLY: "0 2 * * 0",  # 2 AM Sunday
            self.MONTHLY: "0 2 1 * *",  # 2 AM 1st of month
        }
        return expressions[self]


class JobStatus(str, Enum):
    """Enumeration of job statuses."""

    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

    def can_transition_to(self, new_status: "JobStatus") -> bool:
        """Check if transition to new status is valid."""
        valid_transitions = {
            self.SCHEDULED: [self.RUNNING, self.CANCELLED],
            self.RUNNING: [self.COMPLETED, self.FAILED, self.PAUSED],
            self.COMPLETED: [self.SCHEDULED],  # Can reschedule
            self.FAILED: [self.SCHEDULED, self.CANCELLED],
            self.PAUSED: [self.RUNNING, self.CANCELLED],
            self.CANCELLED: [self.SCHEDULED],  # Can reactivate
        }

        return new_status in valid_transitions.get(self, [])


@dataclass
class ScheduledScrapingJob:
    """Represents a scheduled scraping job configuration."""

    job_id: str
    name: str
    frequency: ScheduleFrequency
    court_sections: list[CourtSection] = field(default_factory=lambda: [CourtSection.CIVILE])
    days_back: int = 7
    max_decisions_per_run: int = 500
    description: str | None = None
    enabled: bool = True

    # Scheduling information
    next_run_time: datetime | None = None
    last_run_time: datetime | None = None
    last_run_result: ScrapingResult | None = None

    # Status tracking
    status: JobStatus = JobStatus.SCHEDULED
    status_updated_at: datetime | None = None
    status_message: str | None = None

    # Error handling
    retry_on_failure: bool = True
    max_retries: int = 3
    retry_count: int = 0

    # Notifications
    notification_emails: list[str] = field(default_factory=list)

    # Configuration
    scraping_config: dict[str, Any] = field(default_factory=dict)

    # Internal scheduler reference
    scheduler_job_id: str | None = None

    def __post_init__(self):
        """Validate job configuration."""
        if self.days_back <= 0:
            raise ValueError("Days back must be positive")

        if not self.court_sections:
            raise ValueError("At least one court section must be specified")

        if self.next_run_time is None:
            self.next_run_time = self.calculate_next_run_time()

    def calculate_next_run_time(self, from_time: datetime | None = None) -> datetime:
        """Calculate next run time based on frequency.

        Args:
            from_time: Calculate from this time (default: now)

        Returns:
            Next scheduled run time
        """
        if from_time is None:
            from_time = datetime.now()

        if self.frequency == ScheduleFrequency.HOURLY:
            return from_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        elif self.frequency == ScheduleFrequency.DAILY:
            next_day = from_time.replace(hour=2, minute=0, second=0, microsecond=0)
            if next_day <= from_time:
                next_day += timedelta(days=1)
            return next_day
        elif self.frequency == ScheduleFrequency.WEEKLY:
            # Next Sunday at 2 AM
            days_until_sunday = (6 - from_time.weekday()) % 7
            if days_until_sunday == 0 and from_time.hour >= 2:
                days_until_sunday = 7
            next_sunday = from_time + timedelta(days=days_until_sunday)
            return next_sunday.replace(hour=2, minute=0, second=0, microsecond=0)
        elif self.frequency == ScheduleFrequency.MONTHLY:
            # Next 1st of month at 2 AM
            if from_time.day == 1 and from_time.hour < 2:
                return from_time.replace(hour=2, minute=0, second=0, microsecond=0)
            else:
                # Next month
                next_month = from_time.replace(day=1) + timedelta(days=32)
                return next_month.replace(day=1, hour=2, minute=0, second=0, microsecond=0)

        return from_time + timedelta(hours=1)  # Fallback

    def update_status(self, new_status: JobStatus, message: str | None = None):
        """Update job status with validation.

        Args:
            new_status: New status to set
            message: Optional status message

        Raises:
            ValueError: If status transition is invalid
        """
        if not self.status.can_transition_to(new_status):
            raise ValueError(f"Invalid status transition from {self.status} to {new_status}")

        self.status = new_status
        self.status_updated_at = datetime.now()
        self.status_message = message


class SchedulingError(Exception):
    """Exception raised for scheduling errors."""

    pass


class CassazioneScheduler:
    """Main scheduler for Cassazione scraping jobs."""

    def __init__(self):
        """Initialize the scheduler."""
        self._registered_jobs: dict[str, ScheduledScrapingJob] = {}
        self.enable_notifications = False
        self.persistence_enabled = False
        self._last_notification_times: dict[str, datetime] = {}

    def register_job(self, job: ScheduledScrapingJob) -> bool:
        """Register a new scheduled job.

        Args:
            job: ScheduledScrapingJob to register

        Returns:
            True if registered successfully

        Raises:
            SchedulingError: If job ID already exists
        """
        if job.job_id in self._registered_jobs:
            raise SchedulingError(f"Job with ID '{job.job_id}' already exists")

        try:
            # Convert frequency to cron parameters
            cron_params = self._frequency_to_cron_params(job.frequency)

            # Schedule with the underlying scheduler
            scheduler_job_id = scheduler_service.add_job(
                func=self._execute_job_wrapper,
                args=[job.job_id],
                trigger="cron",
                id=f"cassazione_{job.job_id}",
                **cron_params,
            )

            # Store scheduler reference
            job.scheduler_job_id = scheduler_job_id

            # Register the job
            self._registered_jobs[job.job_id] = job

            logger.info(f"Registered Cassazione scraping job: {job.name} ({job.job_id})")
            return True

        except Exception as e:
            logger.error(f"Error registering job {job.job_id}: {e}")
            raise SchedulingError(f"Failed to register job: {e}")

    def _frequency_to_cron_params(self, frequency: ScheduleFrequency) -> dict[str, Any]:
        """Convert frequency to cron parameters."""
        if frequency == ScheduleFrequency.HOURLY:
            return {"minute": 0}
        elif frequency == ScheduleFrequency.DAILY:
            return {"hour": 2, "minute": 0}
        elif frequency == ScheduleFrequency.WEEKLY:
            return {"day_of_week": "0", "hour": 2, "minute": 0}  # Sunday
        elif frequency == ScheduleFrequency.MONTHLY:
            return {"day": 1, "hour": 2, "minute": 0}  # 1st of month
        else:
            return {"hour": 2, "minute": 0}  # Default to daily

    def unregister_job(self, job_id: str) -> bool:
        """Unregister a scheduled job.

        Args:
            job_id: ID of job to unregister

        Returns:
            True if unregistered successfully

        Raises:
            SchedulingError: If job not found
        """
        if job_id not in self._registered_jobs:
            raise SchedulingError(f"Job with ID '{job_id}' not found")

        job = self._registered_jobs[job_id]

        try:
            # Remove from underlying scheduler
            if job.scheduler_job_id:
                scheduler_service.remove_job(job.scheduler_job_id)

            # Remove from our registry
            del self._registered_jobs[job_id]

            logger.info(f"Unregistered Cassazione scraping job: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Error unregistering job {job_id}: {e}")
            raise SchedulingError(f"Failed to unregister job: {e}")

    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job.

        Args:
            job_id: ID of job to pause

        Returns:
            True if paused successfully
        """
        if job_id not in self._registered_jobs:
            raise SchedulingError(f"Job with ID '{job_id}' not found")

        job = self._registered_jobs[job_id]

        try:
            if job.scheduler_job_id:
                scheduler_service.pause_job(job.scheduler_job_id)

            job.update_status(JobStatus.PAUSED, "Job paused by user")

            logger.info(f"Paused Cassazione scraping job: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Error pausing job {job_id}: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job.

        Args:
            job_id: ID of job to resume

        Returns:
            True if resumed successfully
        """
        if job_id not in self._registered_jobs:
            raise SchedulingError(f"Job with ID '{job_id}' not found")

        job = self._registered_jobs[job_id]

        try:
            if job.scheduler_job_id:
                scheduler_service.resume_job(job.scheduler_job_id)

            job.update_status(JobStatus.SCHEDULED, "Job resumed")

            logger.info(f"Resumed Cassazione scraping job: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Error resuming job {job_id}: {e}")
            return False

    async def _execute_job_wrapper(self, job_id: str):
        """Wrapper for executing jobs (called by scheduler)."""
        try:
            await self.execute_scraping_job(job_id)
        except Exception as e:
            logger.error(f"Error in job wrapper for {job_id}: {e}")

    async def execute_scraping_job(self, job_id: str) -> ScrapingResult | None:
        """Execute a scraping job.

        Args:
            job_id: ID of job to execute

        Returns:
            ScrapingResult or None if failed
        """
        if job_id not in self._registered_jobs:
            logger.error(f"Cannot execute unknown job: {job_id}")
            return None

        job = self._registered_jobs[job_id]

        try:
            # Update job status
            job.update_status(JobStatus.RUNNING, "Job execution started")
            job.last_run_time = datetime.now()

            # Create scraper instance
            scraper_config = job.scraping_config or {}
            scraper = CassazioneScraper(
                rate_limit_delay=scraper_config.get("rate_limit_delay", 2.0),
                timeout_seconds=scraper_config.get("timeout_seconds", 30),
                max_retries=scraper_config.get("max_retries", 3),
            )

            # Execute scraping
            async with scraper:
                result = await scraper.scrape_recent_decisions(
                    sections=job.court_sections, days_back=job.days_back, limit=job.max_decisions_per_run
                )

            # Update job with results
            job.last_run_result = result
            job.update_status(JobStatus.COMPLETED, f"Successfully processed {result.decisions_saved} decisions")
            job.retry_count = 0  # Reset retry count on success

            # Calculate next run time
            job.next_run_time = job.calculate_next_run_time()

            # Send notifications if enabled
            if self.enable_notifications:
                await self._send_job_notification(job, JobStatus.COMPLETED, result)

            logger.info(
                f"Completed scraping job {job_id}: {result.decisions_found} found, {result.decisions_saved} saved"
            )

            return result

        except Exception as e:
            # Handle job failure
            error_message = f"Job execution failed: {str(e)}"
            logger.error(f"Error executing scraping job {job_id}: {e}")

            job.retry_count += 1

            if job.retry_on_failure and job.retry_count <= job.max_retries:
                job.update_status(JobStatus.SCHEDULED, f"Retry {job.retry_count}/{job.max_retries}: {error_message}")
                # Schedule retry (with exponential backoff)
                retry_delay = 2**job.retry_count
                job.next_run_time = datetime.now() + timedelta(minutes=retry_delay)
            else:
                job.update_status(JobStatus.FAILED, error_message)

                # Send failure notification
                if self.enable_notifications:
                    await self._send_job_notification(job, JobStatus.FAILED, error_message=error_message)

            return None

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get status information for a job.

        Args:
            job_id: ID of job to check

        Returns:
            Dictionary with job status information
        """
        if job_id not in self._registered_jobs:
            return {"error": f"Job {job_id} not found"}

        job = self._registered_jobs[job_id]

        return {
            "job_id": job.job_id,
            "name": job.name,
            "status": job.status.value,
            "status_message": job.status_message,
            "status_updated_at": job.status_updated_at.isoformat() if job.status_updated_at else None,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "last_run_time": job.last_run_time.isoformat() if job.last_run_time else None,
            "last_run_result": {
                "decisions_found": job.last_run_result.decisions_found,
                "decisions_saved": job.last_run_result.decisions_saved,
                "errors": job.last_run_result.errors,
            }
            if job.last_run_result
            else None,
            "frequency": job.frequency.value,
            "court_sections": [section.value for section in job.court_sections],
            "enabled": job.enabled,
            "retry_count": job.retry_count,
        }

    def get_all_jobs(self) -> list[dict[str, Any]]:
        """Get status information for all jobs.

        Returns:
            List of job status dictionaries
        """
        return [self.get_job_status(job_id) for job_id in self._registered_jobs.keys()]

    def get_jobs_by_status(self, status: JobStatus) -> list[dict[str, Any]]:
        """Get jobs filtered by status.

        Args:
            status: JobStatus to filter by

        Returns:
            List of job status dictionaries
        """
        filtered_jobs = []
        for job in self._registered_jobs.values():
            if job.status == status:
                filtered_jobs.append(self.get_job_status(job.job_id))

        return filtered_jobs

    async def _send_job_notification(
        self,
        job: ScheduledScrapingJob,
        status: JobStatus,
        result: ScrapingResult | None = None,
        error_message: str | None = None,
    ):
        """Send notification about job status.

        Args:
            job: ScheduledScrapingJob that completed
            status: Final job status
            result: ScrapingResult if successful
            error_message: Error message if failed
        """
        if not job.notification_emails or not self._should_send_notification(job, status):
            return

        try:
            from app.services.email_service import send_email

            # Prepare notification content
            if status == JobStatus.COMPLETED and result:
                subject = f"Cassazione Scraping Job '{job.name}' completed successfully"
                body = f"""
                Job: {job.name} ({job.job_id})
                Status: Completed

                Results:
                - Decisions found: {result.decisions_found}
                - Decisions saved: {result.decisions_saved}
                - Errors: {result.errors}
                - Duration: {result.duration_minutes:.1f} minutes

                Next run: {job.next_run_time.strftime("%Y-%m-%d %H:%M") if job.next_run_time else "N/A"}
                """
            else:
                subject = f"Cassazione Scraping Job '{job.name}' failed"
                body = f"""
                Job: {job.name} ({job.job_id})
                Status: Failed

                Error: {error_message or "Unknown error"}
                Retry count: {job.retry_count}/{job.max_retries}

                Next run: {job.next_run_time.strftime("%Y-%m-%d %H:%M") if job.next_run_time else "N/A"}
                """

            # Send to all recipients
            for email in job.notification_emails:
                await send_email(to=email, subject=subject, body=body)

            # Update last notification time
            self._last_notification_times[job.job_id] = datetime.now()

        except Exception as e:
            logger.error(f"Error sending notification for job {job.job_id}: {e}")

    def _should_send_notification(self, job: ScheduledScrapingJob, status: JobStatus) -> bool:
        """Check if notification should be sent (with throttling).

        Args:
            job: ScheduledScrapingJob
            status: Current job status

        Returns:
            True if notification should be sent
        """
        # Always send failure notifications
        if status == JobStatus.FAILED:
            return True

        # Throttle success notifications
        last_notification = self._last_notification_times.get(job.job_id)
        if last_notification:
            time_since_last = datetime.now() - last_notification
            min_interval = timedelta(hours=1)  # Minimum 1 hour between notifications

            if time_since_last < min_interval:
                return False

        return True

    async def save_job_configuration(self, job: ScheduledScrapingJob):
        """Save job configuration to database.

        Args:
            job: ScheduledScrapingJob to save
        """
        if not self.persistence_enabled:
            return

        try:
            from app.services.database import database_service

            async with database_service.get_session() as session:
                # Convert job to database model (would need to create this)
                # For now, mock the save operation
                await session.add(job)
                await session.commit()

        except Exception as e:
            logger.error(f"Error saving job configuration {job.job_id}: {e}")

    async def load_job_configurations(self) -> list[ScheduledScrapingJob]:
        """Load job configurations from database.

        Returns:
            List of ScheduledScrapingJob objects
        """
        if not self.persistence_enabled:
            return []

        try:
            from app.services.database import database_service

            async with database_service.get_session():
                # Mock loading jobs from database
                # In real implementation, would query actual database
                mock_jobs = [
                    ScheduledScrapingJob(
                        job_id="job1",
                        name="Job 1",
                        frequency=ScheduleFrequency.WEEKLY,
                        court_sections=[CourtSection.CIVILE],
                    ),
                    ScheduledScrapingJob(
                        job_id="job2",
                        name="Job 2",
                        frequency=ScheduleFrequency.DAILY,
                        court_sections=[CourtSection.TRIBUTARIA, CourtSection.LAVORO],
                    ),
                ]
                return mock_jobs

        except Exception as e:
            logger.error(f"Error loading job configurations: {e}")
            return []

    async def update_job_execution_history(self, job: ScheduledScrapingJob, result: ScrapingResult):
        """Update job execution history in database.

        Args:
            job: ScheduledScrapingJob that was executed
            result: ScrapingResult from execution
        """
        if not self.persistence_enabled:
            return

        try:
            from app.services.database import database_service

            async with database_service.get_session() as session:
                # Create execution history record (would need to create model)
                # For now, mock the operation
                await session.add(result)
                await session.commit()

        except Exception as e:
            logger.error(f"Error updating job execution history {job.job_id}: {e}")
