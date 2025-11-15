#!/usr/bin/env python3
"""
Tests for RAG STEP 59 — LangGraphAgent._get_cached_llm_response Check for cached response

This step initializes the cache checking process and prepares context for cache operations.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.orchestrators.cache import step_59__check_cache
from app.schemas.chat import Message


class TestRAGStep59CheckCache:
    """Test suite for RAG STEP 59 - Initialize cache check"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_59_cache_check_success(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 59: Successful cache check initialization"""

        # Mock cache service
        mock_cache_service.enabled = True
        mock_cache_service._generate_query_hash.return_value = "abc123def456"

        ctx = {
            "messages": [{"role": "user", "content": "What is the VAT rate for professional services?"}],
            "model": "gpt-4",
            "temperature": 0.2,
            "user_id": "user_123",
            "session_id": "session_456",
            "provider": "openai",
        }

        # Call the orchestrator function
        result = await step_59__check_cache(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["cache_check_initialized"] is True
        assert result["cache_enabled"] is True
        assert result["messages_count"] == 1
        assert result["model"] == "gpt-4"
        assert result["temperature"] == 0.2
        assert result["query_hash"] == "abc123def456"
        assert result["user_id"] == "user_123"
        assert "timestamp" in result

        # Verify cache service was called correctly
        mock_cache_service._generate_query_hash.assert_called_once()
        call_args = mock_cache_service._generate_query_hash.call_args
        assert call_args[1]["model"] == "gpt-4"
        assert call_args[1]["temperature"] == 0.2
        assert len(call_args[1]["messages"]) == 1

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "Cache check initialized" in log_call[0][0]
        assert log_call[1]["extra"]["cache_event"] == "check_initialized"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_59_cache_disabled(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 59: Cache check with cache service disabled"""

        # Mock cache service as disabled
        mock_cache_service.enabled = False

        ctx = {
            "messages": [{"role": "user", "content": "Test message"}],
            "model": "gpt-3.5-turbo",
            "user_id": "user_123",
        }

        result = await step_59__check_cache(ctx=ctx)

        assert result["cache_check_initialized"] is True
        assert result["cache_enabled"] is False
        assert result["query_hash"] is None
        assert result["model"] == "gpt-3.5-turbo"

        # Should not call hash generation
        mock_cache_service._generate_query_hash.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_59_missing_required_params(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 59: Handle missing required parameters"""

        mock_cache_service.enabled = True

        ctx = {}  # Missing messages and model

        result = await step_59__check_cache(ctx=ctx)

        # Should return error result
        assert result["cache_check_initialized"] is False
        assert result["error"] == "Missing required cache check parameters: messages or model"

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Cache check initialization failed" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_59_message_format_conversion(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 59: Various message format handling"""

        mock_cache_service.enabled = True
        mock_cache_service._generate_query_hash.return_value = "converted123"

        # Test with different message formats
        ctx = {
            "messages": [
                {"role": "user", "content": "Dict format"},
                Message(role="assistant", content="Message object format"),
                "Simple string format",
            ],
            "model": "gpt-4",
        }

        result = await step_59__check_cache(ctx=ctx)

        assert result["cache_check_initialized"] is True
        assert result["messages_count"] == 3
        assert result["query_hash"] == "converted123"

        # Verify all message formats were converted
        mock_cache_service._generate_query_hash.assert_called_once()
        call_args = mock_cache_service._generate_query_hash.call_args
        messages = call_args[1]["messages"]
        assert len(messages) == 3
        assert all(hasattr(msg, "role") and hasattr(msg, "content") for msg in messages)

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_59_hash_generation_error(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 59: Handle hash generation service error"""

        mock_cache_service.enabled = True
        mock_cache_service._generate_query_hash.side_effect = Exception("Hash generation failed")

        ctx = {"messages": [{"role": "user", "content": "Test message"}], "model": "gpt-4"}

        result = await step_59__check_cache(ctx=ctx)

        # Should return error result
        assert result["cache_check_initialized"] is False
        assert result["error"] == "Hash generation failed"

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_59_kwargs_parameters(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 59: Parameters passed via kwargs"""

        mock_cache_service.enabled = True
        mock_cache_service._generate_query_hash.return_value = "kwargs123"

        # Call with kwargs instead of ctx
        result = await step_59__check_cache(
            messages=[{"role": "user", "content": "Test"}],
            model="claude-3",
            temperature=0.5,
            user_id="user_456",
            provider="anthropic",
        )

        # Verify kwargs are processed correctly
        assert result["cache_check_initialized"] is True
        assert result["model"] == "claude-3"
        assert result["temperature"] == 0.5
        assert result["user_id"] == "user_456"
        assert result["provider"] == "anthropic"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service", None)
    async def test_step_59_no_cache_service(self, mock_logger, mock_rag_log):
        """Test Step 59: Handle missing cache service"""

        ctx = {"messages": [{"role": "user", "content": "Test"}], "model": "gpt-4"}

        result = await step_59__check_cache(ctx=ctx)

        assert result["cache_check_initialized"] is True
        assert result["cache_enabled"] is False
        assert result["query_hash"] is None

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_59_performance_tracking(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 59: Performance tracking with timer"""

        with patch("app.orchestrators.cache.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_cache_service.enabled = True
            mock_cache_service._generate_query_hash.return_value = "perf123"

            # Call the orchestrator function
            await step_59__check_cache(ctx={"messages": [{"role": "user", "content": "Test"}], "model": "gpt-4"})

            # Verify timer was used
            mock_timer.assert_called_with(
                59,
                "RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response",
                "CheckCache",
                stage="start",
            )

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_59_comprehensive_logging_format(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 59: Verify comprehensive logging format"""

        mock_cache_service.enabled = True
        mock_cache_service._generate_query_hash.return_value = "log123"

        ctx = {"messages": [{"role": "user", "content": "Test message"}], "model": "gpt-4", "user_id": "user_123"}

        # Call the orchestrator function
        await step_59__check_cache(ctx=ctx)

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
            "cache_check_initialized",
            "cache_enabled",
            "model",
            "messages_count",
            "processing_stage",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]["step"] == 59
        assert log_call[1]["step_id"] == "RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response"
        assert log_call[1]["node_label"] == "CheckCache"
        assert log_call[1]["cache_event"] == "check_initialized"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_59_data_structure(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 59: Verify cache check data structure"""

        mock_cache_service.enabled = True
        mock_cache_service._generate_query_hash.return_value = "struct123"

        ctx = {
            "messages": [{"role": "user", "content": "Test"}],
            "model": "gpt-4",
            "temperature": 0.3,
            "user_id": "user_123",
        }

        # Call the orchestrator function
        result = await step_59__check_cache(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            "timestamp",
            "cache_check_initialized",
            "cache_enabled",
            "messages_count",
            "model",
            "temperature",
            "query_hash",
            "user_id",
            "session_id",
            "provider",
            "error",
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in cache check data: {field}"

        # Verify data types
        assert isinstance(result["timestamp"], str)
        assert isinstance(result["cache_check_initialized"], bool)
        assert isinstance(result["cache_enabled"], bool)
        assert isinstance(result["messages_count"], int)
        assert isinstance(result["model"], str) or result["model"] is None
        assert isinstance(result["temperature"], int | float)
        assert isinstance(result["query_hash"], str) or result["query_hash"] is None

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
