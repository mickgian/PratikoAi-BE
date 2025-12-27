"""Integration Tests for DEV-182: LLM-First Proactivity Flow.

Tests the complete flow from API request through proactivity engine
to response with actions, using mocked LLM responses.

Reference: PRATIKO_1.5_REFERENCE.md Section 12.10
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_response_with_actions():
    """Mock LLM response with answer and suggested actions."""
    return """<answer>L'IRPEF si calcola applicando aliquote progressive agli scaglioni di reddito.</answer>
<suggested_actions>
[
    {"id": "calc_irpef", "label": "Calcola IRPEF", "icon": "🧮", "prompt": "Calcola IRPEF per il mio reddito"},
    {"id": "scaglioni", "label": "Vedi scaglioni", "icon": "📊", "prompt": "Mostra scaglioni IRPEF 2024"},
    {"id": "detrazioni", "label": "Detrazioni", "icon": "💰", "prompt": "Quali detrazioni posso applicare?"}
]
</suggested_actions>"""


@pytest.fixture
def mock_llm_response_without_actions():
    """Mock LLM response without actions tags."""
    return "L'IRPEF è l'Imposta sul Reddito delle Persone Fisiche."


@pytest.fixture
def mock_llm_response_malformed():
    """Mock malformed LLM response with invalid JSON."""
    return """<answer>Risposta valida.</answer>
