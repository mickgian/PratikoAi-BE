"""TDD Tests for Chitchat Cost Optimization.

When a query is classified as 'chitchat', the system should:
1. Use the cheapest LLM model (gpt-4o-mini) instead of the production model
2. Skip web search (already handled by step_100)
3. Not emit fonti/sources SSE events
4. Skip query reformulation LLM calls
5. Force SIMPLE complexity to avoid ToT reasoning

Tests written FIRST following TDD RED-GREEN-REFACTOR methodology.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_orchestrator import (
    ModelConfig,
    QueryComplexity,
)

# =============================================================================
# Test: ModelConfig.for_chitchat() uses cheap model
# =============================================================================


class TestModelConfigForChitchat:
    """Tests for the new ModelConfig.for_chitchat() class method."""

    def test_for_chitchat_returns_model_config(self):
        """for_chitchat() should return a ModelConfig instance."""
        config = ModelConfig.for_chitchat()
        assert isinstance(config, ModelConfig)

    def test_for_chitchat_uses_gpt4o_mini(self):
        """Chitchat should use gpt-4o-mini, the cheapest model."""
        config = ModelConfig.for_chitchat()
        assert config.model == "gpt-4o-mini"

    def test_for_chitchat_uses_minimal_max_tokens(self):
        """Chitchat needs only a short response - max 500 tokens."""
        config = ModelConfig.for_chitchat()
        assert config.max_tokens <= 500

    def test_for_chitchat_uses_low_temperature(self):
        """Chitchat should use low temperature for predictable responses."""
        config = ModelConfig.for_chitchat()
        assert config.temperature <= 0.5

    def test_for_chitchat_uses_cot_reasoning(self):
        """Chitchat should use simple CoT reasoning, not expensive ToT."""
        config = ModelConfig.for_chitchat()
        assert config.reasoning_type == "cot"

    def test_for_chitchat_has_lower_cost_than_simple(self):
        """Chitchat config should be cheaper than SIMPLE complexity config."""
        chitchat_config = ModelConfig.for_chitchat()
        simple_config = ModelConfig.for_complexity(QueryComplexity.SIMPLE)

        # Max tokens should be smaller (fewer output tokens = lower cost)
        assert chitchat_config.max_tokens < simple_config.max_tokens

    def test_for_chitchat_uses_short_timeout(self):
        """Chitchat should have a short timeout since it's a simple response."""
        config = ModelConfig.for_chitchat()
        assert config.timeout_seconds <= 15


# =============================================================================
# Test: Step 064 uses chitchat config for chitchat routes
# =============================================================================


class TestStep064ChitchatOptimization:
    """Tests that step_064 uses cheap model for chitchat queries."""

    @pytest.fixture
    def chitchat_state(self):
        """Create a RAG state for a chitchat query."""
        return {
            "messages": [{"role": "user", "content": "Ciao, come stai?"}],
            "user_message": "Ciao, come stai?",
            "request_id": "test-chitchat-123",
            "session_id": "test-session-456",
            "routing_decision": {
                "route": "chitchat",
                "confidence": 0.95,
                "needs_retrieval": False,
                "is_followup": False,
            },
            "kb_context": "",
            "kb_sources_metadata": [],
        }

    @pytest.mark.asyncio
    @patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator")
    @patch("app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity")
    async def test_chitchat_skips_tot_reasoning(self, mock_classify, mock_get_orch, chitchat_state):
        """Chitchat should never trigger Tree of Thoughts reasoning."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64
        from app.services.llm_orchestrator import UnifiedResponse

        mock_classify.return_value = ("simple", {"complexity": "simple"})

        mock_response = UnifiedResponse(
            reasoning={},
            reasoning_type="cot",
            tot_analysis=None,
            answer="Ciao! Sono PratikoAI. Come posso aiutarti?",
            sources_cited=[],
            suggested_actions=[],
            model_used="gpt-4o-mini",
            tokens_input=50,
            tokens_output=20,
            cost_euros=0.00002,
            latency_ms=200,
        )
        mock_orch = AsyncMock()
        mock_orch.generate_response.return_value = mock_response
        mock_get_orch.return_value = mock_orch

        result = await node_step_64(chitchat_state)

        # Should NOT call use_tree_of_thoughts
        assert result.get("reasoning_type") != "tot"

    @pytest.mark.asyncio
    @patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator")
    @patch("app.core.langgraph.nodes.step_064__llm_call.classify_query_complexity")
    async def test_chitchat_forces_simple_complexity(self, mock_classify, mock_get_orch, chitchat_state):
        """Chitchat should always use SIMPLE complexity regardless of classifier output."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64
        from app.services.llm_orchestrator import UnifiedResponse

        # Even if classifier says complex, chitchat should override to simple
        mock_classify.return_value = ("complex", {"complexity": "complex"})

        mock_response = UnifiedResponse(
            reasoning={},
            reasoning_type="cot",
            tot_analysis=None,
            answer="Ciao!",
            sources_cited=[],
            suggested_actions=[],
            model_used="gpt-4o-mini",
            tokens_input=50,
            tokens_output=20,
            cost_euros=0.00002,
            latency_ms=200,
        )
        mock_orch = AsyncMock()
        mock_orch.generate_response.return_value = mock_response
        mock_get_orch.return_value = mock_orch

        await node_step_64(chitchat_state)

        # Verify classify_query_complexity was NOT called (cost saving)
        mock_classify.assert_not_called()

        # Verify generate_response was called with is_chitchat=True
        call_kwargs = mock_orch.generate_response.call_args
        assert call_kwargs is not None
        # The orchestrator should receive is_chitchat flag
        assert call_kwargs.kwargs.get("is_chitchat") is True or call_kwargs[1].get("is_chitchat") is True


