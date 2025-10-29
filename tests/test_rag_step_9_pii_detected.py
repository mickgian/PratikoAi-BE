#!/usr/bin/env python3
"""
Tests for RAG STEP 9 — PII detected?

This step detects if personally identifiable information is present in the request.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.orchestrators.platform import step_9__piicheck


class TestRAGStep9PIIDetected:
    """Test suite for RAG STEP 9 - PII detected?"""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_9_pii_detected(self, mock_logger, mock_rag_log):
        """Test Step 9: PII detected in query"""

        ctx = {
            'user_query': 'My email is john.doe@company.com and phone is 555-1234',
            'pii_analysis_result': {
                'detected': True,
                'matches': [
                    {'type': 'email', 'value': 'john.doe@company.com', 'confidence': 0.95},
                    {'type': 'phone', 'value': '555-1234', 'confidence': 0.87}
                ]
            },
            'pii_threshold': 0.8
        }

        # Call the orchestrator function
        result = step_9__piicheck(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result['pii_detected'] is True
        assert result['pii_count'] == 2
        assert result['pii_types'] == ['email', 'phone']
        assert result['detection_confidence'] == 0.95  # Highest confidence
        assert 'timestamp' in result

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert 'PII detection completed' in log_call[0][0]
        assert log_call[1]['extra']['pii_event'] == 'pii_detected'
        assert log_call[1]['extra']['pii_detected'] is True

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]
        assert len(completed_logs) > 0
        completed_log = completed_logs[0]
        assert completed_log[1]['step'] == 9
        assert completed_log[1]['pii_event'] == 'pii_detected'
        assert completed_log[1]['pii_detected'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_9_no_pii_detected(self, mock_logger, mock_rag_log):
        """Test Step 9: No PII detected in query"""

        ctx = {
            'user_query': 'What is the weather today?',
            'pii_analysis_result': {
                'detected': False,
                'matches': []
            },
            'pii_threshold': 0.8
        }

        # Call the orchestrator function
        result = step_9__piicheck(ctx=ctx)

        # Verify no PII detected
        assert result['pii_detected'] is False
        assert result['pii_count'] == 0
        assert result['pii_types'] == []
        assert result['detection_confidence'] == 0.0

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert log_call[1]['extra']['pii_detected'] is False

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_9_low_confidence_pii(self, mock_logger, mock_rag_log):
        """Test Step 9: PII detected but below confidence threshold"""

        ctx = {
            'user_query': 'Contact me at maybe-email@test',
            'pii_analysis_result': {
                'detected': True,
                'matches': [
                    {'type': 'email', 'value': 'maybe-email@test', 'confidence': 0.65}
                ]
            },
            'pii_threshold': 0.8  # Higher than detected confidence
        }

        # Call the orchestrator function
        result = step_9__piicheck(ctx=ctx)

        # Should not count low-confidence matches
        assert result['pii_detected'] is False
        assert result['pii_count'] == 0
        assert result['detection_confidence'] == 0.65  # Still report the confidence

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_9_mixed_confidence_pii(self, mock_logger, mock_rag_log):
        """Test Step 9: Mixed confidence PII matches"""

        ctx = {
            'user_query': 'Email john@company.com or maybe call 123',
            'pii_analysis_result': {
                'detected': True,
                'matches': [
                    {'type': 'email', 'value': 'john@company.com', 'confidence': 0.95},
                    {'type': 'phone', 'value': '123', 'confidence': 0.45}
                ]
            },
            'pii_threshold': 0.8
        }

        # Call the orchestrator function
        result = step_9__piicheck(ctx=ctx)

        # Should only count high-confidence matches
        assert result['pii_detected'] is True
        assert result['pii_count'] == 1  # Only email above threshold
        assert result['pii_types'] == ['email']

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_9_empty_context(self, mock_logger, mock_rag_log):
        """Test Step 9: Handle empty context gracefully"""

        # Call with minimal context
        result = step_9__piicheck()

        # Verify defaults are used
        assert isinstance(result, dict)
        assert result['pii_detected'] is False
        assert result['pii_count'] == 0
        assert result['pii_types'] == []
        assert result['query_length'] == 0

        # Verify logging still occurs
        mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_9_kwargs_parameters(self, mock_logger, mock_rag_log):
        """Test Step 9: Parameters passed via kwargs"""

        # Call with kwargs instead of ctx
        result = step_9__piicheck(
            user_query='Test query with email test@example.com',
            pii_detected=True,
            pii_types=['email']
        )

        # Verify kwargs are processed correctly
        assert result['pii_detected'] is True
        assert result['pii_types'] == ['email']

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_9_custom_threshold(self, mock_logger, mock_rag_log):
        """Test Step 9: Custom PII detection threshold"""

        ctx = {
            'user_query': 'Maybe email: test@example',
            'pii_analysis_result': {
                'detected': True,
                'matches': [
                    {'type': 'email', 'value': 'test@example', 'confidence': 0.75}
                ]
            },
            'pii_threshold': 0.7  # Lower threshold
        }

        # Call the orchestrator function
        result = step_9__piicheck(ctx=ctx)

        # Should detect with lower threshold
        assert result['pii_detected'] is True
        assert result['pii_count'] == 1

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_9_multiple_pii_types(self, mock_logger, mock_rag_log):
        """Test Step 9: Multiple types of PII detected"""

        ctx = {
            'user_query': 'Contact John Doe at john@company.com, phone 555-1234, SSN 123-45-6789',
            'pii_analysis_result': {
                'detected': True,
                'matches': [
                    {'type': 'email', 'value': 'john@company.com', 'confidence': 0.98},
                    {'type': 'phone', 'value': '555-1234', 'confidence': 0.92},
                    {'type': 'ssn', 'value': '123-45-6789', 'confidence': 0.85},
                    {'type': 'name', 'value': 'John Doe', 'confidence': 0.88}
                ]
            },
            'pii_threshold': 0.8
        }

        # Call the orchestrator function
        result = step_9__piicheck(ctx=ctx)

        # All should be above threshold
        assert result['pii_detected'] is True
        assert result['pii_count'] == 4
        assert set(result['pii_types']) == {'email', 'phone', 'ssn', 'name'}
        assert result['detection_confidence'] == 0.98  # Highest confidence

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_9_performance_tracking(self, mock_logger, mock_rag_log):
        """Test Step 9: Performance tracking with timer"""

        with patch('app.orchestrators.platform.rag_step_timer') as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Call the orchestrator function
            step_9__piicheck(ctx={'user_query': 'test query'})

            # Verify timer was used
            mock_timer.assert_called_with(
                9,
                'RAG.platform.pii.detected',
                'PIICheck',
                stage='start'
            )

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_9_comprehensive_logging_format(self, mock_logger, mock_rag_log):
        """Test Step 9: Verify comprehensive logging format"""

        ctx = {
            'user_query': 'Contact me at test@example.com',
            'pii_analysis_result': {
                'detected': True,
                'matches': [
                    {'type': 'email', 'value': 'test@example.com', 'confidence': 0.95}
                ]
            }
        }

        # Call the orchestrator function
        step_9__piicheck(ctx=ctx)

        # Verify RAG step logging format
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            'step', 'step_id', 'node_label', 'pii_event',
            'pii_detected', 'pii_count', 'pii_types', 'detection_confidence',
            'query_length', 'processing_stage'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]['step'] == 9
        assert log_call[1]['step_id'] == 'RAG.platform.pii.detected'
        assert log_call[1]['node_label'] == 'PIICheck'
        assert log_call[1]['pii_event'] == 'pii_detected'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_9_pii_data_structure(self, mock_logger, mock_rag_log):
        """Test Step 9: Verify PII detection data structure"""

        ctx = {
            'user_query': 'Contact test@example.com',
            'pii_analysis_result': {
                'detected': True,
                'matches': [
                    {'type': 'email', 'value': 'test@example.com', 'confidence': 0.95}
                ]
            }
        }

        # Call the orchestrator function
        result = step_9__piicheck(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            'timestamp', 'pii_detected', 'pii_count', 'pii_types',
            'detection_confidence', 'query_length'
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in PII data: {field}"

        # Verify data types
        assert isinstance(result['timestamp'], str)
        assert isinstance(result['pii_detected'], bool)
        assert isinstance(result['pii_count'], int)
        assert isinstance(result['pii_types'], list)
        assert isinstance(result['detection_confidence'], (int, float))
        assert isinstance(result['query_length'], int)

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00'))