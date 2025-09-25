"""
Tests for RAG Step 135: GoldenRules (GoldenSetUpdater.auto_rule_eval new or obsolete candidates).

This step automatically evaluates knowledge base content to identify new FAQ candidates
or obsolete ones that need updates.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone


class TestRAGStep135GoldenRules:
    """Unit tests for Step 135: GoldenRules."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_135_evaluates_knowledge_content(self, mock_rag_log):
        """Test Step 135: Evaluates knowledge base content for FAQ candidates."""
        from app.orchestrators.golden import step_135__golden_rules

        ctx = {
            'knowledge_updates': [
                {
                    'id': 'kb_001',
                    'title': 'New INPS Regulation on Contributions',
                    'content': 'Recent changes to INPS contribution calculations that affect all workers in Italy. This is a comprehensive guide to understanding the new requirements and how they impact your monthly contributions.',
                    'category': 'contributions',
                    'source_url': 'https://inps.it/reg_001',
                    'published_date': '2025-09-20'
                },
                {
                    'id': 'kb_002',
                    'title': 'Updated COVID Benefits Guide',
                    'content': 'Changes to COVID-related benefits effective 2024 including eligibility criteria and application process. This comprehensive guide covers all the new requirements.',
                    'category': 'benefits',
                    'source_url': 'https://inps.it/covid_2024',
                    'published_date': '2025-09-15'
                }
            ],
            'evaluation_rules': {
                'min_content_length': 100,
                'priority_categories': ['contributions', 'benefits'],
                'recency_threshold_days': 30
            },
            'request_id': 'test-135-eval'
        }

        result = await step_135__golden_rules(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert 'candidate_evaluation' in result
        assert result['candidate_evaluation']['candidates_generated'] == 2
        assert result['next_step'] == 'golden_candidate'
        assert len(result['candidate_evaluation']['new_candidates']) == 2
        assert result['candidate_evaluation']['success'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_135_identifies_obsolete_candidates(self, mock_rag_log):
        """Test Step 135: Identifies obsolete FAQ candidates needing updates."""
        from app.orchestrators.golden import step_135__golden_rules

        ctx = {
            'knowledge_updates': [
                {
                    'id': 'kb_updated',
                    'title': 'Updated Tax Credit Rules',
                    'content': 'New tax credit calculations supersede previous rules with comprehensive changes to eligibility and calculation methods for all taxpayers.',
                    'supersedes_content_id': 'kb_old_tax',
                    'category': 'tax',
                    'published_date': '2025-09-18'
                }
            ],
            'evaluation_rules': {
                'min_content_length': 100,
                'priority_categories': ['tax'],
                'min_priority_score': 0.5
            },
            'request_id': 'test-135-obsolete'
        }

        result = await step_135__golden_rules(messages=[], ctx=ctx)

        assert result['candidate_evaluation']['obsolete_identified'] == 1
        assert 'obsolete_candidates' in result['candidate_evaluation']
        assert result['candidate_evaluation']['candidates_generated'] == 1

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_135_applies_priority_rules(self, mock_rag_log):
        """Test Step 135: Applies priority rules for candidate evaluation."""
        from app.orchestrators.golden import step_135__golden_rules

        ctx = {
            'knowledge_updates': [
                {
                    'id': 'kb_high_priority',
                    'title': 'High Priority Content',
                    'category': 'contributions',
                    'content': 'Critical INPS update with urgent regulatory changes affecting all Italian workers. This comprehensive guide covers all requirements.',
                    'priority_indicators': ['urgent', 'regulation_change'],
                    'published_date': '2025-09-20'
                },
                {
                    'id': 'kb_low_priority',
                    'title': 'Low Priority Content',
                    'category': 'general',
                    'content': 'Short general update.',  # Below min_content_length
                    'priority_indicators': [],
                    'published_date': '2025-09-20'
                }
            ],
            'evaluation_rules': {
                'priority_categories': ['contributions', 'benefits'],
                'priority_keywords': ['urgent', 'regulation_change'],
                'min_priority_score': 0.7,
                'min_content_length': 100
            },
            'request_id': 'test-135-priority'
        }

        result = await step_135__golden_rules(messages=[], ctx=ctx)

        assert result['candidate_evaluation']['candidates_generated'] == 1
        assert result['candidate_evaluation']['filtered_out'] == 1

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_135_handles_no_knowledge_updates(self, mock_rag_log):
        """Test Step 135: Handles empty knowledge updates gracefully."""
        from app.orchestrators.golden import step_135__golden_rules

        ctx = {
            'knowledge_updates': [],
            'request_id': 'test-135-empty'
        }

        result = await step_135__golden_rules(messages=[], ctx=ctx)

        assert result['candidate_evaluation']['candidates_generated'] == 0
        assert result['candidate_evaluation']['success'] is True
        assert result['next_step'] == 'golden_candidate'

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_135_preserves_context(self, mock_rag_log):
        """Test Step 135: Preserves all context data."""
        from app.orchestrators.golden import step_135__golden_rules

        original_ctx = {
            'knowledge_updates': [
                {
                    'id': 'kb_context_test',
                    'title': 'Context Test',
                    'content': 'Test content for context preservation with sufficient length to pass evaluation criteria and generate candidates.',
                    'category': 'test',
                    'published_date': '2025-09-18'
                }
            ],
            'evaluation_metadata': {
                'evaluation_id': 'eval_123',
                'batch_size': 10
            },
            'user_data': {'id': 'user_456'},
            'session_data': {'id': 'session_789'},
            'request_id': 'test-135-context'
        }

        result = await step_135__golden_rules(messages=[], ctx=original_ctx.copy())

        # Verify all original context is preserved
        assert result['evaluation_metadata'] == original_ctx['evaluation_metadata']
        assert result['user_data'] == original_ctx['user_data']
        assert result['session_data'] == original_ctx['session_data']
        assert result['request_id'] == original_ctx['request_id']

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_135_logs_evaluation_details(self, mock_rag_log):
        """Test Step 135: Logs evaluation details for observability."""
        from app.orchestrators.golden import step_135__golden_rules

        ctx = {
            'knowledge_updates': [
                {
                    'id': 'kb_log',
                    'title': 'Logging Test',
                    'content': 'Logging test content with sufficient length to pass evaluation criteria and generate a candidate for testing purposes.',
                    'category': 'test_category',
                    'published_date': '2025-09-18'
                }
            ],
            'request_id': 'test-135-logging'
        }

        await step_135__golden_rules(messages=[], ctx=ctx)

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        final_call = None
        for call in mock_rag_log.call_args_list:
            if call[1].get('processing_stage') == 'completed':
                final_call = call[1]
                break

        assert final_call is not None
        assert final_call['step'] == 135
        assert 'candidates_generated' in final_call


class TestRAGStep135Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_135_parity_evaluation_behavior(self):
        """Test Step 135 parity: Evaluation behavior unchanged."""
        from app.orchestrators.golden import step_135__golden_rules

        test_cases = [
            {
                'knowledge_updates': [
                    {
                        'id': 'kb_1',
                        'title': 'Test 1',
                        'content': 'Test content 1 with sufficient length to pass evaluation criteria and generate candidates for testing purposes.',
                        'category': 'test',
                        'published_date': '2025-09-18'
                    }
                ],
                'expected_candidates': 1
            },
            {
                'knowledge_updates': [
                    {
                        'id': 'kb_2',
                        'title': 'Test 2',
                        'content': 'Test content 2 with sufficient length to pass evaluation criteria and generate candidates.',
                        'category': 'test',
                        'published_date': '2025-09-18'
                    },
                    {
                        'id': 'kb_3',
                        'title': 'Test 3',
                        'content': 'Test content 3 with sufficient length to pass evaluation criteria and generate candidates.',
                        'category': 'test',
                        'published_date': '2025-09-18'
                    }
                ],
                'expected_candidates': 2
            }
        ]

        for test_case in test_cases:
            ctx = {
                **test_case,
                'evaluation_rules': {
                    'priority_categories': ['test'],  # Include test category
                    'min_priority_score': 0.5,
                    'min_content_length': 50  # Lower threshold for test content
                },
                'request_id': f"parity-{len(test_case['knowledge_updates'])}"
            }

            with patch('app.orchestrators.golden.rag_step_log'):
                result = await step_135__golden_rules(messages=[], ctx=ctx)

            assert 'candidate_evaluation' in result
            assert result['candidate_evaluation']['candidates_generated'] == test_case['expected_candidates']


class TestRAGStep135Integration:
    """Integration tests for Step 135 with neighbors."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_knowledge_store_to_135_integration(self, mock_knowledge_log):
        """Test KnowledgeStore → Step 135 integration."""

        initial_ctx = {
            'knowledge_updates': [
                {
                    'id': 'kb_integration',
                    'title': 'Integration Test Document',
                    'content': 'Test content from knowledge store with comprehensive information about regulatory changes that affect workers.',
                    'category': 'integration_test',
                    'published_date': datetime.now(timezone.utc).isoformat()
                }
            ],
            'knowledge_metadata': {
                'source': 'rss_monitor',
                'batch_id': 'batch_001'
            },
            'request_id': 'integration-kb-135'
        }

        from app.orchestrators.golden import step_135__golden_rules

        result = await step_135__golden_rules(messages=[], ctx=initial_ctx)

        assert 'knowledge_metadata' in result
        assert result['next_step'] == 'golden_candidate'
        assert 'candidate_evaluation' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.golden.rag_step_log')
    async def test_step_135_prepares_for_golden_candidate(self, mock_rag_log):
        """Test Step 135 prepares data for GoldenCandidate (Step 127)."""
        from app.orchestrators.golden import step_135__golden_rules

        ctx = {
            'knowledge_updates': [
                {
                    'id': 'kb_prep',
                    'title': 'Preparation Test',
                    'content': 'Content for candidate preparation with comprehensive information about regulatory processes and requirements for workers.',
                    'category': 'preparation',
                    'published_date': '2025-09-18'
                }
            ],
            'request_id': 'test-135-prep'
        }

        result = await step_135__golden_rules(messages=[], ctx=ctx)

        # Verify data prepared for GoldenCandidate step
        assert result['next_step'] == 'golden_candidate'
        assert 'candidate_evaluation' in result
        assert len(result['candidate_evaluation']['new_candidates']) > 0

        candidate = result['candidate_evaluation']['new_candidates'][0]
        assert 'proposed_question' in candidate
        assert 'confidence' in candidate
        assert 'priority_score' in candidate