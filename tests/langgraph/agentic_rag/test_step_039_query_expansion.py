"""TDD Tests for Step 39: Query Expansion Nodes (DEV-195).

These nodes integrate MultiQueryGenerator, HyDEGenerator, and ParallelRetrieval
services into the RAG pipeline for enhanced document retrieval.

Test Strategy:
- Mock services to test node wrapper logic in isolation
- Verify state updates for query_variants, hyde_result, retrieval_result
- Verify skip logic for non-technical routes
- Verify error handling and fallback behavior
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# Mock database service BEFORE importing any app modules
# This prevents the database connection attempt during module import
# =============================================================================
_mock_db_service = MagicMock()
_mock_db_service.engine = MagicMock()
_mock_db_service.get_session = MagicMock()

# Create a mock module for app.services.database
_mock_db_module = MagicMock()
_mock_db_module.database_service = _mock_db_service
_mock_db_module.DatabaseService = MagicMock(return_value=_mock_db_service)

# Inject the mock into sys.modules BEFORE any imports
sys.modules.setdefault("app.services.database", _mock_db_module)


# Define local dataclasses to avoid importing from app.services (triggers database)
@dataclass
class QueryVariants:
    """Local copy for testing - avoids database import chain."""

    bm25_query: str
    vector_query: str
    entity_query: str
    original_query: str


@dataclass
class HyDEResult:
    """Local copy for testing - avoids database import chain."""

    hypothetical_document: str
    word_count: int
    skipped: bool
    skip_reason: str | None


@dataclass
class RankedDocument:
    """Local copy for testing - avoids database import chain."""

    document_id: str
    content: str
    score: float
    rrf_score: float
    source_type: str
    source_name: str
    published_date: datetime | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Local copy for testing - avoids database import chain."""

    documents: list[RankedDocument]
    total_found: int
    search_time_ms: float


# =============================================================================
# TestNodeStep39aMultiQuery - Multi-Query Generation Tests
# =============================================================================
class TestNodeStep39aMultiQuery:
    """Tests for Step 39a Multi-Query node wrapper."""

    @pytest.mark.asyncio
    async def test_successful_multi_query_generation(self):
        """Test successful multi-query generation for technical research."""
        from app.core.langgraph.nodes.step_039a__multi_query import node_step_39a

        mock_service = AsyncMock()
        mock_service.generate.return_value = QueryVariants(
            bm25_query="P.IVA forfettaria apertura requisiti",
            vector_query="Come aprire una partita IVA con regime forfettario?",
            entity_query="Agenzia Entrate P.IVA regime forfettario",
            original_query="Come apro P.IVA forfettaria?",
        )

        with (
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.multi_query_generator.MultiQueryGeneratorService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-001",
                "user_query": "Come apro P.IVA forfettaria?",
                "routing_decision": {
                    "route": "technical_research",
                    "needs_retrieval": True,
                    "entities": [],
                },
            }

            result = await node_step_39a(state)

            assert "query_variants" in result
            assert result["query_variants"]["bm25_query"] == "P.IVA forfettaria apertura requisiti"
            assert result["query_variants"]["original_query"] == "Come apro P.IVA forfettaria?"

    @pytest.mark.asyncio
    async def test_skip_for_chitchat_route(self):
        """Test that multi-query is skipped for chitchat queries."""
        from app.core.langgraph.nodes.step_039a__multi_query import node_step_39a

        state = {
            "request_id": "test-002",
            "user_query": "Ciao, come stai?",
            "routing_decision": {
                "route": "chitchat",
                "needs_retrieval": False,
            },
        }

        result = await node_step_39a(state)

        assert "query_variants" in result
        assert result["query_variants"]["skipped"] is True
        assert result["query_variants"]["skip_reason"] == "chitchat"

    @pytest.mark.asyncio
    async def test_skip_for_theoretical_definition_route(self):
        """Test that multi-query is skipped for theoretical definition queries."""
        from app.core.langgraph.nodes.step_039a__multi_query import node_step_39a

        state = {
            "request_id": "test-003",
            "user_query": "Cos'e l'IRPEF?",
            "routing_decision": {
                "route": "theoretical_definition",
                "needs_retrieval": True,
            },
        }

        result = await node_step_39a(state)

        assert result["query_variants"]["skipped"] is True
        assert result["query_variants"]["skip_reason"] == "theoretical_definition"

    @pytest.mark.asyncio
    async def test_fallback_on_service_error(self):
        """Test fallback to original query on service error."""
        from app.core.langgraph.nodes.step_039a__multi_query import node_step_39a

        mock_service = AsyncMock()
        mock_service.generate.side_effect = Exception("LLM service unavailable")

        with (
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.multi_query_generator.MultiQueryGeneratorService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-004",
                "user_query": "Test query",
                "routing_decision": {
                    "route": "technical_research",
                    "needs_retrieval": True,
                    "entities": [],
                },
            }

            result = await node_step_39a(state)

            # Should fall back to original query for all variants
            assert result["query_variants"]["bm25_query"] == "Test query"
            assert result["query_variants"]["fallback"] is True

    @pytest.mark.asyncio
    async def test_state_preservation(self):
        """Test that existing state fields are preserved."""
        from app.core.langgraph.nodes.step_039a__multi_query import node_step_39a

        mock_service = AsyncMock()
        mock_service.generate.return_value = QueryVariants(
            bm25_query="test", vector_query="test", entity_query="test", original_query="test"
        )

        with (
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.multi_query_generator.MultiQueryGeneratorService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-005",
                "session_id": "session-abc",
                "user_query": "test",
                "routing_decision": {"route": "technical_research", "entities": []},
                "existing_field": "preserve_me",
            }

            result = await node_step_39a(state)

            assert result["request_id"] == "test-005"
            assert result["session_id"] == "session-abc"
            assert result["existing_field"] == "preserve_me"


