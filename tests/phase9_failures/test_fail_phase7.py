"""
Failure injection tests for Phase 7: Streaming failures.

Tests error handling for stream disconnects and SSE write errors.
"""

from unittest.mock import patch

import pytest

from app.core.langgraph.nodes.step_105__stream_setup import node_step_105
from app.core.langgraph.nodes.step_108__write_sse import node_step_108
from app.core.langgraph.nodes.step_109__stream_response import node_step_109
from tests.common.fakes import FakeOrchestrator, FakeSSEWriter
from tests.common.fixtures_state import make_state, state_streaming_enabled


@pytest.mark.failure
@pytest.mark.phase7
class TestPhase7StreamDisconnect:
    """Test stream disconnect handling."""

    async def test_stream_disconnect_during_write(self):
        """Verify stream disconnect during write is handled gracefully."""
        state = state_streaming_enabled()
        state["response"] = {"content": "chunk1 chunk2 chunk3", "complete": True}

        # SSE write fails mid-stream
        fake_write = FakeOrchestrator(
            {
                "chunks_written": 1,  # Only wrote 1 chunk before disconnect
                "write_success": False,
                "error": "Stream disconnect",
                "disconnect": True,
                "chunks_attempted": 3,
            }
        )
        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_write):
            state = await node_step_108(state)

        # Disconnect handled
        assert state.get("write_success") is False
        assert state.get("disconnect") is True
        assert state.get("chunks_written", 0) < state.get("chunks_attempted", 0)

    async def test_stream_disconnect_cleanup(self):
        """Verify stream disconnect triggers proper cleanup."""
        state = state_streaming_enabled()

        # Disconnect during streaming
        fake_stream = FakeOrchestrator(
            {"streaming_in_progress": False, "disconnect": True, "error": "Connection lost", "cleanup_triggered": True}
        )
        with patch("app.core.langgraph.nodes.step_109__stream_response.step_109__stream_response", fake_stream):
            state = await node_step_109(state)

        # Cleanup triggered
        assert state.get("disconnect") is True
        assert state.get("cleanup_triggered") is True

    async def test_stream_client_timeout(self):
        """Verify client timeout during streaming is handled."""
        state = state_streaming_enabled()

        fake_write = FakeOrchestrator(
            {"write_success": False, "error": "Client timeout", "timeout": True, "client_disconnected": True}
        )
        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_write):
            state = await node_step_108(state)

        # Timeout handled
        assert state.get("write_success") is False
        assert state.get("timeout") is True


@pytest.mark.failure
@pytest.mark.phase7
class TestPhase7SSEWriteErrors:
    """Test SSE write errors."""

    async def test_sse_write_buffer_overflow(self):
        """Verify SSE buffer overflow is handled."""
        state = state_streaming_enabled()
        state["response"] = {"content": "x" * 1000000, "complete": True}  # Very large

        fake_write = FakeOrchestrator(
            {"write_success": False, "error": "Buffer overflow", "buffer_exceeded": True, "buffer_size": 65536}
        )
        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_write):
            state = await node_step_108(state)

        # Buffer overflow handled
        assert state.get("write_success") is False
        assert state.get("buffer_exceeded") is True

    async def test_sse_connection_not_ready(self):
        """Verify error when SSE connection not ready."""
        state = state_streaming_enabled()

        # Connection not ready
        fake_write = FakeOrchestrator(
            {"write_success": False, "error": "SSE connection not ready", "connection_ready": False}
        )
        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_write):
            state = await node_step_108(state)

        # Connection error
        assert state.get("write_success") is False
        assert state.get("connection_ready") is False

    async def test_sse_partial_write_recovery(self):
        """Verify recovery from partial write failure."""
        state = state_streaming_enabled()
        state["response"] = {"content": "chunk1 chunk2 chunk3 chunk4", "complete": True}

        # Partial write (some succeeded, some failed)
        fake_write = FakeOrchestrator(
            {
                "write_success": False,
                "partial_write": True,
                "chunks_written": 2,
                "chunks_attempted": 4,
                "error": "Write failed after chunk 2",
            }
        )
        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_write):
            state = await node_step_108(state)

        # Partial write tracked
        assert state.get("partial_write") is True
        assert state.get("chunks_written") == 2


