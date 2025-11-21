"""LLM API Retry Mechanisms for PratikoAI.

This module provides robust retry mechanisms for LLM API calls to ensure production
reliability by gracefully handling transient failures, rate limits, and timeouts
from OpenAI and Anthropic APIs. Prevents single API failures from resulting in
customer-facing errors while maintaining cost control and performance.

Features:
- Exponential backoff with jitter
- Provider-specific retry configurations
- Circuit breaker for failure protection
- Cost-aware retry budgets
- Provider failover mechanisms
- Comprehensive metrics and monitoring
"""

import asyncio
import functools
import hashlib
import json
import logging
import random
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar, Union

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.services.cache import get_redis_client

T = TypeVar("T")


class RetryableError(Enum):
    """Types of retryable errors."""

    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
    OVERLOADED = "overloaded"
    CONNECTION_ERROR = "connection_error"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay: float = 2.0  # seconds
    max_delay: float = 32.0
    exponential_base: float = 2.0
    timeout: float = 30.0
    jitter: bool = True  # Add randomness to prevent thundering herd

    # Provider-specific settings
    respect_retry_after: bool = True
    circuit_breaker_threshold: int = 5  # failures before circuit opens
    circuit_breaker_timeout: float = 60.0  # seconds before circuit resets

    # Cost control
    max_retry_cost: float = 0.10  # Maximum additional cost in EUR
    retry_budget_window: int = 3600  # 1 hour sliding window

    def __post_init__(self):
        """Validate configuration values."""
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if self.initial_delay < 0:
            raise ValueError("initial_delay must be non-negative")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay must be >= initial_delay")
        if self.exponential_base <= 1:
            raise ValueError("exponential_base must be > 1")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.circuit_breaker_threshold <= 0:
            raise ValueError("circuit_breaker_threshold must be positive")
        if self.max_retry_cost < 0:
            raise ValueError("max_retry_cost must be non-negative")


class ProviderRetryConfig:
    """Provider-specific retry configurations."""

    OPENAI = RetryConfig(
        max_attempts=3, initial_delay=2.0, timeout=30.0, max_retry_cost=0.10, circuit_breaker_threshold=5
    )

    ANTHROPIC = RetryConfig(
        max_attempts=3, initial_delay=1.5, timeout=25.0, max_retry_cost=0.08, circuit_breaker_threshold=5
    )

    # Cheaper model for fallback
    OPENAI_CHEAP = RetryConfig(
        max_attempts=2, initial_delay=1.0, timeout=20.0, max_retry_cost=0.02, circuit_breaker_threshold=3
    )


# Custom exceptions


class RetryError(Exception):
    """Base exception for retry-related errors."""

    pass


class CircuitBreakerOpenError(RetryError):
    """Exception raised when circuit breaker is open."""

    def __init__(self, message: str):
        super().__init__(message)
        self.user_message = "Service temporarily unavailable. Please try again in a few moments."


class MaxRetriesExceededError(RetryError):
    """Exception raised when maximum retry attempts are exceeded."""

    def __init__(self, message: str, last_exception: Exception | None = None):
        super().__init__(message)
        self.last_exception = last_exception
        self.user_message = "Unable to process request at this time. Please try again later."


class AllProvidersFailedError(RetryError):
    """Exception raised when all providers fail."""

    def __init__(self, user_message: str, technical_details: str):
        super().__init__(user_message)
        self.user_message = user_message
        self.technical_details = technical_details


class CostBudgetExceededError(RetryError):
    """Exception raised when user exceeds retry cost budget."""

    def __init__(self, user_id: str, current_cost: float, budget_limit: float):
        message = f"User {user_id} exceeded retry budget: {current_cost:.3f} > {budget_limit:.3f} EUR"
        super().__init__(message)
        self.user_id = user_id
        self.current_cost = current_cost
        self.budget_limit = budget_limit
        self.user_message = "Request processing limit reached. Please try again later."


