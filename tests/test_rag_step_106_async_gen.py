"""
Tests for RAG Step 106: AsyncGen (Create async generator).

This process step creates an async generator for streaming response delivery,
taking streaming setup data from Step 105 and preparing for Step 107.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from typing import AsyncGenerator


class TestRAGStep106AsyncGen:
    """Unit tests for Step 106: AsyncGen."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_106_creates_async_generator(self, mock_rag_log):
        """Test Step 106: Creates async generator for streaming response."""
        from app.orchestrators.platform import step_106__async_gen

        ctx = {
            'stream_context': {
                'messages': [
                    {'role': 'user', 'content': 'Test streaming query'},
                    {'role': 'assistant', 'content': 'Test streaming response'}
                ],
                'session_id': 'test_session_123',
                'user_id': 'user_456',
                'provider': 'openai',
                'model': 'gpt-4',
                'streaming_enabled': True,
                'chunk_size': 1024,
                'include_usage': True,
                'include_metadata': True
            },
            'sse_headers': {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            },
            'processed_messages': [
                {'role': 'user', 'content': 'Test streaming query'},
                {'role': 'assistant', 'content': 'Test streaming response'}
            ],
            'streaming_requested': True,
            'request_id': 'test-106-generator'
        }

        result = await step_106__async_gen(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert 'async_generator' in result
        assert result['generator_created'] is True
        assert result['next_step'] == 'single_pass_stream'
        assert 'generator_config' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_106_configures_generator_settings(self, mock_rag_log):
        """Test Step 106: Configures async generator with proper settings."""
        from app.orchestrators.platform import step_106__async_gen

        ctx = {
            'stream_context': {
                'messages': [{'role': 'user', 'content': 'Test'}],
                'session_id': 'session_123',
                'provider': 'anthropic',
                'model': 'claude-3-sonnet',
                'chunk_size': 2048,
                'include_usage': False,
                'include_metadata': True,
                'heartbeat_interval': 30,
                'connection_timeout': 300
            },
            'streaming_requested': True,
            'request_id': 'test-106-config'
        }

        result = await step_106__async_gen(messages=[], ctx=ctx)

        generator_config = result['generator_config']
        assert generator_config['provider'] == 'anthropic'
        assert generator_config['model'] == 'claude-3-sonnet'
        assert generator_config['chunk_size'] == 2048
        assert generator_config['include_usage'] is False
        assert generator_config['include_metadata'] is True
        assert generator_config['heartbeat_interval'] == 30

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_106_handles_complex_messages(self, mock_rag_log):
        """Test Step 106: Handles complex message structures for generator."""
        from app.orchestrators.platform import step_106__async_gen

        complex_messages = [
            {'role': 'system', 'content': 'You are an Italian tax assistant.'},
            {'role': 'user', 'content': 'What are the current tax rates for businesses?'},
            {'role': 'assistant', 'content': 'Current Italian business tax rates include...', 'metadata': {'sources': ['tax_law_2024.pdf']}}
        ]

        ctx = {
            'stream_context': {
                'messages': complex_messages,
                'session_id': 'session_complex',
                'provider': 'openai',
                'model': 'gpt-4-turbo'
            },
            'processed_messages': complex_messages,
            'response_metadata': {
                'total_tokens': 500,
                'completion_tokens': 350
            },
            'request_id': 'test-106-complex'
        }

        result = await step_106__async_gen(messages=[], ctx=ctx)

        assert result['async_generator'] is not None
        assert len(result['generator_config']['messages']) == 3
        assert result['generator_config']['messages'][0]['role'] == 'system'
        assert 'response_metadata' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_106_preserves_all_context_data(self, mock_rag_log):
        """Test Step 106: Preserves all context data for downstream processing."""
        from app.orchestrators.platform import step_106__async_gen

        original_ctx = {
            'stream_context': {
                'messages': [{'role': 'user', 'content': 'Test'}],
                'session_id': 'session_preserve',
                'user_id': 'user_preserve',
                'streaming_enabled': True
            },
            'sse_headers': {'Content-Type': 'text/event-stream'},
            'user_data': {'id': 'user_123', 'preferences': {'language': 'it'}},
            'session_data': {'id': 'session_456', 'created_at': '2024-01-01'},
            'response_metadata': {
                'provider': 'anthropic',
                'model': 'claude-3',
                'tokens_used': 200
            },
            'processing_history': ['stream_check', 'stream_setup'],
            'request_id': 'test-106-preserve'
        }

        result = await step_106__async_gen(messages=[], ctx=original_ctx.copy())

        # Verify all original context is preserved
        assert result['user_data'] == original_ctx['user_data']
        assert result['session_data'] == original_ctx['session_data']
        assert result['response_metadata'] == original_ctx['response_metadata']
        assert result['processing_history'] == original_ctx['processing_history']
        assert result['sse_headers'] == original_ctx['sse_headers']

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_106_adds_generator_metadata(self, mock_rag_log):
        """Test Step 106: Adds async generator creation metadata."""
        from app.orchestrators.platform import step_106__async_gen

        ctx = {
            'stream_context': {
                'messages': [{'role': 'user', 'content': 'Test'}],
                'session_id': 'test_session'
            },
            'streaming_requested': True,
            'request_id': 'test-106-metadata'
        }

        result = await step_106__async_gen(messages=[], ctx=ctx)

        assert result['processing_stage'] == 'async_generator_created'
        assert result['next_step'] == 'single_pass_stream'
        assert result['generator_created'] is True
        assert 'generator_timestamp' in result

        # Verify timestamp format
        timestamp = result['generator_timestamp']
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))  # Should not raise

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_106_configures_streaming_parameters(self, mock_rag_log):
        """Test Step 106: Configures streaming parameters from context."""
        from app.orchestrators.platform import step_106__async_gen

        ctx = {
            'stream_context': {
                'messages': [{'role': 'user', 'content': 'Test'}],
                'session_id': 'test_session',
                'chunk_size': 512,
                'include_usage': True,
                'include_metadata': False,
                'heartbeat_interval': 45,
                'connection_timeout': 600
            },
            'streaming_configuration': {
                'media_type': 'text/event-stream',
                'compression': True
            },
            'request_id': 'test-106-streaming'
        }

        result = await step_106__async_gen(messages=[], ctx=ctx)

        config = result['generator_config']
        assert config['chunk_size'] == 512
        assert config['include_usage'] is True
        assert config['include_metadata'] is False
        assert config['heartbeat_interval'] == 45
        assert config['connection_timeout'] == 600
        assert 'streaming_configuration' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_106_handles_custom_streaming_options(self, mock_rag_log):
        """Test Step 106: Handles custom streaming options and configurations."""
        from app.orchestrators.platform import step_106__async_gen

        ctx = {
            'stream_context': {
                'messages': [{'role': 'user', 'content': 'Custom stream test'}],
                'session_id': 'custom_session',
                'custom_headers': {'X-Stream-ID': 'custom_123'},
                'compression_enabled': True,
                'buffer_size': 4096
            },
            'streaming_options': {
                'format': 'sse',
                'flush_immediately': True,
                'error_handling': 'graceful'
            },
            'request_id': 'test-106-custom'
        }

        result = await step_106__async_gen(messages=[], ctx=ctx)

        assert result['async_generator'] is not None
        assert result['generator_config']['compression_enabled'] is True
        assert result['generator_config']['buffer_size'] == 4096
        assert 'streaming_options' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_106_validates_streaming_requirements(self, mock_rag_log):
        """Test Step 106: Validates streaming requirements and adds warnings."""
        from app.orchestrators.platform import step_106__async_gen

        ctx = {
            'stream_context': {
                'messages': [],  # Empty messages
                'session_id': None,  # Missing session ID
                'streaming_enabled': False  # Streaming not enabled
            },
            'streaming_requested': False,  # Inconsistent streaming request
            'request_id': 'test-106-validation'
        }

        result = await step_106__async_gen(messages=[], ctx=ctx)

        assert 'validation_warnings' in result
        warnings = result['validation_warnings']
        assert len(warnings) > 0
        assert any('No messages available' in warning for warning in warnings)
        assert any('session ID' in warning for warning in warnings)

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_106_handles_provider_specific_config(self, mock_rag_log):
        """Test Step 106: Handles provider-specific generator configurations."""
        from app.orchestrators.platform import step_106__async_gen

        providers_config = [
            ('openai', 'gpt-4', {'temperature': 0.7, 'max_tokens': 2000}),
            ('anthropic', 'claude-3-sonnet', {'temperature': 0.8, 'max_tokens': 1500}),
            ('azure', 'gpt-4-32k', {'temperature': 0.6, 'max_tokens': 3000})
        ]

        for provider, model, config in providers_config:
            ctx = {
                'stream_context': {
                    'messages': [{'role': 'user', 'content': f'Test {provider}'}],
                    'session_id': f'{provider}_session',
                    'provider': provider,
                    'model': model,
                    'provider_config': config
                },
                'request_id': f'test-106-{provider}'
            }

            result = await step_106__async_gen(messages=[], ctx=ctx)

            gen_config = result['generator_config']
            assert gen_config['provider'] == provider
            assert gen_config['model'] == model
            assert gen_config['provider_config'] == config

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_106_logs_generator_creation(self, mock_rag_log):
        """Test Step 106: Logs async generator creation for observability."""
        from app.orchestrators.platform import step_106__async_gen

        ctx = {
            'stream_context': {
                'messages': [{'role': 'user', 'content': 'Log test'}],
                'session_id': 'log_session',
                'provider': 'openai',
                'model': 'gpt-4'
            },
            'streaming_metrics': {
                'setup_duration_ms': 15,
                'headers_configured': 6
            },
            'request_id': 'test-106-logging'
        }

        await step_106__async_gen(messages=[], ctx=ctx)

        # Verify structured logging
        assert mock_rag_log.call_count >= 2

        # Find the completion log call
        completion_call = None
        for call in mock_rag_log.call_args_list:
            if call[1].get('processing_stage') == 'completed':
                completion_call = call[1]
                break

        assert completion_call is not None
        assert completion_call['step'] == 106
        assert completion_call['generator_created'] is True
        assert completion_call['next_step'] == 'single_pass_stream'


