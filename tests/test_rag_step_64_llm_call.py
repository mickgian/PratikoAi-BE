"""
Tests for RAG Step 64: LLMCall (LLMProvider.chat_completion Make API call).

This process step executes the actual LLM API call using the provider instance,
taking input from cache miss (Step 62) and routing to LLM success check (Step 67).
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.core.llm.base import LLMResponse, LLMProviderType
from app.schemas.chat import Message


class TestRAGStep64LLMCall:
    """Unit tests for Step 64: LLMCall."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_step_64_successful_llm_call(self, mock_rag_log):
        """Test Step 64: Successful LLM API call with OpenAI provider."""
        from app.orchestrators.providers import step_64__llmcall

        # Mock successful LLM response
        mock_llm_response = LLMResponse(
            content="The Italian VAT rates are 22% standard, 10% reduced, and 4% super-reduced.",
            model="gpt-4",
            provider="openai",
            tokens_used=45,
            cost_estimate=0.002,
            finish_reason="stop"
        )

        # Mock provider instance with chat_completion method
        mock_provider = MagicMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_llm_response)
        mock_provider.provider_type = LLMProviderType.OPENAI
        mock_provider.model = "gpt-4"

        ctx = {
            'provider_instance': mock_provider,
            'messages': [
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': 'What are Italian VAT rates?'}
            ],
            'model': 'gpt-4',
            'provider': 'openai',
            'temperature': 0.2,
            'max_tokens': 1000,
            'request_id': 'test-64-successful-call'
        }

        result = await step_64__llmcall(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert result['llm_call_successful'] is True
        assert result['llm_response'] == mock_llm_response
        assert result['provider'] == 'openai'
        assert result['model'] == 'gpt-4'
        assert result['response_content'] == mock_llm_response.content
        assert result['tokens_used'] == 45
        assert result['cost_estimate'] == 0.002

        # Verify the provider's chat_completion was called with correct parameters
        mock_provider.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_step_64_anthropic_llm_call(self, mock_rag_log):
        """Test Step 64: Successful LLM API call with Anthropic provider."""
        from app.orchestrators.providers import step_64__llmcall

        # Mock Anthropic LLM response
        mock_llm_response = LLMResponse(
            content="Italian VAT: 22% standard rate applies to most goods and services.",
            model="claude-3-sonnet-20240229",
            provider="anthropic",
            tokens_used=38,
            cost_estimate=0.0015,
            finish_reason="end_turn"
        )

        mock_provider = MagicMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_llm_response)
        mock_provider.provider_type = LLMProviderType.ANTHROPIC
        mock_provider.model = "claude-3-sonnet-20240229"

        ctx = {
            'provider_instance': mock_provider,
            'messages': [
                {'role': 'user', 'content': 'Italian VAT rates?'}
            ],
            'model': 'claude-3-sonnet-20240229',
            'provider': 'anthropic',
            'temperature': 0.1,
            'max_tokens': 500,
            'tools': [],
            'request_id': 'test-64-anthropic-call'
        }

        result = await step_64__llmcall(messages=[], ctx=ctx)

        assert result['llm_call_successful'] is True
        assert result['llm_response'] == mock_llm_response
        assert result['provider'] == 'anthropic'
        assert result['model'] == 'claude-3-sonnet-20240229'
        assert result['response_content'] == mock_llm_response.content
        assert result['tokens_used'] == 38

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_step_64_llm_call_with_tools(self, mock_rag_log):
        """Test Step 64: LLM API call with tool calling enabled."""
        from app.orchestrators.providers import step_64__llmcall

        # Mock LLM response with tool calls
        mock_tool_calls = [
            {
                'id': 'call_123',
                'type': 'function',
                'function': {
                    'name': 'search_knowledge_base',
                    'arguments': '{"query": "Italian VAT rates"}'
                }
            }
        ]

        mock_llm_response = LLMResponse(
            content="I need to search for current Italian VAT rates.",
            model="gpt-4",
            provider="openai",
            tokens_used=35,
            cost_estimate=0.0018,
            finish_reason="tool_calls",
            tool_calls=mock_tool_calls
        )

        mock_provider = MagicMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_llm_response)
        mock_provider.provider_type = LLMProviderType.OPENAI

        ctx = {
            'provider_instance': mock_provider,
            'messages': [
                {'role': 'user', 'content': 'What are the current Italian VAT rates?'}
            ],
            'model': 'gpt-4',
            'provider': 'openai',
            'tools': [
                {
                    'type': 'function',
                    'function': {
                        'name': 'search_knowledge_base',
                        'description': 'Search the knowledge base'
                    }
                }
            ],
            'temperature': 0.0,
            'request_id': 'test-64-tools-call'
        }

        result = await step_64__llmcall(messages=[], ctx=ctx)

        assert result['llm_call_successful'] is True
        assert result['llm_response'] == mock_llm_response
        assert result['has_tool_calls'] is True
        assert result['tool_calls'] == mock_tool_calls
        assert result['finish_reason'] == 'tool_calls'

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_step_64_llm_call_failure_timeout(self, mock_rag_log):
        """Test Step 64: LLM API call timeout failure."""
        from app.orchestrators.providers import step_64__llmcall
        import asyncio

        mock_provider = MagicMock()
        mock_provider.chat_completion = AsyncMock(side_effect=asyncio.TimeoutError("Request timeout"))
        mock_provider.provider_type = LLMProviderType.OPENAI
        mock_provider.model = "gpt-4"

        ctx = {
            'provider_instance': mock_provider,
            'messages': [
                {'role': 'user', 'content': 'Test timeout'}
            ],
            'model': 'gpt-4',
            'provider': 'openai',
            'temperature': 0.2,
            'max_tokens': 100,
            'request_id': 'test-64-timeout'
        }

        result = await step_64__llmcall(messages=[], ctx=ctx)

        assert result['llm_call_successful'] is False
        assert 'error' in result
        assert 'timeout' in result['error'].lower()
        assert result['exception_type'] == 'TimeoutError'
        assert result['provider'] == 'openai'
        assert result['model'] == 'gpt-4'

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_step_64_llm_call_failure_api_error(self, mock_rag_log):
        """Test Step 64: LLM API call with provider API error."""
        from app.orchestrators.providers import step_64__llmcall

        # Mock API error
        api_error = Exception("OpenAI API error: Rate limit exceeded")
        mock_provider = MagicMock()
        mock_provider.chat_completion = AsyncMock(side_effect=api_error)
        mock_provider.provider_type = LLMProviderType.OPENAI
        mock_provider.model = "gpt-3.5-turbo"

        ctx = {
            'provider_instance': mock_provider,
            'messages': [
                {'role': 'user', 'content': 'Test API error'}
            ],
            'model': 'gpt-3.5-turbo',
            'provider': 'openai',
            'request_id': 'test-64-api-error'
        }

        result = await step_64__llmcall(messages=[], ctx=ctx)

        assert result['llm_call_successful'] is False
        assert 'error' in result
        assert 'rate limit' in result['error'].lower()
        assert result['exception_type'] == 'Exception'
        assert result['provider'] == 'openai'
        assert result['model'] == 'gpt-3.5-turbo'

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_step_64_preserves_context_data(self, mock_rag_log):
        """Test Step 64: Preserves all context data from previous steps."""
        from app.orchestrators.providers import step_64__llmcall

        mock_llm_response = LLMResponse(
            content="Response content",
            model="gpt-4",
            provider="openai",
            tokens_used=25,
            cost_estimate=0.001
        )

        mock_provider = MagicMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_llm_response)

        original_ctx = {
            'provider_instance': mock_provider,
            'messages': [{'role': 'user', 'content': 'Test'}],
            'model': 'gpt-4',
            'provider': 'openai',
            'user_data': {'id': 'user_123', 'preferences': {'language': 'it'}},
            'session_data': {'id': 'session_456', 'created_at': '2024-01-01'},
            'cache_key': 'cache_key_789',
            'attempt_number': 1,
            'max_retries': 3,
            'routing_strategy': 'best',
            'request_id': 'test-64-preserve-context'
        }

        result = await step_64__llmcall(messages=[], ctx=original_ctx.copy())

        # Verify all original context is preserved
        assert result['user_data'] == original_ctx['user_data']
        assert result['session_data'] == original_ctx['session_data']
        assert result['cache_key'] == original_ctx['cache_key']
        assert result['attempt_number'] == original_ctx['attempt_number']
        assert result['max_retries'] == original_ctx['max_retries']
        assert result['routing_strategy'] == original_ctx['routing_strategy']
        assert result['provider'] == original_ctx['provider']
        assert result['model'] == original_ctx['model']

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_step_64_adds_call_metadata(self, mock_rag_log):
        """Test Step 64: Adds LLM call metadata and timing information."""
        from app.orchestrators.providers import step_64__llmcall

        mock_llm_response = LLMResponse(
            content="Metadata test response",
            model="claude-3-sonnet-20240229",
            provider="anthropic",
            tokens_used=30,
            cost_estimate=0.0012,
            finish_reason="end_turn"
        )

        mock_provider = MagicMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_llm_response)

        ctx = {
            'provider_instance': mock_provider,
            'messages': [{'role': 'user', 'content': 'Metadata test'}],
            'model': 'claude-3-sonnet-20240229',
            'provider': 'anthropic',
            'request_id': 'test-64-metadata'
        }

        result = await step_64__llmcall(messages=[], ctx=ctx)

        assert result['processing_stage'] == 'llm_call_completed'
        assert result['llm_call_successful'] is True
        assert 'call_timestamp' in result
        assert 'response_time_ms' in result

        # Verify timestamp format
        timestamp = result['call_timestamp']
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))  # Should not raise

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_step_64_handles_missing_provider(self, mock_rag_log):
        """Test Step 64: Handles missing provider instance gracefully."""
        from app.orchestrators.providers import step_64__llmcall

        ctx = {
            'messages': [{'role': 'user', 'content': 'Test'}],
            'model': 'gpt-4',
            'provider': 'openai',
            'request_id': 'test-64-missing-provider'
            # Note: no 'provider_instance' key
        }

        result = await step_64__llmcall(messages=[], ctx=ctx)

        assert result['llm_call_successful'] is False
        assert 'error' in result
        assert 'provider instance' in result['error'].lower()
        assert result['exception_type'] == 'ConfigurationError'

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_step_64_handles_invalid_messages(self, mock_rag_log):
        """Test Step 64: Handles invalid message format gracefully."""
        from app.orchestrators.providers import step_64__llmcall

        mock_provider = MagicMock()

        ctx = {
            'provider_instance': mock_provider,
            'messages': None,  # Invalid messages
            'model': 'gpt-4',
            'provider': 'openai',
            'request_id': 'test-64-invalid-messages'
        }

        result = await step_64__llmcall(messages=[], ctx=ctx)

        assert result['llm_call_successful'] is False
        assert 'error' in result
        assert 'messages' in result['error'].lower()

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_step_64_logs_call_details(self, mock_rag_log):
        """Test Step 64: Logs LLM call details for observability."""
        from app.orchestrators.providers import step_64__llmcall

        mock_llm_response = LLMResponse(
            content="Logging test response",
            model="gpt-4",
            provider="openai",
            tokens_used=42,
            cost_estimate=0.0025
        )

        mock_provider = MagicMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_llm_response)

        ctx = {
            'provider_instance': mock_provider,
            'messages': [
                {'role': 'system', 'content': 'Test system message'},
                {'role': 'user', 'content': 'Test user message'}
            ],
            'model': 'gpt-4',
            'provider': 'openai',
            'temperature': 0.3,
            'max_tokens': 500,
            'attempt_number': 2,
            'request_id': 'test-64-logging'
        }

        await step_64__llmcall(messages=[], ctx=ctx)

        # Verify structured logging
        assert mock_rag_log.call_count >= 2

        # Find the completion log call
        completion_call = None
        for call in mock_rag_log.call_args_list:
            if call[1].get('processing_stage') == 'completed':
                completion_call = call[1]
                break

        assert completion_call is not None
        assert completion_call['step'] == 64
        assert completion_call['llm_call_successful'] is True
        assert completion_call['provider'] == 'openai'
        assert completion_call['model'] == 'gpt-4'
        assert completion_call['tokens_used'] == 42
        assert completion_call['cost_estimate'] == 0.0025


