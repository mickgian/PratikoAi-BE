# AUTO-GENERATED ORCHESTRATOR STUBS (safe to edit below stubs)
# These functions are the functional *nodes* that mirror the Mermaid diagram.
# Implement thin coordination here (call services/factories), not core business logic.

from contextlib import nullcontext
from typing import Any, Dict, List, Optional

try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover
    def rag_step_log(**kwargs): return None
    def rag_step_timer(*args, **kwargs): return nullcontext()

async def step_59__check_cache(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 59 — LangGraphAgent._get_cached_llm_response Check for cached response
    ID: RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response
    Type: process | Category: cache | Node: CheckCache

    Initializes the cache checking process by extracting query parameters and setting up
    cache checking state. This orchestrator prepares the context for subsequent cache operations.
    """
    from app.core.logging import logger
    from app.services.cache import cache_service
    from datetime import datetime

    with rag_step_timer(59, 'RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response', 'CheckCache', stage="start"):
        # Extract context parameters
        messages_list = kwargs.get('messages') or (ctx or {}).get('messages') or messages or []
        model = kwargs.get('model') or (ctx or {}).get('model')
        temperature = kwargs.get('temperature') or (ctx or {}).get('temperature', 0.2)
        user_id = kwargs.get('user_id') or (ctx or {}).get('user_id')
        session_id = kwargs.get('session_id') or (ctx or {}).get('session_id')
        provider = kwargs.get('provider') or (ctx or {}).get('provider')

        # Initialize cache check data
        cache_enabled = cache_service.enabled if cache_service else False
        cache_check_initialized = False
        query_hash = None
        error = None

        try:
            # Validate required parameters
            if not messages_list or not model:
                error = 'Missing required cache check parameters: messages or model'
                raise ValueError(error)

            # Convert messages to proper format if needed
            from app.schemas.chat import Message
            formatted_messages = []
            for msg in messages_list:
                if isinstance(msg, dict):
                    formatted_messages.append(Message(
                        role=msg.get('role', 'user'),
                        content=str(msg.get('content', ''))
                    ))
                elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                    formatted_messages.append(msg)
                else:
                    formatted_messages.append(Message(
                        role='user',
                        content=str(msg)
                    ))

            # Generate query hash for this request if cache is enabled
            if cache_enabled and formatted_messages:
                query_hash = cache_service._generate_query_hash(
                    messages=formatted_messages,
                    model=model,
                    temperature=temperature
                )

            cache_check_initialized = True

        except Exception as e:
            error = str(e)

        # Create cache check result
        cache_check_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'cache_check_initialized': cache_check_initialized,
            'cache_enabled': cache_enabled,
            'messages_count': len(messages_list) if messages_list else 0,
            'model': model,
            'temperature': temperature,
            'query_hash': query_hash,
            'user_id': user_id,
            'session_id': session_id,
            'provider': provider,
            'error': error
        }

        # Log cache check initialization
        if error:
            log_message = f"Cache check initialization failed: {error}"
            logger.error(log_message, extra={
                'cache_event': 'check_initialization_failed',
                'error': error,
                'model': model,
                'cache_enabled': cache_enabled
            })
        else:
            log_message = f"Cache check initialized for model: {model}"
            logger.info(log_message, extra={
                'cache_event': 'check_initialized',
                'model': model,
                'cache_enabled': cache_enabled,
                'messages_count': len(messages_list) if messages_list else 0,
                'query_hash': query_hash[:16] + '...' if query_hash else None
            })

        # RAG step logging
        rag_step_log(
            step=59,
            step_id='RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response',
            node_label='CheckCache',
            category='cache',
            type='process',
            cache_event='check_initialization_failed' if error else 'check_initialized',
            cache_check_initialized=cache_check_initialized,
            cache_enabled=cache_enabled,
            model=model,
            messages_count=len(messages_list) if messages_list else 0,
            query_hash=query_hash[:16] + '...' if query_hash else None,
            error=error,
            processing_stage="completed"
        )

        return cache_check_data

async def step_61__gen_hash(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 61 — CacheService._generate_response_key sig and doc_hashes and epochs and versions
    ID: RAG.cache.cacheservice.generate.response.key.sig.and.doc.hashes.and.epochs.and.versions
    Type: process | Category: cache | Node: GenHash

    Generates a comprehensive cache key that includes query signature, document hashes,
    epochs, and versions. This orchestrator coordinates cache key generation for response caching.
    """
    from app.core.logging import logger
    from app.services.cache import cache_service
    from datetime import datetime
    import hashlib
    import json

    with rag_step_timer(61, 'RAG.cache.cacheservice.generate.response.key.sig.and.doc.hashes.and.epochs.and.versions', 'GenHash', stage="start"):
        # Extract context parameters
        query_hash = kwargs.get('query_hash') or (ctx or {}).get('query_hash')
        doc_hashes = kwargs.get('doc_hashes') or (ctx or {}).get('doc_hashes', [])
        kb_epoch = kwargs.get('kb_epoch') or (ctx or {}).get('kb_epoch')
        golden_epoch = kwargs.get('golden_epoch') or (ctx or {}).get('golden_epoch')
        ccnl_epoch = kwargs.get('ccnl_epoch') or (ctx or {}).get('ccnl_epoch')
        parser_version = kwargs.get('parser_version') or (ctx or {}).get('parser_version')
        model = kwargs.get('model') or (ctx or {}).get('model')
        temperature = kwargs.get('temperature') or (ctx or {}).get('temperature', 0.2)

        # Initialize hash generation data
        cache_key_generated = False
        cache_key = None
        query_key = None
        composite_key = None
        error = None

        try:
            # Generate base query key if not provided
            if not query_hash and cache_service and cache_service.enabled:
                messages_list = kwargs.get('messages') or (ctx or {}).get('messages') or messages or []
                if messages_list and model:
                    from app.schemas.chat import Message
                    formatted_messages = []
                    for msg in messages_list:
                        if isinstance(msg, dict):
                            formatted_messages.append(Message(
                                role=msg.get('role', 'user'),
                                content=str(msg.get('content', ''))
                            ))
                        elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                            formatted_messages.append(msg)
                        else:
                            formatted_messages.append(Message(
                                role='user',
                                content=str(msg)
                            ))

                    query_hash = cache_service._generate_query_hash(
                        messages=formatted_messages,
                        model=model,
                        temperature=temperature
                    )

            if not query_hash:
                error = 'No query hash available for cache key generation'
                raise ValueError(error)

            # Create comprehensive cache key components
            key_components = {
                'query_hash': query_hash,
                'model': model,
                'temperature': round(temperature, 2),
                'doc_hashes': sorted(doc_hashes) if doc_hashes else [],
                'epochs': {
                    'kb_epoch': kb_epoch,
                    'golden_epoch': golden_epoch,
                    'ccnl_epoch': ccnl_epoch
                },
                'parser_version': parser_version
            }

            # Generate deterministic composite key
            key_string = json.dumps(key_components, sort_keys=True, separators=(',', ':'))
            composite_key = hashlib.sha256(key_string.encode('utf-8')).hexdigest()

            # Create final cache key using CacheService pattern
            if cache_service:
                query_key = cache_service._generate_query_key(query_hash)
                cache_key = f"{query_key}:{composite_key[:16]}"
            else:
                cache_key = f"rag:response:{composite_key[:32]}"

            cache_key_generated = True

        except Exception as e:
            error = str(e)

        # Create hash generation result
        hash_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'cache_key_generated': cache_key_generated,
            'cache_key': cache_key,
            'query_key': query_key,
            'composite_key': composite_key,
            'query_hash': query_hash,
            'doc_hashes_count': len(doc_hashes) if doc_hashes else 0,
            'epochs_included': {
                'kb_epoch': kb_epoch is not None,
                'golden_epoch': golden_epoch is not None,
                'ccnl_epoch': ccnl_epoch is not None
            },
            'parser_version': parser_version,
            'model': model,
            'temperature': temperature,
            'error': error
        }

        # Log hash generation result
        if error:
            log_message = f"Cache key generation failed: {error}"
            logger.error(log_message, extra={
                'cache_event': 'key_generation_failed',
                'error': error,
                'model': model,
                'query_hash': query_hash[:16] + '...' if query_hash else None
            })
        else:
            log_message = f"Cache key generated: {cache_key[:32]}..."
            logger.info(log_message, extra={
                'cache_event': 'key_generated',
                'cache_key': cache_key[:32] + '...' if cache_key else None,
                'model': model,
                'doc_hashes_count': len(doc_hashes) if doc_hashes else 0,
                'epochs_included': sum(1 for epoch in [kb_epoch, golden_epoch, ccnl_epoch] if epoch is not None)
            })

        # RAG step logging
        rag_step_log(
            step=61,
            step_id='RAG.cache.cacheservice.generate.response.key.sig.and.doc.hashes.and.epochs.and.versions',
            node_label='GenHash',
            category='cache',
            type='process',
            cache_event='key_generation_failed' if error else 'key_generated',
            cache_key_generated=cache_key_generated,
            cache_key=cache_key[:32] + '...' if cache_key else None,
            model=model,
            doc_hashes_count=len(doc_hashes) if doc_hashes else 0,
            epochs_included=sum(1 for epoch in [kb_epoch, golden_epoch, ccnl_epoch] if epoch is not None),
            error=error,
            processing_stage="completed"
        )

        return hash_data