class TestRAGStep106Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_106_parity_generator_creation_behavior(self):
        """Test Step 106 parity: Async generator creation behavior unchanged."""
        from app.orchestrators.platform import step_106__async_gen

        test_cases = [
            {
                'stream_context': {
                    'messages': [{'role': 'user', 'content': 'Test 1'}],
                    'session_id': 'session_1',
                    'streaming_enabled': True
                },
                'expected_generator': True,
                'expected_next': 'single_pass_stream'
            },
            {
                'stream_context': {
                    'messages': [{'role': 'user', 'content': 'Test 2'}],
                    'session_id': 'session_2',
                    'provider': 'anthropic',
                    'model': 'claude-3'
                },
                'expected_generator': True,
                'expected_next': 'single_pass_stream'
            },
            {
                'stream_context': {
                    'messages': [{'role': 'user', 'content': 'Complex test'}],
                    'session_id': 'session_3',
                    'chunk_size': 2048,
                    'include_metadata': False
                },
                'expected_generator': True,
                'expected_next': 'single_pass_stream'
            }
        ]

        for test_case in test_cases:
            ctx = {
                **test_case,
                'request_id': f"parity-{hash(str(test_case))}"
            }
            # Remove expected values from context
            ctx.pop('expected_generator', None)
            ctx.pop('expected_next', None)

            with patch('app.orchestrators.platform.rag_step_log'):
                result = await step_106__async_gen(messages=[], ctx=ctx)

            assert result['generator_created'] == test_case['expected_generator']
            assert result['next_step'] == test_case['expected_next']
            assert result['processing_stage'] == 'async_generator_created'


