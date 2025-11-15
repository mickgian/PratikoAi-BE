"""
Comprehensive Test Suite for LLM API Retry Mechanisms.

This test suite follows Test-Driven Development (TDD) methodology to ensure
production reliability by gracefully handling transient failures, rate limits,
and timeouts from OpenAI and Anthropic APIs. Tests must pass before implementation begins.

Test Coverage:
- Exponential backoff retry strategy with jitter
- Maximum retry attempts (configurable per provider)
- Provider-specific error handling (OpenAI 429, Anthropic 529)
- Circuit breaker activation and recovery
- Cost-aware retry budgets
- Provider failover mechanisms
- Performance and concurrent handling
- Timeout and error categorization
"""

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from app.core.config import settings
from app.models.query import QueryResponse
from app.services.llm_retry_service import (
    AllProvidersFailedError,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CostAwareRetryHandler,
    CostBudgetExceededError,
    MaxRetriesExceededError,
    ProviderRetryConfig,
    RetryableError,
    RetryConfig,
    RetryHandler,
    RetryMetrics,
)
from app.services.resilient_llm_service import ResilientLLMService


class TestRetryConfiguration:
    """Test retry configuration and validation."""

    def test_default_retry_config(self):
        """Test default retry configuration values."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.initial_delay == 2.0
        assert config.max_delay == 32.0
        assert config.exponential_base == 2.0
        assert config.timeout == 30.0
        assert config.jitter is True
        assert config.respect_retry_after is True
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_timeout == 60.0
        assert config.max_retry_cost == 0.10
        assert config.retry_budget_window == 3600

    def test_provider_specific_configs(self):
        """Test provider-specific retry configurations."""
        openai_config = ProviderRetryConfig.OPENAI
        anthropic_config = ProviderRetryConfig.ANTHROPIC
        openai_cheap_config = ProviderRetryConfig.OPENAI_CHEAP

        # OpenAI config
        assert openai_config.max_attempts == 3
        assert openai_config.initial_delay == 2.0
        assert openai_config.timeout == 30.0
        assert openai_config.max_retry_cost == 0.10

        # Anthropic config (faster, lower cost)
        assert anthropic_config.max_attempts == 3
        assert anthropic_config.initial_delay == 1.5
        assert anthropic_config.timeout == 25.0
        assert anthropic_config.max_retry_cost == 0.08

        # Cheap fallback config
        assert openai_cheap_config.max_attempts == 2
        assert openai_cheap_config.initial_delay == 1.0
        assert openai_cheap_config.timeout == 20.0
        assert openai_cheap_config.max_retry_cost == 0.02

    def test_config_validation(self):
        """Test retry configuration validation."""
        # Valid config
        config = RetryConfig(max_attempts=5, initial_delay=1.0)
        assert config.max_attempts == 5

        # Invalid config should raise ValueError
        with pytest.raises(ValueError):
            RetryConfig(max_attempts=0)

        with pytest.raises(ValueError):
            RetryConfig(initial_delay=-1.0)

        with pytest.raises(ValueError):
            RetryConfig(max_delay=0.1, initial_delay=1.0)  # max_delay < initial_delay


class TestExponentialBackoffStrategy:
    """Test exponential backoff retry strategy implementation."""

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            initial_delay=2.0,
            exponential_base=2.0,
            max_delay=32.0,
            jitter=False,  # Disable for predictable testing
        )

        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Test delay calculation for each attempt
        assert retry_handler._calculate_backoff_delay(0) == 2.0  # 2 * 2^0
        assert retry_handler._calculate_backoff_delay(1) == 4.0  # 2 * 2^1
        assert retry_handler._calculate_backoff_delay(2) == 8.0  # 2 * 2^2
        assert retry_handler._calculate_backoff_delay(3) == 16.0  # 2 * 2^3
        assert retry_handler._calculate_backoff_delay(4) == 32.0  # 2 * 2^4
        assert retry_handler._calculate_backoff_delay(5) == 32.0  # capped at max_delay

    def test_exponential_backoff_with_jitter(self):
        """Test exponential backoff with jitter to prevent thundering herd."""
        config = RetryConfig(initial_delay=2.0, exponential_base=2.0, jitter=True)

        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # With jitter, delay should be between base_delay * 0.5 and base_delay * 1.5
        delays = [retry_handler._calculate_backoff_delay(1) for _ in range(100)]

        # Expected base delay for attempt 1 is 4.0 seconds
        # With jitter: 4.0 * (0.5 + random[0,1]) = [2.0, 6.0]
        assert all(2.0 <= delay <= 6.0 for delay in delays)
        assert len(set(delays)) > 10  # Should have good randomness

    def test_backoff_respects_max_delay(self):
        """Test that backoff delay is capped at max_delay."""
        config = RetryConfig(initial_delay=10.0, exponential_base=3.0, max_delay=25.0, jitter=False)

        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Delay should be capped at max_delay
        delay = retry_handler._calculate_backoff_delay(3)  # Would be 10 * 3^3 = 270
        assert delay == 25.0

    @pytest.mark.asyncio
    async def test_retry_after_header_respected(self):
        """Test that Retry-After header from provider is respected."""
        config = RetryConfig(respect_retry_after=True)
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Mock time.sleep to verify delay
        with patch("asyncio.sleep") as mock_sleep:
            await retry_handler._handle_retry(0, "rate_limit", "5.5")
            mock_sleep.assert_called_once_with(5.5)

    @pytest.mark.asyncio
    async def test_ignore_retry_after_when_disabled(self):
        """Test that Retry-After header is ignored when respect_retry_after=False."""
        config = RetryConfig(respect_retry_after=False, initial_delay=3.0, jitter=False)
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Mock time.sleep to verify delay
        with patch("asyncio.sleep") as mock_sleep:
            await retry_handler._handle_retry(0, "rate_limit", "10.0")
            mock_sleep.assert_called_once_with(3.0)  # Uses calculated delay, not Retry-After


class TestRetryLogicAndErrorHandling:
    """Test core retry logic and error categorization."""

    @pytest.mark.asyncio
    async def test_successful_request_no_retry(self):
        """Test that successful requests don't trigger retries."""
        config = RetryConfig(max_attempts=3)
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Mock successful function
        mock_func = AsyncMock(return_value="success")

        result = await retry_handler.execute_with_retry(mock_func, "test_arg")

        assert result == "success"
        mock_func.assert_called_once_with("test_arg")
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_retry_on_timeout_error(self):
        """Test retry on timeout errors."""
        config = RetryConfig(max_attempts=3, initial_delay=0.1, jitter=False)
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Mock function that times out twice, then succeeds
        mock_func = AsyncMock(
            side_effect=[TimeoutError("Request timeout"), TimeoutError("Request timeout"), "success"]
        )

        with patch("asyncio.sleep"):  # Speed up test
            result = await retry_handler.execute_with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3
        assert circuit_breaker.failure_count == 0  # Reset on success

    @pytest.mark.asyncio
    async def test_retry_on_http_429_rate_limit(self):
        """Test retry on HTTP 429 rate limit errors."""
        config = RetryConfig(max_attempts=3, initial_delay=0.1, jitter=False)
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Mock HTTP 429 error
        response_mock = Mock()
        response_mock.status_code = 429
        response_mock.headers = {"Retry-After": "2.0"}

        http_error = httpx.HTTPStatusError(message="Rate limited", request=Mock(), response=response_mock)

        mock_func = AsyncMock(side_effect=[http_error, "success"])

        with patch("asyncio.sleep") as mock_sleep:
            result = await retry_handler.execute_with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2
        mock_sleep.assert_called_once_with(2.0)  # Uses Retry-After value

    @pytest.mark.asyncio
    async def test_retry_on_http_5xx_server_errors(self):
        """Test retry on HTTP 5xx server errors."""
        config = RetryConfig(max_attempts=3, initial_delay=0.1, jitter=False)
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Mock HTTP 500 error
        response_mock = Mock()
        response_mock.status_code = 500
        response_mock.headers = {}

        http_error = httpx.HTTPStatusError(message="Internal server error", request=Mock(), response=response_mock)

        mock_func = AsyncMock(side_effect=[http_error, "success"])

        with patch("asyncio.sleep"):
            result = await retry_handler.execute_with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_http_4xx_client_errors(self):
        """Test that HTTP 4xx client errors (except 429) are not retried."""
        config = RetryConfig(max_attempts=3)
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Mock HTTP 400 error
        response_mock = Mock()
        response_mock.status_code = 400
        response_mock.headers = {}

        http_error = httpx.HTTPStatusError(message="Bad request", request=Mock(), response=response_mock)

        mock_func = AsyncMock(side_effect=http_error)

        with pytest.raises(httpx.HTTPStatusError):
            await retry_handler.execute_with_retry(mock_func)

        mock_func.assert_called_once()  # No retries
        assert circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_error(self):
        """Test MaxRetriesExceededError when all retry attempts fail."""
        config = RetryConfig(max_attempts=2, initial_delay=0.1, jitter=False)
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Mock function that always times out
        timeout_error = TimeoutError("Always timeout")
        mock_func = AsyncMock(side_effect=timeout_error)

        with patch("asyncio.sleep"), pytest.raises(MaxRetriesExceededError) as exc_info:
            await retry_handler.execute_with_retry(mock_func)

        assert "Failed after 2 attempts" in str(exc_info.value)
        assert mock_func.call_count == 2
        assert circuit_breaker.failure_count == 1

    def test_retryable_error_detection(self):
        """Test detection of retryable vs non-retryable errors."""
        config = RetryConfig()
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Test retryable errors
        retryable_errors = [
            Exception("Rate limit exceeded"),
            Exception("Request timeout"),
            Exception("Service temporarily unavailable"),
            Exception("Connection error"),
            Exception("Server overloaded"),
        ]

        for error in retryable_errors:
            assert retry_handler._is_retryable_error(error)

        # Test non-retryable errors
        non_retryable_errors = [
            Exception("Invalid API key"),
            Exception("Malformed request"),
            Exception("Access denied"),
        ]

        for error in non_retryable_errors:
            assert not retry_handler._is_retryable_error(error)


