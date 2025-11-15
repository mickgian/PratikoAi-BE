"""
Tests for RAG Step 105: StreamSetup (ChatbotController.chat_stream Setup SSE).

This step sets up Server-Sent Events (SSE) streaming infrastructure for real-time
response delivery, configuring headers and preparing for async generator creation.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestRAGStep105StreamSetup:
    """Unit tests for Step 105: StreamSetup."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_105_sets_up_sse_configuration(self, mock_rag_log):
        """Test Step 105: Sets up SSE streaming configuration."""
        from app.orchestrators.streaming import step_105__stream_setup

        ctx = {
            "streaming_requested": True,
            "stream_configuration": {
                "media_type": "text/event-stream",
                "chunk_size": 1024,
                "include_usage": True,
                "include_metadata": True,
            },
            "processed_messages": [
                {"role": "user", "content": "Test streaming query"},
                {"role": "assistant", "content": "Test streaming response"},
            ],
            "session_data": {"id": "session_123"},
            "request_id": "test-105-sse-setup",
        }

        result = await step_105__stream_setup(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert result["next_step"] == "create_async_generator"
        assert result["streaming_setup"] == "configured"
        assert "sse_headers" in result
        assert result["sse_headers"]["Content-Type"] == "text/event-stream"
        assert result["sse_headers"]["Cache-Control"] == "no-cache"
        assert result["sse_headers"]["Connection"] == "keep-alive"

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_105_configures_sse_headers(self, mock_rag_log):
        """Test Step 105: Configures proper SSE headers."""
        from app.orchestrators.streaming import step_105__stream_setup

        ctx = {
            "streaming_requested": True,
            "stream_configuration": {"media_type": "text/event-stream"},
            "processed_messages": [{"role": "user", "content": "Test"}],
            "request_id": "test-105-headers",
        }

        result = await step_105__stream_setup(messages=[], ctx=ctx)

        sse_headers = result["sse_headers"]
        assert sse_headers["Content-Type"] == "text/event-stream"
        assert sse_headers["Cache-Control"] == "no-cache"
        assert sse_headers["Connection"] == "keep-alive"
        assert sse_headers["Access-Control-Allow-Origin"] == "*"
        assert sse_headers["Access-Control-Allow-Headers"] == "Cache-Control"

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_105_prepares_stream_context(self, mock_rag_log):
        """Test Step 105: Prepares streaming context for async generator."""
        from app.orchestrators.streaming import step_105__stream_setup

        ctx = {
            "streaming_requested": True,
            "processed_messages": [
                {"role": "user", "content": "User query"},
                {"role": "assistant", "content": "Assistant response"},
            ],
            "session_data": {"id": "session_456", "user_id": "user_789"},
            "response_metadata": {"provider": "openai", "model": "gpt-4"},
            "request_id": "test-105-context",
        }

        result = await step_105__stream_setup(messages=[], ctx=ctx)

        assert "stream_context" in result
        stream_context = result["stream_context"]
        assert stream_context["messages"] == ctx["processed_messages"]
        assert stream_context["session_id"] == "session_456"
        assert stream_context["user_id"] == "user_789"
        assert stream_context["provider"] == "openai"
        assert stream_context["model"] == "gpt-4"

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_105_handles_custom_stream_options(self, mock_rag_log):
        """Test Step 105: Handles custom streaming options."""
        from app.orchestrators.streaming import step_105__stream_setup

        ctx = {
            "streaming_requested": True,
            "stream_configuration": {
                "media_type": "text/event-stream",
                "chunk_size": 2048,
                "include_usage": False,
                "include_metadata": True,
                "custom_headers": {"X-Stream-ID": "stream_123", "X-Custom-Header": "custom_value"},
            },
            "processed_messages": [{"role": "user", "content": "Test"}],
            "request_id": "test-105-custom",
        }

        result = await step_105__stream_setup(messages=[], ctx=ctx)

        stream_config = result["stream_configuration"]
        assert stream_config["chunk_size"] == 2048
        assert stream_config["include_usage"] is False
        assert stream_config["include_metadata"] is True

        # Custom headers should be merged
        sse_headers = result["sse_headers"]
        assert sse_headers["X-Stream-ID"] == "stream_123"
        assert sse_headers["X-Custom-Header"] == "custom_value"

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_105_preserves_all_context_data(self, mock_rag_log):
        """Test Step 105: Preserves all context data for downstream processing."""
        from app.orchestrators.streaming import step_105__stream_setup

        original_ctx = {
            "streaming_requested": True,
            "processed_messages": [{"role": "user", "content": "Test"}],
            "user_data": {"id": "user_123"},
            "session_data": {"id": "session_456"},
            "response_metadata": {"provider": "openai", "tokens_used": 150},
            "processing_history": ["stream_check", "stream_setup"],
            "stream_configuration": {"media_type": "text/event-stream"},
            "request_id": "test-105-preserve",
        }

        result = await step_105__stream_setup(messages=[], ctx=original_ctx.copy())

        # Verify all original context is preserved
        assert result["user_data"] == original_ctx["user_data"]
        assert result["session_data"] == original_ctx["session_data"]
        assert result["response_metadata"] == original_ctx["response_metadata"]
        assert result["processing_history"] == original_ctx["processing_history"]
        assert result["processed_messages"] == original_ctx["processed_messages"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_105_adds_streaming_setup_metadata(self, mock_rag_log):
        """Test Step 105: Adds streaming setup metadata."""
        from app.orchestrators.streaming import step_105__stream_setup

        ctx = {
            "streaming_requested": True,
            "stream_configuration": {"media_type": "text/event-stream"},
            "processed_messages": [{"role": "user", "content": "Test"}],
            "request_id": "test-105-metadata",
        }

        result = await step_105__stream_setup(messages=[], ctx=ctx)

        assert result["processing_stage"] == "streaming_setup"
        assert result["next_step"] == "create_async_generator"
        assert result["streaming_setup"] == "configured"
        assert "setup_timestamp" in result

        # Verify timestamp format
        timestamp = result["setup_timestamp"]
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))  # Should not raise

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_105_configures_cors_headers(self, mock_rag_log):
        """Test Step 105: Configures CORS headers for browser streaming."""
        from app.orchestrators.streaming import step_105__stream_setup

        ctx = {
            "streaming_requested": True,
            "client_origin": "https://example.com",
            "cors_enabled": True,
            "processed_messages": [{"role": "user", "content": "Test"}],
            "request_id": "test-105-cors",
        }

        result = await step_105__stream_setup(messages=[], ctx=ctx)

        sse_headers = result["sse_headers"]
        assert "Access-Control-Allow-Origin" in sse_headers
        assert "Access-Control-Allow-Headers" in sse_headers
        assert "Access-Control-Allow-Methods" in sse_headers

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_105_handles_compression_settings(self, mock_rag_log):
        """Test Step 105: Handles compression settings for streaming."""
        from app.orchestrators.streaming import step_105__stream_setup

        ctx = {
            "streaming_requested": True,
            "stream_configuration": {
                "media_type": "text/event-stream",
                "enable_compression": True,
                "compression_level": 6,
            },
            "processed_messages": [{"role": "user", "content": "Test"}],
            "request_id": "test-105-compression",
        }

        result = await step_105__stream_setup(messages=[], ctx=ctx)

        stream_config = result["stream_configuration"]
        assert stream_config["enable_compression"] is True
        assert stream_config["compression_level"] == 6

        # Should add appropriate encoding header
        sse_headers = result["sse_headers"]
        assert "Content-Encoding" in sse_headers or "compression_enabled" in stream_config

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_105_validates_stream_requirements(self, mock_rag_log):
        """Test Step 105: Validates streaming requirements."""
        from app.orchestrators.streaming import step_105__stream_setup

        ctx = {
            "streaming_requested": True,
            "processed_messages": [],  # Empty messages
            "request_id": "test-105-validate",
        }

        result = await step_105__stream_setup(messages=[], ctx=ctx)

        # Should still proceed but with validation warnings
        assert result["next_step"] == "create_async_generator"
        assert "validation_warnings" in result or result["streaming_setup"] == "configured"

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_105_configures_heartbeat_settings(self, mock_rag_log):
        """Test Step 105: Configures heartbeat settings for connection keepalive."""
        from app.orchestrators.streaming import step_105__stream_setup

        ctx = {
            "streaming_requested": True,
            "stream_configuration": {
                "media_type": "text/event-stream",
                "heartbeat_interval": 30,
                "connection_timeout": 300,
            },
            "processed_messages": [{"role": "user", "content": "Test"}],
            "request_id": "test-105-heartbeat",
        }

        result = await step_105__stream_setup(messages=[], ctx=ctx)

        stream_config = result["stream_configuration"]
        assert stream_config["heartbeat_interval"] == 30
        assert stream_config["connection_timeout"] == 300

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_105_logs_setup_details(self, mock_rag_log):
        """Test Step 105: Logs streaming setup details for observability."""
        from app.orchestrators.streaming import step_105__stream_setup

        ctx = {
            "streaming_requested": True,
            "stream_configuration": {"media_type": "text/event-stream", "chunk_size": 1024},
            "processed_messages": [{"role": "user", "content": "Test query"}],
            "session_data": {"id": "session_123"},
            "request_id": "test-105-logging",
        }

        await step_105__stream_setup(messages=[], ctx=ctx)

        # Verify structured logging
        assert mock_rag_log.call_count >= 2

        # Find the completion log call
        completion_call = None
        for call in mock_rag_log.call_args_list:
            if call[1].get("processing_stage") == "completed":
                completion_call = call[1]
                break

        assert completion_call is not None
        assert completion_call["step"] == 105
        assert completion_call["streaming_setup"] == "configured"
        assert completion_call["next_step"] == "create_async_generator"


