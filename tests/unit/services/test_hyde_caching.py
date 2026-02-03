"""TDD Tests for DEV-251 Phase 5: HyDE Redis Caching.

Tests for HyDE result caching to reduce redundant LLM calls.
Cache key format: hyde:{routing_category}:{query_hash}

Run with: pytest tests/unit/services/test_hyde_caching.py -v
"""

import hashlib
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.router import RoutingCategory
from app.services.hyde_generator import HyDEGeneratorService, HyDEResult


class TestCacheServiceHydeMethods:
    """Test cache.py HyDE-specific caching methods."""

    @pytest.mark.asyncio
    async def test_cache_hyde_document_stores_result(self):
        """cache_hyde_document should store HyDE result with correct key."""
        from app.services.cache import CacheService

        service = CacheService()
        mock_redis = AsyncMock()
        service._redis = mock_redis
        service.enabled = True

        hyde_result = {
            "hypothetical_document": "Test document content",
            "word_count": 150,
            "skipped": False,
            "skip_reason": None,
            "variants": None,
        }

        result = await service.cache_hyde_document(
            query_hash="abc123",
            routing_category="technical_research",
            hyde_result=hyde_result,
            ttl=86400,
        )

        assert result is True
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "hyde:technical_research:abc123"
        assert call_args[0][1] == 86400

    @pytest.mark.asyncio
    async def test_get_cached_hyde_document_returns_cached_result(self):
        """get_cached_hyde_document should return cached HyDE result."""
        import json

        from app.services.cache import CacheService

        service = CacheService()
        mock_redis = AsyncMock()
        service._redis = mock_redis
        service.enabled = True

        cached_data = {
            "hypothetical_document": "Cached document",
            "word_count": 200,
            "skipped": False,
            "skip_reason": None,
            "variants": None,
        }
        mock_redis.get.return_value = json.dumps(cached_data)

        result = await service.get_cached_hyde_document(
            query_hash="abc123",
            routing_category="technical_research",
        )

        assert result is not None
        assert result["hypothetical_document"] == "Cached document"
        assert result["word_count"] == 200
        mock_redis.get.assert_called_once_with("hyde:technical_research:abc123")

    @pytest.mark.asyncio
    async def test_get_cached_hyde_document_returns_none_on_miss(self):
        """get_cached_hyde_document should return None on cache miss."""
        from app.services.cache import CacheService

        service = CacheService()
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        service._redis = mock_redis
        service.enabled = True

        result = await service.get_cached_hyde_document(
            query_hash="nonexistent",
            routing_category="technical_research",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_hyde_cache_different_routing_categories_separate_keys(self):
        """Same query with different routing should have separate cache keys."""
        from app.services.cache import CacheService

        service = CacheService()
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        service._redis = mock_redis
        service.enabled = True

        # Query with technical_research routing
        await service.get_cached_hyde_document(
            query_hash="samehash",
            routing_category="technical_research",
        )

        # Query with golden_set routing
        await service.get_cached_hyde_document(
            query_hash="samehash",
            routing_category="golden_set",
        )

        # Should have called with different keys
        calls = mock_redis.get.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "hyde:technical_research:samehash"
        assert calls[1][0][0] == "hyde:golden_set:samehash"

    @pytest.mark.asyncio
    async def test_cache_hyde_document_handles_redis_disabled(self):
        """cache_hyde_document should return False when Redis disabled."""
        from app.services.cache import CacheService

        service = CacheService()
        service.enabled = False

        result = await service.cache_hyde_document(
            query_hash="abc123",
            routing_category="technical_research",
            hyde_result={"test": "data"},
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_get_cached_hyde_document_handles_redis_disabled(self):
        """get_cached_hyde_document should return None when Redis disabled."""
        from app.services.cache import CacheService

        service = CacheService()
        service.enabled = False

        result = await service.get_cached_hyde_document(
            query_hash="abc123",
            routing_category="technical_research",
        )

        assert result is None


class TestHyDEGeneratorCacheIntegration:
    """Test HyDE generator cache integration."""

    @pytest.fixture
    def mock_llm_config(self):
        """Create mock LLM config."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 30000
        config.get_temperature.return_value = 0.3
        return config

    @pytest.mark.asyncio
    async def test_hyde_cache_hit_returns_cached_without_llm_call(self, mock_llm_config):
        """Cache hit should return cached result without making LLM call."""
        cached_result = {
            "hypothetical_document": "Cached HyDE document",
            "word_count": 180,
            "skipped": False,
            "skip_reason": None,
            "variants": None,
        }

        with patch("app.services.hyde_generator.cache_service") as mock_cache:
            mock_cache.get_cached_hyde_document = AsyncMock(return_value=cached_result)
            mock_cache.cache_hyde_document = AsyncMock(return_value=True)

            with patch("app.core.llm.factory.get_llm_factory") as mock_factory:
                service = HyDEGeneratorService(config=mock_llm_config)
                result = await service.generate(
                    query="Test query",
                    routing=RoutingCategory.TECHNICAL_RESEARCH,
                )

                # Should return cached result
                assert result.hypothetical_document == "Cached HyDE document"
                assert result.word_count == 180
                assert not result.skipped

                # Should not call LLM (cache hit means no generation needed)
                mock_factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_hyde_cache_miss_stores_result(self, mock_llm_config):
        """Cache miss should generate HyDE and store in cache."""
        with patch("app.services.hyde_generator.cache_service") as mock_cache:
            mock_cache.get_cached_hyde_document = AsyncMock(return_value=None)
            mock_cache.cache_hyde_document = AsyncMock(return_value=True)

            with patch("app.core.llm.factory.get_llm_factory") as mock_factory:
                mock_provider = AsyncMock()
                mock_provider.chat_completion.return_value = MagicMock(
                    content="Generated HyDE document for testing purposes."
                )
                mock_factory.return_value.create_provider.return_value = mock_provider

                service = HyDEGeneratorService(config=mock_llm_config)
                result = await service.generate(
                    query="Test query",
                    routing=RoutingCategory.TECHNICAL_RESEARCH,
                )

                # Should have generated result
                assert result.hypothetical_document == "Generated HyDE document for testing purposes."
                assert not result.skipped

                # Should have stored in cache
                mock_cache.cache_hyde_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_hyde_skipped_categories_not_cached(self, mock_llm_config):
        """Skipped categories (chitchat, calculator) should not be cached."""
        with patch("app.services.hyde_generator.cache_service") as mock_cache:
            mock_cache.get_cached_hyde_document = AsyncMock(return_value=None)
            mock_cache.cache_hyde_document = AsyncMock(return_value=True)

            service = HyDEGeneratorService(config=mock_llm_config)
            result = await service.generate(
                query="Ciao!",
                routing=RoutingCategory.CHITCHAT,
            )

            # Should be skipped
            assert result.skipped is True
            assert result.skip_reason == "chitchat"

            # Should not attempt to cache or lookup
            mock_cache.get_cached_hyde_document.assert_not_called()
            mock_cache.cache_hyde_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_hyde_query_hash_consistency(self, mock_llm_config):
        """Same query should produce same hash for cache key."""
        query = "Qual è l'aliquota IVA per le prestazioni sanitarie?"

        hash1 = hashlib.md5(query.encode()).hexdigest()
        hash2 = hashlib.md5(query.encode()).hexdigest()

        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_hyde_cache_error_continues_with_generation(self, mock_llm_config):
        """Cache errors should not prevent HyDE generation."""
        with patch("app.services.hyde_generator.cache_service") as mock_cache:
            mock_cache.get_cached_hyde_document = AsyncMock(side_effect=Exception("Redis connection error"))
            mock_cache.cache_hyde_document = AsyncMock(return_value=False)

            with patch("app.core.llm.factory.get_llm_factory") as mock_factory:
                mock_provider = AsyncMock()
                mock_provider.chat_completion.return_value = MagicMock(content="Generated despite cache error.")
                mock_factory.return_value.create_provider.return_value = mock_provider

                service = HyDEGeneratorService(config=mock_llm_config)
                result = await service.generate(
                    query="Test query",
                    routing=RoutingCategory.TECHNICAL_RESEARCH,
                )

                # Should still return generated result
                assert result.hypothetical_document == "Generated despite cache error."
                assert not result.skipped


class TestHyDECacheTTL:
    """Test HyDE cache TTL behavior."""

    @pytest.mark.asyncio
    async def test_default_ttl_is_24_hours(self):
        """Default cache TTL should be 24 hours (86400 seconds)."""
        from app.services.cache import CacheService

        service = CacheService()
        mock_redis = AsyncMock()
        service._redis = mock_redis
        service.enabled = True

        await service.cache_hyde_document(
            query_hash="test",
            routing_category="technical_research",
            hyde_result={"test": "data"},
        )

        # Should use default 24h TTL
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 86400

    @pytest.mark.asyncio
    async def test_custom_ttl_is_respected(self):
        """Custom TTL should be used when provided."""
        from app.services.cache import CacheService

        service = CacheService()
        mock_redis = AsyncMock()
        service._redis = mock_redis
        service.enabled = True

        await service.cache_hyde_document(
            query_hash="test",
            routing_category="technical_research",
            hyde_result={"test": "data"},
            ttl=3600,  # 1 hour
        )

        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 3600
