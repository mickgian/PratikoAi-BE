"""
Parity tests for Phase 6: Request Validation and Privacy Lane.

Verifies that validation and privacy nodes correctly delegate
to orchestrators and maintain state consistency.
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
from app.core.langgraph.nodes.step_006__privacy_check import node_step_6
from app.core.langgraph.nodes.step_009__pii_check import node_step_9


@pytest.mark.parity
@pytest.mark.phase6
class TestPhase6ValidationParity:
    """Test request validation node wrapper parity."""

    async def test_validate_request_delegates_valid(self):
        """Verify validation with valid request delegates correctly."""
        state = make_state(
            messages=[{"role": "user", "content": "test query"}]
        )
        fake_orch = fake_validate_request_orch(valid=True)

        with patch("app.core.langgraph.nodes.step_001__validate_request.step_1__validate_request", fake_orch):
            result = await node_step_1(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify validation result
        assert result.get("request_valid") is True
        assert not result.get("validation_errors")

    async def test_validate_request_delegates_invalid(self):
        """Verify validation with invalid request delegates correctly."""
        state = make_state(messages=[])
        fake_orch = fake_validate_request_orch(valid=False)

        with patch("app.core.langgraph.nodes.step_001__validate_request.step_1__validate_request", fake_orch):
            result = await node_step_1(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify validation failure
        assert result.get("request_valid") is False
        assert result.get("validation_errors")

    async def test_validation_preserves_request_id(self):
        """Verify validation doesn't lose request tracking."""
        request_id = "test-req-789"
        state = make_state(request_id=request_id)
        fake_orch = fake_validate_request_orch(valid=True)

        with patch("app.core.langgraph.nodes.step_001__validate_request.step_1__validate_request", fake_orch):
            result = await node_step_1(state)

        # Request ID preserved
        assert result["request_id"] == request_id


@pytest.mark.parity
@pytest.mark.phase6
class TestPhase6PrivacyParity:
    """Test privacy check node wrapper parity."""

    async def test_privacy_check_enabled_delegates(self):
        """Verify privacy check with enabled privacy delegates correctly."""
        state = make_state()
        fake_orch = fake_privacy_check_orch(enabled=True)

        with patch("app.core.langgraph.nodes.step_006__privacy_check.step_6__privacy_check", fake_orch):
            result = await node_step_6(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify privacy enabled
        assert result.get("privacy_enabled") is True
        assert result.get("anonymize_required") is True

    async def test_privacy_check_disabled_delegates(self):
        """Verify privacy check with disabled privacy delegates correctly."""
        state = make_state()
        fake_orch = fake_privacy_check_orch(enabled=False)

        with patch("app.core.langgraph.nodes.step_006__privacy_check.step_6__privacy_check", fake_orch):
            result = await node_step_6(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify privacy disabled
        assert result.get("privacy_enabled") is False


@pytest.mark.parity
@pytest.mark.phase6
class TestPhase6PIIParity:
    """Test PII detection node wrapper parity."""

    async def test_pii_check_no_pii_delegates(self):
        """Verify PII check with no PII delegates correctly."""
        state = make_state(
            messages=[{"role": "user", "content": "What is the weather?"}]
        )
        fake_orch = FakeOrchestrator({
            "pii_detected": False,
            "pii_entities": []
        })

        with patch("app.core.langgraph.nodes.step_009__pii_check.step_9__pii_check", fake_orch):
            result = await node_step_9(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify no PII detected
        assert result.get("pii_detected") is False

    async def test_pii_check_with_pii_delegates(self):
        """Verify PII check with PII detected delegates correctly."""
        state = make_state(
            messages=[{"role": "user", "content": "My email is john@example.com"}]
        )
        fake_orch = FakeOrchestrator({
            "pii_detected": True,
            "pii_entities": [{"type": "EMAIL", "value": "john@example.com"}]
        })

        with patch("app.core.langgraph.nodes.step_009__pii_check.step_9__pii_check", fake_orch):
            result = await node_step_9(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify PII detected
        assert result.get("pii_detected") is True
        assert len(result.get("pii_entities", [])) > 0

    async def test_pii_wrapper_preserves_privacy_state(self):
        """Verify PII check preserves privacy configuration."""
        state = make_state(
            privacy_enabled=True,
            privacy={"gdpr_logged": True}
        )
        fake_orch = FakeOrchestrator({
            "pii_detected": False,
            "pii_entities": []
        })

        with patch("app.core.langgraph.nodes.step_009__pii_check.step_9__pii_check", fake_orch):
            result = await node_step_9(state)

        # Privacy state preserved
        assert result.get("privacy_enabled") is True
        assert result.get("privacy", {}).get("gdpr_logged") is True
