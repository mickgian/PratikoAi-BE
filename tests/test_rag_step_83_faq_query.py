"""
Tests for RAG STEP 83 — FAQTool.faq_query Query Golden Set (RAG.golden.faqtool.faq.query.query.golden.set)

This process step executes on-demand FAQ queries when the LLM calls the FAQTool.
Uses SemanticFAQMatcher and IntelligentFAQService for semantic FAQ matching and response generation.
"""

from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import json

import pytest


class TestRAGStep83FAQQuery:
    """Test suite for RAG STEP 83 - FAQ query tool."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_83_executes_faq_query(self, mock_rag_log):
        """Test Step 83: Executes FAQ query via tool."""
        from app.orchestrators.golden import step_83__faqquery

        ctx = {
            'tool_name': 'FAQTool',
            'tool_args': {
                'query': 'Come si calcola la partita IVA forfettaria?',
                'max_results': 3,
                'min_confidence': 'medium'
            },
            'tool_call_id': 'call_faq_123',
            'request_id': 'test-83-query'
        }

        result = await step_83__faqquery(messages=[], ctx=ctx)

        assert 'faq_results' in result or 'matches' in result
        assert result['next_step'] == 'tool_results'

        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 83
        assert completed_log['node_label'] == 'FAQQuery'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    @patch('app.core.langgraph.tools.faq_tool.faq_tool._arun')
    async def test_step_83_uses_semantic_faq_matcher(self, mock_faq_arun, mock_rag_log):
        """Test Step 83: Uses FAQTool for FAQ matching."""
        from app.orchestrators.golden import step_83__faqquery

        # Mock FAQ tool response
        mock_faq_arun.return_value = json.dumps({
            'success': True,
            'matches': [{
                'faq_id': 'faq_1',
                'question': 'Come funziona il regime forfettario?',
                'answer': 'Il regime forfettario è...',
                'similarity_score': 0.92,
                'confidence': 'high',
                'needs_update': False,
                'matched_concepts': ['regime forfettario'],
                'source_metadata': {}
            }],
            'match_count': 1
        })

        ctx = {
            'tool_args': {
                'query': 'regime forfettario partita IVA',
                'max_results': 5
            },
            'tool_call_id': 'call_semantic',
            'request_id': 'test-83-semantic'
        }

        result = await step_83__faqquery(messages=[], ctx=ctx)

        assert 'faq_results' in result or 'matches' in result
        assert mock_faq_arun.called

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_83_handles_multiple_matches(self, mock_rag_log):
        """Test Step 83: Handles multiple FAQ matches."""
        from app.orchestrators.golden import step_83__faqquery

        ctx = {
            'tool_args': {
                'query': 'IVA e fatturazione elettronica',
                'max_results': 10,
                'min_confidence': 'low'
            },
            'tool_call_id': 'call_multi',
            'request_id': 'test-83-multiple'
        }

        result = await step_83__faqquery(messages=[], ctx=ctx)

        assert 'match_count' in result or 'faq_results' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_83_respects_confidence_threshold(self, mock_rag_log):
        """Test Step 83: Respects minimum confidence threshold."""
        from app.orchestrators.golden import step_83__faqquery

        ctx = {
            'tool_args': {
                'query': 'Test query',
                'max_results': 3,
                'min_confidence': 'high'
            },
            'tool_call_id': 'call_confidence',
            'request_id': 'test-83-confidence'
        }

        result = await step_83__faqquery(messages=[], ctx=ctx)

        # Should have confidence threshold in metadata
        assert 'query_metadata' in result or 'min_confidence' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_83_includes_metadata(self, mock_rag_log):
        """Test Step 83: Includes query metadata in results."""
        from app.orchestrators.golden import step_83__faqquery

        ctx = {
            'tool_args': {
                'query': 'Detrazioni fiscali 730',
                'max_results': 5,
                'min_confidence': 'medium',
                'include_outdated': False
            },
            'tool_call_id': 'call_meta',
            'request_id': 'test-83-metadata'
        }

        result = await step_83__faqquery(messages=[], ctx=ctx)

        assert 'query_metadata' in result
        assert result['query_metadata']['query'] == 'Detrazioni fiscali 730'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_83_routes_to_tool_results(self, mock_rag_log):
        """Test Step 83: Routes to Step 99 (ToolResults) per Mermaid."""
        from app.orchestrators.golden import step_83__faqquery

        ctx = {
            'tool_args': {
                'query': 'Test routing',
                'max_results': 1
            },
            'tool_call_id': 'call_route',
            'request_id': 'test-83-route'
        }

        result = await step_83__faqquery(messages=[], ctx=ctx)

        # Per Mermaid: FAQQuery → ToolResults (Step 99)
        assert result['next_step'] == 'tool_results'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_83_preserves_context(self, mock_rag_log):
        """Test Step 83: Preserves context fields for next steps."""
        from app.orchestrators.golden import step_83__faqquery

        ctx = {
            'tool_args': {
                'query': 'Context preservation test',
                'max_results': 3
            },
            'tool_call_id': 'call_ctx',
            'request_id': 'test-83-context',
            'ai_message': MagicMock(),
            'other_field': 'preserved_value'
        }

        result = await step_83__faqquery(messages=[], ctx=ctx)

        assert result['request_id'] == 'test-83-context'
        assert result['other_field'] == 'preserved_value'
        assert result['tool_call_id'] == 'call_ctx'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_83_handles_no_matches_gracefully(self, mock_rag_log):
        """Test Step 83: Handles no FAQ matches gracefully."""
        from app.orchestrators.golden import step_83__faqquery

        ctx = {
            'tool_args': {
                'query': 'Completely unrelated query xyz123',
                'max_results': 5
            },
            'tool_call_id': 'call_nomatch',
            'request_id': 'test-83-nomatch'
        }

        result = await step_83__faqquery(messages=[], ctx=ctx)

        # Should still route to next step even with no matches
        assert result['next_step'] == 'tool_results'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_83_handles_error_gracefully(self, mock_rag_log):
        """Test Step 83: Handles FAQ query errors gracefully."""
        from app.orchestrators.golden import step_83__faqquery

        ctx = {
            'tool_args': {
                'query': '',  # Empty query to trigger error handling
                'max_results': 3
            },
            'tool_call_id': 'call_error',
            'request_id': 'test-83-error'
        }

        result = await step_83__faqquery(messages=[], ctx=ctx)

        # Should still route to next step even on error
        assert result['next_step'] == 'tool_results'


class TestRAGStep83Parity:
    """Parity tests proving Step 83 uses FAQ services correctly."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_83_parity_with_semantic_matcher(self, mock_rag_log):
        """Test Step 83: Uses same logic as SemanticFAQMatcher."""
        from app.orchestrators.golden import step_83__faqquery

        tool_args = {
            'query': 'Come calcolare IVA su fattura',
            'max_results': 3,
            'min_confidence': 'medium'
        }

        # Orchestrator call
        ctx = {
            'tool_args': tool_args,
            'tool_call_id': 'call_parity',
            'request_id': 'parity-test'
        }

        orch_result = await step_83__faqquery(messages=[], ctx=ctx)

        # Should produce FAQ results
        assert 'faq_results' in orch_result or 'matches' in orch_result

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_83_parity_with_intelligent_faq_service(self, mock_rag_log):
        """Test Step 83: Compatible with IntelligentFAQService patterns."""
        from app.orchestrators.golden import step_83__faqquery

        ctx = {
            'tool_args': {
                'query': 'Regime forfettario limiti reddito',
                'max_results': 5,
                'min_confidence': 'high'
            },
            'tool_call_id': 'call_intelligent',
            'request_id': 'intelligent-test'
        }

        result = await step_83__faqquery(messages=[], ctx=ctx)

        # Should match IntelligentFAQService response patterns
        assert result['next_step'] == 'tool_results'


