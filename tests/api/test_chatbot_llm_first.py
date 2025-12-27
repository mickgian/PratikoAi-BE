"""TDD Tests for DEV-179: LLM-First Proactivity Integration in /chat Endpoint.

Tests the integration of:
- Simplified ProactivityEngine (DEV-177)
- LLM Response Parser (DEV-176)
- Suggested Actions Prompt (DEV-175)

Reference: PRATIKO_1.5_REFERENCE.md Section 12.7
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.proactivity import Action


class TestChatLLMFirstIntegration:
    """Test LLM-First proactivity integration in /chat endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock session."""
        session = MagicMock()
        session.id = "test-session-123"
        session.user_id = 1
        return session

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_chat_uses_simplified_proactivity_engine(self, mock_session, mock_db):
        """Test that /chat uses the simplified ProactivityEngine from DEV-177."""
        from app.api.v1.chatbot import get_simplified_proactivity_engine

        engine = get_simplified_proactivity_engine()

        # Should return the simplified engine
        from app.services.proactivity_engine_simplified import ProactivityEngine

        assert isinstance(engine, ProactivityEngine)

    @pytest.mark.asyncio
    async def test_chat_includes_suggested_actions_in_response(self, mock_session, mock_db):
        """Test that /chat includes suggested_actions from parsed LLM response."""
        from app.services.llm_response_parser import parse_llm_response

        # Simulate LLM response with actions
        raw_response = """<answer>L'IRPEF è calcolata in base agli scaglioni.</answer>
<suggested_actions>
[
    {"id": "calc_irpef", "label": "Calcola IRPEF", "icon": "🧮", "prompt": "Calcola IRPEF per €35000"},
    {"id": "scadenze", "label": "Scadenze fiscali", "icon": "📅", "prompt": "Mostra scadenze fiscali"}
]
</suggested_actions>"""

        parsed = parse_llm_response(raw_response)

        assert len(parsed.suggested_actions) == 2
        assert parsed.suggested_actions[0].id == "calc_irpef"
        assert parsed.suggested_actions[0].label == "Calcola IRPEF"
        assert parsed.answer == "L'IRPEF è calcolata in base agli scaglioni."

    @pytest.mark.asyncio
    async def test_chat_uses_document_template_when_present(self, mock_session, mock_db):
        """Test that /chat uses DOCUMENT_ACTION_TEMPLATES when document is present."""
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()

        # Simulate document attachment
        document = {"type": "fattura_elettronica", "content": "Invoice content"}

        result = engine.process_query(
            query="Analizza questa fattura",
            document=document,
        )

        # Should return template actions, not use LLM
        assert result.template_actions is not None
        assert result.use_llm_actions is False
        assert result.interactive_question is None

    @pytest.mark.asyncio
    async def test_chat_uses_llm_actions_when_no_template(self, mock_session, mock_db):
        """Test that /chat uses LLM actions when no document template applies."""
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()

        # General query without document
        result = engine.process_query(
            query="Quali sono le novità fiscali 2024?",
            document=None,
        )

        # Should use LLM actions
        assert result.use_llm_actions is True
        assert result.template_actions is None
        assert result.interactive_question is None

    @pytest.mark.asyncio
    async def test_chat_returns_interactive_question_for_calculation(self, mock_session, mock_db):
        """Test that /chat returns InteractiveQuestion for calculable intent with missing params."""
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()

        # Calculation query missing parameters
        result = engine.process_query(
            query="Calcola l'IRPEF",  # Missing reddito
            document=None,
        )

        # Should return InteractiveQuestion
        assert result.interactive_question is not None
        assert result.use_llm_actions is False
        assert result.template_actions is None
        assert result.interactive_question["question_type"] == "multi_field"

    @pytest.mark.asyncio
    async def test_chat_no_question_when_params_present(self, mock_session, mock_db):
        """Test that /chat does NOT return question when all params are present."""
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()

        # Calculation query with all parameters
        result = engine.process_query(
            query="Calcola l'IRPEF su 35000 euro da dipendente",
            document=None,
        )

        # Should NOT return InteractiveQuestion (all params present)
        assert result.interactive_question is None
        assert result.use_llm_actions is True

    @pytest.mark.asyncio
    async def test_chat_graceful_degradation_on_parser_failure(self, mock_session, mock_db):
        """Test that /chat handles parser failures gracefully."""
        from app.services.llm_response_parser import parse_llm_response

        # Malformed response
        raw_response = "Just a plain text response without any tags"

        parsed = parse_llm_response(raw_response)

        # Should return full response as answer, empty actions
        assert parsed.answer == "Just a plain text response without any tags"
        assert parsed.suggested_actions == []

    @pytest.mark.asyncio
    async def test_chat_response_format_unchanged(self, mock_session, mock_db):
        """Test that /chat response schema remains backward compatible."""
        from app.schemas.chat import ChatResponse
        from app.schemas.proactivity import ActionCategory

        # ChatResponse should still accept the same fields
        response = ChatResponse(
            messages=[],
            suggested_actions=[
                Action(
                    id="test",
                    label="Test",
                    icon="🔍",
                    category=ActionCategory.SEARCH,
                    prompt_template="Test {param}",
                )
            ],
            interactive_question=None,
            extracted_params=None,
        )

        assert response.messages == []
        assert len(response.suggested_actions) == 1


class TestChatLLMFirstEdgeCases:
    """Edge case tests for LLM-First integration."""

    @pytest.mark.asyncio
    async def test_chat_empty_actions_from_llm(self):
        """Test handling of empty actions from LLM response."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = """<answer>Ecco la risposta.</answer>
