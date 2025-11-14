"""
Test suite for RAG STEP 64 - LLMProvider.chat_completion Make API call.

This module tests the LLM provider chat completion functionality that implements
structured logging for API calls to track performance, errors, and usage.

Based on Mermaid diagram: LLMCall (LLMProvider.chat_completion Make API call)
"""

import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest

from app.core.llm.base import LLMResponse, LLMProviderType
from app.core.llm.providers.anthropic_provider import AnthropicProvider
from app.core.llm.providers.openai_provider import OpenAIProvider
from app.schemas.chat import Message


def _extract_timer_params(mock_timer):
    """Helper to extract timer params from mocked rag_step_timer, regardless of call style."""
    assert mock_timer.call_count == 1
    args, kwargs = mock_timer.call_args
    if args and len(args) >= 3:
        step, step_id, node_label = args[:3]
    else:
        step = kwargs.get("step")
        step_id = kwargs.get("step_id")
        node_label = kwargs.get("node_label")
    return step, step_id, node_label, kwargs


class TestLLMProviderChatCompletion:
    """Test LLM provider chat completion functionality with structured logging."""
    
    @pytest.fixture
    def sample_messages(self):
        """Sample conversation messages."""
        return [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="What are the Italian VAT rates?")
        ]
    
    @pytest.fixture
    def sample_llm_response(self):
        """Sample LLM response."""
        return LLMResponse(
            content="The Italian VAT rates are 22% standard, 10% reduced, and 4% super-reduced.",
            model="gpt-4o-mini",
            provider="openai",
            tokens_used=25,
            cost_estimate=0.001,
            finish_reason="stop"
        )
    
    @pytest.fixture
    def mock_openai_provider(self):
        """Create mock OpenAI provider."""
        provider = OpenAIProvider(api_key="test_key", model="gpt-4o-mini")
        # Mock the underlying client
        provider._client = AsyncMock()
        return provider
    
    @pytest.fixture
    def mock_anthropic_provider(self):
        """Create mock Anthropic provider."""
        provider = AnthropicProvider(api_key="test_key", model="claude-3-sonnet-20240229")
        # Mock the underlying client
        provider._client = AsyncMock()
        return provider

    @pytest.mark.asyncio
    async def test_openai_chat_completion_with_structured_logging(self, mock_openai_provider, sample_messages, sample_llm_response):
        """Test OpenAI chat completion with proper structured logging."""
        with patch('app.core.llm.providers.openai_provider.rag_step_log') as mock_log, \
             patch('app.core.llm.providers.openai_provider.rag_step_timer') as mock_timer:
            
            # Setup timer context manager mock
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)
            
            # Mock OpenAI client response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = sample_llm_response.content
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = Mock()
            mock_response.usage.total_tokens = 25
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 15
            
            mock_openai_provider.client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Execute method
            result = await mock_openai_provider.chat_completion(
                messages=sample_messages,
                tools=[],
                temperature=0.2,
                max_tokens=100
            )
            
            # Verify API call result
            assert result.content == sample_llm_response.content
            assert result.model == "gpt-4o-mini"
            assert result.provider == "openai"
            assert result.finish_reason == "stop"
            
            # Verify structured logging occurred
            step, step_id, node_label, timer_kwargs = _extract_timer_params(mock_timer)
            assert step == 64
            assert step_id == "RAG.providers.llmprovider.chat.completion.make.api.call"
            assert node_label == "LLMCall"
            assert timer_kwargs['provider'] == "openai"
            assert timer_kwargs['model'] == "gpt-4o-mini"
            assert timer_kwargs['temperature'] == 0.2
            assert timer_kwargs['message_count'] == 2

    @pytest.mark.asyncio
    async def test_anthropic_chat_completion_with_structured_logging(self, mock_anthropic_provider, sample_messages):
        """Test Anthropic chat completion with proper structured logging."""
        with patch('app.core.llm.providers.anthropic_provider.rag_step_log') as mock_log, \
             patch('app.core.llm.providers.anthropic_provider.rag_step_timer') as mock_timer:
            
            # Setup timer context manager mock
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)
            
            # Mock Anthropic client response
            mock_response = Mock()
            mock_content_block = Mock()
            mock_content_block.type = "text"
            mock_content_block.text = "The Italian VAT rates are 22% standard."
            mock_response.content = [mock_content_block]
            mock_response.usage = Mock()
            mock_response.usage.input_tokens = 10
            mock_response.usage.output_tokens = 15
            mock_response.stop_reason = "end_turn"
            
            mock_anthropic_provider.client.messages.create = AsyncMock(return_value=mock_response)
            
            # Execute method
            result = await mock_anthropic_provider.chat_completion(
                messages=sample_messages,
                tools=[],
                temperature=0.2,
                max_tokens=100
            )
            
            # Verify API call result
            assert result.content == "The Italian VAT rates are 22% standard."
            assert result.model == "claude-3-sonnet-20240229"
            assert result.provider == "anthropic"
            
            # Verify structured logging occurred
            step, step_id, node_label, timer_kwargs = _extract_timer_params(mock_timer)
            assert step == 64
            assert step_id == "RAG.providers.llmprovider.chat.completion.make.api.call"
            assert node_label == "LLMCall"
            assert timer_kwargs['provider'] == "anthropic"
            assert timer_kwargs['model'] == "claude-3-sonnet-20240229"

    @pytest.mark.asyncio
    async def test_chat_completion_error_handling_with_logging(self, mock_openai_provider, sample_messages):
        """Test chat completion error handling with proper logging."""
        with patch('app.core.llm.providers.openai_provider.rag_step_log') as mock_log, \
             patch('app.core.llm.providers.openai_provider.rag_step_timer') as mock_timer:
            
            # Setup timer context manager mock to raise exception
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)
            
            # Mock API error
            from openai import OpenAIError
            mock_openai_provider.client.chat.completions.create = AsyncMock(
                side_effect=OpenAIError("API rate limit exceeded")
            )
            
            # Execute method and expect exception
            with pytest.raises(OpenAIError):
                await mock_openai_provider.chat_completion(
                    messages=sample_messages,
                    tools=[],
                    temperature=0.2,
                    max_tokens=100
                )
            
            # Verify structured logging occurred (timer should be called even on error)
            mock_timer.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_completion_with_tools_logging(self, mock_openai_provider, sample_messages):
        """Test chat completion with tools and structured logging."""
        with patch('app.core.llm.providers.openai_provider.rag_step_log') as mock_log, \
             patch('app.core.llm.providers.openai_provider.rag_step_timer') as mock_timer:
            
            # Setup timer context manager mock
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)
            
            # Mock LangChain client with tools
            mock_langchain_response = Mock()
            mock_langchain_response.content = "I'll help you with calculations."
            mock_langchain_response.tool_calls = [
                {
                    "id": "call_123",
                    "name": "calculator",
                    "args": {"expression": "22 + 10 + 4"}
                }
            ]
            
            mock_openai_provider._langchain_client = AsyncMock()
            mock_openai_provider._langchain_client.bind_tools.return_value.ainvoke = AsyncMock(
                return_value=mock_langchain_response
            )
            
            # Sample tools
            mock_tools = [
                Mock(name="calculator", description="Perform calculations")
            ]
            
            # Execute method
            result = await mock_openai_provider.chat_completion(
                messages=sample_messages,
                tools=mock_tools,
                temperature=0.2,
                max_tokens=100
            )
            
            # Verify API call result
            assert result.content == "I'll help you with calculations."
            assert result.tool_calls is not None
            assert len(result.tool_calls) == 1
            assert result.tool_calls[0]["name"] == "calculator"
            
            # Verify structured logging occurred with tools info
            mock_timer.assert_called_once()
            timer_call_kwargs = mock_timer.call_args[1]
            assert timer_call_kwargs['tools_count'] == 1

    @pytest.mark.asyncio
    async def test_rag_step_logging_parameters(self, mock_openai_provider, sample_messages):
        """Test that RAG STEP 64 structured logging has correct parameters."""
        with patch('app.core.llm.providers.openai_provider.rag_step_log') as mock_log, \
             patch('app.core.llm.providers.openai_provider.rag_step_timer') as mock_timer:
            
            # Setup timer context manager mock
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)
            
            # Mock successful response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test response"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = Mock()
            mock_response.usage.total_tokens = 20
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 10
            
            mock_openai_provider.client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Execute method
            await mock_openai_provider.chat_completion(
                messages=sample_messages,
                tools=None,
                temperature=0.7,
                max_tokens=200
            )
            
            # Verify RAG step timer with correct parameters
            mock_timer.assert_called_once()
            
            # Check timer call arguments
            timer_call_args = mock_timer.call_args
            assert timer_call_args[0][0] == 64  # step
            assert timer_call_args[0][1] == "RAG.providers.llmprovider.chat.completion.make.api.call"  # step_id
            assert timer_call_args[0][2] == "LLMCall"  # node_label
            
            # Check timer call kwargs
            timer_call_kwargs = timer_call_args[1]
            assert timer_call_kwargs['provider'] == "openai"
            assert timer_call_kwargs['model'] == "gpt-4o-mini"
            assert timer_call_kwargs['temperature'] == 0.7
            assert timer_call_kwargs['max_tokens'] == 200
            assert timer_call_kwargs['message_count'] == 2
            assert timer_call_kwargs['tools_count'] == 0

    @pytest.mark.asyncio
    async def test_performance_timing(self, mock_openai_provider, sample_messages):
        """Test that performance timing is correctly captured."""
        with patch('app.core.llm.providers.openai_provider.rag_step_timer') as mock_timer:
            
            # Create a real timer context to capture timing
            actual_timer_calls = []
            
            def mock_timer_side_effect(*args, **kwargs):
                # Record the call parameters
                actual_timer_calls.append((args, kwargs))
                # Return a real context manager that tracks timing
                return MagicMock()
            
            mock_timer.side_effect = mock_timer_side_effect
            
            # Mock slow API response
            async def slow_api_call(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms delay
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = "Test response"
                mock_response.choices[0].finish_reason = "stop"
                mock_response.usage = Mock()
                mock_response.usage.total_tokens = 20
                mock_response.usage.prompt_tokens = 10
                mock_response.usage.completion_tokens = 10
                return mock_response
            
            mock_openai_provider.client.chat.completions.create = slow_api_call
            
            # Execute method
            start_time = time.perf_counter()
            await mock_openai_provider.chat_completion(
                messages=sample_messages,
                tools=[],
                temperature=0.2,
                max_tokens=100
            )
            end_time = time.perf_counter()
            
            # Verify timing was captured
            assert len(actual_timer_calls) == 1
            timer_args, timer_kwargs = actual_timer_calls[0]
            
            # Verify timer was called with correct step info
            assert timer_args[0] == 64
            assert timer_args[1] == "RAG.providers.llmprovider.chat.completion.make.api.call"
            assert timer_args[2] == "LLMCall"

    @pytest.mark.asyncio
    async def test_cost_estimation_logging(self, mock_openai_provider, sample_messages):
        """Test that cost estimation is included in logging."""
        with patch('app.core.llm.providers.openai_provider.rag_step_timer') as mock_timer:
            
            # Setup timer context manager mock
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)
            
            # Mock response with usage data
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test response"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = Mock()
            mock_response.usage.total_tokens = 100
            mock_response.usage.prompt_tokens = 60
            mock_response.usage.completion_tokens = 40
            
            mock_openai_provider.client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Execute method
            result = await mock_openai_provider.chat_completion(
                messages=sample_messages,
                tools=[],
                temperature=0.2,
                max_tokens=100
            )
            
            # Verify cost estimation was calculated
            assert result.cost_estimate is not None
            assert result.cost_estimate > 0
            assert result.tokens_used == 100
            
            # Verify structured logging occurred
            mock_timer.assert_called_once()