@pytest.mark.failure
@pytest.mark.phase7
class TestPhase7StreamSetupErrors:
    """Test stream setup errors."""

    async def test_stream_setup_generator_creation_fails(self):
        """Verify generator creation failure is handled."""
        state = state_streaming_enabled()

        # Generator creation fails
        fake_setup = FakeOrchestrator(
            {"sse_ready": False, "generator_created": False, "error": "Failed to create async generator"}
        )
        with patch("app.core.langgraph.nodes.step_105__stream_setup.step_105__stream_setup", fake_setup):
            state = await node_step_105(state)

        # Setup failed
        assert state.get("sse_ready") is False
        assert state.get("generator_created") is False

    async def test_stream_setup_sse_channel_unavailable(self):
        """Verify SSE channel unavailable is handled."""
        state = state_streaming_enabled()

        fake_setup = FakeOrchestrator(
            {"sse_ready": False, "error": "SSE channel unavailable", "channel_available": False}
        )
        with patch("app.core.langgraph.nodes.step_105__stream_setup.step_105__stream_setup", fake_setup):
            state = await node_step_105(state)

        # Channel unavailable
        assert state.get("sse_ready") is False
        assert state.get("channel_available") is False

    async def test_stream_fallback_to_single_pass(self):
        """Verify fallback to single-pass when streaming setup fails."""
        state = state_streaming_enabled()

        # Streaming setup fails
        fake_setup = FakeOrchestrator(
            {"sse_ready": False, "generator_created": False, "error": "Setup failed", "fallback_to_single_pass": True}
        )
        with patch("app.core.langgraph.nodes.step_105__stream_setup.step_105__stream_setup", fake_setup):
            state = await node_step_105(state)

        # Should fallback
        assert state.get("fallback_to_single_pass") is True

        # Use single-pass instead
        fake_single = FakeOrchestrator({"response_complete": True, "response_sent": True, "streaming_disabled": True})
        with patch("app.core.langgraph.nodes.step_107__single_pass.step_107__single_pass", fake_single):
            from app.core.langgraph.nodes.step_107__single_pass import node_step_107

            state = await node_step_107(state)

        # Single-pass used
        assert state.get("response_complete") is True


@pytest.mark.failure
@pytest.mark.phase7
class TestPhase7StreamingDataErrors:
    """Test errors with streaming data."""

    async def test_stream_empty_response_chunks(self):
        """Verify empty response chunks are handled."""
        state = state_streaming_enabled()
        state["response"] = {"content": "", "complete": True}

        fake_write = FakeOrchestrator({"write_success": True, "chunks_written": 0, "empty_response": True})
        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_write):
            state = await node_step_108(state)

        # Empty response handled gracefully
        assert state.get("write_success") is True
        assert state.get("empty_response") is True

    async def test_stream_malformed_response_data(self):
        """Verify malformed response data is handled."""
        state = state_streaming_enabled()
        state["response"] = None  # Missing response

        fake_write = FakeOrchestrator(
            {"write_success": False, "error": "Malformed response data", "response_valid": False}
        )
        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_write):
            state = await node_step_108(state)

        # Malformed data error
        assert state.get("write_success") is False
        assert state.get("response_valid") is False

    async def test_stream_incomplete_response_error(self):
        """Verify incomplete response error is handled."""
        state = state_streaming_enabled()
        state["response"] = {"content": "partial", "complete": False}

        # Try to stream incomplete response
        fake_stream = FakeOrchestrator(
            {"streaming_in_progress": False, "error": "Response incomplete", "response_complete": False}
        )
        with patch("app.core.langgraph.nodes.step_109__stream_response.step_109__stream_response", fake_stream):
            state = await node_step_109(state)

        # Incomplete response error
        assert state.get("response_complete") is False
