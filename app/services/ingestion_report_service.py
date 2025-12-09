"""Ingestion Report Service for Daily RSS and Scraper Monitoring.

This service generates daily reports showing RSS feed ingestion and scraper activity,
including success rates, documents added, and junk percentages.
"""

import logging
import smtplib
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.knowledge import KnowledgeItem
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.regulatory_documents import DocumentProcessingLog, FeedStatus

logger = logging.getLogger(__name__)


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

    # RSS feed statistics
    rss_sources: list[SourceStats] = field(default_factory=list)

    # Scraper statistics
    scraper_sources: list[SourceStats] = field(default_factory=list)

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
        """Generate daily ingestion report.

        Args:
            report_date: Date to generate report for (defaults to yesterday)

        Returns:
            DailyIngestionReport with all metrics
        """
        if report_date is None:
            report_date = date.today() - timedelta(days=1)

        self.logger.info(f"Generating ingestion report for {report_date}")

        report = DailyIngestionReport(report_date=report_date)

        # Get RSS feed statistics
        report.rss_sources = await self._get_rss_stats(report_date)

        # Get scraper statistics
        report.scraper_sources = await self._get_scraper_stats(report_date)

        self.logger.info(
            f"Report generated: {report.total_documents_processed} processed, "
            f"{report.total_documents_added} added, "
            f"{report.overall_success_rate:.1f}% success rate"
        )

        return report

    async def _get_rss_stats(self, report_date: date) -> list[SourceStats]:
        """Get statistics for RSS feed ingestion.

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

        for feed in feeds:
            source_name = feed.source or feed.feed_type or "unknown"

            # Get processing logs for this feed on report_date
            start_dt = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)
            end_dt = start_dt + timedelta(days=1)

            log_query = select(DocumentProcessingLog).where(
                and_(
                    DocumentProcessingLog.feed_url == feed.feed_url,
                    DocumentProcessingLog.processed_at >= start_dt,
                    DocumentProcessingLog.processed_at < end_dt,
                )
            )
            log_result = await self.db.execute(log_query)
            logs = log_result.scalars().all()

            if not logs:
                continue

            # Calculate metrics
            stats = SourceStats(
                source_name=source_name,
                source_type="rss",
                documents_processed=len(logs),
                documents_succeeded=len([log for log in logs if log.status == "success"]),
                documents_failed=len([log for log in logs if log.status == "failed"]),
            )

            # Get avg processing time
            processing_times = [log.processing_time_ms for log in logs if log.processing_time_ms]
            if processing_times:
                stats.avg_processing_time_ms = sum(processing_times) / len(processing_times)

            # Get documents added to knowledge base for this source
            ki_query = select(func.count(KnowledgeItem.id)).where(
                and_(
                    KnowledgeItem.source == source_name,
                    KnowledgeItem.created_at >= start_dt,
                    KnowledgeItem.created_at < end_dt,
                )
            )
            ki_result = await self.db.execute(ki_query)
            stats.documents_added_to_db = ki_result.scalar() or 0

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
        total_query = select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.knowledge_item_id.in_(item_ids))
        total_result = await self.db.execute(total_query)
        total_chunks = total_result.scalar() or 0

        # Count junk chunks
        junk_query = select(func.count(KnowledgeChunk.id)).where(
            and_(
                KnowledgeChunk.knowledge_item_id.in_(item_ids),
                KnowledgeChunk.junk == True,  # noqa: E712
            )
        )
        junk_result = await self.db.execute(junk_query)
        junk_chunks = junk_result.scalar() or 0

        return {"total": total_chunks, "junk": junk_chunks}

    async def send_daily_report_email(self, recipients: list[str]) -> bool:
        """Send daily ingestion report via email.

        Args:
            recipients: List of email addresses

        Returns:
            True if sent successfully, False otherwise
        """
        if not recipients:
            self.logger.warning("No recipients provided for daily report")
            return False

        try:
            report = await self.generate_daily_report()
            html_content = self._generate_html_report(report)
            subject = f"PratikoAI Daily Ingestion Report - {report.report_date.isoformat()}"

            return await self._send_email(recipients, subject, html_content)

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

        # Overall status color
        overall_color = (
            "#28a745"
            if report.overall_success_rate >= 90
            else "#ffc107"
            if report.overall_success_rate >= 70
            else "#dc3545"
        )

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>PratikoAI Daily Ingestion Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 5px 0 0 0; opacity: 0.9; }}
                .summary {{ display: flex; justify-content: space-around; margin-bottom: 20px; }}
                .summary-card {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; min-width: 150px; }}
                .summary-card .number {{ font-size: 32px; font-weight: bold; color: #333; }}
                .summary-card .label {{ font-size: 14px; color: #666; }}
                .section {{ margin-bottom: 25px; }}
                .section h2 {{ margin-bottom: 15px; color: #333; font-size: 18px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; font-weight: 600; color: #333; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .footer {{ margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Daily Ingestion Report</h1>
                    <p>Report Date: {report.report_date.isoformat()} | Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}</p>
                </div>

                <div class="summary">
                    <div class="summary-card">
                        <div class="number">{report.total_documents_processed}</div>
                        <div class="label">Documents Processed</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">{report.total_documents_added}</div>
                        <div class="label">Added to KB</div>
                    </div>
                    <div class="summary-card">
                        <div class="number" style="color: {overall_color}">{report.overall_success_rate:.1f}%</div>
                        <div class="label">Success Rate</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">{report.overall_junk_rate:.1f}%</div>
                        <div class="label">Junk Rate</div>
                    </div>
                </div>

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

                <div class="footer">
                    <p>This is an automated report from PratikoAI Ingestion Monitoring System.</p>
                    <p>Contact DevOps team for questions or to adjust report recipients.</p>
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
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(recipients)

            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.from_email, recipients, msg.as_string())

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
