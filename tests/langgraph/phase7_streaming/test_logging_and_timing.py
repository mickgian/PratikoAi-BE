"""Test logging and timing for Phase 7 nodes."""

import pytest
from unittest.mock import patch, MagicMock
from app.core.langgraph.nodes.step_104__stream_check import node_step_104
from app.core.langgraph.nodes.step_105__stream_setup import node_step_105
from app.core.langgraph.nodes.step_111__collect_metrics import node_step_111
from app.core.langgraph.types import RAGState


@pytest.mark.asyncio
@patch("app.core.langgraph.nodes.step_104__stream_check.rag_step_log")
@patch("app.core.langgraph.nodes.step_104__stream_check.rag_step_timer")
async def test_stream_check_logs_and_times(mock_timer, mock_log):
    """Test that StreamCheck node calls rag_step_log and rag_step_timer."""
    mock_timer.return_value.__enter__ = MagicMock()
    mock_timer.return_value.__exit__ = MagicMock()

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    await node_step_104(state)

    # Verify timer was called for step 104
    mock_timer.assert_called_with(104)

    # Verify log was called for enter and exit
    assert mock_log.call_count >= 2
    calls = [call[0] for call in mock_log.call_args_list]
    assert any(104 in call and "enter" in call for call in calls)
    assert any(104 in call and "exit" in call for call in calls)


@pytest.mark.asyncio
@patch("app.core.langgraph.nodes.step_105__stream_setup.rag_step_log")
@patch("app.core.langgraph.nodes.step_105__stream_setup.rag_step_timer")
async def test_stream_setup_logs_and_times(mock_timer, mock_log):
    """Test that StreamSetup node calls rag_step_log and rag_step_timer."""
    mock_timer.return_value.__enter__ = MagicMock()
    mock_timer.return_value.__exit__ = MagicMock()

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "streaming_requested": True,
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    await node_step_105(state)

    # Verify timer was called for step 105
    mock_timer.assert_called_with(105)

    # Verify log was called
    assert mock_log.call_count >= 2


@pytest.mark.asyncio
@patch("app.core.langgraph.nodes.step_111__collect_metrics.rag_step_log")
@patch("app.core.langgraph.nodes.step_111__collect_metrics.rag_step_timer")
async def test_collect_metrics_logs_and_times(mock_timer, mock_log):
    """Test that CollectMetrics node calls rag_step_log and rag_step_timer."""
    mock_timer.return_value.__enter__ = MagicMock()
    mock_timer.return_value.__exit__ = MagicMock()

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    await node_step_111(state)

    # Verify timer was called for step 111
    mock_timer.assert_called_with(111)

    # Verify log was called
    assert mock_log.call_count >= 2


@pytest.mark.asyncio
async def test_all_phase7_nodes_have_logging():
    """Test that all Phase 7 nodes have logging instrumentation."""
    from app.core.langgraph import nodes

    phase7_nodes = [
        nodes.node_step_104,
        nodes.node_step_105,
        nodes.node_step_106,
        nodes.node_step_107,
        nodes.node_step_108,
        nodes.node_step_109,
        nodes.node_step_110,
        nodes.node_step_111,
    ]

    for node_func in phase7_nodes:
        # Verify function has rag_step_log and rag_step_timer in source
        import inspect
        source = inspect.getsource(node_func)
        assert "rag_step_log" in source, f"{node_func.__name__} missing rag_step_log"
        assert "rag_step_timer" in source, f"{node_func.__name__} missing rag_step_timer"
