"""DEV-395: Redis-based API Rate Limiting Middleware.

Provides per-endpoint, per-user rate limiting via Redis INCR + EXPIRE.
Falls open (allows requests) when Redis is unavailable.

Rate limit headers returned on every response:
    X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After (on 429).
"""

from dataclasses import dataclass, field
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.logging import logger

try:
    import redis.asyncio as aioredis  # type: ignore[import-untyped]

    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None  # type: ignore[assignment]
    REDIS_AVAILABLE = False


# ------------------------------------------------------------------
# Default per-endpoint limits (requests / window_seconds)
# ------------------------------------------------------------------
DEFAULT_ENDPOINT_LIMITS: dict[str, dict[str, int]] = {
    "/api/v1/auth/login": {"limit": 10, "window": 60},
    "/api/v1/auth/register": {"limit": 10, "window": 60},
    "/api/v1/chat": {"limit": 30, "window": 60},
    "/api/v1/search": {"limit": 60, "window": 60},
    "/api/v1/documents/upload": {"limit": 10, "window": 60},
}

_KEY_PREFIX = "ratelimit"


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    default_limit: int = 100
    default_window: int = 60  # seconds
    endpoint_limits: dict[str, dict[str, int]] = field(default_factory=lambda: dict(DEFAULT_ENDPOINT_LIMITS))

    def get_limit(self, path: str) -> tuple[int, int]:
        """Return ``(limit, window)`` for the given endpoint path.

        Falls back to ``default_limit`` / ``default_window`` when
        no explicit config exists.
        """
        # Exact match first
        if path in self.endpoint_limits:
            ep = self.endpoint_limits[path]
            return ep.get("limit", self.default_limit), ep.get("window", self.default_window)

        # Prefix match (e.g. /api/v1/auth covers /api/v1/auth/login)
        for prefix, ep in self.endpoint_limits.items():
            if path.startswith(prefix):
                return ep.get("limit", self.default_limit), ep.get("window", self.default_window)

        return self.default_limit, self.default_window


# ------------------------------------------------------------------
# Core rate-limiter
# ------------------------------------------------------------------
class RateLimiter:
    """Rate limiter backed by Redis INCR/EXPIRE."""

    def __init__(
        self,
        config: RateLimitConfig | None = None,
        redis_url: str | None = None,
    ) -> None:
        self.config = config or RateLimitConfig()
        self._redis_url = redis_url
        self._redis: Any = None

    async def _get_redis(self) -> Any:
        """Lazy Redis connection."""
        if not REDIS_AVAILABLE:
            return None
        if self._redis is None and self._redis_url:
            try:
                self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            except Exception as e:
                logger.critical("rate_limit_redis_connect_failed", error=str(e))
                return None
        return self._redis

    def _build_key(self, identifier: str, endpoint: str) -> str:
        """Build the Redis key: ``ratelimit:{identifier}:{simplified_path}``."""
        simplified = endpoint.strip("/").replace("/", ":")
        return f"{_KEY_PREFIX}:{identifier}:{simplified}"

    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
    ) -> tuple[bool, int, int]:
        """Check (and increment) the rate limit counter.

        Args:
            identifier: ``"user:<id>"`` or ``"ip:<addr>"``.
            endpoint: Request path.

        Returns:
            ``(allowed, remaining, reset_seconds)``
        """
        limit, window = self.config.get_limit(endpoint)

        # limit=0 means disabled for this endpoint
        if limit == 0:
            return True, 0, 0

        r = await self._get_redis()
        if r is None:
            # Fail open — allow request when Redis is down
            logger.critical("rate_limit_redis_unavailable", action="fail_open", identifier=identifier)
            return True, limit, window

        key = self._build_key(identifier, endpoint)

        try:
            current = await r.incr(key)

            # Set TTL only on first request in the window
            if current == 1:
                await r.expire(key, window)

            ttl = await r.ttl(key)
            reset = max(ttl, 0)

            if current > limit:
                remaining = 0
                return False, remaining, reset

            remaining = max(limit - current, 0)
            return True, remaining, reset

        except Exception as e:
            logger.critical("rate_limit_redis_error", error=str(e), action="fail_open")
            return True, limit, window


# ------------------------------------------------------------------
# Starlette / FastAPI middleware
# ------------------------------------------------------------------
class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that enforces rate limits.

    Extracts the user identifier from the authenticated user or falls
    back to the client IP from ``X-Forwarded-For`` (rightmost trusted).
    """

    def __init__(self, app: Any, *, limiter: RateLimiter) -> None:
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        identifier = self._extract_identifier(request)
        endpoint = request.url.path

        allowed, remaining, reset = await self.limiter.check_rate_limit(identifier, endpoint)

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier,
                endpoint=endpoint,
                reset=reset,
            )
            return JSONResponse(
                status_code=429,
                content={"detail": f"Troppe richieste. Riprova tra {reset} secondi."},
                headers={
                    "Retry-After": str(reset),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                },
            )

        response = await call_next(request)

        # Inject rate-limit headers
        limit, _ = self.limiter.config.get_limit(endpoint)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)
        return response

    @staticmethod
    def _extract_identifier(request: Request) -> str:
        """Extract user id or IP for rate limit key."""
        # Authenticated user
        user = getattr(request.state, "user", None) if hasattr(request, "state") else None
        if user and hasattr(user, "id"):
            return f"user:{user.id}"

        # Fallback to IP — rightmost trusted proxy IP
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            ip = forwarded.split(",")[-1].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        return f"ip:{ip}"