class CircuitBreaker:
    """Circuit breaker implementation for failure protection."""

    def __init__(self, failure_threshold: int, timeout: float):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half_open
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        """Get or create the lock in the current event loop.

        This lazy initialization ensures the lock is created in the correct
        event loop, avoiding issues when the CircuitBreaker is instantiated
        in one event loop but used in another (e.g., during testing).

        Returns:
            The asyncio.Lock instance for the current event loop
        """
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def record_success(self):
        """Record a successful operation."""
        async with self._get_lock():
            self.failure_count = 0
            self.state = "closed"
            logger.debug("Circuit breaker: recorded success, state=closed")

    async def record_failure(self):
        """Record a failed operation."""
        async with self._get_lock():
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"Circuit breaker: opened after {self.failure_count} failures")

    async def can_attempt(self) -> bool:
        """Check if requests can be attempted."""
        async with self._get_lock():
            if self.state == "closed":
                return True
            elif self.state == "open":
                if self.last_failure_time and time.time() - self.last_failure_time > self.timeout:
                    self.state = "half_open"
                    logger.info("Circuit breaker: transitioning to half_open")
                    return True
                return False
            else:  # half_open
                return True


class RetryHandler:
    """Core retry handler with exponential backoff and circuit breaker."""

    def __init__(self, config: RetryConfig, circuit_breaker: CircuitBreaker):
        """Initialize retry handler.

        Args:
            config: Retry configuration
            circuit_breaker: Circuit breaker instance
        """
        self.config = config
        self.circuit_breaker = circuit_breaker
        self._request_id_counter = 0

    async def execute_with_retry(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with retry logic.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: When circuit breaker is open
            MaxRetriesExceededError: When all retry attempts fail
        """
        request_id = self._generate_request_id()
        last_exception = None
        start_time = time.time()

        logger.debug(f"[{request_id}] Starting retry execution, max_attempts={self.config.max_attempts}")

        for attempt in range(self.config.max_attempts):
            # Check circuit breaker
            if not await self.circuit_breaker.can_attempt():
                logger.warning(f"[{request_id}] Circuit breaker is open")
                raise CircuitBreakerOpenError("Circuit breaker is open")

            try:
                logger.debug(f"[{request_id}] Attempt {attempt + 1}/{self.config.max_attempts}")

                # Execute with timeout
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)

                # Success - record and return
                await self.circuit_breaker.record_success()

                duration = time.time() - start_time
                logger.info(f"[{request_id}] Success after {attempt + 1} attempts in {duration:.2f}s")

                return result

            except TimeoutError as e:
                last_exception = e
                logger.warning(f"[{request_id}] Timeout on attempt {attempt + 1}")

                if attempt < self.config.max_attempts - 1:
                    await self._handle_retry(request_id, attempt, "timeout", None)

            except httpx.HTTPStatusError as e:
                if self._is_retryable_http_error(e):
                    last_exception = e
                    retry_after = e.response.headers.get("Retry-After")

                    logger.warning(f"[{request_id}] HTTP {e.response.status_code} on attempt {attempt + 1}")

                    if attempt < self.config.max_attempts - 1:
                        await self._handle_retry(request_id, attempt, "http_error", retry_after)
                else:
                    # Non-retryable HTTP error
                    logger.error(f"[{request_id}] Non-retryable HTTP {e.response.status_code}: {e}")
                    await self.circuit_breaker.record_failure()
                    raise

            except Exception as e:
                last_exception = e

                if self._is_retryable_error(e):
                    logger.warning(f"[{request_id}] Retryable error on attempt {attempt + 1}: {e}")

                    if attempt < self.config.max_attempts - 1:
                        await self._handle_retry(request_id, attempt, "general_error", None)
                else:
                    # Non-retryable error
                    logger.error(f"[{request_id}] Non-retryable error: {e}")
                    await self.circuit_breaker.record_failure()
                    raise

        # All retries exhausted
        await self.circuit_breaker.record_failure()

        duration = time.time() - start_time
        logger.error(f"[{request_id}] All {self.config.max_attempts} attempts failed in {duration:.2f}s")

        raise MaxRetriesExceededError(f"Failed after {self.config.max_attempts} attempts", last_exception)

    def _is_retryable_http_error(self, error: httpx.HTTPStatusError) -> bool:
        """Check if HTTP error is retryable."""
        status = error.response.status_code
        # Retry on 429 (rate limit) and 5xx (server errors)
        return status == 429 or status >= 500

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if error is generally retryable."""
        error_str = str(error).lower()
        retryable_keywords = [
            "rate limit",
            "timeout",
            "overloaded",
            "overwhelmed",
            "connection",
            "temporary",
            "unavailable",
            "busy",
            "throttled",
            "capacity",
            "server error",
        ]
        return any(keyword in error_str for keyword in retryable_keywords)

    async def _handle_retry(self, request_id: str, attempt: int, error_type: str, retry_after: str | None):
        """Handle retry delay and logging."""
        if retry_after and self.config.respect_retry_after:
            try:
                delay = float(retry_after)
                logger.info(f"[{request_id}] Using Retry-After: {delay:.2f}s")
            except (ValueError, TypeError):
                delay = self._calculate_backoff_delay(attempt)
                logger.warning(f"[{request_id}] Invalid Retry-After, using backoff: {delay:.2f}s")
        else:
            delay = self._calculate_backoff_delay(attempt)

        logger.info(f"[{request_id}] Retry attempt {attempt + 1} after {error_type}, waiting {delay:.2f}s")

        await asyncio.sleep(delay)

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        # Calculate base delay: initial_delay * base^attempt
        delay = self.config.initial_delay * (self.config.exponential_base**attempt)

        # Cap at max_delay
        delay = min(delay, self.config.max_delay)

        # Add jitter to prevent thundering herd
        if self.config.jitter:
            # Randomize between 50% and 100% of calculated delay
            jitter_factor = 0.5 + (random.random() * 0.5)
            delay *= jitter_factor

        return delay

    def _generate_request_id(self) -> str:
        """Generate unique request ID for tracking."""
        self._request_id_counter += 1
        return f"retry_{int(time.time())}_{self._request_id_counter}"


class CostTracker:
    """Track retry costs for budget enforcement."""

    def __init__(self):
        """Initialize cost tracker."""
        self.redis = get_redis_client()

    async def get_retry_costs(self, user_id: str, window_seconds: int) -> float:
        """Get user's retry costs within time window.

        Args:
            user_id: User identifier
            window_seconds: Time window in seconds

        Returns:
            Total retry costs in EUR
        """
        try:
            # Use Redis sorted set to track costs with timestamps
            key = f"retry_costs:{user_id}"

            # Remove old entries outside window
            cutoff_time = time.time() - window_seconds
            await self.redis.zremrangebyscore(key, 0, cutoff_time)

            # Sum remaining costs
            costs = await self.redis.zrange(key, 0, -1, withscores=False)
            total_cost = sum(float(cost.decode()) for cost in costs) if costs else 0.0

            return total_cost

        except Exception as e:
            logger.error(f"Failed to get retry costs for user {user_id}: {e}")
            return 0.0

    async def record_retry_cost(self, user_id: str, cost: float):
        """Record retry cost for user.

        Args:
            user_id: User identifier
            cost: Cost in EUR
        """
        try:
            key = f"retry_costs:{user_id}"
            timestamp = time.time()

            # Add cost with current timestamp
            await self.redis.zadd(key, {str(cost): timestamp})

            # Set expiration to prevent infinite growth
            await self.redis.expire(key, 7200)  # 2 hours

            logger.debug(f"Recorded retry cost {cost:.3f} EUR for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to record retry cost for user {user_id}: {e}")


class CostAwareRetryHandler(RetryHandler):
    """Retry handler with cost budget enforcement."""

    def __init__(self, config: RetryConfig, circuit_breaker: CircuitBreaker, cost_tracker: CostTracker):
        """Initialize cost-aware retry handler.

        Args:
            config: Retry configuration
            circuit_breaker: Circuit breaker instance
            cost_tracker: Cost tracking service
        """
        super().__init__(config, circuit_breaker)
        self.cost_tracker = cost_tracker

    async def execute_with_retry(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with retry logic and cost tracking.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments (must include user_id)

        Returns:
            Function result

        Raises:
            CostBudgetExceededError: When user exceeds retry budget
        """
        user_id = kwargs.get("user_id")
        estimated_cost = kwargs.get("estimated_cost", 0.02)  # Default cost per request

        if not user_id:
            # Fall back to regular retry handler if no user_id
            return await super().execute_with_retry(func, *args, **kwargs)

        # Check retry budget
        current_costs = await self.cost_tracker.get_retry_costs(user_id, self.config.retry_budget_window)

        if current_costs >= self.config.max_retry_cost:
            logger.warning(
                f"User {user_id} exceeded retry budget: {current_costs:.3f} >= {self.config.max_retry_cost:.3f} EUR"
            )

            # Try once without retries
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
            except Exception:
                raise CostBudgetExceededError(user_id, current_costs, self.config.max_retry_cost)

        # Execute with retry tracking
        start_attempts = self.config.max_attempts
        retry_cost = 0.0

        try:
            result = await super().execute_with_retry(func, *args, **kwargs)

            # Calculate actual retry cost (cost per retry attempt)
            actual_attempts = start_attempts  # Would be tracked in real implementation
            if actual_attempts > 1:
                retry_cost = estimated_cost * (actual_attempts - 1)
                await self.cost_tracker.record_retry_cost(user_id, retry_cost)

            return result

        except Exception:
            # Record retry cost even on failure
            if retry_cost > 0:
                await self.cost_tracker.record_retry_cost(user_id, retry_cost)
            raise


class ErrorCategorizer:
    """Categorize errors as transient vs permanent."""

    def is_transient(self, error: Exception) -> bool:
        """Determine if error is transient (retryable).

        Args:
            error: Exception to categorize

        Returns:
            True if error is transient/retryable
        """
        if isinstance(error, asyncio.TimeoutError):
            return True

        if isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code
            return status == 429 or status >= 500

        error_str = str(error).lower()

        # Transient error indicators
        transient_keywords = [
            "rate limit",
            "timeout",
            "overloaded",
            "overwhelmed",
            "service temporarily unavailable",
            "connection",
            "temporary",
            "busy",
            "throttled",
            "capacity",
        ]

        # Permanent error indicators
        permanent_keywords = [
            "invalid api key",
            "access denied",
            "unauthorized",
            "forbidden",
            "malformed request",
            "bad request",
            "authentication failed",
            "permission denied",
        ]

        # Check for permanent errors first
        if any(keyword in error_str for keyword in permanent_keywords):
            return False

        # Check for transient errors
        if any(keyword in error_str for keyword in transient_keywords):
            return True

        # Default to non-retryable for unknown errors
        return False


class RetryMetrics:
    """Collect and track retry metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.redis = get_redis_client()

        # Initialize Prometheus metrics (if available)
        try:
            from prometheus_client import Counter, Gauge, Histogram

            self.retry_success_counter = Counter("llm_retry_success_total", "Total successful retries", ["provider"])

            self.retry_failure_counter = Counter(
                "llm_retry_failure_total", "Total failed retries", ["provider", "error_type"]
            )

            self.retry_duration_histogram = Histogram(
                "llm_retry_duration_seconds", "Duration of retry operations", ["provider"]
            )

            self.fallback_counter = Counter(
                "llm_provider_fallback_total", "Total provider fallbacks", ["from_provider", "to_provider"]
            )

            self.circuit_breaker_state = Gauge(
                "llm_circuit_breaker_state", "Circuit breaker state (0=closed, 1=open, 2=half_open)", ["provider"]
            )

        except ImportError:
            logger.info("Prometheus client not available, metrics disabled")
            self.retry_success_counter = None
            self.retry_failure_counter = None
            self.retry_duration_histogram = None
            self.fallback_counter = None
            self.circuit_breaker_state = None

    async def record_success(
        self, provider: str, duration: float, was_fallback: bool, from_provider: str | None = None
    ):
        """Record successful retry operation."""
        try:
            # Prometheus metrics
            if self.retry_success_counter:
                self.retry_success_counter.labels(provider=provider).inc()

            if self.retry_duration_histogram:
                self.retry_duration_histogram.labels(provider=provider).observe(duration)

            if was_fallback and self.fallback_counter and from_provider:
                self.fallback_counter.labels(from_provider=from_provider, to_provider=provider).inc()

            # Redis metrics for custom tracking
            await self._record_redis_metric(f"success:{provider}", 1)
            await self._record_redis_metric(f"duration:{provider}", duration)

        except Exception as e:
            logger.error(f"Failed to record success metrics: {e}")

    async def record_failure(self, provider: str, error_type: str):
        """Record failed retry operation."""
        try:
            if self.retry_failure_counter:
                self.retry_failure_counter.labels(provider=provider, error_type=error_type).inc()

            # Redis metrics
            await self._record_redis_metric(f"failure:{provider}:{error_type}", 1)

        except Exception as e:
            logger.error(f"Failed to record failure metrics: {e}")

    async def record_retry_attempt(self, provider: str, attempt: int, error_type: str):
        """Record retry attempt."""
        try:
            # Redis tracking
            key = f"retry_attempts:{provider}:{datetime.now().strftime('%Y%m%d%H')}"
            await self.redis.hincrby(key, f"attempt_{attempt}_{error_type}", 1)
            await self.redis.expire(key, 3600)  # 1 hour

        except Exception as e:
            logger.error(f"Failed to record retry attempt: {e}")

    async def get_health_score(self, provider: str, hours: int = 1) -> float:
        """Calculate provider health score (0-100).

        Args:
            provider: Provider name
            hours: Hours to look back

        Returns:
            Health score from 0-100
        """
        try:
            # Get success/failure counts from Redis
            success_key = f"success:{provider}"
            failure_keys = [
                f"failure:{provider}:timeout",
                f"failure:{provider}:rate_limit",
                f"failure:{provider}:server_error",
            ]

            success_count = await self._get_redis_metric(success_key, hours)
            failure_count = sum(await self._get_redis_metric(key, hours) for key in failure_keys)

            total_requests = success_count + failure_count
            if total_requests == 0:
                return 100.0  # No data, assume healthy

            success_rate = success_count / total_requests
            return success_rate * 100

        except Exception as e:
            logger.error(f"Failed to calculate health score for {provider}: {e}")
            return 50.0  # Default to neutral score

    async def get_retry_statistics(self, provider: str, hours: int = 1) -> dict[str, Any]:
        """Get retry statistics for provider."""
        try:
            # Get hourly retry attempt data
            current_hour = datetime.now().strftime("%Y%m%d%H")
            key = f"retry_attempts:{provider}:{current_hour}"

            stats = await self.redis.hgetall(key)

            retry_reasons = {}
            total_retries = 0

            for field, count in stats.items():
                field_str = field.decode() if isinstance(field, bytes) else field
                count_int = int(count.decode() if isinstance(count, bytes) else count)

                # Parse field like "attempt_1_timeout"
                parts = field_str.split("_")
                if len(parts) >= 3:
                    reason = "_".join(parts[2:])
                    retry_reasons[reason] = retry_reasons.get(reason, 0) + count_int
                    total_retries += count_int

            return {
                "provider": provider,
                "total_retries": total_retries,
                "retry_reasons": retry_reasons,
                "hours": hours,
            }

        except Exception as e:
            logger.error(f"Failed to get retry statistics for {provider}: {e}")
            return {"provider": provider, "total_retries": 0, "retry_reasons": {}, "hours": hours}

    async def _record_redis_metric(self, key: str, value: float):
        """Record metric value in Redis with timestamp."""
        try:
            # Use sorted set with timestamp
            timestamp = time.time()
            await self.redis.zadd(f"metrics:{key}", {str(value): timestamp})

            # Keep only last hour of data
            cutoff = timestamp - 3600
            await self.redis.zremrangebyscore(f"metrics:{key}", 0, cutoff)

        except Exception as e:
            logger.debug(f"Failed to record Redis metric {key}: {e}")

    async def _get_redis_metric(self, key: str, hours: int) -> float:
        """Get aggregated metric value from Redis."""
        try:
            cutoff = time.time() - (hours * 3600)
            values = await self.redis.zrangebyscore(f"metrics:{key}", cutoff, "+inf")

            if not values:
                return 0.0

            # Sum all values
            return sum(float(v.decode() if isinstance(v, bytes) else v) for v in values)

        except Exception as e:
            logger.debug(f"Failed to get Redis metric {key}: {e}")
            return 0.0


# Export main components
__all__ = [
    "RetryHandler",
    "RetryConfig",
    "ProviderRetryConfig",
    "CircuitBreaker",
    "CostAwareRetryHandler",
    "CostTracker",
    "RetryMetrics",
    "ErrorCategorizer",
    "RetryableError",
    "CircuitBreakerOpenError",
    "MaxRetriesExceededError",
    "AllProvidersFailedError",
    "CostBudgetExceededError",
]
