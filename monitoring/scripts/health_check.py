#!/usr/bin/env python3
"""PratikoAI Health Check Monitor

This script performs comprehensive health checks on the monitoring infrastructure:
- Service availability and responsiveness
- Metric collection validation
- Data freshness verification
- Alert system functionality
- Dashboard accessibility
- Critical threshold monitoring

Usage:
    python monitoring/scripts/health_check.py
    python monitoring/scripts/health_check.py --critical-only
    python monitoring/scripts/health_check.py --json
    python monitoring/scripts/health_check.py --notify
"""

import argparse
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result"""

    name: str
    status: HealthStatus
    message: str
    details: dict[str, Any]
    response_time_ms: float | None = None
    last_updated: str | None = None


@dataclass
class HealthReport:
    """Complete health check report"""

    timestamp: str
    overall_status: HealthStatus
    services: dict[str, HealthCheck]
    metrics: dict[str, HealthCheck]
    alerts: dict[str, HealthCheck]
    summary: dict[str, int]
    recommendations: list[str]


class PratikoAIHealthChecker:
    """Main health checker class"""

    def __init__(
        self,
        prometheus_url: str = "http://localhost:9090",
        grafana_url: str = "http://localhost:3000",
        app_url: str = "http://localhost:8000",
    ):
        self.prometheus_url = prometheus_url
        self.grafana_url = grafana_url
        self.app_url = app_url
        self.timeout = 10

    def check_service_health(self, service_name: str, url: str, health_endpoint: str = "/health") -> HealthCheck:
        """Check individual service health"""
        start_time = time.time()

        try:
            response = requests.get(f"{url}{health_endpoint}", timeout=self.timeout)
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                try:
                    health_data = response.json()
                    return HealthCheck(
                        name=service_name,
                        status=HealthStatus.HEALTHY,
                        message=f"{service_name} is healthy",
                        details=health_data,
                        response_time_ms=response_time,
                        last_updated=datetime.now().isoformat(),
                    )
                except json.JSONDecodeError:
                    return HealthCheck(
                        name=service_name,
                        status=HealthStatus.HEALTHY,
                        message=f"{service_name} is responding (non-JSON)",
                        details={"status_code": response.status_code},
                        response_time_ms=response_time,
                        last_updated=datetime.now().isoformat(),
                    )
            else:
                return HealthCheck(
                    name=service_name,
                    status=HealthStatus.WARNING,
                    message=f"{service_name} returned status {response.status_code}",
                    details={"status_code": response.status_code, "response": response.text[:200]},
                    response_time_ms=response_time,
                    last_updated=datetime.now().isoformat(),
                )

        except requests.exceptions.ConnectTimeout:
            return HealthCheck(
                name=service_name,
                status=HealthStatus.CRITICAL,
                message=f"{service_name} connection timeout",
                details={"error": "Connection timeout", "timeout_seconds": self.timeout},
                last_updated=datetime.now().isoformat(),
            )
        except requests.exceptions.ConnectionError:
            return HealthCheck(
                name=service_name,
                status=HealthStatus.CRITICAL,
                message=f"{service_name} connection failed",
                details={"error": "Connection refused or unreachable"},
                last_updated=datetime.now().isoformat(),
            )
        except Exception as e:
            return HealthCheck(
                name=service_name,
                status=HealthStatus.CRITICAL,
                message=f"{service_name} health check failed: {str(e)}",
                details={"error": str(e)},
                last_updated=datetime.now().isoformat(),
            )

    def check_prometheus_metrics(self) -> dict[str, HealthCheck]:
        """Check Prometheus metrics availability and freshness"""
        checks = {}

        # Check Prometheus API availability
        checks["prometheus_api"] = self.check_service_health(
            "Prometheus", self.prometheus_url, "/api/v1/status/config"
        )

        if checks["prometheus_api"].status == HealthStatus.HEALTHY:
            # Check critical metrics availability
            critical_metrics = [
                ("up", "Service uptime metrics"),
                ("http_request_duration_seconds", "HTTP request metrics"),
                ("process_memory_bytes", "System memory metrics"),
                ("user_monthly_cost_eur", "User cost metrics"),
                ("monthly_revenue_eur", "Revenue metrics"),
            ]

            for metric_name, description in critical_metrics:
                checks[f"metric_{metric_name}"] = self._check_metric_availability(metric_name, description)

            # Check metric freshness
            checks["metric_freshness"] = self._check_metric_freshness()

            # Check target availability
            checks["prometheus_targets"] = self._check_prometheus_targets()

        return checks

    def _check_metric_availability(self, metric_name: str, description: str) -> HealthCheck:
        """Check if a specific metric is available"""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query", params={"query": metric_name}, timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("data", {}).get("result", [])

                if results:
                    return HealthCheck(
                        name=f"metric_{metric_name}",
                        status=HealthStatus.HEALTHY,
                        message=f"{description} available ({len(results)} series)",
                        details={"metric": metric_name, "series_count": len(results)},
                        last_updated=datetime.now().isoformat(),
                    )
                else:
                    return HealthCheck(
                        name=f"metric_{metric_name}",
                        status=HealthStatus.WARNING,
                        message=f"{description} not available - no data",
                        details={"metric": metric_name, "series_count": 0},
                        last_updated=datetime.now().isoformat(),
                    )
            else:
                return HealthCheck(
                    name=f"metric_{metric_name}",
                    status=HealthStatus.CRITICAL,
                    message=f"Failed to query {metric_name}: HTTP {response.status_code}",
                    details={"metric": metric_name, "status_code": response.status_code},
                    last_updated=datetime.now().isoformat(),
                )

        except Exception as e:
            return HealthCheck(
                name=f"metric_{metric_name}",
                status=HealthStatus.CRITICAL,
                message=f"Error querying {metric_name}: {str(e)}",
                details={"metric": metric_name, "error": str(e)},
                last_updated=datetime.now().isoformat(),
            )

    def _check_metric_freshness(self) -> HealthCheck:
        """Check if metrics are recent (not stale)"""
        try:
            # Check when metrics were last updated
            query = "time() - prometheus_tsdb_lowest_timestamp"
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query", params={"query": query}, timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("data", {}).get("result", [])

                if results:
                    staleness_seconds = float(results[0]["value"][1])
                    staleness_minutes = staleness_seconds / 60

                    if staleness_minutes < 5:  # Fresh data
                        return HealthCheck(
                            name="metric_freshness",
                            status=HealthStatus.HEALTHY,
                            message=f"Metrics are fresh ({staleness_minutes:.1f} minutes old)",
                            details={"staleness_minutes": staleness_minutes},
                            last_updated=datetime.now().isoformat(),
                        )
                    elif staleness_minutes < 15:  # Somewhat stale
                        return HealthCheck(
                            name="metric_freshness",
                            status=HealthStatus.WARNING,
                            message=f"Metrics are moderately stale ({staleness_minutes:.1f} minutes old)",
                            details={"staleness_minutes": staleness_minutes},
                            last_updated=datetime.now().isoformat(),
                        )
                    else:  # Very stale
                        return HealthCheck(
                            name="metric_freshness",
                            status=HealthStatus.CRITICAL,
                            message=f"Metrics are very stale ({staleness_minutes:.1f} minutes old)",
                            details={"staleness_minutes": staleness_minutes},
                            last_updated=datetime.now().isoformat(),
                        )
                else:
                    return HealthCheck(
                        name="metric_freshness",
                        status=HealthStatus.WARNING,
                        message="Unable to determine metric freshness",
                        details={"error": "No timestamp data available"},
                        last_updated=datetime.now().isoformat(),
                    )
            else:
                return HealthCheck(
                    name="metric_freshness",
                    status=HealthStatus.WARNING,
                    message="Unable to check metric freshness",
                    details={"status_code": response.status_code},
                    last_updated=datetime.now().isoformat(),
                )

        except Exception as e:
            return HealthCheck(
                name="metric_freshness",
                status=HealthStatus.WARNING,
                message=f"Error checking metric freshness: {str(e)}",
                details={"error": str(e)},
                last_updated=datetime.now().isoformat(),
            )

    def _check_prometheus_targets(self) -> HealthCheck:
        """Check Prometheus target health"""
        try:
            response = requests.get(f"{self.prometheus_url}/api/v1/targets", timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                targets = data.get("data", {}).get("activeTargets", [])

                total_targets = len(targets)
                healthy_targets = sum(1 for t in targets if t.get("health") == "up")
                unhealthy_targets = total_targets - healthy_targets

                if unhealthy_targets == 0:
                    return HealthCheck(
                        name="prometheus_targets",
                        status=HealthStatus.HEALTHY,
                        message=f"All {total_targets} targets are healthy",
                        details={
                            "total_targets": total_targets,
                            "healthy_targets": healthy_targets,
                            "unhealthy_targets": unhealthy_targets,
                        },
                        last_updated=datetime.now().isoformat(),
                    )
                elif unhealthy_targets <= total_targets * 0.2:  # Less than 20% unhealthy
                    return HealthCheck(
                        name="prometheus_targets",
                        status=HealthStatus.WARNING,
                        message=f"{unhealthy_targets}/{total_targets} targets are unhealthy",
                        details={
                            "total_targets": total_targets,
                            "healthy_targets": healthy_targets,
                            "unhealthy_targets": unhealthy_targets,
                            "unhealthy_list": [
                                t.get("labels", {}).get("job", "unknown") for t in targets if t.get("health") != "up"
                            ],
                        },
                        last_updated=datetime.now().isoformat(),
                    )
                else:  # More than 20% unhealthy
                    return HealthCheck(
                        name="prometheus_targets",
                        status=HealthStatus.CRITICAL,
                        message=f"{unhealthy_targets}/{total_targets} targets are unhealthy",
                        details={
                            "total_targets": total_targets,
                            "healthy_targets": healthy_targets,
                            "unhealthy_targets": unhealthy_targets,
                            "unhealthy_list": [
                                t.get("labels", {}).get("job", "unknown") for t in targets if t.get("health") != "up"
                            ],
                        },
                        last_updated=datetime.now().isoformat(),
                    )
            else:
                return HealthCheck(
                    name="prometheus_targets",
                    status=HealthStatus.CRITICAL,
                    message=f"Unable to fetch target status: HTTP {response.status_code}",
                    details={"status_code": response.status_code},
                    last_updated=datetime.now().isoformat(),
                )

        except Exception as e:
            return HealthCheck(
                name="prometheus_targets",
                status=HealthStatus.CRITICAL,
                message=f"Error checking targets: {str(e)}",
                details={"error": str(e)},
                last_updated=datetime.now().isoformat(),
            )

    def check_grafana_health(self) -> dict[str, HealthCheck]:
        """Check Grafana dashboard and alerting health"""
        checks = {}

        # Check Grafana API availability
        checks["grafana_api"] = self.check_service_health("Grafana", self.grafana_url, "/api/health")

        if checks["grafana_api"].status == HealthStatus.HEALTHY:
            # Check dashboard availability
            checks["grafana_dashboards"] = self._check_grafana_dashboards()

            # Check data source connectivity
            checks["grafana_datasources"] = self._check_grafana_datasources()

            # Check alerting
            checks["grafana_alerting"] = self._check_grafana_alerting()

        return checks

    def _check_grafana_dashboards(self) -> HealthCheck:
        """Check if Grafana dashboards are accessible"""
        try:
            # Check if we can access dashboard search API (without auth for basic check)
            response = requests.get(f"{self.grafana_url}/api/search", timeout=self.timeout)

            # Grafana might return 401 if no auth, but that means it's responding
            if response.status_code in [200, 401]:
                if response.status_code == 200:
                    dashboards = response.json()
                    dashboard_count = len(dashboards)

                    return HealthCheck(
                        name="grafana_dashboards",
                        status=HealthStatus.HEALTHY,
                        message=f"Grafana dashboards accessible ({dashboard_count} found)",
                        details={"dashboard_count": dashboard_count},
                        last_updated=datetime.now().isoformat(),
                    )
                else:
                    return HealthCheck(
                        name="grafana_dashboards",
                        status=HealthStatus.HEALTHY,
                        message="Grafana is responding (requires authentication)",
                        details={"status_code": response.status_code},
                        last_updated=datetime.now().isoformat(),
                    )
            else:
                return HealthCheck(
                    name="grafana_dashboards",
                    status=HealthStatus.WARNING,
                    message=f"Grafana dashboard API returned {response.status_code}",
                    details={"status_code": response.status_code},
                    last_updated=datetime.now().isoformat(),
                )

        except Exception as e:
            return HealthCheck(
                name="grafana_dashboards",
                status=HealthStatus.CRITICAL,
                message=f"Error checking Grafana dashboards: {str(e)}",
                details={"error": str(e)},
                last_updated=datetime.now().isoformat(),
            )

    def _check_grafana_datasources(self) -> HealthCheck:
        """Check Grafana data source connectivity"""
        try:
            # Basic connectivity check to Grafana
            response = requests.get(f"{self.grafana_url}/api/datasources", timeout=self.timeout)

            if response.status_code in [200, 401]:
                return HealthCheck(
                    name="grafana_datasources",
                    status=HealthStatus.HEALTHY,
                    message="Grafana data source API is accessible",
                    details={"status_code": response.status_code},
                    last_updated=datetime.now().isoformat(),
                )
            else:
                return HealthCheck(
                    name="grafana_datasources",
                    status=HealthStatus.WARNING,
                    message=f"Grafana data source API returned {response.status_code}",
                    details={"status_code": response.status_code},
                    last_updated=datetime.now().isoformat(),
                )

        except Exception as e:
            return HealthCheck(
                name="grafana_datasources",
                status=HealthStatus.CRITICAL,
                message=f"Error checking Grafana data sources: {str(e)}",
                details={"error": str(e)},
                last_updated=datetime.now().isoformat(),
            )

    def _check_grafana_alerting(self) -> HealthCheck:
        """Check Grafana alerting system"""
        try:
            # Check if alerting API is accessible
            response = requests.get(f"{self.grafana_url}/api/ruler/grafana/api/v1/rules", timeout=self.timeout)

            if response.status_code in [200, 401]:
                return HealthCheck(
                    name="grafana_alerting",
                    status=HealthStatus.HEALTHY,
                    message="Grafana alerting API is accessible",
                    details={"status_code": response.status_code},
                    last_updated=datetime.now().isoformat(),
                )
            else:
                return HealthCheck(
                    name="grafana_alerting",
                    status=HealthStatus.WARNING,
                    message=f"Grafana alerting API returned {response.status_code}",
                    details={"status_code": response.status_code},
                    last_updated=datetime.now().isoformat(),
                )

        except Exception as e:
            return HealthCheck(
                name="grafana_alerting",
                status=HealthStatus.WARNING,
                message=f"Error checking Grafana alerting: {str(e)}",
                details={"error": str(e)},
                last_updated=datetime.now().isoformat(),
            )

    def check_critical_thresholds(self) -> dict[str, HealthCheck]:
        """Check if any critical business thresholds are breached"""
        checks = {}

        # Check user cost threshold
        checks["cost_threshold"] = self._check_cost_threshold()

        # Check revenue threshold
        checks["revenue_threshold"] = self._check_revenue_threshold()

        # Check performance thresholds
        checks["performance_threshold"] = self._check_performance_threshold()

        # Check error rate threshold
        checks["error_threshold"] = self._check_error_threshold()

        return checks

    def _check_cost_threshold(self) -> HealthCheck:
        """Check if user costs exceed critical thresholds"""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": "avg(user_monthly_cost_eur)"},
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("data", {}).get("result", [])

                if results:
                    avg_cost = float(results[0]["value"][1])

                    if avg_cost <= 2.0:
                        return HealthCheck(
                            name="cost_threshold",
                            status=HealthStatus.HEALTHY,
                            message=f"Average user cost is €{avg_cost:.2f} (within €2.00 target)",
                            details={"average_cost": avg_cost, "target": 2.0},
                            last_updated=datetime.now().isoformat(),
                        )
                    elif avg_cost <= 2.5:
                        return HealthCheck(
                            name="cost_threshold",
                            status=HealthStatus.WARNING,
                            message=f"Average user cost is €{avg_cost:.2f} (above €2.00 target)",
                            details={"average_cost": avg_cost, "target": 2.0},
                            last_updated=datetime.now().isoformat(),
                        )
                    else:
                        return HealthCheck(
                            name="cost_threshold",
                            status=HealthStatus.CRITICAL,
                            message=f"Average user cost is €{avg_cost:.2f} (critical threshold breached)",
                            details={"average_cost": avg_cost, "target": 2.0, "critical_threshold": 2.5},
                            last_updated=datetime.now().isoformat(),
                        )
                else:
                    return HealthCheck(
                        name="cost_threshold",
                        status=HealthStatus.WARNING,
                        message="No user cost data available",
                        details={"error": "No data"},
                        last_updated=datetime.now().isoformat(),
                    )
            else:
                return HealthCheck(
                    name="cost_threshold",
                    status=HealthStatus.WARNING,
                    message="Unable to check cost threshold",
                    details={"status_code": response.status_code},
                    last_updated=datetime.now().isoformat(),
                )

        except Exception as e:
            return HealthCheck(
                name="cost_threshold",
                status=HealthStatus.WARNING,
                message=f"Error checking cost threshold: {str(e)}",
                details={"error": str(e)},
                last_updated=datetime.now().isoformat(),
            )

    def _check_revenue_threshold(self) -> HealthCheck:
        """Check if revenue is meeting targets"""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query", params={"query": "monthly_revenue_eur"}, timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("data", {}).get("result", [])

                if results:
                    revenue = float(results[0]["value"][1])
                    target = 25000
                    progress = (revenue / target) * 100

                    if progress >= 80:
                        return HealthCheck(
                            name="revenue_threshold",
                            status=HealthStatus.HEALTHY,
                            message=f"Revenue is €{revenue:.0f} ({progress:.1f}% of €25k target)",
                            details={"revenue": revenue, "target": target, "progress_percent": progress},
                            last_updated=datetime.now().isoformat(),
                        )
                    elif progress >= 40:
                        return HealthCheck(
                            name="revenue_threshold",
                            status=HealthStatus.WARNING,
                            message=f"Revenue is €{revenue:.0f} ({progress:.1f}% of €25k target)",
                            details={"revenue": revenue, "target": target, "progress_percent": progress},
                            last_updated=datetime.now().isoformat(),
                        )
                    else:
                        return HealthCheck(
                            name="revenue_threshold",
                            status=HealthStatus.CRITICAL,
                            message=f"Revenue is €{revenue:.0f} ({progress:.1f}% of €25k target - critically low)",
                            details={"revenue": revenue, "target": target, "progress_percent": progress},
                            last_updated=datetime.now().isoformat(),
                        )
                else:
                    return HealthCheck(
                        name="revenue_threshold",
                        status=HealthStatus.WARNING,
                        message="No revenue data available",
                        details={"error": "No data"},
                        last_updated=datetime.now().isoformat(),
                    )
            else:
                return HealthCheck(
                    name="revenue_threshold",
                    status=HealthStatus.WARNING,
                    message="Unable to check revenue threshold",
                    details={"status_code": response.status_code},
                    last_updated=datetime.now().isoformat(),
                )

        except Exception as e:
            return HealthCheck(
                name="revenue_threshold",
                status=HealthStatus.WARNING,
                message=f"Error checking revenue threshold: {str(e)}",
                details={"error": str(e)},
                last_updated=datetime.now().isoformat(),
            )

    def _check_performance_threshold(self) -> HealthCheck:
        """Check if API performance meets SLA"""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"},
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("data", {}).get("result", [])

                if results:
                    p95_time = float(results[0]["value"][1])
                    sla_threshold = 5.0

                    if p95_time <= 2.0:
                        return HealthCheck(
                            name="performance_threshold",
                            status=HealthStatus.HEALTHY,
                            message=f"API p95 response time is {p95_time:.2f}s (excellent performance)",
                            details={"p95_response_time": p95_time, "sla_threshold": sla_threshold},
                            last_updated=datetime.now().isoformat(),
                        )
                    elif p95_time <= sla_threshold:
                        return HealthCheck(
                            name="performance_threshold",
                            status=HealthStatus.WARNING,
                            message=f"API p95 response time is {p95_time:.2f}s (within SLA but degraded)",
                            details={"p95_response_time": p95_time, "sla_threshold": sla_threshold},
                            last_updated=datetime.now().isoformat(),
                        )
                    else:
                        return HealthCheck(
                            name="performance_threshold",
                            status=HealthStatus.CRITICAL,
                            message=f"API p95 response time is {p95_time:.2f}s (SLA breach)",
                            details={"p95_response_time": p95_time, "sla_threshold": sla_threshold},
                            last_updated=datetime.now().isoformat(),
                        )
                else:
                    return HealthCheck(
                        name="performance_threshold",
                        status=HealthStatus.WARNING,
                        message="No performance data available",
                        details={"error": "No data"},
                        last_updated=datetime.now().isoformat(),
                    )
            else:
                return HealthCheck(
                    name="performance_threshold",
                    status=HealthStatus.WARNING,
                    message="Unable to check performance threshold",
                    details={"status_code": response.status_code},
                    last_updated=datetime.now().isoformat(),
                )

        except Exception as e:
            return HealthCheck(
                name="performance_threshold",
                status=HealthStatus.WARNING,
                message=f"Error checking performance threshold: {str(e)}",
                details={"error": str(e)},
                last_updated=datetime.now().isoformat(),
            )

    def _check_error_threshold(self) -> HealthCheck:
        """Check if error rates are within acceptable limits"""
        try:
            query = "(rate(api_errors_total[5m]) / rate(http_request_duration_seconds_count[5m])) * 100"
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query", params={"query": query}, timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("data", {}).get("result", [])

                if results:
                    error_rate = float(results[0]["value"][1])

                    if error_rate <= 1.0:
                        return HealthCheck(
                            name="error_threshold",
                            status=HealthStatus.HEALTHY,
                            message=f"Error rate is {error_rate:.2f}% (excellent reliability)",
                            details={"error_rate_percent": error_rate, "threshold": 5.0},
                            last_updated=datetime.now().isoformat(),
                        )
                    elif error_rate <= 5.0:
                        return HealthCheck(
                            name="error_threshold",
                            status=HealthStatus.WARNING,
                            message=f"Error rate is {error_rate:.2f}% (elevated but acceptable)",
                            details={"error_rate_percent": error_rate, "threshold": 5.0},
                            last_updated=datetime.now().isoformat(),
                        )
                    else:
                        return HealthCheck(
                            name="error_threshold",
                            status=HealthStatus.CRITICAL,
                            message=f"Error rate is {error_rate:.2f}% (exceeds 5% threshold)",
                            details={"error_rate_percent": error_rate, "threshold": 5.0},
                            last_updated=datetime.now().isoformat(),
                        )
                else:
                    return HealthCheck(
                        name="error_threshold",
                        status=HealthStatus.WARNING,
                        message="No error rate data available",
                        details={"error": "No data"},
                        last_updated=datetime.now().isoformat(),
                    )
            else:
                return HealthCheck(
                    name="error_threshold",
                    status=HealthStatus.WARNING,
                    message="Unable to check error threshold",
                    details={"status_code": response.status_code},
                    last_updated=datetime.now().isoformat(),
                )

        except Exception as e:
            return HealthCheck(
                name="error_threshold",
                status=HealthStatus.WARNING,
                message=f"Error checking error threshold: {str(e)}",
                details={"error": str(e)},
                last_updated=datetime.now().isoformat(),
            )

    def generate_recommendations(self, all_checks: dict[str, HealthCheck]) -> list[str]:
        """Generate actionable recommendations based on health check results"""
        recommendations = []

        # Analyze failures by category
        critical_issues = [check for check in all_checks.values() if check.status == HealthStatus.CRITICAL]
        warning_issues = [check for check in all_checks.values() if check.status == HealthStatus.WARNING]

        # Critical recommendations
        for issue in critical_issues:
            if "connection" in issue.message.lower():
                recommendations.append(f"🔴 CRITICAL: Fix connectivity issue with {issue.name}")
            elif "cost" in issue.name:
                recommendations.append(
                    "🔴 CRITICAL: Implement immediate cost controls - user costs exceed safe limits"
                )
            elif "error" in issue.name:
                recommendations.append("🔴 CRITICAL: Investigate high error rates - impacting user experience")
            elif "performance" in issue.name:
                recommendations.append("🔴 CRITICAL: Performance SLA breach - immediate optimization needed")

        # Warning recommendations
        for issue in warning_issues:
            if "metric" in issue.name and "not available" in issue.message:
                recommendations.append(
                    f"🟡 WARNING: Ensure {issue.name.replace('metric_', '')} metrics are being collected"
                )
            elif "stale" in issue.message:
                recommendations.append("🟡 WARNING: Check metric collection pipeline - data appears stale")
            elif "targets" in issue.name:
                recommendations.append("🟡 WARNING: Review Prometheus target configuration - some targets unhealthy")

        # General recommendations
        if len(critical_issues) == 0 and len(warning_issues) == 0:
            recommendations.append("✅ All systems healthy - continue regular monitoring")
        elif len(critical_issues) > 0:
            recommendations.append("📧 Consider sending immediate alert to operations team")

        return recommendations[:5]  # Top 5 most important

    def run_health_check(self, critical_only: bool = False) -> HealthReport:
        """Run comprehensive health check"""
        logger.info("Running PratikoAI health check...")

        all_checks = {}

        # Service health checks
        logger.info("Checking service health...")
        services = {
            "pratikoai_app": self.check_service_health("PratikoAI App", self.app_url),
            "prometheus": self.check_service_health("Prometheus", self.prometheus_url, "/api/v1/status/config"),
            "grafana": self.check_service_health("Grafana", self.grafana_url),
        }
        all_checks.update(services)

        # Metric health checks
        logger.info("Checking metrics health...")
        metrics = self.check_prometheus_metrics()
        all_checks.update(metrics)

        # Grafana health checks
        if not critical_only:
            logger.info("Checking Grafana health...")
            grafana_checks = self.check_grafana_health()
            all_checks.update(grafana_checks)

        # Critical threshold checks
        logger.info("Checking critical thresholds...")
        thresholds = self.check_critical_thresholds()
        all_checks.update(thresholds)

        # Calculate overall status
        statuses = [check.status for check in all_checks.values()]
        if HealthStatus.CRITICAL in statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY

        # Generate summary
        summary = {
            "healthy": sum(1 for s in statuses if s == HealthStatus.HEALTHY),
            "warning": sum(1 for s in statuses if s == HealthStatus.WARNING),
            "critical": sum(1 for s in statuses if s == HealthStatus.CRITICAL),
            "unknown": sum(1 for s in statuses if s == HealthStatus.UNKNOWN),
            "total": len(statuses),
        }

        # Generate recommendations
        recommendations = self.generate_recommendations(all_checks)

        # Organize checks by category
        service_checks = {k: v for k, v in all_checks.items() if k in services}
        metric_checks = {k: v for k, v in all_checks.items() if k.startswith("metric_") or k == "prometheus_targets"}
        alert_checks = {k: v for k, v in all_checks.items() if "threshold" in k or "grafana" in k}

        return HealthReport(
            timestamp=datetime.now().isoformat(),
            overall_status=overall_status,
            services=service_checks,
            metrics=metric_checks,
            alerts=alert_checks,
            summary=summary,
            recommendations=recommendations,
        )


def format_health_report(report: HealthReport, json_format: bool = False) -> str:
    """Format health report for display"""
    if json_format:
        return json.dumps(asdict(report), indent=2, default=str)

    status_icons = {
        HealthStatus.HEALTHY: "✅",
        HealthStatus.WARNING: "⚠️",
        HealthStatus.CRITICAL: "❌",
        HealthStatus.UNKNOWN: "❓",
    }

    output = f"""