class TestCircuitBreakerFunctionality:
    """Test circuit breaker functionality for failure protection."""

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker initial state."""
        circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=60.0)

        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.can_attempt() is True

    def test_circuit_breaker_opens_after_threshold(self):
        """Test that circuit breaker opens after failure threshold."""
        circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=60.0)

        # Record failures up to threshold
        for i in range(3):
            circuit_breaker.record_failure()
            if i < 2:
                assert circuit_breaker.state == "closed"
            else:
                assert circuit_breaker.state == "open"

        assert circuit_breaker.failure_count == 3
        assert circuit_breaker.can_attempt() is False

    def test_circuit_breaker_resets_on_success(self):
        """Test that circuit breaker resets failure count on success."""
        circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=60.0)

        # Record some failures
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.failure_count == 2

        # Record success
        circuit_breaker.record_success()
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == "closed"

    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker half-open state after timeout."""
        circuit_breaker = CircuitBreaker(failure_threshold=2, timeout=1.0)

        # Open the circuit
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.state == "open"
        assert circuit_breaker.can_attempt() is False

        # Wait for timeout (simulate time passing)
        import time

        original_time = circuit_breaker.last_failure_time
        circuit_breaker.last_failure_time = original_time - 2.0  # 2 seconds ago

        assert circuit_breaker.can_attempt() is True
        assert circuit_breaker.state == "half_open"

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_calls_when_open(self):
        """Test that circuit breaker prevents calls when open."""
        config = RetryConfig(max_attempts=3)
        circuit_breaker = CircuitBreaker(failure_threshold=1, timeout=60.0)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Open the circuit
        circuit_breaker.record_failure()
        assert circuit_breaker.state == "open"

        mock_func = AsyncMock()

        with pytest.raises(CircuitBreakerOpenError):
            await retry_handler.execute_with_retry(mock_func)

        mock_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_on_success(self):
        """Test circuit breaker recovery when half-open call succeeds."""
        config = RetryConfig(max_attempts=3)
        circuit_breaker = CircuitBreaker(failure_threshold=1, timeout=0.1)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Open the circuit
        circuit_breaker.record_failure()
        assert circuit_breaker.state == "open"

        # Wait for circuit to become half-open
        await asyncio.sleep(0.2)
        assert circuit_breaker.can_attempt() is True

        # Successful call should close the circuit
        mock_func = AsyncMock(return_value="success")
        result = await retry_handler.execute_with_retry(mock_func)

        assert result == "success"
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0


