"""
Scheduler Service for Automated Tasks

This service handles scheduling of automated tasks including metrics reporting,
system maintenance, and other periodic operations.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
)

from app.core.config import settings
from app.core.logging import logger
from app.services.email_service import email_service
from app.services.metrics_service import Environment


class ScheduleInterval(str, Enum):
    """Schedule interval enumeration."""

    MINUTES_30 = "30_minutes"
    HOURLY = "hourly"
    EVERY_4_HOURS = "4_hours"
    EVERY_12_HOURS = "12_hours"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class ScheduledTask:
    """Scheduled task configuration."""

    name: str
    interval: ScheduleInterval
    function: Callable
    args: tuple = ()
    kwargs: dict = None
    enabled: bool = True
    run_immediately: bool = False  # Run task immediately on scheduler startup
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class SchedulerService:
    """Scheduler service for automated task execution."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self._task_handle: Optional[asyncio.Task] = None

    def add_task(self, task: ScheduledTask) -> None:
        """Add a scheduled task."""
        if task.kwargs is None:
            task.kwargs = {}

        # Calculate next run time
        task.next_run = self._calculate_next_run(task.interval)

        self.tasks[task.name] = task
        self.logger.info(f"Added scheduled task: {task.name} ({task.interval.value})")

    def remove_task(self, task_name: str) -> bool:
        """Remove a scheduled task."""
        if task_name in self.tasks:
            del self.tasks[task_name]
            self.logger.info(f"Removed scheduled task: {task_name}")
            return True
        return False

    def enable_task(self, task_name: str) -> bool:
        """Enable a scheduled task."""
        if task_name in self.tasks:
            self.tasks[task_name].enabled = True
            self.logger.info(f"Enabled scheduled task: {task_name}")
            return True
        return False

    def disable_task(self, task_name: str) -> bool:
        """Disable a scheduled task."""
        if task_name in self.tasks:
            self.tasks[task_name].enabled = False
            self.logger.info(f"Disabled scheduled task: {task_name}")
            return True
        return False

    async def start(self) -> None:
        """Start the scheduler."""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return

        self.running = True
        self._task_handle = asyncio.create_task(self._scheduler_loop())
        self.logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self.running:
            return

        self.running = False

        if self._task_handle:
            self._task_handle.cancel()
            try:
                await self._task_handle
            except asyncio.CancelledError:
                pass

        self.logger.info("Scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        self.logger.info("Scheduler loop started")

        while self.running:
            try:
                current_time = datetime.now(timezone.utc)

                # Check each task
                for task_name, task in self.tasks.items():
                    if not task.enabled:
                        continue

                    if current_time >= task.next_run:
                        await self._execute_task(task)

                # Sleep for 60 seconds before checking again
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Continue after error

        self.logger.info("Scheduler loop ended")

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a scheduled task."""
        try:
            self.logger.info(f"Executing scheduled task: {task.name}")

            # Execute the task
            if asyncio.iscoroutinefunction(task.function):
                await task.function(*task.args, **task.kwargs)
            else:
                task.function(*task.args, **task.kwargs)

            # Update task timing
            task.last_run = datetime.now(timezone.utc)
            task.next_run = self._calculate_next_run(task.interval, task.last_run)

            self.logger.info(f"Completed scheduled task: {task.name}. Next run: {task.next_run}")

        except Exception as e:
            self.logger.error(f"Error executing scheduled task {task.name}: {e}")

            # Still update next run time even if task failed
            task.last_run = datetime.now(timezone.utc)
            task.next_run = self._calculate_next_run(task.interval, task.last_run)

    def _calculate_next_run(self, interval: ScheduleInterval, from_time: Optional[datetime] = None) -> datetime:
        """Calculate next run time based on interval."""
        base_time = from_time or datetime.now(timezone.utc)

        if interval == ScheduleInterval.MINUTES_30:
            return base_time + timedelta(minutes=30)
        elif interval == ScheduleInterval.HOURLY:
            return base_time + timedelta(hours=1)
        elif interval == ScheduleInterval.EVERY_4_HOURS:
            return base_time + timedelta(hours=4)
        elif interval == ScheduleInterval.EVERY_12_HOURS:
            return base_time + timedelta(hours=12)
        elif interval == ScheduleInterval.DAILY:
            return base_time + timedelta(days=1)
        elif interval == ScheduleInterval.WEEKLY:
            return base_time + timedelta(weeks=1)
        else:
            # Default to daily
            return base_time + timedelta(days=1)

    def get_task_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all scheduled tasks."""
        status = {}
        current_time = datetime.now(timezone.utc)

        for task_name, task in self.tasks.items():
            status[task_name] = {
                "enabled": task.enabled,
                "interval": task.interval.value,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": task.next_run.isoformat() if task.next_run else None,
                "overdue": current_time > task.next_run if task.next_run else False,
            }

        return status

    async def run_task_now(self, task_name: str) -> bool:
        """Manually execute a task immediately."""
        if task_name not in self.tasks:
            self.logger.error(f"Task not found: {task_name}")
            return False

        task = self.tasks[task_name]
        await self._execute_task(task)
        return True


# Global scheduler service instance
scheduler_service = SchedulerService()


def get_metrics_report_recipients() -> List[str]:
    """Get list of email recipients for metrics reports from environment variables."""
    recipients = []

    # Primary recipients list
    if hasattr(settings, "METRICS_REPORT_RECIPIENTS") and settings.METRICS_REPORT_RECIPIENTS:
        recipients.extend([email.strip() for email in settings.METRICS_REPORT_RECIPIENTS.split(",") if email.strip()])

    # Role-based recipients
    if hasattr(settings, "METRICS_REPORT_RECIPIENTS_ADMIN") and settings.METRICS_REPORT_RECIPIENTS_ADMIN:
        recipients.extend(
            [email.strip() for email in settings.METRICS_REPORT_RECIPIENTS_ADMIN.split(",") if email.strip()]
        )

    if hasattr(settings, "METRICS_REPORT_RECIPIENTS_TECH") and settings.METRICS_REPORT_RECIPIENTS_TECH:
        recipients.extend(
            [email.strip() for email in settings.METRICS_REPORT_RECIPIENTS_TECH.split(",") if email.strip()]
        )

    if hasattr(settings, "METRICS_REPORT_RECIPIENTS_BUSINESS") and settings.METRICS_REPORT_RECIPIENTS_BUSINESS:
        recipients.extend(
            [email.strip() for email in settings.METRICS_REPORT_RECIPIENTS_BUSINESS.split(",") if email.strip()]
        )

    # Remove duplicates while preserving order
    unique_recipients = []
    for email in recipients:
        if email not in unique_recipients:
            unique_recipients.append(email)

    # Fallback to default if no recipients configured
    if not unique_recipients:
        unique_recipients = ["admin@pratikoai.com"]
        logger.warning("No metrics report recipients configured, using default: admin@pratikoai.com")

    return unique_recipients


async def send_metrics_report_task() -> None:
    """Scheduled task to send metrics reports."""
    try:
        # Get recipient emails from environment configuration
        recipient_emails = get_metrics_report_recipients()

        # Define environments to monitor
        environments = [Environment.DEVELOPMENT, Environment.QA, Environment.PREPROD, Environment.PRODUCTION]

        # Send the report
        success = await email_service.send_metrics_report(recipient_emails, environments)

        if success:
            logger.info(
                f"Metrics report sent successfully to {len(recipient_emails)} recipients: {', '.join(recipient_emails)}"
            )
        else:
            logger.error(f"Failed to send metrics report to some or all recipients: {', '.join(recipient_emails)}")

    except Exception as e:
        logger.error(f"Error in metrics report task: {e}")


async def collect_rss_feeds_task() -> None:
    """Scheduled task for RSS feed collection using database-driven ingestion.

    This task:
    - Reads all enabled feeds from feed_status table
    - Processes each feed with run_rss_ingestion()
    - Passes feed_type for source differentiation (news vs normativa)
    - Updates feed_status table with results
    - Logs comprehensive statistics
    """
    try:
        from datetime import (
            datetime,
            timezone,
        )

        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            create_async_engine,
        )
        from sqlalchemy.orm import sessionmaker

        from app.core.config import settings
        from app.ingest.rss_normativa import run_rss_ingestion
        from app.models.regulatory_documents import FeedStatus

        logger.info("rss_feed_collection_task_started")

        # Create async database session
        postgres_url = settings.POSTGRES_URL
        if postgres_url.startswith("postgresql://"):
            postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
        async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # Aggregate statistics
        aggregate_stats = {
            "feeds_processed": 0,
            "feeds_succeeded": 0,
            "feeds_failed": 0,
            "total_items": 0,
            "total_new_documents": 0,
            "total_skipped": 0,
            "total_failed": 0,
        }

        async with async_session_maker() as session:
            # Query all enabled feeds
            query = select(FeedStatus).where(FeedStatus.enabled == True)  # type: ignore[arg-type]
            result = await session.execute(query)
            feeds = result.scalars().all()

            if not feeds:
                logger.warning("rss_feed_collection_no_enabled_feeds")
                await engine.dispose()
                return

            logger.info("rss_feed_collection_processing_feeds", feed_count=len(feeds))

            # Process each feed
            for feed in feeds:
                try:
                    logger.info(
                        "rss_feed_collection_processing_feed",
                        feed_id=feed.id,
                        source=feed.source,
                        feed_type=feed.feed_type,
                        feed_url=feed.feed_url,
                    )

                    # Run database-driven ingestion
                    stats = await run_rss_ingestion(
                        session=session,
                        feed_url=feed.feed_url,
                        feed_type=feed.feed_type,
                        max_items=None,  # Process all items
                    )

                    # Update aggregate statistics
                    aggregate_stats["feeds_processed"] += 1
                    if stats.get("status") == "success":
                        aggregate_stats["feeds_succeeded"] += 1
                    else:
                        aggregate_stats["feeds_failed"] += 1

                    aggregate_stats["total_items"] += stats.get("total_items", 0)
                    aggregate_stats["total_new_documents"] += stats.get("new_documents", 0)
                    aggregate_stats["total_skipped"] += stats.get("skipped_existing", 0)
                    aggregate_stats["total_failed"] += stats.get("failed", 0)

                    # Update feed_status
                    feed.items_found = stats.get("total_items", 0)
                    feed.last_success = datetime.now(timezone.utc)
                    feed.consecutive_errors = 0
                    feed.status = "healthy"
                    session.add(feed)
                    await session.commit()

                    logger.info(
                        "rss_feed_collection_feed_completed",
                        feed_id=feed.id,
                        source=feed.source,
                        total_items=stats.get("total_items", 0),
                        new_documents=stats.get("new_documents", 0),
                        skipped=stats.get("skipped_existing", 0),
                    )

                except Exception as e:
                    logger.error(
                        "rss_feed_collection_feed_failed",
                        feed_id=feed.id,
                        source=feed.source,
                        error=str(e),
                        exc_info=True,
                    )
                    aggregate_stats["feeds_failed"] += 1

                    # Update feed_status with error
                    feed.consecutive_errors += 1
                    feed.errors += 1
                    feed.last_error = str(e)[:500]
                    feed.status = "error"
                    session.add(feed)
                    await session.commit()

        # Dispose engine
        await engine.dispose()

        # Log final summary
        logger.info(
            "rss_feed_collection_task_completed",
            feeds_processed=aggregate_stats["feeds_processed"],
            feeds_succeeded=aggregate_stats["feeds_succeeded"],
            feeds_failed=aggregate_stats["feeds_failed"],
            total_items=aggregate_stats["total_items"],
            new_documents=aggregate_stats["total_new_documents"],
            skipped_existing=aggregate_stats["total_skipped"],
            failed_downloads=aggregate_stats["total_failed"],
        )

    except Exception as e:
        logger.error("rss_feed_collection_task_failed", error=str(e), exc_info=True)


