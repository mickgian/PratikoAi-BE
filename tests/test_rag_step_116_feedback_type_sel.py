"""
Tests for RAG Step 116: FeedbackTypeSel (Feedback type selected).

This step is a process node that routes feedback to appropriate processing endpoints.
Routes to Step 117 (FAQ), Step 118 (KB), or Step 119 (Expert) based on feedback type.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestRAGStep116FeedbackTypeSel:
    """Unit tests for Step 116: FeedbackTypeSel routing logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_route_to_faq_feedback(self, mock_rag_log):
        """Test Step 116: Route to FAQ feedback (Step 117)."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        ctx = {
            'response_id': 'response-faq-route-123',
            'feedback_type': 'faq',
            'feedback_data': {
                'usage_log_id': 'usage_456',
                'was_helpful': True,
                'followup_needed': False,
                'comments': 'FAQ related feedback'
            },
            'request_id': 'test-116-faq-route',
            'user_id': 'user-faq-feedback'
        }

        result = await step_116__feedback_type_sel(messages=[], ctx=ctx)

        # Verify routing decision
        assert result['feedback_routing_decision'] == 'faq_feedback'
        assert result['next_step'] == 'faq_feedback_endpoint'  # Step 117
        assert result['routing_reason'] == 'feedback_type_faq'

        # Verify context preservation
        assert result['response_id'] == 'response-faq-route-123'
        assert result['feedback_type'] == 'faq'
        assert result['user_id'] == 'user-faq-feedback'

        # Verify logging
        assert mock_rag_log.call_count == 2
        end_call = mock_rag_log.call_args_list[1]
        assert end_call[1]['routing_decision'] == 'faq_feedback'

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_route_to_knowledge_feedback(self, mock_rag_log):
        """Test Step 116: Route to knowledge feedback (Step 118)."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        ctx = {
            'response_id': 'response-kb-route-456',
            'feedback_type': 'knowledge',
            'feedback_data': {
                'kb_doc_id': 'kb_doc_789',
                'rating': 3,
                'accuracy_score': 0.7,
                'improvement_suggestions': 'More examples needed'
            },
            'request_id': 'test-116-kb-route'
        }

        result = await step_116__feedback_type_sel(messages=[], ctx=ctx)

        # Verify routing decision
        assert result['feedback_routing_decision'] == 'knowledge_feedback'
        assert result['next_step'] == 'knowledge_feedback_endpoint'  # Step 118
        assert result['routing_reason'] == 'feedback_type_knowledge'

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_route_to_expert_feedback(self, mock_rag_log):
        """Test Step 116: Route to expert feedback collector (Step 119)."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        ctx = {
            'response_id': 'response-expert-route-789',
            'feedback_type': 'expert',
            'expert_feedback': {
                'feedback_type': 'incomplete',
                'confidence_rating': 0.8,
                'improvement_suggestions': 'Add regulatory references',
                'regulatory_references': ['Art. 123 TUIR']
            },
            'expert_user': True,
            'expert_trust_score': 0.95,
            'request_id': 'test-116-expert-route'
        }

        result = await step_116__feedback_type_sel(messages=[], ctx=ctx)

        # Verify routing decision
        assert result['feedback_routing_decision'] == 'expert_feedback'
        assert result['next_step'] == 'expert_feedback_collector'  # Step 119
        assert result['routing_reason'] == 'expert_user_priority'

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_auto_detect_feedback_type(self, mock_rag_log):
        """Test Step 116: Auto-detect feedback type from context."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        # Expert feedback detected automatically
        ctx_expert = {
            'response_id': 'response-auto-expert',
            'expert_user': True,
            'expert_feedback': {'feedback_type': 'correct'},
            'request_id': 'test-116-auto-expert'
        }

        result = await step_116__feedback_type_sel(messages=[], ctx=ctx_expert)

        assert result['feedback_routing_decision'] == 'expert_feedback'
        assert result['routing_reason'] == 'expert_user_priority'

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_preserves_context_data(self, mock_rag_log):
        """Test Step 116: Preserves all context data while adding routing."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        ctx = {
            'response_id': 'response-preserve-999',
            'query_text': 'Context preservation test',
            'feedback_type': 'faq',
            'request_id': 'test-116-preserve',
            'user_id': 'user-preserve',
            'session_id': 'session-preserve',

            # Pipeline metadata that should be preserved
            'provider': 'openai',
            'model': 'gpt-4',
            'tokens_used': 200,
            'response_time_ms': 1500,
            'upstream_data': {'preserved': 'data'},

            # From Step 114 (Decision)
            'feedback_provided': True,
            'decision_reason': 'user_feedback_present',
            'next_step': 'feedback_type_selected'
        }

        result = await step_116__feedback_type_sel(messages=[], ctx=ctx)

        # Verify routing output
        assert result['feedback_routing_decision'] == 'faq_feedback'
        assert result['next_step'] == 'faq_feedback_endpoint'

        # Verify all original context preserved
        assert result['query_text'] == 'Context preservation test'
        assert result['provider'] == 'openai'
        assert result['model'] == 'gpt-4'
        assert result['tokens_used'] == 200
        assert result['upstream_data'] == {'preserved': 'data'}
        assert result['feedback_provided'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_logs_routing_details(self, mock_rag_log):
        """Test Step 116: Logs comprehensive routing details."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        ctx = {
            'response_id': 'response-logging-test',
            'feedback_type': 'knowledge',
            'request_id': 'test-116-logging',
            'processing_start_time': datetime.now(timezone.utc)
        }

        result = await step_116__feedback_type_sel(messages=[], ctx=ctx)

        # Verify comprehensive logging
        assert mock_rag_log.call_count == 2

        # Check start log
        start_call = mock_rag_log.call_args_list[0]
        assert start_call[1]['step'] == 116
        assert start_call[1]['node_label'] == 'FeedbackTypeSel'
        assert start_call[1]['category'] == 'feedback'
        assert start_call[1]['type'] == 'process'

        # Check completion log
        end_call = mock_rag_log.call_args_list[1]
        assert end_call[1]['processing_stage'] == 'completed'
        assert end_call[1]['routing_decision'] == 'knowledge_feedback'
        assert end_call[1]['next_step'] == 'knowledge_feedback_endpoint'
        assert 'routing_time_ms' in end_call[1]

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_routing_priority_logic(self, mock_rag_log):
        """Test Step 116: Routing priority when multiple types present."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        # Expert feedback should take priority over regular feedback
        ctx = {
            'response_id': 'response-priority-test',
            'feedback_type': 'faq',  # Regular type specified
            'expert_user': True,      # But expert user present
            'expert_feedback': {'feedback_type': 'incomplete'},
            'request_id': 'test-116-priority'
        }

        result = await step_116__feedback_type_sel(messages=[], ctx=ctx)

        # Expert should take priority
        assert result['feedback_routing_decision'] == 'expert_feedback'
        assert result['routing_reason'] == 'expert_user_priority'

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_default_routing_fallback(self, mock_rag_log):
        """Test Step 116: Default routing when type unclear."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        ctx = {
            'response_id': 'response-default-routing',
            'user_feedback': {'feedback_type': 'correct'},  # Generic feedback
            'request_id': 'test-116-default'
        }

        result = await step_116__feedback_type_sel(messages=[], ctx=ctx)

        # Should default to expert feedback collector for processing
        assert result['feedback_routing_decision'] == 'expert_feedback'
        assert result['routing_reason'] == 'default_routing'

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_contextual_routing_detection(self, mock_rag_log):
        """Test Step 116: Contextual detection of feedback routing."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        # Test FAQ context detection
        ctx_faq = {
            'response_id': 'response-faq-context',
            'golden_response': True,  # Indicates FAQ/Golden set feedback
            'golden_match_id': 'golden_123',
            'request_id': 'test-116-faq-context'
        }

        result = await step_116__feedback_type_sel(messages=[], ctx=ctx_faq)

        assert result['feedback_routing_decision'] == 'faq_feedback'
        assert result['routing_reason'] == 'golden_response_detected'

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_error_handling_invalid_type(self, mock_rag_log):
        """Test Step 116: Handle invalid feedback type gracefully."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        ctx = {
            'response_id': 'response-invalid-type',
            'feedback_type': 'invalid_type',
            'request_id': 'test-116-invalid'
        }

        result = await step_116__feedback_type_sel(messages=[], ctx=ctx)

        # Should fallback to default routing
        assert result['feedback_routing_decision'] == 'expert_feedback'
        assert result['routing_reason'] == 'invalid_type_fallback'

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_routing_performance_tracking(self, mock_rag_log):
        """Test Step 116: Performance tracking for routing logic."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        ctx = {
            'response_id': 'performance-test-routing',
            'feedback_type': 'faq',
            'request_id': 'test-116-performance'
        }

        result = await step_116__feedback_type_sel(messages=[], ctx=ctx)

        # Verify routing was processed efficiently
        assert result['feedback_routing_decision'] == 'faq_feedback'

        # Check that timing information is logged
        end_call = mock_rag_log.call_args_list[1]
        assert 'routing_time_ms' in end_call[1]
        assert end_call[1]['routing_time_ms'] >= 0


class TestRAGStep116Parity:
    """Parity tests ensuring Step 116 behavior is consistent."""

    @pytest.mark.asyncio
    async def test_step_116_parity_routing_structure(self):
        """Test Step 116 parity: routing output structure is consistent."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        # Expected routing structure
        expected_keys = ['feedback_routing_decision', 'next_step', 'routing_reason']

        # Test FAQ routing
        ctx_faq = {
            'feedback_type': 'faq',
            'response_id': 'parity-test-faq'
        }

        with patch('app.orchestrators.feedback.rag_step_log'):
            result_faq = await step_116__feedback_type_sel(messages=[], ctx=ctx_faq)

        # Test Expert routing
        ctx_expert = {
            'expert_user': True,
            'expert_feedback': {'feedback_type': 'correct'},
            'response_id': 'parity-test-expert'
        }

        with patch('app.orchestrators.feedback.rag_step_log'):
            result_expert = await step_116__feedback_type_sel(messages=[], ctx=ctx_expert)

        # Verify consistent structure
        for key in expected_keys:
            assert key in result_faq
            assert key in result_expert

        # Verify routing logic consistency
        assert result_faq['feedback_routing_decision'] == 'faq_feedback'
        assert result_expert['feedback_routing_decision'] == 'expert_feedback'


