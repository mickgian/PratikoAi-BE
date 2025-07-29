"""Caching decorators for LLM responses and other expensive operations.

This module provides decorators to automatically cache function results,
particularly for LLM responses and database queries.
"""

import functools
import hashlib
import json
from typing import Any, Callable, Optional, Union, List
from datetime import datetime, timedelta

from app.core.logging import logger
from app.services.cache import cache_service
from app.schemas.chat import Message
from app.core.llm.base import LLMResponse


def cache_llm_response(
    ttl: Optional[int] = None,
    include_temperature: bool = True,
    max_query_size: Optional[int] = None
):
    """Decorator to cache LLM responses based on messages and model.
    
    Args:
        ttl: Time to live in seconds (uses default if None)
        include_temperature: Whether to include temperature in cache key
        max_query_size: Maximum query size to cache (uses config default if None)
    
    Usage:
        @cache_llm_response(ttl=3600)
        async def get_llm_response(messages: List[Message], model: str, temperature: float = 0.2) -> LLMResponse:
            # Your LLM call logic here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> LLMResponse:
            # Extract parameters for caching
            messages = kwargs.get('messages') or (args[0] if args else None)
            model = kwargs.get('model') or (args[1] if len(args) > 1 else None)
            temperature = kwargs.get('temperature', 0.2)
            
            if not messages or not model:
                logger.warning(
                    "cache_decorator_missing_params",
                    function=func.__name__,
                    has_messages=bool(messages),
                    has_model=bool(model)
                )
                return await func(*args, **kwargs)
            
            # Try to get cached response
            try:
                cache_kwargs = {"messages": messages, "model": model}
                if include_temperature:
                    cache_kwargs["temperature"] = temperature
                    
                cached_response = await cache_service.get_cached_response(**cache_kwargs)
                if cached_response:
                    logger.info(
                        "cache_decorator_hit",
                        function=func.__name__,
                        model=model,
                        message_count=len(messages) if isinstance(messages, list) else 1
                    )
                    return cached_response
            except Exception as e:
                logger.error(
                    "cache_decorator_get_failed",
                    function=func.__name__,
                    error=str(e)
                )
            
            # Call original function
            response = await func(*args, **kwargs)
            
            # Cache the response
            if isinstance(response, LLMResponse):
                try:
                    cache_kwargs = {
                        "messages": messages,
                        "model": model,
                        "response": response
                    }
                    if include_temperature:
                        cache_kwargs["temperature"] = temperature
                    if ttl:
                        cache_kwargs["ttl"] = ttl
                        
                    await cache_service.cache_response(**cache_kwargs)
                    logger.info(
                        "cache_decorator_set",
                        function=func.__name__,
                        model=model,
                        response_length=len(response.content)
                    )
                except Exception as e:
                    logger.error(
                        "cache_decorator_set_failed",
                        function=func.__name__,
                        error=str(e)
                    )
            
            return response
        
        return wrapper
    return decorator


def cache_conversation(ttl: Optional[int] = None):
    """Decorator to cache conversation history.
    
    Args:
        ttl: Time to live in seconds (uses default if None)
    
    Usage:
        @cache_conversation(ttl=7200)
        async def get_conversation(session_id: str) -> List[Message]:
            # Your conversation retrieval logic here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> List[Message]:
            # Extract session_id for caching
            session_id = kwargs.get('session_id') or (args[0] if args else None)
            
            if not session_id:
                logger.warning(
                    "cache_conversation_decorator_no_session",
                    function=func.__name__
                )
                return await func(*args, **kwargs)
            
            # Try to get cached conversation
            try:
                cached_messages = await cache_service.get_conversation_cache(session_id)
                if cached_messages:
                    logger.info(
                        "cache_conversation_decorator_hit",
                        function=func.__name__,
                        session_id=session_id,
                        message_count=len(cached_messages)
                    )
                    return cached_messages
            except Exception as e:
                logger.error(
                    "cache_conversation_decorator_get_failed",
                    function=func.__name__,
                    error=str(e),
                    session_id=session_id
                )
            
            # Call original function
            messages = await func(*args, **kwargs)
            
            # Cache the conversation
            if isinstance(messages, list):
                try:
                    cache_kwargs = {
                        "session_id": session_id,
                        "messages": messages
                    }
                    if ttl:
                        cache_kwargs["ttl"] = ttl
                        
                    await cache_service.cache_conversation(**cache_kwargs)
                    logger.info(
                        "cache_conversation_decorator_set",
                        function=func.__name__,
                        session_id=session_id,
                        message_count=len(messages)
                    )
                except Exception as e:
                    logger.error(
                        "cache_conversation_decorator_set_failed",
                        function=func.__name__,
                        error=str(e),
                        session_id=session_id
                    )
            
            return messages
        
        return wrapper
    return decorator


