"""
Tests for the Success Metrics Monitoring Service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from app.services.metrics_service import (
    MetricsService,
    MetricResult,
    MetricsReport,
    MetricStatus,
    Environment
)


class TestMetricsService:
    """Test cases for MetricsService."""

    @pytest.fixture
    def metrics_service(self):
        """Create a MetricsService instance for testing."""
        return MetricsService()

    @pytest.mark.asyncio
    async def test_collect_technical_metrics_success(self, metrics_service):
        """Test successful collection of technical metrics."""
        with patch.object(metrics_service, '_get_api_response_time_p95', return_value=450.0), \
             patch.object(metrics_service, '_get_cache_hit_rate', return_value=85.0), \
             patch.object(metrics_service, '_get_test_coverage', return_value=88.0), \
             patch.object(metrics_service, '_get_critical_vulnerabilities', return_value=0.0):
            
            metrics = await metrics_service.collect_technical_metrics(Environment.DEVELOPMENT)
            
            assert len(metrics) == 4
            
            # Check API response time metric
            response_time_metric = next(m for m in metrics if "Response Time" in m.name)
            assert response_time_metric.value == 450.0
            assert response_time_metric.target == 500.0
            assert response_time_metric.status == MetricStatus.PASS
            assert response_time_metric.unit == "ms"
            
            # Check cache hit rate metric
            cache_metric = next(m for m in metrics if "Cache Hit Rate" in m.name)
            assert cache_metric.value == 85.0
            assert cache_metric.target == 80.0
            assert cache_metric.status == MetricStatus.PASS
            assert cache_metric.unit == "%"
            
            # Check test coverage metric
            coverage_metric = next(m for m in metrics if "Test Coverage" in m.name)
            assert coverage_metric.value == 88.0
            assert coverage_metric.target == 80.0
            assert coverage_metric.status == MetricStatus.PASS
            assert coverage_metric.unit == "%"
            
            # Check security vulnerabilities metric
            security_metric = next(m for m in metrics if "Security Vulnerabilities" in m.name)
            assert security_metric.value == 0.0
            assert security_metric.target == 0.0
            assert security_metric.status == MetricStatus.PASS
            assert security_metric.unit == "count"

    @pytest.mark.asyncio
    async def test_collect_technical_metrics_with_failures(self, metrics_service):
        """Test technical metrics collection with some metrics failing targets."""
        with patch.object(metrics_service, '_get_api_response_time_p95', return_value=750.0), \
             patch.object(metrics_service, '_get_cache_hit_rate', return_value=65.0), \
             patch.object(metrics_service, '_get_test_coverage', return_value=88.0), \
             patch.object(metrics_service, '_get_critical_vulnerabilities', return_value=2.0):
            
            metrics = await metrics_service.collect_technical_metrics(Environment.PRODUCTION)
            
            # Check failing metrics
            response_time_metric = next(m for m in metrics if "Response Time" in m.name)
            assert response_time_metric.status == MetricStatus.FAIL
            
            cache_metric = next(m for m in metrics if "Cache Hit Rate" in m.name)
            assert cache_metric.status == MetricStatus.WARNING
            
            security_metric = next(m for m in metrics if "Security Vulnerabilities" in m.name)
            assert security_metric.status == MetricStatus.FAIL

    @pytest.mark.asyncio
    async def test_collect_business_metrics_success(self, metrics_service):
        """Test successful collection of business metrics."""
        with patch.object(metrics_service, '_get_average_cost_per_user', return_value=1.8), \
             patch.object(metrics_service, '_get_system_uptime', return_value=99.7), \
             patch.object(metrics_service, '_get_user_satisfaction', return_value=4.6), \
             patch.object(metrics_service, '_get_gdpr_compliance_score', return_value=98.0):
            
            metrics = await metrics_service.collect_business_metrics(Environment.PRODUCTION)
            
            assert len(metrics) == 4
            
            # Check cost metric
            cost_metric = next(m for m in metrics if "API Cost" in m.name)
            assert cost_metric.value == 1.8
            assert cost_metric.target == 2.0
            assert cost_metric.status == MetricStatus.PASS
            assert cost_metric.unit == "EUR/month"
            
            # Check uptime metric
            uptime_metric = next(m for m in metrics if "System Uptime" in m.name)
            assert uptime_metric.value == 99.7
            assert uptime_metric.target == 99.5
            assert uptime_metric.status == MetricStatus.PASS
            assert uptime_metric.unit == "%"
            
            # Check satisfaction metric
            satisfaction_metric = next(m for m in metrics if "User Satisfaction" in m.name)
            assert satisfaction_metric.value == 4.6
            assert satisfaction_metric.target == 4.5
            assert satisfaction_metric.status == MetricStatus.PASS
            assert satisfaction_metric.unit == "score"
            
            # Check GDPR compliance metric
            gdpr_metric = next(m for m in metrics if "GDPR Compliance" in m.name)
            assert gdpr_metric.value == 98.0
            assert gdpr_metric.target == 100.0
            assert gdpr_metric.status == MetricStatus.PASS
            assert gdpr_metric.unit == "%"

    @pytest.mark.asyncio
    async def test_generate_metrics_report(self, metrics_service):
        """Test complete metrics report generation."""
        # Mock technical metrics
        technical_metrics = [
            MetricResult(
                name="API Response Time",
                value=400.0,
                target=500.0,
                status=MetricStatus.PASS,
                unit="ms",
                description="Test metric",
                timestamp=datetime.utcnow(),
                environment=Environment.DEVELOPMENT
            ),
            MetricResult(
                name="Cache Hit Rate",
                value=75.0,
                target=80.0,
                status=MetricStatus.WARNING,
                unit="%",
                description="Test metric",
                timestamp=datetime.utcnow(),
                environment=Environment.DEVELOPMENT
            )
        ]
        
        # Mock business metrics
        business_metrics = [
            MetricResult(
                name="API Cost",
                value=1.5,
                target=2.0,
                status=MetricStatus.PASS,
                unit="EUR/month",
                description="Test metric",
                timestamp=datetime.utcnow(),
                environment=Environment.DEVELOPMENT
            )
        ]
        
        with patch.object(metrics_service, 'collect_technical_metrics', return_value=technical_metrics), \
             patch.object(metrics_service, 'collect_business_metrics', return_value=business_metrics):
            
            report = await metrics_service.generate_metrics_report(Environment.DEVELOPMENT)
            
            assert isinstance(report, MetricsReport)
            assert report.environment == Environment.DEVELOPMENT
            assert len(report.technical_metrics) == 2
            assert len(report.business_metrics) == 1
            assert report.overall_health_score == (2/3) * 100  # 2 passed out of 3 total
            assert len(report.alerts) == 1  # One warning alert
            assert "Cache Hit Rate" in report.alerts[0]

    @pytest.mark.asyncio
    async def test_get_api_response_time_p95(self, metrics_service):
        """Test P95 response time calculation."""
        mock_summary = {
            "endpoints": {
                "/api/test1": {"response_times": [100, 200, 300, 400, 500]},
                "/api/test2": {"response_times": [150, 250, 350, 450, 550]}
            }
        }
        
        with patch('app.core.performance.performance_monitor.performance_monitor.get_performance_summary', 
                   return_value=mock_summary):
            
            p95_time = await metrics_service._get_api_response_time_p95()
            
            # P95 of [100, 150, 200, 250, 300, 350, 400, 450, 500, 550] should be 550
            assert p95_time == 550.0

    @pytest.mark.asyncio
    async def test_get_cache_hit_rate(self, metrics_service):
        """Test cache hit rate calculation."""
        mock_stats = {
            "cache_hits": 80,
            "cache_misses": 20
        }
        
        with patch('app.services.cache.cache_service.get_cache_statistics', 
                   return_value=mock_stats):
            
            hit_rate = await metrics_service._get_cache_hit_rate()
            
            assert hit_rate == 80.0  # 80 hits out of 100 total

    @pytest.mark.asyncio
    async def test_get_gdpr_compliance_score(self, metrics_service):
        """Test GDPR compliance score calculation."""
        compliance_score = await metrics_service._get_gdpr_compliance_score()
        
        # Should return 100% since all checks are mocked as True
        assert compliance_score == 100.0

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, metrics_service):
        """Test recommendation generation based on failed metrics."""
        failed_metrics = [
            MetricResult(
                name="API Response Time",
                value=600.0,
                target=500.0,
                status=MetricStatus.FAIL,
                unit="ms",
                description="Test metric",
                timestamp=datetime.utcnow(),
                environment=Environment.DEVELOPMENT
            ),
            MetricResult(
                name="Cache Hit Rate",
                value=65.0,
                target=80.0,
                status=MetricStatus.WARNING,
                unit="%",
                description="Test metric",
                timestamp=datetime.utcnow(),
                environment=Environment.DEVELOPMENT
            )
        ]
        
        recommendations = await metrics_service._generate_recommendations(failed_metrics)
        
        assert len(recommendations) >= 2
        assert any("response caching" in rec.lower() for rec in recommendations)
        assert any("cache parameters" in rec.lower() for rec in recommendations)

    @pytest.mark.asyncio
    async def test_metrics_collection_error_handling(self, metrics_service):
        """Test error handling when metric collection fails."""
        with patch.object(metrics_service, '_get_api_response_time_p95', side_effect=Exception("Test error")):
            
            metrics = await metrics_service.collect_technical_metrics(Environment.DEVELOPMENT)
            
            response_time_metric = next(m for m in metrics if "Response Time" in m.name)
            assert response_time_metric.status == MetricStatus.UNKNOWN
            assert response_time_metric.value == 0.0

    def test_metric_result_creation(self):
        """Test MetricResult creation and properties."""
        timestamp = datetime.utcnow()
        
        metric = MetricResult(
            name="Test Metric",
            value=75.5,
            target=80.0,
            status=MetricStatus.WARNING,
            unit="%",
            description="Test description",
            timestamp=timestamp,
            environment=Environment.STAGING
        )
        
        assert metric.name == "Test Metric"
        assert metric.value == 75.5
        assert metric.target == 80.0
        assert metric.status == MetricStatus.WARNING
        assert metric.unit == "%"
        assert metric.description == "Test description"
        assert metric.timestamp == timestamp
        assert metric.environment == Environment.STAGING