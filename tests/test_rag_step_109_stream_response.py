"""
Tests for RAG Step 109: StreamResponse (StreamingResponse Send chunks).

This process step sends SSE-formatted chunks as a streaming response,
taking formatted stream data from Step 108 and routing to Step 110.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from typing import AsyncGenerator
from fastapi.responses import StreamingResponse


class TestRAGStep109StreamResponse:
    """Unit tests for Step 109: StreamResponse."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_creates_streaming_response(self, mock_rag_log):
        """Test Step 109: Creates StreamingResponse with SSE-formatted chunks."""
        from app.orchestrators.streaming import step_109__stream_response

        async def test_sse_stream():
            yield "data: chunk1: test content\n\n"
            yield "data: chunk2: more content\n\n"
            yield "data: [DONE]\n\n"

        ctx = {
            'sse_formatted_stream': test_sse_stream(),
            'format_config': {
                'session_id': 'test_session_123',
                'provider': 'openai',
                'model': 'gpt-4',
                'sse_format': True,
                'compression': False
            },
            'sse_headers': {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            },
            'chunks_formatted': True,
            'request_id': 'test-109-create-response'
        }

        result = await step_109__stream_response(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert 'streaming_response' in result
        assert isinstance(result['streaming_response'], StreamingResponse)
        assert result['response_created'] is True
        assert result['next_step'] == 'send_done'
        assert 'response_config' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_configures_response_headers(self, mock_rag_log):
        """Test Step 109: Configures StreamingResponse headers."""
        from app.orchestrators.streaming import step_109__stream_response

        async def header_stream():
            yield "data: header test content\n\n"

        ctx = {
            'sse_formatted_stream': header_stream(),
            'sse_headers': {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': 'true'
            },
            'format_config': {
                'session_id': 'header_session',
                'provider': 'anthropic',
                'model': 'claude-3-sonnet'
            },
            'request_id': 'test-109-headers'
        }

        result = await step_109__stream_response(messages=[], ctx=ctx)

        response = result['streaming_response']
        assert response.headers['content-type'] == 'text/event-stream'
        assert response.headers['cache-control'] == 'no-cache'
        assert response.headers['connection'] == 'keep-alive'
        assert 'access-control-allow-origin' in response.headers

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_handles_complex_sse_streams(self, mock_rag_log):
        """Test Step 109: Handles complex SSE stream structures."""
        from app.orchestrators.streaming import step_109__stream_response

        async def complex_sse_stream():
            yield 'data: {"type": "chunk", "content": "chunk1", "metadata": {"tokens": 10}}\n\n'
            yield 'data: {"type": "chunk", "content": "chunk2", "metadata": {"tokens": 15}}\n\n'
            yield 'data: {"type": "done", "content": "[DONE]", "metadata": {"total_tokens": 25}}\n\n'

        ctx = {
            'sse_formatted_stream': complex_sse_stream(),
            'format_config': {
                'session_id': 'complex_session',
                'json_format': True,
                'include_metadata': True,
                'provider': 'openai'
            },
            'format_options': {
                'pretty_json': True,
                'include_timestamps': True
            },
            'request_id': 'test-109-complex'
        }

        result = await step_109__stream_response(messages=[], ctx=ctx)

        assert result['streaming_response'] is not None
        assert result['response_created'] is True
        assert 'format_options' in result
        assert result['response_config']['json_format'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_preserves_all_context_data(self, mock_rag_log):
        """Test Step 109: Preserves all context data for downstream processing."""
        from app.orchestrators.streaming import step_109__stream_response

        async def preserve_stream():
            yield "data: preserved context test\n\n"

        original_ctx = {
            'sse_formatted_stream': preserve_stream(),
            'format_config': {'session_id': 'preserve_session'},
            'user_data': {'id': 'user_123', 'preferences': {'language': 'it'}},
            'session_data': {'id': 'session_456', 'created_at': '2024-01-01'},
            'response_metadata': {
                'provider': 'anthropic',
                'model': 'claude-3',
                'tokens_used': 200
            },
            'processing_history': ['stream_check', 'stream_setup', 'async_gen', 'single_pass', 'write_sse'],
            'sse_headers': {'Content-Type': 'text/event-stream'},
            'chunks_formatted': True,
            'protection_config': {'session_id': 'preserve_session'},
            'request_id': 'test-109-preserve'
        }

        result = await step_109__stream_response(messages=[], ctx=original_ctx.copy())

        # Verify all original context is preserved
        assert result['user_data'] == original_ctx['user_data']
        assert result['session_data'] == original_ctx['session_data']
        assert result['response_metadata'] == original_ctx['response_metadata']
        assert result['processing_history'] == original_ctx['processing_history']
        assert result['sse_headers'] == original_ctx['sse_headers']
        assert result['format_config'] == original_ctx['format_config']
        assert result['chunks_formatted'] == original_ctx['chunks_formatted']

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_adds_response_metadata(self, mock_rag_log):
        """Test Step 109: Adds StreamingResponse metadata."""
        from app.orchestrators.streaming import step_109__stream_response

        async def metadata_stream():
            yield "data: metadata test\n\n"

        ctx = {
            'sse_formatted_stream': metadata_stream(),
            'format_config': {'session_id': 'test_session'},
            'chunks_formatted': True,
            'request_id': 'test-109-metadata'
        }

        result = await step_109__stream_response(messages=[], ctx=ctx)

        assert result['processing_stage'] == 'response_created'
        assert result['next_step'] == 'send_done'
        assert result['response_created'] is True
        assert 'response_timestamp' in result

        # Verify timestamp format
        timestamp = result['response_timestamp']
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))  # Should not raise

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_validates_response_requirements(self, mock_rag_log):
        """Test Step 109: Validates response requirements and adds warnings."""
        from app.orchestrators.streaming import step_109__stream_response

        # Test with missing/invalid stream
        ctx = {
            'sse_formatted_stream': None,  # Missing stream
            'format_config': {},  # Empty config
            'chunks_formatted': False,  # Not formatted
            'request_id': 'test-109-validation'
        }

        result = await step_109__stream_response(messages=[], ctx=ctx)

        assert 'validation_warnings' in result
        warnings = result['validation_warnings']
        assert len(warnings) > 0
        assert any('No SSE formatted stream available' in warning for warning in warnings)
        assert any('chunks not formatted' in warning for warning in warnings)

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_configures_response_options(self, mock_rag_log):
        """Test Step 109: Configures StreamingResponse options."""
        from app.orchestrators.streaming import step_109__stream_response

        async def options_stream():
            yield "data: response options test\n\n"

        ctx = {
            'sse_formatted_stream': options_stream(),
            'format_config': {
                'session_id': 'options_session',
                'compression': True,
                'buffer_size': 2048,
                'media_type': 'text/event-stream'
            },
            'response_options': {
                'status_code': 200,
                'background': None
            },
            'request_id': 'test-109-options'
        }

        result = await step_109__stream_response(messages=[], ctx=ctx)

        response_config = result['response_config']
        assert response_config['compression'] is True
        assert response_config['buffer_size'] == 2048
        assert response_config['media_type'] == 'text/event-stream'
        assert 'response_options' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_handles_response_errors(self, mock_rag_log):
        """Test Step 109: Handles response creation errors gracefully."""
        from app.orchestrators.streaming import step_109__stream_response

        async def error_stream():
            yield "data: chunk1\n\n"
            raise Exception("Stream error")

        ctx = {
            'sse_formatted_stream': error_stream(),
            'format_config': {
                'session_id': 'error_session',
                'error_handling': 'graceful'
            },
            'error_recovery_enabled': True,
            'request_id': 'test-109-errors'
        }

        result = await step_109__stream_response(messages=[], ctx=ctx)

        assert result['streaming_response'] is not None
        assert result['response_created'] is True
        assert result['response_config']['error_handling'] == 'graceful'

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_handles_response_parameters(self, mock_rag_log):
        """Test Step 109: Handles various response parameters."""
        from app.orchestrators.streaming import step_109__stream_response

        async def params_stream():
            yield "data: response params test\n\n"

        ctx = {
            'sse_formatted_stream': params_stream(),
            'format_config': {
                'session_id': 'params_session',
                'media_type': 'text/event-stream',
                'charset': 'utf-8'
            },
            'response_parameters': {
                'status_code': 200,
                'headers': {'X-Custom': 'value'},
                'background_task': None
            },
            'request_id': 'test-109-params'
        }

        result = await step_109__stream_response(messages=[], ctx=ctx)

        assert result['streaming_response'] is not None
        config = result['response_config']
        assert config['media_type'] == 'text/event-stream'
        assert config['charset'] == 'utf-8'
        assert 'response_parameters' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_logs_response_details(self, mock_rag_log):
        """Test Step 109: Logs StreamingResponse details for observability."""
        from app.orchestrators.streaming import step_109__stream_response

        async def logging_stream():
            yield "data: logging test\n\n"

        ctx = {
            'sse_formatted_stream': logging_stream(),
            'format_config': {
                'session_id': 'logging_session',
                'provider': 'openai',
                'model': 'gpt-4'
            },
            'response_metrics': {
                'chunks_sent': 10,
                'bytes_streamed': 2048
            },
            'request_id': 'test-109-logging'
        }

        await step_109__stream_response(messages=[], ctx=ctx)

        # Verify structured logging
        assert mock_rag_log.call_count >= 2

        # Find the completion log call
        completion_call = None
        for call in mock_rag_log.call_args_list:
            if call[1].get('processing_stage') == 'completed':
                completion_call = call[1]
                break

        assert completion_call is not None
        assert completion_call['step'] == 109
        assert completion_call['response_created'] is True
        assert completion_call['next_step'] == 'send_done'


