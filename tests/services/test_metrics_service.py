"""Tests for MetricsService - system uptime and performance metrics collection.

Covers the fix for the await bug where synchronous get_performance_summary()
was incorrectly awaited, causing System Uptime to always report 0%.
"""

import sys
from unittest.mock import MagicMock

import pytest

# Mock database modules before any app imports to avoid DB connection errors.
# The metrics service and performance monitor don't need real DB connections
# for the uptime/response-time tests.
if "app.models.database" not in sys.modules:
    _mock_db_models = MagicMock()
    sys.modules["app.models.database"] = _mock_db_models
if "app.services.database" not in sys.modules:
    _mock_db_svc = MagicMock()
    sys.modules["app.services.database"] = _mock_db_svc

from app.core.performance.performance_monitor import PerformanceMonitor  # noqa: E402


class TestGetSystemUptime:
    """Tests for _get_system_uptime() returning valid uptime values."""

    @pytest.mark.asyncio
    async def test_system_uptime_returns_nonzero_when_monitor_is_available(self):
        """System uptime should not be 0% when the performance monitor is running.

        Root cause bug: get_performance_summary() is synchronous,
        but _get_system_uptime() was awaiting it, causing a TypeError caught
        by the except block which returned 0.0.
        """
        from app.services.metrics_service import MetricsService

        service = MetricsService()
        uptime = await service._get_system_uptime()
        assert uptime > 0.0, "Uptime must not be 0% when the app is running"

    @pytest.mark.asyncio
    async def test_system_uptime_is_valid_percentage(self):
        """System uptime should be a valid percentage between 0 and 100."""
        from app.services.metrics_service import MetricsService

        service = MetricsService()
        uptime = await service._get_system_uptime()
        assert 0.0 <= uptime <= 100.0

    @pytest.mark.asyncio
    async def test_system_uptime_reflects_process_uptime(self):
        """System uptime should be based on actual process running time."""
        from app.services.metrics_service import MetricsService

        service = MetricsService()
        uptime = await service._get_system_uptime()
        assert uptime > 0.0


class TestGetApiResponseTimeP95:
    """Tests for _get_api_response_time_p95() with synchronous performance_monitor."""

    @pytest.mark.asyncio
    async def test_api_response_time_does_not_raise_on_sync_call(self):
        """Calling get_performance_summary() must not raise TypeError.

        Previously failed because of: await sync_function()
        """
        from app.services.metrics_service import MetricsService

        service = MetricsService()
        result = await service._get_api_response_time_p95()
        assert isinstance(result, float)

    @pytest.mark.asyncio
    async def test_api_response_time_returns_zero_when_no_requests(self):
        """Returns 0.0 when there are no recorded requests."""
        from app.services.metrics_service import MetricsService

        service = MetricsService()
        result = await service._get_api_response_time_p95()
        assert result == 0.0


class TestPerformanceMonitorUptimeTracking:
    """Tests for uptime_percentage in PerformanceMonitor.get_performance_summary()."""

    def test_performance_summary_includes_uptime_percentage(self):
        """get_performance_summary() must include an uptime_percentage key."""
        monitor = PerformanceMonitor()
        summary = monitor.get_performance_summary()
        assert "uptime_percentage" in summary, "Performance summary must include uptime_percentage"

    def test_uptime_percentage_is_positive_for_running_process(self):
        """uptime_percentage should be > 0 when the process is running."""
        monitor = PerformanceMonitor()
        summary = monitor.get_performance_summary()
        assert summary["uptime_percentage"] > 0.0

    def test_uptime_percentage_is_valid_range(self):
        """uptime_percentage should be between 0 and 100."""
        monitor = PerformanceMonitor()
        summary = monitor.get_performance_summary()
        assert 0.0 <= summary["uptime_percentage"] <= 100.0


class TestCollectBusinessMetricsUptime:
    """Tests for uptime metric in business metrics collection."""

    @pytest.mark.asyncio
    async def test_system_uptime_metric_not_zero_for_running_app(self):
        """System Uptime metric should not report 0% for a running application."""
        from app.services.metrics_service import Environment, MetricsService

        service = MetricsService()
        metrics = await service.collect_business_metrics(Environment.DEVELOPMENT)

        uptime_metric = next((m for m in metrics if m.name == "System Uptime"), None)
        assert uptime_metric is not None, "System Uptime metric must be present"
        assert uptime_metric.value > 0.0, f"System Uptime should not be 0% for running app, got {uptime_metric.value}"

    @pytest.mark.asyncio
    async def test_system_uptime_metric_status_not_fail(self):
        """System Uptime status should not be FAIL when the process is healthy."""
        from app.services.metrics_service import Environment, MetricsService, MetricStatus

        service = MetricsService()
        metrics = await service.collect_business_metrics(Environment.DEVELOPMENT)

        uptime_metric = next((m for m in metrics if m.name == "System Uptime"), None)
        assert uptime_metric is not None
        assert uptime_metric.status != MetricStatus.FAIL, (
            f"Uptime status should not be FAIL, value was {uptime_metric.value}%"
        )
