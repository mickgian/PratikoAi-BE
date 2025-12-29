"""TDD Tests for Step 100: Post-Response Proactivity Node (DEV-200).

This node adds suggested actions AFTER LLM response. It uses template actions
for recognized document types, or parses LLM response for contextual actions.

Test Strategy:
- Test document template actions for known document types
- Test LLM response parsing for suggested actions
- Test skip logic for pre-proactivity triggered (skip_rag_for_proactivity)
- Test skip logic for chitchat routes
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
# TestStep100PostProactivity - Core Functionality Tests
# =============================================================================
class TestStep100PostProactivity:
    """Tests for Step 100 Post-Response Proactivity node."""

    @pytest.mark.asyncio
    async def test_skip_if_pre_proactivity_triggered(self):
        """If pre-proactivity already triggered, skip post-proactivity."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        state = {
            "request_id": "test-req-101",
            "user_query": "Calcola l'IRPEF",
            "skip_rag_for_proactivity": True,  # Pre-proactivity already handled
            "proactivity": {
                "pre_response": {"question": {"id": "irpef_input_fields"}, "skip_rag": True},
                "post_response": {"actions": [], "source": None},
            },
        }

        result = await node_step_100(state)

        # Should not add actions since pre-proactivity handled it
        proactivity = result.get("proactivity", {})
        post_response = proactivity.get("post_response", {})
        assert post_response.get("actions") == []
        assert post_response.get("source") is None

    @pytest.mark.asyncio
    async def test_skip_chitchat_route(self):
        """Chitchat routes should not get suggested actions."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        state = {
            "request_id": "test-req-102",
            "user_query": "Ciao, come stai?",
            "routing_decision": {"route": "chitchat", "confidence": 0.95},
            "llm": {"response": {"content": "Ciao! Tutto bene, grazie!"}},
        }

        result = await node_step_100(state)

        proactivity = result.get("proactivity", {})
        post_response = proactivity.get("post_response", {})
        assert post_response.get("actions") == []

    @pytest.mark.asyncio
    async def test_document_template_actions_f24(self):
        """F24 document should get template actions."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        state = {
            "request_id": "test-req-103",
            "user_query": "Analizza questo F24",
            "attachments": [{"document_type": "f24", "id": "doc-001"}],
            "llm": {"response": {"content": "Ho analizzato il tuo F24..."}},
        }

        result = await node_step_100(state)

        proactivity = result.get("proactivity", {})
        post_response = proactivity.get("post_response", {})
        actions = post_response.get("actions", [])

        assert len(actions) > 0
        assert post_response.get("source") == "template"
        # F24 should have actions like "Verifica codici", "Scadenza", etc.
        action_ids = [a.get("id") for a in actions]
        assert "codes" in action_ids or "deadline" in action_ids or "ravvedimento" in action_ids

    @pytest.mark.asyncio
    async def test_document_template_actions_fattura(self):
        """Fattura elettronica document should get template actions."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        state = {
            "request_id": "test-req-104",
            "user_query": "Verifica questa fattura",
            "attachments": [{"document_type": "fattura_elettronica", "id": "doc-002"}],
            "llm": {"response": {"content": "Ho verificato la fattura..."}},
        }

        result = await node_step_100(state)

        proactivity = result.get("proactivity", {})
        post_response = proactivity.get("post_response", {})
        actions = post_response.get("actions", [])

        assert len(actions) > 0
        assert post_response.get("source") == "template"

    @pytest.mark.asyncio
    async def test_llm_parsed_actions(self):
        """LLM response with <suggested_actions> should be parsed."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        llm_response = """<answer>Ecco le informazioni sul forfettario.</answer>
