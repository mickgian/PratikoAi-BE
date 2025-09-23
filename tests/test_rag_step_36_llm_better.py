"""
Test suite for RAG STEP 36 - LLM better than rule-based decision

This module tests the orchestration function step_36__llmbetter which decides
whether LLM classification results are better than rule-based classification.

According to the RAG workflow:
- Takes both rule-based and LLM classification results
- Compares their confidence scores and quality
- Routes to either Step 37 (UseLLM) or Step 38 (UseRuleBased)
"""

from unittest.mock import patch

import pytest

from app.orchestrators.llm import step_36__llmbetter


class TestRAGStep36LLMBetter:
    """Test suite for RAG STEP 36 - LLM better than rule-based decision"""

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_36_llm_better_higher_confidence(self, mock_logger, mock_rag_log):
        """Test Step 36: LLM has higher confidence than rule-based"""

        ctx = {
            'request_id': 'test-request-123',
            'rule_based_classification': {
                'domain': 'tax',
                'action': 'information_request',
                'confidence': 0.65,
                'fallback_used': False
            },
            'llm_classification': {
                'domain': 'tax',
                'action': 'information_request',
                'confidence': 0.85,
                'fallback_used': True
            }
        }

        # Call the orchestrator function
        result = await step_36__llmbetter(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result['llm_better'] is True
        assert result['rule_confidence'] == 0.65
        assert result['llm_confidence'] == 0.85
        assert abs(result['confidence_improvement'] - 0.20) < 1e-10
        assert result['decision_reason'] == 'llm_higher_confidence'
        assert result['request_id'] == 'test-request-123'
        assert 'timestamp' in result

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert 'LLM classification better than rule-based' in log_call[0][0]
        assert log_call[1]['extra']['decision'] == 'use_llm'

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_36_rule_based_better_higher_confidence(self, mock_logger, mock_rag_log):
        """Test Step 36: Rule-based has higher confidence than LLM"""

        ctx = {
            'request_id': 'test-request-456',
            'rule_based_classification': {
                'domain': 'tax',
                'action': 'information_request',
                'confidence': 0.90,
                'fallback_used': False
            },
            'llm_classification': {
                'domain': 'tax',
                'action': 'information_request',
                'confidence': 0.70,
                'fallback_used': True
            }
        }

        result = await step_36__llmbetter(ctx=ctx)

        assert result['llm_better'] is False
        assert result['rule_confidence'] == 0.90
        assert result['llm_confidence'] == 0.70
        assert abs(result['confidence_improvement'] - (-0.20)) < 1e-10
        assert result['decision_reason'] == 'rule_based_higher_confidence'

        # Verify warning was logged
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert 'Rule-based classification better than LLM' in log_call[0][0]
        assert log_call[1]['extra']['decision'] == 'use_rule_based'

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_36_llm_better_different_classification(self, mock_logger, mock_rag_log):
        """Test Step 36: LLM provides different classification with higher confidence"""

        ctx = {
            'request_id': 'test-request-789',
            'rule_based_classification': {
                'domain': 'hr',
                'action': 'policy_inquiry',
                'confidence': 0.60,
                'fallback_used': False
            },
            'llm_classification': {
                'domain': 'tax',
                'action': 'calculation_request',
                'confidence': 0.95,
                'fallback_used': True
            }
        }

        result = await step_36__llmbetter(ctx=ctx)

        assert result['llm_better'] is True
        assert result['rule_confidence'] == 0.60
        assert result['llm_confidence'] == 0.95
        assert result['confidence_improvement'] == 0.35
        assert result['decision_reason'] == 'llm_different_classification_higher_confidence'
        assert result['classification_changed'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_36_equal_confidence_prefer_rule_based(self, mock_logger, mock_rag_log):
        """Test Step 36: Equal confidence - prefer rule-based for consistency"""

        ctx = {
            'request_id': 'test-request-equal',
            'rule_based_classification': {
                'domain': 'payroll',
                'action': 'salary_calculation',
                'confidence': 0.75,
                'fallback_used': False
            },
            'llm_classification': {
                'domain': 'payroll',
                'action': 'salary_calculation',
                'confidence': 0.75,
                'fallback_used': True
            }
        }

        result = await step_36__llmbetter(ctx=ctx)

        assert result['llm_better'] is False
        assert result['rule_confidence'] == 0.75
        assert result['llm_confidence'] == 0.75
        assert result['confidence_improvement'] == 0.0
        assert result['decision_reason'] == 'equal_confidence_prefer_rule_based'

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_36_significant_improvement_threshold(self, mock_logger, mock_rag_log):
        """Test Step 36: Small improvement doesn't justify LLM usage"""

        ctx = {
            'request_id': 'test-request-small-improvement',
            'rule_based_classification': {
                'domain': 'contract',
                'action': 'review_request',
                'confidence': 0.70,
                'fallback_used': False
            },
            'llm_classification': {
                'domain': 'contract',
                'action': 'review_request',
                'confidence': 0.72,  # Only 2% improvement
                'fallback_used': True
            },
            'min_improvement_threshold': 0.05  # 5% minimum
        }

        result = await step_36__llmbetter(ctx=ctx)

        assert result['llm_better'] is False
        assert abs(result['confidence_improvement'] - 0.02) < 1e-10
        assert result['decision_reason'] == 'improvement_below_threshold'

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_36_missing_rule_based_classification(self, mock_logger, mock_rag_log):
        """Test Step 36: Missing rule-based classification data"""

        ctx = {
            'request_id': 'test-request-missing-rule',
            'llm_classification': {
                'domain': 'tax',
                'action': 'information_request',
                'confidence': 0.85,
                'fallback_used': True
            }
        }

        result = await step_36__llmbetter(ctx=ctx)

        assert result['llm_better'] is True
        assert result['rule_confidence'] == 0.0
        assert result['llm_confidence'] == 0.85
        assert result['decision_reason'] == 'no_rule_based_available'
        assert result['error'] is None

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_36_missing_llm_classification(self, mock_logger, mock_rag_log):
        """Test Step 36: Missing LLM classification data"""

        ctx = {
            'request_id': 'test-request-missing-llm',
            'rule_based_classification': {
                'domain': 'tax',
                'action': 'information_request',
                'confidence': 0.85,
                'fallback_used': False
            }
        }

        result = await step_36__llmbetter(ctx=ctx)

        assert result['llm_better'] is False
        assert result['rule_confidence'] == 0.85
        assert result['llm_confidence'] == 0.0
        assert result['decision_reason'] == 'no_llm_available'

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_36_missing_both_classifications_error(self, mock_logger, mock_rag_log):
        """Test Step 36: Error when both classifications are missing"""

        ctx = {
            'request_id': 'test-request-missing-both'
        }

        result = await step_36__llmbetter(ctx=ctx)

        assert result['llm_better'] is False
        assert result['rule_confidence'] == 0.0
        assert result['llm_confidence'] == 0.0
        assert result['decision_reason'] == 'error'
        assert 'No classification data available' in result['error']

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_36_kwargs_override_ctx(self, mock_logger, mock_rag_log):
        """Test Step 36: kwargs parameters override ctx parameters"""

        ctx = {
            'request_id': 'test-request-ctx',
            'rule_based_classification': {
                'domain': 'old_domain',
                'action': 'old_action',
                'confidence': 0.50,
                'fallback_used': False
            }
        }

        kwargs_rule_based = {
            'domain': 'new_domain',
            'action': 'new_action',
            'confidence': 0.80,
            'fallback_used': False
        }

        kwargs_llm = {
            'domain': 'new_domain',
            'action': 'new_action',
            'confidence': 0.90,
            'fallback_used': True
        }

        result = await step_36__llmbetter(
            ctx=ctx,
            rule_based_classification=kwargs_rule_based,
            llm_classification=kwargs_llm
        )

        assert result['llm_better'] is True
        assert result['rule_confidence'] == 0.80  # From kwargs, not ctx
        assert result['llm_confidence'] == 0.90

    @pytest.mark.asyncio
    @patch('app.orchestrators.llm.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_36_integration_flow_context_preservation(self, mock_logger, mock_rag_log):
        """Test Step 36: Integration test ensuring context is preserved for next steps"""

        ctx = {
            'request_id': 'test-integration-123',
            'user_message': 'What are the tax deductions for 2023?',
            'canonical_facts': ['tax', '2023', 'deductions'],
            'rule_based_classification': {
                'domain': 'tax',
                'action': 'information_request',
                'confidence': 0.60,
                'fallback_used': False
            },
            'llm_classification': {
                'domain': 'tax',
                'action': 'calculation_request',
                'confidence': 0.85,
                'fallback_used': True
            }
        }

        result = await step_36__llmbetter(ctx=ctx)

        # Verify decision result
        assert result['llm_better'] is True
        assert result['decision_reason'] == 'llm_different_classification_higher_confidence'

        # Verify context preservation
        assert result['request_id'] == 'test-integration-123'
        assert 'timestamp' in result
        assert result['classification_changed'] is True

        # Verify rag_step_log was called with proper parameters
        assert mock_rag_log.call_count >= 2  # start and completed calls
        start_call = mock_rag_log.call_args_list[0][1]
        assert start_call['step'] == 36
        assert start_call['step_id'] == 'RAG.llm.llm.better.than.rule.based'
        assert start_call['node_label'] == 'LLMBetter'
        assert start_call['category'] == 'llm'
        assert start_call['type'] == 'decision'
        assert start_call['processing_stage'] == 'started'