#!/usr/bin/env python3
"""
Tests for RAG STEP 32 — Calculate domain and action scores Match Italian keywords

This step calculates domain and action scores using Italian keyword matching.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.orchestrators.classify import step_32__calc_scores
from app.services.domain_action_classifier import Domain, Action


class TestRAGStep32CalcScores:
    """Test suite for RAG STEP 32 - Calculate domain and action scores"""

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_32_calculate_scores_success(self, mock_logger, mock_rag_log):
        """Test Step 32: Successful score calculation"""

        # Mock domain and action scores
        domain_scores = {
            Domain.TAX: 0.85,
            Domain.LEGAL: 0.23,
            Domain.BUSINESS: 0.15,
            Domain.LABOR: 0.10,
            Domain.ACCOUNTING: 0.05
        }

        action_scores = {
            Action.INFORMATION_REQUEST: 0.90,
            Action.DOCUMENT_GENERATION: 0.20,
            Action.CALCULATION_REQUEST: 0.15,
            Action.COMPLIANCE_CHECK: 0.10,
            Action.STRATEGIC_ADVICE: 0.05,
            Action.DOCUMENT_ANALYSIS: 0.03
        }

        mock_classifier = MagicMock()
        mock_classifier._calculate_domain_scores.return_value = domain_scores
        mock_classifier._calculate_action_scores.return_value = action_scores

        ctx = {
            'user_query': 'Qual è l\'aliquota IVA per i servizi professionali?',
            'classification_service': mock_classifier
        }

        # Call the orchestrator function
        result = await step_32__calc_scores(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result['domain_scores'] == domain_scores
        assert result['action_scores'] == action_scores
        assert result['best_domain'] == Domain.TAX
        assert result['best_action'] == Action.INFORMATION_REQUEST
        assert result['domain_confidence'] == 0.85
        assert result['action_confidence'] == 0.90
        assert result['query_length'] == len(ctx['user_query'])
        assert 'timestamp' in result

        # Verify service methods were called
        mock_classifier._calculate_domain_scores.assert_called_once_with(
            'qual è l\'aliquota iva per i servizi professionali?'
        )
        mock_classifier._calculate_action_scores.assert_called_once_with(
            'qual è l\'aliquota iva per i servizi professionali?'
        )

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert 'Domain/action scores calculated' in log_call[0][0]
        assert log_call[1]['extra']['scoring_event'] == 'scores_calculated'
        assert log_call[1]['extra']['best_domain'] == 'tax'
        assert log_call[1]['extra']['domain_confidence'] == 0.85

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_32_legal_query_scores(self, mock_logger, mock_rag_log):
        """Test Step 32: Legal domain query scoring"""

        domain_scores = {
            Domain.LEGAL: 0.92,
            Domain.TAX: 0.15,
            Domain.BUSINESS: 0.10,
            Domain.LABOR: 0.08,
            Domain.ACCOUNTING: 0.05
        }

        action_scores = {
            Action.DOCUMENT_GENERATION: 0.88,
            Action.INFORMATION_REQUEST: 0.25,
            Action.STRATEGIC_ADVICE: 0.15,
            Action.COMPLIANCE_CHECK: 0.10,
            Action.CALCULATION_REQUEST: 0.05,
            Action.DOCUMENT_ANALYSIS: 0.03
        }

        mock_classifier = MagicMock()
        mock_classifier._calculate_domain_scores.return_value = domain_scores
        mock_classifier._calculate_action_scores.return_value = action_scores

        ctx = {
            'user_query': 'Mi serve un contratto di locazione',
            'classification_service': mock_classifier
        }

        result = await step_32__calc_scores(ctx=ctx)

        assert result['best_domain'] == Domain.LEGAL
        assert result['best_action'] == Action.DOCUMENT_GENERATION
        assert result['domain_confidence'] == 0.92
        assert result['action_confidence'] == 0.88

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_32_low_confidence_scores(self, mock_logger, mock_rag_log):
        """Test Step 32: Low confidence scores"""

        domain_scores = {
            Domain.BUSINESS: 0.35,
            Domain.TAX: 0.30,
            Domain.LEGAL: 0.25,
            Domain.LABOR: 0.20,
            Domain.ACCOUNTING: 0.15
        }

        action_scores = {
            Action.STRATEGIC_ADVICE: 0.40,
            Action.INFORMATION_REQUEST: 0.35,
            Action.DOCUMENT_GENERATION: 0.20,
            Action.COMPLIANCE_CHECK: 0.15,
            Action.CALCULATION_REQUEST: 0.10,
            Action.DOCUMENT_ANALYSIS: 0.05
        }

        mock_classifier = MagicMock()
        mock_classifier._calculate_domain_scores.return_value = domain_scores
        mock_classifier._calculate_action_scores.return_value = action_scores

        ctx = {
            'user_query': 'Come posso migliorare i processi aziendali?',
            'classification_service': mock_classifier
        }

        result = await step_32__calc_scores(ctx=ctx)

        assert result['domain_confidence'] == 0.35  # Low confidence
        assert result['action_confidence'] == 0.40  # Low confidence

        # Verify warning was logged for low confidence
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert 'Low confidence scores detected' in warning_call[0][0]

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_32_classifier_error(self, mock_logger, mock_rag_log):
        """Test Step 32: Handle classifier calculation error"""

        mock_classifier = MagicMock()
        mock_classifier._calculate_domain_scores.side_effect = Exception("Scoring error")

        ctx = {
            'user_query': 'Test query',
            'classification_service': mock_classifier
        }

        result = await step_32__calc_scores(ctx=ctx)

        # Should return error result
        assert result['domain_scores'] is None
        assert result['action_scores'] is None
        assert result['error'] == 'Scoring error'
        assert result['best_domain'] is None
        assert result['domain_confidence'] == 0.0

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert 'Score calculation failed' in error_call[0][0]

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.services.domain_action_classifier.DomainActionClassifier')
    async def test_step_32_create_classifier_if_missing(self, mock_classifier_class, mock_logger, mock_rag_log):
        """Test Step 32: Create classifier if not provided in context"""

        # Mock classifier instance and scores
        mock_classifier = MagicMock()
        mock_classifier_class.return_value = mock_classifier

        domain_scores = {Domain.TAX: 0.80, Domain.LEGAL: 0.20}
        action_scores = {Action.INFORMATION_REQUEST: 0.85, Action.DOCUMENT_GENERATION: 0.15}

        mock_classifier._calculate_domain_scores.return_value = domain_scores
        mock_classifier._calculate_action_scores.return_value = action_scores

        ctx = {
            'user_query': 'Query without classifier service'
        }

        result = await step_32__calc_scores(ctx=ctx)

        # Verify classifier was created and used
        mock_classifier_class.assert_called_once()
        assert result['best_domain'] == Domain.TAX
        assert result['domain_confidence'] == 0.80

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_32_empty_context(self, mock_logger, mock_rag_log):
        """Test Step 32: Handle empty context gracefully"""

        result = await step_32__calc_scores()

        # Verify defaults are used
        assert isinstance(result, dict)
        assert result['domain_scores'] is None
        assert result['action_scores'] is None
        assert result['error'] == 'No user query provided'
        assert result['domain_confidence'] == 0.0

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_32_kwargs_parameters(self, mock_logger, mock_rag_log):
        """Test Step 32: Parameters passed via kwargs"""

        domain_scores = {Domain.LABOR: 0.90, Domain.TAX: 0.10}
        action_scores = {Action.COMPLIANCE_CHECK: 0.95, Action.INFORMATION_REQUEST: 0.05}

        mock_classifier = MagicMock()
        mock_classifier._calculate_domain_scores.return_value = domain_scores
        mock_classifier._calculate_action_scores.return_value = action_scores

        # Call with kwargs instead of ctx
        result = await step_32__calc_scores(
            user_query='Test labor query',
            classification_service=mock_classifier
        )

        # Verify kwargs are processed correctly
        assert result['best_domain'] == Domain.LABOR
        assert result['best_action'] == Action.COMPLIANCE_CHECK
        assert result['domain_confidence'] == 0.90

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_32_performance_tracking(self, mock_logger, mock_rag_log):
        """Test Step 32: Performance tracking with timer"""

        with patch('app.orchestrators.classify.rag_step_timer') as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Call the orchestrator function
            await step_32__calc_scores(ctx={'user_query': 'test query'})

            # Verify timer was used
            mock_timer.assert_called_with(
                32,
                'RAG.classify.calculate.domain.and.action.scores.match.italian.keywords',
                'CalcScores',
                stage='start'
            )

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_32_comprehensive_logging_format(self, mock_logger, mock_rag_log):
        """Test Step 32: Verify comprehensive logging format"""

        domain_scores = {Domain.TAX: 0.85, Domain.LEGAL: 0.15}
        action_scores = {Action.INFORMATION_REQUEST: 0.90, Action.DOCUMENT_GENERATION: 0.10}

        mock_classifier = MagicMock()
        mock_classifier._calculate_domain_scores.return_value = domain_scores
        mock_classifier._calculate_action_scores.return_value = action_scores

        ctx = {
            'user_query': 'Test tax query',
            'classification_service': mock_classifier
        }

        # Call the orchestrator function
        await step_32__calc_scores(ctx=ctx)

        # Verify RAG step logging format
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            'step', 'step_id', 'node_label', 'scoring_event',
            'best_domain', 'best_action', 'domain_confidence', 'action_confidence',
            'query_length', 'processing_stage'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]['step'] == 32
        assert log_call[1]['step_id'] == 'RAG.classify.calculate.domain.and.action.scores.match.italian.keywords'
        assert log_call[1]['node_label'] == 'CalcScores'
        assert log_call[1]['scoring_event'] == 'scores_calculated'

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_32_scores_data_structure(self, mock_logger, mock_rag_log):
        """Test Step 32: Verify scores data structure"""

        domain_scores = {Domain.TAX: 0.85, Domain.LEGAL: 0.15}
        action_scores = {Action.INFORMATION_REQUEST: 0.90, Action.DOCUMENT_GENERATION: 0.10}

        mock_classifier = MagicMock()
        mock_classifier._calculate_domain_scores.return_value = domain_scores
        mock_classifier._calculate_action_scores.return_value = action_scores

        ctx = {
            'user_query': 'Test query',
            'classification_service': mock_classifier
        }

        # Call the orchestrator function
        result = await step_32__calc_scores(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            'timestamp', 'domain_scores', 'action_scores', 'best_domain', 'best_action',
            'domain_confidence', 'action_confidence', 'query_length', 'error'
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in scores data: {field}"

        # Verify data types
        assert isinstance(result['timestamp'], str)
        assert isinstance(result['domain_scores'], dict)
        assert isinstance(result['action_scores'], dict)
        assert isinstance(result['best_domain'], Domain)
        assert isinstance(result['best_action'], Action)
        assert isinstance(result['domain_confidence'], float)
        assert isinstance(result['action_confidence'], float)
        assert isinstance(result['query_length'], int)

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00'))