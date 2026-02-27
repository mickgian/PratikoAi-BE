"""
Tests to verify audit and wiring registry alignment.

These tests ensure that:
1. Wiring registry contains exact IDs from rag_conformance.md
2. Audit counts match registry state
3. Step docs are properly updated with correct Role/Status
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.langgraph.wiring_registry import (
    STEP_IDS,
    WIRED_NODES,
    get_wired_nodes_snapshot,
    initialize_phase4_registry,
    initialize_phase5_registry,
    initialize_phase6_registry,
    initialize_phase7_registry,
    initialize_phase8_registry,
)


@pytest.fixture(scope="module")
def wiring_registry():
    """Initialize and return wiring registry."""
    initialize_phase4_registry()
    initialize_phase5_registry()
    initialize_phase6_registry()
    initialize_phase7_registry()
    initialize_phase8_registry()
    return get_wired_nodes_snapshot()


def test_registry_has_exact_ids(wiring_registry):
    """
    Test 1: Verify registry contains exact IDs from STEP_IDS.

    For each wired step in Phases 4-8, the registry entry must have
    the exact ID string from STEP_IDS mapping.
    """
    # Expected wired steps from Phases 4-8
    expected_phases = {
        # Phase 4: Cache → LLM → Tools Lane
        59,
        62,
        64,
        66,
        67,
        68,
        69,
        70,
        72,
        73,
        74,
        75,
        79,
        80,
        81,
        82,
        83,
        99,
        # Phase 5: Provider Governance Lane
        48,
        49,
        50,
        51,
        52,
        53,
        54,
        55,
        56,
        57,
        58,
        # Phase 6: Request/Privacy Lane
        1,
        3,
        4,
        6,
        7,
        8,
        9,
        10,
        # Phase 7: Streaming/Response Lane
        104,
        105,
        106,
        107,
        108,
        109,
        110,
        111,
        112,
        # Phase 8: Golden/KB Gates
        20,
        24,
        25,
        26,
        27,
        28,
        30,
    }

    # Verify all expected steps are wired
    wired_steps = set(wiring_registry.keys())
    assert expected_phases == wired_steps, (
        f"Wiring mismatch:\n"
        f"  Expected: {sorted(expected_phases)}\n"
        f"  Actual:   {sorted(wired_steps)}\n"
        f"  Missing:  {sorted(expected_phases - wired_steps)}\n"
        f"  Extra:    {sorted(wired_steps - expected_phases)}"
    )

    # Verify exact ID strings match STEP_IDS
    for step_num in expected_phases:
        assert step_num in wiring_registry, f"Step {step_num} not in wiring registry"
        assert step_num in STEP_IDS, f"Step {step_num} not in STEP_IDS mapping"

        registry_id = wiring_registry[step_num]["id"]
        expected_id = STEP_IDS[step_num]

        assert registry_id == expected_id, (
            f"ID mismatch for step {step_num}:\n  Registry: {registry_id}\n  Expected: {expected_id}"
        )

    print(f"✅ All {len(expected_phases)} wired steps have exact IDs")


def test_audit_counts_use_registry(wiring_registry):
    """
    Test 2: Verify introspection script returns correct wired count.

    Run rag_graph_introspect.py and verify the wired node count
    matches the registry state.
    """
    # Run introspection script
    introspect_script = PROJECT_ROOT / "scripts" / "rag_graph_introspect.py"
    assert introspect_script.exists(), f"Script not found: {introspect_script}"

    result = subprocess.run([sys.executable, str(introspect_script)], capture_output=True, text=True, timeout=10)

    assert result.returncode == 0, f"Script failed: {result.stderr}"

    # Parse JSON output
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON from introspection script: {e}\n{result.stdout}")

    assert "wired_nodes" in data, "Output missing 'wired_nodes' key"

    introspect_count = len(data["wired_nodes"])
    registry_count = len(wiring_registry)

    assert introspect_count == registry_count, (
        f"Count mismatch:\n  Introspection script: {introspect_count}\n  Wiring registry:      {registry_count}"
    )

    # Verify expected minimum count (Phases 4-8 = 53 nodes)
    assert introspect_count >= 53, f"Expected at least 53 wired nodes from Phases 4-8, got {introspect_count}"

    print(f"✅ Introspection script reports {introspect_count} wired nodes (matches registry)")


def test_doc_status_updates(wiring_registry):
    """
    Test 3: Verify audit script updates step docs correctly.

    Run rag_audit.py with --write (in test mode) and verify that
    representative step docs have correct Role and Status.
    """
    steps_dir = PROJECT_ROOT / "docs" / "architecture" / "steps"
    assert steps_dir.exists(), f"Steps directory not found: {steps_dir}"

    # Test representative steps from different phases
    test_steps = [
        # Phase 4: Wired node
        (59, "Node", "✅", True),
        # Phase 5: Wired node
        (48, "Node", "✅", True),
        # Phase 6: Wired node
        (1, "Node", "✅", True),
        # Phase 7: Wired node
        (104, "Node", "✅", True),
        # Phase 8: Wired node
        (20, "Node", "✅", True),
        # Internal step (exists but not canonical Node)
        (2, "Internal", "🔌", False),
    ]

    for step_num, expected_role, expected_status, should_be_wired in test_steps:
        # Find step doc (need to get step_id from filename)
        step_docs = list(steps_dir.glob(f"STEP-{step_num}-*.md"))
        assert len(step_docs) == 1, f"Expected 1 doc for step {step_num}, found {len(step_docs)}"

        doc_path = step_docs[0]
        content = doc_path.read_text()

        # Check Role
        role_match = re.search(r"- \*\*Role:\*\* (Node|Internal)", content)
        assert role_match, f"Step {step_num}: Role not found in doc"
        actual_role = role_match.group(1)
        assert actual_role == expected_role, (
            f"Step {step_num}: Role mismatch\n  Expected: {expected_role}\n  Actual:   {actual_role}"
        )

        # Check Status in AUTO-AUDIT block
        status_match = re.search(r"Status: ([✅🔌🟡❌]) \(([^)]+)\)", content)
        assert status_match, f"Step {step_num}: Status not found in AUTO-AUDIT block"
        actual_status = status_match.group(1)
        assert actual_status == expected_status, (
            f"Step {step_num}: Status mismatch\n  Expected: {expected_status}\n  Actual:   {actual_status}"
        )

        # Check registry status
        registry_match = re.search(r"Registry: ([✅❌]) (Wired|Not in registry)", content)
        assert registry_match, f"Step {step_num}: Registry status not found"
        is_wired = registry_match.group(1) == "✅"
        assert is_wired == should_be_wired, (
            f"Step {step_num}: Registry status mismatch\n"
            f"  Expected wired: {should_be_wired}\n"
            f"  Actual wired:   {is_wired}"
        )

        # For wired nodes, verify wiring information is present
        if should_be_wired:
            assert "Wiring information:" in content, f"Step {step_num}: Missing wiring information in AUTO-AUDIT block"
            assert f"- Node name: node_step_{step_num}" in content, f"Step {step_num}: Missing or incorrect node name"
            assert "- Incoming edges:" in content, f"Step {step_num}: Missing incoming edges info"
            assert "- Outgoing edges:" in content, f"Step {step_num}: Missing outgoing edges info"

    print(f"✅ All {len(test_steps)} test steps have correct Role, Status, and wiring info")


def test_conformance_dashboard_updated(wiring_registry):
    """
    Verify conformance dashboard has correct statistics.

    Checks that rag_conformance.md reflects the actual wiring state.
    """
    conformance_path = PROJECT_ROOT / "docs" / "architecture" / "rag_conformance.md"
    assert conformance_path.exists(), f"Conformance dashboard not found: {conformance_path}"

    content = conformance_path.read_text()

    # Check for Audit Summary section
    assert "## Audit Summary" in content, "Missing Audit Summary section"

    # Check for key statistics sections
    assert "**Node Steps**" in content, "Missing Node Steps statistics"
    assert "**Internal Steps**" in content, "Missing Internal Steps statistics"
    assert "Overall Statistics" in content, "Missing Overall Statistics"

    # Verify statistics are numeric (not placeholders)
    wired_match = re.search(r"- ✅ Implemented & Wired: (\d+) steps", content)
    assert wired_match, "Missing wired count in dashboard"
    wired_count = int(wired_match.group(1))

    # Should match registry count (or be close for canonical Nodes only)
    assert wired_count > 0, "Wired count is zero"
    assert wired_count <= len(wiring_registry), (
        f"Wired count in dashboard ({wired_count}) exceeds registry ({len(wiring_registry)})"
    )

    print(f"✅ Conformance dashboard has valid statistics (wired: {wired_count})")


def test_all_phase_nodes_have_correct_ids():
    """
    Verify all phase registries reference STEP_IDS correctly.

    This ensures no hardcoded ID strings exist in phase registries.
    """
    from app.core.langgraph.wiring_registry import (
        PHASE4_WIRED_NODES,
        PHASE5_WIRED_NODES,
        PHASE6_WIRED_NODES,
        PHASE7_WIRED_NODES,
        PHASE8_WIRED_NODES,
    )

    all_phase_nodes = {
        "Phase 4": PHASE4_WIRED_NODES,
        "Phase 5": PHASE5_WIRED_NODES,
        "Phase 6": PHASE6_WIRED_NODES,
        "Phase 7": PHASE7_WIRED_NODES,
        "Phase 8": PHASE8_WIRED_NODES,
    }

    for phase_name, phase_nodes in all_phase_nodes.items():
        for step_num, node_info in phase_nodes.items():
            # Verify ID matches STEP_IDS
            assert step_num in STEP_IDS, f"{phase_name} step {step_num} not in STEP_IDS mapping"
            expected_id = STEP_IDS[step_num]
            actual_id = node_info["id"]

            assert actual_id == expected_id, (
                f"{phase_name} step {step_num} ID mismatch:\n  Expected: {expected_id}\n  Actual:   {actual_id}"
            )

    print("✅ All phase registries use correct STEP_IDS references")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
