"""Tests for embedding utilities.

Covers:
  - Token-accurate truncation (truncate_to_token_limit)
  - Retry logic for transient API errors (rate limit, timeout, connection)

These tests require the real app.core.embed module (tiktoken + OpenAI),
which needs network access for tiktoken encoding data and an OpenAI API key.
They are skipped when the environment cannot support them.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Attempt to load the real embed module.
# - Remove any sys.modules mock from conftest
# - Set a dummy OpenAI API key so the client can init
# - Try to import; if tiktoken can't download data, skip the whole module
_original_mock = sys.modules.pop("app.core.embed", None)
_had_key = "OPENAI_API_KEY" in os.environ
if not _had_key:
    os.environ["OPENAI_API_KEY"] = "sk-test-dummy-key-for-unit-tests"

try:
    import importlib

    import app.core.embed

    importlib.reload(app.core.embed)
    import tiktoken

    from app.core.embed import _MAX_EMBEDDING_TOKENS, truncate_to_token_limit

    _enc = tiktoken.get_encoding("cl100k_base")
    _EMBED_AVAILABLE = True
except Exception:
    _EMBED_AVAILABLE = False
    # Restore the mock so other tests in the suite still work
    if _original_mock is not None:
        sys.modules["app.core.embed"] = _original_mock
finally:
    if not _had_key:
        os.environ.pop("OPENAI_API_KEY", None)

pytestmark = pytest.mark.skipif(
    not _EMBED_AVAILABLE,
    reason="Cannot load real app.core.embed (requires network for tiktoken data)",
)


# -------------------------------------------------------------------------
# truncate_to_token_limit
# -------------------------------------------------------------------------
class TestTruncateToTokenLimit:
    """Tests for truncate_to_token_limit()."""

    def test_short_text_unchanged(self) -> None:
        """Text within token limit is returned as-is."""
        short = "Questo è un breve testo."
        assert truncate_to_token_limit(short) == short

    def test_empty_string(self) -> None:
        """Empty string is returned as-is."""
        assert truncate_to_token_limit("") == ""

    def test_text_over_limit_truncated_to_max_tokens(self) -> None:
        """Text exceeding the limit is truncated to exactly max_tokens."""
        long_text = "word " * 500  # ~500 tokens
        result = truncate_to_token_limit(long_text, max_tokens=100)
        token_count = len(_enc.encode(result))
        assert token_count == 100

    def test_italian_legal_text_truncated(self) -> None:
        """Italian legal text (high token/char ratio) is properly truncated."""
        legal = (
            "Art. 1, c. 2, lett. a) del D.Lgs. 81/2008 e s.m.i. - "
            "Il datore di lavoro è tenuto a valutare i rischi per la "
            "sicurezza e la salute dei lavoratori, ivi compresi quelli "
            "riguardanti gruppi di lavoratori esposti a rischi particolari. "
        ) * 200
        result = truncate_to_token_limit(legal)
        token_count = len(_enc.encode(result))
        assert token_count <= _MAX_EMBEDDING_TOKENS

    def test_custom_max_tokens(self) -> None:
        """Custom max_tokens parameter is respected."""
        text = "token " * 100
        result = truncate_to_token_limit(text, max_tokens=10)
        token_count = len(_enc.encode(result))
        assert token_count == 10


@pytest.mark.asyncio
class TestGenerateEmbeddingTruncation:
    """Integration: generate_embedding() truncates before calling API."""

    async def test_long_text_truncated_before_api_call(self) -> None:
        """Text longer than token limit is truncated before the API call."""
        from app.core.embed import generate_embedding

        good_response = MagicMock()
        good_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_create = AsyncMock(return_value=good_response)

        with patch("app.core.embed._create_embedding", mock_create):
            long_text = "Art. 1, c. 2; " * 5000
            result = await generate_embedding(long_text)

        assert result is not None
        call_args = mock_create.call_args
        sent_text = call_args.kwargs.get("input_data")
        assert len(_enc.encode(sent_text)) <= _MAX_EMBEDDING_TOKENS


@pytest.mark.asyncio
class TestGenerateEmbeddingRetry:
    """Tests for generate_embedding() retry behaviour."""

    async def test_retries_on_rate_limit_then_succeeds(self) -> None:
        """Retries on RateLimitError and eventually returns embedding."""
        from openai import RateLimitError

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

        with patch("app.core.embed._create_embedding", mock_create):
            result = await generate_embedding("test text")

        assert result is not None
        assert len(result) == 1536
        assert mock_create.call_count == 2

    async def test_retries_on_timeout_then_succeeds(self) -> None:
        """Retries on APITimeoutError and eventually returns embedding."""
        from openai import APITimeoutError

        from app.core.embed import generate_embedding

        good_response = MagicMock()
        good_response.data = [MagicMock(embedding=[0.2] * 1536)]

        mock_create = AsyncMock(
            side_effect=[
                APITimeoutError(request=MagicMock()),
                good_response,
            ]
        )

        with patch("app.core.embed._create_embedding", mock_create):
            result = await generate_embedding("test text")

        assert result is not None
        assert mock_create.call_count == 2

    async def test_gives_up_after_max_retries(self) -> None:
        """Returns None after exhausting retry attempts."""
        from openai import RateLimitError

        from app.core.embed import generate_embedding

        mock_create = AsyncMock(
            side_effect=RateLimitError(
                message="rate limit",
                response=MagicMock(status_code=429, headers={}),
                body=None,
            )
        )

        with patch("app.core.embed._create_embedding", mock_create):
            result = await generate_embedding("test text")

        assert result is None
        assert mock_create.call_count == 3  # initial + 2 retries

    async def test_non_retryable_error_returns_none(self) -> None:
        """Non-retryable errors return None immediately."""
        from app.core.embed import generate_embedding

        mock_create = AsyncMock(side_effect=ValueError("bad input"))

        with patch("app.core.embed._create_embedding", mock_create):
            result = await generate_embedding("test text")

        assert result is None
        assert mock_create.call_count == 1


@pytest.mark.asyncio
class TestGenerateEmbeddingsBatchRetry:
    """Tests for generate_embeddings_batch() retry behaviour."""

    async def test_batch_retries_on_transient_error(self) -> None:
        """Batch retries on rate limit and returns embeddings."""
        from openai import RateLimitError

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

        with patch("app.core.embed._create_embedding", mock_create):
            result = await generate_embeddings_batch(["text1"])

        assert len(result) == 1
        assert result[0] is not None
        assert mock_create.call_count == 2

    async def test_batch_returns_none_after_max_retries(self) -> None:
        """Batch returns None entries after exhausting retries."""
        from openai import APIConnectionError

        from app.core.embed import generate_embeddings_batch

        mock_create = AsyncMock(side_effect=APIConnectionError(request=MagicMock()))

        with patch("app.core.embed._create_embedding", mock_create):
            result = await generate_embeddings_batch(["text1"])

        assert len(result) == 1
        assert result[0] is None
