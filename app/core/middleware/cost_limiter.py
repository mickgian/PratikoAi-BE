"""Cost-based rate limiting middleware (DEV-257).

This middleware implements usage-based billing with rolling cost windows
(5h + 7d) and fallback to legacy quota system.
"""

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Optional

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import logger
from app.models.session import Session
from app.services.database import database_service
from app.services.usage_tracker import usage_tracker
from app.utils.auth import verify_token


class CostLimiterMiddleware(BaseHTTPMiddleware):
    """Middleware for cost-based rate limiting with rolling windows."""

    def __init__(self, app: ASGIApp):
        """Initialize the middleware."""
        super().__init__(app)

        self._protected_endpoints = {
            "/api/v1/chat",
            "/api/v1/chat/stream",
            "/api/v1/chatbot/chat",
            "/api/v1/chatbot/chat/stream",
            "/api/v1/messages",
        }

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
        """Process the request and apply rolling window cost limiting."""
        if not self._should_check_limits(request.url.path):
            return await call_next(request)

        user_id = await self._get_user_id(request)
        if not user_id:
            return await call_next(request)

        try:
            # DEV-257: Try rolling window check first
            blocked_response = await self._check_rolling_windows(user_id, request)
            if blocked_response is not None:
                return blocked_response
        except Exception as e:
            # Fallback to legacy quota system on error
            logger.warning(
                "rolling_window_check_failed_using_legacy",
                user_id=user_id,
                error=str(e),
            )
            try:
                is_allowed, reason = await usage_tracker.check_quota_limits(user_id)
                if not is_allowed:
                    return await self._build_legacy_429(user_id, reason)
            except Exception as legacy_err:
                logger.error("legacy_quota_check_also_failed", error=str(legacy_err))

        # Process the request
        try:
            start_time = time.time()
            response = await call_next(request)
            response_time_ms = int((time.time() - start_time) * 1000)

            # Track API usage (non-LLM requests)
            if request.url.path not in ["/api/v1/chat", "/api/v1/chat/stream"]:
                try:
                    session_id = await self._get_session_id(request)
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
            return await call_next(request)

    async def _check_rolling_windows(self, user_id: str, request: Request) -> JSONResponse | None:
        """Check rolling window limits. Returns 429 response if blocked, None if allowed."""
        from app.services.billing_plan_service import billing_plan_service
        from app.services.rolling_window_service import rolling_window_service

        # DEV-257: Honor bypass header for admin/super_user
        if request.headers.get("X-Cost-Limit-Bypass") == "true":
            role = await self._get_user_role(int(user_id))
            if role in ("admin", "super_user"):
                logger.info("cost_limit_bypassed_by_admin", user_id=user_id, role=role)
                return None

        user_id_int = int(user_id)
        plan = await billing_plan_service.get_user_plan(user_id_int)
        result = await rolling_window_service.check_limits(user_id_int, plan.slug)

        if result.allowed:
            return None

        logger.warning(
            "rolling_window_limit_exceeded",
            user_id=user_id,
            window_type=result.window_type,
            current_cost=result.current_cost_eur,
            limit_cost=result.limit_cost_eur,
            endpoint=request.url.path,
        )

        # Calculate reset time
        reset_in_minutes = None
        if result.reset_at:
            reset_at = result.reset_at
            if reset_at.tzinfo is None:
                reset_at = reset_at.replace(tzinfo=UTC)
            delta = (reset_at - datetime.now(UTC)).total_seconds()
            reset_in_minutes = max(0, int(delta / 60))

        # DEV-257: Check if user can bypass (admin/super_user)
        user_role = await self._get_user_role(int(user_id))
        can_bypass = user_role in ("admin", "super_user")

        return JSONResponse(
            status_code=429,
            content={
                "error_code": "USAGE_LIMIT_EXCEEDED",
                "can_bypass": can_bypass,
                "message_it": "Hai raggiunto il limite di utilizzo per questa finestra",
                "limit_info": {
                    "window_type": result.window_type,
                    "cost_consumed_eur": result.current_cost_eur,
                    "cost_limit_eur": result.limit_cost_eur,
                    "reset_at": result.reset_at.isoformat() if result.reset_at else None,
                    "reset_in_minutes": reset_in_minutes,
                },
                "options": {
                    "wait": {
                        "description_it": "Attendi il reset della finestra",
                        "reset_in_minutes": reset_in_minutes,
                    },
                    "upgrade": {
                        "description_it": "Passa a un piano superiore per limiti più alti",
                        "url": "/account/piano",
                    },
                    "recharge": {
                        "description_it": "Ricarica crediti per continuare",
                        "url": "/account/crediti",
                    },
                    "use_credits": {
                        "description_it": "Abilita consumo crediti automatico",
                        "available": result.credits_available,
                        "balance_eur": result.credit_balance,
                    },
                },
            },
        )

    async def _get_user_role(self, user_id: int) -> str:
        """Get user role from database."""
        from app.models.user import User

        async with database_service.get_db() as db:
            result = await db.execute(select(User.role).where(User.id == user_id))
            return result.scalar_one_or_none() or "regular_user"

    async def _build_legacy_429(self, user_id: str, reason: str) -> JSONResponse:
        """Build 429 response using legacy quota system."""
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
                "X-RateLimit-Remaining": str(max(0, quota.daily_requests_limit - quota.current_daily_requests)),
                "X-RateLimit-Reset": str(int(quota.daily_reset_at.timestamp())),
                "X-Cost-Daily-Limit": str(quota.daily_cost_limit_eur),
                "X-Cost-Daily-Current": str(quota.current_daily_cost_eur),
                "X-Cost-Monthly-Limit": str(quota.monthly_cost_limit_eur),
                "X-Cost-Monthly-Current": str(quota.current_monthly_cost_eur),
            },
        )

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

        # Check protected endpoints (exact match to avoid /chat matching /chatbot)
        return path in self._protected_endpoints

    async def _get_user_id(self, request: Request) -> str | None:
        """Get user ID from request state or Authorization header.

        Checks request.state first (if set by upstream middleware), then falls
        back to extracting the user from the Bearer token via the same auth
        utilities used by endpoint-level ``Depends(get_current_session)``.

        Args:
            request: The request object

        Returns:
            Optional[str]: User ID if available
        """
        # Try to get from request state (set by auth middleware)
        if hasattr(request.state, "user_id"):
            return request.state.user_id

        # Try to get from session on request state
        if hasattr(request.state, "session") and isinstance(request.state.session, Session):
            return request.state.session.user_id

        # Fallback: extract from Authorization header
        try:
            auth_header = request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer "):
                return None
            token = auth_header[7:]  # Strip "Bearer "
            session_id = verify_token(token)
            if not session_id:
                return None
            session = await database_service.get_session(session_id)
            if session:
                return str(session.user_id)
        except Exception:
            pass  # Fail open — endpoint-level auth will handle rejection

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
