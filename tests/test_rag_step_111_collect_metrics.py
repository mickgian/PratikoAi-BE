#!/usr/bin/env python3
"""
Tests for RAG STEP 111 — Collect usage metrics

This step collects usage metrics for completed queries and aggregates system-wide metrics.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestrators.metrics import step_111__collect_metrics
from app.services.metrics_service import Environment, MetricResult, MetricsReport, MetricStatus


class TestRAGStep111CollectMetrics:
    """Test suite for RAG STEP 111 - Collect usage metrics"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.metrics_service.MetricsService")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_111_collect_successful_metrics(
        self, mock_usage_tracker, mock_metrics_service_class, mock_logger, mock_rag_log
    ):
        """Test Step 111: Successful metrics collection"""

        # Mock user metrics
        mock_user_metrics = MagicMock()
        mock_user_metrics.total_requests = 25
        mock_user_metrics.total_cost_eur = 0.15
        mock_user_metrics.cache_hit_rate = 0.75
        mock_usage_tracker.get_user_metrics = AsyncMock(return_value=mock_user_metrics)

        # Mock system metrics
        mock_system_metrics = MagicMock()
        mock_system_metrics.total_requests = 1500
        mock_system_metrics.avg_response_time_ms = 320.5
        mock_system_metrics.error_rate = 0.02
        mock_usage_tracker.get_system_metrics = AsyncMock(return_value=mock_system_metrics)

        # Mock metrics report
        mock_metrics_report = MetricsReport(
            environment=Environment.DEVELOPMENT,
            timestamp=datetime.utcnow(),
            technical_metrics=[
                MetricResult(
                    name="API Response Time",
                    value=320.5,
                    target=500.0,
                    status=MetricStatus.PASS,
                    unit="ms",
                    description="API response time",
                    timestamp=datetime.utcnow(),
                    environment=Environment.DEVELOPMENT,
                )
            ],
            business_metrics=[],
            overall_health_score=0.92,
            alerts=[],
            recommendations=[],
        )

        mock_metrics_service = MagicMock()
        mock_metrics_service.generate_metrics_report = AsyncMock(return_value=mock_metrics_report)
        mock_metrics_service_class.return_value = mock_metrics_service

        ctx = {
            "user_id": "user_123",
            "session_id": "session_456",
            "response_time_ms": 320,
            "cache_hit": True,
            "provider": "openai",
            "model": "gpt-4",
            "total_tokens": 150,
            "cost": 0.003,
            "environment": "development",
        }

        # Call the orchestrator function
        result = await step_111__collect_metrics(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["metrics_collected"] is True
        assert result["user_id"] == "user_123"
        assert result["session_id"] == "session_456"
        assert result["environment"] == "development"
        assert result["user_metrics_available"] is True
        assert result["system_metrics_available"] is True
        assert result["metrics_report_available"] is True
        assert result["health_score"] == 0.92
        assert result["alerts_count"] == 0
        assert "timestamp" in result

        # Verify user metrics summary
        assert "user_metrics_summary" in result
        assert result["user_metrics_summary"]["total_requests"] == 25
        assert result["user_metrics_summary"]["total_cost_eur"] == 0.15
        assert result["user_metrics_summary"]["cache_hit_rate"] == 0.75

        # Verify system metrics summary
        assert "system_metrics_summary" in result
        assert result["system_metrics_summary"]["total_requests"] == 1500
        assert result["system_metrics_summary"]["avg_response_time_ms"] == 320.5
        assert result["system_metrics_summary"]["error_rate"] == 0.02

        # Verify services were called correctly
        mock_usage_tracker.get_user_metrics.assert_called_once()
        user_call_args = mock_usage_tracker.get_user_metrics.call_args
        assert user_call_args[1]["user_id"] == "user_123"
        assert isinstance(user_call_args[1]["start_date"], datetime)
        assert isinstance(user_call_args[1]["end_date"], datetime)

        mock_usage_tracker.get_system_metrics.assert_called_once()
        system_call_args = mock_usage_tracker.get_system_metrics.call_args
        assert isinstance(system_call_args[1]["start_date"], datetime)
        assert isinstance(system_call_args[1]["end_date"], datetime)

        mock_metrics_service.generate_metrics_report.assert_called_once_with(Environment.DEVELOPMENT)

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "Metrics collected successfully" in log_call[0][0]
        assert log_call[1]["extra"]["metrics_event"] == "collection_successful"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.metrics_service.MetricsService")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_111_collect_without_user_id(
        self, mock_usage_tracker, mock_metrics_service_class, mock_logger, mock_rag_log
    ):
        """Test Step 111: Metrics collection without user ID"""

        # Mock system metrics only (no user metrics)
        mock_system_metrics = MagicMock()
        mock_system_metrics.total_requests = 500
        mock_system_metrics.avg_response_time_ms = 280.0
        mock_system_metrics.error_rate = 0.01
        mock_usage_tracker.get_system_metrics = AsyncMock(return_value=mock_system_metrics)

        # Mock metrics report
        mock_metrics_report = MagicMock()
        mock_metrics_report.overall_health_score = 0.88
        mock_metrics_report.alerts = ["Warning: High response time"]

        mock_metrics_service = MagicMock()
        mock_metrics_service.generate_metrics_report = AsyncMock(return_value=mock_metrics_report)
        mock_metrics_service_class.return_value = mock_metrics_service

        ctx = {"session_id": "session_789", "response_time_ms": 450, "cache_hit": False, "environment": "production"}

        result = await step_111__collect_metrics(ctx=ctx)

        assert result["metrics_collected"] is True
        assert result["user_id"] is None
        assert result["user_metrics_available"] is False
        assert result["system_metrics_available"] is True
        assert result["metrics_report_available"] is True
        assert result["health_score"] == 0.88
        assert result["alerts_count"] == 1

        # Should not have user metrics summary
        assert "user_metrics_summary" not in result

        # Should have system metrics summary
        assert "system_metrics_summary" in result
        assert result["system_metrics_summary"]["total_requests"] == 500

        # Verify user metrics not called
        mock_usage_tracker.get_user_metrics.assert_not_called()
        # System metrics should still be called
        mock_usage_tracker.get_system_metrics.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.metrics_service.MetricsService")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_111_environment_handling(
        self, mock_usage_tracker, mock_metrics_service_class, mock_logger, mock_rag_log
    ):
        """Test Step 111: Different environment handling"""

        mock_usage_tracker.get_system_metrics = AsyncMock(return_value=MagicMock())
        mock_metrics_service = MagicMock()
        mock_metrics_service.generate_metrics_report = AsyncMock(return_value=MagicMock())
        mock_metrics_service_class.return_value = mock_metrics_service

        # Test production environment
        await step_111__collect_metrics(environment="production")
        mock_metrics_service.generate_metrics_report.assert_called_with(Environment.PRODUCTION)

        # Test staging environment
        await step_111__collect_metrics(environment="staging")
        mock_metrics_service.generate_metrics_report.assert_called_with(Environment.STAGING)

        # Test default to development
        await step_111__collect_metrics(environment="unknown")
        mock_metrics_service.generate_metrics_report.assert_called_with(Environment.DEVELOPMENT)

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.metrics_service.MetricsService")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_111_usage_tracker_error(
        self, mock_usage_tracker, mock_metrics_service_class, mock_logger, mock_rag_log
    ):
        """Test Step 111: Handle usage tracker service error"""

        mock_usage_tracker.get_user_metrics = AsyncMock(side_effect=Exception("Database connection error"))
        mock_usage_tracker.get_system_metrics = AsyncMock(side_effect=Exception("Database connection error"))

        ctx = {"user_id": "user_123", "environment": "development"}

        result = await step_111__collect_metrics(ctx=ctx)

        # Should return error result
        assert result["metrics_collected"] is False
        assert result["error"] == "Database connection error"
        assert result["user_metrics_available"] is False
        assert result["system_metrics_available"] is False

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Metrics collection failed" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.metrics_service.MetricsService")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_111_metrics_service_error(
        self, mock_usage_tracker, mock_metrics_service_class, mock_logger, mock_rag_log
    ):
        """Test Step 111: Handle metrics service error"""

        mock_usage_tracker.get_system_metrics = AsyncMock(return_value=MagicMock())

        mock_metrics_service = MagicMock()
        mock_metrics_service.generate_metrics_report = AsyncMock(side_effect=Exception("Metrics service error"))
        mock_metrics_service_class.return_value = mock_metrics_service

        ctx = {"environment": "development"}

        result = await step_111__collect_metrics(ctx=ctx)

        assert result["metrics_collected"] is False
        assert result["error"] == "Metrics service error"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.metrics_service.MetricsService")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_111_kwargs_parameters(
        self, mock_usage_tracker, mock_metrics_service_class, mock_logger, mock_rag_log
    ):
        """Test Step 111: Parameters passed via kwargs"""

        mock_usage_tracker.get_system_metrics = AsyncMock(return_value=MagicMock())
        mock_metrics_service = MagicMock()
        mock_metrics_service.generate_metrics_report = AsyncMock(return_value=MagicMock())
        mock_metrics_service_class.return_value = mock_metrics_service

        # Call with kwargs instead of ctx
        result = await step_111__collect_metrics(
            user_id="user_456", session_id="session_789", response_time_ms=200, cache_hit=True, environment="staging"
        )

        # Verify kwargs are processed correctly
        assert result["user_id"] == "user_456"
        assert result["session_id"] == "session_789"
        assert result["response_time_ms"] == 200
        assert result["cache_hit"] is True
        assert result["environment"] == "staging"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.metrics_service.MetricsService")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_111_performance_tracking(
        self, mock_usage_tracker, mock_metrics_service_class, mock_logger, mock_rag_log
    ):
        """Test Step 111: Performance tracking with timer"""

        with patch("app.orchestrators.metrics.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_usage_tracker.get_system_metrics = AsyncMock(return_value=MagicMock())
            mock_metrics_service = MagicMock()
            mock_metrics_service.generate_metrics_report = AsyncMock(return_value=MagicMock())
            mock_metrics_service_class.return_value = mock_metrics_service

            # Call the orchestrator function
            await step_111__collect_metrics(ctx={"environment": "development"})

            # Verify timer was used
            mock_timer.assert_called_with(111, "RAG.metrics.collect.usage.metrics", "CollectMetrics", stage="start")

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.metrics_service.MetricsService")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_111_comprehensive_logging_format(
        self, mock_usage_tracker, mock_metrics_service_class, mock_logger, mock_rag_log
    ):
        """Test Step 111: Verify comprehensive logging format"""

        mock_usage_tracker.get_user_metrics = AsyncMock(return_value=MagicMock())
        mock_usage_tracker.get_system_metrics = AsyncMock(return_value=MagicMock())
        mock_metrics_service = MagicMock()
        mock_metrics_service.generate_metrics_report = AsyncMock(return_value=MagicMock())
        mock_metrics_service_class.return_value = mock_metrics_service

        ctx = {"user_id": "user_123", "environment": "development"}

        # Call the orchestrator function
        await step_111__collect_metrics(ctx=ctx)

        # Verify RAG step logging format
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            "step",
            "step_id",
            "node_label",
            "metrics_event",
            "metrics_collected",
            "user_id",
            "environment",
            "user_metrics_available",
            "system_metrics_available",
            "metrics_report_available",
            "processing_stage",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]["step"] == 111
        assert log_call[1]["step_id"] == "RAG.metrics.collect.usage.metrics"
        assert log_call[1]["node_label"] == "CollectMetrics"
        assert log_call[1]["metrics_event"] == "collection_successful"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.metrics_service.MetricsService")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_111_metrics_data_structure(
        self, mock_usage_tracker, mock_metrics_service_class, mock_logger, mock_rag_log
    ):
        """Test Step 111: Verify metrics data structure"""

        mock_usage_tracker.get_user_metrics = AsyncMock(return_value=MagicMock())
        mock_usage_tracker.get_system_metrics = AsyncMock(return_value=MagicMock())
        mock_metrics_service = MagicMock()
        mock_metrics_service.generate_metrics_report = AsyncMock(return_value=MagicMock())
        mock_metrics_service_class.return_value = mock_metrics_service

        ctx = {"user_id": "user_123", "session_id": "session_456", "environment": "development"}

        # Call the orchestrator function
        result = await step_111__collect_metrics(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            "timestamp",
            "metrics_collected",
            "user_id",
            "session_id",
            "response_time_ms",
            "cache_hit",
            "provider",
            "model",
            "total_tokens",
            "cost",
            "environment",
            "user_metrics_available",
            "system_metrics_available",
            "metrics_report_available",
            "error",
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in metrics data: {field}"

        # Verify data types
        assert isinstance(result["timestamp"], str)
        assert isinstance(result["metrics_collected"], bool)
        assert isinstance(result["user_id"], str) or result["user_id"] is None
        assert isinstance(result["session_id"], str) or result["session_id"] is None
        assert isinstance(result["response_time_ms"], int) or result["response_time_ms"] is None
        assert isinstance(result["cache_hit"], bool)
        assert isinstance(result["environment"], str)
        assert isinstance(result["user_metrics_available"], bool)
        assert isinstance(result["system_metrics_available"], bool)
        assert isinstance(result["metrics_report_available"], bool)

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.metrics_service.MetricsService")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_111_partial_failures(
        self, mock_usage_tracker, mock_metrics_service_class, mock_logger, mock_rag_log
    ):
        """Test Step 111: Handle partial service failures gracefully"""

        # User metrics succeeds, system metrics fails
        mock_user_metrics = MagicMock()
        mock_usage_tracker.get_user_metrics = AsyncMock(return_value=mock_user_metrics)
        mock_usage_tracker.get_system_metrics = AsyncMock(side_effect=Exception("System metrics error"))

        ctx = {"user_id": "user_123", "environment": "development"}

        result = await step_111__collect_metrics(ctx=ctx)

        # Should fail overall due to exception
        assert result["metrics_collected"] is False
        assert result["error"] == "System metrics error"
