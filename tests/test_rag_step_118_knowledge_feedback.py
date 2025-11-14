"""
Test Suite for RAG Step 118: POST /api/v1/knowledge/feedback
Process orchestrator that handles knowledge feedback submission and routes to expert feedback collector.

Following MASTER_GUARDRAILS methodology:
- Unit tests: Core functionality, error handling, context preservation
- Parity tests: Behavioral consistency before/after orchestrator
- Integration tests: Step 116→118, 118→119, and full pipeline flows
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import the orchestrator function
from app.orchestrators.kb import step_118__knowledge_feedback


class TestRAGStep118KnowledgeFeedback:
    """Unit tests for Step 118 knowledge feedback orchestrator."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_118_basic_knowledge_feedback_submission(self, mock_rag_log):
        """Test Step 118: Basic knowledge feedback submission."""
        ctx = {
            'feedback_data': {
                'knowledge_item_id': 123,
                'rating': 4,
                'feedback_text': 'Very helpful information',
                'feedback_type': 'helpful',
                'search_query': 'tax deductions 2024'
            },
            'user_id': 'user_456',
            'session_id': 'session_789'
        }

        result = await step_118__knowledge_feedback(messages=[], ctx=ctx)

        # Verify result structure and routing
        assert result is not None
        assert result['knowledge_feedback_submitted'] is True
        assert result['feedback_id'] is not None
        assert result['next_step'] == 'expert_feedback_collector'  # Routes to Step 119
        assert result['knowledge_item_id'] == 123
        assert result['feedback_rating'] == 4

        # Verify context preservation
        assert result['user_id'] == 'user_456'
        assert result['session_id'] == 'session_789'
        assert result['feedback_data']['feedback_type'] == 'helpful'

        # Verify logging
        mock_rag_log.assert_called()
        assert any('knowledge_feedback_submitted' in str(call) for call in mock_rag_log.call_args_list)

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_118_knowledge_feedback_with_ratings(self, mock_rag_log):
        """Test Step 118: Knowledge feedback with different rating levels."""
        test_cases = [
            {'rating': 1, 'feedback_type': 'incorrect'},
            {'rating': 3, 'feedback_type': 'outdated'},
            {'rating': 5, 'feedback_type': 'accurate'}
        ]

        for test_case in test_cases:
            ctx = {
                'feedback_data': {
                    'knowledge_item_id': 456,
                    'rating': test_case['rating'],
                    'feedback_text': f'Test feedback for rating {test_case["rating"]}',
                    'feedback_type': test_case['feedback_type']
                },
                'user_id': 'user_123',
                'session_id': 'session_456'
            }

            result = await step_118__knowledge_feedback(messages=[], ctx=ctx)

            assert result['knowledge_feedback_submitted'] is True
            assert result['feedback_rating'] == test_case['rating']
            assert result['feedback_type'] == test_case['feedback_type']
            assert result['next_step'] == 'expert_feedback_collector'

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_118_preserves_context_data(self, mock_rag_log):
        """Test Step 118: Preserves all context data while adding feedback metadata."""
        ctx = {
            'request_id': 'req_12345',
            'user_query': 'original query',
            'classification_data': {'domain': 'tax', 'confidence': 0.85},
            'feedback_data': {
                'knowledge_item_id': 789,
                'rating': 4,
                'feedback_text': 'Good information',
                'feedback_type': 'helpful',
                'search_query': 'payroll tax 2024'
            },
            'session_metadata': {'start_time': '2024-01-01T10:00:00Z'}
        }

        result = await step_118__knowledge_feedback(messages=[], ctx=ctx)

        # Verify context preservation
        assert result['request_id'] == 'req_12345'
        assert result['user_query'] == 'original query'
        assert result['classification_data'] == {'domain': 'tax', 'confidence': 0.85}
        assert result['session_metadata'] == {'start_time': '2024-01-01T10:00:00Z'}

        # Verify feedback processing
        assert result['knowledge_feedback_submitted'] is True
        assert result['feedback_id'] is not None
        assert result['knowledge_item_id'] == 789

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_118_logs_feedback_details(self, mock_rag_log):
        """Test Step 118: Logs comprehensive feedback submission details."""
        ctx = {
            'feedback_data': {
                'knowledge_item_id': 999,
                'rating': 2,
                'feedback_text': 'Needs improvement',
                'feedback_type': 'outdated',
                'search_query': 'covid regulations'
            },
            'user_id': 'expert_user',
            'session_id': 'session_999'
        }

        result = await step_118__knowledge_feedback(messages=[], ctx=ctx)

        # Verify logging calls contain expected details
        mock_rag_log.assert_called()
        log_calls = [str(call) for call in mock_rag_log.call_args_list]

        # Check for specific log attributes
        assert any('knowledge_item_id' in call for call in log_calls)
        assert any('feedback_rating' in call for call in log_calls)
        assert any('feedback_type' in call for call in log_calls)
        assert any('expert_feedback_collector' in call for call in log_calls)

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_118_feedback_submission_tracking(self, mock_rag_log):
        """Test Step 118: Tracks feedback submission performance and timing."""
        ctx = {
            'feedback_data': {
                'knowledge_item_id': 111,
                'rating': 5,
                'feedback_text': 'Excellent resource',
                'feedback_type': 'accurate'
            }
        }

        result = await step_118__knowledge_feedback(messages=[], ctx=ctx)

        # Verify performance tracking
        assert 'feedback_submission_time_ms' in result
        assert isinstance(result['feedback_submission_time_ms'], (int, float))
        assert result['feedback_submission_time_ms'] >= 0

        # Verify successful submission tracking
        assert result['knowledge_feedback_submitted'] is True
        assert result['submission_status'] == 'success'

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_118_error_handling_missing_feedback_data(self, mock_rag_log):
        """Test Step 118: Handle missing or invalid feedback data gracefully."""
        ctx = {
            'user_id': 'user_123',
            'session_id': 'session_123'
            # Missing feedback_data
        }

        result = await step_118__knowledge_feedback(messages=[], ctx=ctx)

        # Should handle gracefully and still route to expert feedback collector
        assert result['knowledge_feedback_submitted'] is False
        assert result['next_step'] == 'expert_feedback_collector'
        assert result['error_type'] == 'missing_feedback_data'
        assert 'error_message' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_118_error_handling_invalid_knowledge_item(self, mock_rag_log):
        """Test Step 118: Handle invalid knowledge item ID gracefully."""
        ctx = {
            'feedback_data': {
                'knowledge_item_id': -1,  # Invalid ID
                'rating': 3,
                'feedback_type': 'helpful'
            }
        }

        result = await step_118__knowledge_feedback(messages=[], ctx=ctx)

        # Should handle gracefully
        assert result['knowledge_feedback_submitted'] is False
        assert result['next_step'] == 'expert_feedback_collector'
        assert result['error_type'] == 'invalid_knowledge_item'

        # Verify error logging - check the actual log parameters
        mock_rag_log.assert_called()
        # The error_type should be in the final completed log call
        assert mock_rag_log.call_count >= 2  # started and completed calls

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_118_contextual_feedback_detection(self, mock_rag_log):
        """Test Step 118: Detects and processes contextual feedback signals."""
        ctx = {
            'feedback_data': {
                'knowledge_item_id': 222,
                'rating': 1,
                'feedback_text': 'This information is completely wrong',
                'feedback_type': 'incorrect'
            },
            'expert_user': True,  # Expert user context
            'expert_feedback': True
        }

        result = await step_118__knowledge_feedback(messages=[], ctx=ctx)

        # Should detect expert context
        assert result['knowledge_feedback_submitted'] is True
        assert result['expert_feedback_detected'] is True
        assert result['feedback_priority'] == 'high'  # Expert feedback gets high priority
        assert result['next_step'] == 'expert_feedback_collector'

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_118_feedback_routing_consistency(self, mock_rag_log):
        """Test Step 118: Ensures consistent routing to Step 119 regardless of feedback type."""
        feedback_types = ['helpful', 'accurate', 'outdated', 'incorrect', 'incomplete']

        for feedback_type in feedback_types:
            ctx = {
                'feedback_data': {
                    'knowledge_item_id': 333,
                    'rating': 3,
                    'feedback_type': feedback_type
                }
            }

            result = await step_118__knowledge_feedback(messages=[], ctx=ctx)

            # All knowledge feedback should route to expert feedback collector
            assert result['next_step'] == 'expert_feedback_collector'
            assert result['feedback_type'] == feedback_type


