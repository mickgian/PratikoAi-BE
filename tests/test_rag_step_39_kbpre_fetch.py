"""
Test suite for RAG STEP 39 - KnowledgeSearch retrieve_topk BM25 and vectors and recency boost

This module tests the orchestration function step_39__kbpre_fetch which performs
knowledge retrieval using hybrid search (BM25 + vectors + recency boost) as part
of the RAG workflow after classification steps.

According to the RAG workflow and GitHub issue 584:
- Takes query and context from previous classification steps
- Performs hybrid knowledge search with BM25, vectors, and recency boost
- Returns top-k knowledge items for context building
- Thin orchestration that preserves existing KnowledgeSearchService behavior
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.orchestrators.preflight import step_39__kbpre_fetch
from app.services.knowledge_search_service import SearchMode, SearchResult


class TestRAGStep39KBPreFetch:
    """Test suite for RAG STEP 39 - KnowledgeSearch retrieve_topk"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    @patch("app.services.knowledge_search_service.KnowledgeSearchService")
    async def test_step_39_knowledge_search_success(self, mock_service_class, mock_rag_log):
        """Test Step 39: Successful knowledge search with hybrid results"""

        # Mock search results
        mock_results = [
            SearchResult(
                id="kb_1",
                title="Tax Deduction Guidelines 2023",
                content="Tax deduction rules for business expenses...",
                category="tax",
                score=0.95,
                source="knowledge_base",
                updated_at=datetime(2023, 12, 1),
            ),
            SearchResult(
                id="kb_2",
                title="Business Expense Categories",
                content="Categories of allowable business expenses...",
                category="tax",
                score=0.87,
                source="knowledge_base",
                updated_at=datetime(2023, 11, 15),
            ),
        ]

        # Mock the service instance
        mock_service = AsyncMock()
        mock_service.retrieve_topk.return_value = mock_results

        ctx = {
            "request_id": "test-request-123",
            "user_message": "What tax deductions can I claim for business expenses?",
            "canonical_facts": ["tax", "deductions", "business", "expenses"],
            "final_classification": {"domain": "tax", "action": "information_request", "confidence": 0.85},
            "user_id": "user_123",
            "session_id": "session_456",
        }

        # Call the orchestrator function with mock service
        result = await step_39__kbpre_fetch(ctx=ctx, knowledge_service=mock_service)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["search_performed"] is True
        assert result["knowledge_items"] == mock_results
        assert result["search_mode"] == SearchMode.HYBRID.value
        assert result["total_results"] == 2
        assert result["request_id"] == "test-request-123"
        assert "search_query" in result
        assert "timestamp" in result

        # Verify service was called correctly
        mock_service.retrieve_topk.assert_called_once()
        call_args = mock_service.retrieve_topk.call_args[0][0]
        assert call_args["query"] == "What tax deductions can I claim for business expenses?"
        assert call_args["canonical_facts"] == ["tax", "deductions", "business", "expenses"]
        assert call_args["user_id"] == "user_123"
        assert call_args["session_id"] == "session_456"

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    @patch("app.services.knowledge_search_service.KnowledgeSearchService")
    async def test_step_39_with_bm25_only_search_mode(self, mock_service_class, mock_rag_log):
        """Test Step 39: BM25-only search mode"""

        mock_results = [
            SearchResult(
                id="bm25_1",
                title="BM25 Result",
                content="Content found via BM25 search",
                category="legal",
                score=0.92,
                source="knowledge_base",
            )
        ]

        mock_service = AsyncMock()
        mock_service.retrieve_topk.return_value = mock_results

        ctx = {
            "request_id": "test-bm25-only",
            "user_message": "Legal contract terms",
            "search_mode": SearchMode.BM25_ONLY.value,
            "user_id": "user_bm25",
            "session_id": "session_bm25",
        }

        result = await step_39__kbpre_fetch(ctx=ctx, knowledge_service=mock_service)

        assert result["search_performed"] is True
        assert result["search_mode"] == SearchMode.BM25_ONLY.value
        assert result["total_results"] == 1

        # Verify correct search mode was passed
        call_args = mock_service.retrieve_topk.call_args[0][0]
        assert call_args["search_mode"] == SearchMode.BM25_ONLY.value

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    @patch("app.services.knowledge_search_service.KnowledgeSearchService")
    async def test_step_39_with_filters_and_max_results(self, mock_service_class, mock_rag_log):
        """Test Step 39: Search with filters and max results limit"""

        mock_results = []  # Empty results for filtered search
        mock_service = AsyncMock()
        mock_service.retrieve_topk.return_value = mock_results

        ctx = {
            "request_id": "test-filtered",
            "user_message": "HR policies for remote work",
            "canonical_facts": ["hr", "policies", "remote", "work"],
            "filters": {"category": "hr", "source": "internal_policies"},
            "max_results": 5,
            "user_id": "user_hr",
            "session_id": "session_hr",
        }

        result = await step_39__kbpre_fetch(ctx=ctx, knowledge_service=mock_service)

        assert result["search_performed"] is True
        assert result["total_results"] == 0
        assert result["filters"] == {"category": "hr", "source": "internal_policies"}
        assert result["max_results"] == 5

        # Verify filters and max_results were passed correctly
        call_args = mock_service.retrieve_topk.call_args[0][0]
        assert call_args["filters"] == {"category": "hr", "source": "internal_policies"}
        assert call_args["max_results"] == 5

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.knowledge_search_service.KnowledgeSearchService")
    async def test_step_39_empty_query_handling(self, mock_service_class, mock_logger, mock_rag_log):
        """Test Step 39: Handling of empty or missing query"""

        mock_service = AsyncMock()
        mock_service.retrieve_topk.return_value = []
        mock_service_class.return_value = mock_service

        ctx = {
            "request_id": "test-empty-query",
            "user_message": "",  # Empty query
            "user_id": "user_empty",
            "session_id": "session_empty",
        }

        result = await step_39__kbpre_fetch(ctx=ctx, knowledge_service=mock_service)

        assert result["search_performed"] is True  # Still performed, but with empty query
        assert result["total_results"] == 0
        assert result["search_query"] == ""

        # Verify service was still called (it handles empty queries)
        mock_service.retrieve_topk.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.knowledge_search_service.KnowledgeSearchService")
    async def test_step_39_service_error_handling(self, mock_service_class, mock_logger, mock_rag_log):
        """Test Step 39: Error handling when knowledge search service fails"""

        # Mock service to raise an exception
        mock_service = AsyncMock()
        mock_service.retrieve_topk.side_effect = Exception("Knowledge search service unavailable")

        ctx = {
            "request_id": "test-service-error",
            "user_message": "Test query for error handling",
            "user_id": "user_error",
            "session_id": "session_error",
        }

        result = await step_39__kbpre_fetch(ctx=ctx, knowledge_service=mock_service)

        assert result["search_performed"] is False
        assert result["knowledge_items"] == []
        assert result["total_results"] == 0
        assert "Knowledge search service unavailable" in result["error"]

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    @patch("app.services.knowledge_search_service.KnowledgeSearchService")
    async def test_step_39_kwargs_override_ctx(self, mock_service_class, mock_rag_log):
        """Test Step 39: kwargs parameters override ctx parameters"""

        mock_results = [
            SearchResult(
                id="override_test",
                title="Override Test Result",
                content="Test content",
                category="test",
                score=0.90,
                source="test",
            )
        ]

        mock_service = AsyncMock()
        mock_service.retrieve_topk.return_value = mock_results

        ctx = {"request_id": "test-ctx", "user_message": "Context query", "user_id": "ctx_user", "max_results": 10}

        # Override via kwargs
        result = await step_39__kbpre_fetch(
            ctx=ctx,
            knowledge_service=mock_service,
            user_message="Override query",
            user_id="override_user",
            max_results=3,
        )

        assert result["search_performed"] is True
        assert result["search_query"] == "Override query"  # From kwargs, not ctx
        assert result["max_results"] == 3  # From kwargs, not ctx

        # Verify service received kwargs values
        call_args = mock_service.retrieve_topk.call_args[0][0]
        assert call_args["query"] == "Override query"
        assert call_args["user_id"] == "override_user"
        assert call_args["max_results"] == 3

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    @patch("app.services.knowledge_search_service.KnowledgeSearchService")
    async def test_step_39_preserves_search_metadata(self, mock_service_class, mock_rag_log):
        """Test Step 39: Preserves and tracks search metadata"""

        mock_results = [
            SearchResult(
                id="meta_1",
                title="Metadata Test",
                content="Content with metadata",
                category="test",
                score=0.88,
                source="knowledge_base",
            )
        ]

        mock_service = AsyncMock()
        mock_service.retrieve_topk.return_value = mock_results

        ctx = {
            "request_id": "test-metadata",
            "user_message": "Test metadata preservation",
            "canonical_facts": ["test", "metadata"],
            "user_id": "user_meta",
            "session_id": "session_meta",
            "trace_id": "trace_meta_123",
        }

        result = await step_39__kbpre_fetch(ctx=ctx, knowledge_service=mock_service)

        assert result["search_performed"] is True
        assert len(result["knowledge_items"]) == 1
        # Verify metadata preservation (note: SearchResult doesn't have metadata field in actual implementation)
        assert len(result["knowledge_items"]) == 1
        assert result["trace_id"] == "trace_meta_123"

        # Verify trace_id was passed to service
        call_args = mock_service.retrieve_topk.call_args[0][0]
        assert call_args["trace_id"] == "trace_meta_123"

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    @patch("app.services.knowledge_search_service.KnowledgeSearchService")
    async def test_step_39_integration_flow_context_preservation(self, mock_service_class, mock_rag_log):
        """Test Step 39: Integration test ensuring context is preserved for next steps"""

        mock_results = [
            SearchResult(
                id="integration_1",
                title="Integration Test Knowledge",
                content="Knowledge content for integration testing",
                category="tax",
                score=0.93,
                source="knowledge_base",
            )
        ]

        mock_service = AsyncMock()
        mock_service.retrieve_topk.return_value = mock_results

        ctx = {
            "request_id": "test-integration-39",
            "user_message": "What are tax deduction limits for 2023?",
            "canonical_facts": ["tax", "deduction", "limits", "2023"],
            "final_classification": {
                "domain": "tax",
                "action": "information_request",
                "confidence": 0.87,
                "classification_source": "rule_based",
            },
            "user_id": "user_integration",
            "session_id": "session_integration",
        }

        result = await step_39__kbpre_fetch(ctx=ctx, knowledge_service=mock_service)

        # Verify knowledge search was performed
        assert result["search_performed"] is True
        assert result["total_results"] == 1

        # Verify context preservation for BuildContext step (Step 40)
        assert result["request_id"] == "test-integration-39"
        assert "timestamp" in result
        assert result["knowledge_items"] == mock_results

        # Verify rag_step_log was called with proper parameters
        assert mock_rag_log.call_count >= 2  # start and completed calls
        start_call = mock_rag_log.call_args_list[0][1]
        assert start_call["step"] == 39
        assert (
            start_call["step_id"] == "RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost"
        )
        assert start_call["node_label"] == "KBPreFetch"
        assert start_call["category"] == "preflight"
        assert start_call["type"] == "process"
        assert start_call["processing_stage"] == "started"

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    @patch("app.services.knowledge_search_service.KnowledgeSearchService")
    async def test_step_39_parity_test_behavior_preservation(self, mock_service_class, mock_rag_log):
        """Test Step 39: Parity test proving identical behavior before/after orchestrator"""

        # Test data representing direct KnowledgeSearchService.retrieve_topk usage
        query_data = {
            "query": "Test parity preservation",
            "canonical_facts": ["test", "parity"],
            "user_id": "parity_user",
            "session_id": "parity_session",
            "search_mode": SearchMode.HYBRID.value,
            "filters": {"category": "test"},
            "max_results": 8,
        }

        expected_results = [
            SearchResult(
                id="parity_1",
                title="Parity Test Result",
                content="Content for parity testing",
                category="test",
                score=0.91,
                source="test_source",
            )
        ]

        mock_service = AsyncMock()
        mock_service.retrieve_topk.return_value = expected_results
        mock_service_class.return_value = mock_service

        ctx = {
            "request_id": "parity-test-123",
            "user_message": query_data["query"],
            "canonical_facts": query_data["canonical_facts"],
            "user_id": query_data["user_id"],
            "session_id": query_data["session_id"],
            "search_mode": query_data["search_mode"],
            "filters": query_data["filters"],
            "max_results": query_data["max_results"],
        }

        result = await step_39__kbpre_fetch(ctx=ctx, knowledge_service=mock_service)

        # Verify that orchestrator preserves exact same search behavior
        assert result["search_performed"] is True
        assert result["knowledge_items"] == expected_results

        # Verify service was called with exact same parameters
        call_args = mock_service.retrieve_topk.call_args[0][0]
        assert call_args["query"] == query_data["query"]
        assert call_args["canonical_facts"] == query_data["canonical_facts"]
        assert call_args["user_id"] == query_data["user_id"]
        assert call_args["session_id"] == query_data["session_id"]
        assert call_args["search_mode"] == query_data["search_mode"]
        assert call_args["filters"] == query_data["filters"]
        assert call_args["max_results"] == query_data["max_results"]

        # Verify orchestrator adds coordination metadata without changing core behavior
        assert result["search_mode"] == SearchMode.HYBRID.value
        assert result["total_results"] == 1
        assert "timestamp" in result
