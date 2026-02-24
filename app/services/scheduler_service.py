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
    # DEV-242: New fields for non-blocking startup
    timeout_seconds: float | None = None  # Task execution timeout (None = no timeout)
    run_in_thread: bool = False  # Run sync tasks in thread pool to avoid blocking


class SchedulerService:
    """Scheduler service for automated task execution."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tasks: dict[str, ScheduledTask] = {}
        self.running = False
        self._task_handle: asyncio.Task | None = None
        # DEV-242: Track background tasks for graceful shutdown
        self._background_tasks: set[asyncio.Task] = set()

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
        """Start the scheduler.

        DEV-242: Immediate tasks now run in background (non-blocking).
        This ensures FastAPI lifespan startup completes quickly.
        """
        if self.running:
            self.logger.warning("Scheduler is already running")
            return

        self.running = True
        self._task_handle = asyncio.create_task(self._scheduler_loop())
        self.logger.info("Scheduler started")

        # DEV-242: Run immediate tasks in background (non-blocking)
        immediate_tasks = [task for task in self.tasks.values() if task.run_immediately and task.enabled]
        if immediate_tasks:
            self.logger.info(
                f"Scheduling {len(immediate_tasks)} immediate task(s) in background: "
                f"{[t.name for t in immediate_tasks]}"
            )
            for task in immediate_tasks:
                bg_task = asyncio.create_task(
                    self._execute_task_with_cleanup(task),
                    name=f"immediate_{task.name}",
                )
                self._background_tasks.add(bg_task)

    async def _execute_task_with_cleanup(self, task: ScheduledTask) -> None:
        """Execute a task and remove from background tasks when done.

        DEV-242: Wrapper for background task execution with cleanup.
        """
        try:
            await self._execute_task(task)
        finally:
            # Find and remove this task from background tasks
            current_task = asyncio.current_task()
            if current_task in self._background_tasks:
                self._background_tasks.discard(current_task)

    async def stop(self) -> None:
        """Stop the scheduler.

        DEV-242: Also cancels any running background tasks gracefully.
        """
        if not self.running:
            return

        self.running = False

        # DEV-242: Cancel all background tasks
        if self._background_tasks:
            self.logger.info(f"Cancelling {len(self._background_tasks)} background task(s)")
            for bg_task in self._background_tasks:
                bg_task.cancel()

            # Wait for all background tasks to complete (with cancellation)
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks.clear()

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
        """Execute a scheduled task.

        DEV-242: Now supports timeout and thread pool execution.
        """
        try:
            self.logger.info(f"Executing scheduled task: {task.name}")

            # Execute the task
            kwargs = task.kwargs or {}

            # DEV-242: Build the coroutine or wrap sync function
            if asyncio.iscoroutinefunction(task.function):
                coro = task.function(*task.args, **kwargs)
            elif task.run_in_thread:
                # Run sync function in thread pool to avoid blocking event loop
                coro = asyncio.to_thread(task.function, *task.args, **kwargs)
            else:
                # Run sync function directly (legacy behavior)
                task.function(*task.args, **kwargs)
                coro = None

            # DEV-242: Execute with optional timeout
            if coro is not None:
                if task.timeout_seconds is not None:
                    try:
                        await asyncio.wait_for(coro, timeout=task.timeout_seconds)
                    except TimeoutError:
                        self.logger.warning(f"Task {task.name} timed out after {task.timeout_seconds}s")
                        raise  # Re-raise to trigger error handling
                else:
                    await coro

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
                    # DEV-247: Track filtered items for daily report
                    feed.items_filtered = stats.get("skipped_filtered", 0)
                    filtered_samples = stats.get("filtered_samples", [])
                    if filtered_samples:
                        feed.filtered_samples = {"titles": filtered_samples}
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


async def scrape_ader_task() -> None:
    """Scheduled task for AdER (Agenzia Entrate-Riscossione) scraping.

    DEV-242 Phase 38: Recurring ingestion for AdER to capture critical content
    like rottamazione rules, 5-day grace period info, and interest rates.

    This task is called by the scheduler service daily at the configured time.
    Scrapes news and official communications from the AdER portal.
    """
    try:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        from app.services.scrapers.ader_scraper import scrape_ader_daily_task

        logger.info("ader_scraping_task_started")

        # Create async database session
        postgres_url = settings.POSTGRES_URL
        if postgres_url.startswith("postgresql://"):
            postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
        async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session_maker() as session:
            result = await scrape_ader_daily_task(db_session=session)

            logger.info(
                "ader_scraping_task_completed",
                documents_found=result.documents_found,
                documents_saved=result.documents_saved,
                errors=result.errors,
            )

        await engine.dispose()

    except Exception as e:
        logger.error("ader_scraping_task_failed", error=str(e), exc_info=True)


async def send_daily_cost_report_task() -> None:
    """Scheduled task to send daily cost report email.

    DEV-246: Daily Cost Spending Report by Environment and User.
    This task sends an email report with cost breakdown by environment, user,
    and third-party API usage.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.services.daily_cost_report_service import DailyCostReportService

    # Check if report is enabled
    if not getattr(settings, "DAILY_COST_REPORT_ENABLED", True):
        logger.info("Daily cost report is disabled via DAILY_COST_REPORT_ENABLED")
        return

    # Get recipients from settings
    recipients_str = getattr(settings, "DAILY_COST_REPORT_RECIPIENTS", "")
    if not recipients_str:
        logger.warning("DAILY_COST_REPORT_RECIPIENTS not configured, skipping daily cost report")
        return

    recipients = [email.strip() for email in recipients_str.split(",") if email.strip()]
    if not recipients:
        logger.warning("No valid recipients configured for daily cost report")
        return

    try:
        logger.info(f"Sending daily cost report to {len(recipients)} recipients")

        # Create async database session
        postgres_url = settings.POSTGRES_URL
        if postgres_url.startswith("postgresql://"):
            postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
        async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session_maker() as session:
            service = DailyCostReportService(session)
            report = await service.generate_report()
            success = await service.send_report(report, recipients)

            if success:
                logger.info(
                    "daily_cost_report_sent",
                    total_cost=report.total_cost_eur,
                    environments=len(report.environment_breakdown),
                    users=len(report.user_breakdown),
                    alerts=len(report.alerts),
                )
            else:
                logger.error("Failed to send daily cost report")

        await engine.dispose()

    except Exception as e:
        logger.error(f"Error in daily cost report task: {e}", exc_info=True)


