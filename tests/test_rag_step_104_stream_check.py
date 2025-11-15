"""
Tests for RAG Step 104: StreamCheck (Streaming requested?).

This decision step determines if the client requested streaming response format,
routing to either StreamSetup (Step 105) or ReturnComplete (Step 112).
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestRAGStep104StreamCheck:
    """Unit tests for Step 104: StreamCheck."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_104_detects_streaming_request(self, mock_rag_log):
        """Test Step 104: Detects streaming request and routes to StreamSetup."""
        from app.orchestrators.streaming import step_104__stream_check

        ctx = {
            "request_data": {"stream": True, "messages": [{"role": "user", "content": "Test query"}]},
            "client_preferences": {"response_format": "stream", "media_type": "text/event-stream"},
            "processed_messages": [
                {"role": "user", "content": "Test query"},
                {"role": "assistant", "content": "Test response"},
            ],
            "request_id": "test-104-stream-yes",
        }

        result = await step_104__stream_check(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert result["streaming_requested"] is True
        assert result["next_step"] == "stream_setup"
        assert result["decision"] == "yes"
        assert "stream_configuration" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_104_detects_non_streaming_request(self, mock_rag_log):
        """Test Step 104: Detects non-streaming request and routes to ReturnComplete."""
        from app.orchestrators.streaming import step_104__stream_check

        ctx = {
            "request_data": {"stream": False, "messages": [{"role": "user", "content": "Test query"}]},
            "client_preferences": {"response_format": "json", "media_type": "application/json"},
            "processed_messages": [
                {"role": "user", "content": "Test query"},
                {"role": "assistant", "content": "Test response"},
            ],
            "request_id": "test-104-stream-no",
        }

        result = await step_104__stream_check(messages=[], ctx=ctx)

        assert result["streaming_requested"] is False
        assert result["next_step"] == "return_complete"
        assert result["decision"] == "no"
        assert result["response_format"] == "json"

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_104_handles_missing_stream_parameter(self, mock_rag_log):
        """Test Step 104: Handles missing stream parameter, defaults to non-streaming."""
        from app.orchestrators.streaming import step_104__stream_check

        ctx = {
            "request_data": {"messages": [{"role": "user", "content": "Test query without stream param"}]},
            "processed_messages": [
                {"role": "user", "content": "Test query"},
                {"role": "assistant", "content": "Test response"},
            ],
            "request_id": "test-104-stream-missing",
        }

        result = await step_104__stream_check(messages=[], ctx=ctx)

        assert result["streaming_requested"] is False
        assert result["next_step"] == "return_complete"
        assert result["decision"] == "no"
        assert result["default_used"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_104_handles_string_stream_values(self, mock_rag_log):
        """Test Step 104: Handles string stream values (true/false)."""
        from app.orchestrators.streaming import step_104__stream_check

        test_cases = [
            ("true", True),
            ("false", False),
            ("True", True),
            ("False", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
        ]

        for stream_value, expected_result in test_cases:
            ctx = {
                "request_data": {
                    "stream": stream_value,
                    "messages": [{"role": "user", "content": f"Test with stream={stream_value}"}],
                },
                "request_id": f"test-104-stream-{stream_value}",
            }

            result = await step_104__stream_check(messages=[], ctx=ctx)

            assert result["streaming_requested"] is expected_result
            expected_next = "stream_setup" if expected_result else "return_complete"
            assert result["next_step"] == expected_next

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_104_checks_http_headers(self, mock_rag_log):
        """Test Step 104: Checks HTTP headers for streaming preference."""
        from app.orchestrators.streaming import step_104__stream_check

        ctx = {
            "request_data": {"messages": [{"role": "user", "content": "Test query"}]},
            "http_headers": {"Accept": "text/event-stream", "Cache-Control": "no-cache"},
            "request_id": "test-104-headers",
        }

        result = await step_104__stream_check(messages=[], ctx=ctx)

        assert result["streaming_requested"] is True
        assert result["next_step"] == "stream_setup"
        assert result["decision_source"] == "http_headers"

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_104_preserves_all_context_data(self, mock_rag_log):
        """Test Step 104: Preserves all context data for downstream processing."""
        from app.orchestrators.streaming import step_104__stream_check

        original_ctx = {
            "request_data": {"stream": True},
            "processed_messages": [{"role": "user", "content": "Test"}, {"role": "assistant", "content": "Response"}],
            "user_data": {"id": "user_123"},
            "session_data": {"id": "session_456"},
            "response_metadata": {"provider": "openai", "model": "gpt-4", "tokens_used": 150},
            "processing_history": ["final_response", "process_messages", "log_completion"],
            "request_id": "test-104-context",
        }

        result = await step_104__stream_check(messages=[], ctx=original_ctx.copy())

        # Verify all original context is preserved
        assert result["user_data"] == original_ctx["user_data"]
        assert result["session_data"] == original_ctx["session_data"]
        assert result["response_metadata"] == original_ctx["response_metadata"]
        assert result["processing_history"] == original_ctx["processing_history"]
        assert result["processed_messages"] == original_ctx["processed_messages"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_104_adds_decision_metadata(self, mock_rag_log):
        """Test Step 104: Adds streaming decision metadata."""
        from app.orchestrators.streaming import step_104__stream_check

        ctx = {
            "request_data": {"stream": True},
            "processed_messages": [{"role": "user", "content": "Test"}],
            "request_id": "test-104-metadata",
        }

        result = await step_104__stream_check(messages=[], ctx=ctx)

        assert result["processing_stage"] == "streaming_decision"
        assert result["next_step"] == "stream_setup"
        assert result["streaming_requested"] is True
        assert result["decision"] == "yes"
        assert "decision_timestamp" in result

        # Verify timestamp format
        timestamp = result["decision_timestamp"]
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))  # Should not raise

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_104_configures_streaming_options(self, mock_rag_log):
        """Test Step 104: Configures streaming options when streaming is requested."""
        from app.orchestrators.streaming import step_104__stream_check

        ctx = {
            "request_data": {"stream": True, "stream_options": {"chunk_size": 1024, "include_usage": True}},
            "processed_messages": [{"role": "user", "content": "Test"}],
            "request_id": "test-104-config",
        }

        result = await step_104__stream_check(messages=[], ctx=ctx)

        assert result["streaming_requested"] is True
        assert "stream_configuration" in result
        stream_config = result["stream_configuration"]
        assert stream_config["media_type"] == "text/event-stream"
        assert stream_config["chunk_size"] == 1024
        assert stream_config["include_usage"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_104_handles_edge_cases(self, mock_rag_log):
        """Test Step 104: Handles edge cases gracefully."""
        from app.orchestrators.streaming import step_104__stream_check

        edge_cases = [
            # Empty context
            ({}, False),
            # Empty request data
            ({"request_data": {}}, False),
            # Null stream value
            ({"request_data": {"stream": None}}, False),
            # Invalid stream value
            ({"request_data": {"stream": "invalid"}}, False),
            # Numeric stream values
            ({"request_data": {"stream": 1}}, True),
            ({"request_data": {"stream": 0}}, False),
        ]

        for ctx_data, expected_streaming in edge_cases:
            ctx_data["request_id"] = f"test-104-edge-{hash(str(ctx_data))}"

            result = await step_104__stream_check(messages=[], ctx=ctx_data)

            assert result["streaming_requested"] is expected_streaming
            expected_next = "stream_setup" if expected_streaming else "return_complete"
            assert result["next_step"] == expected_next

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_104_logs_decision_details(self, mock_rag_log):
        """Test Step 104: Logs streaming decision details for observability."""
        from app.orchestrators.streaming import step_104__stream_check

        ctx = {
            "request_data": {"stream": True},
            "processed_messages": [{"role": "user", "content": "Test query"}],
            "decision_factors": {"stream_parameter": True, "accept_header": "text/event-stream"},
            "request_id": "test-104-logging",
        }

        await step_104__stream_check(messages=[], ctx=ctx)

        # Verify structured logging
        assert mock_rag_log.call_count >= 2

        # Find the completion log call
        completion_call = None
        for call in mock_rag_log.call_args_list:
            if call[1].get("processing_stage") == "completed":
                completion_call = call[1]
                break

        assert completion_call is not None
        assert completion_call["step"] == 104
        assert completion_call["streaming_requested"] is True
        assert completion_call["decision"] == "yes"
        assert completion_call["next_step"] == "stream_setup"


class TestRAGStep104Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_104_parity_streaming_decision_behavior(self):
        """Test Step 104 parity: Streaming decision behavior unchanged."""
        from app.orchestrators.streaming import step_104__stream_check

        test_cases = [
            {"request_data": {"stream": True}, "expected_streaming": True, "expected_next": "stream_setup"},
            {"request_data": {"stream": False}, "expected_streaming": False, "expected_next": "return_complete"},
            {"request_data": {}, "expected_streaming": False, "expected_next": "return_complete"},
            {
                "http_headers": {"Accept": "text/event-stream"},
                "expected_streaming": True,
                "expected_next": "stream_setup",
            },
        ]

        for test_case in test_cases:
            ctx = {
                **test_case,
                "processed_messages": [{"role": "user", "content": "Test"}],
                "request_id": f"parity-{hash(str(test_case))}",
            }
            # Remove expected values from context
            ctx.pop("expected_streaming", None)
            ctx.pop("expected_next", None)

            with patch("app.orchestrators.streaming.rag_step_log"):
                result = await step_104__stream_check(messages=[], ctx=ctx)

            assert result["streaming_requested"] == test_case["expected_streaming"]
            assert result["next_step"] == test_case["expected_next"]
            assert result["processing_stage"] == "streaming_decision"


class TestRAGStep104Integration:
    """Integration tests for Step 104 with neighbors."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_log_complete_to_104_integration(self, mock_log_log):
        """Test LogComplete → Step 104 integration."""

        # Simulate incoming from LogComplete (Step 103)
        log_complete_ctx = {
            "processed_messages": [
                {"role": "user", "content": "User query about Italian tax law"},
                {"role": "assistant", "content": "Response about Italian tax regulations"},
            ],
            "request_data": {
                "stream": True,
                "messages": [{"role": "user", "content": "User query about Italian tax law"}],
            },
            "completion_logged": True,
            "processing_stage": "completion_logged",
            "response_metadata": {"tokens_used": 150, "processing_time_ms": 1250},
            "request_id": "integration-log-104",
        }

        from app.orchestrators.streaming import step_104__stream_check

        result = await step_104__stream_check(messages=[], ctx=log_complete_ctx)

        assert result["completion_logged"] is True
        assert result["streaming_requested"] is True
        assert result["next_step"] == "stream_setup"
        assert "response_metadata" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_104_prepares_for_stream_setup(self, mock_rag_log):
        """Test Step 104 prepares data for StreamSetup (Step 105)."""
        from app.orchestrators.streaming import step_104__stream_check

        ctx = {
            "request_data": {"stream": True},
            "processed_messages": [
                {"role": "user", "content": "User query"},
                {"role": "assistant", "content": "Assistant response"},
            ],
            "stream_preferences": {"chunk_size": 1024, "include_metadata": True},
            "request_id": "test-104-prep-stream",
        }

        result = await step_104__stream_check(messages=[], ctx=ctx)

        # Verify data prepared for StreamSetup step
        assert result["next_step"] == "stream_setup"
        assert result["streaming_requested"] is True
        assert "stream_configuration" in result
        assert result["stream_configuration"]["media_type"] == "text/event-stream"
        assert "stream_preferences" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.streaming.rag_step_log")
    async def test_step_104_prepares_for_return_complete(self, mock_rag_log):
        """Test Step 104 prepares data for ReturnComplete (Step 112)."""
        from app.orchestrators.streaming import step_104__stream_check

        ctx = {
            "request_data": {"stream": False},
            "processed_messages": [
                {"role": "user", "content": "User query"},
                {"role": "assistant", "content": "Assistant response"},
            ],
            "response_format": "json",
            "completion_ready": True,
            "request_id": "test-104-prep-complete",
        }

        result = await step_104__stream_check(messages=[], ctx=ctx)

        # Verify data prepared for ReturnComplete step
        assert result["next_step"] == "return_complete"
        assert result["streaming_requested"] is False
        assert result["response_format"] == "json"
        assert result["completion_ready"] is True
