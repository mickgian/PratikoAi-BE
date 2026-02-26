"""DEV-395: Tests for API Rate Limiting middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.middleware.rate_limit import RateLimitConfig, RateLimiter


class TestRateLimitConfig:
    """Test rate limit configuration."""

    def test_default_limits(self) -> None:
        """Default rate limits are set per spec."""
        config = RateLimitConfig()
        assert config.default_limit == 100
        assert config.default_window == 60

    def test_per_endpoint_limits(self) -> None:
        """Per-endpoint limits override defaults."""
        config = RateLimitConfig(
            endpoint_limits={
                "/api/v1/auth/login": {"limit": 10, "window": 60},
                "/api/v1/chat": {"limit": 30, "window": 60},
            }
        )
        assert config.get_limit("/api/v1/auth/login") == (10, 60)
        assert config.get_limit("/api/v1/chat") == (30, 60)
        assert config.get_limit("/api/v1/unknown") == (100, 60)

    def test_limit_zero_disabled(self) -> None:
        """Endpoint with limit=0 effectively disables rate limiting."""
        config = RateLimitConfig(endpoint_limits={"/api/v1/health": {"limit": 0, "window": 60}})
        limit, window = config.get_limit("/api/v1/health")
        assert limit == 0


class TestRateLimiter:
    """Test RateLimiter core logic."""

    def setup_method(self) -> None:
        self.config = RateLimitConfig()
        self.limiter = RateLimiter(config=self.config)

    @pytest.mark.asyncio
    async def test_under_limit_allowed(self) -> None:
        """Request under limit is allowed."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 1
        mock_redis.ttl.return_value = 60

        with patch.object(self.limiter, "_get_redis", return_value=mock_redis):
            allowed, remaining, reset = await self.limiter.check_rate_limit(
                identifier="user:1", endpoint="/api/v1/health"
            )

        assert allowed is True
        assert remaining == 99  # default limit 100, minus 1 request

    @pytest.mark.asyncio
    async def test_over_limit_rejected(self) -> None:
        """Request over limit is rejected."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 101
        mock_redis.ttl.return_value = 30

        with patch.object(self.limiter, "_get_redis", return_value=mock_redis):
            allowed, remaining, reset = await self.limiter.check_rate_limit(
                identifier="user:1", endpoint="/api/v1/chat"
            )

        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_redis_unavailable_fail_open(self) -> None:
        """When Redis is unavailable, requests are allowed (fail-open)."""
        with patch.object(self.limiter, "_get_redis", return_value=None):
            allowed, remaining, reset = await self.limiter.check_rate_limit(
                identifier="user:1", endpoint="/api/v1/chat"
            )

        assert allowed is True

    @pytest.mark.asyncio
    async def test_per_endpoint_limits(self) -> None:
        """Different endpoints have different limits."""
        config = RateLimitConfig(
            endpoint_limits={
                "/api/v1/auth/login": {"limit": 10, "window": 60},
            }
        )
        limiter = RateLimiter(config=config)

        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 11
        mock_redis.ttl.return_value = 45

        with patch.object(limiter, "_get_redis", return_value=mock_redis):
            allowed, remaining, reset = await limiter.check_rate_limit(
                identifier="user:1", endpoint="/api/v1/auth/login"
            )

        assert allowed is False  # 11 > 10

    @pytest.mark.asyncio
    async def test_negative_remaining_clamped(self) -> None:
        """Negative remaining from race condition is clamped to 0."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 105  # Way over limit
        mock_redis.ttl.return_value = 20

        with patch.object(self.limiter, "_get_redis", return_value=mock_redis):
            allowed, remaining, reset = await self.limiter.check_rate_limit(
                identifier="user:1", endpoint="/api/v1/chat"
            )

        assert remaining == 0  # Clamped, not -5


class TestRateLimiterKeyGeneration:
    """Test rate limit key generation."""

    def setup_method(self) -> None:
        self.limiter = RateLimiter(config=RateLimitConfig())

    def test_key_includes_identifier_and_endpoint(self) -> None:
        """Redis key includes both user identifier and endpoint."""
        key = self.limiter._build_key("user:42", "/api/v1/chat")
        assert "user:42" in key
        assert "chat" in key

    def test_unauthenticated_ip_key(self) -> None:
        """Unauthenticated requests use IP as identifier."""
        key = self.limiter._build_key("ip:192.168.1.1", "/api/v1/search")
        assert "ip:192.168.1.1" in key