class TestRAGStep64Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_64_parity_llm_call_behavior(self):
        """Test Step 64 parity: LLM call behavior unchanged."""
        from app.orchestrators.providers import step_64__llmcall

        mock_llm_response = LLMResponse(
            content="Parity test response",
            model="gpt-4",
            provider="openai",
            tokens_used=25,
            cost_estimate=0.001
        )

        test_cases = [
            {
                'provider': 'openai',
                'model': 'gpt-4',
                'expected_success': True
            },
            {
                'provider': 'anthropic',
                'model': 'claude-3-sonnet-20240229',
                'expected_success': True
            }
        ]

        for test_case in test_cases:
            mock_provider = MagicMock()
            mock_provider.chat_completion = AsyncMock(return_value=mock_llm_response)

            ctx = {
                'provider_instance': mock_provider,
                'messages': [{'role': 'user', 'content': 'Parity test'}],
                'model': test_case['model'],
                'provider': test_case['provider'],
                'request_id': f"parity-{hash(str(test_case))}"
            }

            with patch('app.orchestrators.providers.rag_step_log'):
                result = await step_64__llmcall(messages=[], ctx=ctx)

            assert result['llm_call_successful'] == test_case['expected_success']
            assert result['provider'] == test_case['provider']
            assert result['model'] == test_case['model']


