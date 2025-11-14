"""Test cost estimation and check functionality."""

import pytest
from unittest.mock import patch

from app.core.langgraph.types import RAGState
from app.core.langgraph.nodes.step_055__estimate_cost import node_step_55
from app.core.langgraph.nodes.step_056__cost_check import node_step_56


class TestCostEstimationAndCheck:
    """Test cost estimation and budget checking."""

    @pytest.fixture
    def base_state(self):
        """Base test state."""
        return {
            "messages": [{"role": "user", "content": "test query"}],
            "provider": {"selected": "openai-gpt-4"},
            "decisions": {}
        }

    @patch('app.orchestrators.providers.step_55__estimate_cost')
    def test_estimate_cost_basic(self, mock_orchestrator, base_state):
        """Test basic cost estimation."""
        mock_orchestrator.return_value = {
            "estimated_cost": 0.05,
            "cost_details": {"input_tokens": 100, "output_tokens": 200}
        }

        result = node_step_55(base_state)

        assert result["provider"]["estimate"] == 0.05
        assert result["provider"]["cost_details"]["input_tokens"] == 100
        assert result["estimated_cost"] == 0.05
        mock_orchestrator.assert_called_once_with(ctx=base_state)

    @patch('app.orchestrators.providers.step_55__estimate_cost')
    def test_estimate_cost_expensive(self, mock_orchestrator, base_state):
        """Test cost estimation for expensive query."""
        mock_orchestrator.return_value = {
            "estimated_cost": 2.50,
            "cost_details": {"input_tokens": 5000, "output_tokens": 3000}
        }

        result = node_step_55(base_state)

        assert result["provider"]["estimate"] == 2.50
        assert result["estimated_cost"] == 2.50

    @patch('app.orchestrators.providers.step_56__cost_check')
    def test_cost_check_approved(self, mock_orchestrator, base_state):
        """Test cost check when budget is approved."""
        base_state["provider"] = {"estimate": 0.05}
        mock_orchestrator.return_value = {
            "budget_ok": True,
            "cost_approved": True
        }

        result = node_step_56(base_state)

        assert result["provider"]["budget_ok"] is True
        assert result["decisions"]["cost_ok"] is True
        mock_orchestrator.assert_called_once_with(ctx=base_state)

    @patch('app.orchestrators.providers.step_56__cost_check')
    def test_cost_check_rejected(self, mock_orchestrator, base_state):
        """Test cost check when budget is rejected."""
        base_state["provider"] = {"estimate": 5.00}
        mock_orchestrator.return_value = {
            "budget_ok": False,
            "cost_approved": False
        }

        result = node_step_56(base_state)

        assert result["provider"]["budget_ok"] is False
        assert result["decisions"]["cost_ok"] is False

    @patch('app.orchestrators.providers.step_56__cost_check')
    def test_cost_check_with_cost_approved_field(self, mock_orchestrator, base_state):
        """Test cost check using cost_approved field."""
        base_state["provider"] = {"estimate": 0.75}
        mock_orchestrator.return_value = {
            "cost_approved": True
        }

        result = node_step_56(base_state)

        assert result["provider"]["cost_approved"] is True
        assert result["decisions"]["cost_ok"] is True

    @patch('app.orchestrators.providers.step_55__estimate_cost')
    def test_estimate_cost_preserves_existing_provider_data(self, mock_orchestrator, base_state):
        """Test that cost estimation preserves existing provider data."""
        base_state["provider"] = {
            "selected": "anthropic-claude-3",
            "strategy": "BEST"
        }
        mock_orchestrator.return_value = {"estimated_cost": 1.25}

        result = node_step_55(base_state)

        assert result["provider"]["selected"] == "anthropic-claude-3"
        assert result["provider"]["strategy"] == "BEST"
        assert result["provider"]["estimate"] == 1.25

    @patch('app.orchestrators.providers.step_56__cost_check')
    def test_cost_check_preserves_existing_provider_data(self, mock_orchestrator, base_state):
        """Test that cost check preserves existing provider data."""
        base_state["provider"] = {
            "selected": "openai-gpt-4",
            "estimate": 0.30,
            "strategy": "BALANCED"
        }
        mock_orchestrator.return_value = {"budget_ok": True}

        result = node_step_56(base_state)

        assert result["provider"]["selected"] == "openai-gpt-4"
        assert result["provider"]["estimate"] == 0.30
        assert result["provider"]["strategy"] == "BALANCED"
        assert result["provider"]["budget_ok"] is True