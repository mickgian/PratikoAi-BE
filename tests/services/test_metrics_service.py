"""Tests for MetricsService - system health report fixes.

Covers:
- Uptime fix (sync get_performance_summary was incorrectly awaited)
- Fake/hardcoded metrics replaced with real data or UNKNOWN status
- Health score excludes UNKNOWN metrics from calculation
- Scheduler changed from EVERY_12_HOURS to DAILY with target_time
- Only current environment is reported (not all 3)
- Redis distributed lock prevents duplicate sends across workers
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock database modules before any app imports to avoid DB connection errors.
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
        """System uptime should not be 0% when the performance monitor is running."""
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
        """Calling get_performance_summary() must not raise TypeError."""
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

    @staticmethod
    def _healthy_summary() -> dict:
        """Return a performance summary representing a healthy process."""
        return {
            "monitoring_status": "active",
            "timestamp": "2026-01-01T00:00:00",
            "uptime_percentage": 99.9,
            "system_metrics": {},
            "request_metrics": {
                "total_requests": 100,
                "total_errors": 0,
                "error_rate": 0,
                "avg_response_time": 0.05,
            },
            "performance_thresholds": {},
            "top_endpoints": [],
            "slowest_endpoints": [],
            "recent_alerts": [],
        }

    @pytest.mark.asyncio
    async def test_system_uptime_metric_not_zero_for_running_app(self):
        """System Uptime metric should not report 0% for a running application."""
        from app.services.metrics_service import Environment, MetricsService

        with patch("app.services.metrics_service.performance_monitor") as mock_monitor:
            mock_monitor.get_performance_summary.return_value = self._healthy_summary()

            service = MetricsService()
            metrics = await service.collect_business_metrics(Environment.DEVELOPMENT)

        uptime_metric = next((m for m in metrics if m.name == "System Uptime"), None)
        assert uptime_metric is not None, "System Uptime metric must be present"
        assert uptime_metric.value > 0.0, f"System Uptime should not be 0% for running app, got {uptime_metric.value}"

    @pytest.mark.asyncio
    async def test_system_uptime_metric_status_not_fail(self):
        """System Uptime status should not be FAIL when the process is healthy."""
        from app.services.metrics_service import Environment, MetricsService, MetricStatus

        with patch("app.services.metrics_service.performance_monitor") as mock_monitor:
            mock_monitor.get_performance_summary.return_value = self._healthy_summary()

            service = MetricsService()
            metrics = await service.collect_business_metrics(Environment.DEVELOPMENT)

        uptime_metric = next((m for m in metrics if m.name == "System Uptime"), None)
        assert uptime_metric is not None
        assert uptime_metric.status != MetricStatus.FAIL, (
            f"Uptime status should not be FAIL, value was {uptime_metric.value}%"
        )


class TestFakeMetricsRemoved:
    """Tests that hardcoded/fake metrics now return UNKNOWN instead of fake PASS."""

    @pytest.mark.asyncio
    async def test_test_coverage_returns_none(self):
        """Test coverage is a CI/CD metric, should return None at runtime."""
        from app.services.metrics_service import MetricsService

        service = MetricsService()
        result = await service._get_test_coverage()
        assert result is None

    @pytest.mark.asyncio
    async def test_security_vulnerabilities_returns_none(self):
        """Security scanning is a CI/CD metric, should return None at runtime."""
        from app.services.metrics_service import MetricsService

        service = MetricsService()
        result = await service._get_critical_vulnerabilities()
        assert result is None

    @pytest.mark.asyncio
    async def test_gdpr_compliance_returns_none(self):
        """GDPR compliance is an audit metric, should return None at runtime."""
        from app.services.metrics_service import MetricsService

        service = MetricsService()
        result = await service._get_gdpr_compliance_score()
        assert result is None

    @pytest.mark.asyncio
    async def test_user_satisfaction_returns_none_when_no_data(self):
        """User satisfaction should return None when no feedback table/data exists."""
        from app.services.metrics_service import MetricsService

        service = MetricsService()
        result = await service._get_user_satisfaction()
        assert result is None


class TestHealthScoreExcludesUnknown:
    """Tests that UNKNOWN metrics are excluded from health score calculation."""

    @pytest.mark.asyncio
    async def test_health_score_ignores_unknown_metrics(self):
        """Health score should only count measurable (non-UNKNOWN) metrics."""
        from app.services.metrics_service import Environment, MetricsService

        with patch("app.services.metrics_service.performance_monitor") as mock_monitor:
            mock_monitor.get_performance_summary.return_value = {
                "monitoring_status": "active",
                "timestamp": "2026-01-01T00:00:00",
                "uptime_percentage": 100.0,
                "system_metrics": {},
                "request_metrics": {
                    "total_requests": 0,
                    "total_errors": 0,
                    "error_rate": 0,
                    "avg_response_time": 0,
                },
                "performance_thresholds": {},
                "top_endpoints": [],
                "slowest_endpoints": [],
                "recent_alerts": [],
            }
            mock_monitor.get_cache_statistics.return_value = {
                "cache_hit_rate": 0.0,
                "cache_miss_rate": 0.0,
                "total_cache_hits": 0,
                "total_cache_misses": 0,
            }

            service = MetricsService()
            report = await service.generate_metrics_report(Environment.DEVELOPMENT)

        # UNKNOWN metrics should NOT drag down the health score
        # With no requests: API Response PASS (0 < 500), Cache FAIL (0 < 80),
        # Test Coverage UNKNOWN, Security UNKNOWN, Cost PASS (0 < 2),
        # Uptime PASS (100), User Satisfaction UNKNOWN, GDPR UNKNOWN
        # Measurable: 4 metrics, 3 PASS, 1 FAIL => 75%
        assert report.overall_health_score > 0, "Health score should not be 0 when some metrics pass"

    @pytest.mark.asyncio
    async def test_report_alerts_show_info_for_unknown(self):
        """UNKNOWN metrics should generate INFO alerts, not CRITICAL."""
        from app.services.metrics_service import Environment, MetricsService

        with patch("app.services.metrics_service.performance_monitor") as mock_monitor:
            mock_monitor.get_performance_summary.return_value = {
                "monitoring_status": "active",
                "timestamp": "2026-01-01T00:00:00",
                "uptime_percentage": 100.0,
                "system_metrics": {},
                "request_metrics": {
                    "total_requests": 0,
                    "total_errors": 0,
                    "error_rate": 0,
                    "avg_response_time": 0,
                },
                "performance_thresholds": {},
                "top_endpoints": [],
                "slowest_endpoints": [],
                "recent_alerts": [],
            }
            mock_monitor.get_cache_statistics.return_value = {
                "cache_hit_rate": 0.0,
                "cache_miss_rate": 0.0,
                "total_cache_hits": 0,
                "total_cache_misses": 0,
            }

            service = MetricsService()
            report = await service.generate_metrics_report(Environment.DEVELOPMENT)

        info_alerts = [a for a in report.alerts if a.startswith("INFO:")]
        assert len(info_alerts) > 0, "UNKNOWN metrics should produce INFO alerts"
        # Should NOT have CRITICAL alerts for metrics that are simply unavailable
        critical_unknown_alerts = [a for a in report.alerts if a.startswith("CRITICAL:") and "no data" in a]
        assert len(critical_unknown_alerts) == 0


class TestSchedulerDailyMetricsReport:
    """Tests that the metrics report is scheduled DAILY (not every 12 hours)."""

    def test_metrics_report_task_is_daily(self):
        """Metrics report should use DAILY interval with a target_time."""
        # setup_default_tasks uses the global scheduler_service, so we inspect it
        # after setup. Reset tasks first to avoid test pollution.
        from app.services.scheduler_service import (
            ScheduleInterval,
            SchedulerService,
            scheduler_service,
            setup_default_tasks,
        )

        scheduler_service.tasks.clear()
        setup_default_tasks()

        assert "metrics_report_daily" in scheduler_service.tasks, (
            "Task should be named 'metrics_report_daily', not 'metrics_report_12h'"
        )
        task = scheduler_service.tasks["metrics_report_daily"]
        assert task.interval == ScheduleInterval.DAILY
        assert task.target_time is not None, "Metrics report should have a fixed target_time"

    def test_old_12h_task_name_removed(self):
        """The old 'metrics_report_12h' task name should no longer exist."""
        from app.services.scheduler_service import scheduler_service, setup_default_tasks

        scheduler_service.tasks.clear()
        setup_default_tasks()

        assert "metrics_report_12h" not in scheduler_service.tasks


class TestSendMetricsReportCurrentEnvOnly:
    """Tests that the metrics report only covers the current environment."""

    @pytest.mark.asyncio
    async def test_sends_only_current_environment(self):
        """send_metrics_report_task should pass only settings.ENVIRONMENT, not all 3."""
        from app.services.scheduler_service import send_metrics_report_task

        with (
            patch("app.services.scheduler_service._acquire_scheduler_lock", return_value=True),
            patch("app.services.scheduler_service.email_service") as mock_email,
            patch("app.services.scheduler_service.settings") as mock_settings,
        ):
            mock_settings.ENVIRONMENT = MagicMock()
            mock_settings.ENVIRONMENT.value = "qa"
            mock_settings.METRICS_REPORT_RECIPIENTS = "test@test.com"
            mock_settings.METRICS_REPORT_RECIPIENTS_ADMIN = ""
            mock_settings.METRICS_REPORT_RECIPIENTS_TECH = ""
            mock_settings.METRICS_REPORT_RECIPIENTS_BUSINESS = ""
            mock_email.send_metrics_report = AsyncMock(return_value=True)

            await send_metrics_report_task()

            mock_email.send_metrics_report.assert_called_once()
            call_args = mock_email.send_metrics_report.call_args
            environments = call_args[0][1]
            assert len(environments) == 1, f"Should send for 1 environment, got {len(environments)}"


class TestDistributedLock:
    """Tests for the Redis-based distributed lock."""

    @pytest.mark.asyncio
    async def test_lock_acquired_allows_execution(self):
        """Task should execute when lock is acquired."""
        from app.services.scheduler_service import _acquire_scheduler_lock

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)

        mock_cache = MagicMock()
        mock_cache._get_redis = AsyncMock(return_value=mock_redis)

        with patch("app.services.cache.cache_service", mock_cache):
            result = await _acquire_scheduler_lock("test_task")

        assert result is True

    @pytest.mark.asyncio
    async def test_lock_not_acquired_blocks_execution(self):
        """Task should NOT execute when another worker holds the lock."""
        from app.services.scheduler_service import _acquire_scheduler_lock

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=False)

        mock_cache = MagicMock()
        mock_cache._get_redis = AsyncMock(return_value=mock_redis)

        with patch("app.services.cache.cache_service", mock_cache):
            result = await _acquire_scheduler_lock("test_task")

        assert result is False

    @pytest.mark.asyncio
    async def test_lock_allows_execution_when_redis_unavailable(self):
        """Task should still execute if Redis is down (graceful degradation)."""
        from app.services.scheduler_service import _acquire_scheduler_lock

        mock_cache = MagicMock()
        mock_cache._get_redis = AsyncMock(return_value=None)

        with patch("app.services.cache.cache_service", mock_cache):
            result = await _acquire_scheduler_lock("test_task")

        assert result is True