class TestRAGStep109Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_109_parity_response_creation_behavior(self):
        """Test Step 109 parity: StreamingResponse creation behavior unchanged."""
        from app.orchestrators.streaming import step_109__stream_response

        async def parity_stream():
            yield "data: parity test chunk 1\n\n"
            yield "data: parity test chunk 2\n\n"

        test_cases = [
            {
                'sse_formatted_stream': parity_stream(),
                'format_config': {
                    'session_id': 'parity_1',
                    'sse_format': True
                },
                'expected_created': True,
                'expected_next': 'send_done'
            },
            {
                'sse_formatted_stream': parity_stream(),
                'format_config': {
                    'session_id': 'parity_2',
                    'provider': 'anthropic',
                    'model': 'claude-3'
                },
                'expected_created': True,
                'expected_next': 'send_done'
            }
        ]

        for test_case in test_cases:
            ctx = {
                **test_case,
                'request_id': f"parity-{hash(str(test_case))}"
            }
            # Remove expected values from context
            ctx.pop('expected_created', None)
            ctx.pop('expected_next', None)

            with patch('app.orchestrators.streaming.rag_step_log'):
                result = await step_109__stream_response(messages=[], ctx=ctx)

            assert result['response_created'] == test_case['expected_created']
            assert result['next_step'] == test_case['expected_next']
            assert result['processing_stage'] == 'response_created'


