# mypy: disable-error-code="arg-type,call-overload,misc,assignment"
"""Consolidated Report Service for Multi-Environment Daily Reports.

Sends a single email covering DEV, QA, and PRODUCTION with collapsible
<details> sections per environment (collapsed by default).

Replaces the per-environment emails so the user receives ONE email
instead of one per environment.
"""

import logging
import smtplib
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import Environment, settings

logger = logging.getLogger(__name__)


# =============================================================================
# Environment Report Configuration
# =============================================================================

ENVIRONMENT_COLORS = {
    Environment.DEVELOPMENT: {"bg": "#6c757d", "name": "DEVELOPMENT", "prefix": "DEV", "emoji": "⚫"},
    Environment.QA: {"bg": "#007bff", "name": "QA", "prefix": "QA", "emoji": "🔵"},
    Environment.PRODUCTION: {"bg": "#28a745", "name": "PRODUCTION", "prefix": "PROD", "emoji": "🟢"},
}

# Display order: DEV, QA, PROD
DISPLAY_ORDER = [Environment.DEVELOPMENT, Environment.QA, Environment.PRODUCTION]


@dataclass
class EnvironmentReportConfig:
    """Configuration for connecting to one environment's database."""

    environment: Environment
    postgres_url: str
    enabled: bool = True

    @property
    def async_postgres_url(self) -> str:
        """Return asyncpg-compatible URL."""
        url = self.postgres_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


# =============================================================================
# Consolidated Report Service
# =============================================================================