async def step_62__cache_hit(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 62 — Cache hit?
    ID: RAG.cache.cache.hit
    Type: decision | Category: cache | Node: CacheHit

    Checks if a cached response exists in Redis for the given cache key.
    This is a decision node that returns true/false based on cache hit status.
    """
    from app.core.logging import logger
    from app.services.cache import cache_service
    from datetime import datetime

    with rag_step_timer(62, 'RAG.cache.cache.hit', 'CacheHit', stage="start"):
        # Extract context parameters
        cache_key = kwargs.get('cache_key') or (ctx or {}).get('cache_key')
        model = kwargs.get('model') or (ctx or {}).get('model')
        temperature = kwargs.get('temperature') or (ctx or {}).get('temperature', 0.2)
        messages_list = kwargs.get('messages') or (ctx or {}).get('messages') or messages or []

        # Initialize cache hit check data
        cache_hit = False
        cached_response = None
        cache_lookup_performed = False
        error = None

        try:
            # Check if cache is enabled and key is available
            if not cache_service or not cache_service.enabled:
                error = 'Cache service not available or disabled'
                raise ValueError(error)

            if not cache_key:
                error = 'No cache key provided for lookup'
                raise ValueError(error)

            # Perform cache lookup using CacheService
            if messages_list and model:
                # Convert messages to proper format if needed
                from app.schemas.chat import Message
                formatted_messages = []
                for msg in messages_list:
                    if isinstance(msg, dict):
                        formatted_messages.append(Message(
                            role=msg.get('role', 'user'),
                            content=str(msg.get('content', ''))
                        ))
                    elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                        formatted_messages.append(msg)
                    else:
                        formatted_messages.append(Message(
                            role='user',
                            content=str(msg)
                        ))

                # Use CacheService get_cached_response method
                cached_response = await cache_service.get_cached_response(
                    messages=formatted_messages,
                    model=model,
                    temperature=temperature
                )

                cache_lookup_performed = True
                cache_hit = cached_response is not None

            else:
                # Fallback: direct Redis lookup using the cache key
                redis_client = await cache_service._get_redis()
                if redis_client:
                    cached_data = await redis_client.get(cache_key)
                    cache_lookup_performed = True
                    cache_hit = cached_data is not None
                    if cached_data:
                        import json
                        try:
                            cached_response = json.loads(cached_data)
                        except json.JSONDecodeError:
                            cached_response = cached_data.decode('utf-8') if isinstance(cached_data, bytes) else cached_data

        except Exception as e:
            error = str(e)

        # Create cache hit result
        cache_hit_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'cache_hit': cache_hit,
            'cache_lookup_performed': cache_lookup_performed,
            'cache_key': cache_key,
            'cached_response_available': cached_response is not None,
            'cached_response_type': type(cached_response).__name__ if cached_response else None,
            'model': model,
            'temperature': temperature,
            'messages_count': len(messages_list) if messages_list else 0,
            'error': error
        }

        # Include cached response if found (for subsequent steps)
        if cached_response and not error:
            cache_hit_data['cached_response'] = cached_response

        # Log cache hit result
        if error:
            log_message = f"Cache lookup failed: {error}"
            logger.error(log_message, extra={
                'cache_event': 'lookup_failed',
                'error': error,
                'cache_key': cache_key[:32] + '...' if cache_key else None,
                'model': model
            })
        elif cache_hit:
            log_message = f"Cache hit for key: {cache_key[:32]}..."
            logger.info(log_message, extra={
                'cache_event': 'cache_hit',
                'cache_key': cache_key[:32] + '...' if cache_key else None,
                'model': model,
                'cached_response_type': type(cached_response).__name__ if cached_response else None
            })
        else:
            log_message = f"Cache miss for key: {cache_key[:32]}..."
            logger.info(log_message, extra={
                'cache_event': 'cache_miss',
                'cache_key': cache_key[:32] + '...' if cache_key else None,
                'model': model
            })

        # RAG step logging
        rag_step_log(
            step=62,
            step_id='RAG.cache.cache.hit',
            node_label='CacheHit',
            category='cache',
            type='decision',
            cache_event='lookup_failed' if error else ('cache_hit' if cache_hit else 'cache_miss'),
            cache_hit=cache_hit,
            cache_lookup_performed=cache_lookup_performed,
            cache_key=cache_key[:32] + '...' if cache_key else None,
            model=model,
            cached_response_available=cached_response is not None,
            error=error,
            processing_stage="completed"
        )

        return cache_hit_data

async def step_63__track_cache_hit(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 63 — UsageTracker.track Track cache hit
    ID: RAG.cache.usagetracker.track.track.cache.hit
    Type: process | Category: cache | Node: TrackCacheHit

    Tracks cache hit usage in the usage tracking system. Cache hits have zero cost
    and improve cache hit rate metrics. This orchestrator coordinates with UsageTracker.
    """
    from app.core.logging import logger
    from app.services.usage_tracker import usage_tracker
    from app.core.llm.base import LLMResponse
    from datetime import datetime

    with rag_step_timer(63, 'RAG.cache.usagetracker.track.track.cache.hit', 'TrackCacheHit', stage="start"):
        # Extract context parameters
        user_id = kwargs.get('user_id') or (ctx or {}).get('user_id')
        session_id = kwargs.get('session_id') or (ctx or {}).get('session_id')
        provider = kwargs.get('provider') or (ctx or {}).get('provider')
        model = kwargs.get('model') or (ctx or {}).get('model')
        cached_response = kwargs.get('cached_response') or (ctx or {}).get('cached_response')
        response_time_ms = kwargs.get('response_time_ms') or (ctx or {}).get('response_time_ms', 0)
        cache_key = kwargs.get('cache_key') or (ctx or {}).get('cache_key')
        pii_detected = kwargs.get('pii_detected') or (ctx or {}).get('pii_detected', False)
        pii_types = kwargs.get('pii_types') or (ctx or {}).get('pii_types')
        ip_address = kwargs.get('ip_address') or (ctx or {}).get('ip_address')
        user_agent = kwargs.get('user_agent') or (ctx or {}).get('user_agent')

        # Initialize cache hit tracking data
        cache_hit_tracked = False
        total_tokens = 0
        error = None

        try:
            # Validate required fields for cache hit tracking
            if not all([user_id, session_id, provider, model]):
                error = 'Missing required cache hit tracking data'
                raise ValueError(error)

            # Create LLMResponse object for cache hit (zero cost, estimated tokens)
            if cached_response:
                # Estimate tokens from cached response content
                if isinstance(cached_response, dict):
                    content = cached_response.get('content', str(cached_response))
                elif hasattr(cached_response, 'content'):
                    content = cached_response.content
                else:
                    content = str(cached_response)

                # Rough token estimation: ~4 chars per token
                estimated_tokens = len(content) // 4 if content else 50

                llm_response = LLMResponse(
                    content=content[:1000] if isinstance(content, str) else str(content)[:1000],
                    model=model,
                    provider=provider,
                    tokens_used=estimated_tokens,
                    cost_estimate=0.0  # Cache hits have zero cost
                )
            else:
                # Fallback LLM response for cache hit
                llm_response = LLMResponse(
                    content="[cached response]",
                    model=model,
                    provider=provider,
                    tokens_used=0,
                    cost_estimate=0.0
                )

            total_tokens = llm_response.tokens_used or 0

            # Track cache hit using UsageTracker with cache_hit=True
            usage_event = await usage_tracker.track_llm_usage(
                user_id=user_id,
                session_id=session_id,
                provider=provider,
                model=model,
                llm_response=llm_response,
                response_time_ms=response_time_ms,
                cache_hit=True,  # This is the key difference
                pii_detected=pii_detected,
                pii_types=pii_types,
                ip_address=ip_address,
                user_agent=user_agent
            )

            cache_hit_tracked = True

        except Exception as e:
            error = str(e)

        # Create cache hit tracking result
        tracking_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'cache_hit_tracked': cache_hit_tracked,
            'user_id': user_id,
            'session_id': session_id,
            'provider': provider,
            'model': model,
            'total_tokens': total_tokens,
            'cost': 0.0,  # Cache hits always have zero cost
            'cache_hit': True,
            'cache_key': cache_key,
            'response_time_ms': response_time_ms,
            'pii_detected': pii_detected,
            'cached_response_available': cached_response is not None,
            'error': error
        }

        # Log cache hit tracking result
        if error:
            log_message = f"Cache hit tracking failed: {error}"
            logger.error(log_message, extra={
                'cache_event': 'hit_tracking_failed',
                'error': error,
                'user_id': user_id,
                'provider': provider,
                'model': model,
                'cache_key': cache_key[:32] + '...' if cache_key else None
            })
        else:
            log_message = f"Cache hit tracked successfully: {provider}/{model}"
            logger.info(log_message, extra={
                'cache_event': 'hit_tracked',
                'user_id': user_id,
                'provider': provider,
                'model': model,
                'total_tokens': total_tokens,
                'response_time_ms': response_time_ms,
                'cache_key': cache_key[:32] + '...' if cache_key else None
            })

        # RAG step logging
        rag_step_log(
            step=63,
            step_id='RAG.cache.usagetracker.track.track.cache.hit',
            node_label='TrackCacheHit',
            category='cache',
            type='process',
            cache_event='hit_tracking_failed' if error else 'hit_tracked',
            cache_hit_tracked=cache_hit_tracked,
            user_id=user_id,
            provider=provider,
            model=model,
            total_tokens=total_tokens,
            cost=0.0,
            cache_hit=True,
            response_time_ms=response_time_ms,
            error=error,
            processing_stage="completed"
        )

        return tracking_data