def cache_result(
    key_func: Optional[Callable] = None,
    ttl: int = 3600,
    namespace: str = "general"
):
    """Generic caching decorator for any function result.
    
    Args:
        key_func: Function to generate cache key from args/kwargs
        ttl: Time to live in seconds
        namespace: Cache namespace to avoid key collisions
    
    Usage:
        @cache_result(key_func=lambda user_id: f"user_data_{user_id}", ttl=1800)
        async def get_user_data(user_id: str) -> dict:
            # Your expensive operation here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            if key_func:
                try:
                    cache_key = key_func(*args, **kwargs)
                except Exception as e:
                    logger.error(
                        "cache_result_key_generation_failed",
                        function=func.__name__,
                        error=str(e)
                    )
                    return await func(*args, **kwargs)
            else:
                # Generate key from function name and args
                key_data = {
                    "function": func.__name__,
                    "args": str(args),
                    "kwargs": str(sorted(kwargs.items()))
                }
                key_string = json.dumps(key_data, sort_keys=True)
                cache_key = hashlib.sha256(key_string.encode()).hexdigest()[:16]
            
            # Add namespace
            full_cache_key = f"{namespace}:{cache_key}"
            
            # Try to get cached result
            redis_client = await cache_service._get_redis()
            if redis_client:
                try:
                    cached_data = await redis_client.get(full_cache_key)
                    if cached_data:
                        try:
                            result = json.loads(cached_data)
                            logger.info(
                                "cache_result_decorator_hit",
                                function=func.__name__,
                                cache_key=cache_key,
                                namespace=namespace
                            )
                            return result
                        except json.JSONDecodeError as e:
                            logger.warning(
                                "cache_result_deserialize_failed",
                                function=func.__name__,
                                error=str(e),
                                cache_key=cache_key
                            )
                            # Remove corrupted cache entry
                            await redis_client.delete(full_cache_key)
                except Exception as e:
                    logger.error(
                        "cache_result_get_failed",
                        function=func.__name__,
                        error=str(e),
                        cache_key=cache_key
                    )
            
            # Call original function
            result = await func(*args, **kwargs)
            
            # Cache the result
            if redis_client and result is not None:
                try:
                    # Only cache JSON-serializable results
                    serialized_result = json.dumps(result, ensure_ascii=False)
                    await redis_client.setex(full_cache_key, ttl, serialized_result)
                    logger.info(
                        "cache_result_decorator_set",
                        function=func.__name__,
                        cache_key=cache_key,
                        namespace=namespace,
                        ttl=ttl
                    )
                except (TypeError, json.JSONEncodeError) as e:
                    logger.warning(
                        "cache_result_serialize_failed",
                        function=func.__name__,
                        error=str(e),
                        cache_key=cache_key
                    )
                except Exception as e:
                    logger.error(
                        "cache_result_set_failed",
                        function=func.__name__,
                        error=str(e),
                        cache_key=cache_key
                    )
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache_on_update(
    cache_keys_func: Callable,
    namespace: str = "general"
):
    """Decorator to invalidate cache entries when data is updated.
    
    Args:
        cache_keys_func: Function to generate cache keys to invalidate
        namespace: Cache namespace
    
    Usage:
        @invalidate_cache_on_update(
            cache_keys_func=lambda user_id: [f"user_data_{user_id}", f"user_profile_{user_id}"]
        )
        async def update_user(user_id: str, data: dict) -> bool:
            # Your update logic here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Call original function first
            result = await func(*args, **kwargs)
            
            # Invalidate cache entries
            redis_client = await cache_service._get_redis()
            if redis_client:
                try:
                    cache_keys = cache_keys_func(*args, **kwargs)
                    if isinstance(cache_keys, str):
                        cache_keys = [cache_keys]
                    
                    full_cache_keys = [f"{namespace}:{key}" for key in cache_keys]
                    if full_cache_keys:
                        deleted = await redis_client.delete(*full_cache_keys)
                        logger.info(
                            "cache_invalidation_decorator",
                            function=func.__name__,
                            keys_deleted=deleted,
                            cache_keys=cache_keys,
                            namespace=namespace
                        )
                except Exception as e:
                    logger.error(
                        "cache_invalidation_failed",
                        function=func.__name__,
                        error=str(e)
                    )
            
            return result
        
        return wrapper
    return decorator