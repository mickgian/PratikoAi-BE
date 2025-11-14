"""
Tests for RAG Step 101: FinalResponse (Return to chat node for final response).

This step serves as a convergence point where all LLM response paths merge to return
control to the chat processing pipeline for final formatting and delivery.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone


class TestRAGStep101FinalResponse:
    """Unit tests for Step 101: FinalResponse."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_101_routes_tool_results_to_processing(self, mock_rag_log):
        """Test Step 101: Routes tool results to message processing."""
        from app.orchestrators.response import step_101__final_response

        ctx = {
            'messages': [
                {'role': 'user', 'content': 'Test query'},
                {'role': 'assistant', 'content': 'Response with tool results', 'tool_calls': []}
            ],
            'response_source': 'tool_results',
            'tool_results': [
                {
                    'tool_name': 'KnowledgeSearchTool',
                    'result': 'Found relevant knowledge'
                }
            ],
            'request_id': 'test-101-tool-results'
        }

        result = await step_101__final_response(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert result['next_step'] == 'process_messages'
        assert result['response_source'] == 'tool_results'
        assert 'tool_results' in result
        assert result['processing_stage'] == 'final_response'

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_101_routes_simple_ai_message(self, mock_rag_log):
        """Test Step 101: Routes simple AI message to processing."""
        from app.orchestrators.response import step_101__final_response

        ctx = {
            'messages': [
                {'role': 'user', 'content': 'Simple question'},
                {'role': 'assistant', 'content': 'Simple answer without tools'}
            ],
            'response_source': 'simple_ai_message',
            'ai_message': {
                'role': 'assistant',
                'content': 'Simple answer without tools'
            },
            'request_id': 'test-101-simple'
        }

        result = await step_101__final_response(messages=[], ctx=ctx)

        assert result['next_step'] == 'process_messages'
        assert result['response_source'] == 'simple_ai_message'
        assert 'ai_message' in result
        assert result['processing_stage'] == 'final_response'

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_101_routes_tool_error(self, mock_rag_log):
        """Test Step 101: Routes tool error to processing."""
        from app.orchestrators.response import step_101__final_response

        ctx = {
            'messages': [
                {'role': 'user', 'content': 'Query with invalid attachment'},
            ],
            'response_source': 'tool_error',
            'tool_error': {
                'error_type': 'invalid_file',
                'message': 'File format not supported',
                'details': {'file_type': 'unsupported'}
            },
            'request_id': 'test-101-tool-error'
        }

        result = await step_101__final_response(messages=[], ctx=ctx)

        assert result['next_step'] == 'process_messages'
        assert result['response_source'] == 'tool_error'
        assert 'tool_error' in result
        assert result['processing_stage'] == 'final_response'

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_101_preserves_conversation_context(self, mock_rag_log):
        """Test Step 101: Preserves full conversation context."""
        from app.orchestrators.response import step_101__final_response

        ctx = {
            'messages': [
                {'role': 'user', 'content': 'First message'},
                {'role': 'assistant', 'content': 'First response'},
                {'role': 'user', 'content': 'Follow-up question'},
                {'role': 'assistant', 'content': 'Follow-up response with context'}
            ],
            'response_source': 'simple_ai_message',
            'conversation_metadata': {
                'turn_count': 2,
                'context_length': 1024,
                'domain_classification': 'tax'
            },
            'request_id': 'test-101-context'
        }

        result = await step_101__final_response(messages=[], ctx=ctx)

        assert len(result['messages']) == 4
        assert result['conversation_metadata']['turn_count'] == 2
        assert result['conversation_metadata']['domain_classification'] == 'tax'

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_101_handles_cached_response_routing(self, mock_rag_log):
        """Test Step 101: Handles cached response routing."""
        from app.orchestrators.response import step_101__final_response

        ctx = {
            'messages': [
                {'role': 'user', 'content': 'Cached query'},
                {'role': 'assistant', 'content': 'Cached response'}
            ],
            'response_source': 'cached',
            'cached_metadata': {
                'cache_hit': True,
                'cache_key': 'query_sig_123',
                'cached_at': '2025-01-15T10:00:00Z'
            },
            'request_id': 'test-101-cached'
        }

        result = await step_101__final_response(messages=[], ctx=ctx)

        assert result['response_source'] == 'cached'
        assert result['cached_metadata']['cache_hit'] is True
        assert result['next_step'] == 'process_messages'

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_101_preserves_all_context_data(self, mock_rag_log):
        """Test Step 101: Preserves all context data for downstream processing."""
        from app.orchestrators.response import step_101__final_response

        original_ctx = {
            'messages': [{'role': 'user', 'content': 'Test'}],
            'response_source': 'tool_results',
            'user_data': {'id': 'user_123'},
            'session_data': {'id': 'session_456'},
            'domain_classification': {'domain': 'tax', 'confidence': 0.95},
            'usage_tracking': {'tokens_used': 150, 'cost': 0.001},
            'request_metadata': {
                'request_id': 'req_789',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_agent': 'test-client'
            }
        }

        result = await step_101__final_response(messages=[], ctx=original_ctx.copy())

        # Verify all original context is preserved
        assert result['user_data'] == original_ctx['user_data']
        assert result['session_data'] == original_ctx['session_data']
        assert result['domain_classification'] == original_ctx['domain_classification']
        assert result['usage_tracking'] == original_ctx['usage_tracking']
        assert result['request_metadata'] == original_ctx['request_metadata']

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_101_adds_final_response_metadata(self, mock_rag_log):
        """Test Step 101: Adds final response stage metadata."""
        from app.orchestrators.response import step_101__final_response

        ctx = {
            'messages': [{'role': 'user', 'content': 'Test query'}],
            'response_source': 'simple_ai_message',
            'request_id': 'test-101-metadata'
        }

        result = await step_101__final_response(messages=[], ctx=ctx)

        assert result['processing_stage'] == 'final_response'
        assert result['next_step'] == 'process_messages'
        assert 'final_response_timestamp' in result

        # Verify timestamp format
        timestamp = result['final_response_timestamp']
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))  # Should not raise

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_101_logs_convergence_details(self, mock_rag_log):
        """Test Step 101: Logs convergence point details for observability."""
        from app.orchestrators.response import step_101__final_response

        ctx = {
            'messages': [{'role': 'user', 'content': 'Test query'}],
            'response_source': 'tool_results',
            'tool_results': [{'tool': 'KnowledgeSearchTool'}],
            'response_path': ['tool_execution', 'tool_results', 'final_response'],
            'request_id': 'test-101-logging'
        }

        await step_101__final_response(messages=[], ctx=ctx)

        # Verify structured logging
        assert mock_rag_log.call_count >= 2

        # Find the completion log call
        completion_call = None
        for call in mock_rag_log.call_args_list:
            if call[1].get('processing_stage') == 'completed':
                completion_call = call[1]
                break

        assert completion_call is not None
        assert completion_call['step'] == 101
        assert completion_call['response_source'] == 'tool_results'
        assert 'convergence_point' in completion_call or 'processing_stage' in completion_call

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_101_handles_empty_messages(self, mock_rag_log):
        """Test Step 101: Handles empty messages gracefully."""
        from app.orchestrators.response import step_101__final_response

        ctx = {
            'messages': [],
            'response_source': 'empty_conversation',
            'request_id': 'test-101-empty'
        }

        result = await step_101__final_response(messages=[], ctx=ctx)

        assert result['messages'] == []
        assert result['next_step'] == 'process_messages'
        assert result['processing_stage'] == 'final_response'


