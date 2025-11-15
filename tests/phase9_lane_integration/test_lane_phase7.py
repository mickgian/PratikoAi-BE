"""
Lane integration tests for Phase 7: Streaming Response Lane.

Tests end-to-end flow through streaming check → setup → SSE write paths.
"""

from unittest.mock import patch

import pytest

from app.core.langgraph.nodes.step_104__stream_check import node_step_104
from app.core.langgraph.nodes.step_105__stream_setup import node_step_105
from app.core.langgraph.nodes.step_107__single_pass import node_step_107
from app.core.langgraph.nodes.step_108__write_sse import node_step_108
from tests.common.fakes import (
    FakeOrchestrator,
    fake_stream_setup_orch,
)
from tests.common.fixtures_state import make_state, state_streaming_enabled


@pytest.mark.lane
@pytest.mark.phase7
class TestPhase7StreamingEnabledPath:
    """Test streaming enabled flow."""

    async def test_streaming_requested_flows_to_setup(self):
        """Verify streaming requested flows to stream setup."""
        state = make_state(
            streaming={"requested": True, "enabled": False}, response={"content": "Test response", "complete": True}
        )

        # Step 104: Stream check (ENABLED)
        fake_check = FakeOrchestrator({"streaming_enabled": True, "stream_requested": True})
        with patch("app.core.langgraph.nodes.step_104__stream_check.step_104__stream_check", fake_check):
            state = await node_step_104(state)

        assert state.get("streaming_enabled") is True

        # Step 105: Stream setup
        with patch("app.core.langgraph.nodes.step_105__stream_setup.step_105__stream_setup", fake_stream_setup_orch()):
            state = await node_step_105(state)

        # Setup completed
        assert state.get("sse_ready") is True
        assert state.get("generator_created") is True

    async def test_streaming_writes_chunks_via_sse(self):
        """Verify streaming writes response chunks via SSE."""
        state = state_streaming_enabled()
        state["response"] = {"content": "chunk1 chunk2 chunk3", "complete": True}

        # Setup streaming
        with patch("app.core.langgraph.nodes.step_105__stream_setup.step_105__stream_setup", fake_stream_setup_orch()):
            state = await node_step_105(state)

        # Step 108: Write SSE chunks
        fake_write = FakeOrchestrator({"chunks_written": 3, "write_success": True})
        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_write):
            state = await node_step_108(state)

        # Chunks written
        assert state.get("write_success") is True
        assert state.get("chunks_written") == 3

    async def test_streaming_completes_with_done_signal(self):
        """Verify streaming completes with done signal."""
        state = state_streaming_enabled()
        state["response"] = {"content": "Final response", "complete": True}

        # Write chunks
        fake_write = FakeOrchestrator({"chunks_written": 1, "write_success": True})
        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_write):
            state = await node_step_108(state)

        # Step 110: Send done signal
        fake_done = FakeOrchestrator({"done_sent": True, "stream_complete": True})
        with patch("app.core.langgraph.nodes.step_110__send_done.step_110__send_done", fake_done):
            from app.core.langgraph.nodes.step_110__send_done import node_step_110

            state = await node_step_110(state)

        # Done signal sent
        assert state.get("done_sent") is True
        assert state.get("stream_complete") is True


