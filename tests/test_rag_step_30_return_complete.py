"""
Tests for RAG Step 30 — Return ChatResponse (RAG.response.return.chatresponse)

Test coverage:
- Unit tests: ChatResponse formatting, response metadata, error handling
- Integration tests: Step 28→30, StreamCheck→30, Step 30→111
- Parity tests: Behavioral definition validation
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

from app.orchestrators.response import step_30__return_complete


class TestStep30ReturnComplete:
    """Unit tests for Step 30 ChatResponse return orchestrator"""

    @pytest.fixture
    def context_from_serve_golden(self) -> Dict[str, Any]:
        """Context from Step 28 (ServeGolden) with golden answer response"""
        return {
            'rag_step': 28,
            'step_id': 'RAG.golden.serve.golden.answer.with.citations',
            'response': {
                'answer': 'The standard VAT rate in Italy is 22%.',
                'citations': [{
                    'source': 'Golden Set FAQ',
                    'faq_id': 'vat_italy_001',
                    'question': 'What is the VAT rate in Italy?',
                    'confidence': 0.95,
                    'updated_at': '2024-01-15T10:30:00Z'
                }]
            },
            'response_metadata': {
                'source': 'golden_set',
                'bypassed_llm': True,
                'confidence': 'high',
                'faq_id': 'vat_italy_001'
            },
            'messages': [
                {'role': 'user', 'content': 'What is the VAT rate in Italy?'},
                {'role': 'assistant', 'content': 'The standard VAT rate in Italy is 22%.'}
            ],
            'request_id': 'golden_req_123',
            'user_id': 'user_456',
            'session_id': 'session_789'
        }

    @pytest.fixture
    def context_from_stream_check(self) -> Dict[str, Any]:
        """Context from StreamCheck (No) with LLM-generated response"""
        return {
            'rag_step': 104,  # StreamCheck step number
            'step_id': 'RAG.response.streaming.requested',
            'streaming_requested': False,
            'processed_messages': [
                {'role': 'user', 'content': 'How do I calculate Italian income tax?'},
                {'role': 'assistant', 'content': 'Italian income tax is calculated using progressive tax brackets. For 2024, the brackets are: 23% up to €15,000, 25% from €15,001 to €28,000, 35% from €28,001 to €50,000, and 43% above €50,000.'}
            ],
            'response': 'Italian income tax is calculated using progressive tax brackets. For 2024, the brackets are: 23% up to €15,000, 25% from €15,001 to €28,000, 35% from €28,001 to €50,000, and 43% above €50,000.',
            'llm_metadata': {
                'provider': 'openai',
                'model': 'gpt-4',
                'cost_eur': 0.045,
                'processing_time_ms': 2800
            },
            'request_id': 'llm_req_456',
            'user_id': 'user_789',
            'session_id': 'session_012'
        }

    @pytest.fixture
    def context_minimal_response(self) -> Dict[str, Any]:
        """Minimal context for testing error handling"""
        return {
            'request_id': 'min_req_789',
            'messages': [
                {'role': 'user', 'content': 'Test question'},
                {'role': 'assistant', 'content': 'Test response'}
            ]
        }

    @pytest.mark.asyncio
    async def test_return_complete_from_serve_golden(self, context_from_serve_golden):
        """Test ChatResponse formatting from ServeGolden path"""

        result = await step_30__return_complete(ctx=context_from_serve_golden)

        # Verify ChatResponse structure
        assert 'chat_response' in result
        chat_response = result['chat_response']

        assert 'messages' in chat_response
        assert 'metadata' in chat_response

        # Verify messages structure
        messages = chat_response['messages']
        assert len(messages) == 2
        assert messages[0]['role'] == 'user'
        assert messages[1]['role'] == 'assistant'
        assert messages[1]['content'] == 'The standard VAT rate in Italy is 22%.'

        # Verify response metadata
        metadata = chat_response['metadata']
        assert metadata['source'] == 'golden_set'
        assert metadata['bypassed_llm'] is True
        assert metadata['confidence'] == 'high'

        # Verify routing
        assert result['next_step'] == 111
        assert result['next_step_id'] == 'RAG.metrics.collect.usage.metrics'
        assert result['route_to'] == 'CollectMetrics'

    @pytest.mark.asyncio
    async def test_return_complete_from_stream_check(self, context_from_stream_check):
        """Test ChatResponse formatting from StreamCheck (No) path"""

        result = await step_30__return_complete(ctx=context_from_stream_check)

        # Verify ChatResponse structure
        assert 'chat_response' in result
        chat_response = result['chat_response']

        # Verify messages
        messages = chat_response['messages']
        assert len(messages) == 2
        assert messages[1]['content'].startswith('Italian income tax is calculated')

        # Verify LLM metadata
        metadata = chat_response['metadata']
        assert metadata['provider'] == 'openai'
        assert metadata['model_used'] == 'gpt-4'
        assert metadata['cost_eur'] == 0.045
        assert metadata['processing_time_ms'] == 2800

        # Verify routing
        assert result['next_step'] == 111
        assert result['route_to'] == 'CollectMetrics'

    @pytest.mark.asyncio
    async def test_context_preservation(self, context_from_serve_golden):
        """Test that all input context is preserved"""

        result = await step_30__return_complete(ctx=context_from_serve_golden)

        # All original context should be preserved
        assert result['request_id'] == context_from_serve_golden['request_id']
        assert result['user_id'] == context_from_serve_golden['user_id']
        assert result['session_id'] == context_from_serve_golden['session_id']
        assert result['response_metadata'] == context_from_serve_golden['response_metadata']

        # New orchestration metadata should be added
        assert 'previous_step' in result
        assert 'chat_response_prepared' in result
        assert 'response_formatting_metadata' in result

    @pytest.mark.asyncio
    async def test_response_validation_and_formatting(self):
        """Test response validation and formatting edge cases"""

        # Test with missing messages
        ctx_no_messages = {'request_id': 'test', 'response': 'Test response'}
        result = await step_30__return_complete(ctx=ctx_no_messages)

        # Should create messages from response
        messages = result['chat_response']['messages']
        assert len(messages) >= 1
        assert any(msg['content'] == 'Test response' for msg in messages)

        # Test with missing response but has messages
        ctx_no_response = {
            'request_id': 'test',
            'messages': [
                {'role': 'user', 'content': 'Question'},
                {'role': 'assistant', 'content': 'Answer from messages'}
            ]
        }
        result = await step_30__return_complete(ctx=ctx_no_response)

        # Should extract response from messages
        messages = result['chat_response']['messages']
        assert any(msg['content'] == 'Answer from messages' for msg in messages)

    @pytest.mark.asyncio
    async def test_missing_context_handling(self, context_minimal_response):
        """Test handling of minimal/missing context data"""

        result = await step_30__return_complete(ctx=context_minimal_response)

        # Should still create valid ChatResponse
        assert 'chat_response' in result
        assert 'messages' in result['chat_response']

        # Should have default metadata
        metadata = result['chat_response']['metadata']
        assert 'source' in metadata
        assert 'formatted_at' in metadata

        # Should route correctly
        assert result['next_step'] == 111

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in ChatResponse formatting"""

        # Test with None context - should create minimal valid response
        result = await step_30__return_complete(ctx=None)

        assert result['chat_response_prepared'] is True
        assert 'chat_response' in result
        assert result['next_step'] == 111  # Still route to CollectMetrics

        # Test with empty context
        result = await step_30__return_complete(ctx={})

        # Should create minimal valid response
        assert 'chat_response' in result
        assert result['next_step'] == 111
        assert result['chat_response_prepared'] is True

    @pytest.mark.asyncio
    async def test_metadata_enhancement(self, context_from_serve_golden):
        """Test metadata enhancement and enrichment"""

        result = await step_30__return_complete(ctx=context_from_serve_golden)

        formatting_metadata = result['response_formatting_metadata']

        # Should include formatting details
        assert 'formatted_at' in formatting_metadata
        assert 'response_type' in formatting_metadata
        assert 'message_count' in formatting_metadata
        assert 'source_step' in formatting_metadata

        # Should preserve original metadata
        chat_metadata = result['chat_response']['metadata']
        assert chat_metadata['source'] == 'golden_set'
        assert chat_metadata['bypassed_llm'] is True


