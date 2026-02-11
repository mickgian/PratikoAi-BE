"""Tests for Gemini provider (DEV-256)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm.base import LLMModelTier, LLMProviderType
from app.schemas.chat import Message


class TestGeminiProvider:
    """Test GeminiProvider implementation."""

    @pytest.fixture
    def mock_genai(self):
        """Mock google.generativeai module."""
        with patch.dict("sys.modules", {"google.generativeai": MagicMock()}):
            with patch("app.core.llm.providers.gemini_provider.GEMINI_AVAILABLE", True):
                with patch("app.core.llm.providers.gemini_provider.genai") as mock_genai:
                    with patch("app.core.llm.providers.gemini_provider.GenerationConfig") as mock_config:
                        mock_config.return_value = MagicMock()
                        yield mock_genai

    @pytest.fixture
    def provider(self, mock_genai):
        """Create a GeminiProvider instance."""
        from app.core.llm.providers.gemini_provider import GeminiProvider

        return GeminiProvider(api_key="test-api-key", model="gemini-2.5-flash")

    def test_provider_type(self, provider):
        """Test provider type is GEMINI."""
        assert provider.provider_type == LLMProviderType.GEMINI

    def test_supported_models(self, provider):
        """Test supported models are defined."""
        models = provider.supported_models

        assert "gemini-2.5-flash" in models
        assert "gemini-2.5-pro" in models
        assert "gemini-2.0-flash" in models

    def test_model_tiers(self, provider):
        """Test model tiers are correctly assigned."""
        models = provider.supported_models

        assert models["gemini-2.5-flash"].tier == LLMModelTier.BASIC
        assert models["gemini-2.5-pro"].tier == LLMModelTier.ADVANCED
        assert models["gemini-2.0-flash"].tier == LLMModelTier.STANDARD

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

    def test_estimate_cost_unknown_model(self, mock_genai):
        """Test cost estimation for unknown model uses fallback."""
        from app.core.llm.providers.gemini_provider import GeminiProvider

        provider = GeminiProvider(api_key="test", model="unknown-model")
        cost = provider.estimate_cost(input_tokens=1000, output_tokens=1000)

        # Should use gemini-2.5-flash as fallback
        assert cost > 0

    def test_convert_messages_to_gemini(self, provider):
        """Test message conversion to Gemini format."""
        messages = [
            Message(role="system", content="You are a helpful assistant"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
            Message(role="user", content="How are you?"),
        ]

        system_instruction, history = provider._convert_messages_to_gemini(messages)

        assert system_instruction == "You are a helpful assistant"
        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "model"
        assert history[2]["role"] == "user"

    def test_convert_messages_no_system(self, provider):
        """Test message conversion without system message."""
        messages = [
            Message(role="user", content="Hello"),
        ]

        system_instruction, history = provider._convert_messages_to_gemini(messages)

        assert system_instruction is None
        assert len(history) == 1

    def test_model_capabilities(self, provider):
        """Test model capabilities."""
        capabilities = provider.get_model_capabilities()

        assert capabilities["supports_json_mode"] is True
        assert capabilities["supports_vision"] is True
        assert "max_context_length" in capabilities

    @pytest.mark.asyncio
    async def test_chat_completion(self, provider, mock_genai):
        """Test chat completion."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "Hello! I'm doing well."
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 20

        mock_chat = MagicMock()
        mock_chat.send_message_async = AsyncMock(return_value=mock_response)

        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat

        mock_genai.GenerativeModel.return_value = mock_model

        messages = [Message(role="user", content="Hello")]

        with patch(
            "app.core.llm.providers.gemini_provider.get_current_trace_id",
            return_value=None,
        ):
            response = await provider.chat_completion(messages)

        assert response.content == "Hello! I'm doing well."
        assert response.provider == "gemini"

    @pytest.mark.asyncio
    async def test_chat_completion_error(self, provider, mock_genai):
        """Test chat completion error handling."""
        mock_chat = MagicMock()
        mock_chat.send_message_async = AsyncMock(side_effect=Exception("API error"))

        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat

        mock_genai.GenerativeModel.return_value = mock_model

        messages = [Message(role="user", content="Hello")]

        with pytest.raises(Exception, match="API error"):
            await provider.chat_completion(messages)

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, provider, mock_genai):
        """Test connection validation success."""
        mock_response = MagicMock()
        mock_response.text = "test"

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)

        mock_genai.GenerativeModel.return_value = mock_model

        result = await provider.validate_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, provider, mock_genai):
        """Test connection validation failure."""
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(side_effect=Exception("Connection failed"))

        mock_genai.GenerativeModel.return_value = mock_model

        result = await provider.validate_connection()

        assert result is False


class TestGeminiProviderImportError:
    """Test GeminiProvider import error handling."""

    def test_import_error_when_not_available(self):
        """Test ImportError when google-generativeai not installed."""
        with patch("app.core.llm.providers.gemini_provider.GEMINI_AVAILABLE", False):
            from app.core.llm.providers.gemini_provider import GeminiProvider

            with pytest.raises(ImportError, match="Google Generative AI"):
                GeminiProvider(api_key="test")
