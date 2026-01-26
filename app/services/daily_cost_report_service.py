# mypy: disable-error-code="arg-type,call-overload,misc,assignment"
"""Daily Cost Report Service for DEV-246.

This service generates daily cost reports showing spending breakdown by environment,
user, and third-party API usage (e.g., Brave Search). Designed to maintain
the €2/user/month target.

DEV-246: Daily Cost Spending Report by Environment and User
"""

import logging
import smtplib
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Environment, get_environment, settings
from app.models.usage import CostCategory, UsageEvent, UsageType

logger = logging.getLogger(__name__)


# =============================================================================
# Alert System Types
# =============================================================================


@dataclass
class CostAlert:
    """Alert for cost threshold violations."""

    alert_type: str  # DAILY_THRESHOLD_EXCEEDED, USER_THRESHOLD_EXCEEDED, etc.
    severity: str  # HIGH, MEDIUM, LOW
    message: str
    environment: str | None = None
    current_cost: float = 0.0
    threshold: float = 0.0
    user_id: str | None = None


# =============================================================================
# Cost Breakdown Types
# =============================================================================


@dataclass
class EnvironmentCostBreakdown:
    """Cost breakdown for a specific environment."""

    environment: str
    total_cost_eur: float = 0.0
    llm_cost_eur: float = 0.0
    third_party_cost_eur: float = 0.0
    request_count: int = 0
    total_tokens: int = 0
    unique_users: int = 0


@dataclass
class UserCostBreakdown:
    """Cost breakdown for a specific user."""

    user_id: str
    total_cost_eur: float = 0.0
    llm_cost_eur: float = 0.0
    third_party_cost_eur: float = 0.0
    request_count: int = 0
    total_tokens: int = 0

    def percentage_of_total(self, total: float) -> float:
        """Calculate percentage of total cost."""
        if total <= 0:
            return 0.0
        return (self.total_cost_eur / total) * 100


@dataclass
class ThirdPartyCostBreakdown:
    """Cost breakdown for a third-party API."""

    api_type: str
    total_cost_eur: float = 0.0
    request_count: int = 0

    @property
    def avg_cost_per_request(self) -> float:
        """Calculate average cost per request."""
        if self.request_count <= 0:
            return 0.0
        return self.total_cost_eur / self.request_count


# =============================================================================
# Environment Color Mapping
# =============================================================================

ENVIRONMENT_COLORS = {
    "development": {"bg": "#6c757d", "name": "Development", "prefix": "DEV"},
    "qa": {"bg": "#007bff", "name": "QA", "prefix": "QA"},
    "production": {"bg": "#28a745", "name": "Production", "prefix": "PROD"},
}


def get_environment_color(env: str) -> dict[str, str]:
    """Get color configuration for an environment."""
    return ENVIRONMENT_COLORS.get(
        env.lower(),
        {"bg": "#6c757d", "name": env.upper(), "prefix": env[:3].upper()},
    )


# =============================================================================
# Daily Cost Report
# =============================================================================


@dataclass
class DailyCostReport:
    """Complete daily cost report."""

    report_date: date
    total_cost_eur: float = 0.0
    llm_cost_eur: float = 0.0
    third_party_cost_eur: float = 0.0
    total_requests: int = 0
    total_tokens: int = 0
    unique_users: int = 0
    environment_breakdown: list[EnvironmentCostBreakdown] = field(default_factory=list)
    user_breakdown: list[UserCostBreakdown] = field(default_factory=list)
    third_party_breakdown: list[ThirdPartyCostBreakdown] = field(default_factory=list)
    alerts: list[CostAlert] = field(default_factory=list)


# =============================================================================
# Cost Thresholds
# =============================================================================

COST_THRESHOLDS = {
    "development": {
        "daily_total": 10.0,  # €10/day warning for dev
        "per_user": 1.0,  # €1/user/day for dev
    },
    "qa": {
        "daily_total": 25.0,  # €25/day warning for QA
        "per_user": 2.0,  # €2/user/day for QA
    },
    "production": {
        "daily_total": 50.0,  # €50/day warning for prod
        "per_user": 2.0,  # €2/user/day for prod (matching monthly target)
    },
}


# =============================================================================
# Daily Cost Report Service
# =============================================================================


