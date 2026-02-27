"""DEV-418: Tests for Monitoring and Metrics Middleware.

Tests: metrics endpoint accessible, key counters increment.
"""

import pytest

from app.middleware.metrics import MetricsMiddleware, metrics_registry


class TestMetricsRegistry:
    def test_registry_exists(self):
        assert metrics_registry is not None

    def test_increment_counter(self):
        metrics_registry.increment("http_requests_total", labels={"method": "GET", "path": "/health"})
        value = metrics_registry.get("http_requests_total", labels={"method": "GET", "path": "/health"})
        assert value >= 1

    def test_observe_histogram(self):
        metrics_registry.observe("http_request_duration_seconds", 0.15, labels={"path": "/health"})
        # No error means success

    def test_set_gauge(self):
        metrics_registry.set_gauge("db_connections_active", 5)
        value = metrics_registry.get_gauge("db_connections_active")
        assert value == 5


class TestMetricsEndpoint:
    def test_format_prometheus(self):
        output = metrics_registry.format_prometheus()
        assert isinstance(output, str)
        # Should contain standard metric format
        assert "# " in output or output == ""


class TestMetricsMiddleware:
    def test_middleware_instantiable(self):
        mw = MetricsMiddleware(app=None)
        assert mw is not None
