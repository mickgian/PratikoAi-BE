"""
Tests for RAG Step 124 — Update expert metrics (RAG.metrics.update.expert.metrics)

Test coverage:
- Unit tests: Expert metrics updates, performance calculations, error handling
- Integration tests: Step 123→124, 124→125, full pipeline flows
- Parity tests: Behavioral definition of done validation
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4, UUID

from app.orchestrators.metrics import step_124__update_expert_metrics
from app.services.expert_validation_workflow import ExpertValidationWorkflow
from app.models.quality_analysis import ExpertProfile, ExpertFeedback, FeedbackType, ItalianFeedbackCategory


class TestStep124UpdateExpertMetrics:
    """Unit tests for Step 124 update expert metrics orchestrator"""

    @pytest.fixture
    def valid_context_from_step_123(self):
        """Context data received from Step 123 (CreateFeedbackRec) with feedback record created"""
        return {
            'rag_step': 123,
            'step_id': 'RAG.feedback.create.expertfeedback.record',
            'node_label': 'CreateFeedbackRec',
            'success': True,
            'feedback_record_created': True,
            'feedback_id': str(uuid4()),
            'feedback_type': 'incorrect',
            'italian_category': 'interpretazione_errata',
            'expert_trust_score': 0.85,
            'query_id': str(uuid4()),
            'expert_id': str(uuid4()),
            'expert_metrics_update': {
                'expert_id': str(uuid4()),
                'feedback_created': True,
                'feedback_record_id': str(uuid4()),
                'feedback_type': 'incorrect',
                'processing_time_ms': 125,
                'trust_score_at_creation': 0.85,
                'feedback_metadata': {
                    'category': 'interpretazione_errata',
                    'confidence_score': 0.9,
                    'time_spent_seconds': 120
                }
            },
            'pipeline_context': {
                'step_121_trust_validation': {
                    'trust_score': 0.85,
                    'meets_threshold': True,
                    'threshold_used': 0.7
                },
                'step_123_feedback_creation': {
                    'success': True,
                    'feedback_id': str(uuid4()),
                    'processing_time_ms': 125
                }
            },
            'processing_metadata': {
                'step_123_duration_ms': 125,
                'feedback_collection_time_ms': 95,
                'timestamp': datetime.utcnow().isoformat()
            }
        }

    @pytest.fixture
    def mock_expert_profile(self):
        """Mock expert profile for metrics updates"""
        return ExpertProfile(
            id=uuid4(),
            user_id=uuid4(),
            credentials=["CPA", "Tax Professional"],
            experience_years=10,
            feedback_count=24,
            feedback_accuracy_rate=0.82,
            average_response_time_seconds=90,
            trust_score=0.85,
            specializations=["Italian Tax Law", "VAT Regulations"]
        )

    @pytest.fixture
    def mock_feedback_record(self):
        """Mock feedback record from Step 123"""
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
    async def test_update_expert_metrics_success(self, valid_context_from_step_123, mock_expert_profile):
        """Test successful expert metrics update with valid context from Step 123"""

        with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
            # Setup mock workflow
            mock_workflow = mock_workflow_class.return_value
            mock_workflow.get_expert_profile = AsyncMock(return_value=mock_expert_profile)
            mock_workflow.update_expert_performance_metrics = AsyncMock(return_value={
                'expert_id': valid_context_from_step_123['expert_id'],
                'metrics_updated': True,
                'new_trust_score': 0.87,
                'feedback_count': 25,
                'accuracy_rate': 0.84,
                'average_response_time': 88,
                'processing_time_ms': 45
            })

            # Execute step
            result = await step_124__update_expert_metrics(ctx=valid_context_from_step_123)

            # Verify orchestrator behavior
            assert result['success'] is True
            assert result['metrics_updated'] is True
            assert result['expert_id'] == valid_context_from_step_123['expert_id']
            assert result['new_trust_score'] == 0.87

            # Verify context preservation
            assert result['query_id'] == valid_context_from_step_123['query_id']
            assert result['feedback_id'] == valid_context_from_step_123['feedback_id']

            # Verify routing metadata for Step 125
            assert result['next_step'] == 125
            assert result['next_step_id'] == 'RAG.cache.cache.feedback.1h.ttl'
            assert result['route_to'] == 'CacheFeedback'

            # Verify service integration
            mock_workflow.update_expert_performance_metrics.assert_called_once()
            metrics_call = mock_workflow.update_expert_performance_metrics.call_args[1]
            assert metrics_call['expert_id'] == valid_context_from_step_123['expert_id']
            assert metrics_call['feedback_metadata']['confidence_score'] == 0.9

    @pytest.mark.asyncio
    async def test_update_expert_metrics_expert_not_found(self, valid_context_from_step_123):
        """Test handling when expert profile is not found"""

        with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
            mock_workflow = mock_workflow_class.return_value
            mock_workflow.get_expert_profile = AsyncMock(return_value=None)

            # Execute step
            result = await step_124__update_expert_metrics(ctx=valid_context_from_step_123)

            # Verify error handling
            assert result['success'] is False
            assert result['error_type'] == 'expert_not_found'
            assert 'Expert profile not found' in result['error_message']

            # Verify context preservation
            assert result['expert_id'] == valid_context_from_step_123['expert_id']
            assert result['query_id'] == valid_context_from_step_123['query_id']

            # Verify graceful error handling (no crash)
            assert 'processing_metadata' in result
            assert result['step'] == 124

    @pytest.mark.asyncio
    async def test_update_expert_metrics_missing_context_data(self):
        """Test handling of missing or incomplete context data from Step 123"""

        incomplete_context = {
            'rag_step': 123,
            'success': True,
            'query_id': str(uuid4()),
            # Missing expert_metrics_update, expert_id, etc.
        }

        # Execute step
        result = await step_124__update_expert_metrics(ctx=incomplete_context)

        # Verify error handling
        assert result['success'] is False
        assert result['error_type'] == 'missing_context_data'
        assert 'expert_metrics_update' in result['error_message'] or 'expert_id' in result['error_message']

        # Verify graceful fallback
        assert result['step'] == 124
        assert result['step_id'] == 'RAG.metrics.update.expert.metrics'

    @pytest.mark.asyncio
    async def test_update_expert_metrics_service_error(self, valid_context_from_step_123, mock_expert_profile):
        """Test handling of service-level errors during metrics update"""

        with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
            mock_workflow = mock_workflow_class.return_value
            mock_workflow.get_expert_profile = AsyncMock(return_value=mock_expert_profile)
            mock_workflow.update_expert_performance_metrics = AsyncMock(
                side_effect=Exception("Database connection failed")
            )

            # Execute step
            result = await step_124__update_expert_metrics(ctx=valid_context_from_step_123)

            # Verify error handling
            assert result['success'] is False
            assert result['error_type'] == 'service_error'
            assert 'Database connection failed' in result['error_message']

            # Verify context preservation
            assert result['expert_id'] == valid_context_from_step_123['expert_id']
            assert result['query_id'] == valid_context_from_step_123['query_id']

    @pytest.mark.asyncio
    async def test_update_expert_metrics_feedback_type_handling(self, valid_context_from_step_123, mock_expert_profile):
        """Test metrics updates for different feedback types (correct, incorrect, incomplete)"""

        feedback_types = ['correct', 'incorrect', 'incomplete']

        for feedback_type in feedback_types:
            context = valid_context_from_step_123.copy()
            context['feedback_type'] = feedback_type
            context['expert_metrics_update']['feedback_type'] = feedback_type

            # Adjust expected correction quality based on feedback type
            expected_quality = {
                'correct': 1.0,
                'incorrect': 0.3,  # Expert found error, good feedback
                'incomplete': 0.7   # Expert provided additional info
            }

            with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
                mock_workflow = mock_workflow_class.return_value
                mock_workflow.get_expert_profile = AsyncMock(return_value=mock_expert_profile)
                mock_workflow.update_expert_performance_metrics = AsyncMock(return_value={
                    'expert_id': context['expert_id'],
                    'metrics_updated': True,
                    'feedback_type_processed': feedback_type,
                    'correction_quality': expected_quality[feedback_type],
                    'new_trust_score': 0.86,
                    'processing_time_ms': 50
                })

                # Execute step
                result = await step_124__update_expert_metrics(ctx=context)

                # Verify feedback type handling
                assert result['success'] is True
                assert result['feedback_type_processed'] == feedback_type
                assert result['correction_quality'] == expected_quality[feedback_type]

                # Verify service called with correct parameters
                metrics_call = mock_workflow.update_expert_performance_metrics.call_args[1]
                assert metrics_call['feedback_type'] == feedback_type

    @pytest.mark.asyncio
    async def test_update_expert_metrics_italian_category_processing(self, valid_context_from_step_123, mock_expert_profile):
        """Test metrics updates for Italian feedback categories"""

        italian_categories = [
            'normativa_obsoleta',
            'interpretazione_errata',
            'caso_mancante',
            'calcolo_sbagliato',
            'troppo_generico'
        ]

        for category in italian_categories:
            context = valid_context_from_step_123.copy()
            context['italian_category'] = category
            context['expert_metrics_update']['feedback_metadata']['category'] = category

            with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
                mock_workflow = mock_workflow_class.return_value
                mock_workflow.get_expert_profile = AsyncMock(return_value=mock_expert_profile)
                mock_workflow.update_expert_performance_metrics = AsyncMock(return_value={
                    'expert_id': context['expert_id'],
                    'metrics_updated': True,
                    'italian_category_processed': category,
                    'category_quality_impact': 0.85,
                    'processing_time_ms': 55
                })

                # Execute step
                result = await step_124__update_expert_metrics(ctx=context)

                # Verify Italian category handling
                assert result['success'] is True
                assert result['italian_category_processed'] == category

                # Verify service receives category information
                metrics_call = mock_workflow.update_expert_performance_metrics.call_args[1]
                assert metrics_call['feedback_metadata']['category'] == category

    @pytest.mark.asyncio
    async def test_update_expert_metrics_performance_tracking(self, valid_context_from_step_123, mock_expert_profile):
        """Test performance tracking and timing requirements"""

        with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
            mock_workflow = mock_workflow_class.return_value
            mock_workflow.get_expert_profile = AsyncMock(return_value=mock_expert_profile)
            mock_workflow.update_expert_performance_metrics = AsyncMock(return_value={
                'expert_id': valid_context_from_step_123['expert_id'],
                'metrics_updated': True,
                'processing_time_ms': 75,  # Simulated service processing time
                'new_trust_score': 0.86
            })

            # Execute step
            start_time = datetime.utcnow()
            result = await step_124__update_expert_metrics(ctx=valid_context_from_step_123)
            end_time = datetime.utcnow()

            # Verify performance tracking
            assert 'processing_metadata' in result
            assert 'step_124_duration_ms' in result['processing_metadata']
            assert 'metrics_update_time_ms' in result['processing_metadata']

            # Verify timing is reasonable (should be fast)
            total_time = (end_time - start_time).total_seconds() * 1000
            assert total_time < 3000  # Should complete in under 3 seconds

            # Verify service processing time is included
            assert result['processing_metadata']['metrics_update_time_ms'] == 75


class TestStep124IntegrationFlows:
    """Integration tests for Step 124 with neighboring RAG steps"""

    @pytest.fixture
    def step_123_output_feedback_created(self):
        """Output from Step 123 when ExpertFeedback record was created successfully"""
        return {
            'rag_step': 123,
            'step_id': 'RAG.feedback.create.expertfeedback.record',
            'node_label': 'CreateFeedbackRec',
            'success': True,
            'feedback_record_created': True,
            'feedback_id': str(uuid4()),
            'feedback_type': 'incomplete',
            'italian_category': 'caso_mancante',
            'expert_trust_score': 0.88,
            'query_id': str(uuid4()),
            'expert_id': str(uuid4()),
            'expert_metrics_update': {
                'expert_id': str(uuid4()),
                'feedback_created': True,
                'feedback_record_id': str(uuid4()),
                'feedback_type': 'incomplete',
                'processing_time_ms': 110,
                'trust_score_at_creation': 0.88,
                'feedback_metadata': {
                    'category': 'caso_mancante',
                    'confidence_score': 0.92,
                    'time_spent_seconds': 150
                }
            },
            'pipeline_context': {
                'step_121_trust_validation': {
                    'trust_score': 0.88,
                    'meets_threshold': True,
                    'threshold_used': 0.7,
                    'validation_timestamp': datetime.utcnow().isoformat()
                },
                'step_123_feedback_creation': {
                    'success': True,
                    'feedback_id': str(uuid4()),
                    'processing_time_ms': 110
                }
            },
            'processing_metadata': {
                'step_123_duration_ms': 110,
                'feedback_collection_time_ms': 85,
                'timestamp': datetime.utcnow().isoformat()
            }
        }

    @pytest.mark.asyncio
    async def test_step_123_to_124_integration(self, step_123_output_feedback_created):
        """Test integration flow from Step 123 (CreateFeedbackRec) to Step 124"""

        mock_expert = ExpertProfile(
            id=uuid4(),
            user_id=uuid4(),
            credentials=["CPA"],
            experience_years=8,
            feedback_count=15,
            feedback_accuracy_rate=0.79,
            trust_score=0.88
        )

        with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
            mock_workflow = mock_workflow_class.return_value
            mock_workflow.get_expert_profile = AsyncMock(return_value=mock_expert)
            mock_workflow.update_expert_performance_metrics = AsyncMock(return_value={
                'expert_id': step_123_output_feedback_created['expert_id'],
                'metrics_updated': True,
                'new_trust_score': 0.89,
                'feedback_count': 16,
                'accuracy_rate': 0.81,
                'processing_time_ms': 65
            })

            # Execute Step 124 with Step 123 output
            result = await step_124__update_expert_metrics(ctx=step_123_output_feedback_created)

            # Verify integration preserves Step 123 data
            assert result['query_id'] == step_123_output_feedback_created['query_id']
            assert result['expert_id'] == step_123_output_feedback_created['expert_id']
            assert result['feedback_id'] == step_123_output_feedback_created['feedback_id']

            # Verify Step 123 context is preserved
            assert result['previous_step'] == 123
            assert result['previous_step_outcome'] == 'feedback_record_created'

            # Verify metrics update uses Step 123 data
            metrics_call = mock_workflow.update_expert_performance_metrics.call_args[1]
            assert metrics_call['feedback_type'] == 'incomplete'
            assert metrics_call['feedback_metadata']['category'] == 'caso_mancante'
            assert metrics_call['feedback_metadata']['confidence_score'] == 0.92

    @pytest.mark.asyncio
    async def test_step_124_to_125_routing_setup(self, step_123_output_feedback_created):
        """Test Step 124 prepares routing to Step 125 (CacheFeedback)"""

        mock_expert = ExpertProfile(
            id=uuid4(),
            user_id=uuid4(),
            trust_score=0.88,
            feedback_count=20
        )

        with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
            mock_workflow = mock_workflow_class.return_value
            mock_workflow.get_expert_profile = AsyncMock(return_value=mock_expert)
            mock_workflow.update_expert_performance_metrics = AsyncMock(return_value={
                'expert_id': step_123_output_feedback_created['expert_id'],
                'metrics_updated': True,
                'new_trust_score': 0.90,
                'processing_time_ms': 70
            })

            # Execute Step 124
            result = await step_124__update_expert_metrics(ctx=step_123_output_feedback_created)

            # Verify routing setup for Step 125
            assert result['next_step'] == 125
            assert result['next_step_id'] == 'RAG.cache.cache.feedback.1h.ttl'
            assert result['route_to'] == 'CacheFeedback'

            # Verify data prepared for Step 125
            assert 'cache_feedback_data' in result
            assert result['cache_feedback_data']['expert_id'] == step_123_output_feedback_created['expert_id']
            assert result['cache_feedback_data']['metrics_updated'] is True
            assert 'updated_metrics' in result['cache_feedback_data']

    @pytest.mark.asyncio
    async def test_full_pipeline_123_124_125_preparation(self, step_123_output_feedback_created):
        """Test full pipeline flow preparation: Step 123 → 124 → 125"""

        mock_expert = ExpertProfile(
            id=uuid4(),
            user_id=uuid4(),
            trust_score=0.88,
            feedback_count=30,
            feedback_accuracy_rate=0.85
        )

        with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
            mock_workflow = mock_workflow_class.return_value
            mock_workflow.get_expert_profile = AsyncMock(return_value=mock_expert)
            mock_workflow.update_expert_performance_metrics = AsyncMock(return_value={
                'expert_id': step_123_output_feedback_created['expert_id'],
                'metrics_updated': True,
                'new_trust_score': 0.91,
                'new_accuracy_rate': 0.87,
                'new_feedback_count': 31,
                'processing_time_ms': 80
            })

            # Execute Step 124
            result = await step_124__update_expert_metrics(ctx=step_123_output_feedback_created)

            # Verify complete pipeline context preservation
            assert result['pipeline_context']['step_123_feedback_creation'] == step_123_output_feedback_created['pipeline_context']['step_123_feedback_creation']
            assert result['pipeline_context']['step_124_metrics_update']['success'] is True

            # Verify data flow continuity
            assert result['expert_id'] == step_123_output_feedback_created['expert_id']
            assert result['feedback_id'] == step_123_output_feedback_created['feedback_id']

            # Verify Step 125 preparation includes all necessary data
            assert 'feedback_cache_key' in result['cache_feedback_data']
            assert 'metrics_snapshot' in result['cache_feedback_data']
            assert 'expert_performance_data' in result['cache_feedback_data']

    @pytest.mark.asyncio
    async def test_metrics_calculation_accuracy_integration(self):
        """Test integration with accurate metrics calculations across feedback types"""

        expert_id = str(uuid4())
        feedback_scenarios = [
            {'type': 'correct', 'confidence': 0.95, 'expected_quality': 1.0},
            {'type': 'incorrect', 'confidence': 0.90, 'expected_quality': 0.3},
            {'type': 'incomplete', 'confidence': 0.85, 'expected_quality': 0.7}
        ]

        for scenario in feedback_scenarios:
            # Create context for each scenario
            context = {
                'rag_step': 123,
                'expert_id': expert_id,
                'feedback_id': str(uuid4()),
                'feedback_type': scenario['type'],
                'expert_metrics_update': {
                    'expert_id': expert_id,
                    'feedback_type': scenario['type'],
                    'feedback_metadata': {
                        'confidence_score': scenario['confidence'],
                        'time_spent_seconds': 100
                    }
                }
            }

            mock_expert = ExpertProfile(
                id=UUID(expert_id),
                user_id=uuid4(),
                trust_score=0.80,
                feedback_count=10,
                feedback_accuracy_rate=0.75
            )

            with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
                mock_workflow = mock_workflow_class.return_value
                mock_workflow.get_expert_profile = AsyncMock(return_value=mock_expert)
                mock_workflow.update_expert_performance_metrics = AsyncMock(return_value={
                    'expert_id': expert_id,
                    'metrics_updated': True,
                    'correction_quality': scenario['expected_quality'],
                    'new_trust_score': 0.82,
                    'processing_time_ms': 60
                })

                # Execute Step 124
                result = await step_124__update_expert_metrics(ctx=context)

                # Verify accurate metrics calculation
                assert result['success'] is True
                assert result['correction_quality'] == scenario['expected_quality']

                # Verify service called with correct quality calculation
                metrics_call = mock_workflow.update_expert_performance_metrics.call_args[1]
                assert metrics_call['feedback_type'] == scenario['type']


class TestStep124ParityAndBehavior:
    """Parity tests ensuring Step 124 meets behavioral definition of done"""

    @pytest.mark.asyncio
    async def test_behavioral_definition_expert_metrics_update(self):
        """
        BEHAVIORAL TEST: Step 124 must update expert performance metrics
        per Mermaid node: UpdateExpertMetrics[Update expert metrics]
        """

        expert_id = str(uuid4())
        context = {
            'rag_step': 123,
            'expert_id': expert_id,
            'feedback_id': str(uuid4()),
            'feedback_type': 'incorrect',
            'expert_metrics_update': {
                'expert_id': expert_id,
                'feedback_type': 'incorrect',
                'feedback_metadata': {
                    'confidence_score': 0.88,
                    'time_spent_seconds': 180,
                    'category': 'calcolo_sbagliato'
                }
            }
        }

        mock_expert = ExpertProfile(
            id=UUID(expert_id),
            user_id=uuid4(),
            trust_score=0.82,
            feedback_count=18,
            feedback_accuracy_rate=0.78
        )

        with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
            mock_workflow = mock_workflow_class.return_value
            mock_workflow.get_expert_profile = AsyncMock(return_value=mock_expert)
            mock_workflow.update_expert_performance_metrics = AsyncMock(return_value={
                'expert_id': expert_id,
                'metrics_updated': True,
                'new_trust_score': 0.84,
                'new_accuracy_rate': 0.79,
                'new_feedback_count': 19,
                'processing_time_ms': 55
            })

            # Execute Step 124
            result = await step_124__update_expert_metrics(ctx=context)

            # BEHAVIORAL VERIFICATION: Expert metrics must be updated
            assert result['metrics_updated'] is True
            assert result['new_trust_score'] == 0.84
            assert result['new_accuracy_rate'] == 0.79

            # Verify service integration updates actual metrics
            mock_workflow.update_expert_performance_metrics.assert_called_once()

            # Verify metrics contain performance improvements
            metrics_call = mock_workflow.update_expert_performance_metrics.call_args[1]
            assert metrics_call['expert_id'] == expert_id
            assert metrics_call['feedback_type'] == 'incorrect'
            assert metrics_call['feedback_metadata']['confidence_score'] == 0.88

    @pytest.mark.asyncio
    async def test_behavioral_definition_mermaid_flow_compliance(self):
        """
        BEHAVIORAL TEST: Step 124 must comply with Mermaid flow:
        CreateFeedbackRec → UpdateExpertMetrics → CacheFeedback
        """

        # Simulate input from CreateFeedbackRec (Step 123)
        create_feedback_output = {
            'rag_step': 123,
            'step_id': 'RAG.feedback.create.expertfeedback.record',
            'node_label': 'CreateFeedbackRec',
            'success': True,
            'feedback_record_created': True,
            'expert_id': str(uuid4()),
            'feedback_id': str(uuid4()),
            'expert_metrics_update': {
                'expert_id': str(uuid4()),
                'feedback_created': True,
                'feedback_metadata': {
                    'confidence_score': 0.93,
                    'time_spent_seconds': 95
                }
            }
        }

        mock_expert = ExpertProfile(
            id=uuid4(),
            user_id=uuid4(),
            trust_score=0.86
        )

        with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
            mock_workflow = mock_workflow_class.return_value
            mock_workflow.get_expert_profile = AsyncMock(return_value=mock_expert)
            mock_workflow.update_expert_performance_metrics = AsyncMock(return_value={
                'expert_id': create_feedback_output['expert_id'],
                'metrics_updated': True,
                'processing_time_ms': 50
            })

            # Execute UpdateExpertMetrics (Step 124)
            result = await step_124__update_expert_metrics(ctx=create_feedback_output)

            # BEHAVIORAL VERIFICATION: Must route to CacheFeedback (Step 125)
            assert result['next_step'] == 125
            assert result['next_step_id'] == 'RAG.cache.cache.feedback.1h.ttl'
            assert result['route_to'] == 'CacheFeedback'

            # Verify Mermaid flow compliance
            assert result['mermaid_flow_compliance'] is True
            assert result['previous_node'] == 'CreateFeedbackRec'
            assert result['current_node'] == 'UpdateExpertMetrics'
            assert result['next_node'] == 'CacheFeedback'

    @pytest.mark.asyncio
    async def test_behavioral_definition_thin_orchestration_pattern(self):
        """
        BEHAVIORAL TEST: Step 124 must follow thin orchestration pattern
        (coordination only, no business logic in orchestrator)
        """

        context = {
            'rag_step': 123,
            'expert_id': str(uuid4()),
            'expert_metrics_update': {
                'expert_id': str(uuid4()),
                'feedback_metadata': {
                    'confidence_score': 0.87,
                    'time_spent_seconds': 110
                }
            }
        }

        mock_expert = ExpertProfile(
            id=uuid4(),
            user_id=uuid4(),
            trust_score=0.83
        )

        with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
            mock_workflow = mock_workflow_class.return_value
            mock_workflow.get_expert_profile = AsyncMock(return_value=mock_expert)
            mock_workflow.update_expert_performance_metrics = AsyncMock(return_value={
                'expert_id': context['expert_id'],
                'metrics_updated': True,
                'processing_time_ms': 65
            })

            # Execute Step 124
            result = await step_124__update_expert_metrics(ctx=context)

            # BEHAVIORAL VERIFICATION: Thin orchestration pattern
            # All business logic must be in ExpertValidationWorkflow service
            mock_workflow.update_expert_performance_metrics.assert_called_once()

            # Orchestrator only coordinates and preserves context
            assert result['orchestration_pattern'] == 'thin'
            assert 'business_logic_delegation' in result
            assert result['business_logic_delegation']['service'] == 'ExpertValidationWorkflow'
            assert result['business_logic_delegation']['method'] == 'update_expert_performance_metrics'

            # Context preservation (coordination responsibility)
            assert result['context_preserved'] is True
            assert result['expert_id'] == context['expert_id']

    @pytest.mark.asyncio
    async def test_behavioral_definition_structured_observability(self):
        """
        BEHAVIORAL TEST: Step 124 must implement structured observability
        with rag_step_log and rag_step_timer per MASTER_GUARDRAILS
        """

        context = {
            'rag_step': 123,
            'expert_id': str(uuid4()),
            'expert_metrics_update': {
                'expert_id': str(uuid4()),
                'feedback_metadata': {'confidence_score': 0.85}
            }
        }

        mock_expert = ExpertProfile(id=uuid4(), user_id=uuid4(), trust_score=0.80)

        with patch('app.orchestrators.metrics.rag_step_log') as mock_log, \
             patch('app.orchestrators.metrics.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:

            mock_workflow = mock_workflow_class.return_value
            mock_workflow.get_expert_profile = AsyncMock(return_value=mock_expert)
            mock_workflow.update_expert_performance_metrics = AsyncMock(return_value={
                'metrics_updated': True,
                'processing_time_ms': 45
            })

            # Execute Step 124
            result = await step_124__update_expert_metrics(ctx=context)

            # BEHAVIORAL VERIFICATION: Structured logging must be used
            mock_log.assert_called()
            log_calls = mock_log.call_args_list

            # Verify required log structure
            start_log = log_calls[0][1]  # kwargs from first call
            assert start_log['step'] == 124
            assert start_log['step_id'] == 'RAG.metrics.update.expert.metrics'
            assert start_log['node_label'] == 'UpdateExpertMetrics'
            assert start_log['category'] == 'metrics'
            assert start_log['type'] == 'process'

            # BEHAVIORAL VERIFICATION: Timing must be tracked
            mock_timer.assert_called_with(
                124,
                'RAG.metrics.update.expert.metrics',
                'UpdateExpertMetrics',
                stage="start"
            )

            # Verify observability in result
            assert 'observability' in result
            assert result['observability']['structured_logging'] is True
            assert result['observability']['timing_tracked'] is True

    @pytest.mark.asyncio
    async def test_behavioral_definition_error_handling_graceful_fallback(self):
        """
        BEHAVIORAL TEST: Step 124 must handle errors gracefully without
        breaking the pipeline flow per MASTER_GUARDRAILS
        """

        context = {
            'rag_step': 123,
            'expert_id': str(uuid4()),
            'expert_metrics_update': {
                'expert_id': str(uuid4()),
                'feedback_metadata': {'confidence_score': 0.89}
            }
        }

        # Test various error scenarios
        error_scenarios = [
            (Exception("Database timeout"), 'service_error'),
            (ValueError("Invalid expert data"), 'data_error'),
            (RuntimeError("Metrics calculation failed"), 'calculation_error')
        ]

        for error, expected_error_type in error_scenarios:
            with patch('app.orchestrators.metrics.ExpertValidationWorkflow') as mock_workflow_class:
                mock_workflow = mock_workflow_class.return_value
                mock_workflow.get_expert_profile = AsyncMock(side_effect=error)

                # Execute Step 124
                result = await step_124__update_expert_metrics(ctx=context)

                # BEHAVIORAL VERIFICATION: Graceful error handling
                assert result['success'] is False
                assert result['error_type'] == expected_error_type
                assert 'error_message' in result

                # Pipeline continuity must be preserved
                assert result['step'] == 124
                assert result['step_id'] == 'RAG.metrics.update.expert.metrics'
                assert result['context_preserved'] is True

                # Context data must be preserved despite errors
                assert result['expert_id'] == context['expert_id']

                # Error must not crash the orchestrator
                assert 'processing_metadata' in result
                assert 'error_handled_gracefully' in result
                assert result['error_handled_gracefully'] is True