"""Billing plan service for usage-based billing (DEV-257).

Manages billing plans (Base/Pro/Premium), user plan lookups,
plan upgrades, and YAML config sync.
"""

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from sqlalchemy import select

from app.core.logging import logger
from app.models.billing import BillingPlan
from app.models.user import User
from app.services.database import database_service

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "billing_plans.yaml"


class BillingPlanService:
    """Manages billing plan operations."""

    async def get_plans(self) -> list[BillingPlan]:
        """Get all active billing plans ordered by price.

        Returns:
            List of active BillingPlan records
        """
        async with database_service.get_db() as db:
            query = (
                select(BillingPlan)
                .where(BillingPlan.is_active == True)  # noqa: E712
                .order_by(BillingPlan.price_eur_monthly.asc())  # type: ignore[attr-defined]
            )
            result = await db.execute(query)
            return list(result.scalars().all())

    async def get_plan_by_slug(self, slug: str) -> BillingPlan | None:
        """Get a billing plan by its slug.

        Args:
            slug: Plan slug (base/pro/premium)

        Returns:
            BillingPlan or None if not found
        """
        async with database_service.get_db() as db:
            query = select(BillingPlan).where(BillingPlan.slug == slug)
            result = await db.execute(query)
            return result.scalar_one_or_none()

    async def get_user_plan(self, user_id: int) -> BillingPlan:
        """Get the billing plan for a user, defaulting to base.

        Args:
            user_id: User ID

        Returns:
            BillingPlan for the user
        """
        async with database_service.get_db() as db:
            user_query = select(User).where(User.id == user_id)
            result = await db.execute(user_query)
            user = result.scalar_one_or_none()

            slug = user.billing_plan_slug if user else "base"

            plan_query = select(BillingPlan).where(BillingPlan.slug == slug)
            result = await db.execute(plan_query)
            plan = result.scalar_one_or_none()

            if plan is None:
                # Fall back to base
                plan_query = select(BillingPlan).where(BillingPlan.slug == "base")
                result = await db.execute(plan_query)
                plan = result.scalar_one_or_none()

            if plan is None:
                logger.error("no_billing_plans_found", user_id=user_id, slug=slug)
                return BillingPlan(
                    slug="base",
                    name="Base",
                    price_eur_monthly=25.0,
                    monthly_cost_limit_eur=10.0,
                    window_5h_cost_limit_eur=2.50,
                    window_7d_cost_limit_eur=7.50,
                    credit_markup_factor=1.50,
                )

            return plan

    async def upgrade_plan(self, user_id: int, new_plan_slug: str) -> BillingPlan:
        """Upgrade user to a different billing plan.

        Args:
            user_id: User ID
            new_plan_slug: Target plan slug

        Returns:
            The new BillingPlan

        Raises:
            ValueError: If same plan or plan not found
        """
        async with database_service.get_db() as db:
            # Get user
            user_query = select(User).where(User.id == user_id)
            result = await db.execute(user_query)
            user = result.scalar_one_or_none()

            if user is None:
                raise ValueError("Utente non trovato")

            if user.billing_plan_slug == new_plan_slug:
                raise ValueError(f"Sei già iscritto al piano {new_plan_slug}")

            # Get target plan
            plan_query = select(BillingPlan).where(
                BillingPlan.slug == new_plan_slug,
                BillingPlan.is_active == True,  # noqa: E712
            )
            result = await db.execute(plan_query)
            plan = result.scalar_one_or_none()

            if plan is None:
                raise ValueError(f"Piano non trovato: {new_plan_slug}")

            old_slug = user.billing_plan_slug
            user.billing_plan_slug = new_plan_slug
            await db.commit()

            logger.info(
                "plan_upgraded",
                user_id=user_id,
                old_plan=old_slug,
                new_plan=new_plan_slug,
            )

            return plan

    async def subscribe(self, user_id: int, plan_slug: str) -> BillingPlan:
        """Subscribe user to a billing plan (initial subscription).

        Args:
            user_id: User ID
            plan_slug: Plan slug to subscribe to

        Returns:
            The subscribed BillingPlan

        Raises:
            ValueError: If plan not found
        """
        async with database_service.get_db() as db:
            plan_query = select(BillingPlan).where(
                BillingPlan.slug == plan_slug,
                BillingPlan.is_active == True,  # noqa: E712
            )
            result = await db.execute(plan_query)
            plan = result.scalar_one_or_none()

            if plan is None:
                raise ValueError(f"Piano non trovato: {plan_slug}")

            user_query = select(User).where(User.id == user_id)
            result = await db.execute(user_query)
            user = result.scalar_one_or_none()

            if user is None:
                raise ValueError("Utente non trovato")

            user.billing_plan_slug = plan_slug
            await db.commit()

            logger.info("plan_subscribed", user_id=user_id, plan=plan_slug)

            return plan

    async def sync_plans_from_config(self, config_path: Path | None = None) -> None:
        """Sync billing plans from YAML config to database.

        For each plan in YAML: if it exists in DB (by slug), update all fields;
        if not, insert a new row. Falls back to hardcoded defaults if YAML is
        missing or unreadable.
        """
        path = config_path or _CONFIG_PATH
        plans_data = _load_plans_yaml(path)

        async with database_service.get_db() as db:
            for slug, plan_data in plans_data.items():
                query = select(BillingPlan).where(BillingPlan.slug == slug)
                result = await db.execute(query)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.name = plan_data["name"]
                    existing.price_eur_monthly = plan_data["price_eur_monthly"]
                    existing.monthly_cost_limit_eur = plan_data["monthly_cost_limit_eur"]
                    existing.window_5h_cost_limit_eur = plan_data["window_5h_cost_limit_eur"]
                    existing.window_7d_cost_limit_eur = plan_data["window_7d_cost_limit_eur"]
                    existing.credit_markup_factor = plan_data.get("credit_markup_factor", 1.0)
                    existing.is_active = plan_data.get("is_active", True)
                else:
                    new_plan = BillingPlan(
                        slug=slug,
                        name=plan_data["name"],
                        price_eur_monthly=plan_data["price_eur_monthly"],
                        monthly_cost_limit_eur=plan_data["monthly_cost_limit_eur"],
                        window_5h_cost_limit_eur=plan_data["window_5h_cost_limit_eur"],
                        window_7d_cost_limit_eur=plan_data["window_7d_cost_limit_eur"],
                        credit_markup_factor=plan_data.get("credit_markup_factor", 1.0),
                        is_active=plan_data.get("is_active", True),
                    )
                    db.add(new_plan)

            await db.commit()

        logger.info(
            "billing_plans_synced",
            source=str(path),
            plan_count=len(plans_data),
            slugs=list(plans_data.keys()),
        )


