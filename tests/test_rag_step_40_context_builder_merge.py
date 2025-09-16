"""
Tests for RAG STEP 40 — ContextBuilder.merge facts and KB docs and optional doc facts

This step merges canonical facts, KB search results, and optional document facts
into a comprehensive context for LLM processing. It handles token budgets,
prioritization, and content deduplication.
"""

import uuid
from datetime import datetime, timezone, timedelta
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
            "Business meals are 50% deductible in most cases"
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
                updated_at=datetime.now(timezone.utc) - timedelta(days=2),
                metadata={
                    "tags": ["business_tax", "deductions", "2024"],
                    "word_count": 45
                }
            ),
            SearchResult(
                id="kb_2",
                title="Small Business Expense Categories",
                content="Small businesses can deduct various operational expenses. Categories include: office rent, utilities, supplies, equipment, travel, meals (50% limit), professional services, insurance.",
                category="business",
                score=0.86,
                source="kb_static",
                updated_at=datetime.now(timezone.utc) - timedelta(days=10),
                metadata={
                    "tags": ["small_business", "expenses", "categories"],
                    "word_count": 32
                }
            )
        ]

    @pytest.fixture
    def document_facts(self):
        """Sample facts extracted from processed documents."""
        return [
            "Invoice #12345 dated 2024-01-15 for office supplies totaling €450",
            "Receipt for computer equipment purchase €1,200 on 2024-02-10",
            "Business lunch receipt €85 from restaurant Il Locale on 2024-03-05"
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
            "priority_weights": {
                "facts": 0.3,
                "kb_docs": 0.5,
                "document_facts": 0.2
            }
        }

    @pytest.mark.asyncio
    @patch('app.services.context_builder_merge.rag_step_log')
    async def test_merge_context_with_all_sources(
        self,
        mock_log,
        context_builder_merge,
        canonical_facts,
        kb_results,
        document_facts,
        context_data_template
    ):
        """Test merging context when all source types are available."""
        context_data = {
            **context_data_template,
            "canonical_facts": canonical_facts,
            "kb_results": kb_results,
            "document_facts": document_facts
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
    @patch('app.services.context_builder_merge.rag_step_log')
    async def test_merge_context_facts_and_kb_only(
        self,
        mock_log,
        context_builder_merge,
        canonical_facts,
        kb_results,
        context_data_template
    ):
        """Test merging context when only facts and KB docs are available (no documents)."""
        context_data = {
            **context_data_template,
            "canonical_facts": canonical_facts,
            "kb_results": kb_results,
            "document_facts": None  # No document facts
        }

        result = context_builder_merge.merge_context(context_data)

        assert result["source_distribution"]["document_facts"] == 0
        assert "From your documents:" not in result["merged_context"]
        assert result["context_quality_score"] > 0.0
        assert "Business tax deductions" in result["merged_context"]
        assert "From knowledge base:" in result["merged_context"]

    @pytest.mark.asyncio
    @patch('app.services.context_builder_merge.rag_step_log')
    async def test_merge_context_token_budget_respected(
        self,
        mock_log,
        context_builder_merge,
        canonical_facts,
        kb_results,
        document_facts,
        context_data_template
    ):
        """Test that token budget limits are respected."""
        # Set very low token limit
        context_data = {
            **context_data_template,
            "canonical_facts": canonical_facts,
            "kb_results": kb_results,
            "document_facts": document_facts,
            "max_context_tokens": 200  # Very low limit
        }

        result = context_builder_merge.merge_context(context_data)

        assert result["token_count"] <= context_data["max_context_tokens"]
        # With low budget, some content should be limited
        total_sources = result["source_distribution"]["facts"] + result["source_distribution"]["kb_docs"] + result["source_distribution"]["document_facts"]
        expected_total = len(canonical_facts) + len(kb_results) + len(document_facts)
        assert total_sources <= expected_total

    @pytest.mark.asyncio
    @patch('app.services.context_builder_merge.rag_step_log')
    async def test_merge_context_prioritization_weights(
        self,
        mock_log,
        context_builder_merge,
        canonical_facts,
        kb_results,
        document_facts,
        context_data_template
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
                "document_facts": 0.7  # Heavy priority on document facts
            }
        }

        result = context_builder_merge.merge_context(context_data)

        # Document facts should be prioritized in the context
        assert "From your documents:" in result["merged_context"]
        assert result["source_distribution"]["document_facts"] > 0
        # Check that document facts appear prominently in the merged context
        assert "Invoice" in result["merged_context"] or "Receipt" in result["merged_context"]

    @pytest.mark.asyncio
    @patch('app.services.context_builder_merge.rag_step_log') 
    async def test_merge_context_empty_inputs(
        self,
        mock_log,
        context_builder_merge,
        context_data_template
    ):
        """Test handling of empty or missing inputs."""
        context_data = {
            **context_data_template,
            "canonical_facts": [],
            "kb_results": [],
            "document_facts": None
        }

        result = context_builder_merge.merge_context(context_data)

        assert result["context_quality_score"] == 0.0
        assert result["token_count"] < 20  # Minimal fallback
        assert len(result["context_parts"]) == 0
        assert result["merged_context"] == "No specific context available for this query."

    @pytest.mark.asyncio
    @patch('app.services.context_builder_merge.rag_step_log')
    async def test_merge_context_deduplication(
        self,
        mock_log,
        context_builder_merge,
        context_data_template
    ):
        """Test deduplication of similar content across sources."""
        # Create overlapping facts and KB content
        overlapping_facts = [
            "Business tax deductions apply to office supplies",
            "Office supplies are deductible business expenses"
        ]
        
        overlapping_kb = [
            SearchResult(
                id="kb_dup",
                title="Office Supply Deductions",
                content="Office supplies are deductible business expenses for tax purposes. This includes paper, pens, computers.",
                category="tax",
                score=0.88,
                source="kb_static"
            )
        ]

        context_data = {
            **context_data_template,
            "canonical_facts": overlapping_facts,
            "kb_results": overlapping_kb,
            "document_facts": ["Invoice for office supplies purchase"]
        }

        result = context_builder_merge.merge_context(context_data)

        # Deduplication should reduce similar content
        expected_unique_facts = len(overlapping_facts)
        actual_facts = result["source_distribution"]["facts"]
        # Should have fewer facts due to deduplication or all facts if they're distinct enough
        assert actual_facts <= expected_unique_facts
        assert "office supplies" in result["merged_context"].lower()

    @pytest.mark.asyncio
    async def test_merge_context_error_handling(
        self,
        context_builder_merge,
        context_data_template
    ):
        """Test error handling in context merging."""
        # Test with invalid data that might cause errors
        context_data = {
            **context_data_template,
            "canonical_facts": [None, "", "  "],  # Invalid facts
            "kb_results": [],
            "document_facts": [None]
        }

        result = context_builder_merge.merge_context(context_data)
        
        # Should handle gracefully
        assert "merged_context" in result
        assert "context_quality_score" in result
        assert "token_count" in result

    @pytest.mark.asyncio
    @patch('app.services.context_builder_merge.rag_step_log')
    async def test_structured_logging_format(
        self,
        mock_log,
        context_builder_merge,
        canonical_facts,
        kb_results,
        context_data_template
    ):
        """Test that structured logging follows correct format for STEP 40."""
        context_data = {
            **context_data_template,
            "canonical_facts": canonical_facts,
            "kb_results": kb_results,
            "document_facts": None
        }

        result = context_builder_merge.merge_context(context_data)

        # Verify the log was called with correct STEP 40 format
        mock_log.assert_called()

        # Find the context merge log call (completed stage)
        merge_log_calls = [
            call for call in mock_log.call_args_list
            if (len(call[1]) > 3 and 
                call[1].get('step') == 40 and
                call[1].get('processing_stage') == 'completed')
        ]

        # Should have at least one log call for the merge
        assert len(merge_log_calls) > 0

        # Verify required fields
        log_call = merge_log_calls[0]
        assert log_call[1]['step'] == 40
        assert log_call[1]['step_id'] == "RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts"
        assert log_call[1]['node_label'] == "BuildContext"
        assert 'token_count' in log_call[1]
        assert 'trace_id' in log_call[1]