#!/usr/bin/env python3
"""
Tests for RAG STEP 62 — RAG.cache.cache_hit Cache hit?

This step checks Redis for cached responses using the generated cache key.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.llm.base import LLMResponse
from app.orchestrators.cache import step_62__cache_hit


class TestRAGStep62CacheHit:
    """Test suite for RAG STEP 62 - Cache hit check"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_62_cache_hit_found(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 62: Successful cache hit with response found"""

        # Mock cached response
        cached_response = LLMResponse(
            content="VAT rate for professional services is 22%", model="gpt-4", tokens_used=70, provider="openai"
        )

        # Mock cache service
        mock_cache_service.enabled = True
        mock_cache_service.get_cached_response.return_value = cached_response

        ctx = {
            "cache_key": "cache_key_abc123def456",
            "query_hash": "hash123",
            "model": "gpt-4",
            "user_id": "user_123",
            "session_id": "session_456",
        }

        # Call the orchestrator function
        result = await step_62__cache_hit(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["cache_hit"] is True
        assert result["cached_response"] == cached_response
        assert result["cache_key"] == "cache_key_abc123def456"
        assert result["query_hash"] == "hash123"
        assert result["user_id"] == "user_123"
        assert "timestamp" in result

        # Verify cache service was called correctly
        mock_cache_service.get_cached_response.assert_called_once_with("cache_key_abc123def456")

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "Cache hit found" in log_call[0][0]
        assert log_call[1]["extra"]["cache_event"] == "hit"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_62_cache_miss(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 62: Cache miss with no response found"""

        # Mock cache service returning None (miss)
        mock_cache_service.enabled = True
        mock_cache_service.get_cached_response.return_value = None

        ctx = {"cache_key": "cache_key_miss123", "query_hash": "hash456", "model": "gpt-4"}

        result = await step_62__cache_hit(ctx=ctx)

        assert result["cache_hit"] is False
        assert result["cached_response"] is None
        assert result["cache_key"] == "cache_key_miss123"

        # Verify cache service was called
        mock_cache_service.get_cached_response.assert_called_once_with("cache_key_miss123")

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "Cache miss" in log_call[0][0]
        assert log_call[1]["extra"]["cache_event"] == "miss"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_62_cache_disabled(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 62: Cache check with cache service disabled"""

        # Mock cache service as disabled
        mock_cache_service.enabled = False

        ctx = {"cache_key": "cache_key_disabled", "model": "gpt-3.5-turbo"}

        result = await step_62__cache_hit(ctx=ctx)

        assert result["cache_hit"] is False
        assert result["cached_response"] is None
        assert result["error"] == "Cache service disabled"

        # Should not call cache lookup
        mock_cache_service.get_cached_response.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_62_missing_cache_key(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 62: Handle missing cache key"""

        mock_cache_service.enabled = True

        ctx = {
            "query_hash": "hash123",
            "model": "gpt-4",
            # Missing cache_key
        }

        result = await step_62__cache_hit(ctx=ctx)

        # Should return error result
        assert result["cache_hit"] is False
        assert result["error"] == "Missing required parameter: cache_key"

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Cache hit check failed" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_62_cache_lookup_error(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 62: Handle cache lookup service error"""

        mock_cache_service.enabled = True
        mock_cache_service.get_cached_response.side_effect = Exception("Redis connection failed")

        ctx = {"cache_key": "cache_key_error", "model": "gpt-4"}

        result = await step_62__cache_hit(ctx=ctx)

        # Should return error result
        assert result["cache_hit"] is False
        assert result["error"] == "Redis connection failed"

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_62_kwargs_parameters(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 62: Parameters passed via kwargs"""

        cached_response = LLMResponse(content="Kwargs cache hit", model="claude-3")

        mock_cache_service.enabled = True
        mock_cache_service.get_cached_response.return_value = cached_response

        # Call with kwargs instead of ctx
        result = await step_62__cache_hit(
            cache_key="kwargs_cache_key", query_hash="kwargs_hash", model="claude-3", user_id="user_456"
        )

        # Verify kwargs are processed correctly
        assert result["cache_hit"] is True
        assert result["cached_response"] == cached_response
        assert result["cache_key"] == "kwargs_cache_key"
        assert result["query_hash"] == "kwargs_hash"
        assert result["user_id"] == "user_456"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service", None)
    async def test_step_62_no_cache_service(self, mock_logger, mock_rag_log):
        """Test Step 62: Handle missing cache service"""

        ctx = {"cache_key": "cache_key_no_service", "model": "gpt-4"}

        result = await step_62__cache_hit(ctx=ctx)

        assert result["cache_hit"] is False
        assert result["cached_response"] is None
        assert result["error"] == "Cache service not available"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_62_cached_response_validation(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 62: Cached response format validation"""

        # Mock various cached response formats
        cached_response = LLMResponse(
            content="Professional services VAT is 22% in Italy",
            model="gpt-4-turbo",
            tokens_used=70,
            provider="openai",
            finish_reason="stop",
        )

        mock_cache_service.enabled = True
        mock_cache_service.get_cached_response.return_value = cached_response

        ctx = {"cache_key": "validation_cache_key", "query_hash": "validation_hash"}

        result = await step_62__cache_hit(ctx=ctx)

        assert result["cache_hit"] is True
        assert isinstance(result["cached_response"], LLMResponse)
        assert result["cached_response"].content == "Professional services VAT is 22% in Italy"
        assert result["cached_response"].tokens_used == 70

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_62_performance_tracking(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 62: Performance tracking with timer"""

        with patch("app.orchestrators.cache.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_cache_service.enabled = True
            mock_cache_service.get_cached_response.return_value = None

            # Call the orchestrator function
            await step_62__cache_hit(ctx={"cache_key": "perf_cache_key", "model": "gpt-4"})

            # Verify timer was used
            mock_timer.assert_called_with(62, "RAG.cache.cache.hit", "CacheHit", stage="start")

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_62_comprehensive_logging_format(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 62: Verify comprehensive logging format"""

        mock_cache_service.enabled = True
        mock_cache_service.get_cached_response.return_value = None

        ctx = {"cache_key": "logging_cache_key", "query_hash": "logging_hash", "user_id": "user_123"}

        # Call the orchestrator function
        await step_62__cache_hit(ctx=ctx)

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
            "cache_hit",
            "cache_key",
            "processing_stage",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]["step"] == 62
        assert log_call[1]["step_id"] == "RAG.cache.cache.hit"
        assert log_call[1]["node_label"] == "CacheHit"
        assert log_call[1]["cache_event"] == "miss"
