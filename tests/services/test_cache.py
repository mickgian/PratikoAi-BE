"""Tests for cache service functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from typing import List

from app.services.cache import CacheService, cache_service
from app.schemas.chat import Message
from app.core.llm.base import LLMResponse


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock()
    redis_mock.get = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.keys = AsyncMock()
    redis_mock.info = AsyncMock()
    redis_mock.eval = AsyncMock()
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
def sample_messages():
    """Sample messages for testing."""
    return [
        Message(role="system", content="You are a helpful assistant"),
        Message(role="user", content="What is 2+2?"),
    ]


@pytest.fixture
def sample_llm_response():
    """Sample LLM response for testing."""
    return LLMResponse(
        content="2+2 equals 4",
        model="gpt-4o-mini",
        provider="openai",
        tokens_used={"input": 20, "output": 8},
        cost_estimate=0.00015,
        finish_reason="stop",
        tool_calls=None,
    )


class TestCacheService:
    """Test cases for the cache service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache_service = CacheService()

    @patch('app.services.cache.REDIS_AVAILABLE', True)
    @patch('app.services.cache.settings')
    def test_init_enabled(self, mock_settings):
        """Test cache service initialization when enabled."""
        mock_settings.CACHE_ENABLED = True
        
        cache_service = CacheService()
        assert cache_service.enabled is True

    @patch('app.services.cache.REDIS_AVAILABLE', False)
    def test_init_redis_not_available(self):
        """Test cache service initialization when Redis is not available."""
        cache_service = CacheService()
        assert cache_service.enabled is False

    @patch('app.services.cache.settings')
    def test_init_disabled_by_config(self, mock_settings):
        """Test cache service initialization when disabled by config."""
        mock_settings.CACHE_ENABLED = False
        
        cache_service = CacheService()
        assert cache_service.enabled is False

    def test_generate_query_hash(self, sample_messages):
        """Test query hash generation."""
        hash1 = self.cache_service._generate_query_hash(
            sample_messages, "gpt-4o-mini", 0.2
        )
        hash2 = self.cache_service._generate_query_hash(
            sample_messages, "gpt-4o-mini", 0.2
        )
        hash3 = self.cache_service._generate_query_hash(
            sample_messages, "claude-3-haiku", 0.2
        )
        
        # Same inputs should produce same hash
        assert hash1 == hash2
        # Different model should produce different hash
        assert hash1 != hash3
        # Hash should be 64 characters (SHA256)
        assert len(hash1) == 64

    def test_generate_conversation_key(self):
        """Test conversation key generation."""
        session_id = "test-session-123"
        key = self.cache_service._generate_conversation_key(session_id)
        assert key == "conversation:test-session-123"

    def test_generate_query_key(self):
        """Test query key generation."""
        query_hash = "abcd1234"
        key = self.cache_service._generate_query_key(query_hash)
        assert key == "llm_response:abcd1234"

    @patch('app.services.cache.settings')
    async def test_get_redis_disabled(self, mock_settings):
        """Test getting Redis connection when disabled."""
        mock_settings.CACHE_ENABLED = False
        cache_service = CacheService()
        
        redis_client = await cache_service._get_redis()
        assert redis_client is None

    @patch('app.services.cache.redis')
    @patch('app.services.cache.settings')
    async def test_get_redis_connection_success(self, mock_settings, mock_redis_module):
        """Test successful Redis connection."""
        mock_settings.CACHE_ENABLED = True
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_settings.REDIS_PASSWORD = ""
        mock_settings.REDIS_DB = 0
        mock_settings.REDIS_MAX_CONNECTIONS = 10
        
        # Mock connection pool and Redis client
        mock_pool = MagicMock()
        mock_redis_module.ConnectionPool.from_url.return_value = mock_pool
        
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock()
        mock_redis_module.Redis.return_value = mock_redis_client
        
        cache_service = CacheService()
        cache_service.enabled = True
        
        redis_client = await cache_service._get_redis()
        
        assert redis_client == mock_redis_client
        mock_redis_client.ping.assert_called_once()

    async def test_get_cached_response_disabled(self, sample_messages):
        """Test getting cached response when cache is disabled."""
        self.cache_service.enabled = False
        
        result = await self.cache_service.get_cached_response(
            sample_messages, "gpt-4o-mini", 0.2
        )
        assert result is None

    @patch('app.services.cache.settings')
    async def test_get_cached_response_query_too_large(self, mock_settings, sample_messages):
        """Test getting cached response when query is too large."""
        mock_settings.CACHE_MAX_QUERY_SIZE = 5  # Very small limit
        
        # Mock Redis to be enabled
        with patch.object(self.cache_service, '_get_redis', return_value=AsyncMock()):
            self.cache_service.enabled = True
            
            result = await self.cache_service.get_cached_response(
                sample_messages, "gpt-4o-mini", 0.2
            )
            assert result is None

    async def test_get_cached_response_hit(self, sample_messages, sample_llm_response, mock_redis):
        """Test cache hit scenario."""
        # Mock cached data
        cached_data = {
            "content": sample_llm_response.content,
            "model": sample_llm_response.model,
            "provider": sample_llm_response.provider,
            "tokens_used": sample_llm_response.tokens_used,
            "cost_estimate": sample_llm_response.cost_estimate,
            "finish_reason": sample_llm_response.finish_reason,
            "tool_calls": sample_llm_response.tool_calls,
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        with patch.object(self.cache_service, '_get_redis', return_value=mock_redis):
            self.cache_service.enabled = True
            
            result = await self.cache_service.get_cached_response(
                sample_messages, "gpt-4o-mini", 0.2
            )
            
            assert result is not None
            assert result.content == sample_llm_response.content
            assert result.model == sample_llm_response.model

    async def test_get_cached_response_miss(self, sample_messages, mock_redis):
        """Test cache miss scenario."""
        mock_redis.get.return_value = None
        
        with patch.object(self.cache_service, '_get_redis', return_value=mock_redis):
            self.cache_service.enabled = True
            
            result = await self.cache_service.get_cached_response(
                sample_messages, "gpt-4o-mini", 0.2
            )
            assert result is None

    async def test_cache_response_success(self, sample_messages, sample_llm_response, mock_redis):
        """Test successful response caching."""
        with patch.object(self.cache_service, '_get_redis', return_value=mock_redis):
            self.cache_service.enabled = True
            
            result = await self.cache_service.cache_response(
                sample_messages, "gpt-4o-mini", sample_llm_response, 0.2, 3600
            )
            
            assert result is True
            mock_redis.setex.assert_called_once()

    async def test_cache_response_disabled(self, sample_messages, sample_llm_response):
        """Test caching when disabled."""
        self.cache_service.enabled = False
        
        result = await self.cache_service.cache_response(
            sample_messages, "gpt-4o-mini", sample_llm_response, 0.2
        )
        assert result is False

    async def test_get_conversation_cache_hit(self, mock_redis):
        """Test conversation cache hit."""
        session_id = "test-session"
        cached_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        mock_redis.get.return_value = json.dumps(cached_messages)
        
        with patch.object(self.cache_service, '_get_redis', return_value=mock_redis):
            self.cache_service.enabled = True
            
            result = await self.cache_service.get_conversation_cache(session_id)
            
            assert result is not None
            assert len(result) == 2
            assert result[0].role == "user"
            assert result[0].content == "Hello"

    async def test_cache_conversation_success(self, mock_redis):
        """Test successful conversation caching."""
        session_id = "test-session"
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!")
        ]
        
        with patch.object(self.cache_service, '_get_redis', return_value=mock_redis):
            self.cache_service.enabled = True
            
            result = await self.cache_service.cache_conversation(session_id, messages, 7200)
            
            assert result is True
            mock_redis.setex.assert_called_once()

    async def test_invalidate_conversation(self, mock_redis):
        """Test conversation invalidation."""
        session_id = "test-session"
        mock_redis.delete.return_value = 1
        
        with patch.object(self.cache_service, '_get_redis', return_value=mock_redis):
            self.cache_service.enabled = True
            
            result = await self.cache_service.invalidate_conversation(session_id)
            
            assert result is True
            mock_redis.delete.assert_called_once()

    async def test_get_cache_stats_disabled(self):
        """Test cache stats when disabled."""
        self.cache_service.enabled = False
        
        stats = await self.cache_service.get_cache_stats()
        
        assert stats["enabled"] is False
        assert stats["connected"] is False
        assert "error" in stats

    async def test_get_cache_stats_success(self, mock_redis):
        """Test successful cache stats retrieval."""
        mock_redis.info.return_value = {
            "redis_version": "7.0.0",
            "used_memory": 1000000,
            "used_memory_human": "976.56K",
            "connected_clients": 5,
            "total_commands_processed": 1000,
            "keyspace_hits": 800,
            "keyspace_misses": 200,
        }
        mock_redis.eval.return_value = 10  # Mock key count
        
        with patch.object(self.cache_service, '_get_redis', return_value=mock_redis):
            self.cache_service.enabled = True
            
            stats = await self.cache_service.get_cache_stats()
            
            assert stats["enabled"] is True
            assert stats["connected"] is True
            assert stats["redis_version"] == "7.0.0"
            assert stats["hit_rate"] == 0.8  # 800/(800+200)

    async def test_clear_cache_pattern(self, mock_redis):
        """Test clearing cache with pattern."""
        mock_redis.keys.return_value = ["llm_response:key1", "llm_response:key2"]
        mock_redis.delete.return_value = 2
        
        with patch.object(self.cache_service, '_get_redis', return_value=mock_redis):
            self.cache_service.enabled = True
            
            deleted = await self.cache_service.clear_cache("llm_response:*")
            
            assert deleted == 2
            mock_redis.keys.assert_called_once_with("llm_response:*")
            mock_redis.delete.assert_called_once()

    async def test_health_check_disabled(self):
        """Test health check when cache is disabled."""
        self.cache_service.enabled = False
        
        result = await self.cache_service.health_check()
        assert result is True  # Disabled cache is considered "healthy"

    async def test_health_check_success(self, mock_redis):
        """Test successful health check."""
        mock_redis.ping.return_value = "PONG"
        
        with patch.object(self.cache_service, '_get_redis', return_value=mock_redis):
            self.cache_service.enabled = True
            
            result = await self.cache_service.health_check()
            
            assert result is True
            mock_redis.ping.assert_called_once()

    async def test_close_connections(self, mock_redis):
        """Test closing Redis connections."""
        mock_pool = AsyncMock()
        self.cache_service._redis = mock_redis
        self.cache_service._connection_pool = mock_pool
        
        await self.cache_service.close()
        
        mock_redis.close.assert_called_once()
        mock_pool.disconnect.assert_called_once()
        assert self.cache_service._redis is None
        assert self.cache_service._connection_pool is None


class TestGlobalCacheService:
    """Test cases for the global cache service instance."""

    def test_cache_service_singleton(self):
        """Test that cache_service is a singleton-like instance."""
        # Import should return the same instance
        from app.services.cache import cache_service as cache1
        from app.services.cache import cache_service as cache2
        
        assert cache1 is cache2
        assert isinstance(cache1, CacheService)