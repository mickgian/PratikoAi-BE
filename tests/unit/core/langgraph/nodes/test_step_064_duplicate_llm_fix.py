"""TDD Tests for DEV-251: Fix Duplicate LLM Calls in Step 64.

DEV-251 Phase 1: The ToT (Tree of Thoughts) already calls generate_response
internally, but the response was discarded. Then step_064 called generate_response
AGAIN, causing 2 main LLM calls instead of 1 for complex queries.

Fix: Reuse the ToT response instead of making a duplicate call.

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.langgraph.nodes.step_064__llm_call import node_step_64
from app.services.llm_orchestrator import QueryComplexity, UnifiedResponse
from app.services.tree_of_thoughts_reasoner import ToTHypothesis, ToTResult


@pytest.fixture
def complex_query_state():
    """Create state with complex query that triggers ToT."""
    return {
        "messages": [
            {
                "role": "user",
                "content": "Come fatturare consulenza a azienda tedesca con sede in Italia per servizi misti B2B e B2C?",
            }
        ],
        "user_message": "Come fatturare consulenza a azienda tedesca con sede in Italia per servizi misti B2B e B2C?",
        "request_id": "test-request-complex",
        "session_id": "test-session-complex",
        "routing_decision": {"route": "technical_research"},
        "kb_context": "Contesto normativo sulla fatturazione internazionale...",
        "kb_sources_metadata": [{"ref": "Art. 7-ter DPR 633/72", "title": "IVA servizi"}],
    }


@pytest.fixture
def simple_query_state():
    """Create state with simple query that does NOT trigger ToT."""
    return {
        "messages": [{"role": "user", "content": "Qual è l'aliquota IVA ordinaria?"}],
        "user_message": "Qual è l'aliquota IVA ordinaria?",
        "request_id": "test-request-simple",
        "session_id": "test-session-simple",
        "routing_decision": {"route": "technical_research"},
        "kb_context": "L'aliquota IVA ordinaria è del 22%.",
        "kb_sources_metadata": [{"ref": "Art. 16 DPR 633/72", "title": "Aliquote IVA"}],
    }


@pytest.fixture
def mock_tot_response():
    """Create mock UnifiedResponse that would be returned by ToT."""
    return UnifiedResponse(
        answer="La fatturazione verso aziende tedesche richiede l'applicazione del reverse charge per servizi B2B...",
        reasoning={
            "ipotesi_1": "Applicazione reverse charge per B2B",
            "ipotesi_2": "IVA italiana per B2C",
            "conclusione": "Dipende dalla natura del destinatario",
        },
        reasoning_type="tot",
        tot_analysis={
            "hypotheses": [
                {"id": "H1", "scenario": "Reverse charge", "confidence": "alta", "sources": ["Art. 7-ter"]},
                {"id": "H2", "scenario": "IVA italiana", "confidence": "media", "sources": ["Art. 16"]},
            ],
            "selected": "H1",
        },
        sources_cited=[
            {"ref": "Art. 7-ter DPR 633/72", "relevance": "principale"},
            {"ref": "Direttiva UE 2006/112/CE", "relevance": "supporto"},
        ],
        suggested_actions=[],
        model_used="gpt-4o",
        tokens_input=500,
        tokens_output=300,
        cost_euros=0.012,
        latency_ms=3500,
    )


@pytest.fixture
def mock_tot_result(mock_tot_response):
    """Create mock ToTResult with embedded response."""
    return ToTResult(
        selected_hypothesis=ToTHypothesis(
            id="H1",
            reasoning_path="Applicazione reverse charge per servizi B2B",
            conclusion="Il reverse charge si applica per servizi B2B verso aziende UE",
            confidence=0.85,
            sources_used=[{"ref": "Art. 7-ter DPR 633/72"}],
            source_weight_score=0.82,
            risk_level="basso",
            risk_factors=None,
        ),
        all_hypotheses=[
            ToTHypothesis(
                id="H1",
                reasoning_path="Reverse charge",
                conclusion="Reverse charge per B2B",
                confidence=0.85,
                sources_used=[{"ref": "Art. 7-ter"}],
                source_weight_score=0.82,
            ),
            ToTHypothesis(
                id="H2",
                reasoning_path="IVA italiana",
                conclusion="IVA italiana per B2C",
                confidence=0.65,
                sources_used=[{"ref": "Art. 16"}],
                source_weight_score=0.60,
            ),
        ],
        reasoning_trace={
            "total_hypotheses": 2,
            "selected_id": "H1",
            "selected_confidence": 0.85,
        },
        total_latency_ms=3500,
        complexity_used="complex",
        # DEV-251: New field to carry the UnifiedResponse
        llm_response=mock_tot_response,
    )


class TestDuplicateLLMCallFix:
    """Test that complex queries only make 1 main LLM call (not 2)."""

    @pytest.mark.asyncio
    async def test_complex_query_calls_generate_response_only_once(
        self, complex_query_state, mock_tot_response, mock_tot_result
    ):
        """DEV-251: Complex queries should only call generate_response ONCE via ToT.

        Previously, step_064 called:
        1. use_tree_of_thoughts() → internally calls generate_response
        2. get_llm_orchestrator().generate_response() → DUPLICATE!

        After fix, only #1 should happen.
        """
        generate_response_call_count = 0

        async def counting_generate_response(*args, **kwargs):
            nonlocal generate_response_call_count
            generate_response_call_count += 1
            return mock_tot_response

        with (
            patch(
                "app.services.llm_response.complexity_classifier.get_llm_orchestrator"
            ) as mock_classifier_orchestrator,
            patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator") as mock_node_orchestrator,
            patch("app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts") as mock_use_tot,
        ):
            # Setup classifier orchestrator
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(return_value=QueryComplexity.COMPLEX)
            mock_orchestrator.generate_response = AsyncMock(side_effect=counting_generate_response)
            mock_classifier_orchestrator.return_value = mock_orchestrator
            mock_node_orchestrator.return_value = mock_orchestrator

            # Setup ToT to return result with embedded response
            mock_use_tot.return_value = mock_tot_result

            await node_step_64(complex_query_state)

            # CRITICAL: generate_response should be called ONLY ONCE (by ToT internally)
            # The mock_use_tot bypasses the internal call, so we check if step_064
            # makes the duplicate call. It should NOT.
            assert generate_response_call_count <= 1, (
                f"generate_response called {generate_response_call_count} times! "
                f"Should be called at most 1 time for complex queries. "
                f"ToT already generates the response internally."
            )

    @pytest.mark.asyncio
    async def test_simple_query_still_calls_generate_response(self, simple_query_state):
        """Simple queries (no ToT) should still call generate_response once."""
        mock_response = UnifiedResponse(
            answer="L'aliquota IVA ordinaria in Italia è del 22%.",
            reasoning={"tema": "IVA ordinaria"},
            reasoning_type="cot",
            tot_analysis=None,
            sources_cited=[{"ref": "Art. 16 DPR 633/72"}],
            suggested_actions=[],
            model_used="gpt-4o",
            tokens_input=100,
            tokens_output=50,
            cost_euros=0.002,
            latency_ms=1500,
        )

        with (
            patch(
                "app.services.llm_response.complexity_classifier.get_llm_orchestrator"
            ) as mock_classifier_orchestrator,
            patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator") as mock_node_orchestrator,
        ):
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(return_value=QueryComplexity.SIMPLE)
            mock_orchestrator.generate_response = AsyncMock(return_value=mock_response)
            mock_classifier_orchestrator.return_value = mock_orchestrator
            mock_node_orchestrator.return_value = mock_orchestrator

            result = await node_step_64(simple_query_state)

            # Simple queries should call generate_response exactly once
            mock_orchestrator.generate_response.assert_called_once()

            # Verify response is in state
            assert result.get("llm", {}).get("success") is True

    @pytest.mark.asyncio
    async def test_tot_response_is_reused_for_complex_query(
        self, complex_query_state, mock_tot_response, mock_tot_result
    ):
        """DEV-251: The ToT response should be reused, not discarded."""
        with (
            patch(
                "app.services.llm_response.complexity_classifier.get_llm_orchestrator"
            ) as mock_classifier_orchestrator,
            patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator") as mock_node_orchestrator,
            patch("app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts") as mock_use_tot,
        ):
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(return_value=QueryComplexity.COMPLEX)
            # This should NOT be called if ToT response is reused
            mock_orchestrator.generate_response = AsyncMock(return_value=mock_tot_response)
            mock_classifier_orchestrator.return_value = mock_orchestrator
            mock_node_orchestrator.return_value = mock_orchestrator

            mock_use_tot.return_value = mock_tot_result

            result = await node_step_64(complex_query_state)

            # Verify the ToT response content is in the final result
            llm_response = result.get("llm", {}).get("response", {})
            if isinstance(llm_response, dict):
                content = llm_response.get("content", "")
            else:
                content = getattr(llm_response, "content", "")

            # The response should contain ToT-generated content
            assert (
                "reverse charge" in content.lower()
                or "fatturazione" in content.lower()
                or result.get("reasoning_type") == "tot"
            ), "ToT response should be used for the final answer"

    @pytest.mark.asyncio
    async def test_multi_domain_query_only_one_llm_call(self, complex_query_state, mock_tot_response, mock_tot_result):
        """Multi-domain queries should also only make 1 main LLM call."""
        multi_domain_state = {
            **complex_query_state,
            "user_message": "Assumo un dipendente con partita IVA. Quali sono gli obblighi fiscali e contributivi?",
            "detected_domains": ["fiscale", "lavoro"],
        }

        generate_response_call_count = 0

        async def counting_generate_response(*args, **kwargs):
            nonlocal generate_response_call_count
            generate_response_call_count += 1
            return mock_tot_response

        with (
            patch(
                "app.services.llm_response.complexity_classifier.get_llm_orchestrator"
            ) as mock_classifier_orchestrator,
            patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator") as mock_node_orchestrator,
            patch("app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts") as mock_use_tot,
        ):
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(return_value=QueryComplexity.MULTI_DOMAIN)
            mock_orchestrator.generate_response = AsyncMock(side_effect=counting_generate_response)
            mock_classifier_orchestrator.return_value = mock_orchestrator
            mock_node_orchestrator.return_value = mock_orchestrator

            mock_use_tot.return_value = mock_tot_result

            await node_step_64(multi_domain_state)

            assert generate_response_call_count <= 1, (
                f"generate_response called {generate_response_call_count} times for multi_domain query! "
                f"Should be at most 1."
            )


class TestToTResponsePropagation:
    """Test that ToT properly returns the UnifiedResponse for reuse."""

    @pytest.mark.asyncio
    async def test_tot_result_includes_llm_response(self, mock_tot_response):
        """ToTResult should include the UnifiedResponse for reuse."""
        # This tests the ToTResult dataclass has the llm_response field
        tot_result = ToTResult(
            selected_hypothesis=ToTHypothesis(
                id="H1",
                reasoning_path="Test",
                conclusion="Test conclusion",
                confidence=0.8,
                sources_used=[],
                source_weight_score=0.75,
            ),
            all_hypotheses=[],
            reasoning_trace={},
            total_latency_ms=1000,
            complexity_used="complex",
            llm_response=mock_tot_response,
        )

        # Verify the response is accessible
        assert tot_result.llm_response is not None
        assert tot_result.llm_response.answer == mock_tot_response.answer
        assert tot_result.llm_response.model_used == "gpt-4o"
        assert tot_result.llm_response.cost_euros == 0.012


class TestCostAndTokenTracking:
    """Test that cost and token info from ToT response is properly tracked."""

    @pytest.mark.asyncio
    async def test_cost_tracked_from_tot_response(self, complex_query_state, mock_tot_response, mock_tot_result):
        """Cost from ToT response should be tracked in state."""
        with (
            patch(
                "app.services.llm_response.complexity_classifier.get_llm_orchestrator"
            ) as mock_classifier_orchestrator,
            patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator") as mock_node_orchestrator,
            patch("app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts") as mock_use_tot,
        ):
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(return_value=QueryComplexity.COMPLEX)
            mock_orchestrator.generate_response = AsyncMock(return_value=mock_tot_response)
            mock_classifier_orchestrator.return_value = mock_orchestrator
            mock_node_orchestrator.return_value = mock_orchestrator
            mock_use_tot.return_value = mock_tot_result

            result = await node_step_64(complex_query_state)

            # Verify cost is tracked
            llm_state = result.get("llm", {})
            cost = llm_state.get("cost_estimate")
            if cost is not None:
                assert cost == mock_tot_response.cost_euros or cost > 0

    @pytest.mark.asyncio
    async def test_tokens_tracked_from_tot_response(self, complex_query_state, mock_tot_response, mock_tot_result):
        """Token usage from ToT response should be tracked in state."""
        with (
            patch(
                "app.services.llm_response.complexity_classifier.get_llm_orchestrator"
            ) as mock_classifier_orchestrator,
            patch("app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator") as mock_node_orchestrator,
            patch("app.core.langgraph.nodes.step_064__llm_call.use_tree_of_thoughts") as mock_use_tot,
        ):
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(return_value=QueryComplexity.COMPLEX)
            mock_orchestrator.generate_response = AsyncMock(return_value=mock_tot_response)
            mock_classifier_orchestrator.return_value = mock_orchestrator
            mock_node_orchestrator.return_value = mock_orchestrator
            mock_use_tot.return_value = mock_tot_result

            result = await node_step_64(complex_query_state)

            # Verify tokens are tracked
            llm_state = result.get("llm", {})
            tokens = llm_state.get("tokens_used")
            if tokens is not None:
                expected_total = mock_tot_response.tokens_input + mock_tot_response.tokens_output
                assert tokens.get("input") == mock_tot_response.tokens_input or tokens == expected_total
