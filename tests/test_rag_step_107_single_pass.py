"""
Tests for RAG Step 107: SinglePass (SinglePassStream Prevent double iteration).

This process step wraps async generators with SinglePassStream to prevent double iteration,
taking generator data from Step 106 and preparing for Step 108.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from typing import AsyncGenerator


class TestRAGStep107SinglePass:
    """Unit tests for Step 107: SinglePass."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_107_wraps_with_single_pass_stream(self, mock_rag_log):
        """Test Step 107: Wraps async generator with SinglePassStream."""
        from app.orchestrators.preflight import step_107__single_pass

        async def test_generator():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"

        ctx = {
            'async_generator': test_generator(),
            'generator_config': {
                'session_id': 'test_session_123',
                'user_id': 'user_456',
                'provider': 'openai',
                'model': 'gpt-4',
                'streaming_enabled': True,
                'chunk_size': 1024
            },
            'generator_created': True,
            'request_id': 'test-107-single-pass'
        }

        result = await step_107__single_pass(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert 'wrapped_stream' in result
        assert result['stream_protected'] is True
        assert result['next_step'] == 'write_sse'
        assert 'protection_config' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_107_configures_stream_protection(self, mock_rag_log):
        """Test Step 107: Configures stream protection settings."""
        from app.orchestrators.preflight import step_107__single_pass

        async def test_generator():
            yield "test content"

        ctx = {
            'async_generator': test_generator(),
            'generator_config': {
                'session_id': 'session_123',
                'provider': 'anthropic',
                'model': 'claude-3-sonnet',
                'include_metadata': True,
                'error_handling': 'graceful'
            },
            'streaming_setup': 'configured',
            'request_id': 'test-107-config'
        }

        result = await step_107__single_pass(messages=[], ctx=ctx)

        protection_config = result['protection_config']
        assert protection_config['double_iteration_prevention'] is True
        assert protection_config['session_id'] == 'session_123'
        assert protection_config['provider'] == 'anthropic'
        assert protection_config['model'] == 'claude-3-sonnet'
        assert protection_config['error_handling'] == 'graceful'

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_107_handles_complex_generators(self, mock_rag_log):
        """Test Step 107: Handles complex async generators with metadata."""
        from app.orchestrators.preflight import step_107__single_pass

        async def complex_generator():
            yield {"type": "chunk", "content": "chunk1", "metadata": {"tokens": 10}}
            yield {"type": "chunk", "content": "chunk2", "metadata": {"tokens": 15}}
            yield {"type": "done", "content": "[DONE]", "metadata": {"total_tokens": 25}}

        ctx = {
            'async_generator': complex_generator(),
            'generator_config': {
                'session_id': 'complex_session',
                'streaming_enabled': True,
                'include_metadata': True,
                'include_usage': True
            },
            'generator_created': True,
            'response_metadata': {
                'provider': 'openai',
                'model': 'gpt-4-turbo',
                'estimated_tokens': 100
            },
            'request_id': 'test-107-complex'
        }

        result = await step_107__single_pass(messages=[], ctx=ctx)

        assert result['wrapped_stream'] is not None
        assert result['stream_protected'] is True
        assert 'response_metadata' in result
        assert result['protection_config']['include_metadata'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_107_preserves_all_context_data(self, mock_rag_log):
        """Test Step 107: Preserves all context data for downstream processing."""
        from app.orchestrators.preflight import step_107__single_pass

        async def test_generator():
            yield "preserved context test"

        original_ctx = {
            'async_generator': test_generator(),
            'generator_config': {'session_id': 'preserve_session'},
            'user_data': {'id': 'user_123', 'preferences': {'language': 'it'}},
            'session_data': {'id': 'session_456', 'created_at': '2024-01-01'},
            'response_metadata': {
                'provider': 'anthropic',
                'model': 'claude-3',
                'tokens_used': 200
            },
            'processing_history': ['stream_check', 'stream_setup', 'async_gen'],
            'sse_headers': {'Content-Type': 'text/event-stream'},
            'request_id': 'test-107-preserve'
        }

        result = await step_107__single_pass(messages=[], ctx=original_ctx.copy())

        # Verify all original context is preserved
        assert result['user_data'] == original_ctx['user_data']
        assert result['session_data'] == original_ctx['session_data']
        assert result['response_metadata'] == original_ctx['response_metadata']
        assert result['processing_history'] == original_ctx['processing_history']
        assert result['sse_headers'] == original_ctx['sse_headers']
        assert result['generator_config'] == original_ctx['generator_config']

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_107_adds_protection_metadata(self, mock_rag_log):
        """Test Step 107: Adds stream protection metadata."""
        from app.orchestrators.preflight import step_107__single_pass

        async def test_generator():
            yield "metadata test"

        ctx = {
            'async_generator': test_generator(),
            'generator_config': {'session_id': 'test_session'},
            'generator_created': True,
            'request_id': 'test-107-metadata'
        }

        result = await step_107__single_pass(messages=[], ctx=ctx)

        assert result['processing_stage'] == 'stream_protected'
        assert result['next_step'] == 'write_sse'
        assert result['stream_protected'] is True
        assert 'protection_timestamp' in result

        # Verify timestamp format
        timestamp = result['protection_timestamp']
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))  # Should not raise

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_107_validates_stream_requirements(self, mock_rag_log):
        """Test Step 107: Validates stream requirements and adds warnings."""
        from app.orchestrators.preflight import step_107__single_pass

        # Test with missing/invalid generator
        ctx = {
            'async_generator': None,  # Missing generator
            'generator_config': {},  # Empty config
            'generator_created': False,  # Not created
            'request_id': 'test-107-validation'
        }

        result = await step_107__single_pass(messages=[], ctx=ctx)

        assert 'validation_warnings' in result
        warnings = result['validation_warnings']
        assert len(warnings) > 0
        assert any('No async generator available' in warning for warning in warnings)
        assert any('generator not created' in warning for warning in warnings)

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_107_configures_protection_settings(self, mock_rag_log):
        """Test Step 107: Configures stream protection settings."""
        from app.orchestrators.preflight import step_107__single_pass

        async def test_generator():
            yield "protection settings test"

        ctx = {
            'async_generator': test_generator(),
            'generator_config': {
                'session_id': 'protection_session',
                'protection_enabled': True,
                'error_recovery': True,
                'iteration_limit': 1
            },
            'stream_protection_config': {
                'prevent_double_iteration': True,
                'runtime_error_message': 'Custom error message'
            },
            'request_id': 'test-107-protection'
        }

        result = await step_107__single_pass(messages=[], ctx=ctx)

        config = result['protection_config']
        assert config['double_iteration_prevention'] is True
        assert config['error_recovery'] is True
        assert config['iteration_limit'] == 1
        assert 'stream_protection_config' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_107_handles_generator_errors(self, mock_rag_log):
        """Test Step 107: Handles generator errors gracefully."""
        from app.orchestrators.preflight import step_107__single_pass

        async def error_generator():
            yield "chunk1"
            raise Exception("Generator error")

        ctx = {
            'async_generator': error_generator(),
            'generator_config': {
                'session_id': 'error_session',
                'error_handling': 'graceful'
            },
            'error_recovery_enabled': True,
            'request_id': 'test-107-errors'
        }

        result = await step_107__single_pass(messages=[], ctx=ctx)

        assert result['wrapped_stream'] is not None
        assert result['stream_protected'] is True
        assert result['protection_config']['error_handling'] == 'graceful'

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_107_handles_streaming_options(self, mock_rag_log):
        """Test Step 107: Handles various streaming options and configurations."""
        from app.orchestrators.preflight import step_107__single_pass

        async def options_generator():
            yield "streaming options test"

        ctx = {
            'async_generator': options_generator(),
            'generator_config': {
                'session_id': 'options_session',
                'heartbeat_enabled': True,
                'timeout_ms': 30000,
                'buffer_size': 2048
            },
            'streaming_options': {
                'format': 'sse',
                'compression': False,
                'keep_alive': True
            },
            'request_id': 'test-107-options'
        }

        result = await step_107__single_pass(messages=[], ctx=ctx)

        assert result['wrapped_stream'] is not None
        config = result['protection_config']
        assert config['heartbeat_enabled'] is True
        assert config['timeout_ms'] == 30000
        assert config['buffer_size'] == 2048
        assert 'streaming_options' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_107_logs_protection_details(self, mock_rag_log):
        """Test Step 107: Logs stream protection details for observability."""
        from app.orchestrators.preflight import step_107__single_pass

        async def logging_generator():
            yield "logging test"

        ctx = {
            'async_generator': logging_generator(),
            'generator_config': {
                'session_id': 'logging_session',
                'provider': 'openai',
                'model': 'gpt-4'
            },
            'protection_metrics': {
                'generators_protected': 5,
                'iterations_prevented': 2
            },
            'request_id': 'test-107-logging'
        }

        await step_107__single_pass(messages=[], ctx=ctx)

        # Verify structured logging
        assert mock_rag_log.call_count >= 2

        # Find the completion log call
        completion_call = None
        for call in mock_rag_log.call_args_list:
            if call[1].get('processing_stage') == 'completed':
                completion_call = call[1]
                break

        assert completion_call is not None
        assert completion_call['step'] == 107
        assert completion_call['stream_protected'] is True
        assert completion_call['next_step'] == 'write_sse'


