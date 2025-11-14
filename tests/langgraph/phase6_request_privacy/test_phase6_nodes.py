"""Tests for Phase 6 Request/Privacy Lane nodes."""

import pytest
from unittest.mock import AsyncMock, patch
from app.core.langgraph.types import RAGState


@pytest.mark.asyncio
async def test_step_1_validate_request():
    """Test Step 1: Validate Request node wrapper."""
    from app.core.langgraph.nodes.step_001__validate_request import node_step_1

    # Create test state
    state: RAGState = {
        "messages": [{"role": "user", "content": "test"}],
    }

    # Mock the orchestrator
    mock_result = {
        "request_valid": True,
        "validation_successful": True,
        "authentication_successful": True,
        "session": {"user_id": "123"},
        "user": {"id": "123", "name": "Test User"},
    }

    with patch("app.orchestrators.platform.step_1__validate_request", new=AsyncMock(return_value=mock_result)):
        result_state = await node_step_1(state)

        # Verify state was updated
        assert "decisions" in result_state
        assert result_state["decisions"]["request_valid"] is True
        assert result_state["session"]["user_id"] == "123"


@pytest.mark.asyncio
async def test_step_3_valid_check():
    """Test Step 3: Valid Check node wrapper."""
    from app.core.langgraph.nodes.step_003__valid_check import node_step_3

    state: RAGState = {"messages": []}

    mock_result = {"is_valid": True, "validation_result": {"status": "ok"}}

    with patch("app.orchestrators.platform.step_3__valid_check", new=AsyncMock(return_value=mock_result)):
        result_state = await node_step_3(state)

        assert result_state["decisions"]["is_valid"] is True


@pytest.mark.asyncio
async def test_step_4_gdpr_log():
    """Test Step 4: GDPR Log node wrapper."""
    from app.core.langgraph.nodes.step_004__gdpr_log import node_step_4

    state: RAGState = {"messages": []}

    mock_result = {
        "gdpr_logged": True,
        "processing_recorded": True,
        "processing_id": "proc-123",
    }

    with patch("app.orchestrators.privacy.step_4__gdprlog", new=AsyncMock(return_value=mock_result)):
        result_state = await node_step_4(state)

        assert result_state["privacy"]["gdpr_logged"] is True
        assert result_state["privacy"]["processing_id"] == "proc-123"


@pytest.mark.asyncio
async def test_step_6_privacy_check():
    """Test Step 6: Privacy Check node wrapper."""
    from app.core.langgraph.nodes.step_006__privacy_check import node_step_6

    state: RAGState = {"messages": []}

    mock_result = {
        "privacy_enabled": True,
        "anonymize_requests": True,
        "privacy_ok": True,
    }

    with patch("app.orchestrators.privacy.step_6__privacy_check", new=AsyncMock(return_value=mock_result)):
        result_state = await node_step_6(state)

        assert result_state["privacy"]["enabled"] is True
        assert result_state["decisions"]["privacy_ok"] is True


@pytest.mark.asyncio
async def test_step_7_anonymize_text():
    """Test Step 7: Anonymize Text node wrapper."""
    from app.core.langgraph.nodes.step_007__anonymize_text import node_step_7

    state: RAGState = {"messages": []}

    mock_result = {
        "anonymized_input": "Hello [NAME]",
        "anonymization_applied": True,
    }

    with patch("app.orchestrators.privacy.step_7__anonymize_text", new=AsyncMock(return_value=mock_result)):
        result_state = await node_step_7(state)

        assert result_state["privacy"]["anonymized_input"] == "Hello [NAME]"
        assert result_state["privacy"]["anonymization_applied"] is True


@pytest.mark.asyncio
async def test_step_9_pii_check():
    """Test Step 9: PII Check node wrapper."""
    from app.core.langgraph.nodes.step_009__pii_check import node_step_9

    state: RAGState = {"messages": []}

    mock_result = {
        "pii_detected": True,
        "pii_entities": [{"type": "EMAIL", "value": "test@example.com"}],
    }

    with patch("app.orchestrators.platform.step_9__piicheck", new=AsyncMock(return_value=mock_result)):
        result_state = await node_step_9(state)

        assert result_state["privacy"]["pii_detected"] is True
        assert len(result_state["privacy"]["pii_entities"]) == 1


@pytest.mark.asyncio
async def test_step_10_log_pii():
    """Test Step 10: Log PII node wrapper."""
    from app.core.langgraph.nodes.step_010__log_pii import node_step_10

    state: RAGState = {"messages": []}

    mock_result = {"pii_logged": True, "log_timestamp": "2025-10-06T12:00:00Z"}

    with patch("app.orchestrators.platform.step_10__log_pii", new=AsyncMock(return_value=mock_result)):
        result_state = await node_step_10(state)

        assert result_state["privacy"]["pii_logged"] is True


@pytest.mark.asyncio
async def test_step_8_init_agent():
    """Test Step 8: Init Agent node wrapper."""
    from app.core.langgraph.nodes.step_008__init_agent import node_step_8

    state: RAGState = {"messages": []}

    mock_result = {"agent_initialized": True, "workflow_ready": True}

    with patch("app.orchestrators.response.step_8__init_agent", new=AsyncMock(return_value=mock_result)):
        result_state = await node_step_8(state)

        assert result_state["agent_initialized"] is True
        assert result_state["workflow_ready"] is True


@pytest.mark.asyncio
async def test_wiring_registry_phase6():
    """Test that Phase 6 nodes are registered in wiring registry."""
    from app.core.langgraph.wiring_registry import get_wired_nodes_snapshot, initialize_phase6_registry, WIRED_NODES

    # Clear and reinitialize
    WIRED_NODES.clear()
    initialize_phase6_registry()

    snapshot = get_wired_nodes_snapshot()

    # Verify all Phase 6 nodes are registered
    phase6_steps = [1, 3, 4, 6, 7, 8, 9, 10]
    for step in phase6_steps:
        assert step in snapshot, f"Step {step} not in wiring registry"
        assert "id" in snapshot[step]
        assert "name" in snapshot[step]
        assert "incoming" in snapshot[step]
        assert "outgoing" in snapshot[step]

    # Verify specific edges
    assert 3 in snapshot[1]["outgoing"]  # 1 → 3
    assert 4 in snapshot[3]["outgoing"]  # 3 → 4
    assert 6 in snapshot[4]["outgoing"]  # 4 → 6
    assert 7 in snapshot[6]["outgoing"]  # 6 → 7
    assert 9 in snapshot[7]["outgoing"]  # 7 → 9
    assert 10 in snapshot[9]["outgoing"]  # 9 → 10
    assert 8 in snapshot[10]["outgoing"]  # 10 → 8
