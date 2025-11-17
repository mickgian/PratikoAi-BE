#!/usr/bin/env python3
"""PratikoAI Feature Flag Python SDK

Python client SDK for integrating with the PratikoAI Feature Flag Service.
Designed for use with FastAPI backend services with caching, fallbacks, and real-time updates.
"""

import asyncio
import json
import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import httpx
import redis.asyncio as redis
import websockets
from cachetools import TTLCache

logger = logging.getLogger(__name__)


@dataclass
class EvaluationContext:
    """Context for feature flag evaluation."""

    user_id: str | None = None
    user_attributes: dict[str, str | int | float | bool] = field(default_factory=dict)
    custom_attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class FlagEvaluation:
    """Result of flag evaluation."""

    flag_id: str
    value: str | int | float | bool | dict
    enabled: bool
    reason: str
    targeting_rule_matched: str | None = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class FeatureFlagError(Exception):
    """Base exception for feature flag errors."""

    pass


class FlagNotFoundError(FeatureFlagError):
    """Exception when flag is not found."""

    pass


class ServiceUnavailableError(FeatureFlagError):
    """Exception when flag service is unavailable."""

    pass


class FeatureFlagClient:
    """Python SDK client for PratikoAI Feature Flag Service."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        environment: str = "production",
        cache_ttl: int = 300,  # 5 minutes
        timeout: int = 5,
        enable_real_time: bool = True,
        redis_url: str | None = None,
        fallback_config: dict[str, Any] | None = None,
    ):
        """Initialize the feature flag client.

        Args:
            api_url: URL of the feature flag service
            api_key: API key for authentication
            environment: Environment name (development, staging, production)
            cache_ttl: Cache TTL in seconds
            timeout: HTTP request timeout in seconds
            enable_real_time: Enable real-time updates via WebSocket
            redis_url: Redis URL for distributed caching (optional)
            fallback_config: Fallback flag values when service is unavailable
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.environment = environment
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self.enable_real_time = enable_real_time

        # HTTP client
        self.http_client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "PratikoAI-Python-SDK/1.0.0",
            },
        )

        # Local cache
        self.local_cache = TTLCache(maxsize=1000, ttl=cache_ttl)
        self.cache_lock = threading.RLock()

        # Redis cache (optional)
        self.redis_client = None
        if redis_url:
            self.redis_client = redis.from_url(redis_url)

        # Fallback configuration
        self.fallback_config = fallback_config or {}

        # Real-time updates
        self.websocket = None
        self.websocket_task = None
        self.flag_update_callbacks: list[Callable] = []

        # Metrics
        self.metrics = {"evaluations": 0, "cache_hits": 0, "cache_misses": 0, "api_calls": 0, "errors": 0}

        # Start background tasks
        if enable_real_time:
            asyncio.create_task(self._start_websocket_connection())

    async def is_enabled(
        self,
        flag_id: str,
        user_id: str | None = None,
        user_attributes: dict[str, Any] | None = None,
        default: bool = False,
    ) -> bool:
        """Check if a boolean feature flag is enabled.

        Args:
            flag_id: The feature flag identifier
            user_id: User ID for targeting
            user_attributes: User attributes for targeting
            default: Default value if flag evaluation fails

        Returns:
            True if flag is enabled, False otherwise
        """
        try:
            context = EvaluationContext(user_id=user_id, user_attributes=user_attributes or {})
            evaluation = await self._evaluate_flag(flag_id, context)
            return bool(evaluation.value) if evaluation.enabled else default
        except Exception as e:
            logger.warning(f"Failed to evaluate flag {flag_id}: {e}")
            return self._get_fallback_value(flag_id, default)

    async def get_value(
        self,
        flag_id: str,
        user_id: str | None = None,
        user_attributes: dict[str, Any] | None = None,
        default: Any = None,
    ) -> Any:
        """Get the value of a feature flag.

        Args:
            flag_id: The feature flag identifier
            user_id: User ID for targeting
            user_attributes: User attributes for targeting
            default: Default value if flag evaluation fails

        Returns:
            The flag value or default if evaluation fails
        """
        try:
            context = EvaluationContext(user_id=user_id, user_attributes=user_attributes or {})
            evaluation = await self._evaluate_flag(flag_id, context)
            return evaluation.value if evaluation.enabled else default
        except Exception as e:
            logger.warning(f"Failed to evaluate flag {flag_id}: {e}")
            return self._get_fallback_value(flag_id, default)

    async def get_all_flags(
        self,
        user_id: str | None = None,
        user_attributes: dict[str, Any] | None = None,
        flag_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get values for multiple flags in a single request.

        Args:
            user_id: User ID for targeting
            user_attributes: User attributes for targeting
            flag_ids: List of flag IDs to evaluate (all flags if None)

        Returns:
            Dictionary mapping flag IDs to their values
        """
        try:
            context = EvaluationContext(user_id=user_id, user_attributes=user_attributes or {})

            if flag_ids:
                # Bulk evaluation for specific flags
                return await self._bulk_evaluate_flags(flag_ids, context)
            else:
                # Get all flags for the environment
                return await self._get_environment_flags(context)

        except Exception as e:
            logger.error(f"Failed to get flags: {e}")
            self.metrics["errors"] += 1
            return {}

    async def _evaluate_flag(self, flag_id: str, context: EvaluationContext) -> FlagEvaluation:
        """Evaluate a single flag with caching."""
        self.metrics["evaluations"] += 1

        # Try cache first
        cached_evaluation = await self._get_cached_evaluation(flag_id, context)
        if cached_evaluation:
            self.metrics["cache_hits"] += 1
            return cached_evaluation

        self.metrics["cache_misses"] += 1

        # Call API
        try:
            evaluation = await self._api_evaluate_flag(flag_id, context)
            await self._cache_evaluation(flag_id, context, evaluation)
            return evaluation
        except Exception as e:
            logger.error(f"API evaluation failed for {flag_id}: {e}")
            self.metrics["errors"] += 1
            raise

    async def _api_evaluate_flag(self, flag_id: str, context: EvaluationContext) -> FlagEvaluation:
        """Call the API to evaluate a flag."""
        self.metrics["api_calls"] += 1

        payload = {
            "user_id": context.user_id,
            "user_attributes": context.user_attributes,
            "environment": self.environment,
        }

        url = f"{self.api_url}/api/v1/evaluate"
        params = {"flag_id": flag_id}

        response = await self.http_client.post(url, json=payload, params=params)
        response.raise_for_status()

        data = response.json()
        return FlagEvaluation(
            flag_id=data["flag_id"],
            value=data["value"],
            enabled=data["enabled"],
            reason=data["reason"],
            targeting_rule_matched=data.get("targeting_rule_matched"),
            evaluated_at=datetime.fromisoformat(data["evaluated_at"].replace("Z", "+00:00")),
        )

    async def _bulk_evaluate_flags(self, flag_ids: list[str], context: EvaluationContext) -> dict[str, Any]:
        """Evaluate multiple flags in a single API call."""
        payload = {
            "flag_ids": flag_ids,
            "context": {
                "user_id": context.user_id,
                "user_attributes": context.user_attributes,
                "environment": self.environment,
            },
        }

        url = f"{self.api_url}/api/v1/evaluate/bulk"
        response = await self.http_client.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        result = {}

        for flag_id, evaluation_data in data["evaluations"].items():
            if "error" not in evaluation_data:
                result[flag_id] = evaluation_data["value"]
                # Cache individual evaluations
                evaluation = FlagEvaluation(
                    flag_id=flag_id,
                    value=evaluation_data["value"],
                    enabled=evaluation_data["enabled"],
                    reason=evaluation_data["reason"],
                    targeting_rule_matched=evaluation_data.get("targeting_rule_matched"),
                )
                await self._cache_evaluation(flag_id, context, evaluation)

        return result

    async def _get_environment_flags(self, context: EvaluationContext) -> dict[str, Any]:
        """Get all flags for the current environment."""
        # This would typically be a separate API endpoint
        url = f"{self.api_url}/api/v1/flags"
        params = {"environment": self.environment}

        response = await self.http_client.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        result = {}

        # For each flag, evaluate it with the given context
        for flag in data["flags"]:
            try:
                evaluation = await self._evaluate_flag(flag["flag_id"], context)
                result[flag["flag_id"]] = evaluation.value
            except Exception as e:
                logger.warning(f"Failed to evaluate flag {flag['flag_id']}: {e}")

        return result

    async def _get_cached_evaluation(self, flag_id: str, context: EvaluationContext) -> FlagEvaluation | None:
        """Get cached evaluation if available."""
        cache_key = self._get_cache_key(flag_id, context)

        # Try Redis cache first
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    return FlagEvaluation(**data)
            except Exception as e:
                logger.warning(f"Redis cache error: {e}")

        # Try local cache
        with self.cache_lock:
            cached_data = self.local_cache.get(cache_key)
            if cached_data:
                return FlagEvaluation(**cached_data)

        return None

    async def _cache_evaluation(self, flag_id: str, context: EvaluationContext, evaluation: FlagEvaluation):
        """Cache flag evaluation."""
        cache_key = self._get_cache_key(flag_id, context)
        evaluation_data = {
            "flag_id": evaluation.flag_id,
            "value": evaluation.value,
            "enabled": evaluation.enabled,
            "reason": evaluation.reason,
            "targeting_rule_matched": evaluation.targeting_rule_matched,
            "evaluated_at": evaluation.evaluated_at.isoformat(),
        }

        # Cache in Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(evaluation_data))
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")

        # Cache locally
        with self.cache_lock:
            self.local_cache[cache_key] = evaluation_data

    def _get_cache_key(self, flag_id: str, context: EvaluationContext) -> str:
        """Generate cache key for flag evaluation."""
        # Include user attributes in cache key for targeting
        context_hash = hash(json.dumps(context.user_attributes, sort_keys=True))
        return f"flag:{self.environment}:{flag_id}:{context.user_id}:{context_hash}"

    def _get_fallback_value(self, flag_id: str, default: Any) -> Any:
        """Get fallback value for a flag."""
        fallback = self.fallback_config.get(flag_id)
        if fallback is not None:
            return fallback.get("value", default)
        return default

    async def _start_websocket_connection(self):
        """Start WebSocket connection for real-time updates."""
        if not self.enable_real_time:
            return

        ws_url = self.api_url.replace("http", "ws") + "/ws/flags"

        while True:
            try:
                async with websockets.connect(ws_url) as websocket:
                    self.websocket = websocket
                    logger.info("WebSocket connection established")

                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            await self._handle_websocket_message(data)
                        except Exception as e:
                            logger.error(f"WebSocket message error: {e}")

            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                await asyncio.sleep(30)  # Retry after 30 seconds

    async def _handle_websocket_message(self, data: dict):
        """Handle WebSocket messages for flag updates."""
        message_type = data.get("type")

        if message_type == "flag_updated":
            flag_id = data.get("flag_id")
            environment = data.get("environment")

            if environment == self.environment:
                # Invalidate cache for this flag
                await self._invalidate_flag_cache(flag_id)

                # Notify callbacks
                for callback in self.flag_update_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(flag_id, data)
                        else:
                            callback(flag_id, data)
                    except Exception as e:
                        logger.error(f"Flag update callback error: {e}")

        elif message_type == "heartbeat":
            # Keep connection alive
            pass

    async def _invalidate_flag_cache(self, flag_id: str):
        """Invalidate cache for a specific flag."""
        # Clear Redis cache
        if self.redis_client:
            try:
                pattern = f"flag:{self.environment}:{flag_id}:*"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis cache invalidation error: {e}")

        # Clear local cache
        with self.cache_lock:
            keys_to_remove = [
                key for key in self.local_cache.keys() if key.startswith(f"flag:{self.environment}:{flag_id}:")
            ]
            for key in keys_to_remove:
                del self.local_cache[key]

    def add_flag_update_callback(self, callback: Callable):
        """Add callback for flag update notifications."""
        self.flag_update_callbacks.append(callback)

    def remove_flag_update_callback(self, callback: Callable):
        """Remove flag update callback."""
        if callback in self.flag_update_callbacks:
            self.flag_update_callbacks.remove(callback)

    def get_metrics(self) -> dict[str, int]:
        """Get client metrics."""
        return self.metrics.copy()

    def reset_metrics(self):
        """Reset client metrics."""
        self.metrics = {"evaluations": 0, "cache_hits": 0, "cache_misses": 0, "api_calls": 0, "errors": 0}

    async def close(self):
        """Close the client and cleanup resources."""
        if self.http_client:
            await self.http_client.aclose()

        if self.redis_client:
            await self.redis_client.close()

        if self.websocket:
            await self.websocket.close()

        if self.websocket_task:
            self.websocket_task.cancel()


# Context manager for easier usage
class FeatureFlagContext:
    """Context manager for feature flag client."""

    def __init__(self, client: FeatureFlagClient):
        self.client = client

    async def __aenter__(self):
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()


# Decorator for feature flag gating
def feature_flag(flag_id: str, client: FeatureFlagClient, default: bool = False):
    """Decorator to gate functions behind feature flags."""

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            async def async_wrapper(*args, **kwargs):
                # Try to extract user context from arguments
                user_id = kwargs.get("user_id")
                user_attributes = kwargs.get("user_attributes", {})

                if await client.is_enabled(flag_id, user_id, user_attributes, default):
                    return await func(*args, **kwargs)
                else:
                    logger.info(f"Function {func.__name__} skipped due to feature flag {flag_id}")
                    return None

            return async_wrapper
        else:

            def sync_wrapper(*args, **kwargs):
                # For sync functions, we need to handle the async call
                loop = asyncio.get_event_loop()
                user_id = kwargs.get("user_id")
                user_attributes = kwargs.get("user_attributes", {})

                enabled = loop.run_until_complete(client.is_enabled(flag_id, user_id, user_attributes, default))

                if enabled:
                    return func(*args, **kwargs)
                else:
                    logger.info(f"Function {func.__name__} skipped due to feature flag {flag_id}")
                    return None

            return sync_wrapper

    return decorator


# FastAPI integration
class FastAPIFeatureFlags:
    """FastAPI integration for feature flags."""

    def __init__(self, client: FeatureFlagClient):
        self.client = client

    async def get_user_flags(
        self, user_id: str, user_attributes: dict[str, Any] | None = None, flag_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """Get flags for a user (useful for endpoints)."""
        return await self.client.get_all_flags(user_id, user_attributes, flag_ids)

    def create_flag_dependency(self, flag_id: str, default: bool = False):
        """Create FastAPI dependency for feature flag checking."""

        async def flag_dependency(user_id: str | None = None, user_attributes: dict[str, Any] | None = None):
            return await self.client.is_enabled(flag_id, user_id, user_attributes, default)

        return flag_dependency


# Example usage
async def example_usage():
    """Example of how to use the Python SDK."""
    # Initialize client
    client = FeatureFlagClient(
        api_url="http://localhost:8001",
        api_key="pratiko-dev-key-123",
        environment="development",
        enable_real_time=True,
        fallback_config={"new_dashboard": {"value": False}, "api_rate_limit": {"value": 100}},
    )

    # Simple boolean flag check
    if await client.is_enabled("new_dashboard", user_id="user-123"):
        print("Show new dashboard")
    else:
        print("Show old dashboard")

    # Get configuration value
    rate_limit = await client.get_value("api_rate_limit", user_id="user-123", default=50)
    print(f"Rate limit: {rate_limit}")

    # Get multiple flags
    user_flags = await client.get_all_flags(
        user_id="user-123",
        user_attributes={"country": "US", "tier": "premium"},
        flag_ids=["new_dashboard", "api_rate_limit", "experimental_feature"],
    )
    print(f"User flags: {user_flags}")

    # Add callback for real-time updates
    def on_flag_update(flag_id: str, data: dict):
        print(f"Flag {flag_id} updated: {data}")

    client.add_flag_update_callback(on_flag_update)

    # Use decorator
    @feature_flag("new_api_endpoint", client, default=False)
    async def new_api_feature(user_id: str):
        return {"message": "New API feature enabled"}

    result = await new_api_feature(user_id="user-123")
    print(f"API result: {result}")

    # Get metrics
    metrics = client.get_metrics()
    print(f"Client metrics: {metrics}")

    # Cleanup
    await client.close()


if __name__ == "__main__":
    asyncio.run(example_usage())
