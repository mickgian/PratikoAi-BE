"""Scheduler Service for Automated Tasks

This service handles scheduling of automated tasks including metrics reporting,
system maintenance, and other periodic operations.
"""

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import (
    UTC,
    datetime,
    timedelta,
    timezone,
)
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
)
from zoneinfo import ZoneInfo

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
    kwargs: dict[Any, Any] | None = None
    enabled: bool = True
    run_immediately: bool = False  # Run task immediately on scheduler startup
    last_run: datetime | None = None
    next_run: datetime | None = None
    target_time: str | None = None  # Time of day to run (e.g., "06:00" for 6 AM Europe/Rome)
    timezone_name: str = "Europe/Rome"  # Timezone for target_time


class SchedulerService:
    """Scheduler service for automated task execution."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tasks: dict[str, ScheduledTask] = {}
        self.running = False
        self._task_handle: asyncio.Task | None = None

    def add_task(self, task: ScheduledTask) -> None:
        """Add a scheduled task."""
        if task.kwargs is None:
            task.kwargs = {}

        # Calculate next run time - use time-of-day if target_time is set
        if task.target_time:
            task.next_run = self._calculate_next_run_at_time(task.target_time, task.timezone_name)
            self.logger.info(
                f"Added scheduled task: {task.name} (daily at {task.target_time} {task.timezone_name}, "
                f"next run: {task.next_run.astimezone(ZoneInfo(task.timezone_name)).strftime('%Y-%m-%d %H:%M %Z')})"
            )
        else:
            task.next_run = self._calculate_next_run(task.interval)
            self.logger.info(f"Added scheduled task: {task.name} ({task.interval.value})")

        self.tasks[task.name] = task

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
            with contextlib.suppress(asyncio.CancelledError):
                await self._task_handle

        self.logger.info("Scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        self.logger.info("Scheduler loop started")

        while self.running:
            try:
                current_time = datetime.now(UTC)

                # Check each task
                for _task_name, task in self.tasks.items():
                    if not task.enabled:
                        continue

                    if task.next_run is not None and current_time >= task.next_run:
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
            kwargs = task.kwargs or {}
            if asyncio.iscoroutinefunction(task.function):
                await task.function(*task.args, **kwargs)
            else:
                task.function(*task.args, **kwargs)

            # Update task timing - use time-of-day if target_time is set
            task.last_run = datetime.now(UTC)
            if task.target_time:
                task.next_run = self._calculate_next_run_at_time(task.target_time, task.timezone_name)
            else:
                task.next_run = self._calculate_next_run(task.interval, task.last_run)

            self.logger.info(f"Completed scheduled task: {task.name}. Next run: {task.next_run}")

        except Exception as e:
            self.logger.error(f"Error executing scheduled task {task.name}: {e}")

            # Still update next run time even if task failed
            task.last_run = datetime.now(UTC)
            if task.target_time:
                task.next_run = self._calculate_next_run_at_time(task.target_time, task.timezone_name)
            else:
                task.next_run = self._calculate_next_run(task.interval, task.last_run)

    def _calculate_next_run(self, interval: ScheduleInterval, from_time: datetime | None = None) -> datetime:
        """Calculate next run time based on interval."""
        base_time = from_time or datetime.now(UTC)

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
        # Default to daily
        return base_time + timedelta(days=1)  # type: ignore[unreachable]

    def _calculate_next_run_at_time(self, target_time: str, timezone_name: str = "Europe/Rome") -> datetime:
        """Calculate next occurrence of a specific time of day.

        Args:
            target_time: Time in HH:MM format (e.g., "06:00" for 6 AM)
            timezone_name: Timezone name (e.g., "Europe/Rome")

        Returns:
            Next datetime in UTC when the target time will occur
        """
        tz = ZoneInfo(timezone_name)
        now = datetime.now(tz)

        # Parse target time
        hour, minute = map(int, target_time.split(":"))

        # Create target datetime for today
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If target time has already passed today, schedule for tomorrow
        if target <= now:
            target += timedelta(days=1)

        # Convert to UTC for storage
        return target.astimezone(UTC)

    def get_task_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all scheduled tasks."""
        status = {}
        current_time = datetime.now(UTC)

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


def get_metrics_report_recipients() -> list[str]:
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
        environments = [Environment.DEVELOPMENT, Environment.QA, Environment.PRODUCTION]

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


