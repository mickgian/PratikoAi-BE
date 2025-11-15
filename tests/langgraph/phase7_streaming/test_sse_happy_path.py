"""Test SSE streaming happy path."""

import pytest

from app.core.langgraph.nodes.step_105__stream_setup import node_step_105
from app.core.langgraph.nodes.step_106__async_gen import node_step_106
from app.core.langgraph.nodes.step_107__single_pass import node_step_107
from app.core.langgraph.nodes.step_108__write_sse import node_step_108
from app.core.langgraph.nodes.step_109__stream_response import node_step_109
from app.core.langgraph.nodes.step_110__send_done import node_step_110
from app.core.langgraph.types import RAGState


@pytest.mark.asyncio
async def test_sse_streaming_full_pipeline():
    """Test complete SSE streaming pipeline from setup to done."""
    # Initial state with streaming requested
    state: RAGState = {
        "messages": [{"role": "user", "content": "test"}],
        "request_id": "test-123",
        "session_id": "session-123",
        "streaming_requested": True,
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    # Step 105: Stream Setup
    state = await node_step_105(state)
    assert "streaming" in state
    assert state["streaming"]["setup"] is True
    assert state["streaming"]["mode"] == "sse"
    assert "sse_headers" in state["streaming"]

    # Step 106: Async Generator
    state = await node_step_106(state)
    assert state["streaming"]["generator_created"] is True

    # Step 107: Single Pass Protection
    state = await node_step_107(state)
    assert state["streaming"]["stream_protected"] is True

    # Step 108: Write SSE
    state = await node_step_108(state)
    assert state["streaming"]["chunks_formatted"] is True

    # Step 109: Stream Response
    state = await node_step_109(state)
    assert state["streaming"]["response_created"] is True

    # Step 110: Send Done
    state = node_step_110(state)
    assert state["streaming"]["done"] is True
    assert "chunks_sent" in state["streaming"]


@pytest.mark.asyncio
async def test_sse_chunks_formatted_incrementally():
    """Test that SSE chunks are properly formatted."""
    state: RAGState = {
        "messages": [{"role": "assistant", "content": "Test response content"}],
        "request_id": "test-123",
        "session_id": "session-123",
        "streaming_requested": True,
        "streaming": {
            "requested": True,
            "setup": True,
            "mode": "sse",
            "generator_created": True,
            "stream_protected": True,
        },
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    # Test SSE formatting
    result = await node_step_108(state)
    assert result["streaming"]["chunks_formatted"] is True
    assert "format_config" in result["streaming"]
