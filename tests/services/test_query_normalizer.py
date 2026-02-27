"""Tests for query normalizer service."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.query_normalizer import QueryNormalizer


class TestQueryNormalizer:
    """Test QueryNormalizer class."""

    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
    def test_initialization(self, mock_settings, mock_openai):
        """Test QueryNormalizer initialization."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"

        normalizer = QueryNormalizer()

        assert normalizer.config is not None
        assert normalizer.client is not None

    @pytest.mark.asyncio
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
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
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
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
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
    async def test_normalize_invalid_json(self, mock_settings, mock_openai):
        """Test handling invalid JSON from LLM."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        # Mock OpenAI response with invalid JSON
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Not valid JSON"

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("test query")

        # Should gracefully return None on JSON error
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
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
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
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
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
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
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
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
        with patch("app.services.query_normalizer.get_settings") as mock_settings:
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            normalizer = QueryNormalizer()
            prompt = normalizer._get_system_prompt()

            assert "Extract document reference" in prompt
            assert "Italian" in prompt
            assert "JSON" in prompt
            assert "risoluzione" in prompt

    @pytest.mark.asyncio
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
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

    @pytest.mark.asyncio
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
    async def test_normalize_inps_messaggio(self, mock_settings, mock_openai):
        """Test INPS messaggio extraction with year field."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"type": "messaggio", "number": "3585", "year": null}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("messaggio 3585 INPS")

        assert result is not None
        assert result["type"] == "messaggio"
        assert result["number"] == "3585"
        assert result.get("year") is None

    @pytest.mark.asyncio
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
    async def test_normalize_compound_reference(self, mock_settings, mock_openai):
        """Test compound reference like DPR 1124/1965 with year extraction."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"type": "DPR", "number": "1124", "year": "1965"}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("DPR 1124/1965")

        assert result is not None
        assert result["type"] == "DPR"
        assert result["number"] == "1124"
        assert result["year"] == "1965"

    @pytest.mark.asyncio
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
    async def test_normalize_msg_abbreviation(self, mock_settings, mock_openai):
        """Test 'msg' abbreviation expansion to 'messaggio'."""
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"type": "messaggio", "number": "3585", "year": null}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("msg 3585")

        assert result is not None
        assert result["type"] == "messaggio"
        assert result["number"] == "3585"

    def test_system_prompt_includes_new_document_types(self):
        """Test that system prompt includes INPS and judicial document types."""
        with patch("app.services.query_normalizer.get_settings") as mock_settings:
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            normalizer = QueryNormalizer()
            prompt = normalizer._get_system_prompt()

            # Check for INPS document types
            assert "messaggio" in prompt
            assert "INPS" in prompt

            # Check for compound reference format
            assert "1124/1965" in prompt or "DPR" in prompt

            # Check for year field in JSON schema
            assert '"year"' in prompt

            # Check for new abbreviations
            assert "msg" in prompt


# ============================================================================
# TDD: Tests for keyword extraction (semantic search support)
# ============================================================================
# These tests validate the new `keywords` field for topic-based queries.
# The keywords field enables semantic search when no document number is found.
# ============================================================================


class TestQueryNormalizerKeywords:
    """Test keyword extraction for topic-based queries."""

    @pytest.mark.asyncio
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
    async def test_topic_query_returns_keywords(self, mock_settings, mock_openai):
        """Test that topic-based queries return keywords field.

        Query: "DL sicurezza lavoro" should return:
        {"type": "DL", "number": null, "year": null, "keywords": ["sicurezza", "lavoro"]}
        """
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        # Mock OpenAI response with keywords
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {"type": "DL", "number": None, "year": None, "keywords": ["sicurezza", "lavoro"]}
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("DL sicurezza lavoro")

        assert result is not None
        assert result["type"] == "DL"
        assert result.get("number") is None
        assert "keywords" in result
        assert "sicurezza" in result["keywords"]
        assert "lavoro" in result["keywords"]

    @pytest.mark.asyncio
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
    async def test_general_topic_query_returns_keywords(self, mock_settings, mock_openai):
        """Test that general topic queries return keywords without type.

        Query: "bonus psicologo 2025" should return:
        {"type": null, "number": null, "year": "2025", "keywords": ["bonus", "psicologo"]}
        """
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {"type": None, "number": None, "year": "2025", "keywords": ["bonus", "psicologo"]}
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("bonus psicologo 2025")

        # Should NOT return None when keywords are present
        assert result is not None
        assert "keywords" in result
        assert "bonus" in result["keywords"]
        assert "psicologo" in result["keywords"]

    @pytest.mark.asyncio
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
    async def test_document_with_topic_returns_both_number_and_keywords(self, mock_settings, mock_openai):
        """Test that document queries with topic return both number and keywords.

        Query: "messaggio 3585 INPS sicurezza lavoro" should return:
        {"type": "messaggio", "number": "3585", "year": null, "keywords": ["sicurezza", "lavoro", "INPS"]}
        """
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {"type": "messaggio", "number": "3585", "year": None, "keywords": ["sicurezza", "lavoro", "INPS"]}
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("messaggio 3585 INPS sicurezza lavoro")

        assert result is not None
        assert result["type"] == "messaggio"
        assert result["number"] == "3585"
        assert "keywords" in result
        assert len(result["keywords"]) >= 2

    @pytest.mark.asyncio
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
    async def test_semantic_variations_produce_similar_keywords(self, mock_settings, mock_openai):
        """Test that semantic variations produce overlapping keywords.

        Different phrasings of the same query should produce similar keywords:
        - "DL sicurezza lavoro"
        - "decreto legge sulla sicurezza sul lavoro"
        - "decreto sicurezza luoghi di lavoro"

        All should include keywords like ["sicurezza", "lavoro"].
        """
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        # The key insight: LLM extracts SEMANTIC keywords, not exact words
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "type": "decreto",
                "number": None,
                "year": None,
                "keywords": ["sicurezza", "lavoro"],  # Core semantic concepts
            }
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()

        # All three variations should produce keywords containing "sicurezza" and "lavoro"
        queries = [
            "DL sicurezza lavoro",
            "decreto legge sulla sicurezza sul lavoro",
            "decreto sicurezza luoghi di lavoro",
        ]

        for query in queries:
            result = await normalizer.normalize(query)
            assert result is not None, f"Query '{query}' should not return None"
            assert "keywords" in result, f"Query '{query}' should have keywords"
            keywords = result["keywords"]
            assert any(
                "sicur" in k.lower() for k in keywords
            ), f"Query '{query}' should have sicurezza-related keyword"
            assert any("lavor" in k.lower() for k in keywords), f"Query '{query}' should have lavoro-related keyword"

    @pytest.mark.asyncio
    @patch("app.services.query_normalizer.AsyncOpenAI")
    @patch("app.services.query_normalizer.get_settings")
    async def test_empty_keywords_for_number_only_query(self, mock_settings, mock_openai):
        """Test that number-only queries can have empty keywords.

        Query: "risoluzione 64" might not need keywords since number is sufficient.
        """
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.QUERY_NORMALIZATION_MODEL = "gpt-4o-mini"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "type": "risoluzione",
                "number": "64",
                "year": None,
                "keywords": [],  # Empty is OK when number is present
            }
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        normalizer = QueryNormalizer()
        result = await normalizer.normalize("risoluzione 64")

        assert result is not None
        assert result["number"] == "64"
        # Keywords can be empty when number is present
        assert "keywords" in result
        assert result["keywords"] == []

    def test_system_prompt_includes_keywords_field(self):
        """Test that system prompt instructs LLM to extract keywords."""
        with patch("app.services.query_normalizer.get_settings") as mock_settings:
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            normalizer = QueryNormalizer()
            prompt = normalizer._get_system_prompt()

            # Check that keywords field is documented
            assert "keywords" in prompt.lower(), "System prompt should mention keywords field"
