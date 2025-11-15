"""Test state integrity throughout Phase 5 provider lane."""

from unittest.mock import patch

import pytest

from app.core.langgraph.nodes.step_048__select_provider import node_step_48
from app.core.langgraph.nodes.step_049__route_strategy import node_step_49
from app.core.langgraph.nodes.step_050__strategy_type import node_step_50
from app.core.langgraph.nodes.step_051__cheap_provider import node_step_51
from app.core.langgraph.nodes.step_055__estimate_cost import node_step_55
from app.core.langgraph.nodes.step_056__cost_check import node_step_56
from app.core.langgraph.nodes.step_057__create_provider import node_step_57
from app.core.langgraph.types import RAGState


class TestStateIntegrity:
    """Test state integrity throughout the provider lane."""

    @pytest.fixture
    def initial_state(self):
        """Initial state with required fields."""
        return {
            "request_id": "test-123",
            "messages": [{"role": "user", "content": "test query"}],
            "user_id": "user-456",
            "streaming": False,
            "provider": {},
            "decisions": {},
            "metrics": {},
        }

    def test_full_lane_state_flow(self, initial_state):
        """Test full provider lane flow maintains state integrity."""
        with (
            patch("app.orchestrators.providers.step_48__select_provider") as mock_48,
            patch("app.orchestrators.facts.step_49__route_strategy") as mock_49,
            patch("app.orchestrators.platform.step_50__strategy_type") as mock_50,
            patch("app.orchestrators.providers.step_51__cheap_provider") as mock_51,
            patch("app.orchestrators.providers.step_55__estimate_cost") as mock_55,
            patch("app.orchestrators.providers.step_56__cost_check") as mock_56,
            patch("app.orchestrators.providers.step_57__create_provider") as mock_57,
        ):
            # Step 48: Select Provider
            mock_48.return_value = {"strategy": "cost_optimization"}
            state = node_step_48(initial_state)

            assert state["request_id"] == "test-123"
            assert state["messages"][0]["content"] == "test query"
            assert state["provider"]["strategy"] == "cost_optimization"

            # Step 49: Route Strategy
            mock_49.return_value = {"routing_strategy": "dynamic"}
            state = node_step_49(state)

            assert state["provider"]["routing_strategy"] == "dynamic"
            assert state["provider"]["strategy"] == "cost_optimization"  # preserved

            # Step 50: Strategy Type
            mock_50.return_value = {"strategy_type": "CHEAP"}
            state = node_step_50(state)

            assert state["decisions"]["strategy_type"] == "CHEAP"
            assert state["provider"]["strategy"] == "cost_optimization"  # preserved

            # Step 51: Cheap Provider
            mock_51.return_value = {"provider": "openai-gpt-3.5-turbo"}
            state = node_step_51(state)

            assert state["provider"]["selected"] == "openai-gpt-3.5-turbo"
            assert state["provider"]["strategy"] == "CHEAP"
            assert state["provider_choice"] == "openai-gpt-3.5-turbo"

            # Step 55: Estimate Cost
            mock_55.return_value = {"estimated_cost": 0.05}
            state = node_step_55(state)

            assert state["provider"]["estimate"] == 0.05
            assert state["estimated_cost"] == 0.05
            assert state["provider"]["selected"] == "openai-gpt-3.5-turbo"  # preserved

            # Step 56: Cost Check
            mock_56.return_value = {"budget_ok": True}
            state = node_step_56(state)

            assert state["decisions"]["cost_ok"] is True
            assert state["provider"]["budget_ok"] is True
            assert state["provider"]["estimate"] == 0.05  # preserved

            # Step 57: Create Provider
            mock_57.return_value = {"provider_created": True, "provider_instance": "instance-123"}
            state = node_step_57(state)

            assert state["provider"]["created"] is True
            assert state["provider"]["instance"] == "instance-123"

            # Verify no unexpected state keys changed
            assert state["request_id"] == "test-123"
            assert state["user_id"] == "user-456"
            assert state["streaming"] is False
            assert len(state["messages"]) == 1

    def test_state_keys_not_corrupted(self, initial_state):
        """Test that existing state keys are not corrupted by provider nodes."""
        # Add some existing state that should be preserved
        initial_state.update(
            {
                "cache_key": "existing-cache-key",
                "privacy_enabled": True,
                "pii_detected": False,
                "atomic_facts": [{"fact": "test"}],
                "kb_docs": [{"doc": "test-doc"}],
            }
        )

        with patch("app.orchestrators.providers.step_48__select_provider") as mock_48:
            mock_48.return_value = {"strategy": "test"}

            result = node_step_48(initial_state)

            # Verify existing keys preserved
            assert result["cache_key"] == "existing-cache-key"
            assert result["privacy_enabled"] is True
            assert result["pii_detected"] is False
            assert result["atomic_facts"][0]["fact"] == "test"
            assert result["kb_docs"][0]["doc"] == "test-doc"

            # Verify new provider data added
            assert result["provider"]["strategy"] == "test"

    def test_provider_dict_updates_are_additive(self, initial_state):
        """Test that provider dictionary updates are additive, not replacing."""
        # Start with some provider data
        initial_state["provider"] = {"existing_field": "should_remain", "another_field": 42}

        with patch("app.orchestrators.providers.step_48__select_provider") as mock_48:
            mock_48.return_value = {"strategy": "new_strategy"}

            result = node_step_48(initial_state)

            # Verify existing provider data preserved
            assert result["provider"]["existing_field"] == "should_remain"
            assert result["provider"]["another_field"] == 42

            # Verify new data added
            assert result["provider"]["strategy"] == "new_strategy"

    def test_decisions_dict_updates_are_additive(self, initial_state):
        """Test that decisions dictionary updates are additive."""
        # Start with some decisions
        initial_state["decisions"] = {"existing_decision": "keep_this", "previous_step": True}

        with patch("app.orchestrators.platform.step_50__strategy_type") as mock_50:
            mock_50.return_value = {"strategy_type": "BALANCED"}

            result = node_step_50(initial_state)

            # Verify existing decisions preserved
            assert result["decisions"]["existing_decision"] == "keep_this"
            assert result["decisions"]["previous_step"] is True

            # Verify new decision added
            assert result["decisions"]["strategy_type"] == "BALANCED"

    def test_legacy_compatibility_fields(self, initial_state):
        """Test that legacy compatibility fields are maintained."""
        with patch("app.orchestrators.providers.step_51__cheap_provider") as mock_51:
            mock_51.return_value = {"provider": "test-provider"}

            result = node_step_51(initial_state)

            # Verify both new and legacy fields are set
            assert result["provider"]["selected"] == "test-provider"
            assert result["provider_choice"] == "test-provider"  # legacy field
            assert result["route_strategy"] == "CHEAP"  # legacy field
