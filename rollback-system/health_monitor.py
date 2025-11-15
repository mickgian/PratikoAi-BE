#!/usr/bin/env python3
"""PratikoAI Health Monitoring Integration System

Advanced health monitoring system that automatically detects deployment failures,
monitors system health metrics, and triggers rollback procedures when issues are detected.

Features:
- Real-time health metric monitoring
- Automatic failure detection with configurable thresholds
- Integration with rollback orchestrator
- System log preservation for post-mortem analysis
- Multi-service health validation
- Alert escalation and notification
"""

import asyncio
import json
import logging
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiofiles
import httpx
import psutil
import requests
import yaml

# Import rollback orchestrator
from rollback_orchestrator import RollbackOrchestrator, RollbackReason, RollbackTarget, RollbackTrigger

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricType(Enum):
    """Types of health metrics."""

    HTTP_RESPONSE = "http_response"
    DATABASE_CONNECTION = "database_connection"
    SYSTEM_RESOURCE = "system_resource"
    APPLICATION_METRIC = "application_metric"
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    CUSTOM = "custom"


@dataclass
class HealthMetric:
    """Individual health metric."""

    metric_id: str
    metric_type: MetricType
    service: str
    name: str
    value: float | int | str | bool
    threshold_warning: float | None = None
    threshold_critical: float | None = None
    unit: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """Health check configuration."""

    check_id: str
    service: str
    name: str
    check_type: MetricType
    endpoint_url: str | None = None
    command: str | None = None
    interval_seconds: int = 30
    timeout_seconds: int = 10
    enabled: bool = True
    threshold_warning: float | None = None
    threshold_critical: float | None = None
    consecutive_failures_for_critical: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    """Comprehensive health report."""

    report_id: str
    deployment_id: str
    environment: str
    created_at: datetime
    overall_status: HealthStatus
    services: dict[str, HealthStatus]
    metrics: list[HealthMetric]
    failed_checks: list[str]
    warnings: list[str]
    recommendations: list[str]
    logs_preserved: dict[str, str]  # service -> log_path


@dataclass
class MonitoringRule:
    """Monitoring rule for automatic actions."""

    rule_id: str
    name: str
    condition: str  # Python expression
    action: str  # rollback, alert, etc.
    priority: int = 1
    enabled: bool = True
    cooldown_minutes: int = 15
    last_triggered: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SystemResourceMonitor:
    """Monitor system resources."""

    async def get_cpu_usage(self) -> float:
        """Get CPU usage percentage."""
        return psutil.cpu_percent(interval=1)

    async def get_memory_usage(self) -> dict[str, float]:
        """Get memory usage information."""
        memory = psutil.virtual_memory()
        return {
            "percent": memory.percent,
            "available_gb": memory.available / (1024**3),
            "used_gb": memory.used / (1024**3),
            "total_gb": memory.total / (1024**3),
        }

    async def get_disk_usage(self, path: str = "/") -> dict[str, float]:
        """Get disk usage information."""
        usage = psutil.disk_usage(path)
        return {
            "percent": (usage.used / usage.total) * 100,
            "free_gb": usage.free / (1024**3),
            "used_gb": usage.used / (1024**3),
            "total_gb": usage.total / (1024**3),
        }

    async def get_network_stats(self) -> dict[str, int]:
        """Get network statistics."""
        stats = psutil.net_io_counters()
        return {
            "bytes_sent": stats.bytes_sent,
            "bytes_recv": stats.bytes_recv,
            "packets_sent": stats.packets_sent,
            "packets_recv": stats.packets_recv,
        }


