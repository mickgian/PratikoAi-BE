"""
Tests for RAG Step 122 - Feedback rejected (Error orchestrator)

This step is an error node that receives input from Step 121 (TrustScoreOK) when trust score < 0.7
and handles rejection of expert feedback due to insufficient trust.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.orchestrators.feedback import step_122__feedback_rejected


class TestRAGStep122FeedbackRejected:
    """Unit tests for Step 122 feedback rejection error handling."""

    @pytest.mark.asyncio
    async def test_step_122_basic_feedback_rejection_handling(self):
        """Test basic feedback rejection with low trust score context."""
        # Setup: Context from Step 121 with rejection decision
        ctx = {
            'expert_validation': {
                'trust_score': 0.65,
                'expert_id': 'expert_rejected',
                'credentials_validated': False,
                'validation_details': {'italian_certification': False}
            },
            'expert_feedback': {
                'feedback_type': 'incorrect',
                'feedback_text': 'Answer needs correction',
                'expert_data': {'name': 'Dr. Low Trust'}
            },
            'trust_score_decision': False,
            'next_step': 'FeedbackRejected',
            'routing_decision': 'reject_feedback',
            'threshold_met': False,
            'request_id': 'req_test_rejection'
        }

        with patch('app.observability.rag_logging.rag_step_log') as mock_log, \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            result = await step_122__feedback_rejected(ctx=ctx)

            # Verify feedback rejection handling
            assert result['feedback_rejected'] is True
            assert result['rejection_reason'] == 'insufficient_trust_score'
            assert result['trust_score'] == 0.65
            assert result['rejection_timestamp'] is not None

            # Verify context preservation
            assert result['expert_validation'] == ctx['expert_validation']
            assert result['expert_feedback'] == ctx['expert_feedback']
            assert result['trust_score_decision'] is False
            assert result['request_id'] == 'req_test_rejection'

            # Verify structured logging was called
            mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_step_122_rejection_with_various_trust_scores(self):
        """Test rejection handling with different trust score values below threshold."""
        test_scenarios = [
            {'trust_score': 0.69, 'description': 'just_below_threshold'},
            {'trust_score': 0.5, 'description': 'medium_low'},
            {'trust_score': 0.2, 'description': 'very_low'},
            {'trust_score': 0.0, 'description': 'zero_trust'}
        ]

        for scenario in test_scenarios:
            ctx = {
                'expert_validation': {
                    'trust_score': scenario['trust_score'],
                    'expert_id': f'expert_{scenario["description"]}',
                    'credentials_validated': False
                },
                'expert_feedback': {
                    'feedback_type': 'wrong',
                    'expert_data': {'name': f'Expert {scenario["description"]}'}
                },
                'trust_score_decision': False,
                'threshold_met': False,
                'request_id': f'req_{scenario["description"]}'
            }

            with patch('app.observability.rag_logging.rag_step_log'), \
                 patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

                mock_timer.return_value.__enter__ = Mock()
                mock_timer.return_value.__exit__ = Mock()

                result = await step_122__feedback_rejected(ctx=ctx)

                # Verify rejection handling for all scenarios
                assert result['feedback_rejected'] is True, f"Failed for {scenario['description']}"
                assert result['rejection_reason'] == 'insufficient_trust_score'
                assert result['trust_score'] == scenario['trust_score']
                assert result['threshold_met'] is False

    @pytest.mark.asyncio
    async def test_step_122_preserves_context_data(self):
        """Test that Step 122 preserves all context data while adding rejection metadata."""
        ctx = {
            'expert_validation': {
                'trust_score': 0.4,
                'expert_id': 'expert_preserve',
                'credentials_validated': False,
                'italian_certification': False,
                'professional_qualifications': ['Basic']
            },
            'expert_feedback': {
                'feedback_type': 'incomplete',
                'feedback_text': 'Missing important details',
                'expert_data': {
                    'name': 'Dr. Context Preserve',
                    'location': 'Roma'
                }
            },
            'trust_score_decision': False,
            'routing_decision': 'reject_feedback',
            'threshold_met': False,
            'performance_tracking': {
                'step_121_duration': 0.025,
                'decision_start_time': '2023-10-01T10:00:00Z'
            },
            'request_id': 'req_preserve_context',
            'trace_id': 'trace_preserve_456'
        }

        with patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            result = await step_122__feedback_rejected(ctx=ctx)

            # Verify all original context is preserved
            assert result['expert_validation'] == ctx['expert_validation']
            assert result['expert_feedback'] == ctx['expert_feedback']
            assert result['trust_score_decision'] == ctx['trust_score_decision']
            assert result['routing_decision'] == ctx['routing_decision']
            assert result['performance_tracking'] == ctx['performance_tracking']
            assert result['request_id'] == ctx['request_id']
            assert result['trace_id'] == ctx['trace_id']

            # Verify new rejection metadata is added
            assert 'feedback_rejected' in result
            assert 'rejection_reason' in result
            assert 'rejection_timestamp' in result
            assert 'expert_feedback_outcome' in result

    @pytest.mark.asyncio
    async def test_step_122_logs_rejection_details(self):
        """Test that Step 122 logs comprehensive rejection details."""
        ctx = {
            'expert_validation': {
                'trust_score': 0.55,
                'expert_id': 'expert_logging',
                'credentials_validated': False
            },
            'expert_feedback': {
                'feedback_type': 'wrong'
            },
            'trust_score_decision': False,
            'request_id': 'req_logging_test'
        }

        with patch('app.observability.rag_logging.rag_step_log') as mock_log, \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            await step_122__feedback_rejected(ctx=ctx)

            # Verify logging was called
            mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_step_122_rejection_performance_tracking(self):
        """Test that Step 122 tracks rejection performance and timing."""
        ctx = {
            'expert_validation': {
                'trust_score': 0.45,
                'expert_id': 'expert_performance'
            },
            'expert_feedback': {
                'feedback_type': 'incomplete'
            },
            'trust_score_decision': False,
            'request_id': 'req_performance_test'
        }

        with patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_context_manager = Mock()
            mock_timer.return_value = mock_context_manager
            mock_context_manager.__enter__ = Mock()
            mock_context_manager.__exit__ = Mock()

            result = await step_122__feedback_rejected(ctx=ctx)

            # Verify performance tracking in result
            assert 'rejection_timestamp' in result
            assert isinstance(result['rejection_timestamp'], str)

    @pytest.mark.asyncio
    async def test_step_122_error_handling_missing_context(self):
        """Test error handling when required context is missing."""
        ctx = {
            # Missing expert_validation and trust_score_decision
            'expert_feedback': {
                'feedback_type': 'wrong'
            },
            'request_id': 'req_missing_context'
        }

        with patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            result = await step_122__feedback_rejected(ctx=ctx)

            # Should handle missing context gracefully with generic rejection
            assert result['feedback_rejected'] is True
            assert result['rejection_reason'] == 'context_validation_error'
            assert 'error' in result
            assert 'missing_trust_validation_data' in result['error']

    @pytest.mark.asyncio
    async def test_step_122_error_handling_invalid_context(self):
        """Test error handling with malformed context data."""
        ctx = {
            'expert_validation': {
                # Missing trust_score
                'expert_id': 'expert_invalid',
                'credentials_validated': None
            },
            'expert_feedback': None,  # Invalid feedback data
            'trust_score_decision': 'invalid',  # Should be boolean
            'request_id': 'req_invalid_context'
        }

        with patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            result = await step_122__feedback_rejected(ctx=ctx)

            # Should handle invalid context by still processing rejection
            assert result['feedback_rejected'] is True
            assert result['rejection_reason'] == 'context_validation_error'
            assert 'error' in result

    @pytest.mark.asyncio
    async def test_step_122_expert_feedback_outcome_tracking(self):
        """Test that Step 122 properly tracks expert feedback outcomes."""
        # Test different feedback types being rejected
        feedback_types = ['incorrect', 'incomplete', 'wrong', 'misleading']

        for feedback_type in feedback_types:
            ctx = {
                'expert_validation': {
                    'trust_score': 0.3,
                    'expert_id': f'expert_{feedback_type}',
                    'credentials_validated': False
                },
                'expert_feedback': {
                    'feedback_type': feedback_type,
                    'feedback_text': f'{feedback_type} feedback text'
                },
                'trust_score_decision': False,
                'request_id': f'req_{feedback_type}'
            }

            with patch('app.observability.rag_logging.rag_step_log'), \
                 patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

                mock_timer.return_value.__enter__ = Mock()
                mock_timer.return_value.__exit__ = Mock()

                result = await step_122__feedback_rejected(ctx=ctx)

                # Verify outcome tracking for each feedback type
                assert result['expert_feedback_outcome'] == 'rejected'
                assert result['feedback_type_processed'] == feedback_type
                assert result['rejection_reason'] == 'insufficient_trust_score'

    @pytest.mark.asyncio
    async def test_step_122_rejection_metadata_structure(self):
        """Test that Step 122 produces consistent rejection metadata structure."""
        ctx = {
            'expert_validation': {
                'trust_score': 0.6,
                'expert_id': 'expert_metadata',
                'credentials_validated': False
            },
            'expert_feedback': {
                'feedback_type': 'incorrect'
            },
            'trust_score_decision': False,
            'request_id': 'req_metadata_test'
        }

        with patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            result = await step_122__feedback_rejected(ctx=ctx)

            # Verify required rejection metadata fields are present
            required_fields = [
                'feedback_rejected', 'rejection_reason', 'rejection_timestamp',
                'expert_feedback_outcome', 'trust_score'
            ]

            for field in required_fields:
                assert field in result, f"Required field '{field}' missing from rejection result"

            # Verify data types
            assert isinstance(result['feedback_rejected'], bool)
            assert isinstance(result['rejection_reason'], str)
            assert isinstance(result['rejection_timestamp'], str)
            assert isinstance(result['expert_feedback_outcome'], str)


class TestRAGStep122Parity:
    """Parity tests to ensure Step 122 maintains behavioral consistency."""

    @pytest.mark.asyncio
    async def test_step_122_parity_rejection_structure(self):
        """Test that Step 122 maintains consistent rejection output structure."""
        ctx = {
            'expert_validation': {
                'trust_score': 0.5,
                'expert_id': 'expert_parity',
                'credentials_validated': False
            },
            'expert_feedback': {
                'feedback_type': 'wrong'
            },
            'trust_score_decision': False,
            'request_id': 'req_parity_test'
        }

        with patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            result = await step_122__feedback_rejected(ctx=ctx)

            # Verify parity in rejection structure
            assert result['feedback_rejected'] is True
            assert result['rejection_reason'] in ['insufficient_trust_score', 'context_validation_error']
            assert result['expert_feedback_outcome'] == 'rejected'

            # Verify all context data is preserved (parity)
            assert 'expert_validation' in result
            assert 'expert_feedback' in result
            assert 'trust_score_decision' in result


class TestRAGStep122Integration:
    """Integration tests for Step 122 with neighboring steps."""

    @pytest.mark.asyncio
    async def test_step_121_to_122_integration(self):
        """Test integration from Step 121 (TrustScoreOK) to Step 122 (FeedbackRejected)."""
        # Simulate output from Step 121 with rejection decision
        step_121_output = {
            'expert_validation': {
                'trust_score': 0.58,
                'expert_id': 'expert_integration_121',
                'credentials_validated': False,
                'validation_details': {
                    'credentials_score': 0.6,
                    'experience_score': 0.5,
                    'track_record_score': 0.65
                }
            },
            'expert_feedback': {
                'feedback_type': 'incomplete',
                'feedback_text': 'Missing key information',
                'expert_data': {
                    'name': 'Dr. Integration Test',
                    'location': 'Milano'
                }
            },
            'trust_score_decision': False,
            'next_step': 'FeedbackRejected',
            'routing_decision': 'reject_feedback',
            'threshold_met': False,
            'decision_timestamp': '2023-10-01T10:00:00Z',
            'request_id': 'req_121_to_122_integration',
            'trace_id': 'trace_integration_test'
        }

        with patch('app.orchestrators.classify.step_121__trust_score_ok') as mock_step_121, \
             patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_step_121.return_value = step_121_output
            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            # Step 121 → Step 122 (mock returns the data directly)
            step_122_result = await step_122__feedback_rejected(ctx=step_121_output)

            # Verify smooth data flow from Step 121 to 122
            assert step_122_result['expert_validation'] == step_121_output['expert_validation']
            assert step_122_result['trust_score'] == 0.58
            assert step_122_result['trust_score_decision'] is False
            assert step_122_result['feedback_rejected'] is True

            # Verify context continuity
            assert step_122_result['request_id'] == step_121_output['request_id']
            assert step_122_result['trace_id'] == step_121_output['trace_id']

            # Verify rejection-specific processing
            assert step_122_result['rejection_reason'] == 'insufficient_trust_score'
            assert step_122_result['expert_feedback_outcome'] == 'rejected'

    @pytest.mark.asyncio
    async def test_step_122_terminal_node_behavior(self):
        """Test that Step 122 behaves as a terminal/error node in the pipeline."""
        # Step 122 should be a terminal node that doesn't route to further steps
        ctx = {
            'expert_validation': {
                'trust_score': 0.35,
                'expert_id': 'expert_terminal',
                'credentials_validated': False
            },
            'expert_feedback': {
                'feedback_type': 'wrong',
                'feedback_text': 'Incorrect information provided'
            },
            'trust_score_decision': False,
            'threshold_met': False,
            'request_id': 'req_terminal_test'
        }

        with patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            result = await step_122__feedback_rejected(ctx=ctx)

            # Verify terminal node behavior - no next_step routing
            assert 'next_step' not in result or result.get('next_step') is None
            assert result['feedback_rejected'] is True
            assert result['expert_feedback_outcome'] == 'rejected'

            # Verify feedback loop termination
            assert result['pipeline_terminated'] is True
            assert result['termination_reason'] == 'expert_feedback_rejected'

    @pytest.mark.asyncio
    async def test_multiple_rejection_scenarios(self):
        """Test Step 122 with multiple realistic rejection scenarios."""
        # Test various scenarios that lead to feedback rejection
        scenarios = [
            {
                'name': 'new_expert_no_credentials',
                'trust_score': 0.2,
                'expert_data': {
                    'name': 'New Expert',
                    'certifications': [],
                    'experience_years': 0
                },
                'feedback_type': 'incorrect',
                'expected_reason': 'insufficient_trust_score'
            },
            {
                'name': 'expired_credentials',
                'trust_score': 0.45,
                'expert_data': {
                    'name': 'Dr. Expired Creds',
                    'certifications': ['Expired CPA'],
                    'experience_years': 10
                },
                'feedback_type': 'incomplete',
                'expected_reason': 'insufficient_trust_score'
            },
            {
                'name': 'suspicious_activity',
                'trust_score': 0.1,
                'expert_data': {
                    'name': 'Suspicious User',
                    'certifications': ['Unknown'],
                    'flags': ['suspicious_activity']
                },
                'feedback_type': 'wrong',
                'expected_reason': 'insufficient_trust_score'
            }
        ]

        for scenario in scenarios:
            ctx = {
                'expert_validation': {
                    'trust_score': scenario['trust_score'],
                    'expert_id': f'expert_{scenario["name"]}',
                    'credentials_validated': False,
                    'expert_data': scenario['expert_data']
                },
                'expert_feedback': {
                    'feedback_type': scenario['feedback_type'],
                    'expert_data': scenario['expert_data']
                },
                'trust_score_decision': False,
                'threshold_met': False,
                'request_id': f'req_{scenario["name"]}'
            }

            with patch('app.observability.rag_logging.rag_step_log'), \
                 patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

                mock_timer.return_value.__enter__ = Mock()
                mock_timer.return_value.__exit__ = Mock()

                result = await step_122__feedback_rejected(ctx=ctx)

                # Verify scenario-specific rejection handling
                assert result['feedback_rejected'] is True, \
                    f"Failed rejection for scenario: {scenario['name']}"
                assert result['rejection_reason'] == scenario['expected_reason']
                assert result['trust_score'] == scenario['trust_score']
                assert result['expert_feedback_outcome'] == 'rejected'

                # Verify feedback type processing
                assert result['feedback_type_processed'] == scenario['feedback_type']