"""TDD Tests for Step 14: Pre-Response Proactivity Node (DEV-200).

This node checks if a calculable intent (IRPEF, IVA, INPS, etc.) has missing
parameters BEFORE RAG execution. If missing, it returns an InteractiveQuestion
and sets skip_rag_for_proactivity=True to bypass RAG.

Test Strategy:
- Test intent classification for calculable queries
- Test parameter detection in queries
- Test InteractiveQuestion generation for missing params
- Test skip_rag flag setting
- Test non-calculable queries pass through without question
- Test error handling and graceful degradation
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Mock database service BEFORE importing any app modules
# =============================================================================
_mock_db_service = MagicMock()
_mock_db_service.engine = MagicMock()
_mock_db_service.get_session = MagicMock()
_mock_db_module = MagicMock()
_mock_db_module.database_service = _mock_db_service
_mock_db_module.DatabaseService = MagicMock(return_value=_mock_db_service)
sys.modules.setdefault("app.services.database", _mock_db_module)


# =============================================================================
# TestStep14PreProactivity - Core Functionality Tests
# =============================================================================
class TestStep14PreProactivity:
    """Tests for Step 14 Pre-Response Proactivity node."""

    @pytest.mark.asyncio
    async def test_skip_non_calculator_route(self):
        """Non-calculator routes should skip proactivity check."""
        from app.core.langgraph.nodes.step_014__pre_proactivity import node_step_14

        state = {
            "request_id": "test-req-001",
            "user_query": "Ciao, come stai?",  # Chitchat, not calculator
            "messages": [{"role": "user", "content": "Ciao, come stai?"}],
            "routing_decision": {"route": "chitchat", "confidence": 0.95},
        }

        result = await node_step_14(state)

        # Should not have question or skip flag
        proactivity = result.get("proactivity", {})
        pre_response = proactivity.get("pre_response", {})
        assert pre_response.get("question") is None
        assert pre_response.get("skip_rag") is False
        assert result.get("skip_rag_for_proactivity") is not True

    @pytest.mark.asyncio
    async def test_skip_no_routing_decision(self):
        """Early pipeline state without routing_decision should skip."""
        from app.core.langgraph.nodes.step_014__pre_proactivity import node_step_14

        state = {
            "request_id": "test-req-002",
            "user_query": "Come funziona il forfettario?",
            "messages": [{"role": "user", "content": "Come funziona il forfettario?"}],
            # No routing_decision yet
        }

        result = await node_step_14(state)

        # Should still check intent patterns directly
        proactivity = result.get("proactivity", {})
        pre_response = proactivity.get("pre_response", {})
        # This is an info query, not calculator - no question expected
        assert pre_response.get("skip_rag") is False

    @pytest.mark.asyncio
    async def test_irpef_query_missing_params_returns_question(self):
        """'Calcola IRPEF' without income should trigger InteractiveQuestion."""
        from app.core.langgraph.nodes.step_014__pre_proactivity import node_step_14

        state = {
            "request_id": "test-req-003",
            "user_query": "Calcola l'IRPEF",  # Missing reddito and tipo_contribuente
            "messages": [{"role": "user", "content": "Calcola l'IRPEF"}],
        }

        result = await node_step_14(state)

        proactivity = result.get("proactivity", {})
        pre_response = proactivity.get("pre_response", {})

        # Should have question
        assert pre_response.get("question") is not None
        question = pre_response["question"]
        assert "irpef" in question.get("id", "").lower()
        assert question.get("question_type") == "multi_field"
        assert len(question.get("fields", [])) > 0

        # Should set skip_rag flag
        assert pre_response.get("skip_rag") is True
        assert result.get("skip_rag_for_proactivity") is True

    @pytest.mark.asyncio
    async def test_iva_query_missing_params_returns_question(self):
        """'Calcola IVA' without amount should trigger InteractiveQuestion."""
        from app.core.langgraph.nodes.step_014__pre_proactivity import node_step_14

        state = {
            "request_id": "test-req-004",
            "user_query": "Quanto è l'IVA?",  # Missing importo
            "messages": [{"role": "user", "content": "Quanto è l'IVA?"}],
        }

        result = await node_step_14(state)

        proactivity = result.get("proactivity", {})
        pre_response = proactivity.get("pre_response", {})

        # Should have question
        assert pre_response.get("question") is not None
        question = pre_response["question"]
        assert "iva" in question.get("id", "").lower()
        assert pre_response.get("skip_rag") is True

    @pytest.mark.asyncio
    async def test_all_params_present_no_question(self):
        """Query with all required params should continue to RAG."""
        from app.core.langgraph.nodes.step_014__pre_proactivity import node_step_14

        state = {
            "request_id": "test-req-005",
            "user_query": "Calcola l'IRPEF su un reddito di 45000 euro come dipendente",
            "messages": [
                {
                    "role": "user",
                    "content": "Calcola l'IRPEF su un reddito di 45000 euro come dipendente",
                }
            ],
        }

        result = await node_step_14(state)

        proactivity = result.get("proactivity", {})
        pre_response = proactivity.get("pre_response", {})

        # Should NOT have question - all params present
        assert pre_response.get("question") is None
        assert pre_response.get("skip_rag") is False
        assert result.get("skip_rag_for_proactivity") is not True

    @pytest.mark.asyncio
    async def test_sets_skip_rag_flag_when_question(self):
        """Verify skip_rag_for_proactivity flag is set in state."""
        from app.core.langgraph.nodes.step_014__pre_proactivity import node_step_14

        state = {
            "request_id": "test-req-006",
            "user_query": "Calcolami l'IVA",
            "messages": [{"role": "user", "content": "Calcolami l'IVA"}],
        }

        result = await node_step_14(state)

        # Both locations should have skip_rag=True
        assert result.get("skip_rag_for_proactivity") is True
        proactivity = result.get("proactivity", {})
        assert proactivity.get("pre_response", {}).get("skip_rag") is True

    @pytest.mark.asyncio
    async def test_question_schema_valid(self):
        """InteractiveQuestion should have valid schema for frontend."""
        from app.core.langgraph.nodes.step_014__pre_proactivity import node_step_14

        state = {
            "request_id": "test-req-007",
            "user_query": "Calcola i contributi INPS",
            "messages": [{"role": "user", "content": "Calcola i contributi INPS"}],
        }

        result = await node_step_14(state)

        proactivity = result.get("proactivity", {})
        question = proactivity.get("pre_response", {}).get("question")

        assert question is not None
        # Required fields for InteractiveQuestion
        assert "id" in question
        assert "question_type" in question
        assert "text" in question
        assert "fields" in question
        assert isinstance(question["fields"], list)

        # Each field should have required properties
        for field in question["fields"]:
            assert "id" in field
            assert "label" in field
            assert "input_type" in field

    @pytest.mark.asyncio
    async def test_error_handling_continues_without_question(self):
        """Service errors should log warning and continue without question."""
        from app.core.langgraph.nodes.step_014__pre_proactivity import node_step_14

        with patch("app.services.proactivity_graph_service.get_proactivity_graph_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.check_calculable_intent.side_effect = Exception("Test error")
            mock_get_service.return_value = mock_service

            state = {
                "request_id": "test-req-008",
                "user_query": "Calcola IRPEF",
                "messages": [{"role": "user", "content": "Calcola IRPEF"}],
            }

            # Should not raise, should gracefully degrade
            result = await node_step_14(state)

            proactivity = result.get("proactivity", {})
            pre_response = proactivity.get("pre_response", {})
            # On error, should not have question and should not skip RAG
            assert pre_response.get("skip_rag") is False

    @pytest.mark.asyncio
    async def test_state_serializable(self):
        """Output state should be JSON serializable for checkpointing."""
        import json

        from app.core.langgraph.nodes.step_014__pre_proactivity import node_step_14

        state = {
            "request_id": "test-req-009",
            "user_query": "Calcola l'IRPEF",
            "messages": [{"role": "user", "content": "Calcola l'IRPEF"}],
        }

        result = await node_step_14(state)

        # Should be JSON serializable
        try:
            json.dumps(result)
        except (TypeError, ValueError) as e:
            pytest.fail(f"Result not JSON serializable: {e}")

    @pytest.mark.asyncio
    async def test_empty_query_no_question(self):
        """Empty query should skip proactivity without question."""
        from app.core.langgraph.nodes.step_014__pre_proactivity import node_step_14

        state = {
            "request_id": "test-req-010",
            "user_query": "",
            "messages": [],
        }

        result = await node_step_14(state)

        proactivity = result.get("proactivity", {})
        pre_response = proactivity.get("pre_response", {})
        assert pre_response.get("question") is None
        assert pre_response.get("skip_rag") is False


# =============================================================================
# TestStep14ProactivityService - Service Integration Tests
# =============================================================================
class TestStep14ProactivityService:
    """Tests for ProactivityGraphService integration with Step 14."""

    def test_service_singleton_created(self):
        """Verify service singleton is properly created."""
        from app.services.proactivity_graph_service import get_proactivity_graph_service

        service1 = get_proactivity_graph_service()
        service2 = get_proactivity_graph_service()

        assert service1 is service2  # Same instance

    def test_check_calculable_intent_irpef(self):
        """Test IRPEF intent detection."""
        from app.services.proactivity_graph_service import get_proactivity_graph_service

        service = get_proactivity_graph_service()

        needs_question, question = service.check_calculable_intent("Calcola l'IRPEF")

        assert needs_question is True
        assert question is not None
        assert "irpef" in question.get("id", "").lower()

    def test_check_calculable_intent_with_params(self):
        """Test that queries with params don't trigger question."""
        from app.services.proactivity_graph_service import get_proactivity_graph_service

        service = get_proactivity_graph_service()

        needs_question, question = service.check_calculable_intent("Calcola l'IVA su 1000 euro")

        # importo is provided (1000), so no question needed
        assert needs_question is False
        assert question is None

    def test_check_non_calculable_intent(self):
        """Test that non-calculable queries don't trigger question."""
        from app.services.proactivity_graph_service import get_proactivity_graph_service

        service = get_proactivity_graph_service()

        needs_question, question = service.check_calculable_intent("Quali sono le scadenze fiscali?")

        assert needs_question is False
        assert question is None
