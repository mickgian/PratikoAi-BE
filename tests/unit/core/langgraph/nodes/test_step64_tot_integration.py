"""TDD Tests for Step 64 Tree of Thoughts Integration.

DEV-226: Tests for integrating TreeOfThoughtsReasoner with Step 64.

These tests follow TDD methodology - written BEFORE implementation.
Run with: pytest tests/unit/core/langgraph/nodes/test_step64_tot_integration.py -v
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def base_state():
    """Base RAG state for tests."""
    return {
        "messages": [{"role": "user", "content": "Test query"}],
        "user_message": "Test query",
        "request_id": "test-request-123",
        "session_id": "test-session-456",
        "provider": {"selected": "openai"},
        "detected_domains": ["fiscale"],
        "kb_sources_metadata": [
            {"id": "doc1", "title": "Legge 123/2020", "type": "legge"},
        ],
    }


@pytest.fixture
def mock_tot_result():
    """Mock ToT result with hypotheses and reasoning trace."""
    from app.services.tree_of_thoughts_reasoner import ToTHypothesis, ToTResult

    hypothesis = ToTHypothesis(
        id="H1",
        reasoning_path="Analysis of IVA application",
        conclusion="IVA applies at 22% rate",
        confidence=0.85,
        sources_used=[{"ref": "Art. 1 DPR 633/72", "type": "legge"}],
        source_weight_score=0.85,
        risk_level="basso",
        risk_factors=None,
    )

    return ToTResult(
        selected_hypothesis=hypothesis,
        all_hypotheses=[hypothesis],
        reasoning_trace={
            "total_hypotheses": 1,
            "selected_id": "H1",
            "selected_confidence": 0.85,
            "selection_reasoning": "Highest weighted score",
        },
        total_latency_ms=1500.0,
        complexity_used="complex",
    )


@pytest.fixture
def mock_orchestrator_response():
    """Mock response from step_64__llmcall orchestrator."""
    return {
        "llm_call_successful": True,
        "response": {
            "content": '{"reasoning": {"tema": "IVA"}, "answer": "Test answer", "sources_cited": [], "suggested_actions": []}',
        },
        "model": "gpt-4o",
        "tokens_used": 500,
        "cost_estimate": 0.01,
    }


# =============================================================================
# Tests: Simple Query Uses CoT (Not ToT)
# =============================================================================


class TestSimpleQueryUsesCoT:
    """Tests that simple queries bypass ToT and use CoT."""

    @pytest.mark.asyncio
    async def test_simple_query_does_not_call_tot(self, base_state, mock_orchestrator_response):
        """ToT reasoner should NOT be called for simple queries."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        # Set complexity to simple
        base_state["query_complexity"] = "simple"

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("simple", {"complexity": "simple"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts",
                new_callable=AsyncMock,
            ) as mock_tot,
        ):
            await node_step_64(base_state)

            # ToT should not be called for simple queries
            mock_tot.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="DEV-245: Test mocks step_64__llmcall but code now uses LLMOrchestrator.generate_response(). "
        "Update test to mock orchestrator.generate_response() - see DEV-248"
    )
    async def test_simple_query_sets_reasoning_type_cot(self, base_state, mock_orchestrator_response):
        """Simple queries should set reasoning_type to 'cot'."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("simple", {"complexity": "simple"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            result = await node_step_64(base_state)

            # Should use CoT reasoning
            assert result.get("reasoning_type") == "cot"


# =============================================================================
# Tests: Complex Query Uses ToT
# =============================================================================


class TestComplexQueryUsesToT:
    """Tests that complex queries use TreeOfThoughtsReasoner."""

    @pytest.mark.asyncio
    async def test_complex_query_calls_tot(self, base_state, mock_tot_result, mock_orchestrator_response):
        """ToT reasoner should be called for complex queries."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("complex", {"complexity": "complex"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts",
                new_callable=AsyncMock,
                return_value=mock_tot_result,
            ) as mock_tot,
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            await node_step_64(base_state)

            # ToT should be called for complex queries
            mock_tot.assert_called_once()

    @pytest.mark.asyncio
    async def test_complex_query_sets_reasoning_type_tot(
        self, base_state, mock_tot_result, mock_orchestrator_response
    ):
        """Complex queries should set reasoning_type to 'tot'."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("complex", {"complexity": "complex"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts",
                new_callable=AsyncMock,
                return_value=mock_tot_result,
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            result = await node_step_64(base_state)

            # Should use ToT reasoning
            assert result.get("reasoning_type") == "tot"


# =============================================================================
# Tests: Multi-Domain Query Uses ToT
# =============================================================================


class TestMultiDomainQueryUsesToT:
    """Tests that multi-domain queries use TreeOfThoughtsReasoner."""

    @pytest.mark.asyncio
    async def test_multi_domain_query_calls_tot(self, base_state, mock_tot_result, mock_orchestrator_response):
        """ToT reasoner should be called for multi_domain queries."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        # Set up multi-domain state
        base_state["detected_domains"] = ["fiscale", "lavoro"]

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("multi_domain", {"complexity": "multi_domain", "domains": ["fiscale", "lavoro"]}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts",
                new_callable=AsyncMock,
                return_value=mock_tot_result,
            ) as mock_tot,
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            await node_step_64(base_state)

            # ToT should be called for multi_domain
            mock_tot.assert_called_once()

    @pytest.mark.asyncio
    async def test_multi_domain_passes_domains_to_tot(self, base_state, mock_tot_result, mock_orchestrator_response):
        """Multi-domain queries should pass domains to ToT."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        base_state["detected_domains"] = ["fiscale", "lavoro"]

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("multi_domain", {"complexity": "multi_domain"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts",
                new_callable=AsyncMock,
                return_value=mock_tot_result,
            ) as mock_tot,
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            result = await node_step_64(base_state)

            # Check that ToT was called (domains are passed via state)
            mock_tot.assert_called_once()
            # Verify complexity_used reflects multi_domain
            assert result.get("query_complexity") == "multi_domain"


# =============================================================================
# Tests: Reasoning Trace Storage
# =============================================================================


class TestReasoningTraceStorage:
    """Tests that reasoning trace is stored in GraphState."""

    @pytest.mark.asyncio
    async def test_tot_reasoning_trace_stored(self, base_state, mock_tot_result, mock_orchestrator_response):
        """ToT reasoning trace should be stored in state."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("complex", {"complexity": "complex"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts",
                new_callable=AsyncMock,
                return_value=mock_tot_result,
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            result = await node_step_64(base_state)

            # reasoning_trace should contain ToT trace
            assert result.get("reasoning_trace") is not None
            assert isinstance(result.get("reasoning_trace"), dict)

    @pytest.mark.asyncio
    async def test_tot_analysis_stored(self, base_state, mock_tot_result, mock_orchestrator_response):
        """Full ToT analysis should be stored in state."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("complex", {"complexity": "complex"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts",
                new_callable=AsyncMock,
                return_value=mock_tot_result,
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            result = await node_step_64(base_state)

            # tot_analysis should be stored
            assert result.get("tot_analysis") is not None or result.get("reasoning_trace") is not None


# =============================================================================
# Tests: Hypothesis Used for Response
# =============================================================================


class TestHypothesisUsedForResponse:
    """Tests that selected hypothesis is used for response generation."""

    @pytest.mark.asyncio
    async def test_selected_hypothesis_stored(self, base_state, mock_tot_result, mock_orchestrator_response):
        """Selected hypothesis should be accessible in state."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("complex", {"complexity": "complex"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts",
                new_callable=AsyncMock,
                return_value=mock_tot_result,
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            result = await node_step_64(base_state)

            # Reasoning trace should contain selection info
            trace = result.get("reasoning_trace", {})
            has_selection = (
                "selected_id" in trace or "selected_hypothesis" in trace or result.get("tot_analysis") is not None
            )
            assert has_selection or result.get("reasoning_type") == "tot"


