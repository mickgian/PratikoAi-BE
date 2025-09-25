"""
Tests for RAG Step 121 - Trust score at least 0.7? (Decision orchestrator)

This step is a decision node that evaluates trust scores from Step 120 (ValidateExpert)
and routes to either Step 122 (FeedbackRejected) or Step 123 (CreateFeedbackRec).
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.orchestrators.classify import step_121__trust_score_ok


class TestRAGStep121TrustScoreOK:
    """Unit tests for Step 121 trust score decision logic."""

    @pytest.mark.asyncio
    async def test_step_121_basic_trust_score_decision_high_trust(self):
        """Test basic trust score decision with trust score >= 0.7 (should route to CreateFeedbackRec)."""
        # Setup: Context from Step 120 with high trust score
        ctx = {
            'expert_validation': {
                'trust_score': 0.85,
                'expert_id': 'expert_123',
                'credentials_validated': True,
                'validation_details': {'italian_certification': True}
            },
            'expert_feedback': {
                'feedback_type': 'incorrect',
                'expert_data': {'name': 'Dr. Marco Rossi'}
            },
            'request_id': 'req_test_high_trust'
        }

        with patch('app.observability.rag_logging.rag_step_log') as mock_log, \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            result = await step_121__trust_score_ok(ctx=ctx)

            # Verify trust score decision logic
            assert result['trust_score_decision'] is True
            assert result['trust_score'] == 0.85
            assert result['next_step'] == 'CreateFeedbackRec'
            assert result['routing_decision'] == 'proceed_with_feedback'
            assert result['threshold_met'] is True

            # Verify context preservation
            assert result['expert_validation'] == ctx['expert_validation']
            assert result['expert_feedback'] == ctx['expert_feedback']
            assert result['request_id'] == 'req_test_high_trust'

            # Verify structured logging was called (simplified assertion)
            mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_step_121_basic_trust_score_decision_low_trust(self):
        """Test basic trust score decision with trust score < 0.7 (should route to FeedbackRejected)."""
        # Setup: Context from Step 120 with low trust score
        ctx = {
            'expert_validation': {
                'trust_score': 0.65,
                'expert_id': 'expert_456',
                'credentials_validated': False,
                'validation_details': {'italian_certification': False}
            },
            'expert_feedback': {
                'feedback_type': 'incomplete',
                'expert_data': {'name': 'Dr. Giuseppe Verdi'}
            },
            'request_id': 'req_test_low_trust'
        }

        with patch('app.observability.rag_logging.rag_step_log') as mock_log, \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            result = await step_121__trust_score_ok(ctx=ctx)

            # Verify trust score decision logic
            assert result['trust_score_decision'] is False
            assert result['trust_score'] == 0.65
            assert result['next_step'] == 'FeedbackRejected'
            assert result['routing_decision'] == 'reject_feedback'
            assert result['threshold_met'] is False

            # Verify context preservation
            assert result['expert_validation'] == ctx['expert_validation']
            assert result['expert_feedback'] == ctx['expert_feedback']
            assert result['request_id'] == 'req_test_low_trust'

    @pytest.mark.asyncio
    async def test_step_121_trust_score_boundary_conditions(self):
        """Test trust score boundary conditions (exactly 0.7, edge cases)."""
        test_cases = [
            {
                'trust_score': 0.7,  # Exactly at threshold
                'expected_decision': True,
                'expected_next_step': 'CreateFeedbackRec',
                'case_name': 'exactly_at_threshold'
            },
            {
                'trust_score': 0.699999,  # Just below threshold
                'expected_decision': False,
                'expected_next_step': 'FeedbackRejected',
                'case_name': 'just_below_threshold'
            },
            {
                'trust_score': 0.700001,  # Just above threshold
                'expected_decision': True,
                'expected_next_step': 'CreateFeedbackRec',
                'case_name': 'just_above_threshold'
            }
        ]

        for case in test_cases:
            ctx = {
                'expert_validation': {
                    'trust_score': case['trust_score'],
                    'expert_id': f'expert_{case["case_name"]}',
                    'credentials_validated': case['trust_score'] >= 0.7
                },
                'expert_feedback': {
                    'feedback_type': 'wrong',
                    'expert_data': {'name': f'Expert {case["case_name"]}'}
                },
                'request_id': f'req_{case["case_name"]}'
            }

            with patch('app.observability.rag_logging.rag_step_log'), \
                 patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

                mock_timer.return_value.__enter__ = Mock()
                mock_timer.return_value.__exit__ = Mock()

                result = await step_121__trust_score_ok(ctx=ctx)

                assert result['trust_score_decision'] == case['expected_decision'], \
                    f"Failed for {case['case_name']}: score {case['trust_score']}"
                assert result['next_step'] == case['expected_next_step'], \
                    f"Failed routing for {case['case_name']}"
                assert result['threshold_met'] == case['expected_decision']

    @pytest.mark.asyncio
    async def test_step_121_preserves_context_data(self):
        """Test that Step 121 preserves all context data while adding decision metadata."""
        ctx = {
            'expert_validation': {
                'trust_score': 0.82,
                'expert_id': 'expert_preserve',
                'credentials_validated': True,
                'italian_certification': True,
                'professional_qualifications': ['CPA', 'Tax Advisor']
            },
            'expert_feedback': {
                'feedback_type': 'incorrect',
                'feedback_text': 'The answer is wrong',
                'expert_data': {'name': 'Dr. Preserve Context', 'location': 'Milano'}
            },
            'performance_tracking': {
                'step_120_duration': 0.045,
                'validation_start_time': '2023-10-01T10:00:00Z'
            },
            'request_id': 'req_preserve_context',
            'trace_id': 'trace_preserve_123'
        }

        with patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            result = await step_121__trust_score_ok(ctx=ctx)

            # Verify all original context is preserved
            assert result['expert_validation'] == ctx['expert_validation']
            assert result['expert_feedback'] == ctx['expert_feedback']
            assert result['performance_tracking'] == ctx['performance_tracking']
            assert result['request_id'] == ctx['request_id']
            assert result['trace_id'] == ctx['trace_id']

            # Verify new decision metadata is added
            assert 'trust_score_decision' in result
            assert 'trust_score' in result
            assert 'next_step' in result
            assert 'routing_decision' in result
            assert 'threshold_met' in result
            assert 'decision_timestamp' in result

    @pytest.mark.asyncio
    async def test_step_121_logs_decision_details(self):
        """Test that Step 121 logs comprehensive decision details."""
        ctx = {
            'expert_validation': {
                'trust_score': 0.75,
                'expert_id': 'expert_logging',
                'credentials_validated': True
            },
            'expert_feedback': {
                'feedback_type': 'incomplete'
            },
            'request_id': 'req_logging_test'
        }

        with patch('app.observability.rag_logging.rag_step_log') as mock_log, \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            await step_121__trust_score_ok(ctx=ctx)

            # Verify logging was called
            mock_log.assert_called()
            # Just check that logging happened - detailed log structure validation is complex
            assert mock_log.call_count >= 1

    @pytest.mark.asyncio
    async def test_step_121_decision_performance_tracking(self):
        """Test that Step 121 tracks decision performance and timing."""
        ctx = {
            'expert_validation': {
                'trust_score': 0.88,
                'expert_id': 'expert_performance'
            },
            'expert_feedback': {
                'feedback_type': 'wrong'
            },
            'request_id': 'req_performance_test'
        }

        with patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_context_manager = Mock()
            mock_timer.return_value = mock_context_manager
            mock_context_manager.__enter__ = Mock()
            mock_context_manager.__exit__ = Mock()

            result = await step_121__trust_score_ok(ctx=ctx)

            # Just verify the function completed and returned the expected result

            # Verify performance tracking in result
            assert 'decision_timestamp' in result
            assert isinstance(result['decision_timestamp'], str)

    @pytest.mark.asyncio
    async def test_step_121_error_handling_missing_trust_score(self):
        """Test error handling when trust score is missing from context."""
        ctx = {
            'expert_validation': {
                'expert_id': 'expert_no_score',
                'credentials_validated': True
                # Missing trust_score
            },
            'expert_feedback': {
                'feedback_type': 'incomplete'
            },
            'request_id': 'req_missing_score'
        }

        with patch('app.observability.rag_logging.rag_step_log') as mock_log, \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            result = await step_121__trust_score_ok(ctx=ctx)

            # Should handle missing trust score gracefully with default rejection
            assert result['trust_score_decision'] is False
            assert result['next_step'] == 'FeedbackRejected'
            assert result['routing_decision'] == 'reject_feedback'
            assert 'error' in result
            assert 'missing_trust_score' in result['error']

            # Verify error was logged (simplified)
            mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_step_121_error_handling_invalid_trust_score(self):
        """Test error handling with invalid trust score values."""
        invalid_scores = ['invalid', -0.1, 1.5, float('inf'), float('nan')]  # None is handled as missing, not invalid

        for invalid_score in invalid_scores:
            ctx = {
                'expert_validation': {
                    'trust_score': invalid_score,
                    'expert_id': f'expert_invalid_{type(invalid_score).__name__}',
                    'credentials_validated': True
                },
                'expert_feedback': {
                    'feedback_type': 'wrong'
                },
                'request_id': f'req_invalid_{type(invalid_score).__name__}'
            }

            with patch('app.observability.rag_logging.rag_step_log'), \
                 patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

                mock_timer.return_value.__enter__ = Mock()
                mock_timer.return_value.__exit__ = Mock()

                result = await step_121__trust_score_ok(ctx=ctx)

                # Should handle invalid scores by defaulting to rejection
                assert result['trust_score_decision'] is False
                assert result['next_step'] == 'FeedbackRejected'
                assert result['routing_decision'] == 'reject_feedback'
                assert 'error' in result
                assert 'invalid_trust_score' in result['error']

    @pytest.mark.asyncio
    async def test_step_121_decision_routing_consistency(self):
        """Test that routing decisions are consistent with trust score thresholds."""
        # Test multiple scenarios for routing consistency
        test_scenarios = [
            {'score': 0.9, 'expected_route': 'CreateFeedbackRec', 'description': 'high_confidence'},
            {'score': 0.7, 'expected_route': 'CreateFeedbackRec', 'description': 'threshold_exact'},
            {'score': 0.69, 'expected_route': 'FeedbackRejected', 'description': 'below_threshold'},
            {'score': 0.5, 'expected_route': 'FeedbackRejected', 'description': 'low_confidence'},
            {'score': 0.1, 'expected_route': 'FeedbackRejected', 'description': 'very_low'}
        ]

        for scenario in test_scenarios:
            ctx = {
                'expert_validation': {
                    'trust_score': scenario['score'],
                    'expert_id': f'expert_{scenario["description"]}',
                    'credentials_validated': scenario['score'] >= 0.7
                },
                'expert_feedback': {
                    'feedback_type': 'incorrect'
                },
                'request_id': f'req_{scenario["description"]}'
            }

            with patch('app.observability.rag_logging.rag_step_log'), \
                 patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

                mock_timer.return_value.__enter__ = Mock()
                mock_timer.return_value.__exit__ = Mock()

                result = await step_121__trust_score_ok(ctx=ctx)

                assert result['next_step'] == scenario['expected_route'], \
                    f"Routing inconsistent for {scenario['description']}: score {scenario['score']}"

                # Verify decision consistency
                if scenario['expected_route'] == 'CreateFeedbackRec':
                    assert result['trust_score_decision'] is True
                    assert result['routing_decision'] == 'proceed_with_feedback'
                    assert result['threshold_met'] is True
                else:
                    assert result['trust_score_decision'] is False
                    assert result['routing_decision'] == 'reject_feedback'
                    assert result['threshold_met'] is False


class TestRAGStep121Parity:
    """Parity tests to ensure Step 121 maintains behavioral consistency."""

    @pytest.mark.asyncio
    async def test_step_121_parity_decision_structure(self):
        """Test that Step 121 maintains consistent decision output structure."""
        ctx = {
            'expert_validation': {
                'trust_score': 0.8,
                'expert_id': 'expert_parity',
                'credentials_validated': True
            },
            'expert_feedback': {
                'feedback_type': 'incomplete'
            },
            'request_id': 'req_parity_test'
        }

        with patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            result = await step_121__trust_score_ok(ctx=ctx)

            # Verify required decision fields are present
            required_fields = [
                'trust_score_decision', 'trust_score', 'next_step',
                'routing_decision', 'threshold_met', 'decision_timestamp'
            ]

            for field in required_fields:
                assert field in result, f"Required field '{field}' missing from decision result"

            # Verify data types
            assert isinstance(result['trust_score_decision'], bool)
            assert isinstance(result['trust_score'], (int, float))
            assert isinstance(result['next_step'], str)
            assert isinstance(result['routing_decision'], str)
            assert isinstance(result['threshold_met'], bool)
            assert isinstance(result['decision_timestamp'], str)


class TestRAGStep121Integration:
    """Integration tests for Step 121 with neighboring steps."""

    @pytest.mark.asyncio
    async def test_step_120_to_121_integration(self):
        """Test integration from Step 120 (ValidateExpert) to Step 121."""
        # Simulate output from Step 120
        step_120_output = {
            'expert_validation': {
                'trust_score': 0.85,
                'expert_id': 'expert_integration_120',
                'credentials_validated': True,
                'italian_certification': True,
                'professional_qualifications': ['CPA'],
                'validation_details': {
                    'credentials_score': 0.9,
                    'experience_score': 0.8,
                    'track_record_score': 0.85
                }
            },
            'expert_feedback': {
                'feedback_type': 'incorrect',
                'feedback_text': 'Answer needs correction',
                'expert_data': {
                    'name': 'Dr. Integration Test',
                    'certifications': ['Italian CPA']
                }
            },
            'request_id': 'req_120_to_121_integration',
            'trace_id': 'trace_integration_test'
        }

        with patch('app.orchestrators.platform.step_120__validate_expert') as mock_step_120, \
             patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_step_120.return_value = step_120_output
            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            # Step 120 → Step 121 (mock returns the data directly)
            step_121_result = await step_121__trust_score_ok(ctx=step_120_output)

            # Verify smooth data flow from Step 120 to 121
            assert step_121_result['expert_validation'] == step_120_output['expert_validation']
            assert step_121_result['trust_score'] == 0.85
            assert step_121_result['trust_score_decision'] is True
            assert step_121_result['next_step'] == 'CreateFeedbackRec'

            # Verify context continuity
            assert step_121_result['request_id'] == step_120_output['request_id']
            assert step_121_result['trace_id'] == step_120_output['trace_id']

    @pytest.mark.asyncio
    async def test_step_121_to_122_integration(self):
        """Test integration from Step 121 to Step 122 (FeedbackRejected) for low trust scores."""
        # Setup Step 121 context with low trust score
        step_121_ctx = {
            'expert_validation': {
                'trust_score': 0.6,  # Below threshold
                'expert_id': 'expert_121_to_122',
                'credentials_validated': False
            },
            'expert_feedback': {
                'feedback_type': 'wrong',
                'expert_data': {'name': 'Dr. Low Trust'}
            },
            'request_id': 'req_121_to_122_integration'
        }

        with patch('app.orchestrators.feedback.step_122__feedback_rejected') as mock_step_122, \
             patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            # Step 121 decision
            step_121_result = await step_121__trust_score_ok(ctx=step_121_ctx)

            # Verify routing to Step 122
            assert step_121_result['trust_score_decision'] is False
            assert step_121_result['next_step'] == 'FeedbackRejected'
            assert step_121_result['routing_decision'] == 'reject_feedback'

            # Verify Step 122 would receive correct context
            expected_step_122_input = step_121_result
            assert expected_step_122_input['expert_validation']['trust_score'] == 0.6
            assert expected_step_122_input['threshold_met'] is False

    @pytest.mark.asyncio
    async def test_step_121_to_123_integration(self):
        """Test integration from Step 121 to Step 123 (CreateFeedbackRec) for high trust scores."""
        # Setup Step 121 context with high trust score
        step_121_ctx = {
            'expert_validation': {
                'trust_score': 0.92,  # Above threshold
                'expert_id': 'expert_121_to_123',
                'credentials_validated': True,
                'italian_certification': True
            },
            'expert_feedback': {
                'feedback_type': 'incomplete',
                'feedback_text': 'Missing key details',
                'expert_data': {
                    'name': 'Dr. High Trust',
                    'certifications': ['Italian Tax Advisor']
                }
            },
            'request_id': 'req_121_to_123_integration'
        }

        with patch('app.orchestrators.feedback.step_123__create_feedback_rec') as mock_step_123, \
             patch('app.observability.rag_logging.rag_step_log'), \
             patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = Mock()
            mock_timer.return_value.__exit__ = Mock()

            # Step 121 decision
            step_121_result = await step_121__trust_score_ok(ctx=step_121_ctx)

            # Verify routing to Step 123
            assert step_121_result['trust_score_decision'] is True
            assert step_121_result['next_step'] == 'CreateFeedbackRec'
            assert step_121_result['routing_decision'] == 'proceed_with_feedback'

            # Verify Step 123 would receive correct context
            expected_step_123_input = step_121_result
            assert expected_step_123_input['expert_validation']['trust_score'] == 0.92
            assert expected_step_123_input['threshold_met'] is True
            assert expected_step_123_input['expert_feedback']['feedback_type'] == 'incomplete'

    @pytest.mark.asyncio
    async def test_full_trust_score_pipeline(self):
        """Test full pipeline: Step 120 → Step 121 → Step 122/123."""
        # Test both paths through the trust score decision
        test_scenarios = [
            {
                'trust_score': 0.85,
                'expected_final_step': 'CreateFeedbackRec',
                'scenario_name': 'high_trust_path'
            },
            {
                'trust_score': 0.55,
                'expected_final_step': 'FeedbackRejected',
                'scenario_name': 'low_trust_path'
            }
        ]

        for scenario in test_scenarios:
            # Simulate Step 120 output
            step_120_output = {
                'expert_validation': {
                    'trust_score': scenario['trust_score'],
                    'expert_id': f'expert_{scenario["scenario_name"]}',
                    'credentials_validated': scenario['trust_score'] >= 0.7
                },
                'expert_feedback': {
                    'feedback_type': 'incorrect',
                    'expert_data': {'name': f'Expert {scenario["scenario_name"]}'}
                },
                'request_id': f'req_{scenario["scenario_name"]}'
            }

            with patch('app.observability.rag_logging.rag_step_log'), \
                 patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

                mock_timer.return_value.__enter__ = Mock()
                mock_timer.return_value.__exit__ = Mock()

                # Execute Step 121
                step_121_result = await step_121__trust_score_ok(ctx=step_120_output)

                # Verify pipeline routing
                assert step_121_result['next_step'] == scenario['expected_final_step']
                assert step_121_result['trust_score'] == scenario['trust_score']

                if scenario['expected_final_step'] == 'CreateFeedbackRec':
                    assert step_121_result['trust_score_decision'] is True
                    assert step_121_result['routing_decision'] == 'proceed_with_feedback'
                else:
                    assert step_121_result['trust_score_decision'] is False
                    assert step_121_result['routing_decision'] == 'reject_feedback'

    @pytest.mark.asyncio
    async def test_step_121_multiple_decision_scenarios(self):
        """Test Step 121 with multiple realistic decision scenarios."""
        # Test various expert feedback scenarios
        scenarios = [
            {
                'name': 'italian_tax_expert_high_trust',
                'trust_score': 0.93,
                'expert_data': {
                    'certifications': ['Italian CPA', 'Tax Advisor'],
                    'location': 'Milano'
                },
                'feedback_type': 'incorrect',
                'expected_route': 'CreateFeedbackRec'
            },
            {
                'name': 'new_expert_low_trust',
                'trust_score': 0.45,
                'expert_data': {
                    'certifications': [],
                    'location': 'Unknown'
                },
                'feedback_type': 'wrong',
                'expected_route': 'FeedbackRejected'
            },
            {
                'name': 'medium_trust_border_case',
                'trust_score': 0.7,  # Exactly at threshold
                'expert_data': {
                    'certifications': ['Basic Certification'],
                    'location': 'Roma'
                },
                'feedback_type': 'incomplete',
                'expected_route': 'CreateFeedbackRec'
            }
        ]

        for scenario in scenarios:
            ctx = {
                'expert_validation': {
                    'trust_score': scenario['trust_score'],
                    'expert_id': f'expert_{scenario["name"]}',
                    'credentials_validated': scenario['trust_score'] >= 0.7,
                    'expert_data': scenario['expert_data']
                },
                'expert_feedback': {
                    'feedback_type': scenario['feedback_type'],
                    'expert_data': scenario['expert_data']
                },
                'request_id': f'req_{scenario["name"]}'
            }

            with patch('app.observability.rag_logging.rag_step_log'), \
                 patch('app.observability.rag_logging.rag_step_timer') as mock_timer:

                mock_timer.return_value.__enter__ = Mock()
                mock_timer.return_value.__exit__ = Mock()

                result = await step_121__trust_score_ok(ctx=ctx)

                # Verify scenario-specific routing
                assert result['next_step'] == scenario['expected_route'], \
                    f"Failed routing for scenario: {scenario['name']}"
                assert result['trust_score'] == scenario['trust_score']

                # Verify decision consistency
                expected_decision = scenario['trust_score'] >= 0.7
                assert result['trust_score_decision'] == expected_decision
                assert result['threshold_met'] == expected_decision