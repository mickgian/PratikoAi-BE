"""
Tests for RAG Step 127: GoldenCandidate (GoldenSetUpdater.propose_candidate from expert feedback).

This step proposes a new FAQ candidate for the Golden Set based on expert feedback.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from decimal import Decimal


class TestRAGStep127GoldenCandidate:
    """Unit tests for Step 127: GoldenCandidate."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_127_proposes_candidate_from_expert_feedback(self, mock_rag_log):
        """Test Step 127: Proposes FAQ candidate from expert feedback."""
        from app.orchestrators.golden import step_127__golden_candidate

        ctx = {
            'expert_feedback': {
                'id': 'feedback_123',
                'query_text': 'How do I calculate INPS contributions?',
                'expert_answer': 'INPS contributions are calculated based on...',
                'category': 'contributions',
                'regulatory_references': ['D.L. 201/2011', 'Circolare INPS 45/2023'],
                'confidence_score': 0.95
            },
            'expert_id': 'expert_456',
            'trust_score': 0.92,
            'request_id': 'test-127-propose'
        }

        result = await step_127__golden_candidate(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert 'faq_candidate' in result
        assert result['faq_candidate']['question'] == ctx['expert_feedback']['query_text']
        assert result['faq_candidate']['answer'] == ctx['expert_feedback']['expert_answer']
        assert result['faq_candidate']['category'] == 'contributions'
        assert result['next_step'] == 'golden_approval'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_127_calculates_priority_score(self, mock_rag_log):
        """Test Step 127: Calculates priority score for candidate."""
        from app.orchestrators.golden import step_127__golden_candidate

        ctx = {
            'expert_feedback': {
                'query_text': 'What are the deadlines for F24 payment?',
                'expert_answer': 'F24 payment deadlines are...',
                'confidence_score': 0.90,
                'frequency': 45  # High frequency query
            },
            'trust_score': 0.88,
            'request_id': 'test-127-priority'
        }

        result = await step_127__golden_candidate(messages=[], ctx=ctx)

        assert 'faq_candidate' in result
        assert 'priority_score' in result['faq_candidate']
        # Priority = confidence (0.90) × trust (0.88) × frequency (45) × 100 = 3564
        assert float(result['faq_candidate']['priority_score']) > 3000

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_127_preserves_regulatory_references(self, mock_rag_log):
        """Test Step 127: Preserves regulatory references from expert."""
        from app.orchestrators.golden import step_127__golden_candidate

        ctx = {
            'expert_feedback': {
                'query_text': 'How to apply for maternity leave?',
                'expert_answer': 'Maternity leave application...',
                'regulatory_references': [
                    'D.Lgs. 151/2001',
                    'Circolare INPS 91/2022',
                    'Art. 16 Legge 53/2000'
                ],
                'confidence_score': 0.93
            },
            'trust_score': 0.90,
            'request_id': 'test-127-refs'
        }

        result = await step_127__golden_candidate(messages=[], ctx=ctx)

        assert 'faq_candidate' in result
        refs = result['faq_candidate']['regulatory_references']
        assert len(refs) == 3
        assert 'D.Lgs. 151/2001' in refs
        assert 'Art. 16 Legge 53/2000' in refs

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_127_preserves_context(self, mock_rag_log):
        """Test Step 127: Preserves all context data."""
        from app.orchestrators.golden import step_127__golden_candidate

        original_ctx = {
            'expert_feedback': {
                'query_text': 'Test question',
                'expert_answer': 'Test answer',
                'confidence_score': 0.85
            },
            'expert_id': 'expert_123',
            'trust_score': 0.90,
            'user_data': {'id': 'user_456'},
            'session_data': {'id': 'session_789'},
            'request_id': 'test-127-context'
        }

        result = await step_127__golden_candidate(messages=[], ctx=original_ctx.copy())

        # Verify all original context is preserved
        assert result['expert_id'] == original_ctx['expert_id']
        assert result['trust_score'] == original_ctx['trust_score']
        assert result['user_data'] == original_ctx['user_data']
        assert result['session_data'] == original_ctx['session_data']
        assert result['request_id'] == original_ctx['request_id']

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_127_adds_candidate_metadata(self, mock_rag_log):
        """Test Step 127: Adds candidate metadata for tracking."""
        from app.orchestrators.golden import step_127__golden_candidate

        ctx = {
            'expert_feedback': {
                'id': 'feedback_meta',
                'query_text': 'Question',
                'expert_answer': 'Answer',
                'confidence_score': 0.91
            },
            'expert_id': 'expert_meta',
            'trust_score': 0.85,
            'request_id': 'test-127-metadata'
        }

        result = await step_127__golden_candidate(messages=[], ctx=ctx)

        assert 'candidate_metadata' in result
        metadata = result['candidate_metadata']
        assert 'proposed_at' in metadata
        assert metadata['source'] == 'expert_feedback'
        assert metadata['expert_id'] == 'expert_meta'
        assert 'candidate_id' in metadata

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_127_handles_missing_category(self, mock_rag_log):
        """Test Step 127: Handles missing category gracefully."""
        from app.orchestrators.golden import step_127__golden_candidate

        ctx = {
            'expert_feedback': {
                'query_text': 'Question without category',
                'expert_answer': 'Answer',
                'confidence_score': 0.87
                # No category provided
            },
            'trust_score': 0.85,
            'request_id': 'test-127-no-category'
        }

        result = await step_127__golden_candidate(messages=[], ctx=ctx)

        assert result['faq_candidate']['category'] == 'generale'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_127_handles_error_gracefully(self, mock_rag_log):
        """Test Step 127: Handles errors gracefully."""
        from app.orchestrators.golden import step_127__golden_candidate

        ctx = {
            'expert_feedback': {
                'query_text': 'Question',
                'expert_answer': 'Answer',
                'confidence_score': 'invalid'  # This will cause an error
            },
            'trust_score': 0.85,
            'request_id': 'test-127-error'
        }

        result = await step_127__golden_candidate(messages=[], ctx=ctx)

        assert 'faq_candidate' in result
        assert 'error' in result['faq_candidate']
        assert result['next_step'] == 'golden_approval'  # Still routes for error handling

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_127_logs_proposal_details(self, mock_rag_log):
        """Test Step 127: Logs proposal details for observability."""
        from app.orchestrators.golden import step_127__golden_candidate

        ctx = {
            'expert_feedback': {
                'id': 'feedback_log',
                'query_text': 'Test question for logging',
                'expert_answer': 'Test answer',
                'confidence_score': 0.94,
                'category': 'test_category'
            },
            'expert_id': 'expert_log',
            'trust_score': 0.91,
            'request_id': 'test-127-logging'
        }

        await step_127__golden_candidate(messages=[], ctx=ctx)

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        final_call = None
        for call in mock_rag_log.call_args_list:
            if call[1].get('processing_stage') == 'completed':
                final_call = call[1]
                break

        assert final_call is not None
        assert final_call['step'] == 127
        assert 'candidate_id' in final_call
        assert 'expert_confidence' in final_call


class TestRAGStep127Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_127_parity_candidate_creation(self):
        """Test Step 127 parity: Candidate creation behavior unchanged."""
        from app.orchestrators.golden import step_127__golden_candidate

        test_cases = [
            {
                'expert_feedback': {
                    'query_text': 'Question 1',
                    'expert_answer': 'Answer 1',
                    'confidence_score': 0.90,
                    'category': 'cat1'
                },
                'expert_id': 'expert_1',
                'trust_score': 0.88
            },
            {
                'expert_feedback': {
                    'query_text': 'Question 2',
                    'expert_answer': 'Answer 2',
                    'confidence_score': 0.85,
                    'regulatory_references': ['Ref1', 'Ref2']
                },
                'expert_id': 'expert_2',
                'trust_score': 0.90
            }
        ]

        for test_case in test_cases:
            ctx = {
                **test_case,
                'request_id': f"parity-{test_case['expert_id']}"
            }

            with patch('app.orchestrators.golden.rag_step_log'):
                result = await step_127__golden_candidate(messages=[], ctx=ctx)

            assert 'faq_candidate' in result
            assert result['faq_candidate']['question'] == test_case['expert_feedback']['query_text']


class TestRAGStep127Integration:
    """Integration tests for Step 127 with neighbors."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_determine_action_to_127_integration(self, mock_golden_log):
        """Test DetermineAction (Step 126) → Step 127 integration."""

        initial_ctx = {
            'action': 'propose_golden_candidate',
            'expert_feedback': {
                'query_text': 'Integration test question',
                'expert_answer': 'Integration test answer',
                'confidence_score': 0.92
            },
            'expert_id': 'expert_integration',
            'trust_score': 0.90,
            'request_id': 'integration-126-127'
        }

        from app.orchestrators.golden import step_127__golden_candidate

        result = await step_127__golden_candidate(messages=[], ctx=initial_ctx)

        assert result['action'] == 'propose_golden_candidate'
        assert result['next_step'] == 'golden_approval'
        assert 'faq_candidate' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_127_prepares_for_golden_approval(self, mock_rag_log):
        """Test Step 127 prepares data for GoldenApproval (Step 128)."""
        from app.orchestrators.golden import step_127__golden_candidate

        ctx = {
            'expert_feedback': {
                'query_text': 'Approval prep question',
                'expert_answer': 'Approval prep answer',
                'confidence_score': 0.96  # High confidence
            },
            'trust_score': 0.94,  # High trust
            'request_id': 'test-127-approval-prep'
        }

        result = await step_127__golden_candidate(messages=[], ctx=ctx)

        # Verify data prepared for approval decision
        assert 'faq_candidate' in result
        assert result['faq_candidate']['quality_score'] >= 0.9  # Should indicate high quality
        assert result['trust_score'] == 0.94
        assert result['next_step'] == 'golden_approval'