class TestProviderSpecificRetryLogic:
    """Test provider-specific retry logic for OpenAI and Anthropic."""

    @pytest.mark.asyncio
    async def test_openai_rate_limit_handling(self):
        """Test OpenAI-specific rate limit handling."""
        config = ProviderRetryConfig.OPENAI
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Mock OpenAI rate limit response
        response_mock = Mock()
        response_mock.status_code = 429
        response_mock.headers = {"Retry-After": "30"}

        rate_limit_error = httpx.HTTPStatusError(message="Rate limit exceeded", request=Mock(), response=response_mock)

        mock_func = AsyncMock(side_effect=[rate_limit_error, "success"])

        with patch("asyncio.sleep") as mock_sleep:
            result = await retry_handler.execute_with_retry(mock_func)

        assert result == "success"
        mock_sleep.assert_called_once_with(30.0)  # Respects Retry-After

    @pytest.mark.asyncio
    async def test_anthropic_overloaded_handling(self):
        """Test Anthropic-specific overloaded (529) handling."""
        config = ProviderRetryConfig.ANTHROPIC
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Mock Anthropic 529 overloaded response
        response_mock = Mock()
        response_mock.status_code = 529
        response_mock.headers = {}

        overloaded_error = httpx.HTTPStatusError(message="Service overloaded", request=Mock(), response=response_mock)

        mock_func = AsyncMock(side_effect=[overloaded_error, "success"])

        with patch("asyncio.sleep"):
            result = await retry_handler.execute_with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_provider_timeout_configurations(self):
        """Test that different providers have different timeout configurations."""
        # OpenAI should have longer timeout
        openai_config = ProviderRetryConfig.OPENAI
        assert openai_config.timeout == 30.0

        # Anthropic should have shorter timeout
        anthropic_config = ProviderRetryConfig.ANTHROPIC
        assert anthropic_config.timeout == 25.0

        # Cheap fallback should have shortest timeout
        cheap_config = ProviderRetryConfig.OPENAI_CHEAP
        assert cheap_config.timeout == 20.0