<suggested_actions>
[
  {"id": "calc_taxes", "label": "Calcola tasse", "icon": "💰", "prompt": "Calcola le tasse per il forfettario"},
  {"id": "deadlines", "label": "Scadenze", "icon": "📅", "prompt": "Mostra le scadenze fiscali"}
]
</suggested_actions>"""

        state = {
            "request_id": "test-req-105",
            "user_query": "Come funziona il forfettario?",
            "routing_decision": {"route": "technical_research", "confidence": 0.9},
            "llm": {"response": {"content": llm_response}},
        }

        result = await node_step_100(state)

        proactivity = result.get("proactivity", {})
        post_response = proactivity.get("post_response", {})
        actions = post_response.get("actions", [])

        assert len(actions) == 2
        assert post_response.get("source") == "llm_parsed"
        assert actions[0]["id"] == "calc_taxes"
        assert actions[1]["id"] == "deadlines"

    @pytest.mark.asyncio
    async def test_empty_response_no_actions(self):
        """Empty LLM response should result in no actions."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        state = {
            "request_id": "test-req-106",
            "user_query": "Test query",
            "llm": {"response": {"content": ""}},
        }

        result = await node_step_100(state)

        proactivity = result.get("proactivity", {})
        post_response = proactivity.get("post_response", {})
        assert post_response.get("actions") == []

    @pytest.mark.asyncio
    async def test_action_schema_valid(self):
        """Actions should have valid schema for frontend."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        state = {
            "request_id": "test-req-107",
            "user_query": "Analizza questo F24",
            "attachments": [{"document_type": "f24", "id": "doc-003"}],
            "llm": {"response": {"content": "Analisi completata."}},
        }

        result = await node_step_100(state)

        proactivity = result.get("proactivity", {})
        actions = proactivity.get("post_response", {}).get("actions", [])

        assert len(actions) > 0
        for action in actions:
            # Required fields for Action
            assert "id" in action
            assert "label" in action
            assert "icon" in action
            assert "prompt" in action

    @pytest.mark.asyncio
    async def test_error_handling_continues_without_actions(self):
        """Service errors should log warning and continue without actions."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        with patch("app.services.proactivity_graph_service.get_proactivity_graph_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_document_actions.side_effect = Exception("Test error")
            mock_service.parse_llm_actions.side_effect = Exception("Test error")
            mock_get_service.return_value = mock_service

            state = {
                "request_id": "test-req-108",
                "user_query": "Test query",
                "attachments": [{"document_type": "f24", "id": "doc-004"}],
                "llm": {"response": {"content": "Response"}},
            }

            # Should not raise, should gracefully degrade
            result = await node_step_100(state)

            proactivity = result.get("proactivity", {})
            post_response = proactivity.get("post_response", {})
            # On error, should return empty actions
            assert post_response.get("actions") == []

    @pytest.mark.asyncio
    async def test_state_serializable(self):
        """Output state should be JSON serializable for checkpointing."""
        import json

        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        state = {
            "request_id": "test-req-109",
            "user_query": "Analizza questo bilancio",
            "attachments": [{"document_type": "bilancio", "id": "doc-005"}],
            "llm": {"response": {"content": "Analisi bilancio completata."}},
        }

        result = await node_step_100(state)

        # Should be JSON serializable
        try:
            json.dumps(result)
        except (TypeError, ValueError) as e:
            pytest.fail(f"Result not JSON serializable: {e}")

    @pytest.mark.asyncio
    async def test_template_actions_override_llm(self):
        """Document template actions should take priority over LLM actions."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        # LLM response has actions, but document type should override
        llm_response = """<answer>Ecco la fattura.</answer>
