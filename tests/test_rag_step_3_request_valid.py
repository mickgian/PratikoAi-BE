#!/usr/bin/env python3
"""
Tests for RAG STEP 3 — Request valid?

This step validates if the incoming request meets basic requirements.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.orchestrators.platform import step_3__valid_check


class TestRAGStep3RequestValid:
    """Test suite for RAG STEP 3 - Request valid?"""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_3_valid_request(self, mock_logger, mock_rag_log):
        """Test Step 3: Valid request with all required fields"""

        ctx = {
            'request_body': {'query': 'What are the tax rates?', 'user_id': 'user123'},
            'content_type': 'application/json',
            'method': 'POST',
            'authenticated': True,
            'user_id': 'user123'
        }

        # Call the orchestrator function
        result = step_3__valid_check(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result['is_valid'] is True
        assert result['validation_errors'] == []
        assert result['request_type'] == 'chat_query'
        assert 'timestamp' in result

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert 'Request validation completed' in log_call[0][0]
        assert log_call[1]['extra']['validation_event'] == 'request_validated'
        assert log_call[1]['extra']['is_valid'] is True

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]
        assert len(completed_logs) > 0
        completed_log = completed_logs[0]
        assert completed_log[1]['step'] == 3
        assert completed_log[1]['validation_event'] == 'request_validated'
        assert completed_log[1]['is_valid'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_3_invalid_request_missing_query(self, mock_logger, mock_rag_log):
        """Test Step 3: Invalid request missing query"""

        ctx = {
            'request_body': {'user_id': 'user123'},  # Missing query
            'content_type': 'application/json',
            'method': 'POST',
            'authenticated': True
        }

        # Call the orchestrator function
        result = step_3__valid_check(ctx=ctx)

        # Verify invalid result
        assert result['is_valid'] is False
        assert 'Missing required field: query' in result['validation_errors']

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert 'Request validation failed' in warning_call[0][0]

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_3_invalid_content_type(self, mock_logger, mock_rag_log):
        """Test Step 3: Invalid content type"""

        ctx = {
            'request_body': {'query': 'Test query'},
            'content_type': 'text/plain',  # Invalid content type
            'method': 'POST',
            'authenticated': True
        }

        # Call the orchestrator function
        result = step_3__valid_check(ctx=ctx)

        # Verify invalid result
        assert result['is_valid'] is False
        assert 'Invalid content type' in str(result['validation_errors'])

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_3_unauthenticated_request(self, mock_logger, mock_rag_log):
        """Test Step 3: Unauthenticated request"""

        ctx = {
            'request_body': {'query': 'Test query'},
            'content_type': 'application/json',
            'method': 'POST',
            'authenticated': False  # Not authenticated
        }

        # Call the orchestrator function
        result = step_3__valid_check(ctx=ctx)

        # Verify invalid result
        assert result['is_valid'] is False
        assert 'Request not authenticated' in result['validation_errors']

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_3_empty_context(self, mock_logger, mock_rag_log):
        """Test Step 3: Handle empty context gracefully"""

        # Call with minimal context
        result = step_3__valid_check()

        # Verify defaults are used
        assert isinstance(result, dict)
        assert result['is_valid'] is False
        assert len(result['validation_errors']) > 0
        assert result['request_type'] == 'unknown'

        # Verify logging still occurs
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_3_kwargs_parameters(self, mock_logger, mock_rag_log):
        """Test Step 3: Parameters passed via kwargs"""

        # Call with kwargs instead of ctx
        result = step_3__valid_check(
            request_body={'query': 'Test query'},
            content_type='application/json',
            method='POST',
            authenticated=True
        )

        # Verify kwargs are processed correctly
        assert result['is_valid'] is True
        assert result['validation_errors'] == []

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_3_invalid_method(self, mock_logger, mock_rag_log):
        """Test Step 3: Invalid HTTP method"""

        ctx = {
            'request_body': {'query': 'Test query'},
            'content_type': 'application/json',
            'method': 'GET',  # Invalid method for chat
            'authenticated': True
        }

        # Call the orchestrator function
        result = step_3__valid_check(ctx=ctx)

        # Verify invalid result
        assert result['is_valid'] is False
        assert 'Invalid HTTP method' in str(result['validation_errors'])

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_3_malformed_request_body(self, mock_logger, mock_rag_log):
        """Test Step 3: Malformed request body"""

        ctx = {
            'request_body': None,  # Malformed body
            'content_type': 'application/json',
            'method': 'POST',
            'authenticated': True
        }

        # Call the orchestrator function
        result = step_3__valid_check(ctx=ctx)

        # Verify invalid result
        assert result['is_valid'] is False
        assert 'Missing or invalid request body' in result['validation_errors']

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_3_performance_tracking(self, mock_logger, mock_rag_log):
        """Test Step 3: Performance tracking with timer"""

        with patch('app.orchestrators.platform.rag_step_timer') as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Call the orchestrator function
            step_3__valid_check(ctx={'request_body': {'query': 'test'}})

            # Verify timer was used
            mock_timer.assert_called_with(
                3,
                'RAG.platform.request.valid',
                'ValidCheck',
                stage='start'
            )

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_3_comprehensive_logging_format(self, mock_logger, mock_rag_log):
        """Test Step 3: Verify comprehensive logging format"""

        ctx = {
            'request_body': {'query': 'Test query'},
            'content_type': 'application/json',
            'method': 'POST',
            'authenticated': True
        }

        # Call the orchestrator function
        step_3__valid_check(ctx=ctx)

        # Verify RAG step logging format
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            'step', 'step_id', 'node_label', 'validation_event',
            'is_valid', 'validation_errors', 'request_type', 'processing_stage'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]['step'] == 3
        assert log_call[1]['step_id'] == 'RAG.platform.request.valid'
        assert log_call[1]['node_label'] == 'ValidCheck'
        assert log_call[1]['validation_event'] == 'request_validated'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_3_validation_data_structure(self, mock_logger, mock_rag_log):
        """Test Step 3: Verify validation data structure"""

        ctx = {
            'request_body': {'query': 'Test query'},
            'content_type': 'application/json',
            'method': 'POST',
            'authenticated': True
        }

        # Call the orchestrator function
        result = step_3__valid_check(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            'timestamp', 'is_valid', 'validation_errors', 'request_type'
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in validation data: {field}"

        # Verify data types
        assert isinstance(result['timestamp'], str)
        assert isinstance(result['is_valid'], bool)
        assert isinstance(result['validation_errors'], list)
        assert isinstance(result['request_type'], str)

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00'))