PratikoAI Health Check Report
{"=" * 50}
Timestamp: {report.timestamp}
Overall Status: {status_icons.get(report.overall_status, "❓")} {report.overall_status.value.upper()}

📊 SUMMARY
----------
Total Checks: {report.summary["total"]}
Healthy: {report.summary["healthy"]} ✅
Warning: {report.summary["warning"]} ⚠️
Critical: {report.summary["critical"]} ❌
Unknown: {report.summary["unknown"]} ❓

🔧 SERVICES
-----------
"""

    for name, check in report.services.items():
        icon = status_icons.get(check.status, "❓")
        response_time = f" ({check.response_time_ms:.0f}ms)" if check.response_time_ms else ""
        output += f"{icon} {name}: {check.message}{response_time}\n"

    output += "\n📈 METRICS\n----------\n"
    for name, check in report.metrics.items():
        icon = status_icons.get(check.status, "❓")
        output += f"{icon} {name}: {check.message}\n"

    if report.alerts:
        output += "\n🚨 CRITICAL THRESHOLDS\n---------------------\n"
        for name, check in report.alerts.items():
            icon = status_icons.get(check.status, "❓")
            output += f"{icon} {name}: {check.message}\n"

    output += "\n💡 RECOMMENDATIONS\n------------------\n"
    for i, rec in enumerate(report.recommendations, 1):
        output += f"{i}. {rec}\n"

    return output


def main():
    parser = argparse.ArgumentParser(description="Run PratikoAI health checks")
    parser.add_argument("--critical-only", action="store_true", help="Check only critical components")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--notify", action="store_true", help="Send notifications on critical issues")
    parser.add_argument("--prometheus-url", default="http://localhost:9090", help="Prometheus URL")
    parser.add_argument("--grafana-url", default="http://localhost:3000", help="Grafana URL")
    parser.add_argument("--app-url", default="http://localhost:8000", help="PratikoAI app URL")

    args = parser.parse_args()

    # Run health check
    checker = PratikoAIHealthChecker(args.prometheus_url, args.grafana_url, args.app_url)
    report = checker.run_health_check(args.critical_only)

    # Display report
    print(format_health_report(report, args.json))

    # Send notifications if requested and there are critical issues
    if args.notify and report.overall_status == HealthStatus.CRITICAL:
        logger.info("Critical issues detected - notifications would be sent")
        # Implementation for actual notifications would go here

    # Exit with appropriate code
    if report.overall_status == HealthStatus.CRITICAL:
        exit(2)
    elif report.overall_status == HealthStatus.WARNING:
        exit(1)
    else:
        exit(0)


if __name__ == "__main__":
    main()