async def step_65__log_cache_hit(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 65 — Logger.info Log cache hit
    ID: RAG.cache.logger.info.log.cache.hit
    Type: process | Category: cache | Node: LogCacheHit

    Logs cache hit event with comprehensive metadata for monitoring and debugging.
    This orchestrator provides detailed logging for cache operations.
    """
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(65, 'RAG.cache.logger.info.log.cache.hit', 'LogCacheHit', stage="start"):
        # Extract context parameters
        cache_key = kwargs.get('cache_key') or (ctx or {}).get('cache_key')
        user_id = kwargs.get('user_id') or (ctx or {}).get('user_id')
        session_id = kwargs.get('session_id') or (ctx or {}).get('session_id')
        model = kwargs.get('model') or (ctx or {}).get('model')
        provider = kwargs.get('provider') or (ctx or {}).get('provider')
        response_time_ms = kwargs.get('response_time_ms') or (ctx or {}).get('response_time_ms', 0)
        total_tokens = kwargs.get('total_tokens') or (ctx or {}).get('total_tokens', 0)
        cached_response_type = kwargs.get('cached_response_type') or (ctx or {}).get('cached_response_type')

        # Create log entry result
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'cache_hit_logged': True,
            'cache_key': cache_key,
            'user_id': user_id,
            'session_id': session_id,
            'model': model,
            'provider': provider,
            'response_time_ms': response_time_ms,
            'total_tokens': total_tokens,
            'cached_response_type': cached_response_type,
            'cost_savings': True  # Cache hits save API costs
        }

        # Log cache hit with detailed information
        log_message = f"Cache hit served for {provider}/{model}"
        logger.info(log_message, extra={
            'cache_event': 'cache_hit_served',
            'cache_key': cache_key[:32] + '...' if cache_key else None,
            'user_id': user_id,
            'session_id': session_id,
            'model': model,
            'provider': provider,
            'response_time_ms': response_time_ms,
            'total_tokens': total_tokens,
            'cached_response_type': cached_response_type,
            'cost_savings': True
        })

        # RAG step logging
        rag_step_log(
            step=65,
            step_id='RAG.cache.logger.info.log.cache.hit',
            node_label='LogCacheHit',
            category='cache',
            type='process',
            cache_event='cache_hit_logged',
            cache_hit_logged=True,
            cache_key=cache_key[:32] + '...' if cache_key else None,
            user_id=user_id,
            model=model,
            provider=provider,
            response_time_ms=response_time_ms,
            total_tokens=total_tokens,
            processing_stage="completed"
        )

        return log_data

async def step_66__return_cached(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 66 — Return cached response
    ID: RAG.cache.return.cached.response
    Type: process | Category: cache | Node: ReturnCached

    Formats and returns the cached response with appropriate metadata.
    This orchestrator prepares cached responses for return to the client.
    """
    from app.core.logging import logger
    from app.core.llm.base import LLMResponse
    from datetime import datetime

    with rag_step_timer(66, 'RAG.cache.return.cached.response', 'ReturnCached', stage="start"):
        # Extract context parameters
        cached_response = kwargs.get('cached_response') or (ctx or {}).get('cached_response')
        cache_key = kwargs.get('cache_key') or (ctx or {}).get('cache_key')
        model = kwargs.get('model') or (ctx or {}).get('model')
        provider = kwargs.get('provider') or (ctx or {}).get('provider')
        user_id = kwargs.get('user_id') or (ctx or {}).get('user_id')
        session_id = kwargs.get('session_id') or (ctx or {}).get('session_id')
        response_time_ms = kwargs.get('response_time_ms') or (ctx or {}).get('response_time_ms', 0)

        # Initialize return data
        cached_response_returned = False
        formatted_response = None
        error = None

        try:
            if not cached_response:
                error = 'No cached response available to return'
                raise ValueError(error)

            # Format cached response based on type
            if isinstance(cached_response, LLMResponse):
                formatted_response = cached_response
            elif isinstance(cached_response, dict):
                # Convert dict to LLMResponse if possible
                formatted_response = LLMResponse(
                    content=cached_response.get('content', str(cached_response)),
                    model=model or cached_response.get('model', 'unknown'),
                    provider=provider or cached_response.get('provider', 'unknown'),
                    tokens_used=cached_response.get('tokens_used', 0),
                    cost_estimate=0.0  # Cache hits have zero cost
                )
            else:
                # Convert string or other types to LLMResponse
                formatted_response = LLMResponse(
                    content=str(cached_response),
                    model=model or 'unknown',
                    provider=provider or 'unknown',
                    tokens_used=len(str(cached_response)) // 4,  # Rough estimate
                    cost_estimate=0.0
                )

            # Add cache metadata
            if hasattr(formatted_response, '__dict__'):
                formatted_response.from_cache = True
                formatted_response.cache_key = cache_key
                formatted_response.cached_at = datetime.utcnow().isoformat() + 'Z'

            cached_response_returned = True

        except Exception as e:
            error = str(e)

        # Create return result
        return_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'cached_response_returned': cached_response_returned,
            'response': formatted_response,
            'cache_key': cache_key,
            'model': model,
            'provider': provider,
            'user_id': user_id,
            'session_id': session_id,
            'response_time_ms': response_time_ms,
            'from_cache': True,
            'cost': 0.0,
            'error': error
        }

        # Log cached response return
        if error:
            log_message = f"Failed to return cached response: {error}"
            logger.error(log_message, extra={
                'cache_event': 'return_failed',
                'error': error,
                'cache_key': cache_key[:32] + '...' if cache_key else None
            })
        else:
            log_message = f"Cached response returned for {provider}/{model}"
            logger.info(log_message, extra={
                'cache_event': 'response_returned',
                'cache_key': cache_key[:32] + '...' if cache_key else None,
                'model': model,
                'provider': provider,
                'response_time_ms': response_time_ms
            })

        # RAG step logging
        rag_step_log(
            step=66,
            step_id='RAG.cache.return.cached.response',
            node_label='ReturnCached',
            category='cache',
            type='process',
            cache_event='return_failed' if error else 'response_returned',
            cached_response_returned=cached_response_returned,
            cache_key=cache_key[:32] + '...' if cache_key else None,
            model=model,
            provider=provider,
            from_cache=True,
            cost=0.0,
            error=error,
            processing_stage="completed"
        )

        return return_data