class TestRAGStep116Integration:
    """Integration tests for Step 116 with neighboring steps."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_114_to_116_integration(self, mock_rag_log):
        """Test integration: Step 114 (Yes feedback) → Step 116 (Feedback type selected)."""
        from app.orchestrators.feedback import step_114__feedback_provided, step_116__feedback_type_sel

        # Step 114 context (feedback provided)
        step_114_ctx = {
            'response_id': 'integration-response-114-116',
            'user_feedback': {'feedback_type': 'incomplete'},
            'request_id': 'test-114-116-integration',
            'user_id': 'integration-user-4'
        }

        step_114_result = await step_114__feedback_provided(messages=[], ctx=step_114_ctx)

        # Step 116 receives Step 114 output
        step_116_ctx = step_114_result.copy()
        step_116_ctx['feedback_type'] = 'knowledge'  # Add routing type

        step_116_result = await step_116__feedback_type_sel(messages=[], ctx=step_116_ctx)

        # Verify integration flow
        assert step_116_result['feedback_provided'] is True  # From step 114
        assert step_116_result['feedback_type'] == 'knowledge'  # Added for routing
        assert step_116_result['feedback_routing_decision'] == 'knowledge_feedback'  # From step 116
        assert step_116_result['next_step'] == 'knowledge_feedback_endpoint'  # From step 116
        assert step_116_result['response_id'] == 'integration-response-114-116'

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_to_117_integration(self, mock_rag_log):
        """Test integration: Step 116 (FAQ route) → Step 117 (FAQ feedback)."""
        from app.orchestrators.feedback import step_116__feedback_type_sel
        from app.orchestrators.golden import step_117__faqfeedback

        # Step 116 context (FAQ routing)
        step_116_ctx = {
            'response_id': 'integration-response-116-117',
            'feedback_type': 'faq',
            'feedback_data': {
                'usage_log_id': 'usage_123',
                'was_helpful': True,
                'comments': 'FAQ integration test'
            },
            'request_id': 'test-116-117-integration'
        }

        step_116_result = await step_116__feedback_type_sel(messages=[], ctx=step_116_ctx)

        # Step 117 receives Step 116 output
        step_117_ctx = step_116_result.copy()

        with patch('app.services.intelligent_faq_service.IntelligentFAQService'):
            step_117_result = await step_117__faqfeedback(messages=[], ctx=step_117_ctx)

        # Verify integration flow
        assert step_117_result['feedback_routing_decision'] == 'faq_feedback'  # From step 116
        assert step_117_result['next_step'] == 'expert_feedback_collector'  # From step 117 (routes to Step 119 per Mermaid)
        assert step_117_result['response_id'] == 'integration-response-116-117'

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_to_119_integration(self, mock_rag_log):
        """Test integration: Step 116 (Expert route) → Step 119 (Expert feedback)."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        # Step 116 context (Expert routing)
        step_116_ctx = {
            'response_id': 'integration-response-116-119',
            'expert_user': True,
            'expert_feedback': {
                'feedback_type': 'incorrect',
                'confidence_rating': 0.9
            },
            'expert_trust_score': 0.85,
            'request_id': 'test-116-119-integration'
        }

        step_116_result = await step_116__feedback_type_sel(messages=[], ctx=step_116_ctx)

        # Verify routing to Step 119
        assert step_116_result['feedback_routing_decision'] == 'expert_feedback'
        assert step_116_result['next_step'] == 'expert_feedback_collector'
        assert step_116_result['expert_user'] is True
        assert step_116_result['expert_trust_score'] == 0.85

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_full_feedback_routing_pipeline(self, mock_rag_log):
        """Test Step 116 in full feedback routing pipeline."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        # Simulate full pipeline context from decision
        pipeline_ctx = {
            'response_id': 'pipeline-routing-123',
            'query_text': 'Full pipeline routing test',
            'user_id': 'pipeline-user',
            'session_id': 'pipeline-session',
            'request_id': 'test-116-full-pipeline',
            'processing_start_time': datetime.now(timezone.utc),

            # From Step 114 (Decision - feedback provided)
            'feedback_provided': True,
            'decision_reason': 'user_feedback_present',
            'next_step': 'feedback_type_selected',

            # Routing context
            'feedback_type': 'knowledge',
            'kb_context': True
        }

        result = await step_116__feedback_type_sel(messages=[], ctx=pipeline_ctx)

        # Verify pipeline routing
        assert result['feedback_routing_decision'] == 'knowledge_feedback'
        assert result['next_step'] == 'knowledge_feedback_endpoint'
        assert result['query_text'] == 'Full pipeline routing test'
        assert result['feedback_provided'] is True
        assert result['processing_start_time'] == pipeline_ctx['processing_start_time']

    @pytest.mark.asyncio
    @patch('app.orchestrators.feedback.rag_step_log')
    async def test_step_116_multiple_routing_scenarios(self, mock_rag_log):
        """Test Step 116: Handle multiple routing scenarios in sequence."""
        from app.orchestrators.feedback import step_116__feedback_type_sel

        # Test various routing scenarios
        scenarios = [
            {
                'name': 'faq_explicit',
                'ctx': {'feedback_type': 'faq'},
                'expected_decision': 'faq_feedback'
            },
            {
                'name': 'knowledge_explicit',
                'ctx': {'feedback_type': 'knowledge'},
                'expected_decision': 'knowledge_feedback'
            },
            {
                'name': 'expert_priority',
                'ctx': {'feedback_type': 'faq', 'expert_user': True, 'expert_feedback': {'feedback_type': 'correct'}},
                'expected_decision': 'expert_feedback'
            },
            {
                'name': 'golden_context',
                'ctx': {'golden_response': True, 'golden_match_id': 'golden_456'},
                'expected_decision': 'faq_feedback'
            }
        ]

        for scenario in scenarios:
            ctx = {
                'response_id': f'scenario-{scenario["name"]}',
                'request_id': f'test-116-{scenario["name"]}',
                **scenario['ctx']
            }

            result = await step_116__feedback_type_sel(messages=[], ctx=ctx)

            # Verify each scenario routes correctly
            assert result['feedback_routing_decision'] == scenario['expected_decision']