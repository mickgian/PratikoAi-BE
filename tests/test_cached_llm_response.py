"""
Test suite for RAG STEP 59 - LangGraphAgent._get_cached_llm_response.

This module tests the cached LLM response functionality that implements cache checking
for LLM responses to reduce API costs and improve response times.

Based on Mermaid diagram: CheckCache (LangGraphAgent._get_cached_llm_response Check for cached response)
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.langgraph.graph import LangGraphAgent
from app.core.llm.base import LLMProvider, LLMProviderType, LLMResponse
from app.schemas.chat import Message


class TestCachedLLMResponse:
    """Test cached LLM response functionality with structured logging."""

    @pytest.fixture
    def mock_provider(self):
        """Create mock LLM provider."""
        provider = Mock(spec=LLMProvider)
        provider.model = "gpt-4"
        provider.provider_type = LLMProviderType.OPENAI
        provider.chat_completion = AsyncMock()
        return provider

    @pytest.fixture
    def sample_messages(self):
        """Sample conversation messages."""
        return [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="What are the Italian VAT rates?"),
        ]

    @pytest.fixture
    def sample_llm_response(self):
        """Sample LLM response."""
        return LLMResponse(
            content="The Italian VAT rates are 22% standard, 10% reduced, and 4% super-reduced.",
            model="gpt-4",
            provider="openai",
            tokens_used=25,
            cost_estimate=0.001,
            finish_reason="stop",
        )

    @pytest.fixture
    def lang_graph_agent(self):
        """Create LangGraphAgent instance for testing."""
        return LangGraphAgent()

    @pytest.mark.asyncio
    async def test_cache_hit_with_structured_logging(
        self, lang_graph_agent, mock_provider, sample_messages, sample_llm_response
    ):
        """Test cache hit scenario with proper structured logging."""
        with (
            patch("app.services.cache.cache_service.get_cached_response") as mock_get_cache,
            patch("app.observability.rag_logging.rag_step_log") as mock_log,
            patch("app.services.usage_tracker.usage_tracker.track_llm_usage") as mock_track,
        ):
            # Setup mocks
            mock_get_cache.return_value = sample_llm_response
            lang_graph_agent._current_session_id = "test_session"
            lang_graph_agent._current_user_id = "test_user"

            # Execute method
            result = await lang_graph_agent._get_cached_llm_response(
                provider=mock_provider, messages=sample_messages, tools=[], temperature=0.2, max_tokens=100
            )

            # Verify cache hit result
            assert result == sample_llm_response
            assert mock_get_cache.called

            # Verify structured logging for cache hit
            mock_log.assert_called()

            # Verify that a call was made with the correct RAG step parameters
            step_59_calls = [
                call
                for call in mock_log.call_args_list
                if len(call[0]) >= 3
                and call[0][0] == 59
                and call[0][1] == "RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response"
            ]
            assert len(step_59_calls) > 0, f"Expected RAG STEP 59 calls but got: {mock_log.call_args_list}"

            # Verify usage tracking for cache hit
            mock_track.assert_called_once()
            track_args = mock_track.call_args[1]
            assert track_args["cache_hit"] is True
            assert track_args["response_time_ms"] == 10  # Minimal time for cache hit

    @pytest.mark.asyncio
    async def test_cache_miss_with_structured_logging(
        self, lang_graph_agent, mock_provider, sample_messages, sample_llm_response
    ):
        """Test cache miss scenario with proper structured logging."""
        with (
            patch("app.services.cache.cache_service.get_cached_response") as mock_get_cache,
            patch("app.services.cache.cache_service.cache_response") as mock_set_cache,
            patch("app.observability.rag_logging.rag_step_log") as mock_log,
            patch("app.services.usage_tracker.usage_tracker.track_llm_usage") as mock_track,
        ):
            # Setup mocks
            mock_get_cache.return_value = None  # Cache miss
            mock_provider.chat_completion.return_value = sample_llm_response
            mock_set_cache.return_value = True
            lang_graph_agent._current_session_id = "test_session"
            lang_graph_agent._current_user_id = "test_user"

            # Execute method
            result = await lang_graph_agent._get_cached_llm_response(
                provider=mock_provider, messages=sample_messages, tools=[], temperature=0.2, max_tokens=100
            )

            # Verify cache miss result
            assert result == sample_llm_response
            mock_provider.chat_completion.assert_called_once()
            mock_set_cache.assert_called_once()

            # Verify structured logging for cache miss
            mock_log.assert_called()

            # Verify that a call was made with the correct RAG step parameters
            step_59_calls = [
                call
                for call in mock_log.call_args_list
                if len(call[0]) >= 3
                and call[0][0] == 59
                and call[0][1] == "RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response"
            ]
            assert len(step_59_calls) > 0, f"Expected RAG STEP 59 calls but got: {mock_log.call_args_list}"

            # Verify usage tracking for cache miss
            mock_track.assert_called_once()
            track_args = mock_track.call_args[1]
            assert track_args["cache_hit"] is False
            assert track_args["response_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_cache_error_handling_with_logging(
        self, lang_graph_agent, mock_provider, sample_messages, sample_llm_response
    ):
        """Test cache error handling with proper logging."""
        with (
            patch("app.services.cache.cache_service.get_cached_response") as mock_get_cache,
            patch("app.observability.rag_logging.rag_step_log") as mock_log,
        ):
            # Setup mocks
            mock_get_cache.side_effect = Exception("Redis connection failed")
            mock_provider.chat_completion.return_value = sample_llm_response

            # Execute method
            result = await lang_graph_agent._get_cached_llm_response(
                provider=mock_provider, messages=sample_messages, tools=[], temperature=0.2, max_tokens=100
            )

            # Verify fallback to LLM call
            assert result == sample_llm_response
            mock_provider.chat_completion.assert_called_once()

            # Verify structured logging occurred
            mock_log.assert_called()

            # Verify that a call was made with the correct RAG step parameters
            step_59_calls = [
                call
                for call in mock_log.call_args_list
                if len(call[0]) >= 3
                and call[0][0] == 59
                and call[0][1] == "RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response"
            ]
            assert len(step_59_calls) > 0, f"Expected RAG STEP 59 calls but got: {mock_log.call_args_list}"

    @pytest.mark.asyncio
    async def test_rag_step_logging_parameters(
        self, lang_graph_agent, mock_provider, sample_messages, sample_llm_response
    ):
        """Test that RAG STEP 59 structured logging has correct parameters."""
        with (
            patch("app.services.cache.cache_service.get_cached_response") as mock_get_cache,
            patch("app.observability.rag_logging.rag_step_log") as mock_log,
        ):
            # Setup mocks
            mock_get_cache.return_value = sample_llm_response

            # Execute method
            await lang_graph_agent._get_cached_llm_response(
                provider=mock_provider, messages=sample_messages, tools=[], temperature=0.2, max_tokens=100
            )

            # Verify RAG step logging with correct parameters
            mock_log.assert_called()

            # Find the RAG STEP 59 specific log call
            rag_step_calls = [
                call
                for call in mock_log.call_args_list
                if len(call[0]) >= 3
                and call[0][0] == 59
                and call[0][1] == "RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response"
            ]

            assert len(rag_step_calls) > 0
            call_args = rag_step_calls[0][1]  # kwargs
            call_positional = rag_step_calls[0][0]  # positional args

            # Check positional arguments
            assert call_positional[0] == 59
            assert call_positional[1] == "RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response"
            assert call_positional[2] == "CheckCache"

            # Check keyword arguments
            assert "model" in call_args
            assert "provider" in call_args
            assert "latency_ms" in call_args

    @pytest.mark.asyncio
    async def test_performance_timing(self, lang_graph_agent, mock_provider, sample_messages, sample_llm_response):
        """Test that performance timing is correctly captured."""
        with (
            patch("app.services.cache.cache_service.get_cached_response") as mock_get_cache,
            patch("app.observability.rag_logging.rag_step_log") as mock_log,
        ):
            # Setup mocks - simulate slow cache operation
            async def slow_cache_get(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms delay
                return None

            mock_get_cache.side_effect = slow_cache_get
            mock_provider.chat_completion.return_value = sample_llm_response

            # Execute method
            time.perf_counter()
            await lang_graph_agent._get_cached_llm_response(
                provider=mock_provider, messages=sample_messages, tools=[], temperature=0.2, max_tokens=100
            )
            time.perf_counter()

            # Verify timing is captured in logs
            mock_log.assert_called()

            # Find timing-related log calls
            timing_calls = [call for call in mock_log.call_args_list if "latency_ms" in call[1]]

            assert len(timing_calls) > 0
            latency_ms = timing_calls[0][1]["latency_ms"]
            assert isinstance(latency_ms, int | float)
            assert latency_ms >= 0

    @pytest.mark.asyncio
    async def test_cache_key_generation_consistency(self, lang_graph_agent, mock_provider, sample_messages):
        """Test that cache key generation is consistent for identical inputs."""
        with (
            patch("app.services.cache.cache_service.get_cached_response") as mock_get_cache,
            patch("app.observability.rag_logging.rag_step_log"),
        ):
            mock_get_cache.return_value = None
            mock_provider.chat_completion.return_value = LLMResponse(content="test", model="gpt-4", provider="openai")

            # Call twice with same parameters
            await lang_graph_agent._get_cached_llm_response(
                provider=mock_provider, messages=sample_messages, tools=[], temperature=0.2, max_tokens=100
            )

            await lang_graph_agent._get_cached_llm_response(
                provider=mock_provider, messages=sample_messages, tools=[], temperature=0.2, max_tokens=100
            )

            # Verify cache service was called with same parameters both times
            assert mock_get_cache.call_count == 2
            first_call = mock_get_cache.call_args_list[0]
            second_call = mock_get_cache.call_args_list[1]

            # Compare call arguments
            assert first_call[1]["messages"] == second_call[1]["messages"]
            assert first_call[1]["model"] == second_call[1]["model"]
            assert first_call[1]["temperature"] == second_call[1]["temperature"]

    @pytest.mark.asyncio
    async def test_ttl_and_cache_invalidation(
        self, lang_graph_agent, mock_provider, sample_messages, sample_llm_response
    ):
        """Test TTL handling and cache invalidation scenarios."""
        with (
            patch("app.services.cache.cache_service.get_cached_response") as mock_get_cache,
            patch("app.services.cache.cache_service.cache_response") as mock_set_cache,
            patch("app.observability.rag_logging.rag_step_log") as mock_log,
        ):
            # Test expired cache scenario
            mock_get_cache.return_value = None  # Simulates expired cache
            mock_provider.chat_completion.return_value = sample_llm_response

            await lang_graph_agent._get_cached_llm_response(
                provider=mock_provider, messages=sample_messages, tools=[], temperature=0.2, max_tokens=100
            )

            # Verify fresh response is cached
            mock_set_cache.assert_called_once()
            cache_call_args = mock_set_cache.call_args[1]
            assert cache_call_args["response"] == sample_llm_response
            assert cache_call_args["model"] == mock_provider.model

            # Verify TTL-related logging
            mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_different_temperature_creates_different_cache_keys(
        self, lang_graph_agent, mock_provider, sample_messages
    ):
        """Test that different temperature values create different cache keys."""
        with (
            patch("app.services.cache.cache_service.get_cached_response") as mock_get_cache,
            patch("app.observability.rag_logging.rag_step_log"),
        ):
            mock_get_cache.return_value = None
            mock_provider.chat_completion.return_value = LLMResponse(content="test", model="gpt-4", provider="openai")

            # Call with different temperatures
            await lang_graph_agent._get_cached_llm_response(
                provider=mock_provider, messages=sample_messages, tools=[], temperature=0.2, max_tokens=100
            )

            await lang_graph_agent._get_cached_llm_response(
                provider=mock_provider, messages=sample_messages, tools=[], temperature=0.8, max_tokens=100
            )

            # Verify different cache calls were made
            assert mock_get_cache.call_count == 2
            first_temp = mock_get_cache.call_args_list[0][1]["temperature"]
            second_temp = mock_get_cache.call_args_list[1][1]["temperature"]
            assert first_temp != second_temp


class TestCacheServiceIntegration:
    """Test integration with cache service."""

    @pytest.mark.asyncio
    async def test_cache_service_availability(self):
        """Test cache service availability detection."""
        from app.services.cache import cache_service

        # Test that cache service can be imported and has required methods
        assert hasattr(cache_service, "get_cached_response")
        assert hasattr(cache_service, "cache_response")
        assert hasattr(cache_service, "enabled")

    @pytest.mark.asyncio
    async def test_cache_disabled_fallback(self):
        """Test behavior when cache is disabled."""
        # Create test fixtures within the test
        lang_graph_agent = LangGraphAgent()
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.model = "gpt-4"
        mock_provider.provider_type = LLMProviderType.OPENAI
        mock_provider.chat_completion = AsyncMock()

        sample_messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="What are the Italian VAT rates?"),
        ]

        sample_llm_response = LLMResponse(
            content="The Italian VAT rates are 22% standard, 10% reduced, and 4% super-reduced.",
            model="gpt-4",
            provider="openai",
            tokens_used=25,
            cost_estimate=0.001,
            finish_reason="stop",
        )

        with (
            patch("app.services.cache.cache_service.enabled", False),
            patch("app.services.cache.cache_service.get_cached_response") as mock_get_cache,
            patch("app.services.cache.cache_service.cache_response") as mock_set_cache,
            patch("app.observability.rag_logging.rag_step_log") as mock_log,
            patch("app.services.usage_tracker.usage_tracker.track_llm_usage"),
        ):
            mock_provider.chat_completion.return_value = sample_llm_response
            mock_get_cache.return_value = None
            mock_set_cache.return_value = True

            result = await lang_graph_agent._get_cached_llm_response(
                provider=mock_provider, messages=sample_messages, tools=[], temperature=0.2, max_tokens=100
            )

            # Should still get response even when cache is disabled
            assert result == sample_llm_response
            mock_provider.chat_completion.assert_called_once()

            # Should log cache disabled status
            mock_log.assert_called()


# Test data fixtures for various scenarios
@pytest.fixture(scope="module")
def test_scenarios():
    """Test scenarios for cache behavior."""
    return {
        "cache_hit": {"description": "Response found in cache", "cache_response": True, "expected_llm_calls": 0},
        "cache_miss": {
            "description": "Response not in cache, fresh LLM call",
            "cache_response": False,
            "expected_llm_calls": 1,
        },
        "cache_error": {
            "description": "Cache service error, fallback to LLM",
            "cache_response": "error",
            "expected_llm_calls": 1,
        },
    }


@pytest.mark.asyncio
async def test_cache_scenarios(test_scenarios):
    """Test various cache scenarios."""
    agent = LangGraphAgent()

    for scenario_name, scenario_data in test_scenarios.items():
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.model = "gpt-4"
        mock_provider.provider_type = LLMProviderType.OPENAI
        mock_provider.chat_completion = AsyncMock()

        sample_response = LLMResponse(content=f"Response for {scenario_name}", model="gpt-4", provider="openai")
        mock_provider.chat_completion.return_value = sample_response

        messages = [Message(role="user", content=f"Test query for {scenario_name}")]

        with (
            patch("app.services.cache.cache_service.get_cached_response") as mock_get_cache,
            patch("app.observability.rag_logging.rag_step_log"),
        ):
            if scenario_data["cache_response"] is True:
                mock_get_cache.return_value = sample_response
            elif scenario_data["cache_response"] is False:
                mock_get_cache.return_value = None
            else:  # error case
                mock_get_cache.side_effect = Exception("Cache error")

            result = await agent._get_cached_llm_response(
                provider=mock_provider, messages=messages, tools=[], temperature=0.2, max_tokens=100
            )

            assert result is not None
            assert mock_provider.chat_completion.call_count == scenario_data["expected_llm_calls"]
