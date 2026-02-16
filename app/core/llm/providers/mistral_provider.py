"""Mistral AI provider implementation (DEV-256)."""

from collections.abc import AsyncGenerator
from typing import Any

try:
    from mistralai import Mistral

    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False
    Mistral = None

from langfuse import get_client

from app.core.llm.base import (
    LLMCostInfo,
    LLMProvider,
    LLMProviderType,
    LLMResponse,
    LLMStreamResponse,
)
from app.core.llm.utils import (
    get_message_content,
    get_message_role,
)
from app.core.logging import logger
from app.observability.langfuse_config import get_current_observation_id, get_current_trace_id
from app.schemas.chat import Message


class MistralProvider(LLMProvider):
    """Mistral AI provider implementation."""

    def __init__(self, api_key: str, model: str = "mistral-small-latest", **kwargs):
        """Initialize Mistral provider.

        Args:
            api_key: Mistral API key
            model: Model name to use
            **kwargs: Additional configuration
        """
        if not MISTRAL_AVAILABLE:
            raise ImportError("Mistral AI package not installed. Install with: pip install mistralai")

        super().__init__(api_key, model, **kwargs)
        self._client = None

    @property
    def client(self) -> Any:
        """Get the Mistral client."""
        if self._client is None:
            self._client = Mistral(api_key=self.api_key)
        return self._client

    @property
    def provider_type(self) -> LLMProviderType:
        """Get the provider type."""
        return LLMProviderType.MISTRAL

    @property
    def supported_models(self) -> dict[str, LLMCostInfo]:
        """Get supported Mistral models from the centralized registry (DEV-257)."""
        from app.core.llm.model_registry import get_model_registry

        registry = get_model_registry()
        return {m.model_name: m.to_cost_info() for m in registry.get_models_by_provider("mistral")}

    def _convert_messages_to_mistral(self, messages: list[Message]) -> list[dict[str, str]]:
        """Convert messages to Mistral format.

        Args:
            messages: List of Message objects or dicts

        Returns:
            List of Mistral-formatted messages
        """
        mistral_messages = []

        for message in messages:
            role = get_message_role(message)
            content = get_message_content(message)
            mistral_messages.append({"role": role, "content": content})

        return mistral_messages

    async def chat_completion(
        self,
        messages: list[Message],
        tools: list[Any] | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a chat completion using Mistral AI.

        Args:
            messages: List of conversation messages
            tools: Optional list of tools (not supported yet)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            LLMResponse with the generated content
        """
        try:
            mistral_messages = self._convert_messages_to_mistral(messages)

            response = await self.client.chat.complete_async(
                model=self.model,
                messages=mistral_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            choice = response.choices[0]
            content = choice.message.content

            # Extract token counts
            input_tokens = None
            output_tokens = None
            if response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

            # Calculate cost (individual input/output costs for Langfuse)
            cost_estimate = None
            input_cost = None
            output_cost = None
            if input_tokens and output_tokens:
                cost_info = self.supported_models.get(self.model)
                if not cost_info:
                    # Fallback to mistral-small-latest for unknown models
                    cost_info = self.supported_models["mistral-small-latest"]
                input_cost = (input_tokens / 1000) * cost_info.input_cost_per_1k_tokens
                output_cost = (output_tokens / 1000) * cost_info.output_cost_per_1k_tokens
                cost_estimate = input_cost + output_cost

            # Report to Langfuse with explicit cost (bypasses Langfuse auto-calculation)
            self._report_langfuse_generation(
                model=self.model,
                input_messages=mistral_messages,
                output_content=content,
                prompt_tokens=input_tokens or 0,
                completion_tokens=output_tokens or 0,
                trace_id=get_current_trace_id(),
                parent_span_id=get_current_observation_id(),
                input_cost=input_cost,
                output_cost=output_cost,
            )

            return LLMResponse(
                content=content,
                model=self.model,
                provider=self.provider_type.value,
                tokens_used={"input": input_tokens, "output": output_tokens} if input_tokens else None,  # type: ignore[dict-item]
                cost_estimate=cost_estimate,
                finish_reason=choice.finish_reason,
            )

        except Exception as e:
            logger.error(
                "mistral_completion_failed",
                error=str(e),
                error_type=type(e).__name__,
                model=self.model,
                provider=self.provider_type.value,
            )
            raise

    async def stream_completion(  # type: ignore[override]
        self,
        messages: list[Message],
        tools: list[Any] | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamResponse]:
        """Generate a streaming chat completion using Mistral AI.

        Args:
            messages: List of conversation messages
            tools: Optional list of tools (not supported yet)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Yields:
            LLMStreamResponse chunks
        """
        try:
            mistral_messages = self._convert_messages_to_mistral(messages)

            stream = await self.client.chat.stream_async(
                model=self.model,
                messages=mistral_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            async for event in stream:
                if event.data.choices:
                    choice = event.data.choices[0]
                    if choice.delta.content:
                        yield LLMStreamResponse(
                            content=choice.delta.content,
                            done=False,
                            model=self.model,
                            provider=self.provider_type.value,
                        )

                    if choice.finish_reason:
                        yield LLMStreamResponse(
                            content="",
                            done=True,
                            model=self.model,
                            provider=self.provider_type.value,
                        )

        except Exception as e:
            logger.error(
                "mistral_stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                model=self.model,
                provider=self.provider_type.value,
            )
            raise

    def estimate_tokens(self, messages: list[Message]) -> int:
        """Estimate token count for Mistral models.

        Args:
            messages: List of conversation messages

        Returns:
            Estimated token count
        """
        total_chars = sum(len(get_message_content(message)) for message in messages)
        # Rough estimation: 1 token ~ 4 characters
        estimated_tokens = int((total_chars / 4) * 1.2)
        return max(estimated_tokens, 10)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for given token counts.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        if self.model not in self.supported_models:
            cost_info = self.supported_models["mistral-small-latest"]
        else:
            cost_info = self.supported_models[self.model]

        input_cost = (input_tokens / 1000) * cost_info.input_cost_per_1k_tokens
        output_cost = (output_tokens / 1000) * cost_info.output_cost_per_1k_tokens

        return input_cost + output_cost

    async def validate_connection(self) -> bool:
        """Validate that the Mistral connection is working.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
            )
            return bool(response.choices)
        except Exception as e:
            logger.error(
                "mistral_connection_validation_failed",
                error=str(e),
                model=self.model,
                provider=self.provider_type.value,
            )
            return False

    def get_model_capabilities(self) -> dict[str, bool]:
        """Get capabilities of the current Mistral model."""
        base_capabilities = super().get_model_capabilities()

        context_lengths = {
            "mistral-small-latest": 32000,
            "mistral-medium-latest": 32000,
            "mistral-large-latest": 128000,
            "open-mistral-7b": 32000,
            "open-mixtral-8x7b": 32000,
            "codestral-latest": 32000,
        }

        base_capabilities.update(
            {
                "supports_json_mode": True,
                "supports_function_calling": "large" in self.model,
                "max_context_length": context_lengths.get(self.model, 32000),  # type: ignore[dict-item]
                "supports_vision": False,
            }
        )

        return base_capabilities

    @staticmethod
    def _report_langfuse_generation(
        model: str,
        input_messages: list[dict[str, str]],
        output_content: str,
        prompt_tokens: int,
        completion_tokens: int,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        input_cost: float | None = None,
        output_cost: float | None = None,
    ) -> None:
        """Report Mistral call to Langfuse as a generation (DEV-255).

        Args:
            model: Model name
            input_messages: Input messages in Mistral format
            output_content: Generated output content
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            trace_id: Langfuse trace ID for context binding
            parent_span_id: Parent observation ID for proper nesting
            input_cost: Cost in USD for input tokens (bypasses Langfuse auto-calculation)
            output_cost: Cost in USD for output tokens (bypasses Langfuse auto-calculation)
        """
        # Debug logging to diagnose Langfuse cost tracking issues
        logger.info(
            "langfuse_generation_params",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            input_cost=input_cost,
            output_cost=output_cost,
        )

        if not trace_id:
            logger.warning("langfuse_skipped_no_trace_id", model=model)
            return

        try:
            client = get_client()
            trace_context = {"trace_id": trace_id}
            if parent_span_id:
                trace_context["parent_span_id"] = parent_span_id

            logger.debug(
                "langfuse_creating_generation",
                model=model,
                trace_context=trace_context,
            )

            generation = client.start_generation(
                trace_context=trace_context,
                name="mistral-chat",
                model=model,
                input={"messages": input_messages},
            )

            # Build update kwargs
            update_kwargs: dict = {
                "output": output_content,
                "usage_details": {
                    "input": prompt_tokens,
                    "output": completion_tokens,
                },
            }

            # Pass cost explicitly to bypass Langfuse's auto-calculation
            # (Langfuse doesn't have Mistral model pricing in its database)
            if input_cost is not None or output_cost is not None:
                update_kwargs["cost_details"] = {
                    "input": input_cost or 0.0,
                    "output": output_cost or 0.0,
                }

            logger.debug(
                "langfuse_updating_generation",
                model=model,
                has_cost_details=("cost_details" in update_kwargs),
            )

            generation.update(**update_kwargs)
            generation.end()
            logger.info(
                "langfuse_generation_reported",
                model=model,
                trace_id=trace_id,
                input_cost=input_cost,
                output_cost=output_cost,
            )
        except Exception as e:
            logger.error(
                "langfuse_generation_failed",
                error=str(e),
                error_type=type(e).__name__,
                model=model,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
            )
