#!/usr/bin/env python3
"""
Tests for RAG STEP 10 — Log PII anonymization

This step logs PII anonymization events for audit trail and GDPR compliance.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.orchestrators.platform import step_10__log_pii


class TestRAGStep10LogPII:
    """Test suite for RAG STEP 10 - Log PII anonymization"""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_10_log_pii_detected(self, mock_logger, mock_rag_log):
        """Test Step 10: Log PII anonymization when PII is detected"""

        # Mock PII anonymization result
        anonymization_result = MagicMock()
        anonymization_result.pii_matches = [
            MagicMock(pii_type=MagicMock(value='email')),
            MagicMock(pii_type=MagicMock(value='phone'))
        ]

        ctx = {
            'anonymization_result': anonymization_result,
            'user_query': 'Please contact me at john@example.com or 555-1234',
            'pii_detected': True,
            'pii_types': ['email', 'phone'],
            'anonymization_method': 'hash'
        }

        # Call the orchestrator function
        result = step_10__log_pii(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result['pii_detected'] is True
        assert result['pii_types'] == ['email', 'phone']
        assert result['anonymized_count'] == 2
        assert result['anonymization_method'] == 'hash'
        assert result['privacy_compliance'] is True
        assert 'timestamp' in result

        # Verify structured logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert 'PII anonymization completed' in log_call[0]
        assert log_call[1]['extra']['audit_event'] == 'pii_anonymization'
        assert log_call[1]['extra']['pii_detected'] is True
        assert log_call[1]['extra']['gdpr_compliance'] is True

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]
        assert len(completed_logs) > 0
        completed_log = completed_logs[0]
        assert completed_log[1]['step'] == 10
        assert completed_log[1]['audit_event'] == 'pii_anonymization'
        assert completed_log[1]['pii_detected'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_10_no_pii_detected(self, mock_logger, mock_rag_log):
        """Test Step 10: Log when no PII is detected"""

        ctx = {
            'user_query': 'What is the weather today?',
            'pii_detected': False,
            'pii_types': [],
            'anonymization_method': 'none'
        }

        # Call the orchestrator function
        result = step_10__log_pii(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result['pii_detected'] is False
        assert result['pii_types'] == []
        assert result['anonymized_count'] == 0
        assert result['anonymization_method'] == 'none'
        assert result['privacy_compliance'] is True

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert log_call[1]['extra']['pii_detected'] is False
        assert log_call[1]['extra']['anonymized_count'] == 0

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_10_dict_anonymization_result(self, mock_logger, mock_rag_log):
        """Test Step 10: Handle dictionary-format anonymization result"""

        anonymization_result = {
            'matches_count': 3,
            'pii_types': ['email', 'phone', 'name']
        }

        ctx = {
            'anonymization_result': anonymization_result,
            'user_query': 'Contact John Doe at john@example.com or 555-1234',
            'pii_detected': True,
            'anonymization_method': 'mask'
        }

        # Call the orchestrator function
        result = step_10__log_pii(ctx=ctx)

        # Verify the result
        assert result['anonymized_count'] == 3
        assert result['pii_types'] == ['email', 'phone', 'name']
        assert result['anonymization_method'] == 'mask'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_10_empty_context(self, mock_logger, mock_rag_log):
        """Test Step 10: Handle empty context gracefully"""

        # Call with minimal context
        result = step_10__log_pii()

        # Verify defaults are used
        assert isinstance(result, dict)
        assert result['pii_detected'] is False
        assert result['pii_types'] == []
        assert result['anonymized_count'] == 0
        assert result['anonymization_method'] == 'hash'
        assert result['query_length'] == 0

        # Verify logging still occurs
        mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_10_kwargs_parameters(self, mock_logger, mock_rag_log):
        """Test Step 10: Parameters passed via kwargs"""

        # Call with kwargs instead of ctx
        result = step_10__log_pii(
            user_query='Test query with PII',
            pii_detected=True,
            pii_types=['codice_fiscale'],
            anonymization_method='encrypt'
        )

        # Verify kwargs are processed correctly
        assert result['pii_detected'] is True
        assert result['pii_types'] == ['codice_fiscale']
        assert result['anonymization_method'] == 'encrypt'
        assert result['query_length'] == len('Test query with PII')

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_10_comprehensive_logging_format(self, mock_logger, mock_rag_log):
        """Test Step 10: Verify comprehensive logging format"""

        ctx = {
            'user_query': 'Test query',
            'pii_detected': True,
            'pii_types': ['email'],
            'anonymization_method': 'hash'
        }

        # Call the orchestrator function
        step_10__log_pii(ctx=ctx)

        # Verify RAG step logging format
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            'step', 'step_id', 'node_label', 'audit_event',
            'pii_detected', 'pii_types', 'anonymized_count',
            'anonymization_method', 'query_length', 'privacy_compliance',
            'processing_stage'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]['step'] == 10
        assert log_call[1]['step_id'] == 'RAG.platform.logger.info.log.pii.anonymization'
        assert log_call[1]['node_label'] == 'LogPII'
        assert log_call[1]['audit_event'] == 'pii_anonymization'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_10_performance_tracking(self, mock_logger, mock_rag_log):
        """Test Step 10: Performance tracking with timer"""

        with patch('app.orchestrators.platform.rag_step_timer') as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Call the orchestrator function
            step_10__log_pii(ctx={'pii_detected': False})

            # Verify timer was used
            mock_timer.assert_called_with(
                10,
                'RAG.platform.logger.info.log.pii.anonymization',
                'LogPII',
                stage='start'
            )

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_10_audit_data_structure(self, mock_logger, mock_rag_log):
        """Test Step 10: Verify audit data structure"""

        ctx = {
            'user_query': 'Contact me at test@example.com',
            'pii_detected': True,
            'pii_types': ['email'],
            'anonymization_method': 'hash'
        }

        # Call the orchestrator function
        result = step_10__log_pii(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            'timestamp', 'pii_detected', 'pii_types', 'anonymization_method',
            'query_length', 'anonymized_count', 'privacy_compliance'
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in audit data: {field}"

        # Verify data types
        assert isinstance(result['timestamp'], str)
        assert isinstance(result['pii_detected'], bool)
        assert isinstance(result['pii_types'], list)
        assert isinstance(result['anonymization_method'], str)
        assert isinstance(result['query_length'], int)
        assert isinstance(result['anonymized_count'], int)
        assert isinstance(result['privacy_compliance'], bool)

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00'))