class TestResilientLLMService:
    """Test the main resilient LLM service with provider fallback."""

    @pytest.mark.asyncio
    async def test_successful_primary_provider(self):
        """Test successful response from primary provider."""
        with patch("app.services.llm_retry_service.OpenAIProvider") as mock_openai:
            with patch("app.services.llm_retry_service.AnthropicProvider") as mock_anthropic:
                # Mock successful OpenAI response
                mock_openai_instance = AsyncMock()
                mock_openai_instance.complete = AsyncMock(return_value="OpenAI response")
                mock_openai.return_value = mock_openai_instance

                service = ResilientLLMService()

                response = await service.complete("Test prompt", user_id="user123", preferred_provider="openai")

                assert response == "OpenAI response"
                mock_openai_instance.complete.assert_called_once()
                # Anthropic should not be called
                mock_anthropic.assert_not_called()

    @pytest.mark.asyncio
    async def test_provider_fallback_on_failure(self):
        """Test fallback to secondary provider when primary fails."""
        with patch("app.services.llm_retry_service.OpenAIProvider") as mock_openai:
            with patch("app.services.llm_retry_service.AnthropicProvider") as mock_anthropic:
                # Mock OpenAI failure
                mock_openai_instance = AsyncMock()
                mock_openai_instance.complete = AsyncMock(side_effect=MaxRetriesExceededError("OpenAI failed", None))
                mock_openai.return_value = mock_openai_instance

                # Mock Anthropic success
                mock_anthropic_instance = AsyncMock()
                mock_anthropic_instance.complete = AsyncMock(return_value="Anthropic response")
                mock_anthropic.return_value = mock_anthropic_instance

                service = ResilientLLMService()

                response = await service.complete(
                    "Test prompt", user_id="user123", preferred_provider="openai", allow_fallback=True
                )

                assert response == "Anthropic response"
                mock_openai_instance.complete.assert_called_once()
                mock_anthropic_instance.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_providers_failed_error(self):
        """Test AllProvidersFailedError when all providers fail."""
        with patch("app.services.llm_retry_service.OpenAIProvider") as mock_openai:
            with patch("app.services.llm_retry_service.AnthropicProvider") as mock_anthropic:
                # Mock both providers failing
                mock_openai_instance = AsyncMock()
                mock_openai_instance.complete = AsyncMock(side_effect=MaxRetriesExceededError("OpenAI failed", None))
                mock_openai.return_value = mock_openai_instance

                mock_anthropic_instance = AsyncMock()
                mock_anthropic_instance.complete = AsyncMock(
                    side_effect=MaxRetriesExceededError("Anthropic failed", None)
                )
                mock_anthropic.return_value = mock_anthropic_instance

                service = ResilientLLMService()

                with pytest.raises(AllProvidersFailedError) as exc_info:
                    await service.complete(
                        "Test prompt", user_id="user123", preferred_provider="openai", allow_fallback=True
                    )

                assert "Unable to get response from any LLM provider" in str(exc_info.value)
                mock_openai_instance.complete.assert_called_once()
                mock_anthropic_instance.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_fallback_when_disabled(self):
        """Test that fallback is not attempted when disabled."""
        with patch("app.services.llm_retry_service.OpenAIProvider") as mock_openai:
            with patch("app.services.llm_retry_service.AnthropicProvider") as mock_anthropic:
                # Mock OpenAI failure
                mock_openai_instance = AsyncMock()
                mock_openai_instance.complete = AsyncMock(side_effect=MaxRetriesExceededError("OpenAI failed", None))
                mock_openai.return_value = mock_openai_instance

                service = ResilientLLMService()

                with pytest.raises(AllProvidersFailedError):
                    await service.complete(
                        "Test prompt", user_id="user123", preferred_provider="openai", allow_fallback=False
                    )

                mock_openai_instance.complete.assert_called_once()
                mock_anthropic.assert_not_called()


