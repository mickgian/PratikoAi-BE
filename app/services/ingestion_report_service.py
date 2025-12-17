"""Ingestion Report Service for Daily RSS and Scraper Monitoring.

This service generates daily reports showing RSS feed ingestion and scraper activity,
including success rates, documents added, junk percentages, environment awareness,
alert system, week-over-week comparison, and new document previews.

DEV-BE-70: Daily Ingestion Collection Email Report
"""

import logging
import smtplib
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Environment, get_environment, settings
from app.models.knowledge import KnowledgeItem
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.regulatory_documents import DocumentProcessingLog, FeedStatus

logger = logging.getLogger(__name__)


# =============================================================================
# Alert System Types
# =============================================================================


class AlertType(str, Enum):
    """Types of ingestion alerts."""

    FEED_DOWN = "FEED_DOWN"  # HTTP 4xx/5xx for 2+ consecutive checks
    FEED_STALE = "FEED_STALE"  # No new items in 7+ days
    HIGH_ERROR_RATE = "HIGH_ERROR_RATE"  # >10% parse failures in 24h
    HIGH_JUNK_RATE = "HIGH_JUNK_RATE"  # >25% junk detection rate
    ZERO_DOCUMENTS = "ZERO_DOCUMENTS"  # No documents from any source in 24h


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class IngestionAlert:
    """Alert for ingestion issues."""

    alert_type: AlertType
    severity: AlertSeverity
    message: str
    source_name: str | None = None


# =============================================================================
# Environment Color Mapping
# =============================================================================

ENVIRONMENT_COLORS = {
    Environment.DEVELOPMENT: {"bg": "#6c757d", "name": "DEVELOPMENT", "prefix": "DEV"},
    Environment.QA: {"bg": "#007bff", "name": "QA", "prefix": "QA"},
    Environment.PRODUCTION: {"bg": "#28a745", "name": "PRODUCTION", "prefix": "PROD"},
}


def get_environment_color(env: Environment) -> dict[str, str]:
    """Get color configuration for an environment.

    Args:
        env: Environment enum value

    Returns:
        Dictionary with 'bg' (background color), 'name', and 'prefix' keys
    """
    return ENVIRONMENT_COLORS.get(
        env,
        {"bg": "#6c757d", "name": "UNKNOWN", "prefix": "UNK"},
    )


# =============================================================================
# Week-over-Week Comparison
# =============================================================================


@dataclass
class WoWComparison:
    """Week-over-week comparison data."""

    current_value: float
    previous_value: float
    change_percent: float | None = None

    def __post_init__(self):
        """Calculate change percentage."""
        if self.previous_value > 0:
            self.change_percent = ((self.current_value - self.previous_value) / self.previous_value) * 100
        elif self.current_value > 0:
            self.change_percent = 100.0  # Went from 0 to positive
        else:
            self.change_percent = 0.0  # Both zero

    @property
    def change_str(self) -> str:
        """Get formatted change string."""
        if self.change_percent is None:
            return "N/A"
        sign = "+" if self.change_percent >= 0 else ""
        return f"{sign}{self.change_percent:.1f}%"

    @property
    def change_color(self) -> str:
        """Get color for the change indicator."""
        if self.change_percent is None or self.change_percent == 0:
            return "#666"
        return "#28a745" if self.change_percent > 0 else "#dc3545"


# =============================================================================
# Document Preview
# =============================================================================


@dataclass
class DocumentPreview:
    """Preview of a new document."""

    source: str
    title: str
    created_at: datetime


# =============================================================================
# Error Sample
# =============================================================================


@dataclass
class ErrorSample:
    """Sample error message for debugging."""

    source_name: str
    error_count: int
    sample_messages: list[str] = field(default_factory=list)


@dataclass
class SourceStats:
    """Statistics for a single source (RSS feed or scraper)."""

    source_name: str
    source_type: str  # "rss" or "scraper"
    documents_processed: int = 0
    documents_succeeded: int = 0
    documents_failed: int = 0
    documents_added_to_db: int = 0
    total_chunks: int = 0
    junk_chunks: int = 0
    avg_processing_time_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.documents_processed == 0:
            return 0.0
        return (self.documents_succeeded / self.documents_processed) * 100

    @property
    def junk_percentage(self) -> float:
        """Calculate junk percentage."""
        if self.total_chunks == 0:
            return 0.0
        return (self.junk_chunks / self.total_chunks) * 100


