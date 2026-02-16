"""Tests for BillingPlanService (DEV-257).

TDD: Tests written FIRST before implementation.
Tests plan retrieval, user plan lookup, plan upgrades, and YAML sync.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.billing import BillingPlan
from app.models.user import User
from app.services.billing_plan_service import BillingPlanService


@pytest.fixture
def service():
    return BillingPlanService()


@pytest.fixture
def plans():
    return [
        BillingPlan(
            id=1,
            slug="base",
            name="Base",
            price_eur_monthly=25.0,
            monthly_cost_limit_eur=10.0,
            window_5h_cost_limit_eur=2.50,
            window_7d_cost_limit_eur=7.50,
            credit_markup_factor=1.50,
            is_active=True,
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
            is_active=True,
        ),
        BillingPlan(
            id=3,
            slug="premium",
            name="Premium",
            price_eur_monthly=150.0,
            monthly_cost_limit_eur=60.0,
            window_5h_cost_limit_eur=10.00,
            window_7d_cost_limit_eur=45.00,
            credit_markup_factor=1.20,
            is_active=True,
        ),
    ]


class TestGetPlans:
    """Tests for get_plans method."""

    @pytest.mark.asyncio
    async def test_returns_active_ordered(self, service, plans):
        """get_plans should return only active plans ordered by price."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = plans
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch("app.services.billing_plan_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            result = await service.get_plans()

            assert len(result) == 3
            assert result[0].slug == "base"
            assert result[2].slug == "premium"


class TestGetUserPlan:
    """Tests for get_user_plan method."""

    @pytest.mark.asyncio
    async def test_returns_correct_plan(self, service, plans):
        """get_user_plan should return the plan matching user's slug."""
        pro_plan = plans[1]
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = pro_plan
        mock_db.execute.return_value = mock_result

        with patch("app.services.billing_plan_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            result = await service.get_plan_by_slug("pro")

            assert result is not None
            assert result.slug == "pro"
            assert result.price_eur_monthly == 75.0

    @pytest.mark.asyncio
    async def test_unknown_slug_returns_none(self, service):
        """get_plan_by_slug with unknown slug should return None."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.services.billing_plan_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            result = await service.get_plan_by_slug("nonexistent")

            assert result is None


class TestUpgradePlan:
    """Tests for upgrade_plan method."""

    @pytest.mark.asyncio
    async def test_upgrade_changes_user_slug(self, service, plans):
        """upgrade_plan should update user's billing_plan_slug."""
        user = User(id=1, email="test@example.com", billing_plan_slug="base")
        pro_plan = plans[1]

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)

        # First call returns user, second returns plan
        mock_result_user = MagicMock()
        mock_result_user.scalar_one_or_none.return_value = user
        mock_result_plan = MagicMock()
        mock_result_plan.scalar_one_or_none.return_value = pro_plan
        mock_db.execute.side_effect = [mock_result_user, mock_result_plan]

        with patch("app.services.billing_plan_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            result = await service.upgrade_plan(user_id=1, new_plan_slug="pro")

            assert user.billing_plan_slug == "pro"
            assert result.slug == "pro"

    @pytest.mark.asyncio
    async def test_upgrade_same_plan_raises(self, service, plans):
        """Upgrading to current plan should raise ValueError."""
        user = User(id=1, email="test@example.com", billing_plan_slug="pro")

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        with patch("app.services.billing_plan_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            with pytest.raises(ValueError, match="Sei già iscritto"):
                await service.upgrade_plan(user_id=1, new_plan_slug="pro")

    @pytest.mark.asyncio
    async def test_upgrade_invalid_plan_raises(self, service):
        """Upgrading to non-existent plan should raise ValueError."""
        user = User(id=1, email="test@example.com", billing_plan_slug="base")

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)

        mock_result_user = MagicMock()
        mock_result_user.scalar_one_or_none.return_value = user
        mock_result_plan = MagicMock()
        mock_result_plan.scalar_one_or_none.return_value = None
        mock_db.execute.side_effect = [mock_result_user, mock_result_plan]

        with patch("app.services.billing_plan_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            with pytest.raises(ValueError, match="Piano non trovato"):
                await service.upgrade_plan(user_id=1, new_plan_slug="nonexistent")


class TestSyncPlansFromConfig:
    """Tests for sync_plans_from_config method."""

    @pytest.mark.asyncio
    async def test_sync_inserts_new_plans(self, service, tmp_path):
        """Sync should INSERT plans that don't exist in DB."""
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
        mock_result.scalar_one_or_none.return_value = None  # Plan doesn't exist
        mock_db.execute.return_value = mock_result

        with patch("app.services.billing_plan_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            await service.sync_plans_from_config(config_path=yaml_file)

            # Should have called db.add for the new plan
            assert mock_db.add.call_count == 1
            added_plan = mock_db.add.call_args[0][0]
            assert added_plan.slug == "base"
            assert added_plan.window_5h_cost_limit_eur == 2.50
            assert added_plan.window_7d_cost_limit_eur == 7.50
            mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sync_updates_existing_plans(self, service, tmp_path):
        """Sync should UPDATE plans that already exist in DB."""
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

        existing_plan = BillingPlan(
            id=1,
            slug="base",
            name="Base",
            price_eur_monthly=25.0,
            monthly_cost_limit_eur=10.0,
            window_5h_cost_limit_eur=0.50,  # Old value
            window_7d_cost_limit_eur=2.50,  # Old value
            credit_markup_factor=1.50,
        )

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_plan
        mock_db.execute.return_value = mock_result

        with patch("app.services.billing_plan_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            await service.sync_plans_from_config(config_path=yaml_file)

            # Should have updated the existing plan in-place
            assert existing_plan.window_5h_cost_limit_eur == 2.50
            assert existing_plan.window_7d_cost_limit_eur == 7.50
            assert mock_db.add.call_count == 0  # No new plan added
            mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sync_uses_defaults_when_yaml_missing(self, service, tmp_path):
        """Sync should use hardcoded defaults if YAML file is missing."""
        missing_file = tmp_path / "nonexistent.yaml"

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.services.billing_plan_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            await service.sync_plans_from_config(config_path=missing_file)

            # Should insert 3 default plans (base, pro, premium)
            assert mock_db.add.call_count == 3
            slugs = {call.args[0].slug for call in mock_db.add.call_args_list}
            assert slugs == {"base", "pro", "premium"}