# =============================================================================
# TestNodeStep39bHyDE - HyDE Generation Tests
# =============================================================================
class TestNodeStep39bHyDE:
    """Tests for Step 39b HyDE node wrapper."""

    @pytest.mark.asyncio
    async def test_successful_hyde_generation(self):
        """Test successful HyDE document generation."""
        from app.core.langgraph.nodes.step_039b__hyde import node_step_39b

        mock_service = AsyncMock()
        mock_service.generate.return_value = HyDEResult(
            hypothetical_document="Ai sensi dell'art. 1 del D.Lgs. 231/2001...",
            word_count=180,
            skipped=False,
            skip_reason=None,
        )

        with (
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.hyde_generator.HyDEGeneratorService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-006",
                "user_query": "Come funziona il ravvedimento?",
                "routing_decision": {
                    "route": "technical_research",
                    "needs_retrieval": True,
                },
            }

            result = await node_step_39b(state)

            assert "hyde_result" in result
            assert "Ai sensi" in result["hyde_result"]["hypothetical_document"]
            assert result["hyde_result"]["word_count"] == 180
            assert result["hyde_result"]["skipped"] is False

    @pytest.mark.asyncio
    async def test_skip_for_chitchat_route(self):
        """Test that HyDE is skipped for chitchat queries."""
        from app.core.langgraph.nodes.step_039b__hyde import node_step_39b

        mock_service = AsyncMock()
        mock_service.generate.return_value = HyDEResult(
            hypothetical_document="",
            word_count=0,
            skipped=True,
            skip_reason="chitchat",
        )

        with (
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.hyde_generator.HyDEGeneratorService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-007",
                "user_query": "Ciao!",
                "routing_decision": {
                    "route": "chitchat",
                    "needs_retrieval": False,
                },
            }

            result = await node_step_39b(state)

            assert result["hyde_result"]["skipped"] is True
            assert result["hyde_result"]["skip_reason"] == "chitchat"

    @pytest.mark.asyncio
    async def test_skip_for_calculator_route(self):
        """Test that HyDE is skipped for calculator queries."""
        from app.core.langgraph.nodes.step_039b__hyde import node_step_39b

        mock_service = AsyncMock()
        mock_service.generate.return_value = HyDEResult(
            hypothetical_document="",
            word_count=0,
            skipped=True,
            skip_reason="calculator",
        )

        with (
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.hyde_generator.HyDEGeneratorService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-008",
                "user_query": "Calcola IRPEF",
                "routing_decision": {
                    "route": "calculator",
                    "needs_retrieval": False,
                },
            }

            result = await node_step_39b(state)

            assert result["hyde_result"]["skipped"] is True

    @pytest.mark.asyncio
    async def test_fallback_on_service_error(self):
        """Test fallback on HyDE service error."""
        from app.core.langgraph.nodes.step_039b__hyde import node_step_39b

        mock_service = AsyncMock()
        mock_service.generate.side_effect = Exception("Timeout")

        with (
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.hyde_generator.HyDEGeneratorService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-009",
                "user_query": "Test query",
                "routing_decision": {
                    "route": "technical_research",
                    "needs_retrieval": True,
                },
            }

            result = await node_step_39b(state)

            assert result["hyde_result"]["skipped"] is True
            assert result["hyde_result"]["skip_reason"] == "error"


