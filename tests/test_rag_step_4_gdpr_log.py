#!/usr/bin/env python3
"""
Tests for RAG STEP 4 — GDPRCompliance.record_processing Log data processing

This step records data processing activities for GDPR compliance.
Receives context from Step 3 (ValidCheck) and logs processing activities.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestRAGStep4GDPRLog:
    """Test suite for RAG STEP 4 - Record processing log"""

    @pytest.fixture
    def mock_session(self):
        """Mock session object."""
        session = MagicMock()
        session.id = "session_123"
        session.user_id = 456
        return session

    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = MagicMock()
        user.id = 456
        user.email = "user@example.com"
        return user

    @pytest.fixture
    def mock_validated_request(self):
        """Mock validated request from Step 3."""
        return {
            "messages": [
                {"role": "user", "content": "What are my tax obligations?"}
            ],
            "user_id": 456
        }

    @pytest.mark.asyncio
    @patch('app.orchestrators.privacy.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.privacy.gdpr.gdpr_compliance')
    async def test_step_4_successful_gdpr_logging(self, mock_gdpr, mock_logger, mock_rag_log, mock_session, mock_user, mock_validated_request):
        """Test Step 4: Successful GDPR data processing logging"""
        from app.orchestrators.privacy import step_4__gdprlog

        # Mock GDPR compliance service
        mock_gdpr.data_processor.record_processing.return_value = {
            'processing_id': 'proc_123',
            'recorded_at': '2024-01-01T10:00:00Z',
            'status': 'recorded'
        }

        # Context from Step 3 (ValidCheck)
        ctx = {
            'validation_result': {
                'is_valid': True,
                'validated_request': mock_validated_request,
                'session': mock_session,
                'user': mock_user
            },
            'request_metadata': {
                'method': 'POST',
                'url': '/api/v1/chat',
                'request_id': 'req_123'
            }
        }

        # Call the orchestrator function
        result = await step_4__gdprlog(ctx=ctx)

        # Verify result structure
        assert isinstance(result, dict)
        assert result['gdpr_logged'] is True
        assert result['processing_recorded'] is True
        assert result['processing_id'] == 'proc_123'
        assert result['next_step'] == 'PrivacyCheck'
        assert 'gdpr_record' in result

        # Verify GDPR service was called correctly
        mock_gdpr.data_processor.record_processing.assert_called_once()
        call_args = mock_gdpr.data_processor.record_processing.call_args

        # Check the parameters passed to GDPR service
        assert call_args[1]['user_id'] == 456
        assert call_args[1]['data_source'] == 'chat_api'
        assert call_args[1]['legal_basis'] == 'Service provision under contract'

        # Verify logging
        mock_logger.info.assert_called()
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any('GDPR processing recorded' in call for call in log_calls)

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]
        assert len(completed_logs) > 0
        log_call = completed_logs[0]
        assert log_call[1]['step'] == 4
        assert log_call[1]['gdpr_logged'] is True
        assert log_call[1]['processing_id'] == 'proc_123'

    @pytest.mark.asyncio
    @patch('app.orchestrators.privacy.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.privacy.gdpr.gdpr_compliance')
    async def test_step_4_gdpr_service_error(self, mock_gdpr, mock_logger, mock_rag_log, mock_session, mock_user, mock_validated_request):
        """Test Step 4: GDPR service error handling"""
        from app.orchestrators.privacy import step_4__gdprlog

        # Mock GDPR service failure
        mock_gdpr.data_processor.record_processing.side_effect = Exception("GDPR service unavailable")

        ctx = {
            'validation_result': {
                'is_valid': True,
                'validated_request': mock_validated_request,
                'session': mock_session,
                'user': mock_user
            }
        }

        result = await step_4__gdprlog(ctx=ctx)

        # Should handle gracefully but mark as failed
        assert result['gdpr_logged'] is False
        assert result['processing_recorded'] is False
        assert 'GDPR service unavailable' in result['error']
        assert result['next_step'] == 'PrivacyCheck'  # Continue despite logging failure

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.privacy.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_4_missing_validation_result(self, mock_logger, mock_rag_log):
        """Test Step 4: Missing validation result from Step 3"""
        from app.orchestrators.privacy import step_4__gdprlog

        ctx = {
            'request_metadata': {'request_id': 'req_123'}
            # Missing validation_result
        }

        result = await step_4__gdprlog(ctx=ctx)

        # Should fail gracefully
        assert result['gdpr_logged'] is False
        assert result['processing_recorded'] is False
        assert 'Missing validation result' in result['error']

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.privacy.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.privacy.gdpr.gdpr_compliance')
    async def test_step_4_invalid_request(self, mock_gdpr, mock_logger, mock_rag_log, mock_session, mock_user):
        """Test Step 4: Handle invalid request from Step 3"""
        from app.orchestrators.privacy import step_4__gdprlog

        # Invalid validation result
        ctx = {
            'validation_result': {
                'is_valid': False,
                'validation_errors': ['Missing required field: messages'],
                'session': mock_session,
                'user': mock_user
            }
        }

        result = await step_4__gdprlog(ctx=ctx)

        # Should skip logging for invalid requests but not fail
        assert result['gdpr_logged'] is False
        assert result['processing_recorded'] is False
        assert result['skip_reason'] == 'invalid_request'
        assert result['next_step'] == 'PrivacyCheck'

        # Should not call GDPR service for invalid requests
        mock_gdpr.data_processor.record_processing.assert_not_called()

    @pytest.mark.asyncio
    @patch('app.orchestrators.privacy.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.privacy.gdpr.gdpr_compliance')
    @patch('app.core.config.settings')
    async def test_step_4_privacy_anonymization_enabled(self, mock_settings, mock_gdpr, mock_logger, mock_rag_log, mock_session, mock_user, mock_validated_request):
        """Test Step 4: GDPR logging with privacy anonymization enabled"""
        from app.orchestrators.privacy import step_4__gdprlog

        # Enable privacy anonymization
        mock_settings.PRIVACY_ANONYMIZE_REQUESTS = True

        mock_gdpr.data_processor.record_processing.return_value = {
            'processing_id': 'proc_456',
            'recorded_at': '2024-01-01T10:00:00Z',
            'anonymized': True
        }

        ctx = {
            'validation_result': {
                'is_valid': True,
                'validated_request': mock_validated_request,
                'session': mock_session,
                'user': mock_user
            }
        }

        result = await step_4__gdprlog(ctx=ctx)

        # Should succeed and note anonymization
        assert result['gdpr_logged'] is True
        assert result['processing_recorded'] is True
        assert result['anonymized'] is True

        # Verify anonymization flag was passed to GDPR service
        call_args = mock_gdpr.data_processor.record_processing.call_args
        assert call_args[1]['anonymized'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.privacy.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.privacy.gdpr.gdpr_compliance')
    async def test_step_4_different_data_categories(self, mock_gdpr, mock_logger, mock_rag_log, mock_session, mock_user):
        """Test Step 4: Different data categories and processing purposes"""
        from app.orchestrators.privacy import step_4__gdprlog

        mock_gdpr.data_processor.record_processing.return_value = {
            'processing_id': 'proc_789',
            'recorded_at': '2024-01-01T10:00:00Z'
        }

        # Request with attachments (different data category)
        request_with_attachments = {
            "messages": [{"role": "user", "content": "Review my documents"}],
            "attachments": [{"filename": "tax_form.pdf", "size": 1024}],
            "user_id": 456
        }

        ctx = {
            'validation_result': {
                'is_valid': True,
                'validated_request': request_with_attachments,
                'session': mock_session,
                'user': mock_user
            }
        }

        result = await step_4__gdprlog(ctx=ctx)

        # Should succeed
        assert result['gdpr_logged'] is True

        # Verify correct data category was used
        call_args = mock_gdpr.data_processor.record_processing.call_args
        # Should use CONTENT category (implementation currently uses CONTENT for all requests)
        assert 'CONTENT' in str(call_args)

    @pytest.mark.asyncio
    @patch('app.orchestrators.privacy.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.privacy.gdpr.gdpr_compliance')
    async def test_step_4_ready_for_step_6(self, mock_gdpr, mock_logger, mock_rag_log, mock_session, mock_user, mock_validated_request):
        """Test Step 4: Output ready for Step 6 (PrivacyCheck)"""
        from app.orchestrators.privacy import step_4__gdprlog

        mock_gdpr.data_processor.record_processing.return_value = {
            'processing_id': 'proc_999',
            'recorded_at': '2024-01-01T10:00:00Z'
        }

        ctx = {
            'validation_result': {
                'is_valid': True,
                'validated_request': mock_validated_request,
                'session': mock_session,
                'user': mock_user
            }
        }

        result = await step_4__gdprlog(ctx=ctx)

        # Verify output is ready for Step 6
        assert result['ready_for_privacy_check'] is True
        assert 'gdpr_record' in result
        assert 'validated_request' in result
        assert result['next_step'] == 'PrivacyCheck'

        # These fields needed for Step 6 privacy checking
        assert result['validated_request'] == mock_validated_request
        assert result['session'] == mock_session
        assert result['user'] == mock_user

    @pytest.mark.asyncio
    @patch('app.orchestrators.privacy.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.privacy.gdpr.gdpr_compliance')
    async def test_step_4_comprehensive_logging(self, mock_gdpr, mock_logger, mock_rag_log, mock_session, mock_user, mock_validated_request):
        """Test Step 4: Comprehensive logging format"""
        from app.orchestrators.privacy import step_4__gdprlog

        mock_gdpr.data_processor.record_processing.return_value = {
            'processing_id': 'proc_comprehensive',
            'recorded_at': '2024-01-01T10:00:00Z'
        }

        ctx = {
            'validation_result': {
                'is_valid': True,
                'validated_request': mock_validated_request,
                'session': mock_session,
                'user': mock_user
            },
            'request_metadata': {'request_id': 'req_comprehensive'}
        }

        await step_4__gdprlog(ctx=ctx)

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
            'gdpr_logged', 'processing_recorded', 'processing_id',
            'processing_stage', 'session_id', 'user_id'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing field: {field}"

        assert log_call[1]['step'] == 4
        assert log_call[1]['step_id'] == 'RAG.privacy.gdprcompliance.record.processing.log.data.processing'
        assert log_call[1]['node_label'] == 'GDPRLog'

    @pytest.mark.asyncio
    @patch('app.orchestrators.privacy.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.privacy.gdpr.gdpr_compliance')
    async def test_step_4_performance_tracking(self, mock_gdpr, mock_logger, mock_rag_log, mock_session, mock_user, mock_validated_request):
        """Test Step 4: Performance tracking with timer"""
        from app.orchestrators.privacy import step_4__gdprlog

        mock_gdpr.data_processor.record_processing.return_value = {'processing_id': 'proc_perf'}

        with patch('app.orchestrators.privacy.rag_step_timer') as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            ctx = {
                'validation_result': {
                    'is_valid': True,
                    'validated_request': mock_validated_request,
                    'session': mock_session,
                    'user': mock_user
                }
            }

            await step_4__gdprlog(ctx=ctx)

            # Verify timer was used
            mock_timer.assert_called_with(
                4,
                'RAG.privacy.gdprcompliance.record.processing.log.data.processing',
                'GDPRLog',
                stage='start'
            )

    @pytest.mark.asyncio
    @patch('app.orchestrators.privacy.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.privacy.gdpr.gdpr_compliance')
    async def test_step_4_parity_preservation(self, mock_gdpr, mock_logger, mock_rag_log, mock_session, mock_user, mock_validated_request):
        """Test Step 4: Parity test - behavior identical to ChatbotController.chat GDPR logging"""
        from app.orchestrators.privacy import step_4__gdprlog

        mock_gdpr.data_processor.record_processing.return_value = {
            'processing_id': 'proc_parity',
            'recorded_at': '2024-01-01T10:00:00Z'
        }

        ctx = {
            'validation_result': {
                'is_valid': True,
                'validated_request': mock_validated_request,
                'session': mock_session,
                'user': mock_user
            }
        }

        result = await step_4__gdprlog(ctx=ctx)

        # Verify behavior matches ChatbotController.chat GDPR logging
        assert result['gdpr_logged'] is True
        assert result['processing_recorded'] is True

        # Verify same parameters are passed as in original implementation
        call_args = mock_gdpr.data_processor.record_processing.call_args
        assert call_args[1]['user_id'] == mock_session.user_id
        assert call_args[1]['data_source'] == 'chat_api'
        assert call_args[1]['legal_basis'] == 'Service provision under contract'

        # Verify data is preserved for next step
        assert result['validated_request'] == mock_validated_request
        assert result['session'] == mock_session
        assert result['user'] == mock_user