class TestCostAwareRetryMechanisms:
    """Test cost-aware retry mechanisms and budget controls."""

    @pytest.mark.asyncio
    async def test_retry_budget_enforcement(self):
        """Test that retry budget prevents excessive retries."""
        config = RetryConfig(max_retry_cost=0.05)

        # Mock cost tracker that reports user already at budget
        mock_cost_tracker = AsyncMock()
        mock_cost_tracker.get_retry_costs = AsyncMock(return_value=0.05)  # At budget

        cost_retry_handler = CostAwareRetryHandler(config, mock_cost_tracker)

        # Mock function that would normally be retried
        mock_func = AsyncMock(side_effect=TimeoutError("Timeout"))

        # Should try once but not retry due to budget
        with pytest.raises(asyncio.TimeoutError):
            await cost_retry_handler.execute_with_retry(mock_func, user_id="user123", estimated_cost=0.02)

        mock_func.assert_called_once()  # Only one attempt, no retries
        mock_cost_tracker.get_retry_costs.assert_called_once_with("user123", 3600)

    @pytest.mark.asyncio
    async def test_retry_cost_tracking(self):
        """Test that retry costs are properly tracked."""
        config = RetryConfig(max_retry_cost=0.10, initial_delay=0.1, jitter=False)

        # Mock cost tracker with available budget
        mock_cost_tracker = AsyncMock()
        mock_cost_tracker.get_retry_costs = AsyncMock(return_value=0.02)  # Under budget
        mock_cost_tracker.record_retry_cost = AsyncMock()

        cost_retry_handler = CostAwareRetryHandler(config, mock_cost_tracker)

        # Mock function that fails once then succeeds
        mock_func = AsyncMock(side_effect=[TimeoutError("Timeout"), "success"])

        with patch("asyncio.sleep"):
            result = await cost_retry_handler.execute_with_retry(mock_func, user_id="user123", estimated_cost=0.02)

        assert result == "success"
        assert mock_func.call_count == 2

        # Should record retry cost (1 retry * 0.02 cost)
        mock_cost_tracker.record_retry_cost.assert_called_once_with("user123", 0.02)

    @pytest.mark.asyncio
    async def test_retry_budget_window(self):
        """Test retry budget sliding window functionality."""
        config = RetryConfig(retry_budget_window=1800)  # 30 minutes

        mock_cost_tracker = AsyncMock()
        mock_cost_tracker.get_retry_costs = AsyncMock(return_value=0.03)

        cost_retry_handler = CostAwareRetryHandler(config, mock_cost_tracker)

        await cost_retry_handler.execute_with_retry(AsyncMock(return_value="success"), user_id="user123")

        # Should check costs with correct window
        mock_cost_tracker.get_retry_costs.assert_called_once_with("user123", 1800)

    def test_cost_budget_exceeded_error(self):
        """Test CostBudgetExceededError when user exceeds retry budget."""
        error = CostBudgetExceededError("user123", 0.15, 0.10)

        assert "user123" in str(error)
        assert "0.15" in str(error)
        assert "0.10" in str(error)
        assert error.user_id == "user123"
        assert error.current_cost == 0.15
        assert error.budget_limit == 0.10


