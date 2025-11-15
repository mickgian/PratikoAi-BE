#!/usr/bin/env python3
"""
Regression test for audit roles and wiring detection.

Ensures that Phase 4 nodes remain detectable as ✅ Implemented & Wired
and that the audit pipeline correctly distinguishes between Node and Internal roles.
"""

import os
import re
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.langgraph.wiring_registry import get_wired_nodes_snapshot


class TestAuditRolesAndWiring:
    """Test audit roles and wiring detection."""

    # Phase 4 node numbers that should be wired
    PHASE4_NODES = [59, 62, 64, 66, 67, 68, 69, 70, 72, 73, 74, 75, 79, 80, 81, 82, 83, 99]

    def test_wiring_registry_loads(self):
        """Test that wiring registry loads successfully."""
        registry = get_wired_nodes_snapshot()
        assert isinstance(registry, dict), "Registry should be a dictionary"
        assert len(registry) > 0, "Registry should not be empty"

    def test_phase4_nodes_in_registry(self):
        """Test that all Phase 4 nodes are present in wiring registry."""
        registry = get_wired_nodes_snapshot()

        for node_num in self.PHASE4_NODES:
            assert node_num in registry, f"Phase 4 node {node_num} should be in wiring registry"

            node_data = registry[node_num]
            assert "id" in node_data, f"Node {node_num} should have 'id' field"
            assert "name" in node_data, f"Node {node_num} should have 'name' field"
            assert "incoming" in node_data, f"Node {node_num} should have 'incoming' field"
            assert "outgoing" in node_data, f"Node {node_num} should have 'outgoing' field"

            # Check that name follows expected pattern
            assert (
                node_data["name"] == f"node_step_{node_num}"
            ), f"Node {node_num} name should be 'node_step_{node_num}'"

    def test_phase4_step_files_exist(self):
        """Test that all Phase 4 step documentation files exist."""
        steps_dir = project_root / "docs/architecture/steps"

        for node_num in self.PHASE4_NODES:
            step_files = list(steps_dir.glob(f"STEP-{node_num}-*.md"))
            assert len(step_files) == 1, f"Should find exactly one file for step {node_num}, found {len(step_files)}"

    def test_phase4_roles_are_node(self):
        """Test that all Phase 4 steps have Role: Node."""
        steps_dir = project_root / "docs/architecture/steps"

        for node_num in self.PHASE4_NODES:
            step_files = list(steps_dir.glob(f"STEP-{node_num}-*.md"))
            assert len(step_files) == 1, f"Should find exactly one file for step {node_num}"

            step_file = step_files[0]
            with open(step_file) as f:
                content = f.read()

            # Check for Role: Node pattern
            role_match = re.search(r"- \*\*Role:\*\* (Node|Internal)", content)
            assert role_match, f"Step {node_num} should have Role defined"
            assert (
                role_match.group(1) == "Node"
            ), f"Step {node_num} should have Role: Node, found Role: {role_match.group(1)}"

    def test_phase4_status_is_wired(self):
        """Test that all Phase 4 steps show ✅ Implemented & Wired status."""
        steps_dir = project_root / "docs/architecture/steps"

        for node_num in self.PHASE4_NODES:
            step_files = list(steps_dir.glob(f"STEP-{node_num}-*.md"))
            assert len(step_files) == 1, f"Should find exactly one file for step {node_num}"

            step_file = step_files[0]
            with open(step_file) as f:
                content = f.read()

            # Check for status in AUTO-AUDIT section
            status_match = re.search(r"Role: Node\s*\|\s*Status: ([^|]+?)\s*\|", content)
            assert status_match, f"Step {node_num} should have Status defined in AUTO-AUDIT section"

            status = status_match.group(1).strip()
            assert (
                "✅" in status or "Implemented & Wired" in status
            ), f"Step {node_num} should show ✅ Implemented & Wired status, found: '{status}'"

    def test_wiring_connections_valid(self):
        """Test that wiring connections are valid."""
        registry = get_wired_nodes_snapshot()

        for node_num, node_data in registry.items():
            # Check that incoming connections are valid
            for incoming_node in node_data["incoming"]:
                assert incoming_node in registry, f"Node {node_num} has invalid incoming connection to {incoming_node}"
                # Check reverse connection exists
                assert (
                    node_num in registry[incoming_node]["outgoing"]
                ), f"Node {incoming_node} should have outgoing connection to {node_num}"

            # Check that outgoing connections are valid
            for outgoing_node in node_data["outgoing"]:
                assert outgoing_node in registry, f"Node {node_num} has invalid outgoing connection to {outgoing_node}"
                # Check reverse connection exists
                assert (
                    node_num in registry[outgoing_node]["incoming"]
                ), f"Node {outgoing_node} should have incoming connection from {node_num}"

    def test_node_exports_exist(self):
        """Test that all Phase 4 nodes are exported in __init__.py."""
        init_file = project_root / "app/core/langgraph/nodes/__init__.py"

        with open(init_file) as f:
            content = f.read()

        for node_num in self.PHASE4_NODES:
            # Check import statement
            assert (
                f"from .step_{node_num:03d}" in content or f"node_step_{node_num}" in content
            ), f"Node {node_num} should be imported in __init__.py"

            # Check __all__ export
            assert f'"node_step_{node_num}"' in content, f"Node {node_num} should be exported in __all__ list"

    def test_phase4_hot_path_connectivity(self):
        """Test that Phase 4 hot path is properly connected."""
        registry = get_wired_nodes_snapshot()

        # Define expected hot path: 59 → 62 → (66 | 64 → 67 → 68 → 74 → 75 → 79 → tools → 99)
        expected_connections = {
            59: [62],  # CheckCache → CacheHit
            62: [64, 66],  # CacheHit → (LLMCall | ReturnCached)
            64: [67],  # LLMCall → LLMSuccess
            67: [68, 69],  # LLMSuccess → (CacheResponse | RetryCheck)
            68: [74],  # CacheResponse → TrackUsage
            69: [70],  # RetryCheck → ProdCheck
            70: [72, 73],  # ProdCheck → (FailoverProvider | RetrySameProvider)
            72: [64],  # FailoverProvider → LLMCall
            73: [64],  # RetrySameProvider → LLMCall
            74: [75],  # TrackUsage → ToolCheck
            75: [79],  # ToolCheck → ToolType
            79: [80, 81, 82, 83],  # ToolType → (KB | CCNL | DocIngest | FAQ)
            80: [99],  # KB → ToolResults
            81: [99],  # CCNL → ToolResults
            82: [99],  # DocIngest → ToolResults
            83: [99],  # FAQ → ToolResults
            99: [],  # ToolResults → END
            66: [],  # ReturnCached → END
        }

        for node_num, expected_outgoing in expected_connections.items():
            assert node_num in registry, f"Hot path node {node_num} should be in registry"
            actual_outgoing = registry[node_num]["outgoing"]
            assert set(actual_outgoing) == set(
                expected_outgoing
            ), f"Node {node_num} outgoing connections: expected {expected_outgoing}, got {actual_outgoing}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