# =============================================================================
# Tests: ToT Failure Fallback
# =============================================================================


class TestToTFailureFallback:
    """Tests fallback to CoT when ToT fails."""

    @pytest.mark.asyncio
    async def test_tot_failure_falls_back_to_cot(self, base_state, mock_orchestrator_response):
        """Should fall back to CoT when ToT fails."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("complex", {"complexity": "complex"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts",
                new_callable=AsyncMock,
                side_effect=Exception("ToT failed"),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            result = await node_step_64(base_state)

            # Should still succeed with fallback
            llm_state = result.get("llm", {})
            assert llm_state.get("success") is True or result.get("llm_response") is not None

    @pytest.mark.asyncio
    async def test_tot_failure_sets_fallback_reasoning_type(self, base_state, mock_orchestrator_response):
        """ToT failure should set reasoning_type to cot (fallback)."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("complex", {"complexity": "complex"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts",
                new_callable=AsyncMock,
                side_effect=Exception("ToT failed"),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            result = await node_step_64(base_state)

            # Should fall back to CoT
            assert result.get("reasoning_type") == "cot"


# =============================================================================
# Tests: Regression - Existing Behavior Preserved
# =============================================================================


class TestRegressionExistingBehavior:
    """Tests that existing Step 64 behavior is preserved."""

    @pytest.mark.asyncio
    async def test_llm_response_still_stored(self, base_state, mock_orchestrator_response):
        """LLM response should still be stored in state."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("simple", {"complexity": "simple"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            result = await node_step_64(base_state)

            # LLM response should be stored
            assert result.get("llm", {}).get("response") is not None or result.get("llm_response") is not None

    @pytest.mark.asyncio
    async def test_assistant_message_still_added(self, base_state, mock_orchestrator_response):
        """Assistant message should still be added to messages list."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("simple", {"complexity": "simple"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            result = await node_step_64(base_state)

            # Check messages list has assistant response
            messages = result.get("messages", [])
            has_assistant = any(msg.get("role") == "assistant" for msg in messages if isinstance(msg, dict))
            assert has_assistant

    @pytest.mark.asyncio
    async def test_complexity_still_stored(self, base_state, mock_orchestrator_response):
        """Query complexity should still be stored in state."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("complex", {"complexity": "complex"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts",
                new_callable=AsyncMock,
                return_value=MagicMock(
                    reasoning_trace={"test": True},
                    selected_hypothesis=MagicMock(id="H1"),
                    complexity_used="complex",
                ),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            result = await node_step_64(base_state)

            # Complexity should be stored
            assert result.get("query_complexity") == "complex"


# =============================================================================
# Tests: Performance
# =============================================================================


class TestPerformance:
    """Tests for performance requirements."""

    @pytest.mark.asyncio
    async def test_tot_overhead_acceptable(self, base_state, mock_tot_result, mock_orchestrator_response):
        """ToT overhead should be tracked in state."""
        import time

        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        with (
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity",
                new_callable=AsyncMock,
                return_value=("complex", {"complexity": "complex"}),
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts",
                new_callable=AsyncMock,
                return_value=mock_tot_result,
            ),
            patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
                new_callable=AsyncMock,
                return_value=mock_orchestrator_response,
            ),
        ):
            start = time.perf_counter()
            await node_step_64(base_state)
            elapsed_ms = (time.perf_counter() - start) * 1000

            # With mocks, should be very fast
            assert elapsed_ms < 1000  # Under 1 second with mocks
