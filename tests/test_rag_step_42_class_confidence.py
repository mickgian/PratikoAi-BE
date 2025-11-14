#!/usr/bin/env python3
"""
Tests for RAG STEP 42 — Classification exists and confidence at least 0.6?

This step checks for classification existence and 0.6 confidence threshold.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.orchestrators.classify import step_42__class_confidence
from app.services.domain_action_classifier import Domain, Action, DomainActionClassification


class TestRAGStep42ClassConfidence:
    """Test suite for RAG STEP 42 - Classification existence and confidence check"""

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_42_classification_exists_confidence_ok(self, mock_logger, mock_rag_log):
        """Test Step 42: Classification exists with confidence >= 0.6"""

        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.85,
            reasoning="Tax information request",
            fallback_used=False
        )

        ctx = {
            'classification': classification
        }

        # Call the orchestrator function
        result = await step_42__class_confidence(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result['classification_exists'] is True
        assert result['confidence_sufficient'] is True
        assert result['confidence_value'] == 0.85
        assert result['threshold'] == 0.6
        assert result['domain'] == 'tax'
        assert result['action'] == 'information_request'
        assert 'timestamp' in result

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert 'Classification exists with sufficient confidence' in log_call[0][0]
        assert log_call[1]['extra']['classification_event'] == 'exists_confidence_sufficient'

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_42_classification_exists_confidence_low(self, mock_logger, mock_rag_log):
        """Test Step 42: Classification exists but confidence < 0.6"""

        classification = DomainActionClassification(
            domain=Domain.BUSINESS,
            action=Action.STRATEGIC_ADVICE,
            confidence=0.45,
            reasoning="Business advice request",
            fallback_used=False
        )

        ctx = {
            'classification': classification
        }

        result = await step_42__class_confidence(ctx=ctx)

        assert result['classification_exists'] is True
        assert result['confidence_sufficient'] is False
        assert result['confidence_value'] == 0.45

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert 'Classification exists but insufficient confidence' in warning_call[0][0]

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_42_classification_missing(self, mock_logger, mock_rag_log):
        """Test Step 42: No classification provided"""

        ctx = {}

        result = await step_42__class_confidence(ctx=ctx)

        assert result['classification_exists'] is False
        assert result['confidence_sufficient'] is False
        assert result['confidence_value'] == 0.0

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert 'No classification provided' in warning_call[0][0]

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_42_exact_threshold_confidence(self, mock_logger, mock_rag_log):
        """Test Step 42: Classification with exactly 0.6 confidence"""

        classification = DomainActionClassification(
            domain=Domain.LEGAL,
            action=Action.DOCUMENT_GENERATION,
            confidence=0.6,
            reasoning="Legal document generation",
            fallback_used=False
        )

        ctx = {
            'classification': classification
        }

        result = await step_42__class_confidence(ctx=ctx)

        assert result['classification_exists'] is True
        assert result['confidence_sufficient'] is True
        assert result['confidence_value'] == 0.6

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_42_fallback_used_high_confidence(self, mock_logger, mock_rag_log):
        """Test Step 42: Classification via LLM fallback with high confidence"""

        classification = DomainActionClassification(
            domain=Domain.ACCOUNTING,
            action=Action.CALCULATION_REQUEST,
            confidence=0.88,
            reasoning="Accounting calculation via LLM",
            fallback_used=True
        )

        ctx = {
            'classification': classification
        }

        result = await step_42__class_confidence(ctx=ctx)

        assert result['classification_exists'] is True
        assert result['confidence_sufficient'] is True
        assert result['fallback_used'] is True

        # Verify fallback was noted in logging
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert log_call[1]['extra']['fallback_used'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_42_fallback_used_low_confidence(self, mock_logger, mock_rag_log):
        """Test Step 42: Classification via LLM fallback with low confidence"""

        classification = DomainActionClassification(
            domain=Domain.LABOR,
            action=Action.COMPLIANCE_CHECK,
            confidence=0.35,
            reasoning="Labor compliance via LLM",
            fallback_used=True
        )

        ctx = {
            'classification': classification
        }

        result = await step_42__class_confidence(ctx=ctx)

        assert result['classification_exists'] is True
        assert result['confidence_sufficient'] is False
        assert result['fallback_used'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_42_classification_dict_format(self, mock_logger, mock_rag_log):
        """Test Step 42: Classification provided as dict instead of object"""

        ctx = {
            'classification': {
                'domain': Domain.TAX,
                'action': Action.INFORMATION_REQUEST,
                'confidence': 0.75,
                'reasoning': "Tax information request",
                'fallback_used': False
            }
        }

        result = await step_42__class_confidence(ctx=ctx)

        assert result['classification_exists'] is True
        assert result['confidence_sufficient'] is True
        assert result['domain'] == 'tax'
        assert result['action'] == 'information_request'

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_42_kwargs_parameters(self, mock_logger, mock_rag_log):
        """Test Step 42: Parameters passed via kwargs"""

        classification = DomainActionClassification(
            domain=Domain.LEGAL,
            action=Action.DOCUMENT_GENERATION,
            confidence=0.92,
            reasoning="Legal document generation"
        )

        # Call with kwargs instead of ctx
        result = await step_42__class_confidence(
            classification=classification
        )

        # Verify kwargs are processed correctly
        assert result['classification_exists'] is True
        assert result['confidence_sufficient'] is True
        assert result['confidence_value'] == 0.92

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_42_performance_tracking(self, mock_logger, mock_rag_log):
        """Test Step 42: Performance tracking with timer"""

        with patch('app.orchestrators.classify.rag_step_timer') as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Call the orchestrator function
            await step_42__class_confidence(ctx={'classification': None})

            # Verify timer was used
            mock_timer.assert_called_with(
                42,
                'RAG.classify.classification.exists.and.confidence.at.least.0.6',
                'ClassConfidence',
                stage='start'
            )

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_42_comprehensive_logging_format(self, mock_logger, mock_rag_log):
        """Test Step 42: Verify comprehensive logging format"""

        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.85,
            reasoning="Tax query classification"
        )

        ctx = {
            'classification': classification
        }

        # Call the orchestrator function
        await step_42__class_confidence(ctx=ctx)

        # Verify RAG step logging format
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            'step', 'step_id', 'node_label', 'classification_event',
            'classification_exists', 'confidence_sufficient', 'confidence_value',
            'threshold', 'domain', 'action', 'processing_stage'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]['step'] == 42
        assert log_call[1]['step_id'] == 'RAG.classify.classification.exists.and.confidence.at.least.0.6'
        assert log_call[1]['node_label'] == 'ClassConfidence'
        assert log_call[1]['classification_event'] == 'exists_confidence_sufficient'

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_42_class_confidence_data_structure(self, mock_logger, mock_rag_log):
        """Test Step 42: Verify class confidence data structure"""

        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.85,
            reasoning="Test classification"
        )

        ctx = {
            'classification': classification
        }

        # Call the orchestrator function
        result = await step_42__class_confidence(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            'timestamp', 'classification_exists', 'confidence_sufficient',
            'confidence_value', 'threshold', 'domain', 'action',
            'fallback_used', 'reasoning'
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in class confidence data: {field}"

        # Verify data types
        assert isinstance(result['timestamp'], str)
        assert isinstance(result['classification_exists'], bool)
        assert isinstance(result['confidence_sufficient'], bool)
        assert isinstance(result['confidence_value'], float)
        assert isinstance(result['threshold'], float)
        assert isinstance(result['domain'], str) or result['domain'] is None
        assert isinstance(result['action'], str) or result['action'] is None
        assert isinstance(result['fallback_used'], bool)
        assert isinstance(result['reasoning'], str) or result['reasoning'] is None

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00'))