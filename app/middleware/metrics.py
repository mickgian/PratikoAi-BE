"""DEV-418: Monitoring and Alerting Infrastructure.

Prometheus-compatible metrics endpoint + basic metrics registry.
Tracks: P95 response time, matching latency, import throughput,
communication generation time, error rates, DB pool, Redis cache hit rate.

Reference: PRD §4.1 (99.9% uptime via Prometheus).
"""

import time
from collections import defaultdict
from typing import Any

from app.core.logging import logger


class MetricsRegistry:
    """In-memory metrics registry with Prometheus-compatible output."""

    def __init__(self) -> None:
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)

    def increment(
        self,
        name: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        self._counters[key] += value

    def get(
        self,
        name: str,
        labels: dict[str, str] | None = None,
    ) -> float:
        """Get current counter value."""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0.0)

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge metric."""
        self._gauges[name] = value

    def get_gauge(self, name: str) -> float:
        """Get current gauge value."""
        return self._gauges.get(name, 0.0)

    def observe(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a histogram observation."""
        key = self._make_key(name, labels)
        self._histograms[key].append(value)

    def format_prometheus(self) -> str:
        """Format all metrics in Prometheus text exposition format."""
        lines = []

        # Counters
        for key, value in sorted(self._counters.items()):
            name, labels_str = self._parse_key(key)
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name}{labels_str} {value}")

        # Gauges
        for name, value in sorted(self._gauges.items()):
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")

        # Histograms (simplified as summary)
        for key, values in sorted(self._histograms.items()):
            name, labels_str = self._parse_key(key)
            if values:
                sorted_vals = sorted(values)
                count = len(sorted_vals)
                total = sum(sorted_vals)
                p50 = sorted_vals[int(count * 0.5)] if count > 0 else 0
                p95 = sorted_vals[int(count * 0.95)] if count > 0 else 0
                p99 = sorted_vals[int(count * 0.99)] if count > 0 else 0
                lines.append(f"# TYPE {name} summary")
                lines.append(f'{name}{{quantile="0.5"{self._merge_labels(labels_str)}}} {p50}')
                lines.append(f'{name}{{quantile="0.95"{self._merge_labels(labels_str)}}} {p95}')
                lines.append(f'{name}{{quantile="0.99"{self._merge_labels(labels_str)}}} {p99}')
                lines.append(f"{name}_count{labels_str} {count}")
                lines.append(f"{name}_sum{labels_str} {total}")

        return "\n".join(lines)

    @staticmethod
    def _make_key(name: str, labels: dict[str, str] | None = None) -> str:
        """Create a unique key from name and labels."""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    @staticmethod
    def _parse_key(key: str) -> tuple[str, str]:
        """Parse key back to name and labels string."""
        if "{" in key:
            name = key[: key.index("{")]
            labels_str = key[key.index("{") :]
            return name, labels_str
        return key, ""

    @staticmethod
    def _merge_labels(existing: str) -> str:
        """Merge additional labels into existing label string."""
        if not existing:
            return ""
        return "," + existing.strip("{}")


# Global registry
metrics_registry = MetricsRegistry()


class MetricsMiddleware:
    """ASGI middleware for tracking HTTP request metrics."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        """Process request and record metrics."""
        if scope.get("type") != "http":
            if self.app:
                await self.app(scope, receive, send)
            return

        start_time = time.monotonic()
        path = scope.get("path", "/")
        method = scope.get("method", "GET")

        try:
            if self.app:
                await self.app(scope, receive, send)
        finally:
            duration = time.monotonic() - start_time
            metrics_registry.increment(
                "http_requests_total",
                labels={"method": method, "path": path},
            )
            metrics_registry.observe(
                "http_request_duration_seconds",
                duration,
                labels={"path": path},
            )