class TestRAGStep105Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_105_parity_sse_setup_behavior(self):
        """Test Step 105 parity: SSE setup behavior unchanged."""
        from app.orchestrators.streaming import step_105__stream_setup

        test_cases = [
            {
                "stream_configuration": {"media_type": "text/event-stream", "chunk_size": 1024},
                "expected_content_type": "text/event-stream",
            },
            {
                "stream_configuration": {"media_type": "text/event-stream", "chunk_size": 2048, "include_usage": True},
                "expected_content_type": "text/event-stream",
            },
            {
                "stream_configuration": {"media_type": "text/event-stream"},
                "expected_content_type": "text/event-stream",
            },
        ]

        for test_case in test_cases:
            ctx = {
                "streaming_requested": True,
                "processed_messages": [{"role": "user", "content": "Test"}],
                "request_id": f"parity-{hash(str(test_case))}",
                **test_case,
            }
            # Remove expected values from context
            ctx.pop("expected_content_type", None)

            with patch("app.orchestrators.streaming.rag_step_log"):
                result = await step_105__stream_setup(messages=[], ctx=ctx)

            assert result["sse_headers"]["Content-Type"] == test_case["expected_content_type"]
            assert result["next_step"] == "create_async_generator"
            assert result["streaming_setup"] == "configured"
            assert result["processing_stage"] == "streaming_setup"


