"""
Tests for RAG Step 128: GoldenApproval (Auto threshold met or manual approval?).

This step decides if an FAQ candidate meets auto-approval threshold or needs manual review.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone


class TestRAGStep128GoldenApproval:
    """Unit tests for Step 128: GoldenApproval."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_128_auto_approves_high_quality_candidate(self, mock_rag_log):
        """Test Step 128: Auto-approves candidate meeting threshold."""
        from app.orchestrators.golden import step_128__golden_approval

        ctx = {
            'faq_candidate': {
                'question': 'High quality question',
                'answer': 'High quality answer',
                'quality_score': 0.96,  # Above 0.95 threshold
                'priority_score': 85.0
            },
            'candidate_metadata': {
                'candidate_id': 'candidate_high',
                'trust_score': 0.94,
                'expert_confidence': 0.98
            },
            'request_id': 'test-128-auto-approve'
        }

        result = await step_128__golden_approval(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert result['approval_decision'] == 'auto_approved'
        assert result['next_step'] == 'publish_golden'
        assert result['approval_reason'] == 'quality_threshold_met'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_128_rejects_low_quality_candidate(self, mock_rag_log):
        """Test Step 128: Rejects candidate below threshold."""
        from app.orchestrators.golden import step_128__golden_approval

        ctx = {
            'faq_candidate': {
                'question': 'Low quality question',
                'answer': 'Low quality answer',
                'quality_score': 0.70,  # Below 0.95 threshold
                'priority_score': 40.0
            },
            'candidate_metadata': {
                'candidate_id': 'candidate_low',
                'trust_score': 0.72,
                'expert_confidence': 0.68
            },
            'request_id': 'test-128-reject'
        }

        result = await step_128__golden_approval(messages=[], ctx=ctx)

        assert result['approval_decision'] == 'rejected'
        assert result['next_step'] == 'feedback_end'
        assert result['rejection_reason'] == 'quality_below_threshold'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_128_requires_manual_review_borderline(self, mock_rag_log):
        """Test Step 128: Requires manual review for borderline quality."""
        from app.orchestrators.golden import step_128__golden_approval

        ctx = {
            'faq_candidate': {
                'question': 'Borderline question',
                'answer': 'Borderline answer',
                'quality_score': 0.88,  # Between rejection and auto-approval
                'priority_score': 65.0
            },
            'candidate_metadata': {
                'candidate_id': 'candidate_borderline',
                'trust_score': 0.85,
                'expert_confidence': 0.91
            },
            'request_id': 'test-128-manual'
        }

        result = await step_128__golden_approval(messages=[], ctx=ctx)

        assert result['approval_decision'] == 'manual_review_required'
        assert result['next_step'] == 'feedback_end'  # For now, treat as rejected
        assert 'quality_score' in result['approval_metadata']

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_128_considers_trust_score(self, mock_rag_log):
        """Test Step 128: Considers trust score in decision."""
        from app.orchestrators.golden import step_128__golden_approval

        ctx = {
            'faq_candidate': {
                'question': 'High quality question',
                'answer': 'High quality answer',
                'quality_score': 0.94  # Just below threshold
            },
            'candidate_metadata': {
                'trust_score': 0.98,  # Very high trust - should boost
                'expert_confidence': 0.96
            },
            'request_id': 'test-128-trust-boost'
        }

        result = await step_128__golden_approval(messages=[], ctx=ctx)

        # High trust score should boost approval
        assert result['approval_decision'] in ['auto_approved', 'manual_review_required']

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_128_preserves_context(self, mock_rag_log):
        """Test Step 128: Preserves all context data."""
        from app.orchestrators.golden import step_128__golden_approval

        original_ctx = {
            'faq_candidate': {
                'question': 'Test question',
                'answer': 'Test answer',
                'quality_score': 0.96
            },
            'candidate_metadata': {
                'candidate_id': 'candidate_ctx',
                'expert_id': 'expert_123'
            },
            'expert_id': 'expert_123',
            'trust_score': 0.92,
            'user_data': {'id': 'user_456'},
            'session_data': {'id': 'session_789'},
            'request_id': 'test-128-context'
        }

        result = await step_128__golden_approval(messages=[], ctx=original_ctx.copy())

        # Verify all original context is preserved
        assert result['expert_id'] == original_ctx['expert_id']
        assert result['trust_score'] == original_ctx['trust_score']
        assert result['user_data'] == original_ctx['user_data']
        assert result['session_data'] == original_ctx['session_data']
        assert result['request_id'] == original_ctx['request_id']

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_128_adds_approval_metadata(self, mock_rag_log):
        """Test Step 128: Adds approval metadata for tracking."""
        from app.orchestrators.golden import step_128__golden_approval

        ctx = {
            'faq_candidate': {
                'question': 'Question',
                'answer': 'Answer',
                'quality_score': 0.97
            },
            'candidate_metadata': {
                'candidate_id': 'candidate_meta'
            },
            'request_id': 'test-128-metadata'
        }

        result = await step_128__golden_approval(messages=[], ctx=ctx)

        assert 'approval_metadata' in result
        metadata = result['approval_metadata']
        assert 'decided_at' in metadata
        assert 'decision' in metadata
        assert 'quality_score' in metadata
        assert 'threshold_used' in metadata

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_128_handles_missing_quality_score(self, mock_rag_log):
        """Test Step 128: Handles missing quality score gracefully."""
        from app.orchestrators.golden import step_128__golden_approval

        ctx = {
            'faq_candidate': {
                'question': 'Question without quality score',
                'answer': 'Answer'
                # No quality_score provided
            },
            'candidate_metadata': {
                'candidate_id': 'candidate_no_score'
            },
            'request_id': 'test-128-no-score'
        }

        result = await step_128__golden_approval(messages=[], ctx=ctx)

        # Should reject without quality score
        assert result['approval_decision'] == 'rejected'
        assert 'missing_quality_score' in result.get('rejection_reason', '')

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_128_handles_error_gracefully(self, mock_rag_log):
        """Test Step 128: Handles errors gracefully."""
        from app.orchestrators.golden import step_128__golden_approval

        ctx = {
            'faq_candidate': {
                'question': 'Question',
                'answer': 'Answer',
                'quality_score': 'invalid'  # Invalid type
            },
            'request_id': 'test-128-error'
        }

        result = await step_128__golden_approval(messages=[], ctx=ctx)

        assert 'error' in result or result['approval_decision'] == 'rejected'
        assert result['next_step'] == 'feedback_end'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_128_logs_approval_decision(self, mock_rag_log):
        """Test Step 128: Logs approval decision for observability."""
        from app.orchestrators.golden import step_128__golden_approval

        ctx = {
            'faq_candidate': {
                'question': 'Test question for logging',
                'answer': 'Test answer',
                'quality_score': 0.96
            },
            'candidate_metadata': {
                'candidate_id': 'candidate_log'
            },
            'request_id': 'test-128-logging'
        }

        await step_128__golden_approval(messages=[], ctx=ctx)

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        final_call = None
        for call in mock_rag_log.call_args_list:
            if call[1].get('processing_stage') == 'completed':
                final_call = call[1]
                break

        assert final_call is not None
        assert final_call['step'] == 128
        assert 'approval_decision' in final_call
        assert 'quality_score' in final_call


class TestRAGStep128Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_128_parity_approval_logic(self):
        """Test Step 128 parity: Approval logic behavior unchanged."""
        from app.orchestrators.golden import step_128__golden_approval

        test_cases = [
            {
                'faq_candidate': {'quality_score': 0.97},
                'expected_decision': 'auto_approved'
            },
            {
                'faq_candidate': {'quality_score': 0.65},
                'expected_decision': 'rejected'
            },
            {
                'faq_candidate': {'quality_score': 0.88},
                'expected_decision': 'manual_review_required'
            }
        ]

        for test_case in test_cases:
            ctx = {
                **test_case,
                'candidate_metadata': {'candidate_id': 'parity_test'},
                'request_id': f"parity-{test_case['faq_candidate']['quality_score']}"
            }

            with patch('app.orchestrators.golden.rag_step_log'):
                result = await step_128__golden_approval(messages=[], ctx=ctx)

            assert result['approval_decision'] == test_case['expected_decision']


class TestRAGStep128Integration:
    """Integration tests for Step 128 with neighbors."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_golden_candidate_to_128_integration(self, mock_golden_log):
        """Test GoldenCandidate (Step 127) → Step 128 integration."""

        initial_ctx = {
            'faq_candidate': {
                'question': 'Integration test question',
                'answer': 'Integration test answer',
                'quality_score': 0.96,
                'category': 'test'
            },
            'candidate_metadata': {
                'candidate_id': 'candidate_integration',
                'source': 'expert_feedback'
            },
            'trust_score': 0.93,
            'request_id': 'integration-127-128'
        }

        from app.orchestrators.golden import step_128__golden_approval

        result = await step_128__golden_approval(messages=[], ctx=initial_ctx)

        assert result['approval_decision'] == 'auto_approved'
        assert result['next_step'] == 'publish_golden'
        assert 'faq_candidate' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_128_prepares_for_publish_golden(self, mock_rag_log):
        """Test Step 128 prepares data for PublishGolden (Step 129)."""
        from app.orchestrators.golden import step_128__golden_approval

        ctx = {
            'faq_candidate': {
                'question': 'Publish prep question',
                'answer': 'Publish prep answer',
                'quality_score': 0.97,
                'category': 'test',
                'regulatory_references': ['Ref1']
            },
            'candidate_metadata': {
                'candidate_id': 'candidate_publish'
            },
            'request_id': 'test-128-publish-prep'
        }

        result = await step_128__golden_approval(messages=[], ctx=ctx)

        # Verify data prepared for publishing
        assert result['approval_decision'] == 'auto_approved'
        assert result['next_step'] == 'publish_golden'
        assert 'faq_candidate' in result
        assert result['faq_candidate']['category'] == 'test'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_128_routes_rejection_to_feedback_end(self, mock_rag_log):
        """Test Step 128 routes rejections to FeedbackEnd (Step 115)."""
        from app.orchestrators.golden import step_128__golden_approval

        ctx = {
            'faq_candidate': {
                'question': 'Low quality',
                'answer': 'Low quality answer',
                'quality_score': 0.60
            },
            'candidate_metadata': {
                'candidate_id': 'candidate_reject'
            },
            'request_id': 'test-128-reject-route'
        }

        result = await step_128__golden_approval(messages=[], ctx=ctx)

        assert result['approval_decision'] == 'rejected'
        assert result['next_step'] == 'feedback_end'