"""
Tests for RAG Step 117: FAQFeedback (POST /api/v1/faq/feedback).

This step processes FAQ feedback submissions and routes to ExpertFeedbackCollector.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone


class TestRAGStep117FAQFeedback:
    """Unit tests for Step 117: FAQFeedback."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_117_processes_faq_feedback(self, mock_rag_log):
        """Test Step 117: Processes FAQ feedback successfully."""
        from app.orchestrators.golden import step_117__faqfeedback

        ctx = {
            'feedback_data': {
                'usage_log_id': 'usage_123',
                'was_helpful': True,
                'followup_needed': False,
                'comments': 'Very helpful answer!'
            },
            'user_id': 'user_456',
            'session_id': 'session_789',
            'request_id': 'test-117-process'
        }

        with patch('app.services.intelligent_faq_service.IntelligentFAQService') as MockService:
            mock_service = MockService.return_value
            mock_service.collect_feedback = AsyncMock(return_value=True)

            result = await step_117__faqfeedback(messages=[], ctx=ctx)

            assert isinstance(result, dict)
            assert 'feedback_result' in result
            assert result['feedback_result']['success'] is True
            assert result['next_step'] == 'expert_feedback_collector'

            # Verify service was called
            mock_service.collect_feedback.assert_called_once_with(
                usage_log_id='usage_123',
                was_helpful=True,
                followup_needed=False,
                comments='Very helpful answer!'
            )

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_117_handles_missing_usage_log(self, mock_rag_log):
        """Test Step 117: Handles missing usage log gracefully."""
        from app.orchestrators.golden import step_117__faqfeedback

        ctx = {
            'feedback_data': {
                'usage_log_id': 'missing_123',
                'was_helpful': False,
                'followup_needed': True
            },
            'request_id': 'test-117-missing'
        }

        with patch('app.services.intelligent_faq_service.IntelligentFAQService') as MockService:
            mock_service = MockService.return_value
            mock_service.collect_feedback = AsyncMock(return_value=False)

            result = await step_117__faqfeedback(messages=[], ctx=ctx)

            assert result['feedback_result']['success'] is False
            assert 'error' in result['feedback_result']
            # Still routes to next step for error handling
            assert result['next_step'] == 'expert_feedback_collector'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_117_preserves_context(self, mock_rag_log):
        """Test Step 117: Preserves all context data."""
        from app.orchestrators.golden import step_117__faqfeedback

        original_ctx = {
            'feedback_data': {
                'usage_log_id': 'usage_456',
                'was_helpful': True
            },
            'user_data': {'id': 'user_123', 'name': 'Test User'},
            'session_data': {'id': 'session_456'},
            'request_id': 'test-117-context'
        }

        with patch('app.services.intelligent_faq_service.IntelligentFAQService') as MockService:
            mock_service = MockService.return_value
            mock_service.collect_feedback = AsyncMock(return_value=True)

            result = await step_117__faqfeedback(messages=[], ctx=original_ctx.copy())

            # Verify all original context is preserved
            assert result['user_data'] == original_ctx['user_data']
            assert result['session_data'] == original_ctx['session_data']
            assert result['request_id'] == original_ctx['request_id']

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_117_adds_feedback_metadata(self, mock_rag_log):
        """Test Step 117: Adds feedback metadata for tracking."""
        from app.orchestrators.golden import step_117__faqfeedback

        ctx = {
            'feedback_data': {
                'usage_log_id': 'usage_789',
                'was_helpful': True,
                'comments': 'Great!'
            },
            'request_id': 'test-117-metadata'
        }

        with patch('app.services.intelligent_faq_service.IntelligentFAQService') as MockService:
            mock_service = MockService.return_value
            mock_service.collect_feedback = AsyncMock(return_value=True)

            result = await step_117__faqfeedback(messages=[], ctx=ctx)

            assert 'feedback_metadata' in result
            metadata = result['feedback_metadata']
            assert 'submitted_at' in metadata
            assert metadata['feedback_type'] == 'faq'
            assert metadata['was_helpful'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_117_handles_service_error(self, mock_rag_log):
        """Test Step 117: Handles service errors gracefully."""
        from app.orchestrators.golden import step_117__faqfeedback

        ctx = {
            'feedback_data': {
                'usage_log_id': 'usage_error',
                'was_helpful': True
            },
            'request_id': 'test-117-error'
        }

        with patch('app.services.intelligent_faq_service.IntelligentFAQService') as MockService:
            mock_service = MockService.return_value
            mock_service.collect_feedback = AsyncMock(
                side_effect=Exception("Database connection error")
            )

            result = await step_117__faqfeedback(messages=[], ctx=ctx)

            assert result['feedback_result']['success'] is False
            assert 'Database connection error' in result['feedback_result']['error']
            assert result['next_step'] == 'expert_feedback_collector'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_117_logs_feedback_details(self, mock_rag_log):
        """Test Step 117: Logs feedback details for observability."""
        from app.orchestrators.golden import step_117__faqfeedback

        ctx = {
            'feedback_data': {
                'usage_log_id': 'usage_log_123',
                'was_helpful': False,
                'followup_needed': True,
                'comments': 'Needs improvement'
            },
            'request_id': 'test-117-logging'
        }

        with patch('app.services.intelligent_faq_service.IntelligentFAQService') as MockService:
            mock_service = MockService.return_value
            mock_service.collect_feedback = AsyncMock(return_value=True)

            await step_117__faqfeedback(messages=[], ctx=ctx)

            # Verify structured logging
            assert mock_rag_log.call_count >= 2
            final_call = None
            for call in mock_rag_log.call_args_list:
                if call[1].get('processing_stage') == 'completed':
                    final_call = call[1]
                    break

            assert final_call is not None
            assert final_call['step'] == 117
            assert final_call['was_helpful'] is False
            assert final_call['followup_needed'] is True


class TestRAGStep117Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_117_parity_feedback_collection(self):
        """Test Step 117 parity: Feedback collection behavior unchanged."""
        from app.orchestrators.golden import step_117__faqfeedback

        test_cases = [
            {
                'feedback_data': {
                    'usage_log_id': 'log_1',
                    'was_helpful': True,
                    'followup_needed': False,
                    'comments': None
                },
                'expected_success': True
            },
            {
                'feedback_data': {
                    'usage_log_id': 'log_2',
                    'was_helpful': False,
                    'followup_needed': True,
                    'comments': 'Please clarify'
                },
                'expected_success': True
            }
        ]

        with patch('app.services.intelligent_faq_service.IntelligentFAQService') as MockService:
            mock_service = MockService.return_value

            for test_case in test_cases:
                mock_service.collect_feedback = AsyncMock(
                    return_value=test_case['expected_success']
                )

                ctx = {
                    **test_case,
                    'request_id': f"parity-{test_case['feedback_data']['usage_log_id']}"
                }

                with patch('app.orchestrators.golden.rag_step_log'):
                    result = await step_117__faqfeedback(messages=[], ctx=ctx)

                assert result['feedback_result']['success'] == test_case['expected_success']


class TestRAGStep117Integration:
    """Integration tests for Step 117 with neighbors."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_feedback_type_to_117_integration(self, mock_golden_log, mock_feedback_log):
        """Test FeedbackTypeSel → Step 117 integration."""
        # This would test the flow from feedback type selection to FAQ feedback
        # In practice, the FeedbackTypeSel would be another step that routes here

        initial_ctx = {
            'feedback_type': 'faq',
            'feedback_data': {
                'usage_log_id': 'usage_integration',
                'was_helpful': True,
                'followup_needed': False
            },
            'request_id': 'integration-116-117'
        }

        from app.orchestrators.golden import step_117__faqfeedback

        with patch('app.services.intelligent_faq_service.IntelligentFAQService') as MockService:
            mock_service = MockService.return_value
            mock_service.collect_feedback = AsyncMock(return_value=True)

            result = await step_117__faqfeedback(messages=[], ctx=initial_ctx)

            assert result['feedback_type'] == 'faq'
            assert result['next_step'] == 'expert_feedback_collector'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_117_prepares_for_expert_collector(self, mock_rag_log):
        """Test Step 117 prepares data for ExpertFeedbackCollector."""
        from app.orchestrators.golden import step_117__faqfeedback

        ctx = {
            'feedback_data': {
                'usage_log_id': 'usage_expert',
                'was_helpful': False,
                'followup_needed': True,
                'comments': 'Expert review needed'
            },
            'user_id': 'expert_user',
            'request_id': 'test-117-expert-prep'
        }

        with patch('app.services.intelligent_faq_service.IntelligentFAQService') as MockService:
            mock_service = MockService.return_value
            mock_service.collect_feedback = AsyncMock(return_value=True)

            result = await step_117__faqfeedback(messages=[], ctx=ctx)

            # Verify data prepared for expert collector
            assert result['feedback_data']['comments'] == 'Expert review needed'
            assert result['feedback_type'] == 'faq'
            assert result.get('followup_needed') is True
            assert result['next_step'] == 'expert_feedback_collector'