class ApplicationHealthChecker:
    """Check application-specific health metrics."""

    def __init__(self, httpx_client: httpx.AsyncClient):
        self.client = httpx_client

    async def check_http_endpoint(self, url: str, timeout: int = 10, expected_status: int = 200) -> HealthMetric:
        """Check HTTP endpoint health."""
        start_time = datetime.now(UTC)

        try:
            response = await self.client.get(url, timeout=timeout)
            response_time = (datetime.now(UTC) - start_time).total_seconds()

            return HealthMetric(
                metric_id=f"http_{url.replace('://', '_').replace('/', '_')}",
                metric_type=MetricType.HTTP_RESPONSE,
                service="http",
                name=f"HTTP Response - {url}",
                value=response.status_code,
                timestamp=start_time,
                metadata={
                    "url": url,
                    "response_time_seconds": response_time,
                    "status_text": response.reason_phrase,
                    "content_length": len(response.content) if hasattr(response, "content") else 0,
                    "expected_status": expected_status,
                },
            )

        except Exception as e:
            return HealthMetric(
                metric_id=f"http_{url.replace('://', '_').replace('/', '_')}",
                metric_type=MetricType.HTTP_RESPONSE,
                service="http",
                name=f"HTTP Response - {url}",
                value=0,
                timestamp=start_time,
                metadata={"url": url, "error": str(e), "expected_status": expected_status},
            )

    async def check_database_connection(self, connection_string: str, query: str = "SELECT 1") -> HealthMetric:
        """Check database connection health."""
        start_time = datetime.now(UTC)

        try:
            # This is a simplified example - in practice, you'd use appropriate DB drivers
            import asyncpg  # For PostgreSQL

            conn = await asyncpg.connect(connection_string)
            result = await conn.fetchval(query)
            await conn.close()

            response_time = (datetime.now(UTC) - start_time).total_seconds()

            return HealthMetric(
                metric_id="database_connection",
                metric_type=MetricType.DATABASE_CONNECTION,
                service="database",
                name="Database Connection",
                value=1,  # Success
                timestamp=start_time,
                metadata={"query": query, "response_time_seconds": response_time, "result": str(result)},
            )

        except Exception as e:
            return HealthMetric(
                metric_id="database_connection",
                metric_type=MetricType.DATABASE_CONNECTION,
                service="database",
                name="Database Connection",
                value=0,  # Failure
                timestamp=start_time,
                metadata={"query": query, "error": str(e)},
            )

    async def check_custom_metric(self, command: str, service: str, metric_name: str) -> HealthMetric:
        """Execute custom command and extract metric."""
        start_time = datetime.now(UTC)

        try:
            result = subprocess.run(command.split(), capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                # Try to parse numeric value from output
                try:
                    value = float(result.stdout.strip())
                except ValueError:
                    value = result.stdout.strip()

                return HealthMetric(
                    metric_id=f"custom_{service}_{metric_name}",
                    metric_type=MetricType.CUSTOM,
                    service=service,
                    name=metric_name,
                    value=value,
                    timestamp=start_time,
                    metadata={"command": command, "stdout": result.stdout, "stderr": result.stderr},
                )
            else:
                return HealthMetric(
                    metric_id=f"custom_{service}_{metric_name}",
                    metric_type=MetricType.CUSTOM,
                    service=service,
                    name=metric_name,
                    value=0,
                    timestamp=start_time,
                    metadata={
                        "command": command,
                        "error": f"Command failed with code {result.returncode}",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    },
                )

        except Exception as e:
            return HealthMetric(
                metric_id=f"custom_{service}_{metric_name}",
                metric_type=MetricType.CUSTOM,
                service=service,
                name=metric_name,
                value=0,
                timestamp=start_time,
                metadata={"command": command, "error": str(e)},
            )


class LogPreserver:
    """Preserve system logs for post-mortem analysis."""

    def __init__(self, log_directory: str = "/var/log/pratiko-rollback"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)

    async def preserve_service_logs(self, service: str, deployment_id: str, log_sources: list[str]) -> str:
        """Preserve logs for a specific service."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        preserve_dir = self.log_directory / f"{deployment_id}_{timestamp}" / service
        preserve_dir.mkdir(parents=True, exist_ok=True)

        preserved_files = []

        for log_source in log_sources:
            try:
                source_path = Path(log_source)
                if source_path.exists():
                    if source_path.is_file():
                        # Copy single file
                        dest_path = preserve_dir / source_path.name
                        async with aiofiles.open(source_path, "rb") as src:
                            async with aiofiles.open(dest_path, "wb") as dst:
                                await dst.write(await src.read())
                        preserved_files.append(str(dest_path))

                    elif source_path.is_dir():
                        # Copy directory contents
                        for log_file in source_path.glob("*.log"):
                            dest_path = preserve_dir / log_file.name
                            async with aiofiles.open(log_file, "rb") as src:
                                async with aiofiles.open(dest_path, "wb") as dst:
                                    await dst.write(await src.read())
                            preserved_files.append(str(dest_path))

            except Exception as e:
                logger.error(f"Failed to preserve log {log_source}: {str(e)}")

        # Create index file
        index_file = preserve_dir / "preserved_logs_index.json"
        index_data = {
            "service": service,
            "deployment_id": deployment_id,
            "preserved_at": datetime.now(UTC).isoformat(),
            "original_sources": log_sources,
            "preserved_files": preserved_files,
        }

        async with aiofiles.open(index_file, "w") as f:
            await f.write(json.dumps(index_data, indent=2))

        logger.info(f"Preserved {len(preserved_files)} log files for {service}")
        return str(preserve_dir)

    async def preserve_system_logs(self, deployment_id: str) -> dict[str, str]:
        """Preserve system-wide logs."""
        system_logs = {
            "syslog": "/var/log/syslog",
            "kern": "/var/log/kern.log",
            "auth": "/var/log/auth.log",
            "docker": "/var/log/docker.log",
            "nginx": "/var/log/nginx/error.log",
            "systemd": "/var/log/systemd",
        }

        preserved_paths = {}

        for log_type, log_path in system_logs.items():
            try:
                preserve_path = await self.preserve_service_logs(f"system_{log_type}", deployment_id, [log_path])
                preserved_paths[log_type] = preserve_path
            except Exception as e:
                logger.error(f"Failed to preserve {log_type} logs: {str(e)}")

        return preserved_paths


class HealthMonitor:
    """Main health monitoring system with automatic failure detection."""

    def __init__(self, config_file: str = "health_monitor_config.yaml"):
        self.config_file = config_file
        self.config = self._load_config()

        self.httpx_client = httpx.AsyncClient()
        self.resource_monitor = SystemResourceMonitor()
        self.app_checker = ApplicationHealthChecker(self.httpx_client)
        self.log_preserver = LogPreserver()

        self.rollback_orchestrator: RollbackOrchestrator | None = None
        self.health_checks: dict[str, HealthCheck] = {}
        self.monitoring_rules: dict[str, MonitoringRule] = {}
        self.recent_metrics: dict[str, list[HealthMetric]] = {}
        self.is_monitoring = False

        self._load_health_checks()
        self._load_monitoring_rules()

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file) as f:
                    return yaml.safe_load(f)
            else:
                # Return default configuration
                return {
                    "monitoring_interval_seconds": 30,
                    "metrics_retention_minutes": 60,
                    "rollback_enabled": True,
                    "log_preservation_enabled": True,
                    "notification_channels": ["slack", "email"],
                    "system_resource_thresholds": {
                        "cpu_warning": 80,
                        "cpu_critical": 95,
                        "memory_warning": 80,
                        "memory_critical": 95,
                        "disk_warning": 85,
                        "disk_critical": 95,
                    },
                    "services": {},
                }
        except Exception as e:
            logger.error(f"Failed to load config: {str(e)}")
            return {}

    def _load_health_checks(self):
        """Load health checks from configuration."""
        checks_config = self.config.get("health_checks", [])

        for check_config in checks_config:
            health_check = HealthCheck(
                check_id=check_config["check_id"],
                service=check_config["service"],
                name=check_config["name"],
                check_type=MetricType(check_config["check_type"]),
                endpoint_url=check_config.get("endpoint_url"),
                command=check_config.get("command"),
                interval_seconds=check_config.get("interval_seconds", 30),
                timeout_seconds=check_config.get("timeout_seconds", 10),
                enabled=check_config.get("enabled", True),
                threshold_warning=check_config.get("threshold_warning"),
                threshold_critical=check_config.get("threshold_critical"),
                consecutive_failures_for_critical=check_config.get("consecutive_failures_for_critical", 3),
                metadata=check_config.get("metadata", {}),
            )
            self.health_checks[health_check.check_id] = health_check

    def _load_monitoring_rules(self):
        """Load monitoring rules from configuration."""
        rules_config = self.config.get("monitoring_rules", [])

        for rule_config in rules_config:
            rule = MonitoringRule(
                rule_id=rule_config["rule_id"],
                name=rule_config["name"],
                condition=rule_config["condition"],
                action=rule_config["action"],
                priority=rule_config.get("priority", 1),
                enabled=rule_config.get("enabled", True),
                cooldown_minutes=rule_config.get("cooldown_minutes", 15),
                metadata=rule_config.get("metadata", {}),
            )
            self.monitoring_rules[rule.rule_id] = rule

    def set_rollback_orchestrator(self, orchestrator: RollbackOrchestrator):
        """Set the rollback orchestrator for automatic rollbacks."""
        self.rollback_orchestrator = orchestrator

    async def start_monitoring(self, deployment_id: str):
        """Start continuous health monitoring."""
        if self.is_monitoring:
            logger.warning("Monitoring already running")
            return

        self.is_monitoring = True
        logger.info(f"Starting health monitoring for deployment {deployment_id}")

        try:
            while self.is_monitoring:
                # Run all health checks
                await self._run_health_checks(deployment_id)

                # Evaluate monitoring rules
                await self._evaluate_monitoring_rules(deployment_id)

                # Clean up old metrics
                self._cleanup_old_metrics()

                # Wait for next monitoring cycle
                await asyncio.sleep(self.config.get("monitoring_interval_seconds", 30))

        except Exception as e:
            logger.error(f"Monitoring error: {str(e)}")
        finally:
            self.is_monitoring = False

    async def stop_monitoring(self):
        """Stop health monitoring."""
        self.is_monitoring = False
        logger.info("Health monitoring stopped")

    async def _run_health_checks(self, deployment_id: str):
        """Run all enabled health checks."""
        tasks = []

        for check in self.health_checks.values():
            if check.enabled:
                tasks.append(self._execute_health_check(check, deployment_id))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for _i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Health check failed: {str(result)}")
                elif result:
                    # Store metric
                    service = result.service
                    if service not in self.recent_metrics:
                        self.recent_metrics[service] = []
                    self.recent_metrics[service].append(result)

    async def _execute_health_check(self, check: HealthCheck, deployment_id: str) -> HealthMetric | None:
        """Execute a single health check."""
        try:
            if check.check_type == MetricType.HTTP_RESPONSE and check.endpoint_url:
                return await self.app_checker.check_http_endpoint(check.endpoint_url, check.timeout_seconds)

            elif check.check_type == MetricType.DATABASE_CONNECTION and check.endpoint_url:
                return await self.app_checker.check_database_connection(check.endpoint_url)

            elif check.check_type == MetricType.CUSTOM and check.command:
                return await self.app_checker.check_custom_metric(check.command, check.service, check.name)

            elif check.check_type == MetricType.SYSTEM_RESOURCE:
                return await self._check_system_resources(check)

        except Exception as e:
            logger.error(f"Failed to execute health check {check.check_id}: {str(e)}")
            return None

    async def _check_system_resources(self, check: HealthCheck) -> HealthMetric:
        """Check system resource metrics."""
        resource_name = check.metadata.get("resource", "cpu")

        if resource_name == "cpu":
            value = await self.resource_monitor.get_cpu_usage()
            return HealthMetric(
                metric_id=f"system_cpu_{check.check_id}",
                metric_type=MetricType.SYSTEM_RESOURCE,
                service="system",
                name="CPU Usage",
                value=value,
                threshold_warning=check.threshold_warning,
                threshold_critical=check.threshold_critical,
                unit="%",
            )

        elif resource_name == "memory":
            memory_info = await self.resource_monitor.get_memory_usage()
            return HealthMetric(
                metric_id=f"system_memory_{check.check_id}",
                metric_type=MetricType.SYSTEM_RESOURCE,
                service="system",
                name="Memory Usage",
                value=memory_info["percent"],
                threshold_warning=check.threshold_warning,
                threshold_critical=check.threshold_critical,
                unit="%",
                metadata=memory_info,
            )

        elif resource_name == "disk":
            disk_path = check.metadata.get("path", "/")
            disk_info = await self.resource_monitor.get_disk_usage(disk_path)
            return HealthMetric(
                metric_id=f"system_disk_{check.check_id}",
                metric_type=MetricType.SYSTEM_RESOURCE,
                service="system",
                name=f"Disk Usage ({disk_path})",
                value=disk_info["percent"],
                threshold_warning=check.threshold_warning,
                threshold_critical=check.threshold_critical,
                unit="%",
                metadata=disk_info,
            )

        else:
            raise ValueError(f"Unknown system resource: {resource_name}")

    async def _evaluate_monitoring_rules(self, deployment_id: str):
        """Evaluate monitoring rules and trigger actions."""
        for rule in self.monitoring_rules.values():
            if not rule.enabled:
                continue

            # Check cooldown
            if rule.last_triggered:
                cooldown_end = rule.last_triggered + timedelta(minutes=rule.cooldown_minutes)
                if datetime.now(UTC) < cooldown_end:
                    continue

            try:
                # Evaluate rule condition
                if self._evaluate_rule_condition(rule):
                    logger.warning(f"Monitoring rule triggered: {rule.name}")

                    # Execute rule action
                    await self._execute_rule_action(rule, deployment_id)

                    # Update last triggered time
                    rule.last_triggered = datetime.now(UTC)

            except Exception as e:
                logger.error(f"Failed to evaluate rule {rule.rule_id}: {str(e)}")

    def _evaluate_rule_condition(self, rule: MonitoringRule) -> bool:
        """Evaluate a monitoring rule condition."""
        try:
            # Create context for rule evaluation
            context = {
                "metrics": self.recent_metrics,
                "config": self.config,
                "datetime": datetime,
                "len": len,
                "any": any,
                "all": all,
                "sum": sum,
                "max": max,
                "min": min,
                "avg": lambda x: sum(x) / len(x) if x else 0,
            }

            # Add helper functions
            def get_latest_metric(service: str, metric_type: str = None) -> HealthMetric | None:
                service_metrics = context["metrics"].get(service, [])
                if not service_metrics:
                    return None

                if metric_type:
                    filtered = [m for m in service_metrics if m.metric_type.value == metric_type]
                    return filtered[-1] if filtered else None
                else:
                    return service_metrics[-1]

            def get_failure_count(service: str, minutes: int = 5) -> int:
                service_metrics = context["metrics"].get(service, [])
                cutoff_time = datetime.now(UTC) - timedelta(minutes=minutes)

                failures = 0
                for metric in service_metrics:
                    if metric.timestamp >= cutoff_time:
                        if (isinstance(metric.value, int | float) and metric.value == 0) or (
                            isinstance(metric.value, str) and "error" in metric.value.lower()
                        ):
                            failures += 1

                return failures

            context["get_latest_metric"] = get_latest_metric
            context["get_failure_count"] = get_failure_count

            # Evaluate the condition
            result = eval(rule.condition, {"__builtins__": {}}, context)
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to evaluate rule condition: {str(e)}")
            return False

    async def _execute_rule_action(self, rule: MonitoringRule, deployment_id: str):
        """Execute a monitoring rule action."""
        action = rule.action.lower()

        if action == "rollback" and self.rollback_orchestrator:
            # Preserve logs before rollback
            if self.config.get("log_preservation_enabled", True):
                preserved_logs = await self.log_preserver.preserve_system_logs(deployment_id)
                logger.info(f"Preserved logs to: {preserved_logs}")

            # Trigger automatic rollback
            trigger = RollbackTrigger(
                trigger_id=f"health_monitor_{rule.rule_id}_{int(datetime.now().timestamp())}",
                reason=RollbackReason.HEALTH_CHECK_FAILED,
                triggered_by="health_monitor",
                deployment_id=deployment_id,
                message=f"Health monitoring rule triggered: {rule.name}",
                metadata={"rule_id": rule.rule_id, "rule_name": rule.name, "condition": rule.condition},
            )

            # Determine rollback targets based on failed services
            targets = []
            for service, metrics in self.recent_metrics.items():
                if service != "system" and metrics:
                    latest_metric = metrics[-1]
                    if isinstance(latest_metric.value, int | float) and latest_metric.value == 0:
                        targets.append(RollbackTarget(service=service, environment=deployment_id))

            if not targets:
                # Default to all services if we can't determine specific failures
                targets = [
                    RollbackTarget(service="backend", environment=deployment_id),
                    RollbackTarget(service="frontend", environment=deployment_id),
                ]

            try:
                execution = await self.rollback_orchestrator.initiate_rollback(trigger, targets, "health_monitor")
                logger.info(f"Initiated automatic rollback: {execution.execution_id}")

            except Exception as e:
                logger.error(f"Failed to initiate rollback: {str(e)}")

        elif action == "alert":
            # Send alert notification
            await self._send_health_alert(rule, deployment_id)

        elif action.startswith("preserve_logs"):
            # Preserve logs for specific services
            services = rule.metadata.get("services", ["system"])
            for service in services:
                log_sources = rule.metadata.get(f"{service}_logs", [f"/var/log/{service}"])
                await self.log_preserver.preserve_service_logs(service, deployment_id, log_sources)

        else:
            logger.warning(f"Unknown rule action: {action}")

    async def _send_health_alert(self, rule: MonitoringRule, deployment_id: str):
        """Send health alert notification."""
        # Create alert message
        alert_data = {
            "rule_name": rule.name,
            "deployment_id": deployment_id,
            "condition": rule.condition,
            "triggered_at": datetime.now(UTC).isoformat(),
            "priority": rule.priority,
            "recent_metrics": {
                service: [
                    {"name": m.name, "value": m.value, "timestamp": m.timestamp.isoformat()}
                    for m in metrics[-3:]  # Last 3 metrics
                ]
                for service, metrics in self.recent_metrics.items()
            },
        }

        # Here you would integrate with your notification system
        logger.warning(f"HEALTH ALERT: {rule.name} - {alert_data}")

    def _cleanup_old_metrics(self):
        """Remove old metrics to prevent memory growth."""
        retention_minutes = self.config.get("metrics_retention_minutes", 60)
        cutoff_time = datetime.now(UTC) - timedelta(minutes=retention_minutes)

        for service in self.recent_metrics:
            self.recent_metrics[service] = [m for m in self.recent_metrics[service] if m.timestamp >= cutoff_time]

    async def generate_health_report(self, deployment_id: str) -> HealthReport:
        """Generate comprehensive health report."""
        # Analyze current health status
        overall_status = HealthStatus.HEALTHY
        services_status = {}
        failed_checks = []
        warnings = []
        recommendations = []

        for service, metrics in self.recent_metrics.items():
            if not metrics:
                services_status[service] = HealthStatus.UNKNOWN
                continue

            latest_metric = metrics[-1]
            service_status = HealthStatus.HEALTHY

            # Check if metric indicates failure
            if isinstance(latest_metric.value, int | float):
                if latest_metric.threshold_critical and latest_metric.value >= latest_metric.threshold_critical:
                    service_status = HealthStatus.CRITICAL
                    failed_checks.append(f"{service}: {latest_metric.name} critical")
                elif latest_metric.threshold_warning and latest_metric.value >= latest_metric.threshold_warning:
                    service_status = HealthStatus.WARNING
                    warnings.append(f"{service}: {latest_metric.name} warning")
            elif latest_metric.value == 0:  # Typically indicates failure
                service_status = HealthStatus.CRITICAL
                failed_checks.append(f"{service}: {latest_metric.name} failed")

            services_status[service] = service_status

            # Update overall status
            if service_status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
            elif service_status == HealthStatus.WARNING and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.WARNING

        # Generate recommendations
        if failed_checks:
            recommendations.append("Consider immediate rollback due to critical failures")
        if warnings:
            recommendations.append("Monitor warning conditions closely")
        if overall_status == HealthStatus.HEALTHY:
            recommendations.append("System is healthy - continue monitoring")

        # Collect all current metrics
        all_metrics = []
        for metrics_list in self.recent_metrics.values():
            all_metrics.extend(metrics_list)

        return HealthReport(
            report_id=f"health_report_{deployment_id}_{int(datetime.now().timestamp())}",
            deployment_id=deployment_id,
            environment=deployment_id,  # Assuming deployment_id includes environment
            created_at=datetime.now(UTC),
            overall_status=overall_status,
            services=services_status,
            metrics=all_metrics,
            failed_checks=failed_checks,
            warnings=warnings,
            recommendations=recommendations,
            logs_preserved={},  # Would be populated if logs were preserved
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.httpx_client.aclose()
        await self.stop_monitoring()


# Default configuration template
DEFAULT_CONFIG = """
monitoring_interval_seconds: 30
metrics_retention_minutes: 60
rollback_enabled: true
log_preservation_enabled: true
notification_channels:
  - slack
  - email

system_resource_thresholds:
  cpu_warning: 80
  cpu_critical: 95
  memory_warning: 80
  memory_critical: 95
  disk_warning: 85
  disk_critical: 95

health_checks:
  - check_id: backend_health
    service: backend
    name: Backend Health Check
    check_type: http_response
    endpoint_url: "https://api.pratiko.ai/health"
    interval_seconds: 30
    timeout_seconds: 10
    threshold_critical: 500  # HTTP status codes >= 500 are critical
    consecutive_failures_for_critical: 3

  - check_id: frontend_health
    service: frontend
    name: Frontend Health Check
    check_type: http_response
    endpoint_url: "https://pratiko.ai/health"
    interval_seconds: 30
    timeout_seconds: 10

  - check_id: database_health
    service: database
    name: Database Connection
    check_type: database_connection
    endpoint_url: "postgresql://user:pass@localhost/pratiko"
    interval_seconds: 60
    timeout_seconds: 15

  - check_id: system_cpu
    service: system
    name: CPU Usage
    check_type: system_resource
    threshold_warning: 80
    threshold_critical: 95
    metadata:
      resource: cpu

  - check_id: system_memory
    service: system
    name: Memory Usage
    check_type: system_resource
    threshold_warning: 80
    threshold_critical: 95
    metadata:
      resource: memory

monitoring_rules:
  - rule_id: critical_failure_rollback
    name: Critical Service Failure Rollback
    condition: "get_failure_count('backend', 5) >= 3 or get_failure_count('frontend', 5) >= 3"
    action: rollback
    priority: 1
    cooldown_minutes: 30

  - rule_id: system_resource_alert
    name: System Resource Alert
    condition: "get_latest_metric('system', 'system_resource') and get_latest_metric('system', 'system_resource').value > 90"
    action: alert
    priority: 2
    cooldown_minutes: 15

  - rule_id: multiple_service_degradation
    name: Multiple Service Degradation
    condition: "len([s for s, m in metrics.items() if m and any(isinstance(metric.value, (int, float)) and metric.value == 0 for metric in m[-3:])]) >= 2"
    action: rollback
    priority: 1
    cooldown_minutes: 20

services:
  backend:
    log_sources:
      - "/var/log/pratiko-backend"
      - "/var/log/nginx/error.log"
  frontend:
    log_sources:
      - "/var/log/nginx/access.log"
      - "/var/log/nginx/error.log"
"""


async def main():
    """Example usage of the health monitoring system."""
    # Create configuration file if it doesn't exist
    config_file = "health_monitor_config.yaml"
    if not os.path.exists(config_file):
        with open(config_file, "w") as f:
            f.write(DEFAULT_CONFIG)
        print(f"Created default configuration: {config_file}")

    # Initialize health monitor
    async with HealthMonitor(config_file) as monitor:
        # Set up rollback orchestrator integration
        from rollback_orchestrator import RollbackOrchestrator

        rollback_orchestrator = RollbackOrchestrator()
        monitor.set_rollback_orchestrator(rollback_orchestrator)

        deployment_id = "deploy-staging-20240115-143022"

        print(f"Starting health monitoring for deployment: {deployment_id}")

        # Start monitoring in background
        monitoring_task = asyncio.create_task(monitor.start_monitoring(deployment_id))

        # Let it run for a while for demonstration
        await asyncio.sleep(60)

        # Generate health report
        report = await monitor.generate_health_report(deployment_id)
        print("\nHealth Report:")
        print(f"Overall Status: {report.overall_status.value}")
        print(f"Services: {report.services}")
        print(f"Failed Checks: {report.failed_checks}")
        print(f"Warnings: {report.warnings}")
        print(f"Recommendations: {report.recommendations}")

        # Stop monitoring
        await monitor.stop_monitoring()
        monitoring_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
