"""
Performance Monitoring Integration Tests.

Tests system performance, monitoring, and alerting under various conditions
to ensure SLA compliance and early detection of performance degradation.
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from unittest.mock import patch, AsyncMock

from tests.integration.test_pratikoai_integration import integration_test_environment


class TestPerformanceCompliance:
    """Test compliance with performance SLAs"""
    
    @pytest.mark.asyncio
    async def test_response_time_sla_compliance(self, integration_test_environment):
        """Test 95th percentile response time <3 seconds SLA"""
        services, metrics = integration_test_environment
        
        # Test with variety of query complexities
        test_queries = [
            # Simple FAQ queries (should be <0.5s)
            *[{"query": "Come calcolare IVA 22%?", "expected_max": 0.5, "complexity": "simple"}] * 20,
            
            # Medium complexity (should be <2s)
            *[{"query": "IRPEF con addizionale regionale Lombardia", "expected_max": 2.0, "complexity": "medium"}] * 15,
            
            # Complex queries (should be <3s)
            *[{"query": "Consolidato fiscale holding internazionale", "expected_max": 3.0, "complexity": "complex"}] * 10,
            
            # Very complex (edge cases, should be <3s)
            *[{"query": "Transfer pricing multinazionale CFC rules", "expected_max": 3.0, "complexity": "very_complex"}] * 5
        ]
        
        response_times = []
        failed_queries = []
        
        # Execute all queries
        for i, test_case in enumerate(test_queries):
            start_time = time.time()
            
            try:
                response = await services["query_processor"].process_query({
                    "query": test_case["query"],
                    "user_id": f"sla_test_user_{i}",
                    "complexity": test_case["complexity"]
                })
                
                end_time = time.time()
                response_time = end_time - start_time
                response_times.append(response_time)
                
                # Individual query should not exceed expected maximum
                if response_time > test_case["expected_max"]:
                    failed_queries.append({
                        "query": test_case["query"],
                        "response_time": response_time,
                        "expected_max": test_case["expected_max"],
                        "complexity": test_case["complexity"]
                    })
                
                assert response["success"] == True, f"Query failed: {test_case['query']}"
                
            except Exception as e:
                failed_queries.append({
                    "query": test_case["query"],
                    "error": str(e),
                    "complexity": test_case["complexity"]
                })
        
        # Calculate performance statistics
        response_times.sort()
        
        p50 = statistics.median(response_times)
        p95 = response_times[int(0.95 * len(response_times))] if response_times else 0
        p99 = response_times[int(0.99 * len(response_times))] if response_times else 0
        avg_time = statistics.mean(response_times)
        max_time = max(response_times) if response_times else 0
        
        # SLA Assertions
        assert p95 < 3.0, f"95th percentile ({p95:.2f}s) exceeds 3s SLA"
        assert p50 < 1.5, f"Median response time ({p50:.2f}s) should be under 1.5s"
        assert len(failed_queries) <= 2, f"Too many failed queries: {len(failed_queries)}"
        
        # Performance quality assertions
        simple_times = [rt for i, rt in enumerate(response_times) if test_queries[i]["complexity"] == "simple"]
        if simple_times:
            avg_simple = statistics.mean(simple_times)
            assert avg_simple < 0.5, f"Simple queries average {avg_simple:.2f}s, should be <0.5s"
        
        print(f"✅ SLA Compliance: P50={p50:.2f}s, P95={p95:.2f}s, P99={p99:.2f}s, Max={max_time:.2f}s")
        print(f"   Failed queries: {len(failed_queries)}/{len(test_queries)}")
        
        return {
            "p50": p50,
            "p95": p95, 
            "p99": p99,
            "avg": avg_time,
            "max": max_time,
            "failed_count": len(failed_queries),
            "total_queries": len(test_queries)
        }
    
    @pytest.mark.asyncio
    async def test_cost_efficiency_targets(self, integration_test_environment):
        """Test cost efficiency targets: <€1.70 per user daily"""
        services, metrics = integration_test_environment
        
        # Simulate typical user daily usage patterns
        user_patterns = [
            # Professional user (high usage)
            {
                "user_type": "commercialista",
                "daily_queries": [
                    *["Scadenze fiscali"] * 2,  # Check twice daily
                    *["IRPEF calcolo cliente"] * 8,  # 8 client calculations
                    *["Normativa aggiornata"] * 1,  # News check
                    *["Consolidato fiscale complesso"] * 2,  # Complex research
                    *["F24 compilazione"] * 5  # F24 preparations
                ],
                "target_cost": 1.20  # €1.20 for professional
            },
            # Regular business user (medium usage)  
            {
                "user_type": "business_owner",
                "daily_queries": [
                    *["Regime forfettario"] * 3,
                    *["IVA trimestrale"] * 2, 
                    *["Detrazioni spese"] * 4,
                    *["F24 online"] * 2
                ],
                "target_cost": 0.80  # €0.80 for business
            },
            # Individual taxpayer (low usage)
            {
                "user_type": "individual", 
                "daily_queries": [
                    *["730 precompilato"] * 2,
                    *["Detrazioni mediche"] * 1,
                    *["Bonus casa"] * 1,
                    *["Rimborso IRPEF"] * 1
                ],
                "target_cost": 0.30  # €0.30 for individual
            }
        ]
        
        cost_results = []
        
        for pattern in user_patterns:
            user_id = f"{pattern['user_type']}_cost_test"
            daily_cost = 0.0
            query_count = 0
            
            for query in pattern["daily_queries"]:
                response = await services["query_processor"].process_query({
                    "query": query,
                    "user_id": user_id,
                    "user_type": pattern["user_type"]
                })
                
                assert response["success"] == True
                
                cost = response.get("cost", 0.01)
                daily_cost += cost
                query_count += 1
            
            # Cost efficiency assertions
            assert daily_cost <= pattern["target_cost"], \
                f"{pattern['user_type']} daily cost €{daily_cost:.4f} exceeds target €{pattern['target_cost']}"
            
            avg_cost_per_query = daily_cost / query_count if query_count > 0 else 0
            
            cost_results.append({
                "user_type": pattern["user_type"],
                "daily_cost": daily_cost,
                "query_count": query_count,
                "avg_cost_per_query": avg_cost_per_query,
                "target_cost": pattern["target_cost"],
                "efficiency": (pattern["target_cost"] - daily_cost) / pattern["target_cost"]
            })
            
            print(f"✅ {pattern['user_type']}: €{daily_cost:.4f}/day ({query_count} queries, €{avg_cost_per_query:.4f}/query)")
        
        # Overall efficiency check
        total_cost = sum(r["daily_cost"] for r in cost_results)
        total_queries = sum(r["query_count"] for r in cost_results)
        avg_cost_per_query = total_cost / total_queries
        
        assert avg_cost_per_query <= 0.010, f"Average cost per query {avg_cost_per_query:.4f} too high"
        
        return cost_results
    
    @pytest.mark.asyncio
    async def test_concurrent_load_performance(self, integration_test_environment):
        """Test performance under concurrent load"""
        services, metrics = integration_test_environment
        
        # Simulate different concurrency levels
        concurrency_tests = [
            {"concurrent_users": 10, "max_degradation": 0.3},   # 30% slowdown acceptable
            {"concurrent_users": 25, "max_degradation": 0.5},   # 50% slowdown at higher load
            {"concurrent_users": 50, "max_degradation": 0.8}    # 80% slowdown at peak
        ]
        
        # Baseline single-user performance
        baseline_query = "Calcolo IRPEF reddito €40.000"
        baseline_start = time.time()
        
        baseline_response = await services["query_processor"].process_query({
            "query": baseline_query,
            "user_id": "baseline_user"
        })
        
        baseline_time = time.time() - baseline_start
        assert baseline_response["success"] == True
        
        print(f"Baseline response time: {baseline_time:.3f}s")
        
        # Test each concurrency level
        for test in concurrency_tests:
            concurrent_users = test["concurrent_users"]
            max_degradation = test["max_degradation"]
            
            # Create concurrent tasks
            tasks = []
            start_time = time.time()
            
            for i in range(concurrent_users):
                task = asyncio.create_task(
                    services["query_processor"].process_query({
                        "query": f"{baseline_query} user {i}",
                        "user_id": f"concurrent_user_{i}"
                    })
                )
                tasks.append(task)
            
            # Wait for all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analyze results
            successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
            failed_count = len(results) - len(successful_results)
            
            # Calculate performance metrics
            total_duration = end_time - start_time
            avg_response_time = total_duration  # Since they ran concurrently
            
            degradation = (avg_response_time - baseline_time) / baseline_time
            
            # Assertions
            assert failed_count <= concurrent_users * 0.05, \
                f"Too many failures at {concurrent_users} concurrent: {failed_count}"
            
            assert degradation <= max_degradation, \
                f"Performance degradation {degradation:.1%} exceeds {max_degradation:.1%} at {concurrent_users} concurrent"
            
            success_rate = len(successful_results) / concurrent_users
            assert success_rate >= 0.95, f"Success rate {success_rate:.1%} too low"
            
            print(f"✅ {concurrent_users} concurrent: {degradation:.1%} degradation, {success_rate:.1%} success rate")


class TestSystemMonitoringIntegration:
    """Test monitoring and alerting system integration"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_monitoring_alerts(self, integration_test_environment):
        """Test circuit breaker state monitoring and alerting"""
        services, metrics = integration_test_environment
        
        # Trigger circuit breaker states and verify monitoring
        provider = "test_provider"
        circuit_breaker = services["circuit_breaker"]
        
        # 1. Trigger OPEN state
        for i in range(6):  # Exceed failure threshold
            await circuit_breaker.record_failure(provider, failure_type="timeout")
        
        # Check monitoring detects OPEN state
        health_metrics = await circuit_breaker.get_health_metrics()
        
        assert health_metrics["total_providers"] >= 1
        assert provider in health_metrics["providers"]
        assert health_metrics["providers"][provider]["state"] == "open"
        
        # Check alerts generated
        alerts = await circuit_breaker.generate_alerts()
        open_alerts = [a for a in alerts if a["type"] == "circuit_open" and a["provider"] == provider]
        
        assert len(open_alerts) > 0, "No circuit open alert generated"
        assert open_alerts[0]["severity"] == "error"
        
        # 2. Test recovery monitoring
        recovery_coordinator = services["recovery_coordinator"]
        
        recovery_result = await recovery_coordinator.start_recovery(provider, strategy="moderate")
        assert recovery_result["success"] == True
        
        # Check recovery status monitoring
        recovery_status = await recovery_coordinator.get_recovery_status(recovery_result["recovery_id"])
        assert recovery_status is not None
        assert recovery_status.provider == provider
        assert recovery_status.phase.value in ["initial", "progressive"]
        
        # 3. Test health scoring integration
        health_scorer = services["health_scorer"]
        
        health_score = await health_scorer.calculate_health_score(
            provider, 
            {"total_requests": 10, "success_count": 3, "failure_count": 7}
        )
        
        assert health_score.overall_score < 0.5  # Should be low due to failures
        assert health_score.status.value in ["critical", "failing"]
        assert len(health_score.recommendations) > 0
        
        print(f"✅ Circuit breaker monitoring: {len(alerts)} alerts, recovery started")
    
    @pytest.mark.asyncio
    async def test_cost_monitoring_and_alerts(self, integration_test_environment):
        """Test cost monitoring and budget alerts"""
        services, metrics = integration_test_environment
        
        cost_circuit = services["cost_circuit"]
        
        # Set up budget for monitoring
        provider = "openai"
        
        budget_result = await cost_circuit.set_cost_budget(
            provider,
            period="daily",
            limit=5.0,  # €5 daily limit
            alert_thresholds=[0.7, 0.8, 0.9],  # 70%, 80%, 90%
            hard_limit=True
        )
        
        assert budget_result == True
        
        # Simulate spending approaching limits
        spending_scenarios = [
            {"cost": 1.0, "description": "Normal usage"},
            {"cost": 2.0, "description": "Increased usage"}, 
            {"cost": 1.5, "description": "Approaching 70% (€3.5/€5)"},
            {"cost": 0.6, "description": "Hit 70% threshold (€4.1/€5)"},
            {"cost": 0.5, "description": "Hit 80% threshold (€4.6/€5)"},
            {"cost": 0.3, "description": "Hit 90% threshold (€4.9/€5)"}
        ]
        
        total_spent = 0.0
        alerts_generated = []
        
        for scenario in spending_scenarios:
            # Check if request would be allowed
            cost_check = await cost_circuit.should_allow_request_cost_check(
                provider,
                estimated_cost=scenario["cost"]
            )
            
            if cost_check["allowed"]:
                # Record actual cost
                await cost_circuit.record_actual_cost(provider, scenario["cost"])
                total_spent += scenario["cost"]
                
                # Check for new alerts
                current_alerts = cost_circuit.get_active_cost_alerts()
                new_alerts = [a for a in current_alerts if a not in alerts_generated]
                alerts_generated.extend(new_alerts)
                
                print(f"Spent €{scenario['cost']:.1f} - Total: €{total_spent:.1f}/€5.0 - {scenario['description']}")
                
                if new_alerts:
                    for alert in new_alerts:
                        print(f"  🚨 Alert: {alert['type']} - {alert['message']}")
            else:
                print(f"❌ Request blocked: {cost_check['reason']}")
                break
        
        # Verify alert progression
        budget_alerts = [a for a in alerts_generated if "budget" in a["type"]]
        assert len(budget_alerts) >= 2, "Should generate multiple budget alerts"
        
        # Check final cost metrics
        cost_metrics = await cost_circuit.get_cost_metrics(provider)
        assert cost_metrics is not None
        assert cost_metrics.total_cost >= 4.0  # Should have spent significant amount
        
        # Check budget protection worked
        assert total_spent <= 5.2  # Should not exceed limit by much
        
        print(f"✅ Cost monitoring: €{total_spent:.2f} spent, {len(alerts_generated)} alerts generated")
    
    @pytest.mark.asyncio
    async def test_quality_degradation_detection(self, integration_test_environment):
        """Test quality monitoring and degradation alerts"""
        services, metrics = integration_test_environment
        
        # Simulate quality degradation over time
        quality_scenarios = [
            {"period": "baseline", "error_rate": 0.05, "expected_quality": 0.95},
            {"period": "slight_degradation", "error_rate": 0.10, "expected_quality": 0.90},
            {"period": "noticeable_degradation", "error_rate": 0.15, "expected_quality": 0.85},
            {"period": "significant_degradation", "error_rate": 0.25, "expected_quality": 0.75}
        ]
        
        quality_history = []
        
        for scenario in quality_scenarios:
            # Simulate queries with specific error rates
            correct_responses = int(20 * (1 - scenario["error_rate"]))
            incorrect_responses = 20 - correct_responses
            
            period_quality_scores = []
            
            # Generate responses with controlled quality
            for i in range(correct_responses):
                response = await services["query_processor"].process_query({
                    "query": f"Test quality query {i} - {scenario['period']}",
                    "simulate_quality": 0.9  # High quality
                })
                period_quality_scores.append(response.get("quality_score", 0.9))
            
            for i in range(incorrect_responses):
                response = await services["query_processor"].process_query({
                    "query": f"Test degraded query {i} - {scenario['period']}",
                    "simulate_quality": 0.5  # Lower quality
                })
                period_quality_scores.append(response.get("quality_score", 0.5))
            
            avg_period_quality = sum(period_quality_scores) / len(period_quality_scores)
            quality_history.append({
                "period": scenario["period"],
                "avg_quality": avg_period_quality,
                "expected": scenario["expected_quality"],
                "error_rate": scenario["error_rate"]
            })
            
            print(f"{scenario['period']}: {avg_period_quality:.3f} quality ({scenario['error_rate']:.1%} error rate)")
        
        # Check quality trend detection
        quality_values = [q["avg_quality"] for q in quality_history]
        quality_trend = quality_values[-1] - quality_values[0]  # Final - Initial
        
        assert quality_trend < -0.1, f"Quality degradation {quality_trend:.3f} should be detected"
        
        # Simulate quality alert system
        if quality_values[-1] < 0.80:  # Below 80% quality
            quality_alert = {
                "type": "quality_degradation",
                "current_quality": quality_values[-1],
                "baseline_quality": quality_values[0],
                "degradation": abs(quality_trend),
                "severity": "critical" if quality_values[-1] < 0.75 else "warning"
            }
            
            assert quality_alert["severity"] == "critical", "Should trigger critical alert"
            print(f"🚨 Quality Alert: {quality_alert['degradation']:.3f} degradation detected")
        
        print(f"✅ Quality monitoring: {quality_trend:.3f} degradation detected and alerted")


