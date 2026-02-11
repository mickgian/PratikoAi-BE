"""Tests for Mistral provider (DEV-256)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm.base import LLMModelTier, LLMProviderType
from app.schemas.chat import Message


class TestMistralProvider:
    """Test MistralProvider implementation."""

    @pytest.fixture
    def mock_mistral(self):
        """Mock mistralai module."""
        with patch.dict("sys.modules", {"mistralai": MagicMock()}):
            with patch("app.core.llm.providers.mistral_provider.MISTRAL_AVAILABLE", True):
                with patch("app.core.llm.providers.mistral_provider.Mistral") as mock_class:
                    mock_client = MagicMock()
                    mock_class.return_value = mock_client
                    yield mock_client

    @pytest.fixture
    def provider(self, mock_mistral):
        """Create a MistralProvider instance."""
        from app.core.llm.providers.mistral_provider import MistralProvider

        return MistralProvider(api_key="test-api-key", model="mistral-small-latest")

    def test_provider_type(self, provider):
        """Test provider type is MISTRAL."""
        assert provider.provider_type == LLMProviderType.MISTRAL

    def test_supported_models(self, provider):
        """Test supported models are defined."""
        models = provider.supported_models

        assert "mistral-small-latest" in models
        assert "mistral-large-latest" in models
        assert "codestral-latest" in models

    def test_model_tiers(self, provider):
        """Test model tiers are correctly assigned."""
        models = provider.supported_models

        assert models["mistral-small-latest"].tier == LLMModelTier.BASIC
        assert models["mistral-medium-latest"].tier == LLMModelTier.STANDARD
        assert models["mistral-large-latest"].tier == LLMModelTier.ADVANCED

    def test_estimate_tokens(self, provider):
        """Test token estimation."""
        messages = [
            Message(role="user", content="Hello, how are you?"),
        ]

        tokens = provider.estimate_tokens(messages)

        assert tokens > 0
        assert isinstance(tokens, int)

    def test_estimate_cost(self, provider):
        """Test cost estimation."""
        cost = provider.estimate_cost(input_tokens=100, output_tokens=200)

        assert cost > 0
        assert isinstance(cost, float)

    def test_estimate_cost_unknown_model(self, mock_mistral):
        """Test cost estimation for unknown model uses fallback."""
        from app.core.llm.providers.mistral_provider import MistralProvider

        provider = MistralProvider(api_key="test", model="unknown-model")
        cost = provider.estimate_cost(input_tokens=1000, output_tokens=1000)

        # Should use mistral-small-latest as fallback
        assert cost > 0

    def test_convert_messages_to_mistral(self, provider):
        """Test message conversion to Mistral format."""
        messages = [
            Message(role="system", content="You are a helpful assistant"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]

        mistral_messages = provider._convert_messages_to_mistral(messages)

        assert len(mistral_messages) == 3
        assert mistral_messages[0]["role"] == "system"
        assert mistral_messages[1]["role"] == "user"
        assert mistral_messages[2]["role"] == "assistant"

    def test_model_capabilities(self, provider):
        """Test model capabilities."""
        capabilities = provider.get_model_capabilities()

        assert capabilities["supports_json_mode"] is True
        assert "max_context_length" in capabilities

    def test_model_capabilities_large(self, mock_mistral):
        """Test capabilities for large model."""
        from app.core.llm.providers.mistral_provider import MistralProvider

        provider = MistralProvider(api_key="test", model="mistral-large-latest")
        capabilities = provider.get_model_capabilities()

        assert capabilities["supports_function_calling"] is True
        assert capabilities["max_context_length"] == 128000

    @pytest.mark.asyncio
    async def test_chat_completion(self, provider, mock_mistral):
        """Test chat completion."""
        # Setup mock response
        mock_choice = MagicMock()
        mock_choice.message.content = "Hello! I'm doing well."
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        mock_mistral.chat.complete_async = AsyncMock(return_value=mock_response)

        messages = [Message(role="user", content="Hello")]

        with patch(
            "app.core.llm.providers.mistral_provider.get_current_trace_id",
            return_value=None,
        ):
            response = await provider.chat_completion(messages)

        assert response.content == "Hello! I'm doing well."
        assert response.provider == "mistral"

    @pytest.mark.asyncio
    async def test_chat_completion_error(self, provider, mock_mistral):
        """Test chat completion error handling."""
        mock_mistral.chat.complete_async = AsyncMock(side_effect=Exception("API error"))

        messages = [Message(role="user", content="Hello")]

        with pytest.raises(Exception, match="API error"):
            await provider.chat_completion(messages)

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, provider, mock_mistral):
        """Test connection validation success."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]

        mock_mistral.chat.complete_async = AsyncMock(return_value=mock_response)

        result = await provider.validate_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, provider, mock_mistral):
        """Test connection validation failure."""
        mock_mistral.chat.complete_async = AsyncMock(side_effect=Exception("Connection failed"))

        result = await provider.validate_connection()

        assert result is False


class TestMistralProviderImportError:
    """Test MistralProvider import error handling."""

    def test_import_error_when_not_available(self):
        """Test ImportError when mistralai not installed."""
        with patch("app.core.llm.providers.mistral_provider.MISTRAL_AVAILABLE", False):
            from app.core.llm.providers.mistral_provider import MistralProvider

            with pytest.raises(ImportError, match="Mistral AI"):
                MistralProvider(api_key="test")