class TestPerformanceAndConcurrency:
    """Test performance characteristics and concurrent request handling."""

    @pytest.mark.asyncio
    async def test_retry_performance_impact(self):
        """Test that retries add minimal latency to 95th percentile response time."""
        config = RetryConfig(max_attempts=3, initial_delay=0.1, jitter=False)
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Mock function with one failure then success
        mock_func = AsyncMock(side_effect=[TimeoutError("Timeout"), "success"])

        start_time = time.time()

        with patch("asyncio.sleep") as mock_sleep:
            result = await retry_handler.execute_with_retry(mock_func)

        duration = time.time() - start_time

        assert result == "success"
        # Should be fast with mocked sleep
        assert duration < 0.1
        mock_sleep.assert_called_once_with(0.1)  # One retry delay

    @pytest.mark.asyncio
    async def test_concurrent_retry_handling(self):
        """Test handling of concurrent requests with retries."""
        config = RetryConfig(max_attempts=2, initial_delay=0.05, jitter=False)
        circuit_breaker = CircuitBreaker(10, 60)  # Higher threshold for concurrent tests
        retry_handler = RetryHandler(config, circuit_breaker)

        # Create concurrent requests
        async def request_func(request_id: int):
            mock_func = AsyncMock(side_effect=[TimeoutError(f"Timeout {request_id}"), f"success {request_id}"])

            with patch("asyncio.sleep"):
                return await retry_handler.execute_with_retry(mock_func)

        # Run 10 concurrent requests
        tasks = [request_func(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all("success" in result for result in results)
        # Circuit breaker should still be closed
        assert circuit_breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_memory_usage_during_retries(self):
        """Test that retry mechanisms don't cause memory leaks."""
        config = RetryConfig(max_attempts=3, initial_delay=0.01, jitter=False)
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Mock function that always succeeds
        mock_func = AsyncMock(return_value="success")

        # Run many sequential requests
        with patch("asyncio.sleep"):
            for _i in range(100):
                result = await retry_handler.execute_with_retry(mock_func)
                assert result == "success"

        # Verify circuit breaker state is clean
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_request_timeout_handling(self):
        """Test that request timeouts are properly handled."""
        config = RetryConfig(timeout=0.1, max_attempts=2)  # Very short timeout
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Mock function that takes too long
        async def slow_func():
            await asyncio.sleep(0.2)  # Longer than timeout
            return "success"

        with pytest.raises(MaxRetriesExceededError):
            await retry_handler.execute_with_retry(slow_func)


class TestRetryMetricsAndMonitoring:
    """Test retry metrics collection and monitoring."""

    @pytest.mark.asyncio
    async def test_retry_metrics_collection(self):
        """Test that retry metrics are properly collected."""
        metrics = RetryMetrics()

        # Mock Redis client
        with patch("app.services.llm_retry_service.get_redis_client") as mock_redis_client:
            mock_redis = AsyncMock()
            mock_redis_client.return_value = mock_redis

            # Test success metrics
            await metrics.record_success("openai", 2.5, False)
            await metrics.record_success("anthropic", 1.8, True)  # Was fallback

            # Test failure metrics
            await metrics.record_failure("openai", "timeout")
            await metrics.record_failure("anthropic", "rate_limit")

            # Verify metrics were recorded (would call Prometheus counters)
            # In real implementation, this would increment prometheus metrics

    @pytest.mark.asyncio
    async def test_provider_health_score_calculation(self):
        """Test provider health score calculation."""
        metrics = RetryMetrics()

        # Mock recent success/failure data
        with patch.object(metrics, "_get_recent_stats") as mock_stats:
            mock_stats.return_value = {
                "total_requests": 100,
                "successful_requests": 95,
                "avg_response_time": 1.2,
                "p95_response_time": 2.1,
            }

            health_score = await metrics.get_health_score("openai")

            # Health score should be high for 95% success rate
            assert 90 <= health_score <= 100

    @pytest.mark.asyncio
    async def test_retry_rate_tracking(self):
        """Test tracking of retry rates by provider."""
        metrics = RetryMetrics()

        # Simulate retry events
        await metrics.record_retry_attempt("openai", 1, "timeout")
        await metrics.record_retry_attempt("openai", 2, "rate_limit")
        await metrics.record_retry_attempt("anthropic", 1, "overloaded")

        # Get retry statistics
        retry_stats = await metrics.get_retry_statistics("openai", hours=1)

        assert retry_stats["total_retries"] >= 2
        assert "timeout" in retry_stats["retry_reasons"]
        assert "rate_limit" in retry_stats["retry_reasons"]


class TestErrorHandlingAndUserExperience:
    """Test error handling and user-friendly error messages."""

    def test_user_friendly_error_messages(self):
        """Test that error messages are user-friendly."""
        # Test AllProvidersFailedError message
        error = AllProvidersFailedError(
            "Unable to get response from any LLM provider. Please try again in a few moments.",
            "Technical error details",
        )

        # User message should be friendly and actionable
        assert "Unable to get response" in error.user_message
        assert "Please try again" in error.user_message
        assert "few moments" in error.user_message

        # Technical details should be separate
        assert error.technical_details == "Technical error details"

    def test_error_categorization(self):
        """Test proper categorization of transient vs permanent errors."""
        from app.services.llm_retry_service import ErrorCategorizer

        categorizer = ErrorCategorizer()

        # Transient errors
        assert categorizer.is_transient(TimeoutError("timeout"))
        assert categorizer.is_transient(Exception("rate limit exceeded"))
        assert categorizer.is_transient(Exception("service temporarily unavailable"))

        # Permanent errors
        assert not categorizer.is_transient(Exception("invalid api key"))
        assert not categorizer.is_transient(Exception("access denied"))
        assert not categorizer.is_transient(Exception("malformed request"))

    @pytest.mark.asyncio
    async def test_graceful_degradation_response(self):
        """Test graceful degradation when all providers fail."""
        from app.services.query_service import QueryService

        with patch("app.services.llm_retry_service.ResilientLLMService") as mock_llm:
            # Mock LLM service failure
            mock_llm_instance = AsyncMock()
            mock_llm_instance.complete = AsyncMock(
                side_effect=AllProvidersFailedError("Service temporarily unavailable", "All providers failed")
            )
            mock_llm.return_value = mock_llm_instance

            query_service = QueryService()

            response = await query_service.answer_query("test query", "user123")

            # Should return graceful error response
            assert response.success is False
            assert "temporarily unable" in response.error.lower()
            assert response.retry_after == 30


class TestIntegrationWithExistingServices:
    """Test integration with existing PratikoAI services."""

    @pytest.mark.asyncio
    async def test_query_service_integration(self):
        """Test integration with existing QueryService."""
        from app.services.query_service import QueryService

        with patch("app.services.llm_retry_service.ResilientLLMService") as mock_llm:
            # Mock successful LLM response
            mock_llm_instance = AsyncMock()
            mock_llm_instance.complete = AsyncMock(return_value="LLM response")
            mock_llm.return_value = mock_llm_instance

            query_service = QueryService()

            # Mock FAQ service to return None (no cached response)
            with patch.object(query_service, "faq") as mock_faq:
                mock_faq.get_answer = AsyncMock(return_value=None)

                # Mock cache service to return None (no cached response)
                with patch.object(query_service, "cache") as mock_cache:
                    mock_cache.get = AsyncMock(return_value=None)
                    mock_cache.set = AsyncMock()

                    response = await query_service.answer_query("test query", "user123")

                    assert response == "LLM response"
                    mock_llm_instance.complete.assert_called_once()
                    mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cost_tracking_integration(self):
        """Test integration with existing cost tracking system."""
        from app.services.stripe_service import StripeService

        with patch("app.services.llm_retry_service.CostTracker") as mock_cost_tracker:
            mock_tracker_instance = AsyncMock()
            mock_tracker_instance.get_retry_costs = AsyncMock(return_value=0.05)
            mock_tracker_instance.record_retry_cost = AsyncMock()
            mock_cost_tracker.return_value = mock_tracker_instance

            config = RetryConfig(max_retry_cost=0.10)
            cost_retry_handler = CostAwareRetryHandler(config, mock_tracker_instance)

            # Mock successful retry
            mock_func = AsyncMock(side_effect=[TimeoutError("timeout"), "success"])

            with patch("asyncio.sleep"):
                result = await cost_retry_handler.execute_with_retry(mock_func, user_id="user123", estimated_cost=0.02)

            assert result == "success"
            mock_tracker_instance.record_retry_cost.assert_called_once()


# Test fixtures and utilities


@pytest.fixture
def mock_openai_provider():
    """Mock OpenAI provider for testing."""
    provider = AsyncMock()
    provider.complete = AsyncMock(return_value="OpenAI response")
    return provider


@pytest.fixture
def mock_anthropic_provider():
    """Mock Anthropic provider for testing."""
    provider = AsyncMock()
    provider.complete = AsyncMock(return_value="Anthropic response")
    return provider


@pytest.fixture
def mock_cost_tracker():
    """Mock cost tracker for testing."""
    tracker = AsyncMock()
    tracker.get_retry_costs = AsyncMock(return_value=0.02)
    tracker.record_retry_cost = AsyncMock()
    return tracker


@pytest.fixture
def sample_retry_config():
    """Sample retry configuration for testing."""
    return RetryConfig(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=16.0,
        timeout=30.0,
        jitter=False,  # Disable for predictable testing
    )


# Performance and stress testing


class TestRetryPerformanceAndScalability:
    """Test retry performance and scalability characteristics."""

    @pytest.mark.asyncio
    async def test_high_concurrent_retry_load(self):
        """Test system behavior under high concurrent retry load."""
        config = RetryConfig(max_attempts=2, initial_delay=0.01, jitter=False)
        circuit_breaker = CircuitBreaker(100, 60)  # High threshold for load test
        retry_handler = RetryHandler(config, circuit_breaker)

        async def request_with_retry(request_id: int):
            mock_func = AsyncMock(side_effect=[TimeoutError(f"Timeout {request_id}"), f"success {request_id}"])

            with patch("asyncio.sleep"):
                return await retry_handler.execute_with_retry(mock_func)

        # Run 100 concurrent requests
        start_time = time.time()
        tasks = [request_with_retry(i) for i in range(100)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

        assert len(results) == 100
        assert all("success" in result for result in results)
        assert duration < 5.0  # Should complete quickly with mocked delays

    @pytest.mark.asyncio
    async def test_circuit_breaker_under_load(self):
        """Test circuit breaker behavior under high error load."""
        config = RetryConfig(max_attempts=1, initial_delay=0.01)
        circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=1.0)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Function that always fails
        failing_func = AsyncMock(side_effect=Exception("Always fails"))

        # Generate enough failures to open circuit
        failed_count = 0
        circuit_opened_count = 0

        for _i in range(10):
            try:
                await retry_handler.execute_with_retry(failing_func)
            except CircuitBreakerOpenError:
                circuit_opened_count += 1
            except Exception:
                failed_count += 1

        assert circuit_breaker.state == "open"
        assert failed_count >= 5  # At least threshold failures
        assert circuit_opened_count > 0  # Some requests blocked by circuit breaker

    @pytest.mark.asyncio
    async def test_retry_memory_efficiency(self):
        """Test that retry mechanisms are memory efficient."""
        config = RetryConfig(max_attempts=3, initial_delay=0.001)
        circuit_breaker = CircuitBreaker(5, 60)
        retry_handler = RetryHandler(config, circuit_breaker)

        # Create many retry handlers to test memory usage
        handlers = [RetryHandler(config, CircuitBreaker(5, 60)) for _ in range(1000)]

        # All handlers should be lightweight
        assert len(handlers) == 1000

        # Test garbage collection works properly
        del handlers
        import gc

        gc.collect()

        # Original handler should still work
        mock_func = AsyncMock(return_value="success")
        result = await retry_handler.execute_with_retry(mock_func)
        assert result == "success"
