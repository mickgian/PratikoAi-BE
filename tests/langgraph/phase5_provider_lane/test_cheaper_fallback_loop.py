"""Test cheaper provider fallback loop functionality."""

from unittest.mock import patch

import pytest

from app.core.langgraph.nodes.step_055__estimate_cost import node_step_55
from app.core.langgraph.nodes.step_058__cheaper_provider import node_step_58
from app.core.langgraph.types import RAGState


class TestCheaperFallbackLoop:
    """Test cheaper provider fallback and loop behavior."""

    @pytest.fixture
    def base_state(self):
        """Base test state."""
        return {
            "messages": [{"role": "user", "content": "expensive query"}],
            "provider": {"selected": "anthropic-claude-3", "estimate": 2.50, "budget_ok": False},
            "decisions": {"cost_ok": False},
        }

    @patch("app.orchestrators.providers.step_58__cheaper_provider")
    def test_cheaper_provider_found(self, mock_orchestrator, base_state):
        """Test when a cheaper provider is found."""
        mock_orchestrator.return_value = {
            "provider": "openai-gpt-3.5-turbo",
            "cheaper_found": True,
            "fallback_strategy": "downgrade",
        }

        result = node_step_58(base_state)

        assert result["provider"]["selected"] == "openai-gpt-3.5-turbo"
        assert result["provider"]["cheaper_found"] is True
        assert result["provider"]["fallback_strategy"] == "downgrade"
        assert result["provider_choice"] == "openai-gpt-3.5-turbo"
        mock_orchestrator.assert_called_once_with(ctx=base_state)

    @patch("app.orchestrators.providers.step_58__cheaper_provider")
    def test_cheaper_provider_not_found(self, mock_orchestrator, base_state):
        """Test when no cheaper provider is available."""
        mock_orchestrator.return_value = {"provider": None, "cheaper_found": False, "fallback_strategy": "reject"}

        result = node_step_58(base_state)

        assert result["provider"]["selected"] is None
        assert result["provider"]["cheaper_found"] is False
        assert result["provider"]["fallback_strategy"] == "reject"

    @patch("app.orchestrators.providers.step_58__cheaper_provider")
    def test_cheaper_provider_preserves_existing_data(self, mock_orchestrator, base_state):
        """Test that cheaper provider search preserves existing provider data."""
        base_state["provider"].update({"strategy": "BEST", "cost_details": {"tokens": 1000}})
        mock_orchestrator.return_value = {"provider": "openai-gpt-4", "cheaper_found": True}

        result = node_step_58(base_state)

        assert result["provider"]["strategy"] == "BEST"
        assert result["provider"]["cost_details"]["tokens"] == 1000
        assert result["provider"]["selected"] == "openai-gpt-4"
        assert result["provider"]["cheaper_found"] is True

    def test_cost_estimation_after_cheaper_provider(self, base_state):
        """Test that cost is re-estimated after finding cheaper provider."""
        # Simulate the loop: CheaperProvider → EstimateCost
        with (
            patch("app.orchestrators.providers.step_58__cheaper_provider") as mock_cheaper,
            patch("app.orchestrators.providers.step_55__estimate_cost") as mock_estimate,
        ):
            # First, cheaper provider found
            mock_cheaper.return_value = {"provider": "openai-gpt-3.5-turbo", "cheaper_found": True}

            result1 = node_step_58(base_state)
            assert result1["provider"]["selected"] == "openai-gpt-3.5-turbo"

            # Then, re-estimate cost with new provider
            mock_estimate.return_value = {
                "estimated_cost": 0.75,
                "cost_details": {"input_tokens": 100, "output_tokens": 150},
            }

            result2 = node_step_55(result1)
            assert result2["provider"]["estimate"] == 0.75
            assert result2["estimated_cost"] == 0.75

    @patch("app.orchestrators.providers.step_58__cheaper_provider")
    def test_cheaper_provider_multiple_attempts(self, mock_orchestrator, base_state):
        """Test multiple attempts to find cheaper provider."""
        # First attempt - finds slightly cheaper but still expensive
        mock_orchestrator.return_value = {
            "provider": "openai-gpt-4",
            "cheaper_found": True,
            "fallback_strategy": "moderate_downgrade",
        }

        result1 = node_step_58(base_state)
        assert result1["provider"]["selected"] == "openai-gpt-4"
        assert result1["provider"]["cheaper_found"] is True

        # Simulate state after re-estimation still shows too expensive
        result1["provider"]["estimate"] = 1.80
        result1["decisions"]["cost_ok"] = False

        # Second attempt - finds even cheaper option
        mock_orchestrator.return_value = {
            "provider": "openai-gpt-3.5-turbo",
            "cheaper_found": True,
            "fallback_strategy": "significant_downgrade",
        }

        result2 = node_step_58(result1)
        assert result2["provider"]["selected"] == "openai-gpt-3.5-turbo"
        assert result2["provider"]["fallback_strategy"] == "significant_downgrade"

    @patch("app.orchestrators.providers.step_58__cheaper_provider")
    def test_cheaper_provider_exit_condition(self, mock_orchestrator, base_state):
        """Test loop exit when no cheaper option available."""
        mock_orchestrator.return_value = {
            "provider": None,
            "cheaper_found": False,
            "fallback_strategy": "none_available",
        }

        result = node_step_58(base_state)

        assert result["provider"]["cheaper_found"] is False
        assert result["provider"]["fallback_strategy"] == "none_available"
        # This should signal to the orchestrator to exit the loop