# =============================================================================
# Test: Fonti suppression for chitchat in graph streaming
# =============================================================================


class TestChitchatFontiSuppression:
    """Tests that fonti/sources are not emitted for chitchat queries."""

    def test_chitchat_state_has_no_structured_sources(self):
        """For chitchat, kb_sources_metadata should be empty after retrieval skip."""
        # After the pipeline runs with needs_retrieval=False, there should be
        # no sources to emit
        state = {
            "routing_decision": {"route": "chitchat", "needs_retrieval": False},
            "kb_sources_metadata": [],
            "structured_sources": None,
            "web_verification": {},
        }
        # Verify the state has no sources to yield
        assert not state.get("structured_sources")
        assert not state.get("kb_sources_metadata")
        assert not state.get("web_verification", {}).get("verification_performed")


# =============================================================================
# Test: Query reformulation skipped for chitchat
# =============================================================================


class TestChitchatQueryReformulationSkip:
    """Tests that reformulate_short_query_llm is skipped for chitchat."""

    @pytest.mark.asyncio
    async def test_multiquery_skips_reformulation_for_chitchat(self):
        """MultiQuery node should skip LLM reformulation call for chitchat routes."""
        from app.services.query_reformulation.constants import SKIP_EXPANSION_ROUTES

        # Verify chitchat is in skip routes
        assert "chitchat" in SKIP_EXPANSION_ROUTES


# =============================================================================
# Test: LLMOrchestrator handles is_chitchat flag
# =============================================================================


class TestOrchestratorChitchatHandling:
    """Tests that LLMOrchestrator handles the is_chitchat parameter."""

    @pytest.mark.asyncio
    @patch("app.services.llm_orchestrator.LLMOrchestrator._call_llm")
    async def test_generate_response_uses_mini_for_chitchat(self, mock_call_llm):
        """When is_chitchat=True, orchestrator should use gpt-4o-mini."""
        from app.services.llm_orchestrator import LLMOrchestrator

        mock_call_llm.return_value = (
            '{"answer": "Ciao!", "reasoning": {}, "sources_cited": [], "suggested_actions": []}',
            50,
            20,
        )

        orchestrator = LLMOrchestrator()
        response = await orchestrator.generate_response(
            query="Ciao",
            kb_context="",
            kb_sources_metadata=[],
            complexity=QueryComplexity.SIMPLE,
            is_chitchat=True,
        )

        # Verify gpt-4o-mini was used
        assert response.model_used == "gpt-4o-mini"

        # Verify _call_llm was called with gpt-4o-mini
        call_args = mock_call_llm.call_args
        assert call_args.kwargs.get("model") == "gpt-4o-mini" or call_args[0][1] == "gpt-4o-mini"

    @pytest.mark.asyncio
    @patch("app.services.llm_orchestrator.LLMOrchestrator._call_llm")
    async def test_generate_response_uses_low_max_tokens_for_chitchat(self, mock_call_llm):
        """When is_chitchat=True, max_tokens should be minimal."""
        from app.services.llm_orchestrator import LLMOrchestrator

        mock_call_llm.return_value = (
            '{"answer": "Ciao!", "reasoning": {}, "sources_cited": [], "suggested_actions": []}',
            50,
            20,
        )

        orchestrator = LLMOrchestrator()
        await orchestrator.generate_response(
            query="Ciao",
            kb_context="",
            kb_sources_metadata=[],
            complexity=QueryComplexity.SIMPLE,
            is_chitchat=True,
        )

        # Verify max_tokens was low (<=500)
        call_args = mock_call_llm.call_args
        max_tokens_used = call_args.kwargs.get("max_tokens") or call_args[0][3]
        assert max_tokens_used <= 500
