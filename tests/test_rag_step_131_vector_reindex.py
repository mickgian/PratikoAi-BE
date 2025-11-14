"""
Tests for RAG Step 131: VectorReindex (VectorIndex.upsert_faq update embeddings).

This step updates vector embeddings for published/updated FAQ entries using EmbeddingManager.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone


class TestRAGStep131VectorReindex:
    """Unit tests for Step 131: VectorReindex."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_131_updates_faq_embeddings(self, mock_rag_log):
        """Test Step 131: Updates FAQ embeddings in vector index."""
        from app.orchestrators.golden import step_131__vector_reindex

        ctx = {
            'published_faq': {
                'id': 'faq_123',
                'question': 'How do I calculate INPS contributions?',
                'answer': 'INPS contributions are calculated based on...',
                'category': 'contributions',
                'version': 1
            },
            'publication_metadata': {
                'faq_id': 'faq_123',
                'operation': 'created'
            },
            'request_id': 'test-131-update'
        }

        with patch('app.services.embedding_management.EmbeddingManager') as MockEmbedding:
            mock_manager = MagicMock()
            mock_result = MagicMock()
            mock_result.successful = 1
            mock_result.total_items = 1
            mock_result.failed = 0
            mock_result.processing_time_seconds = 0.5

            mock_manager.update_pinecone_embeddings = AsyncMock(return_value=mock_result)
            MockEmbedding.return_value = mock_manager

            result = await step_131__vector_reindex(messages=[], ctx=ctx)

            assert isinstance(result, dict)
            assert 'vector_index_metadata' in result
            assert result['vector_index_metadata']['faq_id'] == 'faq_123'
            assert result['vector_index_metadata']['embeddings_updated'] == 1
            assert result['vector_index_metadata']['success'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_131_handles_updated_faq(self, mock_rag_log):
        """Test Step 131: Handles updated FAQ with version increment."""
        from app.orchestrators.golden import step_131__vector_reindex

        ctx = {
            'published_faq': {
                'id': 'faq_456',
                'question': 'Updated question',
                'answer': 'Updated answer',
                'category': 'test',
                'version': 2
            },
            'publication_metadata': {
                'faq_id': 'faq_456',
                'operation': 'updated',
                'previous_version': 1
            },
            'request_id': 'test-131-version'
        }

        with patch('app.services.embedding_management.EmbeddingManager') as MockEmbedding:
            mock_manager = MagicMock()
            mock_result = MagicMock()
            mock_result.successful = 1
            mock_result.total_items = 1
            mock_result.failed = 0
            mock_result.processing_time_seconds = 0.3

            mock_manager.update_pinecone_embeddings = AsyncMock(return_value=mock_result)
            MockEmbedding.return_value = mock_manager

            result = await step_131__vector_reindex(messages=[], ctx=ctx)

            assert result['vector_index_metadata']['version'] == 2
            assert result['vector_index_metadata']['operation'] == 'updated'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_131_preserves_context(self, mock_rag_log):
        """Test Step 131: Preserves all context data."""
        from app.orchestrators.golden import step_131__vector_reindex

        original_ctx = {
            'published_faq': {
                'id': 'faq_ctx',
                'question': 'Test question',
                'answer': 'Test answer',
                'category': 'test'
            },
            'publication_metadata': {
                'faq_id': 'faq_ctx',
                'operation': 'created'
            },
            'cache_invalidation': {
                'keys_deleted': 5,
                'success': True
            },
            'expert_id': 'expert_123',
            'trust_score': 0.92,
            'user_data': {'id': 'user_456'},
            'session_data': {'id': 'session_789'},
            'request_id': 'test-131-context'
        }

        with patch('app.services.embedding_management.EmbeddingManager') as MockEmbedding:
            mock_manager = MagicMock()
            mock_result = MagicMock()
            mock_result.successful = 1
            mock_result.failed = 0
            mock_result.processing_time_seconds = 0.2

            mock_manager.update_pinecone_embeddings = AsyncMock(return_value=mock_result)
            MockEmbedding.return_value = mock_manager

            result = await step_131__vector_reindex(messages=[], ctx=original_ctx.copy())

            # Verify all original context is preserved
            assert result['expert_id'] == original_ctx['expert_id']
            assert result['trust_score'] == original_ctx['trust_score']
            assert result['user_data'] == original_ctx['user_data']
            assert result['session_data'] == original_ctx['session_data']
            assert result['cache_invalidation'] == original_ctx['cache_invalidation']
            assert result['request_id'] == original_ctx['request_id']

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_131_includes_metadata_in_embeddings(self, mock_rag_log):
        """Test Step 131: Includes FAQ metadata in vector embeddings."""
        from app.orchestrators.golden import step_131__vector_reindex

        ctx = {
            'published_faq': {
                'id': 'faq_meta',
                'question': 'Metadata test question',
                'answer': 'Metadata test answer',
                'category': 'benefits',
                'regulatory_references': ['D.L. 201/2011'],
                'quality_score': 0.96
            },
            'publication_metadata': {
                'faq_id': 'faq_meta',
                'operation': 'created'
            },
            'request_id': 'test-131-metadata'
        }

        with patch('app.services.embedding_management.EmbeddingManager') as MockEmbedding:
            mock_manager = MagicMock()
            mock_result = MagicMock()
            mock_result.successful = 1
            mock_result.failed = 0
            mock_result.processing_time_seconds = 0.1

            mock_manager.update_pinecone_embeddings = AsyncMock(return_value=mock_result)
            MockEmbedding.return_value = mock_manager

            result = await step_131__vector_reindex(messages=[], ctx=ctx)

            # Verify update_pinecone_embeddings was called with proper metadata
            mock_manager.update_pinecone_embeddings.assert_called_once()
            call_args = mock_manager.update_pinecone_embeddings.call_args

            # Should include FAQ content and metadata - check kwargs
            kwargs = call_args[1]  # Keyword arguments
            assert 'items' in kwargs
            items = kwargs['items']
            assert len(items) == 1
            assert 'metadata' in items[0]

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_131_handles_embedding_service_error(self, mock_rag_log):
        """Test Step 131: Handles embedding service errors gracefully."""
        from app.orchestrators.golden import step_131__vector_reindex

        ctx = {
            'published_faq': {
                'id': 'faq_error',
                'question': 'Error question',
                'answer': 'Error answer',
                'category': 'test'
            },
            'publication_metadata': {
                'faq_id': 'faq_error',
                'operation': 'created'
            },
            'request_id': 'test-131-error'
        }

        with patch('app.services.embedding_management.EmbeddingManager') as MockEmbedding:
            mock_manager = MagicMock()
            mock_manager.update_pinecone_embeddings = AsyncMock(
                side_effect=Exception("Pinecone connection error")
            )
            MockEmbedding.return_value = mock_manager

            result = await step_131__vector_reindex(messages=[], ctx=ctx)

            assert 'vector_index_metadata' in result
            assert result['vector_index_metadata']['success'] is False
            assert 'error' in result['vector_index_metadata']

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_131_adds_indexing_metadata(self, mock_rag_log):
        """Test Step 131: Adds vector indexing metadata for tracking."""
        from app.orchestrators.golden import step_131__vector_reindex

        ctx = {
            'published_faq': {
                'id': 'faq_track',
                'question': 'Tracking question',
                'answer': 'Tracking answer',
                'category': 'test'
            },
            'publication_metadata': {
                'faq_id': 'faq_track',
                'operation': 'created'
            },
            'request_id': 'test-131-tracking'
        }

        with patch('app.services.embedding_management.EmbeddingManager') as MockEmbedding:
            mock_manager = MagicMock()
            mock_result = MagicMock()
            mock_result.successful = 1
            mock_result.total_items = 1
            mock_result.processing_time_seconds = 0.5

            mock_manager.update_pinecone_embeddings = AsyncMock(return_value=mock_result)
            MockEmbedding.return_value = mock_manager

            result = await step_131__vector_reindex(messages=[], ctx=ctx)

            assert 'vector_index_metadata' in result
            metadata = result['vector_index_metadata']
            assert 'indexed_at' in metadata
            assert 'faq_id' in metadata
            assert 'embeddings_updated' in metadata
            assert 'processing_time' in metadata

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_131_completes_faq_publication_flow(self, mock_rag_log):
        """Test Step 131: Completes the FAQ publication flow."""
        from app.orchestrators.golden import step_131__vector_reindex

        ctx = {
            'published_faq': {
                'id': 'faq_complete',
                'question': 'Complete flow question',
                'answer': 'Complete flow answer',
                'category': 'test'
            },
            'publication_metadata': {
                'faq_id': 'faq_complete',
                'operation': 'created'
            },
            'request_id': 'test-131-complete'
        }

        with patch('app.services.embedding_management.EmbeddingManager') as MockEmbedding:
            mock_manager = MagicMock()
            mock_result = MagicMock()
            mock_result.successful = 1
            mock_result.failed = 0
            mock_result.processing_time_seconds = 0.4

            mock_manager.update_pinecone_embeddings = AsyncMock(return_value=mock_result)
            MockEmbedding.return_value = mock_manager

            result = await step_131__vector_reindex(messages=[], ctx=ctx)

            # Verify flow completion indicators
            assert 'vector_index_metadata' in result
            assert result['vector_index_metadata']['success'] is True
            # Step 131 is an end node in the FAQ publication flow

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_131_logs_indexing_details(self, mock_rag_log):
        """Test Step 131: Logs vector indexing details for observability."""
        from app.orchestrators.golden import step_131__vector_reindex

        ctx = {
            'published_faq': {
                'id': 'faq_log',
                'question': 'Log question',
                'answer': 'Log answer',
                'category': 'test_category'
            },
            'publication_metadata': {
                'faq_id': 'faq_log',
                'operation': 'created'
            },
            'request_id': 'test-131-logging'
        }

        with patch('app.services.embedding_management.EmbeddingManager') as MockEmbedding:
            mock_manager = MagicMock()
            mock_result = MagicMock()
            mock_result.successful = 1
            mock_result.failed = 0
            mock_result.processing_time_seconds = 0.1

            mock_manager.update_pinecone_embeddings = AsyncMock(return_value=mock_result)
            MockEmbedding.return_value = mock_manager

            await step_131__vector_reindex(messages=[], ctx=ctx)

            # Verify structured logging
            assert mock_rag_log.call_count >= 2
            final_call = None
            for call in mock_rag_log.call_args_list:
                if call[1].get('processing_stage') == 'completed':
                    final_call = call[1]
                    break

            assert final_call is not None
            assert final_call['step'] == 131
            assert 'faq_id' in final_call
            assert 'embeddings_updated' in final_call


class TestRAGStep131Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_131_parity_embedding_update(self):
        """Test Step 131 parity: Embedding update behavior unchanged."""
        from app.orchestrators.golden import step_131__vector_reindex

        test_cases = [
            {
                'published_faq': {'id': 'faq_1', 'question': 'Q1', 'answer': 'A1'},
                'expected_calls': 1
            },
            {
                'published_faq': {'id': 'faq_2', 'question': 'Q2', 'answer': 'A2', 'version': 2},
                'expected_calls': 1
            }
        ]

        for test_case in test_cases:
            ctx = {
                **test_case,
                'publication_metadata': {'faq_id': test_case['published_faq']['id']},
                'request_id': f"parity-{test_case['published_faq']['id']}"
            }

            with patch('app.services.embedding_management.EmbeddingManager') as MockEmbedding:
                mock_manager = MagicMock()
                mock_result = MagicMock()
                mock_result.successful = 1

                mock_manager.update_pinecone_embeddings = AsyncMock(return_value=mock_result)
                MockEmbedding.return_value = mock_manager

                with patch('app.orchestrators.golden.rag_step_log'):
                    result = await step_131__vector_reindex(messages=[], ctx=ctx)

                assert 'vector_index_metadata' in result
                assert mock_manager.update_pinecone_embeddings.call_count == test_case['expected_calls']


class TestRAGStep131Integration:
    """Integration tests for Step 131 with neighbors."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_publish_golden_to_131_integration(self, mock_golden_log):
        """Test PublishGolden (Step 129) → Step 131 integration."""

        initial_ctx = {
            'published_faq': {
                'id': 'faq_integration',
                'question': 'Integration question',
                'answer': 'Integration answer',
                'category': 'test',
                'version': 1
            },
            'publication_metadata': {
                'faq_id': 'faq_integration',
                'operation': 'created',
                'published_at': datetime.now(timezone.utc).isoformat()
            },
            'operation': 'created',
            'request_id': 'integration-129-131'
        }

        from app.orchestrators.golden import step_131__vector_reindex

        with patch('app.services.embedding_management.EmbeddingManager') as MockEmbedding:
            mock_manager = MagicMock()
            mock_result = MagicMock()
            mock_result.successful = 1
            mock_result.failed = 0
            mock_result.processing_time_seconds = 0.1

            mock_manager.update_pinecone_embeddings = AsyncMock(return_value=mock_result)
            MockEmbedding.return_value = mock_manager

            result = await step_131__vector_reindex(messages=[], ctx=initial_ctx)

            assert result['operation'] == 'created'
            assert 'vector_index_metadata' in result
            assert result['vector_index_metadata']['faq_id'] == 'faq_integration'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_131_parallel_with_step_130(self, mock_rag_log):
        """Test Step 131 runs in parallel with InvalidateFAQCache (Step 130)."""
        from app.orchestrators.golden import step_131__vector_reindex

        ctx = {
            'published_faq': {
                'id': 'faq_parallel',
                'question': 'Parallel test question',
                'answer': 'Parallel test answer',
                'category': 'test'
            },
            'publication_metadata': {
                'faq_id': 'faq_parallel',
                'operation': 'created'
            },
            # Step 130 might add this, but Step 131 shouldn't depend on it
            # since they run in parallel from Step 129
            'request_id': 'test-131-parallel'
        }

        with patch('app.services.embedding_management.EmbeddingManager') as MockEmbedding:
            mock_manager = MagicMock()
            mock_result = MagicMock()
            mock_result.successful = 1
            mock_result.failed = 0
            mock_result.processing_time_seconds = 0.1

            mock_manager.update_pinecone_embeddings = AsyncMock(return_value=mock_result)
            MockEmbedding.return_value = mock_manager

            result = await step_131__vector_reindex(messages=[], ctx=ctx)

            # Should work independently of Step 130
            assert 'vector_index_metadata' in result
            assert result['vector_index_metadata']['success'] is True