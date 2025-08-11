"""
Comprehensive Load Testing Tests for PratikoAI.

These tests validate that the system can handle 50-100 concurrent users
(target customer base for €25k ARR) without performance degradation.
Tests are written following TDD methodology - implementation comes after.

Target Metrics:
- Single user: <3s response time (P95)
- 50 concurrent users: <5s response time (P95)
- 100 concurrent users: <8s response time (P95)
- Throughput: 1000 requests/minute sustained
- Error rate: <1%
- Cache hit rate: >70% under load
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Test configuration
@dataclass
class LoadTestMetrics:
    """Metrics collected during load tests"""
    response_times: List[float]
    error_count: int
    success_count: int
    cpu_usage: List[float]
    memory_usage: List[float]
    db_connections: List[int]
    cache_hits: int
    cache_misses: int
    start_time: datetime
    end_time: datetime
    
    @property
    def total_requests(self) -> int:
        return self.success_count + self.error_count
    
    @property
    def error_rate(self) -> float:
        return self.error_count / self.total_requests if self.total_requests > 0 else 0
    
    @property
    def cache_hit_rate(self) -> float:
        total_cache_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / total_cache_requests if total_cache_requests > 0 else 0
    
    @property
    def p95_response_time(self) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[index]
    
    @property
    def p99_response_time(self) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.99)
        return sorted_times[index]
    
    @property
    def avg_response_time(self) -> float:
        return statistics.mean(self.response_times) if self.response_times else 0
    
    @property
    def throughput(self) -> float:
        """Requests per minute"""
        duration = (self.end_time - self.start_time).total_seconds()
        return (self.total_requests / duration) * 60 if duration > 0 else 0


class TestPerformanceBaselines:
    """Test performance baseline requirements"""
    
    @pytest.mark.asyncio
    async def test_single_user_response_time(self, load_tester):
        """Test single user response time <3 seconds (P95)"""
        # Arrange
        metrics = await load_tester.run_test(
            users=1,
            duration=60,  # 1 minute
            scenario="mixed"
        )
        
        # Assert
        assert metrics.p95_response_time < 3.0, \
            f"Single user P95 response time {metrics.p95_response_time}s exceeds 3s SLA"
        assert metrics.error_rate < 0.01, \
            f"Single user error rate {metrics.error_rate} exceeds 1% threshold"
    
    @pytest.mark.asyncio
    async def test_50_concurrent_users_response_time(self, load_tester):
        """Test 50 concurrent users with <5 second response time (P95)"""
        # Arrange
        metrics = await load_tester.run_test(
            users=50,
            duration=300,  # 5 minutes
            ramp_up=60,    # 1 minute ramp-up
            scenario="mixed"
        )
        
        # Assert
        assert metrics.p95_response_time < 5.0, \
            f"50 users P95 response time {metrics.p95_response_time}s exceeds 5s SLA"
        assert metrics.error_rate < 0.01, \
            f"50 users error rate {metrics.error_rate} exceeds 1% threshold"
        assert metrics.throughput >= 1000, \
            f"Throughput {metrics.throughput} req/min below 1000 req/min target"
    
    @pytest.mark.asyncio
    async def test_100_concurrent_users_response_time(self, load_tester):
        """Test 100 concurrent users with <8 second response time (P95)"""
        # Arrange
        metrics = await load_tester.run_test(
            users=100,
            duration=300,  # 5 minutes
            ramp_up=120,   # 2 minute ramp-up
            scenario="mixed"
        )
        
        # Assert
        assert metrics.p95_response_time < 8.0, \
            f"100 users P95 response time {metrics.p95_response_time}s exceeds 8s SLA"
        assert metrics.error_rate < 0.02, \
            f"100 users error rate {metrics.error_rate} exceeds 2% threshold"
    
    @pytest.mark.asyncio
    async def test_sustained_throughput(self, load_tester):
        """Test throughput of 1000 requests/minute sustained"""
        # Arrange
        metrics = await load_tester.run_test(
            users=50,
            duration=600,  # 10 minutes sustained
            scenario="high_frequency"
        )
        
        # Assert
        assert metrics.throughput >= 1000, \
            f"Sustained throughput {metrics.throughput} req/min below target"
        # Check consistency over time windows
        throughput_windows = load_tester.get_throughput_windows(metrics, window_size=60)
        for window_throughput in throughput_windows:
            assert window_throughput >= 900, \
                "Throughput dropped below 900 req/min during test"
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_under_load(self, load_tester):
        """Test cache hit rate remains >70% under load"""
        # Arrange
        metrics = await load_tester.run_test(
            users=50,
            duration=300,
            scenario="cacheable_queries"  # Repeated queries
        )
        
        # Assert
        assert metrics.cache_hit_rate > 0.7, \
            f"Cache hit rate {metrics.cache_hit_rate} below 70% target"
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_handling(self, load_tester):
        """Test database connection pool handling (max 100 connections)"""
        # Arrange
        metrics = await load_tester.run_test(
            users=100,
            duration=300,
            scenario="database_heavy"
        )
        
        # Assert
        max_db_connections = max(metrics.db_connections)
        assert max_db_connections <= 100, \
            f"Database connections {max_db_connections} exceeded 100 connection limit"
        
        # Verify no connection pool exhaustion errors
        connection_errors = load_tester.get_errors_by_type(metrics, "connection_pool_exhausted")
        assert len(connection_errors) == 0, \
            f"Found {len(connection_errors)} connection pool exhaustion errors"
    
    @pytest.mark.asyncio
    async def test_redis_performance_under_concurrent_access(self, load_tester):
        """Test Redis performance under concurrent access"""
        # Arrange
        metrics = await load_tester.run_test(
            users=100,
            duration=300,
            scenario="cache_heavy"
        )
        
        # Assert
        redis_latencies = load_tester.get_redis_latencies(metrics)
        p95_redis_latency = statistics.quantiles(redis_latencies, n=20)[18]  # 95th percentile
        assert p95_redis_latency < 10, \
            f"Redis P95 latency {p95_redis_latency}ms exceeds 10ms threshold"
    
    @pytest.mark.asyncio
    async def test_llm_api_rate_limit_handling(self, load_tester):
        """Test LLM API rate limit handling under load"""
        # Arrange
        metrics = await load_tester.run_test(
            users=50,
            duration=300,
            scenario="llm_heavy"
        )
        
        # Assert
        rate_limit_errors = load_tester.get_errors_by_type(metrics, "rate_limit")
        assert len(rate_limit_errors) < metrics.total_requests * 0.01, \
            f"Rate limit errors {len(rate_limit_errors)} exceed 1% of requests"
        
        # Verify retry mechanisms are working
        retry_successes = load_tester.get_retry_successes(metrics)
        assert len(retry_successes) > 0, "No successful retries found"


class TestScalability:
    """Test system scalability characteristics"""
    
    @pytest.mark.asyncio
    async def test_linear_scaling_to_50_users(self, load_tester):
        """Test linear scaling from 1 to 50 users"""
        # Arrange
        scaling_points = [1, 10, 20, 30, 40, 50]
        metrics_by_users = {}
        
        for users in scaling_points:
            metrics_by_users[users] = await load_tester.run_test(
                users=users,
                duration=120,
                scenario="mixed"
            )
        
        # Assert - Response time should not increase more than linearly
        base_response_time = metrics_by_users[1].avg_response_time
        for users, metrics in metrics_by_users.items():
            expected_max_response_time = base_response_time * (1 + (users - 1) * 0.02)  # 2% degradation per user
            assert metrics.avg_response_time <= expected_max_response_time, \
                f"Response time at {users} users degraded non-linearly"
        
        # Throughput should scale almost linearly
        base_throughput = metrics_by_users[1].throughput
        for users, metrics in metrics_by_users.items():
            expected_min_throughput = base_throughput * users * 0.8  # 80% efficiency
            assert metrics.throughput >= expected_min_throughput, \
                f"Throughput at {users} users below linear scaling"
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_at_100_users(self, load_tester):
        """Test system behavior at 100 users (graceful degradation)"""
        # Arrange
        metrics = await load_tester.run_test(
            users=100,
            duration=300,
            scenario="mixed"
        )
        
        # Assert - System should degrade gracefully, not fail
        assert metrics.error_rate < 0.05, \
            f"Error rate {metrics.error_rate} exceeds 5% graceful degradation threshold"
        
        # Critical functions should still work
        critical_endpoints = ["/api/auth/login", "/api/query", "/api/tax/calculate"]
        for endpoint in critical_endpoints:
            endpoint_metrics = load_tester.get_endpoint_metrics(metrics, endpoint)
            assert endpoint_metrics.error_rate < 0.02, \
                f"Critical endpoint {endpoint} error rate too high"
    
    @pytest.mark.asyncio
    async def test_auto_scaling_triggers(self, load_tester):
        """Test auto-scaling triggers (if configured)"""
        # Arrange
        metrics = await load_tester.run_test(
            users=50,
            duration=300,
            scenario="cpu_intensive",
            monitor_scaling=True
        )
        
        # Assert
        scaling_events = load_tester.get_scaling_events(metrics)
        if metrics.avg_cpu_usage > 70:
            assert len(scaling_events) > 0, \
                "No scaling events triggered despite high CPU usage"
        
        # Verify scaling improves performance
        if scaling_events:
            pre_scaling_metrics = load_tester.get_metrics_before(metrics, scaling_events[0].timestamp)
            post_scaling_metrics = load_tester.get_metrics_after(metrics, scaling_events[0].timestamp)
            assert post_scaling_metrics.avg_response_time < pre_scaling_metrics.avg_response_time, \
                "Performance did not improve after scaling"
    
    @pytest.mark.asyncio
    async def test_load_balancer_distribution(self, load_tester):
        """Test load balancer distribution (if applicable)"""
        # Arrange
        metrics = await load_tester.run_test(
            users=50,
            duration=300,
            scenario="mixed",
            track_instances=True
        )
        
        # Assert
        instance_distributions = load_tester.get_instance_distributions(metrics)
        if len(instance_distributions) > 1:
            # Check distribution is relatively even
            total_requests = sum(instance_distributions.values())
            for instance, count in instance_distributions.items():
                expected_share = total_requests / len(instance_distributions)
                assert abs(count - expected_share) / expected_share < 0.2, \
                    f"Instance {instance} has uneven load distribution"
    
    @pytest.mark.asyncio
    async def test_memory_usage_growth_under_sustained_load(self, load_tester):
        """Test memory usage growth under sustained load"""
        # Arrange
        metrics = await load_tester.run_test(
            users=50,
            duration=1800,  # 30 minutes sustained
            scenario="mixed"
        )
        
        # Assert - Memory should stabilize, not grow indefinitely
        memory_samples = metrics.memory_usage
        first_quarter = memory_samples[:len(memory_samples)//4]
        last_quarter = memory_samples[3*len(memory_samples)//4:]
        
        avg_initial_memory = statistics.mean(first_quarter)
        avg_final_memory = statistics.mean(last_quarter)
        
        memory_growth = (avg_final_memory - avg_initial_memory) / avg_initial_memory
        assert memory_growth < 0.2, \
            f"Memory grew by {memory_growth*100}% during sustained load"
    
    @pytest.mark.asyncio
    async def test_cpu_utilization_at_target_load(self, load_tester):
        """Test CPU utilization remains <80% at target load"""
        # Arrange
        metrics = await load_tester.run_test(
            users=50,
            duration=300,
            scenario="mixed"
        )
        
        # Assert
        avg_cpu = statistics.mean(metrics.cpu_usage)
        max_cpu = max(metrics.cpu_usage)
        
        assert avg_cpu < 80, \
            f"Average CPU usage {avg_cpu}% exceeds 80% threshold"
        assert max_cpu < 95, \
            f"Max CPU usage {max_cpu}% exceeds 95% threshold"
    
    @pytest.mark.asyncio
    async def test_disk_io_patterns_during_peak_usage(self, load_tester):
        """Test disk I/O patterns during peak usage"""
        # Arrange
        metrics = await load_tester.run_test(
            users=100,
            duration=300,
            scenario="document_heavy"  # PDF processing
        )
        
        # Assert
        disk_io_metrics = load_tester.get_disk_io_metrics(metrics)
        
        # Check for I/O bottlenecks
        assert disk_io_metrics.avg_queue_length < 10, \
            f"Disk queue length {disk_io_metrics.avg_queue_length} indicates I/O bottleneck"
        assert disk_io_metrics.avg_wait_time < 100, \
            f"Disk wait time {disk_io_metrics.avg_wait_time}ms too high"


class TestStressAndSpike:
    """Test system behavior under stress and spike conditions"""
    
    @pytest.mark.asyncio
    async def test_sudden_spike_from_10_to_100_users(self, load_tester):
        """Test sudden spike from 10 to 100 users"""
        # Arrange
        spike_config = {
            "initial_users": 10,
            "spike_users": 100,
            "spike_duration": 10,  # 10 seconds to spike
            "total_duration": 600  # 10 minutes total
        }
        
        metrics = await load_tester.run_spike_test(**spike_config)
        
        # Assert
        spike_metrics = load_tester.get_metrics_during_spike(metrics, spike_config)
        
        # System should handle spike without crashes
        assert spike_metrics.error_rate < 0.05, \
            f"Error rate {spike_metrics.error_rate} during spike exceeds 5%"
        
        # Response time should stabilize after spike
        post_spike_metrics = load_tester.get_metrics_after_spike(metrics, spike_config)
        assert post_spike_metrics.p95_response_time < 10.0, \
            f"Response time did not stabilize after spike"
    
    @pytest.mark.asyncio
    async def test_sustained_maximum_load_for_1_hour(self, load_tester):
        """Test sustained maximum load for 1 hour"""
        # Arrange
        metrics = await load_tester.run_test(
            users=100,
            duration=3600,  # 1 hour
            scenario="mixed"
        )
        
        # Assert
        # System should remain stable
        assert metrics.error_rate < 0.02, \
            f"Error rate {metrics.error_rate} during sustained load exceeds 2%"
        
        # Check for memory leaks
        memory_trend = load_tester.calculate_trend(metrics.memory_usage)
        assert memory_trend < 0.1, \
            f"Memory shows upward trend of {memory_trend}GB/hour indicating leak"
        
        # Check for degradation over time
        hourly_metrics = load_tester.get_hourly_metrics(metrics)
        first_15min = hourly_metrics[0]
        last_15min = hourly_metrics[-1]
        
        performance_degradation = (last_15min.avg_response_time - first_15min.avg_response_time) / first_15min.avg_response_time
        assert performance_degradation < 0.3, \
            f"Performance degraded by {performance_degradation*100}% over 1 hour"
    
    @pytest.mark.asyncio
    async def test_recovery_after_overload_condition(self, load_tester):
        """Test recovery after overload condition"""
        # Arrange
        recovery_test_config = {
            "phases": [
                {"users": 50, "duration": 300},   # Normal load
                {"users": 200, "duration": 300},  # Overload
                {"users": 50, "duration": 300}    # Recovery
            ]
        }
        
        metrics = await load_tester.run_phased_test(recovery_test_config)
        
        # Assert
        normal_metrics = load_tester.get_phase_metrics(metrics, 0)
        overload_metrics = load_tester.get_phase_metrics(metrics, 1)
        recovery_metrics = load_tester.get_phase_metrics(metrics, 2)
        
        # System should recover to near-normal performance
        recovery_ratio = recovery_metrics.avg_response_time / normal_metrics.avg_response_time
        assert recovery_ratio < 1.2, \
            f"System did not recover properly, response time {recovery_ratio}x normal"
        
        # Error rate should return to normal
        assert recovery_metrics.error_rate <= normal_metrics.error_rate * 1.5, \
            "Error rate did not recover after overload"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_activation_under_stress(self, load_tester):
        """Test circuit breaker activation under stress"""
        # Arrange
        # Simulate provider failures
        with patch('app.services.openai_provider.OpenAIProvider.chat_completion') as mock_openai:
            mock_openai.side_effect = Exception("Service unavailable")
            
            metrics = await load_tester.run_test(
                users=50,
                duration=300,
                scenario="llm_heavy"
            )
        
        # Assert
        circuit_breaker_events = load_tester.get_circuit_breaker_events(metrics)
        assert len(circuit_breaker_events) > 0, \
            "Circuit breaker did not activate despite failures"
        
        # Verify fallback mechanisms worked
        fallback_successes = load_tester.get_fallback_successes(metrics)
        assert len(fallback_successes) > 0, \
            "No successful fallbacks after circuit breaker activation"
    
    @pytest.mark.asyncio
    async def test_retry_mechanism_behavior_under_load(self, load_tester):
        """Test retry mechanism behavior under load"""
        # Arrange
        # Inject transient failures
        failure_rate = 0.1  # 10% transient failures
        
        metrics = await load_tester.run_test(
            users=50,
            duration=300,
            scenario="mixed",
            inject_failures=failure_rate
        )
        
        # Assert
        retry_metrics = load_tester.get_retry_metrics(metrics)
        
        # Retries should succeed for transient failures
        retry_success_rate = retry_metrics.successful_retries / retry_metrics.total_retries
        assert retry_success_rate > 0.8, \
            f"Retry success rate {retry_success_rate} below 80%"
        
        # Retry overhead should be reasonable
        retry_overhead = retry_metrics.total_retry_time / metrics.total_requests
        assert retry_overhead < 0.5, \
            f"Retry overhead {retry_overhead}s per request too high"
    
    @pytest.mark.asyncio
    async def test_faq_system_performance_under_concurrent_queries(self, load_tester):
        """Test FAQ system performance under concurrent queries"""
        # Arrange
        metrics = await load_tester.run_test(
            users=100,
            duration=300,
            scenario="faq_only"
        )
        
        # Assert
        # FAQ queries should be fast even under load
        faq_metrics = load_tester.get_endpoint_metrics(metrics, "/api/faq/search")
        assert faq_metrics.p95_response_time < 1.0, \
            f"FAQ P95 response time {faq_metrics.p95_response_time}s exceeds 1s"
        
        # High cache hit rate for FAQ
        assert faq_metrics.cache_hit_rate > 0.9, \
            f"FAQ cache hit rate {faq_metrics.cache_hit_rate} below 90%"
    
    @pytest.mark.asyncio
    async def test_knowledge_update_system_during_high_traffic(self, load_tester):
        """Test knowledge update system during high traffic"""
        # Arrange
        # Run load test while triggering knowledge updates
        update_task = asyncio.create_task(
            load_tester.trigger_knowledge_updates(interval=60, count=5)
        )
        
        metrics = await load_tester.run_test(
            users=50,
            duration=300,
            scenario="mixed"
        )
        
        await update_task
        
        # Assert
        # Updates should not significantly impact performance
        update_impact_metrics = load_tester.get_metrics_during_updates(metrics)
        normal_metrics = load_tester.get_metrics_between_updates(metrics)
        
        performance_impact = (update_impact_metrics.avg_response_time - normal_metrics.avg_response_time) / normal_metrics.avg_response_time
        assert performance_impact < 0.2, \
            f"Knowledge updates caused {performance_impact*100}% performance degradation"


class TestItalianMarketSpecific:
    """Test Italian market specific features under load"""
    
    @pytest.mark.asyncio
    async def test_concurrent_tax_calculations(self, load_tester):
        """Test concurrent tax calculations (IVA, IRPEF)"""
        # Arrange
        italian_tax_scenarios = {
            "IVA": 0.4,      # 40% IVA calculations
            "IRPEF": 0.3,    # 30% IRPEF calculations
            "IMU": 0.2,      # 20% IMU calculations
            "mixed": 0.1     # 10% mixed calculations
        }
        
        metrics = await load_tester.run_test(
            users=50,
            duration=300,
            scenario="italian_tax",
            scenario_weights=italian_tax_scenarios
        )
        
        # Assert
        tax_endpoint_metrics = load_tester.get_endpoint_metrics(metrics, "/api/tax/calculate")
        
        # Tax calculations should be fast
        assert tax_endpoint_metrics.p95_response_time < 2.0, \
            f"Tax calculation P95 time {tax_endpoint_metrics.p95_response_time}s exceeds 2s"
        
        # Accuracy under load
        tax_accuracy = load_tester.verify_tax_calculation_accuracy(metrics)
        assert tax_accuracy > 0.999, \
            f"Tax calculation accuracy {tax_accuracy} below 99.9%"
    
    @pytest.mark.asyncio
    async def test_document_processing_under_load(self, load_tester):
        """Test document processing under load (PDF analysis)"""
        # Arrange
        # Test with typical Italian tax documents
        document_types = {
            "fattura_elettronica": 0.4,
            "f24": 0.3,
            "dichiarazione_redditi": 0.2,
            "contratto": 0.1
        }
        
        metrics = await load_tester.run_test(
            users=30,  # Lower concurrency for heavy operations
            duration=300,
            scenario="document_processing",
            document_types=document_types
        )
        
        # Assert
        doc_metrics = load_tester.get_endpoint_metrics(metrics, "/api/document/analyze")
        
        # Document processing should complete within reasonable time
        assert doc_metrics.p95_response_time < 30.0, \
            f"Document processing P95 time {doc_metrics.p95_response_time}s exceeds 30s"
        
        # Check for document queue buildup
        max_queue_size = load_tester.get_max_queue_size(metrics, "document_processing")
        assert max_queue_size < 100, \
            f"Document processing queue reached {max_queue_size} items"
    
    @pytest.mark.asyncio
    async def test_italian_query_normalization_performance(self, load_tester):
        """Test Italian query normalization performance"""
        # Arrange
        # Test with various Italian language queries
        italian_queries = load_tester.load_italian_test_queries()
        
        metrics = await load_tester.run_test(
            users=50,
            duration=300,
            scenario="custom",
            custom_queries=italian_queries
        )
        
        # Assert
        normalization_overhead = load_tester.get_normalization_overhead(metrics)
        assert normalization_overhead < 50, \
            f"Query normalization adds {normalization_overhead}ms overhead"
        
        # Verify normalized queries still get correct results
        accuracy = load_tester.verify_query_accuracy(metrics)
        assert accuracy > 0.95, \
            f"Query accuracy {accuracy} below 95% threshold"
    
    @pytest.mark.asyncio
    async def test_regulatory_knowledge_queries_at_scale(self, load_tester):
        """Test regulatory knowledge queries at scale"""
        # Arrange
        regulatory_queries = [
            "Circolare Agenzia Entrate 2024",
            "Decreto fiscale ultimo",
            "Normativa fatturazione elettronica",
            "Codice fiscale validazione",
            "Aliquote IVA aggiornate"
        ]
        
        metrics = await load_tester.run_test(
            users=50,
            duration=300,
            scenario="custom",
            custom_queries=regulatory_queries
        )
        
        # Assert
        # Knowledge queries should be efficient
        knowledge_metrics = load_tester.get_endpoint_metrics(metrics, "/api/knowledge/search")
        assert knowledge_metrics.p95_response_time < 3.0, \
            f"Knowledge search P95 time {knowledge_metrics.p95_response_time}s exceeds 3s"
        
        # Verify index performance
        index_metrics = load_tester.get_search_index_metrics(metrics)
        assert index_metrics.avg_search_time < 100, \
            f"Search index average time {index_metrics.avg_search_time}ms too high"
    
    @pytest.mark.asyncio
    async def test_gdpr_operations_under_load(self, load_tester):
        """Test GDPR operations (data export/deletion) under load"""
        # Arrange
        gdpr_operations = {
            "data_export": 0.7,     # 70% export requests
            "data_deletion": 0.2,   # 20% deletion requests
            "data_update": 0.1      # 10% update requests
        }
        
        # Lower concurrency for GDPR operations
        metrics = await load_tester.run_test(
            users=20,
            duration=300,
            scenario="gdpr_operations",
            operation_weights=gdpr_operations
        )
        
        # Assert
        gdpr_metrics = load_tester.get_endpoint_group_metrics(metrics, "/api/gdpr/*")
        
        # GDPR operations should complete even if slower
        assert gdpr_metrics.success_rate > 0.99, \
            f"GDPR operation success rate {gdpr_metrics.success_rate} below 99%"
        
        # Data export should be reasonably fast
        export_metrics = load_tester.get_endpoint_metrics(metrics, "/api/gdpr/export")
        assert export_metrics.p95_response_time < 60.0, \
            f"Data export P95 time {export_metrics.p95_response_time}s exceeds 60s"
        
        # Verify data consistency during concurrent operations
        consistency_check = await load_tester.verify_data_consistency_after_test()
        assert consistency_check.is_consistent, \
            f"Data consistency issues found: {consistency_check.issues}"


@pytest.fixture
async def load_tester():
    """Provide load testing framework instance"""
    from load_testing.framework import LoadTestFramework
    
    tester = LoadTestFramework(
        base_url="http://localhost:8000",
        enable_monitoring=True
    )
    
    # Setup test data
    await tester.setup_test_users(count=200)
    await tester.setup_test_documents()
    await tester.warmup_cache()
    
    yield tester
    
    # Cleanup
    await tester.cleanup()


class TestLoadTestReporting:
    """Test load test reporting and analysis"""
    
    @pytest.mark.asyncio
    async def test_performance_baseline_establishment(self, load_tester):
        """Test that performance baselines are properly established"""
        # Arrange
        baseline_metrics = await load_tester.establish_baseline()
        
        # Assert
        assert baseline_metrics.single_user_p95 is not None
        assert baseline_metrics.optimal_throughput is not None
        assert baseline_metrics.resource_limits is not None
        
        # Verify baseline is reasonable
        assert 0.5 < baseline_metrics.single_user_p95 < 3.0, \
            "Baseline response time outside expected range"
    
    @pytest.mark.asyncio
    async def test_bottleneck_identification(self, load_tester):
        """Test automatic bottleneck identification"""
        # Arrange
        metrics = await load_tester.run_test(
            users=100,
            duration=300,
            scenario="mixed",
            identify_bottlenecks=True
        )
        
        bottlenecks = load_tester.identify_bottlenecks(metrics)
        
        # Assert
        assert isinstance(bottlenecks, list)
        
        # Verify bottleneck detection works
        if metrics.avg_cpu_usage > 80:
            assert any(b.type == "CPU" for b in bottlenecks), \
                "Failed to identify CPU bottleneck"
        
        if max(metrics.db_connections) > 80:
            assert any(b.type == "DATABASE" for b in bottlenecks), \
                "Failed to identify database bottleneck"
    
    @pytest.mark.asyncio
    async def test_scaling_recommendations(self, load_tester):
        """Test that appropriate scaling recommendations are provided"""
        # Arrange
        metrics = await load_tester.run_test(
            users=100,
            duration=300,
            scenario="mixed"
        )
        
        recommendations = load_tester.generate_scaling_recommendations(metrics)
        
        # Assert
        assert len(recommendations) > 0
        
        # Verify recommendations are actionable
        for rec in recommendations:
            assert rec.priority in ["HIGH", "MEDIUM", "LOW"]
            assert rec.estimated_improvement > 0
            assert rec.implementation_effort in ["LOW", "MEDIUM", "HIGH"]


class TestCIIntegration:
    """Test CI/CD integration for load testing"""
    
    @pytest.mark.asyncio
    async def test_load_test_ci_workflow(self, load_tester):
        """Test that load tests can run in CI environment"""
        # Arrange
        ci_config = {
            "users": 20,  # Lower for CI
            "duration": 120,
            "fail_on_degradation": True,
            "baseline_comparison": True
        }
        
        # Act
        result = await load_tester.run_ci_test(ci_config)
        
        # Assert
        assert result.exit_code in [0, 1], "Invalid CI exit code"
        assert result.report_path.exists(), "CI report not generated"
        assert result.metrics_uploaded, "Metrics not uploaded to monitoring"
    
    @pytest.mark.asyncio
    async def test_performance_regression_detection(self, load_tester):
        """Test detection of performance regressions"""
        # Arrange
        baseline = await load_tester.load_baseline_metrics()
        current = await load_tester.run_test(
            users=50,
            duration=300,
            scenario="mixed"
        )
        
        # Act
        regression = load_tester.detect_regression(baseline, current)
        
        # Assert
        if regression.detected:
            assert regression.severity in ["LOW", "MEDIUM", "HIGH"]
            assert len(regression.degraded_metrics) > 0
            assert regression.recommended_action is not None