def _load_plans_yaml(path: Path) -> dict[str, Any]:
    """Load billing plans from YAML file with hardcoded fallback."""
    if path.exists():
        try:
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
            plans = raw.get("plans", {})
            if plans:
                return plans
        except yaml.YAMLError as e:
            logger.warning("billing_plans_yaml_error", error=str(e))

    logger.info("billing_plans_using_defaults", config_path=str(path))
    return _get_default_plans()


def _get_default_plans() -> dict[str, Any]:
    """Hardcoded fallback plan definitions."""
    return {
        "base": {
            "name": "Base",
            "price_eur_monthly": 25.0,
            "monthly_cost_limit_eur": 10.0,
            "window_5h_cost_limit_eur": 2.50,
            "window_7d_cost_limit_eur": 7.50,
            "credit_markup_factor": 1.50,
            "is_active": True,
        },
        "pro": {
            "name": "Pro",
            "price_eur_monthly": 75.0,
            "monthly_cost_limit_eur": 30.0,
            "window_5h_cost_limit_eur": 5.00,
            "window_7d_cost_limit_eur": 22.50,
            "credit_markup_factor": 1.30,
            "is_active": True,
        },
        "premium": {
            "name": "Premium",
            "price_eur_monthly": 150.0,
            "monthly_cost_limit_eur": 60.0,
            "window_5h_cost_limit_eur": 10.00,
            "window_7d_cost_limit_eur": 45.00,
            "credit_markup_factor": 1.20,
            "is_active": True,
        },
    }


# Global instance
billing_plan_service = BillingPlanService()
