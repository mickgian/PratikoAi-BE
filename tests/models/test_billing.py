"""Tests for billing models (DEV-257).

Tests model field defaults, constraints, and enums.
"""

import pytest

from app.models.billing import (
    BillingPlan,
    CreditTransaction,
    TransactionType,
    UsageWindow,
    UserCredit,
    WindowType,
)


class TestWindowType:
    def test_five_hour_value(self):
        assert WindowType.FIVE_HOUR == "5h"

    def test_seven_day_value(self):
        assert WindowType.SEVEN_DAY == "7d"


class TestTransactionType:
    def test_recharge_value(self):
        assert TransactionType.RECHARGE == "recharge"

    def test_consumption_value(self):
        assert TransactionType.CONSUMPTION == "consumption"

    def test_refund_value(self):
        assert TransactionType.REFUND == "refund"


class TestBillingPlan:
    def test_default_fields(self):
        plan = BillingPlan(
            slug="test",
            name="Test Plan",
            price_eur_monthly=25.0,
            monthly_cost_limit_eur=10.0,
            window_5h_cost_limit_eur=2.50,
            window_7d_cost_limit_eur=7.50,
        )
        assert plan.slug == "test"
        assert plan.credit_markup_factor == 1.0
        assert plan.is_active is True
        assert plan.stripe_price_id is None
        assert plan.id is None

    def test_all_fields(self):
        plan = BillingPlan(
            slug="pro",
            name="Pro",
            price_eur_monthly=75.0,
            monthly_cost_limit_eur=30.0,
            window_5h_cost_limit_eur=1.0,
            window_7d_cost_limit_eur=7.5,
            credit_markup_factor=1.3,
            stripe_price_id="price_abc123",
            is_active=True,
        )
        assert plan.price_eur_monthly == 75.0
        assert plan.credit_markup_factor == 1.3
        assert plan.stripe_price_id == "price_abc123"

    def test_created_at_uses_server_default(self):
        """created_at is None in-memory; PostgreSQL sets it via server_default."""
        plan = BillingPlan(
            slug="base",
            name="Base",
            price_eur_monthly=25.0,
            monthly_cost_limit_eur=10.0,
            window_5h_cost_limit_eur=2.5,
            window_7d_cost_limit_eur=7.5,
        )
        assert plan.created_at is None


class TestUsageWindow:
    def test_default_fields(self):
        window = UsageWindow(
            user_id=1,
            window_type=WindowType.FIVE_HOUR,
            cost_eur=0.05,
        )
        assert window.user_id == 1
        assert window.window_type == "5h"
        assert window.cost_eur == 0.05
        assert window.usage_event_id is None
        # recorded_at is None in-memory; PostgreSQL sets it via server_default
        assert window.recorded_at is None

    def test_with_usage_event_id(self):
        window = UsageWindow(
            user_id=1,
            window_type=WindowType.SEVEN_DAY,
            cost_eur=0.10,
            usage_event_id=42,
        )
        assert window.usage_event_id == 42
        assert window.window_type == "7d"


class TestUserCredit:
    def test_default_fields(self):
        credit = UserCredit(user_id=1)
        assert credit.balance_eur == 0.0
        assert credit.extra_usage_enabled is False
        # updated_at is None in-memory; PostgreSQL sets it via server_default
        assert credit.updated_at is None

    def test_with_balance(self):
        credit = UserCredit(user_id=1, balance_eur=25.0, extra_usage_enabled=True)
        assert credit.balance_eur == 25.0
        assert credit.extra_usage_enabled is True


class TestCreditTransaction:
    def test_recharge_transaction(self):
        tx = CreditTransaction(
            user_id=1,
            transaction_type=TransactionType.RECHARGE,
            amount_eur=10.0,
            balance_after_eur=10.0,
            stripe_payment_intent_id="pi_abc123",
            description="Credit recharge",
        )
        assert tx.transaction_type == "recharge"
        assert tx.amount_eur == 10.0
        assert tx.balance_after_eur == 10.0
        assert tx.stripe_payment_intent_id == "pi_abc123"

    def test_consumption_transaction(self):
        tx = CreditTransaction(
            user_id=1,
            transaction_type=TransactionType.CONSUMPTION,
            amount_eur=0.05,
            balance_after_eur=9.95,
            usage_event_id=100,
        )
        assert tx.transaction_type == "consumption"
        assert tx.usage_event_id == 100
        assert tx.stripe_payment_intent_id is None

    def test_default_fields(self):
        tx = CreditTransaction(
            user_id=1,
            transaction_type=TransactionType.REFUND,
            amount_eur=5.0,
            balance_after_eur=15.0,
        )
        assert tx.description is None
        assert tx.stripe_payment_intent_id is None
        assert tx.usage_event_id is None
        # created_at is None in-memory; PostgreSQL sets it via server_default
        assert tx.created_at is None
