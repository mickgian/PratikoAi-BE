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


class TestStreamingLLMDeferral:
    """Test that step_064 defers LLM call when streaming is requested."""

    @pytest.fixture
    def streaming_state(self, mock_state: dict) -> dict:
        """State with streaming flag set."""
        mock_state["streaming"] = {"requested": True}
        return mock_state

    @pytest.mark.asyncio
    async def test_defers_llm_when_streaming_requested(self, streaming_state: dict) -> None:
        """Should set stream_llm_pending and skip generate_response()."""
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
            patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator") as mock_orch,
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.extract_user_message",
                return_value="test query",
            ),
            patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_log"),
            patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_timer"),
        ):
            from app.core.langgraph.nodes.step_064__llm_call import node_step_64

            result = await node_step_64(streaming_state)

            # Should have deferred LLM call
            assert result["stream_llm_pending"] is True
            assert "stream_llm_params" in result
            assert result["stream_llm_params"]["query"] == "test query"
            assert result["stream_llm_params"]["complexity"] == "simple"

            # LLM namespace should indicate success + deferred
            llm_ns = result.get("llm", {})
            assert llm_ns.get("success") is True
            assert llm_ns.get("deferred_for_streaming") is True

            # generate_response should NOT have been called
            mock_orch.return_value.generate_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_defer_when_tot_used(self, streaming_state: dict, mock_unified_response: MagicMock) -> None:
        """Should NOT defer if ToT already produced a response."""
        # Create mock ToT result
        mock_tot = MagicMock()
        mock_tot.reasoning_trace = {"tema_identificato": "test"}
        mock_tot.selected_hypothesis = MagicMock(id="h1", confidence=0.9, source_weight_score=0.8)
        mock_tot.all_hypotheses = [mock_tot.selected_hypothesis]
        mock_tot.complexity_used = "complex"
        mock_tot.total_latency_ms = 500
        mock_tot.llm_response = mock_unified_response

        streaming_state["routing_decision"] = {"route": "technical_research", "is_followup": False}

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("complex", {}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.check_kb_empty_and_inject_warning",
                return_value=False,
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts",
                new_callable=AsyncMock,
                return_value=mock_tot,
            ),
            patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator") as mock_orch,
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
            patch("app.core.langgraph.nodes.step_064__llm_call.log_tot_hypothesis_evaluated"),
            patch("app.core.langgraph.nodes.step_064__llm_call.log_reasoning_trace_recorded"),
        ):
            from app.core.langgraph.nodes.step_064__llm_call import node_step_64

            result = await node_step_64(streaming_state)

            # ToT response should be used, NOT deferred
            assert result.get("stream_llm_pending") is not True
            # generate_response should NOT have been called (ToT reuse)
            mock_orch.return_value.generate_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_stream_params_include_chitchat_flag(self, mock_state: dict) -> None:
        """stream_llm_params should include is_chitchat=True for chitchat queries."""
        mock_state["streaming"] = {"requested": True}
        mock_state["routing_decision"] = {"route": "chitchat", "is_followup": False}

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.check_kb_empty_and_inject_warning",
                return_value=False,
            ),
            patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator"),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.extract_user_message",
                return_value="ciao",
            ),
            patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_log"),
            patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_timer"),
        ):
            from app.core.langgraph.nodes.step_064__llm_call import node_step_64

            result = await node_step_64(mock_state)

            assert result["stream_llm_pending"] is True
            assert result["stream_llm_params"]["is_chitchat"] is True
