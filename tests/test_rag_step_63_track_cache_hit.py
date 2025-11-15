#!/usr/bin/env python3
"""
Tests for RAG STEP 63 — UsageTracker.track Track cache hit

This step tracks cache hit metrics using the UsageTracker with zero cost and cache_hit=True.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm.base import LLMResponse
from app.orchestrators.cache import step_63__track_cache_hit


class TestRAGStep63TrackCacheHit:
    """Test suite for RAG STEP 63 - Track cache hit"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_63_track_cache_hit_success(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 63: Successful cache hit tracking"""

        # Mock cached response
        cached_response = LLMResponse(
            content="VAT rate for professional services is 22%", model="gpt-4", tokens_used=70, provider="openai"
        )

        # Mock usage tracker
        mock_usage_tracker.track_llm_usage = AsyncMock()

        ctx = {
            "cached_response": cached_response,
            "model": "gpt-4",
            "provider": "openai",
            "user_id": "user_123",
            "session_id": "session_456",
            "query_hash": "hash123",
        }

        # Call the orchestrator function
        result = await step_63__track_cache_hit(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["tracking_successful"] is True
        assert result["cache_hit_tracked"] is True
        assert {"tokens_used": result["cached_response"].tokens_used} == {"input_tokens": 50, "output_tokens": 20}
        assert result["model"] == "gpt-4"
        assert result["provider"] == "openai"
        assert result["cost"] == 0.0  # Cache hits are free
        assert "timestamp" in result

        # Verify usage tracker was called correctly
        mock_usage_tracker.track_llm_usage.assert_called_once()
        call_args = mock_usage_tracker.track_llm_usage.call_args
        assert call_args[1]["model"] == "gpt-4"
        assert call_args[1]["provider"] == "openai"
        assert call_args[1]["cache_hit"] is True
        assert call_args[1]["cost"] == 0.0
        assert call_args[1]["user_id"] == "user_123"

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "Cache hit tracked" in log_call[0][0]
        assert log_call[1]["extra"]["cache_event"] == "hit_tracked"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_63_missing_cached_response(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 63: Handle missing cached response"""

        mock_usage_tracker.track_llm_usage = AsyncMock()

        ctx = {
            "model": "gpt-4",
            "user_id": "user_123",
            # Missing cached_response
        }

        result = await step_63__track_cache_hit(ctx=ctx)

        # Should return error result
        assert result["tracking_successful"] is False
        assert result["error"] == "Missing required parameter: cached_response"

        # Should not call usage tracker
        mock_usage_tracker.track_llm_usage.assert_not_called()

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Cache hit tracking failed" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_63_tracking_error(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 63: Handle usage tracking service error"""

        cached_response = LLMResponse(content="Test response", model="gpt-4")

        mock_usage_tracker.track_llm_usage = AsyncMock(side_effect=Exception("Tracking service failed"))

        ctx = {"cached_response": cached_response, "model": "gpt-4", "user_id": "user_123"}

        result = await step_63__track_cache_hit(ctx=ctx)

        # Should return error result
        assert result["tracking_successful"] is False
        assert result["error"] == "Tracking service failed"

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_63_default_values(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 63: Default values for missing optional parameters"""

        cached_response = LLMResponse(content="Test response", model="gpt-3.5-turbo")

        mock_usage_tracker.track_llm_usage = AsyncMock()

        ctx = {
            "cached_response": cached_response
            # Missing optional parameters
        }

        result = await step_63__track_cache_hit(ctx=ctx)

        assert result["tracking_successful"] is True
        assert result["model"] == "gpt-3.5-turbo"
        assert result["provider"] is None
        assert result["user_id"] is None
        assert result["session_id"] is None

        # Verify defaults were passed to tracker
        call_args = mock_usage_tracker.track_llm_usage.call_args
        assert call_args[1]["provider"] is None
        assert call_args[1]["user_id"] is None
        assert call_args[1]["cache_hit"] is True
        assert call_args[1]["cost"] == 0.0

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_63_kwargs_parameters(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 63: Parameters passed via kwargs"""

        cached_response = LLMResponse(
            content="Kwargs cache hit", model="claude-3", tokens_used=70, provider="anthropic"
        )

        mock_usage_tracker.track_llm_usage = AsyncMock()

        # Call with kwargs instead of ctx
        result = await step_63__track_cache_hit(
            cached_response=cached_response,
            model="claude-3",
            provider="anthropic",
            user_id="user_456",
            session_id="session_789",
        )

        # Verify kwargs are processed correctly
        assert result["tracking_successful"] is True
        assert result["model"] == "claude-3"
        assert result["provider"] == "anthropic"
        assert result["user_id"] == "user_456"
        assert result["session_id"] == "session_789"

        # Verify correct tracking call
        call_args = mock_usage_tracker.track_llm_usage.call_args
        assert call_args[1]["model"] == "claude-3"
        assert call_args[1]["provider"] == "anthropic"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker", None)
    async def test_step_63_no_usage_tracker(self, mock_logger, mock_rag_log):
        """Test Step 63: Handle missing usage tracker"""

        cached_response = LLMResponse(content="Test response", model="gpt-4")

        ctx = {"cached_response": cached_response, "model": "gpt-4"}

        result = await step_63__track_cache_hit(ctx=ctx)

        assert result["tracking_successful"] is False
        assert result["error"] == "Usage tracker not available"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_63_token_usage_calculation(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 63: Token usage calculation and cost tracking"""

        cached_response = LLMResponse(
            content="Complex response with detailed token usage",
            model="gpt-4-turbo",
            tokens_used=70,
            provider="openai",
        )

        mock_usage_tracker.track_llm_usage = AsyncMock()

        ctx = {"cached_response": cached_response, "model": "gpt-4-turbo", "provider": "openai", "user_id": "user_123"}

        result = await step_63__track_cache_hit(ctx=ctx)

        assert result["tracking_successful"] is True
        assert {"tokens_used": result["cached_response"].tokens_used}["input_tokens"] == 150
        assert {"tokens_used": result["cached_response"].tokens_used}["output_tokens"] == 75
        assert {"tokens_used": result["cached_response"].tokens_used}["total_tokens"] == 225
        assert result["cost"] == 0.0  # Always zero for cache hits

        # Verify tracking includes full token details
        call_args = mock_usage_tracker.track_llm_usage.call_args
        assert call_args[1]["token_usage"]["total_tokens"] == 225
        assert call_args[1]["cost"] == 0.0

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_63_performance_tracking(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 63: Performance tracking with timer"""

        with patch("app.orchestrators.cache.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            cached_response = LLMResponse(content="Test", model="gpt-4")
            mock_usage_tracker.track_llm_usage = AsyncMock()

            # Call the orchestrator function
            await step_63__track_cache_hit(ctx={"cached_response": cached_response, "model": "gpt-4"})

            # Verify timer was used
            mock_timer.assert_called_with(
                63, "RAG.cache.usagetracker.track.track.cache.hit", "TrackCacheHit", stage="start"
            )

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_step_63_comprehensive_logging_format(self, mock_usage_tracker, mock_logger, mock_rag_log):
        """Test Step 63: Verify comprehensive logging format"""

        cached_response = LLMResponse(content="Test", model="gpt-4")
        mock_usage_tracker.track_llm_usage = AsyncMock()

        ctx = {"cached_response": cached_response, "model": "gpt-4", "user_id": "user_123"}

        # Call the orchestrator function
        await step_63__track_cache_hit(ctx=ctx)

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
            "cache_event",
            "tracking_successful",
            "cache_hit_tracked",
            "model",
            "cost",
            "processing_stage",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]["step"] == 63
        assert log_call[1]["step_id"] == "RAG.cache.usagetracker.track.track.cache.hit"
        assert log_call[1]["node_label"] == "TrackCacheHit"
        assert log_call[1]["cache_event"] == "hit_tracked"
        assert log_call[1]["cost"] == 0.0