@pytest.mark.lane
@pytest.mark.phase7
class TestPhase7NonStreamingPath:
    """Test non-streaming (single-pass) flow."""

    async def test_non_streaming_returns_complete_response(self):
        """Verify non-streaming returns complete response immediately."""
        state = make_state(
            streaming={"requested": False, "enabled": False},
            response={"content": "Complete response text", "complete": True},
        )

        # Step 104: Stream check (DISABLED)
        fake_check = FakeOrchestrator({"streaming_enabled": False, "stream_requested": False})
        with patch("app.core.langgraph.nodes.step_104__stream_check.step_104__stream_check", fake_check):
            state = await node_step_104(state)

        assert state.get("streaming_enabled") is False

        # Step 107: Single-pass response (non-streaming)
        fake_single = FakeOrchestrator({"response_complete": True, "response_sent": True})
        with patch("app.core.langgraph.nodes.step_107__single_pass.step_107__single_pass", fake_single):
            state = await node_step_107(state)

        # Complete response returned
        assert state.get("response_complete") is True
        assert state.get("response_sent") is True

    async def test_non_streaming_skips_sse_setup(self):
        """Verify non-streaming skips SSE setup."""
        state = make_state(
            streaming={"requested": False, "enabled": False}, response={"content": "Response", "complete": True}
        )

        # Stream check disabled
        fake_check = FakeOrchestrator({"streaming_enabled": False})
        with patch("app.core.langgraph.nodes.step_104__stream_check.step_104__stream_check", fake_check):
            state = await node_step_104(state)

        # Should not have SSE setup flags
        assert state.get("streaming_enabled") is False
        # In real flow, routing would skip steps 105-110


@pytest.mark.lane
@pytest.mark.phase7
class TestPhase7StreamingWithLLMResponse:
    """Test streaming integrated with LLM response."""

    async def test_llm_response_flows_to_streaming(self):
        """Verify LLM response flows to streaming when requested."""
        state = make_state(
            streaming={"requested": True, "enabled": False},
            llm={
                "success": True,
                "response": {"content": "LLM generated response text", "model": "claude-3-5-sonnet-20241022"},
            },
        )

        # Enable streaming
        fake_check = FakeOrchestrator({"streaming_enabled": True})
        with patch("app.core.langgraph.nodes.step_104__stream_check.step_104__stream_check", fake_check):
            state = await node_step_104(state)

        # Setup streaming
        with patch("app.core.langgraph.nodes.step_105__stream_setup.step_105__stream_setup", fake_stream_setup_orch()):
            state = await node_step_105(state)

        # LLM response preserved
        assert state["llm"]["success"] is True
        assert state["llm"]["response"]["content"]

    async def test_streaming_preserves_llm_metadata(self):
        """Verify streaming preserves LLM metadata."""
        state = state_streaming_enabled()
        state["llm"] = {
            "success": True,
            "response": {
                "content": "Response",
                "model": "claude-3-5-sonnet-20241022",
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
        }

        # Write via streaming
        fake_write = FakeOrchestrator({"chunks_written": 1, "write_success": True})
        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_write):
            state = await node_step_108(state)

        # LLM metadata preserved
        assert state["llm"]["response"]["usage"]["input_tokens"] == 100


@pytest.mark.lane
@pytest.mark.phase7
class TestPhase7StreamingGenerator:
    """Test async generator streaming path."""

    async def test_async_generator_creates_chunks(self):
        """Verify async generator creates response chunks."""
        state = state_streaming_enabled()
        state["response"] = {"content": "word1 word2 word3", "complete": False}

        # Step 106: Create async generator
        fake_gen = FakeOrchestrator({"generator_ready": True, "chunk_count": 3})
        with patch("app.core.langgraph.nodes.step_106__async_gen.step_106__async_gen", fake_gen):
            from app.core.langgraph.nodes.step_106__async_gen import node_step_106

            state = await node_step_106(state)

        # Generator ready
        assert state.get("generator_ready") is True
        assert state.get("chunk_count") == 3

    async def test_stream_response_sends_incrementally(self):
        """Verify stream response sends chunks incrementally."""
        state = state_streaming_enabled()

        # Step 109: Stream response
        fake_stream = FakeOrchestrator({"streaming_in_progress": True, "chunks_sent": 5})
        with patch("app.core.langgraph.nodes.step_109__stream_response.step_109__stream_response", fake_stream):
            from app.core.langgraph.nodes.step_109__stream_response import node_step_109

            state = await node_step_109(state)

        # Streaming in progress
        assert state.get("streaming_in_progress") is True
        assert state.get("chunks_sent") == 5
