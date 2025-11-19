"""Tests for Anthropic provider."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.models.query import LLMResponse
from app.services.anthropic_provider import AnthropicProvider, AnthropicResponse


class TestAnthropicProvider:
    """Test AnthropicProvider class."""

    @patch("app.services.anthropic_provider.settings")
    def test_initialization_with_api_key(self, mock_settings):
        """Test Anthropic provider initialization with API key."""
        mock_settings.anthropic_api_key = "test-api-key"

        provider = AnthropicProvider(model="claude-3-haiku-20240307")

        assert provider.model == "claude-3-haiku-20240307"
        assert provider.api_key == "test-api-key"
        assert provider.base_url == "https://api.anthropic.com/v1"

    @patch("app.services.anthropic_provider.settings")
    def test_initialization_without_api_key(self, mock_settings):
        """Test Anthropic provider initialization without API key."""
        mock_settings.anthropic_api_key = None

        provider = AnthropicProvider()

        assert provider.api_key is None

    @pytest.mark.asyncio
    @patch("app.services.anthropic_provider.settings")
    async def test_complete_no_api_key(self, mock_settings):
        """Test completion fails without API key."""
        mock_settings.anthropic_api_key = None

        provider = AnthropicProvider()

        with pytest.raises(Exception, match="Anthropic API key not configured"):
            await provider.complete(prompt="Test", user_id="user123")

    @pytest.mark.asyncio
    @patch("app.services.anthropic_provider.httpx.AsyncClient")
    @patch("app.services.anthropic_provider.settings")
    async def test_complete_success(self, mock_settings, mock_httpx):
        """Test successful completion."""
        mock_settings.anthropic_api_key = "test-api-key"

        # Mock Anthropic API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Hello, how can I assist you today?"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 40},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = AnthropicProvider(model="claude-3-haiku-20240307")
        result = await provider.complete(prompt="Hello", user_id="user123")

        assert isinstance(result, LLMResponse)
        assert result.text == "Hello, how can I assist you today?"
        assert result.model == "claude-3-haiku-20240307"
        assert result.tokens_used == 50
        assert result.provider == "anthropic"
        assert result.response_metadata["stop_reason"] == "end_turn"

    @pytest.mark.asyncio
    @patch("app.services.anthropic_provider.httpx.AsyncClient")
    @patch("app.services.anthropic_provider.settings")
    async def test_complete_with_system_prompt(self, mock_settings, mock_httpx):
        """Test completion with system prompt."""
        mock_settings.anthropic_api_key = "test-api-key"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Response"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 15, "output_tokens": 15},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = AnthropicProvider()
        await provider.complete(prompt="Test", user_id="user123", system_prompt="You are a helpful assistant")

        # Verify system prompt was included
        call_args = mock_client.post.call_args
        request_data = call_args.kwargs["json"]
        assert request_data["system"] == "You are a helpful assistant"

    @pytest.mark.asyncio
    @patch("app.services.anthropic_provider.httpx.AsyncClient")
    @patch("app.services.anthropic_provider.settings")
    async def test_complete_with_custom_parameters(self, mock_settings, mock_httpx):
        """Test completion with custom parameters."""
        mock_settings.anthropic_api_key = "test-api-key"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Response"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 15, "output_tokens": 15},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = AnthropicProvider()
        await provider.complete(
            prompt="Test",
            user_id="user123",
            model="claude-3-opus-20240229",
            max_tokens=500,
            temperature=0.8,
            timeout=60.0,
        )

        call_args = mock_client.post.call_args
        request_data = call_args.kwargs["json"]
        assert request_data["model"] == "claude-3-opus-20240229"
        assert request_data["max_tokens"] == 500
        assert request_data["temperature"] == 0.8

    @pytest.mark.asyncio
    @patch("app.services.anthropic_provider.httpx.AsyncClient")
    @patch("app.services.anthropic_provider.settings")
    async def test_complete_http_error(self, mock_settings, mock_httpx):
        """Test completion with HTTP error."""
        mock_settings.anthropic_api_key = "test-api-key"

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limit", request=Mock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = AnthropicProvider()

        with pytest.raises(httpx.HTTPStatusError):
            await provider.complete(prompt="Test", user_id="user123")

    @pytest.mark.asyncio
    @patch("app.services.anthropic_provider.httpx.AsyncClient")
    @patch("app.services.anthropic_provider.settings")
    async def test_complete_timeout_error(self, mock_settings, mock_httpx):
        """Test completion with timeout error."""
        mock_settings.anthropic_api_key = "test-api-key"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = AnthropicProvider()

        with pytest.raises(TimeoutError, match="Anthropic API request timed out"):
            await provider.complete(prompt="Test", user_id="user123")

    @pytest.mark.asyncio
    @patch("app.services.anthropic_provider.httpx.AsyncClient")
    @patch("app.services.anthropic_provider.settings")
    async def test_complete_generic_error(self, mock_settings, mock_httpx):
        """Test completion with generic error."""
        mock_settings.anthropic_api_key = "test-api-key"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Unexpected error"))
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = AnthropicProvider()

        with pytest.raises(Exception, match="Unexpected error"):
            await provider.complete(prompt="Test", user_id="user123")

    @patch("app.services.anthropic_provider.settings")
    def test_calculate_cost_claude_haiku(self, mock_settings):
        """Test cost calculation for Claude Haiku."""
        mock_settings.anthropic_api_key = "test-api-key"

        provider = AnthropicProvider()
        cost = provider._calculate_cost("claude-3-haiku-20240307", input_tokens=1000, output_tokens=500)

        # Claude Haiku: $0.00025 input, $0.00125 output per 1K tokens
        expected_cost = (1000 / 1000 * 0.00025) + (500 / 1000 * 0.00125)
        assert cost == pytest.approx(expected_cost)

    @patch("app.services.anthropic_provider.settings")
    def test_calculate_cost_claude_opus(self, mock_settings):
        """Test cost calculation for Claude Opus."""
        mock_settings.anthropic_api_key = "test-api-key"

        provider = AnthropicProvider()
        cost = provider._calculate_cost("claude-3-opus-20240229", input_tokens=1000, output_tokens=500)

        # Claude Opus: $0.015 input, $0.075 output per 1K tokens
        expected_cost = (1000 / 1000 * 0.015) + (500 / 1000 * 0.075)
        assert cost == pytest.approx(expected_cost)

    @patch("app.services.anthropic_provider.settings")
    def test_calculate_cost_unknown_model(self, mock_settings):
        """Test cost calculation defaults to Haiku pricing for unknown model."""
        mock_settings.anthropic_api_key = "test-api-key"

        provider = AnthropicProvider()
        cost = provider._calculate_cost("unknown-model", input_tokens=1000, output_tokens=500)

        # Should default to Haiku pricing
        expected_cost = (1000 / 1000 * 0.00025) + (500 / 1000 * 0.00125)
        assert cost == pytest.approx(expected_cost)

    @pytest.mark.asyncio
    @patch("app.services.anthropic_provider.settings")
    async def test_health_check_no_api_key(self, mock_settings):
        """Test health check without API key."""
        mock_settings.anthropic_api_key = None

        provider = AnthropicProvider()
        result = await provider.health_check()

        assert result["status"] == "error"
        assert "API key not configured" in result["message"]

    @pytest.mark.asyncio
    @patch("app.services.anthropic_provider.httpx.AsyncClient")
    @patch("app.services.anthropic_provider.settings")
    async def test_health_check_success(self, mock_settings, mock_httpx):
        """Test successful health check."""
        mock_settings.anthropic_api_key = "test-api-key"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Hi"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 2, "output_tokens": 3},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = AnthropicProvider(model="claude-3-haiku-20240307")
        result = await provider.health_check()

        assert result["status"] == "healthy"
        assert result["model"] == "claude-3-haiku-20240307"
        assert "response_time" in result

    @pytest.mark.asyncio
    @patch("app.services.anthropic_provider.httpx.AsyncClient")
    @patch("app.services.anthropic_provider.settings")
    async def test_health_check_failure(self, mock_settings, mock_httpx):
        """Test health check failure."""
        mock_settings.anthropic_api_key = "test-api-key"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("API error"))
        mock_httpx.return_value.__aenter__.return_value = mock_client

        provider = AnthropicProvider()
        result = await provider.health_check()

        assert result["status"] == "unhealthy"
        assert "API error" in result["error"]