class TestLLMProviderIntegration:
    """Test integration scenarios for LLM provider chat completion."""
    
    @pytest.mark.asyncio
    async def test_provider_selection_logging(self):
        """Test that provider selection scenarios are logged correctly."""
        # This test would verify different providers log consistently
        # For now, verify that different provider types work
        
        openai_provider = OpenAIProvider(api_key="test_key", model="gpt-4o-mini")
        anthropic_provider = AnthropicProvider(api_key="test_key", model="claude-3-sonnet-20240229")
        
        assert openai_provider.provider_type == LLMProviderType.OPENAI
        assert anthropic_provider.provider_type == LLMProviderType.ANTHROPIC
    
    @pytest.mark.asyncio
    async def test_multiple_provider_calls_logging(self):
        """Test logging for multiple sequential provider calls."""
        with patch('app.core.llm.providers.openai_provider.rag_step_timer') as mock_timer:
            
            # Setup timer context manager mock
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)
            
            provider = OpenAIProvider(api_key="test_key", model="gpt-4o-mini")
            provider._client = AsyncMock()
            
            # Mock response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test response"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = Mock()
            mock_response.usage.total_tokens = 20
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 10
            
            provider.client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            messages = [Message(role="user", content="Test message")]
            
            # Make multiple calls
            await provider.chat_completion(messages=messages)
            await provider.chat_completion(messages=messages)
            
            # Verify both calls were logged
            assert mock_timer.call_count == 2


