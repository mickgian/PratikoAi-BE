"""Tests for billing schemas (DEV-257)."""

import pytest
from pydantic import ValidationError

from app.models.billing import BillingPlan
from app.schemas.billing import (
    BillingPlanSchema,
    CreditInfoSchema,
    CreditRechargeRequest,
    EnableExtraUsageRequest,
    UpgradePlanRequest,
    UsageStatusResponse,
    WindowInfoSchema,
)


class TestCreditRechargeRequest:
    def test_valid_amount(self):
        req = CreditRechargeRequest(amount_eur=10)
        assert req.amount_eur == 10

    def test_requires_amount(self):
        with pytest.raises(ValidationError):
            CreditRechargeRequest()


class TestEnableExtraUsageRequest:
    def test_enable(self):
        req = EnableExtraUsageRequest(enabled=True)
        assert req.enabled is True


class TestUpgradePlanRequest:
    def test_valid(self):
        req = UpgradePlanRequest(new_plan_slug="pro")
        assert req.new_plan_slug == "pro"


class TestBillingPlanSchema:
    def test_from_plan(self):
        plan = BillingPlan(
            slug="base",
            name="Base",
            price_eur_monthly=25.0,
            monthly_cost_limit_eur=10.0,
            window_5h_cost_limit_eur=2.50,
            window_7d_cost_limit_eur=7.50,
            credit_markup_factor=1.50,
        )
        schema = BillingPlanSchema.from_plan(plan)
        assert schema.slug == "base"
        assert schema.markup_percentage == 50

    def test_markup_percentage_pro(self):
        plan = BillingPlan(
            slug="pro",
            name="Pro",
            price_eur_monthly=75.0,
            monthly_cost_limit_eur=30.0,
            window_5h_cost_limit_eur=5.0,
            window_7d_cost_limit_eur=22.5,
            credit_markup_factor=1.30,
        )
        schema = BillingPlanSchema.from_plan(plan)
        assert schema.markup_percentage == 30


class TestUsageStatusResponse:
    def test_full_response(self):
        resp = UsageStatusResponse(
            plan_slug="base",
            plan_name="Base",
            window_5h=WindowInfoSchema(
                window_type="5h",
                current_cost_eur=0.50,
                limit_cost_eur=2.50,
                usage_percentage=20.0,
            ),
            window_7d=WindowInfoSchema(
                window_type="7d",
                current_cost_eur=1.50,
                limit_cost_eur=7.50,
                usage_percentage=20.0,
            ),
            credits=CreditInfoSchema(balance_eur=5.0, extra_usage_enabled=False),
            is_admin=True,
            message_it="Utilizzo nella norma",
        )
        assert resp.plan_slug == "base"
        assert resp.window_5h.usage_percentage == 20.0
        assert resp.is_admin is True

    def test_is_admin_defaults_to_false(self):
        resp = UsageStatusResponse(
            plan_slug="base",
            plan_name="Base",
            window_5h=WindowInfoSchema(
                window_type="5h",
                current_cost_eur=0.0,
                limit_cost_eur=2.50,
                usage_percentage=0.0,
            ),
            window_7d=WindowInfoSchema(
                window_type="7d",
                current_cost_eur=0.0,
                limit_cost_eur=7.50,
                usage_percentage=0.0,
            ),
            credits=CreditInfoSchema(balance_eur=0.0, extra_usage_enabled=False),
        )
        assert resp.is_admin is False