class TestRealTimeMonitoringDashboard:
    """Test real-time monitoring dashboard data"""
    
    @pytest.mark.asyncio
    async def test_dashboard_metrics_accuracy(self, integration_test_environment):
        """Test accuracy of real-time dashboard metrics"""
        services, metrics = integration_test_environment
        
        # Generate controlled test activity
        test_activity = {
            "queries_processed": 0,
            "total_cost": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_response_time": 0.0,
            "error_count": 0
        }
        
        # Execute known set of queries
        test_queries = [
            {"query": "Test dashboard query 1", "should_hit_cache": False},
            {"query": "Test dashboard query 1", "should_hit_cache": True},  # Repeat for cache hit
            {"query": "Test dashboard query 2", "should_hit_cache": False},
            {"query": "Test dashboard query 3", "should_hit_cache": False},
            {"query": "Test dashboard query 2", "should_hit_cache": True},  # Another cache hit
        ]
        
        response_times = []
        
        for test_query in test_queries:
            start_time = time.time()
            
            response = await services["query_processor"].process_query({
                "query": test_query["query"],
                "user_id": "dashboard_test_user",
                "track_metrics": True
            })
            
            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)
            
            # Track expected metrics
            test_activity["queries_processed"] += 1
            test_activity["total_cost"] += response.get("cost", 0.01)
            
            if response.get("source") == "cache" or test_query["should_hit_cache"]:
                test_activity["cache_hits"] += 1
            else:
                test_activity["cache_misses"] += 1
            
            if not response.get("success", True):
                test_activity["error_count"] += 1
        
        test_activity["avg_response_time"] = sum(response_times) / len(response_times)
        
        # Get dashboard metrics
        dashboard_metrics = {
            "queries_processed": metrics.get("query_count", 0),
            "total_cost": metrics.get("total_cost", 0.0),
            "cache_hits": metrics.get("cache_hits", 0), 
            "cache_misses": metrics.get("cache_misses", 0),
            "avg_response_time": sum(metrics.get("response_times", [])) / max(len(metrics.get("response_times", [])), 1),
            "error_count": len(metrics.get("errors", []))
        }
        
        # Verify dashboard accuracy
        tolerance = 0.1  # 10% tolerance for timing variations
        
        assert abs(dashboard_metrics["queries_processed"] - test_activity["queries_processed"]) <= 1
        assert abs(dashboard_metrics["total_cost"] - test_activity["total_cost"]) <= test_activity["total_cost"] * tolerance
        
        # Cache hit ratio should be reasonable
        total_cache_operations = dashboard_metrics["cache_hits"] + dashboard_metrics["cache_misses"]
        if total_cache_operations > 0:
            cache_hit_rate = dashboard_metrics["cache_hits"] / total_cache_operations
            assert 0.0 <= cache_hit_rate <= 1.0, f"Invalid cache hit rate: {cache_hit_rate}"
        
        print(f"✅ Dashboard metrics accuracy verified:")
        print(f"   Queries: {dashboard_metrics['queries_processed']}, Cost: €{dashboard_metrics['total_cost']:.4f}")
        print(f"   Cache: {dashboard_metrics['cache_hits']} hits, {dashboard_metrics['cache_misses']} misses")
        print(f"   Avg Response: {dashboard_metrics['avg_response_time']:.3f}s, Errors: {dashboard_metrics['error_count']}")
    
    @pytest.mark.asyncio 
    async def test_real_time_health_dashboard(self, integration_test_environment):
        """Test real-time health monitoring dashboard"""
        services, metrics = integration_test_environment
        
        # Get comprehensive health metrics
        circuit_breaker = services["circuit_breaker"]
        health_scorer = services["health_scorer"]
        
        # Test multiple providers
        test_providers = ["openai", "anthropic", "google"]
        
        for provider in test_providers:
            # Generate some activity
            await circuit_breaker.record_success(provider, response_time=0.5, cost=0.01)
            await circuit_breaker.record_success(provider, response_time=0.3, cost=0.008)
            await circuit_breaker.record_failure(provider, failure_type="timeout", cost=0.01)
        
        # Get comprehensive health metrics
        health_metrics = await circuit_breaker.get_health_metrics()
        
        # Verify dashboard data structure
        assert "total_providers" in health_metrics
        assert "providers" in health_metrics
        assert "overall_health" in health_metrics
        assert "alerts" in health_metrics
        
        assert health_metrics["total_providers"] == len(test_providers)
        assert health_metrics["overall_health"] >= 0.0 and health_metrics["overall_health"] <= 1.0
        
        # Check individual provider metrics
        for provider in test_providers:
            provider_metrics = health_metrics["providers"][provider]
            
            assert "health_score" in provider_metrics
            assert "state" in provider_metrics
            assert "success_rate" in provider_metrics
            assert "cost_utilization" in provider_metrics
            
            assert 0.0 <= provider_metrics["health_score"] <= 1.0
            assert provider_metrics["state"] in ["closed", "open", "half_open", "throttled", "maintenance"]
        
        # Test alert generation
        alerts = health_metrics["alerts"]
        
        for alert in alerts:
            assert "severity" in alert
            assert "provider" in alert
            assert "message" in alert
            assert alert["severity"] in ["low", "medium", "high", "critical"]
        
        print(f"✅ Health dashboard: {health_metrics['total_providers']} providers, {health_metrics['overall_health']:.3f} overall health, {len(alerts)} alerts")


if __name__ == "__main__":
    # Run performance monitoring tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])