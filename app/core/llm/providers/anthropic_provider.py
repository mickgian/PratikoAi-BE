"""Anthropic Claude provider implementation."""

from typing import Any, AsyncGenerator, Dict, List, Optional

try:
    import anthropic
    from anthropic import AsyncAnthropic, AnthropicError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    AnthropicError = Exception

from app.core.llm.base import (
    LLMProvider,
    LLMProviderType,
    LLMResponse,
    LLMStreamResponse,
    LLMCostInfo,
    LLMModelTier,
)
from app.core.logging import logger
from app.observability.rag_logging import rag_step_timer
from app.schemas.chat import Message


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation."""

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307", **kwargs):
        """Initialize Anthropic provider.
        
        Args:
            api_key: Anthropic API key
            model: Model name to use
            **kwargs: Additional configuration
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "Anthropic package not installed. Install with: pip install anthropic"
            )
            
        super().__init__(api_key, model, **kwargs)
        self._client = None
        
    @property
    def client(self) -> AsyncAnthropic:
        """Get the Anthropic async client."""
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    @property
    def provider_type(self) -> LLMProviderType:
        """Get the provider type."""
        return LLMProviderType.ANTHROPIC

    @property
    def supported_models(self) -> Dict[str, LLMCostInfo]:
        """Get supported Anthropic models and their cost information.
        
        Costs are in EUR per 1K tokens (converted from USD).
        Current exchange rate: 1 USD ≈ 0.92 EUR
        """
        return {
            "claude-3-haiku-20240307": LLMCostInfo(
                input_cost_per_1k_tokens=0.00023,   # $0.25/1M tokens * 0.92
                output_cost_per_1k_tokens=0.00115,  # $1.25/1M tokens * 0.92
                model_name="claude-3-haiku-20240307",
                tier=LLMModelTier.BASIC,
            ),
            "claude-3-sonnet-20241022": LLMCostInfo(
                input_cost_per_1k_tokens=0.00276,   # $3.00/1M tokens * 0.92
                output_cost_per_1k_tokens=0.0138,   # $15.00/1M tokens * 0.92
                model_name="claude-3-sonnet-20241022",
                tier=LLMModelTier.STANDARD,
            ),
            "claude-3-opus-20240229": LLMCostInfo(
                input_cost_per_1k_tokens=0.0138,    # $15.00/1M tokens * 0.92
                output_cost_per_1k_tokens=0.069,    # $75.00/1M tokens * 0.92
                model_name="claude-3-opus-20240229",
                tier=LLMModelTier.PREMIUM,
            ),
        }

    def _convert_messages_to_anthropic(self, messages: List[Message]) -> tuple[str, List[Dict[str, Any]]]:
        """Convert messages to Anthropic format.
        
        Args:
            messages: List of Message objects
            
        Returns:
            Tuple of (system_prompt, conversation_messages)
        """
        system_prompt = ""
        conversation_messages = []
        
        for message in messages:
            if message.role == "system":
                system_prompt = message.content
            elif message.role in ["user", "assistant"]:
                conversation_messages.append({
                    "role": message.role,
                    "content": message.content
                })
            # Skip tool messages for now - Anthropic has different tool format
        
        return system_prompt, conversation_messages

    def _convert_tools_to_anthropic(self, tools: Optional[List[Any]]) -> Optional[List[Dict[str, Any]]]:
        """Convert tools to Anthropic format.
        
        Args:
            tools: List of tools in LangChain format
            
        Returns:
            Tools converted to Anthropic format
        """
        if not tools:
            return None
            
        anthropic_tools = []
        for tool in tools:
            # Extract tool information from LangChain tool
            tool_def = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            
            # Try to extract schema from tool args_schema if available
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    schema = tool.args_schema.model_json_schema()
                    tool_def["input_schema"] = {
                        "type": "object",
                        "properties": schema.get("properties", {}),
                        "required": schema.get("required", [])
                    }
                except (AttributeError, TypeError, ValueError) as e:
                    logger.warning(
                        "anthropic_tool_schema_conversion_failed",
                        tool_name=tool.name,
                        error=str(e)
                    )
            
            anthropic_tools.append(tool_def)
        
        return anthropic_tools

    async def chat_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Any]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a chat completion using Anthropic Claude.
        
        Args:
            messages: List of conversation messages
            tools: Optional list of tools
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse with the generated content
        """
        # Note: Step 64 timing/logging handled by node_step_64 wrapper to avoid duplicate logging
        try:
            system_prompt, conversation_messages = self._convert_messages_to_anthropic(messages)
            anthropic_tools = self._convert_tools_to_anthropic(tools)

            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": conversation_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 4096,
                **kwargs
            }

            if system_prompt:
                request_params["system"] = system_prompt

            if anthropic_tools:
                request_params["tools"] = anthropic_tools

            response = await self.client.messages.create(**request_params)

            # Extract content
            content = ""
            tool_calls = None

            for content_block in response.content:
                if content_block.type == "text":
                    content += content_block.text
                elif content_block.type == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append({
                        "id": content_block.id,
                        "name": content_block.name,
                        "args": content_block.input
                    })

            # Calculate cost estimate
            cost_estimate = None
            if response.usage:
                cost_estimate = self.estimate_cost(
                    response.usage.input_tokens,
                    response.usage.output_tokens
                )

            return LLMResponse(
                content=content,
                model=self.model,
                provider=self.provider_type.value,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens if response.usage else None,
                cost_estimate=cost_estimate,
                finish_reason=response.stop_reason,
                tool_calls=tool_calls,
            )

        except AnthropicError as e:
            logger.error(
                "anthropic_completion_failed",
                error=str(e),
                model=self.model,
                provider=self.provider_type.value,
            )
            raise
        except Exception as e:
            logger.error(
                "anthropic_completion_unexpected_error",
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
        """Generate a streaming chat completion using Anthropic Claude.
        
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
            system_prompt, conversation_messages = self._convert_messages_to_anthropic(messages)
            anthropic_tools = self._convert_tools_to_anthropic(tools)
            
            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": conversation_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 4096,
                "stream": True,
                **kwargs
            }
            
            if system_prompt:
                request_params["system"] = system_prompt
                
            if anthropic_tools:
                request_params["tools"] = anthropic_tools
            
            async with self.client.messages.stream(**request_params) as stream:
                async for event in stream:
                    if event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield LLMStreamResponse(
                                content=event.delta.text,
                                done=False,
                                model=self.model,
                                provider=self.provider_type.value,
                            )
                    elif event.type == "message_stop":
                        yield LLMStreamResponse(
                            content="",
                            done=True,
                            model=self.model,
                            provider=self.provider_type.value,
                        )
                        
        except AnthropicError as e:
            logger.error(
                "anthropic_stream_failed",
                error=str(e),
                model=self.model,
                provider=self.provider_type.value,
            )
            raise
        except Exception as e:
            logger.error(
                "anthropic_stream_unexpected_error",
                error=str(e),
                model=self.model,
                provider=self.provider_type.value,
            )
            raise

    def estimate_tokens(self, messages: List[Message]) -> int:
        """Estimate token count for Anthropic models.
        
        This is a rough estimation based on character count.
        Anthropic typically has similar tokenization to OpenAI.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Estimated token count
        """
        total_chars = sum(len(message.content) for message in messages)
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
            # Use claude-3-haiku as fallback
            cost_info = self.supported_models["claude-3-haiku-20240307"]
        else:
            cost_info = self.supported_models[self.model]
        
        input_cost = (input_tokens / 1000) * cost_info.input_cost_per_1k_tokens
        output_cost = (output_tokens / 1000) * cost_info.output_cost_per_1k_tokens
        
        return input_cost + output_cost

    async def validate_connection(self) -> bool:
        """Validate that the Anthropic connection is working.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Make a minimal API call to test the connection
            await self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],  # type: ignore[arg-type]
                max_tokens=1,
            )
            return True
        except (AnthropicError, ConnectionError, TimeoutError) as e:
            logger.error(
                "anthropic_connection_validation_failed",
                error=str(e),
                model=self.model,
                provider=self.provider_type.value,
            )
            return False

    def get_model_capabilities(self) -> Dict[str, bool]:
        """Get capabilities of the current Anthropic model.
        
        Returns:
            Dictionary of capability flags
        """
        base_capabilities = super().get_model_capabilities()
        
        # Model-specific capabilities
        if self.model == "claude-3-haiku-20240307":
            base_capabilities.update({
                "supports_json_mode": False,
                "supports_function_calling": True,
                "max_context_length": 200000,
                "supports_vision": True,
            })
        elif self.model == "claude-3-sonnet-20241022":
            base_capabilities.update({
                "supports_json_mode": False,
                "supports_function_calling": True,
                "max_context_length": 200000,
                "supports_vision": True,
            })
        elif self.model == "claude-3-opus-20240229":
            base_capabilities.update({
                "supports_json_mode": False,
                "supports_function_calling": True,
                "max_context_length": 200000,
                "supports_vision": True,
            })
        
        return base_capabilities