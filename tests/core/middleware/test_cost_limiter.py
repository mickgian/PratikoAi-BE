"""Tests for CostLimiterMiddleware rolling window integration (DEV-257).

Tests the _check_rolling_windows method that replaces legacy quota checks.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.middleware.cost_limiter import CostLimiterMiddleware
from app.models.billing import BillingPlan
from app.services.rolling_window_service import WindowCheckResult


@pytest.fixture
def middleware():
    app = MagicMock()
    return CostLimiterMiddleware(app)


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.url.path = "/api/v1/chat/stream"
    request.headers = {}
    return request


@pytest.fixture
def base_plan():
    return BillingPlan(
        id=1,
        slug="base",
        name="Base",
        price_eur_monthly=25.0,
        monthly_cost_limit_eur=10.0,
        window_5h_cost_limit_eur=2.50,
        window_7d_cost_limit_eur=7.50,
        credit_markup_factor=1.50,
    )


class TestCheckRollingWindows:
    """Tests for _check_rolling_windows method."""

    @pytest.mark.asyncio
    async def test_allowed_returns_none(self, middleware, mock_request, base_plan):
        """Allowed request should return None (proceed)."""
        result = WindowCheckResult(allowed=True)

        with (
            patch("app.services.billing_plan_service.billing_plan_service") as mock_plan,
            patch("app.services.rolling_window_service.rolling_window_service") as mock_window,
        ):
            mock_plan.get_user_plan = AsyncMock(return_value=base_plan)
            mock_window.check_limits = AsyncMock(return_value=result)

            response = await middleware._check_rolling_windows("1", mock_request)
            assert response is None

    @pytest.mark.asyncio
    async def test_blocked_returns_429(self, middleware, mock_request, base_plan):
        """Blocked request should return 429 with Italian message."""
        reset_at = datetime.now(UTC) + timedelta(hours=2)
        result = WindowCheckResult(
            allowed=False,
            reason="Limite finestra 5h raggiunto",
            window_type="5h",
            current_cost_eur=2.50,
            limit_cost_eur=2.50,
            reset_at=reset_at,
            credits_available=False,
            credit_balance=0.0,
        )

        with (
            patch("app.services.billing_plan_service.billing_plan_service") as mock_plan,
            patch("app.services.rolling_window_service.rolling_window_service") as mock_window,
            patch.object(middleware, "_get_user_role", new_callable=AsyncMock, return_value="regular_user"),
        ):
            mock_plan.get_user_plan = AsyncMock(return_value=base_plan)
            mock_window.check_limits = AsyncMock(return_value=result)

            response = await middleware._check_rolling_windows("1", mock_request)
            assert response is not None
            assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_blocked_with_credits_info(self, middleware, mock_request, base_plan):
        """Blocked response should include credit availability info."""
        result = WindowCheckResult(
            allowed=False,
            reason="Limite raggiunto",
            window_type="7d",
            current_cost_eur=7.50,
            limit_cost_eur=7.50,
            credits_available=True,
            credit_balance=10.0,
        )

        with (
            patch("app.services.billing_plan_service.billing_plan_service") as mock_plan,
            patch("app.services.rolling_window_service.rolling_window_service") as mock_window,
            patch.object(middleware, "_get_user_role", new_callable=AsyncMock, return_value="regular_user"),
        ):
            mock_plan.get_user_plan = AsyncMock(return_value=base_plan)
            mock_window.check_limits = AsyncMock(return_value=result)

            response = await middleware._check_rolling_windows("1", mock_request)
            assert response.status_code == 429
            import json

            body = json.loads(response.body)
            assert body["options"]["use_credits"]["available"] is True
            assert body["options"]["use_credits"]["balance_eur"] == 10.0


class TestAdminBypass:
    """Tests for admin bypass functionality (DEV-257)."""

    @pytest.mark.asyncio
    async def test_admin_sees_can_bypass_in_429(self, middleware, mock_request, base_plan):
        """429 response should include can_bypass: true for admin role."""
        result = WindowCheckResult(
            allowed=False,
            reason="Limite raggiunto",
            window_type="5h",
            current_cost_eur=2.50,
            limit_cost_eur=2.50,
            credits_available=False,
            credit_balance=0.0,
        )

        with (
            patch("app.services.billing_plan_service.billing_plan_service") as mock_plan,
            patch("app.services.rolling_window_service.rolling_window_service") as mock_window,
            patch.object(middleware, "_get_user_role", new_callable=AsyncMock, return_value="admin"),
        ):
            mock_plan.get_user_plan = AsyncMock(return_value=base_plan)
            mock_window.check_limits = AsyncMock(return_value=result)

            response = await middleware._check_rolling_windows("1", mock_request)
            assert response.status_code == 429
            import json

            body = json.loads(response.body)
            assert body["can_bypass"] is True

    @pytest.mark.asyncio
    async def test_regular_user_no_can_bypass(self, middleware, mock_request, base_plan):
        """429 response should have can_bypass: false for regular_user."""
        result = WindowCheckResult(
            allowed=False,
            reason="Limite raggiunto",
            window_type="5h",
            current_cost_eur=2.50,
            limit_cost_eur=2.50,
            credits_available=False,
            credit_balance=0.0,
        )

        with (
            patch("app.services.billing_plan_service.billing_plan_service") as mock_plan,
            patch("app.services.rolling_window_service.rolling_window_service") as mock_window,
            patch.object(middleware, "_get_user_role", new_callable=AsyncMock, return_value="regular_user"),
        ):
            mock_plan.get_user_plan = AsyncMock(return_value=base_plan)
            mock_window.check_limits = AsyncMock(return_value=result)

            response = await middleware._check_rolling_windows("1", mock_request)
            assert response.status_code == 429
            import json

            body = json.loads(response.body)
            assert body["can_bypass"] is False

    @pytest.mark.asyncio
    async def test_bypass_header_allows_admin_through(self, middleware, base_plan):
        """Request with X-Cost-Limit-Bypass header + admin role should return None."""
        request = MagicMock()
        request.url.path = "/api/v1/chat/stream"
        request.headers = {"X-Cost-Limit-Bypass": "true"}

        with patch.object(middleware, "_get_user_role", new_callable=AsyncMock, return_value="admin"):
            response = await middleware._check_rolling_windows("1", request)
            assert response is None

    @pytest.mark.asyncio
    async def test_bypass_header_ignored_for_regular_user(self, middleware, base_plan):
        """Regular user with bypass header should still get 429."""
        request = MagicMock()
        request.url.path = "/api/v1/chat/stream"
        request.headers = {"X-Cost-Limit-Bypass": "true"}

        result = WindowCheckResult(
            allowed=False,
            reason="Limite raggiunto",
            window_type="5h",
            current_cost_eur=2.50,
            limit_cost_eur=2.50,
            credits_available=False,
            credit_balance=0.0,
        )

        with (
            patch.object(middleware, "_get_user_role", new_callable=AsyncMock, return_value="regular_user"),
            patch("app.services.billing_plan_service.billing_plan_service") as mock_plan,
            patch("app.services.rolling_window_service.rolling_window_service") as mock_window,
        ):
            mock_plan.get_user_plan = AsyncMock(return_value=base_plan)
            mock_window.check_limits = AsyncMock(return_value=result)

            response = await middleware._check_rolling_windows("1", request)
            assert response is not None
            assert response.status_code == 429


class TestGetUserId:
    """Tests for _get_user_id extracting user from Authorization header."""

    @pytest.mark.asyncio
    async def test_extracts_user_id_from_bearer_token(self, middleware):
        """Valid Bearer token should resolve to user_id via session lookup."""
        request = MagicMock()
        request.state = MagicMock(spec=[])  # No user_id or session attrs
        request.headers = {"authorization": "Bearer valid.jwt.token"}

        mock_session = MagicMock()
        mock_session.user_id = 42

        with (
            patch("app.core.middleware.cost_limiter.verify_token", return_value="session-abc") as mock_verify,
            patch("app.core.middleware.cost_limiter.database_service") as mock_db,
        ):
            mock_db.get_session = AsyncMock(return_value=mock_session)
            result = await middleware._get_user_id(request)

        assert result == "42"
        mock_verify.assert_called_once_with("valid.jwt.token")
        mock_db.get_session.assert_called_once_with("session-abc")

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_auth_header(self, middleware):
        """Request without Authorization header should return None."""
        request = MagicMock()
        request.state = MagicMock(spec=[])  # No user_id or session attrs
        request.headers = {}

        result = await middleware._get_user_id(request)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_token(self, middleware):
        """verify_token raising should return None (fail open)."""
        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.headers = {"authorization": "Bearer bad.jwt.token"}

        with patch("app.core.middleware.cost_limiter.verify_token", side_effect=ValueError("bad")):
            result = await middleware._get_user_id(request)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_session(self, middleware):
        """Session not found in DB should return None."""
        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.headers = {"authorization": "Bearer valid.jwt.token"}

        with (
            patch("app.core.middleware.cost_limiter.verify_token", return_value="session-abc"),
            patch("app.core.middleware.cost_limiter.database_service") as mock_db,
        ):
            mock_db.get_session = AsyncMock(return_value=None)
            result = await middleware._get_user_id(request)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_non_bearer_scheme(self, middleware):
        """Non-Bearer auth scheme should return None."""
        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.headers = {"authorization": "Basic dXNlcjpwYXNz"}

        result = await middleware._get_user_id(request)
        assert result is None

    @pytest.mark.asyncio
    async def test_prefers_request_state_user_id(self, middleware):
        """If request.state.user_id is set, use it directly."""
        request = MagicMock()
        request.state.user_id = "99"

        result = await middleware._get_user_id(request)
        assert result == "99"


class TestShouldCheckLimits:
    """Tests for _should_check_limits with explicit endpoint matching."""

    def test_exact_match_chat(self, middleware):
        assert middleware._should_check_limits("/api/v1/chat") is True

    def test_exact_match_chat_stream(self, middleware):
        assert middleware._should_check_limits("/api/v1/chat/stream") is True

    def test_exact_match_chatbot_chat(self, middleware):
        assert middleware._should_check_limits("/api/v1/chatbot/chat") is True

    def test_exact_match_chatbot_stream(self, middleware):
        assert middleware._should_check_limits("/api/v1/chatbot/chat/stream") is True

    def test_unrelated_api_not_matched(self, middleware):
        assert middleware._should_check_limits("/api/v1/users") is False

    def test_exempt_endpoint(self, middleware):
        assert middleware._should_check_limits("/health") is False
