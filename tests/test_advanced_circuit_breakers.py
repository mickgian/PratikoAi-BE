"""
Comprehensive TDD Tests for Advanced Circuit Breaker Pattern Enhancements.

Tests all advanced circuit breaker features for PratikoAI:
- Provider-specific circuit breaker isolation
- Advanced circuit states (Open, Closed, Half-Open, Throttled, Maintenance)
- Intelligent failure detection with weighted failures
- Gradual recovery mechanisms with traffic percentage
- Cost-aware circuit breaking with budget limits
- Italian market specific features (peak hours, holidays, tax deadlines)
- Monitoring and alerting capabilities
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4
from enum import Enum

import numpy as np


# Test fixtures and data structures
class CircuitBreakerState(Enum):
    """Advanced circuit breaker states"""
    CLOSED = "closed"           # Normal operation
    OPEN = "open"              # Provider blocked due to failures
    HALF_OPEN = "half_open"    # Testing recovery with limited traffic
    THROTTLED = "throttled"    # Reduced traffic due to degraded performance
    MAINTENANCE = "maintenance" # Manually set for planned downtime


class FailureType(Enum):
    """Different types of failures with weights"""
    CONNECTION_REFUSED = "connection_refused"    # High weight: 1.0
    TIMEOUT = "timeout"                         # Medium weight: 0.7
    RATE_LIMIT = "rate_limit"                  # Low weight: 0.3
    QUALITY_ISSUE = "quality_issue"            # Medium weight: 0.6
    AUTHENTICATION_ERROR = "auth_error"         # High weight: 0.9
    SERVER_ERROR = "server_error"              # High weight: 0.8


@pytest.fixture
def sample_provider_config():
    """Sample provider configuration for testing"""
    return {
        "openai": {
            "failure_threshold": 5,
            "timeout_seconds": 60,
            "recovery_steps": [1, 5, 10, 25, 50, 100],
            "cost_limit_hourly_eur": 100.0,
            "peak_hours_multiplier": 1.5,
            "sliding_window_size": 100,
            "quality_threshold": 0.8
        },
        "anthropic": {
            "failure_threshold": 3,
            "timeout_seconds": 45,
            "recovery_steps": [5, 25, 50, 100],
            "cost_limit_hourly_eur": 80.0,
            "peak_hours_multiplier": 1.3,
            "sliding_window_size": 100,
            "quality_threshold": 0.85
        },
        "gpt35": {
            "failure_threshold": 7,
            "timeout_seconds": 30,
            "recovery_steps": [10, 50, 100],
            "cost_limit_hourly_eur": 50.0,
            "peak_hours_multiplier": 1.2,
            "sliding_window_size": 100,
            "quality_threshold": 0.75
        }
    }


@pytest.fixture
def sample_italian_market_config():
    """Italian market specific configuration"""
    return {
        "business_hours": {
            "start": 9,  # 9 AM
            "end": 18   # 6 PM
        },
        "peak_hours": {
            "start": 10, # 10 AM
            "end": 16   # 4 PM
        },
        "holiday_months": [8],  # August vacation
        "tax_deadline_periods": [
            {"start": "2024-03-01", "end": "2024-03-31"},  # March tax deadline
            {"start": "2024-06-01", "end": "2024-06-30"},  # June deadline
            {"start": "2024-09-01", "end": "2024-09-30"}   # September deadline
        ],
        "regional_preferences": {
            "north": ["openai", "anthropic", "gpt35"],
            "center": ["anthropic", "openai", "gpt35"],
            "south": ["gpt35", "openai", "anthropic"]
        }
    }


@pytest.fixture
def mock_cost_tracker():
    """Mock cost tracking service"""
    tracker = AsyncMock()
    tracker.get_hourly_cost.return_value = 25.0
    tracker.get_daily_cost.return_value = 150.0
    tracker.track_request_cost.return_value = None
    return tracker


@pytest.fixture
def mock_monitoring_service():
    """Mock monitoring and alerting service"""
    service = AsyncMock()
    service.record_metric.return_value = None
    service.send_alert.return_value = None
    service.get_provider_health.return_value = 0.95
    return service


class TestAdvancedCircuitBreakerStates:
    """Test advanced circuit breaker states and transitions"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_state_transitions(self, sample_provider_config):
        """Test all possible state transitions"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "openai"
        
        # Initial state should be CLOSED
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.CLOSED
        
        # Simulate failures to trigger OPEN state
        for _ in range(6):  # Exceed threshold of 5
            await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)
        
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.OPEN
        
        # After timeout, should move to HALF_OPEN
        with patch('time.time', return_value=time.time() + 70):  # 70 seconds later
            state = await manager.get_circuit_state(provider)
            assert state == CircuitBreakerState.HALF_OPEN
        
        # Test THROTTLED state with quality issues
        await manager.record_quality_issue(provider, quality_score=0.5)
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.THROTTLED
        
        # Test MAINTENANCE state
        await manager.set_maintenance_mode(provider, True)
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.MAINTENANCE
    
    @pytest.mark.asyncio
    async def test_throttled_state_traffic_reduction(self, sample_provider_config):
        """Test traffic reduction in THROTTLED state"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "openai"
        
        # Trigger THROTTLED state with quality issues
        for _ in range(3):
            await manager.record_quality_issue(provider, quality_score=0.6)
        
        # Check traffic allowance is reduced
        traffic_allowance = await manager.get_traffic_allowance(provider)
        assert traffic_allowance < 1.0  # Should be less than 100%
        assert traffic_allowance >= 0.25  # Should be at least 25%
        
        # Multiple requests should show throttling
        allowed_requests = 0
        total_requests = 100
        
        for _ in range(total_requests):
            if await manager.should_allow_request(provider):
                allowed_requests += 1
        
        # Should allow approximately traffic_allowance percentage of requests
        expected_allowed = int(total_requests * traffic_allowance)
        assert abs(allowed_requests - expected_allowed) <= 10  # Allow 10% variance
    
    @pytest.mark.asyncio
    async def test_manual_maintenance_mode(self, sample_provider_config):
        """Test manual maintenance mode override"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "anthropic"
        
        # Set maintenance mode
        await manager.set_maintenance_mode(provider, True, reason="Planned upgrade")
        
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.MAINTENANCE
        
        # All requests should be blocked
        for _ in range(10):
            allowed = await manager.should_allow_request(provider)
            assert not allowed
        
        # Clear maintenance mode
        await manager.set_maintenance_mode(provider, False)
        
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.CLOSED
        
        # Requests should now be allowed
        allowed = await manager.should_allow_request(provider)
        assert allowed


class TestProviderSpecificIsolation:
    """Test provider-specific circuit breaker isolation"""
    
    @pytest.mark.asyncio
    async def test_independent_provider_failure_tracking(self, sample_provider_config):
        """Test that provider failures are tracked independently"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        # OpenAI fails but Anthropic is fine
        for _ in range(6):  # Exceed OpenAI threshold
            await manager.record_failure("openai", FailureType.TIMEOUT)
        
        # OpenAI should be OPEN, Anthropic should be CLOSED
        openai_state = await manager.get_circuit_state("openai")
        anthropic_state = await manager.get_circuit_state("anthropic")
        
        assert openai_state == CircuitBreakerState.OPEN
        assert anthropic_state == CircuitBreakerState.CLOSED
        
        # Only OpenAI requests should be blocked
        openai_allowed = await manager.should_allow_request("openai")
        anthropic_allowed = await manager.should_allow_request("anthropic")
        
        assert not openai_allowed
        assert anthropic_allowed
    
    @pytest.mark.asyncio
    async def test_provider_health_scores(self, sample_provider_config):
        """Test provider health score calculation"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        # Record mixed success/failure patterns for different providers
        
        # OpenAI: 80% success rate
        for _ in range(8):
            await manager.record_success("openai", response_time=200, cost=0.01)
        for _ in range(2):
            await manager.record_failure("openai", FailureType.TIMEOUT)
        
        # Anthropic: 95% success rate
        for _ in range(19):
            await manager.record_success("anthropic", response_time=150, cost=0.015)
        for _ in range(1):
            await manager.record_failure("anthropic", FailureType.RATE_LIMIT)
        
        # Check health scores
        openai_health = await manager.get_provider_health_score("openai")
        anthropic_health = await manager.get_provider_health_score("anthropic")
        
        assert 0.7 <= openai_health <= 0.9
        assert 0.9 <= anthropic_health <= 1.0
        assert anthropic_health > openai_health
    
    @pytest.mark.asyncio
    async def test_partial_service_degradation(self, sample_provider_config):
        """Test system continues with remaining providers when one fails"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        # Make OpenAI fail
        for _ in range(6):
            await manager.record_failure("openai", FailureType.CONNECTION_REFUSED)
        
        # Check available providers
        available_providers = await manager.get_available_providers()
        healthy_providers = await manager.get_healthy_providers()
        
        assert "openai" not in available_providers
        assert "anthropic" in available_providers
        assert "gpt35" in available_providers
        
        assert "openai" not in healthy_providers
        assert len(healthy_providers) >= 2
        
        # Test intelligent routing to healthy providers
        best_provider = await manager.select_best_provider(exclude=["openai"])
        assert best_provider in ["anthropic", "gpt35"]
    
    @pytest.mark.asyncio
    async def test_provider_specific_thresholds(self, sample_provider_config):
        """Test that each provider has different failure thresholds"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        # OpenAI threshold: 5, Anthropic threshold: 3, GPT-3.5 threshold: 7
        
        # Test Anthropic opens first (lowest threshold)
        for i in range(4):  # 4 failures
            await manager.record_failure("openai", FailureType.TIMEOUT)
            await manager.record_failure("anthropic", FailureType.TIMEOUT)
            await manager.record_failure("gpt35", FailureType.TIMEOUT)
            
            if i == 3:  # After 4 failures
                # Only Anthropic should be OPEN (threshold 3)
                assert await manager.get_circuit_state("anthropic") == CircuitBreakerState.OPEN
                assert await manager.get_circuit_state("openai") == CircuitBreakerState.CLOSED
                assert await manager.get_circuit_state("gpt35") == CircuitBreakerState.CLOSED


class TestIntelligentFailureDetection:
    """Test intelligent failure detection with weighted failures"""
    
    @pytest.mark.asyncio
    async def test_weighted_failure_scoring(self, sample_provider_config):
        """Test that different failure types have different weights"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "openai"
        
        # Test high-weight failures trigger circuit faster
        await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)  # Weight: 1.0
        await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)
        await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)
        await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)
        await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)
        
        # Should trigger circuit (5 high-weight failures = threshold)
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.OPEN
        
        # Reset circuit for next test
        await manager.reset_circuit(provider)
        
        # Test low-weight failures need more to trigger
        for _ in range(10):  # Many rate limit failures (weight: 0.3)
            await manager.record_failure(provider, FailureType.RATE_LIMIT)
        
        # Should still be closed (10 * 0.3 = 3.0, below threshold of 5)
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.CLOSED
        
        # Add a few more to trigger
        for _ in range(7):  # Additional rate limits
            await manager.record_failure(provider, FailureType.RATE_LIMIT)
        
        # Now should be open (17 * 0.3 = 5.1, above threshold)
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_sliding_window_failure_tracking(self, sample_provider_config):
        """Test sliding window for failure tracking"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "openai"
        window_size = sample_provider_config[provider]["sliding_window_size"]  # 100
        
        # Fill the sliding window with successes
        for _ in range(window_size):
            await manager.record_success(provider, response_time=200, cost=0.01)
        
        # Add failures beyond threshold
        for _ in range(10):  # High weight failures
            await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)
        
        # Should be open due to recent failures
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.OPEN
        
        # Reset and test old failures don't count
        await manager.reset_circuit(provider)
        
        # Add many successes to push old failures out of window
        for _ in range(window_size + 20):
            await manager.record_success(provider, response_time=200, cost=0.01)
        
        # Circuit should remain closed despite old failures
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_adaptive_thresholds_by_load(self, sample_provider_config):
        """Test adaptive thresholds based on current load"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "openai"
        base_threshold = sample_provider_config[provider]["failure_threshold"]  # 5
        
        # Test high load increases threshold tolerance
        await manager.set_current_load(provider, load_factor=2.0)  # 2x normal load
        adjusted_threshold = await manager.get_adjusted_threshold(provider)
        assert adjusted_threshold > base_threshold
        
        # Test low load decreases threshold tolerance
        await manager.set_current_load(provider, load_factor=0.3)  # 30% of normal
        adjusted_threshold = await manager.get_adjusted_threshold(provider)
        assert adjusted_threshold < base_threshold
    
    @pytest.mark.asyncio
    async def test_quality_issue_detection(self, sample_provider_config):
        """Test detection of quality issues in responses"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "openai"
        quality_threshold = sample_provider_config[provider]["quality_threshold"]  # 0.8
        
        # Record responses with poor quality
        for _ in range(5):
            await manager.record_success(
                provider, 
                response_time=200, 
                cost=0.01, 
                quality_score=0.4  # Poor quality
            )
        
        # Should trigger THROTTLED state
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.THROTTLED
        
        # Test quality recovery
        for _ in range(10):
            await manager.record_success(
                provider,
                response_time=200,
                cost=0.01,
                quality_score=0.9  # Good quality
            )
        
        # Should recover to CLOSED state
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.CLOSED


class TestGradualRecoveryMechanism:
    """Test gradual recovery mechanisms with traffic percentage"""
    
    @pytest.mark.asyncio
    async def test_gradual_traffic_increase(self, sample_provider_config):
        """Test gradual traffic increase during recovery"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "openai"
        recovery_steps = sample_provider_config[provider]["recovery_steps"]  # [1, 5, 10, 25, 50, 100]
        
        # Trigger circuit to OPEN
        for _ in range(6):
            await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)
        
        # Move to HALF_OPEN after timeout
        with patch('time.time', return_value=time.time() + 70):
            await manager.check_recovery_eligibility(provider)
        
        # Test each recovery step
        for i, expected_percentage in enumerate(recovery_steps):
            current_step = await manager.get_recovery_step(provider)
            traffic_percentage = await manager.get_recovery_traffic_percentage(provider)
            
            assert current_step == i
            assert traffic_percentage == expected_percentage / 100.0
            
            # Simulate successful requests at current step
            success_count = int(100 * (expected_percentage / 100.0))
            for _ in range(success_count):
                await manager.record_success(provider, response_time=200, cost=0.01)
            
            # Advance to next step
            if i < len(recovery_steps) - 1:
                await manager.advance_recovery_step(provider)
        
        # Final step should return to CLOSED state
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_recovery_failure_resets_to_open(self, sample_provider_config):
        """Test that failure during recovery resets circuit to OPEN"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "anthropic"
        
        # Trigger circuit to OPEN
        for _ in range(4):
            await manager.record_failure(provider, FailureType.SERVER_ERROR)
        
        # Move to HALF_OPEN
        with patch('time.time', return_value=time.time() + 50):
            await manager.check_recovery_eligibility(provider)
        
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.HALF_OPEN
        
        # Record failure during recovery
        await manager.record_failure(provider, FailureType.TIMEOUT)
        
        # Should reset to OPEN with increased timeout
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.OPEN
        
        # Recovery timeout should be increased
        next_recovery_time = await manager.get_next_recovery_time(provider)
        original_timeout = sample_provider_config[provider]["timeout_seconds"]
        assert next_recovery_time > time.time() + original_timeout
    
    @pytest.mark.asyncio
    async def test_configurable_recovery_intervals(self, sample_provider_config):
        """Test configurable recovery intervals between providers"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        # OpenAI timeout: 60s, Anthropic timeout: 45s
        providers_and_timeouts = [
            ("openai", 60),
            ("anthropic", 45)
        ]
        
        for provider, expected_timeout in providers_and_timeouts:
            # Trigger circuit
            threshold = sample_provider_config[provider]["failure_threshold"]
            for _ in range(threshold + 1):
                await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)
            
            # Check recovery time
            next_recovery = await manager.get_next_recovery_time(provider)
            expected_recovery = time.time() + expected_timeout
            
            assert abs(next_recovery - expected_recovery) < 5  # 5 second tolerance
    
    @pytest.mark.asyncio
    async def test_concurrent_provider_recovery(self, sample_provider_config):
        """Test multiple providers can recover independently"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        # Make all providers fail
        for provider in ["openai", "anthropic", "gpt35"]:
            threshold = sample_provider_config[provider]["failure_threshold"]
            for _ in range(threshold + 1):
                await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)
        
        # All should be OPEN
        for provider in ["openai", "anthropic", "gpt35"]:
            state = await manager.get_circuit_state(provider)
            assert state == CircuitBreakerState.OPEN
        
        # Advance time and recover Anthropic only (shortest timeout: 45s)
        with patch('time.time', return_value=time.time() + 50):
            await manager.check_recovery_eligibility("anthropic")
            
            # Only Anthropic should be HALF_OPEN
            assert await manager.get_circuit_state("anthropic") == CircuitBreakerState.HALF_OPEN
            assert await manager.get_circuit_state("openai") == CircuitBreakerState.OPEN
            assert await manager.get_circuit_state("gpt35") == CircuitBreakerState.OPEN
        
        # Recover Anthropic completely
        for _ in range(10):
            await manager.record_success("anthropic", response_time=150, cost=0.015)
        
        await manager.complete_recovery("anthropic")
        assert await manager.get_circuit_state("anthropic") == CircuitBreakerState.CLOSED


class TestCostAwareCircuitBreaking:
    """Test cost-aware circuit breaking with budget limits"""
    
    @pytest.mark.asyncio
    async def test_cost_limit_circuit_breaking(self, sample_provider_config, mock_cost_tracker):
        """Test circuit opens when cost limits are exceeded"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        # Mock high costs for OpenAI
        mock_cost_tracker.get_hourly_cost.return_value = 120.0  # Above €100 limit
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=mock_cost_tracker,
            monitoring=AsyncMock()
        )
        
        provider = "openai"
        
        # Check cost limits
        is_over_budget = await manager.is_over_cost_budget(provider)
        assert is_over_budget
        
        # Circuit should open due to cost
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.OPEN
        
        # Requests should be blocked
        allowed = await manager.should_allow_request(provider)
        assert not allowed
    
    @pytest.mark.asyncio
    async def test_automatic_routing_to_cheaper_providers(self, sample_provider_config, mock_cost_tracker):
        """Test automatic routing to cheaper providers when budget exceeded"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        # Mock costs: OpenAI expensive, others cheap
        def mock_get_hourly_cost(provider):
            costs = {"openai": 120.0, "anthropic": 30.0, "gpt35": 15.0}
            return costs.get(provider, 0.0)
        
        mock_cost_tracker.get_hourly_cost.side_effect = mock_get_hourly_cost
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=mock_cost_tracker,
            monitoring=AsyncMock()
        )
        
        # Get available providers considering cost
        available_providers = await manager.get_cost_effective_providers()
        
        assert "openai" not in available_providers  # Too expensive
        assert "anthropic" in available_providers
        assert "gpt35" in available_providers
        
        # Best provider should be cheapest with good health
        best_provider = await manager.select_best_provider(consider_cost=True)
        assert best_provider in ["anthropic", "gpt35"]
    
    @pytest.mark.asyncio
    async def test_cost_spike_detection(self, sample_provider_config, mock_cost_tracker):
        """Test detection of unexpected cost spikes"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=mock_cost_tracker,
            monitoring=AsyncMock()
        )
        
        provider = "anthropic"
        
        # Simulate normal cost pattern
        normal_costs = [0.02, 0.018, 0.021, 0.019, 0.02]
        for cost in normal_costs:
            await manager.record_success(provider, response_time=150, cost=cost)
        
        # Simulate cost spike
        spike_cost = 0.15  # 7.5x normal cost
        await manager.record_success(provider, response_time=150, cost=spike_cost)
        
        # Should detect cost anomaly and trigger THROTTLED state
        has_cost_anomaly = await manager.has_cost_anomaly(provider)
        assert has_cost_anomaly
        
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.THROTTLED
    
    @pytest.mark.asyncio
    async def test_budget_based_traffic_shaping(self, sample_provider_config, mock_cost_tracker):
        """Test traffic shaping based on remaining budget"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        # Mock decreasing budget throughout the hour
        budget_progression = [80.0, 60.0, 40.0, 20.0, 5.0]  # Costs approaching €100 limit
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=mock_cost_tracker,
            monitoring=AsyncMock()
        )
        
        provider = "openai"
        
        for current_cost in budget_progression:
            mock_cost_tracker.get_hourly_cost.return_value = current_cost
            
            traffic_allowance = await manager.get_cost_based_traffic_allowance(provider)
            remaining_budget_percentage = (100.0 - current_cost) / 100.0
            
            # Traffic allowance should correlate with remaining budget
            if remaining_budget_percentage > 0.5:  # >50% budget left
                assert traffic_allowance == 1.0  # Full traffic
            elif remaining_budget_percentage > 0.1:  # >10% budget left
                assert 0.25 <= traffic_allowance <= 0.75  # Throttled
            else:  # <10% budget left
                assert traffic_allowance < 0.1  # Heavily restricted


class TestItalianMarketSpecificFeatures:
    """Test Italian market specific features"""
    
    @pytest.mark.asyncio
    async def test_peak_hour_threshold_adjustments(self, sample_provider_config, sample_italian_market_config):
        """Test threshold adjustments during Italian peak hours"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock(),
            italian_market_config=sample_italian_market_config
        )
        
        provider = "openai"
        base_threshold = sample_provider_config[provider]["failure_threshold"]  # 5
        peak_multiplier = sample_provider_config[provider]["peak_hours_multiplier"]  # 1.5
        
        # Test during peak hours (10 AM - 4 PM Italian time)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 3, 15, 14, 0)  # 2 PM Italian time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            adjusted_threshold = await manager.get_peak_hour_adjusted_threshold(provider)
            expected_threshold = base_threshold * peak_multiplier
            
            assert adjusted_threshold == expected_threshold
            
            # Should tolerate more failures during peak hours
            for _ in range(int(expected_threshold)):
                await manager.record_failure(provider, FailureType.TIMEOUT)
            
            # Should still be CLOSED due to peak hour tolerance
            state = await manager.get_circuit_state(provider)
            assert state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_august_vacation_mode(self, sample_provider_config, sample_italian_market_config):
        """Test reduced thresholds during August vacation period"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock(),
            italian_market_config=sample_italian_market_config
        )
        
        provider = "anthropic"
        base_threshold = sample_provider_config[provider]["failure_threshold"]  # 3
        
        # Test during August (vacation month)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 8, 15, 12, 0)  # August 15th
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            is_vacation_period = await manager.is_vacation_period()
            assert is_vacation_period
            
            adjusted_threshold = await manager.get_vacation_adjusted_threshold(provider)
            assert adjusted_threshold < base_threshold  # More sensitive during vacation
            
            # Should trip circuit earlier during vacation
            for _ in range(2):  # Fewer failures needed
                await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)
            
            state = await manager.get_circuit_state(provider)
            assert state == CircuitBreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_tax_deadline_period_stricter_thresholds(self, sample_provider_config, sample_italian_market_config):
        """Test stricter thresholds during tax deadline periods"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock(),
            italian_market_config=sample_italian_market_config
        )
        
        provider = "gpt35"
        base_threshold = sample_provider_config[provider]["failure_threshold"]  # 7
        
        # Test during March tax deadline period
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 3, 15, 10, 0)  # March 15th
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            is_deadline_period = await manager.is_tax_deadline_period()
            assert is_deadline_period
            
            adjusted_threshold = await manager.get_deadline_adjusted_threshold(provider)
            assert adjusted_threshold < base_threshold  # Stricter during deadlines
            
            # Should be more sensitive to failures during tax deadlines
            failure_count = int(adjusted_threshold) + 1
            for _ in range(failure_count):
                await manager.record_failure(provider, FailureType.QUALITY_ISSUE)
            
            state = await manager.get_circuit_state(provider)
            assert state in [CircuitBreakerState.OPEN, CircuitBreakerState.THROTTLED]
    
    @pytest.mark.asyncio
    async def test_regional_provider_preferences(self, sample_provider_config, sample_italian_market_config):
        """Test regional provider preferences for Italian users"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock(),
            italian_market_config=sample_italian_market_config
        )
        
        # Test different regional preferences
        regions_and_preferences = [
            ("north", ["openai", "anthropic", "gpt35"]),
            ("center", ["anthropic", "openai", "gpt35"]),
            ("south", ["gpt35", "openai", "anthropic"])
        ]
        
        for region, expected_order in regions_and_preferences:
            preferred_providers = await manager.get_regional_provider_preferences(region)
            assert preferred_providers == expected_order
            
            # Best provider should respect regional preferences
            best_provider = await manager.select_best_provider(region=region)
            assert best_provider == expected_order[0]  # Should pick first preference
    
    @pytest.mark.asyncio
    async def test_business_hours_vs_off_hours_behavior(self, sample_provider_config, sample_italian_market_config):
        """Test different behavior during business hours vs off-hours"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock(),
            italian_market_config=sample_italian_market_config
        )
        
        provider = "openai"
        
        # Test during business hours (9 AM - 6 PM)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 3, 15, 11, 0)  # 11 AM
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            is_business_hours = await manager.is_business_hours()
            assert is_business_hours
            
            business_hours_config = await manager.get_business_hours_config(provider)
            assert business_hours_config["stricter_monitoring"] is True
            assert business_hours_config["faster_recovery"] is True
        
        # Test during off-hours
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 3, 15, 22, 0)  # 10 PM
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            is_business_hours = await manager.is_business_hours()
            assert not is_business_hours
            
            off_hours_config = await manager.get_off_hours_config(provider)
            assert off_hours_config["relaxed_thresholds"] is True
            assert off_hours_config["longer_recovery_time"] is True