class TestRAGStep107Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_107_parity_stream_protection_behavior(self):
        """Test Step 107 parity: Stream protection behavior unchanged."""
        from app.orchestrators.preflight import step_107__single_pass

        async def parity_generator():
            yield "parity test chunk 1"
            yield "parity test chunk 2"

        test_cases = [
            {
                'async_generator': parity_generator(),
                'generator_config': {
                    'session_id': 'parity_1',
                    'streaming_enabled': True
                },
                'expected_protected': True,
                'expected_next': 'write_sse'
            },
            {
                'async_generator': parity_generator(),
                'generator_config': {
                    'session_id': 'parity_2',
                    'provider': 'anthropic',
                    'model': 'claude-3'
                },
                'expected_protected': True,
                'expected_next': 'write_sse'
            }
        ]

        for test_case in test_cases:
            ctx = {
                **test_case,
                'request_id': f"parity-{hash(str(test_case))}"
            }
            # Remove expected values from context
            ctx.pop('expected_protected', None)
            ctx.pop('expected_next', None)

            with patch('app.orchestrators.preflight.rag_step_log'):
                result = await step_107__single_pass(messages=[], ctx=ctx)

            assert result['stream_protected'] == test_case['expected_protected']
            assert result['next_step'] == test_case['expected_next']
            assert result['processing_stage'] == 'stream_protected'