# =============================================================================
# TestNodeStep39cParallelRetrieval - Parallel Retrieval Tests
# =============================================================================
class TestNodeStep39cParallelRetrieval:
    """Tests for Step 39c Parallel Retrieval node wrapper."""

    @pytest.mark.asyncio
    async def test_successful_parallel_retrieval(self):
        """Test successful parallel retrieval with documents."""
        from app.core.langgraph.nodes.step_039c__parallel_retrieval import node_step_39c

        mock_service = AsyncMock()
        mock_service.retrieve.return_value = RetrievalResult(
            documents=[
                RankedDocument(
                    document_id="doc-001",
                    content="Contenuto documento legge...",
                    score=0.95,
                    rrf_score=0.85,
                    source_type="legge",
                    source_name="Legge 104/1992",
                    published_date=datetime(2024, 1, 1),
                    metadata={"articolo": "3"},
                ),
            ],
            total_found=15,
            search_time_ms=125.5,
        )

        with patch(
            "app.services.parallel_retrieval.ParallelRetrievalService",
            return_value=mock_service,
        ):
            state = {
                "request_id": "test-010",
                "user_query": "Permessi legge 104",
                "routing_decision": {"route": "technical_research", "needs_retrieval": True},
                "query_variants": {
                    "bm25_query": "permessi legge 104",
                    "vector_query": "permessi lavorativi legge 104",
                    "entity_query": "Legge 104/1992 Art. 3",
                    "original_query": "Permessi legge 104",
                },
                "hyde_result": {
                    "hypothetical_document": "La Legge 104...",
                    "skipped": False,
                },
            }

            result = await node_step_39c(state)

            assert "retrieval_result" in result
            assert result["retrieval_result"]["total_found"] == 15
            assert len(result["retrieval_result"]["documents"]) == 1
            assert result["retrieval_result"]["documents"][0]["source_name"] == "Legge 104/1992"

    @pytest.mark.asyncio
    async def test_skip_when_no_retrieval_needed(self):
        """Test that retrieval is skipped when not needed."""
        from app.core.langgraph.nodes.step_039c__parallel_retrieval import node_step_39c

        state = {
            "request_id": "test-011",
            "user_query": "Ciao!",
            "routing_decision": {"route": "chitchat", "needs_retrieval": False},
        }

        result = await node_step_39c(state)

        assert result["retrieval_result"]["skipped"] is True
        assert result["retrieval_result"]["skip_reason"] == "no_retrieval_needed"

    @pytest.mark.asyncio
    async def test_fallback_on_service_error(self):
        """Test fallback on retrieval service error."""
        from app.core.langgraph.nodes.step_039c__parallel_retrieval import node_step_39c

        mock_service = AsyncMock()
        mock_service.retrieve.side_effect = Exception("Search service unavailable")

        with patch(
            "app.services.parallel_retrieval.ParallelRetrievalService",
            return_value=mock_service,
        ):
            state = {
                "request_id": "test-012",
                "user_query": "Test query",
                "routing_decision": {"route": "technical_research", "needs_retrieval": True},
                "query_variants": {
                    "bm25_query": "test",
                    "vector_query": "test",
                    "entity_query": "test",
                    "original_query": "test",
                },
                "hyde_result": {"skipped": True},
            }

            result = await node_step_39c(state)

            assert result["retrieval_result"]["documents"] == []
            assert result["retrieval_result"]["error"] is True

    @pytest.mark.asyncio
    async def test_handles_missing_query_variants_gracefully(self):
        """Test handling when query_variants is missing."""
        from app.core.langgraph.nodes.step_039c__parallel_retrieval import node_step_39c

        mock_service = AsyncMock()
        mock_service.retrieve.return_value = RetrievalResult(
            documents=[],
            total_found=0,
            search_time_ms=50.0,
        )

        with patch(
            "app.services.parallel_retrieval.ParallelRetrievalService",
            return_value=mock_service,
        ):
            state = {
                "request_id": "test-013",
                "user_query": "Test query",
                "routing_decision": {"route": "technical_research", "needs_retrieval": True},
                # query_variants is missing
            }

            result = await node_step_39c(state)

            # Should still work, creating default query variants
            assert "retrieval_result" in result


