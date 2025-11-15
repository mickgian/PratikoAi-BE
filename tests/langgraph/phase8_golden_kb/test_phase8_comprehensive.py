"""Comprehensive Phase 8 Golden/KB Gates tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.langgraph.nodes.step_020__golden_fast_gate import node_step_20
from app.core.langgraph.nodes.step_024__golden_lookup import node_step_24
from app.core.langgraph.nodes.step_025__golden_hit import node_step_25
from app.core.langgraph.nodes.step_026__kb_context_check import node_step_26
from app.core.langgraph.nodes.step_027__kb_delta import node_step_27
from app.core.langgraph.nodes.step_028__serve_golden import node_step_28
from app.core.langgraph.nodes.step_030__return_complete import node_step_30
from app.core.langgraph.types import RAGState


# Test 1: Golden Fast Gate - Eligible vs Not Eligible
@pytest.mark.asyncio
@patch("app.orchestrators.golden.step_20__golden_fast_gate", new_callable=AsyncMock)
async def test_golden_fast_gate_eligible(mock_orch):
    """Test golden fast gate with eligible query."""
    mock_orch.return_value = {"golden_eligible": True}

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_20(state)

    # Verify state structure (additive)
    assert "golden" in result
    assert "decisions" in result
    assert "eligible" in result["golden"]
    assert "golden_eligible" in result["decisions"]


@pytest.mark.asyncio
@patch("app.orchestrators.golden.step_20__golden_fast_gate", new_callable=AsyncMock)
async def test_golden_fast_gate_not_eligible(mock_orch):
    """Test golden fast gate with ineligible query."""
    mock_orch.return_value = {"golden_eligible": False}

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_20(state)

    assert result["golden"]["eligible"] is False
    assert result["decisions"]["golden_eligible"] is False


# Test 2: Golden Lookup and Hit - Hit / No-Hit Branch
@pytest.mark.asyncio
@patch("app.orchestrators.preflight.step_24__golden_lookup", new_callable=AsyncMock)
async def test_golden_lookup_match_found(mock_orch):
    """Test golden lookup with match found."""
    mock_orch.return_value = {"match_found": True, "lookup": {"faq_id": "faq-123", "similarity_score": 0.95}}

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_24(state)

    # Verify state structure (additive)
    assert "golden" in result
    assert "match_found" in result["golden"]
    assert "lookup" in result["golden"]


@pytest.mark.asyncio
@patch("app.orchestrators.golden.step_25__golden_hit", new_callable=AsyncMock)
async def test_golden_hit_high_confidence(mock_orch):
    """Test golden hit decision with high confidence."""
    mock_orch.return_value = {"high_confidence_match": True, "similarity_score": 0.95}

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_25(state)

    # Verify state structure (additive)
    assert "golden" in result
    assert "hit" in result["golden"]
    assert "decisions" in result
    assert "golden_hit" in result["decisions"]


@pytest.mark.asyncio
@patch("app.orchestrators.golden.step_25__golden_hit", new_callable=AsyncMock)
async def test_golden_hit_low_confidence(mock_orch):
    """Test golden hit decision with low confidence."""
    mock_orch.return_value = {"high_confidence_match": False, "similarity_score": 0.75}

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_25(state)

    assert result["golden"]["hit"] is False
    assert result["decisions"]["golden_hit"] is False


# Test 3: KB Context and Delta
@pytest.mark.asyncio
@patch("app.orchestrators.kb.step_26__kbcontext_check", new_callable=AsyncMock)
async def test_kb_context_with_recent_changes(mock_orch):
    """Test KB context check with recent changes."""
    mock_orch.return_value = {
        "kb_docs": [{"doc_id": "kb-1", "title": "Update"}],
        "kb_epoch": "2025-01-01",
        "has_recent_changes": True,
    }

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_26(state)

    # Verify state structure (additive)
    assert "kb" in result
    assert "has_recent_changes" in result["kb"]
    assert "docs" in result["kb"]


@pytest.mark.asyncio
@patch("app.orchestrators.golden.step_27__kbdelta", new_callable=AsyncMock)
async def test_kb_delta_true(mock_orch):
    """Test KB delta with newer content."""
    mock_orch.return_value = {"kb_has_delta": True, "conflict_reason": "newer_timestamp"}

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_27(state)

    # Verify state structure (additive)
    assert "kb" in result
    assert "delta" in result["kb"]
    assert "decisions" in result
    assert "kb_required" in result["decisions"]


@pytest.mark.asyncio
@patch("app.orchestrators.golden.step_27__kbdelta", new_callable=AsyncMock)
async def test_kb_delta_false(mock_orch):
    """Test KB delta with no conflicts."""
    mock_orch.return_value = {"kb_has_delta": False, "conflict_reason": None}

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_27(state)

    assert result["kb"]["delta"] is False
    assert result["decisions"]["kb_required"] is False


# Test 4: Serve Golden and Return
@pytest.mark.asyncio
@patch("app.orchestrators.golden.step_28__serve_golden", new_callable=AsyncMock)
async def test_serve_golden_with_citations(mock_orch):
    """Test serving golden answer with citations."""
    mock_orch.return_value = {
        "answer": {"faq_id": "faq-123", "text": "Golden answer text", "citations": ["source1", "source2"]}
    }

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_28(state)

    # Verify state structure (additive)
    assert "golden" in result
    assert "served" in result["golden"]
    assert "answer" in result["golden"]


@pytest.mark.asyncio
@patch("app.orchestrators.response.step_30__return_complete", new_callable=AsyncMock)
async def test_return_complete(mock_orch):
    """Test return complete with response."""
    mock_orch.return_value = {"response": {"message": "Complete response"}, "complete": True}

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    result = await node_step_30(state)

    assert result["complete"] is True
    assert "response" in result


# Test 5: State Integrity - Additive Merge
@pytest.mark.asyncio
@patch("app.orchestrators.golden.step_20__golden_fast_gate", new_callable=AsyncMock)
async def test_state_integrity_no_key_loss(mock_orch):
    """Test that Phase 8 nodes don't lose existing state keys."""
    mock_orch.return_value = {"golden_eligible": True}

    state: RAGState = {
        "messages": [{"role": "user", "content": "test"}],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {"existing_metric": 123},
        "processing_stage": "init",
        "node_history": ["step_1"],
        "custom_key": "should_not_be_lost",
    }

    original_keys = set(state.keys())
    result = await node_step_20(state)

    # Verify no keys were lost
    assert original_keys.issubset(set(result.keys()))
    # Verify new keys were added
    assert "golden" in result
    assert "decisions" in result


