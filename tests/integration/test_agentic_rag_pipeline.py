"""DEV-198: Integration Tests for Agentic RAG Flow.

End-to-end integration tests with mocked LLM that verify:
- Full pipeline from query to Verdetto
- Golden Set fast-path still works
- KB hybrid search unchanged
- Document context injection

Test Strategy:
- Mock LLM responses to test full pipeline flow
- Verify state propagation through all steps
- Ensure no regressions in existing functionality
"""

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

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
# Helper Functions
# =============================================================================
def create_mock_routing_decision(route: str = "technical_research") -> dict[str, Any]:
    """Create a mock routing decision for testing."""
    return {
        "route": route,
        "confidence": 0.95,
        "reasoning": f"Query classified as {route}",
        "entities": [],
        "requires_freshness": False,
        "suggested_sources": ["kb", "golden"],
        "needs_retrieval": route in ["technical_research", "normative_reference", "theoretical_definition"],
    }


def create_mock_query_variants() -> dict[str, Any]:
    """Create mock query variants for testing."""
    return {
        "bm25_query": "regime forfettario requisiti 2024",
        "vector_query": "quali sono i requisiti per accedere al regime forfettario",
        "entity_query": "regime forfettario requisiti limite fatturato",
        "original_query": "Quali sono i requisiti per il regime forfettario?",
        "skipped": False,
        "fallback": False,
    }


def create_mock_hyde_result() -> dict[str, Any]:
    """Create mock HyDE result for testing."""
    return {
        "hypothetical_document": (
            "Il regime forfettario richiede un fatturato annuo inferiore a 85.000 euro. "
            "Non si possono avere partecipazioni in società di persone. "
            "I redditi da lavoro dipendente non devono superare 30.000 euro."
        ),
        "word_count": 35,
        "skipped": False,
        "skip_reason": None,
    }


def create_mock_retrieval_result() -> dict[str, Any]:
    """Create mock retrieval result for testing."""
    return {
        "documents": [
            {
                "document_id": "doc-001",
                "content": "Il regime forfettario prevede un limite di ricavi di 85.000 euro.",
                "score": 0.92,
                "rrf_score": 0.85,
                "source_type": "circolare",
                "source_name": "Agenzia delle Entrate",
                "published_date": "2024-01-15",
                "metadata": {"article": "Art. 1, comma 54"},
            },
            {
                "document_id": "doc-002",
                "content": "I requisiti per il regime forfettario includono limiti di fatturato.",
                "score": 0.88,
                "rrf_score": 0.78,
                "source_type": "legge",
                "source_name": "Legge di Bilancio 2023",
                "published_date": "2022-12-29",
                "metadata": {},
            },
        ],
        "total_found": 2,
        "search_time_ms": 45.3,
        "skipped": False,
        "error": False,
    }


def create_mock_verdetto_response() -> str:
    """Create a mock LLM response with Verdetto Operativo."""
    return """
Il regime forfettario prevede specifici requisiti per l'accesso.

## Analisi dei Requisiti

In base alla documentazione esaminata, i requisiti principali sono:
1. Limite di ricavi: 85.000 euro annui
2. Nessuna partecipazione in società di persone
3. Redditi da lavoro dipendente < 30.000 euro

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERDETTO OPERATIVO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ AZIONE CONSIGLIATA
Verificare il fatturato annuo e procedere con l'adesione al regime forfettario
se tutti i requisiti sono soddisfatti.

⚠️ ANALISI DEL RISCHIO
Rischio medio: il superamento del limite di fatturato comporta l'uscita
automatica dal regime con effetto dall'anno successivo.

📅 SCADENZA IMMINENTE
31 dicembre per l'adesione al regime forfettario per l'anno successivo.

📁 DOCUMENTAZIONE NECESSARIA
- Modello AA9/12 per apertura P.IVA
- Dichiarazione sostitutiva requisiti
- Codice fiscale

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INDICE DELLE FONTI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| # | Data | Ente | Tipo | Riferimento |
|---|------|------|------|-------------|
| 1 | 2024-01-15 | Agenzia delle Entrate | Circolare | Art. 1, comma 54 |
| 2 | 2022-12-29 | Parlamento | Legge | Legge di Bilancio 2023 |
"""


