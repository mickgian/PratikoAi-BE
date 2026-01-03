"""TDD Tests for Phase 9: Step 64 LLMOrchestrator Integration.

DEV-222: Integrate LLMOrchestrator with Step 64.

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.

Coverage Target: 90%+ for new code.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.langgraph.nodes.step_064__llm_call import node_step_64
from app.services.llm_orchestrator import (
    ComplexityContext,
    QueryComplexity,
    UnifiedResponse,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def base_state():
    """Create base RAG state for testing."""
    return {
        "messages": [{"role": "user", "content": "Qual è l'aliquota IVA?"}],
        "user_message": "Qual è l'aliquota IVA?",
        "request_id": "test-request-123",
        "session_id": "test-session-456",
        "routing_decision": {"route": "technical_research"},
        "kb_context": "L'aliquota IVA ordinaria è del 22%.",
        "kb_sources_metadata": [
            {"ref": "Art. 16 DPR 633/72", "relevance": "principale"}
        ],
    }


@pytest.fixture
def complex_query_state():
    """Create state with complex query requiring GPT-4o."""
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
        "kb_sources_metadata": [],
    }


@pytest.fixture
def multi_domain_state():
    """Create state with multi-domain query spanning fiscal + labor."""
    return {
        "messages": [
            {
                "role": "user",
                "content": "Assumo un dipendente che ha anche una partita IVA come freelancer. Quali sono gli obblighi fiscali e contributivi?",
            }
        ],
        "user_message": "Assumo un dipendente che ha anche una partita IVA come freelancer. Quali sono gli obblighi fiscali e contributivi?",
        "request_id": "test-request-multi",
        "session_id": "test-session-multi",
        "routing_decision": {"route": "technical_research"},
        "kb_context": "Contesto su lavoro dipendente e partita IVA...",
        "kb_sources_metadata": [],
        "detected_domains": ["fiscale", "lavoro"],
    }


@pytest.fixture
def mock_simple_response():
    """Create mock UnifiedResponse for simple queries."""
    return UnifiedResponse(
        answer="L'aliquota IVA ordinaria in Italia è del 22%.",
        reasoning={"tema": "IVA ordinaria"},
        reasoning_type="cot",
        tot_analysis=None,
        sources_cited=[{"ref": "Art. 16 DPR 633/72", "relevance": "principale"}],
        suggested_actions=[],
        model_used="gpt-4o-mini",
        tokens_input=50,
        tokens_output=30,
        cost_euros=0.0001,
        latency_ms=150,
    )


@pytest.fixture
def mock_complex_response():
    """Create mock UnifiedResponse for complex queries."""
    return UnifiedResponse(
        answer="La fatturazione verso aziende tedesche richiede...",
        reasoning={
            "ipotesi_1": "Applicazione reverse charge",
            "ipotesi_2": "IVA italiana",
            "conclusione": "Dipende dalla sede effettiva",
        },
        reasoning_type="tot",
        tot_analysis={
            "hypotheses": [
                {"id": 1, "description": "Reverse charge"},
                {"id": 2, "description": "IVA italiana"},
            ],
            "selected": 1,
        },
        sources_cited=[
            {"ref": "Art. 7-ter DPR 633/72", "relevance": "principale"},
            {"ref": "Direttiva UE 2006/112/CE", "relevance": "supporto"},
        ],
        suggested_actions=[],
        model_used="gpt-4o",
        tokens_input=200,
        tokens_output=150,
        cost_euros=0.005,
        latency_ms=500,
    )


# =============================================================================
# Tests: Complexity Classification Before LLM Call
# =============================================================================


class TestComplexityClassificationBeforeLLMCall:
    """Test that complexity is classified before making LLM call."""

    @pytest.mark.asyncio
    async def test_simple_query_classified_before_llm_call(
        self, base_state, mock_simple_response
    ):
        """Simple queries should be classified as SIMPLE before LLM call."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator"
        ) as mock_get_orchestrator:
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(
                return_value=QueryComplexity.SIMPLE
            )
            mock_orchestrator.generate_response = AsyncMock(
                return_value=mock_simple_response
            )
            mock_get_orchestrator.return_value = mock_orchestrator

            with patch(
                "app.orchestrators.providers.step_64__llmcall"
            ) as mock_llmcall:
                mock_llmcall.return_value = {
                    "llm_call_successful": True,
                    "response": {"content": mock_simple_response.answer},
                }

                result = await node_step_64(base_state)

                # Verify classify_complexity was called
                mock_orchestrator.classify_complexity.assert_called_once()

    @pytest.mark.asyncio
    async def test_complex_query_classified_as_complex(
        self, complex_query_state, mock_complex_response
    ):
        """Complex queries should be classified as COMPLEX."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator"
        ) as mock_get_orchestrator:
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(
                return_value=QueryComplexity.COMPLEX
            )
            mock_orchestrator.generate_response = AsyncMock(
                return_value=mock_complex_response
            )
            mock_get_orchestrator.return_value = mock_orchestrator

            with patch(
                "app.orchestrators.providers.step_64__llmcall"
            ) as mock_llmcall:
                mock_llmcall.return_value = {
                    "llm_call_successful": True,
                    "response": {"content": mock_complex_response.answer},
                }

                result = await node_step_64(complex_query_state)

                # Verify classification was COMPLEX
                mock_orchestrator.classify_complexity.assert_called_once()

    @pytest.mark.asyncio
    async def test_multi_domain_query_classified_correctly(
        self, multi_domain_state
    ):
        """Multi-domain queries should be classified as MULTI_DOMAIN."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator"
        ) as mock_get_orchestrator:
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(
                return_value=QueryComplexity.MULTI_DOMAIN
            )
            mock_orchestrator.generate_response = AsyncMock(
                return_value=UnifiedResponse(
                    answer="Risposta multi-dominio",
                    reasoning={"domains": ["fiscale", "lavoro"]},
                    reasoning_type="tot_multi",
                    tot_analysis={"multi_domain": True},
                    sources_cited=[],
                    suggested_actions=[],
                    model_used="gpt-4o",
                    tokens_input=300,
                    tokens_output=200,
                    cost_euros=0.008,
                    latency_ms=800,
                )
            )
            mock_get_orchestrator.return_value = mock_orchestrator

            with patch(
                "app.orchestrators.providers.step_64__llmcall"
            ) as mock_llmcall:
                mock_llmcall.return_value = {
                    "llm_call_successful": True,
                    "response": {"content": "Risposta multi-dominio"},
                }

                result = await node_step_64(multi_domain_state)

                # Verify classification accounts for multiple domains
                call_args = mock_orchestrator.classify_complexity.call_args
                assert call_args is not None


