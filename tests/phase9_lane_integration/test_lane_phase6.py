"""
Lane integration tests for Phase 6: Request Validation and Privacy Lane.

Tests end-to-end flow through validation → privacy checks → agent init.
"""

import pytest
from unittest.mock import patch

from tests.common.fixtures_state import make_state
from tests.common.fakes import (
    fake_validate_request_orch,
    fake_privacy_check_orch,
    FakeOrchestrator,
)
from app.core.langgraph.nodes.step_001__validate_request import node_step_1
from app.core.langgraph.nodes.step_003__valid_check import node_step_3
from app.core.langgraph.nodes.step_006__privacy_check import node_step_6
from app.core.langgraph.nodes.step_009__pii_check import node_step_9
from app.core.langgraph.nodes.step_008__init_agent import node_step_8


@pytest.mark.lane
@pytest.mark.phase6
class TestPhase6ValidationFlow:
    """Test request validation flow."""

    async def test_valid_request_proceeds_to_privacy(self):
        """Verify valid request proceeds to privacy checks."""
        state = make_state(
            messages=[{"role": "user", "content": "What is the weather?"}]
        )

        # Step 1: Validate request
        with patch("app.core.langgraph.nodes.step_001__validate_request.step_1__validate_request",
                   fake_validate_request_orch(valid=True)):
            state = await node_step_1(state)

        # Verify validation passed
        assert state.get("request_valid") is True

        # Step 3: Check validation result (routing decision)
        fake_check = FakeOrchestrator({
            "validation_passed": True,
            "proceed_to_privacy": True
        })
        with patch("app.core.langgraph.nodes.step_003__valid_check.step_3__valid_check", fake_check):
            state = await node_step_3(state)

        assert state.get("validation_passed") is True
        assert state.get("proceed_to_privacy") is True

    async def test_invalid_request_stops_early(self):
        """Verify invalid request stops processing early."""
        state = make_state(messages=[])  # Empty messages = invalid

        # Step 1: Validate request (FAIL)
        with patch("app.core.langgraph.nodes.step_001__validate_request.step_1__validate_request",
                   fake_validate_request_orch(valid=False)):
            state = await node_step_1(state)

        # Verify validation failed
        assert state.get("request_valid") is False
        assert state.get("validation_errors")

        # Step 3: Check would route to error
        fake_check = FakeOrchestrator({
            "validation_passed": False,
            "should_return_error": True
        })
        with patch("app.core.langgraph.nodes.step_003__valid_check.step_3__valid_check", fake_check):
            state = await node_step_3(state)

        assert state.get("validation_passed") is False


@pytest.mark.lane
@pytest.mark.phase6
class TestPhase6PrivacyFlow:
    """Test privacy check and PII detection flow."""

    async def test_privacy_enabled_no_pii_proceeds(self):
        """Verify privacy enabled with no PII proceeds to agent init."""
        state = make_state(
            messages=[{"role": "user", "content": "What is the weather?"}]
        )

        # Step 6: Privacy check (ENABLED)
        with patch("app.core.langgraph.nodes.step_006__privacy_check.step_6__privacy_check",
                   fake_privacy_check_orch(enabled=True)):
            state = await node_step_6(state)

        assert state.get("privacy_enabled") is True

        # Step 9: PII check (NO PII)
        fake_pii = FakeOrchestrator({
            "pii_detected": False,
            "pii_entities": []
        })
        with patch("app.core.langgraph.nodes.step_009__pii_check.step_9__pii_check", fake_pii):
            state = await node_step_9(state)

        # No PII detected
        assert state.get("pii_detected") is False

    async def test_privacy_enabled_pii_detected_anonymizes(self):
        """Verify PII detection triggers anonymization."""
        state = make_state(
            messages=[{"role": "user", "content": "My email is john@example.com"}]
        )

        # Step 6: Privacy check (ENABLED)
        with patch("app.core.langgraph.nodes.step_006__privacy_check.step_6__privacy_check",
                   fake_privacy_check_orch(enabled=True)):
            state = await node_step_6(state)

        # Step 9: PII check (PII DETECTED)
        fake_pii = FakeOrchestrator({
            "pii_detected": True,
            "pii_entities": [{"type": "EMAIL", "value": "john@example.com"}]
        })
        with patch("app.core.langgraph.nodes.step_009__pii_check.step_9__pii_check", fake_pii):
            state = await node_step_9(state)

        assert state.get("pii_detected") is True
        assert len(state.get("pii_entities", [])) > 0

        # Step 7: Anonymize text (would be called in real flow)
        fake_anon = FakeOrchestrator({
            "anonymized_input": "My email is [EMAIL]",
            "anonymization_map": {"[EMAIL]": "john@example.com"}
        })
        with patch("app.core.langgraph.nodes.step_007__anonymize_text.step_7__anonymize_text", fake_anon):
            from app.core.langgraph.nodes.step_007__anonymize_text import node_step_7
            state = await node_step_7(state)

        # Verify anonymization
        assert state.get("anonymized_input") == "My email is [EMAIL]"

    async def test_privacy_disabled_skips_pii_checks(self):
        """Verify privacy disabled skips PII checks."""
        state = make_state(
            messages=[{"role": "user", "content": "My email is john@example.com"}]
        )

        # Step 6: Privacy check (DISABLED)
        with patch("app.core.langgraph.nodes.step_006__privacy_check.step_6__privacy_check",
                   fake_privacy_check_orch(enabled=False)):
            state = await node_step_6(state)

        # Privacy disabled - would skip PII checks in routing
        assert state.get("privacy_enabled") is False