async def send_daily_ingestion_report_task() -> None:
    """Scheduled task to send daily ingestion collection email report.

    This task is called by the scheduler service daily at the configured time.
    DEV-BE-70: Daily Ingestion Collection Email Report
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.services.ingestion_report_service import IngestionReportService

    # Check if report is enabled
    if not getattr(settings, "INGESTION_REPORT_ENABLED", True):
        logger.info("Daily ingestion report is disabled via INGESTION_REPORT_ENABLED")
        return

    # Get recipients from settings
    recipients_str = getattr(settings, "INGESTION_REPORT_RECIPIENTS", "")
    if not recipients_str:
        logger.warning("INGESTION_REPORT_RECIPIENTS not configured, skipping daily ingestion report")
        return

    recipients = [email.strip() for email in recipients_str.split(",") if email.strip()]
    if not recipients:
        logger.warning("No valid recipients configured for daily ingestion report")
        return

    try:
        logger.info(f"Sending daily ingestion report to {len(recipients)} recipients")

        # Create async database session
        postgres_url = settings.POSTGRES_URL
        if postgres_url.startswith("postgresql://"):
            postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
        async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session_maker() as session:
            service = IngestionReportService(session)
            success = await service.send_daily_report_email(recipients)

            if success:
                logger.info("Daily ingestion report sent successfully")
            else:
                logger.error("Failed to send daily ingestion report")

        await engine.dispose()

    except Exception as e:
        logger.error(f"Error in daily ingestion report task: {e}", exc_info=True)


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
            query = select(FeedStatus).where(FeedStatus.enabled == True)  # noqa: E712
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
                    feed.last_success = datetime.now(UTC)
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


async def scrape_gazzetta_task() -> None:
    """Scheduled task for Gazzetta Ufficiale scraping.

    This task is called by the scheduler service daily at the configured time.
    Scrapes recent documents from the Italian Official Gazette.
    """
    try:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        from app.services.scrapers.gazzetta_scraper import scrape_gazzetta_daily_task

        logger.info("gazzetta_scraping_task_started")

        # Create async database session
        postgres_url = settings.POSTGRES_URL
        if postgres_url.startswith("postgresql://"):
            postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
        async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session_maker() as session:
            result = await scrape_gazzetta_daily_task(db_session=session)

            logger.info(
                "gazzetta_scraping_task_completed",
                documents_found=result.documents_found,
                documents_saved=result.documents_saved,
                errors=result.errors,
            )

        await engine.dispose()

    except Exception as e:
        logger.error("gazzetta_scraping_task_failed", error=str(e), exc_info=True)


async def scrape_cassazione_task() -> None:
    """Scheduled task for Cassazione (Supreme Court) scraping.

    This task is called by the scheduler service daily at the configured time.
    Scrapes recent court decisions focusing on Tax and Labor sections.
    """
    try:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        from app.services.scrapers.cassazione_scraper import scrape_cassazione_daily_task

        logger.info("cassazione_scraping_task_started")

        # Create async database session
        postgres_url = settings.POSTGRES_URL
        if postgres_url.startswith("postgresql://"):
            postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
        async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session_maker() as session:
            result = await scrape_cassazione_daily_task(db_session=session)

            logger.info(
                "cassazione_scraping_task_completed",
                decisions_found=result.decisions_found,
                decisions_saved=result.decisions_saved,
                errors=result.errors,
            )

        await engine.dispose()

    except Exception as e:
        logger.error("cassazione_scraping_task_failed", error=str(e), exc_info=True)


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

    # Add RSS feed collection task - daily at configured time (default 01:00 Europe/Rome)
    # run_immediately=True ensures feeds are collected right after app startup
    rss_collection_time = getattr(settings, "RSS_COLLECTION_TIME", "01:00")
    rss_feeds_task = ScheduledTask(
        name="rss_feeds_daily",
        interval=ScheduleInterval.DAILY,
        function=collect_rss_feeds_task,
        enabled=True,
        run_immediately=True,  # Collect feeds immediately on startup
        target_time=rss_collection_time,  # Run daily at configured time
    )
    scheduler_service.add_task(rss_feeds_task)

    # Add Gazzetta Ufficiale scraper task - daily at same time as RSS (01:00 Europe/Rome)
    # Scrapes Italian Official Gazette for tax and labor laws
    gazzetta_scraper_task = ScheduledTask(
        name="gazzetta_scraper_daily",
        interval=ScheduleInterval.DAILY,
        function=scrape_gazzetta_task,
        enabled=True,
        run_immediately=False,  # Don't scrape external site on every startup
        target_time=rss_collection_time,  # Same time as RSS collection
    )
    scheduler_service.add_task(gazzetta_scraper_task)

    # Add Cassazione (Supreme Court) scraper task - daily at same time as RSS (01:00 Europe/Rome)
    # Scrapes court decisions for Tax (Tributaria) and Labor (Lavoro) sections
    cassazione_scraper_task = ScheduledTask(
        name="cassazione_scraper_daily",
        interval=ScheduleInterval.DAILY,
        function=scrape_cassazione_task,
        enabled=True,
        run_immediately=False,  # Don't scrape external site on every startup
        target_time=rss_collection_time,  # Same time as RSS collection
    )
    scheduler_service.add_task(cassazione_scraper_task)

    # Add daily ingestion report task (DEV-BE-70)
    # Sends daily email with RSS + scraper metrics, alerts, WoW comparison
    # Default time: 06:00 Europe/Rome (configured via INGESTION_REPORT_TIME)
    ingestion_report_enabled = getattr(settings, "INGESTION_REPORT_ENABLED", True)
    ingestion_report_time = getattr(settings, "INGESTION_REPORT_TIME", "06:00")
    ingestion_report_task = ScheduledTask(
        name="daily_ingestion_report",
        interval=ScheduleInterval.DAILY,
        function=send_daily_ingestion_report_task,
        enabled=ingestion_report_enabled,
        target_time=ingestion_report_time,  # Run daily at configured time
    )
    scheduler_service.add_task(ingestion_report_task)

    logger.info(
        f"Default scheduled tasks configured (metrics reports + RSS feeds + Gazzetta scraper + Cassazione scraper + daily ingestion report [enabled={ingestion_report_enabled}])"
    )


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
