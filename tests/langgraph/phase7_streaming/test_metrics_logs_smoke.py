"""Smoke tests for Phase 7 streaming metrics and logs."""

import pytest

from app.core.langgraph.nodes.step_104__stream_check import node_step_104
from app.core.langgraph.nodes.step_111__collect_metrics import node_step_111
from app.core.langgraph.nodes.step_112__end import node_step_112
from app.core.langgraph.types import RAGState


@pytest.mark.asyncio
async def test_phase7_nodes_dont_crash_with_minimal_state():
    """Smoke test: Phase 7 nodes should not crash with minimal state."""
    minimal_state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    # These should not raise exceptions
    state = await node_step_104(minimal_state.copy())
    assert "streaming" in state

    state = await node_step_111(minimal_state.copy())
    assert "metrics" in state

    state = await node_step_112(minimal_state.copy())
    # Should complete without error


@pytest.mark.asyncio
async def test_streaming_state_structure():
    """Test that streaming state dict has expected structure."""
    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "streaming_requested": True,
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_104(state)

    # Verify streaming dict structure
    assert isinstance(result["streaming"], dict)
    assert "requested" in result["streaming"]
    assert "decision" in result["streaming"]
    assert isinstance(result["streaming"]["requested"], bool)


@pytest.mark.asyncio
async def test_metrics_collected_in_step_111():
    """Test that CollectMetrics populates metrics dict."""
    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "user_id": "user-456",
        "cache_hit": False,
        "provider": "openai",
        "model": "gpt-4",
        "total_tokens": 100,
        "cost": 0.05,
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_111(state)

    # Verify metrics dict is populated
    assert "metrics" in result
    assert isinstance(result["metrics"], dict)


@pytest.mark.asyncio
async def test_client_disconnect_graceful_handling():
    """Test that nodes handle simulated disconnect gracefully (no crash)."""
    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "streaming": {
            "requested": True,
            "client_disconnected": True,  # Simulate disconnect
        },
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    # Nodes should not crash even with disconnect flag
    result = await node_step_111(state)
    assert "metrics" in result


@pytest.mark.asyncio
async def test_backpressure_flag_handling():
    """Test that streaming nodes handle backpressure flag without crashing."""
    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "streaming": {
            "requested": True,
            "backpressure": True,  # Simulate backpressure
        },
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    # Should not crash
    result = await node_step_104(state)
    assert "streaming" in result


@pytest.mark.asyncio
async def test_phase7_nodes_preserve_state():
    """Test that Phase 7 nodes preserve existing state fields."""
    state: RAGState = {
        "messages": [{"role": "user", "content": "test"}],
        "request_id": "test-123",
        "session_id": "session-123",
        "user_id": "user-456",
        "final_response": {"content": "existing response"},
        "llm_response": {"role": "assistant", "content": "test"},
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    # Process through Phase 7 nodes
    result = await node_step_104(state)
    result = await node_step_111(result)
    result = await node_step_112(result)

    # Verify original fields are preserved
    assert result["request_id"] == "test-123"
    assert result["session_id"] == "session-123"
    assert result["user_id"] == "user-456"
    assert "final_response" in result
    assert result["messages"][0]["content"] == "test"
