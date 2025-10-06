"""Test provider strategy branches routing."""

import pytest
from unittest.mock import patch, MagicMock

from app.core.langgraph.types import RAGState
from app.core.langgraph.nodes.step_050__strategy_type import node_step_50
from app.core.langgraph.nodes.step_051__cheap_provider import node_step_51
from app.core.langgraph.nodes.step_052__best_provider import node_step_52
from app.core.langgraph.nodes.step_053__balance_provider import node_step_53
from app.core.langgraph.nodes.step_054__primary_provider import node_step_54


class TestProviderStrategyBranches:
    """Test provider strategy routing to correct nodes."""

    @pytest.fixture
    def base_state(self):
        """Base test state."""
        return {
            "messages": [{"role": "user", "content": "test"}],
            "provider": {},
            "decisions": {}
        }

    @patch('app.orchestrators.platform.step_50__strategy_type')
    def test_strategy_type_cheap(self, mock_orchestrator, base_state):
        """Test routing to CHEAP strategy."""
        mock_orchestrator.return_value = {"strategy_type": "CHEAP"}

        result = node_step_50(base_state)

        assert result["decisions"]["strategy_type"] == "CHEAP"
        mock_orchestrator.assert_called_once_with(ctx=base_state)

    @patch('app.orchestrators.platform.step_50__strategy_type')
    def test_strategy_type_best(self, mock_orchestrator, base_state):
        """Test routing to BEST strategy."""
        mock_orchestrator.return_value = {"strategy_type": "BEST"}

        result = node_step_50(base_state)

        assert result["decisions"]["strategy_type"] == "BEST"

    @patch('app.orchestrators.platform.step_50__strategy_type')
    def test_strategy_type_balanced(self, mock_orchestrator, base_state):
        """Test routing to BALANCED strategy."""
        mock_orchestrator.return_value = {"strategy_type": "BALANCED"}

        result = node_step_50(base_state)

        assert result["decisions"]["strategy_type"] == "BALANCED"

    @patch('app.orchestrators.platform.step_50__strategy_type')
    def test_strategy_type_primary(self, mock_orchestrator, base_state):
        """Test routing to PRIMARY strategy."""
        mock_orchestrator.return_value = {"strategy_type": "PRIMARY"}

        result = node_step_50(base_state)

        assert result["decisions"]["strategy_type"] == "PRIMARY"

    @patch('app.orchestrators.providers.step_51__cheap_provider')
    def test_cheap_provider_node(self, mock_orchestrator, base_state):
        """Test cheap provider node execution."""
        mock_orchestrator.return_value = {"provider": "openai-gpt-3.5-turbo"}

        result = node_step_51(base_state)

        assert result["provider"]["selected"] == "openai-gpt-3.5-turbo"
        assert result["provider"]["strategy"] == "CHEAP"
        assert result["provider_choice"] == "openai-gpt-3.5-turbo"
        assert result["route_strategy"] == "CHEAP"

    @patch('app.orchestrators.providers.step_52__best_provider')
    def test_best_provider_node(self, mock_orchestrator, base_state):
        """Test best provider node execution."""
        mock_orchestrator.return_value = {"provider": "anthropic-claude-3"}

        result = node_step_52(base_state)

        assert result["provider"]["selected"] == "anthropic-claude-3"
        assert result["provider"]["strategy"] == "BEST"

    @patch('app.orchestrators.providers.step_53__balance_provider')
    def test_balance_provider_node(self, mock_orchestrator, base_state):
        """Test balance provider node execution."""
        mock_orchestrator.return_value = {"provider": "openai-gpt-4"}

        result = node_step_53(base_state)

        assert result["provider"]["selected"] == "openai-gpt-4"
        assert result["provider"]["strategy"] == "BALANCED"

    @patch('app.orchestrators.providers.step_54__primary_provider')
    def test_primary_provider_node(self, mock_orchestrator, base_state):
        """Test primary provider node execution."""
        mock_orchestrator.return_value = {"provider": "default-provider"}

        result = node_step_54(base_state)

        assert result["provider"]["selected"] == "default-provider"
        assert result["provider"]["strategy"] == "PRIMARY"