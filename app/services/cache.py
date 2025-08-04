"""Redis-based caching service for LLM responses and conversations.

This module provides comprehensive caching capabilities to reduce API costs
and improve response times for the NormoAI application.
"""

import hashlib
import json
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import asdict

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.core.config import settings
from app.core.monitoring.metrics import track_cache_performance
from app.core.logging import logger
from app.schemas.chat import Message
from app.core.llm.base import LLMResponse


class CacheService:
    """Redis-based caching service for LLM responses and conversations."""

    def __init__(self):
        """Initialize the cache service."""
        self._redis: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
        self.enabled = settings.CACHE_ENABLED and REDIS_AVAILABLE
        
        if not REDIS_AVAILABLE:
            logger.warning(
                "redis_not_available",
                message="Redis package not installed. Caching disabled. Install with: pip install redis"
            )
            self.enabled = False
            
        if not self.enabled:
            logger.info("cache_service_disabled", redis_available=REDIS_AVAILABLE, config_enabled=settings.CACHE_ENABLED)

    async def _get_redis(self) -> Optional[redis.Redis]:
        """Get Redis connection with connection pooling.
        
        Returns:
            Redis connection or None if caching is disabled
        """
        if not self.enabled:
            return None
            
        if self._redis is None:
            try:
                # Create connection pool if not exists
                if self._connection_pool is None:
                    self._connection_pool = redis.ConnectionPool.from_url(
                        settings.REDIS_URL,
                        password=settings.REDIS_PASSWORD or None,
                        db=settings.REDIS_DB,
                        max_connections=settings.REDIS_MAX_CONNECTIONS,
                        retry_on_timeout=True,
                        socket_connect_timeout=5,
                        socket_timeout=5,
                    )
                
                self._redis = redis.Redis(connection_pool=self._connection_pool)
                
                # Test connection
                await self._redis.ping()
                logger.info("redis_connection_established", redis_url=settings.REDIS_URL)
                
            except Exception as e:
                logger.error("redis_connection_failed", error=str(e), redis_url=settings.REDIS_URL)
                self.enabled = False
                return None
                
        return self._redis

    def _generate_query_hash(self, messages: List[Message], model: str, temperature: float = 0.2) -> str:
        """Generate a deterministic hash for query deduplication.
        
        Args:
            messages: List of conversation messages
            model: Model name used for the query
            temperature: Temperature setting
            
        Returns:
            SHA256 hash of the query components
        """
        # Create a normalized representation of the query
        query_data = {
            "messages": [
                {"role": msg.role, "content": msg.content.strip()} 
                for msg in messages
            ],
            "model": model,
            "temperature": round(temperature, 2),  # Round to avoid floating point precision issues
        }
        
        # Sort keys for consistent hashing
        query_json = json.dumps(query_data, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(query_json.encode('utf-8')).hexdigest()

    def _generate_conversation_key(self, session_id: str) -> str:
        """Generate cache key for conversation history.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Cache key for the conversation
        """
        return f"conversation:{session_id}"

    def _generate_query_key(self, query_hash: str) -> str:
        """Generate cache key for LLM query response.
        
        Args:
            query_hash: Hash of the query
            
        Returns:
            Cache key for the query response
        """
        return f"llm_response:{query_hash}"

    async def get_cached_response(
        self, 
        messages: List[Message], 
        model: str, 
        temperature: float = 0.2
    ) -> Optional[LLMResponse]:
        """Get cached LLM response for a query.
        
        Args:
            messages: List of conversation messages
            model: Model name used for the query
            temperature: Temperature setting
            
        Returns:
            Cached LLMResponse or None if not found
        """
        redis_client = await self._get_redis()
        if not redis_client:
            return None
            
        try:
            # Check if query is too large to cache
            total_content_size = sum(len(msg.content) for msg in messages)
            if total_content_size > settings.CACHE_MAX_QUERY_SIZE:
                logger.debug(
                    "query_too_large_for_cache",
                    content_size=total_content_size,
                    max_size=settings.CACHE_MAX_QUERY_SIZE
                )
                return None
            
            query_hash = self._generate_query_hash(messages, model, temperature)
            cache_key = self._generate_query_key(query_hash)
            
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                try:
                    response_data = json.loads(cached_data)
                    logger.info(
                        "cache_hit_llm_response",
                        query_hash=query_hash[:12],
                        model=model,
                        cache_key=cache_key
                    )
                    
                    # Track cache hit in Prometheus
                    try:
                        # Cache hit metrics will be updated by periodic jobs
                        # This individual hit is logged for statistics
                        pass
                    except Exception as e:
                        logger.error("cache_metrics_tracking_failed", error=str(e))
                    
                    return LLMResponse(**response_data)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(
                        "cache_deserialization_failed",
                        error=str(e),
                        cache_key=cache_key
                    )
                    # Remove corrupted cache entry
                    await redis_client.delete(cache_key)
            
            return None
            
        except Exception as e:
            logger.error("cache_get_response_failed", error=str(e), model=model)
            return None

    async def cache_response(
        self,
        messages: List[Message],
        model: str,
        response: LLMResponse,
        temperature: float = 0.2,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache an LLM response for future use.
        
        Args:
            messages: List of conversation messages
            model: Model name used for the query
            response: LLM response to cache
            temperature: Temperature setting
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if caching succeeded, False otherwise
        """
        redis_client = await self._get_redis()
        if not redis_client:
            return False
            
        try:
            # Check if query is too large to cache
            total_content_size = sum(len(msg.content) for msg in messages)
            if total_content_size > settings.CACHE_MAX_QUERY_SIZE:
                return False
            
            query_hash = self._generate_query_hash(messages, model, temperature)
            cache_key = self._generate_query_key(query_hash)
            ttl = ttl or settings.CACHE_LLM_RESPONSE_TTL
            
            # Serialize response (excluding non-serializable fields if any)
            response_data = {
                "content": response.content,
                "model": response.model,
                "provider": response.provider,
                "tokens_used": response.tokens_used,
                "cost_estimate": response.cost_estimate,
                "finish_reason": response.finish_reason,
                "tool_calls": response.tool_calls,
            }
            
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(response_data, ensure_ascii=False)
            )
            
            logger.info(
                "cache_set_llm_response",
                query_hash=query_hash[:12],
                model=model,
                cache_key=cache_key,
                ttl=ttl,
                response_length=len(response.content)
            )
            
            return True
            
        except Exception as e:
            logger.error("cache_set_response_failed", error=str(e), model=model)
            return False

    async def get_conversation_cache(self, session_id: str) -> Optional[List[Message]]:
        """Get cached conversation history.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            List of cached messages or None if not found
        """
        redis_client = await self._get_redis()
        if not redis_client:
            return None
            
        try:
            cache_key = self._generate_conversation_key(session_id)
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                try:
                    messages_data = json.loads(cached_data)
                    messages = [Message(**msg_data) for msg_data in messages_data]
                    logger.info(
                        "cache_hit_conversation",
                        session_id=session_id,
                        message_count=len(messages)
                    )
                    return messages
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(
                        "cache_conversation_deserialization_failed",
                        error=str(e),
                        session_id=session_id
                    )
                    # Remove corrupted cache entry
                    await redis_client.delete(cache_key)
            
            return None
            
        except Exception as e:
            logger.error("cache_get_conversation_failed", error=str(e), session_id=session_id)
            return None

    async def cache_conversation(
        self,
        session_id: str,
        messages: List[Message],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache conversation history.
        
        Args:
            session_id: Unique session identifier
            messages: List of conversation messages
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if caching succeeded, False otherwise
        """
        redis_client = await self._get_redis()
        if not redis_client:
            return False
            
        try:
            cache_key = self._generate_conversation_key(session_id)
            ttl = ttl or settings.CACHE_CONVERSATION_TTL
            
            # Serialize messages
            messages_data = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(messages_data, ensure_ascii=False)
            )
            
            logger.info(
                "cache_set_conversation",
                session_id=session_id,
                message_count=len(messages),
                ttl=ttl
            )
            
            return True
            
        except Exception as e:
            logger.error("cache_set_conversation_failed", error=str(e), session_id=session_id)
            return False

    async def invalidate_conversation(self, session_id: str) -> bool:
        """Invalidate cached conversation history.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if invalidation succeeded, False otherwise
        """
        redis_client = await self._get_redis()
        if not redis_client:
            return False
            
        try:
            cache_key = self._generate_conversation_key(session_id)
            deleted = await redis_client.delete(cache_key)
            
            logger.info(
                "cache_invalidated_conversation",
                session_id=session_id,
                cache_deleted=bool(deleted)
            )
            
            return bool(deleted)
            
        except Exception as e:
            logger.error("cache_invalidate_conversation_failed", error=str(e), session_id=session_id)
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and health information.
        
        Returns:
            Dictionary with cache statistics
        """
        redis_client = await self._get_redis()
        if not redis_client:
            return {
                "enabled": False,
                "connected": False,
                "error": "Redis not available or disabled"
            }
            
        try:
            info = await redis_client.info()
            
            # Get key counts by pattern
            llm_response_keys = await redis_client.eval(
                "return #redis.call('keys', ARGV[1])", 0, "llm_response:*"
            )
            conversation_keys = await redis_client.eval(
                "return #redis.call('keys', ARGV[1])", 0, "conversation:*"
            )
            
            stats = {
                "enabled": True,
                "connected": True,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "llm_response_keys": llm_response_keys,
                "conversation_keys": conversation_keys,
                "total_keys": llm_response_keys + conversation_keys,
                "settings": {
                    "default_ttl": settings.CACHE_DEFAULT_TTL,
                    "conversation_ttl": settings.CACHE_CONVERSATION_TTL,
                    "llm_response_ttl": settings.CACHE_LLM_RESPONSE_TTL,
                    "max_query_size": settings.CACHE_MAX_QUERY_SIZE,
                }
            }
            
            # Calculate hit rate if we have data
            hits = stats["keyspace_hits"]
            misses = stats["keyspace_misses"]
            if hits + misses > 0:
                stats["hit_rate"] = hits / (hits + misses)
            else:
                stats["hit_rate"] = 0.0
                
            return stats
            
        except Exception as e:
            logger.error("cache_stats_failed", error=str(e))
            return {
                "enabled": True,
                "connected": False,
                "error": str(e)
            }

    async def clear_cache(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries matching a pattern.
        
        Args:
            pattern: Redis key pattern to match (e.g., "llm_response:*")
                    If None, clears all cache entries
            
        Returns:
            Number of keys deleted
        """
        redis_client = await self._get_redis()
        if not redis_client:
            return 0
            
        try:
            if pattern:
                # Delete keys matching pattern
                keys = await redis_client.keys(pattern)
                if keys:
                    deleted = await redis_client.delete(*keys)
                else:
                    deleted = 0
            else:
                # Clear all our cache keys
                llm_keys = await redis_client.keys("llm_response:*")
                conv_keys = await redis_client.keys("conversation:*")
                all_keys = llm_keys + conv_keys
                if all_keys:
                    deleted = await redis_client.delete(*all_keys)
                else:
                    deleted = 0
            
            logger.info(
                "cache_cleared",
                pattern=pattern or "all",
                keys_deleted=deleted
            )
            
            return deleted
            
        except Exception as e:
            logger.error("cache_clear_failed", error=str(e), pattern=pattern)
            return 0

    async def health_check(self) -> bool:
        """Check if the cache service is healthy.
        
        Returns:
            True if cache service is working, False otherwise
        """
        if not self.enabled:
            return True  # If caching is disabled, consider it "healthy"
            
        redis_client = await self._get_redis()
        if not redis_client:
            return False
            
        try:
            await redis_client.ping()
            return True
        except Exception as e:
            logger.error("cache_health_check_failed", error=str(e))
            return False

    async def close(self):
        """Close Redis connections and clean up resources."""
        if self._redis:
            try:
                await self._redis.close()
                logger.info("redis_connection_closed")
            except Exception as e:
                logger.error("redis_close_failed", error=str(e))
            finally:
                self._redis = None
                
        if self._connection_pool:
            try:
                await self._connection_pool.disconnect()
                logger.info("redis_connection_pool_closed")
            except Exception as e:
                logger.error("redis_pool_close_failed", error=str(e))
            finally:
                self._connection_pool = None

    async def update_cache_metrics(self):
        """Update Prometheus metrics for cache performance."""
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return
                
            # Get cache statistics
            info = await redis_client.info("stats")
            
            # Calculate hit ratio if available
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total = hits + misses
            
            if total > 0:
                hit_ratio = hits / total
                track_cache_performance('llm_responses', hit_ratio)
                track_cache_performance('conversations', hit_ratio)  # Simplified
                
                logger.debug(
                    "cache_metrics_updated",
                    hits=hits,
                    misses=misses,
                    hit_ratio=hit_ratio
                )
            
        except Exception as e:
            logger.error("cache_metrics_update_failed", error=str(e))


# Global cache service instance
cache_service = CacheService()