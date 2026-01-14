"""Premium Model Selector Service for DEV-185.

Dynamic model selection for synthesis step per Section 13.10.4.
Always prefers GPT-4o with Anthropic Claude as fallback when OpenAI
is unavailable.

Usage:
    from app.services.premium_model_selector import PremiumModelSelector, SynthesisContext

    selector = PremiumModelSelector(config=get_model_config())
    context = SynthesisContext(total_tokens=5000)
    selection = selector.select(context)
"""

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.core.llm.base import LLMProviderType, LLMResponse
from app.core.llm.model_config import LLMModelConfig, ModelTier
from app.core.logging import logger

if TYPE_CHECKING:
    from app.schemas.chat import Message

# Pre-warm timeout in seconds
DEFAULT_PRE_WARM_TIMEOUT = 3.0


@dataclass
class SynthesisContext:
    """Context information for model selection decision.

    Attributes:
        total_tokens: Total tokens in the context (query + retrieved docs)
        query_complexity: Complexity level of the query (standard, complex, expert)
    """

    total_tokens: int
    query_complexity: str = "standard"


@dataclass
class ModelSelection:
    """Result of model selection decision.

    Attributes:
        model: Selected model name
        provider: Provider name (openai, anthropic)
        is_fallback: True if this is a fallback selection due to primary unavailability
        is_degraded: True if both providers are unavailable (best-effort mode)
    """

    model: str
    provider: str
    is_fallback: bool = False
    is_degraded: bool = False


