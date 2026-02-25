"""Success Metrics Monitoring Service

This service monitors and validates all technical and business success metrics
for the PratikoAI system. Metrics are collected from the current running instance
only — not from remote environments.
"""

import logging
from dataclasses import (
    dataclass,
)
from datetime import (
    datetime,
    timedelta,
)
from enum import Enum
from typing import (
    Any,
    cast,
)

from sqlalchemy import text

from app.core.config import Environment, settings
from app.core.database import get_session
from app.core.performance.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


class MetricStatus(str, Enum):
    """Metric status enumeration."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    UNKNOWN = "UNKNOWN"


@dataclass
class MetricResult:
    """Individual metric result."""

    name: str
    value: float
    target: float
    status: MetricStatus
    unit: str
    description: str
    timestamp: datetime
    environment: Environment


@dataclass
class MetricsReport:
    """Complete metrics report."""

    environment: Environment
    timestamp: datetime
    technical_metrics: list[MetricResult]
    business_metrics: list[MetricResult]
    overall_health_score: float
    alerts: list[str]
    recommendations: list[str]


class MetricsService:
    """Success metrics monitoring and validation service."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def collect_technical_metrics(self, environment: Environment) -> list[MetricResult]:
        """Collect all technical success metrics."""
        metrics = []
        current_time = datetime.utcnow()

        # API Response Time (P95 < 500ms)
        try:
            response_time_p95 = await self._get_api_response_time_p95()
            metrics.append(
                MetricResult(
                    name="API Response Time (P95)",
                    value=response_time_p95,
                    target=500.0,
                    status=MetricStatus.PASS if response_time_p95 < 500 else MetricStatus.FAIL,
                    unit="ms",
                    description="95th percentile API response time",
                    timestamp=current_time,
                    environment=environment,
                )
            )
        except Exception as e:
            self.logger.error(f"Failed to collect API response time: {e}")
            metrics.append(
                MetricResult(
                    name="API Response Time (P95)",
                    value=0.0,
                    target=500.0,
                    status=MetricStatus.UNKNOWN,
                    unit="ms",
                    description="95th percentile API response time",
                    timestamp=current_time,
                    environment=environment,
                )
            )

        # Cache Hit Rate (> 80%)
        try:
            cache_hit_rate = await self._get_cache_hit_rate()
            metrics.append(
                MetricResult(
                    name="Cache Hit Rate",
                    value=cache_hit_rate,
                    target=80.0,
                    status=(
                        MetricStatus.PASS
                        if cache_hit_rate > 80
                        else MetricStatus.WARNING
                        if cache_hit_rate > 60
                        else MetricStatus.FAIL
                    ),
                    unit="%",
                    description="Percentage of cache hits vs total requests",
                    timestamp=current_time,
                    environment=environment,
                )
            )
        except Exception as e:
            self.logger.error(f"Failed to collect cache hit rate: {e}")
            metrics.append(
                MetricResult(
                    name="Cache Hit Rate",
                    value=0.0,
                    target=80.0,
                    status=MetricStatus.UNKNOWN,
                    unit="%",
                    description="Percentage of cache hits vs total requests",
                    timestamp=current_time,
                    environment=environment,
                )
            )

        # Test Coverage (> 80%) — CI/CD metric, not measurable at runtime
        test_coverage = await self._get_test_coverage()
        metrics.append(
            MetricResult(
                name="Test Coverage",
                value=test_coverage if test_coverage is not None else 0.0,
                target=80.0,
                status=(
                    (
                        MetricStatus.PASS
                        if test_coverage > 80
                        else MetricStatus.WARNING
                        if test_coverage > 70
                        else MetricStatus.FAIL
                    )
                    if test_coverage is not None
                    else MetricStatus.UNKNOWN
                ),
                unit="%",
                description="Code test coverage percentage (CI/CD metric)",
                timestamp=current_time,
                environment=environment,
            )
        )

        # Security Vulnerabilities (0 critical) — CI/CD metric, not measurable at runtime
        critical_vulnerabilities = await self._get_critical_vulnerabilities()
        metrics.append(
            MetricResult(
                name="Critical Security Vulnerabilities",
                value=critical_vulnerabilities if critical_vulnerabilities is not None else 0.0,
                target=0.0,
                status=(
                    (MetricStatus.PASS if critical_vulnerabilities == 0 else MetricStatus.FAIL)
                    if critical_vulnerabilities is not None
                    else MetricStatus.UNKNOWN
                ),
                unit="count",
                description="Number of critical security vulnerabilities (CI/CD metric)",
                timestamp=current_time,
                environment=environment,
            )
        )

        return metrics

    async def collect_business_metrics(self, environment: Environment) -> list[MetricResult]:
        """Collect all business success metrics."""
        metrics = []
        current_time = datetime.utcnow()

        # API Cost per User (< €2/month)
        try:
            avg_cost_per_user = await self._get_average_cost_per_user()
            metrics.append(
                MetricResult(
                    name="API Cost per User",
                    value=avg_cost_per_user,
                    target=2.0,
                    status=(
                        MetricStatus.PASS
                        if avg_cost_per_user < 2.0
                        else MetricStatus.WARNING
                        if avg_cost_per_user < 3.0
                        else MetricStatus.FAIL
                    ),
                    unit="EUR/month",
                    description="Average API cost per user per month",
                    timestamp=current_time,
                    environment=environment,
                )
            )
        except Exception as e:
            self.logger.error(f"Failed to collect API cost per user: {e}")
            metrics.append(
                MetricResult(
                    name="API Cost per User",
                    value=0.0,
                    target=2.0,
                    status=MetricStatus.UNKNOWN,
                    unit="EUR/month",
                    description="Average API cost per user per month",
                    timestamp=current_time,
                    environment=environment,
                )
            )

        # System Uptime (> 99.5%)
        try:
            system_uptime = await self._get_system_uptime()
            metrics.append(
                MetricResult(
                    name="System Uptime",
                    value=system_uptime,
                    target=99.5,
                    status=(
                        MetricStatus.PASS
                        if system_uptime > 99.5
                        else MetricStatus.WARNING
                        if system_uptime > 99.0
                        else MetricStatus.FAIL
                    ),
                    unit="%",
                    description="System uptime percentage over last 30 days",
                    timestamp=current_time,
                    environment=environment,
                )
            )
        except Exception as e:
            self.logger.error(f"Failed to collect system uptime: {e}")
            metrics.append(
                MetricResult(
                    name="System Uptime",
                    value=0.0,
                    target=99.5,
                    status=MetricStatus.UNKNOWN,
                    unit="%",
                    description="System uptime percentage over last 30 days",
                    timestamp=current_time,
                    environment=environment,
                )
            )

        # User Satisfaction (> 4.5/5)
        user_satisfaction = await self._get_user_satisfaction()
        metrics.append(
            MetricResult(
                name="User Satisfaction",
                value=user_satisfaction if user_satisfaction is not None else 0.0,
                target=4.5,
                status=(
                    (
                        MetricStatus.PASS
                        if user_satisfaction > 4.5
                        else MetricStatus.WARNING
                        if user_satisfaction > 4.0
                        else MetricStatus.FAIL
                    )
                    if user_satisfaction is not None
                    else MetricStatus.UNKNOWN
                ),
                unit="score",
                description="Average user satisfaction score (1-5)",
                timestamp=current_time,
                environment=environment,
            )
        )

        # GDPR Compliance — audit metric, not measurable at runtime
        gdpr_compliance_score = await self._get_gdpr_compliance_score()
        metrics.append(
            MetricResult(
                name="GDPR Compliance Score",
                value=gdpr_compliance_score if gdpr_compliance_score is not None else 0.0,
                target=100.0,
                status=(
                    (
                        MetricStatus.PASS
                        if gdpr_compliance_score >= 95
                        else MetricStatus.WARNING
                        if gdpr_compliance_score >= 85
                        else MetricStatus.FAIL
                    )
                    if gdpr_compliance_score is not None
                    else MetricStatus.UNKNOWN
                ),
                unit="%",
                description="GDPR compliance verification score (audit metric)",
                timestamp=current_time,
                environment=environment,
            )
        )

        return metrics

    async def generate_metrics_report(self, environment: Environment) -> MetricsReport:
        """Generate complete metrics report for an environment."""
        technical_metrics = await self.collect_technical_metrics(environment)
        business_metrics = await self.collect_business_metrics(environment)

        # Calculate overall health score — exclude UNKNOWN metrics
        all_metrics = technical_metrics + business_metrics
        measurable_metrics = [m for m in all_metrics if m.status != MetricStatus.UNKNOWN]
        passed_metrics = sum(1 for m in measurable_metrics if m.status == MetricStatus.PASS)
        total_measurable = len(measurable_metrics)
        health_score = (passed_metrics / total_measurable * 100) if total_measurable > 0 else 0

        # Generate alerts
        alerts = []
        for metric in all_metrics:
            if metric.status == MetricStatus.FAIL:
                alerts.append(
                    f"CRITICAL: {metric.name} is {metric.value:.2f} {metric.unit}, target: {metric.target:.2f} {metric.unit}"
                )
            elif metric.status == MetricStatus.WARNING:
                alerts.append(
                    f"WARNING: {metric.name} is {metric.value:.2f} {metric.unit}, target: {metric.target:.2f} {metric.unit}"
                )
            elif metric.status == MetricStatus.UNKNOWN:
                alerts.append(f"INFO: {metric.name} — no data available (data source not configured)")

        # Generate recommendations
        recommendations = await self._generate_recommendations(all_metrics)

        return MetricsReport(
            environment=environment,
            timestamp=datetime.utcnow(),
            technical_metrics=technical_metrics,
            business_metrics=business_metrics,
            overall_health_score=health_score,
            alerts=alerts,
            recommendations=recommendations,
        )

    async def _get_api_response_time_p95(self) -> float:
        """Get 95th percentile API response time in milliseconds."""
        try:
            # get_performance_summary() is synchronous - do not await
            summary = performance_monitor.get_performance_summary()

            # Calculate P95 from request metrics
            response_times = []
            for endpoint_data in summary.get("endpoints", {}).values():
                response_times.extend(endpoint_data.get("response_times", []))

            if not response_times:
                return 0.0

            response_times.sort()
            p95_index = int(len(response_times) * 0.95)
            return cast(float, response_times[p95_index] if p95_index < len(response_times) else response_times[-1])
        except Exception as e:
            self.logger.error(f"Error calculating P95 response time: {e}")
            return 0.0

    async def _get_cache_hit_rate(self) -> float:
        """Get cache hit rate percentage from in-memory performance monitor."""
        try:
            stats = performance_monitor.get_cache_statistics()
            return cast(float, stats.get("cache_hit_rate", 0.0))
        except Exception as e:
            self.logger.error(f"Error calculating cache hit rate: {e}")
            return 0.0

    async def _get_test_coverage(self) -> float | None:
        """Get test coverage percentage.

        Returns None when coverage data is not available at runtime.
        Test coverage is a CI/CD metric — it cannot be measured from a running app.
        """
        return None

    async def _get_critical_vulnerabilities(self) -> float | None:
        """Get number of critical security vulnerabilities.

        Returns None when security scanning is not available at runtime.
        Vulnerability scanning is a CI/CD metric (e.g. pip-audit, safety).
        """
        return None

    async def _get_average_cost_per_user(self) -> float:
        """Get average API cost per user per month in EUR."""
        try:
            # Get cost data from usage tracker
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            async with get_session() as session:
                # Get total API costs for the last 30 days
                cost_query = text(
                    """
                    SELECT COALESCE(SUM(total_cost), 0) as total_cost,
                           COUNT(DISTINCT user_id) as unique_users
                    FROM usage_logs
                    WHERE created_at >= :start_date
                """
                )

                result = await session.execute(cost_query, {"start_date": thirty_days_ago})
                row = result.fetchone()

                if row and row.unique_users > 0:
                    return float(row.total_cost) / float(row.unique_users)
                return 0.0
        except Exception as e:
            self.logger.error(f"Error calculating cost per user: {e}")
            return 0.0

    async def _get_system_uptime(self) -> float:
        """Get system uptime percentage over last 30 days."""
        try:
            # get_performance_summary() is synchronous - do not await
            summary = performance_monitor.get_performance_summary()
            return cast(float, summary.get("uptime_percentage", 0.0))
        except Exception as e:
            self.logger.error(f"Error getting system uptime: {e}")
            return 0.0

    async def _get_user_satisfaction(self) -> float | None:
        """Get average user satisfaction score.

        Returns None if no feedback data is available.
        """
        try:
            async with get_session() as session:
                # Get user satisfaction ratings from the last 30 days
                satisfaction_query = text(
                    """
                    SELECT AVG(rating) as avg_rating
                    FROM user_feedback
                    WHERE created_at >= :start_date
                    AND rating IS NOT NULL
                """
                )

                thirty_days_ago = datetime.utcnow() - timedelta(days=30)
                result = await session.execute(satisfaction_query, {"start_date": thirty_days_ago})
                row = result.fetchone()

                if row and row.avg_rating:
                    return float(row.avg_rating)
                return None
        except Exception as e:
            self.logger.error(f"Error getting user satisfaction: {e}")
            return None

    async def _get_gdpr_compliance_score(self) -> float | None:
        """Get GDPR compliance verification score.

        Returns None — GDPR compliance is verified through audits, not runtime checks.
        A real score requires external tooling (e.g. OneTrust, Vanta).
        """
        return None

    async def _generate_recommendations(self, metrics: list[MetricResult]) -> list[str]:
        """Generate recommendations based on metric results."""
        recommendations = []

        for metric in metrics:
            if metric.status == MetricStatus.FAIL:
                if "Response Time" in metric.name:
                    recommendations.append(
                        "Consider implementing response caching, database query optimization, or CDN usage to improve API response times"
                    )
                elif "Cache Hit Rate" in metric.name:
                    recommendations.append(
                        "Review cache configuration, increase cache TTL for stable data, or implement more aggressive caching strategies"
                    )
                elif "Test Coverage" in metric.name:
                    recommendations.append(
                        "Increase test coverage by adding unit tests for uncovered code paths and integration tests for critical workflows"
                    )
                elif "Security Vulnerabilities" in metric.name:
                    recommendations.append(
                        "Immediately address critical security vulnerabilities through patches, configuration updates, or code fixes"
                    )
                elif "API Cost" in metric.name:
                    recommendations.append(
                        "Optimize LLM usage through better caching, query optimization, or switching to more cost-effective models"
                    )
                elif "System Uptime" in metric.name:
                    recommendations.append(
                        "Investigate and resolve infrastructure issues, implement better monitoring, and consider redundancy improvements"
                    )
                elif "User Satisfaction" in metric.name:
                    recommendations.append(
                        "Collect user feedback, improve response quality, reduce response times, and enhance user experience"
                    )
                elif "GDPR Compliance" in metric.name:
                    recommendations.append(
                        "Review and strengthen GDPR compliance measures including data anonymization, consent management, and audit trails"
                    )

            elif metric.status == MetricStatus.WARNING:
                if "Response Time" in metric.name:
                    recommendations.append("Monitor API response times closely and prepare optimization strategies")
                elif "Cache Hit Rate" in metric.name:
                    recommendations.append("Consider tuning cache parameters to improve hit rates")
                elif "API Cost" in metric.name:
                    recommendations.append("Monitor API costs and implement additional cost optimization measures")

        # Remove duplicates
        return list(set(recommendations))


# Global metrics service instance
metrics_service = MetricsService()
