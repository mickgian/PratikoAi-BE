"""Performance monitoring middleware for request tracking and optimization."""

import asyncio
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import logger
from app.core.performance import database_optimizer, performance_monitor, response_compressor


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware for performance monitoring and optimization."""

    def __init__(self, app, enabled: bool = True):
        """Initialize performance middleware.

        Args:
            app: FastAPI application
            enabled: Whether performance monitoring is enabled
        """
        super().__init__(app)
        self.enabled = enabled

        # Paths to monitor for database performance
        self.db_monitored_paths = {
            "/api/v1/italian/",
            "/api/v1/payments/",
            "/api/v1/search/",
            "/api/v1/analytics/",
            "/api/v1/auth/",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through performance middleware.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            HTTP response with performance optimizations
        """
        if not self.enabled:
            return await call_next(request)

        start_time = time.time()
        request_size = self._get_request_size(request)

        try:
            # Track database queries for monitored paths
            db_query_start = None
            if self._should_monitor_db_performance(request):
                db_query_start = time.time()

            # Process request
            response = await call_next(request)

            # Calculate timing
            response_time = time.time() - start_time
            response_size = self._get_response_size(response)

            # Record database performance if monitored
            if db_query_start:
                db_query_time = time.time() - db_query_start
                await self._record_database_performance(request, db_query_time)

            # Record request metrics
            await self._record_request_performance(request, response, response_time, request_size, response_size)

            # Apply performance optimizations
            response = await self._optimize_response(request, response)

            return response

        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            await self._record_error_performance(request, e, response_time)
            raise

    def _get_request_size(self, request: Request) -> int:
        """Get request size in bytes."""
        try:
            content_length = request.headers.get("content-length")
            if content_length:
                return int(content_length)

            # Estimate size from URL and headers
            url_size = len(str(request.url))
            headers_size = sum(len(k) + len(v) for k, v in request.headers.items())
            return url_size + headers_size

        except Exception:
            return 0

    def _get_response_size(self, response: Response) -> int:
        """Get response size in bytes."""
        try:
            if hasattr(response, "body") and response.body:
                return len(response.body)

            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)

            return 0

        except Exception:
            return 0

    def _should_monitor_db_performance(self, request: Request) -> bool:
        """Check if request should be monitored for database performance."""
        path = str(request.url.path)

        return any(path.startswith(monitored_path) for monitored_path in self.db_monitored_paths)

    async def _record_database_performance(self, request: Request, query_time: float) -> None:
        """Record database performance metrics."""
        try:
            # Simulate database query monitoring
            # In a real implementation, this would hook into SQLAlchemy events
            query_hash = await database_optimizer.monitor_query(
                query=f"SIMULATED_QUERY_{request.method}_{request.url.path}",
                parameters=None,
                execution_time=query_time,
                rows_affected=1,
            )

            # Record database query counter
            performance_monitor.record_db_query()

            logger.debug(
                "database_performance_recorded",
                path=str(request.url.path),
                query_time=round(query_time * 1000, 2),  # ms
                query_hash=query_hash[:8] + "..." if query_hash else "none",
            )

        except Exception as e:
            logger.error("database_performance_recording_failed", path=str(request.url.path), error=str(e))

    async def _record_request_performance(
        self, request: Request, response: Response, response_time: float, request_size: int, response_size: int
    ) -> None:
        """Record request performance metrics."""
        try:
            # Extract user info if available
            user_id = None
            session_id = None

            # Try to get user info from request state (set by auth middleware)
            if hasattr(request.state, "user_id"):
                user_id = request.state.user_id
            if hasattr(request.state, "session_id"):
                session_id = request.state.session_id

            # Record metrics
            await performance_monitor.record_request_metrics(
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                response_time=response_time,
                request_size=request_size,
                response_size=response_size,
                user_id=user_id,
                session_id=session_id,
                error_message=None if response.status_code < 400 else f"HTTP {response.status_code}",
            )

            # Log slow requests
            if response_time > 2.0:  # 2 seconds threshold
                logger.warning(
                    "slow_request_detected",
                    method=request.method,
                    path=str(request.url.path),
                    response_time=round(response_time, 3),
                    status_code=response.status_code,
                    user_id=user_id,
                )

        except Exception as e:
            logger.error(
                "request_performance_recording_failed", method=request.method, path=str(request.url.path), error=str(e)
            )

    async def _record_error_performance(self, request: Request, error: Exception, response_time: float) -> None:
        """Record error performance metrics."""
        try:
            await performance_monitor.record_request_metrics(
                method=request.method,
                path=str(request.url.path),
                status_code=500,
                response_time=response_time,
                request_size=self._get_request_size(request),
                response_size=0,
                error_message=str(error),
            )

        except Exception as e:
            logger.error(
                "error_performance_recording_failed",
                method=request.method,
                path=str(request.url.path),
                original_error=str(error),
                recording_error=str(e),
            )

    async def _optimize_response(self, request: Request, response: Response) -> Response:
        """Apply response optimizations."""
        try:
            # Only optimize successful responses
            if response.status_code >= 400:
                return response

            # Check if response should be compressed
            if hasattr(response, "body") and response.body:
                content_type = response.headers.get("content-type", "")
                accept_encoding = request.headers.get("accept-encoding", "")

                should_compress, compression_type = response_compressor.should_compress(
                    response.body, content_type, accept_encoding
                )

                if should_compress:
                    compressed_content, compression_time, compression_ratio = response_compressor.compress_content(
                        response.body, compression_type
                    )

                    # Update response with compressed content
                    response.headers["content-encoding"] = compression_type.value
                    response.headers["content-length"] = str(len(compressed_content))
                    response.headers["vary"] = "Accept-Encoding"

                    # Create new response with compressed content
                    from fastapi import Response as FastAPIResponse

                    optimized_response = FastAPIResponse(
                        content=compressed_content,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type,
                    )

                    logger.debug(
                        "response_compressed",
                        path=str(request.url.path),
                        original_size=len(response.body),
                        compressed_size=len(compressed_content),
                        compression_ratio=round(compression_ratio, 3),
                        compression_type=compression_type.value,
                    )

                    return optimized_response

            # Add performance headers
            response.headers["x-response-time"] = f"{time.time() * 1000:.2f}ms"

            return response

        except Exception as e:
            logger.error("response_optimization_failed", path=str(request.url.path), error=str(e))
            return response


