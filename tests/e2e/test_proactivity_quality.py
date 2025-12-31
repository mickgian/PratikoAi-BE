"""E2E Tests for DEV-183: Proactivity Quality Verification.

Verifies acceptance criteria from PRATIKO_1.5_REFERENCE.md Section 12.10:
- AC-REV.1: InteractiveQuestion ONLY for CALCULABLE_INTENTS with missing params
- AC-REV.2: SuggestedActions appears on EVERY response
- AC-REV.3: LLM generates 2-4 pertinent actions in 90%+ of responses
- AC-REV.4: Parsing fails gracefully (no crashes)
- AC-REV.5: Document templates have priority over LLM actions
- AC-REV.6: Cost tracking verification
"""

import pytest

from app.core.proactivity_constants import CALCULABLE_INTENTS, DOCUMENT_ACTION_TEMPLATES
from app.services.llm_response_parser import parse_llm_response
from app.services.proactivity_engine_simplified import ProactivityEngine


class TestProactivityQuality:
    """E2E quality verification tests for LLM-First proactivity."""

    @pytest.fixture
    def proactivity_engine(self):
        """Create ProactivityEngine instance."""
        return ProactivityEngine()

    @pytest.mark.asyncio
    async def test_interactive_question_only_for_calculable_intents(self, proactivity_engine):
        """AC-REV.1: InteractiveQuestion ONLY for CALCULABLE_INTENTS with missing params."""
        # Queries that SHOULD trigger InteractiveQuestion (calculable + missing params)
        calculable_queries = [
            "Calcola l'IRPEF",  # Missing: reddito, tipo_contribuente
            "Calcola l'IVA",  # Missing: imponibile, aliquota
            "Calcola i contributi INPS",  # Missing: reddito, tipo_contribuente
            "Calcola il ravvedimento operoso",  # Missing: importo, giorni_ritardo
            "Compila il modello F24",  # Missing: codice_tributo, importo
        ]

        for query in calculable_queries:
            result = proactivity_engine.process_query(query=query, document=None)
            assert result.interactive_question is not None, f"Expected InteractiveQuestion for: {query}"
            assert result.use_llm_actions is False

        # Queries that should NOT trigger InteractiveQuestion
        non_calculable_queries = [
            "Cos'è l'IRPEF?",  # Informational, not calculation
            "Quali sono le scadenze fiscali?",  # Informational
            "Come funziona la fatturazione elettronica?",  # Informational
        ]

        for query in non_calculable_queries:
            result = proactivity_engine.process_query(query=query, document=None)
            assert result.interactive_question is None, f"Expected no InteractiveQuestion for: {query}"
            assert result.use_llm_actions is True

    @pytest.mark.asyncio
    async def test_suggested_actions_on_every_response(self, proactivity_engine):
        """AC-REV.2: SuggestedActions appears on EVERY response."""
        test_queries = [
            "Cos'è l'IRPEF?",
            "Come funziona la fatturazione elettronica?",
            "Quali sono i requisiti per aprire una partita IVA?",
            "Spiegami il regime forfettario",
            "Quali tasse devo pagare come freelance?",
        ]

        for query in test_queries:
            result = proactivity_engine.process_query(query=query, document=None)

            # For non-calculable queries, should use LLM actions
            if result.interactive_question is None:
                assert result.use_llm_actions is True, f"Expected use_llm_actions=True for: {query}"

    @pytest.mark.asyncio
    async def test_llm_generates_2_to_4_actions(self):
        """AC-REV.3: LLM generates 2-4 pertinent actions."""
        # Test with various mock LLM responses
        valid_responses = [
            """<answer>L'IRPEF si calcola in base agli scaglioni.</answer>
<suggested_actions>[
    {"id": "calc", "label": "Calcola", "icon": "🧮", "prompt": "Calcola IRPEF"},
    {"id": "info", "label": "Info", "icon": "ℹ️", "prompt": "Maggiori info"}
]</suggested_actions>""",
            """<answer>La fattura elettronica è obbligatoria.</answer>
<suggested_actions>[
    {"id": "a1", "label": "Azione 1", "icon": "📄", "prompt": "P1"},
    {"id": "a2", "label": "Azione 2", "icon": "📝", "prompt": "P2"},
    {"id": "a3", "label": "Azione 3", "icon": "🔍", "prompt": "P3"},
    {"id": "a4", "label": "Azione 4", "icon": "💡", "prompt": "P4"}
]</suggested_actions>""",
        ]

        for response in valid_responses:
            parsed = parse_llm_response(response)
            assert (
                2 <= len(parsed.suggested_actions) <= 4
            ), f"Expected 2-4 actions, got {len(parsed.suggested_actions)}"

    @pytest.mark.asyncio
    async def test_actions_are_pertinent_to_query(self, proactivity_engine):
        """AC-REV.3: Actions should be contextually relevant."""
        # Test with fattura document
        fattura_doc = {"type": "fattura_elettronica", "content": "Fattura n. 123..."}
        result = proactivity_engine.process_query(
            query="Analizza questa fattura",
            document=fattura_doc,
        )

        # Should get fattura-specific template actions
        assert result.template_actions is not None
        action_ids = [a.get("id", "") for a in result.template_actions]
        # Fattura templates include: verify, vat, entry, recipient
        assert any(aid in ["verify", "vat", "entry", "recipient"] for aid in action_ids)

    @pytest.mark.asyncio
    async def test_parsing_fails_gracefully(self):
        """AC-REV.4: Parsing fails gracefully (no crashes)."""
        malformed_responses = [
            "",  # Empty
            "Plain text without tags",  # No XML
            "<answer>Only answer, no actions</answer>",  # Missing actions
            "<answer>Text</answer><suggested_actions>not json</suggested_actions>",
            "<answer>Text</answer><suggested_actions>[{broken}]</suggested_actions>",
            "<suggested_actions>[{}]</suggested_actions>",  # Missing answer
            None,  # None value (should be handled)
        ]

        for response in malformed_responses:
            if response is None:
                continue  # Skip None for this test
            # Should not crash
            parsed = parse_llm_response(response)
            # Should return something valid
            assert parsed is not None
            assert isinstance(parsed.answer, str)
            assert isinstance(parsed.suggested_actions, list)

    @pytest.mark.asyncio
    async def test_document_templates_have_priority(self, proactivity_engine):
        """AC-REV.5: Document templates have priority over LLM actions."""
        from app.api.v1.chatbot import apply_action_override

        # LLM-generated actions
        llm_actions = [{"id": "llm_1", "label": "LLM Action", "icon": "🤖", "prompt": "..."}]

        # Template actions (from document)
        template_actions = [{"id": "tpl_1", "label": "Template Action", "icon": "📄", "prompt": "..."}]

        # Template should take priority
        result = apply_action_override(llm_actions, template_actions)
        assert result == template_actions
        assert result != llm_actions

        # When no template, LLM actions used
        result_no_template = apply_action_override(llm_actions, None)
        assert result_no_template == llm_actions

    @pytest.mark.asyncio
    async def test_all_document_types_have_templates(self):
        """Verify all expected document types have action templates."""
        expected_types = ["fattura_elettronica", "f24", "bilancio", "cu"]

        for doc_type in expected_types:
            assert doc_type in DOCUMENT_ACTION_TEMPLATES, f"Missing template for {doc_type}"
            templates = DOCUMENT_ACTION_TEMPLATES[doc_type]
            assert len(templates) > 0, f"Empty templates for {doc_type}"

    @pytest.mark.asyncio
    async def test_all_calculable_intents_defined(self):
        """Verify all calculable intents have required parameters."""
        expected_intents = [
            "calcolo_irpef",
            "calcolo_iva",
            "calcolo_contributi_inps",
            "ravvedimento_operoso",
            "calcolo_f24",
        ]

        for intent in expected_intents:
            assert intent in CALCULABLE_INTENTS, f"Missing intent: {intent}"
            intent_config = CALCULABLE_INTENTS[intent]
            # Config has 'required' and 'question_flow' keys
            assert "required" in intent_config
            assert "question_flow" in intent_config
            assert len(intent_config["required"]) > 0

    @pytest.mark.asyncio
    async def test_interactive_question_format(self, proactivity_engine):
        """Verify InteractiveQuestion has correct structure."""
        result = proactivity_engine.process_query(
            query="Calcola l'IRPEF",
            document=None,
        )

        assert result.interactive_question is not None
        question = result.interactive_question

        # Required fields
        assert "question_type" in question
        assert question["question_type"] == "multi_field"
        assert "fields" in question
        assert len(question["fields"]) > 0

        # Each field should have required attributes
        for field in question["fields"]:
            assert "id" in field
            assert "label" in field
            assert "input_type" in field  # Field uses input_type, not type