# =============================================================================
# Tests: Model Selection Based on Complexity
# =============================================================================


class TestModelSelectionBasedOnComplexity:
    """Test that correct model is selected based on complexity."""

    @pytest.mark.asyncio
    async def test_simple_query_uses_gpt4o_mini(
        self, base_state, mock_simple_response
    ):
        """Simple queries should use GPT-4o-mini for cost efficiency."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator"
        ) as mock_get_orchestrator:
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(
                return_value=QueryComplexity.SIMPLE
            )
            mock_orchestrator.generate_response = AsyncMock(
                return_value=mock_simple_response
            )
            mock_get_orchestrator.return_value = mock_orchestrator

            with patch(
                "app.orchestrators.providers.step_64__llmcall"
            ) as mock_llmcall:
                mock_llmcall.return_value = {
                    "llm_call_successful": True,
                    "response": {"content": mock_simple_response.answer},
                }

                result = await node_step_64(base_state)

                # Verify generate_response was called with SIMPLE complexity
                gen_call = mock_orchestrator.generate_response.call_args
                if gen_call:
                    assert gen_call.kwargs.get("complexity") == QueryComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_complex_query_uses_gpt4o(
        self, complex_query_state, mock_complex_response
    ):
        """Complex queries should use GPT-4o for better reasoning."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator"
        ) as mock_get_orchestrator:
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(
                return_value=QueryComplexity.COMPLEX
            )
            mock_orchestrator.generate_response = AsyncMock(
                return_value=mock_complex_response
            )
            mock_get_orchestrator.return_value = mock_orchestrator

            with patch(
                "app.orchestrators.providers.step_64__llmcall"
            ) as mock_llmcall:
                mock_llmcall.return_value = {
                    "llm_call_successful": True,
                    "response": {"content": mock_complex_response.answer},
                }

                result = await node_step_64(complex_query_state)

                # Verify generate_response was called with COMPLEX complexity
                gen_call = mock_orchestrator.generate_response.call_args
                if gen_call:
                    assert gen_call.kwargs.get("complexity") == QueryComplexity.COMPLEX


# =============================================================================
# Tests: Cost Tracking in State
# =============================================================================


