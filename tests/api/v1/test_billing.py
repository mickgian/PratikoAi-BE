"""Tests for billing API endpoints (DEV-257).

TDD: Tests written FIRST before implementation.
Tests all billing endpoints with mocked services.
"""

from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from fastapi import HTTPException

from app.models.billing import BillingPlan, CreditTransaction, TransactionType
from app.schemas.billing import BillingPlanSchema
from app.services.rolling_window_service import WindowCheckResult, WindowUsageInfo


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    user = MagicMock()
    user.id = 1
    user.role = "super_user"
    return user


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
        is_active=True,
    )


class TestGetUsageStatus:
    """Tests for GET /billing/usage."""

    @pytest.mark.asyncio
    async def test_returns_usage_status(self, mock_user, base_plan):
        """Should return current usage across both windows."""
        from app.api.v1.billing import get_usage_status

        usage_info = WindowUsageInfo(cost_5h_eur=0.20, cost_7d_eur=1.00)

        with (
            patch("app.api.v1.billing.billing_plan_service") as mock_plan_svc,
            patch("app.api.v1.billing.rolling_window_service") as mock_window_svc,
            patch("app.api.v1.billing.usage_credit_service") as mock_credit_svc,
        ):
            mock_plan_svc.get_user_plan = AsyncMock(return_value=base_plan)
            mock_window_svc.get_current_usage = AsyncMock(return_value=usage_info)
            mock_window_svc.get_reset_time = AsyncMock(return_value=None)
            mock_credit_svc.get_balance = AsyncMock(return_value=5.0)
            mock_credit_svc.enable_extra_usage = AsyncMock()

            # Mock the credit info query
            with patch("app.api.v1.billing._get_credit_info", return_value=(False, 5.0)):
                result = await get_usage_status(user=mock_user)

            assert result.plan_slug == "base"
            assert result.is_admin is True
            assert result.window_5h.current_cost_eur == 0.20
            assert result.window_7d.current_cost_eur == 1.00

    @pytest.mark.asyncio
    async def test_returns_reset_times(self, mock_user, base_plan):
        """Should populate reset_at and reset_in_minutes for both windows."""
        from app.api.v1.billing import get_usage_status

        usage_info = WindowUsageInfo(cost_5h_eur=0.10, cost_7d_eur=0.50)
        reset_5h = datetime(2099, 1, 1, 12, 0, 0, tzinfo=UTC)
        reset_7d = datetime(2099, 1, 7, 0, 0, 0, tzinfo=UTC)

        with (
            patch("app.api.v1.billing.billing_plan_service") as mock_plan_svc,
            patch("app.api.v1.billing.rolling_window_service") as mock_window_svc,
        ):
            mock_plan_svc.get_user_plan = AsyncMock(return_value=base_plan)
            mock_window_svc.get_current_usage = AsyncMock(return_value=usage_info)
            mock_window_svc.get_reset_time = AsyncMock(side_effect=[reset_5h, reset_7d])

            with patch("app.api.v1.billing._get_credit_info", return_value=(False, 0.0)):
                result = await get_usage_status(user=mock_user)

            assert result.window_5h.reset_at == reset_5h
            assert result.window_5h.reset_in_minutes is not None
            assert result.window_5h.reset_in_minutes > 0
            assert result.window_7d.reset_at == reset_7d
            assert result.window_7d.reset_in_minutes is not None
            assert result.window_7d.reset_in_minutes > 0

    @pytest.mark.asyncio
    async def test_reset_times_none_when_no_usage(self, mock_user, base_plan):
        """Should return None reset times when windows are empty."""
        from app.api.v1.billing import get_usage_status

        usage_info = WindowUsageInfo(cost_5h_eur=0.0, cost_7d_eur=0.0)

        with (
            patch("app.api.v1.billing.billing_plan_service") as mock_plan_svc,
            patch("app.api.v1.billing.rolling_window_service") as mock_window_svc,
        ):
            mock_plan_svc.get_user_plan = AsyncMock(return_value=base_plan)
            mock_window_svc.get_current_usage = AsyncMock(return_value=usage_info)
            mock_window_svc.get_reset_time = AsyncMock(return_value=None)

            with patch("app.api.v1.billing._get_credit_info", return_value=(False, 0.0)):
                result = await get_usage_status(user=mock_user)

            assert result.window_5h.reset_at is None
            assert result.window_5h.reset_in_minutes is None
            assert result.window_7d.reset_at is None
            assert result.window_7d.reset_in_minutes is None