# Test 6: Metrics and Logging Smoke Test
@pytest.mark.asyncio
@patch("app.core.langgraph.nodes.step_020__golden_fast_gate.rag_step_log")
@patch("app.core.langgraph.nodes.step_020__golden_fast_gate.rag_step_timer")
@patch("app.orchestrators.golden.step_20__golden_fast_gate", new_callable=AsyncMock)
async def test_golden_fast_gate_logs_and_times(mock_orch, mock_timer, mock_log):
    """Test that nodes call rag_step_log and rag_step_timer."""
    mock_timer.return_value.__enter__ = MagicMock()
    mock_timer.return_value.__exit__ = MagicMock()
    mock_orch.return_value = {"golden_eligible": True}

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    await node_step_20(state)

    # Verify timer was called for step 20
    mock_timer.assert_called_with(20)

    # Verify log was called for enter and exit
    assert mock_log.call_count >= 2


@pytest.mark.asyncio
@patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_log")
@patch("app.orchestrators.golden.step_28__serve_golden", new_callable=AsyncMock)
async def test_serve_golden_logs_metric(mock_orch, mock_log):
    """Test that ServeGolden logs golden_hit metric."""
    mock_orch.return_value = {"answer": {"faq_id": "faq-123", "text": "answer"}}

    state: RAGState = {
        "messages": [],
        "request_id": "test-123",
        "session_id": "session-123",
        "metrics": {},
        "processing_stage": "init",
        "node_history": [],
    }

    await node_step_28(state)

    # Verify rag_step_log was called (includes metric logging)
    assert mock_log.call_count >= 2  # At least enter and exit logs
    # Check that metric logging occurred
    call_args = [str(call) for call in mock_log.call_args_list]
    has_metric_call = any("metric" in arg for arg in call_args)
    assert has_metric_call


# Test 7: Wiring Registry Phase 8
def test_phase8_wiring_registry():
    """Test that Phase 8 nodes are registered with correct edges."""
    from app.core.langgraph.wiring_registry import PHASE8_WIRED_NODES

    # Verify all 7 Phase 8 nodes are registered
    expected_steps = [20, 24, 25, 26, 27, 28, 30]
    assert all(step in PHASE8_WIRED_NODES for step in expected_steps)

    # Verify edges
    assert 24 in PHASE8_WIRED_NODES[20]["outgoing"]
    assert 25 in PHASE8_WIRED_NODES[24]["outgoing"]
    assert 26 in PHASE8_WIRED_NODES[25]["outgoing"]
    assert 27 in PHASE8_WIRED_NODES[26]["outgoing"]
    assert 28 in PHASE8_WIRED_NODES[27]["outgoing"]
    assert 30 in PHASE8_WIRED_NODES[28]["outgoing"]

    # Verify node IDs
    assert PHASE8_WIRED_NODES[20]["name"] == "node_step_20"
    assert PHASE8_WIRED_NODES[24]["name"] == "node_step_24"
    assert PHASE8_WIRED_NODES[25]["name"] == "node_step_25"
    assert PHASE8_WIRED_NODES[26]["name"] == "node_step_26"
    assert PHASE8_WIRED_NODES[27]["name"] == "node_step_27"
    assert PHASE8_WIRED_NODES[28]["name"] == "node_step_28"
    assert PHASE8_WIRED_NODES[30]["name"] == "node_step_30"


def test_phase8_registry_initialized():
    """Test that Phase 8 registry is initialized in graph."""
    # Import graph first to trigger registry initialization
    import app.core.langgraph.graph
    from app.core.langgraph.wiring_registry import get_wired_nodes_snapshot

    registry = get_wired_nodes_snapshot()

    # Verify Phase 8 nodes are in global registry
    phase8_nodes = [20, 24, 25, 26, 27, 28, 30]
    for node in phase8_nodes:
        assert node in registry, f"Node {node} not in wiring registry"
