"""
Tests for RAG STEP 28 Orchestrator — Serve Golden answer with citations
(RAG.golden.serve.golden.answer.with.citations)

This orchestrator formats the Golden Set match into a ChatResponse with proper
citations and metadata, serving as the final step for high-confidence FAQ matches.
"""

from unittest.mock import patch
from datetime import datetime, timezone

import pytest


class TestRAGStep28ServeGolden:
    """Test suite for RAG STEP 28 orchestrator - serve golden answer."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_28_serves_golden_with_citations(self, mock_rag_log):
        """Test Step 28: Serves Golden answer with proper citations."""
        from app.orchestrators.golden import step_28__serve_golden

        ctx = {
            'user_query': 'Quali sono le detrazioni fiscali 2024?',
            'golden_match': {
                'faq_id': 'faq_001',
                'question': 'Detrazioni fiscali 2024?',
                'answer': 'Le detrazioni fiscali per il 2024 includono...',
                'category': 'tax',
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'metadata': {'source': 'FAQ database', 'version': 1}
            },
            'kb_has_delta': False,
            'request_id': 'test-28-serve'
        }

        result = await step_28__serve_golden(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert 'response' in result
        assert result['response']['answer'] == 'Le detrazioni fiscali per il 2024 includono...'
        assert 'citations' in result['response']
        assert result['response']['citations'][0]['source'] == 'Golden Set FAQ'
        assert result['response']['citations'][0]['faq_id'] == 'faq_001'
        assert result['next_step'] == 'return_complete'

        assert mock_rag_log.call_count >= 2

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_28_includes_faq_metadata(self, mock_rag_log):
        """Test Step 28: Includes FAQ metadata in response."""
        from app.orchestrators.golden import step_28__serve_golden

        ctx = {
            'user_query': 'Pensione anticipata',
            'golden_match': {
                'faq_id': 'faq_002',
                'question': 'Pensione anticipata?',
                'answer': 'La pensione anticipata richiede...',
                'confidence': 0.95,  # Add confidence for proper test
                'category': 'pension',
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'metadata': {
                    'regulatory_refs': ['DL 123/2020'],
                    'last_validated': '2024-01-15'
                }
            },
            'request_id': 'test-28-metadata'
        }

        result = await step_28__serve_golden(messages=[], ctx=ctx)

        assert 'response_metadata' in result
        metadata = result['response_metadata']
        assert metadata['source_type'] == 'golden_set'
        assert metadata['faq_id'] == 'faq_002'
        assert metadata['category'] == 'pension'
        assert 'confidence' in metadata
        assert metadata['confidence'] == 'high'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_28_formats_citations_correctly(self, mock_rag_log):
        """Test Step 28: Formats citations with all required fields."""
        from app.orchestrators.golden import step_28__serve_golden

        ctx = {
            'golden_match': {
                'faq_id': 'faq_003',
                'question': 'CCNL metalmeccanici?',
                'answer': 'Il CCNL metalmeccanici prevede...',
                'updated_at': '2024-01-20T10:00:00Z',
                'metadata': {
                    'regulatory_refs': ['CCNL 2023', 'Art. 45'],
                    'source_url': 'https://example.com/faq/003'
                }
            },
            'request_id': 'test-28-citations'
        }

        result = await step_28__serve_golden(messages=[], ctx=ctx)

        citations = result['response']['citations']
        assert len(citations) == 1
        citation = citations[0]
        assert citation['source'] == 'Golden Set FAQ'
        assert citation['faq_id'] == 'faq_003'
        assert citation['question'] == 'CCNL metalmeccanici?'
        assert citation['updated_at'] == '2024-01-20T10:00:00Z'
        assert 'regulatory_refs' in citation

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_28_preserves_context(self, mock_rag_log):
        """Test Step 28: Preserves all context from previous steps."""
        from app.orchestrators.golden import step_28__serve_golden

        ctx = {
            'user_query': 'Test query',
            'canonical_facts': ['tax', '2024'],
            'golden_match': {
                'faq_id': 'faq_001',
                'answer': 'Test answer',
                'updated_at': datetime.now(timezone.utc).isoformat()
            },
            'high_confidence_match': True,
            'similarity_score': 0.95,
            'kb_has_delta': False,
            'request_id': 'test-28-context'
        }

        result = await step_28__serve_golden(messages=[], ctx=ctx)

        assert result['user_query'] == 'Test query'
        assert result['canonical_facts'] == ['tax', '2024']
        assert result['high_confidence_match'] is True
        assert result['similarity_score'] == 0.95
        assert result['kb_has_delta'] is False

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_28_logs_serving_details(self, mock_rag_log):
        """Test Step 28: Logs Golden answer serving details."""
        from app.orchestrators.golden import step_28__serve_golden

        ctx = {
            'golden_match': {
                'faq_id': 'faq_001',
                'question': 'Test?',
                'answer': 'Test answer',
                'updated_at': datetime.now(timezone.utc).isoformat()
            },
            'request_id': 'test-28-logging'
        }

        result = await step_28__serve_golden(messages=[], ctx=ctx)

        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        log = completed_logs[0][1]
        assert log['step'] == 28
        assert log['node_label'] == 'ServeGolden'
        assert log['faq_id'] == 'faq_001'
        assert 'answer_length' in log

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_28_handles_missing_metadata(self, mock_rag_log):
        """Test Step 28: Handles missing metadata gracefully."""
        from app.orchestrators.golden import step_28__serve_golden

        ctx = {
            'golden_match': {
                'faq_id': 'faq_minimal',
                'answer': 'Minimal answer',
                'updated_at': datetime.now(timezone.utc).isoformat()
            },
            'request_id': 'test-28-minimal'
        }

        result = await step_28__serve_golden(messages=[], ctx=ctx)

        assert result['response']['answer'] == 'Minimal answer'
        assert 'citations' in result['response']
        assert result['response']['citations'][0]['faq_id'] == 'faq_minimal'
        assert result['next_step'] == 'return_complete'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_28_includes_timing_metadata(self, mock_rag_log):
        """Test Step 28: Includes timing metadata for observability."""
        from app.orchestrators.golden import step_28__serve_golden

        ctx = {
            'golden_match': {
                'faq_id': 'faq_001',
                'answer': 'Test',
                'updated_at': datetime.now(timezone.utc).isoformat()
            },
            'request_id': 'test-28-timing'
        }

        result = await step_28__serve_golden(messages=[], ctx=ctx)

        assert 'serving_metadata' in result
        metadata = result['serving_metadata']
        assert 'served_at' in metadata
        assert metadata['source'] == 'golden_set'
        assert metadata['bypassed_llm'] is True


class TestRAGStep28Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_28_parity_response_format(self):
        """Test Step 28: Response format matches expected structure."""
        from app.orchestrators.golden import step_28__serve_golden

        ctx = {
            'golden_match': {
                'faq_id': 'faq_test',
                'question': 'Test question?',
                'answer': 'Test answer',
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'metadata': {}
            },
            'request_id': 'parity-test'
        }

        result = await step_28__serve_golden(messages=[], ctx=ctx)

        assert 'response' in result
        assert 'answer' in result['response']
        assert 'citations' in result['response']
        assert 'next_step' in result
        assert result['next_step'] == 'return_complete'


class TestRAGStep28Integration:
    """Integration tests - prove Step 27 → 28 → ReturnComplete flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_27_to_28_integration(self, mock_rag_log):
        """Test Step 27 → 28 integration: No delta flows to serve golden."""
        from app.orchestrators.golden import step_27__kbdelta, step_28__serve_golden

        initial_ctx = {
            'user_query': 'Detrazioni fiscali 2024',
            'golden_match': {
                'faq_id': 'faq_001',
                'question': 'Detrazioni fiscali?',
                'answer': 'Le detrazioni includono...',
                'updated_at': datetime.now(timezone.utc).isoformat()
            },
            'kb_recent_changes': [],
            'has_recent_changes': False,
            'request_id': 'integration-27-28'
        }

        step_27_result = await step_27__kbdelta(messages=[], ctx=initial_ctx)

        assert step_27_result['kb_has_delta'] is False
        assert step_27_result['next_step'] == 'serve_golden'

        step_28_result = await step_28__serve_golden(messages=[], ctx=step_27_result)

        assert step_28_result['next_step'] == 'return_complete'
        assert 'response' in step_28_result
        assert step_28_result['response']['answer'] == 'Le detrazioni includono...'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_28_prepares_for_return_complete(self, mock_rag_log):
        """Test Step 28: Prepares response for ReturnComplete step."""
        from app.orchestrators.golden import step_28__serve_golden

        ctx = {
            'user_query': 'Pensione anticipata',
            'golden_match': {
                'faq_id': 'faq_002',
                'question': 'Pensione anticipata?',
                'answer': 'La pensione anticipata richiede 42 anni...',
                'category': 'pension',
                'updated_at': datetime.now(timezone.utc).isoformat()
            },
            'request_id': 'test-28-to-complete'
        }

        result = await step_28__serve_golden(messages=[], ctx=ctx)

        assert result['next_step'] == 'return_complete'
        assert 'response' in result
        assert 'citations' in result['response']
        assert result['response']['answer'] is not None
        assert len(result['response']['citations']) > 0