class TestRAGStep105Integration:
    """Integration tests for Step 105 with neighbors."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_stream_check_to_105_integration(self, mock_stream_log):
        """Test StreamCheck → Step 105 integration."""

        # Simulate incoming from StreamCheck (Step 104)
        stream_check_ctx = {
            "streaming_requested": True,
            "decision": "yes",
            "decision_source": "stream_parameter",
            "stream_configuration": {"media_type": "text/event-stream", "chunk_size": 1024, "include_usage": True},
            "processed_messages": [
                {"role": "user", "content": "User query about Italian tax law"},
                {"role": "assistant", "content": "Response about Italian tax regulations"},
            ],
            "next_step": "stream_setup",
            "request_id": "integration-check-105",
        }

        from app.orchestrators.streaming import step_105__stream_setup

        result = await step_105__stream_setup(messages=[], ctx=stream_check_ctx)

        assert result["streaming_requested"] is True
        assert result["decision"] == "yes"
        assert result["next_step"] == "create_async_generator"
        assert result["streaming_setup"] == "configured"
        assert "sse_headers" in result
        assert "stream_context" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_105_prepares_for_async_gen(self, mock_rag_log):
        """Test Step 105 prepares data for AsyncGen (Step 106)."""
        from app.orchestrators.streaming import step_105__stream_setup

        ctx = {
            "streaming_requested": True,
            "processed_messages": [
                {"role": "user", "content": "User query"},
                {"role": "assistant", "content": "Assistant response"},
            ],
            "session_data": {"id": "session_456", "user_id": "user_789"},
            "stream_configuration": {"media_type": "text/event-stream", "chunk_size": 1024},
            "generator_ready": True,
            "request_id": "test-105-prep-async",
        }

        result = await step_105__stream_setup(messages=[], ctx=ctx)

        # Verify data prepared for AsyncGen step
        assert result["next_step"] == "create_async_generator"
        assert result["streaming_setup"] == "configured"
        assert "stream_context" in result
        assert result["stream_context"]["messages"] == ctx["processed_messages"]
        assert result["stream_context"]["session_id"] == "session_456"
        assert "sse_headers" in result
        assert result["generator_ready"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_105_error_handling(self, mock_rag_log):
        """Test Step 105: Error handling for invalid streaming setup."""
        from app.orchestrators.streaming import step_105__stream_setup

        ctx = {
            "streaming_requested": False,  # Inconsistent state
            "processed_messages": [{"role": "user", "content": "Test"}],
            "request_id": "test-105-error",
        }

        result = await step_105__stream_setup(messages=[], ctx=ctx)

        # Should handle gracefully with warnings
        assert "streaming_setup" in result
        assert result["next_step"] == "create_async_generator"
        # Should proceed but may have validation issues noted
