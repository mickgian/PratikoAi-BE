"""
Resilient LLM Service with Provider Fallback for PratikoAI.

This service provides a resilient interface to multiple LLM providers (OpenAI, Anthropic)
with automatic failover, retry mechanisms, and cost-aware request handling. Ensures
high availability and reliability for critical AI functionality.

Features:
- Multi-provider support with automatic failover
- Provider-specific retry configurations
- Circuit breaker protection
- Cost-aware retry budgets
- Request routing and load balancing
- Comprehensive monitoring and metrics
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import logging

from app.services.llm_retry_service import (
    RetryHandler,
    CostAwareRetryHandler,
    RetryConfig,
    ProviderRetryConfig,
    CircuitBreaker,
    CostTracker,
    RetryMetrics,
    CircuitBreakerOpenError,
    MaxRetriesExceededError,
    AllProvidersFailedError,
    CostBudgetExceededError
)
from app.services.openai_provider import OpenAIProvider
from app.services.anthropic_provider import AnthropicProvider
from app.models.query import QueryResponse, LLMResponse
from app.core.logging import logger
from app.core.config import settings


@dataclass
class ProviderConfig:
    """Configuration for LLM provider."""
    name: str
    provider_class: type
    retry_config: RetryConfig
    priority: int  # Lower number = higher priority
    cost_multiplier: float = 1.0  # Relative cost compared to base
    enabled: bool = True


@dataclass 
class LLMRequest:
    """LLM request with metadata."""
    prompt: str
    user_id: str
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    system_prompt: Optional[str] = None
    estimated_cost: Optional[float] = None
    preferred_provider: Optional[str] = None
    allow_fallback: bool = True
    timeout: Optional[float] = None


@dataclass
class LLMResult:
    """LLM response with metadata."""
    response: str
    provider_used: str
    model_used: str
    tokens_used: int
    actual_cost: float
    processing_time: float
    was_fallback: bool
    retry_count: int
    request_id: str


class ResilientLLMService:
    """
    Main resilient LLM service with multi-provider support.
    
    This service automatically handles:
    - Provider selection and fallback
    - Retry logic with exponential backoff
    - Circuit breaker protection
    - Cost tracking and budget enforcement
    - Performance monitoring and metrics
    """
    
    def __init__(self):
        """Initialize resilient LLM service."""
        self.settings = settings
        
        # Initialize providers with configurations
        self.provider_configs = {
            "openai": ProviderConfig(
                name="openai",
                provider_class=OpenAIProvider,
                retry_config=ProviderRetryConfig.OPENAI,
                priority=1,
                cost_multiplier=1.0,
                enabled=True
            ),
            "anthropic": ProviderConfig(
                name="anthropic", 
                provider_class=AnthropicProvider,
                retry_config=ProviderRetryConfig.ANTHROPIC,
                priority=2,
                cost_multiplier=0.8,  # Generally cheaper
                enabled=True
            ),
            "openai_cheap": ProviderConfig(
                name="openai_cheap",
                provider_class=OpenAIProvider,
                retry_config=ProviderRetryConfig.OPENAI_CHEAP,
                priority=3,
                cost_multiplier=0.1,  # Much cheaper model
                enabled=True
            )
        }
        
        # Initialize provider instances
        self.providers = {}
        self.retry_handlers = {}
        self.circuit_breakers = {}
        
        for name, config in self.provider_configs.items():
            if config.enabled:
                # Create provider instance
                if config.name == "openai_cheap":
                    # Use cheaper model for fallback
                    self.providers[name] = config.provider_class(model="gpt-3.5-turbo")
                else:
                    self.providers[name] = config.provider_class()
                
                # Create circuit breaker
                self.circuit_breakers[name] = CircuitBreaker(
                    config.retry_config.circuit_breaker_threshold,
                    config.retry_config.circuit_breaker_timeout
                )
                
                # Create retry handler
                if hasattr(self.settings, 'cost_tracking_enabled') and self.settings.cost_tracking_enabled:
                    cost_tracker = CostTracker()
                    self.retry_handlers[name] = CostAwareRetryHandler(
                        config.retry_config,
                        self.circuit_breakers[name],
                        cost_tracker
                    )
                else:
                    self.retry_handlers[name] = RetryHandler(
                        config.retry_config,
                        self.circuit_breakers[name]
                    )
        
        # Initialize metrics
        self.metrics = RetryMetrics()
        
        # Request tracking
        self._request_counter = 0
        
        logger.info(f"Initialized ResilientLLMService with providers: {list(self.providers.keys())}")
    
    async def complete(
        self,
        prompt: str,
        user_id: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        preferred_provider: str = "openai",
        allow_fallback: bool = True,
        timeout: Optional[float] = None
    ) -> LLMResult:
        """
        Complete text using LLM with resilient handling.
        
        Args:
            prompt: Text prompt for completion
            user_id: User identifier for cost tracking
            model: Specific model to use (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: System prompt/instructions
            preferred_provider: Preferred provider name
            allow_fallback: Whether to allow fallback to other providers
            timeout: Request timeout override
            
        Returns:
            LLMResult with response and metadata
            
        Raises:
            AllProvidersFailedError: When all providers fail
            CostBudgetExceededError: When user exceeds cost budget
        """
        request = LLMRequest(
            prompt=prompt,
            user_id=user_id,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
            estimated_cost=self._estimate_cost(prompt, max_tokens),
            preferred_provider=preferred_provider,
            allow_fallback=allow_fallback,
            timeout=timeout
        )
        
        return await self._execute_request(request)
    
    async def _execute_request(self, request: LLMRequest) -> LLMResult:
        """Execute LLM request with provider fallback."""
        self._request_counter += 1
        request_id = f"req_{int(time.time())}_{self._request_counter}"
        
        start_time = time.time()
        
        # Determine provider order
        providers_to_try = self._get_provider_order(
            request.preferred_provider,
            request.allow_fallback
        )
        
        logger.info(
            f"[{request_id}] Starting LLM request for user {request.user_id}, "
            f"providers: {providers_to_try}"
        )
        
        last_error = None
        
        for i, provider_name in enumerate(providers_to_try):
            if provider_name not in self.providers:
                logger.warning(f"[{request_id}] Provider {provider_name} not available")
                continue
            
            try:
                provider = self.providers[provider_name]
                retry_handler = self.retry_handlers[provider_name]
                was_fallback = i > 0
                
                logger.debug(f"[{request_id}] Trying provider {provider_name}")
                
                # Execute with retry
                response = await retry_handler.execute_with_retry(
                    self._call_provider,
                    provider,
                    request,
                    user_id=request.user_id,
                    estimated_cost=request.estimated_cost * self.provider_configs[provider_name].cost_multiplier
                )
                
                # Success - create result
                processing_time = time.time() - start_time
                
                result = LLMResult(
                    response=response.text,
                    provider_used=provider_name,
                    model_used=response.model or "unknown",
                    tokens_used=response.tokens_used,
                    actual_cost=response.cost,
                    processing_time=processing_time,
                    was_fallback=was_fallback,
                    retry_count=0,  # Would be tracked in retry handler
                    request_id=request_id
                )
                
                # Record success metrics
                await self.metrics.record_success(
                    provider_name,
                    processing_time,
                    was_fallback,
                    request.preferred_provider if was_fallback else None
                )
                
                logger.info(
                    f"[{request_id}] Success with {provider_name} "
                    f"in {processing_time:.2f}s (fallback={was_fallback})"
                )
                
                return result
                
            except CircuitBreakerOpenError as e:
                last_error = f"{provider_name} circuit breaker open"
                logger.warning(f"[{request_id}] {last_error}")
                await self.metrics.record_failure(provider_name, "circuit_breaker")
                continue
                
            except MaxRetriesExceededError as e:
                last_error = f"{provider_name} max retries exceeded"
                logger.error(f"[{request_id}] {last_error}: {e}")
                await self.metrics.record_failure(provider_name, "max_retries")
                continue
                
            except CostBudgetExceededError as e:
                # Don't try other providers if user exceeded budget
                logger.warning(f"[{request_id}] Cost budget exceeded for user {request.user_id}")
                raise
                
            except Exception as e:
                last_error = f"{provider_name} unexpected error: {str(e)}"
                logger.error(f"[{request_id}] {last_error}")
                await self.metrics.record_failure(provider_name, "unexpected_error")
                continue
        
        # All providers failed
        processing_time = time.time() - start_time
        
        logger.error(
            f"[{request_id}] All providers failed in {processing_time:.2f}s, "
            f"last_error: {last_error}"
        )
        
        raise AllProvidersFailedError(
            "Unable to get response from any LLM provider. "
            "Please try again in a few moments.",
            last_error or "All providers failed"
        )
    
    async def _call_provider(
        self,
        provider,
        request: LLMRequest
    ) -> LLMResponse:
        """Call specific provider with request."""
        # Prepare provider-specific parameters
        params = {
            "prompt": request.prompt,
            "user_id": request.user_id
        }
        
        if request.model:
            params["model"] = request.model
        if request.max_tokens:
            params["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            params["temperature"] = request.temperature
        if request.system_prompt:
            params["system_prompt"] = request.system_prompt
        if request.timeout:
            params["timeout"] = request.timeout
        
        # Call provider
        return await provider.complete(**params)
    
    def _get_provider_order(
        self,
        preferred_provider: Optional[str],
        allow_fallback: bool
    ) -> List[str]:
        """Determine order of providers to try."""
        available_providers = [
            name for name, config in self.provider_configs.items()
            if config.enabled and name in self.providers
        ]
        
        if not available_providers:
            return []
        
        # Start with preferred provider if available
        providers_to_try = []
        
        if preferred_provider and preferred_provider in available_providers:
            providers_to_try.append(preferred_provider)
            available_providers.remove(preferred_provider)
        
        # Add fallback providers if allowed
        if allow_fallback:
            # Sort remaining providers by priority
            remaining = sorted(
                available_providers,
                key=lambda name: self.provider_configs[name].priority
            )
            providers_to_try.extend(remaining)
        
        return providers_to_try
    
    def _estimate_cost(self, prompt: str, max_tokens: Optional[int]) -> float:
        """Estimate request cost in EUR."""
        # Rough estimation based on token count
        input_tokens = len(prompt.split()) * 1.3  # Approximate tokens
        output_tokens = max_tokens or 150
        
        # Rough cost estimation (OpenAI GPT-4 pricing)
        input_cost = (input_tokens / 1000) * 0.03  # €0.03 per 1K input tokens
        output_cost = (output_tokens / 1000) * 0.06  # €0.06 per 1K output tokens
        
        return input_cost + output_cost
    
    async def get_provider_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all providers."""
        health_status = {}
        
        for provider_name in self.providers:
            circuit_breaker = self.circuit_breakers[provider_name]
            health_score = await self.metrics.get_health_score(provider_name)
            
            health_status[provider_name] = {
                "enabled": self.provider_configs[provider_name].enabled,
                "circuit_breaker_state": circuit_breaker.state,
                "failure_count": circuit_breaker.failure_count,
                "health_score": health_score,
                "priority": self.provider_configs[provider_name].priority,
                "cost_multiplier": self.provider_configs[provider_name].cost_multiplier
            }
        
        return health_status
    
    async def get_retry_statistics(self, hours: int = 1) -> Dict[str, Any]:
        """Get retry statistics for all providers."""
        stats = {}
        
        for provider_name in self.providers:
            provider_stats = await self.metrics.get_retry_statistics(provider_name, hours)
            stats[provider_name] = provider_stats
        
        return {
            "providers": stats,
            "hours": hours,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def reset_circuit_breaker(self, provider_name: str) -> bool:
        """Manually reset circuit breaker for provider."""
        if provider_name not in self.circuit_breakers:
            return False
        
        circuit_breaker = self.circuit_breakers[provider_name]
        await circuit_breaker.record_success()
        
        logger.info(f"Reset circuit breaker for provider {provider_name}")
        return True
    
    async def disable_provider(self, provider_name: str) -> bool:
        """Temporarily disable a provider."""
        if provider_name not in self.provider_configs:
            return False
        
        self.provider_configs[provider_name].enabled = False
        logger.warning(f"Disabled provider {provider_name}")
        return True
    
    async def enable_provider(self, provider_name: str) -> bool:
        """Re-enable a provider."""
        if provider_name not in self.provider_configs:
            return False
        
        self.provider_configs[provider_name].enabled = True
        logger.info(f"Enabled provider {provider_name}")
        return True


class LLMServiceManager:
    """Manager for LLM service lifecycle and health monitoring."""
    
    def __init__(self):
        """Initialize service manager."""
        self.service = ResilientLLMService()
        self.health_check_interval = 300  # 5 minutes
        self._health_check_task = None
        self._is_running = False
    
    async def start(self):
        """Start the LLM service manager."""
        if self._is_running:
            return
        
        self._is_running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("Started LLM service manager")
    
    async def stop(self):
        """Stop the LLM service manager."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped LLM service manager")
    
    async def _health_check_loop(self):
        """Periodic health check loop."""
        while self._is_running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                await asyncio.sleep(60)  # Shorter interval on error
    
    async def _perform_health_check(self):
        """Perform health check on all providers."""
        health_status = await self.service.get_provider_health()
        
        for provider_name, status in health_status.items():
            # Log warnings for unhealthy providers
            if status["health_score"] < 50:
                logger.warning(
                    f"Provider {provider_name} health score: {status['health_score']:.1f}%"
                )
            
            # Automatically disable providers that are consistently failing
            if (status["circuit_breaker_state"] == "open" and
                status["health_score"] < 25):
                logger.warning(f"Auto-disabling unhealthy provider {provider_name}")
                await self.service.disable_provider(provider_name)
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get overall service status."""
        health_status = await self.service.get_provider_health()
        retry_stats = await self.service.get_retry_statistics()
        
        # Calculate overall health
        enabled_providers = [
            name for name, status in health_status.items()
            if status["enabled"]
        ]
        
        if not enabled_providers:
            overall_health = "critical"
        else:
            avg_health = sum(
                health_status[name]["health_score"]
                for name in enabled_providers
            ) / len(enabled_providers)
            
            if avg_health >= 90:
                overall_health = "excellent"
            elif avg_health >= 70:
                overall_health = "good"
            elif avg_health >= 50:
                overall_health = "degraded"
            else:
                overall_health = "poor"
        
        return {
            "overall_health": overall_health,
            "enabled_providers": enabled_providers,
            "provider_health": health_status,
            "retry_statistics": retry_stats,
            "service_running": self._is_running,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Singleton instance
_service_manager: Optional[LLMServiceManager] = None

async def get_llm_service() -> ResilientLLMService:
    """Get singleton LLM service instance."""
    global _service_manager
    
    if _service_manager is None:
        _service_manager = LLMServiceManager()
        await _service_manager.start()
    
    return _service_manager.service

async def get_llm_service_status() -> Dict[str, Any]:
    """Get LLM service status."""
    global _service_manager
    
    if _service_manager is None:
        return {"status": "not_initialized"}
    
    return await _service_manager.get_service_status()

async def shutdown_llm_service():
    """Shutdown LLM service manager."""
    global _service_manager
    
    if _service_manager:
        await _service_manager.stop()
        _service_manager = None