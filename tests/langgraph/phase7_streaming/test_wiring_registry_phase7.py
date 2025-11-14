"""Test Phase 7 wiring registry."""

import pytest
from app.core.langgraph.wiring_registry import (
    PHASE7_WIRED_NODES,
    WIRED_NODES,
    get_wired_nodes_snapshot,
)

# Import graph to trigger initialization
import app.core.langgraph.graph  # noqa: F401


def test_phase7_nodes_registered():
    """Test that all Phase 7 nodes are registered in wiring registry."""
    expected_nodes = [104, 105, 106, 107, 108, 109, 110, 111, 112]

    for node_id in expected_nodes:
        assert node_id in PHASE7_WIRED_NODES, f"Node {node_id} missing from Phase 7 registry"


def test_phase7_node_metadata():
    """Test that Phase 7 nodes have correct metadata."""
    # Node 104: StreamCheck
    assert PHASE7_WIRED_NODES[104]["id"] == "RAG.streaming.streaming.requested"
    assert PHASE7_WIRED_NODES[104]["name"] == "node_step_104"
    assert 105 in PHASE7_WIRED_NODES[104]["outgoing"]
    assert 111 in PHASE7_WIRED_NODES[104]["outgoing"]

    # Node 105: StreamSetup
    assert PHASE7_WIRED_NODES[105]["id"] == "RAG.streaming.chatbotcontroller.chat.stream.setup.sse"
    assert 104 in PHASE7_WIRED_NODES[105]["incoming"]
    assert 106 in PHASE7_WIRED_NODES[105]["outgoing"]

    # Node 111: CollectMetrics
    assert PHASE7_WIRED_NODES[111]["id"] == "RAG.metrics.collect.usage.metrics"
    assert 104 in PHASE7_WIRED_NODES[111]["incoming"]
    assert 110 in PHASE7_WIRED_NODES[111]["incoming"]
    assert 112 in PHASE7_WIRED_NODES[111]["outgoing"]

    # Node 112: End
    assert PHASE7_WIRED_NODES[112]["id"] == "RAG.response.chatbotcontroller.chat.return.response"
    assert 111 in PHASE7_WIRED_NODES[112]["incoming"]
    assert PHASE7_WIRED_NODES[112]["outgoing"] == []


def test_phase7_streaming_path_edges():
    """Test streaming path has correct sequential edges."""
    streaming_path = [105, 106, 107, 108, 109, 110]

    for i in range(len(streaming_path) - 1):
        current_node = streaming_path[i]
        next_node = streaming_path[i + 1]

        assert next_node in PHASE7_WIRED_NODES[current_node]["outgoing"], \
            f"Edge missing: {current_node} → {next_node}"
        assert current_node in PHASE7_WIRED_NODES[next_node]["incoming"], \
            f"Reverse edge missing: {current_node} ← {next_node}"


def test_phase7_nodes_in_global_registry():
    """Test that Phase 7 nodes are visible in global wiring registry."""
    snapshot = get_wired_nodes_snapshot()

    # Check that Phase 7 nodes are present
    expected_nodes = [104, 105, 106, 107, 108, 109, 110, 111, 112]
    for node_id in expected_nodes:
        assert node_id in snapshot, f"Node {node_id} not in global wiring registry"


def test_phase7_branch_convergence():
    """Test that both streaming and non-streaming paths converge at CollectMetrics."""
    # Both paths should lead to node 111
    assert 111 in PHASE7_WIRED_NODES[104]["outgoing"]  # Direct non-streaming path
    assert 111 in PHASE7_WIRED_NODES[110]["outgoing"]  # End of streaming path

    # Node 111 should have both paths as incoming
    assert 104 in PHASE7_WIRED_NODES[111]["incoming"]
    assert 110 in PHASE7_WIRED_NODES[111]["incoming"]
