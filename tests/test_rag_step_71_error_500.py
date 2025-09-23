"""
Tests for RAG STEP 71 — Return 500 error (RAG.platform.return.500.error)

This error handler step returns a 500 Internal Server Error when all retry attempts
have been exhausted. It logs the failure and provides error details to the caller.
"""

from unittest.mock import patch

import pytest


class TestRAGStep71Error500:
    """Test suite for RAG STEP 71 - Return 500 error handler."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_71_max_retries_exhausted(self, mock_rag_log):
        """Test Step 71: Max retries exhausted - return 500 error."""
        from app.orchestrators.platform import step_71__error500

        ctx = {
            'attempt_number': 3,
            'max_retries': 3,
            'error': 'API timeout',
            'previous_errors': [
                'Attempt 1: Rate limit exceeded',
                'Attempt 2: Connection timeout',
                'Attempt 3: API timeout'
            ],
            'request_id': 'test-71-exhausted'
        }

        result = await step_71__error500(messages=[], ctx=ctx)

        # Verify error response
        assert isinstance(result, dict)
        assert result['error_raised'] is True
        assert result['status_code'] == 500
        assert result['error_type'] == 'max_retries_exhausted'
        assert 'Failed to get a response from the LLM after 3 attempts' in result['error_message']
        assert result['attempt_number'] == 3
        assert result['max_retries'] == 3
        assert result['all_attempts_failed'] is True

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 71
        assert completed_log['node_label'] == 'Error500'
        assert completed_log['error_raised'] is True
        assert completed_log['status_code'] == 500

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_71_with_error_history(self, mock_rag_log):
        """Test Step 71: Return 500 with full error history."""
        from app.orchestrators.platform import step_71__error500

        previous_errors = [
            'Attempt 1: Rate limit exceeded',
            'Attempt 2: Connection timeout',
            'Attempt 3: Service unavailable',
            'Attempt 4: API error'
        ]

        ctx = {
            'attempt_number': 4,
            'max_retries': 4,
            'error': 'API error',
            'previous_errors': previous_errors,
            'request_id': 'test-71-history'
        }

        result = await step_71__error500(messages=[], ctx=ctx)

        # Verify error history is included
        assert result['error_raised'] is True
        assert result['previous_errors'] == previous_errors
        assert result['error_count'] == 4
        assert result['last_error'] == 'API error'

        # Verify logging includes error count
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        completed_log = completed_logs[0][1]
        assert completed_log['error_count'] == 4

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_71_different_max_retries(self, mock_rag_log):
        """Test Step 71: Error message adapts to different max_retries."""
        from app.orchestrators.platform import step_71__error500

        test_cases = [
            (3, 3, '3 attempts'),
            (5, 5, '5 attempts'),
            (1, 1, '1 attempts'),
        ]

        for attempt, max_retries, expected_text in test_cases:
            mock_rag_log.reset_mock()

            ctx = {
                'attempt_number': attempt,
                'max_retries': max_retries,
                'error': 'Test error',
                'request_id': f'test-71-max-{max_retries}'
            }

            result = await step_71__error500(messages=[], ctx=ctx)

            assert result['error_raised'] is True
            assert expected_text in result['error_message']
            assert result['max_retries'] == max_retries

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_71_provider_info(self, mock_rag_log):
        """Test Step 71: Include provider information in error."""
        from app.orchestrators.platform import step_71__error500

        ctx = {
            'attempt_number': 3,
            'max_retries': 3,
            'error': 'Provider error',
            'provider': 'openai',
            'model': 'gpt-4',
            'request_id': 'test-71-provider'
        }

        result = await step_71__error500(messages=[], ctx=ctx)

        # Verify provider metadata is preserved
        assert result['error_raised'] is True
        assert result['provider'] == 'openai'
        assert result['model'] == 'gpt-4'

        # Verify logging includes provider info
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        completed_log = completed_logs[0][1]
        assert completed_log['provider'] == 'openai'
        assert completed_log['model'] == 'gpt-4'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_71_minimal_context(self, mock_rag_log):
        """Test Step 71: Works with minimal context."""
        from app.orchestrators.platform import step_71__error500

        ctx = {
            'error': 'Generic error',
            'request_id': 'test-71-minimal'
        }

        result = await step_71__error500(messages=[], ctx=ctx)

        # Should still create error response with defaults
        assert result['error_raised'] is True
        assert result['status_code'] == 500
        assert result['error_type'] == 'max_retries_exhausted'
        assert 'attempt_number' in result
        assert 'max_retries' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_71_exception_details(self, mock_rag_log):
        """Test Step 71: Capture exception details if provided."""
        from app.orchestrators.platform import step_71__error500

        exception = ValueError("Invalid API key")

        ctx = {
            'attempt_number': 3,
            'max_retries': 3,
            'error': str(exception),
            'exception': exception,
            'request_id': 'test-71-exception'
        }

        result = await step_71__error500(messages=[], ctx=ctx)

        assert result['error_raised'] is True
        assert result['exception_type'] == 'ValueError'
        assert 'Invalid API key' in result['error_message']


class TestRAGStep71Parity:
    """Parity tests proving Step 71 preserves existing error behavior."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_71_parity_exception_message(self, mock_rag_log):
        """Test Step 71: Parity with existing exception message."""
        from app.orchestrators.platform import step_71__error500

        # Original logic from graph.py:801
        # raise Exception(f"Failed to get a response from the LLM after {max_retries} attempts")
        max_retries = 3

        ctx = {
            'attempt_number': max_retries,
            'max_retries': max_retries,
            'error': 'All attempts failed',
            'request_id': 'test-parity-message'
        }

        result = await step_71__error500(messages=[], ctx=ctx)

        # Verify message matches original
        expected_message = f"Failed to get a response from the LLM after {max_retries} attempts"
        assert result['error_raised'] is True
        assert expected_message in result['error_message']

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_71_parity_error_status(self, mock_rag_log):
        """Test Step 71: Parity for 500 status code."""
        from app.orchestrators.platform import step_71__error500

        ctx = {
            'attempt_number': 3,
            'max_retries': 3,
            'error': 'Test error',
            'request_id': 'test-parity-status'
        }

        result = await step_71__error500(messages=[], ctx=ctx)

        # Original behavior: Exception raised (would become 500 in API layer)
        # Our behavior: Return error metadata with status_code 500
        assert result['error_raised'] is True
        assert result['status_code'] == 500
        assert result['error_type'] == 'max_retries_exhausted'