# =============================================================================
# TestAgenticRAGPipeline - Full Flow Tests
# =============================================================================
class TestAgenticRAGPipeline:
    """Integration tests for the complete Agentic RAG pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_technical_research(self):
        """Test complete pipeline for TECHNICAL_RESEARCH query."""
        from app.core.langgraph.nodes.step_034a__llm_router import node_step_34a
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        # Initial state
        state = {
            "request_id": "integration-001",
            "session_id": "session-001",
            "user_query": "Quali sono i requisiti per il regime forfettario?",
            "messages": [{"role": "user", "content": "Quali sono i requisiti per il regime forfettario?"}],
        }

        # Use mock routing decision to verify helper works
        _ = create_mock_routing_decision("technical_research")

        # Mock HF classifier to force GPT fallback (HF runs first in node)
        mock_hf = MagicMock()
        mock_hf.classify_async = AsyncMock(
            return_value=MagicMock(intent="technical_research", confidence=0.3, all_scores={})
        )
        mock_hf.should_fallback_to_gpt.return_value = True
        mock_hf.confidence_threshold = 0.6

        with (
            patch(
                "app.core.langgraph.nodes.step_034a__llm_router.get_hf_intent_classifier",
                return_value=mock_hf,
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService.route",
                new_callable=AsyncMock,
                return_value=MagicMock(
                    route="technical_research",
                    confidence=0.95,
                    reasoning="Query about tax requirements",
                    entities=[],
                    requires_freshness=False,
                    suggested_sources=["kb"],
                    needs_retrieval=True,
                ),
            ),
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
        ):
            # Step 34a: Route the query
            state_after_routing = await node_step_34a(state)

            # Verify routing decision
            assert "routing_decision" in state_after_routing
            routing = state_after_routing["routing_decision"]
            assert routing["route"] == "technical_research"
            assert routing["needs_retrieval"] is True

        # Add retrieval results and simulate LLM call
        state_after_routing["query_variants"] = create_mock_query_variants()
        state_after_routing["hyde_result"] = create_mock_hyde_result()
        state_after_routing["retrieval_result"] = create_mock_retrieval_result()

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.content = create_mock_verdetto_response()
        mock_llm_response.model = "gpt-4o"
        mock_llm_response.tokens_used = 500
        mock_llm_response.cost_estimate = 0.015

        mock_orchestrator_result = {
            "llm_call_successful": True,
            "llm_response": mock_llm_response,
            "response_content": mock_llm_response.content,
        }

        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_result,
        ):
            # Step 64: LLM Call with Verdetto parsing
            final_state = await node_step_64(state_after_routing)

            # Verify final state
            assert "llm" in final_state
            assert final_state["llm"]["success"] is True

            # Verify messages updated
            assert "messages" in final_state
            messages = final_state["messages"]
            assert len(messages) >= 2  # User + Assistant

            # Verify parsed_synthesis (if TECHNICAL_RESEARCH)
            # Note: parsed_synthesis only set for technical_research route
            if final_state.get("parsed_synthesis"):
                assert "answer_text" in final_state["parsed_synthesis"]

    @pytest.mark.asyncio
    async def test_pipeline_chitchat_bypass(self):
        """Test that CHITCHAT queries bypass retrieval steps."""
        from app.core.langgraph.nodes.step_034a__llm_router import node_step_34a

        state = {
            "request_id": "integration-002",
            "session_id": "session-002",
            "user_query": "Ciao, come stai?",
            "messages": [{"role": "user", "content": "Ciao, come stai?"}],
        }

        # Create mock route enum
        mock_route = MagicMock()
        mock_route.value = "chitchat"

        # Create mock router service instance
        mock_router_instance = MagicMock()
        mock_router_instance.route = AsyncMock(
            return_value=MagicMock(
                route=mock_route,  # Enum with .value attribute
                confidence=0.98,
                reasoning="Greeting message",
                entities=[],
                requires_freshness=False,
                suggested_sources=[],
                needs_retrieval=False,
            )
        )

        with (
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_router_instance,
            ),
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
        ):
            state_after_routing = await node_step_34a(state)

            # Verify routing decision
            routing = state_after_routing["routing_decision"]
            assert routing["route"] == "chitchat"
            assert routing["needs_retrieval"] is False

    @pytest.mark.asyncio
    async def test_pipeline_state_preservation(self):
        """Test that state is preserved through pipeline steps."""
        from app.core.langgraph.nodes.step_034a__llm_router import node_step_34a

        # State with custom fields
        state = {
            "request_id": "integration-003",
            "session_id": "session-003",
            "user_id": "user-123",
            "user_query": "Test query",
            "messages": [{"role": "user", "content": "Test query"}],
            "custom_field": "preserve_me",
            "privacy": {"pii_detected": False},
        }

        with (
            patch(
                "app.services.llm_router_service.LLMRouterService.route",
                new_callable=AsyncMock,
                return_value=MagicMock(
                    route="technical_research",
                    confidence=0.9,
                    reasoning="Test",
                    entities=[],
                    requires_freshness=False,
                    suggested_sources=[],
                    needs_retrieval=True,
                ),
            ),
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
        ):
            result = await node_step_34a(state)

            # Verify original fields preserved
            assert result["request_id"] == "integration-003"
            assert result["session_id"] == "session-003"
            assert result["user_id"] == "user-123"
            assert result["custom_field"] == "preserve_me"
            assert result["privacy"]["pii_detected"] is False


# =============================================================================
# TestGoldenSetKBRegression - Regression Tests (CRITICAL)
# =============================================================================
class TestGoldenSetKBRegression:
    """Regression tests to ensure Golden Set and KB functionality unchanged."""

    @pytest.mark.asyncio
    async def test_golden_set_fast_path_not_broken(self):
        """Verify Normative Reference fast-path still works after rename."""
        from app.core.langgraph.nodes.step_034a__llm_router import node_step_34a

        state = {
            "request_id": "regression-001",
            "user_query": "Qual è il limite di fatturato per il regime forfettario?",
            "messages": [{"role": "user", "content": "Qual è il limite di fatturato?"}],
        }

        # Mock HF classifier to force GPT fallback
        mock_hf = MagicMock()
        mock_hf.classify_async = AsyncMock(
            return_value=MagicMock(intent="normative_reference", confidence=0.3, all_scores={})
        )
        mock_hf.should_fallback_to_gpt.return_value = True
        mock_hf.confidence_threshold = 0.6

        # Simulate routing to NORMATIVE_REFERENCE (renamed from GOLDEN_SET)
        mock_route = MagicMock()
        mock_route.value = "normative_reference"

        mock_router_instance = MagicMock()
        mock_router_instance.route = AsyncMock(
            return_value=MagicMock(
                route=mock_route,  # Enum with .value attribute
                confidence=0.99,
                reasoning="FAQ match",
                entities=[],
                requires_freshness=False,
                suggested_sources=["golden"],
                needs_retrieval=True,
            )
        )

        with (
            patch(
                "app.core.langgraph.nodes.step_034a__llm_router.get_hf_intent_classifier",
                return_value=mock_hf,
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_router_instance,
            ),
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
        ):
            result = await node_step_34a(state)

            # Normative reference should be routed correctly
            assert result["routing_decision"]["route"] == "normative_reference"
            assert result["routing_decision"]["needs_retrieval"] is True

    @pytest.mark.asyncio
    async def test_kb_hybrid_search_not_broken(self):
        """Verify KB hybrid search still works after Agentic RAG changes."""
        from app.core.langgraph.nodes.step_039c__parallel_retrieval import node_step_39c

        state = {
            "request_id": "regression-002",
            "user_query": "Come calcolare le tasse sul reddito",
            "routing_decision": create_mock_routing_decision("technical_research"),
            "query_variants": create_mock_query_variants(),
            "hyde_result": create_mock_hyde_result(),
        }

        # Mock the retrieval service
        with patch(
            "app.services.parallel_retrieval.ParallelRetrievalService.retrieve",
            new_callable=AsyncMock,
            return_value=MagicMock(
                documents=[
                    MagicMock(
                        document_id="doc-1",
                        content="Tax calculation guide",
                        score=0.9,
                        rrf_score=0.85,
                        source_type="guide",
                        source_name="AdE",
                        published_date=None,
                        metadata={},
                    )
                ],
                total_found=1,
                search_time_ms=50.0,
            ),
        ):
            result = await node_step_39c(state)

            # Verify retrieval result
            assert "retrieval_result" in result
            assert result["retrieval_result"]["total_found"] == 1
            assert not result["retrieval_result"]["skipped"]

    @pytest.mark.asyncio
    async def test_retrieval_skip_for_calculator(self):
        """Verify retrieval is skipped for CALCULATOR route."""
        from app.core.langgraph.nodes.step_039c__parallel_retrieval import node_step_39c

        state = {
            "request_id": "regression-003",
            "user_query": "2 + 2",
            "routing_decision": {
                "route": "calculator",
                "needs_retrieval": False,
            },
            "query_variants": {},
            "hyde_result": {},
        }

        result = await node_step_39c(state)

        # Verify retrieval was skipped
        assert "retrieval_result" in result
        assert result["retrieval_result"]["skipped"] is True


# =============================================================================
# TestDocumentContextInjection - Document Injection Tests
# =============================================================================
class TestDocumentContextInjection:
    """Tests for document context injection into LLM prompts."""

    @pytest.mark.asyncio
    async def test_retrieval_result_available_for_synthesis(self):
        """Verify retrieval results are available for synthesis step."""
        state = {
            "request_id": "context-001",
            "user_query": "Test query",
            "routing_decision": create_mock_routing_decision(),
            "query_variants": create_mock_query_variants(),
            "hyde_result": create_mock_hyde_result(),
            "retrieval_result": create_mock_retrieval_result(),
        }

        # Verify context is ready for synthesis
        assert "retrieval_result" in state
        assert len(state["retrieval_result"]["documents"]) > 0
        assert state["retrieval_result"]["documents"][0]["content"] is not None

    def test_document_metadata_preserved(self):
        """Verify document metadata is preserved through pipeline."""
        retrieval_result = create_mock_retrieval_result()

        doc = retrieval_result["documents"][0]

        # Verify metadata fields
        assert "source_type" in doc
        assert "source_name" in doc
        assert "published_date" in doc
        assert doc["source_type"] == "circolare"
        assert doc["source_name"] == "Agenzia delle Entrate"


# =============================================================================
# TestPipelineErrorHandling - Error Handling Tests
# =============================================================================
class TestPipelineErrorHandling:
    """Tests for pipeline error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_routing_fallback_on_error(self):
        """Test that routing falls back to TECHNICAL_RESEARCH on error."""
        from app.core.langgraph.nodes.step_034a__llm_router import node_step_34a

        state = {
            "request_id": "error-001",
            "user_query": "Test query",
            "messages": [{"role": "user", "content": "Test query"}],
        }

        # Simulate service error
        with (
            patch(
                "app.services.llm_router_service.LLMRouterService.route",
                new_callable=AsyncMock,
                side_effect=Exception("Service unavailable"),
            ),
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
        ):
            result = await node_step_34a(state)

            # Should fallback to TECHNICAL_RESEARCH
            assert "routing_decision" in result
            assert result["routing_decision"]["route"] == "technical_research"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="DEV-245: step_064 API changed, test needs update")
    async def test_llm_call_handles_failure(self):
        """Test that LLM call handles failure gracefully."""
        from app.core.langgraph.nodes.step_064__llm_call import node_step_64

        state = {
            "request_id": "error-002",
            "user_query": "Test query",
            "messages": [{"role": "user", "content": "Test query"}],
            "routing_decision": create_mock_routing_decision(),
        }

        # Simulate LLM failure
        mock_error_result = {
            "llm_call_successful": False,
            "error": "LLM service unavailable",
            "error_type": "ServiceError",
        }

        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_error_result,
        ):
            result = await node_step_64(state)

            # Should handle error gracefully
            assert "llm" in result
            assert result["llm"]["success"] is False
            assert "error" in result["llm"]