class ConsolidatedReportService:
    """Service to generate consolidated multi-environment reports."""

    def __init__(self, env_configs: list[EnvironmentReportConfig]):
        """Initialize with environment configurations.

        Args:
            env_configs: List of environment DB configs
        """
        self.env_configs = env_configs
        self.logger = logging.getLogger(__name__)

        # SMTP configuration
        self.smtp_server = getattr(settings, "SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = getattr(settings, "SMTP_PORT", 587)
        self.smtp_username = getattr(settings, "SMTP_USERNAME", "")
        self.smtp_password = getattr(settings, "SMTP_PASSWORD", "")
        self.from_email = getattr(settings, "FROM_EMAIL", "noreply@pratikoai.com")

    @property
    def active_configs(self) -> list[EnvironmentReportConfig]:
        """Return only enabled environment configs."""
        return [c for c in self.env_configs if c.enabled and c.postgres_url]

    @property
    def display_environments(self) -> list[Environment]:
        """Return all environments in display order (always includes all 3)."""
        return list(DISPLAY_ORDER)

    # =========================================================================
    # Ingestion Report
    # =========================================================================

    async def send_consolidated_ingestion_report(self, recipients: list[str]) -> bool:
        """Generate and send consolidated ingestion report across all environments.

        Args:
            recipients: Email recipients

        Returns:
            True if sent successfully
        """
        from app.services.ingestion_report_service import DailyIngestionReport

        if not recipients:
            self.logger.warning("consolidated_ingestion_report_no_recipients")
            return False

        report_date = (datetime.now(UTC) - timedelta(days=1)).date()
        env_reports: dict[Environment, DailyIngestionReport] = {}

        for config in self.active_configs:
            try:
                session = await self._create_session(config)
                async with session:
                    report = await self._generate_ingestion_report_for_session(session, config.environment)
                    env_reports[config.environment] = report
            except Exception as e:
                self.logger.error(
                    "consolidated_ingestion_report_env_failed",
                    extra={
                        "environment": config.environment.value,
                        "error": str(e),
                    },
                )

        # Check for alerts across all environments
        has_alerts = any(len(r.alerts) > 0 for r in env_reports.values())

        html = self._generate_consolidated_ingestion_html(env_reports, report_date)
        subject = self._get_ingestion_subject(report_date, has_alerts)

        return self._send_email(recipients, subject, html)

    async def _generate_ingestion_report_for_session(self, session, environment: Environment):
        """Generate ingestion report using a specific DB session.

        Args:
            session: AsyncSession for the target environment
            environment: Environment enum

        Returns:
            DailyIngestionReport
        """
        from app.services.ingestion_report_service import IngestionReportService

        service = IngestionReportService(session)
        report = await service.generate_daily_report()
        # Override environment to match the config (not the local APP_ENV)
        report.environment = environment
        return report

    def _get_ingestion_subject(self, report_date: date, has_alerts: bool) -> str:
        """Generate email subject for consolidated ingestion report."""
        subject = f"PratikoAI Daily Ingestion Report - {report_date.isoformat()}"
        if has_alerts:
            subject = f"⚠️ {subject}"
        return subject

    def _generate_consolidated_ingestion_html(
        self,
        env_reports: dict,
        report_date: date,
    ) -> str:
        """Generate consolidated HTML with collapsible sections per environment.

        Args:
            env_reports: Dict mapping Environment to DailyIngestionReport
            report_date: Report date

        Returns:
            Complete HTML string
        """
        from app.services.ingestion_report_service import WoWComparison

        # Aggregate alert counts
        total_alerts = sum(len(r.alerts) for r in env_reports.values())
        total_processed = sum(r.total_documents_processed for r in env_reports.values())
        total_added = sum(r.total_documents_added for r in env_reports.values())

        # Build environment sections
        env_sections = ""
        for env in DISPLAY_ORDER:
            env_color = ENVIRONMENT_COLORS[env]
            report = env_reports.get(env)

            if report is not None:
                env_sections += self._build_ingestion_env_section(env, env_color, report)
            else:
                env_sections += self._build_placeholder_section(env, env_color, "ingestion")

        generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>PratikoAI Consolidated Daily Ingestion Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 900px; margin: 0 auto; background-color: white; padding: 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .header h1 {{ margin: 0; font-size: 22px; }}
                .header p {{ margin: 5px 0 0 0; opacity: 0.9; font-size: 14px; }}
                .content {{ padding: 20px; }}
                .grand-summary {{ display: flex; flex-wrap: wrap; justify-content: space-around; margin-bottom: 20px; gap: 10px; }}
                .grand-summary .stat-card {{ text-align: center; padding: 12px; background: #f8f9fa; border-radius: 8px; min-width: 120px; flex: 1; }}
                .grand-summary .number {{ font-size: 24px; font-weight: bold; color: #333; }}
                .grand-summary .label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                details {{ margin-bottom: 12px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }}
                summary {{ cursor: pointer; padding: 14px 18px; background: #f8f9fa; font-weight: 600; font-size: 15px; list-style: none; display: flex; align-items: center; gap: 10px; }}
                summary::-webkit-details-marker {{ display: none; }}
                summary::before {{ content: "▶"; font-size: 12px; transition: transform 0.2s; color: #666; }}
                details[open] summary::before {{ transform: rotate(90deg); }}
                .env-badge {{ display: inline-block; color: white; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
                .env-content {{ padding: 15px 18px; }}
                .summary-metrics {{ color: #666; font-size: 13px; font-weight: normal; margin-left: auto; }}
                .section {{ margin-bottom: 20px; }}
                .section h3 {{ margin-bottom: 10px; color: #333; font-size: 15px; border-bottom: 1px solid #667eea; padding-bottom: 6px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #eee; font-size: 13px; }}
                th {{ background-color: #f8f9fa; font-weight: 600; color: #333; }}
                .summary-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 15px; }}
                .mini-card {{ text-align: center; padding: 10px; background: #f8f9fa; border-radius: 6px; min-width: 100px; flex: 1; }}
                .mini-card .number {{ font-size: 20px; font-weight: bold; color: #333; }}
                .mini-card .label {{ font-size: 11px; color: #666; }}
                .mini-card .wow {{ font-size: 10px; margin-top: 2px; }}
                .alert-badge {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 600; margin-left: 8px; }}
                .footer {{ text-align: center; padding: 15px; color: #666; font-size: 12px; border-top: 1px solid #ddd; }}
                .note {{ font-size: 12px; color: #999; font-style: italic; margin: 10px 18px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Daily Ingestion Report</h1>
                    <p>Report Date: {report_date.isoformat()} | Generated: {generated_at}</p>
                    <p style="margin-top: 8px; font-size: 13px; opacity: 0.8;">
                        Consolidated view across all environments. Click each section to expand.
                    </p>
                </div>
                <div class="content">
                    <div class="grand-summary">
                        <div class="stat-card">
                            <div class="number">{total_processed}</div>
                            <div class="label">Total Processed</div>
                        </div>
                        <div class="stat-card">
                            <div class="number">{total_added}</div>
                            <div class="label">Total Added to KB</div>
                        </div>
                        <div class="stat-card">
                            <div class="number">{total_alerts}</div>
                            <div class="label">Alerts</div>
                        </div>
                        <div class="stat-card">
                            <div class="number">{len(env_reports)}</div>
                            <div class="label">Environments</div>
                        </div>
                    </div>

                    {env_sections}
                </div>
                <div class="footer">
                    <p>Automated report from PratikoAI Ingestion Monitoring System</p>
                    <p style="font-size: 11px; color: #bbb; margin-top: 4px;">
                        Tip: If sections don't collapse in your email client, all content is shown expanded.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _build_ingestion_env_section(self, env: Environment, env_color: dict, report) -> str:
        """Build a collapsible <details> section for one environment's ingestion report.

        Args:
            env: Environment enum
            env_color: Color config dict
            report: DailyIngestionReport for this environment

        Returns:
            HTML string for one environment section
        """
        from app.services.ingestion_report_service import WoWComparison

        def wow_indicator(wow: WoWComparison | None) -> str:
            if wow is None:
                return ""
            return f'<span style="font-size: 10px; color: {wow.change_color};">({wow.change_str})</span>'

        # Alert badge
        alert_badge = ""
        alert_count = len(report.alerts)
        if alert_count > 0:
            high_count = sum(1 for a in report.alerts if a.severity.value == "HIGH")
            if high_count > 0:
                alert_badge = f'<span class="alert-badge" style="background: #dc3545; color: white;">&#x1F534; {alert_count} alert{"s" if alert_count > 1 else ""}</span>'
            else:
                alert_badge = f'<span class="alert-badge" style="background: #ffc107; color: #333;">&#x1F7E0; {alert_count} alert{"s" if alert_count > 1 else ""}</span>'

        # Determine success rate color
        success_rate = report.overall_success_rate
        rate_color = "#28a745" if success_rate >= 90 else "#ffc107" if success_rate >= 70 else "#dc3545"

        # Summary metrics for the collapsed header
        summary_text = (
            f"{report.total_documents_processed} processed, "
            f"{report.total_documents_added} added, "
            f'<span style="color: {rate_color};">{success_rate:.0f}% success</span>'
        )

        # RSS table
        rss_rows = ""
        for source in report.rss_sources:
            s_color = "#28a745" if source.success_rate >= 90 else "#ffc107" if source.success_rate >= 70 else "#dc3545"
            rss_rows += f"""
                <tr>
                    <td>{source.source_name}</td>
                    <td>{source.documents_processed}</td>
                    <td style="color: {s_color}">{source.documents_succeeded}</td>
                    <td>{source.documents_failed}</td>
                    <td>{source.documents_added_to_db}</td>
                    <td>{source.junk_percentage:.1f}%</td>
                </tr>
            """
        if not rss_rows:
            rss_rows = '<tr><td colspan="6" style="text-align: center; color: #666;">No RSS activity</td></tr>'

        # Scraper table
        scraper_rows = ""
        for source in report.scraper_sources:
            s_color = "#28a745" if source.success_rate >= 90 else "#ffc107" if source.success_rate >= 70 else "#dc3545"
            scraper_rows += f"""
                <tr>
                    <td>{source.source_name}</td>
                    <td>{source.documents_processed}</td>
                    <td style="color: {s_color}">{source.documents_succeeded}</td>
                    <td>{source.documents_failed}</td>
                    <td>{source.documents_added_to_db}</td>
                    <td>{source.junk_percentage:.1f}%</td>
                </tr>
            """
        if not scraper_rows:
            scraper_rows = '<tr><td colspan="6" style="text-align: center; color: #666;">No scraper activity</td></tr>'

        # Alerts
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
                    <h3>Alerts ({alert_count})</h3>
                    <table>
                        <thead><tr><th>Severity</th><th>Type</th><th>Source</th><th>Message</th></tr></thead>
                        <tbody>{alert_rows}</tbody>
                    </table>
                </div>
            """

        # New document previews
        docs_html = ""
        if report.new_document_previews:
            doc_rows = ""
            for doc in report.new_document_previews[:10]:
                doc_rows += f"<tr><td>{doc.source}</td><td>{doc.title}</td></tr>"
            docs_html = f"""
                <div class="section">
                    <h3>New Documents</h3>
                    <table>
                        <thead><tr><th>Source</th><th>Title</th></tr></thead>
                        <tbody>{doc_rows}</tbody>
                    </table>
                </div>
            """

        # Error samples
        errors_html = ""
        if report.error_samples:
            error_rows = ""
            for sample in report.error_samples:
                messages = "<br>".join([f"&bull; {msg}" for msg in sample.sample_messages])
                error_rows += f"""
                    <tr>
                        <td>{sample.source_name}</td>
                        <td style="color: #dc3545;">{sample.error_count}</td>
                        <td style="font-size: 12px;">{messages}</td>
                    </tr>
                """
            errors_html = f"""
                <div class="section">
                    <h3>Error Details</h3>
                    <table>
                        <thead><tr><th>Source</th><th>Count</th><th>Sample Messages</th></tr></thead>
                        <tbody>{error_rows}</tbody>
                    </table>
                </div>
            """

        # Filtered content
        filtered_html = ""
        if report.filtered_content_samples:
            total_filtered = sum(s.items_filtered for s in report.filtered_content_samples)
            filtered_rows = ""
            for fs in report.filtered_content_samples:
                titles = "<br>".join([f"&bull; {t}" for t in fs.sample_titles])
                if not titles:
                    titles = "<em style='color: #999;'>No samples</em>"
                filtered_rows += f"""
                    <tr>
                        <td>{fs.source_name}</td>
                        <td>{fs.items_filtered}</td>
                        <td style="font-size: 12px;">{titles}</td>
                    </tr>
                """
            filtered_html = f"""
                <div class="section">
                    <h3>Filtered Content ({total_filtered} items)</h3>
                    <table>
                        <thead><tr><th>Source</th><th>Filtered</th><th>Samples</th></tr></thead>
                        <tbody>{filtered_rows}</tbody>
                    </table>
                </div>
            """

        # Data quality
        dq_html = ""
        if report.data_quality:
            dq_html = self._build_data_quality_html(report.data_quality)

        return f"""
            <details>
                <summary>
                    <span class="env-badge" style="background-color: {env_color["bg"]};">{env_color["name"]}</span>
                    <span class="summary-metrics">{summary_text}</span>
                    {alert_badge}
                </summary>
                <div class="env-content">
                    <div class="summary-row">
                        <div class="mini-card">
                            <div class="number">{report.total_documents_processed}</div>
                            <div class="label">Processed</div>
                            <div class="wow">{wow_indicator(report.wow_documents_processed)}</div>
                        </div>
                        <div class="mini-card">
                            <div class="number">{report.total_documents_added}</div>
                            <div class="label">Added to KB</div>
                            <div class="wow">{wow_indicator(report.wow_documents_added)}</div>
                        </div>
                        <div class="mini-card">
                            <div class="number" style="color: {rate_color}">{success_rate:.1f}%</div>
                            <div class="label">Success Rate</div>
                            <div class="wow">{wow_indicator(report.wow_success_rate)}</div>
                        </div>
                        <div class="mini-card">
                            <div class="number">{report.overall_junk_rate:.1f}%</div>
                            <div class="label">Junk Rate</div>
                            <div class="wow">{wow_indicator(report.wow_junk_rate)}</div>
                        </div>
                    </div>

                    {alerts_html}

                    <div class="section">
                        <h3>RSS Feeds ({len(report.rss_sources)} sources)</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Source</th><th>Processed</th><th>Success</th>
                                    <th>Failed</th><th>Added to KB</th><th>Junk %</th>
                                </tr>
                            </thead>
                            <tbody>{rss_rows}</tbody>
                        </table>
                    </div>

                    <div class="section">
                        <h3>Web Scrapers ({len(report.scraper_sources)} sources)</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Source</th><th>Processed</th><th>Success</th>
                                    <th>Failed</th><th>Added to KB</th><th>Junk %</th>
                                </tr>
                            </thead>
                            <tbody>{scraper_rows}</tbody>
                        </table>
                    </div>

                    {docs_html}
                    {errors_html}
                    {filtered_html}
                    {dq_html}
                </div>
            </details>
        """

    def _build_data_quality_html(self, dq) -> str:
        """Build data quality section HTML.

        Args:
            dq: DataQualitySummary instance

        Returns:
            HTML string
        """

        def _status(value: int, threshold: int = 0) -> str:
            if value <= threshold:
                return '<span style="color: #28a745;">OK</span>'
            return f'<span style="color: #dc3545;">{value}</span>'

        rows = f"""
            <tr><td>Total Items</td><td>{dq.total_items}</td><td>-</td></tr>
            <tr><td>Total Chunks</td><td>{dq.total_chunks}</td><td>-</td></tr>
            <tr><td>URL Duplicate Groups</td><td>{dq.url_duplicate_groups}</td><td>{_status(dq.url_duplicate_groups)}</td></tr>
            <tr><td>Navigation Contaminated</td><td>{dq.navigation_contaminated_chunks}</td><td>{_status(dq.navigation_contaminated_chunks, 10)}</td></tr>
            <tr><td>Items Missing Embedding</td><td>{dq.items_missing_embedding}</td><td>{_status(dq.items_missing_embedding)}</td></tr>
            <tr><td>Chunks Missing Embedding</td><td>{dq.chunks_missing_embedding}</td><td>{_status(dq.chunks_missing_embedding)}</td></tr>
        """

        return f"""
            <div class="section">
                <h3>Data Quality</h3>
                <table>
                    <thead><tr><th>Metric</th><th>Count</th><th>Status</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        """

    # =========================================================================
    # Cost Report
    # =========================================================================

    async def send_consolidated_cost_report(self, recipients: list[str]) -> bool:
        """Generate and send consolidated cost report across all environments.

        Args:
            recipients: Email recipients

        Returns:
            True if sent successfully
        """
        from app.services.daily_cost_report_service import DailyCostReport

        if not recipients:
            self.logger.warning("consolidated_cost_report_no_recipients")
            return False

        report_date = (datetime.now(UTC) - timedelta(days=1)).date()
        env_reports: dict[Environment, DailyCostReport] = {}

        for config in self.active_configs:
            try:
                session = await self._create_session(config)
                async with session:
                    report = await self._generate_cost_report_for_session(session)
                    env_reports[config.environment] = report
            except Exception as e:
                self.logger.error(
                    "consolidated_cost_report_env_failed",
                    extra={
                        "environment": config.environment.value,
                        "error": str(e),
                    },
                )

        total_cost = sum(r.total_cost_eur for r in env_reports.values())
        has_alerts = any(len(r.alerts) > 0 for r in env_reports.values())

        html = self._generate_consolidated_cost_html(env_reports, report_date)
        subject = self._get_cost_subject(report_date, total_cost, has_alerts)

        return self._send_email(recipients, subject, html)

    async def _generate_cost_report_for_session(self, session):
        """Generate cost report using a specific DB session.

        Args:
            session: AsyncSession for the target environment

        Returns:
            DailyCostReport
        """
        from app.services.daily_cost_report_service import DailyCostReportService

        service = DailyCostReportService(session)
        return await service.generate_report()

    def _get_cost_subject(self, report_date: date, total_cost: float, has_alerts: bool) -> str:
        """Generate email subject for consolidated cost report."""
        subject = f"PratikoAI Daily Cost Report - {report_date.isoformat()} - €{total_cost:.2f}"
        if has_alerts:
            subject = f"⚠️ {subject}"
        return subject

    def _generate_consolidated_cost_html(
        self,
        env_reports: dict,
        report_date: date,
    ) -> str:
        """Generate consolidated cost report HTML with collapsible sections.

        Args:
            env_reports: Dict mapping Environment to DailyCostReport
            report_date: Report date

        Returns:
            Complete HTML string
        """
        from app.services.daily_cost_report_service import get_environment_color

        # Grand totals
        grand_total_cost = sum(r.total_cost_eur for r in env_reports.values())
        grand_total_requests = sum(r.total_requests for r in env_reports.values())
        grand_total_users = sum(r.unique_users for r in env_reports.values())

        # Build environment sections
        env_sections = ""
        for env in DISPLAY_ORDER:
            env_color = ENVIRONMENT_COLORS[env]
            report = env_reports.get(env)

            if report is not None:
                env_sections += self._build_cost_env_section(env, env_color, report)
            else:
                env_sections += self._build_placeholder_section(env, env_color, "cost")

        generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>PratikoAI Consolidated Daily Cost Report</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px 12px 0 0; }}
                .header h1 {{ margin: 0; font-size: 22px; }}
                .header p {{ margin: 5px 0 0 0; opacity: 0.9; font-size: 14px; }}
                .content {{ padding: 20px; }}
                .grand-summary {{ display: flex; flex-wrap: wrap; justify-content: space-around; gap: 12px; margin-bottom: 20px; }}
                .grand-summary .stat-card {{ text-align: center; padding: 12px; background: #f8f9fa; border-radius: 8px; min-width: 120px; flex: 1; }}
                .grand-summary .number {{ font-size: 24px; font-weight: bold; color: #333; }}
                .grand-summary .label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                details {{ margin-bottom: 12px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }}
                summary {{ cursor: pointer; padding: 14px 18px; background: #f8f9fa; font-weight: 600; font-size: 15px; list-style: none; display: flex; align-items: center; gap: 10px; }}
                summary::-webkit-details-marker {{ display: none; }}
                summary::before {{ content: "▶"; font-size: 12px; transition: transform 0.2s; color: #666; }}
                details[open] summary::before {{ transform: rotate(90deg); }}
                .env-badge {{ display: inline-block; color: white; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
                .env-content {{ padding: 15px 18px; }}
                .summary-metrics {{ color: #666; font-size: 13px; font-weight: normal; margin-left: auto; }}
                .section {{ margin-bottom: 20px; }}
                .section h3 {{ margin-bottom: 10px; color: #333; font-size: 15px; border-bottom: 1px solid #667eea; padding-bottom: 6px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #eee; font-size: 13px; }}
                th {{ background-color: #f8f9fa; font-weight: 600; }}
                .summary-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 15px; }}
                .mini-card {{ text-align: center; padding: 10px; background: #f8f9fa; border-radius: 6px; min-width: 100px; flex: 1; }}
                .mini-card .number {{ font-size: 20px; font-weight: bold; color: #333; }}
                .mini-card .label {{ font-size: 11px; color: #666; }}
                .alert-badge {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 600; margin-left: 8px; }}
                .footer {{ text-align: center; padding: 15px; color: #666; font-size: 12px; border-top: 1px solid #eee; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Daily Cost Report</h1>
                    <p>{report_date.strftime("%A, %B %d, %Y")} | Generated: {generated_at}</p>
                    <p style="margin-top: 8px; font-size: 13px; opacity: 0.8;">
                        Consolidated view across all environments. Click each section to expand.
                    </p>
                </div>
                <div class="content">
                    <div class="grand-summary">
                        <div class="stat-card">
                            <div class="number">€{grand_total_cost:.2f}</div>
                            <div class="label">Total Cost</div>
                        </div>
                        <div class="stat-card">
                            <div class="number">{grand_total_requests:,}</div>
                            <div class="label">Total Requests</div>
                        </div>
                        <div class="stat-card">
                            <div class="number">{grand_total_users}</div>
                            <div class="label">Unique Users</div>
                        </div>
                    </div>

                    {env_sections}
                </div>
                <div class="footer">
                    Generated by PratikoAI Cost Monitoring | Target: €2/user/month
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _build_cost_env_section(self, env: Environment, env_color: dict, report) -> str:
        """Build a collapsible <details> section for one environment's cost report.

        Args:
            env: Environment enum
            env_color: Color config dict
            report: DailyCostReport for this environment

        Returns:
            HTML string
        """
        # Alert badge
        alert_badge = ""
        if report.alerts:
            alert_badge = f'<span class="alert-badge" style="background: #ffc107; color: #333;">⚠️ {len(report.alerts)} alert{"s" if len(report.alerts) > 1 else ""}</span>'

        summary_text = (
            f"€{report.total_cost_eur:.2f} | {report.total_requests:,} requests | {report.unique_users} users"
        )

        # User breakdown rows
        user_rows = ""
        for user in report.user_breakdown:
            pct = user.percentage_of_total(report.total_cost_eur)
            user_rows += f"""
                <tr>
                    <td>{user.user_id}</td>
                    <td style="text-align: right;">€{user.total_cost_eur:.2f}</td>
                    <td style="text-align: right;">{pct:.1f}%</td>
                    <td style="text-align: right;">{user.request_count:,}</td>
                    <td style="text-align: right;">{user.total_tokens:,}</td>
                </tr>
            """
        if not user_rows:
            user_rows = '<tr><td colspan="5" style="text-align: center; color: #666;">No user data</td></tr>'

        # Third-party rows
        tp_rows = ""
        for tp in report.third_party_breakdown:
            tp_rows += f"""
                <tr>
                    <td>{tp.api_type}</td>
                    <td style="text-align: right;">€{tp.total_cost_eur:.4f}</td>
                    <td style="text-align: right;">{tp.request_count:,}</td>
                    <td style="text-align: right;">€{tp.avg_cost_per_request:.4f}</td>
                </tr>
            """
        if not tp_rows:
            tp_rows = '<tr><td colspan="4" style="text-align: center; color: #666;">No third-party usage</td></tr>'

        # Cost alerts
        alerts_html = ""
        if report.alerts:
            alert_items = ""
            for alert in report.alerts:
                sev_color = {"HIGH": "#dc3545", "MEDIUM": "#ffc107", "LOW": "#17a2b8"}.get(alert.severity, "#6c757d")
                alert_items += f'<li style="color: {sev_color};">{alert.message}</li>'
            alerts_html = f"""
                <div style="margin-bottom: 15px; padding: 10px; background-color: #fff3cd; border-radius: 6px; border-left: 3px solid #ffc107;">
                    <strong>⚠️ Cost Alerts</strong>
                    <ul style="margin: 5px 0 0 0; padding-left: 20px;">{alert_items}</ul>
                </div>
            """

        return f"""
            <details>
                <summary>
                    <span class="env-badge" style="background-color: {env_color["bg"]};">{env_color["name"]}</span>
                    <span class="summary-metrics">{summary_text}</span>
                    {alert_badge}
                </summary>
                <div class="env-content">
                    {alerts_html}

                    <div class="summary-row">
                        <div class="mini-card">
                            <div class="number">€{report.total_cost_eur:.2f}</div>
                            <div class="label">Total Cost</div>
                        </div>
                        <div class="mini-card">
                            <div class="number">€{report.llm_cost_eur:.2f}</div>
                            <div class="label">LLM Inference</div>
                        </div>
                        <div class="mini-card">
                            <div class="number">€{report.third_party_cost_eur:.4f}</div>
                            <div class="label">Third-Party</div>
                        </div>
                        <div class="mini-card">
                            <div class="number">{report.total_tokens:,}</div>
                            <div class="label">Tokens</div>
                        </div>
                    </div>

                    <div class="section">
                        <h3>Top Users by Cost</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th style="text-align: right;">Cost</th>
                                    <th style="text-align: right;">%</th>
                                    <th style="text-align: right;">Requests</th>
                                    <th style="text-align: right;">Tokens</th>
                                </tr>
                            </thead>
                            <tbody>{user_rows}</tbody>
                        </table>
                    </div>

                    <div class="section">
                        <h3>Third-Party APIs</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>API Type</th>
                                    <th style="text-align: right;">Cost</th>
                                    <th style="text-align: right;">Requests</th>
                                    <th style="text-align: right;">Avg/Request</th>
                                </tr>
                            </thead>
                            <tbody>{tp_rows}</tbody>
                        </table>
                    </div>
                </div>
            </details>
        """

    # =========================================================================
    # Shared Helpers
    # =========================================================================

    def _build_placeholder_section(self, env: Environment, env_color: dict, report_type: str) -> str:
        """Build a placeholder section for an environment without data.

        Args:
            env: Environment enum
            env_color: Color config dict
            report_type: "ingestion" or "cost"

        Returns:
            HTML string
        """
        return f"""
            <details>
                <summary>
                    <span class="env-badge" style="background-color: {env_color["bg"]};">{env_color["name"]}</span>
                    <span class="summary-metrics" style="color: #999;">Not yet provisioned</span>
                </summary>
                <div class="env-content">
                    <p style="color: #999; text-align: center; padding: 20px;">
                        {env_color["name"]} environment is not yet provisioned.
                        Configure <code>CONSOLIDATED_REPORT_{env_color["prefix"]}_DB_URL</code> to enable.
                    </p>
                </div>
            </details>
        """

    async def _create_session(self, config: EnvironmentReportConfig):
        """Create an async DB session for an environment.

        Args:
            config: Environment report config

        Returns:
            AsyncSession
        """
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_async_engine(
            config.async_postgres_url,
            echo=False,
            pool_pre_ping=True,
        )
        async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        session = async_session_maker()
        # Store engine ref on session for cleanup
        session._engine_ref = engine  # type: ignore[attr-defined]
        return session

    def _send_email(self, recipients: list[str], subject: str, html_content: str) -> bool:
        """Send email via SMTP.

        Args:
            recipients: Email recipients
            subject: Email subject
            html_content: HTML body

        Returns:
            True if sent successfully
        """
        if not recipients:
            self.logger.warning("No recipients for consolidated report")
            return False

        if not self.smtp_username or not self.smtp_password:
            self.logger.warning("SMTP credentials not configured for consolidated report")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = Header(subject, "utf-8")
            msg["From"] = self.from_email
            msg["To"] = ", ".join(recipients)

            html_part = MIMEText(html_content, "html", _charset="utf-8")
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg, self.from_email, recipients)

            self.logger.info(
                "consolidated_report_sent",
                extra={
                    "subject": subject,
                    "recipients_count": len(recipients),
                },
            )
            return True

        except Exception as e:
            self.logger.error(
                "consolidated_report_send_failed",
                extra={"error": str(e)},
            )
            return False