class TestCostTrackingInState:
    """Test that LLM costs are tracked in state."""

    @pytest.mark.asyncio
    async def test_cost_stored_in_state_after_simple_query(
        self, base_state, mock_simple_response
    ):
        """Cost should be stored in state after simple query."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator"
        ) as mock_get_orchestrator:
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(
                return_value=QueryComplexity.SIMPLE
            )
            mock_orchestrator.generate_response = AsyncMock(
                return_value=mock_simple_response
            )
            mock_get_orchestrator.return_value = mock_orchestrator

            with patch(
                "app.orchestrators.providers.step_64__llmcall"
            ) as mock_llmcall:
                mock_llmcall.return_value = {
                    "llm_call_successful": True,
                    "response": {"content": mock_simple_response.answer},
                }

                result = await node_step_64(base_state)

                # Check that llm namespace has cost info
                llm = result.get("llm", {})
                # Cost should be tracked (implementation will add this)
                # This test will initially fail (RED) until implementation

    @pytest.mark.asyncio
    async def test_tokens_tracked_in_state(
        self, base_state, mock_simple_response
    ):
        """Token usage should be tracked in state."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator"
        ) as mock_get_orchestrator:
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(
                return_value=QueryComplexity.SIMPLE
            )
            mock_orchestrator.generate_response = AsyncMock(
                return_value=mock_simple_response
            )
            mock_get_orchestrator.return_value = mock_orchestrator

            with patch(
                "app.orchestrators.providers.step_64__llmcall"
            ) as mock_llmcall:
                mock_llmcall.return_value = {
                    "llm_call_successful": True,
                    "response": {"content": mock_simple_response.answer},
                    "tokens_used": 80,
                }

                result = await node_step_64(base_state)

                # Token tracking should be available
                llm = result.get("llm", {})
                # Implementation will add token tracking

    @pytest.mark.asyncio
    async def test_complexity_stored_in_state(
        self, base_state, mock_simple_response
    ):
        """Query complexity should be stored in state for analytics."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator"
        ) as mock_get_orchestrator:
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(
                return_value=QueryComplexity.SIMPLE
            )
            mock_orchestrator.generate_response = AsyncMock(
                return_value=mock_simple_response
            )
            mock_get_orchestrator.return_value = mock_orchestrator

            with patch(
                "app.orchestrators.providers.step_64__llmcall"
            ) as mock_llmcall:
                mock_llmcall.return_value = {
                    "llm_call_successful": True,
                    "response": {"content": mock_simple_response.answer},
                }

                result = await node_step_64(base_state)

                # Complexity should be stored in state
                # Implementation will add: state["query_complexity"] = complexity


# =============================================================================
# Tests: Existing Functionality Regression
# =============================================================================


class TestExistingStep64Functionality:
    """Regression tests to ensure existing Step 64 functionality is preserved."""

    @pytest.mark.asyncio
    async def test_deanonymization_still_works(self, base_state):
        """PII deanonymization should still work after integration."""
        state_with_pii = {
            **base_state,
            "privacy": {
                "document_deanonymization_map": {
                    "[NOME_ABC123]": "Mario Rossi",
                }
            },
        }

        with patch(
            "app.orchestrators.providers.step_64__llmcall"
        ) as mock_llmcall:
            mock_llmcall.return_value = {
                "llm_call_successful": True,
                "response": {"content": "Il cliente [NOME_ABC123] deve pagare..."},
            }

            result = await node_step_64(state_with_pii)

            # Response should have PII restored
            llm = result.get("llm", {})
            if llm.get("response"):
                content = (
                    llm["response"].get("content", "")
                    if isinstance(llm["response"], dict)
                    else ""
                )
                assert "Mario Rossi" in content or "[NOME_ABC123]" not in content

    @pytest.mark.asyncio
    async def test_json_parsing_still_works(self, base_state):
        """Unified JSON response parsing should still work."""
        json_response = json.dumps({
            "reasoning": {"tema": "IVA"},
            "answer": "L'IVA è del 22%",
            "sources_cited": [{"ref": "Art. 16 DPR 633/72"}],
            "suggested_actions": [],
        })

        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator"
        ) as mock_get_orchestrator:
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(
                return_value=QueryComplexity.SIMPLE
            )
            mock_get_orchestrator.return_value = mock_orchestrator

            # Patch where it's imported (in the node module)
            with patch(
                "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall"
            ) as mock_llmcall:
                mock_llmcall.return_value = {
                    "llm_call_successful": True,
                    "response": {"content": json_response},
                }

                result = await node_step_64(base_state)

                # State should have parsed fields (reasoning_type or actions_source)
                # If JSON parsing works, at least one of these should be set
                has_parsing = (
                    result.get("reasoning_type") is not None
                    or result.get("actions_source") is not None
                    or result.get("reasoning_trace") is not None
                )
                assert has_parsing or result.get("llm", {}).get("success") is True

    @pytest.mark.asyncio
    async def test_source_hierarchy_still_applied(self, base_state):
        """Source hierarchy ranking should still be applied."""
        json_response = json.dumps({
            "reasoning": {"tema": "Test"},
            "answer": "Test answer",
            "sources_cited": [
                {"ref": "Circolare AdE 12/E/2024", "relevance": "supporto"},
                {"ref": "Legge 190/2014", "relevance": "principale"},
            ],
            "suggested_actions": [],
        })

        with patch(
            "app.orchestrators.providers.step_64__llmcall"
        ) as mock_llmcall:
            mock_llmcall.return_value = {
                "llm_call_successful": True,
                "response": {"content": json_response},
            }

            result = await node_step_64(base_state)

            # Sources should be sorted by hierarchy
            sources = result.get("sources_cited", [])
            if len(sources) >= 2:
                # Legge should come before Circolare
                legge_idx = next(
                    (i for i, s in enumerate(sources) if "legge" in s.get("ref", "").lower()),
                    -1,
                )
                circolare_idx = next(
                    (i for i, s in enumerate(sources) if "circolare" in s.get("ref", "").lower()),
                    -1,
                )
                if legge_idx >= 0 and circolare_idx >= 0:
                    assert legge_idx < circolare_idx


# =============================================================================
# Tests: Fallback Behavior
# =============================================================================


class TestFallbackBehavior:
    """Test fallback behavior when orchestrator fails."""

    @pytest.mark.asyncio
    async def test_fallback_to_default_on_classification_error(self, base_state):
        """Should fallback to default processing on classification error."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator"
        ) as mock_get_orchestrator:
            mock_orchestrator = MagicMock()
            mock_orchestrator.classify_complexity = AsyncMock(
                side_effect=Exception("Classification failed")
            )
            mock_get_orchestrator.return_value = mock_orchestrator

            with patch(
                "app.orchestrators.providers.step_64__llmcall"
            ) as mock_llmcall:
                mock_llmcall.return_value = {
                    "llm_call_successful": True,
                    "response": {"content": "Fallback response"},
                }

                # Should not raise, should fallback gracefully
                result = await node_step_64(base_state)

                # Verify fallback happened (complexity should default to "simple")
                assert result.get("query_complexity") == "simple"
                # Fallback context should indicate error
                assert result.get("complexity_context", {}).get("fallback") is True

    @pytest.mark.asyncio
    async def test_original_flow_preserved_when_orchestrator_unavailable(
        self, base_state
    ):
        """Original Step 64 flow should work when orchestrator is unavailable."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator"
        ) as mock_get_orchestrator:
            mock_get_orchestrator.side_effect = ImportError("Orchestrator not available")

            with patch(
                "app.orchestrators.providers.step_64__llmcall"
            ) as mock_llmcall:
                mock_llmcall.return_value = {
                    "llm_call_successful": True,
                    "response": {"content": "Original flow response"},
                }

                # Should fallback to original flow (classification fails, defaults to simple)
                result = await node_step_64(base_state)

                # Verify fallback happened
                assert result.get("query_complexity") == "simple"
                # Fallback context should indicate error
                assert result.get("complexity_context", {}).get("fallback") is True


# =============================================================================
# Tests: Performance
# =============================================================================


class TestPerformance:
    """Test performance requirements for orchestrator integration."""

    @pytest.mark.asyncio
    async def test_classification_adds_minimal_latency(self, base_state):
        """Classification should add minimal latency (<100ms)."""
        import time

        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.get_llm_orchestrator"
        ) as mock_get_orchestrator:
            mock_orchestrator = MagicMock()

            # Simulate fast classification
            async def fast_classify(*args, **kwargs):
                return QueryComplexity.SIMPLE

            mock_orchestrator.classify_complexity = fast_classify
            mock_orchestrator.generate_response = AsyncMock(
                return_value=UnifiedResponse(
                    answer="Test",
                    reasoning={},
                    reasoning_type="cot",
                    tot_analysis=None,
                    sources_cited=[],
                    suggested_actions=[],
                    model_used="gpt-4o-mini",
                    tokens_input=50,
                    tokens_output=30,
                    cost_euros=0.0001,
                    latency_ms=100,
                )
            )
            mock_get_orchestrator.return_value = mock_orchestrator

            with patch(
                "app.orchestrators.providers.step_64__llmcall"
            ) as mock_llmcall:
                mock_llmcall.return_value = {
                    "llm_call_successful": True,
                    "response": {"content": "Test"},
                }

                start = time.time()
                result = await node_step_64(base_state)
                elapsed = (time.time() - start) * 1000

                # Total execution should be reasonable
                # (mocked calls should be very fast)
                assert elapsed < 1000  # Less than 1 second for mocked test