<suggested_actions>[]</suggested_actions>"""

        parsed = parse_llm_response(raw_response)

        assert parsed.answer == "Ecco la risposta."
        assert parsed.suggested_actions == []

    @pytest.mark.asyncio
    async def test_chat_malformed_json_actions(self):
        """Test handling of malformed JSON in actions."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = """<answer>Answer text.</answer>
<suggested_actions>[{not valid json}]</suggested_actions>"""

        parsed = parse_llm_response(raw_response)

        assert parsed.answer == "Answer text."
        assert parsed.suggested_actions == []

    @pytest.mark.asyncio
    async def test_chat_actions_truncated_to_max_4(self):
        """Test that actions are truncated to max 4."""
        from app.services.llm_response_parser import parse_llm_response

        # Response with 6 actions
        actions = [
            {"id": f"action_{i}", "label": f"Action {i}", "icon": "🔍", "prompt": f"Prompt {i}"}
            for i in range(6)
        ]
        import json

        raw_response = f"""<answer>Answer.</answer>
<suggested_actions>{json.dumps(actions)}</suggested_actions>"""

        parsed = parse_llm_response(raw_response)

        assert len(parsed.suggested_actions) == 4

    @pytest.mark.asyncio
    async def test_chat_very_long_response(self):
        """Test handling of very long LLM response."""
        from app.services.llm_response_parser import parse_llm_response

        # Very long answer
        long_text = "A" * 10000
        raw_response = f"""<answer>{long_text}</answer>
<suggested_actions>[{{"id": "test", "label": "Test", "icon": "🔍", "prompt": "Test"}}]</suggested_actions>"""

        parsed = parse_llm_response(raw_response)

        assert len(parsed.answer) == 10000
        assert len(parsed.suggested_actions) == 1

    @pytest.mark.asyncio
    async def test_chat_decision_logic_priority(self):
        """Test that decision logic follows correct priority order.

        Priority: calculable intent > document template > LLM actions
        """
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()

        # Query with calculable intent - should get question even with document
        result = engine.process_query(
            query="Calcola l'IRPEF",  # Calculable intent
            document={"type": "fattura_elettronica", "content": "..."},
        )

        # Calculable intent takes priority over document
        assert result.interactive_question is not None
        assert result.template_actions is None

    @pytest.mark.asyncio
    async def test_chat_unknown_document_type_uses_llm(self):
        """Test that unknown document types fall back to LLM actions."""
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()

        result = engine.process_query(
            query="Analizza questo documento",
            document={"type": "unknown_type", "content": "..."},
        )

        # Unknown type should use LLM
        assert result.use_llm_actions is True
        assert result.template_actions is None


class TestProactivityPromptInjection:
    """Tests for suggested_actions prompt injection."""

    @pytest.mark.asyncio
    async def test_suggested_actions_prompt_loads(self):
        """Test that suggested_actions prompt loads correctly."""
        from app.core.prompts import SUGGESTED_ACTIONS_PROMPT

        assert SUGGESTED_ACTIONS_PROMPT is not None
        assert len(SUGGESTED_ACTIONS_PROMPT) > 0
        assert "<answer>" in SUGGESTED_ACTIONS_PROMPT
        assert "<suggested_actions>" in SUGGESTED_ACTIONS_PROMPT

    @pytest.mark.asyncio
    async def test_prompt_injection_helper(self):
        """Test the prompt injection helper function."""
        from app.api.v1.chatbot import inject_proactivity_prompt
        from app.core.prompts import SUGGESTED_ACTIONS_PROMPT

        base_prompt = "You are a helpful assistant."

        result = inject_proactivity_prompt(base_prompt)

        # Should append suggested actions prompt
        assert base_prompt in result
        assert SUGGESTED_ACTIONS_PROMPT in result
        # Should be appended, not prepended
        assert result.index(base_prompt) < result.index(SUGGESTED_ACTIONS_PROMPT)


class TestProactivityActionOverride:
    """Tests for action override logic."""

    @pytest.mark.asyncio
    async def test_template_actions_override_llm_actions(self):
        """Test that template actions override LLM-generated actions."""
        from app.api.v1.chatbot import apply_action_override

        llm_actions = [
            {"id": "llm_1", "label": "LLM Action", "icon": "🤖", "prompt": "..."}
        ]
        template_actions = [
            {"id": "tpl_1", "label": "Template Action", "icon": "📄", "prompt": "..."}
        ]

        result = apply_action_override(llm_actions, template_actions)

        # Template actions should take priority
        assert result == template_actions

    @pytest.mark.asyncio
    async def test_llm_actions_used_when_no_template(self):
        """Test that LLM actions are used when no template override."""
        from app.api.v1.chatbot import apply_action_override

        llm_actions = [
            {"id": "llm_1", "label": "LLM Action", "icon": "🤖", "prompt": "..."}
        ]

        result = apply_action_override(llm_actions, None)

        # LLM actions should be used
        assert result == llm_actions

    @pytest.mark.asyncio
    async def test_empty_result_when_both_empty(self):
        """Test empty result when both sources are empty."""
        from app.api.v1.chatbot import apply_action_override

        result = apply_action_override([], None)

        assert result == []