class TestMonitoringAndAlerting:
    """Test monitoring and alerting capabilities"""
    
    @pytest.mark.asyncio
    async def test_circuit_state_change_alerts(self, sample_provider_config, mock_monitoring_service):
        """Test alerts are sent when circuit states change"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=mock_monitoring_service
        )
        
        provider = "openai"
        
        # Trigger circuit to OPEN
        for _ in range(6):
            await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)
        
        # Should have sent alert for state change
        mock_monitoring_service.send_alert.assert_called()
        alert_calls = mock_monitoring_service.send_alert.call_args_list
        
        # Verify alert content
        latest_alert = alert_calls[-1][1]  # Get kwargs from latest call
        assert latest_alert["severity"] in ["high", "critical"]
        assert provider in latest_alert["message"]
        assert "OPEN" in latest_alert["message"]
    
    @pytest.mark.asyncio
    async def test_provider_health_metrics_recording(self, sample_provider_config, mock_monitoring_service):
        """Test provider health metrics are recorded"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=mock_monitoring_service
        )
        
        provider = "anthropic"
        
        # Record various operations
        await manager.record_success(provider, response_time=150, cost=0.02)
        await manager.record_failure(provider, FailureType.TIMEOUT)
        await manager.record_success(provider, response_time=200, cost=0.015)
        
        # Check metrics were recorded
        mock_monitoring_service.record_metric.assert_called()
        metric_calls = mock_monitoring_service.record_metric.call_args_list
        
        # Should have recorded health score, response time, cost, etc.
        recorded_metrics = [call[0][0] for call in metric_calls]  # First positional arg (metric name)
        assert any("health_score" in metric for metric in recorded_metrics)
        assert any("response_time" in metric for metric in recorded_metrics)
        assert any("cost" in metric for metric in recorded_metrics)
    
    @pytest.mark.asyncio
    async def test_recovery_time_predictions(self, sample_provider_config):
        """Test recovery time prediction accuracy"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "gpt35"
        
        # Trigger circuit to OPEN
        for _ in range(8):
            await manager.record_failure(provider, FailureType.SERVER_ERROR)
        
        # Get recovery prediction
        predicted_recovery_time = await manager.predict_recovery_time(provider)
        configured_timeout = sample_provider_config[provider]["timeout_seconds"]
        
        # Prediction should be based on configured timeout + some variance
        assert predicted_recovery_time >= configured_timeout
        assert predicted_recovery_time <= configured_timeout * 2  # Reasonable upper bound
        
        # Test prediction accuracy after actual recovery
        actual_recovery_start = time.time()
        
        # Simulate recovery process
        with patch('time.time', return_value=time.time() + configured_timeout + 5):
            await manager.check_recovery_eligibility(provider)
            
            # Complete recovery
            for _ in range(10):
                await manager.record_success(provider, response_time=180, cost=0.008)
            
            actual_recovery_time = time.time() - actual_recovery_start
            prediction_error = abs(predicted_recovery_time - actual_recovery_time)
            
            # Prediction should be reasonably accurate (within 50% error)
            assert prediction_error <= predicted_recovery_time * 0.5
    
    @pytest.mark.asyncio
    async def test_cost_impact_analysis(self, sample_provider_config, mock_cost_tracker):
        """Test cost impact analysis when circuits open"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        # Mock cost data
        mock_cost_tracker.get_hourly_cost.side_effect = lambda p: {"openai": 85.0, "anthropic": 45.0}.get(p, 20.0)
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=mock_cost_tracker,
            monitoring=AsyncMock()
        )
        
        # Make OpenAI circuit open
        for _ in range(6):
            await manager.record_failure("openai", FailureType.CONNECTION_REFUSED)
        
        # Analyze cost impact of circuit opening
        cost_impact = await manager.analyze_cost_impact("openai")
        
        assert cost_impact["provider"] == "openai"
        assert cost_impact["circuit_state"] == CircuitBreakerState.OPEN.value
        assert "cost_savings" in cost_impact
        assert "alternative_providers" in cost_impact
        assert cost_impact["cost_savings"] > 0  # Should show savings from not using expensive provider
        
        # Alternative providers should be suggested
        alternatives = cost_impact["alternative_providers"]
        assert len(alternatives) > 0
        assert all(alt["provider"] != "openai" for alt in alternatives)
    
    @pytest.mark.asyncio
    async def test_real_time_dashboard_data(self, sample_provider_config):
        """Test real-time dashboard data generation"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        # Create varied states across providers
        await manager.set_maintenance_mode("openai", True)  # MAINTENANCE
        
        for _ in range(4):  # OPEN
            await manager.record_failure("anthropic", FailureType.CONNECTION_REFUSED)
        
        for _ in range(3):  # THROTTLED (quality issues)
            await manager.record_quality_issue("gpt35", quality_score=0.5)
        
        # Get dashboard data
        dashboard_data = await manager.get_dashboard_data()
        
        assert dashboard_data["timestamp"] is not None
        assert len(dashboard_data["providers"]) == 3
        
        # Check each provider status
        provider_states = {p["name"]: p["state"] for p in dashboard_data["providers"]}
        assert provider_states["openai"] == CircuitBreakerState.MAINTENANCE.value
        assert provider_states["anthropic"] == CircuitBreakerState.OPEN.value
        assert provider_states["gpt35"] == CircuitBreakerState.THROTTLED.value
        
        # Check summary metrics
        assert "total_providers" in dashboard_data["summary"]
        assert "healthy_providers" in dashboard_data["summary"]
        assert "degraded_providers" in dashboard_data["summary"]


class TestSystemIntegration:
    """Test integration with existing systems and backward compatibility"""
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_with_existing_circuit_breaker(self, sample_provider_config):
        """Test backward compatibility with existing CircuitBreaker class"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "openai"
        
        # Test basic circuit breaker interface still works
        is_available = await manager.is_available(provider)
        assert is_available is True
        
        # Record failure using old interface
        await manager.record_failure(provider, FailureType.TIMEOUT)
        
        # Should still track failures properly
        failure_count = await manager.get_failure_count(provider)
        assert failure_count > 0
        
        # Circuit should open when threshold reached
        for _ in range(5):  # Remaining failures to reach threshold
            await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)
        
        is_available = await manager.is_available(provider)
        assert is_available is False
    
    @pytest.mark.asyncio
    async def test_performance_overhead_under_1ms(self, sample_provider_config):
        """Test that circuit state checks add <1ms latency"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "anthropic"
        
        # Warm up
        for _ in range(10):
            await manager.should_allow_request(provider)
        
        # Measure performance
        start_time = time.perf_counter()
        
        for _ in range(100):  # 100 checks
            await manager.should_allow_request(provider)
        
        end_time = time.perf_counter()
        avg_time_per_check = (end_time - start_time) / 100
        
        # Should be well under 1ms (0.001 seconds)
        assert avg_time_per_check < 0.001
        print(f"Average circuit check time: {avg_time_per_check*1000:.3f}ms")
    
    @pytest.mark.asyncio
    async def test_state_persistence_after_restart(self, sample_provider_config):
        """Test state persistence for recovery after restart"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        # Create first manager instance
        manager1 = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock(),
            persistence_enabled=True
        )
        
        provider = "openai"
        
        # Trigger circuit to OPEN
        for _ in range(6):
            await manager1.record_failure(provider, FailureType.CONNECTION_REFUSED)
        
        state1 = await manager1.get_circuit_state(provider)
        assert state1 == CircuitBreakerState.OPEN
        
        # Save state
        await manager1.persist_state()
        
        # Create new manager instance (simulating restart)
        manager2 = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock(),
            persistence_enabled=True
        )
        
        # Load persisted state
        await manager2.load_persisted_state()
        
        # State should be preserved
        state2 = await manager2.get_circuit_state(provider)
        assert state2 == CircuitBreakerState.OPEN
        
        # Should still block requests
        allowed = await manager2.should_allow_request(provider)
        assert not allowed
    
    @pytest.mark.asyncio
    async def test_async_state_updates_non_blocking(self, sample_provider_config):
        """Test async state updates don't block requests"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "gpt35"
        
        # Simulate slow monitoring service
        slow_monitoring = AsyncMock()
        
        async def slow_record_metric(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
        
        slow_monitoring.record_metric.side_effect = slow_record_metric
        manager.monitoring = slow_monitoring
        
        # Measure request processing time
        start_time = time.perf_counter()
        
        # Record success (which triggers async monitoring)
        await manager.record_success(provider, response_time=200, cost=0.01)
        
        # Check request is processed immediately
        allowed = await manager.should_allow_request(provider)
        
        end_time = time.perf_counter()
        processing_time = end_time - start_time
        
        # Should complete quickly despite slow monitoring
        assert processing_time < 0.05  # Less than 50ms
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_memory_efficiency_high_volume(self, sample_provider_config):
        """Test memory efficiency for high-volume operations"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        import psutil
        import os
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate high volume operations
        providers = ["openai", "anthropic", "gpt35"]
        
        for i in range(10000):  # 10,000 operations
            provider = providers[i % 3]
            
            if i % 10 == 0:  # 10% failures
                await manager.record_failure(provider, FailureType.TIMEOUT)
            else:  # 90% successes
                await manager.record_success(provider, response_time=200, cost=0.01)
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 50MB for 10k operations)
        assert memory_increase < 50
        print(f"Memory increase after 10k operations: {memory_increase:.1f}MB")


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_unknown_provider_handling(self, sample_provider_config):
        """Test handling of unknown provider names"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        unknown_provider = "unknown_llm_provider"
        
        # Should handle gracefully without crashing
        state = await manager.get_circuit_state(unknown_provider)
        assert state == CircuitBreakerState.CLOSED  # Default to closed for unknown providers
        
        allowed = await manager.should_allow_request(unknown_provider)
        assert allowed is True  # Allow requests to unknown providers by default
        
        # Should be able to record metrics without error
        await manager.record_success(unknown_provider, response_time=200, cost=0.01)
        await manager.record_failure(unknown_provider, FailureType.TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_invalid_configuration_handling(self):
        """Test handling of invalid configuration"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        invalid_config = {
            "openai": {
                "failure_threshold": -1,  # Invalid negative threshold
                "timeout_seconds": 0,     # Invalid zero timeout
                "recovery_steps": [],     # Empty recovery steps
                "cost_limit_hourly_eur": -100  # Invalid negative cost limit
            }
        }
        
        # Should handle invalid config gracefully
        manager = AdvancedCircuitBreakerManager(
            config=invalid_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        # Should use default values for invalid config
        threshold = await manager.get_failure_threshold("openai")
        assert threshold > 0  # Should have positive default
        
        timeout = await manager.get_recovery_timeout("openai")
        assert timeout > 0  # Should have positive default
    
    @pytest.mark.asyncio
    async def test_concurrent_state_modifications(self, sample_provider_config):
        """Test handling of concurrent state modifications"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "openai"
        
        # Simulate concurrent failures and successes
        async def record_failures():
            for _ in range(10):
                await manager.record_failure(provider, FailureType.TIMEOUT)
                await asyncio.sleep(0.01)  # Small delay
        
        async def record_successes():
            for _ in range(10):
                await manager.record_success(provider, response_time=200, cost=0.01)
                await asyncio.sleep(0.01)  # Small delay
        
        async def check_states():
            for _ in range(20):
                await manager.get_circuit_state(provider)
                await asyncio.sleep(0.005)  # Smaller delay
        
        # Run concurrently
        await asyncio.gather(
            record_failures(),
            record_successes(),
            check_states()
        )
        
        # Should complete without errors and have consistent final state
        final_state = await manager.get_circuit_state(provider)
        assert final_state in [state for state in CircuitBreakerState]
    
    @pytest.mark.asyncio
    async def test_extreme_failure_rates(self, sample_provider_config):
        """Test handling of extreme failure rates"""
        from app.services.advanced_circuit_breaker import AdvancedCircuitBreakerManager
        
        manager = AdvancedCircuitBreakerManager(
            config=sample_provider_config,
            cost_tracker=AsyncMock(),
            monitoring=AsyncMock()
        )
        
        provider = "anthropic"
        
        # Test 100% failure rate
        for _ in range(100):
            await manager.record_failure(provider, FailureType.CONNECTION_REFUSED)
        
        state = await manager.get_circuit_state(provider)
        assert state == CircuitBreakerState.OPEN
        
        health_score = await manager.get_provider_health_score(provider)
        assert health_score < 0.1  # Should be very low
        
        # Test recovery from extreme failure rate
        await manager.reset_circuit(provider)
        
        # Mix of successes and failures
        for _ in range(50):
            await manager.record_success(provider, response_time=150, cost=0.015)
        
        health_score = await manager.get_provider_health_score(provider)
        assert health_score > 0.8  # Should recover


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])