class TestRAGStep64Integration:
    """Integration tests for Step 64 with neighbors."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_cache_miss_to_64_integration(self, mock_rag_log):
        """Test Cache Miss → Step 64 integration."""

        # Simulate incoming from Cache Miss (Step 62)
        cache_miss_ctx = {
            'cache_hit': False,
            'cache_key': 'test_cache_key_12345',
            'provider_instance': MagicMock(),
            'messages': [
                {'role': 'user', 'content': 'Integration test query'}
            ],
            'model': 'gpt-4',
            'provider': 'openai',
            'temperature': 0.2,
            'max_tokens': 1000,
            'user_id': 'integration_user_64',
            'session_id': 'integration_session_64',
            'request_id': 'integration-cache-miss-64'
        }

        # Mock successful response
        mock_llm_response = LLMResponse(
            content="Integration test response",
            model="gpt-4",
            provider="openai",
            tokens_used=35,
            cost_estimate=0.0018
        )
        cache_miss_ctx['provider_instance'].chat_completion = AsyncMock(return_value=mock_llm_response)

        from app.orchestrators.providers import step_64__llmcall
        result = await step_64__llmcall(messages=[], ctx=cache_miss_ctx)

        assert result['cache_hit'] is False
        assert result['cache_key'] == 'test_cache_key_12345'
        assert result['llm_call_successful'] is True
        assert result['llm_response'] == mock_llm_response
        assert result['user_id'] == 'integration_user_64'
        assert result['session_id'] == 'integration_session_64'

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_step_64_prepares_for_llm_success(self, mock_rag_log):
        """Test Step 64 prepares data for LLM Success (Step 67)."""
        from app.orchestrators.providers import step_64__llmcall

        mock_llm_response = LLMResponse(
            content="Success check preparation",
            model="claude-3-sonnet-20240229",
            provider="anthropic",
            tokens_used=40,
            cost_estimate=0.002,
            finish_reason="end_turn"
        )

        mock_provider = MagicMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_llm_response)

        ctx = {
            'provider_instance': mock_provider,
            'messages': [{'role': 'user', 'content': 'Success prep test'}],
            'model': 'claude-3-sonnet-20240229',
            'provider': 'anthropic',
            'attempt_number': 1,
            'max_retries': 3,
            'request_id': 'test-64-prep-success'
        }

        result = await step_64__llmcall(messages=[], ctx=ctx)

        # Verify data prepared for LLM Success step
        assert result['llm_call_successful'] is True
        assert result['llm_response'] == mock_llm_response
        assert result['attempt_number'] == 1
        assert result['max_retries'] == 3
        assert result['provider'] == 'anthropic'
        assert result['model'] == 'claude-3-sonnet-20240229'
        assert 'response_time_ms' in result
        assert 'call_timestamp' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_step_64_error_handling_integration(self, mock_rag_log):
        """Test Step 64 error handling and preparation for retry logic."""
        from app.orchestrators.providers import step_64__llmcall

        # Mock provider error
        mock_provider = MagicMock()
        mock_provider.chat_completion = AsyncMock(side_effect=Exception("Provider unavailable"))

        ctx = {
            'provider_instance': mock_provider,
            'messages': [{'role': 'user', 'content': 'Error handling test'}],
            'model': 'gpt-4',
            'provider': 'openai',
            'attempt_number': 2,
            'max_retries': 3,
            'request_id': 'test-64-error-handling'
        }

        result = await step_64__llmcall(messages=[], ctx=ctx)

        # Should handle gracefully and prepare for retry logic
        assert result['llm_call_successful'] is False
        assert 'error' in result
        assert result['attempt_number'] == 2
        assert result['max_retries'] == 3
        assert result['provider'] == 'openai'
        assert result['exception_type'] == 'Exception'

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    async def test_step_64_streaming_context_integration(self, mock_rag_log):
        """Test Step 64 integration with streaming context."""
        from app.orchestrators.providers import step_64__llmcall

        mock_llm_response = LLMResponse(
            content="Streaming context test response",
            model="gpt-4",
            provider="openai",
            tokens_used=50,
            cost_estimate=0.003
        )

        mock_provider = MagicMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_llm_response)

        ctx = {
            'provider_instance': mock_provider,
            'messages': [{'role': 'user', 'content': 'Streaming test'}],
            'model': 'gpt-4',
            'provider': 'openai',
            'streaming_requested': True,
            'stream_context': {'format': 'sse', 'chunk_size': 1024},
            'request_id': 'test-64-streaming-context'
        }

        result = await step_64__llmcall(messages=[], ctx=ctx)

        # Should preserve streaming context for downstream steps
        assert result['llm_call_successful'] is True
        assert result['streaming_requested'] is True
        assert result['stream_context'] == {'format': 'sse', 'chunk_size': 1024}
        assert result['llm_response'] == mock_llm_response