class DailyCostReportService:
    """Service to generate and send daily cost reports."""

    def __init__(self, db: AsyncSession):
        """Initialize the service.

        Args:
            db: Async database session
        """
        self.db = db
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD

    async def generate_report(self, report_date: date | None = None) -> DailyCostReport:
        """Generate daily cost report.

        Args:
            report_date: Date to generate report for (defaults to yesterday)

        Returns:
            DailyCostReport with all breakdowns
        """
        if report_date is None:
            report_date = (datetime.now(UTC) - timedelta(days=1)).date()

        # Get date range for the report day
        start_dt = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)
        end_dt = datetime.combine(report_date, datetime.max.time()).replace(tzinfo=UTC)

        # Get totals
        totals = await self._get_totals(start_dt, end_dt)

        # Get breakdowns
        environment_breakdown = await self._get_environment_breakdown(report_date)
        user_breakdown = await self._get_user_breakdown(report_date, limit=10)
        third_party_breakdown = await self._get_third_party_breakdown(report_date)

        # Generate alerts
        alerts = self._generate_alerts(totals, environment_breakdown, user_breakdown)

        return DailyCostReport(
            report_date=report_date,
            total_cost_eur=totals.get("total_cost", 0.0),
            llm_cost_eur=totals.get("llm_cost", 0.0),
            third_party_cost_eur=totals.get("third_party_cost", 0.0),
            total_requests=totals.get("total_requests", 0),
            total_tokens=totals.get("total_tokens", 0),
            unique_users=totals.get("unique_users", 0),
            environment_breakdown=environment_breakdown,
            user_breakdown=user_breakdown,
            third_party_breakdown=third_party_breakdown,
            alerts=alerts,
        )

    async def _get_totals(self, start_dt: datetime, end_dt: datetime) -> dict[str, Any]:
        """Get total costs for the period.

        Args:
            start_dt: Start datetime
            end_dt: End datetime

        Returns:
            Dictionary with total costs
        """
        query = select(
            func.coalesce(func.sum(UsageEvent.cost_eur), 0).label("total_cost"),
            func.coalesce(
                func.sum(
                    case(
                        (UsageEvent.cost_category == CostCategory.LLM_INFERENCE, UsageEvent.cost_eur),
                        else_=0,
                    )
                ),
                0,
            ).label("llm_cost"),
            func.coalesce(
                func.sum(
                    case(
                        (UsageEvent.cost_category == CostCategory.THIRD_PARTY, UsageEvent.cost_eur),
                        else_=0,
                    )
                ),
                0,
            ).label("third_party_cost"),
            func.count(UsageEvent.id).label("total_requests"),
            func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("total_tokens"),
            func.count(func.distinct(UsageEvent.user_id)).label("unique_users"),
        ).where(
            and_(
                UsageEvent.timestamp >= start_dt,
                UsageEvent.timestamp <= end_dt,
            )
        )

        result = await self.db.execute(query)
        row = result.first()

        if row:
            return {
                "total_cost": float(row[0] or 0),
                "llm_cost": float(row[1] or 0),
                "third_party_cost": float(row[2] or 0),
                "total_requests": int(row[3] or 0),
                "total_tokens": int(row[4] or 0),
                "unique_users": int(row[5] or 0),
            }

        return {
            "total_cost": 0.0,
            "llm_cost": 0.0,
            "third_party_cost": 0.0,
            "total_requests": 0,
            "total_tokens": 0,
            "unique_users": 0,
        }

    async def _get_environment_breakdown(self, report_date: date) -> list[EnvironmentCostBreakdown]:
        """Get cost breakdown by environment.

        Args:
            report_date: Date to get breakdown for

        Returns:
            List of EnvironmentCostBreakdown
        """
        start_dt = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)
        end_dt = datetime.combine(report_date, datetime.max.time()).replace(tzinfo=UTC)

        query = (
            select(
                UsageEvent.environment,
                func.coalesce(func.sum(UsageEvent.cost_eur), 0).label("total_cost"),
                func.coalesce(
                    func.sum(
                        case(
                            (UsageEvent.cost_category == CostCategory.LLM_INFERENCE, UsageEvent.cost_eur),
                            else_=0,
                        )
                    ),
                    0,
                ).label("llm_cost"),
                func.coalesce(
                    func.sum(
                        case(
                            (UsageEvent.cost_category == CostCategory.THIRD_PARTY, UsageEvent.cost_eur),
                            else_=0,
                        )
                    ),
                    0,
                ).label("third_party_cost"),
                func.count(UsageEvent.id).label("request_count"),
                func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("total_tokens"),
                func.count(func.distinct(UsageEvent.user_id)).label("unique_users"),
            )
            .where(
                and_(
                    UsageEvent.timestamp >= start_dt,
                    UsageEvent.timestamp <= end_dt,
                    UsageEvent.environment.isnot(None),  # type: ignore[union-attr]
                )
            )
            .group_by(UsageEvent.environment)
            .order_by(func.sum(UsageEvent.cost_eur).desc())
        )

        result = await self.db.execute(query)
        rows = result.all()

        breakdowns = []
        for row in rows:
            breakdowns.append(
                EnvironmentCostBreakdown(
                    environment=row[0] or "unknown",
                    total_cost_eur=float(row[1] or 0),
                    llm_cost_eur=float(row[2] or 0),
                    third_party_cost_eur=float(row[3] or 0),
                    request_count=int(row[4] or 0),
                    total_tokens=int(row[5] or 0),
                    unique_users=int(row[6] or 0),
                )
            )

        return breakdowns

    async def _get_user_breakdown(self, report_date: date, limit: int = 10) -> list[UserCostBreakdown]:
        """Get cost breakdown by user (top N users).

        Args:
            report_date: Date to get breakdown for
            limit: Maximum number of users to return

        Returns:
            List of UserCostBreakdown sorted by cost descending
        """
        start_dt = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)
        end_dt = datetime.combine(report_date, datetime.max.time()).replace(tzinfo=UTC)

        query = (
            select(
                UsageEvent.user_id,
                func.coalesce(func.sum(UsageEvent.cost_eur), 0).label("total_cost"),
                func.coalesce(
                    func.sum(
                        case(
                            (UsageEvent.cost_category == CostCategory.LLM_INFERENCE, UsageEvent.cost_eur),
                            else_=0,
                        )
                    ),
                    0,
                ).label("llm_cost"),
                func.coalesce(
                    func.sum(
                        case(
                            (UsageEvent.cost_category == CostCategory.THIRD_PARTY, UsageEvent.cost_eur),
                            else_=0,
                        )
                    ),
                    0,
                ).label("third_party_cost"),
                func.count(UsageEvent.id).label("request_count"),
                func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("total_tokens"),
            )
            .where(
                and_(
                    UsageEvent.timestamp >= start_dt,
                    UsageEvent.timestamp <= end_dt,
                )
            )
            .group_by(UsageEvent.user_id)
            .order_by(func.sum(UsageEvent.cost_eur).desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        breakdowns = []
        for row in rows:
            breakdowns.append(
                UserCostBreakdown(
                    user_id=str(row[0] or "unknown"),
                    total_cost_eur=float(row[1] or 0),
                    llm_cost_eur=float(row[2] or 0),
                    third_party_cost_eur=float(row[3] or 0),
                    request_count=int(row[4] or 0),
                    total_tokens=int(row[5] or 0),
                )
            )

        return breakdowns

    async def _get_third_party_breakdown(self, report_date: date) -> list[ThirdPartyCostBreakdown]:
        """Get cost breakdown by third-party API type.

        Args:
            report_date: Date to get breakdown for

        Returns:
            List of ThirdPartyCostBreakdown
        """
        start_dt = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)
        end_dt = datetime.combine(report_date, datetime.max.time()).replace(tzinfo=UTC)

        query = (
            select(
                UsageEvent.api_type,
                func.coalesce(func.sum(UsageEvent.cost_eur), 0).label("total_cost"),
                func.count(UsageEvent.id).label("request_count"),
            )
            .where(
                and_(
                    UsageEvent.timestamp >= start_dt,
                    UsageEvent.timestamp <= end_dt,
                    UsageEvent.cost_category == CostCategory.THIRD_PARTY,
                    UsageEvent.api_type.isnot(None),  # type: ignore[union-attr]
                )
            )
            .group_by(UsageEvent.api_type)
            .order_by(func.sum(UsageEvent.cost_eur).desc())
        )

        result = await self.db.execute(query)
        rows = result.all()

        breakdowns = []
        for row in rows:
            breakdowns.append(
                ThirdPartyCostBreakdown(
                    api_type=row[0] or "unknown",
                    total_cost_eur=float(row[1] or 0),
                    request_count=int(row[2] or 0),
                )
            )

        return breakdowns

    def _generate_alerts(
        self,
        totals: dict[str, Any],
        environment_breakdown: list[EnvironmentCostBreakdown],
        user_breakdown: list[UserCostBreakdown],
    ) -> list[CostAlert]:
        """Generate cost alerts based on thresholds.

        Args:
            totals: Total costs dictionary
            environment_breakdown: Environment breakdowns
            user_breakdown: User breakdowns

        Returns:
            List of CostAlert
        """
        alerts = []

        # Check environment thresholds
        for env_cost in environment_breakdown:
            env_thresholds = COST_THRESHOLDS.get(env_cost.environment.lower(), {})
            daily_threshold = env_thresholds.get("daily_total", 50.0)

            if env_cost.total_cost_eur > daily_threshold:
                alerts.append(
                    CostAlert(
                        alert_type="DAILY_THRESHOLD_EXCEEDED",
                        severity="HIGH",
                        message=f"Daily cost for {env_cost.environment} exceeded €{daily_threshold:.2f} threshold",
                        environment=env_cost.environment,
                        current_cost=env_cost.total_cost_eur,
                        threshold=daily_threshold,
                    )
                )

        # Check user thresholds (using production threshold as default)
        per_user_threshold = COST_THRESHOLDS.get("production", {}).get("per_user", 2.0)
        for user_cost in user_breakdown:
            if user_cost.total_cost_eur > per_user_threshold:
                alerts.append(
                    CostAlert(
                        alert_type="USER_THRESHOLD_EXCEEDED",
                        severity="MEDIUM",
                        message=f"User {user_cost.user_id} exceeded €{per_user_threshold:.2f}/day threshold",
                        current_cost=user_cost.total_cost_eur,
                        threshold=per_user_threshold,
                        user_id=user_cost.user_id,
                    )
                )

        return alerts

    def _generate_html_report(self, report: DailyCostReport) -> str:
        """Generate HTML report content.

        Args:
            report: DailyCostReport to render

        Returns:
            HTML string
        """
        current_env = get_environment()
        env_color = get_environment_color(current_env.value)

        # Build environment breakdown rows
        env_rows = ""
        for env in report.environment_breakdown:
            env_c = get_environment_color(env.environment)
            env_rows += f"""
            <tr>
                <td><span style="background-color: {env_c['bg']}; color: white; padding: 2px 8px; border-radius: 4px;">{env.environment.upper()}</span></td>
                <td style="text-align: right;">€{env.total_cost_eur:.2f}</td>
                <td style="text-align: right;">€{env.llm_cost_eur:.2f}</td>
                <td style="text-align: right;">€{env.third_party_cost_eur:.2f}</td>
                <td style="text-align: right;">{env.request_count:,}</td>
                <td style="text-align: right;">{env.unique_users}</td>
            </tr>
            """

        # Build user breakdown rows
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

        # Build third-party breakdown rows
        third_party_rows = ""
        for tp in report.third_party_breakdown:
            third_party_rows += f"""
            <tr>
                <td>{tp.api_type}</td>
                <td style="text-align: right;">€{tp.total_cost_eur:.2f}</td>
                <td style="text-align: right;">{tp.request_count:,}</td>
                <td style="text-align: right;">€{tp.avg_cost_per_request:.4f}</td>
            </tr>
            """

        # Build alerts section
        alerts_html = ""
        if report.alerts:
            alerts_html = """
            <div style="margin: 20px 0; padding: 15px; background-color: #fff3cd; border-radius: 8px; border-left: 4px solid #ffc107;">
                <h3 style="margin: 0 0 10px 0; color: #856404;">⚠️ Cost Alerts</h3>
                <ul style="margin: 0; padding-left: 20px;">
            """
            for alert in report.alerts:
                severity_color = {"HIGH": "#dc3545", "MEDIUM": "#ffc107", "LOW": "#17a2b8"}.get(
                    alert.severity, "#6c757d"
                )
                alerts_html += f'<li style="color: {severity_color};">{alert.message}</li>'
            alerts_html += "</ul></div>"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Daily Cost Report - {report.report_date}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .header {{ background-color: {env_color['bg']}; color: white; padding: 20px; border-radius: 12px 12px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .header p {{ margin: 5px 0 0 0; opacity: 0.9; }}
        .content {{ padding: 20px; }}
        .summary {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 28px; font-weight: bold; color: #333; }}
        .stat-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        h2 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 25px; }}
        .footer {{ text-align: center; padding: 15px; color: #666; font-size: 12px; border-top: 1px solid #eee; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Daily Cost Report</h1>
            <p>{report.report_date.strftime('%A, %B %d, %Y')} | Environment: {env_color['name']}</p>
        </div>
        <div class="content">
            {alerts_html}

            <div class="summary">
                <div class="stat-card">
                    <div class="stat-value">€{report.total_cost_eur:.2f}</div>
                    <div class="stat-label">Total Cost</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{report.total_requests:,}</div>
                    <div class="stat-label">Total Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{report.unique_users}</div>
                    <div class="stat-label">Unique Users</div>
                </div>
            </div>

            <h2>💰 Cost Breakdown by Category</h2>
            <div class="summary">
                <div class="stat-card">
                    <div class="stat-value">€{report.llm_cost_eur:.2f}</div>
                    <div class="stat-label">LLM Inference</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">€{report.third_party_cost_eur:.2f}</div>
                    <div class="stat-label">Third-Party APIs</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{report.total_tokens:,}</div>
                    <div class="stat-label">Total Tokens</div>
                </div>
            </div>

            <h2>🌍 Cost by Environment</h2>
            <table>
                <thead>
                    <tr>
                        <th>Environment</th>
                        <th style="text-align: right;">Total Cost</th>
                        <th style="text-align: right;">LLM Cost</th>
                        <th style="text-align: right;">Third-Party</th>
                        <th style="text-align: right;">Requests</th>
                        <th style="text-align: right;">Users</th>
                    </tr>
                </thead>
                <tbody>
                    {env_rows if env_rows else '<tr><td colspan="6" style="text-align: center; color: #666;">No data</td></tr>'}
                </tbody>
            </table>

            <h2>👥 Top Users by Cost</h2>
            <table>
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th style="text-align: right;">Total Cost</th>
                        <th style="text-align: right;">% of Total</th>
                        <th style="text-align: right;">Requests</th>
                        <th style="text-align: right;">Tokens</th>
                    </tr>
                </thead>
                <tbody>
                    {user_rows if user_rows else '<tr><td colspan="5" style="text-align: center; color: #666;">No data</td></tr>'}
                </tbody>
            </table>

            <h2>🔌 Third-Party API Costs</h2>
            <table>
                <thead>
                    <tr>
                        <th>API Type</th>
                        <th style="text-align: right;">Total Cost</th>
                        <th style="text-align: right;">Requests</th>
                        <th style="text-align: right;">Avg/Request</th>
                    </tr>
                </thead>
                <tbody>
                    {third_party_rows if third_party_rows else '<tr><td colspan="4" style="text-align: center; color: #666;">No third-party API usage</td></tr>'}
                </tbody>
            </table>
        </div>
        <div class="footer">
            Generated by PratikoAI Cost Monitoring | Target: €2/user/month
        </div>
    </div>
</body>
</html>
        """

        return html

    async def send_report(self, report: DailyCostReport, recipients: list[str] | None = None) -> bool:
        """Send cost report via email.

        Args:
            report: DailyCostReport to send
            recipients: List of email recipients (defaults to settings)

        Returns:
            True if email sent successfully
        """
        if recipients is None:
            recipients = getattr(settings, "DAILY_COST_REPORT_RECIPIENTS", [])

        if not recipients:
            logger.warning("daily_cost_report_no_recipients")
            return False

        try:
            current_env = get_environment()
            env_color = get_environment_color(current_env.value)

            # Build subject
            subject = (
                f"[{env_color['prefix']}] Daily Cost Report - {report.report_date} - €{report.total_cost_eur:.2f}"
            )
            if report.alerts:
                subject = f"⚠️ {subject}"

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = Header(subject, "utf-8")
            msg["From"] = self.smtp_user
            msg["To"] = ", ".join(recipients)

            # Attach HTML
            html_content = self._generate_html_report(report)
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # Send email using STARTTLS (port 587)
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg, self.smtp_user, recipients)

            logger.info(
                "daily_cost_report_sent",
                extra={
                    "report_date": str(report.report_date),
                    "total_cost": report.total_cost_eur,
                    "recipients": recipients,
                },
            )

            return True

        except Exception as e:
            logger.error(
                "daily_cost_report_send_failed",
                extra={
                    "error": str(e),
                    "report_date": str(report.report_date),
                },
            )
            return False


# Convenience function for creating service with database session
async def create_daily_cost_report_service(db: AsyncSession) -> DailyCostReportService:
    """Create DailyCostReportService with database session.

    Args:
        db: Async database session

    Returns:
        DailyCostReportService instance
    """
    return DailyCostReportService(db)