<suggested_actions>
[{"id": "llm_action", "label": "LLM Action", "icon": "🤖", "prompt": "LLM generated"}]
</suggested_actions>"""

        state = {
            "request_id": "test-req-110",
            "user_query": "Verifica questa fattura",
            "attachments": [{"document_type": "fattura_elettronica", "id": "doc-006"}],
            "llm": {"response": {"content": llm_response}},
        }

        result = await node_step_100(state)

        proactivity = result.get("proactivity", {})
        post_response = proactivity.get("post_response", {})

        # Should use template actions, not LLM parsed
        assert post_response.get("source") == "template"
        actions = post_response.get("actions", [])
        # Template actions for fattura_elettronica don't include "llm_action"
        action_ids = [a.get("id") for a in actions]
        assert "llm_action" not in action_ids


# =============================================================================
# TestStep100ProactivityService - Service Integration Tests
# =============================================================================
class TestStep100ProactivityService:
    """Tests for ProactivityGraphService integration with Step 100."""

    def test_get_document_actions_f24(self):
        """Test F24 document actions retrieval."""
        from app.services.proactivity_graph_service import get_proactivity_graph_service

        service = get_proactivity_graph_service()
        actions = service.get_document_actions("f24")

        assert actions is not None
        assert len(actions) > 0
        # F24 has "codes", "deadline", "ravvedimento"
        action_ids = [a.get("id") for a in actions]
        assert "codes" in action_ids

    def test_get_document_actions_unknown_type(self):
        """Unknown document type should return None."""
        from app.services.proactivity_graph_service import get_proactivity_graph_service

        service = get_proactivity_graph_service()
        actions = service.get_document_actions("unknown_type")

        assert actions is None

    def test_parse_llm_actions_with_tags(self):
        """Test LLM response parsing with suggested_actions tags."""
        from app.services.proactivity_graph_service import get_proactivity_graph_service

        service = get_proactivity_graph_service()

        llm_response = """<answer>Answer text.</answer>
<suggested_actions>
[{"id": "action1", "label": "Action 1", "icon": "🔍", "prompt": "Prompt 1"}]
</suggested_actions>"""

        actions = service.parse_llm_actions(llm_response)

        assert len(actions) == 1
        assert actions[0]["id"] == "action1"

    def test_parse_llm_actions_no_tags(self):
        """Test LLM response without tags returns empty list."""
        from app.services.proactivity_graph_service import get_proactivity_graph_service

        service = get_proactivity_graph_service()
        actions = service.parse_llm_actions("Just a plain response without tags.")

        assert actions == []


# =============================================================================
# TestStep100VerdettoExtraction - VERDETTO Extraction Tests (DEV-200 Phase 2)
# =============================================================================
class TestStep100VerdettoExtraction:
    """Tests for VERDETTO extraction in technical_research routes."""

    @pytest.mark.asyncio
    async def test_verdetto_extracts_azione_consigliata(self):
        """technical_research route with VERDETTO extracts azione_consigliata."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        state = {
            "request_id": "test-verdetto-001",
            "user_query": "Parlami della rottamazione quinquies",
            "routing_decision": {"route": "technical_research", "confidence": 0.9},
            "parsed_synthesis": {
                "verdetto": {
                    "azione_consigliata": "Verificare i requisiti per l'adesione alla rottamazione quinquies",
                    "analisi_rischio": None,
                    "scadenza": "Nessuna scadenza critica rilevata",
                    "documentazione": [],
                    "indice_fonti": [],
                },
            },
            "llm": {"response": {"content": "Risposta sulla rottamazione..."}},
        }

        result = await node_step_100(state)

        proactivity = result.get("proactivity", {})
        post_response = proactivity.get("post_response", {})
        actions = post_response.get("actions", [])

        assert post_response.get("source") == "verdetto"
        assert len(actions) >= 1
        assert actions[0]["id"] == "azione_consigliata"
        assert actions[0]["label"] == "Segui consiglio"
        assert actions[0]["icon"] == "✅"
        assert "rottamazione" in actions[0]["prompt"].lower()

    @pytest.mark.asyncio
    async def test_verdetto_includes_scadenza_action(self):
        """VERDETTO with valid scadenza adds scadenza action."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        state = {
            "request_id": "test-verdetto-002",
            "user_query": "Scadenza F24",
            "routing_decision": {"route": "technical_research", "confidence": 0.9},
            "parsed_synthesis": {
                "verdetto": {
                    "azione_consigliata": "Pagare l'F24 entro la scadenza",
                    "analisi_rischio": None,
                    "scadenza": "16 gennaio 2025 - Versamento ritenute",
                    "documentazione": [],
                    "indice_fonti": [],
                },
            },
            "llm": {"response": {"content": "..."}},
        }

        result = await node_step_100(state)

        proactivity = result.get("proactivity", {})
        actions = proactivity.get("post_response", {}).get("actions", [])

        action_ids = [a["id"] for a in actions]
        assert "scadenza" in action_ids

        scadenza_action = next(a for a in actions if a["id"] == "scadenza")
        assert scadenza_action["icon"] == "📅"
        assert "16 gennaio 2025" in scadenza_action["prompt"]

    @pytest.mark.asyncio
    async def test_verdetto_skips_nessuna_scadenza(self):
        """VERDETTO with 'Nessuna scadenza' does not add scadenza action."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        state = {
            "request_id": "test-verdetto-003",
            "user_query": "Forfettario",
            "routing_decision": {"route": "technical_research", "confidence": 0.9},
            "parsed_synthesis": {
                "verdetto": {
                    "azione_consigliata": "Verificare i requisiti del forfettario",
                    "analisi_rischio": None,
                    "scadenza": "Nessuna scadenza critica rilevata",
                    "documentazione": [],
                    "indice_fonti": [],
                },
            },
            "llm": {"response": {"content": "..."}},
        }

        result = await node_step_100(state)

        proactivity = result.get("proactivity", {})
        actions = proactivity.get("post_response", {}).get("actions", [])

        action_ids = [a["id"] for a in actions]
        assert "scadenza" not in action_ids

    @pytest.mark.asyncio
    async def test_verdetto_includes_rischio_action(self):
        """VERDETTO with analisi_rischio adds rischio action."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        state = {
            "request_id": "test-verdetto-004",
            "user_query": "Rischi evasione",
            "routing_decision": {"route": "technical_research", "confidence": 0.9},
            "parsed_synthesis": {
                "verdetto": {
                    "azione_consigliata": "Regolarizzare la posizione",
                    "analisi_rischio": "Sanzioni dal 30% al 240% dell'imposta evasa",
                    "scadenza": None,
                    "documentazione": [],
                    "indice_fonti": [],
                },
            },
            "llm": {"response": {"content": "..."}},
        }

        result = await node_step_100(state)

        proactivity = result.get("proactivity", {})
        actions = proactivity.get("post_response", {}).get("actions", [])

        action_ids = [a["id"] for a in actions]
        assert "rischio" in action_ids

        rischio_action = next(a for a in actions if a["id"] == "rischio")
        assert rischio_action["icon"] == "⚠️"

    @pytest.mark.asyncio
    async def test_verdetto_fallback_to_llm_parsed_when_no_azione(self):
        """technical_research without azione_consigliata falls back to llm_parsed."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        llm_response = """<answer>Risposta</answer>
