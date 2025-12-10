"""Performance monitoring system for comprehensive application metrics."""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import psutil

from app.core.config import settings
from app.core.logging import logger


class PerformanceAlert(str, Enum):
    """Performance alert types."""

    HIGH_CPU = "high_cpu"
    HIGH_MEMORY = "high_memory"
    HIGH_RESPONSE_TIME = "high_response_time"
    HIGH_ERROR_RATE = "high_error_rate"
    LOW_THROUGHPUT = "low_throughput"
    DATABASE_SLOW = "database_slow"
    CACHE_MISS_HIGH = "cache_miss_high"


@dataclass
class RequestMetrics:
    """Metrics for individual requests."""

    timestamp: datetime
    method: str
    path: str
    status_code: int
    response_time: float
    request_size: int
    response_size: int
    user_id: str | None = None
    session_id: str | None = None
    error_message: str | None = None


@dataclass
class SystemMetrics:
    """System-level performance metrics."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    active_connections: int
    thread_count: int


@dataclass
class EndpointMetrics:
    """Aggregated metrics for API endpoints."""

    endpoint: str
    method: str
    request_count: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    error_count: int
    error_rate: float
    total_bytes_sent: int
    total_bytes_received: int
    last_request: datetime


class PerformanceMonitor:
    """Comprehensive performance monitoring system."""

    def __init__(self):
        """Initialize performance monitor."""
        self.enabled = True
        self.monitoring_interval = 30  # seconds
        self.metrics_retention_hours = 24
        self.request_buffer_size = 10000

        # Performance thresholds
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "response_time_p95": 2.0,  # seconds
            "error_rate": 0.05,  # 5%
            "disk_usage": 90.0,
            "cache_miss_rate": 0.3,  # 30%
        }

        # Metrics storage
        self.request_metrics: deque[RequestMetrics] = deque(maxlen=self.request_buffer_size)
        self.system_metrics: deque[SystemMetrics] = deque(maxlen=2880)  # 24 hours at 30s intervals
        self.endpoint_metrics: dict[str, EndpointMetrics] = {}

        # Alert tracking
        self.active_alerts: dict[PerformanceAlert, datetime] = {}
        self.alert_history: deque[dict[str, Any]] = deque(maxlen=1000)

        # Performance counters
        self.counters = {
            "total_requests": 0,
            "total_errors": 0,
            "total_cache_hits": 0,
            "total_cache_misses": 0,
            "total_db_queries": 0,
            "total_response_time": 0.0,
        }

        # System baseline (for anomaly detection)
        self.baseline_metrics = {
            "avg_cpu": 0.0,
            "avg_memory": 0.0,
            "avg_response_time": 0.0,
            "baseline_established": False,
        }

        # Start monitoring tasks (only if event loop is running)
        if self.enabled:
            try:
                asyncio.get_running_loop()
                asyncio.create_task(self._system_metrics_collector())
                asyncio.create_task(self._performance_analyzer())
            except RuntimeError:
                # No running event loop - tasks will be started when needed
                pass

    async def record_request_metrics(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time: float,
        request_size: int = 0,
        response_size: int = 0,
        user_id: str | None = None,
        session_id: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Record metrics for a request.

        Args:
            method: HTTP method
            path: Request path
            status_code: HTTP status code
            response_time: Response time in seconds
            request_size: Request size in bytes
            response_size: Response size in bytes
            user_id: User identifier
            session_id: Session identifier
            error_message: Error message if applicable
        """
        try:
            if not self.enabled:
                return

            # Create request metrics
            metrics = RequestMetrics(
                timestamp=datetime.utcnow(),
                method=method,
                path=path,
                status_code=status_code,
                response_time=response_time,
                request_size=request_size,
                response_size=response_size,
                user_id=user_id,
                session_id=session_id,
                error_message=error_message,
            )

            # Add to request buffer
            self.request_metrics.append(metrics)

            # Update counters
            self.counters["total_requests"] += 1
            self.counters["total_response_time"] += response_time

            if status_code >= 400:
                self.counters["total_errors"] += 1

            # Update endpoint metrics
            await self._update_endpoint_metrics(metrics)

            # Check for performance alerts
            await self._check_performance_alerts(metrics)  # type: ignore[attr-defined]

        except Exception as e:
            logger.error("request_metrics_recording_failed", method=method, path=path, error=str(e), exc_info=True)

    async def _update_endpoint_metrics(self, request_metrics: RequestMetrics) -> None:
        """Update aggregated endpoint metrics."""
        try:
            endpoint_key = f"{request_metrics.method} {request_metrics.path}"

            if endpoint_key not in self.endpoint_metrics:
                self.endpoint_metrics[endpoint_key] = EndpointMetrics(
                    endpoint=request_metrics.path,
                    method=request_metrics.method,
                    request_count=0,
                    avg_response_time=0.0,
                    min_response_time=float("inf"),
                    max_response_time=0.0,
                    p95_response_time=0.0,
                    p99_response_time=0.0,
                    error_count=0,
                    error_rate=0.0,
                    total_bytes_sent=0,
                    total_bytes_received=0,
                    last_request=request_metrics.timestamp,
                )

            endpoint = self.endpoint_metrics[endpoint_key]

            # Update basic metrics
            endpoint.request_count += 1
            endpoint.total_bytes_sent += request_metrics.response_size
            endpoint.total_bytes_received += request_metrics.request_size
            endpoint.last_request = request_metrics.timestamp

            # Update response time metrics
            endpoint.min_response_time = min(endpoint.min_response_time, request_metrics.response_time)
            endpoint.max_response_time = max(endpoint.max_response_time, request_metrics.response_time)

            # Calculate average response time
            total_time = endpoint.avg_response_time * (endpoint.request_count - 1) + request_metrics.response_time
            endpoint.avg_response_time = total_time / endpoint.request_count

            # Update error metrics
            if request_metrics.status_code >= 400:
                endpoint.error_count += 1

            endpoint.error_rate = endpoint.error_count / endpoint.request_count

            # Calculate percentiles (simplified - would use actual percentile calculation in production)
            if endpoint.request_count % 100 == 0:  # Recalculate every 100 requests
                await self._recalculate_endpoint_percentiles(endpoint_key)

        except Exception as e:
            logger.error(
                "endpoint_metrics_update_failed",
                endpoint=f"{request_metrics.method} {request_metrics.path}",
                error=str(e),
                exc_info=True,
            )

    async def _recalculate_endpoint_percentiles(self, endpoint_key: str) -> None:
        """Recalculate percentiles for an endpoint."""
        try:
            endpoint = self.endpoint_metrics[endpoint_key]

            # Get recent response times for this endpoint (last 1000 requests)
            recent_times = [
                metrics.response_time
                for metrics in list(self.request_metrics)[-1000:]
                if f"{metrics.method} {metrics.path}" == endpoint_key
            ]

            if recent_times:
                recent_times.sort()
                n = len(recent_times)

                # Calculate percentiles
                p95_index = int(0.95 * n)
                p99_index = int(0.99 * n)

                endpoint.p95_response_time = recent_times[p95_index] if p95_index < n else recent_times[-1]
                endpoint.p99_response_time = recent_times[p99_index] if p99_index < n else recent_times[-1]

        except Exception as e:
            logger.error("percentile_calculation_failed", endpoint_key=endpoint_key, error=str(e))

    async def _system_metrics_collector(self) -> None:
        """Background task to collect system metrics."""
        while self.enabled:
            try:
                await asyncio.sleep(self.monitoring_interval)

                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage("/")
                disk_io = psutil.disk_io_counters()
                network_io = psutil.net_io_counters()

                # Create system metrics
                metrics = SystemMetrics(
                    timestamp=datetime.utcnow(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_used_mb=memory.used / (1024 * 1024),
                    memory_available_mb=memory.available / (1024 * 1024),
                    disk_usage_percent=disk.percent,
                    disk_io_read_mb=disk_io.read_bytes / (1024 * 1024) if disk_io else 0,
                    disk_io_write_mb=disk_io.write_bytes / (1024 * 1024) if disk_io else 0,
                    network_sent_mb=network_io.bytes_sent / (1024 * 1024) if network_io else 0,
                    network_recv_mb=network_io.bytes_recv / (1024 * 1024) if network_io else 0,
                    active_connections=len(psutil.net_connections()),
                    thread_count=psutil.Process().num_threads(),
                )

                # Add to metrics buffer
                self.system_metrics.append(metrics)

                # Update baseline metrics
                await self._update_baseline_metrics(metrics)

                logger.debug(
                    "system_metrics_collected",
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    disk_percent=disk.percent,
                )

            except Exception as e:
                logger.error("system_metrics_collection_failed", error=str(e), exc_info=True)

    async def _update_baseline_metrics(self, metrics: SystemMetrics) -> None:
        """Update baseline metrics for anomaly detection."""
        try:
            if len(self.system_metrics) < 10:  # Need minimum data points
                return

            # Calculate rolling averages (last 10 data points)
            recent_metrics = list(self.system_metrics)[-10:]

            self.baseline_metrics["avg_cpu"] = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
            self.baseline_metrics["avg_memory"] = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)

            # Calculate average response time from recent requests
            recent_requests = list(self.request_metrics)[-100:]
            if recent_requests:
                self.baseline_metrics["avg_response_time"] = sum(r.response_time for r in recent_requests) / len(
                    recent_requests
                )

            self.baseline_metrics["baseline_established"] = True

        except Exception as e:
            logger.error("baseline_metrics_update_failed", error=str(e))

    async def _performance_analyzer(self) -> None:
        """Background task to analyze performance and generate alerts."""
        while self.enabled:
            try:
                await asyncio.sleep(60)  # Analyze every minute

                # Analyze system performance
                await self._analyze_system_performance()

                # Analyze request performance
                await self._analyze_request_performance()

                # Clean up old data
                await self._cleanup_old_metrics()

            except Exception as e:
                logger.error("performance_analysis_failed", error=str(e), exc_info=True)

    async def _analyze_system_performance(self) -> None:
        """Analyze system performance and generate alerts."""
        try:
            if not self.system_metrics:
                return

            latest_metrics = self.system_metrics[-1]

            # Check CPU usage
            if latest_metrics.cpu_percent > self.thresholds["cpu_percent"]:
                await self._trigger_alert(PerformanceAlert.HIGH_CPU, f"CPU usage at {latest_metrics.cpu_percent:.1f}%")

            # Check memory usage
            if latest_metrics.memory_percent > self.thresholds["memory_percent"]:
                await self._trigger_alert(
                    PerformanceAlert.HIGH_MEMORY, f"Memory usage at {latest_metrics.memory_percent:.1f}%"
                )

            # Check disk usage
            if latest_metrics.disk_usage_percent > self.thresholds["disk_usage"]:
                await self._trigger_alert(
                    PerformanceAlert.HIGH_CPU,  # Reusing alert type
                    f"Disk usage at {latest_metrics.disk_usage_percent:.1f}%",
                )

        except Exception as e:
            logger.error("system_performance_analysis_failed", error=str(e))

    async def _analyze_request_performance(self) -> None:
        """Analyze request performance and generate alerts."""
        try:
            if not self.request_metrics:
                return

            # Analyze recent requests (last 5 minutes)
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)
            recent_requests = [r for r in self.request_metrics if r.timestamp >= cutoff_time]

            if not recent_requests:
                return

            # Calculate error rate
            error_count = sum(1 for r in recent_requests if r.status_code >= 400)
            error_rate = error_count / len(recent_requests)

            if error_rate > self.thresholds["error_rate"]:
                await self._trigger_alert(PerformanceAlert.HIGH_ERROR_RATE, f"Error rate at {error_rate * 100:.1f}%")

            # Calculate P95 response time
            response_times = sorted([r.response_time for r in recent_requests])
            if response_times:
                p95_index = int(0.95 * len(response_times))
                p95_time = response_times[p95_index] if p95_index < len(response_times) else response_times[-1]

                if p95_time > self.thresholds["response_time_p95"]:
                    await self._trigger_alert(
                        PerformanceAlert.HIGH_RESPONSE_TIME, f"P95 response time at {p95_time:.2f}s"
                    )

        except Exception as e:
            logger.error("request_performance_analysis_failed", error=str(e))

    async def _trigger_alert(self, alert_type: PerformanceAlert, message: str) -> None:
        """Trigger a performance alert."""
        try:
            current_time = datetime.utcnow()

            # Check if alert is already active (avoid spam)
            if alert_type in self.active_alerts:
                last_alert = self.active_alerts[alert_type]
                if current_time - last_alert < timedelta(minutes=10):  # 10-minute cooldown
                    return

            # Record alert
            self.active_alerts[alert_type] = current_time

            alert_data = {
                "alert_type": alert_type.value,
                "message": message,
                "timestamp": current_time.isoformat(),
                "severity": "warning",
            }

            # Determine severity
            if alert_type in [PerformanceAlert.HIGH_CPU, PerformanceAlert.HIGH_MEMORY]:
                if "90" in message or "95" in message:
                    alert_data["severity"] = "critical"

            self.alert_history.append(alert_data)

            logger.warning(
                "performance_alert_triggered",
                alert_type=alert_type.value,
                message=message,
                severity=alert_data["severity"],
            )

        except Exception as e:
            logger.error("alert_triggering_failed", alert_type=alert_type.value, message=message, error=str(e))

    async def _cleanup_old_metrics(self) -> None:
        """Clean up old metrics data."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.metrics_retention_hours)

            # Clean up old alerts
            self.active_alerts = {
                alert_type: timestamp
                for alert_type, timestamp in self.active_alerts.items()
                if timestamp >= cutoff_time
            }

            logger.debug(
                "metrics_cleanup_completed",
                request_metrics_count=len(self.request_metrics),
                system_metrics_count=len(self.system_metrics),
                active_alerts_count=len(self.active_alerts),
            )

        except Exception as e:
            logger.error("metrics_cleanup_failed", error=str(e))

    def get_performance_summary(self) -> dict[str, Any]:
        """Get comprehensive performance summary.

        Returns:
            Performance summary data
        """
        try:
            current_time = datetime.utcnow()

            # System metrics summary
            system_summary = {}
            if self.system_metrics:
                latest_system = self.system_metrics[-1]
                system_summary = {
                    "cpu_percent": latest_system.cpu_percent,
                    "memory_percent": latest_system.memory_percent,
                    "memory_used_mb": round(latest_system.memory_used_mb, 1),
                    "disk_usage_percent": latest_system.disk_usage_percent,
                    "active_connections": latest_system.active_connections,
                    "thread_count": latest_system.thread_count,
                    "last_updated": latest_system.timestamp.isoformat(),
                }

            # Request metrics summary
            request_summary = {
                "total_requests": self.counters["total_requests"],
                "total_errors": self.counters["total_errors"],
                "error_rate": (
                    self.counters["total_errors"] / self.counters["total_requests"] * 100
                    if self.counters["total_requests"] > 0
                    else 0
                ),
                "avg_response_time": (
                    self.counters["total_response_time"] / self.counters["total_requests"]
                    if self.counters["total_requests"] > 0
                    else 0
                ),
            }

            # Top endpoints by request count
            top_endpoints = sorted(self.endpoint_metrics.values(), key=lambda x: x.request_count, reverse=True)[:10]

            # Slowest endpoints
            slowest_endpoints = sorted(
                self.endpoint_metrics.values(), key=lambda x: x.avg_response_time, reverse=True
            )[:5]

            # Recent alerts
            recent_alerts = [
                alert
                for alert in self.alert_history
                if datetime.fromisoformat(alert["timestamp"]) >= current_time - timedelta(hours=1)
            ]

            summary = {
                "monitoring_status": "active" if self.enabled else "inactive",
                "timestamp": current_time.isoformat(),
                "system_metrics": system_summary,
                "request_metrics": request_summary,
                "performance_thresholds": self.thresholds,
                "top_endpoints": [
                    {
                        "endpoint": f"{ep.method} {ep.endpoint}",
                        "request_count": ep.request_count,
                        "avg_response_time": round(ep.avg_response_time, 3),
                        "error_rate": round(ep.error_rate * 100, 1),
                    }
                    for ep in top_endpoints
                ],
                "slowest_endpoints": [
                    {
                        "endpoint": f"{ep.method} {ep.endpoint}",
                        "avg_response_time": round(ep.avg_response_time, 3),
                        "p95_response_time": round(ep.p95_response_time, 3),
                        "request_count": ep.request_count,
                    }
                    for ep in slowest_endpoints
                ],
                "active_alerts": list(self.active_alerts.keys()),
                "recent_alerts": recent_alerts[-10:],  # Last 10 alerts
                "baseline_metrics": self.baseline_metrics,
            }

            return summary

        except Exception as e:
            logger.error("performance_summary_generation_failed", error=str(e), exc_info=True)
            return {"error": str(e), "status": "error"}

    def get_endpoint_details(self, endpoint_pattern: str | None = None) -> list[dict[str, Any]]:
        """Get detailed endpoint performance metrics.

        Args:
            endpoint_pattern: Optional pattern to filter endpoints

        Returns:
            List of endpoint details
        """
        try:
            endpoint_details = []

            for endpoint_key, metrics in self.endpoint_metrics.items():
                if endpoint_pattern and endpoint_pattern not in endpoint_key:
                    continue

                details = {
                    "endpoint": f"{metrics.method} {metrics.endpoint}",
                    "request_count": metrics.request_count,
                    "avg_response_time": round(metrics.avg_response_time, 3),
                    "min_response_time": round(metrics.min_response_time, 3),
                    "max_response_time": round(metrics.max_response_time, 3),
                    "p95_response_time": round(metrics.p95_response_time, 3),
                    "p99_response_time": round(metrics.p99_response_time, 3),
                    "error_count": metrics.error_count,
                    "error_rate": round(metrics.error_rate * 100, 1),
                    "total_bytes_sent": metrics.total_bytes_sent,
                    "total_bytes_received": metrics.total_bytes_received,
                    "last_request": metrics.last_request.isoformat(),
                    "throughput_rps": (
                        metrics.request_count / max(1, (datetime.utcnow() - metrics.last_request).total_seconds())
                        if metrics.request_count > 0
                        else 0
                    ),
                }

                endpoint_details.append(details)

            # Sort by request count
            endpoint_details.sort(key=lambda x: int(x.get("request_count", 0)), reverse=True)  # type: ignore[call-overload]

            return endpoint_details

        except Exception as e:
            logger.error(
                "endpoint_details_retrieval_failed", endpoint_pattern=endpoint_pattern, error=str(e), exc_info=True
            )
            return []

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self.counters["total_cache_hits"] += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self.counters["total_cache_misses"] += 1

    def record_db_query(self) -> None:
        """Record a database query."""
        self.counters["total_db_queries"] += 1

    def get_cache_statistics(self) -> dict[str, Any]:
        """Get cache performance statistics."""
        total_cache_requests = self.counters["total_cache_hits"] + self.counters["total_cache_misses"]

        return {
            "total_cache_hits": self.counters["total_cache_hits"],
            "total_cache_misses": self.counters["total_cache_misses"],
            "cache_hit_rate": (
                self.counters["total_cache_hits"] / total_cache_requests * 100 if total_cache_requests > 0 else 0
            ),
            "cache_miss_rate": (
                self.counters["total_cache_misses"] / total_cache_requests * 100 if total_cache_requests > 0 else 0
            ),
        }


# Global instance
performance_monitor = PerformanceMonitor()
