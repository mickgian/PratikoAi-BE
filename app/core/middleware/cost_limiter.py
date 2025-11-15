"""Cost-based rate limiting middleware.

This middleware implements intelligent rate limiting based on user costs
and quotas to maintain the €2/user/month target.
"""

import time
from collections.abc import Callable
from typing import Optional

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import logger
from app.models.session import Session
from app.services.usage_tracker import usage_tracker


class CostLimiterMiddleware(BaseHTTPMiddleware):
    """Middleware for cost-based rate limiting."""

    def __init__(self, app: ASGIApp):
        """Initialize the middleware.

        Args:
            app: The ASGI application
        """
        super().__init__(app)

        # Endpoints that should be checked for cost limits
        self._protected_endpoints = {
            "/api/v1/chat",
            "/api/v1/chat/stream",
            "/api/v1/messages",
        }

        # Endpoints exempt from cost limiting
        self._exempt_endpoints = {
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/privacy/consent",
            "/api/v1/privacy/data-subject-request",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and apply cost-based rate limiting.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
            Response: The response from the handler or an error response
        """
        # Skip non-protected endpoints
        if not self._should_check_limits(request.url.path):
            return await call_next(request)

        # Get user from request state (set by auth middleware)
        user_id = await self._get_user_id(request)
        if not user_id:
            # No authenticated user, let regular auth handle it
            return await call_next(request)

        # Check quota limits
        try:
            is_allowed, reason = await usage_tracker.check_quota_limits(user_id)

            if not is_allowed:
                logger.warning("cost_limit_exceeded", user_id=user_id, reason=reason, endpoint=request.url.path)

                # Get user quota for detailed response
                quota = await usage_tracker.get_user_quota(user_id)

                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": reason,
                        "error_code": "COST_LIMIT_EXCEEDED",
                        "quota_info": {
                            "daily_cost": {
                                "current": quota.current_daily_cost_eur,
                                "limit": quota.daily_cost_limit_eur,
                            },
                            "monthly_cost": {
                                "current": quota.current_monthly_cost_eur,
                                "limit": quota.monthly_cost_limit_eur,
                            },
                            "daily_requests": {
                                "current": quota.current_daily_requests,
                                "limit": quota.daily_requests_limit,
                            },
                        },
                    },
                    headers={
                        "X-RateLimit-Limit": str(quota.daily_requests_limit),
                        "X-RateLimit-Remaining": str(
                            max(0, quota.daily_requests_limit - quota.current_daily_requests)
                        ),
                        "X-RateLimit-Reset": str(int(quota.daily_reset_at.timestamp())),
                        "X-Cost-Daily-Limit": str(quota.daily_cost_limit_eur),
                        "X-Cost-Daily-Current": str(quota.current_daily_cost_eur),
                        "X-Cost-Monthly-Limit": str(quota.monthly_cost_limit_eur),
                        "X-Cost-Monthly-Current": str(quota.current_monthly_cost_eur),
                    },
                )

            # Process the request
            start_time = time.time()
            response = await call_next(request)
            response_time_ms = int((time.time() - start_time) * 1000)

            # Track API usage (non-LLM requests)
            if request.url.path not in ["/api/v1/chat", "/api/v1/chat/stream"]:
                try:
                    # Get session ID if available
                    session_id = await self._get_session_id(request)

                    # Estimate request and response sizes
                    request_size = int(request.headers.get("content-length", 0))
                    response_size = int(response.headers.get("content-length", 0))

                    await usage_tracker.track_api_request(
                        user_id=user_id,
                        session_id=session_id or "unknown",
                        endpoint=request.url.path,
                        method=request.method,
                        response_time_ms=response_time_ms,
                        request_size=request_size,
                        response_size=response_size,
                        error_occurred=response.status_code >= 400,
                        error_type=f"HTTP_{response.status_code}" if response.status_code >= 400 else None,
                    )
                except Exception as e:
                    logger.error("api_usage_tracking_failed", error=str(e), endpoint=request.url.path)

            # Add cost information to response headers
            if response.status_code < 400:
                try:
                    quota = await usage_tracker.get_user_quota(user_id)
                    response.headers["X-Cost-Daily-Current"] = str(quota.current_daily_cost_eur)
                    response.headers["X-Cost-Monthly-Current"] = str(quota.current_monthly_cost_eur)
                    response.headers["X-RateLimit-Remaining"] = str(
                        max(0, quota.daily_requests_limit - quota.current_daily_requests)
                    )
                except Exception as e:
                    logger.error("cost_header_update_failed", error=str(e))

            return response

        except Exception as e:
            logger.error("cost_limiter_error", error=str(e), user_id=user_id, endpoint=request.url.path, exc_info=True)
            # On error, allow the request to proceed
            return await call_next(request)

    def _should_check_limits(self, path: str) -> bool:
        """Check if the endpoint should be rate limited.

        Args:
            path: The request path

        Returns:
            bool: True if limits should be checked
        """
        # Check if explicitly exempt
        if path in self._exempt_endpoints:
            return False

        # Check if it's an API endpoint
        if not path.startswith("/api/"):
            return False

        # Check protected endpoints
        return any(path.startswith(endpoint) for endpoint in self._protected_endpoints)

    async def _get_user_id(self, request: Request) -> str | None:
        """Get user ID from request state.

        Args:
            request: The request object

        Returns:
            Optional[str]: User ID if available
        """
        # Try to get from request state (set by auth middleware)
        if hasattr(request.state, "user_id"):
            return request.state.user_id

        # Try to get from session
        if hasattr(request.state, "session") and isinstance(request.state.session, Session):
            return request.state.session.user_id

        return None

    async def _get_session_id(self, request: Request) -> str | None:
        """Get session ID from request state.

        Args:
            request: The request object

        Returns:
            Optional[str]: Session ID if available
        """
        if hasattr(request.state, "session") and isinstance(request.state.session, Session):
            return request.state.session.id

        return None


class CostOptimizationMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic cost optimization."""

    def __init__(self, app: ASGIApp):
        """Initialize the middleware.

        Args:
            app: The ASGI application
        """
        super().__init__(app)

        # Track request patterns for optimization
        self._request_patterns = {}
        self._pattern_check_interval = 300  # 5 minutes
        self._last_pattern_check = time.time()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and apply cost optimizations.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
            Response: The response from the handler
        """
        # Only optimize for chat endpoints
        if request.url.path not in ["/api/v1/chat", "/api/v1/chat/stream"]:
            return await call_next(request)

        # Get user ID
        user_id = await self._get_user_id(request)
        if not user_id:
            return await call_next(request)

        # Check if we should generate optimization suggestions
        current_time = time.time()
        if current_time - self._last_pattern_check > self._pattern_check_interval:
            self._last_pattern_check = current_time
            try:
                # Generate suggestions in background
                await usage_tracker.generate_optimization_suggestions(user_id)
            except Exception as e:
                logger.error("optimization_suggestion_generation_failed", error=str(e), user_id=user_id)

        # Add optimization hints to request state
        try:
            # Get user's recent metrics
            metrics = await usage_tracker.get_user_metrics(user_id)

            # Add optimization hints
            if hasattr(request.state, "optimization_hints"):
                request.state.optimization_hints = {}
            else:
                request.state.optimization_hints = {}

            # Suggest caching if low hit rate
            if metrics.cache_hit_rate < 0.5:
                request.state.optimization_hints["improve_caching"] = True

            # Suggest model optimization if high cost
            if metrics.total_cost_eur > 1.5:  # 75% of monthly target
                request.state.optimization_hints["use_cheaper_models"] = True

        except Exception as e:
            logger.error("optimization_hint_generation_failed", error=str(e), user_id=user_id)

        return await call_next(request)

    async def _get_user_id(self, request: Request) -> str | None:
        """Get user ID from request state.

        Args:
            request: The request object

        Returns:
            Optional[str]: User ID if available
        """
        if hasattr(request.state, "user_id"):
            return request.state.user_id

        if hasattr(request.state, "session") and isinstance(request.state.session, Session):
            return request.state.session.user_id

        return None
