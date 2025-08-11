"""
Query Service with Resilient LLM Integration for PratikoAI.

This service provides the main interface for processing LLM queries with built-in
retry mechanisms, provider fallback, cost tracking, and comprehensive error handling.
Integrates the existing LLM factory with the new retry mechanisms to ensure
production reliability.

Features:
- Integration with existing LLM factory and providers
- Resilient query processing with automatic retries
- Provider fallback and circuit breaker protection
- Cost tracking and budget enforcement
- Query metadata and response tracking
- Comprehensive monitoring and metrics
"""

import asyncio
import hashlib
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import get_llm_provider, LLMFactory
from app.core.llm.factory import RoutingStrategy
from app.core.llm.base import LLMResponse as CoreLLMResponse
from app.services.resilient_llm_service import (
    ResilientLLMService,
    get_llm_service,
    LLMResult
)
from app.models.query import (
    QueryRequest,
    QueryResponse,
    QueryResponseSchema,
    QueryErrorResponse,
    QueryStatus,
    QueryType,
    LLMResponse,
    QueryMetrics
)
from app.schemas.chat import Message
from app.services.llm_retry_service import (
    AllProvidersFailedError,
    CostBudgetExceededError,
    CircuitBreakerOpenError,
    MaxRetriesExceededError
)
from app.core.logging import logger
from app.core.config import settings
from app.services.cache import get_redis_client