class TestGetPlans:
    """Tests for GET /billing/plans."""

    @pytest.mark.asyncio
    async def test_returns_plans(self):
        """Should return all active plans."""
        from app.api.v1.billing import get_plans

        plans = [
            BillingPlan(
                id=1,
                slug="base",
                name="Base",
                price_eur_monthly=25.0,
                monthly_cost_limit_eur=10.0,
                window_5h_cost_limit_eur=2.50,
                window_7d_cost_limit_eur=7.50,
                credit_markup_factor=1.50,
            ),
            BillingPlan(
                id=2,
                slug="pro",
                name="Pro",
                price_eur_monthly=75.0,
                monthly_cost_limit_eur=30.0,
                window_5h_cost_limit_eur=5.00,
                window_7d_cost_limit_eur=22.50,
                credit_markup_factor=1.30,
            ),
        ]

        with patch("app.api.v1.billing.billing_plan_service") as mock_svc:
            mock_svc.get_plans = AsyncMock(return_value=plans)
            result = await get_plans()

        assert len(result.plans) == 2
        assert result.plans[0].slug == "base"
        assert result.plans[1].slug == "pro"


class TestCreditRecharge:
    """Tests for POST /billing/credits/recharge."""

    @pytest.mark.asyncio
    async def test_recharge_valid_amount(self, mock_user):
        """Should accept valid recharge amounts."""
        from app.api.v1.billing import recharge_credits
        from app.schemas.billing import CreditRechargeRequest

        request = CreditRechargeRequest(amount_eur=25)

        with patch("app.api.v1.billing.usage_credit_service") as mock_svc:
            mock_svc.recharge = AsyncMock(return_value=30.0)
            result = await recharge_credits(request=request, user=mock_user)

        assert result.balance_eur == 30.0


class TestEnableExtraUsage:
    """Tests for POST /billing/credits/enable-extra-usage."""

    @pytest.mark.asyncio
    async def test_toggle_on(self, mock_user):
        """Should toggle extra usage flag."""
        from app.api.v1.billing import enable_extra_usage
        from app.schemas.billing import EnableExtraUsageRequest

        request = EnableExtraUsageRequest(enabled=True)

        with patch("app.api.v1.billing.usage_credit_service") as mock_svc:
            mock_svc.enable_extra_usage = AsyncMock()
            result = await enable_extra_usage(request=request, user=mock_user)

        assert result["success"] is True


class TestUpgradePlan:
    """Tests for POST /billing/plans/upgrade."""

    @pytest.mark.asyncio
    async def test_upgrade_success(self, mock_user):
        """Should upgrade plan and return new plan info."""
        from app.api.v1.billing import upgrade_plan
        from app.schemas.billing import UpgradePlanRequest

        request = UpgradePlanRequest(new_plan_slug="pro")
        pro_plan = BillingPlan(
            id=2,
            slug="pro",
            name="Pro",
            price_eur_monthly=75.0,
            monthly_cost_limit_eur=30.0,
            window_5h_cost_limit_eur=5.00,
            window_7d_cost_limit_eur=22.50,
            credit_markup_factor=1.30,
        )

        with patch("app.api.v1.billing.billing_plan_service") as mock_svc:
            mock_svc.upgrade_plan = AsyncMock(return_value=pro_plan)
            result = await upgrade_plan(request=request, user=mock_user)

        assert result.success is True
        assert result.plan.slug == "pro"


