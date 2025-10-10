"""
Parity tests for Phase 5: Provider Governance Lane.

Verifies that provider selection and cost estimation nodes correctly
delegate to orchestrators.
"""

import pytest
from unittest.mock import patch

from tests.common.fixtures_state import make_state
from tests.common.fakes import (
    fake_provider_select_orch,
    fake_cost_estimate_orch,
    FakeOrchestrator,
)
from app.core.langgraph.nodes.step_048__select_provider import node_step_48
from app.core.langgraph.nodes.step_055__estimate_cost import node_step_55
from app.core.langgraph.nodes.step_057__create_provider import node_step_57


@pytest.mark.parity
@pytest.mark.phase5
class TestPhase5ProviderParity:
    """Test provider selection node wrapper parity."""

    async def test_provider_select_delegates_to_orchestrator(self):
        """Verify provider selection delegates correctly."""
        state = make_state(
            route_strategy="BEST"
        )
        fake_orch = fake_provider_select_orch(provider="anthropic")

        with patch("app.core.langgraph.nodes.step_048__select_provider.step_48__select_provider", fake_orch):
            result = await node_step_48(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify provider selection result in state
        assert result.get("provider_selected") is True
        assert result.get("provider", {}).get("name") == "anthropic"

    async def test_provider_select_preserves_strategy(self):
        """Verify provider selection preserves routing strategy."""
        state = make_state(route_strategy="CHEAP")
        fake_orch = fake_provider_select_orch(provider="openai")

        with patch("app.core.langgraph.nodes.step_048__select_provider.step_48__select_provider", fake_orch):
            result = await node_step_48(state)

        # Original strategy preserved
        assert result.get("route_strategy") == "CHEAP"

    async def test_cost_estimate_delegates_correctly(self):
        """Verify cost estimation delegates to orchestrator."""
        state = make_state(
            provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"},
            messages=[{"role": "user", "content": "test query"}]
        )
        fake_orch = fake_cost_estimate_orch(cost=0.015, within_budget=True)

        with patch("app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost", fake_orch):
            result = await node_step_55(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify cost estimation in state
        assert result.get("cost_estimate") is not None
        assert result.get("within_budget") is True


@pytest.mark.parity
@pytest.mark.phase5
class TestPhase5CostCheckParity:
    """Test cost estimation and budget check parity."""

    async def test_within_budget_delegates_correctly(self):
        """Verify within-budget scenario delegates correctly."""
        state = make_state(
            provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"}
        )
        fake_orch = fake_cost_estimate_orch(cost=0.01, within_budget=True)

        with patch("app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost", fake_orch):
            result = await node_step_55(state)

        assert result.get("within_budget") is True
        assert result.get("cost_estimate") == 0.01

    async def test_over_budget_delegates_correctly(self):
        """Verify over-budget scenario delegates correctly."""
        state = make_state(
            provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"}
        )
        fake_orch = fake_cost_estimate_orch(cost=0.75, within_budget=False)

        with patch("app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost", fake_orch):
            result = await node_step_55(state)

        assert result.get("within_budget") is False
        assert result.get("cost_estimate") == 0.75


@pytest.mark.parity
@pytest.mark.phase5
class TestPhase5CreateProviderParity:
    """Test provider instance creation parity."""

    async def test_create_provider_delegates_correctly(self):
        """Verify provider creation delegates to orchestrator."""
        state = make_state(
            provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"}
        )
        fake_orch = FakeOrchestrator({
            "provider_instance": {
                "name": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "api_key": "fake-key"
            },
            "provider_ready": True
        })

        with patch("app.core.langgraph.nodes.step_057__create_provider.step_57__create_provider", fake_orch):
            result = await node_step_57(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify provider instance created
        assert result.get("provider_ready") is True
        assert result.get("provider_instance") is not None

    async def test_create_provider_preserves_cost_info(self):
        """Verify provider creation preserves cost estimation."""
        state = make_state(
            provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"},
            cost_estimate=0.015,
            within_budget=True
        )
        fake_orch = FakeOrchestrator({
            "provider_instance": {"name": "anthropic"},
            "provider_ready": True
        })

        with patch("app.core.langgraph.nodes.step_057__create_provider.step_57__create_provider", fake_orch):
            result = await node_step_57(state)

        # Cost info preserved
        assert result.get("cost_estimate") == 0.015
        assert result.get("within_budget") is True
