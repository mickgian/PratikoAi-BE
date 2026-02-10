"""Google Gemini provider implementation (DEV-256)."""

from collections.abc import AsyncGenerator
from typing import Any

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
    GenerationConfig = None

from langfuse import get_client

from app.core.llm.base import (
    LLMCostInfo,
    LLMModelTier,
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


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", **kwargs):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key
            model: Model name to use
            **kwargs: Additional configuration
        """
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "Google Generative AI package not installed. Install with: pip install google-generativeai"
            )

        super().__init__(api_key, model, **kwargs)
        genai.configure(api_key=self.api_key)
        self._client = None

    @property
    def client(self) -> Any:
        """Get the Gemini client (GenerativeModel)."""
        if self._client is None:
            self._client = genai.GenerativeModel(self.model)
        return self._client

    @property
    def provider_type(self) -> LLMProviderType:
        """Get the provider type."""
        return LLMProviderType.GEMINI

    @property
    def supported_models(self) -> dict[str, LLMCostInfo]:
        """Get supported Gemini models and their cost information.

        Costs are in EUR per 1K tokens (converted from USD).
        Current exchange rate: 1 USD = 0.92 EUR
        """
        return {
            "gemini-2.5-flash": LLMCostInfo(
                input_cost_per_1k_tokens=0.0000691,  # Estimate based on Flash pricing
                output_cost_per_1k_tokens=0.000276,
                model_name="gemini-2.5-flash",
                tier=LLMModelTier.BASIC,
            ),
            "gemini-2.5-pro": LLMCostInfo(
                input_cost_per_1k_tokens=0.00115,  # Estimate based on Pro pricing
                output_cost_per_1k_tokens=0.0046,
                model_name="gemini-2.5-pro",
                tier=LLMModelTier.ADVANCED,
            ),
            "gemini-2.0-flash": LLMCostInfo(
                input_cost_per_1k_tokens=0.0000691,
                output_cost_per_1k_tokens=0.000276,
                model_name="gemini-2.0-flash",
                tier=LLMModelTier.STANDARD,
            ),
        }

    def _convert_messages_to_gemini(self, messages: list[Message]) -> tuple[str | None, list[dict[str, Any]]]:
        """Convert messages to Gemini format.

        Args:
            messages: List of Message objects or dicts

        Returns:
            Tuple of (system_instruction, history_messages)
        """
        system_instruction = None
        history = []

        for message in messages:
            role = get_message_role(message)
            content = get_message_content(message)

            if role == "system":
                system_instruction = content
            elif role == "user":
                history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                history.append({"role": "model", "parts": [content]})

        return system_instruction, history

    async def chat_completion(
        self,
        messages: list[Message],
        tools: list[Any] | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a chat completion using Google Gemini.

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
            system_instruction, history = self._convert_messages_to_gemini(messages)

            # Create generation config
            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            # Create model with system instruction if provided
            model = genai.GenerativeModel(
                self.model,
                system_instruction=system_instruction,
            )

            # Get the last user message for the prompt
            if history and history[-1]["role"] == "user":
                prompt = history[-1]["parts"][0]
                chat_history = history[:-1] if len(history) > 1 else []
            else:
                prompt = ""
                chat_history = history

            # Start chat with history
            chat = model.start_chat(history=chat_history)

            # Generate response
            response = await chat.send_message_async(
                prompt,
                generation_config=generation_config,
            )

            # Extract token counts
            input_tokens = None
            output_tokens = None
            if hasattr(response, "usage_metadata"):
                input_tokens = getattr(response.usage_metadata, "prompt_token_count", None)
                output_tokens = getattr(response.usage_metadata, "candidates_token_count", None)

            # Calculate cost
            cost_estimate = None
            if input_tokens and output_tokens:
                cost_estimate = self.estimate_cost(input_tokens, output_tokens)

            # Report to Langfuse
            self._report_langfuse_generation(
                model=self.model,
                input_messages=[{"role": "user", "content": prompt}],
                output_content=response.text,
                prompt_tokens=input_tokens or 0,
                completion_tokens=output_tokens or 0,
                trace_id=get_current_trace_id(),
                parent_span_id=get_current_observation_id(),
            )

            return LLMResponse(
                content=response.text,
                model=self.model,
                provider=self.provider_type.value,
                tokens_used={"input": input_tokens, "output": output_tokens} if input_tokens else None,
                cost_estimate=cost_estimate,
                finish_reason="stop",
            )

        except Exception as e:
            logger.error(
                "gemini_completion_failed",
                error=str(e),
                error_type=type(e).__name__,
                model=self.model,
                provider=self.provider_type.value,
            )
            raise

    async def stream_completion(
        self,
        messages: list[Message],
        tools: list[Any] | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamResponse]:
        """Generate a streaming chat completion using Google Gemini.

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
            system_instruction, history = self._convert_messages_to_gemini(messages)

            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            model = genai.GenerativeModel(
                self.model,
                system_instruction=system_instruction,
            )

            if history and history[-1]["role"] == "user":
                prompt = history[-1]["parts"][0]
                chat_history = history[:-1] if len(history) > 1 else []
            else:
                prompt = ""
                chat_history = history

            chat = model.start_chat(history=chat_history)

            response = await chat.send_message_async(
                prompt,
                generation_config=generation_config,
                stream=True,
            )

            async for chunk in response:
                if chunk.text:
                    yield LLMStreamResponse(
                        content=chunk.text,
                        done=False,
                        model=self.model,
                        provider=self.provider_type.value,
                    )

            yield LLMStreamResponse(
                content="",
                done=True,
                model=self.model,
                provider=self.provider_type.value,
            )

        except Exception as e:
            logger.error(
                "gemini_stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                model=self.model,
                provider=self.provider_type.value,
            )
            raise

    def estimate_tokens(self, messages: list[Message]) -> int:
        """Estimate token count for Gemini models.

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
            Estimated cost in EUR
        """
        if self.model not in self.supported_models:
            cost_info = self.supported_models["gemini-2.5-flash"]
        else:
            cost_info = self.supported_models[self.model]

        input_cost = (input_tokens / 1000) * cost_info.input_cost_per_1k_tokens
        output_cost = (output_tokens / 1000) * cost_info.output_cost_per_1k_tokens

        return input_cost + output_cost

    async def validate_connection(self) -> bool:
        """Validate that the Gemini connection is working.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            model = genai.GenerativeModel(self.model)
            response = await model.generate_content_async(
                "test",
                generation_config=GenerationConfig(max_output_tokens=1),
            )
            return bool(response.text)
        except Exception as e:
            logger.error(
                "gemini_connection_validation_failed",
                error=str(e),
                model=self.model,
                provider=self.provider_type.value,
            )
            return False

    def get_model_capabilities(self) -> dict[str, bool]:
        """Get capabilities of the current Gemini model."""
        base_capabilities = super().get_model_capabilities()

        base_capabilities.update(
            {
                "supports_json_mode": True,
                "supports_function_calling": True,
                "max_context_length": 1000000 if "pro" in self.model else 128000,
                "supports_vision": True,
            }
        )

        return base_capabilities

    @staticmethod
    def _report_langfuse_generation(
        model: str,
        input_messages: list[dict[str, Any]],
        output_content: str,
        prompt_tokens: int,
        completion_tokens: int,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
    ) -> None:
        """Report Gemini call to Langfuse as a generation (DEV-255)."""
        if not trace_id:
            return

        try:
            client = get_client()
            trace_context = {"trace_id": trace_id}
            if parent_span_id:
                trace_context["parent_span_id"] = parent_span_id

            generation = client.start_generation(
                trace_context=trace_context,
                name="gemini-chat",
                model=model,
                input={"messages": input_messages},
            )
            generation.update(
                output=output_content,
                usage_details={
                    "input": prompt_tokens,
                    "output": completion_tokens,
                },
            )
            generation.end()
        except Exception:
            pass  # Graceful degradation