# =============================================================================
# TestStep39Integration - Integration-style Tests
# =============================================================================
class TestStep39Integration:
    """Integration-style tests for Step 39 flow."""

    @pytest.mark.asyncio
    async def test_full_query_expansion_flow(self):
        """Test the complete query expansion flow (39a -> 39b -> 39c)."""
        from app.core.langgraph.nodes.step_039a__multi_query import node_step_39a
        from app.core.langgraph.nodes.step_039b__hyde import node_step_39b
        from app.core.langgraph.nodes.step_039c__parallel_retrieval import node_step_39c

        # Mock all services
        mock_mq = AsyncMock()
        mock_mq.generate.return_value = QueryVariants(
            bm25_query="test bm25",
            vector_query="test vector",
            entity_query="test entity",
            original_query="test query",
        )

        mock_hyde = AsyncMock()
        mock_hyde.generate.return_value = HyDEResult(
            hypothetical_document="Test document...",
            word_count=50,
            skipped=False,
            skip_reason=None,
        )

        mock_retrieval = AsyncMock()
        mock_retrieval.retrieve.return_value = RetrievalResult(
            documents=[],
            total_found=0,
            search_time_ms=100.0,
        )

        state = {
            "request_id": "test-integration",
            "user_query": "test query",
            "routing_decision": {
                "route": "technical_research",
                "needs_retrieval": True,
                "entities": [],
            },
        }

        with (
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.multi_query_generator.MultiQueryGeneratorService",
                return_value=mock_mq,
            ),
            patch(
                "app.services.hyde_generator.HyDEGeneratorService",
                return_value=mock_hyde,
            ),
            patch(
                "app.services.parallel_retrieval.ParallelRetrievalService",
                return_value=mock_retrieval,
            ),
        ):
            # Execute 39a
            state = await node_step_39a(state)
            assert "query_variants" in state

            # Execute 39b
            state = await node_step_39b(state)
            assert "hyde_result" in state

            # Execute 39c
            state = await node_step_39c(state)
            assert "retrieval_result" in state

    @pytest.mark.asyncio
    async def test_serializable_results_for_state(self):
        """Test that all results are serializable dicts for LangGraph state."""
        from app.core.langgraph.nodes.step_039a__multi_query import node_step_39a

        mock_service = AsyncMock()
        mock_service.generate.return_value = QueryVariants(
            bm25_query="test",
            vector_query="test",
            entity_query="test",
            original_query="test",
        )

        with (
            patch(
                "app.core.llm.model_config.get_model_config",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.multi_query_generator.MultiQueryGeneratorService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-serialize",
                "user_query": "test",
                "routing_decision": {"route": "technical_research", "entities": []},
            }

            result = await node_step_39a(state)

            # Must be dict, not dataclass (for state serialization)
            assert isinstance(result["query_variants"], dict)
            assert isinstance(result["query_variants"]["bm25_query"], str)
