"""Tests for migration adding custom_email_allowed column to billing_plans.

Verifies the migration module exists, has correct revision chain,
and that the BillingPlan model includes the custom_email_allowed field.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

# ---------------------------------------------------------------------------
# Ensure app.services.database is stubbed before model imports
# ---------------------------------------------------------------------------
if "app.services.database" not in sys.modules:
    from unittest.mock import MagicMock

    _db_stub = ModuleType("app.services.database")
    _db_stub.database_service = MagicMock()  # type: ignore[attr-defined]
    sys.modules["app.services.database"] = _db_stub

from app.models.billing import BillingPlan

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_MIGRATION_FILE = _PROJECT_ROOT / "alembic" / "versions" / "20260301_add_custom_email_allowed.py"


def _load_migration():
    """Load the migration module dynamically."""
    spec = importlib.util.spec_from_file_location("migration_custom_email", _MIGRATION_FILE)
    assert spec is not None, f"Migration file not found: {_MIGRATION_FILE}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestMigrationModuleStructure:
    """Verify migration file has correct structure and revision chain."""

    def test_migration_file_exists(self):
        assert _MIGRATION_FILE.exists(), f"Missing migration: {_MIGRATION_FILE}"

    def test_revision_identifiers(self):
        mod = _load_migration()
        assert mod.revision == "add_custom_email_20260301"
        assert mod.down_revision == "persist_comparison_20260228"

    def test_has_upgrade_and_downgrade(self):
        mod = _load_migration()
        assert callable(getattr(mod, "upgrade", None))
        assert callable(getattr(mod, "downgrade", None))


class TestBillingPlanModelHasField:
    """Verify the BillingPlan model has the custom_email_allowed field."""

    def test_model_has_custom_email_allowed_field(self):
        assert hasattr(BillingPlan, "custom_email_allowed")

    def test_custom_email_allowed_default_is_false(self):
        plan = BillingPlan(
            slug="test",
            name="Test",
            price_eur_monthly=10.0,
            monthly_cost_limit_eur=5.0,
            window_5h_cost_limit_eur=1.0,
            window_7d_cost_limit_eur=3.0,
        )
        assert plan.custom_email_allowed is False

    def test_column_in_table_metadata(self):
        table = BillingPlan.__table__  # type: ignore[attr-defined]
        column_names = [c.name for c in table.columns]
        assert "custom_email_allowed" in column_names

    def test_column_type_is_boolean(self):
        import sqlalchemy as sa

        table = BillingPlan.__table__  # type: ignore[attr-defined]
        col = table.c.custom_email_allowed
        assert isinstance(col.type, sa.Boolean)
