"""
Tests for RAG STEP 26 Orchestrator — KnowledgeSearch.context_topk fetch recent KB for changes
(RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes)

This orchestrator fetches recent KB changes when a high-confidence Golden Set match occurs,
to determine if the KB has newer or conflicting information that should override the Golden answer.
"""

from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta

import pytest


class TestRAGStep26KBContextOrchestrator:
    """Test suite for RAG STEP 26 orchestrator - KB context check."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_26_fetches_recent_kb_changes(self, mock_rag_log):
        """Test Step 26: Fetches recent KB changes for Golden Set validation."""
        from app.orchestrators.kb import step_26__kbcontext_check

        ctx = {
            'user_query': 'Quali sono le detrazioni fiscali 2024?',
            'golden_match': {
                'faq_id': 'faq_001',
                'question': 'Detrazioni fiscali 2024?',
                'answer': 'Le detrazioni includono...',
                'updated_at': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            },
            'canonical_facts': ['detrazioni', 'fiscali', '2024'],
            'request_id': 'test-26-fetch'
        }

        with patch('app.services.knowledge_search_service.KnowledgeSearchService') as MockService:
            mock_service = MockService.return_value
            mock_service.fetch_recent_kb_for_changes = AsyncMock(return_value=[
                MagicMock(
                    id='kb_001',
                    title='Nuove detrazioni 2024',
                    content='Aggiornamento detrazioni fiscali',
                    updated_at=datetime.now(timezone.utc) - timedelta(days=5),
                    score=0.92
                )
            ])

            result = await step_26__kbcontext_check(messages=[], ctx=ctx)

            assert isinstance(result, dict)
            assert 'kb_recent_changes' in result
            assert len(result['kb_recent_changes']) == 1
            assert result['kb_recent_changes'][0]['id'] == 'kb_001'
            assert result['has_recent_changes'] is True
            assert result['next_step'] == 'kb_delta_check'  # Routes to Step 27

            assert mock_rag_log.call_count >= 2

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_26_no_recent_changes(self, mock_rag_log):
        """Test Step 26: No recent KB changes found."""
        from app.orchestrators.kb import step_26__kbcontext_check

        ctx = {
            'user_query': 'Pensione anticipata',
            'golden_match': {
                'faq_id': 'faq_002',
                'updated_at': (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
            },
            'request_id': 'test-26-no-changes'
        }

        with patch('app.services.knowledge_search_service.KnowledgeSearchService') as MockService:
            mock_service = MockService.return_value
            mock_service.fetch_recent_kb_for_changes = AsyncMock(return_value=[])

            result = await step_26__kbcontext_check(messages=[], ctx=ctx)

            assert result['kb_recent_changes'] == []
            assert result['has_recent_changes'] is False
            assert result['next_step'] == 'kb_delta_check'

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_26_preserves_context(self, mock_rag_log):
        """Test Step 26: Preserves all context from previous steps."""
        from app.orchestrators.kb import step_26__kbcontext_check

        ctx = {
            'user_query': 'Test query',
            'canonical_facts': ['test', 'facts'],
            'golden_match': {'faq_id': 'faq_001', 'updated_at': datetime.now(timezone.utc).isoformat()},
            'high_confidence_match': True,
            'similarity_score': 0.95,
            'match_type': 'semantic',
            'request_id': 'test-26-context'
        }

        with patch('app.services.knowledge_search_service.KnowledgeSearchService') as MockService:
            mock_service = MockService.return_value
            mock_service.fetch_recent_kb_for_changes = AsyncMock(return_value=[])

            result = await step_26__kbcontext_check(messages=[], ctx=ctx)

            assert result['user_query'] == 'Test query'
            assert result['canonical_facts'] == ['test', 'facts']
            assert result['golden_match']['faq_id'] == 'faq_001'
            assert result['high_confidence_match'] is True
            assert result['similarity_score'] == 0.95

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_26_includes_kb_metadata(self, mock_rag_log):
        """Test Step 26: Includes KB fetch metadata for observability."""
        from app.orchestrators.kb import step_26__kbcontext_check

        ctx = {
            'user_query': 'Test',
            'golden_match': {'faq_id': 'faq_001', 'updated_at': datetime.now(timezone.utc).isoformat()},
            'request_id': 'test-26-metadata'
        }

        with patch('app.services.knowledge_search_service.KnowledgeSearchService') as MockService:
            mock_service = MockService.return_value
            mock_service.fetch_recent_kb_for_changes = AsyncMock(return_value=[
                MagicMock(id='kb_1', score=0.9),
                MagicMock(id='kb_2', score=0.85)
            ])

            result = await step_26__kbcontext_check(messages=[], ctx=ctx)

            assert 'kb_fetch_metadata' in result
            metadata = result['kb_fetch_metadata']
            assert metadata['recent_changes_count'] == 2
            assert metadata['has_recent_changes'] is True
            assert 'fetch_timestamp' in metadata

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_26_logs_kb_fetch_details(self, mock_rag_log):
        """Test Step 26: Logs KB fetch details for debugging."""
        from app.orchestrators.kb import step_26__kbcontext_check

        ctx = {
            'user_query': 'Test query',
            'golden_match': {'faq_id': 'faq_001', 'updated_at': datetime.now(timezone.utc).isoformat()},
            'request_id': 'test-26-logging'
        }

        with patch('app.services.knowledge_search_service.KnowledgeSearchService') as MockService:
            mock_service = MockService.return_value
            mock_service.fetch_recent_kb_for_changes = AsyncMock(return_value=[
                MagicMock(id='kb_1')
            ])

            result = await step_26__kbcontext_check(messages=[], ctx=ctx)

            completed_logs = [
                call for call in mock_rag_log.call_args_list
                if call[1].get('processing_stage') == 'completed'
            ]

            assert len(completed_logs) > 0
            log = completed_logs[0][1]
            assert log['step'] == 26
            assert log['node_label'] == 'KBContextCheck'
            assert log['has_recent_changes'] is True
            assert log['recent_changes_count'] == 1

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_26_handles_service_error(self, mock_rag_log):
        """Test Step 26: Handles KB service errors gracefully."""
        from app.orchestrators.kb import step_26__kbcontext_check

        ctx = {
            'user_query': 'Test',
            'golden_match': {'faq_id': 'faq_001', 'updated_at': datetime.now(timezone.utc).isoformat()},
            'request_id': 'test-26-error'
        }

        with patch('app.services.knowledge_search_service.KnowledgeSearchService') as MockService:
            mock_service = MockService.return_value
            mock_service.fetch_recent_kb_for_changes = AsyncMock(
                side_effect=Exception("KB service error")
            )

            result = await step_26__kbcontext_check(messages=[], ctx=ctx)

            # Should gracefully degrade to no changes
            assert result['kb_recent_changes'] == []
            assert result['has_recent_changes'] is False
            assert 'error' in result

            error_logs = [
                call for call in mock_rag_log.call_args_list
                if call[1].get('processing_stage') == 'error'
            ]
            assert len(error_logs) > 0

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_26_uses_golden_timestamp(self, mock_rag_log):
        """Test Step 26: Uses Golden Set timestamp for recency comparison."""
        from app.orchestrators.kb import step_26__kbcontext_check

        golden_updated_at = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
        ctx = {
            'user_query': 'Test',
            'golden_match': {
                'faq_id': 'faq_001',
                'updated_at': golden_updated_at
            },
            'request_id': 'test-26-timestamp'
        }

        with patch('app.services.knowledge_search_service.KnowledgeSearchService') as MockService:
            mock_service = MockService.return_value
            mock_service.fetch_recent_kb_for_changes = AsyncMock(return_value=[])

            result = await step_26__kbcontext_check(messages=[], ctx=ctx)

            # Verify service was called with query and since_date
            call_kwargs = mock_service.fetch_recent_kb_for_changes.call_args[1]
            assert 'query' in call_kwargs
            assert 'since_date' in call_kwargs
            assert call_kwargs['query'] == 'Test'


class TestRAGStep26Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_26_parity_kb_service_integration(self):
        """Test Step 26: KB service integration matches expected behavior."""
        from app.orchestrators.kb import step_26__kbcontext_check

        ctx = {
            'user_query': 'Test query',
            'golden_match': {'faq_id': 'test', 'updated_at': datetime.now(timezone.utc).isoformat()},
            'request_id': 'parity-test'
        }

        with patch('app.services.knowledge_search_service.KnowledgeSearchService') as MockService:
            mock_service = MockService.return_value
            mock_service.fetch_recent_kb_for_changes = AsyncMock(return_value=[])

            result = await step_26__kbcontext_check(messages=[], ctx=ctx)

            # Verify service was initialized and called
            MockService.assert_called_once()
            mock_service.fetch_recent_kb_for_changes.assert_called_once()

            # Verify result structure
            assert 'kb_recent_changes' in result
            assert 'has_recent_changes' in result
            assert 'next_step' in result


class TestRAGStep26Integration:
    """Integration tests - prove Step 25 → 26 → 27 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_25_to_26_high_confidence_integration(self, mock_golden_log, mock_kb_log):
        """Test Step 25 → 26 integration: High confidence match flows to KB check."""
        from app.orchestrators.golden import step_25__golden_hit
        from app.orchestrators.kb import step_26__kbcontext_check

        initial_ctx = {
            'golden_match': {
                'faq_id': 'faq_001',
                'similarity_score': 0.95,
                'updated_at': (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
            },
            'match_found': True,
            'similarity_score': 0.95,
            'request_id': 'integration-25-26'
        }

        step_25_result = await step_25__golden_hit(messages=[], ctx=initial_ctx)

        assert step_25_result['high_confidence_match'] is True
        assert step_25_result['next_step'] == 'kb_context_check'

        with patch('app.services.knowledge_search_service.KnowledgeSearchService') as MockService:
            mock_service = MockService.return_value
            mock_service.fetch_recent_kb_for_changes = AsyncMock(return_value=[
                MagicMock(id='kb_new', updated_at=datetime.now(timezone.utc) - timedelta(days=5))
            ])

            step_26_result = await step_26__kbcontext_check(messages=[], ctx=step_25_result)

            assert 'kb_recent_changes' in step_26_result
            assert step_26_result['has_recent_changes'] is True
            assert step_26_result['next_step'] == 'kb_delta_check'

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_26_prepares_for_step_27(self, mock_rag_log):
        """Test Step 26: Prepares context correctly for Step 27 (KB delta check)."""
        from app.orchestrators.kb import step_26__kbcontext_check

        ctx = {
            'user_query': 'Detrazioni 2024',
            'golden_match': {
                'faq_id': 'faq_001',
                'answer': 'Detrazioni al 22%',
                'updated_at': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                'metadata': {'category': 'tax', 'tags': ['rate_22']}
            },
            'high_confidence_match': True,
            'similarity_score': 0.94,
            'request_id': 'test-26-to-27'
        }

        with patch('app.services.knowledge_search_service.KnowledgeSearchService') as MockService:
            mock_service = MockService.return_value
            mock_service.fetch_recent_kb_for_changes = AsyncMock(return_value=[
                MagicMock(
                    id='kb_new',
                    content='Nuove aliquote al 25%',
                    updated_at=datetime.now(timezone.utc) - timedelta(days=3),
                    metadata={'category': 'tax', 'tags': ['rate_25', 'supersedes']}
                )
            ])

            result = await step_26__kbcontext_check(messages=[], ctx=ctx)

            assert result['next_step'] == 'kb_delta_check'
            assert 'kb_recent_changes' in result
            assert len(result['kb_recent_changes']) == 1
            assert result['golden_match']['faq_id'] == 'faq_001'
            assert result['has_recent_changes'] is True