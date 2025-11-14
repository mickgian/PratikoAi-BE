#!/usr/bin/env python3
"""
Tests for RAG STEP 13 — User message exists?

This step checks if a user message exists in the request for processing.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.orchestrators.platform import step_13__message_exists


class TestRAGStep13UserMessageExists:
    """Test suite for RAG STEP 13 - User message exists?"""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_13_user_message_exists(self, mock_logger, mock_rag_log):
        """Test Step 13: User message found in messages"""

        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant'},
            {'role': 'user', 'content': 'What are the tax rates for 2024?'},
            {'role': 'assistant', 'content': 'I can help with tax information'}
        ]

        ctx = {
            'messages': messages,
            'user_query': 'What are the tax rates for 2024?'
        }

        # Call the orchestrator function
        result = step_13__message_exists(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result['message_exists'] is True
        assert result['user_message_count'] == 1
        assert result['total_message_count'] == 3
        assert result['user_message_content'] == 'What are the tax rates for 2024?'
        assert 'timestamp' in result

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert 'User message check completed' in log_call[0][0]
        assert log_call[1]['extra']['message_event'] == 'user_message_found'
        assert log_call[1]['extra']['message_exists'] is True

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]
        assert len(completed_logs) > 0
        completed_log = completed_logs[0]
        assert completed_log[1]['step'] == 13
        assert completed_log[1]['message_event'] == 'user_message_found'
        assert completed_log[1]['message_exists'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_13_no_user_message(self, mock_logger, mock_rag_log):
        """Test Step 13: No user message found"""

        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant'},
            {'role': 'assistant', 'content': 'How can I help you today?'}
        ]

        ctx = {
            'messages': messages
        }

        # Call the orchestrator function
        result = step_13__message_exists(ctx=ctx)

        # Verify no user message found
        assert result['message_exists'] is False
        assert result['user_message_count'] == 0
        assert result['total_message_count'] == 2
        assert result['user_message_content'] == ''

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert 'No user message found' in warning_call[0][0]

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_13_multiple_user_messages(self, mock_logger, mock_rag_log):
        """Test Step 13: Multiple user messages found"""

        messages = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there!'},
            {'role': 'user', 'content': 'What are tax rates?'},
            {'role': 'assistant', 'content': 'Let me help with that'},
            {'role': 'user', 'content': 'For Italy specifically'}
        ]

        ctx = {
            'messages': messages
        }

        # Call the orchestrator function
        result = step_13__message_exists(ctx=ctx)

        # Should find multiple user messages
        assert result['message_exists'] is True
        assert result['user_message_count'] == 3
        assert result['total_message_count'] == 5
        assert result['user_message_content'] == 'For Italy specifically'  # Latest user message

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_13_empty_messages(self, mock_logger, mock_rag_log):
        """Test Step 13: Empty messages list"""

        ctx = {
            'messages': []
        }

        # Call the orchestrator function
        result = step_13__message_exists(ctx=ctx)

        # Should find no user messages
        assert result['message_exists'] is False
        assert result['user_message_count'] == 0
        assert result['total_message_count'] == 0

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_13_user_query_fallback(self, mock_logger, mock_rag_log):
        """Test Step 13: Use user_query as fallback when no messages"""

        ctx = {
            'user_query': 'Direct query without messages'
        }

        # Call the orchestrator function
        result = step_13__message_exists(ctx=ctx)

        # Should use user_query as fallback
        assert result['message_exists'] is True
        assert result['user_message_count'] == 1  # Fallback count
        assert result['user_message_content'] == 'Direct query without messages'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_13_empty_context(self, mock_logger, mock_rag_log):
        """Test Step 13: Handle empty context gracefully"""

        # Call with minimal context
        result = step_13__message_exists()

        # Verify defaults are used
        assert isinstance(result, dict)
        assert result['message_exists'] is False
        assert result['user_message_count'] == 0
        assert result['total_message_count'] == 0
        assert result['user_message_content'] == ''

        # Verify logging still occurs
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_13_kwargs_parameters(self, mock_logger, mock_rag_log):
        """Test Step 13: Parameters passed via kwargs"""

        messages = [
            {'role': 'user', 'content': 'Test message'}
        ]

        # Call with kwargs instead of ctx
        result = step_13__message_exists(
            messages=messages,
            user_query='Fallback query'
        )

        # Verify kwargs are processed correctly
        assert result['message_exists'] is True
        assert result['user_message_count'] == 1

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_13_malformed_messages(self, mock_logger, mock_rag_log):
        """Test Step 13: Handle malformed message objects"""

        messages = [
            {'role': 'user'},  # Missing content
            {'content': 'Message without role'},  # Missing role
            {'role': 'user', 'content': 'Valid message'},
            None,  # Invalid message
            {'role': 'assistant', 'content': 'Assistant response'}
        ]

        ctx = {
            'messages': messages
        }

        # Call the orchestrator function
        result = step_13__message_exists(ctx=ctx)

        # Should only count valid user messages
        assert result['message_exists'] is True
        assert result['user_message_count'] == 1  # Only the valid user message
        assert result['user_message_content'] == 'Valid message'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_13_case_insensitive_role(self, mock_logger, mock_rag_log):
        """Test Step 13: Case insensitive role matching"""

        messages = [
            {'role': 'USER', 'content': 'Uppercase role'},
            {'role': 'user', 'content': 'Lowercase role'},
            {'role': 'User', 'content': 'Title case role'}
        ]

        ctx = {
            'messages': messages
        }

        # Call the orchestrator function
        result = step_13__message_exists(ctx=ctx)

        # Should find all user messages regardless of case
        assert result['message_exists'] is True
        assert result['user_message_count'] == 3

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_13_performance_tracking(self, mock_logger, mock_rag_log):
        """Test Step 13: Performance tracking with timer"""

        with patch('app.orchestrators.platform.rag_step_timer') as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Call the orchestrator function
            step_13__message_exists(ctx={'messages': []})

            # Verify timer was used
            mock_timer.assert_called_with(
                13,
                'RAG.platform.user.message.exists',
                'MessageExists',
                stage='start'
            )

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_13_comprehensive_logging_format(self, mock_logger, mock_rag_log):
        """Test Step 13: Verify comprehensive logging format"""

        messages = [
            {'role': 'user', 'content': 'Test message'}
        ]

        ctx = {
            'messages': messages
        }

        # Call the orchestrator function
        step_13__message_exists(ctx=ctx)

        # Verify RAG step logging format
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            'step', 'step_id', 'node_label', 'message_event',
            'message_exists', 'user_message_count', 'total_message_count',
            'processing_stage'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]['step'] == 13
        assert log_call[1]['step_id'] == 'RAG.platform.user.message.exists'
        assert log_call[1]['node_label'] == 'MessageExists'
        assert log_call[1]['message_event'] == 'user_message_found'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_13_message_data_structure(self, mock_logger, mock_rag_log):
        """Test Step 13: Verify message existence data structure"""

        messages = [
            {'role': 'user', 'content': 'Test message'}
        ]

        ctx = {
            'messages': messages
        }

        # Call the orchestrator function
        result = step_13__message_exists(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            'timestamp', 'message_exists', 'user_message_count',
            'total_message_count', 'user_message_content'
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in message data: {field}"

        # Verify data types
        assert isinstance(result['timestamp'], str)
        assert isinstance(result['message_exists'], bool)
        assert isinstance(result['user_message_count'], int)
        assert isinstance(result['total_message_count'], int)
        assert isinstance(result['user_message_content'], str)

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00'))