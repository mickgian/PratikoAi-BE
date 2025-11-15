"""
Lane integration tests for Phase 5: Provider Governance Lane.

Tests end-to-end flow through provider selection → cost check → cheaper loop.
"""

from unittest.mock import patch

import pytest

from app.core.langgraph.nodes.step_048__select_provider import node_step_48
from app.core.langgraph.nodes.step_055__estimate_cost import node_step_55
from app.core.langgraph.nodes.step_056__cost_check import node_step_56
from app.core.langgraph.nodes.step_057__create_provider import node_step_57
from app.core.langgraph.nodes.step_058__cheaper_provider import node_step_58
from tests.common.fakes import (
    FakeOrchestrator,
    fake_cost_estimate_orch,
    fake_provider_select_orch,
)
from tests.common.fixtures_state import make_state


@pytest.mark.lane
@pytest.mark.phase5
class TestPhase5ProviderSelectionPath:
    """Test provider selection flow."""

    async def test_provider_selection_to_cost_check(self):
        """Verify provider selection flows to cost check."""
        state = make_state(route_strategy="BEST")

        # Step 48: Select provider
        with patch(
            "app.core.langgraph.nodes.step_048__select_provider.step_48__select_provider",
            fake_provider_select_orch(provider="anthropic"),
        ):
            state = await node_step_48(state)

        # Verify provider selected
        assert state.get("provider_selected") is True
        assert state["provider"]["name"] == "anthropic"

        # Step 55: Estimate cost
        with patch(
            "app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost",
            fake_cost_estimate_orch(cost=0.015, within_budget=True),
        ):
            state = await node_step_55(state)

        # Verify cost estimated and within budget
        assert state["cost_estimate"] == 0.015
        assert state["within_budget"] is True

    async def test_best_strategy_selects_high_quality_provider(self):
        """Verify BEST strategy selects high-quality provider."""
        state = make_state(route_strategy="BEST")

        with patch(
            "app.core.langgraph.nodes.step_048__select_provider.step_48__select_provider",
            fake_provider_select_orch(provider="anthropic"),
        ):
            state = await node_step_48(state)

        # BEST should select anthropic (high quality)
        assert state["provider"]["name"] == "anthropic"
        assert state["provider"]["strategy"] == "BEST"