@dataclass
class DailyIngestionReport:
    """Complete daily ingestion report."""

    report_date: date
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Environment identification
    environment: Environment = field(default_factory=get_environment)

    # RSS feed statistics
    rss_sources: list[SourceStats] = field(default_factory=list)

    # Scraper statistics
    scraper_sources: list[SourceStats] = field(default_factory=list)

    # Alert system
    alerts: list[IngestionAlert] = field(default_factory=list)

    # Week-over-week comparison
    wow_documents_processed: WoWComparison | None = None
    wow_documents_added: WoWComparison | None = None
    wow_success_rate: WoWComparison | None = None
    wow_junk_rate: WoWComparison | None = None

    # New document previews (top 5 per source)
    new_document_previews: list[DocumentPreview] = field(default_factory=list)

    # Error samples for debugging
    error_samples: list[ErrorSample] = field(default_factory=list)

    @property
    def total_documents_processed(self) -> int:
        """Total documents processed across all sources."""
        return sum(s.documents_processed for s in self.rss_sources + self.scraper_sources)

    @property
    def total_documents_succeeded(self) -> int:
        """Total successful documents."""
        return sum(s.documents_succeeded for s in self.rss_sources + self.scraper_sources)

    @property
    def total_documents_added(self) -> int:
        """Total documents added to knowledge base."""
        return sum(s.documents_added_to_db for s in self.rss_sources + self.scraper_sources)

    @property
    def overall_success_rate(self) -> float:
        """Overall success rate across all sources."""
        total = self.total_documents_processed
        if total == 0:
            return 0.0
        return (self.total_documents_succeeded / total) * 100

    @property
    def overall_junk_rate(self) -> float:
        """Overall junk rate across all sources."""
        total_chunks = sum(s.total_chunks for s in self.rss_sources + self.scraper_sources)
        junk_chunks = sum(s.junk_chunks for s in self.rss_sources + self.scraper_sources)
        if total_chunks == 0:
            return 0.0
        return (junk_chunks / total_chunks) * 100

    @property
    def alerts_by_severity(self) -> dict[str, int]:
        """Count alerts by severity."""
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for alert in self.alerts:
            counts[alert.severity.value] += 1
        return counts

    @property
    def environment_color(self) -> dict[str, str]:
        """Get environment color configuration."""
        return get_environment_color(self.environment)


