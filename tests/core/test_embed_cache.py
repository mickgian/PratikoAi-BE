"""Tests for S3: Embedding cache by content hash.

Validates that identical text inputs return cached embeddings
instead of making duplicate OpenAI API calls.

These tests require the real app.core.embed module (tiktoken + OpenAI),
which needs network access for tiktoken encoding data and an OpenAI API key.
They are skipped when the environment cannot support them.
"""

import importlib
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Remove any sys.modules mock from conftest (some conftest files replace
# app.core.embed with a MagicMock globally)
_original_mock = sys.modules.pop("app.core.embed", None)
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "sk-test-dummy-key-for-unit-tests"

try:
    import app.core.embed

    importlib.reload(app.core.embed)
    from app.core.embed import _embedding_cache_key

    _EMBED_AVAILABLE = True
except Exception:
    _EMBED_AVAILABLE = False


pytestmark = pytest.mark.skipif(not _EMBED_AVAILABLE, reason="embed module not available")


class TestEmbeddingCacheKey:
    """Tests for cache key generation."""

    def test_same_text_same_key(self):
        """Identical text produces identical cache key."""
        key1 = _embedding_cache_key("test query")
        key2 = _embedding_cache_key("test query")
        assert key1 == key2

    def test_different_text_different_key(self):
        """Different text produces different cache key."""
        key1 = _embedding_cache_key("query one")
        key2 = _embedding_cache_key("query two")
        assert key1 != key2

    def test_key_has_prefix(self):
        """Cache key has embed: prefix for namespacing."""
        key = _embedding_cache_key("test")
        assert key.startswith("embed:")


class TestEmbeddingCache:
    """Tests for cached embedding generation."""

    @pytest.mark.asyncio
    async def test_cache_hit_skips_api_call(self):
        """Cached embedding is returned without calling OpenAI API."""
        import json

        cached_embedding = [0.1] * 1536

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_embedding).encode())

        with (
            patch("app.core.embed._get_cached_embedding", new_callable=AsyncMock, return_value=cached_embedding),
            patch("app.core.embed._create_embedding") as mock_api,
        ):
            from app.core.embed import generate_embedding

            result = await generate_embedding("test query")

        # API should NOT be called on cache hit
        mock_api.assert_not_called()
        assert result == cached_embedding

    @pytest.mark.asyncio
    async def test_cache_miss_calls_api_and_stores(self):
        """On cache miss, calls API and stores result in cache."""
        embedding = [0.1] * 1536
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=embedding)]
        mock_response.usage.total_tokens = 10

        with (
            patch("app.core.embed._get_cached_embedding", new_callable=AsyncMock, return_value=None),
            patch("app.core.embed._cache_embedding", new_callable=AsyncMock) as mock_cache_store,
            patch("app.core.embed._create_embedding", new_callable=AsyncMock, return_value=mock_response),
            patch("app.core.embed._track_embedding_cost", new_callable=AsyncMock),
        ):
            from app.core.embed import generate_embedding

            result = await generate_embedding("test query")

        assert result == embedding
        mock_cache_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_disabled_still_works(self):
        """When cache is disabled, API is called directly (cache returns None)."""
        embedding = [0.1] * 1536
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=embedding)]
        mock_response.usage.total_tokens = 10

        with (
            patch("app.core.embed._get_cached_embedding", new_callable=AsyncMock, return_value=None),
            patch("app.core.embed._cache_embedding", new_callable=AsyncMock),
            patch("app.core.embed._create_embedding", new_callable=AsyncMock, return_value=mock_response),
            patch("app.core.embed._track_embedding_cost", new_callable=AsyncMock),
        ):
            from app.core.embed import generate_embedding

            result = await generate_embedding("test query")

        assert result == embedding

    @pytest.mark.asyncio
    async def test_empty_text_returns_none(self):
        """Empty text returns None without cache or API call."""
        from app.core.embed import generate_embedding

        result = await generate_embedding("")
        assert result is None

        result = await generate_embedding("   ")
        assert result is None
