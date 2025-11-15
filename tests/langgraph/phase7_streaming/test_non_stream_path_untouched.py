"""Test non-streaming path remains unchanged."""

import pytest

from app.core.langgraph.nodes.step_104__stream_check import node_step_104
from app.core.langgraph.nodes.step_111__collect_metrics import node_step_111
from app.core.langgraph.nodes.step_112__end import node_step_112
from app.core.langgraph.types import RAGState


@pytest.mark.asyncio
async def test_non_stream_path_skips_streaming_nodes():
    """Test that non-streaming requests skip steps 105-110."""
    # Initial state without streaming
    state: RAGState = {
        "messages": [{"role": "user", "content": "test"}],
        "request_id": "test-123",
        "session_id": "session-123",
        "streaming_requested": False,
        "llm_response": {"content": "Test response"},
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    # Step 104: StreamCheck (should route to CollectMetrics)
    state = await node_step_104(state)
    assert state["streaming"]["requested"] is False

    # Skip steps 105-110 for non-streaming path

    # Step 111: CollectMetrics (should work without streaming state)
    state = await node_step_111(state)
    assert "metrics" in state
    # Metrics should be populated regardless of streaming

    # Step 112: End
    state = await node_step_112(state)
    # Should complete successfully without streaming nodes


@pytest.mark.asyncio
async def test_non_stream_produces_identical_final_response():
    """Test that non-streaming path produces same final response structure."""
    # Non-streaming state
    state_no_stream: RAGState = {
        "messages": [{"role": "user", "content": "test"}],
        "request_id": "test-123",
        "session_id": "session-123",
        "streaming_requested": False,
        "llm_response": {"content": "Test response", "role": "assistant"},
        "final_response": {"content": "Test response"},
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    # Process through non-streaming path
    state_no_stream = await node_step_104(state_no_stream)
    state_no_stream = await node_step_111(state_no_stream)
    state_no_stream = await node_step_112(state_no_stream)

    # Verify final_response is unchanged
    assert "final_response" in state_no_stream
    assert state_no_stream["final_response"]["content"] == "Test response"


@pytest.mark.asyncio
async def test_non_stream_path_backwards_compatible():
    """Test that non-streaming behavior is backward compatible."""
    # Legacy state without streaming field
    state: RAGState = {
        "messages": [{"role": "user", "content": "test"}],
        "request_id": "test-123",
        "session_id": "session-123",
        "final_response": {"content": "Legacy response"},
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    # Should handle missing streaming_requested gracefully
    state = await node_step_104(state)
    assert state["streaming"]["requested"] is False  # Default

    # Continue through non-streaming path
    state = await node_step_111(state)
    state = await node_step_112(state)

    # Legacy final_response should be preserved
    assert state["final_response"]["content"] == "Legacy response"
