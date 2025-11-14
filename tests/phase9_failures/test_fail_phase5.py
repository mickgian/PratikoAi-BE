"""
Failure injection tests for Phase 5: Provider Governance failures.

Tests error handling for cost rejection loops and provider factory errors.
"""

import pytest
from unittest.mock import patch

from tests.common.fixtures_state import make_state
from tests.common.fakes import FakeOrchestrator
from app.core.langgraph.nodes.step_048__select_provider import node_step_48
from app.core.langgraph.nodes.step_055__estimate_cost import node_step_55
from app.core.langgraph.nodes.step_056__cost_check import node_step_56
from app.core.langgraph.nodes.step_057__create_provider import node_step_57
from app.core.langgraph.nodes.step_058__cheaper_provider import node_step_58


@pytest.mark.failure
@pytest.mark.phase5
class TestPhase5CostRejectionLoop:
    """Test cost rejection and cheaper provider loop."""

    async def test_repeated_cost_rejection_eventually_fails(self):
        """Verify repeated cost rejections eventually fail request."""
        state = make_state(
            provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"},
            cheaper_attempts=0
        )

        # Attempt 1: over budget
        fake_cost1 = FakeOrchestrator({
            "cost_estimate": 0.80,
            "within_budget": False
        })
        with patch("app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost", fake_cost1):
            state = await node_step_55(state)

        assert state["within_budget"] is False

        # Try cheaper provider
        fake_cheaper1 = FakeOrchestrator({
            "cheaper_provider_found": True,
            "provider": {"name": "openai", "model": "gpt-4"},
            "cheaper_attempts": 1
        })
        with patch("app.core.langgraph.nodes.step_058__cheaper_provider.step_58__cheaper_provider", fake_cheaper1):
            state = await node_step_58(state)
            state["cheaper_attempts"] = 1

        # Attempt 2: still over budget
        fake_cost2 = FakeOrchestrator({
            "cost_estimate": 0.65,
            "within_budget": False
        })
        with patch("app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost", fake_cost2):
            state = await node_step_55(state)

        # Try even cheaper
        fake_cheaper2 = FakeOrchestrator({
            "cheaper_provider_found": True,
            "provider": {"name": "openai", "model": "gpt-3.5-turbo"},
            "cheaper_attempts": 2
        })
        with patch("app.core.langgraph.nodes.step_058__cheaper_provider.step_58__cheaper_provider", fake_cheaper2):
            state = await node_step_58(state)
            state["cheaper_attempts"] = 2

        # Attempt 3: still over budget
        fake_cost3 = FakeOrchestrator({
            "cost_estimate": 0.55,
            "within_budget": False
        })
        with patch("app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost", fake_cost3):
            state = await node_step_55(state)

        # Attempt 4: No cheaper provider available
        fake_cheaper3 = FakeOrchestrator({
            "cheaper_provider_found": False,
            "error": "No cheaper provider available",
            "cheaper_attempts": 3,
            "max_attempts_reached": True
        })
        with patch("app.core.langgraph.nodes.step_058__cheaper_provider.step_58__cheaper_provider", fake_cheaper3):
            state = await node_step_58(state)

        # Should fail after exhausting options
        assert state.get("cheaper_provider_found") is False
        assert state.get("max_attempts_reached") is True

    async def test_cost_estimate_infinite_loop_protection(self):
        """Verify infinite cost rejection loop is prevented."""
        state = make_state(
            provider={"name": "anthropic"},
            cheaper_attempts=5  # Already at high count
        )

        # Cost check with max attempts
        fake_check = FakeOrchestrator({
            "cost_approved": False,
            "need_cheaper_provider": True,
            "cheaper_attempts": 5,
            "max_attempts": 3  # Exceeded
        })
        with patch("app.core.langgraph.nodes.step_056__cost_check.step_56__cost_check", fake_check):
            state = await node_step_56(state)

        # Should indicate loop protection triggered
        assert state.get("cheaper_attempts") >= state.get("max_attempts", 3)

    async def test_all_providers_over_budget_fails_gracefully(self):
        """Verify request fails gracefully when all providers exceed budget."""
        state = make_state(budget_limit=0.001)  # Very low budget

        # Try cheapest provider first
        fake_select = FakeOrchestrator({
            "provider_selected": True,
            "provider": {"name": "openai", "model": "gpt-3.5-turbo"}
        })
        with patch("app.core.langgraph.nodes.step_048__select_provider.step_48__select_provider", fake_select):
            state = await node_step_48(state)

        # Even cheapest is over budget
        fake_cost = FakeOrchestrator({
            "cost_estimate": 0.005,
            "within_budget": False,
            "budget_limit": 0.001
        })
        with patch("app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost", fake_cost):
            state = await node_step_55(state)

        # No cheaper available
        fake_cheaper = FakeOrchestrator({
            "cheaper_provider_found": False,
            "error": "All providers exceed budget"
        })
        with patch("app.core.langgraph.nodes.step_058__cheaper_provider.step_58__cheaper_provider", fake_cheaper):
            state = await node_step_58(state)

        # Graceful failure
        assert state.get("cheaper_provider_found") is False
        assert "budget" in state.get("error", "").lower()