@pytest.mark.lane
@pytest.mark.phase5
class TestPhase5CostCheckPath:
    """Test cost check and budget validation flow."""

    async def test_within_budget_proceeds_to_provider_creation(self):
        """Verify within-budget proceeds to provider creation."""
        state = make_state(provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"})

        # Estimate cost (within budget)
        with patch(
            "app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost",
            fake_cost_estimate_orch(cost=0.02, within_budget=True),
        ):
            state = await node_step_55(state)

        assert state["within_budget"] is True

        # Step 56: Cost check (should pass)
        fake_check = FakeOrchestrator({"cost_approved": True, "proceed_with_llm": True})
        with patch("app.core.langgraph.nodes.step_056__cost_check.step_56__cost_check", fake_check):
            state = await node_step_56(state)

        assert state.get("cost_approved") is True

        # Step 57: Create provider instance
        fake_create = FakeOrchestrator(
            {"provider_instance": {"name": "anthropic", "api_key": "fake-key"}, "provider_ready": True}
        )
        with patch("app.core.langgraph.nodes.step_057__create_provider.step_57__create_provider", fake_create):
            state = await node_step_57(state)

        assert state.get("provider_ready") is True

    async def test_over_budget_triggers_cheaper_loop(self):
        """Verify over-budget triggers cheaper provider loop."""
        state = make_state(provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"})

        # Estimate cost (over budget)
        with patch(
            "app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost",
            fake_cost_estimate_orch(cost=0.85, within_budget=False),
        ):
            state = await node_step_55(state)

        assert state["within_budget"] is False
        assert state["cost_estimate"] == 0.85

        # Step 56: Cost check (should reject)
        fake_check = FakeOrchestrator({"cost_approved": False, "need_cheaper_provider": True})
        with patch("app.core.langgraph.nodes.step_056__cost_check.step_56__cost_check", fake_check):
            state = await node_step_56(state)

        assert state.get("cost_approved") is False
        assert state.get("need_cheaper_provider") is True


@pytest.mark.lane
@pytest.mark.phase5
class TestPhase5CheaperProviderLoop:
    """Test cheaper provider selection loop."""

    async def test_cheaper_provider_selection_after_cost_reject(self):
        """Verify cheaper provider selected after cost rejection."""
        state = make_state(
            provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"},
            cost_estimate=0.85,
            within_budget=False,
        )

        # Step 58: Select cheaper provider
        fake_cheaper = FakeOrchestrator(
            {
                "cheaper_provider_found": True,
                "provider": {"name": "openai", "model": "gpt-3.5-turbo", "strategy": "CHEAP"},
            }
        )
        with patch("app.core.langgraph.nodes.step_058__cheaper_provider.step_58__cheaper_provider", fake_cheaper):
            state = await node_step_58(state)

        # Verify cheaper provider selected
        assert state.get("cheaper_provider_found") is True
        assert state["provider"]["name"] == "openai"

        # Re-estimate cost with cheaper provider
        with patch(
            "app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost",
            fake_cost_estimate_orch(cost=0.005, within_budget=True),
        ):
            state = await node_step_55(state)

        # Should now be within budget
        assert state["within_budget"] is True
        assert state["cost_estimate"] == 0.005

    async def test_cheaper_loop_eventually_succeeds(self):
        """Verify cheaper loop eventually finds acceptable provider."""
        state = make_state(provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"})

        # First attempt: over budget
        with patch(
            "app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost",
            fake_cost_estimate_orch(cost=0.80, within_budget=False),
        ):
            state = await node_step_55(state)

        # Get cheaper provider
        fake_cheaper = FakeOrchestrator(
            {"cheaper_provider_found": True, "provider": {"name": "openai", "model": "gpt-3.5-turbo"}}
        )
        with patch("app.core.langgraph.nodes.step_058__cheaper_provider.step_58__cheaper_provider", fake_cheaper):
            state = await node_step_58(state)

        # Second attempt: within budget
        with patch(
            "app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost",
            fake_cost_estimate_orch(cost=0.01, within_budget=True),
        ):
            state = await node_step_55(state)

        # Success
        assert state["within_budget"] is True

    async def test_no_cheaper_provider_available(self):
        """Verify handling when no cheaper provider available."""
        state = make_state(
            provider={"name": "openai", "model": "gpt-3.5-turbo"},  # Already cheapest
            cost_estimate=0.60,
            within_budget=False,
        )

        # Step 58: Try to find cheaper (none available)
        fake_cheaper = FakeOrchestrator({"cheaper_provider_found": False, "error": "No cheaper provider available"})
        with patch("app.core.langgraph.nodes.step_058__cheaper_provider.step_58__cheaper_provider", fake_cheaper):
            state = await node_step_58(state)

        # Should indicate failure
        assert state.get("cheaper_provider_found") is False
        assert state.get("error") is not None


@pytest.mark.lane
@pytest.mark.phase5
class TestPhase5StrategyRouting:
    """Test different routing strategies."""

    async def test_cheap_strategy_selects_low_cost_provider(self):
        """Verify CHEAP strategy selects low-cost provider."""
        state = make_state(route_strategy="CHEAP")

        fake_orch = FakeOrchestrator(
            {"provider_selected": True, "provider": {"name": "openai", "model": "gpt-3.5-turbo", "strategy": "CHEAP"}}
        )
        with patch("app.core.langgraph.nodes.step_048__select_provider.step_48__select_provider", fake_orch):
            state = await node_step_48(state)

        # CHEAP strategy should select cost-effective provider
        assert state["provider"]["strategy"] == "CHEAP"

    async def test_balance_strategy_balances_cost_and_quality(self):
        """Verify BALANCE strategy balances cost and quality."""
        state = make_state(route_strategy="BALANCE")

        fake_orch = FakeOrchestrator(
            {
                "provider_selected": True,
                "provider": {"name": "anthropic", "model": "claude-3-haiku-20240307", "strategy": "BALANCE"},
            }
        )
        with patch("app.core.langgraph.nodes.step_048__select_provider.step_48__select_provider", fake_orch):
            state = await node_step_48(state)

        # BALANCE strategy selected
        assert state["provider"]["strategy"] == "BALANCE"