def setup_default_tasks() -> None:
    """Setup default scheduled tasks."""

    # Add 12-hour metrics report task
    metrics_report_task = ScheduledTask(
        name="metrics_report_12h",
        interval=ScheduleInterval.EVERY_12_HOURS,
        function=send_metrics_report_task,
        enabled=True,
    )
    scheduler_service.add_task(metrics_report_task)

    # Add RSS feed collection task (every 4 hours) - Database-driven ingestion
    # run_immediately=True ensures feeds are collected right after app startup
    rss_feeds_task = ScheduledTask(
        name="rss_feeds_4h",
        interval=ScheduleInterval.EVERY_4_HOURS,
        function=collect_rss_feeds_task,
        enabled=True,
        run_immediately=True,  # Collect feeds immediately on startup
    )
    scheduler_service.add_task(rss_feeds_task)

    logger.info("Default scheduled tasks configured (metrics reports + RSS feed collection)")


async def start_scheduler() -> None:
    """Start the scheduler with default tasks."""
    setup_default_tasks()
    await scheduler_service.start()

    # Run tasks marked with run_immediately=True
    immediate_tasks = [task for task in scheduler_service.tasks.values() if task.run_immediately and task.enabled]
    if immediate_tasks:
        logger.info(
            f"Running {len(immediate_tasks)} immediate task(s) on startup: {[t.name for t in immediate_tasks]}"
        )
        for task in immediate_tasks:
            try:
                await scheduler_service._execute_task(task)
            except Exception as e:
                logger.error(f"Failed to run immediate task {task.name} on startup: {e}")


async def stop_scheduler() -> None:
    """Stop the scheduler."""
    await scheduler_service.stop()
