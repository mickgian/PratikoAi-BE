"""Test StreamCheck node branching logic."""

import pytest

from app.core.langgraph.nodes.step_104__stream_check import node_step_104
from app.core.langgraph.types import RAGState


@pytest.mark.asyncio
async def test_stream_check_routes_to_stream_setup_when_streaming_requested():
    """Test that StreamCheck routes to StreamSetup when stream=True."""
    state: RAGState = {
        "messages": [{"role": "user", "content": "test"}],
        "request_id": "test-123",
        "session_id": "session-123",
        "request_data": {"stream": True},  # Orchestrator looks for request_data.stream
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_104(state)

    assert "streaming" in result
    assert result["streaming"]["requested"] is True
    assert result["streaming"]["decision"] == "yes"


@pytest.mark.asyncio
async def test_stream_check_routes_to_collect_metrics_when_streaming_not_requested():
    """Test that StreamCheck routes to CollectMetrics when stream=False."""
    state: RAGState = {
        "messages": [{"role": "user", "content": "test"}],
        "request_id": "test-123",
        "session_id": "session-123",
        "streaming_requested": False,
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_104(state)

    assert "streaming" in result
    assert result["streaming"]["requested"] is False
    assert result["streaming"]["decision"] == "no"


@pytest.mark.asyncio
async def test_stream_check_default_when_no_streaming_param():
    """Test that StreamCheck defaults to non-streaming when no param provided."""
    state: RAGState = {
        "messages": [{"role": "user", "content": "test"}],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_104(state)

    assert "streaming" in result
    assert result["streaming"]["requested"] is False
    assert result["streaming"]["decision_source"] == "default"
