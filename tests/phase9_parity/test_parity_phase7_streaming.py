"""
Parity tests for Phase 7: Streaming Response Lane.

Verifies that streaming nodes correctly delegate to orchestrators
and handle both streaming and non-streaming paths.
"""

import pytest
from unittest.mock import patch

from tests.common.fixtures_state import make_state, state_streaming_enabled
from tests.common.fakes import (
    fake_stream_setup_orch,
    FakeOrchestrator,
    FakeSSEWriter,
)
from app.core.langgraph.nodes.step_104__stream_check import node_step_104
from app.core.langgraph.nodes.step_105__stream_setup import node_step_105
from app.core.langgraph.nodes.step_108__write_sse import node_step_108


@pytest.mark.parity
@pytest.mark.phase7
class TestPhase7StreamCheckParity:
    """Test stream check node wrapper parity."""

    async def test_stream_check_enabled_delegates(self):
        """Verify stream check with streaming enabled delegates correctly."""
        state = make_state(
            streaming={"requested": True, "enabled": True}
        )
        fake_orch = FakeOrchestrator({
            "streaming_enabled": True,
            "stream_requested": True
        })

        with patch("app.core.langgraph.nodes.step_104__stream_check.step_104__stream_check", fake_orch):
            result = await node_step_104(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify streaming enabled
        assert result.get("streaming_enabled") is True

    async def test_stream_check_disabled_delegates(self):
        """Verify stream check with streaming disabled delegates correctly."""
        state = make_state(
            streaming={"requested": False, "enabled": False}
        )
        fake_orch = FakeOrchestrator({
            "streaming_enabled": False,
            "stream_requested": False
        })

        with patch("app.core.langgraph.nodes.step_104__stream_check.step_104__stream_check", fake_orch):
            result = await node_step_104(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify streaming disabled
        assert result.get("streaming_enabled") is False

    async def test_stream_check_preserves_response(self):
        """Verify stream check doesn't lose response data."""
        state = make_state(
            streaming={"requested": True},
            response={"content": "test response", "complete": True}
        )
        fake_orch = FakeOrchestrator({
            "streaming_enabled": True
        })

        with patch("app.core.langgraph.nodes.step_104__stream_check.step_104__stream_check", fake_orch):
            result = await node_step_104(state)

        # Response preserved
        assert result.get("response", {}).get("content") == "test response"


@pytest.mark.parity
@pytest.mark.phase7
class TestPhase7StreamSetupParity:
    """Test stream setup node wrapper parity."""

    async def test_stream_setup_delegates_correctly(self):
        """Verify stream setup delegates to orchestrator."""
        state = state_streaming_enabled()
        fake_orch = fake_stream_setup_orch()

        with patch("app.core.langgraph.nodes.step_105__stream_setup.step_105__stream_setup", fake_orch):
            result = await node_step_105(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify setup completed
        assert result.get("sse_ready") is True
        assert result.get("generator_created") is True

    async def test_stream_setup_preserves_streaming_config(self):
        """Verify stream setup preserves streaming configuration."""
        state = state_streaming_enabled()
        original_streaming = state.get("streaming")
        fake_orch = fake_stream_setup_orch()

        with patch("app.core.langgraph.nodes.step_105__stream_setup.step_105__stream_setup", fake_orch):
            result = await node_step_105(state)

        # Streaming config preserved
        assert result.get("streaming", {}).get("enabled") == original_streaming.get("enabled")


@pytest.mark.parity
@pytest.mark.phase7
class TestPhase7SSEWriteParity:
    """Test SSE write node wrapper parity."""

    async def test_sse_write_delegates_correctly(self):
        """Verify SSE write delegates to orchestrator."""
        state = state_streaming_enabled()
        state["response"] = {"content": "chunk1 chunk2 chunk3", "complete": True}

        fake_orch = FakeOrchestrator({
            "chunks_written": 3,
            "write_success": True
        })

        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_orch):
            result = await node_step_108(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify write success
        assert result.get("write_success") is True
        assert result.get("chunks_written") == 3

    async def test_sse_write_preserves_response_metadata(self):
        """Verify SSE write preserves response metadata."""
        state = state_streaming_enabled()
        state["response"] = {
            "content": "test",
            "complete": True,
            "metadata": {"model": "claude-3-5-sonnet-20241022"}
        }

        fake_orch = FakeOrchestrator({
            "chunks_written": 1,
            "write_success": True
        })

        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_orch):
            result = await node_step_108(state)

        # Metadata preserved
        assert result.get("response", {}).get("metadata", {}).get("model") == "claude-3-5-sonnet-20241022"

    async def test_non_streaming_path_delegates(self):
        """Verify non-streaming path delegates correctly."""
        state = make_state(
            streaming={"enabled": False},
            response={"content": "complete response", "complete": True}
        )

        fake_orch = FakeOrchestrator({
            "streaming_enabled": False,
            "response_complete": True
        })

        # For non-streaming, step_107 is used
        with patch("app.core.langgraph.nodes.step_107__single_pass.step_107__single_pass", fake_orch):
            from app.core.langgraph.nodes.step_107__single_pass import node_step_107
            result = await node_step_107(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify non-streaming response
        assert result.get("response_complete") is True