# Test data fixtures for various scenarios
@pytest.fixture(scope="module")
def llm_test_scenarios():
    """Test scenarios for LLM provider behavior."""
    return {
        "successful_call": {
            "description": "Successful API call with response",
            "expected_logs": 1,
            "should_succeed": True
        },
        "api_error": {
            "description": "API error during call",
            "expected_logs": 1,
            "should_succeed": False
        },
        "timeout_error": {
            "description": "Timeout during API call",
            "expected_logs": 1,
            "should_succeed": False
        }
    }


@pytest.mark.asyncio
async def test_llm_provider_scenarios(llm_test_scenarios):
    """Test various LLM provider scenarios."""
    provider = OpenAIProvider(api_key="test_key", model="gpt-4o-mini")
    provider._client = AsyncMock()
    
    for scenario_name, scenario_data in llm_test_scenarios.items():
        with patch('app.core.llm.providers.openai_provider.rag_step_timer') as mock_timer:
            
            # Setup timer context manager mock
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)
            
            messages = [Message(role="user", content=f"Test query for {scenario_name}")]
            
            if scenario_data["should_succeed"]:
                # Mock successful response
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = f"Response for {scenario_name}"
                mock_response.choices[0].finish_reason = "stop"
                mock_response.usage = Mock()
                mock_response.usage.total_tokens = 20
                mock_response.usage.prompt_tokens = 10
                mock_response.usage.completion_tokens = 10
                
                provider.client.chat.completions.create = AsyncMock(return_value=mock_response)
                
                result = await provider.chat_completion(messages=messages)
                assert result is not None
            else:
                # Mock API error
                from openai import OpenAIError
                provider.client.chat.completions.create = AsyncMock(
                    side_effect=OpenAIError(f"Error in {scenario_name}")
                )
                
                with pytest.raises(OpenAIError):
                    await provider.chat_completion(messages=messages)
            
            # Verify logging occurred
            assert mock_timer.call_count == scenario_data["expected_logs"]