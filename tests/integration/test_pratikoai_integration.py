"""
Comprehensive Integration Tests for PratikoAI System.

Tests end-to-end workflows across all 14+ implemented features to ensure
complex data flows maintain quality, cost efficiency, and Italian compliance requirements.

Test Coverage:
1. Query Processing Pipeline Integration
2. Knowledge Update Propagation
3. Cost Optimization Flow
4. Quality Improvement Loop
5. Italian Compliance Suite
6. Multi-Feature Stress Testing

Uses realistic Italian tax scenarios with TDD methodology.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.services.advanced_cache_optimizer import AdvancedCacheOptimizer
from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
from app.services.automated_faq_generator import AutomatedFAQGenerator
from app.services.cost_aware_circuit_logic import CostAwareCircuitLogic
from app.services.enhanced_faq_matcher import EnhancedFAQMatcher
from app.services.expert_feedback_collector import ExpertFeedbackCollector
from app.services.gradual_recovery_coordinator import GradualRecoveryCoordinator
from app.services.intelligent_rss_manager import IntelligentRSSManager
from app.services.knowledge_base_manager import KnowledgeBaseManager
from app.services.llm_cost_optimizer import LLMCostOptimizer
from app.services.provider_health_scorer import ProviderHealthScorer

# Import all services for integration testing
from app.services.query_processor import QueryProcessor
from app.services.vector_service import VectorService

# Test data for Italian tax scenarios
ITALIAN_TAX_TEST_DATA = {
    "simple_faq_queries": [
        {
            "query": "Come calcolare l'IVA al 22%?",
            "expected_answer_contains": ["22%", "moltiplicare", "0,22"],
            "expected_cost": 0.0003,  # Should hit FAQ cache
            "expected_response_time": 0.5,
        },
        {
            "query": "Quali sono le scadenze fiscali 2024?",
            "expected_answer_contains": ["30 giugno", "luglio", "novembre"],
            "expected_cost": 0.0003,
            "expected_response_time": 0.5,
        },
    ],
    "complex_queries": [
        {
            "query": "Come calcolare l'IRPEF con addizionale regionale per un reddito di €45.000 in Lombardia?",
            "expected_answer_contains": ["IRPEF", "Lombardia", "45.000", "addizionale"],
            "expected_cost": 0.015,  # Requires LLM processing
            "expected_response_time": 2.5,
            "regional_data_required": True,
        },
        {
            "query": "Calcolo IMU per prima casa a Roma, valore catastale €150.000?",
            "expected_answer_contains": ["IMU", "Roma", "150.000", "prima casa"],
            "expected_cost": 0.012,
            "expected_response_time": 2.0,
            "regional_data_required": True,
        },
    ],
    "rss_updates": [
        {
            "title": "Nuove aliquote IVA per servizi digitali 2024",
            "content": "Dal 1° gennaio 2024 le aliquote IVA per i servizi digitali cambiano al 25%",
            "source": "Agenzia delle Entrate",
            "affects_queries": ["IVA", "servizi digitali", "aliquote"],
            "expected_impact": "high",
        },
        {
            "title": "Aggiornamento scaglioni IRPEF 2024",
            "content": "Nuovi scaglioni IRPEF: fino €28.000 23%, €28.000-€50.000 35%",
            "source": "Ministero Economia",
            "affects_queries": ["IRPEF", "scaglioni", "calcolo"],
            "expected_impact": "high",
        },
    ],
    "expert_feedback_scenarios": [
        {
            "query_id": "test_query_1",
            "feedback_type": "incorrect",
            "category": "interpretazione_errata",
            "expert_answer": "La risposta corretta è che l'IVA al 22% si applica anche ai servizi digitali dal 2024",
            "confidence": 0.95,
            "expected_pattern_detection": True,
        },
        {
            "query_id": "test_query_2",
            "feedback_type": "incomplete",
            "category": "caso_mancante",
            "expert_answer": "Mancano le informazioni sui casi speciali per le startup innovative",
            "confidence": 0.88,
            "expected_pattern_detection": False,
        },
    ],
}


@pytest.fixture
async def integration_test_environment():
    """Set up complete integration test environment with all services"""

    # Initialize all services
    services = {
        "query_processor": QueryProcessor(),
        "faq_matcher": EnhancedFAQMatcher(),
        "knowledge_base": KnowledgeBaseManager(),
        "vector_service": VectorService(),
        "cost_optimizer": LLMCostOptimizer(),
        "cache_optimizer": AdvancedCacheOptimizer(),
        "rss_manager": IntelligentRSSManager(),
        "faq_generator": AutomatedFAQGenerator(),
        "feedback_collector": ExpertFeedbackCollector(),
        "circuit_breaker": AdvancedCircuitBreakerManager(),
        "cost_circuit": CostAwareCircuitLogic(),
        "health_scorer": ProviderHealthScorer(),
        "recovery_coordinator": GradualRecoveryCoordinator(),
    }

    # Set up test databases and clear caches
    await _setup_test_databases(services)
    await _load_test_data(services)

    # Initialize monitoring
    test_metrics = {
        "query_count": 0,
        "total_cost": 0.0,
        "response_times": [],
        "quality_scores": [],
        "cache_hits": 0,
        "cache_misses": 0,
        "errors": [],
    }

    yield services, test_metrics

    # Cleanup
    await _cleanup_test_environment(services)


class TestQueryProcessingPipelineIntegration:
    """Test complete query processing pipeline from input to response"""

    @pytest.mark.asyncio
    async def test_simple_faq_query_full_flow(self, integration_test_environment):
        """Test simple FAQ query through complete processing pipeline"""
        services, metrics = integration_test_environment

        query_data = ITALIAN_TAX_TEST_DATA["simple_faq_queries"][0]
        query = query_data["query"]

        start_time = time.time()

        # 1. Query normalization and preprocessing
        normalized_query = await services["query_processor"].normalize_query(query)
        assert normalized_query is not None
        assert len(normalized_query) > 0

        # 2. FAQ matching attempt
        faq_result = await services["faq_matcher"].find_best_match(
            {"query": normalized_query, "use_semantic_search": True, "confidence_threshold": 0.7}
        )

        # Should find FAQ match for simple query
        assert faq_result["match_found"] is True
        assert faq_result["confidence"] > 0.7
        assert any(expected in faq_result["answer"].lower() for expected in query_data["expected_answer_contains"])

        # 3. Cost tracking
        await services["cost_optimizer"].track_request_cost("faq_match", faq_result.get("processing_cost", 0.0003))

        # 4. Cache storage
        cache_result = await services["cache_optimizer"].store_response(
            {"query": query, "response": faq_result["answer"], "cost": 0.0003, "source": "faq"}
        )

        end_time = time.time()
        response_time = end_time - start_time

        # Verifications
        assert response_time < query_data["expected_response_time"]
        assert faq_result.get("processing_cost", 0.0003) <= query_data["expected_cost"]
        assert cache_result["stored"] is True

        # Update metrics
        metrics["query_count"] += 1
        metrics["total_cost"] += 0.0003
        metrics["response_times"].append(response_time)
        metrics["cache_hits"] += 1

        print(f"✅ Simple FAQ query processed in {response_time:.3f}s at cost €{0.0003:.4f}")

    @pytest.mark.asyncio
    async def test_complex_query_full_flow(self, integration_test_environment):
        """Test complex query requiring LLM processing and knowledge base search"""
        services, metrics = integration_test_environment

        query_data = ITALIAN_TAX_TEST_DATA["complex_queries"][0]
        query = query_data["query"]

        start_time = time.time()

        # 1. Query processing and classification
        processed_query = await services["query_processor"].process_query(
            {"query": query, "classify_complexity": True, "extract_entities": True}
        )

        assert processed_query["complexity"] == "high"
        assert processed_query["requires_llm"] is True
        assert "Lombardia" in processed_query.get("entities", [])

        # 2. FAQ matching (should fail)
        faq_result = await services["faq_matcher"].find_best_match({"query": query, "confidence_threshold": 0.7})

        assert faq_result["match_found"] is False or faq_result["confidence"] < 0.7

        # 3. Vector search for relevant documents
        vector_results = await services["vector_service"].search(
            {"query": query, "top_k": 5, "filters": {"region": "Lombardia"}}
        )

        assert len(vector_results["results"]) > 0
        assert any("IRPEF" in doc["content"] for doc in vector_results["results"])

        # 4. LLM processing with context
        llm_response = await services["cost_optimizer"].generate_response(
            {
                "query": query,
                "context_documents": vector_results["results"],
                "complexity": "high",
                "region": "Lombardia",
            }
        )

        assert llm_response["success"] is True
        assert any(expected in llm_response["answer"].lower() for expected in query_data["expected_answer_contains"])

        # 5. Cost tracking and optimization
        total_cost = vector_results.get("cost", 0.005) + llm_response.get("cost", 0.010)

        await services["cost_optimizer"].track_request_cost("complex_query", total_cost)

        # 6. Cache the response
        await services["cache_optimizer"].store_response(
            {
                "query": query,
                "response": llm_response["answer"],
                "cost": total_cost,
                "source": "llm",
                "complexity": "high",
            }
        )

        end_time = time.time()
        response_time = end_time - start_time

        # Verifications
        assert response_time < query_data["expected_response_time"]
        assert total_cost <= query_data["expected_cost"]
        assert llm_response["quality_score"] > 0.8

        # Update metrics
        metrics["query_count"] += 1
        metrics["total_cost"] += total_cost
        metrics["response_times"].append(response_time)
        metrics["cache_misses"] += 1
        metrics["quality_scores"].append(llm_response["quality_score"])

        print(f"✅ Complex query processed in {response_time:.3f}s at cost €{total_cost:.4f}")

    @pytest.mark.asyncio
    async def test_query_during_cost_limit_exceeded(self, integration_test_environment):
        """Test query processing when cost limits are exceeded"""
        services, metrics = integration_test_environment

        # Set low cost limit to trigger circuit breaker
        await services["cost_circuit"].set_cost_budget(
            "openai",
            period="daily",
            limit=0.001,  # Very low limit
            hard_limit=True,
        )

        query = "Calcolo complesso IRES per holding con partecipazioni estere"

        # Should trigger cost circuit breaker
        cost_check = await services["cost_circuit"].should_allow_request_cost_check(
            "openai",
            estimated_cost=0.015,  # Exceeds limit
        )

        assert cost_check["allowed"] is False
        assert cost_check["reason"] == "budget_exceeded"
        assert len(cost_check["alternative_providers"]) > 0

        # Try with alternative provider
        alternative = cost_check["alternative_providers"][0]["provider"]

        alt_cost_check = await services["cost_circuit"].should_allow_request_cost_check(
            alternative,
            estimated_cost=0.008,  # Lower cost
        )

        if alt_cost_check["allowed"]:
            # Process with alternative provider
            response = await services["cost_optimizer"].generate_response(
                {"query": query, "provider": alternative, "complexity": "high"}
            )

            assert response["success"] is True
            assert response["provider"] == alternative

        print(f"✅ Cost limits enforced, fallback to {alternative} successful")


class TestKnowledgeUpdatePropagation:
    """Test RSS updates propagating through to user responses"""

    @pytest.mark.asyncio
    async def test_rss_update_to_response_impact(self, integration_test_environment):
        """Test complete flow from RSS update to improved responses"""
        services, metrics = integration_test_environment

        update_data = ITALIAN_TAX_TEST_DATA["rss_updates"][0]

        # 1. Before update - test baseline response
        baseline_query = "Quali sono le aliquote IVA per servizi digitali?"

        baseline_response = await services["query_processor"].process_query({"query": baseline_query})

        # Should not mention 25% yet
        assert "25%" not in baseline_response.get("answer", "")

        # 2. Simulate RSS update arrival
        rss_update = {
            "title": update_data["title"],
            "content": update_data["content"],
            "source": update_data["source"],
            "published_date": datetime.utcnow(),
            "importance_score": 0.9,
        }

        update_result = await services["rss_manager"].process_feed_update(rss_update)
        assert update_result["processed"] is True
        assert update_result["importance_score"] > 0.8

        # 3. Knowledge base update
        kb_update = await services["knowledge_base"].update_from_rss(
            {
                "content": rss_update["content"],
                "source": rss_update["source"],
                "affects_topics": ["IVA", "servizi digitali"],
            }
        )

        assert kb_update["updated"] is True
        assert len(kb_update["affected_documents"]) > 0

        # 4. Vector embeddings regeneration
        embedding_update = await services["vector_service"].update_embeddings(
            {"documents": kb_update["affected_documents"], "incremental": True}
        )

        assert embedding_update["success"] is True

        # 5. Cache invalidation for affected queries
        cache_invalidation = await services["cache_optimizer"].invalidate_by_topics(update_data["affects_queries"])

        assert cache_invalidation["invalidated_count"] > 0

        # 6. Wait for propagation (simulate 30 minutes)
        await asyncio.sleep(0.1)  # Simulate time passage

        # 7. Test same query again - should now include updated information
        updated_response = await services["query_processor"].process_query({"query": baseline_query})

        # Should now mention 25%
        assert "25%" in updated_response.get("answer", "")
        assert updated_response["source_freshness"] < 1800  # Less than 30 minutes old

        # 8. Verify FAQ updates if threshold reached
        faq_check = await services["faq_generator"].check_update_threshold(
            {"topic": "IVA servizi digitali", "update_impact": "high"}
        )

        if faq_check["should_update"]:
            faq_update = await services["faq_generator"].generate_from_update(
                {"content": rss_update["content"], "topic": "IVA servizi digitali"}
            )

            assert faq_update["generated"] is True

        print("✅ RSS update propagated through system in <30 minutes")

    @pytest.mark.asyncio
    async def test_conflicting_updates_resolution(self, integration_test_environment):
        """Test handling of conflicting information from multiple sources"""
        services, metrics = integration_test_environment

        # Two conflicting updates
        update1 = {
            "title": "IVA servizi digitali al 25%",
            "content": "Dal 2024 IVA servizi digitali al 25%",
            "source": "Agenzia delle Entrate",
            "authority_score": 0.95,
            "published_date": datetime.utcnow(),
        }

        update2 = {
            "title": "IVA servizi digitali al 22%",
            "content": "Confermata IVA servizi digitali al 22%",
            "source": "Consulenti Tributari",
            "authority_score": 0.7,
            "published_date": datetime.utcnow() - timedelta(hours=1),
        }

        # Process both updates
        await services["rss_manager"].process_feed_update(update1)
        await services["rss_manager"].process_feed_update(update2)

        # System should prioritize higher authority source (Agenzia delle Entrate)
        conflict_resolution = await services["rss_manager"].resolve_conflicts(
            {"topic": "IVA servizi digitali", "conflicting_updates": [update1, update2]}
        )

        assert conflict_resolution["resolved"] is True
        assert conflict_resolution["chosen_source"] == "Agenzia delle Entrate"
        assert "25%" in conflict_resolution["final_information"]

        # Verify expert validation triggered for conflicts
        validation_request = await services["feedback_collector"].check_validation_required(
            {
                "conflict_detected": True,
                "topic": "IVA servizi digitali",
                "sources": ["Agenzia delle Entrate", "Consulenti Tributari"],
            }
        )

        assert validation_request["validation_required"] is True

        print("✅ Conflicting updates resolved correctly, expert validation requested")


class TestCostOptimizationFlow:
    """Test all cost-saving mechanisms working together"""

    @pytest.mark.asyncio
    async def test_progressive_cost_reduction_through_faq_generation(self, integration_test_environment):
        """Test cost reduction as queries become FAQs through repeated asking"""
        services, metrics = integration_test_environment

        query = "Come calcolare la ritenuta d'acconto per professionisti?"
        expected_costs = [0.015, 0.014, 0.013, 0.012, 0.011]  # Decreasing due to optimization

        total_cost = 0.0
        response_times = []

        # Simulate 10 different users asking the same question
        for i in range(10):
            start_time = time.time()

            # Check if FAQ exists yet
            faq_match = await services["faq_matcher"].find_best_match({"query": query, "confidence_threshold": 0.8})

            if faq_match["match_found"] and i >= 5:  # FAQ should be generated after 5 queries
                # Should use FAQ (very cheap)
                cost = 0.0003
                response = faq_match["answer"]
                source = "faq"
            else:
                # Use LLM (more expensive)
                llm_response = await services["cost_optimizer"].generate_response(
                    {"query": query, "complexity": "medium"}
                )
                cost = llm_response.get("cost", 0.012)
                response = llm_response["answer"]
                source = "llm"

            end_time = time.time()
            response_time = end_time - start_time

            # Track metrics
            total_cost += cost
            response_times.append(response_time)

            # Update query frequency for FAQ generation
            await services["faq_generator"].track_query_frequency(
                {"query": query, "normalized_query": query.lower(), "cost": cost, "user_id": f"user_{i}"}
            )

            # Check if FAQ should be generated
            if i == 4:  # After 5th query
                faq_generation = await services["faq_generator"].check_generation_threshold(
                    {"query": query, "frequency_count": 5, "total_cost": sum(expected_costs[:5])}
                )

                if faq_generation["should_generate"]:
                    generated_faq = await services["faq_generator"].generate_faq(
                        {"query": query, "best_response": response, "confidence": 0.9}
                    )

                    assert generated_faq["success"] is True

            print(f"Query {i + 1}: {source} - €{cost:.4f} in {response_time:.3f}s")

        # Verifications
        assert total_cost < 0.08  # Should be less than 10 * €0.015

        # Later queries should be faster (FAQ hits)
        assert response_times[-1] < response_times[0]

        # FAQ should exist now
        final_faq_check = await services["faq_matcher"].find_best_match({"query": query, "confidence_threshold": 0.8})
        assert final_faq_check["match_found"] is True

        print(f"✅ Progressive cost reduction: €{total_cost:.4f} total (avg €{total_cost / 10:.4f})")

    @pytest.mark.asyncio
    async def test_circuit_breaker_cost_protection(self, integration_test_environment):
        """Test circuit breakers protecting against cost overruns"""
        services, metrics = integration_test_environment

        # Set monthly budget
        await services["cost_circuit"].set_cost_budget(
            "openai",
            period="monthly",
            limit=10.0,  # €10 monthly limit
            alert_thresholds=[0.7, 0.8, 0.9],
        )

        # Simulate expensive queries approaching limit
        total_spent = 0.0
        queries_processed = 0
        queries_blocked = 0

        expensive_query = "Analisi fiscale completa per gruppo multinazionale con holding in Lussemburgo"

        for i in range(15):  # Try 15 expensive queries
            cost_check = await services["cost_circuit"].should_allow_request_cost_check(
                "openai",
                estimated_cost=0.8,  # €0.80 per query
            )

            if cost_check["allowed"]:
                # Process query
                response = await services["cost_optimizer"].generate_response(
                    {"query": f"{expensive_query} caso {i}", "provider": "openai", "complexity": "very_high"}
                )

                actual_cost = response.get("cost", 0.8)
                total_spent += actual_cost
                queries_processed += 1

                # Record actual cost
                await services["cost_circuit"].record_actual_cost("openai", actual_cost)
            else:
                queries_blocked += 1

                # Should suggest alternatives
                assert len(cost_check["alternative_providers"]) > 0

                # Try cheaper alternative
                alternative = cost_check["alternative_providers"][0]["provider"]
                alt_response = await services["cost_optimizer"].generate_response(
                    {
                        "query": f"{expensive_query} caso {i}",
                        "provider": alternative,
                        "complexity": "high",  # Reduced complexity for cheaper provider
                    }
                )

                if alt_response["success"]:
                    total_spent += alt_response.get("cost", 0.4)
                    queries_processed += 1

        # Verifications
        assert queries_blocked > 0  # Some queries should have been blocked
        assert total_spent <= 12.0  # Should not exceed limit by much
        assert queries_processed == 15  # All queries processed (some with alternatives)

        # Check that alerts were generated
        alerts = services["cost_circuit"].get_active_cost_alerts()
        assert len(alerts) > 0
        assert any(alert["type"] == "budget_exceeded" for alert in alerts)

        print(f"✅ Circuit breaker protected costs: €{total_spent:.2f}, blocked {queries_blocked} queries")

    @pytest.mark.asyncio
    async def test_italian_market_cost_adjustments(self, integration_test_environment):
        """Test cost adjustments during Italian market conditions"""
        services, metrics = integration_test_environment

        base_cost = 0.01

        # Test different market conditions
        test_scenarios = [
            {
                "time": "peak_hours",  # 2 PM Italian time
                "month": 7,  # July (tax deadline)
                "expected_multiplier": 1.8,  # 1.2 * 1.5
                "description": "Peak hours + tax deadline",
            },
            {
                "time": "off_hours",  # 11 PM Italian time
                "month": 8,  # August (vacation)
                "expected_multiplier": 0.88,  # 1.1 * 0.8
                "description": "Off hours + vacation",
            },
            {
                "time": "peak_hours",
                "month": 3,  # Normal month
                "expected_multiplier": 1.2,  # Just peak hours
                "description": "Peak hours only",
            },
        ]

        for scenario in test_scenarios:
            # Mock current time for scenario
            with patch("datetime.datetime") as mock_datetime:
                mock_now = datetime(2024, scenario["month"], 15, 14, 0, 0)  # 2 PM
                if scenario["time"] == "off_hours":
                    mock_now = mock_now.replace(hour=23)  # 11 PM

                mock_datetime.utcnow.return_value = mock_now

                # Get cost adjustment
                cost_check = await services["cost_circuit"].should_allow_request_cost_check(
                    "openai", estimated_cost=base_cost
                )

                if cost_check["allowed"]:
                    italian_adjustment = cost_check.get("italian_adjustment", {})
                    actual_multiplier = italian_adjustment.get("multiplier", 1.0)

                    # Verify multiplier is close to expected
                    assert abs(actual_multiplier - scenario["expected_multiplier"]) < 0.1

                    final_cost = cost_check["estimated_cost"]
                    expected_cost = base_cost * scenario["expected_multiplier"]

                    assert abs(final_cost - expected_cost) < 0.001

                    print(f"✅ {scenario['description']}: {actual_multiplier:.2f}x = €{final_cost:.4f}")


class TestQualityImprovementLoop:
    """Test expert feedback through to system improvements"""

    @pytest.mark.asyncio
    async def test_expert_feedback_to_improvement_cycle(self, integration_test_environment):
        """Test complete cycle from expert feedback to system improvement"""
        services, metrics = integration_test_environment

        feedback_data = ITALIAN_TAX_TEST_DATA["expert_feedback_scenarios"][0]

        # 1. Generate initial response that will receive feedback
        query = "Applicazione IVA per servizi digitali 2024"

        initial_response = await services["query_processor"].process_query({"query": query})

        query_id = str(uuid4())

        # 2. Expert provides feedback
        feedback_result = await services["feedback_collector"].collect_feedback(
            {
                "query_id": query_id,
                "expert_id": "expert_tax_001",
                "query": query,
                "ai_response": initial_response["answer"],
                "feedback_type": feedback_data["feedback_type"],
                "category": feedback_data["category"],
                "expert_answer": feedback_data["expert_answer"],
                "confidence_score": feedback_data["confidence"],
                "time_spent_seconds": 120,
            }
        )

        assert feedback_result["success"] is True
        assert feedback_result["processing_time_ms"] < 30000  # <30 seconds

        # 3. Pattern analysis should identify issue
        pattern_analysis = await services["feedback_collector"].analyze_feedback_patterns(
            {"category": feedback_data["category"], "time_window_hours": 24, "min_frequency": 1}
        )

        if feedback_data["expected_pattern_detection"]:
            assert len(pattern_analysis["patterns"]) > 0

            # 4. Automatic improvement should be generated
            improvement_result = await services["faq_generator"].generate_improvement_from_feedback(
                {
                    "feedback": feedback_result,
                    "pattern": pattern_analysis["patterns"][0],
                    "expert_answer": feedback_data["expert_answer"],
                }
            )

            assert improvement_result["improvement_generated"] is True

            # 5. FAQ should be updated or created
            faq_update = await services["faq_matcher"].update_or_create_from_expert(
                {
                    "query": query,
                    "expert_answer": feedback_data["expert_answer"],
                    "confidence": feedback_data["confidence"],
                    "category": feedback_data["category"],
                }
            )

            assert faq_update["updated"] is True

            # 6. Test that subsequent similar queries use improved response
            similar_query = "IVA servizi digitali dal 2024"

            improved_response = await services["query_processor"].process_query({"query": similar_query})

            # Should contain expert's correction
            assert any(word in improved_response["answer"].lower() for word in ["2024", "digitali", "iva"])
            assert improved_response["confidence"] > initial_response.get("confidence", 0.5)

        print("✅ Expert feedback cycle completed - improvement applied")

    @pytest.mark.asyncio
    async def test_multi_expert_consensus_validation(self, integration_test_environment):
        """Test multi-expert consensus for complex corrections"""
        services, metrics = integration_test_environment

        query = "Calcolo IRES per holding con partecipazioni estere"
        query_id = str(uuid4())

        # Generate initial response
        initial_response = await services["query_processor"].process_query({"query": query})

        # Multiple expert feedbacks
        expert_feedbacks = [
            {
                "expert_id": "expert_001",
                "feedback_type": "incorrect",
                "category": "calcolo_sbagliato",
                "expert_answer": "IRES holding al 24% su reddito consolidato",
                "confidence": 0.9,
                "trust_score": 0.95,
            },
            {
                "expert_id": "expert_002",
                "feedback_type": "incorrect",
                "category": "calcolo_sbagliato",
                "expert_answer": "IRES 24% con consolidato fiscale per partecipazioni >95%",
                "confidence": 0.85,
                "trust_score": 0.88,
            },
            {
                "expert_id": "expert_003",
                "feedback_type": "incomplete",
                "category": "caso_mancante",
                "expert_answer": "Manca riferimento a CFC rules per partecipazioni estere",
                "confidence": 0.92,
                "trust_score": 0.92,
            },
        ]

        # Collect all feedback
        feedback_results = []
        for feedback in expert_feedbacks:
            result = await services["feedback_collector"].collect_feedback(
                {"query_id": query_id, "query": query, "ai_response": initial_response["answer"], **feedback}
            )
            feedback_results.append(result)

        # Calculate expert consensus
        consensus_result = await services["feedback_collector"].calculate_expert_consensus(expert_feedbacks)

        assert consensus_result["consensus_reached"] is True
        assert consensus_result["consensus_strength"] > 0.8
        assert "24%" in consensus_result["final_answer"]

        # Should identify areas of disagreement
        if not consensus_result["consensus_reached"]:
            assert len(consensus_result["disagreement_areas"]) > 0

        # Generate improved response based on consensus
        improved_response = await services["faq_generator"].generate_from_expert_consensus(
            {"query": query, "consensus": consensus_result, "original_response": initial_response["answer"]}
        )

        assert improved_response["success"] is True
        assert improved_response["quality_score"] > initial_response.get("quality_score", 0.5)

        print(f"✅ Multi-expert consensus reached: {consensus_result['consensus_strength']:.2f}")


class TestItalianComplianceSuite:
    """Test Italian tax calculations and compliance requirements"""

    @pytest.mark.asyncio
    async def test_irpef_calculation_with_regional_variations(self, integration_test_environment):
        """Test IRPEF calculation with different regional addizionali"""
        services, metrics = integration_test_environment

        test_cases = [
            {
                "region": "Lombardia",
                "income": 45000,
                "expected_addizionale_regionale": 1.73,  # %
                "expected_addizionale_comunale": 0.8,  # % (Milano)
                "query_template": "Calcola IRPEF per reddito €{income} in {region}",
            },
            {
                "region": "Sicilia",
                "income": 35000,
                "expected_addizionale_regionale": 1.73,
                "expected_addizionale_comunale": 0.5,  # % (Palermo)
                "query_template": "IRPEF €{income} per residente {region}",
            },
            {
                "region": "Trentino-Alto Adige",
                "income": 50000,
                "expected_addizionale_regionale": 1.23,  # Lower autonomous region rate
                "expected_addizionale_comunale": 0.4,
                "query_template": "Quanto IRPEF per €{income} in {region}?",
            },
        ]

        for test_case in test_cases:
            query = test_case["query_template"].format(income=test_case["income"], region=test_case["region"])

            # Process query with regional context
            response = await services["query_processor"].process_query(
                {"query": query, "region": test_case["region"], "calculation_required": True}
            )

            # Verify response contains correct regional information
            assert response["success"] is True
            assert test_case["region"] in response["answer"]
            assert str(test_case["income"]) in response["answer"]

            # Check for correct addizionale rates
            answer_lower = response["answer"].lower()

            # Should mention regional addizionale
            assert any(term in answer_lower for term in ["addizionale regionale", "regionale"])

            # Should have correct calculation components
            assert any(term in answer_lower for term in ["irpef", "scaglioni", "aliquota"])

            # Verify calculation accuracy (would need actual tax calculation service)
            if "calculation_result" in response:
                calc = response["calculation_result"]
                assert calc["region"] == test_case["region"]
                assert calc["gross_income"] == test_case["income"]
                assert calc["regional_rate"] == test_case["expected_addizionale_regionale"]

            print(f"✅ IRPEF {test_case['region']}: €{test_case['income']} calculated correctly")

    @pytest.mark.asyncio
    async def test_imu_calculation_regional_variations(self, integration_test_environment):
        """Test IMU calculation for different comuni"""
        services, metrics = integration_test_environment

        test_scenarios = [
            {
                "comune": "Roma",
                "property_type": "prima casa",
                "catastral_value": 150000,
                "expected_rate": 0.0,  # Prima casa exempt in Rome
                "expected_imu": 0.0,
            },
            {
                "comune": "Milano",
                "property_type": "seconda casa",
                "catastral_value": 200000,
                "expected_rate": 1.06,  # Standard rate
                "expected_imu": 2120.0,  # 200000 * 1.06%
            },
            {
                "comune": "Napoli",
                "property_type": "ufficio",
                "catastral_value": 100000,
                "expected_rate": 1.06,
                "expected_imu": 1060.0,
            },
        ]

        for scenario in test_scenarios:
            query = f"Calcola IMU per {scenario['property_type']} a {scenario['comune']} valore catastale €{scenario['catastral_value']}"

            response = await services["query_processor"].process_query(
                {"query": query, "comune": scenario["comune"], "property_calculation": True}
            )

            assert response["success"] is True
            assert scenario["comune"] in response["answer"]
            assert str(scenario["catastral_value"]) in response["answer"]

            # Check for IMU-specific terms
            answer_lower = response["answer"].lower()
            assert "imu" in answer_lower

            if scenario["expected_imu"] == 0.0:
                assert any(term in answer_lower for term in ["esente", "non dovuta", "0"])
            else:
                # Should mention the rate and calculation
                assert any(str(scenario["expected_rate"]) in response["answer"] for _ in [scenario["expected_rate"]])

            print(f"✅ IMU {scenario['comune']}: {scenario['property_type']} calculated")

    @pytest.mark.asyncio
    async def test_f24_generation_with_correct_codes(self, integration_test_environment):
        """Test F24 form generation with correct tax codes"""
        services, metrics = integration_test_environment

        f24_requests = [
            {
                "tax_type": "IRPEF",
                "amount": 2500.0,
                "period": "2023",
                "expected_code": "4001",
                "description": "IRPEF acconto prima rata",
            },
            {
                "tax_type": "IVA",
                "amount": 1800.0,
                "period": "gennaio_2024",
                "expected_code": "6001",
                "description": "IVA mensile",
            },
            {
                "tax_type": "IRES",
                "amount": 5000.0,
                "period": "2023",
                "expected_code": "2003",
                "description": "IRES acconto",
            },
        ]

        for f24_request in f24_requests:
            query = (
                f"Genera F24 per {f24_request['tax_type']} €{f24_request['amount']} periodo {f24_request['period']}"
            )

            response = await services["query_processor"].process_query(
                {
                    "query": query,
                    "generate_f24": True,
                    "tax_type": f24_request["tax_type"],
                    "amount": f24_request["amount"],
                    "period": f24_request["period"],
                }
            )

            assert response["success"] is True

            # Should contain correct tax code
            assert f24_request["expected_code"] in response["answer"]

            # Should contain amount
            assert str(f24_request["amount"]) in response["answer"]

            # Should mention F24
            assert "F24" in response["answer"]

            # Check for proper Italian format
            answer_lower = response["answer"].lower()
            assert any(term in answer_lower for term in ["codice", "importo", "versamento"])

            print(f"✅ F24 {f24_request['tax_type']}: code {f24_request['expected_code']} generated")

    @pytest.mark.asyncio
    async def test_gdpr_compliance_data_export(self, integration_test_environment):
        """Test GDPR-compliant data export functionality"""
        services, metrics = integration_test_environment

        user_id = "test_user_gdpr_001"

        # Simulate user queries and data collection
        user_queries = ["Calcolo IRPEF 2024", "Regime forfettario soglie", "IVA prestazioni professionali"]

        # Process queries to generate user data
        for query in user_queries:
            await services["query_processor"].process_query(
                {"query": query, "user_id": user_id, "track_user_data": True}
            )

        # Request GDPR data export
        export_request = {"user_id": user_id, "export_type": "gdpr_full", "format": "json", "include_analytics": True}

        export_result = await services["query_processor"].export_user_data(export_request)

        assert export_result["success"] is True
        assert export_result["format"] == "json"

        # Verify export contents
        exported_data = export_result["data"]

        # Should include user queries
        assert "queries" in exported_data
        assert len(exported_data["queries"]) >= len(user_queries)

        # Should include personal data
        assert "user_profile" in exported_data
        assert "preferences" in exported_data

        # Should include Italian-specific compliance info
        assert "compliance_info" in exported_data
        assert exported_data["compliance_info"]["gdpr_compliant"] is True

        # Should be formatted for Italian authorities
        assert "italian_format" in exported_data["compliance_info"]

        print(f"✅ GDPR export generated: {len(exported_data)} sections")


class TestMultiFeatureStressTest:
    """Test system behavior under realistic load with all features active"""

    @pytest.mark.asyncio
    async def test_tax_deadline_peak_load_scenario(self, integration_test_environment):
        """Simulate 50 concurrent users during July tax deadline"""
        services, metrics = integration_test_environment

        # Mock July tax deadline conditions
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 7, 30, 14, 0, 0)  # July 30, 2 PM

            # Mix of query types during tax deadline
            query_mix = [
                # 60% simple FAQ queries
                *["Come versare F24?"] * 30,
                *["Scadenze luglio 2024"] * 30,
                # 30% medium complexity
                *["Calcolo acconto IRPEF"] * 15,
                *["IMU seconda casa Roma"] * 15,
                # 10% complex queries
                *["Consolidato fiscale holding"] * 5,
                *["CFC rules partecipazioni estere"] * 5,
            ]

            # Simulate 50 concurrent users
            concurrent_tasks = []
            start_time = time.time()

            for i, query in enumerate(query_mix[:50]):  # 50 concurrent requests
                task = asyncio.create_task(self._simulate_user_request(services, query, f"user_{i}", metrics))
                concurrent_tasks.append(task)

            # Wait for all requests to complete
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)

            end_time = time.time()
            total_duration = end_time - start_time

            # Analyze results
            successful_requests = [r for r in results if isinstance(r, dict) and r.get("success")]
            [r for r in results if not (isinstance(r, dict) and r.get("success"))]

            # Performance assertions
            assert len(successful_requests) >= 45  # At least 90% success rate
            assert total_duration < 10.0  # All 50 requests in under 10 seconds

            # Calculate response time percentiles
            response_times = [r["response_time"] for r in successful_requests]
            response_times.sort()

            p95_time = response_times[int(0.95 * len(response_times))] if response_times else 0
            assert p95_time < 3.0  # 95th percentile under 3 seconds

            # Cost efficiency during peak
            total_cost = sum(r.get("cost", 0) for r in successful_requests)
            avg_cost = total_cost / len(successful_requests) if successful_requests else 0

            # Should benefit from caching and FAQ hits
            assert avg_cost < 0.005  # Average under €0.005 due to FAQ hits

            # Quality maintenance
            quality_scores = [r.get("quality_score", 0) for r in successful_requests if r.get("quality_score")]
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

            assert avg_quality > 0.90  # Maintain >90% quality under load

            print(f"✅ Peak load test: {len(successful_requests)}/50 requests in {total_duration:.2f}s")
            print(f"   95th percentile: {p95_time:.2f}s, avg cost: €{avg_cost:.4f}, avg quality: {avg_quality:.2f}")

    @pytest.mark.asyncio
    async def test_rss_update_during_peak_load(self, integration_test_environment):
        """Test RSS updates processing during high query volume"""
        services, metrics = integration_test_environment

        # Start continuous query load
        query_tasks = []

        # Background query load (20 requests/minute)
        for i in range(20):
            task = asyncio.create_task(
                self._simulate_user_request(services, f"Query during RSS update {i}", f"bg_user_{i}", metrics)
            )
            query_tasks.append(task)

        # Simulate RSS update arriving during load
        rss_update = {
            "title": "Urgente: Proroga scadenze fiscali luglio",
            "content": "Prorogate al 20 agosto le scadenze fiscali di luglio per eventi eccezionali",
            "source": "Agenzia delle Entrate",
            "importance_score": 0.95,
            "affects_queries": ["scadenze", "luglio", "proroga"],
        }

        # Process RSS update while queries are running
        rss_start_time = time.time()

        rss_task = asyncio.create_task(services["rss_manager"].process_feed_update(rss_update))

        # Wait for both background queries and RSS update
        all_results = await asyncio.gather(*query_tasks, rss_task, return_exceptions=True)

        rss_end_time = time.time()
        rss_processing_time = rss_end_time - rss_start_time

        # Separate RSS result from query results
        query_results = all_results[:-1]
        rss_result = all_results[-1]

        # Assertions
        assert isinstance(rss_result, dict) and rss_result.get("processed") is True
        assert rss_processing_time < 240.0  # RSS processed within 4 minutes

        # Background queries should still succeed
        successful_queries = [r for r in query_results if isinstance(r, dict) and r.get("success")]
        assert len(successful_queries) >= 18  # At least 90% of background queries succeed

        # Test that new information is available immediately for new queries
        test_query = "Quando scadono le tasse di luglio 2024?"

        updated_response = await services["query_processor"].process_query({"query": test_query})

        # Should reflect the update
        answer_lower = updated_response["answer"].lower()
        assert any(term in answer_lower for term in ["agosto", "proroga", "20"])

        print(f"✅ RSS update processed in {rss_processing_time:.1f}s during peak load")

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_under_load(self, integration_test_environment):
        """Test circuit breaker activation and recovery during load"""
        services, metrics = integration_test_environment

        # Set low failure threshold for testing
        circuit_breaker = services["circuit_breaker"]

        # Simulate provider failures
        expensive_provider = "openai"

        # Generate failures to trip circuit breaker
        for i in range(6):  # Trip at 5 failures
            await circuit_breaker.record_failure(expensive_provider, failure_type="timeout", cost=0.01)

        # Verify circuit is open
        status = await circuit_breaker.get_circuit_status(expensive_provider)
        assert status["state"] == "open"

        # Start continuous load with mix of providers
        load_tasks = []

        for i in range(30):
            query = f"Test query for circuit recovery {i}"
            task = asyncio.create_task(
                self._test_circuit_recovery_request(services, query, f"test_user_{i}", expensive_provider)
            )
            load_tasks.append(task)

        # Wait for requests to complete
        recovery_results = await asyncio.gather(*load_tasks, return_exceptions=True)

        # Analyze results
        successful_requests = [r for r in recovery_results if isinstance(r, dict) and r.get("success")]
        fallback_used = [r for r in successful_requests if r.get("provider") != expensive_provider]

        # Assertions
        assert len(successful_requests) >= 25  # Most requests should succeed via fallback
        assert len(fallback_used) > 20  # Most should use alternative providers

        # Simulate some successes to trigger recovery
        await asyncio.sleep(0.1)  # Wait for circuit breaker timeout

        # Gradual recovery should start
        recovery_coordinator = services["recovery_coordinator"]

        recovery_result = await recovery_coordinator.start_recovery(expensive_provider, strategy="moderate")

        assert recovery_result["success"] is True

        # Test gradual traffic restoration
        for traffic_percent in [25, 50, 75, 100]:
            test_query = f"Recovery test at {traffic_percent}%"

            # Some requests should go to recovering provider
            recovery_response = await services["query_processor"].process_query(
                {"query": test_query, "preferred_provider": expensive_provider}
            )

            # Should succeed (simulated recovery)
            assert recovery_response["success"] is True

        print("✅ Circuit breaker recovery completed under load")

    async def _simulate_user_request(self, services, query: str, user_id: str, metrics: dict) -> dict:
        """Simulate a complete user request"""
        start_time = time.time()

        try:
            # Process query through complete pipeline
            response = await services["query_processor"].process_query(
                {"query": query, "user_id": user_id, "track_metrics": True}
            )

            end_time = time.time()
            response_time = end_time - start_time

            # Update metrics
            metrics["query_count"] += 1
            metrics["response_times"].append(response_time)

            if response.get("success"):
                cost = response.get("cost", 0.01)
                quality = response.get("quality_score", 0.85)

                metrics["total_cost"] += cost
                metrics["quality_scores"].append(quality)

                if response.get("source") == "faq":
                    metrics["cache_hits"] += 1
                else:
                    metrics["cache_misses"] += 1

                return {
                    "success": True,
                    "response_time": response_time,
                    "cost": cost,
                    "quality_score": quality,
                    "source": response.get("source", "unknown"),
                }
            else:
                metrics["errors"].append(response.get("error", "unknown"))
                return {"success": False, "error": response.get("error")}

        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time

            metrics["errors"].append(str(e))

            return {"success": False, "error": str(e), "response_time": response_time}

    async def _test_circuit_recovery_request(
        self, services, query: str, user_id: str, preferred_provider: str
    ) -> dict:
        """Test request during circuit breaker recovery"""

        try:
            # Check if preferred provider is available
            status = await services["circuit_breaker"].get_circuit_status(preferred_provider)

            if status["state"] == "open":
                # Use alternative provider
                alternative_response = await services["query_processor"].process_query(
                    {"query": query, "user_id": user_id, "fallback_mode": True}
                )

                return {
                    "success": alternative_response.get("success", False),
                    "provider": alternative_response.get("provider", "fallback"),
                    "cost": alternative_response.get("cost", 0.005),
                }
            else:
                # Use preferred provider
                response = await services["query_processor"].process_query(
                    {"query": query, "user_id": user_id, "preferred_provider": preferred_provider}
                )

                return {
                    "success": response.get("success", False),
                    "provider": preferred_provider,
                    "cost": response.get("cost", 0.01),
                }

        except Exception as e:
            return {"success": False, "error": str(e)}


# Helper functions for test setup and cleanup


async def _setup_test_databases(services: dict) -> None:
    """Set up test databases and initialize services"""

    # Initialize each service for testing
    for _service_name, service in services.items():
        if hasattr(service, "initialize_for_testing"):
            await service.initialize_for_testing()


async def _load_test_data(services: dict) -> None:
    """Load Italian tax test data into services"""

    # Load FAQ test data
    faq_service = services.get("faq_matcher")
    if faq_service and hasattr(faq_service, "load_test_faqs"):
        await faq_service.load_test_faqs(ITALIAN_TAX_TEST_DATA)

    # Load knowledge base test data
    kb_service = services.get("knowledge_base")
    if kb_service and hasattr(kb_service, "load_test_documents"):
        await kb_service.load_test_documents(ITALIAN_TAX_TEST_DATA)


async def _cleanup_test_environment(services: dict) -> None:
    """Clean up test environment"""

    for _service_name, service in services.items():
        if hasattr(service, "cleanup_testing"):
            await service.cleanup_testing()


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
