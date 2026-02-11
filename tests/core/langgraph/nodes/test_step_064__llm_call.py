"""Tests for step_064__llm_call node - DEV-256: enriched_prompt propagation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_state() -> dict:
    """Create a minimal mock state for testing."""
    return {
        "messages": [{"role": "user", "content": "test query"}],
        "context": "test context",
        "kb_context": "test kb context",
        "provider": {"selected": "openai"},
        "routing_decision": {"is_followup": False},
    }


@pytest.fixture
def mock_unified_response():
    """Create a mock UnifiedResponse with enriched_prompt."""
    response = MagicMock()
    response.answer = "Test answer"
    response.model_used = "gpt-4o"
    response.tokens_input = 100
    response.tokens_output = 50
    response.cost_euros = 0.001
    response.sources_cited = []
    response.enriched_prompt = "Query: test query\n\nContext: test context"
    return response


class TestEnrichedPromptPropagation:
    """DEV-256: Test that enriched_prompt is properly set in state."""

    @pytest.mark.asyncio
    async def test_enriched_prompt_set_from_unified_response(
        self, mock_state: dict, mock_unified_response: MagicMock
    ) -> None:
        """enriched_prompt should be set in state when UnifiedResponse has it."""
        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("simple", {}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.check_kb_empty_and_inject_warning",
                return_value=False,
            ),
            patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator") as mock_orchestrator,
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.extract_user_message",
                return_value="test query",
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.process_unified_response",
                return_value="Test answer",
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.validate_citations_in_response",
                return_value=None,
            ),
            patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_log"),
            patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_timer"),
        ):
            mock_orchestrator.return_value.generate_response = AsyncMock(return_value=mock_unified_response)

            from app.core.langgraph.nodes.step_064__llm_call import node_step_64

            result = await node_step_64(mock_state)

            assert "enriched_prompt" in result
            assert result["enriched_prompt"] == "Query: test query\n\nContext: test context"

    @pytest.mark.asyncio
    async def test_enriched_prompt_not_set_when_none(self, mock_state: dict, mock_unified_response: MagicMock) -> None:
        """enriched_prompt should not be set when UnifiedResponse has None."""
        mock_unified_response.enriched_prompt = None

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("simple", {}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.check_kb_empty_and_inject_warning",
                return_value=False,
            ),
            patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator") as mock_orchestrator,
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.extract_user_message",
                return_value="test query",
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.process_unified_response",
                return_value="Test answer",
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.validate_citations_in_response",
                return_value=None,
            ),
            patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_log"),
            patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_timer"),
        ):
            mock_orchestrator.return_value.generate_response = AsyncMock(return_value=mock_unified_response)

            from app.core.langgraph.nodes.step_064__llm_call import node_step_64

            result = await node_step_64(mock_state)

            assert result.get("enriched_prompt") is None

    @pytest.mark.asyncio
    async def test_enriched_prompt_fallback_on_exception(self, mock_state: dict) -> None:
        """enriched_prompt should be constructed from context on fallback path."""
        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("simple", {}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.check_kb_empty_and_inject_warning",
                return_value=False,
            ),
            patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator") as mock_orchestrator,
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.extract_user_message",
                return_value="test query",
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value={"llm_call_successful": True, "response": {"content": "fallback"}},
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.process_unified_response",
                return_value="fallback",
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.validate_citations_in_response",
                return_value=None,
            ),
            patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_log"),
            patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_timer"),
        ):
            # Make generate_response raise an exception to trigger fallback
            mock_orchestrator.return_value.generate_response = AsyncMock(side_effect=Exception("LLM error"))

            from app.core.langgraph.nodes.step_064__llm_call import node_step_64

            result = await node_step_64(mock_state)

            # Fallback should construct enriched_prompt from context
            assert "enriched_prompt" in result
            assert "test query" in result["enriched_prompt"]
            assert "test context" in result["enriched_prompt"]