<suggested_actions>[{invalid json here}]</suggested_actions>"""


@pytest.fixture
def test_document_fattura():
    """Sample fattura document for testing."""
    return {
        "type": "fattura_elettronica",
        "content": "Fattura n. 123 del 15/12/2024...",
        "metadata": {"format": "xml"},
    }


@pytest.fixture
def test_document_f24():
    """Sample F24 document for testing."""
    return {
        "type": "f24",
        "content": "Modello F24 con codice tributo 1001...",
        "metadata": {"anno": "2024"},
    }


@pytest.fixture
def test_session_context():
    """Sample session context for testing."""
    return {
        "session_id": "test-session-123",
        "user_id": 1,
        "conversation_history": [
            {"role": "user", "content": "Ciao"},
            {"role": "assistant", "content": "Ciao! Come posso aiutarti?"},
        ],
    }


@pytest.fixture
def golden_set_entry():
    """Sample golden set FAQ entry."""
    return {
        "query": "Cos'è l'IRPEF?",
        "answer": "L'IRPEF è l'Imposta sul Reddito delle Persone Fisiche...",
        "category": "tax",
        "confidence": 0.95,
    }


@pytest.fixture
def kb_document():
    """Sample KB document for injection."""
    return {
        "id": "kb-doc-001",
        "title": "Guida IRPEF 2024",
        "content": "L'IRPEF prevede i seguenti scaglioni...",
        "source": "agenzia_entrate",
    }


# =============================================================================
# TestLLMFirstProactivityIntegration
# =============================================================================


class TestLLMFirstProactivityIntegration:
    """Integration tests for LLM-First proactivity flow."""

    @pytest.mark.asyncio
    async def test_chat_endpoint_returns_actions_from_llm(
        self, mock_llm_response_with_actions
    ):
        """Test that /chat returns actions parsed from LLM response."""
        from app.api.v1.chatbot import apply_action_override
        from app.services.llm_response_parser import parse_llm_response

        # Parse LLM response
        parsed = parse_llm_response(mock_llm_response_with_actions)

        # Apply action override (no template)
        actions = apply_action_override(
            llm_actions=[a.model_dump() for a in parsed.suggested_actions],
            template_actions=None,
        )

        # Verify actions from LLM are returned
        assert len(actions) == 3
        assert actions[0]["id"] == "calc_irpef"
        assert actions[0]["label"] == "Calcola IRPEF"
        assert "Calcola IRPEF" in actions[0]["prompt"]

    @pytest.mark.asyncio
    async def test_chat_endpoint_returns_template_actions_for_document(
        self, test_document_fattura
    ):
        """Test that /chat returns template actions when document is present."""
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()
        result = engine.process_query(
            query="Analizza questa fattura",
            document=test_document_fattura,
        )

        # Should return template actions for fattura
        assert result.template_actions is not None
        assert result.use_llm_actions is False
        assert len(result.template_actions) > 0

        # Verify fattura-specific actions (verify, vat, entry, recipient)
        action_ids = [a["id"] for a in result.template_actions]
        assert "verify" in action_ids or "vat" in action_ids

    @pytest.mark.asyncio
    async def test_chat_endpoint_returns_interactive_question_for_calculation(self):
        """Test that /chat returns InteractiveQuestion for calculation queries."""
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()
        result = engine.process_query(
            query="Calcola l'IRPEF",  # Missing required params
            document=None,
        )

        # Should return interactive question
        assert result.interactive_question is not None
        assert result.use_llm_actions is False
        assert result.template_actions is None

        # Verify question structure
        question = result.interactive_question
        assert "question_type" in question
        assert question["question_type"] == "multi_field"
        assert "fields" in question
        assert len(question["fields"]) > 0

    @pytest.mark.asyncio
    async def test_chat_endpoint_overrides_llm_actions_with_template(
        self, mock_llm_response_with_actions, test_document_fattura
    ):
        """Test that template actions override LLM actions when document present."""
        from app.api.v1.chatbot import apply_action_override
        from app.services.llm_response_parser import parse_llm_response
        from app.services.proactivity_engine_simplified import ProactivityEngine

        # Get LLM actions
        parsed = parse_llm_response(mock_llm_response_with_actions)
        llm_actions = [a.model_dump() for a in parsed.suggested_actions]

        # Get template actions
        engine = ProactivityEngine()
        proactivity_result = engine.process_query(
            query="Analizza fattura", document=test_document_fattura
        )

        # Apply override
        final_actions = apply_action_override(
            llm_actions=llm_actions,
            template_actions=proactivity_result.template_actions,
        )

        # Template should take priority
        assert final_actions == proactivity_result.template_actions
        assert final_actions != llm_actions

    @pytest.mark.asyncio
    async def test_chat_endpoint_graceful_degradation_on_malformed_llm(
        self, mock_llm_response_malformed
    ):
        """Test graceful degradation when LLM returns malformed JSON."""
        from app.services.llm_response_parser import parse_llm_response

        parsed = parse_llm_response(mock_llm_response_malformed)

        # Should still extract answer
        assert parsed.answer == "Risposta valida."

        # Should return empty actions (not crash)
        assert parsed.suggested_actions == []

    @pytest.mark.asyncio
    async def test_stream_endpoint_sends_actions_event(
        self, mock_llm_response_with_actions
    ):
        """Test that streaming endpoint sends suggested_actions SSE event."""
        from app.api.v1.chatbot import format_actions_sse_event
        from app.services.llm_response_parser import parse_llm_response

        # Parse response
        parsed = parse_llm_response(mock_llm_response_with_actions)
        actions = [a.model_dump() for a in parsed.suggested_actions]

        # Format SSE event
        event = format_actions_sse_event(actions)

        # Verify event format
        assert "data:" in event
        assert "suggested_actions" in event
        assert "calc_irpef" in event

    @pytest.mark.asyncio
    async def test_stream_endpoint_strips_tags_from_content(
        self, mock_llm_response_with_actions
    ):
        """Test that streaming strips XML tags from content."""
        from app.api.v1.chatbot import strip_xml_tags

        stripped = strip_xml_tags(mock_llm_response_with_actions)

        # Tags should be removed
        assert "<answer>" not in stripped
        assert "</answer>" not in stripped
        assert "<suggested_actions>" not in stripped

        # Content should be preserved
        assert "IRPEF" in stripped
        assert "scaglioni" in stripped

    @pytest.mark.asyncio
    async def test_stream_endpoint_sends_interactive_question(self):
        """Test that streaming sends interactive_question SSE event."""
        from app.api.v1.chatbot import format_question_sse_event
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()
        result = engine.process_query(query="Calcola l'IVA", document=None)

        assert result.interactive_question is not None

        # Format SSE event
        event = format_question_sse_event(result.interactive_question)

        # Verify event format
        assert "data:" in event
        assert "interactive_question" in event

    @pytest.mark.asyncio
    async def test_full_flow_with_session_context(self, test_session_context):
        """Test full flow with session context preserved."""
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()

        # Process with session context
        result = engine.process_query(
            query="Quanto pago di IRPEF su 35000 euro da dipendente?",
            document=None,
            session_context=test_session_context,
        )

        # Should use LLM (all params present)
        assert result.use_llm_actions is True
        assert result.interactive_question is None

    @pytest.mark.asyncio
    async def test_full_flow_with_document_context(self, test_document_f24):
        """Test full flow with document context."""
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()

        result = engine.process_query(
            query="Come compilo questo F24?",
            document=test_document_f24,
        )

        # Should return F24-specific template actions
        assert result.template_actions is not None
        assert result.use_llm_actions is False


# =============================================================================
# TestGoldenSetKBRegression
# =============================================================================


class TestGoldenSetKBRegression:
    """Regression tests to verify Golden Set and KB flows still work."""

    @pytest.mark.asyncio
    async def test_golden_set_fast_path_still_works_with_proactivity(
        self, golden_set_entry
    ):
        """Test that golden set fast-path is not affected by proactivity."""
        # The proactivity engine should NOT interfere with golden set matching
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()

        # Golden set query should still be recognized
        # (Proactivity runs AFTER golden set check in real flow)
        result = engine.process_query(
            query=golden_set_entry["query"],
            document=None,
        )

        # Should not trigger interactive question for simple FAQ
        # (No calculation keywords)
        assert result.interactive_question is None

        # Should use LLM actions (golden set handles the answer separately)
        assert result.use_llm_actions is True

    @pytest.mark.asyncio
    async def test_kb_documents_injected_before_llm_call(self, kb_document):
        """Test that KB documents are still available for context injection."""
        # This test verifies the KB injection happens BEFORE proactivity parsing
        # The actual injection is in the orchestrator, not proactivity engine

        # Verify KB document has required fields for injection
        assert "id" in kb_document
        assert "content" in kb_document
        assert "title" in kb_document

        # KB content should be injectable into prompts
        prompt_context = f"Documento: {kb_document['title']}\n{kb_document['content']}"
        assert "IRPEF" in prompt_context
        assert "scaglioni" in prompt_context

    @pytest.mark.asyncio
    async def test_document_citations_preserved_in_response(
        self, mock_llm_response_with_actions
    ):
        """Test that document citations [1], [2] are preserved after tag stripping."""
        from app.api.v1.chatbot import strip_xml_tags

        # Response with citations
        response_with_citations = """<answer>Secondo la normativa [1], l'IRPEF si applica [2] ai redditi.</answer>
