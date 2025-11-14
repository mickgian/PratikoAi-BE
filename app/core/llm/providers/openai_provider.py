"""OpenAI provider implementation."""

import asyncio
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
)

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from openai import (
    AsyncOpenAI,
    OpenAIError,
)

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
from app.observability.rag_logging import rag_step_timer
from app.schemas.chat import Message


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", **kwargs):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model name to use
            **kwargs: Additional configuration
        """
        super().__init__(api_key, model, **kwargs)
        self._client = None
        self._langchain_client = None

    @property
    def client(self) -> AsyncOpenAI:
        """Get the OpenAI async client."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)  # type: ignore[arg-type]
        return self._client

    @property
    def langchain_client(self) -> ChatOpenAI:
        """Get the LangChain OpenAI client."""
        if self._langchain_client is None:
            self._langchain_client = ChatOpenAI(
                api_key=self.api_key,  # type: ignore[arg-type]
                model=self.model,
                temperature=self.config.get("temperature", 0.2),
                max_tokens=self.config.get("max_tokens", None),
            )
        return self._langchain_client

    @property
    def provider_type(self) -> LLMProviderType:
        """Get the provider type."""
        return LLMProviderType.OPENAI

    @property
    def supported_models(self) -> Dict[str, LLMCostInfo]:
        """Get supported OpenAI models and their cost information.

        Costs are in EUR per 1K tokens (converted from USD).
        Current exchange rate: 1 USD ≈ 0.92 EUR
        """
        return {
            "gpt-4o-mini": LLMCostInfo(
                input_cost_per_1k_tokens=0.000138,  # $0.15/1M tokens * 0.92
                output_cost_per_1k_tokens=0.000552,  # $0.60/1M tokens * 0.92
                model_name="gpt-4o-mini",
                tier=LLMModelTier.BASIC,
            ),
            "gpt-4o": LLMCostInfo(
                input_cost_per_1k_tokens=0.0046,  # $5.00/1M tokens * 0.92
                output_cost_per_1k_tokens=0.0138,  # $15.00/1M tokens * 0.92
                model_name="gpt-4o",
                tier=LLMModelTier.ADVANCED,
            ),
            "gpt-4-turbo": LLMCostInfo(
                input_cost_per_1k_tokens=0.0092,  # $10.00/1M tokens * 0.92
                output_cost_per_1k_tokens=0.0276,  # $30.00/1M tokens * 0.92
                model_name="gpt-4-turbo",
                tier=LLMModelTier.PREMIUM,
            ),
            "gpt-3.5-turbo": LLMCostInfo(
                input_cost_per_1k_tokens=0.0005,  # $0.50/1M tokens * 0.92
                output_cost_per_1k_tokens=0.0015,  # $1.50/1M tokens * 0.92
                model_name="gpt-3.5-turbo",
                tier=LLMModelTier.BASIC,
            ),
        }

    def _convert_messages_to_openai(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert messages to OpenAI format.

        Args:
            messages: List of Message objects or dicts

        Returns:
            List of OpenAI-formatted messages
        """
        openai_messages = []
        for message in messages:
            openai_message = {
                "role": get_message_role(message),
                "content": get_message_content(message),
            }
            openai_messages.append(openai_message)
        return openai_messages

    def _convert_messages_to_langchain(self, messages: List[Message]) -> List[BaseMessage]:
        """Convert messages to LangChain format.

        Args:
            messages: List of Message objects or dicts

        Returns:
            List of LangChain BaseMessage objects
        """
        langchain_messages = []
        for message in messages:
            role = get_message_role(message)
            content = get_message_content(message)
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            elif role == "tool":
                langchain_messages.append(ToolMessage(content=content, tool_call_id=""))
        return langchain_messages

    async def chat_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Any]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a chat completion using OpenAI.

        Args:
            messages: List of conversation messages
            tools: Optional list of tools (LangChain format)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            LLMResponse with the generated content
        """
        # Note: Step 64 timing/logging handled by node_step_64 wrapper to avoid duplicate logging
        try:
            if tools:
                # Use LangChain for tool support
                langchain_messages = self._convert_messages_to_langchain(messages)
                llm_with_tools = self.langchain_client.bind_tools(tools)
                # Defensive: if tests/mock make bind_tools async, await it
                if asyncio.iscoroutine(llm_with_tools):
                    llm_with_tools = await llm_with_tools  # type: ignore[misc]

                response = await llm_with_tools.ainvoke(
                    langchain_messages, temperature=temperature, max_tokens=max_tokens, **kwargs
                )

                tool_calls = None
                if hasattr(response, "tool_calls") and response.tool_calls:
                    tool_calls = [
                        {"id": tc["id"], "name": tc["name"], "args": tc["args"]} for tc in response.tool_calls
                    ]

                return LLMResponse(
                    content=response.content,
                    model=self.model,
                    provider=self.provider_type.value,
                    tool_calls=tool_calls,
                    finish_reason="stop",
                )
            else:
                # Use direct OpenAI client for better control
                openai_messages = self._convert_messages_to_openai(messages)

                response = await self.client.chat.completions.create(  # type: ignore[call-overload]
                    model=self.model,
                    messages=openai_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )

                choice = response.choices[0]
                tokens_used = response.usage.total_tokens if response.usage else None
                cost_estimate = None

                if response.usage:
                    cost_estimate = self.estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)

                return LLMResponse(
                    content=choice.message.content or "",
                    model=self.model,
                    provider=self.provider_type.value,
                    tokens_used=tokens_used,
                    cost_estimate=cost_estimate,
                    finish_reason=choice.finish_reason,
                )

        except OpenAIError as e:
            logger.error(
                "openai_completion_failed",
                error=str(e),
                model=self.model,
                provider=self.provider_type.value,
            )
            raise
        except (ConnectionError, TimeoutError, ValueError) as e:
            logger.error(
                "openai_completion_unexpected_error",
                error=str(e),
                model=self.model,
                provider=self.provider_type.value,
            )
            raise

    async def stream_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Any]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamResponse, None]:
        """Generate a streaming chat completion using OpenAI.

        Args:
            messages: List of conversation messages
            tools: Optional list of tools
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Yields:
            LLMStreamResponse chunks
        """
        try:
            openai_messages = self._convert_messages_to_openai(messages)

            # Note: Streaming with tools is complex, for now we'll disable tools in streaming
            # This can be enhanced later if needed
            stream = await self.client.chat.completions.create(  # type: ignore[call-overload]
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices:
                    choice = chunk.choices[0]
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

        except OpenAIError as e:
            logger.error(
                "openai_stream_failed",
                error=str(e),
                model=self.model,
                provider=self.provider_type.value,
            )
            raise
        except (ConnectionError, TimeoutError, ValueError) as e:
            logger.error(
                "openai_stream_unexpected_error",
                error=str(e),
                model=self.model,
                provider=self.provider_type.value,
            )
            raise

    def estimate_tokens(self, messages: List[Message]) -> int:
        """Estimate token count for OpenAI models.

        This is a rough estimation based on character count.
        For production use, consider using tiktoken library for accurate counting.

        Args:
            messages: List of conversation messages (Message objects or dicts)

        Returns:
            Estimated token count
        """
        total_chars = sum(len(get_message_content(message)) for message in messages)
        # Rough estimation: 1 token ≈ 4 characters for English text
        # Add 20% buffer for message formatting and overhead
        estimated_tokens = int((total_chars / 4) * 1.2)
        return max(estimated_tokens, 10)  # Minimum 10 tokens

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for given token counts.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in EUR
        """
        if self.model not in self.supported_models:
            logger.warning(
                "unknown_model_cost_estimation",
                model=self.model,
                provider=self.provider_type.value,
            )
            # Use gpt-4o-mini as fallback
            cost_info = self.supported_models["gpt-4o-mini"]
        else:
            cost_info = self.supported_models[self.model]

        input_cost = (input_tokens / 1000) * cost_info.input_cost_per_1k_tokens
        output_cost = (output_tokens / 1000) * cost_info.output_cost_per_1k_tokens

        return input_cost + output_cost

    async def validate_connection(self) -> bool:
        """Validate that the OpenAI connection is working.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Make a minimal API call to test the connection
            await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],  # type: ignore[arg-type]
                max_tokens=1,
            )
            return True
        except (OpenAIError, ConnectionError, TimeoutError) as e:
            logger.error(
                "openai_connection_validation_failed",
                error=str(e),
                model=self.model,
                provider=self.provider_type.value,
            )
            return False

    def get_model_capabilities(self) -> Dict[str, bool]:
        """Get capabilities of the current OpenAI model.

        Returns:
            Dictionary of capability flags
        """
        base_capabilities = super().get_model_capabilities()

        # Model-specific capabilities
        if self.model in ["gpt-4o", "gpt-4o-mini"]:
            base_capabilities.update(
                {
                    "supports_json_mode": True,
                    "supports_function_calling": True,
                    "max_context_length": 128000,
                    "supports_vision": True,
                }
            )
        elif self.model == "gpt-4-turbo":
            base_capabilities.update(
                {
                    "supports_json_mode": True,
                    "supports_function_calling": True,
                    "max_context_length": 128000,
                    "supports_vision": True,
                }
            )
        elif self.model == "gpt-3.5-turbo":
            base_capabilities.update(
                {
                    "supports_json_mode": True,
                    "supports_function_calling": True,
                    "max_context_length": 4096,
                    "supports_vision": False,
                }
            )

        return base_capabilities