@pytest.mark.lane
@pytest.mark.phase6
class TestPhase6AgentInitFlow:
    """Test agent initialization after validation and privacy."""

    async def test_successful_validation_privacy_inits_agent(self):
        """Verify successful validation and privacy checks init agent."""
        state = make_state(
            messages=[{"role": "user", "content": "What is the weather?"}]
        )

        # Validation passed
        with patch("app.core.langgraph.nodes.step_001__validate_request.step_1__validate_request",
                   fake_validate_request_orch(valid=True)):
            state = await node_step_1(state)

        # Privacy passed (no PII)
        with patch("app.core.langgraph.nodes.step_006__privacy_check.step_6__privacy_check",
                   fake_privacy_check_orch(enabled=True)):
            state = await node_step_6(state)

        fake_pii = FakeOrchestrator({"pii_detected": False})
        with patch("app.core.langgraph.nodes.step_009__pii_check.step_9__pii_check", fake_pii):
            state = await node_step_9(state)

        # Step 8: Init agent
        fake_init = FakeOrchestrator({
            "agent_initialized": True,
            "agent_config": {"llm_enabled": True, "tools_available": ["kb_search"]}
        })
        with patch("app.core.langgraph.nodes.step_008__init_agent.step_8__init_agent", fake_init):
            state = await node_step_8(state)

        # Agent initialized
        assert state.get("agent_initialized") is True
        assert state.get("agent_config") is not None

    async def test_privacy_flow_preserves_request_context(self):
        """Verify privacy flow preserves request context."""
        request_id = "req-abc-123"
        session_id = "sess-xyz-789"
        state = make_state(
            request_id=request_id,
            session_id=session_id,
            messages=[{"role": "user", "content": "test"}]
        )

        # Go through validation and privacy
        with patch("app.core.langgraph.nodes.step_001__validate_request.step_1__validate_request",
                   fake_validate_request_orch(valid=True)):
            state = await node_step_1(state)

        with patch("app.core.langgraph.nodes.step_006__privacy_check.step_6__privacy_check",
                   fake_privacy_check_orch(enabled=True)):
            state = await node_step_6(state)

        # Context preserved
        assert state["request_id"] == request_id
        assert state["session_id"] == session_id


@pytest.mark.lane
@pytest.mark.phase6
class TestPhase6GDPRLogging:
    """Test GDPR logging in validation flow."""

    async def test_gdpr_log_after_validation(self):
        """Verify GDPR log is created after validation."""
        state = make_state()

        # Step 4: GDPR log
        fake_gdpr = FakeOrchestrator({
            "gdpr_logged": True,
            "log_id": "gdpr-log-123"
        })
        with patch("app.core.langgraph.nodes.step_004__gdpr_log.step_4__gdpr_log", fake_gdpr):
            from app.core.langgraph.nodes.step_004__gdpr_log import node_step_4
            state = await node_step_4(state)

        # GDPR logged
        assert state.get("gdpr_logged") is True
        assert state.get("log_id") == "gdpr-log-123"
