"""Tests for OpenAI provider."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.models.query import LLMResponse
from app.services.openai_provider import OpenAIProvider, OpenAIResponse


class TestOpenAIProvider:
    """Test OpenAIProvider class."""

    @patch("app.services.openai_provider.settings")
    def test_initialization_with_api_key(self, mock_settings):
        """Test OpenAI provider initialization with API key."""
        mock_settings.openai_api_key = "test-api-key"

        provider = OpenAIProvider(model="gpt-4o-mini")

        assert provider.model == "gpt-4o-mini"
        assert provider.api_key == "test-api-key"
        assert provider.base_url == "https://api.openai.com/v1"

    @patch("app.services.openai_provider.settings")
    def test_initialization_without_api_key(self, mock_settings):
        """Test OpenAI provider initialization without API key."""
        mock_settings.openai_api_key = None

        provider = OpenAIProvider()

        assert provider.api_key is None

    @pytest.mark.asyncio
    @patch("app.services.openai_provider.settings")
    async def test_complete_no_api_key(self, mock_settings):
        """Test completion fails without API key."""
        mock_settings.openai_api_key = None

        provider = OpenAIProvider()

        with pytest.raises(Exception, match="OpenAI API key not configured"):
            await provider.complete(prompt="Test", user_id="user123")

    @pytest.mark.asyncio
    @patch("app.services.openai_provider.httpx.AsyncClient")
    @patch("app.services.openai_provider.settings")
    async def test_complete_success(self, mock_settings, mock_httpx):
        """Test successful completion."""
        mock_settings.openai_api_key = "test-api-key"

        # Mock OpenAI API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello, how can I help you?"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 50, "prompt_tokens": 10, "completion_tokens": 40},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = OpenAIProvider(model="gpt-4o-mini")
        result = await provider.complete(prompt="Hello", user_id="user123")

        assert isinstance(result, LLMResponse)
        assert result.text == "Hello, how can I help you?"
        assert result.model == "gpt-4o-mini"
        assert result.tokens_used == 50
        assert result.provider == "openai"
        assert result.response_metadata["finish_reason"] == "stop"

    @pytest.mark.asyncio
    @patch("app.services.openai_provider.httpx.AsyncClient")
    @patch("app.services.openai_provider.settings")
    async def test_complete_with_system_prompt(self, mock_settings, mock_httpx):
        """Test completion with system prompt."""
        mock_settings.openai_api_key = "test-api-key"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 30, "prompt_tokens": 15, "completion_tokens": 15},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = OpenAIProvider()
        await provider.complete(prompt="Test", user_id="user123", system_prompt="You are a helpful assistant")

        # Verify system prompt was included in messages
        call_args = mock_client.post.call_args
        messages = call_args.kwargs["json"]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant"

    @pytest.mark.asyncio
    @patch("app.services.openai_provider.httpx.AsyncClient")
    @patch("app.services.openai_provider.settings")
    async def test_complete_with_custom_parameters(self, mock_settings, mock_httpx):
        """Test completion with custom parameters."""
        mock_settings.openai_api_key = "test-api-key"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 30, "prompt_tokens": 15, "completion_tokens": 15},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = OpenAIProvider()
        await provider.complete(
            prompt="Test", user_id="user123", model="gpt-4", max_tokens=500, temperature=0.5, timeout=60.0
        )

        call_args = mock_client.post.call_args
        request_data = call_args.kwargs["json"]
        assert request_data["model"] == "gpt-4"
        assert request_data["max_tokens"] == 500
        assert request_data["temperature"] == 0.5

    @pytest.mark.asyncio
    @patch("app.services.openai_provider.httpx.AsyncClient")
    @patch("app.services.openai_provider.settings")
    async def test_complete_http_error(self, mock_settings, mock_httpx):
        """Test completion with HTTP error."""
        mock_settings.openai_api_key = "test-api-key"

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limit", request=Mock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = OpenAIProvider()

        with pytest.raises(httpx.HTTPStatusError):
            await provider.complete(prompt="Test", user_id="user123")

    @pytest.mark.asyncio
    @patch("app.services.openai_provider.httpx.AsyncClient")
    @patch("app.services.openai_provider.settings")
    async def test_complete_timeout_error(self, mock_settings, mock_httpx):
        """Test completion with timeout error."""
        mock_settings.openai_api_key = "test-api-key"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = OpenAIProvider()

        with pytest.raises(TimeoutError, match="OpenAI API request timed out"):
            await provider.complete(prompt="Test", user_id="user123")

    @pytest.mark.asyncio
    @patch("app.services.openai_provider.httpx.AsyncClient")
    @patch("app.services.openai_provider.settings")
    async def test_complete_generic_error(self, mock_settings, mock_httpx):
        """Test completion with generic error."""
        mock_settings.openai_api_key = "test-api-key"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Unexpected error"))
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = OpenAIProvider()

        with pytest.raises(Exception, match="Unexpected error"):
            await provider.complete(prompt="Test", user_id="user123")

    @patch("app.services.openai_provider.settings")
    def test_calculate_cost_gpt4o_mini(self, mock_settings):
        """Test cost calculation for GPT-4o-mini."""
        mock_settings.openai_api_key = "test-api-key"

        provider = OpenAIProvider()
        cost = provider._calculate_cost("gpt-4o-mini", prompt_tokens=1000, completion_tokens=500)

        # GPT-4o-mini: $0.00015 input, $0.0006 output per 1K tokens
        expected_cost = (1000 / 1000 * 0.00015) + (500 / 1000 * 0.0006)
        assert cost == pytest.approx(expected_cost)

    @patch("app.services.openai_provider.settings")
    def test_calculate_cost_gpt4(self, mock_settings):
        """Test cost calculation for GPT-4."""
        mock_settings.openai_api_key = "test-api-key"

        provider = OpenAIProvider()
        cost = provider._calculate_cost("gpt-4", prompt_tokens=1000, completion_tokens=500)

        # GPT-4: $0.03 input, $0.06 output per 1K tokens
        expected_cost = (1000 / 1000 * 0.03) + (500 / 1000 * 0.06)
        assert cost == pytest.approx(expected_cost)

    @patch("app.services.openai_provider.settings")
    def test_calculate_cost_unknown_model(self, mock_settings):
        """Test cost calculation defaults to GPT-4 pricing for unknown model."""
        mock_settings.openai_api_key = "test-api-key"

        provider = OpenAIProvider()
        cost = provider._calculate_cost("unknown-model", prompt_tokens=1000, completion_tokens=500)

        # Should default to GPT-4 pricing
        expected_cost = (1000 / 1000 * 0.03) + (500 / 1000 * 0.06)
        assert cost == pytest.approx(expected_cost)

    @pytest.mark.asyncio
    @patch("app.services.openai_provider.settings")
    async def test_health_check_no_api_key(self, mock_settings):
        """Test health check without API key."""
        mock_settings.openai_api_key = None

        provider = OpenAIProvider()
        result = await provider.health_check()

        assert result["status"] == "error"
        assert "API key not configured" in result["message"]

    @pytest.mark.asyncio
    @patch("app.services.openai_provider.httpx.AsyncClient")
    @patch("app.services.openai_provider.settings")
    async def test_health_check_success(self, mock_settings, mock_httpx):
        """Test successful health check."""
        mock_settings.openai_api_key = "test-api-key"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 5, "prompt_tokens": 2, "completion_tokens": 3},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = OpenAIProvider(model="gpt-4o-mini")
        result = await provider.health_check()

        assert result["status"] == "healthy"
        assert result["model"] == "gpt-4o-mini"
        assert "response_time" in result

    @pytest.mark.asyncio
    @patch("app.services.openai_provider.httpx.AsyncClient")
    @patch("app.services.openai_provider.settings")
    async def test_health_check_failure(self, mock_settings, mock_httpx):
        """Test health check failure."""
        mock_settings.openai_api_key = "test-api-key"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("API error"))
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = OpenAIProvider()
        result = await provider.health_check()

        assert result["status"] == "unhealthy"
        assert "API error" in result["error"]