class TestRAGStep106Integration:
    """Integration tests for Step 106 with neighbors."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_stream_setup_to_106_integration(self, mock_setup_log):
        """Test StreamSetup → Step 106 integration."""

        # Simulate incoming from StreamSetup (Step 105)
        stream_setup_ctx = {
            'sse_headers': {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*'
            },
            'stream_context': {
                'messages': [
                    {'role': 'user', 'content': 'Integration test query'},
                    {'role': 'assistant', 'content': 'Integration test response'}
                ],
                'session_id': 'integration_session_106',
                'user_id': 'integration_user',
                'provider': 'openai',
                'model': 'gpt-4',
                'streaming_enabled': True,
                'chunk_size': 1024,
                'include_usage': True
            },
            'streaming_setup': 'configured',
            'processing_stage': 'streaming_setup',
            'next_step': 'create_async_generator',
            'request_id': 'integration-setup-106'
        }

        from app.orchestrators.platform import step_106__async_gen

        result = await step_106__async_gen(messages=[], ctx=stream_setup_ctx)

        assert result['streaming_setup'] == 'configured'
        assert result['generator_created'] is True
        assert result['next_step'] == 'single_pass_stream'
        assert 'sse_headers' in result
        assert 'stream_context' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_106_prepares_for_single_pass(self, mock_rag_log):
        """Test Step 106 prepares data for SinglePassStream (Step 107)."""
        from app.orchestrators.platform import step_106__async_gen

        ctx = {
            'stream_context': {
                'messages': [
                    {'role': 'user', 'content': 'User query for single pass'},
                    {'role': 'assistant', 'content': 'Assistant response for single pass'}
                ],
                'session_id': 'single_pass_session',
                'streaming_enabled': True
            },
            'generator_settings': {
                'prevent_double_iteration': True,
                'stream_guard_enabled': True
            },
            'request_id': 'test-106-prep-single-pass'
        }

        result = await step_106__async_gen(messages=[], ctx=ctx)

        # Verify data prepared for SinglePassStream step
        assert result['next_step'] == 'single_pass_stream'
        assert result['generator_created'] is True
        assert 'async_generator' in result
        assert result['async_generator'] is not None
        assert 'generator_settings' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_106_error_handling(self, mock_rag_log):
        """Test Step 106 error handling and recovery."""
        from app.orchestrators.platform import step_106__async_gen

        # Test with minimal/invalid context
        minimal_ctx = {
            'request_id': 'test-106-error-handling'
        }

        result = await step_106__async_gen(messages=[], ctx=minimal_ctx)

        # Should handle gracefully with warnings
        assert 'validation_warnings' in result
        assert result['generator_created'] is True  # Should still create generator
        assert 'async_generator' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_106_streaming_flow_integration(self, mock_rag_log):
        """Test Step 106 integration with full streaming flow."""
        from app.orchestrators.platform import step_106__async_gen

        # Simulate full streaming context from previous steps
        full_streaming_ctx = {
            # From StreamCheck (Step 104)
            'streaming_requested': True,
            'decision': 'yes',
            'decision_source': 'stream_parameter',
            'stream_configuration': {
                'media_type': 'text/event-stream',
                'chunk_size': 1024,
                'include_usage': False,
                'include_metadata': True
            },
            # From StreamSetup (Step 105)
            'sse_headers': {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            },
            'stream_context': {
                'messages': [
                    {'role': 'user', 'content': 'Full flow integration test'},
                    {'role': 'assistant', 'content': 'Full flow response'}
                ],
                'session_id': 'full_flow_session',
                'user_id': 'full_flow_user',
                'provider': 'anthropic',
                'model': 'claude-3-sonnet',
                'streaming_enabled': True
            },
            'streaming_setup': 'configured',
            'processing_stage': 'streaming_setup',
            'request_id': 'integration-full-flow-106'
        }

        result = await step_106__async_gen(messages=[], ctx=full_streaming_ctx)

        # Verify integration with full flow
        assert result['streaming_requested'] is True
        assert result['streaming_setup'] == 'configured'
        assert result['generator_created'] is True
        assert result['next_step'] == 'single_pass_stream'
        assert 'async_generator' in result
        assert result['processing_stage'] == 'async_generator_created'