class TestStep30IntegrationFlows:
    """Integration tests for Step 30 with neighboring steps"""

    @pytest.mark.asyncio
    async def test_step_28_to_30_serve_golden_flow(self):
        """Test flow from Step 28 (ServeGolden) to Step 30"""

        # Simulate Step 28 output
        step_28_output = {
            'rag_step': 28,
            'step_id': 'RAG.golden.serve.golden.answer.with.citations',
            'response': {
                'answer': 'Corporate tax rate in Italy is 24% (IRES) plus regional tax.',
                'citations': [{
                    'source': 'Golden Set FAQ',
                    'faq_id': 'corp_tax_italy',
                    'confidence': 0.92
                }]
            },
            'response_metadata': {
                'source': 'golden_set',
                'bypassed_llm': True,
                'confidence': 'high'
            },
            'bypassed_llm': True,
            'request_id': 'golden_flow_test'
        }

        result = await step_30__return_complete(ctx=step_28_output)

        # Verify Step 28 context preserved
        assert result['bypassed_llm'] is True
        assert result['response_metadata']['source'] == 'golden_set'

        # Verify ChatResponse created
        assert 'chat_response' in result
        assert result['chat_response']['messages'][0]['role'] in ['user', 'assistant']

        # Verify routing to Step 111
        assert result['next_step'] == 111
        assert result['previous_step'] == 28

    @pytest.mark.asyncio
    async def test_step_104_to_30_stream_check_flow(self):
        """Test flow from StreamCheck (No) to Step 30"""

        # Simulate StreamCheck (No) output
        stream_check_output = {
            'rag_step': 104,
            'step_id': 'RAG.response.streaming.requested',
            'streaming_requested': False,
            'stream_decision': 'no_streaming',
            'processed_messages': [
                {'role': 'user', 'content': 'What are the deduction limits?'},
                {'role': 'assistant', 'content': 'Italian tax deductions have specific limits based on income brackets and deduction categories.'}
            ],
            'llm_metadata': {
                'provider': 'openai',
                'model': 'gpt-3.5-turbo',
                'tokens_used': 156,
                'cost_eur': 0.012
            },
            'request_id': 'stream_check_flow_test'
        }

        result = await step_30__return_complete(ctx=stream_check_output)

        # Verify StreamCheck context preserved
        assert result['streaming_requested'] is False
        assert result['stream_decision'] == 'no_streaming'

        # Verify ChatResponse formatting
        chat_response = result['chat_response']
        assert len(chat_response['messages']) == 2
        assert chat_response['metadata']['provider'] == 'openai'

        # Verify routing
        assert result['next_step'] == 111
        assert result['previous_step'] == 104

    @pytest.mark.asyncio
    async def test_step_30_to_111_collect_metrics_preparation(self):
        """Test Step 30 prepares data for Step 111 (CollectMetrics)"""

        ctx = {
            'request_id': 'metrics_prep_test',
            'messages': [{'role': 'assistant', 'content': 'Test response'}],
            'user_id': 'user_123',
            'session_id': 'session_456',
            'processing_time_ms': 1500,
            'cost_eur': 0.025
        }

        result = await step_30__return_complete(ctx=ctx)

        # Verify metrics preparation
        assert result['next_step'] == 111
        assert result['next_step_id'] == 'RAG.metrics.collect.usage.metrics'

        # Should preserve metrics-relevant data
        assert result['user_id'] == 'user_123'
        assert result['session_id'] == 'session_456'
        assert result['processing_time_ms'] == 1500
        assert result['cost_eur'] == 0.025

        # Should add response completion metadata
        assert 'response_completion_metadata' in result
        completion_metadata = result['response_completion_metadata']
        assert 'completed_at' in completion_metadata
        assert completion_metadata['response_delivered'] is True


