"""DEV-395: Tests for API Rate Limiting middleware.

Tests cover:
- RateLimitConfig (exact match, prefix match, default fallback)
- RateLimiter core logic (under/over limit, fail-open, limit=0, Redis errors)
- RateLimitMiddleware integration (dispatch, headers, 429, identifier extraction)
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.middleware.rate_limit import (
    RateLimitConfig,
    RateLimiter,
    RateLimitMiddleware,
)


# ------------------------------------------------------------------ #
# RateLimitConfig
# ------------------------------------------------------------------ #
class TestRateLimitConfig:
    """Test rate limit configuration."""

    def test_default_limits(self) -> None:
        config = RateLimitConfig()
        assert config.default_limit == 100
        assert config.default_window == 60

    def test_exact_match(self) -> None:
        config = RateLimitConfig(
            endpoint_limits={
                "/api/v1/auth/login": {"limit": 10, "window": 60},
                "/api/v1/chat": {"limit": 30, "window": 60},
            }
        )
        assert config.get_limit("/api/v1/auth/login") == (10, 60)
        assert config.get_limit("/api/v1/chat") == (30, 60)

    def test_prefix_match(self) -> None:
        """Prefix match covers sub-paths."""
        config = RateLimitConfig(endpoint_limits={"/api/v1/auth": {"limit": 10, "window": 60}})
        # /api/v1/auth/login starts with /api/v1/auth
        assert config.get_limit("/api/v1/auth/login") == (10, 60)
        assert config.get_limit("/api/v1/auth/register") == (10, 60)

    def test_default_fallback(self) -> None:
        config = RateLimitConfig()
        assert config.get_limit("/api/v1/unknown") == (100, 60)

    def test_limit_zero(self) -> None:
        config = RateLimitConfig(endpoint_limits={"/api/v1/health": {"limit": 0, "window": 60}})
        limit, window = config.get_limit("/api/v1/health")
        assert limit == 0

    def test_custom_defaults(self) -> None:
        config = RateLimitConfig(default_limit=200, default_window=120)
        assert config.get_limit("/unknown") == (200, 120)


# ------------------------------------------------------------------ #
# RateLimiter core
# ------------------------------------------------------------------ #
class TestRateLimiter:
    """Test RateLimiter INCR/EXPIRE logic."""

    def setup_method(self) -> None:
        self.config = RateLimitConfig()
        self.limiter = RateLimiter(config=self.config)

    @pytest.mark.asyncio
    async def test_first_request_allowed(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 1
        mock_redis.ttl.return_value = 60

        with patch.object(self.limiter, "_get_redis", return_value=mock_redis):
            allowed, remaining, reset = await self.limiter.check_rate_limit(
                identifier="user:1", endpoint="/api/v1/health"
            )

        assert allowed is True
        assert remaining == 99
        # First request should set expire
        mock_redis.expire.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_second_request_no_expire(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 2
        mock_redis.ttl.return_value = 55

        with patch.object(self.limiter, "_get_redis", return_value=mock_redis):
            allowed, remaining, reset = await self.limiter.check_rate_limit(
                identifier="user:1", endpoint="/api/v1/health"
            )

        assert allowed is True
        assert remaining == 98
        # Second request should NOT set expire
        mock_redis.expire.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_over_limit_rejected(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 101
        mock_redis.ttl.return_value = 30

        with patch.object(self.limiter, "_get_redis", return_value=mock_redis):
            allowed, remaining, reset = await self.limiter.check_rate_limit(
                identifier="user:1", endpoint="/api/v1/health"
            )

        assert allowed is False
        assert remaining == 0
        assert reset == 30

    @pytest.mark.asyncio
    async def test_redis_unavailable_fail_open(self) -> None:
        with patch.object(self.limiter, "_get_redis", return_value=None):
            allowed, remaining, reset = await self.limiter.check_rate_limit(
                identifier="user:1", endpoint="/api/v1/chat"
            )

        assert allowed is True

    @pytest.mark.asyncio
    async def test_limit_zero_disables_check(self) -> None:
        config = RateLimitConfig(endpoint_limits={"/api/v1/health": {"limit": 0, "window": 60}})
        limiter = RateLimiter(config=config)

        # Should not even touch Redis
        allowed, remaining, reset = await limiter.check_rate_limit(identifier="user:1", endpoint="/api/v1/health")
        assert allowed is True
        assert remaining == 0
        assert reset == 0

    @pytest.mark.asyncio
    async def test_negative_remaining_clamped(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 200
        mock_redis.ttl.return_value = 20

        with patch.object(self.limiter, "_get_redis", return_value=mock_redis):
            allowed, remaining, reset = await self.limiter.check_rate_limit(
                identifier="user:1", endpoint="/api/v1/health"
            )

        assert remaining == 0  # Clamped

    @pytest.mark.asyncio
    async def test_redis_error_fail_open(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.incr.side_effect = ConnectionError("Redis down")

        with patch.object(self.limiter, "_get_redis", return_value=mock_redis):
            allowed, remaining, reset = await self.limiter.check_rate_limit(
                identifier="user:1", endpoint="/api/v1/health"
            )

        assert allowed is True

    @pytest.mark.asyncio
    async def test_negative_ttl_clamped_to_zero(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 50
        mock_redis.ttl.return_value = -1

        with patch.object(self.limiter, "_get_redis", return_value=mock_redis):
            allowed, remaining, reset = await self.limiter.check_rate_limit(
                identifier="user:1", endpoint="/api/v1/health"
            )

        assert reset == 0


# ------------------------------------------------------------------ #
# RateLimiter internals
# ------------------------------------------------------------------ #
class TestRateLimiterInternals:
    """Test _build_key and _get_redis."""

    def test_build_key_format(self) -> None:
        limiter = RateLimiter(config=RateLimitConfig())
        key = limiter._build_key("user:42", "/api/v1/chat")
        assert key == "ratelimit:user:42:api:v1:chat"

    def test_build_key_ip(self) -> None:
        limiter = RateLimiter(config=RateLimitConfig())
        key = limiter._build_key("ip:10.0.0.1", "/api/v1/search")
        assert key == "ratelimit:ip:10.0.0.1:api:v1:search"

    @pytest.mark.asyncio
    async def test_get_redis_unavailable(self) -> None:
        """REDIS_AVAILABLE=False returns None."""
        limiter = RateLimiter(config=RateLimitConfig(), redis_url="redis://fake")
        with patch("app.middleware.rate_limit.REDIS_AVAILABLE", False):
            result = await limiter._get_redis()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_redis_no_url(self) -> None:
        """No redis_url configured returns None."""
        limiter = RateLimiter(config=RateLimitConfig(), redis_url=None)
        result = await limiter._get_redis()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_redis_connect_error(self) -> None:
        """Connection failure returns None (fail-open)."""
        limiter = RateLimiter(config=RateLimitConfig(), redis_url="redis://fake")
        with (
            patch("app.middleware.rate_limit.REDIS_AVAILABLE", True),
            patch("app.middleware.rate_limit.aioredis") as mock_aioredis,
        ):
            mock_aioredis.from_url.side_effect = ConnectionError("Cannot connect")
            result = await limiter._get_redis()
        assert result is None


# ------------------------------------------------------------------ #
# Middleware integration
# ------------------------------------------------------------------ #
def _make_test_app(limiter: RateLimiter) -> Starlette:
    """Create a minimal Starlette app with rate limit middleware."""

    async def homepage(request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")

    app = Starlette(routes=[Route("/api/v1/health", homepage)])
    app.add_middleware(RateLimitMiddleware, limiter=limiter)
    return app


class TestRateLimitMiddleware:
    """Integration tests for the full middleware dispatch."""

    def test_allowed_request_has_headers(self) -> None:
        """Allowed request includes rate limit headers."""
        limiter = RateLimiter(config=RateLimitConfig())
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 1
        mock_redis.ttl.return_value = 60
        limiter._redis = mock_redis

        with patch("app.middleware.rate_limit.REDIS_AVAILABLE", True):
            app = _make_test_app(limiter)
            client = TestClient(app)
            resp = client.get("/api/v1/health")

        assert resp.status_code == 200
        assert "X-RateLimit-Limit" in resp.headers
        assert resp.headers["X-RateLimit-Limit"] == "100"
        assert "X-RateLimit-Remaining" in resp.headers
        assert "X-RateLimit-Reset" in resp.headers

    def test_rejected_returns_429(self) -> None:
        """Over-limit request returns 429 with Retry-After."""
        limiter = RateLimiter(config=RateLimitConfig())
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 101
        mock_redis.ttl.return_value = 42
        limiter._redis = mock_redis

        with patch("app.middleware.rate_limit.REDIS_AVAILABLE", True):
            app = _make_test_app(limiter)
            client = TestClient(app)
            resp = client.get("/api/v1/health")

        assert resp.status_code == 429
        assert resp.headers["Retry-After"] == "42"
        assert resp.headers["X-RateLimit-Remaining"] == "0"
        body = resp.json()
        assert "Troppe richieste" in body["detail"]

    def test_redis_down_allows_through(self) -> None:
        """Redis unavailable allows request (fail-open)."""
        limiter = RateLimiter(config=RateLimitConfig())

        with patch("app.middleware.rate_limit.REDIS_AVAILABLE", False):
            app = _make_test_app(limiter)
            client = TestClient(app)
            resp = client.get("/api/v1/health")

        assert resp.status_code == 200


class TestExtractIdentifier:
    """Test _extract_identifier static method."""

    def _make_request(
        self,
        *,
        user: object | None = None,
        forwarded: str | None = None,
        client_host: str = "127.0.0.1",
    ) -> MagicMock:
        request = MagicMock(spec=Request)
        request.state = SimpleNamespace()
        if user is not None:
            request.state.user = user
        request.headers = {}
        if forwarded:
            request.headers["x-forwarded-for"] = forwarded
        request.client = SimpleNamespace(host=client_host)
        return request

    def test_authenticated_user(self) -> None:
        user = SimpleNamespace(id="uuid-42")
        request = self._make_request(user=user)
        identifier = RateLimitMiddleware._extract_identifier(request)
        assert identifier == "user:uuid-42"

    def test_forwarded_ip(self) -> None:
        request = self._make_request(forwarded="10.0.0.1, 172.16.0.1, 192.168.1.1")
        identifier = RateLimitMiddleware._extract_identifier(request)
        assert identifier == "ip:192.168.1.1"

    def test_single_forwarded_ip(self) -> None:
        request = self._make_request(forwarded="203.0.113.5")
        identifier = RateLimitMiddleware._extract_identifier(request)
        assert identifier == "ip:203.0.113.5"

    def test_client_ip_fallback(self) -> None:
        request = self._make_request(client_host="10.10.10.10")
        identifier = RateLimitMiddleware._extract_identifier(request)
        assert identifier == "ip:10.10.10.10"

    def test_no_client_unknown(self) -> None:
        request = MagicMock(spec=Request)
        request.state = SimpleNamespace()
        request.headers = {}
        request.client = None
        identifier = RateLimitMiddleware._extract_identifier(request)
        assert identifier == "ip:unknown"
