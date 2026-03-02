"""DEV-448: Tests for custom_email_allowed field on BillingPlan.

TDD RED phase: Tests written FIRST.
Validates that Base=false, Pro=true, Premium=true, YAML sync includes field,
and schema exposes the field.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.billing import BillingPlan
from app.schemas.billing import BillingPlanSchema
from app.services.billing_plan_service import BillingPlanService


@pytest.fixture
def service():
    return BillingPlanService()


class TestCustomEmailAllowedField:
    """Tests for custom_email_allowed on BillingPlan model."""

    def test_base_plan_custom_email_false(self) -> None:
        """Base plan should NOT allow custom email."""
        plan = BillingPlan(
            slug="base",
            name="Base",
            price_eur_monthly=25.0,
            monthly_cost_limit_eur=10.0,
            window_5h_cost_limit_eur=2.50,
            window_7d_cost_limit_eur=7.50,
            custom_email_allowed=False,
        )
        assert plan.custom_email_allowed is False

    def test_pro_plan_custom_email_true(self) -> None:
        """Pro plan should allow custom email."""
        plan = BillingPlan(
            slug="pro",
            name="Pro",
            price_eur_monthly=75.0,
            monthly_cost_limit_eur=30.0,
            window_5h_cost_limit_eur=5.00,
            window_7d_cost_limit_eur=22.50,
            custom_email_allowed=True,
        )
        assert plan.custom_email_allowed is True

    def test_premium_plan_custom_email_true(self) -> None:
        """Premium plan should allow custom email."""
        plan = BillingPlan(
            slug="premium",
            name="Premium",
            price_eur_monthly=150.0,
            monthly_cost_limit_eur=60.0,
            window_5h_cost_limit_eur=10.00,
            window_7d_cost_limit_eur=45.00,
            custom_email_allowed=True,
        )
        assert plan.custom_email_allowed is True

    def test_default_custom_email_false(self) -> None:
        """Default for custom_email_allowed should be False."""
        plan = BillingPlan(
            slug="test",
            name="Test",
            price_eur_monthly=0.0,
            monthly_cost_limit_eur=0.0,
            window_5h_cost_limit_eur=0.0,
            window_7d_cost_limit_eur=0.0,
        )
        assert plan.custom_email_allowed is False


class TestBillingPlanSchemaCustomEmail:
    """Tests for custom_email_allowed in BillingPlanSchema."""

    def test_schema_exposes_custom_email_allowed(self) -> None:
        """BillingPlanSchema should include custom_email_allowed field."""
        plan = BillingPlan(
            slug="pro",
            name="Pro",
            price_eur_monthly=75.0,
            monthly_cost_limit_eur=30.0,
            window_5h_cost_limit_eur=5.00,
            window_7d_cost_limit_eur=22.50,
            credit_markup_factor=1.30,
            custom_email_allowed=True,
        )
        schema = BillingPlanSchema.from_plan(plan)
        assert schema.custom_email_allowed is True

    def test_schema_base_plan_false(self) -> None:
        """BillingPlanSchema for base plan should show custom_email_allowed=False."""
        plan = BillingPlan(
            slug="base",
            name="Base",
            price_eur_monthly=25.0,
            monthly_cost_limit_eur=10.0,
            window_5h_cost_limit_eur=2.50,
            window_7d_cost_limit_eur=7.50,
            credit_markup_factor=1.50,
            custom_email_allowed=False,
        )
        schema = BillingPlanSchema.from_plan(plan)
        assert schema.custom_email_allowed is False


class TestYamlSyncCustomEmail:
    """Tests for YAML sync including custom_email_allowed field."""

    @pytest.mark.asyncio
    async def test_sync_includes_custom_email_field(self, service, tmp_path):
        """YAML sync should populate custom_email_allowed from config."""
        yaml_file = tmp_path / "billing_plans.yaml"
        yaml_file.write_text(
            """
version: "1.0"
plans:
  pro:
    name: "Pro"
    price_eur_monthly: 75.0
    monthly_cost_limit_eur: 30.0
    window_5h_cost_limit_eur: 5.00
    window_7d_cost_limit_eur: 22.50
    credit_markup_factor: 1.30
    custom_email_allowed: true
    is_active: true
"""
        )

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Plan doesn't exist
        mock_db.execute.return_value = mock_result

        with patch("app.services.billing_plan_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            await service.sync_plans_from_config(config_path=yaml_file)

            assert mock_db.add.call_count == 1
            added_plan = mock_db.add.call_args[0][0]
            assert added_plan.custom_email_allowed is True

    @pytest.mark.asyncio
    async def test_sync_defaults_custom_email_false(self, service, tmp_path):
        """YAML without custom_email_allowed should default to False."""
        yaml_file = tmp_path / "billing_plans.yaml"
        yaml_file.write_text(
            """
version: "1.0"
plans:
  base:
    name: "Base"
    price_eur_monthly: 25.0
    monthly_cost_limit_eur: 10.0
    window_5h_cost_limit_eur: 2.50
    window_7d_cost_limit_eur: 7.50
    credit_markup_factor: 1.50
    is_active: true
"""
        )

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.services.billing_plan_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            await service.sync_plans_from_config(config_path=yaml_file)

            added_plan = mock_db.add.call_args[0][0]
            assert added_plan.custom_email_allowed is False