class TestRAGStep107Integration:
    """Integration tests for Step 107 with neighbors."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_async_gen_to_107_integration(self, mock_async_log):
        """Test AsyncGen → Step 107 integration."""

        # Simulate incoming from AsyncGen (Step 106)
        async def integration_generator():
            yield "integration chunk 1"
            yield "integration chunk 2"
            yield "[DONE]"

        async_gen_ctx = {
            'async_generator': integration_generator(),
            'generator_config': {
                'session_id': 'integration_session_107',
                'user_id': 'integration_user',
                'provider': 'openai',
                'model': 'gpt-4',
                'streaming_enabled': True,
                'chunk_size': 1024,
                'include_usage': True
            },
            'generator_created': True,
            'processing_stage': 'async_generator_created',
            'next_step': 'single_pass_stream',
            'request_id': 'integration-async-gen-107'
        }

        from app.orchestrators.preflight import step_107__single_pass

        result = await step_107__single_pass(messages=[], ctx=async_gen_ctx)

        assert result['generator_created'] is True
        assert result['stream_protected'] is True
        assert result['next_step'] == 'write_sse'
        assert 'wrapped_stream' in result
        assert 'generator_config' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_107_prepares_for_write_sse(self, mock_rag_log):
        """Test Step 107 prepares data for WriteSSE (Step 108)."""
        from app.orchestrators.preflight import step_107__single_pass

        async def sse_prep_generator():
            yield "data: chunk for SSE\n\n"
            yield "data: another chunk\n\n"

        ctx = {
            'async_generator': sse_prep_generator(),
            'generator_config': {
                'session_id': 'sse_prep_session',
                'streaming_enabled': True,
                'format': 'sse'
            },
            'sse_headers': {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache'
            },
            'request_id': 'test-107-prep-sse'
        }

        result = await step_107__single_pass(messages=[], ctx=ctx)

        # Verify data prepared for WriteSSE step
        assert result['next_step'] == 'write_sse'
        assert result['stream_protected'] is True
        assert 'wrapped_stream' in result
        assert result['wrapped_stream'] is not None
        assert 'sse_headers' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_107_error_handling(self, mock_rag_log):
        """Test Step 107 error handling and recovery."""
        from app.orchestrators.preflight import step_107__single_pass

        # Test with minimal/invalid context
        minimal_ctx = {
            'request_id': 'test-107-error-handling'
        }

        result = await step_107__single_pass(messages=[], ctx=minimal_ctx)

        # Should handle gracefully with warnings
        assert 'validation_warnings' in result
        assert result['stream_protected'] is True  # Should still protect
        assert 'wrapped_stream' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_107_streaming_flow_integration(self, mock_rag_log):
        """Test Step 107 integration with full streaming flow."""
        from app.orchestrators.preflight import step_107__single_pass

        async def full_flow_generator():
            yield "Full streaming flow test chunk 1"
            yield "Full streaming flow test chunk 2"
            yield "[DONE]"

        # Simulate full streaming context from previous steps
        full_streaming_ctx = {
            # From StreamCheck (Step 104)
            'streaming_requested': True,
            'decision': 'yes',
            'decision_source': 'stream_parameter',
            # From StreamSetup (Step 105)
            'sse_headers': {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            },
            'stream_context': {
                'session_id': 'full_flow_session',
                'user_id': 'full_flow_user',
                'streaming_enabled': True
            },
            'streaming_setup': 'configured',
            # From AsyncGen (Step 106)
            'async_generator': full_flow_generator(),
            'generator_config': {
                'session_id': 'full_flow_session',
                'provider': 'anthropic',
                'model': 'claude-3-sonnet',
                'streaming_enabled': True
            },
            'generator_created': True,
            'processing_stage': 'async_generator_created',
            'request_id': 'integration-full-flow-107'
        }

        result = await step_107__single_pass(messages=[], ctx=full_streaming_ctx)

        # Verify integration with full flow
        assert result['streaming_requested'] is True
        assert result['streaming_setup'] == 'configured'
        assert result['generator_created'] is True
        assert result['stream_protected'] is True
        assert result['next_step'] == 'write_sse'
        assert 'wrapped_stream' in result
        assert result['processing_stage'] == 'stream_protected'