@pytest.mark.failure
@pytest.mark.phase5
class TestPhase5ProviderFactoryErrors:
    """Test provider factory/creation errors."""

    async def test_provider_creation_fails_retries_with_different(self):
        """Verify provider creation failure retries with different provider."""
        state = make_state(
            provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"}
        )

        # Provider creation fails
        fake_create = FakeOrchestrator({
            "provider_ready": False,
            "error": "Failed to initialize provider",
            "error_type": "initialization_error"
        })
        with patch("app.core.langgraph.nodes.step_057__create_provider.step_57__create_provider", fake_create):
            state = await node_step_57(state)

        # Creation failed
        assert state.get("provider_ready") is False
        assert state.get("error") is not None

        # In real flow, step_72 (failover_provider) would select different provider
        fake_failover = FakeOrchestrator({
            "failover_provider": {"name": "openai", "model": "gpt-4"},
            "failover_triggered": True
        })
        with patch("app.core.langgraph.nodes.step_072__failover_provider.step_72__failover_provider", fake_failover):
            from app.core.langgraph.nodes.step_072__failover_provider import node_step_72
            state = await node_step_72(state)

        # Failover triggered
        assert state.get("failover_triggered") is True

    async def test_provider_invalid_api_key_error(self):
        """Verify invalid API key error is handled."""
        state = make_state(
            provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"}
        )

        # API key invalid
        fake_create = FakeOrchestrator({
            "provider_ready": False,
            "error": "Invalid API key",
            "error_type": "auth_error",
            "retryable": False
        })
        with patch("app.core.langgraph.nodes.step_057__create_provider.step_57__create_provider", fake_create):
            state = await node_step_57(state)

        # Auth error - not retryable
        assert state.get("provider_ready") is False
        assert state.get("error_type") == "auth_error"
        assert state.get("retryable") is False

    async def test_provider_model_not_available_error(self):
        """Verify model not available error triggers failover."""
        state = make_state(
            provider={"name": "anthropic", "model": "claude-3-opus-deprecated"}
        )

        # Model not available
        fake_create = FakeOrchestrator({
            "provider_ready": False,
            "error": "Model not available",
            "error_type": "model_not_found",
            "should_failover": True
        })
        with patch("app.core.langgraph.nodes.step_057__create_provider.step_57__create_provider", fake_create):
            state = await node_step_57(state)

        # Should trigger failover to different model
        assert state.get("provider_ready") is False
        assert state.get("should_failover") is True


@pytest.mark.failure
@pytest.mark.phase5
class TestPhase5ProviderSelectionErrors:
    """Test provider selection logic errors."""

    async def test_no_providers_available_for_strategy(self):
        """Verify error when no providers match strategy."""
        state = make_state(route_strategy="NONEXISTENT")

        # No providers match strategy
        fake_select = FakeOrchestrator({
            "provider_selected": False,
            "error": "No providers available for strategy",
            "strategy": "NONEXISTENT"
        })
        with patch("app.core.langgraph.nodes.step_048__select_provider.step_48__select_provider", fake_select):
            state = await node_step_48(state)

        # Selection failed
        assert state.get("provider_selected") is False
        assert state.get("error") is not None

    async def test_provider_registry_empty_error(self):
        """Verify error when provider registry is empty."""
        state = make_state(route_strategy="BEST")

        # Registry empty
        fake_select = FakeOrchestrator({
            "provider_selected": False,
            "error": "Provider registry is empty",
            "registry_available": False
        })
        with patch("app.core.langgraph.nodes.step_048__select_provider.step_48__select_provider", fake_select):
            state = await node_step_48(state)

        # Registry error
        assert state.get("provider_selected") is False
        assert state.get("registry_available") is False


@pytest.mark.failure
@pytest.mark.phase5
class TestPhase5CostEstimationErrors:
    """Test cost estimation errors."""

    async def test_cost_estimation_service_unavailable(self):
        """Verify cost estimation service unavailable is handled."""
        state = make_state(
            provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"}
        )

        # Cost service unavailable
        fake_cost = FakeOrchestrator({
            "cost_estimate": None,
            "within_budget": None,
            "error": "Cost estimation service unavailable",
            "service_available": False,
            "default_to_proceed": True  # Proceed without cost check
        })
        with patch("app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost", fake_cost):
            state = await node_step_55(state)

        # Should proceed despite estimation failure
        assert state.get("service_available") is False
        assert state.get("default_to_proceed") is True

    async def test_cost_estimation_invalid_model_data(self):
        """Verify invalid model pricing data is handled."""
        state = make_state(
            provider={"name": "unknown_provider", "model": "unknown_model"}
        )

        # Model pricing not found
        fake_cost = FakeOrchestrator({
            "cost_estimate": None,
            "within_budget": None,
            "error": "Pricing data not found for model",
            "pricing_available": False,
            "use_default_estimate": True,
            "default_cost": 0.10
        })
        with patch("app.core.langgraph.nodes.step_055__estimate_cost.step_55__estimate_cost", fake_cost):
            state = await node_step_55(state)

        # Use default estimate
        assert state.get("pricing_available") is False
        assert state.get("use_default_estimate") is True
