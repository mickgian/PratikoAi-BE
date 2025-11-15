"""
Tests for RAG Step 108: WriteSSE (write_sse Format chunks).

This process step formats streaming chunks into SSE format,
taking protected stream data from Step 107 and preparing for Step 109.
"""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRAGStep108WriteSSE:
    """Unit tests for Step 108: WriteSSE."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_108_formats_sse_chunks(self, mock_rag_log):
        """Test Step 108: Formats streaming chunks into SSE format."""
        from app.orchestrators.streaming import step_108__write_sse

        async def test_stream():
            yield "chunk1: test content"
            yield "chunk2: more content"
            yield "[DONE]"

        ctx = {
            "wrapped_stream": test_stream(),
            "protection_config": {
                "session_id": "test_session_123",
                "user_id": "user_456",
                "provider": "openai",
                "model": "gpt-4",
                "streaming_enabled": True,
            },
            "stream_protected": True,
            "request_id": "test-108-format-sse",
        }

        result = await step_108__write_sse(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert "sse_formatted_stream" in result
        assert result["chunks_formatted"] is True
        assert result["next_step"] == "streaming_response"
        assert "format_config" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_108_configures_sse_formatting(self, mock_rag_log):
        """Test Step 108: Configures SSE formatting settings."""
        from app.orchestrators.streaming import step_108__write_sse

        async def test_stream():
            yield "formatted test content"

        ctx = {
            "wrapped_stream": test_stream(),
            "protection_config": {
                "session_id": "session_123",
                "provider": "anthropic",
                "model": "claude-3-sonnet",
                "include_metadata": True,
                "chunk_size": 1024,
            },
            "sse_headers": {"Content-Type": "text/event-stream", "Cache-Control": "no-cache"},
            "request_id": "test-108-config",
        }

        result = await step_108__write_sse(messages=[], ctx=ctx)

        format_config = result["format_config"]
        assert format_config["provider"] == "anthropic"
        assert format_config["model"] == "claude-3-sonnet"
        assert format_config["include_metadata"] is True
        assert format_config["chunk_size"] == 1024
        assert format_config["sse_format"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_108_handles_complex_chunks(self, mock_rag_log):
        """Test Step 108: Handles complex chunk structures for SSE formatting."""
        from app.orchestrators.streaming import step_108__write_sse

        async def complex_stream():
            yield {"type": "chunk", "content": "chunk1", "metadata": {"tokens": 10}}
            yield {"type": "chunk", "content": "chunk2", "metadata": {"tokens": 15}}
            yield {"type": "done", "content": "[DONE]", "metadata": {"total_tokens": 25}}

        ctx = {
            "wrapped_stream": complex_stream(),
            "protection_config": {
                "session_id": "complex_session",
                "streaming_enabled": True,
                "include_metadata": True,
                "format": "sse",
            },
            "format_options": {"json_format": True, "include_timestamps": True},
            "request_id": "test-108-complex",
        }

        result = await step_108__write_sse(messages=[], ctx=ctx)

        assert result["sse_formatted_stream"] is not None
        assert result["chunks_formatted"] is True
        assert "format_options" in result
        assert result["format_config"]["json_format"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_108_preserves_all_context_data(self, mock_rag_log):
        """Test Step 108: Preserves all context data for downstream processing."""
        from app.orchestrators.streaming import step_108__write_sse

        async def test_stream():
            yield "preserved context test"

        original_ctx = {
            "wrapped_stream": test_stream(),
            "protection_config": {"session_id": "preserve_session"},
            "user_data": {"id": "user_123", "preferences": {"language": "it"}},
            "session_data": {"id": "session_456", "created_at": "2024-01-01"},
            "response_metadata": {"provider": "anthropic", "model": "claude-3", "tokens_used": 200},
            "processing_history": ["stream_check", "stream_setup", "async_gen", "single_pass"],
            "sse_headers": {"Content-Type": "text/event-stream"},
            "stream_protected": True,
            "request_id": "test-108-preserve",
        }

        result = await step_108__write_sse(messages=[], ctx=original_ctx.copy())

        # Verify all original context is preserved
        assert result["user_data"] == original_ctx["user_data"]
        assert result["session_data"] == original_ctx["session_data"]
        assert result["response_metadata"] == original_ctx["response_metadata"]
        assert result["processing_history"] == original_ctx["processing_history"]
        assert result["sse_headers"] == original_ctx["sse_headers"]
        assert result["protection_config"] == original_ctx["protection_config"]
        assert result["stream_protected"] == original_ctx["stream_protected"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_108_adds_formatting_metadata(self, mock_rag_log):
        """Test Step 108: Adds SSE formatting metadata."""
        from app.orchestrators.streaming import step_108__write_sse

        async def test_stream():
            yield "metadata test"

        ctx = {
            "wrapped_stream": test_stream(),
            "protection_config": {"session_id": "test_session"},
            "stream_protected": True,
            "request_id": "test-108-metadata",
        }

        result = await step_108__write_sse(messages=[], ctx=ctx)

        assert result["processing_stage"] == "sse_formatted"
        assert result["next_step"] == "streaming_response"
        assert result["chunks_formatted"] is True
        assert "formatting_timestamp" in result

        # Verify timestamp format
        timestamp = result["formatting_timestamp"]
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))  # Should not raise

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_108_validates_stream_requirements(self, mock_rag_log):
        """Test Step 108: Validates stream requirements and adds warnings."""
        from app.orchestrators.streaming import step_108__write_sse

        # Test with missing/invalid stream
        ctx = {
            "wrapped_stream": None,  # Missing stream
            "protection_config": {},  # Empty config
            "stream_protected": False,  # Not protected
            "request_id": "test-108-validation",
        }

        result = await step_108__write_sse(messages=[], ctx=ctx)

        assert "validation_warnings" in result
        warnings = result["validation_warnings"]
        assert len(warnings) > 0
        assert any("No wrapped stream available" in warning for warning in warnings)
        assert any("stream not protected" in warning for warning in warnings)

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_108_configures_sse_options(self, mock_rag_log):
        """Test Step 108: Configures SSE formatting options."""
        from app.orchestrators.streaming import step_108__write_sse

        async def test_stream():
            yield "sse options test"

        ctx = {
            "wrapped_stream": test_stream(),
            "protection_config": {
                "session_id": "options_session",
                "format": "sse",
                "compression": True,
                "buffer_size": 2048,
            },
            "sse_format_config": {"event_type": "message", "retry_interval": 3000, "include_id": True},
            "request_id": "test-108-options",
        }

        result = await step_108__write_sse(messages=[], ctx=ctx)

        format_config = result["format_config"]
        assert format_config["format"] == "sse"
        assert format_config["compression"] is True
        assert format_config["buffer_size"] == 2048
        assert "sse_format_config" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_108_handles_stream_errors(self, mock_rag_log):
        """Test Step 108: Handles stream errors gracefully."""
        from app.orchestrators.streaming import step_108__write_sse

        async def error_stream():
            yield "chunk1"
            raise Exception("Stream error")

        ctx = {
            "wrapped_stream": error_stream(),
            "protection_config": {"session_id": "error_session", "error_handling": "graceful"},
            "error_recovery_enabled": True,
            "request_id": "test-108-errors",
        }

        result = await step_108__write_sse(messages=[], ctx=ctx)

        assert result["sse_formatted_stream"] is not None
        assert result["chunks_formatted"] is True
        assert result["format_config"]["error_handling"] == "graceful"

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_108_handles_formatting_parameters(self, mock_rag_log):
        """Test Step 108: Handles various formatting parameters."""
        from app.orchestrators.streaming import step_108__write_sse

        async def params_stream():
            yield "formatting params test"

        ctx = {
            "wrapped_stream": params_stream(),
            "protection_config": {
                "session_id": "params_session",
                "include_usage": True,
                "include_metadata": False,
                "chunk_delimiter": "\n\n",
            },
            "formatting_options": {"pretty_json": True, "escape_newlines": True, "max_chunk_size": 4096},
            "request_id": "test-108-params",
        }

        result = await step_108__write_sse(messages=[], ctx=ctx)

        assert result["sse_formatted_stream"] is not None
        config = result["format_config"]
        assert config["include_usage"] is True
        assert config["include_metadata"] is False
        assert config["chunk_delimiter"] == "\n\n"
        assert "formatting_options" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_108_logs_formatting_details(self, mock_rag_log):
        """Test Step 108: Logs SSE formatting details for observability."""
        from app.orchestrators.streaming import step_108__write_sse

        async def logging_stream():
            yield "logging test"

        ctx = {
            "wrapped_stream": logging_stream(),
            "protection_config": {"session_id": "logging_session", "provider": "openai", "model": "gpt-4"},
            "formatting_metrics": {"chunks_processed": 10, "bytes_formatted": 2048},
            "request_id": "test-108-logging",
        }

        await step_108__write_sse(messages=[], ctx=ctx)

        # Verify structured logging
        assert mock_rag_log.call_count >= 2

        # Find the completion log call
        completion_call = None
        for call in mock_rag_log.call_args_list:
            if call[1].get("processing_stage") == "completed":
                completion_call = call[1]
                break

        assert completion_call is not None
        assert completion_call["step"] == 108
        assert completion_call["chunks_formatted"] is True
        assert completion_call["next_step"] == "streaming_response"


class TestRAGStep108Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_108_parity_sse_formatting_behavior(self):
        """Test Step 108 parity: SSE formatting behavior unchanged."""
        from app.orchestrators.streaming import step_108__write_sse

        async def parity_stream():
            yield "parity test chunk 1"
            yield "parity test chunk 2"

        test_cases = [
            {
                "wrapped_stream": parity_stream(),
                "protection_config": {"session_id": "parity_1", "streaming_enabled": True},
                "expected_formatted": True,
                "expected_next": "streaming_response",
            },
            {
                "wrapped_stream": parity_stream(),
                "protection_config": {"session_id": "parity_2", "provider": "anthropic", "model": "claude-3"},
                "expected_formatted": True,
                "expected_next": "streaming_response",
            },
        ]

        for test_case in test_cases:
            ctx = {**test_case, "request_id": f"parity-{hash(str(test_case))}"}
            # Remove expected values from context
            ctx.pop("expected_formatted", None)
            ctx.pop("expected_next", None)

            with patch("app.orchestrators.streaming.rag_step_log"):
                result = await step_108__write_sse(messages=[], ctx=ctx)

            assert result["chunks_formatted"] == test_case["expected_formatted"]
            assert result["next_step"] == test_case["expected_next"]
            assert result["processing_stage"] == "sse_formatted"


class TestRAGStep108Integration:
    """Integration tests for Step 108 with neighbors."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_single_pass_to_108_integration(self, mock_single_pass_log):
        """Test SinglePass → Step 108 integration."""

        # Simulate incoming from SinglePass (Step 107)
        async def integration_stream():
            yield "integration chunk 1"
            yield "integration chunk 2"
            yield "[DONE]"

        single_pass_ctx = {
            "wrapped_stream": integration_stream(),
            "protection_config": {
                "double_iteration_prevention": True,
                "session_id": "integration_session_108",
                "user_id": "integration_user",
                "provider": "openai",
                "model": "gpt-4",
                "streaming_enabled": True,
                "chunk_size": 1024,
            },
            "stream_protected": True,
            "processing_stage": "stream_protected",
            "next_step": "write_sse",
            "request_id": "integration-single-pass-108",
        }

        from app.orchestrators.streaming import step_108__write_sse

        result = await step_108__write_sse(messages=[], ctx=single_pass_ctx)

        assert result["stream_protected"] is True
        assert result["chunks_formatted"] is True
        assert result["next_step"] == "streaming_response"
        assert "sse_formatted_stream" in result
        assert "protection_config" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_108_prepares_for_stream_response(self, mock_rag_log):
        """Test Step 108 prepares data for StreamResponse (Step 109)."""
        from app.orchestrators.streaming import step_108__write_sse

        async def response_prep_stream():
            yield "data: prepared for streaming response\n\n"
            yield "data: another formatted chunk\n\n"

        ctx = {
            "wrapped_stream": response_prep_stream(),
            "protection_config": {"session_id": "response_prep_session", "streaming_enabled": True, "format": "sse"},
            "sse_headers": {"Content-Type": "text/event-stream", "Cache-Control": "no-cache"},
            "request_id": "test-108-prep-response",
        }

        result = await step_108__write_sse(messages=[], ctx=ctx)

        # Verify data prepared for StreamResponse step
        assert result["next_step"] == "streaming_response"
        assert result["chunks_formatted"] is True
        assert "sse_formatted_stream" in result
        assert result["sse_formatted_stream"] is not None
        assert "sse_headers" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_108_error_handling(self, mock_rag_log):
        """Test Step 108 error handling and recovery."""
        from app.orchestrators.streaming import step_108__write_sse

        # Test with minimal/invalid context
        minimal_ctx = {"request_id": "test-108-error-handling"}

        result = await step_108__write_sse(messages=[], ctx=minimal_ctx)

        # Should handle gracefully with warnings
        assert "validation_warnings" in result
        assert result["chunks_formatted"] is True  # Should still format
        assert "sse_formatted_stream" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_108_streaming_flow_integration(self, mock_rag_log):
        """Test Step 108 integration with full streaming flow."""
        from app.orchestrators.streaming import step_108__write_sse

        async def full_flow_stream():
            yield "Full streaming flow test chunk 1"
            yield "Full streaming flow test chunk 2"
            yield "[DONE]"

        # Simulate full streaming context from previous steps
        full_streaming_ctx = {
            # From StreamCheck (Step 104)
            "streaming_requested": True,
            "decision": "yes",
            "decision_source": "stream_parameter",
            # From StreamSetup (Step 105)
            "sse_headers": {
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
            "stream_context": {
                "session_id": "full_flow_session",
                "user_id": "full_flow_user",
                "streaming_enabled": True,
            },
            "streaming_setup": "configured",
            # From AsyncGen (Step 106)
            "generator_created": True,
            # From SinglePass (Step 107)
            "wrapped_stream": full_flow_stream(),
            "protection_config": {
                "double_iteration_prevention": True,
                "session_id": "full_flow_session",
                "provider": "anthropic",
                "model": "claude-3-sonnet",
                "streaming_enabled": True,
            },
            "stream_protected": True,
            "processing_stage": "stream_protected",
            "request_id": "integration-full-flow-108",
        }

        result = await step_108__write_sse(messages=[], ctx=full_streaming_ctx)

        # Verify integration with full flow
        assert result["streaming_requested"] is True
        assert result["streaming_setup"] == "configured"
        assert result["generator_created"] is True
        assert result["stream_protected"] is True
        assert result["chunks_formatted"] is True
        assert result["next_step"] == "streaming_response"
        assert "sse_formatted_stream" in result
        assert result["processing_stage"] == "sse_formatted"
