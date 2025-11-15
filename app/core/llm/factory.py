"""LLM provider factory and routing logic."""

from enum import Enum
from typing import Dict, List, Optional, Union

from app.core.config import settings
from app.core.llm.base import LLMModelTier, LLMProvider, LLMProviderType
from app.core.llm.cost_calculator import CostCalculator, QueryComplexity
from app.core.llm.providers.anthropic_provider import AnthropicProvider
from app.core.llm.providers.openai_provider import OpenAIProvider
from app.core.logging import logger
from app.core.monitoring.metrics import track_api_call, track_llm_cost, track_llm_error
from app.schemas.chat import Message


class RoutingStrategy(str, Enum):
    """LLM routing strategies."""

    COST_OPTIMIZED = "cost_optimized"  # Choose cheapest suitable provider
    QUALITY_FIRST = "quality_first"  # Choose highest quality provider
    BALANCED = "balanced"  # Balance cost and quality
    FAILOVER = "failover"  # Use primary, fallback on failure


class LLMFactory:
    """Factory for creating and managing LLM providers."""

    def __init__(self):
        """Initialize the LLM factory."""
        self.cost_calculator = CostCalculator()
        self._providers: dict[str, LLMProvider] = {}
        self._provider_configs = self._get_provider_configs()

    def _get_provider_configs(self) -> dict[str, dict]:
        """Get provider configurations from settings.

        Returns:
            Dictionary of provider configurations
        """
        configs = {}

        # OpenAI configuration
        if hasattr(settings, "LLM_API_KEY") and settings.LLM_API_KEY:
            configs["openai"] = {
                "api_key": settings.LLM_API_KEY,
                "default_model": getattr(settings, "LLM_MODEL", "gpt-4o-mini"),
                "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            }

        # Anthropic configuration
        if hasattr(settings, "ANTHROPIC_API_KEY") and settings.ANTHROPIC_API_KEY:
            configs["anthropic"] = {
                "api_key": settings.ANTHROPIC_API_KEY,
                "default_model": getattr(settings, "ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
                "models": ["claude-3-haiku-20240307", "claude-3-sonnet-20241022", "claude-3-opus-20240229"],
            }

        return configs

    def create_provider(self, provider_type: str | LLMProviderType, model: str | None = None, **kwargs) -> LLMProvider:
        """Create an LLM provider instance.

        Args:
            provider_type: Type of provider to create
            model: Optional specific model to use
            **kwargs: Additional provider-specific arguments

        Returns:
            LLM provider instance

        Raises:
            ValueError: If provider type is not supported or not configured
        """
        if isinstance(provider_type, str):
            provider_type = LLMProviderType(provider_type)

        provider_key = provider_type.value

        if provider_key not in self._provider_configs:
            raise ValueError(f"Provider {provider_key} is not configured")

        config = self._provider_configs[provider_key]
        model = model or config["default_model"]

        # Create provider instance
        if provider_type == LLMProviderType.OPENAI:
            return OpenAIProvider(api_key=config["api_key"], model=model, **kwargs)
        elif provider_type == LLMProviderType.ANTHROPIC:
            return AnthropicProvider(api_key=config["api_key"], model=model, **kwargs)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    def get_available_providers(self) -> list[LLMProvider]:
        """Get all available configured providers.

        Returns:
            List of available provider instances
        """
        providers = []

        for provider_type_str in self._provider_configs:
            try:
                provider_type = LLMProviderType(provider_type_str)
                provider = self.create_provider(provider_type)
                providers.append(provider)
            except Exception as e:
                logger.warning("provider_creation_failed", provider_type=provider_type_str, error=str(e))

        return providers

    def get_optimal_provider(
        self,
        messages: list[Message],
        strategy: RoutingStrategy = RoutingStrategy.COST_OPTIMIZED,
        max_cost_eur: float | None = None,
        preferred_provider: str | None = None,
        **kwargs,
    ) -> LLMProvider:
        """Get the optimal provider based on routing strategy.

        Args:
            messages: List of conversation messages
            strategy: Routing strategy to use
            max_cost_eur: Maximum acceptable cost in EUR
            preferred_provider: Preferred provider type
            **kwargs: Additional routing parameters

        Returns:
            Optimal LLM provider

        Raises:
            ValueError: If no suitable provider is found
        """
        available_providers = self.get_available_providers()

        if not available_providers:
            raise ValueError("No LLM providers are configured")

        # If preferred provider is specified, try it first
        if preferred_provider:
            try:
                provider = self.create_provider(preferred_provider)
                estimate = self.cost_calculator.calculate_cost_estimate(provider, messages)

                if not max_cost_eur or estimate.total_cost_eur <= max_cost_eur:
                    logger.info(
                        "using_preferred_provider", provider=preferred_provider, estimated_cost=estimate.total_cost_eur
                    )
                    return provider
            except Exception as e:
                logger.warning("preferred_provider_failed", provider=preferred_provider, error=str(e))

        # Apply routing strategy
        if strategy == RoutingStrategy.COST_OPTIMIZED:
            return self._route_cost_optimized(available_providers, messages, max_cost_eur)
        elif strategy == RoutingStrategy.QUALITY_FIRST:
            return self._route_quality_first(available_providers, messages, max_cost_eur)
        elif strategy == RoutingStrategy.BALANCED:
            return self._route_balanced(available_providers, messages, max_cost_eur)
        elif strategy == RoutingStrategy.FAILOVER:
            return self._route_failover(available_providers, messages, max_cost_eur)
        else:
            raise ValueError(f"Unsupported routing strategy: {strategy}")

    def _route_cost_optimized(
        self, providers: list[LLMProvider], messages: list[Message], max_cost_eur: float | None
    ) -> LLMProvider:
        """Route to the cheapest suitable provider.

        Args:
            providers: Available providers
            messages: Conversation messages
            max_cost_eur: Maximum cost constraint

        Returns:
            Cost-optimized provider
        """
        optimal_provider, _ = self.cost_calculator.find_optimal_provider(providers, messages, max_cost_eur)
        return optimal_provider

    def _route_quality_first(
        self, providers: list[LLMProvider], messages: list[Message], max_cost_eur: float | None
    ) -> LLMProvider:
        """Route to the highest quality provider within budget.

        Args:
            providers: Available providers
            messages: Conversation messages
            max_cost_eur: Maximum cost constraint

        Returns:
            Quality-optimized provider
        """
        complexity = self.cost_calculator.classify_query_complexity(messages)

        # Determine minimum tier based on complexity
        tier_mapping = {
            QueryComplexity.SIMPLE: LLMModelTier.BASIC,
            QueryComplexity.MODERATE: LLMModelTier.STANDARD,
            QueryComplexity.COMPLEX: LLMModelTier.ADVANCED,
            QueryComplexity.ADVANCED: LLMModelTier.PREMIUM,
        }

        min_tier = tier_mapping[complexity]

        try:
            optimal_provider, _ = self.cost_calculator.find_optimal_provider(
                providers, messages, max_cost_eur, min_tier
            )
            return optimal_provider
        except ValueError:
            # Fallback to cost optimization if quality requirements can't be met
            logger.warning(
                "quality_requirements_not_met_fallback_to_cost", min_tier=min_tier.value, max_cost_eur=max_cost_eur
            )
            return self._route_cost_optimized(providers, messages, max_cost_eur)

    def _route_balanced(
        self, providers: list[LLMProvider], messages: list[Message], max_cost_eur: float | None
    ) -> LLMProvider:
        """Route using a balanced cost/quality approach.

        Args:
            providers: Available providers
            messages: Conversation messages
            max_cost_eur: Maximum cost constraint

        Returns:
            Balanced provider choice
        """
        complexity = self.cost_calculator.classify_query_complexity(messages)

        # For balanced routing, we use slightly higher tier requirements
        # but with cost constraints
        tier_mapping = {
            QueryComplexity.SIMPLE: LLMModelTier.BASIC,
            QueryComplexity.MODERATE: LLMModelTier.STANDARD,
            QueryComplexity.COMPLEX: LLMModelTier.STANDARD,  # Not premium for complex
            QueryComplexity.ADVANCED: LLMModelTier.ADVANCED,  # Not premium for advanced
        }

        min_tier = tier_mapping[complexity]

        # Set reasonable cost limits if not provided
        if max_cost_eur is None:
            cost_limits = {
                QueryComplexity.SIMPLE: 0.002,  # €0.002
                QueryComplexity.MODERATE: 0.005,  # €0.005
                QueryComplexity.COMPLEX: 0.010,  # €0.010
                QueryComplexity.ADVANCED: 0.020,  # €0.020
            }
            max_cost_eur = cost_limits[complexity]

        try:
            optimal_provider, _ = self.cost_calculator.find_optimal_provider(
                providers, messages, max_cost_eur, min_tier
            )
            return optimal_provider
        except ValueError:
            # Fallback to cost optimization
            return self._route_cost_optimized(providers, messages, max_cost_eur)

    def _route_failover(
        self, providers: list[LLMProvider], messages: list[Message], max_cost_eur: float | None
    ) -> LLMProvider:
        """Route with failover logic - primary provider with fallbacks.

        Args:
            providers: Available providers
            messages: Conversation messages
            max_cost_eur: Maximum cost constraint

        Returns:
            Primary or fallback provider
        """
        # Preferred provider order for failover
        provider_priority = [
            LLMProviderType.OPENAI,  # Primary
            LLMProviderType.ANTHROPIC,  # Fallback
        ]

        for provider_type in provider_priority:
            for provider in providers:
                if provider.provider_type == provider_type:
                    try:
                        # Test connection
                        # Note: This is async, in practice you might want to cache this
                        estimate = self.cost_calculator.calculate_cost_estimate(provider, messages)

                        if not max_cost_eur or estimate.total_cost_eur <= max_cost_eur:
                            logger.info(
                                "failover_provider_selected",
                                provider=provider.provider_type.value,
                                model=provider.model,
                                is_primary=provider_type == provider_priority[0],
                            )
                            return provider
                    except Exception as e:
                        logger.warning("failover_provider_failed", provider=provider.provider_type.value, error=str(e))
                        continue

        # If all failover providers fail, use cost optimization as last resort
        logger.warning("all_failover_providers_failed_using_cost_optimization")
        return self._route_cost_optimized(providers, messages, max_cost_eur)


# Global factory instance
_llm_factory = None


def get_llm_factory() -> LLMFactory:
    """Get the global LLM factory instance.

    Returns:
        LLM factory instance
    """
    global _llm_factory
    if _llm_factory is None:
        _llm_factory = LLMFactory()
    return _llm_factory


def get_llm_provider(
    messages: list[Message],
    strategy: RoutingStrategy = RoutingStrategy.COST_OPTIMIZED,
    max_cost_eur: float | None = None,
    preferred_provider: str | None = None,
    **kwargs,
) -> LLMProvider:
    """Convenience function to get an optimal LLM provider.

    Args:
        messages: List of conversation messages
        strategy: Routing strategy to use
        max_cost_eur: Maximum acceptable cost in EUR
        preferred_provider: Preferred provider type
        **kwargs: Additional routing parameters

    Returns:
        Optimal LLM provider
    """
    factory = get_llm_factory()
    return factory.get_optimal_provider(
        messages=messages,
        strategy=strategy,
        max_cost_eur=max_cost_eur,
        preferred_provider=preferred_provider,
        **kwargs,
    )