class TestSimulateUsage:
    """Tests for POST /billing/simulate-usage."""

    @pytest.fixture
    def admin_user(self):
        user = MagicMock()
        user.id = 1
        user.role = "super_user"
        return user

    @pytest.fixture
    def regular_user(self):
        user = MagicMock()
        user.id = 2
        user.role = "regular_user"
        return user

    @pytest.mark.asyncio
    async def test_simulate_usage_happy_path(self, admin_user, base_plan):
        """Should set usage to target percentage and return result."""
        from app.api.v1.billing import simulate_usage
        from app.schemas.billing import SimulateUsageRequest

        request = SimulateUsageRequest(window_type="5h", target_percentage=50.0)

        with (
            patch("app.api.v1.billing.billing_plan_service") as mock_plan_svc,
            patch("app.api.v1.billing.rolling_window_service") as mock_window_svc,
        ):
            mock_plan_svc.get_user_plan = AsyncMock(return_value=base_plan)
            mock_window_svc.replace_usage_for_window = AsyncMock()
            result = await simulate_usage(request=request, user=admin_user)

        assert result.success is True
        assert result.window_type == "5h"
        assert result.target_percentage == 50.0
        assert result.simulated_cost_eur == 1.25  # 50% of 2.50
        assert result.limit_cost_eur == 2.50

    @pytest.mark.asyncio
    async def test_simulate_usage_at_100_percent(self, admin_user, base_plan):
        """Should set usage to exactly the limit."""
        from app.api.v1.billing import simulate_usage
        from app.schemas.billing import SimulateUsageRequest

        request = SimulateUsageRequest(window_type="7d", target_percentage=100.0)

        with (
            patch("app.api.v1.billing.billing_plan_service") as mock_plan_svc,
            patch("app.api.v1.billing.rolling_window_service") as mock_window_svc,
        ):
            mock_plan_svc.get_user_plan = AsyncMock(return_value=base_plan)
            mock_window_svc.replace_usage_for_window = AsyncMock()
            result = await simulate_usage(request=request, user=admin_user)

        assert result.success is True
        assert result.simulated_cost_eur == 7.50  # 100% of 7.50
        assert result.limit_cost_eur == 7.50

    @pytest.mark.asyncio
    async def test_simulate_usage_forbidden_for_regular_user(self, regular_user):
        """Should reject non-admin users with 403."""
        from app.api.v1.billing import simulate_usage
        from app.schemas.billing import SimulateUsageRequest

        request = SimulateUsageRequest(window_type="5h", target_percentage=50.0)

        with pytest.raises(HTTPException) as exc_info:
            await simulate_usage(request=request, user=regular_user)

        assert exc_info.value.status_code == 403


class TestResetUsage:
    """Tests for POST /billing/reset-usage."""

    @pytest.fixture
    def admin_user(self):
        user = MagicMock()
        user.id = 1
        user.role = "super_user"
        return user

    @pytest.fixture
    def regular_user(self):
        user = MagicMock()
        user.id = 2
        user.role = "regular_user"
        return user

    @pytest.mark.asyncio
    async def test_reset_usage_happy_path(self, admin_user):
        """Should clear all usage and return counts."""
        from app.api.v1.billing import reset_usage

        with patch("app.api.v1.billing.rolling_window_service") as mock_window_svc:
            mock_window_svc.clear_usage = AsyncMock(return_value=(5, 2))
            result = await reset_usage(user=admin_user)

        assert result.success is True
        assert result.windows_cleared == 5
        assert result.redis_keys_cleared == 2

    @pytest.mark.asyncio
    async def test_reset_usage_forbidden_for_regular_user(self, regular_user):
        """Should reject non-admin users with 403."""
        from app.api.v1.billing import reset_usage

        with pytest.raises(HTTPException) as exc_info:
            await reset_usage(user=regular_user)

        assert exc_info.value.status_code == 403