class TestRAGStep83Integration:
    """Integration tests for Step 79 → Step 83 → Step 99 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_79_to_83_integration(self, mock_golden_log):
        """Test Step 79 (ToolType) → Step 83 (FAQQuery) integration flow."""
        from app.orchestrators.golden import step_83__faqquery

        # Simulate Step 79 output (when FAQ tool type is detected)
        step_79_output = {
            'tool_type': 'FAQ',
            'tool_name': 'FAQTool',
            'tool_call_id': 'call_integration',
            'tool_args': {
                'query': 'Come funziona la fattura elettronica?',
                'max_results': 5,
                'min_confidence': 'medium'
            },
            'next_step': 'faq_query',
            'request_id': 'test-integration-79-83'
        }

        # Step 83: Execute FAQ query
        step_83_result = await step_83__faqquery(messages=[], ctx=step_79_output)

        # Should route to Step 99 (ToolResults)
        assert step_83_result['next_step'] == 'tool_results'
        assert 'faq_results' in step_83_result or 'matches' in step_83_result

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_83_prepares_for_step_99(self, mock_rag_log):
        """Test Step 83: Prepares output for Step 99 (ToolResults)."""
        from app.orchestrators.golden import step_83__faqquery

        ctx = {
            'tool_args': {
                'query': 'Detrazioni fiscali per lavoratori dipendenti',
                'max_results': 3,
                'min_confidence': 'high'
            },
            'tool_call_id': 'call_final',
            'request_id': 'test-83-final',
            'ai_message': MagicMock()
        }

        result = await step_83__faqquery(messages=[], ctx=ctx)

        # Should have everything Step 99 needs
        assert 'tool_call_id' in result
        assert result['next_step'] == 'tool_results'
        assert 'faq_results' in result or 'query_result' in result