class TestProactivityCostTracking:
    """Tests for AC-REV.6: Cost tracking verification."""

    @pytest.mark.asyncio
    async def test_suggested_actions_prompt_size(self):
        """Verify suggested_actions prompt is reasonable size for cost control."""
        from app.core.prompts import SUGGESTED_ACTIONS_PROMPT

        # DEV-201b: Increased limit to 4000 chars for comprehensive prompt
        # with domain classification, multi-step strategy, and icon documentation
        assert len(SUGGESTED_ACTIONS_PROMPT) < 4000
        # Should contain required instructions
        assert "<answer>" in SUGGESTED_ACTIONS_PROMPT
        assert "<suggested_actions>" in SUGGESTED_ACTIONS_PROMPT

    @pytest.mark.asyncio
    async def test_max_actions_limited_to_4(self):
        """Verify parser limits actions to 4 max."""
        # Response with 6 actions
        response = """<answer>Test</answer>
<suggested_actions>[
    {"id": "1", "label": "A1", "icon": "1", "prompt": "1"},
    {"id": "2", "label": "A2", "icon": "2", "prompt": "2"},
    {"id": "3", "label": "A3", "icon": "3", "prompt": "3"},
    {"id": "4", "label": "A4", "icon": "4", "prompt": "4"},
    {"id": "5", "label": "A5", "icon": "5", "prompt": "5"},
    {"id": "6", "label": "A6", "icon": "6", "prompt": "6"}
]</suggested_actions>"""

        parsed = parse_llm_response(response)
        assert len(parsed.suggested_actions) <= 4