class IngestionReportService:
    """Service for generating and sending daily ingestion reports."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the service.

        Args:
            db_session: Database session for querying metrics
        """
        self.db = db_session
        self.logger = logging.getLogger(__name__)

        # Email configuration
        self.smtp_server = getattr(settings, "SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = getattr(settings, "SMTP_PORT", 587)
        self.smtp_username = getattr(settings, "SMTP_USERNAME", None)
        self.smtp_password = getattr(settings, "SMTP_PASSWORD", None)
        self.from_email = getattr(settings, "FROM_EMAIL", "noreply@pratikoai.com")

    async def generate_daily_report(self, report_date: date | None = None) -> DailyIngestionReport:
        """Generate daily ingestion report with all metrics and alerts.

        Args:
            report_date: Date to generate report for (defaults to yesterday)

        Returns:
            DailyIngestionReport with all metrics, alerts, WoW comparison, and previews
        """
        if report_date is None:
            report_date = date.today() - timedelta(days=1)

        self.logger.info(f"Generating ingestion report for {report_date} (env: {get_environment().value})")

        report = DailyIngestionReport(report_date=report_date)

        # Get RSS feed statistics
        report.rss_sources = await self._get_rss_stats(report_date)

        # Get scraper statistics
        report.scraper_sources = await self._get_scraper_stats(report_date)

        # Detect alerts based on current data
        report.alerts = await self._detect_alerts(report_date, report)

        # Get week-over-week comparison
        prev_week_stats = await self._get_previous_week_stats(report_date)
        if prev_week_stats:
            report.wow_documents_processed = WoWComparison(
                current_value=float(report.total_documents_processed),
                previous_value=float(prev_week_stats.get("documents_processed", 0)),
            )
            report.wow_documents_added = WoWComparison(
                current_value=float(report.total_documents_added),
                previous_value=float(prev_week_stats.get("documents_added", 0)),
            )
            report.wow_success_rate = WoWComparison(
                current_value=report.overall_success_rate,
                previous_value=prev_week_stats.get("success_rate", 0.0),
            )
            report.wow_junk_rate = WoWComparison(
                current_value=report.overall_junk_rate,
                previous_value=prev_week_stats.get("junk_rate", 0.0),
            )

        # Get new document previews (top 5 per source)
        report.new_document_previews = await self._get_new_document_titles(report_date)

        # Get error samples for debugging
        report.error_samples = await self._get_error_samples(report_date)

        self.logger.info(
            f"Report generated: {report.total_documents_processed} processed, "
            f"{report.total_documents_added} added, "
            f"{report.overall_success_rate:.1f}% success rate, "
            f"{len(report.alerts)} alerts"
        )

        return report

    async def _get_rss_stats(self, report_date: date) -> list[SourceStats]:
        """Get statistics for RSS feed ingestion.

        Query KnowledgeItem directly instead of relying on DocumentProcessingLog,
        since RSS ingestion writes to KnowledgeItem but not DocumentProcessingLog.

        Args:
            report_date: Date to get stats for

        Returns:
            List of SourceStats for each RSS feed
        """
        stats_list = []

        # Get all enabled feeds
        feed_query = select(FeedStatus).where(FeedStatus.enabled == True)  # noqa: E712
        feed_result = await self.db.execute(feed_query)
        feeds = feed_result.scalars().all()

        # Time range for the report date
        start_dt = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)
        end_dt = start_dt + timedelta(days=1)

        for feed in feeds:
            # Match the source_identifier format used in rss_normativa.py:
            # source_identifier = f"{source_name}_{feed_type or 'generic'}"
            if feed.source and feed.feed_type:
                source_name = f"{feed.source}_{feed.feed_type}"
            else:
                source_name = feed.source or feed.feed_type or "unknown"

            # Query KnowledgeItem directly to count documents for this source
            # RSS ingestion writes to KnowledgeItem, not DocumentProcessingLog
            ki_query = select(func.count(KnowledgeItem.id)).where(
                and_(
                    KnowledgeItem.source == source_name,
                    KnowledgeItem.created_at >= start_dt,
                    KnowledgeItem.created_at < end_dt,
                )
            )
            ki_result = await self.db.execute(ki_query)
            documents_added = ki_result.scalar() or 0

            # Show ALL feeds (even with 0 documents) so user can see complete picture
            # Documents in KnowledgeItem are successfully processed
            # (failed documents don't get added to the knowledge base)
            stats = SourceStats(
                source_name=source_name,
                source_type="rss",
                documents_processed=documents_added,
                documents_succeeded=documents_added,
                documents_failed=0,  # If in KB, it succeeded
                documents_added_to_db=documents_added,
            )

            # Optionally get processing time from DocumentProcessingLog if available
            log_query = select(DocumentProcessingLog).where(
                and_(
                    DocumentProcessingLog.feed_url == feed.feed_url,
                    DocumentProcessingLog.created_at >= start_dt,
                    DocumentProcessingLog.created_at < end_dt,
                )
            )
            log_result = await self.db.execute(log_query)
            logs = log_result.scalars().all()

            if logs:
                processing_times = [log.processing_time_ms for log in logs if log.processing_time_ms]
                if processing_times:
                    stats.avg_processing_time_ms = sum(processing_times) / len(processing_times)
                # Update failed count if logs show failures
                stats.documents_failed = len([log for log in logs if log.status == "failed"])

            # Get chunk statistics
            chunk_stats = await self._get_chunk_stats_for_source(source_name, start_dt, end_dt)
            stats.total_chunks = chunk_stats["total"]
            stats.junk_chunks = chunk_stats["junk"]

            stats_list.append(stats)

        return stats_list

    async def _get_scraper_stats(self, report_date: date) -> list[SourceStats]:
        """Get statistics for web scrapers (Gazzetta, Cassazione).

        Args:
            report_date: Date to get stats for

        Returns:
            List of SourceStats for each scraper
        """
        stats_list = []
        start_dt = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)
        end_dt = start_dt + timedelta(days=1)

        # Check for Gazzetta scraper activity
        gazzetta_query = select(func.count(KnowledgeItem.id)).where(
            and_(
                KnowledgeItem.source == "gazzetta_ufficiale",
                KnowledgeItem.created_at >= start_dt,
                KnowledgeItem.created_at < end_dt,
            )
        )
        gazzetta_result = await self.db.execute(gazzetta_query)
        gazzetta_count = gazzetta_result.scalar() or 0

        if gazzetta_count > 0:
            chunk_stats = await self._get_chunk_stats_for_source("gazzetta_ufficiale", start_dt, end_dt)
            stats_list.append(
                SourceStats(
                    source_name="Gazzetta Ufficiale",
                    source_type="scraper",
                    documents_processed=gazzetta_count,
                    documents_succeeded=gazzetta_count,
                    documents_added_to_db=gazzetta_count,
                    total_chunks=chunk_stats["total"],
                    junk_chunks=chunk_stats["junk"],
                )
            )

        # Check for Cassazione scraper activity
        cassazione_query = select(func.count(KnowledgeItem.id)).where(
            and_(
                KnowledgeItem.source == "cassazione",
                KnowledgeItem.created_at >= start_dt,
                KnowledgeItem.created_at < end_dt,
            )
        )
        cassazione_result = await self.db.execute(cassazione_query)
        cassazione_count = cassazione_result.scalar() or 0

        if cassazione_count > 0:
            chunk_stats = await self._get_chunk_stats_for_source("cassazione", start_dt, end_dt)
            stats_list.append(
                SourceStats(
                    source_name="Cassazione",
                    source_type="scraper",
                    documents_processed=cassazione_count,
                    documents_succeeded=cassazione_count,
                    documents_added_to_db=cassazione_count,
                    total_chunks=chunk_stats["total"],
                    junk_chunks=chunk_stats["junk"],
                )
            )

        # Fallback: Check for regulatory_update (legacy source name from before fix)
        # This catches documents created before KnowledgeIntegrator was fixed to use
        # the source from document_data
        regulatory_query = select(func.count(KnowledgeItem.id)).where(
            and_(
                KnowledgeItem.source == "regulatory_update",
                KnowledgeItem.created_at >= start_dt,
                KnowledgeItem.created_at < end_dt,
            )
        )
        regulatory_result = await self.db.execute(regulatory_query)
        regulatory_count = regulatory_result.scalar() or 0

        if regulatory_count > 0:
            chunk_stats = await self._get_chunk_stats_for_source("regulatory_update", start_dt, end_dt)
            stats_list.append(
                SourceStats(
                    source_name="Regulatory Update (Legacy)",
                    source_type="scraper",
                    documents_processed=regulatory_count,
                    documents_succeeded=regulatory_count,
                    documents_added_to_db=regulatory_count,
                    total_chunks=chunk_stats["total"],
                    junk_chunks=chunk_stats["junk"],
                )
            )

        return stats_list

    async def _get_chunk_stats_for_source(self, source: str, start_dt: datetime, end_dt: datetime) -> dict[str, int]:
        """Get chunk statistics for a specific source.

        Args:
            source: Source name
            start_dt: Start datetime
            end_dt: End datetime

        Returns:
            Dictionary with total and junk chunk counts
        """
        # Get knowledge items for this source in time range
        ki_query = select(KnowledgeItem.id).where(
            and_(
                KnowledgeItem.source == source,
                KnowledgeItem.created_at >= start_dt,
                KnowledgeItem.created_at < end_dt,
            )
        )
        ki_result = await self.db.execute(ki_query)
        item_ids = [row[0] for row in ki_result.fetchall()]

        if not item_ids:
            return {"total": 0, "junk": 0}

        # Count total chunks for these items
        total_query = select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.knowledge_item_id.in_(item_ids))  # type: ignore[union-attr]
        total_result = await self.db.execute(total_query)
        total_chunks = total_result.scalar() or 0

        # Count junk chunks
        junk_query = select(func.count(KnowledgeChunk.id)).where(
            and_(
                KnowledgeChunk.knowledge_item_id.in_(item_ids),  # type: ignore[union-attr]
                KnowledgeChunk.junk == True,  # noqa: E712
            )
        )
        junk_result = await self.db.execute(junk_query)
        junk_chunks = junk_result.scalar() or 0

        return {"total": total_chunks, "junk": junk_chunks}

    async def _detect_alerts(self, report_date: date, report: DailyIngestionReport) -> list[IngestionAlert]:
        """Detect alerts based on ingestion metrics.

        Args:
            report_date: Date of the report
            report: Current report with basic metrics

        Returns:
            List of IngestionAlert objects
        """
        alerts: list[IngestionAlert] = []

        # Alert 1: ZERO_DOCUMENTS - No documents from any source in 24h
        if report.total_documents_processed == 0:
            alerts.append(
                IngestionAlert(
                    alert_type=AlertType.ZERO_DOCUMENTS,
                    severity=AlertSeverity.HIGH,
                    message="No documents collected from any source in the last 24 hours",
                )
            )

        # Alert 2: FEED_DOWN - HTTP 4xx/5xx for 2+ consecutive checks
        down_feeds = await self._get_down_feeds()
        for feed in down_feeds:
            alerts.append(
                IngestionAlert(
                    alert_type=AlertType.FEED_DOWN,
                    severity=AlertSeverity.HIGH,
                    message=f"Feed has failed {feed['consecutive_errors']} consecutive checks",
                    source_name=feed["source"],
                )
            )

        # Alert 3: FEED_STALE - No new items in 7+ days
        stale_feeds = await self._get_stale_feeds()
        for feed in stale_feeds:
            alerts.append(
                IngestionAlert(
                    alert_type=AlertType.FEED_STALE,
                    severity=AlertSeverity.MEDIUM,
                    message=f"No new items in {feed['days_stale']} days",
                    source_name=feed["source"],
                )
            )

        # Alert 4: HIGH_ERROR_RATE - >10% parse failures in 24h
        for source in report.rss_sources + report.scraper_sources:
            if source.documents_processed > 0:
                error_rate = (source.documents_failed / source.documents_processed) * 100
                if error_rate > 10:
                    alerts.append(
                        IngestionAlert(
                            alert_type=AlertType.HIGH_ERROR_RATE,
                            severity=AlertSeverity.MEDIUM,
                            message=f"{error_rate:.1f}% error rate ({source.documents_failed}/{source.documents_processed} failures)",
                            source_name=source.source_name,
                        )
                    )

        # Alert 5: HIGH_JUNK_RATE - >25% junk detection rate
        for source in report.rss_sources + report.scraper_sources:
            if source.junk_percentage > 25:
                alerts.append(
                    IngestionAlert(
                        alert_type=AlertType.HIGH_JUNK_RATE,
                        severity=AlertSeverity.LOW,
                        message=f"{source.junk_percentage:.1f}% junk rate ({source.junk_chunks}/{source.total_chunks} chunks)",
                        source_name=source.source_name,
                    )
                )

        return alerts

    async def _get_down_feeds(self) -> list[dict[str, Any]]:
        """Get feeds that are down (2+ consecutive errors).

        Returns:
            List of dictionaries with source and consecutive_errors
        """
        query = select(FeedStatus).where(
            and_(
                FeedStatus.enabled == True,  # noqa: E712
                FeedStatus.consecutive_errors >= 2,
            )
        )
        result = await self.db.execute(query)
        feeds = result.scalars().all()

        return [
            {
                "source": feed.source or feed.feed_type or "unknown",
                "consecutive_errors": feed.consecutive_errors,
            }
            for feed in feeds
        ]

    async def _get_stale_feeds(self) -> list[dict[str, Any]]:
        """Get feeds with no new items in 7+ days.

        Returns:
            List of dictionaries with source and days_stale
        """
        stale_threshold = datetime.now(UTC) - timedelta(days=7)

        query = select(FeedStatus).where(
            and_(
                FeedStatus.enabled == True,  # noqa: E712
                or_(
                    FeedStatus.last_success < stale_threshold,  # type: ignore[operator]
                    FeedStatus.last_success.is_(None),  # type: ignore[union-attr]
                ),
            )
        )
        result = await self.db.execute(query)
        feeds = result.scalars().all()

        stale_list = []
        for feed in feeds:
            if feed.last_success:
                days_stale = (datetime.now(UTC) - feed.last_success).days
            else:
                days_stale = 999  # Never succeeded
            stale_list.append(
                {
                    "source": feed.source or feed.feed_type or "unknown",
                    "days_stale": days_stale,
                }
            )

        return stale_list

    async def _get_previous_week_stats(self, report_date: date) -> dict[str, Any] | None:
        """Get statistics from previous week for WoW comparison.

        Query KnowledgeItem directly since RSS ingestion writes to KnowledgeItem,
        not DocumentProcessingLog.

        Args:
            report_date: Current report date

        Returns:
            Dictionary with documents_processed, documents_added, success_rate, junk_rate
        """
        prev_week_date = report_date - timedelta(days=7)
        start_dt = datetime.combine(prev_week_date, datetime.min.time()).replace(tzinfo=UTC)
        end_dt = start_dt + timedelta(days=1)

        # Get documents added from previous week (from KnowledgeItem directly)
        # Documents in KnowledgeItem are successfully processed
        ki_query = select(func.count(KnowledgeItem.id)).where(
            and_(
                KnowledgeItem.created_at >= start_dt,
                KnowledgeItem.created_at < end_dt,
            )
        )
        ki_result = await self.db.execute(ki_query)
        documents_added = ki_result.scalar() or 0

        # Documents processed = documents added (documents in KB are successfully processed)
        documents_processed = documents_added

        # Get chunk stats from previous week
        chunk_query = select(KnowledgeItem.id).where(
            and_(
                KnowledgeItem.created_at >= start_dt,
                KnowledgeItem.created_at < end_dt,
            )
        )
        chunk_result = await self.db.execute(chunk_query)
        item_ids = [row[0] for row in chunk_result.fetchall()]

        total_chunks = 0
        junk_chunks = 0
        if item_ids:
            total_q = select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.knowledge_item_id.in_(item_ids))  # type: ignore[union-attr]
            total_r = await self.db.execute(total_q)
            total_chunks = total_r.scalar() or 0

            junk_q = select(func.count(KnowledgeChunk.id)).where(
                and_(
                    KnowledgeChunk.knowledge_item_id.in_(item_ids),  # type: ignore[union-attr]
                    KnowledgeChunk.junk == True,  # noqa: E712
                )
            )
            junk_r = await self.db.execute(junk_q)
            junk_chunks = junk_r.scalar() or 0

        # Success rate is 100% for documents in KB (they succeeded to be stored)
        success_rate = 100.0 if documents_processed > 0 else 0.0
        junk_rate = (junk_chunks / total_chunks * 100) if total_chunks > 0 else 0.0

        return {
            "documents_processed": documents_processed,
            "documents_added": documents_added,
            "success_rate": success_rate,
            "junk_rate": junk_rate,
        }

    async def _get_new_document_titles(self, report_date: date, limit_per_source: int = 5) -> list[DocumentPreview]:
        """Get top N new document titles per source.

        Args:
            report_date: Date to get documents for
            limit_per_source: Maximum documents per source

        Returns:
            List of DocumentPreview objects
        """
        start_dt = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)
        end_dt = start_dt + timedelta(days=1)

        # Get recent documents grouped by source
        query = (
            select(KnowledgeItem.source, KnowledgeItem.title, KnowledgeItem.created_at)
            .where(
                and_(
                    KnowledgeItem.created_at >= start_dt,
                    KnowledgeItem.created_at < end_dt,
                )
            )
            .order_by(KnowledgeItem.created_at.desc())  # type: ignore[attr-defined]
        )
        result = await self.db.execute(query)
        rows = result.fetchall()

        # Group by source and take top N per source
        source_docs: dict[str, list[DocumentPreview]] = {}
        for row in rows:
            source = row[0] or "unknown"
            title = row[1] or "Untitled"
            created_at = row[2]

            # Truncate title to 100 chars
            if len(title) > 100:
                title = title[:97] + "..."

            if source not in source_docs:
                source_docs[source] = []

            if len(source_docs[source]) < limit_per_source:
                source_docs[source].append(
                    DocumentPreview(
                        source=source,
                        title=title,
                        created_at=created_at,
                    )
                )

        # Flatten and return
        previews = []
        for docs in source_docs.values():
            previews.extend(docs)

        return previews

    async def _get_error_samples(self, report_date: date, samples_per_source: int = 2) -> list[ErrorSample]:
        """Get error samples for debugging.

        Args:
            report_date: Date to get errors for
            samples_per_source: Number of sample error messages per source

        Returns:
            List of ErrorSample objects
        """
        start_dt = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)
        end_dt = start_dt + timedelta(days=1)

        # Get failed processing logs with error messages
        query = (
            select(DocumentProcessingLog)
            .where(
                and_(
                    DocumentProcessingLog.created_at >= start_dt,
                    DocumentProcessingLog.created_at < end_dt,
                    DocumentProcessingLog.status == "failed",
                )
            )
            .order_by(DocumentProcessingLog.created_at.desc())  # type: ignore[attr-defined]
        )
        result = await self.db.execute(query)
        logs = result.scalars().all()

        # Group errors by feed URL (as proxy for source)
        source_errors: dict[str, list[str]] = {}
        source_counts: dict[str, int] = {}

        for log in logs:
            source = log.feed_url or "unknown"
            error_msg = log.error_message or "Unknown error"

            if source not in source_errors:
                source_errors[source] = []
                source_counts[source] = 0

            source_counts[source] += 1

            # Only keep up to N sample messages
            if len(source_errors[source]) < samples_per_source:
                # Truncate long error messages
                if len(error_msg) > 200:
                    error_msg = error_msg[:197] + "..."
                source_errors[source].append(error_msg)

        # Convert to ErrorSample objects
        samples = []
        for source, messages in source_errors.items():
            samples.append(
                ErrorSample(
                    source_name=source,
                    error_count=source_counts[source],
                    sample_messages=messages,
                )
            )

        return samples

    async def send_daily_report_email(self, recipients: list[str], max_retries: int = 3) -> bool:
        """Send daily ingestion report via email with retry logic.

        Args:
            recipients: List of email addresses
            max_retries: Maximum retry attempts (default 3)

        Returns:
            True if sent successfully, False otherwise
        """
        if not recipients:
            self.logger.warning("No recipients provided for daily report")
            return False

        try:
            report = await self.generate_daily_report()
            html_content = self._generate_html_report(report)

            # Environment prefix in subject: [DEV], [QA], [PROD]
            env_color = report.environment_color
            subject = f"[{env_color['prefix']}] PratikoAI Daily Ingestion Report - {report.report_date.isoformat()}"

            # Retry logic with exponential backoff
            for attempt in range(max_retries):
                try:
                    success = await self._send_email(recipients, subject, html_content)
                    if success:
                        return True
                    self.logger.warning(f"Email send attempt {attempt + 1} failed, retrying...")
                except Exception as e:
                    self.logger.warning(f"Email send attempt {attempt + 1} failed: {e}")

                # Exponential backoff: 1s, 2s, 4s
                if attempt < max_retries - 1:
                    import asyncio

                    await asyncio.sleep(2**attempt)

            self.logger.error(f"Failed to send daily report after {max_retries} attempts")
            return False

        except Exception as e:
            self.logger.error(f"Failed to send daily report: {e}")
            return False

    def _generate_html_report(self, report: DailyIngestionReport) -> str:
        """Generate HTML email content from report.

        Args:
            report: DailyIngestionReport to format

        Returns:
            HTML string for email body
        """
        # Environment color configuration
        env_color = report.environment_color

        # Generate WoW change indicators
        def wow_indicator(wow: WoWComparison | None) -> str:
            if wow is None:
                return ""
            return f'<span style="font-size: 12px; color: {wow.change_color};">({wow.change_str} vs last week)</span>'

        # Generate RSS table rows
        rss_rows = ""
        for source in report.rss_sources:
            status_color = (
                "#28a745" if source.success_rate >= 90 else "#ffc107" if source.success_rate >= 70 else "#dc3545"
            )
            rss_rows += f"""
            <tr>
                <td>{source.source_name}</td>
                <td>{source.documents_processed}</td>
                <td style="color: {status_color}">{source.documents_succeeded}</td>
                <td>{source.documents_failed}</td>
                <td>{source.documents_added_to_db}</td>
                <td>{source.junk_percentage:.1f}%</td>
            </tr>
            """

        if not rss_rows:
            rss_rows = '<tr><td colspan="6" style="text-align: center; color: #666;">No RSS activity</td></tr>'

        # Generate scraper table rows
        scraper_rows = ""
        for source in report.scraper_sources:
            status_color = (
                "#28a745" if source.success_rate >= 90 else "#ffc107" if source.success_rate >= 70 else "#dc3545"
            )
            scraper_rows += f"""
            <tr>
                <td>{source.source_name}</td>
                <td>{source.documents_processed}</td>
                <td style="color: {status_color}">{source.documents_succeeded}</td>
                <td>{source.documents_failed}</td>
                <td>{source.documents_added_to_db}</td>
                <td>{source.junk_percentage:.1f}%</td>
            </tr>
            """

        if not scraper_rows:
            scraper_rows = '<tr><td colspan="6" style="text-align: center; color: #666;">No scraper activity</td></tr>'

        # Generate alerts section
        alerts_html = ""
        if report.alerts:
            severity_icons = {"HIGH": "&#x1F534;", "MEDIUM": "&#x1F7E0;", "LOW": "&#x1F7E1;"}
            alert_rows = ""
            for alert in report.alerts:
                icon = severity_icons.get(alert.severity.value, "&#x26A0;")
                source = alert.source_name or "All Sources"
                alert_rows += f"""
                <tr>
                    <td>{icon} {alert.severity.value}</td>
                    <td>{alert.alert_type.value}</td>
                    <td>{source}</td>
                    <td>{alert.message}</td>
                </tr>
                """
            alerts_html = f"""
            <div class="section">
                <h2>Alerts ({len(report.alerts)})</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Severity</th>
                            <th>Type</th>
                            <th>Source</th>
                            <th>Message</th>
                        </tr>
                    </thead>
                    <tbody>
                        {alert_rows}
                    </tbody>
                </table>
            </div>
            """
        else:
            alerts_html = """
            <div class="section">
                <h2>Alerts</h2>
                <p style="color: #28a745; font-weight: 500;">&#x2705; No alerts - all systems operating normally</p>
            </div>
            """

        # Generate new documents preview section
        docs_preview_html = ""
        if report.new_document_previews:
            doc_rows = ""
            for doc in report.new_document_previews[:15]:  # Max 15 total
                doc_rows += f"""
                <tr>
                    <td>{doc.source}</td>
                    <td>{doc.title}</td>
                </tr>
                """
            docs_preview_html = f"""
            <div class="section">
                <h2>New Documents Preview (Top 5 per source)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Source</th>
                            <th>Document Title</th>
                        </tr>
                    </thead>
                    <tbody>
                        {doc_rows}
                    </tbody>
                </table>
            </div>
            """
        else:
            docs_preview_html = """
            <div class="section">
                <h2>New Documents Preview</h2>
                <p style="color: #666;">No new documents added today.</p>
            </div>
            """

        # Generate error samples section
        errors_html = ""
        if report.error_samples:
            error_rows = ""
            for sample in report.error_samples:
                messages = "<br>".join([f"&bull; {msg}" for msg in sample.sample_messages])
                error_rows += f"""
                <tr>
                    <td>{sample.source_name}</td>
                    <td style="color: #dc3545; font-weight: 500;">{sample.error_count}</td>
                    <td style="font-size: 12px;">{messages}</td>
                </tr>
                """
            errors_html = f"""
            <div class="section">
                <h2>Error Details</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Source</th>
                            <th>Count</th>
                            <th>Sample Messages</th>
                        </tr>
                    </thead>
                    <tbody>
                        {error_rows}
                    </tbody>
                </table>
            </div>
            """

        # Overall status color
        overall_color = (
            "#28a745"
            if report.overall_success_rate >= 90
            else "#ffc107"
            if report.overall_success_rate >= 70
            else "#dc3545"
        )

        # Alert summary for header
        alert_counts = report.alerts_by_severity
        alert_summary = ""
        if any(alert_counts.values()):
            parts = []
            if alert_counts["HIGH"]:
                parts.append(f"&#x1F534; {alert_counts['HIGH']} High")
            if alert_counts["MEDIUM"]:
                parts.append(f"&#x1F7E0; {alert_counts['MEDIUM']} Medium")
            if alert_counts["LOW"]:
                parts.append(f"&#x1F7E1; {alert_counts['LOW']} Low")
            alert_summary = " | ".join(parts)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>PratikoAI Daily Ingestion Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 900px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .env-badge {{ display: inline-block; background-color: {env_color["bg"]}; color: white; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-bottom: 10px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 5px 0 0 0; opacity: 0.9; }}
                .header .alert-summary {{ margin-top: 10px; font-size: 14px; }}
                .summary {{ display: flex; flex-wrap: wrap; justify-content: space-around; margin-bottom: 20px; gap: 10px; }}
                .summary-card {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; min-width: 140px; flex: 1; }}
                .summary-card .number {{ font-size: 28px; font-weight: bold; color: #333; }}
                .summary-card .label {{ font-size: 13px; color: #666; }}
                .summary-card .wow {{ font-size: 11px; margin-top: 4px; }}
                .section {{ margin-bottom: 25px; }}
                .section h2 {{ margin-bottom: 15px; color: #333; font-size: 18px; border-bottom: 2px solid #667eea; padding-bottom: 8px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; font-weight: 600; color: #333; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .footer {{ margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <span class="env-badge">{env_color["name"]}</span>
                    <h1>Daily Ingestion Report</h1>
                    <p>Report Date: {report.report_date.isoformat()} | Generated: {report.generated_at.strftime("%Y-%m-%d %H:%M UTC")}</p>
                    {f'<div class="alert-summary">Alerts: {alert_summary}</div>' if alert_summary else ""}
                </div>

                <div class="summary">
                    <div class="summary-card">
                        <div class="number">{report.total_documents_processed}</div>
                        <div class="label">Documents Processed</div>
                        <div class="wow">{wow_indicator(report.wow_documents_processed)}</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">{report.total_documents_added}</div>
                        <div class="label">Added to KB</div>
                        <div class="wow">{wow_indicator(report.wow_documents_added)}</div>
                    </div>
                    <div class="summary-card">
                        <div class="number" style="color: {overall_color}">{report.overall_success_rate:.1f}%</div>
                        <div class="label">Success Rate</div>
                        <div class="wow">{wow_indicator(report.wow_success_rate)}</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">{report.overall_junk_rate:.1f}%</div>
                        <div class="label">Junk Rate</div>
                        <div class="wow">{wow_indicator(report.wow_junk_rate)}</div>
                    </div>
                </div>

                {alerts_html}

                <div class="section">
                    <h2>RSS Feeds ({len(report.rss_sources)} sources)</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Source</th>
                                <th>Processed</th>
                                <th>Success</th>
                                <th>Failed</th>
                                <th>Added to KB</th>
                                <th>Junk %</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rss_rows}
                        </tbody>
                    </table>
                </div>

                <div class="section">
                    <h2>Web Scrapers ({len(report.scraper_sources)} sources)</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Source</th>
                                <th>Processed</th>
                                <th>Success</th>
                                <th>Failed</th>
                                <th>Added to KB</th>
                                <th>Junk %</th>
                            </tr>
                        </thead>
                        <tbody>
                            {scraper_rows}
                        </tbody>
                    </table>
                </div>

                {docs_preview_html}

                {errors_html}

                <div class="footer">
                    <p>This is an automated report from PratikoAI Ingestion Monitoring System.</p>
                    <p>Environment: {env_color["name"]} | Contact DevOps team for questions.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    async def _send_email(self, recipients: list[str], subject: str, html_content: str) -> bool:
        """Send email via SMTP.

        Args:
            recipients: List of email addresses
            subject: Email subject
            html_content: HTML email body

        Returns:
            True if sent successfully
        """
        if not self.smtp_username or not self.smtp_password:
            self.logger.warning("SMTP credentials not configured, skipping email send")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = Header(subject, "utf-8")
            msg["From"] = self.from_email
            msg["To"] = ", ".join(recipients)

            # Attach HTML content with UTF-8 charset
            html_part = MIMEText(html_content, "html", _charset="utf-8")
            msg.attach(html_part)

            # Send email using send_message for proper encoding
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg, self.from_email, recipients)

            self.logger.info(f"Daily ingestion report sent to {len(recipients)} recipients")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False


# Scheduled task function for integration with scheduler service
async def send_ingestion_daily_report_task(db_session: AsyncSession) -> bool:
    """Scheduled task function for sending daily ingestion report.

    This function is called by the scheduler service daily at 06:00 UTC.

    Args:
        db_session: Database session

    Returns:
        True if report sent successfully
    """
    recipients_str = getattr(settings, "INGESTION_REPORT_RECIPIENTS", "")
    if not recipients_str:
        logger.warning("INGESTION_REPORT_RECIPIENTS not configured, skipping daily report")
        return False

    recipients = [email.strip() for email in recipients_str.split(",") if email.strip()]

    service = IngestionReportService(db_session)
    return await service.send_daily_report_email(recipients)
