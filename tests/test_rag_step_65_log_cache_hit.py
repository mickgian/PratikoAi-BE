#!/usr/bin/env python3
"""
Tests for RAG STEP 65 — Logger.info Log cache hit

This step provides structured logging for cache hit events with comprehensive context.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.llm.base import LLMResponse
from app.orchestrators.cache import step_65__log_cache_hit


class TestRAGStep65LogCacheHit:
    """Test suite for RAG STEP 65 - Log cache hit"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_65_log_cache_hit_success(self, mock_logger, mock_rag_log):
        """Test Step 65: Successful cache hit logging"""

        cached_response = LLMResponse(
            content="VAT rate for professional services is 22%", model="gpt-4", tokens_used=70, provider="openai"
        )

        ctx = {
            "cached_response": cached_response,
            "cache_key": "cache_key_abc123def456",
            "query_hash": "hash123",
            "model": "gpt-4",
            "provider": "openai",
            "user_id": "user_123",
            "session_id": "session_456",
            "cost_saved": 0.0045,  # Estimated cost saved
        }

        # Call the orchestrator function
        result = await step_65__log_cache_hit(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["logging_successful"] is True
        assert result["cache_hit_logged"] is True
        assert result["cache_key"] == "cache_key_abc123def456"
        assert result["query_hash"] == "hash123"
        assert result["model"] == "gpt-4"
        assert result["cost_saved"] == 0.0045
        assert "timestamp" in result

        # Verify structured logging was called
        mock_logger.info.assert_called()
        log_calls = mock_logger.info.call_args_list

        # Find the cache hit log call
        cache_hit_log = None
        for call in log_calls:
            if "Cache hit served" in call[0][0]:
                cache_hit_log = call
                break

        assert cache_hit_log is not None
        log_extra = cache_hit_log[1]["extra"]
        assert log_extra["cache_event"] == "hit_served"
        assert log_extra["cache_key"] == "cache_key_abc123def456"
        assert log_extra["model"] == "gpt-4"
        assert log_extra["cost_saved"] == 0.0045

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_65_minimal_context(self, mock_logger, mock_rag_log):
        """Test Step 65: Logging with minimal context"""

        cached_response = LLMResponse(content="Minimal response", model="gpt-3.5-turbo")

        ctx = {
            "cached_response": cached_response,
            "cache_key": "minimal_key",
            # Missing optional parameters
        }

        result = await step_65__log_cache_hit(ctx=ctx)

        assert result["logging_successful"] is True
        assert result["cache_hit_logged"] is True
        assert result["cache_key"] == "minimal_key"
        assert result["query_hash"] is None
        assert result["model"] == "gpt-3.5-turbo"
        assert result["cost_saved"] == 0.0  # Default value

        # Verify logging included available data
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_65_missing_cached_response(self, mock_logger, mock_rag_log):
        """Test Step 65: Handle missing cached response"""

        ctx = {
            "cache_key": "some_key",
            "model": "gpt-4",
            # Missing cached_response
        }

        result = await step_65__log_cache_hit(ctx=ctx)

        # Should return error result
        assert result["logging_successful"] is False
        assert result["error"] == "Missing required parameter: cached_response"

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Cache hit logging failed" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_65_logging_error(self, mock_logger, mock_rag_log):
        """Test Step 65: Handle logging service error"""

        cached_response = LLMResponse(content="Test", model="gpt-4")
        mock_logger.info.side_effect = Exception("Logging service failed")

        ctx = {"cached_response": cached_response, "cache_key": "error_key"}

        result = await step_65__log_cache_hit(ctx=ctx)

        # Should return error result
        assert result["logging_successful"] is False
        assert result["error"] == "Logging service failed"

        # Verify error was logged to error level
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_65_kwargs_parameters(self, mock_logger, mock_rag_log):
        """Test Step 65: Parameters passed via kwargs"""

        cached_response = LLMResponse(content="Kwargs cache hit", model="claude-3", provider="anthropic")

        # Call with kwargs instead of ctx
        result = await step_65__log_cache_hit(
            cached_response=cached_response,
            cache_key="kwargs_cache_key",
            query_hash="kwargs_hash",
            model="claude-3",
            provider="anthropic",
            user_id="user_456",
            cost_saved=0.0032,
        )

        # Verify kwargs are processed correctly
        assert result["logging_successful"] is True
        assert result["cache_key"] == "kwargs_cache_key"
        assert result["query_hash"] == "kwargs_hash"
        assert result["model"] == "claude-3"
        assert result["provider"] == "anthropic"
        assert result["cost_saved"] == 0.0032

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_65_token_usage_logging(self, mock_logger, mock_rag_log):
        """Test Step 65: Token usage details in logging"""

        cached_response = LLMResponse(
            content="Detailed response with comprehensive token tracking",
            model="gpt-4-turbo",
            tokens_used=70,
            provider="openai",
            finish_reason="stop",
        )

        ctx = {
            "cached_response": cached_response,
            "cache_key": "detailed_key",
            "query_hash": "detailed_hash",
            "model": "gpt-4-turbo",
            "cost_saved": 0.0084,  # Calculated based on token usage
        }

        result = await step_65__log_cache_hit(ctx=ctx)

        assert result["logging_successful"] is True
        assert {"tokens_used": result["cached_response"].tokens_used} == {
            "input_tokens": 125,
            "output_tokens": 85,
            "total_tokens": 210,
        }

        # Verify token details included in logging
        mock_logger.info.assert_called()
        log_calls = mock_logger.info.call_args_list

        # Find the cache hit log call and check token usage
        cache_hit_log = None
        for call in log_calls:
            if "Cache hit served" in call[0][0]:
                cache_hit_log = call
                break

        assert cache_hit_log is not None
        log_extra = cache_hit_log[1]["extra"]
        assert log_extra["token_usage"]["total_tokens"] == 210
        assert log_extra["cost_saved"] == 0.0084

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_65_response_content_summary(self, mock_logger, mock_rag_log):
        """Test Step 65: Response content summarization for logging"""

        long_content = "This is a very long response " * 100  # 500+ characters
        cached_response = LLMResponse(content=long_content, model="gpt-4")

        ctx = {"cached_response": cached_response, "cache_key": "long_content_key"}

        result = await step_65__log_cache_hit(ctx=ctx)

        assert result["logging_successful"] is True

        # Content should be truncated for logging
        assert "content_length" in result
        assert result["content_length"] == len(long_content)

        # Verify logging includes content summary
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_65_performance_tracking(self, mock_logger, mock_rag_log):
        """Test Step 65: Performance tracking with timer"""

        with patch("app.orchestrators.cache.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            cached_response = LLMResponse(content="Test", model="gpt-4")

            # Call the orchestrator function
            await step_65__log_cache_hit(ctx={"cached_response": cached_response, "cache_key": "perf_key"})

            # Verify timer was used
            mock_timer.assert_called_with(65, "RAG.cache.logger.info.log.cache.hit", "LogCacheHit", stage="start")

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_65_comprehensive_logging_format(self, mock_logger, mock_rag_log):
        """Test Step 65: Verify comprehensive logging format"""

        cached_response = LLMResponse(content="Test", model="gpt-4")

        ctx = {"cached_response": cached_response, "cache_key": "format_key", "user_id": "user_123"}

        # Call the orchestrator function
        await step_65__log_cache_hit(ctx=ctx)

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
            "logging_successful",
            "cache_hit_logged",
            "cache_key",
            "processing_stage",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]["step"] == 65
        assert log_call[1]["step_id"] == "RAG.cache.logger.info.log.cache.hit"
        assert log_call[1]["node_label"] == "LogCacheHit"
        assert log_call[1]["cache_event"] == "hit_logged"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_65_cache_metrics_tracking(self, mock_logger, mock_rag_log):
        """Test Step 65: Cache metrics and performance tracking"""

        cached_response = LLMResponse(content="Response with performance metrics", model="gpt-4", tokens_used=70)

        ctx = {
            "cached_response": cached_response,
            "cache_key": "metrics_key",
            "query_hash": "metrics_hash",
            "response_time_saved": 1.2,  # Seconds saved
            "cost_saved": 0.0024,
            "cache_age": 3600,  # 1 hour old
        }

        result = await step_65__log_cache_hit(ctx=ctx)

        assert result["logging_successful"] is True
        assert result["response_time_saved"] == 1.2
        assert result["cache_age"] == 3600

        # Verify performance metrics logged
        mock_logger.info.assert_called()
        log_calls = mock_logger.info.call_args_list

        cache_hit_log = None
        for call in log_calls:
            if "Cache hit served" in call[0][0]:
                cache_hit_log = call
                break

        assert cache_hit_log is not None
        log_extra = cache_hit_log[1]["extra"]
        assert log_extra["response_time_saved"] == 1.2
        assert log_extra["cache_age"] == 3600
