#!/usr/bin/env python3
"""
Tests for RAG STEP 1 — ChatbotController.chat Validate request and authenticate

This step validates incoming requests and performs authentication.
Connects to Step 3 (ValidCheck) for request validation flow.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models.session import Session
from app.models.user import User


class TestRAGStep1ValidateRequest:
    """Test suite for RAG STEP 1 - Validate request and authenticate"""

    @pytest.fixture
    def mock_session(self):
        """Mock session object."""
        session = MagicMock(spec=Session)
        session.id = "test_session_123"
        session.user_id = 123
        session.created_at = "2024-01-01T00:00:00Z"
        return session

    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = MagicMock(spec=User)
        user.id = 123
        user.email = "test@example.com"
        user.is_active = True
        return user

    @pytest.fixture
    def mock_chat_request(self):
        """Mock chat request data."""
        return {
            "messages": [
                {"role": "user", "content": "Calculate my tax deductions"}
            ],
            "user_id": 123
        }

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.api.v1.auth.get_current_session')
    @patch('app.api.v1.auth.get_current_user')
    async def test_step_1_successful_validation_and_auth(self, mock_get_user, mock_get_session, mock_logger, mock_rag_log, mock_session, mock_user, mock_chat_request):
        """Test Step 1: Successful request validation and authentication"""
        from app.orchestrators.platform import step_1__validate_request

        # Mock authentication dependencies
        mock_get_session.return_value = mock_session
        mock_get_user.return_value = mock_user

        # Context with valid request data
        ctx = {
            'request_body': mock_chat_request,
            'content_type': 'application/json',
            'method': 'POST',
            'authorization_header': 'Bearer valid_token_123',
            'request_id': 'req_123'
        }

        # Call the orchestrator function
        result = await step_1__validate_request(ctx=ctx)

        # Verify result structure
        assert isinstance(result, dict)
        assert result['validation_successful'] is True
        assert result['authentication_successful'] is True
        assert result['session'] == mock_session
        assert result['user'] == mock_user
        assert result['request_valid'] is True
        assert 'validated_request' in result
        assert result['next_step'] == 'ValidCheck'

        # Verify logging
        mock_logger.info.assert_called()
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any('Request validation and authentication completed' in call for call in log_calls)

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]
        assert len(completed_logs) > 0
        log_call = completed_logs[0]
        assert log_call[1]['step'] == 1
        assert log_call[1]['validation_successful'] is True
        assert log_call[1]['authentication_successful'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_1_missing_authorization_header(self, mock_logger, mock_rag_log, mock_chat_request):
        """Test Step 1: Missing authorization header"""
        from app.orchestrators.platform import step_1__validate_request

        ctx = {
            'request_body': mock_chat_request,
            'content_type': 'application/json',
            'method': 'POST',
            # Missing authorization_header
        }

        result = await step_1__validate_request(ctx=ctx)

        # Should fail authentication
        assert result['validation_successful'] is False
        assert result['authentication_successful'] is False
        assert result['error'] == 'Missing authorization header'
        assert result['next_step'] == 'Error400'

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.api.v1.auth.get_current_session')
    async def test_step_1_invalid_token(self, mock_get_session, mock_logger, mock_rag_log, mock_chat_request):
        """Test Step 1: Invalid authentication token"""
        from app.orchestrators.platform import step_1__validate_request

        # Mock invalid token - authentication fails
        mock_get_session.side_effect = Exception("Invalid token")

        ctx = {
            'request_body': mock_chat_request,
            'content_type': 'application/json',
            'method': 'POST',
            'authorization_header': 'Bearer invalid_token'
        }

        result = await step_1__validate_request(ctx=ctx)

        # Should fail authentication
        assert result['validation_successful'] is False
        assert result['authentication_successful'] is False
        assert 'Invalid token' in result['error']
        assert result['next_step'] == 'Error400'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_1_malformed_request_body(self, mock_logger, mock_rag_log):
        """Test Step 1: Malformed request body"""
        from app.orchestrators.platform import step_1__validate_request

        ctx = {
            'request_body': None,  # Invalid request body
            'content_type': 'application/json',
            'method': 'POST',
            'authorization_header': 'Bearer valid_token'
        }

        result = await step_1__validate_request(ctx=ctx)

        # Should fail validation
        assert result['validation_successful'] is False
        assert result['authentication_successful'] is False
        assert 'Invalid request body' in result['error']
        assert result['next_step'] == 'Error400'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_1_invalid_http_method(self, mock_logger, mock_rag_log, mock_chat_request):
        """Test Step 1: Invalid HTTP method"""
        from app.orchestrators.platform import step_1__validate_request

        ctx = {
            'request_body': mock_chat_request,
            'content_type': 'application/json',
            'method': 'GET',  # Invalid method
            'authorization_header': 'Bearer valid_token'
        }

        result = await step_1__validate_request(ctx=ctx)

        # Should fail validation
        assert result['validation_successful'] is False
        assert 'Invalid HTTP method' in result['error']
        assert result['next_step'] == 'Error400'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.api.v1.auth.get_current_session')
    @patch('app.api.v1.auth.get_current_user')
    async def test_step_1_missing_required_fields(self, mock_get_user, mock_get_session, mock_logger, mock_rag_log, mock_session, mock_user):
        """Test Step 1: Missing required fields in request"""
        from app.orchestrators.platform import step_1__validate_request

        mock_get_session.return_value = mock_session
        mock_get_user.return_value = mock_user

        # Request missing required 'messages' field
        invalid_request = {"user_id": 123}

        ctx = {
            'request_body': invalid_request,
            'content_type': 'application/json',
            'method': 'POST',
            'authorization_header': 'Bearer valid_token'
        }

        result = await step_1__validate_request(ctx=ctx)

        # Should fail validation despite authentication success
        assert result['authentication_successful'] is True
        assert result['validation_successful'] is False
        assert 'Missing required field: messages' in result['error']
        assert result['next_step'] == 'Error400'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.api.v1.auth.get_current_session')
    @patch('app.api.v1.auth.get_current_user')
    async def test_step_1_invalid_content_type(self, mock_get_user, mock_get_session, mock_logger, mock_rag_log, mock_session, mock_user, mock_chat_request):
        """Test Step 1: Invalid content type"""
        from app.orchestrators.platform import step_1__validate_request

        mock_get_session.return_value = mock_session
        mock_get_user.return_value = mock_user

        ctx = {
            'request_body': mock_chat_request,
            'content_type': 'text/plain',  # Invalid content type
            'method': 'POST',
            'authorization_header': 'Bearer valid_token'
        }

        result = await step_1__validate_request(ctx=ctx)

        # Should fail validation
        assert result['authentication_successful'] is True
        assert result['validation_successful'] is False
        assert 'Invalid content type' in result['error']

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_1_empty_context(self, mock_logger, mock_rag_log):
        """Test Step 1: Handle empty context gracefully"""
        from app.orchestrators.platform import step_1__validate_request

        # Call with no context
        result = await step_1__validate_request()

        # Should fail validation
        assert result['validation_successful'] is False
        assert result['authentication_successful'] is False
        assert 'Missing request context' in result['error']
        assert result['next_step'] == 'Error400'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.api.v1.auth.get_current_session')
    @patch('app.api.v1.auth.get_current_user')
    async def test_step_1_ready_for_step_3(self, mock_get_user, mock_get_session, mock_logger, mock_rag_log, mock_session, mock_user, mock_chat_request):
        """Test Step 1: Output ready for Step 3 (ValidCheck)"""
        from app.orchestrators.platform import step_1__validate_request

        mock_get_session.return_value = mock_session
        mock_get_user.return_value = mock_user

        ctx = {
            'request_body': mock_chat_request,
            'content_type': 'application/json',
            'method': 'POST',
            'authorization_header': 'Bearer valid_token'
        }

        result = await step_1__validate_request(ctx=ctx)

        # Verify output is ready for Step 3
        assert result['ready_for_validation'] is True
        assert 'validated_request' in result
        assert 'session' in result
        assert 'user' in result
        assert result['next_step'] == 'ValidCheck'

        # These fields needed for Step 3 validation
        assert result['validated_request'] is not None
        assert result['session'] == mock_session
        assert result['user'] == mock_user

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.api.v1.auth.get_current_session')
    @patch('app.api.v1.auth.get_current_user')
    async def test_step_1_comprehensive_logging(self, mock_get_user, mock_get_session, mock_logger, mock_rag_log, mock_session, mock_user, mock_chat_request):
        """Test Step 1: Comprehensive logging format"""
        from app.orchestrators.platform import step_1__validate_request

        mock_get_session.return_value = mock_session
        mock_get_user.return_value = mock_user

        ctx = {
            'request_body': mock_chat_request,
            'content_type': 'application/json',
            'method': 'POST',
            'authorization_header': 'Bearer valid_token',
            'request_id': 'req_123'
        }

        await step_1__validate_request(ctx=ctx)

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
            'validation_successful', 'authentication_successful',
            'processing_stage', 'session_id', 'user_id'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing field: {field}"

        assert log_call[1]['step'] == 1
        assert log_call[1]['step_id'] == 'RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate'
        assert log_call[1]['node_label'] == 'ValidateRequest'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.api.v1.auth.get_current_session')
    @patch('app.api.v1.auth.get_current_user')
    async def test_step_1_performance_tracking(self, mock_get_user, mock_get_session, mock_logger, mock_rag_log, mock_session, mock_user, mock_chat_request):
        """Test Step 1: Performance tracking with timer"""
        from app.orchestrators.platform import step_1__validate_request

        mock_get_session.return_value = mock_session
        mock_get_user.return_value = mock_user

        with patch('app.orchestrators.platform.rag_step_timer') as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            ctx = {
                'request_body': mock_chat_request,
                'content_type': 'application/json',
                'method': 'POST',
                'authorization_header': 'Bearer valid_token'
            }

            await step_1__validate_request(ctx=ctx)

            # Verify timer was used
            mock_timer.assert_called_with(
                1,
                'RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate',
                'ValidateRequest',
                stage='start'
            )

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.api.v1.auth.get_current_session')
    @patch('app.api.v1.auth.get_current_user')
    async def test_step_1_parity_preservation(self, mock_get_user, mock_get_session, mock_logger, mock_rag_log, mock_session, mock_user, mock_chat_request):
        """Test Step 1: Parity test - behavior identical before/after orchestrator"""
        from app.orchestrators.platform import step_1__validate_request

        mock_get_session.return_value = mock_session
        mock_get_user.return_value = mock_user

        ctx = {
            'request_body': mock_chat_request,
            'content_type': 'application/json',
            'method': 'POST',
            'authorization_header': 'Bearer valid_token'
        }

        # Call orchestrator
        result = await step_1__validate_request(ctx=ctx)

        # Verify behavior matches expected ChatbotController.chat validation
        assert result['validation_successful'] is True
        assert result['authentication_successful'] is True
        assert result['session'] == mock_session
        assert result['user'] == mock_user

        # Verify input request data is preserved
        assert result['validated_request']['messages'] == mock_chat_request['messages']
        assert result['validated_request']['user_id'] == mock_chat_request['user_id']

        # Verify session and user data are preserved
        assert result['session'].id == mock_session.id
        assert result['user'].id == mock_user.id