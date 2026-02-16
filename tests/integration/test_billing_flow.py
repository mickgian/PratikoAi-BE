"""Integration tests for billing flow (DEV-257).

Tests the complete billing workflow:
  - Usage recording → window check → limit hit → 429
  - Credit recharge → continue usage
  - Plan upgrade → increased limits

NOTE: Skipped in CI - requires test database on port 5433.
"""

import pytest

pytest.skip(
    "Integration tests require test database on port 5433 - skipped in CI",
    allow_module_level=True,
)

from app.models.billing import (  # noqa: E402
    BillingPlan,
    TransactionType,
)
from app.services.rolling_window_service import rolling_window_service  # noqa: E402
from app.services.usage_credit_service import usage_credit_service  # noqa: E402


class TestBillingEndToEnd:
    """Full billing flow integration tests."""

    @pytest.mark.asyncio
    async def test_usage_within_limits_allows_request(self, test_db, test_user):
        """User within 5h window limit can continue using the service."""
        # Seed plan
        plan = BillingPlan(
            slug="base",
            name="Base",
            price_eur_monthly=25.0,
            monthly_cost_limit_eur=10.0,
            window_5h_cost_limit_eur=2.50,
            window_7d_cost_limit_eur=7.50,
            credit_markup_factor=1.50,
            is_active=True,
        )
        test_db.add(plan)
        await test_db.commit()

        # Record small usage
        await rolling_window_service.record_usage(
            user_id=test_user.id,
            cost_eur=0.10,
            usage_event_id=1,
            db=test_db,
        )

        # Check limits - should be allowed
        result = await rolling_window_service.check_limits(
            user_id=test_user.id,
            plan_slug="base",
            db=test_db,
        )
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_usage_exceeds_5h_limit_blocks(self, test_db, test_user):
        """User exceeding 5h window limit gets blocked."""
        plan = BillingPlan(
            slug="base",
            name="Base",
            price_eur_monthly=25.0,
            monthly_cost_limit_eur=10.0,
            window_5h_cost_limit_eur=2.50,
            window_7d_cost_limit_eur=7.50,
            credit_markup_factor=1.50,
            is_active=True,
        )
        test_db.add(plan)
        await test_db.commit()

        # Record usage that exceeds 5h limit (26 * 0.10 = 2.60 > 2.50)
        for i in range(26):
            await rolling_window_service.record_usage(
                user_id=test_user.id,
                cost_eur=0.10,
                usage_event_id=i + 1,
                db=test_db,
            )

        result = await rolling_window_service.check_limits(
            user_id=test_user.id,
            plan_slug="base",
            db=test_db,
        )
        assert result.allowed is False
        assert result.window_type == "5h"

    @pytest.mark.asyncio
    async def test_credit_recharge_and_consume(self, test_db, test_user):
        """User can recharge credits and consume them with markup."""
        # Recharge 10 EUR
        await usage_credit_service.recharge(
            user_id=test_user.id,
            amount_eur=10,
            db=test_db,
        )

        balance = await usage_credit_service.get_balance(
            user_id=test_user.id,
            db=test_db,
        )
        assert balance == 10.0

        # Consume with 50% markup (base plan)
        await usage_credit_service.consume(
            user_id=test_user.id,
            cost_eur=1.0,
            markup_factor=1.50,
            db=test_db,
        )

        balance_after = await usage_credit_service.get_balance(
            user_id=test_user.id,
            db=test_db,
        )
        assert balance_after == 8.50  # 10 - (1.0 * 1.50)

    @pytest.mark.asyncio
    async def test_upgrade_increases_limits(self, test_db, test_user):
        """Upgrading from base to pro increases window limits."""
        base = BillingPlan(
            slug="base",
            name="Base",
            price_eur_monthly=25.0,
            monthly_cost_limit_eur=10.0,
            window_5h_cost_limit_eur=2.50,
            window_7d_cost_limit_eur=7.50,
            credit_markup_factor=1.50,
            is_active=True,
        )
        pro = BillingPlan(
            slug="pro",
            name="Pro",
            price_eur_monthly=75.0,
            monthly_cost_limit_eur=30.0,
            window_5h_cost_limit_eur=5.00,
            window_7d_cost_limit_eur=22.50,
            credit_markup_factor=1.30,
            is_active=True,
        )
        test_db.add(base)
        test_db.add(pro)
        await test_db.commit()

        # Record usage that exceeds base 5h limit (2.50) but not pro (5.00)
        # 26 * 0.10 = 2.60 EUR
        for i in range(26):
            await rolling_window_service.record_usage(
                user_id=test_user.id,
                cost_eur=0.10,
                usage_event_id=i + 1,
                db=test_db,
            )

        # Check with base plan - blocked (2.60 >= 2.50)
        base_result = await rolling_window_service.check_limits(
            user_id=test_user.id,
            plan_slug="base",
            db=test_db,
        )
        assert base_result.allowed is False

        # Check with pro plan - allowed (2.60 < 5.00)
        pro_result = await rolling_window_service.check_limits(
            user_id=test_user.id,
            plan_slug="pro",
            db=test_db,
        )
        assert pro_result.allowed is True

    @pytest.mark.asyncio
    async def test_transaction_history_records_operations(self, test_db, test_user):
        """All credit operations are recorded in transaction history."""
        # Recharge
        await usage_credit_service.recharge(
            user_id=test_user.id,
            amount_eur=25,
            db=test_db,
        )

        # Consume
        await usage_credit_service.consume(
            user_id=test_user.id,
            cost_eur=0.50,
            markup_factor=1.30,
            db=test_db,
        )

        history = await usage_credit_service.get_transaction_history(
            user_id=test_user.id,
            db=test_db,
        )
        assert len(history) == 2
        assert history[0].transaction_type == TransactionType.CONSUMPTION
        assert history[1].transaction_type == TransactionType.RECHARGE
