"""
Tests for RAG Step 123 — Create ExpertFeedback record (RAG.feedback.create.expertfeedback.record)

Test coverage:
- Unit tests: Feedback record creation, validation, error handling
- Integration tests: Step 121→123, 123→124, full pipeline flows
- Parity tests: Behavioral definition of done validation
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4, UUID

from app.orchestrators.feedback import step_123__create_feedback_rec
from app.services.expert_feedback_collector import ExpertFeedbackCollector, FeedbackValidationError
from app.models.quality_analysis import ExpertFeedback, ExpertProfile, FeedbackType, ItalianFeedbackCategory


class TestStep123CreateFeedbackRec:
    """Unit tests for Step 123 create feedback record orchestrator"""

    @pytest.fixture
    def valid_context_from_step_121(self):
        """Context data received from Step 121 (TrustScoreOK) with trust score >= 0.7"""
        return {
            'rag_step': 121,
            'step_id': 'RAG.classify.trust.score.at.least.0.7',
            'node_label': 'TrustScoreOK',
            'query_id': str(uuid4()),
            'expert_id': str(uuid4()),
            'expert_profile': {
                'id': str(uuid4()),
                'trust_score': 0.85,
                'credentials': ['CPA', 'Tax Professional'],
                'experience_years': 10
            },
            'feedback_data': {
                'feedback_type': 'incorrect',
                'category': 'interpretazione_errata',
                'query_text': 'How to handle Italian VAT for services?',
                'original_answer': 'VAT is 22% for all services',
                'expert_answer': 'VAT varies by service type: 10% for tourism, 22% for consultancy',
                'improvement_suggestions': ['Add service-specific VAT rates', 'Include regulatory references'],
                'confidence_score': 0.9,
                'time_spent_seconds': 120
            },
            'trust_validation_result': {
                'trust_score': 0.85,
                'meets_threshold': True,
                'threshold_used': 0.7
            },
            'processing_metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'step_121_duration_ms': 45,
                'decision_outcome': 'trust_score_acceptable'
            }
        }

    @pytest.fixture
    def mock_expert_profile(self):
        """Mock expert profile for testing"""
        return ExpertProfile(
            id=uuid4(),
            name="Marco Rossi",
            email="marco.rossi@example.it",
            credentials=["CPA", "Tax Professional"],
            trust_score=0.85,
            experience_years=10,
            feedback_count=25,
            average_response_time_seconds=90,
            specializations=["Italian Tax Law", "VAT Regulations"]
        )

    @pytest.fixture
    def mock_feedback_record(self):
        """Mock feedback record for testing"""
        return ExpertFeedback(
            id=uuid4(),
            query_id=uuid4(),
            expert_id=uuid4(),
            feedback_type=FeedbackType.INCORRECT,
            category=ItalianFeedbackCategory.INTERPRETAZIONE_ERRATA,
            query_text="How to handle Italian VAT for services?",
            original_answer="VAT is 22% for all services",
            expert_answer="VAT varies by service type: 10% for tourism, 22% for consultancy",
            improvement_suggestions=["Add service-specific VAT rates", "Include regulatory references"],
            confidence_score=0.9,
            time_spent_seconds=120,
            feedback_timestamp=datetime.utcnow()
        )

    @pytest.mark.asyncio
    async def test_create_feedback_record_success(self, valid_context_from_step_121, mock_expert_profile, mock_feedback_record):
        """Test successful feedback record creation with valid context from Step 121"""

        with patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:
            # Setup mocks
            mock_collector = mock_collector_class.return_value
            mock_collector.collect_feedback = AsyncMock(return_value={
                'success': True,
                'feedback_id': str(mock_feedback_record.id),
                'feedback_type': 'incorrect',
                'category': 'interpretazione_errata',
                'processing_time_ms': 85,
                'expert_trust_score': 0.85,
                'action_taken': 'record_created'
            })

            # Execute step
            result = await step_123__create_feedback_rec(ctx=valid_context_from_step_121)

            # Verify orchestrator behavior
            assert result['success'] is True
            assert result['feedback_record_created'] is True
            assert result['feedback_id'] == str(mock_feedback_record.id)
            assert result['expert_trust_score'] == 0.85

            # Verify context preservation
            assert result['query_id'] == valid_context_from_step_121['query_id']
            assert result['expert_id'] == valid_context_from_step_121['expert_id']

            # Verify routing metadata for Step 124
            assert result['next_step'] == 124
            assert result['next_step_id'] == 'RAG.metrics.update.expert.metrics'
            assert result['route_to'] == 'UpdateExpertMetrics'

            # Verify service integration
            mock_collector.collect_feedback.assert_called_once()
            feedback_call = mock_collector.collect_feedback.call_args[1]
            assert feedback_call['query_id'] == valid_context_from_step_121['query_id']
            assert feedback_call['expert_id'] == valid_context_from_step_121['expert_id']
            assert feedback_call['feedback_type'] == 'incorrect'

    @pytest.mark.asyncio
    async def test_create_feedback_record_validation_error(self, valid_context_from_step_121):
        """Test handling of feedback validation errors"""

        # Create invalid context (missing required feedback data)
        invalid_context = valid_context_from_step_121.copy()
        del invalid_context['feedback_data']['feedback_type']

        with patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:
            mock_collector = mock_collector_class.return_value
            mock_collector.collect_feedback = AsyncMock(side_effect=FeedbackValidationError("Missing feedback_type"))

            # Execute step
            result = await step_123__create_feedback_rec(ctx=invalid_context)

            # Verify error handling
            assert result['success'] is False
            assert result['error_type'] == 'validation_error'
            assert 'Missing feedback_type' in result['error_message']

            # Verify context preservation
            assert result['query_id'] == invalid_context['query_id']
            assert result['expert_id'] == invalid_context['expert_id']

            # Verify graceful error handling (no crash)
            assert 'processing_metadata' in result
            assert result['step'] == 123

    @pytest.mark.asyncio
    async def test_create_feedback_record_missing_context_data(self):
        """Test handling of missing or incomplete context data from Step 121"""

        incomplete_context = {
            'rag_step': 121,
            'query_id': str(uuid4()),
            # Missing expert_id, feedback_data, etc.
        }

        # Execute step
        result = await step_123__create_feedback_rec(ctx=incomplete_context)

        # Verify error handling
        assert result['success'] is False
        assert result['error_type'] == 'missing_context_data'
        assert 'expert_id' in result['error_message'] or 'feedback_data' in result['error_message']

        # Verify graceful fallback
        assert result['step'] == 123
        assert result['step_id'] == 'RAG.feedback.create.expertfeedback.record'

    @pytest.mark.asyncio
    async def test_create_feedback_record_service_error(self, valid_context_from_step_121):
        """Test handling of service-level errors during feedback collection"""

        with patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:
            mock_collector = mock_collector_class.return_value
            mock_collector.collect_feedback = AsyncMock(side_effect=Exception("Database connection failed"))

            # Execute step
            result = await step_123__create_feedback_rec(ctx=valid_context_from_step_121)

            # Verify error handling
            assert result['success'] is False
            assert result['error_type'] == 'service_error'
            assert 'Database connection failed' in result['error_message']

            # Verify context preservation
            assert result['query_id'] == valid_context_from_step_121['query_id']
            assert result['expert_id'] == valid_context_from_step_121['expert_id']

    @pytest.mark.asyncio
    async def test_create_feedback_record_italian_category_handling(self, valid_context_from_step_121):
        """Test proper handling of Italian feedback categories for tax professionals"""

        # Test all Italian categories
        italian_categories = [
            'normativa_obsoleta',
            'interpretazione_errata',
            'caso_mancante',
            'calcolo_sbagliato',
            'troppo_generico'
        ]

        for category in italian_categories:
            context = valid_context_from_step_121.copy()
            context['feedback_data']['category'] = category

            with patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:
                mock_collector = mock_collector_class.return_value
                mock_collector.collect_feedback = AsyncMock(return_value={
                    'success': True,
                    'feedback_id': str(uuid4()),
                    'feedback_type': 'incorrect',
                    'category': category,
                    'processing_time_ms': 75,
                    'expert_trust_score': 0.85,
                    'action_taken': 'record_created'
                })

                # Execute step
                result = await step_123__create_feedback_rec(ctx=context)

                # Verify category handling
                assert result['success'] is True
                assert result['italian_category'] == category

                # Verify service call includes category
                feedback_call = mock_collector.collect_feedback.call_args[1]
                assert feedback_call['category'] == category

    @pytest.mark.asyncio
    async def test_create_feedback_record_performance_tracking(self, valid_context_from_step_121, mock_feedback_record):
        """Test performance tracking and timing requirements"""

        with patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:
            mock_collector = mock_collector_class.return_value
            mock_collector.collect_feedback = AsyncMock(return_value={
                'success': True,
                'feedback_id': str(mock_feedback_record.id),
                'feedback_type': 'incorrect',
                'processing_time_ms': 1250,  # Simulated processing time
                'expert_trust_score': 0.85,
                'action_taken': 'record_created'
            })

            # Execute step
            start_time = datetime.utcnow()
            result = await step_123__create_feedback_rec(ctx=valid_context_from_step_121)
            end_time = datetime.utcnow()

            # Verify performance tracking
            assert 'processing_metadata' in result
            assert 'step_123_duration_ms' in result['processing_metadata']
            assert 'feedback_collection_time_ms' in result['processing_metadata']

            # Verify timing is reasonable (should be fast)
            total_time = (end_time - start_time).total_seconds() * 1000
            assert total_time < 5000  # Should complete in under 5 seconds

            # Verify service processing time is included
            assert result['processing_metadata']['feedback_collection_time_ms'] == 1250


class TestStep123IntegrationFlows:
    """Integration tests for Step 123 with neighboring RAG steps"""

    @pytest.fixture
    def step_121_output_trust_accepted(self):
        """Output from Step 121 when trust score >= 0.7 (routes to Step 123)"""
        return {
            'rag_step': 121,
            'step_id': 'RAG.classify.trust.score.at.least.0.7',
            'node_label': 'TrustScoreOK',
            'decision_outcome': 'trust_score_acceptable',
            'query_id': str(uuid4()),
            'expert_id': str(uuid4()),
            'expert_profile': {
                'id': str(uuid4()),
                'name': 'Dr. Giuseppe Bianchi',
                'trust_score': 0.92,
                'credentials': ['CPA', 'PhD in Tax Law'],
                'experience_years': 15
            },
            'feedback_data': {
                'feedback_type': 'incomplete',
                'category': 'caso_mancante',
                'query_text': 'What are the tax implications for Italian freelancers?',
                'original_answer': 'Freelancers pay 22% tax rate',
                'expert_answer': 'Tax rate varies by income bracket: 23% up to €15k, 27% up to €28k, etc.',
                'improvement_suggestions': ['Include income brackets', 'Add deduction information'],
                'confidence_score': 0.95,
                'time_spent_seconds': 180
            },
            'trust_validation_result': {
                'trust_score': 0.92,
                'meets_threshold': True,
                'threshold_used': 0.7,
                'validation_timestamp': datetime.utcnow().isoformat()
            },
            'processing_metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'step_121_duration_ms': 38,
                'routing_decision': 'route_to_create_feedback_rec'
            }
        }

    @pytest.mark.asyncio
    async def test_step_121_to_123_integration(self, step_121_output_trust_accepted):
        """Test integration flow from Step 121 (TrustScoreOK) to Step 123"""

        with patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:
            mock_collector = mock_collector_class.return_value
            mock_collector.collect_feedback = AsyncMock(return_value={
                'success': True,
                'feedback_id': str(uuid4()),
                'feedback_type': 'incomplete',
                'category': 'caso_mancante',
                'processing_time_ms': 95,
                'expert_trust_score': 0.92,
                'action_taken': 'record_created'
            })

            # Execute Step 123 with Step 121 output
            result = await step_123__create_feedback_rec(ctx=step_121_output_trust_accepted)

            # Verify integration preserves Step 121 data
            assert result['query_id'] == step_121_output_trust_accepted['query_id']
            assert result['expert_id'] == step_121_output_trust_accepted['expert_id']
            assert result['expert_trust_score'] == 0.92

            # Verify Step 121 context is preserved
            assert result['previous_step'] == 121
            assert result['previous_step_decision'] == 'trust_score_acceptable'

            # Verify feedback creation uses Step 121 data
            feedback_call = mock_collector.collect_feedback.call_args[1]
            assert feedback_call['feedback_type'] == 'incomplete'
            assert feedback_call['category'] == 'caso_mancante'
            assert feedback_call['confidence_score'] == 0.95

    @pytest.mark.asyncio
    async def test_step_123_to_124_routing_setup(self, step_121_output_trust_accepted):
        """Test Step 123 prepares routing to Step 124 (UpdateExpertMetrics)"""

        with patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:
            mock_collector = mock_collector_class.return_value
            mock_collector.collect_feedback = AsyncMock(return_value={
                'success': True,
                'feedback_id': str(uuid4()),
                'feedback_type': 'incomplete',
                'processing_time_ms': 110,
                'expert_trust_score': 0.92,
                'action_taken': 'record_created'
            })

            # Execute Step 123
            result = await step_123__create_feedback_rec(ctx=step_121_output_trust_accepted)

            # Verify routing setup for Step 124
            assert result['next_step'] == 124
            assert result['next_step_id'] == 'RAG.metrics.update.expert.metrics'
            assert result['route_to'] == 'UpdateExpertMetrics'

            # Verify data prepared for Step 124
            assert 'expert_metrics_update' in result
            assert result['expert_metrics_update']['expert_id'] == step_121_output_trust_accepted['expert_id']
            assert result['expert_metrics_update']['feedback_created'] is True
            assert 'feedback_metadata' in result['expert_metrics_update']

    @pytest.mark.asyncio
    async def test_full_pipeline_121_123_124_preparation(self, step_121_output_trust_accepted):
        """Test full pipeline flow preparation: Step 121 → 123 → 124"""

        with patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:
            mock_collector = mock_collector_class.return_value
            mock_collector.collect_feedback = AsyncMock(return_value={
                'success': True,
                'feedback_id': str(uuid4()),
                'feedback_type': 'incomplete',
                'category': 'caso_mancante',
                'processing_time_ms': 125,
                'expert_trust_score': 0.92,
                'action_taken': 'record_created',
                'expert_answer': 'Enhanced answer with income brackets'
            })

            # Execute Step 123
            result = await step_123__create_feedback_rec(ctx=step_121_output_trust_accepted)

            # Verify complete pipeline context preservation
            assert result['pipeline_context']['step_121_trust_validation'] == step_121_output_trust_accepted['trust_validation_result']
            assert result['pipeline_context']['step_123_feedback_creation']['success'] is True

            # Verify data flow continuity
            assert result['expert_id'] == step_121_output_trust_accepted['expert_id']
            assert result['query_id'] == step_121_output_trust_accepted['query_id']

            # Verify Step 124 preparation includes all necessary data
            assert 'feedback_record_id' in result['expert_metrics_update']
            assert 'processing_time_ms' in result['expert_metrics_update']
            assert 'trust_score_at_creation' in result['expert_metrics_update']

    @pytest.mark.asyncio
    async def test_multiple_feedback_types_integration(self):
        """Test integration with different feedback types from Step 121"""

        feedback_types = ['correct', 'incomplete', 'incorrect']

        for feedback_type in feedback_types:
            # Create context for each feedback type
            context = {
                'rag_step': 121,
                'query_id': str(uuid4()),
                'expert_id': str(uuid4()),
                'expert_profile': {'id': str(uuid4()), 'trust_score': 0.85},
                'feedback_data': {
                    'feedback_type': feedback_type,
                    'category': 'interpretazione_errata',
                    'query_text': f'Test query for {feedback_type}',
                    'confidence_score': 0.8,
                    'time_spent_seconds': 90
                },
                'trust_validation_result': {'trust_score': 0.85, 'meets_threshold': True}
            }

            with patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:
                mock_collector = mock_collector_class.return_value
                mock_collector.collect_feedback = AsyncMock(return_value={
                    'success': True,
                    'feedback_id': str(uuid4()),
                    'feedback_type': feedback_type,
                    'processing_time_ms': 100,
                    'expert_trust_score': 0.85,
                    'action_taken': 'record_created'
                })

                # Execute Step 123
                result = await step_123__create_feedback_rec(ctx=context)

                # Verify feedback type handling
                assert result['success'] is True
                assert result['feedback_type'] == feedback_type

                # Verify service called with correct type
                feedback_call = mock_collector.collect_feedback.call_args[1]
                assert feedback_call['feedback_type'] == feedback_type


class TestStep123ParityAndBehavior:
    """Parity tests ensuring Step 123 meets behavioral definition of done"""

    @pytest.mark.asyncio
    async def test_behavioral_definition_feedback_record_creation(self):
        """
        BEHAVIORAL TEST: Step 123 must create ExpertFeedback records in database
        per Mermaid node: CreateFeedbackRec[Create ExpertFeedback record]
        """

        context = {
            'rag_step': 121,
            'query_id': str(uuid4()),
            'expert_id': str(uuid4()),
            'feedback_data': {
                'feedback_type': 'incorrect',
                'category': 'calcolo_sbagliato',
                'query_text': 'How to calculate Italian corporate tax?',
                'expert_answer': 'Corrected calculation methodology',
                'confidence_score': 0.9,
                'time_spent_seconds': 150
            },
            'trust_validation_result': {'trust_score': 0.88, 'meets_threshold': True}
        }

        with patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:
            mock_collector = mock_collector_class.return_value
            mock_collector.collect_feedback = AsyncMock(return_value={
                'success': True,
                'feedback_id': str(uuid4()),
                'feedback_type': 'incorrect',
                'category': 'calcolo_sbagliato',
                'processing_time_ms': 140,
                'expert_trust_score': 0.88,
                'action_taken': 'record_created'
            })

            # Execute Step 123
            result = await step_123__create_feedback_rec(ctx=context)

            # BEHAVIORAL VERIFICATION: ExpertFeedback record must be created
            assert result['feedback_record_created'] is True
            assert result['feedback_id'] is not None

            # Verify service integration creates actual record
            mock_collector.collect_feedback.assert_called_once()

            # Verify record contains all required feedback data
            feedback_call = mock_collector.collect_feedback.call_args[1]
            assert feedback_call['query_id'] == context['query_id']
            assert feedback_call['expert_id'] == context['expert_id']
            assert feedback_call['feedback_type'] == 'incorrect'
            assert feedback_call['category'] == 'calcolo_sbagliato'

    @pytest.mark.asyncio
    async def test_behavioral_definition_mermaid_flow_compliance(self):
        """
        BEHAVIORAL TEST: Step 123 must comply with Mermaid flow:
        TrustScoreOK →|Yes| CreateFeedbackRec → UpdateExpertMetrics
        """

        # Simulate input from TrustScoreOK (Step 121) with "Yes" decision
        trust_score_ok_output = {
            'rag_step': 121,
            'step_id': 'RAG.classify.trust.score.at.least.0.7',
            'node_label': 'TrustScoreOK',
            'decision_outcome': 'Yes',  # Trust score >= 0.7
            'query_id': str(uuid4()),
            'expert_id': str(uuid4()),
            'feedback_data': {
                'feedback_type': 'correct',
                'confidence_score': 0.95,
                'time_spent_seconds': 60
            },
            'trust_validation_result': {'trust_score': 0.95, 'meets_threshold': True}
        }

        with patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:
            mock_collector = mock_collector_class.return_value
            mock_collector.collect_feedback = AsyncMock(return_value={
                'success': True,
                'feedback_id': str(uuid4()),
                'feedback_type': 'correct',
                'processing_time_ms': 80,
                'expert_trust_score': 0.95,
                'action_taken': 'record_created'
            })

            # Execute CreateFeedbackRec (Step 123)
            result = await step_123__create_feedback_rec(ctx=trust_score_ok_output)

            # BEHAVIORAL VERIFICATION: Must route to UpdateExpertMetrics (Step 124)
            assert result['next_step'] == 124
            assert result['next_step_id'] == 'RAG.metrics.update.expert.metrics'
            assert result['route_to'] == 'UpdateExpertMetrics'

            # Verify Mermaid flow compliance
            assert result['mermaid_flow_compliance'] is True
            assert result['previous_node'] == 'TrustScoreOK'
            assert result['current_node'] == 'CreateFeedbackRec'
            assert result['next_node'] == 'UpdateExpertMetrics'

    @pytest.mark.asyncio
    async def test_behavioral_definition_thin_orchestration_pattern(self):
        """
        BEHAVIORAL TEST: Step 123 must follow thin orchestration pattern
        (coordination only, no business logic in orchestrator)
        """

        context = {
            'rag_step': 121,
            'query_id': str(uuid4()),
            'expert_id': str(uuid4()),
            'feedback_data': {
                'feedback_type': 'incomplete',
                'category': 'troppo_generico',
                'confidence_score': 0.8,
                'time_spent_seconds': 100
            },
            'trust_validation_result': {'trust_score': 0.82, 'meets_threshold': True}
        }

        with patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:
            mock_collector = mock_collector_class.return_value
            mock_collector.collect_feedback = AsyncMock(return_value={
                'success': True,
                'feedback_id': str(uuid4()),
                'feedback_type': 'incomplete',
                'category': 'troppo_generico',
                'processing_time_ms': 105,
                'expert_trust_score': 0.82,
                'action_taken': 'record_created'
            })

            # Execute Step 123
            result = await step_123__create_feedback_rec(ctx=context)

            # BEHAVIORAL VERIFICATION: Thin orchestration pattern
            # All business logic must be in ExpertFeedbackCollector service
            mock_collector.collect_feedback.assert_called_once()

            # Orchestrator only coordinates and preserves context
            assert result['orchestration_pattern'] == 'thin'
            assert 'business_logic_delegation' in result
            assert result['business_logic_delegation']['service'] == 'ExpertFeedbackCollector'
            assert result['business_logic_delegation']['method'] == 'collect_feedback'

            # Context preservation (coordination responsibility)
            assert result['context_preserved'] is True
            assert result['query_id'] == context['query_id']
            assert result['expert_id'] == context['expert_id']

    @pytest.mark.asyncio
    async def test_behavioral_definition_structured_observability(self):
        """
        BEHAVIORAL TEST: Step 123 must implement structured observability
        with rag_step_log and rag_step_timer per MASTER_GUARDRAILS
        """

        context = {
            'rag_step': 121,
            'query_id': str(uuid4()),
            'expert_id': str(uuid4()),
            'feedback_data': {
                'feedback_type': 'incorrect',
                'confidence_score': 0.85,
                'time_spent_seconds': 120
            }
        }

        with patch('app.orchestrators.feedback.rag_step_log') as mock_log, \
             patch('app.orchestrators.feedback.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:

            mock_collector = mock_collector_class.return_value
            mock_collector.collect_feedback = AsyncMock(return_value={
                'success': True,
                'feedback_id': str(uuid4()),
                'processing_time_ms': 95
            })

            # Execute Step 123
            result = await step_123__create_feedback_rec(ctx=context)

            # BEHAVIORAL VERIFICATION: Structured logging must be used
            mock_log.assert_called()
            log_calls = mock_log.call_args_list

            # Verify required log structure
            start_log = log_calls[0][1]  # kwargs from first call
            assert start_log['step'] == 123
            assert start_log['step_id'] == 'RAG.feedback.create.expertfeedback.record'
            assert start_log['node_label'] == 'CreateFeedbackRec'
            assert start_log['category'] == 'feedback'
            assert start_log['type'] == 'process'

            # BEHAVIORAL VERIFICATION: Timing must be tracked
            mock_timer.assert_called_with(
                123,
                'RAG.feedback.create.expertfeedback.record',
                'CreateFeedbackRec',
                stage="start"
            )

            # Verify observability in result
            assert 'observability' in result
            assert result['observability']['structured_logging'] is True
            assert result['observability']['timing_tracked'] is True

    @pytest.mark.asyncio
    async def test_behavioral_definition_error_handling_graceful_fallback(self):
        """
        BEHAVIORAL TEST: Step 123 must handle errors gracefully without
        breaking the pipeline flow per MASTER_GUARDRAILS
        """

        context = {
            'rag_step': 121,
            'query_id': str(uuid4()),
            'expert_id': str(uuid4()),
            'feedback_data': {
                'feedback_type': 'incorrect',
                'confidence_score': 0.8,
                'time_spent_seconds': 90
            }
        }

        # Test various error scenarios
        error_scenarios = [
            (FeedbackValidationError("Invalid feedback format"), 'validation_error'),
            (Exception("Database connection lost"), 'service_error'),
            (ValueError("Invalid UUID format"), 'data_error')
        ]

        for error, expected_error_type in error_scenarios:
            with patch('app.orchestrators.feedback.ExpertFeedbackCollector') as mock_collector_class:
                mock_collector = mock_collector_class.return_value
                mock_collector.collect_feedback = AsyncMock(side_effect=error)

                # Execute Step 123
                result = await step_123__create_feedback_rec(ctx=context)

                # BEHAVIORAL VERIFICATION: Graceful error handling
                assert result['success'] is False
                assert result['error_type'] == expected_error_type
                assert 'error_message' in result

                # Pipeline continuity must be preserved
                assert result['step'] == 123
                assert result['step_id'] == 'RAG.feedback.create.expertfeedback.record'
                assert result['context_preserved'] is True

                # Context data must be preserved despite errors
                assert result['query_id'] == context['query_id']
                assert result['expert_id'] == context['expert_id']

                # Error must not crash the orchestrator
                assert 'processing_metadata' in result
                assert 'error_handled_gracefully' in result
                assert result['error_handled_gracefully'] is True