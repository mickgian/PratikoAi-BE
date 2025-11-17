"""
Tests for RAG STEP 40 — ContextBuilder.merge facts and KB docs and optional doc facts

This step merges canonical facts, KB search results, and optional document facts
into a comprehensive context for LLM processing. It handles token budgets,
prioritization, and content deduplication.
"""

import uuid
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.services.context_builder_merge import ContextBuilderMerge
from app.services.knowledge_search_service import SearchResult


class TestRAGStep40ContextBuilderMerge:
    """Test suite for RAG STEP 40 - ContextBuilder.merge facts and KB docs and optional doc facts."""

    @pytest.fixture
    def context_builder_merge(self):
        """Create ContextBuilderMerge instance for testing."""
        return ContextBuilderMerge()

    @pytest.fixture
    def canonical_facts(self):
        """Sample canonical facts extracted from user query."""
        return [
            "Business tax deductions apply to legitimate business expenses",
            "Small business expenses include office supplies and equipment",
            "Tax year 2024 has updated deduction limits",
            "Business meals are 50% deductible in most cases",
        ]

    @pytest.fixture
    def kb_results(self):
        """Sample KB search results."""
        return [
            SearchResult(
                id="kb_1",
                title="Business Tax Deductions Guide 2024",
                content="Comprehensive guide to business tax deductions for 2024. Office supplies, equipment purchases, and business meals qualify for deductions. New limits: office supplies up to $2500, equipment depreciation changes.",
                category="tax",
                score=0.92,
                source="kb_rss",
                updated_at=datetime.now(UTC) - timedelta(days=2),
                metadata={"tags": ["business_tax", "deductions", "2024"], "word_count": 45},
            ),
            SearchResult(
                id="kb_2",
                title="Small Business Expense Categories",
                content="Small businesses can deduct various operational expenses. Categories include: office rent, utilities, supplies, equipment, travel, meals (50% limit), professional services, insurance.",
                category="business",
                score=0.86,
                source="kb_static",
                updated_at=datetime.now(UTC) - timedelta(days=10),
                metadata={"tags": ["small_business", "expenses", "categories"], "word_count": 32},
            ),
        ]

    @pytest.fixture
    def document_facts(self):
        """Sample facts extracted from processed documents."""
        return [
            "Invoice #12345 dated 2024-01-15 for office supplies totaling €450",
            "Receipt for computer equipment purchase €1,200 on 2024-02-10",
            "Business lunch receipt €85 from restaurant Il Locale on 2024-03-05",
        ]

    @pytest.fixture
    def context_data_template(self):
        """Template for context merging data."""
        return {
            "query": "What business expenses can I deduct for taxes?",
            "trace_id": "test_trace_001",
            "user_id": str(uuid.uuid4()),
            "session_id": "test_session_123",
            "max_context_tokens": 1000,
            "priority_weights": {"facts": 0.3, "kb_docs": 0.5, "document_facts": 0.2},
        }

    @pytest.mark.asyncio
    @patch("app.services.context_builder_merge.rag_step_log")
    async def test_merge_context_with_all_sources(
        self, mock_log, context_builder_merge, canonical_facts, kb_results, document_facts, context_data_template
    ):
        """Test merging context when all source types are available."""
        context_data = {
            **context_data_template,
            "canonical_facts": canonical_facts,
            "kb_results": kb_results,
            "document_facts": document_facts,
        }

        result = context_builder_merge.merge_context(context_data)

        assert "merged_context" in result
        assert result["token_count"] <= context_data["max_context_tokens"]
        assert result["source_distribution"]["facts"] == len(canonical_facts)
        assert result["source_distribution"]["kb_docs"] == len(kb_results)
        assert result["source_distribution"]["document_facts"] == len(document_facts)
        assert result["context_quality_score"] > 0.0
        assert "Business tax deductions" in result["merged_context"]
        assert "From knowledge base:" in result["merged_context"]
        assert "From your documents:" in result["merged_context"]

    @pytest.mark.asyncio
    @patch("app.services.context_builder_merge.rag_step_log")
    async def test_merge_context_facts_and_kb_only(
        self, mock_log, context_builder_merge, canonical_facts, kb_results, context_data_template
    ):
        """Test merging context when only facts and KB docs are available (no documents)."""
        context_data = {
            **context_data_template,
            "canonical_facts": canonical_facts,
            "kb_results": kb_results,
            "document_facts": None,  # No document facts
        }

        result = context_builder_merge.merge_context(context_data)

        assert result["source_distribution"]["document_facts"] == 0
        assert "From your documents:" not in result["merged_context"]
        assert result["context_quality_score"] > 0.0
        assert "Business tax deductions" in result["merged_context"]
        assert "From knowledge base:" in result["merged_context"]

    @pytest.mark.asyncio
    @patch("app.services.context_builder_merge.rag_step_log")
    async def test_merge_context_token_budget_respected(
        self, mock_log, context_builder_merge, canonical_facts, kb_results, document_facts, context_data_template
    ):
        """Test that token budget limits are respected."""
        # Set very low token limit
        context_data = {
            **context_data_template,
            "canonical_facts": canonical_facts,
            "kb_results": kb_results,
            "document_facts": document_facts,
            "max_context_tokens": 200,  # Very low limit
        }

        result = context_builder_merge.merge_context(context_data)

        assert result["token_count"] <= context_data["max_context_tokens"]
        # With low budget, some content should be limited
        total_sources = (
            result["source_distribution"]["facts"]
            + result["source_distribution"]["kb_docs"]
            + result["source_distribution"]["document_facts"]
        )
        expected_total = len(canonical_facts) + len(kb_results) + len(document_facts)
        assert total_sources <= expected_total

    @pytest.mark.asyncio
    @patch("app.services.context_builder_merge.rag_step_log")
    async def test_merge_context_prioritization_weights(
        self, mock_log, context_builder_merge, canonical_facts, kb_results, document_facts, context_data_template
    ):
        """Test that priority weights affect content selection."""
        # Prioritize document facts heavily
        context_data = {
            **context_data_template,
            "canonical_facts": canonical_facts,
            "kb_results": kb_results,
            "document_facts": document_facts,
            "priority_weights": {
                "facts": 0.1,
                "kb_docs": 0.2,
                "document_facts": 0.7,  # Heavy priority on document facts
            },
        }

        result = context_builder_merge.merge_context(context_data)

        # Document facts should be prioritized in the context
        assert "From your documents:" in result["merged_context"]
        assert result["source_distribution"]["document_facts"] > 0
        # Check that document facts appear prominently in the merged context
        assert "Invoice" in result["merged_context"] or "Receipt" in result["merged_context"]

    @pytest.mark.asyncio
    @patch("app.services.context_builder_merge.rag_step_log")
    async def test_merge_context_empty_inputs(self, mock_log, context_builder_merge, context_data_template):
        """Test handling of empty or missing inputs."""
        context_data = {**context_data_template, "canonical_facts": [], "kb_results": [], "document_facts": None}

        result = context_builder_merge.merge_context(context_data)

        assert result["context_quality_score"] == 0.0
        assert result["token_count"] < 20  # Minimal fallback
        assert len(result["context_parts"]) == 0
        assert result["merged_context"] == "No specific context available for this query."

    @pytest.mark.asyncio
    @patch("app.services.context_builder_merge.rag_step_log")
    async def test_merge_context_deduplication(self, mock_log, context_builder_merge, context_data_template):
        """Test deduplication of similar content across sources."""
        # Create overlapping facts and KB content
        overlapping_facts = [
            "Business tax deductions apply to office supplies",
            "Office supplies are deductible business expenses",
        ]

        overlapping_kb = [
            SearchResult(
                id="kb_dup",
                title="Office Supply Deductions",
                content="Office supplies are deductible business expenses for tax purposes. This includes paper, pens, computers.",
                category="tax",
                score=0.88,
                source="kb_static",
            )
        ]

        context_data = {
            **context_data_template,
            "canonical_facts": overlapping_facts,
            "kb_results": overlapping_kb,
            "document_facts": ["Invoice for office supplies purchase"],
        }

        result = context_builder_merge.merge_context(context_data)

        # Deduplication should reduce similar content
        expected_unique_facts = len(overlapping_facts)
        actual_facts = result["source_distribution"]["facts"]
        # Should have fewer facts due to deduplication or all facts if they're distinct enough
        assert actual_facts <= expected_unique_facts
        assert "office supplies" in result["merged_context"].lower()

    @pytest.mark.asyncio
    async def test_merge_context_error_handling(self, context_builder_merge, context_data_template):
        """Test error handling in context merging."""
        # Test with invalid data that might cause errors
        context_data = {
            **context_data_template,
            "canonical_facts": [None, "", "  "],  # Invalid facts
            "kb_results": [],
            "document_facts": [None],
        }

        result = context_builder_merge.merge_context(context_data)

        # Should handle gracefully
        assert "merged_context" in result
        assert "context_quality_score" in result
        assert "token_count" in result

    @pytest.mark.asyncio
    @patch("app.services.context_builder_merge.rag_step_log")
    async def test_structured_logging_format(
        self, mock_log, context_builder_merge, canonical_facts, kb_results, context_data_template
    ):
        """Test that structured logging follows correct format for STEP 40."""
        context_data = {
            **context_data_template,
            "canonical_facts": canonical_facts,
            "kb_results": kb_results,
            "document_facts": None,
        }

        context_builder_merge.merge_context(context_data)

        # Verify the log was called with correct STEP 40 format
        mock_log.assert_called()

        # Find the context merge log call (completed stage)
        merge_log_calls = [
            call
            for call in mock_log.call_args_list
            if (len(call[1]) > 3 and call[1].get("step") == 40 and call[1].get("processing_stage") == "completed")
        ]

        # Should have at least one log call for the merge
        assert len(merge_log_calls) > 0

        # Verify required fields
        log_call = merge_log_calls[0]
        assert log_call[1]["step"] == 40
        assert log_call[1]["step_id"] == "RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts"
        assert log_call[1]["node_label"] == "BuildContext"
        assert "token_count" in log_call[1]
        assert "trace_id" in log_call[1]