class TestRAGStep109Integration:
    """Integration tests for Step 109 with neighbors."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_write_sse_to_109_integration(self, mock_write_sse_log):
        """Test WriteSSE → Step 109 integration."""

        # Simulate incoming from WriteSSE (Step 108)
        async def integration_sse_stream():
            yield "data: integration chunk 1\n\n"
            yield "data: integration chunk 2\n\n"
            yield "data: [DONE]\n\n"

        write_sse_ctx = {
            'sse_formatted_stream': integration_sse_stream(),
            'format_config': {
                'session_id': 'integration_session_109',
                'user_id': 'integration_user',
                'provider': 'openai',
                'model': 'gpt-4',
                'sse_format': True,
                'compression': False,
                'buffer_size': 1024
            },
            'chunks_formatted': True,
            'sse_headers': {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache'
            },
            'processing_stage': 'sse_formatted',
            'next_step': 'streaming_response',
            'request_id': 'integration-write-sse-109'
        }

        from app.orchestrators.streaming import step_109__stream_response

        result = await step_109__stream_response(messages=[], ctx=write_sse_ctx)

        assert result['chunks_formatted'] is True
        assert result['response_created'] is True
        assert result['next_step'] == 'send_done'
        assert isinstance(result['streaming_response'], StreamingResponse)
        assert 'format_config' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_prepares_for_send_done(self, mock_rag_log):
        """Test Step 109 prepares data for SendDone (Step 110)."""
        from app.orchestrators.streaming import step_109__stream_response

        async def send_done_prep_stream():
            yield "data: prepared for send done\n\n"
            yield "data: final chunk\n\n"

        ctx = {
            'sse_formatted_stream': send_done_prep_stream(),
            'format_config': {
                'session_id': 'send_done_prep_session',
                'sse_format': True
            },
            'sse_headers': {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache'
            },
            'chunks_formatted': True,
            'request_id': 'test-109-prep-send-done'
        }

        result = await step_109__stream_response(messages=[], ctx=ctx)

        # Verify data prepared for SendDone step
        assert result['next_step'] == 'send_done'
        assert result['response_created'] is True
        assert isinstance(result['streaming_response'], StreamingResponse)
        assert 'response_config' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_error_handling(self, mock_rag_log):
        """Test Step 109 error handling and recovery."""
        from app.orchestrators.streaming import step_109__stream_response

        # Test with minimal/invalid context
        minimal_ctx = {
            'request_id': 'test-109-error-handling'
        }

        result = await step_109__stream_response(messages=[], ctx=minimal_ctx)

        # Should handle gracefully with warnings
        assert 'validation_warnings' in result
        assert result['response_created'] is True  # Should still create response
        assert 'streaming_response' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_full_streaming_flow_integration(self, mock_rag_log):
        """Test Step 109 integration with full streaming flow."""
        from app.orchestrators.streaming import step_109__stream_response

        async def full_flow_sse_stream():
            yield "data: Full streaming flow test chunk 1\n\n"
            yield "data: Full streaming flow test chunk 2\n\n"
            yield "data: [DONE]\n\n"

        # Simulate full streaming context from all previous steps
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
            'generator_created': True,
            # From SinglePass (Step 107)
            'protection_config': {
                'double_iteration_prevention': True,
                'session_id': 'full_flow_session',
                'provider': 'anthropic',
                'model': 'claude-3-sonnet',
                'streaming_enabled': True
            },
            'stream_protected': True,
            # From WriteSSE (Step 108)
            'sse_formatted_stream': full_flow_sse_stream(),
            'format_config': {
                'session_id': 'full_flow_session',
                'provider': 'anthropic',
                'model': 'claude-3-sonnet',
                'sse_format': True
            },
            'chunks_formatted': True,
            'processing_stage': 'sse_formatted',
            'request_id': 'integration-full-flow-109'
        }

        result = await step_109__stream_response(messages=[], ctx=full_streaming_ctx)

        # Verify integration with full flow
        assert result['streaming_requested'] is True
        assert result['streaming_setup'] == 'configured'
        assert result['generator_created'] is True
        assert result['stream_protected'] is True
        assert result['chunks_formatted'] is True
        assert result['response_created'] is True
        assert result['next_step'] == 'send_done'
        assert isinstance(result['streaming_response'], StreamingResponse)
        assert result['processing_stage'] == 'response_created'

    @pytest.mark.asyncio
    @patch('app.orchestrators.streaming.rag_step_log')
    async def test_step_109_fastapi_streaming_response_integration(self, mock_rag_log):
        """Test Step 109 integration with FastAPI StreamingResponse."""
        from app.orchestrators.streaming import step_109__stream_response

        async def fastapi_stream():
            yield "data: FastAPI integration test\n\n"
            yield "data: streaming response test\n\n"
            yield "data: [DONE]\n\n"

        ctx = {
            'sse_formatted_stream': fastapi_stream(),
            'format_config': {
                'session_id': 'fastapi_session',
                'media_type': 'text/event-stream'
            },
            'sse_headers': {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'  # Nginx streaming hint
            },
            'chunks_formatted': True,
            'request_id': 'test-109-fastapi-integration'
        }

        result = await step_109__stream_response(messages=[], ctx=ctx)

        # Verify FastAPI StreamingResponse properties
        streaming_response = result['streaming_response']
        assert isinstance(streaming_response, StreamingResponse)
        assert streaming_response.media_type == 'text/event-stream'
        assert 'x-accel-buffering' in streaming_response.headers
        assert result['response_created'] is True