async def step_68__cache_response(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 68 — CacheService.cache_response Store in Redis
    ID: RAG.cache.cacheservice.cache.response.store.in.redis
    Type: process | Category: cache | Node: CacheResponse

    Stores successful LLM response in Redis cache for future retrieval.
    This orchestrator coordinates with CacheService for response caching.
    """
    from app.core.logging import logger
    from app.services.cache import cache_service
    from app.core.llm.base import LLMResponse
    from datetime import datetime

    with rag_step_timer(68, 'RAG.cache.cacheservice.cache.response.store.in.redis', 'CacheResponse', stage="start"):
        # Extract context parameters
        llm_response = kwargs.get('llm_response') or (ctx or {}).get('llm_response')
        messages_list = kwargs.get('messages') or (ctx or {}).get('messages') or messages or []
        model = kwargs.get('model') or (ctx or {}).get('model')
        temperature = kwargs.get('temperature') or (ctx or {}).get('temperature', 0.2)
        cache_key = kwargs.get('cache_key') or (ctx or {}).get('cache_key')
        provider = kwargs.get('provider') or (ctx or {}).get('provider')
        ttl_hours = kwargs.get('ttl_hours') or (ctx or {}).get('ttl_hours', 24)

        # Initialize cache storage data
        response_cached = False
        cache_storage_key = None
        error = None

        try:
            # Validate required parameters
            if not llm_response:
                error = 'No LLM response provided for caching'
                raise ValueError(error)

            if not cache_service or not cache_service.enabled:
                error = 'Cache service not available or disabled'
                raise ValueError(error)

            # Prepare messages for caching
            if messages_list and model:
                from app.schemas.chat import Message
                formatted_messages = []
                for msg in messages_list:
                    if isinstance(msg, dict):
                        formatted_messages.append(Message(
                            role=msg.get('role', 'user'),
                            content=str(msg.get('content', ''))
                        ))
                    elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                        formatted_messages.append(msg)
                    else:
                        formatted_messages.append(Message(
                            role='user',
                            content=str(msg)
                        ))

                # Cache using CacheService
                await cache_service.cache_response(
                    messages=formatted_messages,
                    model=model,
                    response=llm_response,
                    temperature=temperature,
                    ttl_hours=ttl_hours
                )

                # Generate cache key for reference
                cache_storage_key = cache_service._generate_query_key(
                    cache_service._generate_query_hash(
                        messages=formatted_messages,
                        model=model,
                        temperature=temperature
                    )
                )

            response_cached = True

        except Exception as e:
            error = str(e)

        # Create cache storage result
        storage_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'response_cached': response_cached,
            'cache_storage_key': cache_storage_key,
            'cache_key': cache_key,
            'model': model,
            'provider': provider,
            'temperature': temperature,
            'ttl_hours': ttl_hours,
            'messages_count': len(messages_list) if messages_list else 0,
            'response_type': type(llm_response).__name__ if llm_response else None,
            'error': error
        }

        # Log cache storage result
        if error:
            log_message = f"Response caching failed: {error}"
            logger.error(log_message, extra={
                'cache_event': 'storage_failed',
                'error': error,
                'model': model,
                'provider': provider
            })
        else:
            log_message = f"Response cached successfully for {provider}/{model}"
            logger.info(log_message, extra={
                'cache_event': 'response_stored',
                'cache_storage_key': cache_storage_key[:32] + '...' if cache_storage_key else None,
                'model': model,
                'provider': provider,
                'ttl_hours': ttl_hours,
                'messages_count': len(messages_list) if messages_list else 0
            })

        # RAG step logging
        rag_step_log(
            step=68,
            step_id='RAG.cache.cacheservice.cache.response.store.in.redis',
            node_label='CacheResponse',
            category='cache',
            type='process',
            cache_event='storage_failed' if error else 'response_stored',
            response_cached=response_cached,
            cache_storage_key=cache_storage_key[:32] + '...' if cache_storage_key else None,
            model=model,
            provider=provider,
            ttl_hours=ttl_hours,
            messages_count=len(messages_list) if messages_list else 0,
            error=error,
            processing_stage="completed"
        )

        return storage_data

async def _cache_feedback_with_ttl(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper function to cache expert feedback with 1-hour TTL.
    Handles cache operation execution, error handling, and performance tracking.
    """
    import time
    import json
    from datetime import datetime

    try:
        # Extract feedback record from context
        feedback_record = ctx.get('feedback_record')
        if not feedback_record:
            return {
                'feedback_cached': False,
                'error': 'No feedback_record available for caching',
                'cache_key': None,
                'ttl_hours': 1
            }

        # Extract cache service from context
        cache_service = ctx.get('cache_service')
        if not cache_service:
            return {
                'feedback_cached': False,
                'error': 'Cache service not available',
                'cache_key': None,
                'ttl_hours': 1,
                'feedback_id': str(feedback_record.id) if hasattr(feedback_record, 'id') else None
            }

        # Prepare cache key and data
        cache_key = f"expert_feedback:{feedback_record.query_id}"

        # Build cache data structure matching ExpertFeedbackCollector format
        feedback_data = {
            'id': str(feedback_record.id),
            'feedback_type': feedback_record.feedback_type.value if hasattr(feedback_record.feedback_type, 'value') else str(feedback_record.feedback_type),
            'category': feedback_record.category.value if feedback_record.category and hasattr(feedback_record.category, 'value') else (feedback_record.category if feedback_record.category else None),
            'expert_answer': getattr(feedback_record, 'expert_answer', None),
            'confidence_score': getattr(feedback_record, 'confidence_score', 0.0),
            'timestamp': feedback_record.feedback_timestamp.isoformat() if hasattr(feedback_record, 'feedback_timestamp') else datetime.utcnow().isoformat()
        }

        # Record start time for performance tracking
        start_time = time.time()

        # Execute cache operation with 1-hour TTL (3600 seconds)
        ttl_seconds = 3600
        await cache_service.setex(cache_key, ttl_seconds, feedback_data)

        # Calculate operation time
        end_time = time.time()
        operation_time_ms = (end_time - start_time) * 1000

        # Return successful cache result
        return {
            'feedback_cached': True,
            'cache_key': cache_key,
            'ttl_hours': 1,
            'feedback_id': str(feedback_record.id),
            'feedback_type': feedback_data['feedback_type'],
            'category': feedback_data['category'],
            'cache_operation_time_ms': operation_time_ms,
            'action_taken': ctx.get('action_taken', 'feedback_cached'),
            'error': None
        }

    except Exception as e:
        # Handle cache operation errors
        error_msg = f"Feedback caching failed: {str(e)}"

        return {
            'feedback_cached': False,
            'error': error_msg,
            'cache_key': cache_key if 'cache_key' in locals() else None,
            'ttl_hours': 1,
            'feedback_id': str(feedback_record.id) if feedback_record and hasattr(feedback_record, 'id') else None,
            'feedback_type': ctx.get('feedback_type'),
            'category': ctx.get('category'),
            'cache_operation_time_ms': None
        }

async def step_125__cache_feedback(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 125 — Cache feedback 1h TTL
    ID: RAG.cache.cache.feedback.1h.ttl
    Type: process | Category: cache | Node: CacheFeedback

    Thin async orchestrator that caches expert feedback with 1-hour TTL using Redis.
    Takes input from update expert metrics (Step 124) and routes to determine action (Step 126).
    Preserves all context while adding cache operation results.

    Incoming: Update Expert Metrics (Step 124)
    Outgoing: Determine Action (Step 126)
    """
    import time
    from datetime import datetime, timezone

    with rag_step_timer(125, 'RAG.cache.cache.feedback.1h.ttl', 'CacheFeedback', stage="start"):
        ctx = ctx or {}

        rag_step_log(
            step=125,
            step_id='RAG.cache.cache.feedback.1h.ttl',
            node_label='CacheFeedback',
            category='cache',
            type='process',
            request_id=ctx.get('request_id'),
            processing_stage="started"
        )

        # Execute feedback caching
        cache_result = await _cache_feedback_with_ttl(ctx)

        # Preserve all context and add caching results
        result = ctx.copy()
        result.update(cache_result)

        # Add processing metadata
        result.update({
            'processing_stage': 'feedback_cached' if cache_result.get('feedback_cached') else 'cache_failed',
            'cache_timestamp': datetime.now(timezone.utc).isoformat()
        })

        rag_step_log(
            step=125,
            step_id='RAG.cache.cache.feedback.1h.ttl',
            node_label='CacheFeedback',
            category='cache',
            type='process',
            request_id=ctx.get('request_id'),
            feedback_cached=result.get('feedback_cached', False),
            cache_key=result.get('cache_key'),
            feedback_type=result.get('feedback_type'),
            feedback_category=result.get('category'),
            ttl_hours=result.get('ttl_hours', 1),
            cache_operation_time_ms=result.get('cache_operation_time_ms'),
            error=result.get('error'),
            processing_stage="completed"
        )

        return result