class DatabaseQueryMiddleware:
    """Middleware for database query optimization and monitoring."""

    def __init__(self, enabled: bool = True):
        """Initialize database query middleware.

        Args:
            enabled: Whether database monitoring is enabled
        """
        self.enabled = enabled

    async def __call__(self, query: str, parameters: dict = None):
        """Monitor and optimize database queries.

        Args:
            query: SQL query
            parameters: Query parameters

        Returns:
            Query execution context
        """
        if not self.enabled:
            return {"query": query, "parameters": parameters}

        start_time = time.time()

        try:
            # Optimize query before execution
            optimized_query, execution_hints = await database_optimizer.optimize_query_execution(query, parameters)

            # Create execution context
            context = {
                "original_query": query,
                "optimized_query": optimized_query,
                "parameters": parameters,
                "execution_hints": execution_hints,
                "start_time": start_time,
            }

            return context

        except Exception as e:
            logger.error(
                "database_query_middleware_failed",
                query=query[:100] + "..." if len(query) > 100 else query,
                error=str(e),
            )
            return {"query": query, "parameters": parameters}

    async def record_execution(
        self, context: dict, execution_time: float, rows_affected: int = 0, error: Exception = None
    ) -> None:
        """Record query execution results.

        Args:
            context: Query execution context
            execution_time: Query execution time
            rows_affected: Number of rows affected
            error: Exception if query failed
        """
        try:
            if not self.enabled:
                return

            # Record query performance
            await database_optimizer.monitor_query(
                query=context.get("optimized_query", context.get("original_query", "")),
                parameters=context.get("parameters"),
                execution_time=execution_time,
                rows_affected=rows_affected,
            )

            # Log slow queries
            if execution_time > database_optimizer.slow_query_threshold:
                logger.warning(
                    "slow_database_query",
                    execution_time=round(execution_time, 3),
                    rows_affected=rows_affected,
                    query_preview=context.get("optimized_query", "")[:200] + "...",
                    optimization_applied=context.get("execution_hints", {}).get("optimization_applied", False),
                )

        except Exception as e:
            logger.error("query_execution_recording_failed", execution_time=execution_time, error=str(e))


class CacheMiddleware:
    """Middleware for cache performance monitoring."""

    def __init__(self, enabled: bool = True):
        """Initialize cache middleware.

        Args:
            enabled: Whether cache monitoring is enabled
        """
        self.enabled = enabled

    def record_cache_hit(self, cache_key: str, cache_type: str = "redis") -> None:
        """Record a cache hit.

        Args:
            cache_key: Cache key that was hit
            cache_type: Type of cache (redis, memory, etc.)
        """
        if not self.enabled:
            return

        try:
            performance_monitor.record_cache_hit()

            logger.debug(
                "cache_hit_recorded",
                cache_key=cache_key[:50] + "..." if len(cache_key) > 50 else cache_key,
                cache_type=cache_type,
            )

        except Exception as e:
            logger.error("cache_hit_recording_failed", cache_key=cache_key, error=str(e))

    def record_cache_miss(self, cache_key: str, cache_type: str = "redis") -> None:
        """Record a cache miss.

        Args:
            cache_key: Cache key that was missed
            cache_type: Type of cache (redis, memory, etc.)
        """
        if not self.enabled:
            return

        try:
            performance_monitor.record_cache_miss()

            logger.debug(
                "cache_miss_recorded",
                cache_key=cache_key[:50] + "..." if len(cache_key) > 50 else cache_key,
                cache_type=cache_type,
            )

        except Exception as e:
            logger.error("cache_miss_recording_failed", cache_key=cache_key, error=str(e))


# Global instances
database_query_middleware = DatabaseQueryMiddleware()
cache_middleware = CacheMiddleware()
