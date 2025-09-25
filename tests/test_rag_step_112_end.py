"""
Tests for RAG Step 112: End (Return response to user).

This startEnd step returns the final response to the user after all processing is complete,
taking metrics data from Step 111 and creating the final response output.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any, List


class TestRAGStep112End:
    """Unit tests for Step 112: End."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_112_returns_final_response(self, mock_rag_log):
        """Test Step 112: Returns final response to user."""
        from app.orchestrators.response import step_112__end

        # Simulate incoming data from CollectMetrics (Step 111)
        ctx = {
            'metrics_collected': True,
            'user_id': 'user_123',
            'session_id': 'session_456',
            'response_time_ms': 850,
            'cache_hit': False,
            'provider': 'openai',
            'model': 'gpt-4',
            'total_tokens': 245,
            'cost': 0.003,
            'environment': 'development',
            'health_score': 0.95,
            'response': 'Final response content',
            'messages': [
                {'role': 'user', 'content': 'What are the tax rates?'},
                {'role': 'assistant', 'content': 'Final response content'}
            ],
            'metadata': {
                'model_used': 'gpt-4',
                'provider': 'openai',
                'strategy': 'best',
                'cost_eur': 0.003,
                'processing_time_ms': 850
            },
            'request_id': 'test-112-final-response'
        }

        result = await step_112__end(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert result['response_delivered'] is True
        assert result['final_step'] is True
        assert result['response'] == 'Final response content'
        assert result['messages'] == ctx['messages']
        assert result['metadata'] == ctx['metadata']

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_112_handles_streaming_response(self, mock_rag_log):
        """Test Step 112: Handles streaming response completion."""
        from app.orchestrators.response import step_112__end

        ctx = {
            'streaming_response': True,
            'chunks_sent': 15,
            'total_bytes': 2048,
            'streaming_completed': True,
            'metrics_collected': True,
            'user_id': 'user_789',
            'response': 'Streaming response completed',
            'messages': [
                {'role': 'user', 'content': 'Stream this response'},
                {'role': 'assistant', 'content': 'Streaming response completed'}
            ],
            'request_id': 'test-112-streaming'
        }

        result = await step_112__end(messages=[], ctx=ctx)

        assert result['response_delivered'] is True
        assert result['streaming_response'] is True
        assert result['streaming_completed'] is True
        assert result['chunks_sent'] == 15
        assert result['total_bytes'] == 2048

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_112_preserves_all_context_data(self, mock_rag_log):
        """Test Step 112: Preserves all context data for final response."""
        from app.orchestrators.response import step_112__end

        original_ctx = {
            'user_data': {'id': 'user_123', 'preferences': {'language': 'it'}},
            'session_data': {'id': 'session_456', 'created_at': '2024-01-01'},
            'response_metadata': {
                'provider': 'anthropic',
                'model': 'claude-3',
                'tokens_used': 200,
                'cost_eur': 0.002
            },
            'processing_history': ['init_agent', 'classify', 'kb_search', 'llm_call', 'collect_metrics'],
            'metrics_collected': True,
            'response': 'Comprehensive response',
            'messages': [
                {'role': 'user', 'content': 'Test query'},
                {'role': 'assistant', 'content': 'Comprehensive response'}
            ],
            'request_id': 'test-112-preserve'
        }

        result = await step_112__end(messages=[], ctx=original_ctx.copy())

        # Verify all original context is preserved
        assert result['user_data'] == original_ctx['user_data']
        assert result['session_data'] == original_ctx['session_data']
        assert result['response_metadata'] == original_ctx['response_metadata']
        assert result['processing_history'] == original_ctx['processing_history']
        assert result['metrics_collected'] == original_ctx['metrics_collected']
        assert result['response'] == original_ctx['response']
        assert result['messages'] == original_ctx['messages']

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_112_adds_completion_metadata(self, mock_rag_log):
        """Test Step 112: Adds completion metadata."""
        from app.orchestrators.response import step_112__end

        ctx = {
            'response': 'Test response',
            'messages': [{'role': 'assistant', 'content': 'Test response'}],
            'metrics_collected': True,
            'request_id': 'test-112-metadata'
        }

        result = await step_112__end(messages=[], ctx=ctx)

        assert result['processing_stage'] == 'completed'
        assert result['final_step'] is True
        assert result['response_delivered'] is True
        assert 'completion_timestamp' in result

        # Verify timestamp format
        timestamp = result['completion_timestamp']
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))  # Should not raise

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_112_handles_error_responses(self, mock_rag_log):
        """Test Step 112: Handles error responses appropriately."""
        from app.orchestrators.response import step_112__end

        ctx = {
            'error': 'LLM provider timeout',
            'response': None,
            'response_type': 'error',
            'success': False,
            'messages': [],
            'request_id': 'test-112-error'
        }

        result = await step_112__end(messages=[], ctx=ctx)

        assert result['response_delivered'] is True  # Still delivered, even if error
        assert result['error'] == 'LLM provider timeout'
        assert result['response_type'] == 'error'
        assert result['success'] is False

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_112_handles_empty_context(self, mock_rag_log):
        """Test Step 112: Handles empty or minimal context gracefully."""
        from app.orchestrators.response import step_112__end

        # Test with minimal context
        ctx = {
            'request_id': 'test-112-minimal'
        }

        result = await step_112__end(messages=[], ctx=ctx)

        assert result['response_delivered'] is True
        assert result['final_step'] is True
        assert 'completion_timestamp' in result
        assert result.get('response') == ''
        assert result.get('messages') == []

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_112_handles_various_response_types(self, mock_rag_log):
        """Test Step 112: Handles various response types."""
        from app.orchestrators.response import step_112__end

        test_cases = [
            {
                'response_type': 'text',
                'response': 'Plain text response',
                'expected_type': 'text'
            },
            {
                'response_type': 'json',
                'response': {'data': 'JSON response'},
                'expected_type': 'json'
            },
            {
                'response_type': 'streaming',
                'streaming_completed': True,
                'expected_type': 'streaming'
            }
        ]

        for i, test_case in enumerate(test_cases):
            ctx = {
                **test_case,
                'request_id': f'test-112-types-{i}'
            }
            # Remove expected values from context
            expected_type = ctx.pop('expected_type', None)

            with patch('app.orchestrators.response.rag_step_log'):
                result = await step_112__end(messages=[], ctx=ctx)

            assert result['response_delivered'] is True
            if 'response_type' in test_case:
                assert result['response_type'] == expected_type

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_112_includes_performance_metrics(self, mock_rag_log):
        """Test Step 112: Includes performance metrics in final response."""
        from app.orchestrators.response import step_112__end

        ctx = {
            'response_time_ms': 1200,
            'total_tokens': 150,
            'cost': 0.0025,
            'cache_hit': True,
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'metrics_collected': True,
            'health_score': 0.88,
            'response': 'Performance test response',
            'request_id': 'test-112-performance'
        }

        result = await step_112__end(messages=[], ctx=ctx)

        assert result['response_time_ms'] == 1200
        assert result['total_tokens'] == 150
        assert result['cost'] == 0.0025
        assert result['cache_hit'] is True
        assert result['provider'] == 'openai'
        assert result['model'] == 'gpt-3.5-turbo'
        assert result['health_score'] == 0.88

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_112_handles_feedback_context(self, mock_rag_log):
        """Test Step 112: Handles feedback collection context."""
        from app.orchestrators.response import step_112__end

        ctx = {
            'response': 'Response with feedback',
            'messages': [
                {'role': 'user', 'content': 'Question with potential feedback'},
                {'role': 'assistant', 'content': 'Response with feedback'}
            ],
            'feedback_enabled': True,
            'feedback_options': ['correct', 'incomplete', 'wrong'],
            'expert_feedback_available': True,
            'metrics_collected': True,
            'request_id': 'test-112-feedback'
        }

        result = await step_112__end(messages=[], ctx=ctx)

        assert result['response_delivered'] is True
        assert result['feedback_enabled'] is True
        assert result['feedback_options'] == ['correct', 'incomplete', 'wrong']
        assert result['expert_feedback_available'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_112_logs_completion_details(self, mock_rag_log):
        """Test Step 112: Logs completion details for observability."""
        from app.orchestrators.response import step_112__end

        ctx = {
            'response': 'Logging test response',
            'messages': [
                {'role': 'assistant', 'content': 'Logging test response'}
            ],
            'user_id': 'user_logging_test',
            'session_id': 'session_logging_test',
            'provider': 'anthropic',
            'model': 'claude-3',
            'response_time_ms': 950,
            'metrics_collected': True,
            'request_id': 'test-112-logging'
        }

        await step_112__end(messages=[], ctx=ctx)

        # Verify structured logging
        assert mock_rag_log.call_count >= 2

        # Find the completion log call
        completion_call = None
        for call in mock_rag_log.call_args_list:
            if call[1].get('processing_stage') == 'completed':
                completion_call = call[1]
                break

        assert completion_call is not None
        assert completion_call['step'] == 112
        assert completion_call['response_delivered'] is True
        assert completion_call['final_step'] is True


class TestRAGStep112Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_112_parity_response_delivery_behavior(self):
        """Test Step 112 parity: Response delivery behavior unchanged."""
        from app.orchestrators.response import step_112__end

        test_cases = [
            {
                'response': 'Parity test response 1',
                'messages': [{'role': 'assistant', 'content': 'Parity test response 1'}],
                'expected_delivered': True,
                'expected_final': True
            },
            {
                'response': 'Parity test response 2',
                'messages': [{'role': 'assistant', 'content': 'Parity test response 2'}],
                'streaming_response': True,
                'expected_delivered': True,
                'expected_final': True
            }
        ]

        for test_case in test_cases:
            ctx = {
                **test_case,
                'request_id': f"parity-{hash(str(test_case))}"
            }
            # Remove expected values from context
            expected_delivered = ctx.pop('expected_delivered', None)
            expected_final = ctx.pop('expected_final', None)

            with patch('app.orchestrators.response.rag_step_log'):
                result = await step_112__end(messages=[], ctx=ctx)

            assert result['response_delivered'] == expected_delivered
            assert result['final_step'] == expected_final
            assert result['processing_stage'] == 'completed'


class TestRAGStep112Integration:
    """Integration tests for Step 112 with neighbors."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_collect_metrics_to_112_integration(self, mock_collect_metrics_log):
        """Test CollectMetrics → Step 112 integration."""

        # Simulate incoming from CollectMetrics (Step 111)
        collect_metrics_ctx = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metrics_collected': True,
            'user_id': 'integration_user_112',
            'session_id': 'integration_session_112',
            'response_time_ms': 750,
            'cache_hit': True,
            'provider': 'openai',
            'model': 'gpt-4',
            'total_tokens': 180,
            'cost': 0.0035,
            'environment': 'development',
            'user_metrics_available': True,
            'system_metrics_available': True,
            'metrics_report_available': True,
            'health_score': 0.92,
            'alerts_count': 0,
            'response': 'Integration test response',
            'messages': [
                {'role': 'user', 'content': 'Integration test query'},
                {'role': 'assistant', 'content': 'Integration test response'}
            ],
            'metadata': {
                'model_used': 'gpt-4',
                'provider': 'openai',
                'strategy': 'best',
                'cost_eur': 0.0035,
                'processing_time_ms': 750
            },
            'request_id': 'integration-collect-metrics-112'
        }

        from app.orchestrators.response import step_112__end

        result = await step_112__end(messages=[], ctx=collect_metrics_ctx)

        assert result['metrics_collected'] is True
        assert result['response_delivered'] is True
        assert result['final_step'] is True
        assert result['response'] == 'Integration test response'
        assert result['messages'] == collect_metrics_ctx['messages']
        assert result['metadata'] == collect_metrics_ctx['metadata']
        assert result['health_score'] == 0.92

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_112_full_pipeline_completion(self, mock_rag_log):
        """Test Step 112 completes the full RAG pipeline."""
        from app.orchestrators.response import step_112__end

        # Simulate full pipeline context
        full_pipeline_ctx = {
            # User input tracking
            'user_id': 'full_pipeline_user',
            'session_id': 'full_pipeline_session',
            'original_query': 'What are the current tax rates?',
            # Processing stages
            'processing_history': [
                'validate_request', 'gdpr_log', 'classify_query', 'extract_facts',
                'knowledge_search', 'llm_call', 'process_response', 'collect_metrics'
            ],
            # Classification results
            'domain': 'TAX',
            'action': 'INFORMATION_REQUEST',
            'confidence': 0.85,
            # LLM interaction
            'provider': 'openai',
            'model': 'gpt-4',
            'response_time_ms': 1100,
            'total_tokens': 220,
            'cost': 0.004,
            'cache_hit': False,
            # Final response
            'response': 'Current tax rates are: Personal income tax ranges from 23% to 43%...',
            'messages': [
                {'role': 'user', 'content': 'What are the current tax rates?'},
                {'role': 'assistant', 'content': 'Current tax rates are: Personal income tax ranges from 23% to 43%...'}
            ],
            'metadata': {
                'model_used': 'gpt-4',
                'provider': 'openai',
                'strategy': 'best',
                'cost_eur': 0.004,
                'processing_time_ms': 1100,
                'classification': {
                    'domain': 'TAX',
                    'action': 'INFORMATION_REQUEST',
                    'confidence': 0.85
                }
            },
            # Metrics collection
            'metrics_collected': True,
            'health_score': 0.96,
            'user_metrics_available': True,
            'system_metrics_available': True,
            'request_id': 'full-pipeline-112'
        }

        result = await step_112__end(messages=[], ctx=full_pipeline_ctx)

        # Verify full pipeline completion
        assert result['response_delivered'] is True
        assert result['final_step'] is True
        assert result['processing_history'] == full_pipeline_ctx['processing_history']
        assert result['domain'] == 'TAX'
        assert result['action'] == 'INFORMATION_REQUEST'
        assert result['confidence'] == 0.85
        assert result['provider'] == 'openai'
        assert result['model'] == 'gpt-4'
        assert result['response'] == full_pipeline_ctx['response']
        assert result['messages'] == full_pipeline_ctx['messages']
        assert result['metadata'] == full_pipeline_ctx['metadata']
        assert result['metrics_collected'] is True
        assert result['health_score'] == 0.96

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_112_error_handling(self, mock_rag_log):
        """Test Step 112 error handling and graceful completion."""
        from app.orchestrators.response import step_112__end

        # Test with error context
        error_ctx = {
            'error': 'Provider timeout during LLM call',
            'success': False,
            'response_type': 'error',
            'response': None,
            'messages': [],
            'provider': 'openai',
            'model': 'gpt-4',
            'response_time_ms': 30000,  # Timeout
            'metrics_collected': True,
            'request_id': 'test-112-error-handling'
        }

        result = await step_112__end(messages=[], ctx=error_ctx)

        # Should handle gracefully even with errors
        assert result['response_delivered'] is True  # Always delivers, even errors
        assert result['final_step'] is True
        assert result['error'] == 'Provider timeout during LLM call'
        assert result['success'] is False
        assert result['response_type'] == 'error'

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_112_response_finalization(self, mock_rag_log):
        """Test Step 112 properly finalizes the response."""
        from app.orchestrators.response import step_112__end

        ctx = {
            'response': 'Finalized response content',
            'messages': [
                {'role': 'user', 'content': 'Test finalization'},
                {'role': 'assistant', 'content': 'Finalized response content'}
            ],
            'user_id': 'finalization_user',
            'session_id': 'finalization_session',
            'metrics_collected': True,
            'processing_complete': True,
            'request_id': 'test-112-finalization'
        }

        result = await step_112__end(messages=[], ctx=ctx)

        # Verify response finalization
        assert result['response_delivered'] is True
        assert result['final_step'] is True
        assert result['processing_stage'] == 'completed'
        assert result['processing_complete'] is True
        assert 'completion_timestamp' in result