#!/usr/bin/env python3
"""
Tests for RAG STEP 68 — CacheService.cache_response Store in Redis

This step stores LLM responses in Redis cache for future retrieval with TTL and encryption.
"""

from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from app.core.llm.base import LLMResponse
from app.orchestrators.cache import step_68__cache_response


class TestRAGStep68CacheResponse:
    """Test suite for RAG STEP 68 - Store response in cache"""

    @pytest.mark.asyncio
    @patch('app.orchestrators.cache.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.cache.cache_service')
    async def test_step_68_cache_response_success(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 68: Successful response caching"""

        llm_response = LLMResponse(
            content="VAT rate for professional services is 22%",
            model="gpt-4",
            tokens_used=70,
            provider="openai",
            finish_reason="stop"
        )

        # Mock cache service
        mock_cache_service.enabled = True
        mock_cache_service.cache_response = AsyncMock(return_value=True)

        ctx = {
            'llm_response': llm_response,
            'cache_key': 'cache_key_abc123def456',
            'query_hash': 'hash123',
            'ttl': 3600,  # 1 hour
            'user_id': 'user_123',
            'session_id': 'session_456'
        }

        # Call the orchestrator function
        result = await step_68__cache_response(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result['caching_successful'] is True
        assert result['response_cached'] is True
        assert result['cache_key'] == 'cache_key_abc123def456'
        assert result['ttl'] == 3600
        assert result['model'] == 'gpt-4'
        assert result['provider'] == 'openai'
        assert 'timestamp' in result

        # Verify cache service was called correctly
        mock_cache_service.cache_response.assert_called_once()
        call_args = mock_cache_service.cache_response.call_args
        assert call_args[1]['cache_key'] == 'cache_key_abc123def456'
        assert call_args[1]['response'] == llm_response
        assert call_args[1]['ttl'] == 3600

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert 'Response cached successfully' in log_call[0][0]
        assert log_call[1]['extra']['cache_event'] == 'response_stored'

    @pytest.mark.asyncio
    @patch('app.orchestrators.cache.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.cache.cache_service')
    async def test_step_68_cache_disabled(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 68: Cache response with cache service disabled"""

        llm_response = LLMResponse(content="Test", model="gpt-4")

        # Mock cache service as disabled
        mock_cache_service.enabled = False

        ctx = {
            'llm_response': llm_response,
            'cache_key': 'disabled_key'
        }

        result = await step_68__cache_response(ctx=ctx)

        assert result['caching_successful'] is False
        assert result['response_cached'] is False
        assert result['error'] == 'Cache service disabled'

        # Should not call cache storage
        mock_cache_service.cache_response.assert_not_called()

    @pytest.mark.asyncio
    @patch('app.orchestrators.cache.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.cache.cache_service')
    async def test_step_68_missing_required_params(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 68: Handle missing required parameters"""

        mock_cache_service.enabled = True

        ctx = {
            'cache_key': 'some_key'
            # Missing llm_response
        }

        result = await step_68__cache_response(ctx=ctx)

        # Should return error result
        assert result['caching_successful'] is False
        assert result['error'] == 'Missing required parameters: llm_response or cache_key'

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert 'Response caching failed' in error_call[0][0]

    @pytest.mark.asyncio
    @patch('app.orchestrators.cache.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.cache.cache_service')
    async def test_step_68_default_ttl(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 68: Default TTL when not specified"""

        llm_response = LLMResponse(content="Test", model="gpt-3.5-turbo")

        mock_cache_service.enabled = True
        mock_cache_service.cache_response = AsyncMock(return_value=True)

        ctx = {
            'llm_response': llm_response,
            'cache_key': 'default_ttl_key'
            # Missing TTL - should use default
        }

        result = await step_68__cache_response(ctx=ctx)

        assert result['caching_successful'] is True
        assert result['ttl'] == 86400  # Default 24 hours

        # Verify default TTL was passed to service
        call_args = mock_cache_service.cache_response.call_args
        assert call_args[1]['ttl'] == 86400

    @pytest.mark.asyncio
    @patch('app.orchestrators.cache.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.cache.cache_service')
    async def test_step_68_cache_storage_error(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 68: Handle cache storage service error"""

        llm_response = LLMResponse(content="Test", model="gpt-4")

        mock_cache_service.enabled = True
        mock_cache_service.cache_response = AsyncMock(side_effect=Exception("Redis storage failed"))

        ctx = {
            'llm_response': llm_response,
            'cache_key': 'error_key'
        }

        result = await step_68__cache_response(ctx=ctx)

        # Should return error result
        assert result['caching_successful'] is False
        assert result['error'] == 'Redis storage failed'

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.cache.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.cache.cache_service')
    async def test_step_68_kwargs_parameters(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 68: Parameters passed via kwargs"""

        llm_response = LLMResponse(
            content="Kwargs response",
            model="claude-3",
            provider="anthropic"
        )

        mock_cache_service.enabled = True
        mock_cache_service.cache_response = AsyncMock(return_value=True)

        # Call with kwargs instead of ctx
        result = await step_68__cache_response(
            llm_response=llm_response,
            cache_key='kwargs_cache_key',
            query_hash='kwargs_hash',
            ttl=7200,  # 2 hours
            user_id='user_456'
        )

        # Verify kwargs are processed correctly
        assert result['caching_successful'] is True
        assert result['cache_key'] == 'kwargs_cache_key'
        assert result['query_hash'] == 'kwargs_hash'
        assert result['ttl'] == 7200
        assert result['user_id'] == 'user_456'

    @pytest.mark.asyncio
    @patch('app.orchestrators.cache.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.cache.cache_service', None)
    async def test_step_68_no_cache_service(self, mock_logger, mock_rag_log):
        """Test Step 68: Handle missing cache service"""

        llm_response = LLMResponse(content="Test", model="gpt-4")

        ctx = {
            'llm_response': llm_response,
            'cache_key': 'no_service_key'
        }

        result = await step_68__cache_response(ctx=ctx)

        assert result['caching_successful'] is False
        assert result['response_cached'] is False
        assert result['error'] == 'Cache service not available'

    @pytest.mark.asyncio
    @patch('app.orchestrators.cache.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.cache.cache_service')
    async def test_step_68_complex_response_caching(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 68: Complex response with tool calls and metadata"""

        llm_response = LLMResponse(
            content="Complex analysis with multiple data points",
            model="gpt-4-turbo",
            tokens_used=70,
            provider="openai",
            finish_reason="stop",
            tool_calls=[
                {"name": "calculate_vat", "arguments": {"rate": 0.22}},
                {"name": "lookup_regulation", "arguments": {"code": "DPR633"}}
            ]
        )

        mock_cache_service.enabled = True
        mock_cache_service.cache_response = AsyncMock(return_value=True)

        ctx = {
            'llm_response': llm_response,
            'cache_key': 'complex_key',
            'ttl': 1800,  # 30 minutes
            'compression': True,
            'encryption': True
        }

        result = await step_68__cache_response(ctx=ctx)

        assert result['caching_successful'] is True
        assert {'tokens_used': result['cached_response'].tokens_used}['total_tokens'] == 430
        assert result['compression'] is True
        assert result['encryption'] is True

        # Verify complex response was passed correctly
        call_args = mock_cache_service.cache_response.call_args
        cached_response = call_args[1]['response']
        assert len(cached_response.tool_calls) == 2
        assert cached_response.tool_calls[0]['name'] == 'calculate_vat'

    @pytest.mark.asyncio
    @patch('app.orchestrators.cache.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.cache.cache_service')
    async def test_step_68_cache_storage_failure(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 68: Handle cache storage returning False"""

        llm_response = LLMResponse(content="Test", model="gpt-4")

        mock_cache_service.enabled = True
        mock_cache_service.cache_response = AsyncMock(return_value=False)  # Storage failed

        ctx = {
            'llm_response': llm_response,
            'cache_key': 'failure_key'
        }

        result = await step_68__cache_response(ctx=ctx)

        assert result['caching_successful'] is False
        assert result['response_cached'] is False
        assert result['error'] == 'Cache storage operation failed'

    @pytest.mark.asyncio
    @patch('app.orchestrators.cache.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.cache.cache_service')
    async def test_step_68_response_size_tracking(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 68: Response size tracking and optimization"""

        large_content = "Large response content " * 500  # ~10KB response
        llm_response = LLMResponse(
            content=large_content,
            model="gpt-4"
        )

        mock_cache_service.enabled = True
        mock_cache_service.cache_response = AsyncMock(return_value=True)

        ctx = {
            'llm_response': llm_response,
            'cache_key': 'large_response_key',
            'optimize_storage': True
        }

        result = await step_68__cache_response(ctx=ctx)

        assert result['caching_successful'] is True
        assert 'response_size' in result
        assert result['response_size'] > 10000  # Should track large size
        assert result['optimize_storage'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.cache.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.cache.cache_service')
    async def test_step_68_performance_tracking(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 68: Performance tracking with timer"""

        with patch('app.orchestrators.cache.rag_step_timer') as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            llm_response = LLMResponse(content="Test", model="gpt-4")
            mock_cache_service.enabled = True
            mock_cache_service.cache_response = AsyncMock(return_value=True)

            # Call the orchestrator function
            await step_68__cache_response(ctx={
                'llm_response': llm_response,
                'cache_key': 'perf_key'
            })

            # Verify timer was used
            mock_timer.assert_called_with(
                68,
                'RAG.cache.cacheservice.cache.response.store.in.redis',
                'CacheResponse',
                stage='start'
            )

    @pytest.mark.asyncio
    @patch('app.orchestrators.cache.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.cache.cache_service')
    async def test_step_68_comprehensive_logging_format(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 68: Verify comprehensive logging format"""

        llm_response = LLMResponse(content="Test", model="gpt-4")
        mock_cache_service.enabled = True
        mock_cache_service.cache_response = AsyncMock(return_value=True)

        ctx = {
            'llm_response': llm_response,
            'cache_key': 'format_key',
            'user_id': 'user_123'
        }

        # Call the orchestrator function
        await step_68__cache_response(ctx=ctx)

        # Verify RAG step logging format
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            'step', 'step_id', 'node_label', 'cache_event',
            'caching_successful', 'response_cached', 'cache_key',
            'model', 'ttl', 'processing_stage'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]['step'] == 68
        assert log_call[1]['step_id'] == 'RAG.cache.cacheservice.cache.response.store.in.redis'
        assert log_call[1]['node_label'] == 'CacheResponse'
        assert log_call[1]['cache_event'] == 'response_stored'

    @pytest.mark.asyncio
    @patch('app.orchestrators.cache.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.cache.cache_service')
    async def test_step_68_cache_metadata_storage(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 68: Cache metadata and versioning"""

        llm_response = LLMResponse(
            content="Response with versioning metadata",
            model="claude-3-sonnet",
            provider="anthropic"
        )

        mock_cache_service.enabled = True
        mock_cache_service.cache_response = AsyncMock(return_value=True)

        ctx = {
            'llm_response': llm_response,
            'cache_key': 'metadata_key',
            'cache_version': '2.1',
            'tags': ['vat', 'professional_services'],
            'priority': 'high'
        }

        result = await step_68__cache_response(ctx=ctx)

        assert result['caching_successful'] is True
        assert result['cache_version'] == '2.1'
        assert result['tags'] == ['vat', 'professional_services']
        assert result['priority'] == 'high'

        # Verify metadata passed to cache service
        call_args = mock_cache_service.cache_response.call_args
        assert call_args[1]['cache_key'] == 'metadata_key'
        assert call_args[1]['response'] == llm_response