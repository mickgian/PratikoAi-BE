"""Smoke tests for metrics and logging in Phase 5 nodes."""

from unittest.mock import MagicMock, call, patch

import pytest

from app.core.langgraph.nodes.step_048__select_provider import node_step_48
from app.core.langgraph.nodes.step_055__estimate_cost import node_step_55
from app.core.langgraph.nodes.step_056__cost_check import node_step_56
from app.core.langgraph.types import RAGState


class TestMetricsLogsSmoke:
    """Smoke tests for metrics and logging functionality."""

    @pytest.fixture
    def base_state(self):
        """Base test state."""
        return {"messages": [{"role": "user", "content": "test"}], "provider": {}, "decisions": {}}

    @patch("app.core.langgraph.types.rag_step_log")
    @patch("app.core.langgraph.types.rag_step_timer")
    @patch("app.orchestrators.providers.step_48__select_provider")
    def test_step_48_logging_and_timing(self, mock_orchestrator, mock_timer, mock_log, base_state):
        """Test that Step 48 calls logging and timing functions."""
        mock_orchestrator.return_value = {"strategy": "test_strategy"}
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        result = node_step_48(base_state)

        # Verify timer was called
        mock_timer.assert_called_once_with(48)

        # Verify logging was called at enter and exit
        assert mock_log.call_count == 2
        mock_log.assert_has_calls(
            [call(48, "enter", keys=list(base_state.keys())), call(48, "exit", provider=result["provider"])]
        )

    @patch("app.core.langgraph.types.rag_step_log")
    @patch("app.core.langgraph.types.rag_step_timer")
    @patch("app.orchestrators.providers.step_55__estimate_cost")
    def test_step_55_logging_with_cost_data(self, mock_orchestrator, mock_timer, mock_log, base_state):
        """Test that Step 55 logs cost estimation data."""
        mock_orchestrator.return_value = {"estimated_cost": 1.25}
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        result = node_step_55(base_state)

        # Verify exit log includes cost estimate
        mock_log.assert_any_call(55, "exit", provider=result["provider"], estimate=1.25)

    @patch("app.core.langgraph.types.rag_step_log")
    @patch("app.core.langgraph.types.rag_step_timer")
    @patch("app.orchestrators.providers.step_56__cost_check")
    def test_step_56_logging_with_decision_data(self, mock_orchestrator, mock_timer, mock_log, base_state):
        """Test that Step 56 logs decision data."""
        mock_orchestrator.return_value = {"budget_ok": True}
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        result = node_step_56(base_state)

        # Verify exit log includes decisions
        mock_log.assert_any_call(56, "exit", provider=result["provider"], decisions=result["decisions"])

    @patch("app.core.langgraph.types.rag_step_log")
    @patch("app.orchestrators.providers.step_48__select_provider")
    def test_logging_with_exception_handling(self, mock_orchestrator, mock_log, base_state):
        """Test that logging continues to work even if orchestrator raises exception."""
        mock_orchestrator.side_effect = Exception("Test exception")

        with pytest.raises(Exception, match="Test exception"):
            node_step_48(base_state)

        # Verify enter log was called despite exception
        mock_log.assert_any_call(48, "enter", keys=list(base_state.keys()))

    @patch("app.core.langgraph.types.rag_step_timer")
    @patch("app.orchestrators.providers.step_48__select_provider")
    def test_timer_context_manager_usage(self, mock_orchestrator, mock_timer, base_state):
        """Test that timer is used as a context manager."""
        mock_orchestrator.return_value = {"strategy": "test"}
        mock_context = MagicMock()
        mock_timer.return_value = mock_context

        node_step_48(base_state)

        # Verify timer was used as context manager
        mock_timer.assert_called_once_with(48)
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()

    def test_all_phase5_nodes_have_logging(self):
        """Smoke test that all Phase 5 nodes import and use logging functions."""
        from app.core.langgraph.nodes import (
            step_048__select_provider,
            step_049__route_strategy,
            step_050__strategy_type,
            step_051__cheap_provider,
            step_052__best_provider,
            step_053__balance_provider,
            step_054__primary_provider,
            step_055__estimate_cost,
            step_056__cost_check,
            step_057__create_provider,
            step_058__cheaper_provider,
        )

        # Check that all modules import the required functions
        modules = [
            step_048__select_provider,
            step_049__route_strategy,
            step_050__strategy_type,
            step_051__cheap_provider,
            step_052__best_provider,
            step_053__balance_provider,
            step_054__primary_provider,
            step_055__estimate_cost,
            step_056__cost_check,
            step_057__create_provider,
            step_058__cheaper_provider,
        ]

        for module in modules:
            # Verify each module has the required imports
            assert hasattr(module, "rag_step_log"), f"{module.__name__} missing rag_step_log import"
            assert hasattr(module, "rag_step_timer"), f"{module.__name__} missing rag_step_timer import"
            assert hasattr(module, "STEP"), f"{module.__name__} missing STEP constant"

    def test_step_constants_are_correct(self):
        """Test that STEP constants match expected values."""
        from app.core.langgraph.nodes import (
            step_048__select_provider,
            step_049__route_strategy,
            step_050__strategy_type,
            step_051__cheap_provider,
            step_052__best_provider,
            step_053__balance_provider,
            step_054__primary_provider,
            step_055__estimate_cost,
            step_056__cost_check,
            step_057__create_provider,
            step_058__cheaper_provider,
        )

        expected_steps = {
            step_048__select_provider: 48,
            step_049__route_strategy: 49,
            step_050__strategy_type: 50,
            step_051__cheap_provider: 51,
            step_052__best_provider: 52,
            step_053__balance_provider: 53,
            step_054__primary_provider: 54,
            step_055__estimate_cost: 55,
            step_056__cost_check: 56,
            step_057__create_provider: 57,
            step_058__cheaper_provider: 58,
        }

        for module, expected_step in expected_steps.items():
            assert expected_step == module.STEP, f"{module.__name__} has incorrect STEP constant"
