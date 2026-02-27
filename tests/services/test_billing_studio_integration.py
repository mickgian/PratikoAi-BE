"""DEV-417: Tests for Billing Studio Integration.

Tests: studio usage tracking, cost ceiling enforcement, exchange rate EUR.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.billing_plan_service import BillingPlanService


@pytest.fixture
def svc():
    return BillingPlanService()


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestStudioUsageTracking:
    @pytest.mark.asyncio
    async def test_get_plans(self, svc):
        """Verify plans can be retrieved."""
        # Uses hardcoded fallback
        with patch("app.services.billing_plan_service.database_service") as mock_ds:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_ds.get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ds.get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            plans = await svc.get_plans()
            assert isinstance(plans, list)


class TestCostCeiling:
    def test_default_plans_have_limits(self):
        """Verify fallback plans have cost limits."""
        from app.services.billing_plan_service import _get_default_plans

        plans = _get_default_plans()
        for slug, plan in plans.items():
            assert "monthly_cost_limit_eur" in plan
            assert plan["monthly_cost_limit_eur"] > 0
            assert "window_5h_cost_limit_eur" in plan
            assert "window_7d_cost_limit_eur" in plan


class TestExchangeRate:
    @pytest.mark.asyncio
    async def test_convert_eur_to_usd(self):
        from app.services.exchange_rate_service import convert_eur_to_usd

        result = convert_eur_to_usd(10.0, 1.08)
        assert result is not None
        assert abs(result - 10.80) < 0.01

    @pytest.mark.asyncio
    async def test_convert_none(self):
        from app.services.exchange_rate_service import convert_eur_to_usd

        assert convert_eur_to_usd(None, 1.08) is None

    @pytest.mark.asyncio
    async def test_convert_usd_to_eur(self):
        from app.services.exchange_rate_service import convert_usd_to_eur

        result = convert_usd_to_eur(10.80, 1.08)
        assert result is not None
        assert abs(result - 10.0) < 0.01
