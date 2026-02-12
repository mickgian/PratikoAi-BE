"""Tests for embedding utilities.

Covers:
  - Token-accurate truncation (truncate_to_token_limit)
  - Retry logic for transient API errors (rate limit, timeout, connection)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import tiktoken
from openai import APIConnectionError, APITimeoutError, RateLimitError

from app.core.embed import _MAX_EMBEDDING_TOKENS, truncate_to_token_limit


# -------------------------------------------------------------------------
# truncate_to_token_limit
# -------------------------------------------------------------------------
class TestTruncateToTokenLimit:
    """Tests for truncate_to_token_limit()."""

    _enc = tiktoken.get_encoding("cl100k_base")

    def test_short_text_unchanged(self) -> None:
        """Text within token limit is returned as-is."""
        short = "Questo è un breve testo."
        assert truncate_to_token_limit(short) == short

    def test_empty_string(self) -> None:
        """Empty string is returned as-is."""
        assert truncate_to_token_limit("") == ""

    def test_text_over_limit_truncated_to_max_tokens(self) -> None:
        """Text exceeding the limit is truncated to exactly max_tokens."""
        # Build a string that is definitely over 100 tokens
        long_text = "word " * 500  # ~500 tokens
        result = truncate_to_token_limit(long_text, max_tokens=100)
        token_count = len(self._enc.encode(result))
        assert token_count == 100

    def test_italian_legal_text_truncated(self) -> None:
        """Italian legal text (high token/char ratio) is properly truncated."""
        # Italian legal text with short words, numbers, and abbreviations
        # that tokenize at ~2 chars/token instead of ~4
        legal = (
            "Art. 1, c. 2, lett. a) del D.Lgs. 81/2008 e s.m.i. - "
            "Il datore di lavoro è tenuto a valutare i rischi per la "
            "sicurezza e la salute dei lavoratori, ivi compresi quelli "
            "riguardanti gruppi di lavoratori esposti a rischi particolari. "
        ) * 200  # repeat to exceed limit
        result = truncate_to_token_limit(legal)
        token_count = len(self._enc.encode(result))
        assert token_count <= _MAX_EMBEDDING_TOKENS

    def test_custom_max_tokens(self) -> None:
        """Custom max_tokens parameter is respected."""
        text = "token " * 100
        result = truncate_to_token_limit(text, max_tokens=10)
        token_count = len(self._enc.encode(result))
        assert token_count == 10


@pytest.mark.asyncio
class TestGenerateEmbeddingTruncation:
    """Integration: generate_embedding() truncates before calling API."""

    @patch("app.core.embed.client")
    async def test_long_text_truncated_before_api_call(self, mock_client: MagicMock) -> None:
        """Text longer than token limit is truncated before the API call."""
        from app.core.embed import generate_embedding

        good_response = MagicMock()
        good_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_create = AsyncMock(return_value=good_response)
        mock_client.embeddings.create = mock_create

        # 50k chars of Italian legal abbreviations → would be ~20k+ tokens
        long_text = "Art. 1, c. 2; " * 5000
        result = await generate_embedding(long_text)

        assert result is not None
        # Verify the text sent to API is within token limit
        call_args = mock_create.call_args
        sent_text = call_args.kwargs.get("input") or call_args[1].get("input_data")
        enc = tiktoken.get_encoding("cl100k_base")
        assert len(enc.encode(sent_text)) <= _MAX_EMBEDDING_TOKENS


@pytest.mark.asyncio
class TestGenerateEmbeddingRetry:
    """Tests for generate_embedding() retry behaviour."""

    @patch("app.core.embed.client")
    async def test_retries_on_rate_limit_then_succeeds(self, mock_client: MagicMock) -> None:
        """Retries on RateLimitError and eventually returns embedding."""
        from app.core.embed import generate_embedding

        good_response = MagicMock()
        good_response.data = [MagicMock(embedding=[0.1] * 1536)]

        mock_create = AsyncMock(
            side_effect=[
                RateLimitError(
                    message="rate limit",
                    response=MagicMock(status_code=429, headers={}),
                    body=None,
                ),
                good_response,
            ]
        )
        mock_client.embeddings.create = mock_create

        result = await generate_embedding("test text")

        assert result is not None
        assert len(result) == 1536
        assert mock_create.call_count == 2

    @patch("app.core.embed.client")
    async def test_retries_on_timeout_then_succeeds(self, mock_client: MagicMock) -> None:
        """Retries on APITimeoutError and eventually returns embedding."""
        from app.core.embed import generate_embedding

        good_response = MagicMock()
        good_response.data = [MagicMock(embedding=[0.2] * 1536)]

        mock_create = AsyncMock(
            side_effect=[
                APITimeoutError(request=MagicMock()),
                good_response,
            ]
        )
        mock_client.embeddings.create = mock_create

        result = await generate_embedding("test text")

        assert result is not None
        assert mock_create.call_count == 2

    @patch("app.core.embed.client")
    async def test_gives_up_after_max_retries(self, mock_client: MagicMock) -> None:
        """Returns None after exhausting retry attempts."""
        from app.core.embed import generate_embedding

        mock_create = AsyncMock(
            side_effect=RateLimitError(
                message="rate limit",
                response=MagicMock(status_code=429, headers={}),
                body=None,
            )
        )
        mock_client.embeddings.create = mock_create

        result = await generate_embedding("test text")

        assert result is None
        assert mock_create.call_count == 3  # initial + 2 retries

    @patch("app.core.embed.client")
    async def test_non_retryable_error_returns_none(self, mock_client: MagicMock) -> None:
        """Non-retryable errors return None immediately."""
        from app.core.embed import generate_embedding

        mock_create = AsyncMock(side_effect=ValueError("bad input"))
        mock_client.embeddings.create = mock_create

        result = await generate_embedding("test text")

        assert result is None
        assert mock_create.call_count == 1


@pytest.mark.asyncio
class TestGenerateEmbeddingsBatchRetry:
    """Tests for generate_embeddings_batch() retry behaviour."""

    @patch("app.core.embed.client")
    async def test_batch_retries_on_transient_error(self, mock_client: MagicMock) -> None:
        """Batch retries on rate limit and returns embeddings."""
        from app.core.embed import generate_embeddings_batch

        good_response = MagicMock()
        good_response.data = [MagicMock(embedding=[0.1] * 1536)]

        mock_create = AsyncMock(
            side_effect=[
                RateLimitError(
                    message="rate limit",
                    response=MagicMock(status_code=429, headers={}),
                    body=None,
                ),
                good_response,
            ]
        )
        mock_client.embeddings.create = mock_create

        result = await generate_embeddings_batch(["text1"])

        assert len(result) == 1
        assert result[0] is not None
        assert mock_create.call_count == 2

    @patch("app.core.embed.client")
    async def test_batch_returns_none_after_max_retries(self, mock_client: MagicMock) -> None:
        """Batch returns None entries after exhausting retries."""
        from app.core.embed import generate_embeddings_batch

        mock_create = AsyncMock(side_effect=APIConnectionError(request=MagicMock()))
        mock_client.embeddings.create = mock_create

        result = await generate_embeddings_batch(["text1"])

        assert len(result) == 1
        assert result[0] is None
