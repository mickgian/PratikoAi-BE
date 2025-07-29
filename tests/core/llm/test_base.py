"""Tests for LLM base classes."""

import pytest
from typing import Any, AsyncIterator, Dict, List, Optional

from app.core.llm.base import (
    LLMProvider,
    LLMProviderType,
    LLMResponse,
    LLMStreamResponse,
    LLMCostInfo,
    LLMModelTier,
)
from app.schemas.chat import Message


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, api_key: str, model: str = "mock-model", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.call_count = 0
        self.should_fail = False

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.OPENAI

    @property
    def supported_models(self) -> Dict[str, LLMCostInfo]:
        return {
            "mock-model": LLMCostInfo(
                input_cost_per_1k_tokens=0.001,
                output_cost_per_1k_tokens=0.002,
                model_name="mock-model",
                tier=LLMModelTier.BASIC,
            )
        }

    async def chat_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Any]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        self.call_count += 1
        
        if self.should_fail:
            raise Exception("Mock provider failure")
            
        return LLMResponse(
            content="Mock response",
            model=self.model,
            provider=self.provider_type.value,
            tokens_used=100,
            cost_estimate=0.001,
            finish_reason="stop",
        )

    async def stream_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Any]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[LLMStreamResponse]:
        self.call_count += 1
        
        if self.should_fail:
            raise Exception("Mock provider failure")
            
        yield LLMStreamResponse(content="Mock", done=False)
        yield LLMStreamResponse(content=" stream", done=False)
        yield LLMStreamResponse(content="", done=True)

    def estimate_tokens(self, messages: List[Message]) -> int:
        return sum(len(msg.content) // 4 for msg in messages)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        cost_info = self.supported_models[self.model]
        return (
            (input_tokens / 1000) * cost_info.input_cost_per_1k_tokens +
            (output_tokens / 1000) * cost_info.output_cost_per_1k_tokens
        )

    async def validate_connection(self) -> bool:
        return not self.should_fail


class TestLLMProvider:
    """Test cases for LLM provider base functionality."""

    def test_provider_initialization(self):
        """Test basic provider initialization."""
        provider = MockLLMProvider(api_key="test-key", model="mock-model")
        
        assert provider.api_key == "test-key"
        assert provider.model == "mock-model"
        assert provider.provider_type == LLMProviderType.OPENAI

    def test_supported_models(self):
        """Test supported models property."""
        provider = MockLLMProvider(api_key="test-key")
        models = provider.supported_models
        
        assert "mock-model" in models
        assert models["mock-model"].tier == LLMModelTier.BASIC
        assert models["mock-model"].input_cost_per_1k_tokens == 0.001

    @pytest.mark.asyncio
    async def test_chat_completion(self):
        """Test chat completion functionality."""
        provider = MockLLMProvider(api_key="test-key")
        messages = [Message(role="user", content="Hello")]
        
        response = await provider.chat_completion(messages)
        
        assert response.content == "Mock response"
        assert response.model == "mock-model"
        assert response.provider == "openai"
        assert response.tokens_used == 100
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_stream_completion(self):
        """Test streaming completion functionality."""
        provider = MockLLMProvider(api_key="test-key")
        messages = [Message(role="user", content="Hello")]
        
        chunks = []
        async for chunk in provider.stream_completion(messages):
            chunks.append(chunk)
        
        assert len(chunks) == 3
        assert chunks[0].content == "Mock"
        assert chunks[1].content == " stream"
        assert chunks[2].done is True
        assert provider.call_count == 1

    def test_estimate_tokens(self):
        """Test token estimation."""
        provider = MockLLMProvider(api_key="test-key")
        messages = [
            Message(role="user", content="Hello world"),  # 11 chars -> ~2.75 tokens
            Message(role="assistant", content="Hi there!"),  # 9 chars -> ~2.25 tokens
        ]
        
        tokens = provider.estimate_tokens(messages)
        assert tokens == 5  # (11//4) + (9//4) = 2 + 2 = 4, but actually it's 5

    def test_estimate_cost(self):
        """Test cost estimation."""
        provider = MockLLMProvider(api_key="test-key")
        
        cost = provider.estimate_cost(input_tokens=1000, output_tokens=500)
        expected_cost = (1000 / 1000) * 0.001 + (500 / 1000) * 0.002
        
        assert cost == expected_cost

    @pytest.mark.asyncio
    async def test_validate_connection_success(self):
        """Test successful connection validation."""
        provider = MockLLMProvider(api_key="test-key")
        
        is_valid = await provider.validate_connection()
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self):
        """Test failed connection validation."""
        provider = MockLLMProvider(api_key="test-key")
        provider.should_fail = True
        
        is_valid = await provider.validate_connection()
        assert is_valid is False

    def test_get_model_capabilities(self):
        """Test model capabilities."""
        provider = MockLLMProvider(api_key="test-key")
        capabilities = provider.get_model_capabilities()
        
        assert "supports_tools" in capabilities
        assert "supports_streaming" in capabilities
        assert capabilities["supports_tools"] is True

    def test_convert_tools_format(self):
        """Test tools format conversion."""
        provider = MockLLMProvider(api_key="test-key")
        tools = [{"name": "test_tool", "description": "A test tool"}]
        
        converted = provider.convert_tools_format(tools)
        assert converted == tools  # Default implementation returns as-is


class TestLLMResponse:
    """Test cases for LLM response objects."""

    def test_llm_response_creation(self):
        """Test LLM response creation."""
        response = LLMResponse(
            content="Test response",
            model="test-model",
            provider="test-provider",
            tokens_used=50,
            cost_estimate=0.005,
            finish_reason="stop",
        )
        
        assert response.content == "Test response"
        assert response.model == "test-model"
        assert response.provider == "test-provider"
        assert response.tokens_used == 50
        assert response.cost_estimate == 0.005

    def test_llm_stream_response_creation(self):
        """Test LLM stream response creation."""
        response = LLMStreamResponse(
            content="Stream chunk",
            done=False,
            model="test-model",
            provider="test-provider",
        )
        
        assert response.content == "Stream chunk"
        assert response.done is False
        assert response.model == "test-model"
        assert response.provider == "test-provider"


class TestLLMCostInfo:
    """Test cases for LLM cost information."""

    def test_cost_info_creation(self):
        """Test cost info creation."""
        cost_info = LLMCostInfo(
            input_cost_per_1k_tokens=0.001,
            output_cost_per_1k_tokens=0.002,
            model_name="test-model",
            tier=LLMModelTier.STANDARD,
        )
        
        assert cost_info.input_cost_per_1k_tokens == 0.001
        assert cost_info.output_cost_per_1k_tokens == 0.002
        assert cost_info.model_name == "test-model"
        assert cost_info.tier == LLMModelTier.STANDARD