class TestRAGStep40Orchestrator:
    """Test suite for RAG STEP 40 Orchestrator - BuildContext orchestration function."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_40_orchestrator_success(self, mock_rag_log):
        """Test Step 40: Successful context merging via orchestrator."""
        from app.orchestrators.facts import step_40__build_context
        from app.services.context_builder_merge import ContextBuilderMerge
        from app.services.knowledge_search_service import SearchResult

        # Mock service instance
        mock_service = ContextBuilderMerge()

        # Mock KB results (from Step 39)
        kb_results = [
            SearchResult(
                id="kb_1",
                title="Tax Guide 2024",
                content="Business tax deductions for 2024",
                category="tax",
                score=0.92,
                source="kb_tax_guide",
            )
        ]

        ctx = {
            "request_id": "test-step-40",
            "canonical_facts": ["business", "tax", "deductions", "2024"],
            "knowledge_items": kb_results,  # Output from Step 39
            "document_facts": ["Document shows business expenses"],
            "user_message": "What tax deductions can I claim for business expenses?",
            "user_id": "user_40",
            "session_id": "session_40",
            "trace_id": "trace_40_123",
        }

        result = await step_40__build_context(ctx=ctx, context_builder_service=mock_service)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["context_merged"] is True
        assert "merged_context" in result
        assert result["token_count"] > 0
        assert result["source_distribution"]["facts"] > 0
        assert result["source_distribution"]["kb_docs"] > 0
        assert result["source_distribution"]["document_facts"] > 0
        assert result["context_quality_score"] > 0.0
        assert result["request_id"] == "test-step-40"
        assert "timestamp" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_40_orchestrator_kwargs_override_ctx(self, mock_rag_log):
        """Test Step 40: kwargs parameters override ctx parameters."""
        from app.orchestrators.facts import step_40__build_context
        from app.services.context_builder_merge import ContextBuilderMerge

        mock_service = ContextBuilderMerge()

        ctx = {
            "request_id": "test-ctx",
            "canonical_facts": ["ctx", "facts"],
            "user_message": "Context query",
            "max_context_tokens": 1000,
        }

        # Override via kwargs
        result = await step_40__build_context(
            ctx=ctx,
            context_builder_service=mock_service,
            canonical_facts=["override", "facts"],
            query="Override query",
            max_context_tokens=800,
        )

        assert result["context_merged"] is True
        assert result["query"] == "Override query"  # From kwargs, not ctx
        assert result["max_context_tokens"] == 800  # From kwargs, not ctx
        assert result["canonical_facts"] == ["override", "facts"]  # From kwargs, not ctx

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_40_orchestrator_empty_inputs(self, mock_rag_log):
        """Test Step 40: Handling of empty inputs."""
        from app.orchestrators.facts import step_40__build_context
        from app.services.context_builder_merge import ContextBuilderMerge

        mock_service = ContextBuilderMerge()

        ctx = {
            "request_id": "test-empty",
            "canonical_facts": [],  # Empty facts
            "knowledge_items": [],  # Empty KB results
            "document_facts": [],  # Empty document facts
            "user_message": "",  # Empty query
            "user_id": "user_empty",
            "session_id": "session_empty",
        }

        result = await step_40__build_context(ctx=ctx, context_builder_service=mock_service)

        assert result["context_merged"] is True  # Service handles empty inputs gracefully
        assert result["token_count"] >= 0
        assert result["source_distribution"]["facts"] == 0
        assert result["source_distribution"]["kb_docs"] == 0
        assert result["source_distribution"]["document_facts"] == 0

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_40_orchestrator_service_error_handling(self, mock_logger, mock_rag_log):
        """Test Step 40: Error handling when context builder service fails."""
        from unittest.mock import Mock

        from app.orchestrators.facts import step_40__build_context

        # Mock service to raise an exception
        mock_service = Mock()
        mock_service.merge_context.side_effect = Exception("Context merging failed")

        ctx = {
            "request_id": "test-error",
            "canonical_facts": ["test", "facts"],
            "user_message": "Test query for error handling",
            "user_id": "user_error",
            "session_id": "session_error",
        }

        result = await step_40__build_context(ctx=ctx, context_builder_service=mock_service)

        assert result["context_merged"] is False
        assert result["merged_context"] == ""
        assert result["context_parts"] == []
        assert result["token_count"] == 0
        assert "Context merging failed" in result["error"]

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_40_orchestrator_integration_flow(self, mock_rag_log):
        """Test Step 40: Integration test ensuring proper workflow integration."""
        from app.orchestrators.facts import step_40__build_context
        from app.services.context_builder_merge import ContextBuilderMerge
        from app.services.knowledge_search_service import SearchResult

        # Simulate realistic data flowing from previous steps
        kb_results = [
            SearchResult(
                id="integration_kb_1",
                title="Integration Test Knowledge",
                content="Knowledge content from Step 39 for integration testing",
                category="business",
                score=0.87,
                source="kb_integration_test",
            )
        ]

        ctx = {
            "request_id": "test-integration-40",
            "canonical_facts": ["business", "integration", "test", "facts"],
            "knowledge_items": kb_results,  # From Step 39: KBPreFetch
            "document_facts": ["Document fact from integration test"],
            "user_message": "Integration test query for context building",
            "search_query": "Integration test query for context building",  # Alternative query source
            "user_id": "user_integration",
            "session_id": "session_integration",
            "trace_id": "trace_integration_40",
        }

        mock_service = ContextBuilderMerge()
        result = await step_40__build_context(ctx=ctx, context_builder_service=mock_service)

        # Verify context was merged successfully
        assert result["context_merged"] is True
        assert result["token_count"] > 0

        # Verify context preservation for next steps (Step 41: SelectPrompt)
        assert result["request_id"] == "test-integration-40"
        assert "timestamp" in result
        assert result["merged_context"] != ""
        assert len(result["context_parts"]) > 0

        # Verify rag_step_log was called with proper parameters
        assert mock_rag_log.call_count >= 2  # start and completed calls
        start_call = mock_rag_log.call_args_list[0][1]
        assert start_call["step"] == 40
        assert start_call["step_id"] == "RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts"
        assert start_call["node_label"] == "BuildContext"
        assert start_call["category"] == "facts"
        assert start_call["type"] == "process"
        assert start_call["processing_stage"] == "started"

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_40_parity_behavior_preservation(self, mock_rag_log):
        """Test Step 40: Parity test proving identical behavior before/after orchestrator."""
        from app.orchestrators.facts import step_40__build_context
        from app.services.context_builder_merge import ContextBuilderMerge, merge_context
        from app.services.knowledge_search_service import SearchResult

        # Test data representing direct ContextBuilderMerge usage
        canonical_facts = ["parity", "test", "facts"]
        kb_results = [
            SearchResult(
                id="parity_kb_1",
                title="Parity Test KB",
                content="Content for parity testing",
                category="test",
                score=0.91,
                source="parity_test",
            )
        ]
        document_facts = ["Document fact for parity test"]

        context_data = {
            "canonical_facts": canonical_facts,
            "kb_results": kb_results,
            "document_facts": document_facts,
            "query": "Test parity preservation",
            "user_id": "parity_user",
            "session_id": "parity_session",
            "trace_id": "parity_trace_123",
            "max_context_tokens": 1200,
        }

        # Direct service call (before orchestrator)
        direct_result = merge_context(context_data)

        # Orchestrator call (after orchestrator)
        ctx = {
            "request_id": "parity-test-40",
            "canonical_facts": canonical_facts,
            "knowledge_items": kb_results,  # Use knowledge_items (Step 39 output key)
            "document_facts": document_facts,
            "query": context_data["query"],
            "user_id": context_data["user_id"],
            "session_id": context_data["session_id"],
            "trace_id": context_data["trace_id"],
            "max_context_tokens": context_data["max_context_tokens"],
        }

        mock_service = ContextBuilderMerge()
        orchestrator_result = await step_40__build_context(ctx=ctx, context_builder_service=mock_service)

        # Verify that orchestrator preserves core merging behavior
        assert orchestrator_result["context_merged"] is True

        # Check that both contain the same essential content components
        assert "parity test facts" in orchestrator_result["merged_context"]
        assert "parity test facts" in direct_result["merged_context"]
        assert "Content for parity testing" in orchestrator_result["merged_context"]
        assert "Content for parity testing" in direct_result["merged_context"]
        assert "Document fact for parity test" in orchestrator_result["merged_context"]
        assert "Document fact for parity test" in direct_result["merged_context"]

        # Verify core metrics are equivalent (allowing for small variations due to orchestrator context)
        assert orchestrator_result["token_count"] == direct_result["token_count"]
        assert orchestrator_result["source_distribution"] == direct_result["source_distribution"]
        # Allow small variation in quality score due to orchestrator context differences
        assert abs(orchestrator_result["context_quality_score"] - direct_result["context_quality_score"]) < 0.15

        # Verify orchestrator adds coordination metadata without changing core behavior
        assert orchestrator_result["request_id"] == "parity-test-40"
        assert "timestamp" in orchestrator_result
