#!/usr/bin/env python3
"""
Tests for RAG STEP 74 — UsageTracker.track Track API usage

This step tracks API usage using the existing UsageTracker infrastructure.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm.base import LLMResponse
from app.orchestrators.metrics import step_74__track_usage


class TestRAGStep74TrackUsage:
    """Test suite for RAG STEP 74 - Track API usage"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_74_track_successful_llm_usage(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 74: Successful LLM usage tracking"""

        # Mock LLM response
        llm_response = LLMResponse(
            content="Test response content", model="gpt-4", provider="openai", tokens_used=150, cost_estimate=0.003
        )

        # Mock usage event
        mock_usage_event = MagicMock()
        mock_usage_event.id = "usage_123"
        mock_usage_event.total_cost = 0.003
        mock_usage_tracker.track_llm_usage = AsyncMock(return_value=mock_usage_event)

        ctx = {
            "user_id": "user_123",
            "session_id": "session_456",
            "provider": "openai",
            "model": "gpt-4",
            "llm_response": llm_response,
            "response_time_ms": 1500,
            "cache_hit": False,
            "pii_detected": False,
        }

        # Call the orchestrator function
        result = await step_74__track_usage(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["usage_tracked"] is True
        assert result["user_id"] == "user_123"
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4"
        assert result["total_tokens"] == 150
        assert result["cost"] == 0.003
        assert result["cache_hit"] is False
        assert result["response_time_ms"] == 1500
        assert "timestamp" in result

        # Verify usage tracker was called correctly
        mock_usage_tracker.track_llm_usage.assert_called_once_with(
            user_id="user_123",
            session_id="session_456",
            provider="openai",
            model="gpt-4",
            llm_response=llm_response,
            response_time_ms=1500,
            cache_hit=False,
            pii_detected=False,
            pii_types=None,
            ip_address=None,
            user_agent=None,
        )

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "API usage tracked successfully" in log_call[0][0]
        assert log_call[1]["extra"]["usage_event"] == "api_usage_tracked"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_74_track_with_cache_hit(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 74: Track usage with cache hit"""

        llm_response = LLMResponse(
            content="Cached response",
            model="gpt-3.5-turbo",
            provider="openai",
            tokens_used=75,
            cost_estimate=0.0001,  # Much lower cost for cached response
        )

        mock_usage_event = MagicMock()
        mock_usage_event.total_cost = 0.0001
        mock_usage_tracker.track_llm_usage = AsyncMock(return_value=mock_usage_event)

        ctx = {
            "user_id": "user_456",
            "session_id": "session_789",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "llm_response": llm_response,
            "response_time_ms": 150,  # Fast cache response
            "cache_hit": True,
            "pii_detected": False,
        }

        result = await step_74__track_usage(ctx=ctx)

        assert result["usage_tracked"] is True
        assert result["cache_hit"] is True
        assert result["response_time_ms"] == 150
        assert result["cost"] == 0.0001

        # Verify cache hit tracking
        mock_usage_tracker.track_llm_usage.assert_called_once()
        call_args = mock_usage_tracker.track_llm_usage.call_args
        assert call_args[1]["cache_hit"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_74_track_with_pii_detection(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 74: Track usage with PII detection"""

        llm_response = LLMResponse(
            content="Response with anonymized data",
            model="gpt-4",
            provider="anthropic",
            tokens_used=200,
            cost_estimate=0.004,
        )

        mock_usage_event = MagicMock()
        mock_usage_tracker.track_llm_usage = AsyncMock(return_value=mock_usage_event)

        ctx = {
            "user_id": "user_789",
            "session_id": "session_101",
            "provider": "anthropic",
            "model": "claude-3",
            "llm_response": llm_response,
            "response_time_ms": 2000,
            "cache_hit": False,
            "pii_detected": True,
            "pii_types": ["email", "phone"],
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
        }

        result = await step_74__track_usage(ctx=ctx)

        assert result["usage_tracked"] is True
        assert result["pii_detected"] is True

        # Verify PII tracking
        call_args = mock_usage_tracker.track_llm_usage.call_args
        assert call_args[1]["pii_detected"] is True
        assert call_args[1]["pii_types"] == ["email", "phone"]
        assert call_args[1]["ip_address"] == "192.168.1.1"
        assert call_args[1]["user_agent"] == "Mozilla/5.0"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_74_missing_required_data(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 74: Handle missing required tracking data"""

        ctx = {"user_id": "user_123"}  # Missing other required fields

        result = await step_74__track_usage(ctx=ctx)

        # Should return error result
        assert result["usage_tracked"] is False
        assert result["error"] == "Missing required usage tracking data"

        # Should not call tracking
        mock_usage_tracker.track_llm_usage.assert_not_called()

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "API usage tracking failed" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_74_usage_tracker_error(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 74: Handle usage tracker service error"""

        mock_usage_tracker.track_llm_usage = AsyncMock(side_effect=Exception("Usage tracking service error"))

        llm_response = LLMResponse(
            content="Test response", model="gpt-4", provider="openai", tokens_used=100, cost_estimate=0.002
        )

        ctx = {
            "user_id": "user_123",
            "session_id": "session_456",
            "provider": "openai",
            "model": "gpt-4",
            "llm_response": llm_response,
            "response_time_ms": 1500,
        }

        result = await step_74__track_usage(ctx=ctx)

        # Should return error result
        assert result["usage_tracked"] is False
        assert result["error"] == "Usage tracking service error"

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "API usage tracking failed" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_74_high_cost_tracking(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 74: Track high-cost API usage with warning"""

        llm_response = LLMResponse(
            content="Expensive response",
            model="gpt-4",
            provider="openai",
            tokens_used=3500,
            cost_estimate=0.07,  # High cost
        )

        mock_usage_event = MagicMock()
        mock_usage_event.total_cost = 0.07
        mock_usage_tracker.track_llm_usage = AsyncMock(return_value=mock_usage_event)

        ctx = {
            "user_id": "user_123",
            "session_id": "session_456",
            "provider": "openai",
            "model": "gpt-4",
            "llm_response": llm_response,
            "response_time_ms": 5000,
            "cache_hit": False,
        }

        result = await step_74__track_usage(ctx=ctx)

        assert result["usage_tracked"] is True
        assert result["cost"] == 0.07

        # Should log warning for high cost
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert "High-cost API usage tracked" in warning_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_74_kwargs_parameters(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 74: Parameters passed via kwargs"""

        llm_response = LLMResponse(
            content="Test response", model="gpt-4", provider="openai", tokens_used=100, cost_estimate=0.002
        )

        mock_usage_event = MagicMock()
        mock_usage_tracker.track_llm_usage = AsyncMock(return_value=mock_usage_event)

        # Call with kwargs instead of ctx
        result = await step_74__track_usage(
            user_id="user_123",
            session_id="session_456",
            provider="openai",
            model="gpt-4",
            llm_response=llm_response,
            response_time_ms=1500,
        )

        # Verify kwargs are processed correctly
        assert result["usage_tracked"] is True
        assert result["user_id"] == "user_123"
        assert result["provider"] == "openai"

        mock_usage_tracker.track_llm_usage.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_74_performance_tracking(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 74: Performance tracking with timer"""

        with patch("app.orchestrators.metrics.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            llm_response = LLMResponse(
                content="Test", model="gpt-4", provider="openai", tokens_used=10, cost_estimate=0.001
            )

            # Call the orchestrator function
            await step_74__track_usage(
                ctx={
                    "user_id": "user_123",
                    "session_id": "session_456",
                    "provider": "openai",
                    "model": "gpt-4",
                    "llm_response": llm_response,
                    "response_time_ms": 1000,
                }
            )

            # Verify timer was used
            mock_timer.assert_called_with(
                74, "RAG.metrics.usagetracker.track.track.api.usage", "TrackUsage", stage="start"
            )

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_74_comprehensive_logging_format(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 74: Verify comprehensive logging format"""

        llm_response = LLMResponse(
            content="Test response", model="gpt-4", provider="openai", tokens_used=100, cost_estimate=0.002
        )

        mock_usage_event = MagicMock()
        mock_usage_event.total_cost = 0.002
        mock_usage_tracker.track_llm_usage = AsyncMock(return_value=mock_usage_event)

        ctx = {
            "user_id": "user_123",
            "session_id": "session_456",
            "provider": "openai",
            "model": "gpt-4",
            "llm_response": llm_response,
            "response_time_ms": 1500,
        }

        # Call the orchestrator function
        await step_74__track_usage(ctx=ctx)

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
            "usage_event",
            "usage_tracked",
            "user_id",
            "provider",
            "model",
            "total_tokens",
            "cost",
            "cache_hit",
            "processing_stage",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]["step"] == 74
        assert log_call[1]["step_id"] == "RAG.metrics.usagetracker.track.track.api.usage"
        assert log_call[1]["node_label"] == "TrackUsage"
        assert log_call[1]["usage_event"] == "api_usage_tracked"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_74_usage_data_structure(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 74: Verify usage data structure"""

        llm_response = LLMResponse(
            content="Test response", model="gpt-4", provider="openai", tokens_used=100, cost_estimate=0.002
        )

        mock_usage_event = MagicMock()
        mock_usage_event.total_cost = 0.002
        mock_usage_tracker.track_llm_usage = AsyncMock(return_value=mock_usage_event)

        ctx = {
            "user_id": "user_123",
            "session_id": "session_456",
            "provider": "openai",
            "model": "gpt-4",
            "llm_response": llm_response,
            "response_time_ms": 1500,
        }

        # Call the orchestrator function
        result = await step_74__track_usage(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            "timestamp",
            "usage_tracked",
            "user_id",
            "session_id",
            "provider",
            "model",
            "total_tokens",
            "cost",
            "cache_hit",
            "pii_detected",
            "response_time_ms",
            "error",
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in usage data: {field}"

        # Verify data types
        assert isinstance(result["timestamp"], str)
        assert isinstance(result["usage_tracked"], bool)
        assert isinstance(result["user_id"], str) or result["user_id"] is None
        assert isinstance(result["provider"], str) or result["provider"] is None
        assert isinstance(result["model"], str) or result["model"] is None
        assert isinstance(result["total_tokens"], int)
        assert isinstance(result["cost"], float)
        assert isinstance(result["cache_hit"], bool)
        assert isinstance(result["pii_detected"], bool)
        assert isinstance(result["response_time_ms"], int)

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