async def send_daily_eval_report_task() -> None:
    """Scheduled task to run daily evaluation and send email report.

    DEV-252: Daily AI Agent Evaluation Report.
    Runs nightly evaluation suite and sends results via email.
    """
    from pathlib import Path

    logger.info("Starting daily evaluation report task")

    # Check if enabled
    if not getattr(settings, "EVAL_REPORT_ENABLED", True):
        logger.info("Daily evaluation report is disabled, skipping")
        return

    try:
        from evals.config import create_nightly_config
        from evals.runner import EvalRunner, load_test_cases

        # Run nightly evaluation
        config = create_nightly_config()
        runner = EvalRunner(config)

        # Load test cases
        test_dir = Path("evals/datasets/regression")
        if not test_dir.exists():
            logger.warning(f"Test directory {test_dir} not found, skipping eval report")
            return

        test_cases = load_test_cases(test_dir)
        if not test_cases:
            logger.info("No test cases found, skipping eval report")
            return

        # Run evaluation (this also sends the email via _send_email_report)
        result = await runner.run(test_cases)

        logger.info(f"Daily evaluation complete: {result.passed}/{result.total} passed ({result.pass_rate:.1%})")

    except Exception as e:
        logger.error(f"Error running daily evaluation report: {e}")


async def backfill_missing_embeddings_task() -> None:
    """Scheduled task to backfill missing embeddings for knowledge items and chunks.

    Queries for items/chunks with NULL embedding and generates embeddings
    using the OpenAI API in batches. This handles cases where embedding
    generation failed during initial ingestion (API errors, rate limits, etc.).

    Runs daily after ingestion to ensure all content is searchable.
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.embed import generate_embeddings_batch

    if not getattr(settings, "EMBEDDING_BACKFILL_ENABLED", True):
        logger.info("Embedding backfill is disabled via EMBEDDING_BACKFILL_ENABLED")
        return

    try:
        postgres_url = settings.POSTGRES_URL
        if postgres_url.startswith("postgresql://"):
            postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
        async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session_maker() as session:
            # --- Backfill items ---
            result = await session.execute(
                text(
                    "SELECT id, content FROM knowledge_items WHERE embedding IS NULL AND status = 'active' ORDER BY id"
                )
            )
            item_rows = result.fetchall()

            if item_rows:
                logger.info(f"Backfilling embeddings for {len(item_rows)} items")
                for i in range(0, len(item_rows), 20):
                    batch = item_rows[i : i + 20]
                    texts = [row[1] if row[1] else "" for row in batch]
                    embeddings = await generate_embeddings_batch(texts, batch_size=20)

                    for (item_id, _), emb in zip(batch, embeddings, strict=False):
                        if emb is not None:
                            await session.execute(
                                text("UPDATE knowledge_items SET embedding = :emb WHERE id = :id"),
                                {"emb": str(emb), "id": item_id},
                            )

                    await session.commit()
                    logger.info(
                        f"Backfilled items batch {i // 20 + 1} ({min(i + 20, len(item_rows))}/{len(item_rows)})"
                    )

            # --- Backfill chunks ---
            result = await session.execute(
                text("SELECT id, chunk_text FROM knowledge_chunks WHERE embedding IS NULL ORDER BY id")
            )
            chunk_rows = result.fetchall()

            if chunk_rows:
                logger.info(f"Backfilling embeddings for {len(chunk_rows)} chunks")
                for i in range(0, len(chunk_rows), 20):
                    batch = chunk_rows[i : i + 20]
                    texts = [row[1] if row[1] else "" for row in batch]
                    embeddings = await generate_embeddings_batch(texts, batch_size=20)

                    for (chunk_id, _), emb in zip(batch, embeddings, strict=False):
                        if emb is not None:
                            await session.execute(
                                text("UPDATE knowledge_chunks SET embedding = :emb WHERE id = :id"),
                                {"emb": str(emb), "id": chunk_id},
                            )

                    await session.commit()
                    logger.info(
                        f"Backfilled chunks batch {i // 20 + 1} ({min(i + 20, len(chunk_rows))}/{len(chunk_rows)})"
                    )

            if not item_rows and not chunk_rows:
                logger.info("No missing embeddings found, backfill not needed")

        await engine.dispose()

    except Exception as e:
        logger.error(f"Error in embedding backfill task: {e}", exc_info=True)


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
    # DEV-242: RSS feeds now run in background with timeout protection
    rss_feeds_task = ScheduledTask(
        name="rss_feeds_daily",
        interval=ScheduleInterval.DAILY,
        function=collect_rss_feeds_task,
        enabled=True,
        run_immediately=True,  # Collect feeds immediately on startup (non-blocking)
        target_time=rss_collection_time,  # Run daily at configured time
        timeout_seconds=1800,  # DEV-242: 30 min timeout to prevent infinite hangs
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

    # Add AdER (Agenzia Entrate-Riscossione) scraper task - daily at same time as RSS (01:00 Europe/Rome)
    # DEV-242 Phase 38: Scrapes rottamazione rules, payment deadlines, grace periods
    ader_scraper_task = ScheduledTask(
        name="ader_scraper_daily",
        interval=ScheduleInterval.DAILY,
        function=scrape_ader_task,
        enabled=True,
        run_immediately=False,  # Don't scrape external site on every startup
        target_time=rss_collection_time,  # Same time as RSS collection
    )
    scheduler_service.add_task(ader_scraper_task)

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

    # DEV-246: Add daily cost report task
    # Sends daily email with cost breakdown by environment, user, and third-party APIs
    # Default time: 07:00 Europe/Rome (configured via DAILY_COST_REPORT_TIME)
    cost_report_enabled = getattr(settings, "DAILY_COST_REPORT_ENABLED", True)
    cost_report_time = getattr(settings, "DAILY_COST_REPORT_TIME", "07:00")
    cost_report_task = ScheduledTask(
        name="daily_cost_report",
        interval=ScheduleInterval.DAILY,
        function=send_daily_cost_report_task,
        enabled=cost_report_enabled,
        target_time=cost_report_time,  # Run daily at configured time
    )
    scheduler_service.add_task(cost_report_task)

    # DEV-252: Add daily evaluation report task
    # Runs nightly evaluation suite and sends results via email
    # Default time: 06:00 Europe/Rome (configured via EVAL_REPORT_TIME)
    eval_report_enabled = getattr(settings, "EVAL_REPORT_ENABLED", True)
    eval_report_time = getattr(settings, "EVAL_REPORT_TIME", "06:00")
    eval_report_task = ScheduledTask(
        name="daily_eval_report",
        interval=ScheduleInterval.DAILY,
        function=send_daily_eval_report_task,
        enabled=eval_report_enabled,
        target_time=eval_report_time,  # Run daily at configured time
    )
    scheduler_service.add_task(eval_report_task)
    logger.info(f"Registered daily_eval_report task at {eval_report_time} (enabled={eval_report_enabled})")

    # Embedding backfill task: repairs missing embeddings from failed API calls
    # Runs daily at 03:00 Europe/Rome (after RSS ingestion at 01:00, before reports at 06:00)
    embedding_backfill_enabled = getattr(settings, "EMBEDDING_BACKFILL_ENABLED", True)
    embedding_backfill_time = getattr(settings, "EMBEDDING_BACKFILL_TIME", "03:00")
    embedding_backfill_task = ScheduledTask(
        name="embedding_backfill_daily",
        interval=ScheduleInterval.DAILY,
        function=backfill_missing_embeddings_task,
        enabled=embedding_backfill_enabled,
        target_time=embedding_backfill_time,
    )
    scheduler_service.add_task(embedding_backfill_task)

    logger.info(
        f"Default scheduled tasks configured (metrics reports + RSS feeds + Gazzetta scraper + Cassazione scraper + AdER scraper + daily ingestion report [enabled={ingestion_report_enabled}] + daily cost report [enabled={cost_report_enabled}] + daily eval report [enabled={eval_report_enabled}] + embedding backfill [enabled={embedding_backfill_enabled}])"
    )


async def start_scheduler() -> None:
    """Start the scheduler with default tasks.

    DEV-242: Immediate tasks now run in background (non-blocking).
    The scheduler.start() method handles this automatically.
    """
    setup_default_tasks()
    await scheduler_service.start()
    # DEV-242: Immediate tasks are now scheduled in background by start()
    # No blocking loop here - app startup completes immediately


async def stop_scheduler() -> None:
    """Stop the scheduler."""
    await scheduler_service.stop()
