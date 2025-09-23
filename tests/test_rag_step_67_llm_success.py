"""
Tests for RAG STEP 67 — LLM call successful? (RAG.llm.llm.call.successful)

This decision step validates whether an LLM API call succeeded or failed.
It routes successful responses to caching (Step 68) and failed responses to retry logic (Step 69).
"""

from unittest.mock import patch

import pytest

from app.core.llm.base import LLMResponse


class TestRAGStep67LLMSuccess:
    """Test suite for RAG STEP 67 - LLM call successful decision."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    async def test_step_67_llm_call_successful(self, mock_rag_log):
        """Test Step 67: LLM call succeeds - routes to cache response."""
        from app.orchestrators.llm import step_67__llmsuccess

        # Create successful LLM response
        llm_response = LLMResponse(
            content="Here's the answer to your question...",
            tool_calls=[],
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai"
        )

        # Call orchestrator
        ctx = {
            'llm_response': llm_response,
            'error': None,
            'exception': None,
            'request_id': 'test-67-success'
        }

        result = await step_67__llmsuccess(messages=[], ctx=ctx)

        # Verify decision result
        assert isinstance(result, dict)
        assert result['llm_success'] is True
        assert result['has_response'] is True
        assert result['error_occurred'] is False
        assert result['next_step'] == 'cache_response'  # Routes to Step 68
        assert result['llm_response'] == llm_response
        assert result['request_id'] == 'test-67-success'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2  # start and completed
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 67
        assert completed_log['node_label'] == 'LLMSuccess'
        assert completed_log['llm_success'] is True
        assert completed_log['decision'] == 'success'

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    async def test_step_67_llm_call_failed_with_exception(self, mock_rag_log):
        """Test Step 67: LLM call fails with exception - routes to retry check."""
        from app.orchestrators.llm import step_67__llmsuccess

        # Simulate failed LLM call with exception
        error_message = "OpenAI API rate limit exceeded"
        exception = Exception(error_message)

        ctx = {
            'llm_response': None,
            'error': error_message,
            'exception': exception,
            'attempt_number': 1,
            'request_id': 'test-67-failure'
        }

        result = await step_67__llmsuccess(messages=[], ctx=ctx)

        # Verify decision result routes to retry logic
        assert result['llm_success'] is False
        assert result['has_response'] is False
        assert result['error_occurred'] is True
        assert result['next_step'] == 'retry_check'  # Routes to Step 69
        assert result['error_message'] == error_message
        assert result['exception_type'] == 'Exception'
        assert result['request_id'] == 'test-67-failure'

        # Verify error logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['llm_success'] is False
        assert completed_log['decision'] == 'failure'
        assert completed_log['error_occurred'] is True
        assert completed_log['error_type'] == 'Exception'

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    async def test_step_67_llm_call_failed_empty_response(self, mock_rag_log):
        """Test Step 67: LLM call returns None/empty response - routes to retry."""
        from app.orchestrators.llm import step_67__llmsuccess

        # Simulate empty response (no exception but no content)
        ctx = {
            'llm_response': None,
            'error': "Empty response from LLM",
            'exception': None,
            'attempt_number': 1,
            'request_id': 'test-67-empty'
        }

        result = await step_67__llmsuccess(messages=[], ctx=ctx)

        # Should route to retry
        assert result['llm_success'] is False
        assert result['has_response'] is False
        assert result['next_step'] == 'retry_check'
        assert result['error_message'] == "Empty response from LLM"

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    async def test_step_67_with_response_metadata(self, mock_rag_log):
        """Test Step 67: Success with detailed response metadata logged."""
        from app.orchestrators.llm import step_67__llmsuccess

        llm_response = LLMResponse(
            content="Detailed answer with citations...",
            tool_calls=[{"name": "search", "args": {"query": "tax rates"}}],
            cost_estimate=0.005,
            model="gpt-4-turbo",
            provider="openai"
        )
        # Add cost_eur as an attribute after creation
        llm_response.cost_eur = 0.0045

        ctx = {
            'llm_response': llm_response,
            'provider': 'openai',
            'model': 'gpt-4-turbo',
            'attempt_number': 1,
            'response_time_ms': 1234,
            'request_id': 'test-67-metadata'
        }

        result = await step_67__llmsuccess(messages=[], ctx=ctx)

        # Verify metadata is captured
        assert result['llm_success'] is True
        assert result['provider'] == 'openai'
        assert result['model'] == 'gpt-4-turbo'
        assert result['response_time_ms'] == 1234
        assert result['has_tool_calls'] is True

        # Verify metadata in logs
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        completed_log = completed_logs[0][1]
        assert completed_log['provider'] == 'openai'
        assert completed_log['model'] == 'gpt-4-turbo'
        assert completed_log['response_time_ms'] == 1234
        assert completed_log['has_tool_calls'] is True
        assert completed_log['cost_eur'] == 0.0045

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    async def test_step_67_multiple_retry_attempts(self, mock_rag_log):
        """Test Step 67: Decision tracking across multiple retry attempts."""
        from app.orchestrators.llm import step_67__llmsuccess

        # Test different attempt numbers
        for attempt in [1, 2, 3]:
            mock_rag_log.reset_mock()

            ctx = {
                'llm_response': None,
                'error': f"Attempt {attempt} failed",
                'exception': Exception(f"Error on attempt {attempt}"),
                'attempt_number': attempt,
                'max_retries': 3,
                'request_id': f'test-67-attempt-{attempt}'
            }

            result = await step_67__llmsuccess(messages=[], ctx=ctx)

            # All attempts should route to retry check
            assert result['llm_success'] is False
            assert result['next_step'] == 'retry_check'
            assert result['attempt_number'] == attempt

            # Verify attempt tracking in logs
            completed_logs = [
                call for call in mock_rag_log.call_args_list
                if call[1].get('processing_stage') == 'completed'
            ]

            completed_log = completed_logs[0][1]
            assert completed_log['attempt_number'] == attempt
            assert completed_log['max_retries'] == 3

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    async def test_step_67_success_after_retry(self, mock_rag_log):
        """Test Step 67: Success on retry attempt (not first attempt)."""
        from app.orchestrators.llm import step_67__llmsuccess

        llm_response = LLMResponse(
            content="Success after retry",
            tool_calls=[],
            cost_estimate=0.002,
            model="claude-3-sonnet",
            provider="anthropic"
        )

        ctx = {
            'llm_response': llm_response,
            'attempt_number': 2,  # Second attempt succeeded
            'previous_errors': ["First attempt failed"],
            'request_id': 'test-67-retry-success'
        }

        result = await step_67__llmsuccess(messages=[], ctx=ctx)

        # Should route to cache even on retry
        assert result['llm_success'] is True
        assert result['next_step'] == 'cache_response'
        assert result['attempt_number'] == 2

        # Verify retry success is logged
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        completed_log = completed_logs[0][1]
        assert completed_log['llm_success'] is True
        assert completed_log['attempt_number'] == 2
        # Verify it's a retry (attempt > 1) and succeeded
        assert completed_log['attempt_number'] > 1 and completed_log['decision'] == 'success'


class TestRAGStep67Parity:
    """Parity tests proving Step 67 preserves existing behavior."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    async def test_step_67_parity_success_behavior(self, mock_rag_log):
        """Test Step 67: Parity test for success path."""
        from app.orchestrators.llm import step_67__llmsuccess

        llm_response = LLMResponse(
            content="Test response",
            tool_calls=[],
            cost_estimate=0.001,
            model="gpt-3.5-turbo",
            provider="openai"
        )

        # Original behavior: if response exists, it's a success
        original_success = llm_response is not None

        # Orchestrator behavior
        ctx = {
            'llm_response': llm_response,
            'request_id': 'test-67-parity'
        }

        result = await step_67__llmsuccess(messages=[], ctx=ctx)

        # Verify identical decision logic
        assert result['llm_success'] == original_success
        assert result['has_response'] == (llm_response is not None)

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    async def test_step_67_parity_failure_behavior(self, mock_rag_log):
        """Test Step 67: Parity test for failure path."""
        from app.orchestrators.llm import step_67__llmsuccess

        # Original behavior: if response is None or exception, it's a failure
        llm_response = None
        original_success = llm_response is not None

        # Orchestrator behavior
        ctx = {
            'llm_response': llm_response,
            'error': "API error",
            'exception': Exception("API error"),
            'request_id': 'test-67-parity-fail'
        }

        result = await step_67__llmsuccess(messages=[], ctx=ctx)

        # Verify identical decision logic
        assert result['llm_success'] == original_success
        assert result['has_response'] == (llm_response is not None)