class PremiumModelSelector:
    """Dynamic model selector for premium tier synthesis.

    Always prefers GPT-4o (OpenAI) as the primary model. Falls back to
    Anthropic Claude only when OpenAI is unavailable.

    Example:
        config = get_model_config()
        selector = PremiumModelSelector(config=config)

        # Pre-warm at startup
        await selector.pre_warm()

        # Select model for request
        context = SynthesisContext(total_tokens=5000)
        selection = selector.select(context)
    """

    def __init__(self, config: LLMModelConfig):
        """Initialize the premium model selector.

        Args:
            config: LLM model configuration instance
        """
        self._config = config
        self._provider_health: dict[str, bool] = {
            "openai": True,
            "anthropic": True,
        }
        self._pre_warm_timeout = DEFAULT_PRE_WARM_TIMEOUT

        # Get model configurations from config
        self._primary_model = config.get_model(ModelTier.PREMIUM)
        self._primary_provider = config.get_provider(ModelTier.PREMIUM)

        # Get fallback configuration
        fallback_config = config.get_fallback(ModelTier.PREMIUM)
        if fallback_config:
            self._fallback_model = fallback_config.get("model", "claude-3-5-sonnet-20241022")
            self._fallback_provider = fallback_config.get("provider", "anthropic")
        else:
            self._fallback_model = "claude-3-5-sonnet-20241022"
            self._fallback_provider = "anthropic"

    def select(self, context: SynthesisContext) -> ModelSelection:
        """Select the optimal model for the given context.

        Selection logic:
        1. Always prefer GPT-4o (OpenAI) as primary
        2. If OpenAI unavailable → use Anthropic Claude as fallback
        3. If both unavailable → return degraded selection

        Args:
            context: Synthesis context with token count and complexity

        Returns:
            ModelSelection with chosen model and metadata
        """
        # Always prefer primary model (GPT-4o) regardless of context size
        preferred_model = self._primary_model
        preferred_provider = self._primary_provider
        alternate_model = self._fallback_model
        alternate_provider = self._fallback_provider

        # Check provider availability
        if self.is_available(preferred_provider):
            return ModelSelection(
                model=preferred_model,
                provider=preferred_provider,
                is_fallback=False,
                is_degraded=False,
            )

        # Try fallback provider
        if self.is_available(alternate_provider):
            logger.warning(
                "premium_model_using_fallback",
                preferred_provider=preferred_provider,
                fallback_provider=alternate_provider,
                reason="primary_unavailable",
            )
            return ModelSelection(
                model=alternate_model,
                provider=alternate_provider,
                is_fallback=True,
                is_degraded=False,
            )

        # Both providers unavailable - degraded mode
        logger.error(
            "premium_model_degraded_mode",
            openai_available=self.is_available("openai"),
            anthropic_available=self.is_available("anthropic"),
        )
        return ModelSelection(
            model=preferred_model,
            provider=preferred_provider,
            is_fallback=False,
            is_degraded=True,
        )

    def is_available(self, provider: str) -> bool:
        """Check if a provider is available.

        Args:
            provider: Provider name (openai, anthropic)

        Returns:
            True if provider is healthy, False otherwise
        """
        return self._provider_health.get(provider, False)

    def get_fallback(self, model: str) -> str:
        """Get the fallback model for a given model.

        Args:
            model: Current model name

        Returns:
            Fallback model name
        """
        if model == self._primary_model:
            return self._fallback_model
        return self._primary_model

    async def pre_warm(self) -> dict[str, bool]:
        """Pre-warm and validate both providers.

        Runs validation for OpenAI and Anthropic in parallel with timeout.
        Updates provider health status based on results.

        Returns:
            Dictionary mapping provider name to availability status
        """

        async def validate_with_timeout(provider: str) -> tuple[str, bool]:
            """Validate provider with timeout."""
            try:
                result = await asyncio.wait_for(
                    self._validate_provider(provider),
                    timeout=self._pre_warm_timeout,
                )
                return provider, result
            except TimeoutError:
                logger.warning(
                    "premium_model_prewarm_timeout",
                    provider=provider,
                    timeout_seconds=self._pre_warm_timeout,
                )
                return provider, False
            except Exception as e:
                logger.error(
                    "premium_model_prewarm_error",
                    provider=provider,
                    error=str(e),
                )
                return provider, False

        # Validate both providers in parallel
        results = await asyncio.gather(
            validate_with_timeout("openai"),
            validate_with_timeout("anthropic"),
        )

        # Update health status
        status = {}
        for provider, is_healthy in results:
            self._provider_health[provider] = is_healthy
            status[provider] = is_healthy
            if is_healthy:
                logger.info(
                    "premium_model_provider_ready",
                    provider=provider,
                )
            else:
                logger.warning(
                    "premium_model_provider_unavailable",
                    provider=provider,
                )

        return status

    async def _validate_provider(self, provider: str) -> bool:
        """Validate a provider's API key and connectivity.

        This is a placeholder that should be overridden or mocked in tests.
        In production, this would make a minimal API call to validate.

        Args:
            provider: Provider name to validate

        Returns:
            True if provider is valid and reachable
        """
        # In production, this would use the actual provider clients
        # For now, return True as default (healthy)
        return True

    def mark_provider_unhealthy(self, provider: str) -> None:
        """Mark a provider as unhealthy after a failure.

        Args:
            provider: Provider name to mark as unhealthy
        """
        self._provider_health[provider] = False
        logger.warning(
            "premium_model_provider_marked_unhealthy",
            provider=provider,
        )

    def mark_provider_healthy(self, provider: str) -> None:
        """Mark a provider as healthy after recovery.

        Args:
            provider: Provider name to mark as healthy
        """
        self._provider_health[provider] = True
        logger.info(
            "premium_model_provider_marked_healthy",
            provider=provider,
        )

    async def execute(
        self,
        context: SynthesisContext,
        messages: list["Message"],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Select and execute LLM completion using the optimal model.

        This method bridges model selection with actual LLM execution by:
        1. Selecting the optimal model based on context
        2. Creating the appropriate provider via LLMFactory
        3. Executing the chat completion
        4. Handling fallback on provider failure

        Args:
            context: Synthesis context with token count and complexity
            messages: List of conversation messages
            temperature: Sampling temperature (default 0.2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters passed to chat_completion

        Returns:
            LLMResponse with the generated content

        Raises:
            ValueError: If no providers are available
            Exception: If both primary and fallback providers fail
        """
        from app.core.llm.factory import get_llm_factory

        selection = self.select(context)
        factory = get_llm_factory()

        logger.info(
            "premium_model_execute_start",
            model=selection.model,
            provider=selection.provider,
            is_fallback=selection.is_fallback,
            is_degraded=selection.is_degraded,
            total_tokens=context.total_tokens,
        )

        try:
            # Create provider and execute
            provider = factory.create_provider(
                provider_type=LLMProviderType(selection.provider),
                model=selection.model,
            )

            response = await provider.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            logger.info(
                "premium_model_execute_success",
                model=selection.model,
                provider=selection.provider,
                tokens_used=response.tokens_used,
                cost_estimate=response.cost_estimate,
            )

            return response

        except Exception as e:
            # Mark provider as unhealthy and try fallback
            self.mark_provider_unhealthy(selection.provider)

            logger.warning(
                "premium_model_execute_failed_trying_fallback",
                failed_provider=selection.provider,
                failed_model=selection.model,
                error=str(e),
            )

            # Try fallback if not already using one and not degraded
            if not selection.is_fallback and not selection.is_degraded:
                fallback_selection = self.select(context)

                if fallback_selection.provider != selection.provider:
                    try:
                        fallback_provider = factory.create_provider(
                            provider_type=LLMProviderType(fallback_selection.provider),
                            model=fallback_selection.model,
                        )

                        response = await fallback_provider.chat_completion(
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            **kwargs,
                        )

                        logger.info(
                            "premium_model_execute_fallback_success",
                            model=fallback_selection.model,
                            provider=fallback_selection.provider,
                            tokens_used=response.tokens_used,
                        )

                        return response

                    except Exception as fallback_error:
                        self.mark_provider_unhealthy(fallback_selection.provider)
                        logger.error(
                            "premium_model_execute_fallback_failed",
                            fallback_provider=fallback_selection.provider,
                            error=str(fallback_error),
                        )
                        raise

            # Re-raise original error if no fallback available
            raise
