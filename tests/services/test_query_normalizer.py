"""Tests for query normalizer service."""

import pytest
import json
from unittest.mock import AsyncMock, Mock, patch

from app.services.query_normalizer import QueryNormalizer


class TestQueryNormalizer:
    """Test QueryNormalizer class."""

    @patch('app.services.query_normalizer.AsyncOpenAI')
    @patch('app.services.query_normalizer.get_settings')
    def test_initialization(self, mock_settings, mock_openai):
        """Test QueryNormalizer initialization."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"

        normalizer = QueryNormalizer()

        assert normalizer.config is not None
        assert normalizer.client is not None

    @pytest.mark.asyncio
    @patch('app.services.query_normalizer.AsyncOpenAI')
    @patch('app.services.query_normalizer.get_settings')
    async def test_normalize_document_found(self, mock_settings, mock_openai):
        """Test normalizing query with document reference."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"type": "risoluzione", "number": "64"}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("risoluzione 64")

        assert result is not None
        assert result["type"] == "risoluzione"
        assert result["number"] == "64"

    @pytest.mark.asyncio
    @patch('app.services.query_normalizer.AsyncOpenAI')
    @patch('app.services.query_normalizer.get_settings')
    async def test_normalize_no_document(self, mock_settings, mock_openai):
        """Test normalizing query without document reference."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        # Mock OpenAI response with no document
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"type": null}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("come calcolare le tasse")

        assert result is None

    @pytest.mark.asyncio
    @patch('app.services.query_normalizer.AsyncOpenAI')
    @patch('app.services.query_normalizer.get_settings')
    async def test_normalize_invalid_json(self, mock_settings, mock_openai):
        """Test handling invalid JSON from LLM."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        # Mock OpenAI response with invalid JSON
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = 'Not valid JSON'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("test query")

        # Should gracefully return None on JSON error
        assert result is None

    @pytest.mark.asyncio
    @patch('app.services.query_normalizer.AsyncOpenAI')
    @patch('app.services.query_normalizer.get_settings')
    async def test_normalize_timeout_error(self, mock_settings, mock_openai):
        """Test handling timeout error."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        # Mock timeout error
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=TimeoutError("Request timeout"))
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("test query")

        # Should gracefully return None on timeout
        assert result is None

    @pytest.mark.asyncio
    @patch('app.services.query_normalizer.AsyncOpenAI')
    @patch('app.services.query_normalizer.get_settings')
    async def test_normalize_generic_exception(self, mock_settings, mock_openai):
        """Test handling generic exception."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        # Mock generic exception
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("test query")

        # Should gracefully return None on error
        assert result is None

    @pytest.mark.asyncio
    @patch('app.services.query_normalizer.AsyncOpenAI')
    @patch('app.services.query_normalizer.get_settings')
    async def test_normalize_written_numbers(self, mock_settings, mock_openai):
        """Test normalizing written numbers."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        # Mock OpenAI converting written number
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"type": "risoluzione", "number": "64"}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("risoluzione sessantaquattro")

        assert result is not None
        assert result["number"] == "64"

    @pytest.mark.asyncio
    @patch('app.services.query_normalizer.AsyncOpenAI')
    @patch('app.services.query_normalizer.get_settings')
    async def test_normalize_abbreviations(self, mock_settings, mock_openai):
        """Test normalizing abbreviations."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        # Mock OpenAI expanding abbreviation
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"type": "risoluzione", "number": "64"}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("ris 64")

        assert result is not None
        assert result["type"] == "risoluzione"

    def test_get_system_prompt(self):
        """Test system prompt generation."""
        with patch('app.services.query_normalizer.get_settings') as mock_settings:
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            normalizer = QueryNormalizer()
            prompt = normalizer._get_system_prompt()

            assert "Extract document reference" in prompt
            assert "Italian" in prompt
            assert "JSON" in prompt
            assert "risoluzione" in prompt

    @pytest.mark.asyncio
    @patch('app.services.query_normalizer.AsyncOpenAI')
    @patch('app.services.query_normalizer.get_settings')
    async def test_normalize_calls_llm_with_correct_params(self, mock_settings, mock_openai):
        """Test that normalize calls LLM with correct parameters."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"type": null}'

        mock_client = AsyncMock()
        mock_create = AsyncMock(return_value=mock_response)
        mock_client.chat.completions.create = mock_create
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        await normalizer.normalize("test query")

        # Verify LLM was called with correct parameters
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs

        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["temperature"] == 0
        assert call_kwargs["max_tokens"] == 100
        assert call_kwargs["timeout"] == 2.0
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"
        assert call_kwargs["messages"][1]["content"] == "test query"
