#!/usr/bin/env python3
"""
Tests for RAG STEP 66 — Return cached response

This step formats and returns the cached response, ensuring compatibility with the expected response format.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.llm.base import LLMResponse
from app.orchestrators.cache import step_66__return_cached


class TestRAGStep66ReturnCached:
    """Test suite for RAG STEP 66 - Return cached response"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_66_return_cached_success(self, mock_logger, mock_rag_log):
        """Test Step 66: Successful cached response return"""

        cached_response = LLMResponse(
            content="VAT rate for professional services is 22%",
            model="gpt-4",
            tokens_used=70,
            provider="openai",
            finish_reason="stop",
        )

        ctx = {
            "cached_response": cached_response,
            "cache_key": "cache_key_abc123def456",
            "query_hash": "hash123",
            "user_id": "user_123",
            "session_id": "session_456",
        }

        # Call the orchestrator function
        result = await step_66__return_cached(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["response_returned"] is True
        assert result["formatted_response"] == cached_response
        assert result["cache_key"] == "cache_key_abc123def456"
        assert result["model"] == "gpt-4"
        assert result["provider"] == "openai"
        assert "timestamp" in result

        # Verify cached flag is properly set

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "Cached response returned" in log_call[0][0]
        assert log_call[1]["extra"]["cache_event"] == "response_returned"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_66_missing_cached_response(self, mock_logger, mock_rag_log):
        """Test Step 66: Handle missing cached response"""

        ctx = {
            "cache_key": "some_key",
            "user_id": "user_123",
            # Missing cached_response
        }

        result = await step_66__return_cached(ctx=ctx)

        # Should return error result
        assert result["response_returned"] is False
        assert result["error"] == "Missing required parameter: cached_response"

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Cached response return failed" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_66_response_formatting(self, mock_logger, mock_rag_log):
        """Test Step 66: Response formatting and metadata addition"""

        cached_response = LLMResponse(
            content="Tax deduction information",
            model="gpt-3.5-turbo",
            tokens_used=70,
            provider="openai",  # Should be updated to True
        )

        ctx = {"cached_response": cached_response, "cache_key": "format_key", "response_time_saved": 1.5}

        result = await step_66__return_cached(ctx=ctx)

        assert result["response_returned"] is True
        assert result["response_time_saved"] == 1.5

        # Original response should maintain other properties
        formatted = result["formatted_response"]
        assert formatted.content == "Tax deduction information"
        assert formatted.model == "gpt-3.5-turbo"
        assert formatted.tokens_used == 30

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_66_response_metadata_enhancement(self, mock_logger, mock_rag_log):
        """Test Step 66: Enhanced metadata for cached responses"""

        cached_response = LLMResponse(content="Labor agreement information", model="claude-3", provider="anthropic")

        ctx = {
            "cached_response": cached_response,
            "cache_key": "metadata_key",
            "cache_age": 1800,  # 30 minutes old
            "cost_saved": 0.0045,
            "response_time_saved": 2.1,
        }

        result = await step_66__return_cached(ctx=ctx)

        assert result["response_returned"] is True
        assert result["cache_age"] == 1800
        assert result["cost_saved"] == 0.0045
        assert result["response_time_saved"] == 2.1

        # Verify metadata is accessible
        formatted = result["formatted_response"]
        assert formatted.content == "Labor agreement information"
        assert formatted.model == "claude-3"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_66_kwargs_parameters(self, mock_logger, mock_rag_log):
        """Test Step 66: Parameters passed via kwargs"""

        cached_response = LLMResponse(content="Kwargs cached response", model="gpt-4-turbo")

        # Call with kwargs instead of ctx
        result = await step_66__return_cached(
            cached_response=cached_response,
            cache_key="kwargs_cache_key",
            query_hash="kwargs_hash",
            user_id="user_456",
            session_id="session_789",
        )

        # Verify kwargs are processed correctly
        assert result["response_returned"] is True
        assert result["cache_key"] == "kwargs_cache_key"
        assert result["query_hash"] == "kwargs_hash"
        assert result["user_id"] == "user_456"
        assert result["session_id"] == "session_789"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_66_response_validation(self, mock_logger, mock_rag_log):
        """Test Step 66: Response validation and error handling"""

        # Test with invalid response object
        invalid_response = "Not an LLMResponse object"

        ctx = {"cached_response": invalid_response, "cache_key": "invalid_key"}

        result = await step_66__return_cached(ctx=ctx)

        # Should handle gracefully
        assert result["response_returned"] is False
        assert "error" in result

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_66_token_usage_preservation(self, mock_logger, mock_rag_log):
        """Test Step 66: Token usage preservation and reporting"""

        cached_response = LLMResponse(
            content="Detailed financial information with extensive context",
            model="gpt-4-turbo",
            tokens_used=70,
            provider="openai",
            finish_reason="stop",
        )

        ctx = {"cached_response": cached_response, "cache_key": "token_key"}

        result = await step_66__return_cached(ctx=ctx)

        assert result["response_returned"] is True

        # Verify token usage is preserved
        formatted = result["formatted_response"]
        assert formatted.tokens_used == 180
        assert formatted.token_usage["output_tokens"] == 95
        assert formatted.tokens_used == 275

        # Verify token usage reported in result
        assert {"tokens_used": result["cached_response"].tokens_used} == {
            "input_tokens": 180,
            "output_tokens": 95,
            "total_tokens": 275,
        }

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_66_minimal_response(self, mock_logger, mock_rag_log):
        """Test Step 66: Minimal response handling"""

        cached_response = LLMResponse(content="Simple answer", model="gpt-3.5-turbo")

        ctx = {
            "cached_response": cached_response
            # Minimal context
        }

        result = await step_66__return_cached(ctx=ctx)

        assert result["response_returned"] is True
        assert result["formatted_response"].content == "Simple answer"
        assert result["cache_key"] is None  # Should handle missing optional fields
        assert result["query_hash"] is None

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_66_performance_tracking(self, mock_logger, mock_rag_log):
        """Test Step 66: Performance tracking with timer"""

        with patch("app.orchestrators.cache.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            cached_response = LLMResponse(content="Test", model="gpt-4")

            # Call the orchestrator function
            await step_66__return_cached(ctx={"cached_response": cached_response, "cache_key": "perf_key"})

            # Verify timer was used
            mock_timer.assert_called_with(66, "RAG.cache.return.cached.response", "ReturnCached", stage="start")

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_66_comprehensive_logging_format(self, mock_logger, mock_rag_log):
        """Test Step 66: Verify comprehensive logging format"""

        cached_response = LLMResponse(content="Test", model="gpt-4")

        ctx = {"cached_response": cached_response, "cache_key": "format_key", "user_id": "user_123"}

        # Call the orchestrator function
        await step_66__return_cached(ctx=ctx)

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
            "response_returned",
            "cached",
            "cache_key",
            "processing_stage",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]["step"] == 66
        assert log_call[1]["step_id"] == "RAG.cache.return.cached.response"
        assert log_call[1]["node_label"] == "ReturnCached"
        assert log_call[1]["cache_event"] == "response_returned"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_66_response_compatibility(self, mock_logger, mock_rag_log):
        """Test Step 66: Response format compatibility verification"""

        cached_response = LLMResponse(
            content="Contract analysis results with citations",
            model="claude-3-sonnet",
            tokens_used=70,
            provider="anthropic",
            tool_calls=[],  # Empty tool calls
            finish_reason="stop",
        )

        ctx = {"cached_response": cached_response, "cache_key": "compatibility_key", "format_version": "1.0"}

        result = await step_66__return_cached(ctx=ctx)

        assert result["response_returned"] is True

        # Verify response maintains all original properties
        formatted = result["formatted_response"]
        assert formatted.content == "Contract analysis results with citations"
        assert formatted.model == "claude-3-sonnet"
        assert formatted.provider == "anthropic"
        assert formatted.tool_calls == []
        assert formatted.finish_reason == "stop"

        # Verify compatibility metadata
        assert result["format_version"] == "1.0"