class QueryService:
    """
    Main query service with resilient LLM integration.
    
    This service acts as the primary interface for processing LLM queries,
    integrating the existing LLM factory with the new retry mechanisms
    to provide production-grade reliability.
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize query service.
        
        Args:
            db_session: Optional database session for query tracking
        """
        self.settings = settings
        self.db_session = db_session
        self.llm_factory = LLMFactory()
        self.redis = get_redis_client()
        
        # Query tracking
        self._query_counter = 0
        self._active_queries: Dict[str, QueryResponse] = {}
        
        logger.info("Initialized QueryService with resilient LLM integration")
    
    async def process_query(
        self,
        request: QueryRequest,
        use_retry_mechanisms: bool = True
    ) -> Union[QueryResponseSchema, QueryErrorResponse]:
        """
        Process a query request with resilient handling.
        
        Args:
            request: Query request with parameters
            use_retry_mechanisms: Whether to use retry mechanisms (default: True)
            
        Returns:
            Query response or error response
        """
        query_id = self._generate_query_id()
        start_time = time.time()
        
        # Create initial query response for tracking
        query_response = QueryResponse(
            query_id=query_id,
            user_id=request.user_id,
            response="",
            status=QueryStatus.PROCESSING,
            model_used="",
            provider_used="",
            tokens_used=0,
            cost=0.0,
            processing_time=0.0,
            created_at=datetime.now(timezone.utc),
            metadata={
                "request_params": request.dict(exclude={'context'}),
                "use_retry_mechanisms": use_retry_mechanisms
            }
        )
        
        self._active_queries[query_id] = query_response
        
        logger.info(
            f"[{query_id}] Starting query processing for user {request.user_id}, "
            f"type: {request.query_type}, retry_enabled: {use_retry_mechanisms}"
        )
        
        try:
            if use_retry_mechanisms:
                # Use resilient LLM service with retry mechanisms
                result = await self._process_with_retry_mechanisms(request, query_id)
            else:
                # Use direct LLM factory (legacy mode)
                result = await self._process_with_factory(request, query_id)
            
            # Update query response with success
            processing_time = time.time() - start_time
            query_response.response = result.response
            query_response.status = QueryStatus.COMPLETED
            query_response.model_used = result.model_used
            query_response.provider_used = result.provider_used
            query_response.tokens_used = result.tokens_used
            query_response.cost = result.actual_cost
            query_response.processing_time = processing_time
            query_response.completed_at = datetime.now(timezone.utc)
            query_response.retry_count = result.retry_count
            
            # Store in cache for retrieval
            await self._cache_query_response(query_id, query_response)
            
            # Create response schema
            response_schema = QueryResponseSchema(
                query_id=query_id,
                response=result.response,
                status=QueryStatus.COMPLETED,
                model_used=result.model_used,
                provider_used=result.provider_used,
                tokens_used=result.tokens_used,
                cost=result.actual_cost,
                processing_time=processing_time,
                created_at=query_response.created_at,
                completed_at=query_response.completed_at,
                retry_count=result.retry_count,
                was_fallback=result.was_fallback
            )
            
            logger.info(
                f"[{query_id}] Query completed successfully in {processing_time:.2f}s, "
                f"provider: {result.provider_used}, cost: €{result.actual_cost:.4f}"
            )
            
            return response_schema
            
        except (AllProvidersFailedError, CircuitBreakerOpenError, MaxRetriesExceededError) as e:
            # Handle retry-specific errors
            processing_time = time.time() - start_time
            
            error_response = QueryErrorResponse(
                query_id=query_id,
                error_type=type(e).__name__,
                error_message=str(e),
                user_message=getattr(e, 'user_message', "Unable to process request. Please try again later."),
                status=QueryStatus.FAILED,
                retry_count=getattr(e, 'retry_count', 0),
                can_retry=isinstance(e, (CircuitBreakerOpenError, MaxRetriesExceededError)),
                estimated_retry_delay=60.0 if isinstance(e, CircuitBreakerOpenError) else None,
                processing_time=processing_time
            )
            
            # Update tracking
            query_response.status = QueryStatus.FAILED
            query_response.error_message = str(e)
            query_response.processing_time = processing_time
            
            logger.error(
                f"[{query_id}] Query failed with retry error: {type(e).__name__}: {e}"
            )
            
            return error_response
            
        except CostBudgetExceededError as e:
            # Handle cost budget errors
            processing_time = time.time() - start_time
            
            error_response = QueryErrorResponse(
                query_id=query_id,
                error_type="CostBudgetExceededError",
                error_message=str(e),
                user_message=e.user_message,
                status=QueryStatus.FAILED,
                retry_count=0,
                can_retry=False,
                processing_time=processing_time
            )
            
            query_response.status = QueryStatus.FAILED
            query_response.error_message = str(e)
            query_response.processing_time = processing_time
            
            logger.warning(
                f"[{query_id}] Query failed due to cost budget exceeded for user {e.user_id}"
            )
            
            return error_response
            
        except Exception as e:
            # Handle unexpected errors
            processing_time = time.time() - start_time
            
            error_response = QueryErrorResponse(
                query_id=query_id,
                error_type="UnexpectedError",
                error_message=str(e),
                user_message="An unexpected error occurred. Please try again.",
                status=QueryStatus.FAILED,
                retry_count=0,
                can_retry=True,
                processing_time=processing_time
            )
            
            query_response.status = QueryStatus.FAILED
            query_response.error_message = str(e)
            query_response.processing_time = processing_time
            
            logger.error(
                f"[{query_id}] Query failed with unexpected error: {e}",
                exc_info=True
            )
            
            return error_response
            
        finally:
            # Clean up active query tracking
            self._active_queries.pop(query_id, None)
    
    async def _process_with_retry_mechanisms(
        self,
        request: QueryRequest,
        query_id: str
    ) -> LLMResult:
        """Process query using resilient LLM service with retry mechanisms."""
        # Get resilient LLM service
        resilient_service = await get_llm_service()
        
        # Execute with retry mechanisms
        result = await resilient_service.complete(
            prompt=request.prompt,
            user_id=request.user_id,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system_prompt=request.system_prompt,
            preferred_provider=request.preferred_provider,
            allow_fallback=request.allow_fallback,
            timeout=request.timeout
        )
        
        return result
    
    async def _process_with_factory(
        self,
        request: QueryRequest,
        query_id: str
    ) -> LLMResult:
        """Process query using direct LLM factory (legacy mode)."""
        # Convert request to messages format
        messages = [Message(role="user", content=request.prompt)]
        if request.system_prompt:
            messages.insert(0, Message(role="system", content=request.system_prompt))
        
        # Get optimal provider
        provider = get_llm_provider(
            messages=messages,
            strategy=RoutingStrategy.BALANCED,
            preferred_provider=request.preferred_provider
        )
        
        start_time = time.time()
        
        # Execute query
        response = await provider.chat_completion(
            messages=messages,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens
        )
        
        processing_time = time.time() - start_time
        
        # Convert to LLMResult format
        result = LLMResult(
            response=response.content,
            provider_used=provider.provider_type.value,
            model_used=response.model,
            tokens_used=response.tokens_used or 0,
            actual_cost=response.cost_estimate or 0.0,
            processing_time=processing_time,
            was_fallback=False,
            retry_count=0,
            request_id=query_id
        )
        
        return result
    
    async def get_query_status(self, query_id: str) -> Optional[QueryResponseSchema]:
        """
        Get status of a query by ID.
        
        Args:
            query_id: Query identifier
            
        Returns:
            Query response schema or None if not found
        """
        # Check active queries first
        if query_id in self._active_queries:
            query_response = self._active_queries[query_id]
            return QueryResponseSchema(
                query_id=query_response.query_id,
                response=query_response.response,
                status=query_response.status,
                model_used=query_response.model_used,
                provider_used=query_response.provider_used,
                tokens_used=query_response.tokens_used,
                cost=query_response.cost,
                processing_time=query_response.processing_time,
                created_at=query_response.created_at,
                completed_at=query_response.completed_at,
                retry_count=query_response.retry_count
            )
        
        # Check cache
        try:
            cached_response = await self.redis.get(f"query:{query_id}")
            if cached_response:
                import json
                data = json.loads(cached_response)
                return QueryResponseSchema(**data)
        except Exception as e:
            logger.error(f"Failed to retrieve cached query {query_id}: {e}")
        
        return None
    
    async def get_user_query_metrics(
        self,
        user_id: str,
        hours: int = 24
    ) -> QueryMetrics:
        """
        Get query metrics for a user.
        
        Args:
            user_id: User identifier
            hours: Hours to look back
            
        Returns:
            Query metrics
        """
        try:
            # Get metrics from cache/Redis
            end_time = datetime.now(timezone.utc)
            start_time = end_time.replace(hour=end_time.hour - hours)
            
            # This would normally query the database or cache
            # For now, return basic metrics structure
            return QueryMetrics(
                total_queries=0,
                successful_queries=0,
                failed_queries=0,
                retry_attempts=0,
                average_processing_time=0.0,
                total_cost=0.0,
                total_tokens=0,
                provider_stats={},
                start_time=start_time,
                end_time=end_time
            )
            
        except Exception as e:
            logger.error(f"Failed to get query metrics for user {user_id}: {e}")
            # Return empty metrics on error
            return QueryMetrics(
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc)
            )
    
    async def get_service_health(self) -> Dict[str, Any]:
        """
        Get health status of the query service.
        
        Returns:
            Service health information
        """
        try:
            # Get resilient LLM service status
            from app.services.resilient_llm_service import get_llm_service_status
            llm_status = await get_llm_service_status()
            
            # Get basic service stats
            active_queries = len(self._active_queries)
            
            return {
                "service_name": "QueryService",
                "status": "healthy",
                "active_queries": active_queries,
                "llm_service_status": llm_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get service health: {e}")
            return {
                "service_name": "QueryService",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _generate_query_id(self) -> str:
        """Generate unique query ID."""
        self._query_counter += 1
        timestamp = int(time.time())
        return f"query_{timestamp}_{self._query_counter}_{uuid.uuid4().hex[:8]}"
    
    async def _cache_query_response(self, query_id: str, response: QueryResponse):
        """Cache query response for retrieval."""
        try:
            # Convert to dict for JSON serialization
            response_dict = asdict(response)
            # Handle datetime serialization
            for key, value in response_dict.items():
                if isinstance(value, datetime):
                    response_dict[key] = value.isoformat()
            
            import json
            await self.redis.setex(
                f"query:{query_id}",
                3600,  # 1 hour TTL
                json.dumps(response_dict)
            )
        except Exception as e:
            logger.error(f"Failed to cache query response {query_id}: {e}")


# Singleton instance management
_query_service: Optional[QueryService] = None

async def get_query_service(db_session: Optional[AsyncSession] = None) -> QueryService:
    """
    Get singleton query service instance.
    
    Args:
        db_session: Optional database session
        
    Returns:
        Query service instance
    """
    global _query_service
    
    if _query_service is None:
        _query_service = QueryService(db_session)
    
    return _query_service

async def get_query_service_health() -> Dict[str, Any]:
    """
    Get query service health status.
    
    Returns:
        Service health information
    """
    service = await get_query_service()
    return await service.get_service_health()


# Export main components
__all__ = [
    'QueryService',
    'get_query_service',
    'get_query_service_health'
]