class TestRAGStep71Integration:
    """Integration tests for Step 69 → Step 71 and Step 70 → Step 71 flows."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_69_to_71_integration(self, mock_rag_log):
        """Test Step 69 (retry exhausted) → Step 71 (error 500) integration."""
        from app.orchestrators.platform import step_69__retry_check, step_71__error500

        # Step 69: Check if retry allowed (exhausted)
        step_69_ctx = {
            'attempt_number': 3,
            'max_retries': 3,
            'error': 'Final attempt failed',
            'previous_errors': [
                'Attempt 1: Rate limit',
                'Attempt 2: Timeout',
                'Attempt 3: Final error'
            ],
            'request_id': 'test-integration-69-71'
        }

        step_69_result = await step_69__retry_check(messages=[], ctx=step_69_ctx)

        # Should deny retry and route to error_500
        assert step_69_result['retry_allowed'] is False
        assert step_69_result['next_step'] == 'error_500'
        assert step_69_result['all_attempts_failed'] is True

        # Step 71: Return 500 error
        step_71_ctx = {
            'attempt_number': step_69_result['attempt_number'],
            'max_retries': step_69_result['max_retries'],
            'error': step_69_ctx['error'],
            'previous_errors': step_69_ctx['previous_errors'],
            'request_id': step_69_result['request_id']
        }

        step_71_result = await step_71__error500(messages=[], ctx=step_71_ctx)

        # Should return 500 error
        assert step_71_result['error_raised'] is True
        assert step_71_result['status_code'] == 500
        assert step_71_result['all_attempts_failed'] is True
        assert step_71_result['error_count'] == 3

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_67_to_69_to_71_full_flow(self, mock_rag_log):
        """Test full failure flow: Step 67 → Step 69 → Step 71."""
        from app.orchestrators.llm import step_67__llmsuccess
        from app.orchestrators.platform import step_69__retry_check, step_71__error500

        # Step 67: LLM call failed (final attempt)
        step_67_ctx = {
            'llm_response': None,
            'error': 'Final LLM error',
            'attempt_number': 3,
            'max_retries': 3,
            'request_id': 'test-full-flow-error'
        }

        step_67_result = await step_67__llmsuccess(messages=[], ctx=step_67_ctx)

        # Should route to retry_check
        assert step_67_result['llm_success'] is False
        assert step_67_result['next_step'] == 'retry_check'

        # Step 69: Check retry (exhausted)
        step_69_ctx = {
            'attempt_number': step_67_result['attempt_number'],
            'max_retries': step_67_result['max_retries'],
            'error': step_67_result['error_message'],
            'request_id': step_67_result['request_id']
        }

        step_69_result = await step_69__retry_check(messages=[], ctx=step_69_ctx)

        # Should route to error_500
        assert step_69_result['retry_allowed'] is False
        assert step_69_result['next_step'] == 'error_500'

        # Step 71: Return 500 error
        step_71_ctx = {
            'attempt_number': step_69_result['attempt_number'],
            'max_retries': step_69_result['max_retries'],
            'error': step_69_ctx['error'],
            'request_id': step_69_result['request_id']
        }

        step_71_result = await step_71__error500(messages=[], ctx=step_71_ctx)

        # Final error response
        assert step_71_result['error_raised'] is True
        assert step_71_result['status_code'] == 500
        assert step_71_result['request_id'] == 'test-full-flow-error'