<suggested_actions>
[{"id": "fallback", "label": "Fallback", "icon": "🔄", "prompt": "Fallback action"}]
</suggested_actions>"""

        state = {
            "request_id": "test-verdetto-005",
            "user_query": "Query",
            "routing_decision": {"route": "technical_research", "confidence": 0.9},
            "parsed_synthesis": {
                "verdetto": {
                    "azione_consigliata": None,  # No action
                    "analisi_rischio": None,
                    "scadenza": None,
                    "documentazione": [],
                    "indice_fonti": [],
                },
            },
            "llm": {"response": {"content": llm_response}},
        }

        result = await node_step_100(state)

        proactivity = result.get("proactivity", {})
        post_response = proactivity.get("post_response", {})

        assert post_response.get("source") == "llm_parsed"
        assert post_response.get("actions", [])[0]["id"] == "fallback"

    @pytest.mark.asyncio
    async def test_non_synthesis_route_uses_llm_parsed(self):
        """Non-synthesis routes (theoretical_definition) use llm_parsed."""
        from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

        llm_response = """<answer>Definizione</answer>
<suggested_actions>
[{"id": "definition_action", "label": "Approfondisci", "icon": "📖", "prompt": "Altro"}]
</suggested_actions>"""

        state = {
            "request_id": "test-verdetto-006",
            "user_query": "Cos'è il forfettario?",
            "routing_decision": {"route": "theoretical_definition", "confidence": 0.9},
            "llm": {"response": {"content": llm_response}},
        }

        result = await node_step_100(state)

        proactivity = result.get("proactivity", {})
        post_response = proactivity.get("post_response", {})

        assert post_response.get("source") == "llm_parsed"
        assert post_response.get("actions", [])[0]["id"] == "definition_action"
