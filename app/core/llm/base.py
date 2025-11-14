"""Base classes for LLM provider abstraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.schemas.chat import Message


class LLMProviderType(str, Enum):
    """Supported LLM provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class LLMModelTier(str, Enum):
    """Model capability tiers for cost optimization."""
    BASIC = "basic"          # Simple queries, cheap models
    STANDARD = "standard"    # General purpose
    ADVANCED = "advanced"    # Complex reasoning, expensive models
    PREMIUM = "premium"      # Highest capability models


@dataclass
class LLMCostInfo:
    """Cost information for an LLM provider."""
    input_cost_per_1k_tokens: float
    output_cost_per_1k_tokens: float
    model_name: str
    tier: LLMModelTier


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class LLMStreamResponse:
    """Streaming response chunk from an LLM provider."""
    content: str
    done: bool = False
    model: Optional[str] = None
    provider: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, api_key: str, model: str, **kwargs):
        """Initialize the LLM provider.
        
        Args:
            api_key: API key for the provider
            model: Model name to use
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.model = model
        self.config = kwargs

    @property
    @abstractmethod
    def provider_type(self) -> LLMProviderType:
        """Get the provider type."""
        pass

    @property
    @abstractmethod
    def supported_models(self) -> Dict[str, LLMCostInfo]:
        """Get supported models and their cost information."""
        pass

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Any]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a chat completion.
        
        Args:
            messages: List of conversation messages
            tools: Optional list of tools available to the model
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse with the generated content
        """
        pass

    @abstractmethod
    async def stream_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Any]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamResponse, None]:
        """Generate a streaming chat completion.

        Args:
            messages: List of conversation messages
            tools: Optional list of tools available to the model
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Yields:
            LLMStreamResponse chunks
        """
        pass

    @abstractmethod
    def estimate_tokens(self, messages: List[Message]) -> int:
        """Estimate token count for a list of messages.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Estimated token count
        """
        pass

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for given token counts.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in EUR
        """
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate that the provider connection is working.
        
        Returns:
            True if connection is valid, False otherwise
        """
        pass

    def get_model_capabilities(self) -> Dict[str, bool]:
        """Get capabilities of the current model.
        
        Returns:
            Dictionary of capability flags
        """
        return {
            "supports_tools": True,
            "supports_streaming": True,
            "supports_system_messages": True,
            "supports_json_mode": False,
            "max_context_length": 4096,
        }

    def convert_tools_format(self, tools: Optional[List[Any]]) -> Optional[List[Any]]:
        """Convert tools to provider-specific format.
        
        Args:
            tools: List of tools in standard format
            
        Returns:
            Tools converted to provider format
        """
        # Default implementation - no conversion needed
        return tools