#!/usr/bin/env python3
"""
Tests for RAG STEP 2 — User submits query via POST /api/v1/chat

This step represents the entry point where users submit queries.
It's a startEnd type node that initiates the RAG workflow.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestRAGStep2Start:
    """Test suite for RAG STEP 2 - User submits query via POST"""

    @pytest.fixture
    def mock_chat_request(self):
        """Mock chat request data."""
        return {
            "messages": [
                {"role": "user", "content": "What are Italian tax regulations for freelancers?"}
            ],
            "user_id": 123
        }

    @pytest.fixture
    def mock_request_context(self):
        """Mock HTTP request context."""
        return {
            'method': 'POST',
            'url': '/api/v1/chat',
            'content_type': 'application/json',
            'user_agent': 'PratikoAI-Client/1.0',
            'request_id': 'req_456',
            'timestamp': '2024-01-01T10:00:00Z'
        }

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_2_successful_start(self, mock_logger, mock_rag_log, mock_chat_request, mock_request_context):
        """Test Step 2: Successful workflow start"""
        from app.orchestrators.platform import step_2__start

        # Context with valid request data
        ctx = {
            'request_body': mock_chat_request,
            'request_context': mock_request_context,
            'session_id': 'session_123',
            'user_id': 123
        }

        # Call the orchestrator function
        result = step_2__start(ctx=ctx)

        # Verify result structure
        assert isinstance(result, dict)
        assert result['workflow_started'] is True
        assert result['request_received'] is True
        assert result['entry_point'] == 'chat_api'
        assert result['next_step'] == 'ValidateRequest'
        assert 'workflow_context' in result
        assert 'request_metadata' in result

        # Verify request metadata is preserved
        assert result['request_metadata']['method'] == 'POST'
        assert result['request_metadata']['url'] == '/api/v1/chat'
        assert result['request_metadata']['request_id'] == 'req_456'

        # Verify workflow context
        assert result['workflow_context']['messages'] == mock_chat_request['messages']
        assert result['workflow_context']['user_id'] == 123
        assert result['workflow_context']['session_id'] == 'session_123'

        # Verify logging
        mock_logger.info.assert_called()
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any('RAG workflow started' in call for call in log_calls)

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]
        assert len(completed_logs) > 0
        log_call = completed_logs[0]
        assert log_call[1]['step'] == 2
        assert log_call[1]['workflow_started'] is True
        assert log_call[1]['entry_point'] == 'chat_api'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_2_minimal_context(self, mock_logger, mock_rag_log, mock_chat_request):
        """Test Step 2: Start with minimal context"""
        from app.orchestrators.platform import step_2__start

        # Minimal context
        ctx = {
            'request_body': mock_chat_request
        }

        result = step_2__start(ctx=ctx)

        # Should still start successfully with defaults
        assert result['workflow_started'] is True
        assert result['request_received'] is True
        assert result['entry_point'] == 'chat_api'
        assert result['next_step'] == 'ValidateRequest'

        # Should have default values
        assert 'req_' in result['request_metadata']['request_id']
        assert result['request_metadata']['method'] == 'POST'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_2_empty_context(self, mock_logger, mock_rag_log):
        """Test Step 2: Handle empty context gracefully"""
        from app.orchestrators.platform import step_2__start

        # Call with no context
        result = step_2__start()

        # Should still start but indicate missing data
        assert result['workflow_started'] is True
        assert result['request_received'] is False
        assert result['entry_point'] == 'chat_api'
        assert result['next_step'] == 'ValidateRequest'
        assert 'No request body provided' in result['warning']

        # Verify warning logged
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_2_kwargs_parameters(self, mock_logger, mock_rag_log, mock_chat_request):
        """Test Step 2: Parameters passed via kwargs"""
        from app.orchestrators.platform import step_2__start

        # Call with kwargs instead of ctx
        result = step_2__start(
            request_body=mock_chat_request,
            session_id='session_456',
            user_id=789
        )

        # Verify kwargs are processed correctly
        assert result['workflow_started'] is True
        assert result['workflow_context']['user_id'] == 789
        assert result['workflow_context']['session_id'] == 'session_456'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_2_ready_for_step_1(self, mock_logger, mock_rag_log, mock_chat_request, mock_request_context):
        """Test Step 2: Output ready for Step 1 (ValidateRequest)"""
        from app.orchestrators.platform import step_2__start

        ctx = {
            'request_body': mock_chat_request,
            'request_context': mock_request_context,
            'session_id': 'session_123'
        }

        result = step_2__start(ctx=ctx)

        # Verify output is ready for Step 1
        assert result['ready_for_validation'] is True
        assert 'workflow_context' in result
        assert 'request_metadata' in result
        assert result['next_step'] == 'ValidateRequest'

        # These fields needed for Step 1 validation
        assert result['workflow_context'] is not None
        assert result['request_metadata'] is not None
        assert 'messages' in result['workflow_context']

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_2_different_request_types(self, mock_logger, mock_rag_log):
        """Test Step 2: Handle different request types"""
        from app.orchestrators.platform import step_2__start

        # Test with different message types
        streaming_request = {
            "messages": [
                {"role": "user", "content": "Explain tax deductions"},
                {"role": "assistant", "content": "Tax deductions are..."},
                {"role": "user", "content": "Can you elaborate?"}
            ],
            "stream": True,
            "user_id": 456
        }

        ctx = {
            'request_body': streaming_request,
            'request_context': {'url': '/api/v1/chat/stream'}
        }

        result = step_2__start(ctx=ctx)

        # Should handle streaming requests
        assert result['workflow_started'] is True
        assert result['workflow_context']['stream'] is True
        assert len(result['workflow_context']['messages']) == 3

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_2_comprehensive_logging(self, mock_logger, mock_rag_log, mock_chat_request, mock_request_context):
        """Test Step 2: Comprehensive logging format"""
        from app.orchestrators.platform import step_2__start

        ctx = {
            'request_body': mock_chat_request,
            'request_context': mock_request_context,
            'session_id': 'session_123'
        }

        step_2__start(ctx=ctx)

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            'step', 'step_id', 'node_label',
            'workflow_started', 'request_received', 'entry_point',
            'processing_stage', 'next_step'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing field: {field}"

        assert log_call[1]['step'] == 2
        assert log_call[1]['step_id'] == 'RAG.platform.user.submits.query.via.post.api.v1.chat'
        assert log_call[1]['node_label'] == 'Start'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_2_performance_tracking(self, mock_logger, mock_rag_log, mock_chat_request):
        """Test Step 2: Performance tracking with timer"""
        from app.orchestrators.platform import step_2__start

        with patch('app.orchestrators.platform.rag_step_timer') as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            ctx = {'request_body': mock_chat_request}
            step_2__start(ctx=ctx)

            # Verify timer was used
            mock_timer.assert_called_with(
                2,
                'RAG.platform.user.submits.query.via.post.api.v1.chat',
                'Start',
                stage='start'
            )

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_2_workflow_initialization(self, mock_logger, mock_rag_log, mock_chat_request, mock_request_context):
        """Test Step 2: Proper workflow initialization"""
        from app.orchestrators.platform import step_2__start

        ctx = {
            'request_body': mock_chat_request,
            'request_context': mock_request_context,
            'session_id': 'session_789',
            'user_id': 999
        }

        result = step_2__start(ctx=ctx)

        # Verify workflow is properly initialized
        assert result['workflow_started'] is True
        assert result['entry_point'] == 'chat_api'
        assert result['workflow_context']['initialized'] is True

        # Verify all necessary data is preserved for downstream steps
        assert result['workflow_context']['session_id'] == 'session_789'
        assert result['workflow_context']['user_id'] == 999
        assert result['workflow_context']['messages'] == mock_chat_request['messages']

        # Verify request metadata
        assert result['request_metadata']['method'] == 'POST'
        assert result['request_metadata']['url'] == '/api/v1/chat'
        assert result['request_metadata']['request_id'] == 'req_456'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_2_message_count_tracking(self, mock_logger, mock_rag_log, mock_request_context):
        """Test Step 2: Message count tracking"""
        from app.orchestrators.platform import step_2__start

        # Test with multiple messages
        multi_message_request = {
            "messages": [
                {"role": "user", "content": "First message"},
                {"role": "assistant", "content": "Response"},
                {"role": "user", "content": "Follow up"},
                {"role": "assistant", "content": "Another response"},
                {"role": "user", "content": "Final question"}
            ],
            "user_id": 123
        }

        ctx = {
            'request_body': multi_message_request,
            'request_context': mock_request_context
        }

        result = step_2__start(ctx=ctx)

        # Verify message count is tracked
        assert result['workflow_context']['message_count'] == 5
        assert len(result['workflow_context']['messages']) == 5

        # Verify logging includes message count
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]
        log_call = completed_logs[0]
        assert log_call[1]['message_count'] == 5