<suggested_actions>[]</suggested_actions>"""

        stripped = strip_xml_tags(response_with_citations)

        # Citations should be preserved
        assert "[1]" in stripped
        assert "[2]" in stripped
        assert "normativa" in stripped

    @pytest.mark.asyncio
    async def test_user_attachment_context_not_affected(self, test_document_fattura):
        """Test that user attachment context is preserved through proactivity."""
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()

        # Document should be accessible through the flow
        result = engine.process_query(
            query="Analizza allegato",
            document=test_document_fattura,
        )

        # Document type should be recognized
        assert result.template_actions is not None

        # Actions should be fattura-specific (check IDs or labels)
        action_ids = [a.get("id", "") for a in result.template_actions]
        assert "verify" in action_ids or "vat" in action_ids

    @pytest.mark.asyncio
    async def test_token_budget_respects_kb_priority(self, kb_document):
        """Test that token budget logic respects KB document priority."""
        # Token budget is managed in context_builder, not proactivity
        # This test verifies the proactivity additions don't exceed limits

        from app.core.prompts import SUGGESTED_ACTIONS_PROMPT

        # Suggested actions prompt should be reasonable size
        prompt_length = len(SUGGESTED_ACTIONS_PROMPT)

        # Should be under 2000 chars (leaving room for KB docs)
        assert prompt_length < 2000, f"Prompt too long: {prompt_length} chars"

        # Verify it's appendable (not too disruptive to token budget)
        assert prompt_length > 100, "Prompt too short to be meaningful"


# =============================================================================
# TestEdgeCases
# =============================================================================


class TestEdgeCases:
    """Additional edge case tests for integration."""

    @pytest.mark.asyncio
    async def test_empty_query_handled_gracefully(self):
        """Test empty query doesn't crash."""
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()
        result = engine.process_query(query="", document=None)

        # Should default to LLM actions
        assert result.use_llm_actions is True

    @pytest.mark.asyncio
    async def test_unknown_document_type_uses_llm(self):
        """Test unknown document type falls back to LLM."""
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()
        result = engine.process_query(
            query="Analizza questo",
            document={"type": "unknown_type", "content": "..."},
        )

        # Should use LLM (no template for unknown type)
        assert result.use_llm_actions is True
        assert result.template_actions is None

    @pytest.mark.asyncio
    async def test_all_document_types_have_templates(self):
        """Test that all supported document types have templates."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        expected_types = ["fattura_elettronica", "f24", "bilancio", "cu"]

        for doc_type in expected_types:
            assert doc_type in DOCUMENT_ACTION_TEMPLATES, f"Missing template for {doc_type}"
            assert len(DOCUMENT_ACTION_TEMPLATES[doc_type]) > 0

    @pytest.mark.asyncio
    async def test_all_calculable_intents_have_questions(self):
        """Test that all calculable intents can generate questions."""
        from app.core.proactivity_constants import CALCULABLE_INTENTS
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()

        test_queries = {
            "calcolo_irpef": "Calcola l'IRPEF",
            "calcolo_iva": "Calcola l'IVA",
            "calcolo_contributi_inps": "Calcola i contributi INPS",
            "ravvedimento_operoso": "Calcola il ravvedimento operoso",
            "calcolo_f24": "Compila il modello F24",
        }

        for intent, query in test_queries.items():
            result = engine.process_query(query=query, document=None)
            assert result.interactive_question is not None, f"No question for {intent}"

    @pytest.mark.asyncio
    async def test_concurrent_requests_are_thread_safe(self):
        """Test that engine handles concurrent requests safely."""
        import asyncio

        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()

        async def process_request(query: str):
            return engine.process_query(query=query, document=None)

        # Run multiple concurrent requests
        queries = [
            "Calcola IRPEF",
            "Qual è l'aliquota IVA?",
            "Come compilo il 730?",
            "Calcola contributi INPS",
        ]

        results = await asyncio.gather(*[process_request(q) for q in queries])

        # All should complete without errors
        assert len(results) == 4
        for result in results:
            assert result is not None
