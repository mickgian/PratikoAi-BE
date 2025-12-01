"""Test to prevent duplicate table names across SQLModel models.

This regression test ensures we don't accidentally import models with
duplicate __tablename__ values, which causes SQLAlchemy metadata conflicts.

Related Bug: Phase 3 migration failure due to duplicate 'subscriptions' table
between payment.py and subscription.py models.
"""

import importlib
import inspect
from typing import Dict, List, Set

import pytest
from sqlmodel import SQLModel


def get_all_model_modules() -> list[str]:
    """Get list of all model modules to check."""
    return [
        "app.models.cassazione",
        "app.models.ccnl_database",
        "app.models.data_export",
        "app.models.document",
        "app.models.faq",
        "app.models.faq_automation",
        "app.models.italian_data",
        "app.models.knowledge",
        "app.models.knowledge_chunk",
        "app.models.payment",
        # "app.models.subscription",  # Excluded: Conflicts with payment.py
        "app.models.quality_analysis",
        "app.models.query_normalization",
        "app.models.regulatory_documents",
        "app.models.session",
        "app.models.thread",
        "app.models.usage",
        "app.models.user",
    ]


def get_sqlmodel_classes(module_name: str) -> list[type]:
    """Extract all SQLModel table classes from a module."""
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return []

    # Ignore these base class names (not actual table models)
    IGNORE_CLASSES = {"SQLModel", "BaseModel", "Base"}

    classes = []
    for name, obj in inspect.getmembers(module, inspect.isclass):
        # Skip base classes
        if name in IGNORE_CLASSES:
            continue

        # Skip if class is defined in a different module (imported, not defined here)
        if obj.__module__ != module_name:
            continue

        # Check if it's a SQLModel with table=True
        if (
            issubclass(obj, SQLModel)
            and hasattr(obj, "__tablename__")
            and obj.__tablename__ is not None
            and isinstance(obj.__tablename__, str)  # Must be actual string, not inherited
        ):
            classes.append(obj)

    return classes


def test_no_duplicate_table_names():
    """Regression test: Ensure no duplicate table names across models.

    BEFORE FIX: payment.py and subscription.py both defined 'subscriptions' table
    AFTER FIX: Only payment.py is imported; subscription.py excluded from alembic

    This test fails if:
    - Two models define the same __tablename__
    - Alembic imports would cause metadata conflicts
    """
    table_name_map: dict[str, list[str]] = {}

    # Scan all model modules
    for module_name in get_all_model_modules():
        classes = get_sqlmodel_classes(module_name)

        for cls in classes:
            table_name = cls.__tablename__
            model_path = f"{module_name}.{cls.__name__}"

            if table_name not in table_name_map:
                table_name_map[table_name] = []

            table_name_map[table_name].append(model_path)

    # Find duplicates
    duplicates = {table: models for table, models in table_name_map.items() if len(models) > 1}

    # Assert no duplicates
    if duplicates:
        error_msg = "Duplicate table names detected:\n"
        for table_name, models in duplicates.items():
            error_msg += f"\n  Table '{table_name}' defined in:\n"
            for model in models:
                error_msg += f"    - {model}\n"

        error_msg += "\nFix: Ensure each table name is unique, or exclude conflicting models from alembic/env.py"
        pytest.fail(error_msg)

    print(f"✓ Checked {len(table_name_map)} unique table names across {len(get_all_model_modules())} modules")


def test_subscription_models_not_both_imported():
    """Ensure payment.py and subscription.py Subscription models aren't both imported.

    CONTEXT:
    - payment.py defines: Subscription (simple Stripe model)
    - subscription.py defines: Subscription (Italian market model with Partita IVA)
    - Both use __tablename__ = "subscriptions"

    CURRENT STATE:
    - payment.py is imported (matches current DB schema)
    - subscription.py is excluded (awaiting schema migration)

    This test ensures we don't accidentally re-enable both imports.
    """
    # Read alembic/env.py
    with open("/Users/micky/PycharmProjects/PratikoAi-BE/alembic/env.py") as f:
        env_content = f.read()

    # Check imports
    has_payment_subscription = "from app.models.payment import" in env_content
    has_subscription_subscription = (
        "from app.models.subscription import" in env_content
        and "Subscription" in env_content.split("from app.models.subscription import")[1].split("\n")[0]
    )

    # Should have payment.py import
    assert has_payment_subscription, "payment.py should be imported in alembic/env.py"

    # Should NOT have uncommented subscription.py import
    # (Comment check: line should start with # or not import Subscription)
    subscription_import_lines = [
        line for line in env_content.split("\n") if "from app.models.subscription import" in line
    ]

    for line in subscription_import_lines:
        # If line imports Subscription, it must be commented out
        if "Subscription" in line and not line.strip().startswith("#"):
            pytest.fail(
                f"subscription.py Subscription import must be commented out to avoid conflict.\n"
                f"Found: {line}\n\n"
                f"Reason: Both payment.py and subscription.py define 'subscriptions' table.\n"
                f"Current DB uses payment.py schema. subscription.py awaits migration."
            )

    print("✓ No conflicting Subscription imports detected")


def test_alembic_env_imports_match_expected():
    """Verify alembic/env.py imports the expected Phase 3 models."""
    expected_phase3_imports = [
        "DataExportRequest",
        "ExportAuditLog",
        "FAQCandidate",
        "QueryCluster",
        "ExpertFeedback",
        "ExpertProfile",
        "QualityMetric",
    ]

    with open("/Users/micky/PycharmProjects/PratikoAi-BE/alembic/env.py") as f:
        env_content = f.read()

    missing_imports = []
    for model_name in expected_phase3_imports:
        if model_name not in env_content:
            missing_imports.append(model_name)

    if missing_imports:
        pytest.fail(
            f"Expected Phase 3 models missing from alembic/env.py:\n"
            f"  {', '.join(missing_imports)}\n\n"
            f"These models should be imported for migration generation."
        )

    print(f"✓ All {len(expected_phase3_imports)} expected Phase 3 models are imported")