class TestRAGStep101Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_101_parity_convergence_behavior(self):
        """Test Step 101 parity: Convergence behavior unchanged."""
        from app.orchestrators.response import step_101__final_response

        test_cases = [
            {
                'response_source': 'tool_results',
                'tool_results': [{'tool': 'KnowledgeSearchTool', 'result': 'Data'}],
                'expected_next': 'process_messages'
            },
            {
                'response_source': 'simple_ai_message',
                'ai_message': {'role': 'assistant', 'content': 'Simple response'},
                'expected_next': 'process_messages'
            },
            {
                'response_source': 'tool_error',
                'tool_error': {'error_type': 'validation', 'message': 'Error occurred'},
                'expected_next': 'process_messages'
            }
        ]

        for test_case in test_cases:
            ctx = {
                'messages': [{'role': 'user', 'content': 'Test'}],
                **test_case,
                'request_id': f"parity-{test_case['response_source']}"
            }

            with patch('app.orchestrators.response.rag_step_log'):
                result = await step_101__final_response(messages=[], ctx=ctx)

            assert result['next_step'] == test_case['expected_next']
            assert result['response_source'] == test_case['response_source']
            assert result['processing_stage'] == 'final_response'


class TestRAGStep101Integration:
    """Integration tests for Step 101 with neighbors."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_tool_results_to_101_integration(self, mock_tool_log):
        """Test ToolResults → Step 101 integration."""

        # Simulate incoming from ToolResults (Steps 99, 80-83)
        tool_results_ctx = {
            'messages': [{'role': 'user', 'content': 'Search knowledge base'}],
            'tool_execution_results': [
                {
                    'tool_name': 'KnowledgeSearchTool',
                    'status': 'success',
                    'result': 'Found 3 relevant documents about Italian tax regulations'
                }
            ],
            'response_source': 'tool_results',
            'processing_path': ['tool_execution', 'knowledge_search', 'tool_results'],
            'request_id': 'integration-tool-results-101'
        }

        from app.orchestrators.response import step_101__final_response

        result = await step_101__final_response(messages=[], ctx=tool_results_ctx)

        assert result['response_source'] == 'tool_results'
        assert result['next_step'] == 'process_messages'
        assert 'tool_execution_results' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_simple_ai_msg_to_101_integration(self, mock_simple_log):
        """Test SimpleAIMsg → Step 101 integration."""

        # Simulate incoming from SimpleAIMsg (Step 77)
        simple_ai_ctx = {
            'messages': [
                {'role': 'user', 'content': 'Simple question'},
                {'role': 'assistant', 'content': 'Direct AI response without tools'}
            ],
            'response_source': 'simple_ai_message',
            'ai_message_metadata': {
                'provider': 'openai',
                'model': 'gpt-4',
                'tokens_used': 85
            },
            'processing_path': ['llm_call', 'simple_ai_message'],
            'request_id': 'integration-simple-101'
        }

        from app.orchestrators.response import step_101__final_response

        result = await step_101__final_response(messages=[], ctx=simple_ai_ctx)

        assert result['response_source'] == 'simple_ai_message'
        assert result['next_step'] == 'process_messages'
        assert 'ai_message_metadata' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_101_prepares_for_process_messages(self, mock_rag_log):
        """Test Step 101 prepares data for ProcessMessages (Step 102)."""
        from app.orchestrators.response import step_101__final_response

        ctx = {
            'messages': [
                {'role': 'user', 'content': 'User query'},
                {'role': 'assistant', 'content': 'Assistant response'}
            ],
            'response_source': 'tool_results',
            'final_processing_needed': True,
            'format_requirements': {
                'include_metadata': True,
                'include_citations': True
            },
            'request_id': 'test-101-prep'
        }

        result = await step_101__final_response(messages=[], ctx=ctx)

        # Verify data prepared for ProcessMessages step
        assert result['next_step'] == 'process_messages'
        assert result['processing_stage'] == 'final_response'
        assert 'final_processing_needed' in result
        assert 'format_requirements' in result
        assert len(result['messages']) == 2