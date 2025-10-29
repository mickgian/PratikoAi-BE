"""
Test Suite for RAG Step 120: Validate expert credentials
Process orchestrator that validates expert credentials and routes to trust score decision.

Following MASTER_GUARDRAILS methodology:
- Unit tests: Core functionality, error handling, context preservation
- Parity tests: Behavioral consistency before/after orchestrator
- Integration tests: Step 119→120, 120→121, and full pipeline flows
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import the orchestrator function
from app.orchestrators.platform import step_120__validate_expert


class TestRAGStep120ValidateExpert:
    """Unit tests for Step 120 expert validation orchestrator."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_120_basic_expert_validation(self, mock_rag_log):
        """Test Step 120: Basic expert credential validation."""
        ctx = {
            'expert_feedback_collected': True,
            'expert_id': 'expert_123',
            'feedback_data': {
                'expert_id': 'expert_123',
                'feedback_type': 'incorrect',
                'confidence_score': 0.9
            },
            'expert_validation_required': True
        }

        result = await step_120__validate_expert(messages=[], ctx=ctx)

        # Verify result structure and routing
        assert result is not None
        assert result['expert_validation_completed'] is True
        assert result['expert_id'] == 'expert_123'
        assert result['next_step'] == 'trust_score_decision'  # Routes to Step 121
        assert 'trust_score' in result
        assert 'validation_status' in result

        # Verify context preservation
        assert result['expert_feedback_collected'] is True
        assert result['feedback_data']['expert_id'] == 'expert_123'

        # Verify logging
        mock_rag_log.assert_called()
        assert any('expert_validation_completed' in str(call) for call in mock_rag_log.call_args_list)

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_120_trust_score_calculation(self, mock_rag_log):
        """Test Step 120: Trust score calculation for different expert profiles."""
        test_cases = [
            {
                'expert_id': 'expert_high_trust',
                'expert_profile': {
                    'credentials': ['certified_tax_advisor', 'italian_comercialista'],
                    'years_experience': 15,
                    'successful_validations': 150
                },
                'expected_trust_score_range': (0.7, 1.0)
            },
            {
                'expert_id': 'expert_medium_trust',
                'expert_profile': {
                    'credentials': ['tax_professional'],
                    'years_experience': 5,
                    'successful_validations': 25
                },
                'expected_trust_score_range': (0.3, 0.6)
            },
            {
                'expert_id': 'expert_low_trust',
                'expert_profile': {
                    'credentials': [],
                    'years_experience': 1,
                    'successful_validations': 2
                },
                'expected_trust_score_range': (0.0, 0.6)
            }
        ]

        for test_case in test_cases:
            ctx = {
                'expert_id': test_case['expert_id'],
                'expert_profile': test_case['expert_profile'],
                'feedback_data': {'feedback_type': 'incorrect'}
            }

            result = await step_120__validate_expert(messages=[], ctx=ctx)

            assert result['expert_validation_completed'] is True
            assert result['trust_score'] >= test_case['expected_trust_score_range'][0]
            assert result['trust_score'] <= test_case['expected_trust_score_range'][1]
            assert result['next_step'] == 'trust_score_decision'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_120_preserves_context_data(self, mock_rag_log):
        """Test Step 120: Preserves all context data while adding validation metadata."""
        ctx = {
            'request_id': 'req_12345',
            'user_query': 'original query about taxes',
            'classification_data': {'domain': 'tax', 'confidence': 0.85},
            'expert_feedback_collected': True,
            'feedback_routing_decision': 'expert_feedback',
            'expert_id': 'expert_456',
            'feedback_data': {
                'query_id': 'query_789',
                'expert_id': 'expert_456',
                'feedback_type': 'incomplete',
                'expert_answer': 'Additional details needed...'
            },
            'session_metadata': {'start_time': '2024-01-01T10:00:00Z'}
        }

        result = await step_120__validate_expert(messages=[], ctx=ctx)

        # Verify context preservation
        assert result['request_id'] == 'req_12345'
        assert result['user_query'] == 'original query about taxes'
        assert result['classification_data'] == {'domain': 'tax', 'confidence': 0.85}
        assert result['expert_feedback_collected'] is True
        assert result['feedback_routing_decision'] == 'expert_feedback'
        assert result['session_metadata'] == {'start_time': '2024-01-01T10:00:00Z'}

        # Verify validation processing
        assert result['expert_validation_completed'] is True
        assert result['expert_id'] == 'expert_456'
        assert result['trust_score'] is not None

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_120_logs_validation_details(self, mock_rag_log):
        """Test Step 120: Logs comprehensive validation details."""
        ctx = {
            'expert_id': 'expert_999',
            'feedback_data': {
                'feedback_type': 'correct',
                'confidence_score': 0.95
            },
            'expert_profile': {
                'credentials': ['certified_tax_advisor'],
                'years_experience': 10
            }
        }

        result = await step_120__validate_expert(messages=[], ctx=ctx)

        # Verify logging calls contain expected details
        mock_rag_log.assert_called()
        log_calls = [str(call) for call in mock_rag_log.call_args_list]

        # Check for specific log attributes
        assert any('expert_id' in call for call in log_calls)
        assert any('trust_score' in call for call in log_calls)
        assert any('trust_score_decision' in call for call in log_calls)

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_120_validation_performance_tracking(self, mock_rag_log):
        """Test Step 120: Tracks validation performance and timing."""
        ctx = {
            'expert_id': 'expert_111',
            'feedback_data': {'feedback_type': 'incorrect'},
            'expert_profile': {'credentials': ['tax_professional']}
        }

        result = await step_120__validate_expert(messages=[], ctx=ctx)

        # Verify performance tracking
        assert 'validation_processing_time_ms' in result
        assert isinstance(result['validation_processing_time_ms'], (int, float))
        assert result['validation_processing_time_ms'] >= 0

        # Verify successful validation tracking
        assert result['expert_validation_completed'] is True
        assert result['validation_status'] == 'success'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_120_error_handling_missing_expert_data(self, mock_rag_log):
        """Test Step 120: Handle missing or invalid expert data gracefully."""
        ctx = {
            'feedback_data': {'feedback_type': 'correct'}
            # Missing expert_id and expert_profile
        }

        result = await step_120__validate_expert(messages=[], ctx=ctx)

        # Should handle gracefully and still route to trust score decision
        assert result['expert_validation_completed'] is False
        assert result['next_step'] == 'trust_score_decision'
        assert result['error_type'] == 'invalid_expert_id'
        assert result['trust_score'] == 0.0  # Default low trust score
        assert 'error_message' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_120_error_handling_invalid_expert_id(self, mock_rag_log):
        """Test Step 120: Handle invalid expert ID gracefully."""
        ctx = {
            'expert_id': '',  # Invalid expert ID
            'feedback_data': {'feedback_type': 'incorrect'}
        }

        result = await step_120__validate_expert(messages=[], ctx=ctx)

        # Should handle gracefully
        assert result['expert_validation_completed'] is False
        assert result['next_step'] == 'trust_score_decision'
        assert result['error_type'] == 'invalid_expert_id'
        assert result['trust_score'] == 0.0

        # Verify error logging
        mock_rag_log.assert_called()
        assert mock_rag_log.call_count >= 2  # started and completed/error calls

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_120_italian_credentials_validation(self, mock_rag_log):
        """Test Step 120: Italian tax professional credentials validation."""
        italian_credentials = [
            'dottore_commercialista',
            'consulente_del_lavoro',
            'revisore_legale',
            'tributarista_certificato',
            'caf_operatore'
        ]

        for credential in italian_credentials:
            ctx = {
                'expert_id': 'expert_italian',
                'expert_profile': {
                    'credentials': [credential],
                    'years_experience': 8,
                    'italian_certification': True
                },
                'feedback_data': {'feedback_type': 'incorrect'}
            }

            result = await step_120__validate_expert(messages=[], ctx=ctx)

            assert result['expert_validation_completed'] is True
            assert result['italian_credentials_validated'] is True
            assert result['trust_score'] > 0.5  # Italian credentials should boost trust
            assert result['next_step'] == 'trust_score_decision'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_120_trust_threshold_preparation(self, mock_rag_log):
        """Test Step 120: Prepares trust score threshold comparison for Step 121."""
        test_cases = [
            {'trust_score': 0.8, 'expected_meets_threshold': True},
            {'trust_score': 0.7, 'expected_meets_threshold': True},
            {'trust_score': 0.65, 'expected_meets_threshold': False},
            {'trust_score': 0.3, 'expected_meets_threshold': False}
        ]

        for test_case in test_cases:
            ctx = {
                'expert_id': 'expert_test',
                'expert_profile': {
                    'mock_trust_score': test_case['trust_score']  # For testing
                },
                'feedback_data': {'feedback_type': 'incorrect'}
            }

            result = await step_120__validate_expert(messages=[], ctx=ctx)

            assert result['expert_validation_completed'] is True
            assert abs(result['trust_score'] - test_case['trust_score']) < 0.1
            assert result['trust_threshold'] == 0.7
            assert result['meets_trust_threshold'] == test_case['expected_meets_threshold']
            assert result['next_step'] == 'trust_score_decision'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_120_validation_routing_consistency(self, mock_rag_log):
        """Test Step 120: Ensures consistent routing to Step 121 regardless of validation result."""
        test_scenarios = [
            {'expert_validation_completed': True, 'trust_score': 0.9},
            {'expert_validation_completed': True, 'trust_score': 0.5},
            {'expert_validation_completed': False, 'error_type': 'missing_expert_data'}
        ]

        for scenario in test_scenarios:
            ctx = {
                'expert_id': 'expert_test',
                'feedback_data': {'feedback_type': 'incorrect'}
            }

            result = await step_120__validate_expert(messages=[], ctx=ctx)

            # All validation attempts should route to trust score decision
            assert result['next_step'] == 'trust_score_decision'
            assert 'trust_score' in result
            assert 'meets_trust_threshold' in result