class TestStep30ParityAndBehavior:
    """Parity tests ensuring Step 30 meets behavioral definition of done"""

    @pytest.mark.asyncio
    async def test_behavioral_chat_response_formatting(self):
        """
        BEHAVIORAL TEST: Step 30 must format responses into proper ChatResponse structure
        with messages and metadata according to schema requirements.
        """

        # Test various input formats
        test_contexts = [
            # Golden Set response
            {
                'response': {'answer': 'Golden answer', 'citations': []},
                'messages': [{'role': 'user', 'content': 'Question'}],
                'response_metadata': {'source': 'golden_set'}
            },
            # LLM response
            {
                'processed_messages': [
                    {'role': 'user', 'content': 'Question'},
                    {'role': 'assistant', 'content': 'LLM answer'}
                ],
                'llm_metadata': {'provider': 'openai', 'model': 'gpt-4'}
            }
        ]

        for ctx in test_contexts:
            ctx['request_id'] = 'behavioral_test'
            result = await step_30__return_complete(ctx=ctx)

            # Must create valid ChatResponse structure
            assert 'chat_response' in result
            chat_response = result['chat_response']

            # Must have required fields
            assert 'messages' in chat_response
            assert 'metadata' in chat_response

            # Messages must be properly formatted
            messages = chat_response['messages']
            assert isinstance(messages, list)
            assert len(messages) > 0

            for msg in messages:
                assert 'role' in msg
                assert 'content' in msg
                assert msg['role'] in ['user', 'assistant', 'system']

            # Metadata must be present
            metadata = chat_response['metadata']
            assert isinstance(metadata, dict)

    @pytest.mark.asyncio
    async def test_behavioral_mermaid_flow_compliance(self):
        """
        BEHAVIORAL TEST: Step 30 must comply with Mermaid flow:
        - Receives from ServeGolden (Step 28) OR StreamCheck→No
        - Routes to CollectMetrics (Step 111)
        """

        # From ServeGolden (Step 28)
        from_serve_golden = {
            'rag_step': 28,
            'response': {'answer': 'Golden answer'},
            'request_id': 'mermaid_test_1'
        }
        result = await step_30__return_complete(ctx=from_serve_golden)
        assert result['previous_step'] == 28
        assert result['next_step'] == 111
        assert result['route_to'] == 'CollectMetrics'

        # From StreamCheck (No streaming)
        from_stream_check = {
            'rag_step': 104,
            'streaming_requested': False,
            'processed_messages': [{'role': 'assistant', 'content': 'Answer'}],
            'request_id': 'mermaid_test_2'
        }
        result = await step_30__return_complete(ctx=from_stream_check)
        assert result['previous_step'] == 104
        assert result['next_step'] == 111
        assert result['route_to'] == 'CollectMetrics'

    @pytest.mark.asyncio
    async def test_behavioral_context_preservation(self):
        """
        BEHAVIORAL TEST: Step 30 must preserve all context while adding ChatResponse formatting.
        """

        original_ctx = {
            'rag_step': 28,
            'request_id': 'context_test',
            'user_id': 'user_789',
            'session_id': 'session_012',
            'custom_metadata': {'key': 'value'},
            'messages': [{'role': 'assistant', 'content': 'Test response'}],
            'response_metadata': {'source': 'test', 'confidence': 0.85}
        }

        result = await step_30__return_complete(ctx=original_ctx)

        # All original context must be preserved
        assert result['request_id'] == original_ctx['request_id']
        assert result['user_id'] == original_ctx['user_id']
        assert result['session_id'] == original_ctx['session_id']
        assert result['custom_metadata'] == original_ctx['custom_metadata']
        assert result['response_metadata'] == original_ctx['response_metadata']

        # New ChatResponse formatting must be added
        assert 'chat_response' in result
        assert 'chat_response_prepared' in result
        assert 'response_formatting_metadata' in result
        assert 'next_step' in result

    @pytest.mark.asyncio
    async def test_behavioral_structured_observability(self):
        """
        BEHAVIORAL TEST: Step 30 must implement structured observability
        with rag_step_log and rag_step_timer per MASTER_GUARDRAILS.
        """

        with patch('app.orchestrators.response.rag_step_log') as mock_log, \
             patch('app.orchestrators.response.rag_step_timer') as mock_timer:

            ctx = {
                'request_id': 'observability_test',
                'messages': [{'role': 'assistant', 'content': 'Test'}]
            }

            result = await step_30__return_complete(ctx=ctx)

            # Verify structured logging
            mock_log.assert_called()
            log_calls = mock_log.call_args_list

            # Check required log attributes
            start_log = log_calls[0][1]  # kwargs from first call
            assert start_log['step'] == 30
            assert start_log['step_id'] == 'RAG.response.return.chatresponse'
            assert start_log['node_label'] == 'ReturnComplete'
            assert start_log['category'] == 'response'
            assert start_log['type'] == 'process'

            # Verify timing
            mock_timer.assert_called_with(
                30,
                'RAG.response.return.chatresponse',
                'ReturnComplete',
                request_id='observability_test',
                stage="start"
            )

    @pytest.mark.asyncio
    async def test_behavioral_response_delivery_validation(self):
        """
        BEHAVIORAL TEST: Step 30 must validate response delivery requirements
        and handle various response formats consistently.
        """

        test_cases = [
            # Golden Set response
            {
                'input': {
                    'response': {'answer': 'Golden answer'},
                    'response_metadata': {'source': 'golden_set'},
                    'messages': [{'role': 'user', 'content': 'Q'}]
                },
                'expected_source': 'golden_set'
            },
            # LLM response
            {
                'input': {
                    'processed_messages': [
                        {'role': 'assistant', 'content': 'LLM answer'}
                    ],
                    'llm_metadata': {'provider': 'openai'}
                },
                'expected_source': 'llm'
            },
            # Cached response
            {
                'input': {
                    'cached_response': True,
                    'messages': [{'role': 'assistant', 'content': 'Cached'}],
                    'response_metadata': {'source': 'cache'}
                },
                'expected_source': 'cache'
            }
        ]

        for case in test_cases:
            case['input']['request_id'] = 'validation_test'
            result = await step_30__return_complete(ctx=case['input'])

            # Must create consistent ChatResponse structure
            assert 'chat_response' in result
            assert 'messages' in result['chat_response']
            assert 'metadata' in result['chat_response']

            # Must preserve response source information
            assert result['response_formatting_metadata']['response_type'] == 'chat_response'
            assert result['chat_response_prepared'] is True

            # Must route consistently
            assert result['next_step'] == 111