class TestRAGStep118Parity:
    """Parity tests ensuring behavioral consistency before/after orchestrator."""

    @pytest.mark.asyncio
    async def test_step_118_parity_feedback_submission_structure(self):
        """Test Step 118: Maintains consistent output structure for knowledge feedback."""
        ctx = {
            'feedback_data': {
                'knowledge_item_id': 444,
                'rating': 4,
                'feedback_text': 'Very useful',
                'feedback_type': 'helpful'
            },
            'user_id': 'user_444',
            'session_id': 'session_444'
        }

        result = await step_118__knowledge_feedback(messages=[], ctx=ctx)

        # Verify expected output structure matches API expectations
        expected_fields = [
            'knowledge_feedback_submitted', 'feedback_id', 'knowledge_item_id',
            'feedback_rating', 'feedback_type', 'next_step', 'user_id', 'session_id'
        ]

        for field in expected_fields:
            assert field in result, f"Expected field '{field}' missing from result"

        # Verify routing consistency
        assert result['next_step'] == 'expert_feedback_collector'


class TestRAGStep118Integration:
    """Integration tests for Step 118 with neighboring steps."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.step_116__feedback_type_sel')
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_116_to_118_integration(self, mock_rag_log, mock_step_116):
        """Test Step 116→118: Feedback type selection routes to knowledge feedback."""
        # Mock Step 116 routing to Step 118
        mock_step_116.return_value = {
            'feedback_routing_decision': 'knowledge_feedback',
            'next_step': 'knowledge_feedback_endpoint',
            'feedback_data': {
                'knowledge_item_id': 555,
                'rating': 3,
                'feedback_type': 'outdated'
            },
            'routing_reason': 'feedback_type_kb'
        }

        # Call Step 116 first
        step_116_result = await mock_step_116(
            messages=[],
            ctx={'feedback_type': 'kb', 'feedback_data': {'knowledge_item_id': 555}}
        )

        # Then call Step 118 with Step 116's output
        step_118_result = await step_118__knowledge_feedback(
            messages=[],
            ctx=step_116_result
        )

        # Verify integration flow
        assert step_116_result['next_step'] == 'knowledge_feedback_endpoint'
        assert step_118_result['knowledge_feedback_submitted'] is True
        assert step_118_result['next_step'] == 'expert_feedback_collector'
        assert step_118_result['knowledge_item_id'] == 555

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_118_to_119_integration(self, mock_rag_log):
        """Test Step 118→119: Knowledge feedback routes to expert feedback collector."""
        # Call Step 118
        step_118_result = await step_118__knowledge_feedback(
            messages=[],
            ctx={
                'feedback_data': {
                    'knowledge_item_id': 666,
                    'rating': 2,
                    'feedback_type': 'incorrect'
                }
            }
        )

        # Verify Step 118 prepares proper routing to Step 119
        assert step_118_result['next_step'] == 'expert_feedback_collector'
        assert step_118_result['knowledge_feedback_submitted'] is True
        assert step_118_result['knowledge_item_id'] == 666
        assert step_118_result['feedback_type'] == 'incorrect'

        # Verify all context is preserved for Step 119
        assert 'feedback_data' in step_118_result
        assert step_118_result['feedback_data']['knowledge_item_id'] == 666

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.step_116__feedback_type_sel')
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_full_knowledge_feedback_pipeline(self, mock_rag_log, mock_step_116):
        """Test Step 116→118→119: Full knowledge feedback pipeline integration."""
        # Mock Step 116
        mock_step_116.return_value = {
            'feedback_routing_decision': 'knowledge_feedback',
            'next_step': 'knowledge_feedback_endpoint',
            'feedback_data': {
                'knowledge_item_id': 777,
                'rating': 5,
                'feedback_type': 'accurate'
            }
        }

        # Execute pipeline through Step 118
        step_116_result = await mock_step_116(messages=[], ctx={'feedback_type': 'kb'})
        step_118_result = await step_118__knowledge_feedback(messages=[], ctx=step_116_result)

        # Verify pipeline flow through Step 118
        assert step_116_result['feedback_routing_decision'] == 'knowledge_feedback'
        assert step_118_result['knowledge_feedback_submitted'] is True
        assert step_118_result['knowledge_item_id'] == 777
        assert step_118_result['next_step'] == 'expert_feedback_collector'  # Ready for Step 119

        # Verify Step 118 preserves Step 116 routing context
        assert step_118_result['feedback_routing_decision'] == 'knowledge_feedback'
        assert step_118_result['feedback_type'] == 'accurate'

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_118_multiple_feedback_scenarios(self, mock_rag_log):
        """Test Step 118: Multiple feedback scenarios in sequence."""
        test_scenarios = [
            {
                'name': 'positive_feedback',
                'ctx': {
                    'feedback_data': {
                        'knowledge_item_id': 888,
                        'rating': 5,
                        'feedback_type': 'helpful'
                    }
                },
                'expected_priority': 'normal'
            },
            {
                'name': 'negative_expert_feedback',
                'ctx': {
                    'feedback_data': {
                        'knowledge_item_id': 888,
                        'rating': 1,
                        'feedback_type': 'incorrect'
                    },
                    'expert_user': True,
                    'expert_feedback': True
                },
                'expected_priority': 'high'
            },
            {
                'name': 'outdated_content_feedback',
                'ctx': {
                    'feedback_data': {
                        'knowledge_item_id': 888,
                        'rating': 2,
                        'feedback_type': 'outdated'
                    }
                },
                'expected_priority': 'normal'
            }
        ]

        for scenario in test_scenarios:
            result = await step_118__knowledge_feedback(messages=[], ctx=scenario['ctx'])

            assert result['knowledge_feedback_submitted'] is True
            assert result['next_step'] == 'expert_feedback_collector'
            assert result['knowledge_item_id'] == 888

            if 'expected_priority' in scenario:
                if scenario['expected_priority'] == 'high':
                    assert result.get('expert_feedback_detected') is True
                    assert result.get('feedback_priority') == 'high'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])