class TestRAGStep120Parity:
    """Parity tests ensuring behavioral consistency before/after orchestrator."""

    @pytest.mark.asyncio
    async def test_step_120_parity_validation_structure(self):
        """Test Step 120: Maintains consistent output structure for expert validation."""
        ctx = {
            'expert_id': 'expert_444',
            'feedback_data': {'feedback_type': 'correct'},
            'expert_profile': {
                'credentials': ['tax_professional'],
                'years_experience': 5
            }
        }

        result = await step_120__validate_expert(messages=[], ctx=ctx)

        # Verify expected output structure matches service expectations
        expected_fields = [
            'expert_validation_completed', 'expert_id', 'trust_score',
            'trust_threshold', 'meets_trust_threshold', 'next_step',
            'validation_status', 'validation_processing_time_ms'
        ]

        for field in expected_fields:
            assert field in result, f"Expected field '{field}' missing from result"

        # Verify routing consistency
        assert result['next_step'] == 'trust_score_decision'


class TestRAGStep120Integration:
    """Integration tests for Step 120 with neighboring steps."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.metrics.step_119__expert_feedback_collector')
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_119_to_120_integration(self, mock_rag_log, mock_step_119):
        """Test Step 119→120: Expert feedback collector routes to expert validation."""
        # Mock Step 119 expert feedback collector
        mock_step_119.return_value = {
            'expert_feedback_collected': True,
            'next_step': 'validate_expert_credentials',
            'expert_id': 'expert_666',
            'feedback_data': {
                'expert_id': 'expert_666',
                'feedback_type': 'incorrect'
            },
            'expert_validation_required': True
        }

        # Call Step 119 first
        step_119_result = await mock_step_119(
            messages=[],
            ctx={'feedback_data': {'expert_id': 'expert_666'}}
        )

        # Then call Step 120 with Step 119's output
        step_120_result = await step_120__validate_expert(
            messages=[],
            ctx=step_119_result
        )

        # Verify integration flow
        assert step_119_result['next_step'] == 'validate_expert_credentials'
        assert step_120_result['expert_validation_completed'] is True
        assert step_120_result['next_step'] == 'trust_score_decision'
        assert step_120_result['expert_id'] == 'expert_666'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_120_to_121_integration(self, mock_rag_log):
        """Test Step 120→121: Expert validation routes to trust score decision."""
        # Call Step 120
        step_120_result = await step_120__validate_expert(
            messages=[],
            ctx={
                'expert_id': 'expert_777',
                'feedback_data': {'feedback_type': 'incomplete'},
                'expert_profile': {
                    'credentials': ['certified_tax_advisor'],
                    'years_experience': 12
                }
            }
        )

        # Verify Step 120 prepares proper routing to Step 121
        assert step_120_result['next_step'] == 'trust_score_decision'
        assert step_120_result['expert_validation_completed'] is True
        assert step_120_result['expert_id'] == 'expert_777'
        assert step_120_result['trust_score'] is not None
        assert step_120_result['meets_trust_threshold'] is not None

        # Verify all context is preserved for Step 121
        assert 'feedback_data' in step_120_result
        assert step_120_result['feedback_data']['feedback_type'] == 'incomplete'

    @pytest.mark.asyncio
    @patch('app.orchestrators.metrics.step_119__expert_feedback_collector')
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_full_expert_validation_pipeline(self, mock_rag_log, mock_step_119):
        """Test Step 119→120→121: Full expert validation pipeline integration."""
        # Mock Step 119
        mock_step_119.return_value = {
            'expert_feedback_collected': True,
            'next_step': 'validate_expert_credentials',
            'expert_id': 'expert_888',
            'feedback_data': {
                'expert_id': 'expert_888',
                'feedback_type': 'correct'
            },
            'expert_validation_required': True
        }

        # Execute pipeline through Step 120
        step_119_result = await mock_step_119(messages=[], ctx={'expert_user': True})
        step_120_result = await step_120__validate_expert(messages=[], ctx=step_119_result)

        # Verify full pipeline flow through Step 120
        assert step_119_result['expert_feedback_collected'] is True
        assert step_120_result['expert_validation_completed'] is True
        assert step_120_result['next_step'] == 'trust_score_decision'

        # Verify Step 120 preserves Step 119 context
        assert step_120_result['expert_feedback_collected'] is True
        assert step_120_result['expert_validation_required'] is True
        assert step_120_result['expert_id'] == 'expert_888'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_120_multiple_validation_scenarios(self, mock_rag_log):
        """Test Step 120: Multiple expert validation scenarios in sequence."""
        test_scenarios = [
            {
                'name': 'high_trust_expert',
                'ctx': {
                    'expert_id': 'expert_high',
                    'expert_profile': {
                        'credentials': ['dottore_commercialista', 'revisore_legale'],
                        'years_experience': 20,
                        'successful_validations': 200
                    },
                    'feedback_data': {'feedback_type': 'incorrect'}
                },
                'expected_meets_threshold': True
            },
            {
                'name': 'medium_trust_expert',
                'ctx': {
                    'expert_id': 'expert_medium',
                    'expert_profile': {
                        'credentials': ['tax_professional'],
                        'years_experience': 3,
                        'successful_validations': 15
                    },
                    'feedback_data': {'feedback_type': 'incomplete'}
                },
                'expected_meets_threshold': False
            },
            {
                'name': 'new_expert',
                'ctx': {
                    'expert_id': 'expert_new',
                    'expert_profile': {
                        'credentials': [],
                        'years_experience': 0,
                        'successful_validations': 0
                    },
                    'feedback_data': {'feedback_type': 'correct'}
                },
                'expected_meets_threshold': False
            }
        ]

        for scenario in test_scenarios:
            result = await step_120__validate_expert(messages=[], ctx=scenario['ctx'])

            assert result['expert_validation_completed'] is True
            assert result['next_step'] == 'trust_score_decision'
            assert result['expert_id'] == scenario['ctx']['expert_id']
            assert result['meets_trust_threshold'] == scenario['expected_meets_threshold']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])