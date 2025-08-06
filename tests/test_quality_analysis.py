"""
Comprehensive TDD Tests for Quality Analysis System with Expert Feedback Loop.

Tests all components of the quality analysis system for PratikoAI:
- Expert feedback collection with simple UI elements
- Advanced prompt engineering with structured reasoning
- Failure pattern analysis and categorization  
- Automatic improvement engine
- Expert validation workflow
- Quality metrics dashboard
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4, UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

# Test data structures and models
@pytest.fixture
def sample_expert_feedback():
    """Sample expert feedback data for testing"""
    return {
        "query_id": str(uuid4()),
        "expert_id": str(uuid4()),
        "feedback_type": "incorrect",  # correct, incomplete, incorrect
        "category": "interpretazione_errata",  # Italian categories
        "expert_answer": "La risposta corretta è che l'IVA al 22% si applica...",
        "confidence_score": 0.95,
        "time_spent_seconds": 45,
        "feedback_timestamp": datetime.utcnow(),
        "query_text": "Come calcolare l'IVA al 22%?",
        "original_answer": "L'IVA si calcola moltiplicando...",
        "improvement_suggestions": [
            "Specificare l'aliquota corretta",
            "Aggiungere esempi pratici"
        ]
    }


@pytest.fixture
def sample_prompt_template():
    """Sample advanced prompt template for testing"""
    return {
        "template_id": str(uuid4()),
        "name": "structured_reasoning_v1",
        "template_text": """
        ## Analisi del Quesito Fiscale

        **Domanda:** {query}

        **Contesto Normativo:** {regulatory_context}

        **Ragionamento Strutturato:**
        1. **Identificazione del Problema:** {problem_identification}
        2. **Normativa Applicabile:** {applicable_regulations}
        3. **Interpretazione:** {interpretation}
        4. **Conclusioni:** {conclusions}

        **Risposta Finale:** {final_answer}

        **Fonti:** {sources}
        """,
        "variables": ["query", "regulatory_context", "problem_identification", 
                     "applicable_regulations", "interpretation", "conclusions",
                     "final_answer", "sources"],
        "quality_metrics": {
            "clarity_score": 0.85,
            "completeness_score": 0.90,
            "accuracy_score": 0.88
        },
        "usage_count": 0,
        "success_rate": 0.0
    }


@pytest.fixture
def sample_failure_patterns():
    """Sample failure patterns for analysis testing"""
    return [
        {
            "pattern_id": str(uuid4()),
            "pattern_type": "regulatory_outdated",
            "frequency": 15,
            "categories": ["normativa_obsoleta", "riferimenti_datati"],
            "example_queries": [
                "Regime forfettario 2023 soglie",
                "Detrazioni fiscali vecchia normativa"
            ],
            "impact_score": 0.8,
            "confidence": 0.9
        },
        {
            "pattern_id": str(uuid4()),
            "pattern_type": "interpretation_error",
            "frequency": 8,
            "categories": ["interpretazione_errata", "calcolo_sbagliato"],
            "example_queries": [
                "Calcolo IRPEF scaglioni",
                "IVA regime misto"
            ],
            "impact_score": 0.9,
            "confidence": 0.85
        }
    ]


class TestExpertFeedbackCollection:
    """Test expert feedback collection system"""
    
    @pytest.mark.asyncio
    async def test_collect_simple_feedback_correct(self, sample_expert_feedback):
        """Test collecting simple 'correct' feedback"""
        from app.services.expert_feedback_collector import ExpertFeedbackCollector
        
        collector = ExpertFeedbackCollector(db=AsyncMock(), cache=AsyncMock())
        
        # Test simple 'correct' feedback
        feedback_data = {
            "query_id": sample_expert_feedback["query_id"],
            "expert_id": sample_expert_feedback["expert_id"],
            "feedback_type": "correct",
            "time_spent_seconds": 15
        }
        
        result = await collector.collect_feedback(feedback_data)
        
        assert result["success"] is True
        assert result["feedback_id"] is not None
        assert result["processing_time_ms"] < 30000  # Under 30 second requirement
        
        # Verify database interaction
        collector.db.execute.assert_called()
        collector.db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_collect_detailed_feedback_incorrect(self, sample_expert_feedback):
        """Test collecting detailed 'incorrect' feedback with categories"""
        from app.services.expert_feedback_collector import ExpertFeedbackCollector
        
        collector = ExpertFeedbackCollector(db=AsyncMock(), cache=AsyncMock())
        
        # Mock successful feedback storage
        collector.db.execute.return_value.scalar.return_value = UUID(sample_expert_feedback["query_id"])
        
        result = await collector.collect_feedback(sample_expert_feedback)
        
        assert result["success"] is True
        assert result["feedback_type"] == "incorrect"
        assert result["category"] == "interpretazione_errata"
        assert "expert_answer" in result
        assert result["processing_time_ms"] < 30000
    
    @pytest.mark.asyncio
    async def test_collect_feedback_with_italian_categories(self):
        """Test feedback collection with Italian categorization options"""
        from app.services.expert_feedback_collector import ExpertFeedbackCollector
        
        collector = ExpertFeedbackCollector(db=AsyncMock(), cache=AsyncMock())
        
        italian_categories = [
            "normativa_obsoleta",        # Outdated regulation
            "interpretazione_errata",    # Wrong interpretation
            "caso_mancante",            # Missing case
            "calcolo_sbagliato",        # Wrong calculation
            "troppo_generico"           # Too generic
        ]
        
        for category in italian_categories:
            feedback_data = {
                "query_id": str(uuid4()),
                "expert_id": str(uuid4()),
                "feedback_type": "incorrect",
                "category": category,
                "time_spent_seconds": 30
            }
            
            result = await collector.collect_feedback(feedback_data)
            
            assert result["success"] is True
            assert result["category"] == category
    
    @pytest.mark.asyncio
    async def test_feedback_ui_response_time(self):
        """Test feedback UI response time requirement (< 30 seconds)"""
        from app.services.expert_feedback_collector import ExpertFeedbackCollector
        
        collector = ExpertFeedbackCollector(db=AsyncMock(), cache=AsyncMock())
        
        start_time = time.time()
        
        feedback_data = {
            "query_id": str(uuid4()),
            "expert_id": str(uuid4()),
            "feedback_type": "incomplete",
            "category": "caso_mancante",
            "time_spent_seconds": 25
        }
        
        result = await collector.collect_feedback(feedback_data)
        
        processing_time = (time.time() - start_time) * 1000
        
        assert processing_time < 30000  # Must be under 30 seconds
        assert result["processing_time_ms"] < 30000
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_feedback_validation_errors(self):
        """Test feedback validation and error handling"""
        from app.services.expert_feedback_collector import ExpertFeedbackCollector
        
        collector = ExpertFeedbackCollector(db=AsyncMock(), cache=AsyncMock())
        
        # Test missing required fields
        with pytest.raises(ValueError, match="Missing required field: query_id"):
            await collector.collect_feedback({
                "expert_id": str(uuid4()),
                "feedback_type": "correct"
            })
        
        # Test invalid feedback type
        with pytest.raises(ValueError, match="Invalid feedback_type"):
            await collector.collect_feedback({
                "query_id": str(uuid4()),
                "expert_id": str(uuid4()),
                "feedback_type": "invalid_type"
            })
        
        # Test invalid category for Italian system
        with pytest.raises(ValueError, match="Invalid category"):
            await collector.collect_feedback({
                "query_id": str(uuid4()),
                "expert_id": str(uuid4()),
                "feedback_type": "incorrect",
                "category": "invalid_category"
            })
    
    @pytest.mark.asyncio
    async def test_feedback_storage_and_retrieval(self, sample_expert_feedback):
        """Test feedback storage and retrieval functionality"""
        from app.services.expert_feedback_collector import ExpertFeedbackCollector
        
        collector = ExpertFeedbackCollector(db=AsyncMock(), cache=AsyncMock())
        
        # Store feedback
        await collector.collect_feedback(sample_expert_feedback)
        
        # Retrieve feedback
        stored_feedback = await collector.get_feedback_by_query_id(
            sample_expert_feedback["query_id"]
        )
        
        assert len(stored_feedback) > 0
        assert stored_feedback[0]["feedback_type"] == sample_expert_feedback["feedback_type"]
        assert stored_feedback[0]["category"] == sample_expert_feedback["category"]


class TestAdvancedPromptEngineering:
    """Test advanced prompt engineering system"""
    
    @pytest.mark.asyncio
    async def test_structured_reasoning_template(self, sample_prompt_template):
        """Test structured reasoning prompt template"""
        from app.services.advanced_prompt_engineer import AdvancedPromptEngineer
        
        engineer = AdvancedPromptEngineer(db=AsyncMock(), cache=AsyncMock())
        
        # Test template creation
        result = await engineer.create_prompt_template(sample_prompt_template)
        
        assert result["success"] is True
        assert result["template_id"] is not None
        assert "structured_reasoning_v1" in result["template_name"]
    
    @pytest.mark.asyncio
    async def test_prompt_generation_with_context(self):
        """Test prompt generation with Italian tax context"""
        from app.services.advanced_prompt_engineer import AdvancedPromptEngineer
        
        engineer = AdvancedPromptEngineer(db=AsyncMock(), cache=AsyncMock())
        
        context_data = {
            "query": "Come calcolare l'IVA per regime forfettario?",
            "regulatory_context": "DL 23/2015 e successive modifiche",
            "user_profile": "Commercialista con 10 anni esperienza",
            "complexity_level": "intermediate"
        }
        
        generated_prompt = await engineer.generate_enhanced_prompt(
            template_id="structured_reasoning_v1",
            context_data=context_data
        )
        
        assert "Come calcolare l'IVA per regime forfettario?" in generated_prompt
        assert "DL 23/2015" in generated_prompt
        assert "Ragionamento Strutturato:" in generated_prompt
        assert len(generated_prompt) > 200  # Substantial content
    
    @pytest.mark.asyncio
    async def test_prompt_quality_metrics(self):
        """Test prompt quality metrics calculation"""
        from app.services.advanced_prompt_engineer import AdvancedPromptEngineer
        
        engineer = AdvancedPromptEngineer(db=AsyncMock(), cache=AsyncMock())
        
        test_prompt = """
        ## Analisi Fiscale IVA
        
        **Domanda:** Calcolo IVA regime forfettario
        **Normativa:** Art. 1, comma 54, L. 190/2014
        
        **Ragionamento:**
        1. Identificazione regime applicabile
        2. Verifica requisiti soggettivi
        3. Calcolo aliquota ridotta
        
        **Conclusione:** Nel regime forfettario non si applica IVA
        """
        
        quality_metrics = await engineer.calculate_prompt_quality(test_prompt)
        
        assert "clarity_score" in quality_metrics
        assert "completeness_score" in quality_metrics
        assert "structure_score" in quality_metrics
        assert quality_metrics["overall_score"] > 0.7
    
    @pytest.mark.asyncio
    async def test_prompt_a_b_testing(self):
        """Test A/B testing of prompt templates"""
        from app.services.advanced_prompt_engineer import AdvancedPromptEngineer
        
        engineer = AdvancedPromptEngineer(db=AsyncMock(), cache=AsyncMock())
        
        # Create two template variants
        template_a = {
            "template_id": str(uuid4()),
            "name": "basic_template",
            "template_text": "Risposta: {answer}",
            "variant": "A"
        }
        
        template_b = {
            "template_id": str(uuid4()),
            "name": "advanced_template",
            "template_text": """
            **Analisi:** {analysis}
            **Normativa:** {regulation}
            **Risposta:** {answer}
            """,
            "variant": "B"
        }
        
        # Test variant selection
        selected_template = await engineer.select_template_variant("fiscal_query")
        
        assert selected_template["variant"] in ["A", "B"]
        assert "template_id" in selected_template
    
    @pytest.mark.asyncio
    async def test_prompt_improvement_based_on_feedback(self, sample_expert_feedback):
        """Test prompt improvement based on expert feedback"""
        from app.services.advanced_prompt_engineer import AdvancedPromptEngineer
        
        engineer = AdvancedPromptEngineer(db=AsyncMock(), cache=AsyncMock())
        
        improvement_data = {
            "template_id": str(uuid4()),
            "feedback_data": [sample_expert_feedback],
            "performance_metrics": {
                "accuracy_score": 0.75,
                "user_satisfaction": 0.65
            }
        }
        
        improved_template = await engineer.improve_template_from_feedback(improvement_data)
        
        assert improved_template["success"] is True
        assert improved_template["improvements_made"] > 0
        assert "enhanced_sections" in improved_template


class TestFailurePatternAnalysis:
    """Test failure pattern analysis system"""
    
    @pytest.mark.asyncio
    async def test_identify_failure_patterns(self, sample_failure_patterns):
        """Test identification of failure patterns from feedback"""
        from app.services.failure_pattern_analyzer import FailurePatternAnalyzer
        
        analyzer = FailurePatternAnalyzer(db=AsyncMock(), ml_service=AsyncMock())
        
        # Mock ML service to return patterns
        analyzer.ml_service.cluster_failures.return_value = sample_failure_patterns
        
        feedback_data = [
            {"category": "normativa_obsoleta", "query": "Regime forfettario 2023"},
            {"category": "normativa_obsoleta", "query": "Detrazioni 2023"},
            {"category": "interpretazione_errata", "query": "Calcolo IRPEF"}
        ]
        
        patterns = await analyzer.identify_patterns(feedback_data)
        
        assert len(patterns) > 0
        assert patterns[0]["pattern_type"] in ["regulatory_outdated", "interpretation_error"]
        assert patterns[0]["frequency"] > 0
        assert patterns[0]["confidence"] > 0.8
    
    @pytest.mark.asyncio
    async def test_categorize_failure_types(self):
        """Test failure type categorization for Italian tax system"""
        from app.services.failure_pattern_analyzer import FailurePatternAnalyzer
        
        analyzer = FailurePatternAnalyzer(db=AsyncMock(), ml_service=AsyncMock())
        
        test_failures = [
            {
                "feedback": "La normativa citata è del 2020, ora è cambiata",
                "category": "normativa_obsoleta",
                "query": "Regime forfettario soglie"
            },
            {
                "feedback": "Il calcolo dell'IRPEF è sbagliato",
                "category": "calcolo_sbagliato", 
                "query": "Scaglioni IRPEF 2024"
            }
        ]
        
        categorized = await analyzer.categorize_failures(test_failures)
        
        assert len(categorized) == 2
        assert categorized[0]["italian_category"] == "normativa_obsoleta"
        assert categorized[1]["italian_category"] == "calcolo_sbagliato"
    
    @pytest.mark.asyncio
    async def test_pattern_clustering_dbscan(self):
        """Test DBSCAN clustering for similar failure patterns"""
        from app.services.failure_pattern_analyzer import FailurePatternAnalyzer
        
        analyzer = FailurePatternAnalyzer(db=AsyncMock(), ml_service=AsyncMock())
        
        # Mock embedding service for semantic similarity
        analyzer.embedding_service = AsyncMock()
        analyzer.embedding_service.embed.return_value = [0.1] * 768  # Mock embedding
        
        failure_texts = [
            "La normativa del regime forfettario è cambiata",
            "Regime forfettario: normativa non aggiornata", 
            "Calcolo IVA errato per professionisti",
            "IVA: errore nel calcolo dell'aliquota"
        ]
        
        clusters = await analyzer.cluster_similar_failures(failure_texts)
        
        assert len(clusters) >= 2  # At least 2 clusters expected
        assert "cluster_0" in clusters
        assert len(clusters["cluster_0"]["items"]) > 0
    
    @pytest.mark.asyncio
    async def test_failure_impact_assessment(self):
        """Test failure impact assessment and prioritization"""
        from app.services.failure_pattern_analyzer import FailurePatternAnalyzer
        
        analyzer = FailurePatternAnalyzer(db=AsyncMock(), ml_service=AsyncMock())
        
        failure_pattern = {
            "pattern_type": "regulatory_outdated",
            "frequency": 25,
            "affected_queries": 150,
            "expert_corrections": 20,
            "user_satisfaction_impact": -0.3
        }
        
        impact_score = await analyzer.assess_failure_impact(failure_pattern)
        
        assert 0.0 <= impact_score <= 1.0
        assert impact_score > 0.7  # High frequency should result in high impact


class TestAutomaticImprovementEngine:
    """Test automatic improvement engine"""
    
    @pytest.mark.asyncio
    async def test_generate_improvement_recommendations(self):
        """Test generation of improvement recommendations"""
        from app.services.automatic_improvement_engine import AutomaticImprovementEngine
        
        engine = AutomaticImprovementEngine(
            db=AsyncMock(),
            prompt_engineer=AsyncMock(),
            pattern_analyzer=AsyncMock()
        )
        
        failure_analysis = {
            "primary_patterns": [
                {
                    "type": "regulatory_outdated",
                    "frequency": 15,
                    "impact": 0.8
                }
            ],
            "affected_areas": ["regime_forfettario", "iva_calculation"],
            "expert_suggestions": [
                "Aggiornare riferimenti normativi",
                "Includere esempi pratici"
            ]
        }
        
        recommendations = await engine.generate_recommendations(failure_analysis)
        
        assert len(recommendations) > 0
        assert "action_type" in recommendations[0]
        assert "priority" in recommendations[0]
        assert recommendations[0]["priority"] in ["high", "medium", "low"]
    
    @pytest.mark.asyncio
    async def test_automatic_prompt_updates(self):
        """Test automatic prompt template updates"""
        from app.services.automatic_improvement_engine import AutomaticImprovementEngine
        
        engine = AutomaticImprovementEngine(
            db=AsyncMock(),
            prompt_engineer=AsyncMock(),
            pattern_analyzer=AsyncMock()
        )
        
        # Mock successful prompt update
        engine.prompt_engineer.update_template.return_value = {
            "success": True,
            "changes_made": ["Added regulatory references", "Enhanced examples"]
        }
        
        update_request = {
            "template_id": str(uuid4()),
            "improvement_type": "regulatory_update",
            "specific_changes": [
                "Update regime forfettario references to 2024",
                "Add new IVA calculation examples"
            ]
        }
        
        result = await engine.apply_automatic_updates(update_request)
        
        assert result["success"] is True
        assert len(result["changes_applied"]) > 0
    
    @pytest.mark.asyncio
    async def test_knowledge_base_updates(self):
        """Test automatic knowledge base updates"""
        from app.services.automatic_improvement_engine import AutomaticImprovementEngine
        
        engine = AutomaticImprovementEngine(
            db=AsyncMock(),
            prompt_engineer=AsyncMock(),
            pattern_analyzer=AsyncMock()
        )
        
        knowledge_update = {
            "category": "regime_forfettario",
            "outdated_content": "Soglia 2023: €65.000",
            "updated_content": "Soglia 2024: €85.000",
            "source": "DL 104/2023",
            "confidence": 0.95
        }
        
        result = await engine.update_knowledge_base(knowledge_update)
        
        assert result["success"] is True
        assert result["updated_items"] > 0
    
    @pytest.mark.asyncio
    async def test_improvement_impact_measurement(self):
        """Test measurement of improvement impact"""
        from app.services.automatic_improvement_engine import AutomaticImprovementEngine
        
        engine = AutomaticImprovementEngine(
            db=AsyncMock(),
            prompt_engineer=AsyncMock(),
            pattern_analyzer=AsyncMock()
        )
        
        # Mock metrics before and after improvement
        before_metrics = {
            "accuracy_score": 0.75,
            "user_satisfaction": 0.70,
            "failure_rate": 0.15
        }
        
        after_metrics = {
            "accuracy_score": 0.85,
            "user_satisfaction": 0.80,
            "failure_rate": 0.08
        }
        
        impact_analysis = await engine.measure_improvement_impact(
            before_metrics,
            after_metrics,
            time_period_days=30
        )
        
        assert impact_analysis["accuracy_improvement"] > 0
        assert impact_analysis["satisfaction_improvement"] > 0
        assert impact_analysis["failure_reduction"] > 0
        assert impact_analysis["overall_success"] is True


class TestExpertValidationWorkflow:
    """Test expert validation workflow"""
    
    @pytest.mark.asyncio
    async def test_expert_qualification_system(self):
        """Test expert qualification and trust scoring"""
        from app.services.expert_validation_workflow import ExpertValidationWorkflow
        
        workflow = ExpertValidationWorkflow(db=AsyncMock(), cache=AsyncMock())
        
        expert_profile = {
            "expert_id": str(uuid4()),
            "credentials": [
                "Dottore Commercialista",
                "Revisore Legale"
            ],
            "experience_years": 15,
            "specializations": ["Fiscalità", "IVA", "Regime forfettario"],
            "feedback_accuracy_history": 0.92,
            "response_time_avg_seconds": 180
        }
        
        trust_score = await workflow.calculate_expert_trust_score(expert_profile)
        
        assert 0.0 <= trust_score <= 1.0
        assert trust_score > 0.8  # Qualified expert should have high trust score
    
    @pytest.mark.asyncio
    async def test_expert_answer_validation(self):
        """Test validation of expert-provided answers"""
        from app.services.expert_validation_workflow import ExpertValidationWorkflow
        
        workflow = ExpertValidationWorkflow(db=AsyncMock(), cache=AsyncMock())
        
        expert_answer = {
            "answer_id": str(uuid4()),
            "expert_id": str(uuid4()),
            "query": "Calcolo IVA regime forfettario 2024",
            "expert_answer": """
            Nel regime forfettario 2024, l'IVA non si applica in base all'art. 1, 
            comma 54, della Legge 190/2014. Il professionista emette fattura 
            senza IVA con dicitura specifica.
            """,
            "regulatory_references": ["L. 190/2014, art. 1, comma 54"],
            "confidence_level": 0.95
        }
        
        validation_result = await workflow.validate_expert_answer(expert_answer)
        
        assert validation_result["is_valid"] is True
        assert validation_result["quality_score"] > 0.8
        assert "regulatory_references" in validation_result
    
    @pytest.mark.asyncio
    async def test_multi_expert_consensus(self):
        """Test multi-expert consensus for complex questions"""
        from app.services.expert_validation_workflow import ExpertValidationWorkflow
        
        workflow = ExpertValidationWorkflow(db=AsyncMock(), cache=AsyncMock())
        
        expert_answers = [
            {
                "expert_id": "expert_1",
                "answer": "IVA non applicabile nel forfettario",
                "confidence": 0.95,
                "trust_score": 0.9
            },
            {
                "expert_id": "expert_2", 
                "answer": "Regime forfettario escluso da IVA",
                "confidence": 0.90,
                "trust_score": 0.85
            },
            {
                "expert_id": "expert_3",
                "answer": "IVA non si applica, art. 1 c.54 L.190/2014",
                "confidence": 0.92,
                "trust_score": 0.88
            }
        ]
        
        consensus_result = await workflow.calculate_expert_consensus(expert_answers)
        
        assert consensus_result["consensus_reached"] is True
        assert consensus_result["consensus_strength"] > 0.8
        assert "final_answer" in consensus_result
    
    @pytest.mark.asyncio
    async def test_expert_feedback_loop(self):
        """Test continuous expert feedback loop"""
        from app.services.expert_validation_workflow import ExpertValidationWorkflow
        
        workflow = ExpertValidationWorkflow(db=AsyncMock(), cache=AsyncMock())
        
        feedback_loop_data = {
            "query_id": str(uuid4()),
            "initial_answer": "Risposta generata automaticamente",
            "expert_corrections": [
                {
                    "expert_id": "expert_1",
                    "correction": "Manca riferimento normativo",
                    "corrected_answer": "Risposta con D.L. 23/2015"
                }
            ],
            "system_learning_applied": True
        }
        
        loop_result = await workflow.process_feedback_loop(feedback_loop_data)
        
        assert loop_result["learning_applied"] is True
        assert "improved_answer" in loop_result
        assert loop_result["expert_satisfaction"] > 0.7


class TestQualityMetricsDashboard:
    """Test quality metrics dashboard"""
    
    @pytest.mark.asyncio
    async def test_quality_metrics_calculation(self):
        """Test calculation of comprehensive quality metrics"""
        from app.services.quality_metrics_dashboard import QualityMetricsDashboard
        
        dashboard = QualityMetricsDashboard(db=AsyncMock(), cache=AsyncMock())
        
        # Mock database queries for metrics
        dashboard.db.execute.return_value.scalars.return_value.all.return_value = [
            {"accuracy": 0.85, "satisfaction": 0.80, "response_time": 250},
            {"accuracy": 0.88, "satisfaction": 0.82, "response_time": 230},
            {"accuracy": 0.90, "satisfaction": 0.85, "response_time": 200}
        ]
        
        metrics = await dashboard.calculate_quality_metrics(
            time_period=timedelta(days=30)
        )
        
        assert "overall_quality_score" in metrics
        assert "accuracy_trend" in metrics
        assert "expert_satisfaction" in metrics
        assert "improvement_velocity" in metrics
        assert metrics["overall_quality_score"] > 0.8
    
    @pytest.mark.asyncio
    async def test_failure_analysis_dashboard(self):
        """Test failure analysis dashboard components"""
        from app.services.quality_metrics_dashboard import QualityMetricsDashboard
        
        dashboard = QualityMetricsDashboard(db=AsyncMock(), cache=AsyncMock())
        
        dashboard_data = await dashboard.get_failure_analysis_dashboard()
        
        assert "failure_categories" in dashboard_data
        assert "trending_issues" in dashboard_data
        assert "expert_intervention_rate" in dashboard_data
        assert "automated_fixes_applied" in dashboard_data
    
    @pytest.mark.asyncio
    async def test_expert_performance_metrics(self):
        """Test expert performance tracking metrics"""
        from app.services.quality_metrics_dashboard import QualityMetricsDashboard
        
        dashboard = QualityMetricsDashboard(db=AsyncMock(), cache=AsyncMock())
        
        expert_metrics = await dashboard.get_expert_performance_metrics(
            expert_id=str(uuid4()),
            time_period=timedelta(days=30)
        )
        
        assert "feedback_count" in expert_metrics
        assert "accuracy_rate" in expert_metrics
        assert "average_response_time" in expert_metrics
        assert "trust_score" in expert_metrics
        assert "specialization_areas" in expert_metrics
    
    @pytest.mark.asyncio
    async def test_system_improvement_tracking(self):
        """Test system improvement tracking over time"""
        from app.services.quality_metrics_dashboard import QualityMetricsDashboard
        
        dashboard = QualityMetricsDashboard(db=AsyncMock(), cache=AsyncMock())
        
        improvement_data = await dashboard.track_system_improvements(
            start_date=datetime.utcnow() - timedelta(days=90),
            end_date=datetime.utcnow()
        )
        
        assert "quality_trend" in improvement_data
        assert "automated_improvements" in improvement_data
        assert "expert_driven_improvements" in improvement_data
        assert "roi_metrics" in improvement_data
    
    @pytest.mark.asyncio
    async def test_real_time_quality_monitoring(self):
        """Test real-time quality monitoring alerts"""
        from app.services.quality_metrics_dashboard import QualityMetricsDashboard
        
        dashboard = QualityMetricsDashboard(db=AsyncMock(), cache=AsyncMock())
        
        # Mock quality degradation scenario
        current_metrics = {
            "accuracy_score": 0.75,  # Below threshold
            "failure_rate": 0.20,    # Above threshold
            "expert_intervention_rate": 0.15
        }
        
        alerts = await dashboard.check_quality_alerts(current_metrics)
        
        assert len(alerts) > 0
        assert any(alert["type"] == "accuracy_degradation" for alert in alerts)
        assert any(alert["priority"] == "high" for alert in alerts)


class TestSystemIntegration:
    """Test integration between all quality analysis components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_quality_workflow(self, sample_expert_feedback):
        """Test complete end-to-end quality analysis workflow"""
        from app.services.quality_analysis_orchestrator import QualityAnalysisOrchestrator
        
        orchestrator = QualityAnalysisOrchestrator(
            feedback_collector=AsyncMock(),
            prompt_engineer=AsyncMock(),
            pattern_analyzer=AsyncMock(),
            improvement_engine=AsyncMock(),
            validation_workflow=AsyncMock(),
            dashboard=AsyncMock()
        )
        
        # Mock successful workflow execution
        workflow_result = await orchestrator.execute_quality_workflow(
            query_id=sample_expert_feedback["query_id"],
            expert_feedback=sample_expert_feedback
        )
        
        assert workflow_result["success"] is True
        assert "feedback_processed" in workflow_result
        assert "patterns_identified" in workflow_result
        assert "improvements_applied" in workflow_result
        assert "validation_completed" in workflow_result
    
    @pytest.mark.asyncio 
    async def test_performance_requirements(self):
        """Test that all components meet performance requirements"""
        from app.services.expert_feedback_collector import ExpertFeedbackCollector
        
        collector = ExpertFeedbackCollector(db=AsyncMock(), cache=AsyncMock())
        
        start_time = time.time()
        
        # Test rapid feedback collection
        for i in range(10):
            feedback_data = {
                "query_id": str(uuid4()),
                "expert_id": str(uuid4()),
                "feedback_type": "correct",
                "time_spent_seconds": 10 + i
            }
            
            result = await collector.collect_feedback(feedback_data)
            assert result["success"] is True
        
        total_time = (time.time() - start_time) * 1000
        
        # Should process 10 feedback items in well under 30 seconds
        assert total_time < 15000  # 15 seconds for batch processing
    
    @pytest.mark.asyncio
    async def test_italian_language_support(self):
        """Test Italian language support across all components"""
        from app.services.expert_feedback_collector import ExpertFeedbackCollector
        
        collector = ExpertFeedbackCollector(db=AsyncMock(), cache=AsyncMock())
        
        italian_feedback = {
            "query_id": str(uuid4()),
            "expert_id": str(uuid4()),
            "feedback_type": "incomplete",
            "category": "normativa_obsoleta", 
            "expert_answer": "La risposta dovrebbe includere il D.L. 104/2023 che ha modificato le soglie del regime forfettario portandole a €85.000",
            "improvement_suggestions": [
                "Aggiornare i riferimenti normativi",
                "Includere la nuova soglia 2024",
                "Specificare l'articolo di legge"
            ]
        }
        
        result = await collector.collect_feedback(italian_feedback)
        
        assert result["success"] is True
        assert "normativa_obsoleta" in result["category"]
        
        # Verify Italian text is properly handled
        assert "D.L. 104/2023" in result.get("expert_answer", "")
    
    @pytest.mark.asyncio
    async def test_scalability_concurrent_requests(self):
        """Test system scalability with concurrent requests"""
        from app.services.expert_feedback_collector import ExpertFeedbackCollector
        
        collector = ExpertFeedbackCollector(db=AsyncMock(), cache=AsyncMock())
        
        # Create 50 concurrent feedback requests
        async def submit_feedback(i):
            feedback_data = {
                "query_id": str(uuid4()),
                "expert_id": str(uuid4()),
                "feedback_type": ["correct", "incomplete", "incorrect"][i % 3],
                "time_spent_seconds": 15 + (i % 30)
            }
            return await collector.collect_feedback(feedback_data)
        
        tasks = [submit_feedback(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert all(result["success"] for result in results)
        assert len(results) == 50


# Performance and benchmarking tests
class TestPerformanceBenchmarks:
    """Performance benchmark tests for quality analysis system"""
    
    @pytest.mark.asyncio
    async def test_feedback_collection_performance(self):
        """Benchmark feedback collection performance"""
        from app.services.expert_feedback_collector import ExpertFeedbackCollector
        
        collector = ExpertFeedbackCollector(db=AsyncMock(), cache=AsyncMock())
        
        # Benchmark single feedback submission
        start_time = time.perf_counter()
        
        feedback_data = {
            "query_id": str(uuid4()),
            "expert_id": str(uuid4()),
            "feedback_type": "incorrect",
            "category": "interpretazione_errata",
            "time_spent_seconds": 45
        }
        
        result = await collector.collect_feedback(feedback_data)
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        assert result["success"] is True
        assert execution_time < 1000  # Under 1 second
        
        print(f"Feedback collection time: {execution_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_pattern_analysis_performance(self):
        """Benchmark pattern analysis performance"""
        from app.services.failure_pattern_analyzer import FailurePatternAnalyzer
        
        analyzer = FailurePatternAnalyzer(db=AsyncMock(), ml_service=AsyncMock())
        
        # Mock large dataset
        feedback_dataset = [
            {
                "category": "normativa_obsoleta",
                "query": f"Query about outdated regulation {i}",
                "feedback": f"Feedback about regulation {i}"
            }
            for i in range(100)  # 100 feedback items
        ]
        
        start_time = time.perf_counter()
        
        patterns = await analyzer.identify_patterns(feedback_dataset)
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        assert len(patterns) >= 0
        assert execution_time < 5000  # Under 5 seconds for 100 items
        
        print(f"Pattern analysis time for 100 items: {execution_time:.2f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])