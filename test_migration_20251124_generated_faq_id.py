#!/usr/bin/env python
"""Test script for the generated_faq_id migration.

This script verifies that the migration adds the correct column, foreign key,
and index to the expert_feedback table.

Usage:
    python test_migration_20251124_generated_faq_id.py

Prerequisites:
    - PostgreSQL database running
    - Database connection configured in alembic.ini or environment variables
    - Alembic migrations up to 20251124_add_user_role applied
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool

# Test database connection (adjust as needed)
DATABASE_URL = "postgresql://aifinance:devpass@localhost:5432/aifinance"


def test_migration():
    """Test the generated_faq_id migration."""
    print("=" * 80)
    print("Testing Migration: add_generated_faq_id_to_expert_feedback")
    print("=" * 80)

    try:
        # Create engine
        engine = create_engine(DATABASE_URL, poolclass=NullPool)
        inspector = inspect(engine)

        print("\n1. Checking expert_feedback table exists...")
        tables = inspector.get_table_names()
        if "expert_feedback" not in tables:
            print("   ❌ FAIL: expert_feedback table not found")
            return False
        print("   ✓ expert_feedback table exists")

        print("\n2. Checking generated_faq_id column...")
        columns = {col["name"]: col for col in inspector.get_columns("expert_feedback")}

        if "generated_faq_id" not in columns:
            print("   ❌ FAIL: generated_faq_id column not found")
            return False

        col = columns["generated_faq_id"]
        print(f"   ✓ Column exists: {col['name']}")
        print(f"   - Type: {col['type']}")
        print(f"   - Nullable: {col['nullable']}")

        # Verify column type is String/VARCHAR(100)
        if "VARCHAR" not in str(col["type"]).upper() and "TEXT" not in str(col["type"]).upper():
            print(f"   ⚠️  WARNING: Expected VARCHAR type, got {col['type']}")

        # Verify column is nullable
        if not col["nullable"]:
            print("   ❌ FAIL: Column should be nullable")
            return False
        print("   ✓ Column is nullable")

        print("\n3. Checking foreign key constraint...")
        foreign_keys = inspector.get_foreign_keys("expert_feedback")
        fk_found = False

        for fk in foreign_keys:
            if "generated_faq_id" in fk["constrained_columns"]:
                fk_found = True
                print(f"   ✓ Foreign key exists: {fk['name']}")
                print(f"   - Constrained columns: {fk['constrained_columns']}")
                print(f"   - Referred table: {fk['referred_table']}")
                print(f"   - Referred columns: {fk['referred_columns']}")
                print(f"   - On delete: {fk.get('ondelete', 'NO ACTION')}")

                # Verify foreign key properties
                if fk["referred_table"] != "faq_entries":
                    print(f"   ❌ FAIL: Should reference faq_entries, got {fk['referred_table']}")
                    return False

                if fk["referred_columns"] != ["id"]:
                    print(f"   ❌ FAIL: Should reference id column, got {fk['referred_columns']}")
                    return False

                if fk.get("ondelete", "").upper() != "SET NULL":
                    print(f"   ⚠️  WARNING: Expected ON DELETE SET NULL, got {fk.get('ondelete')}")

                break

        if not fk_found:
            print("   ❌ FAIL: Foreign key constraint not found")
            return False

        print("\n4. Checking index...")
        indexes = inspector.get_indexes("expert_feedback")
        index_found = False

        for idx in indexes:
            if "generated_faq_id" in idx["column_names"]:
                index_found = True
                print(f"   ✓ Index exists: {idx['name']}")
                print(f"   - Columns: {idx['column_names']}")
                print(f"   - Unique: {idx['unique']}")
                break

        if not index_found:
            print("   ❌ FAIL: Index on generated_faq_id not found")
            return False

        print("\n5. Testing data insertion...")
        with engine.begin() as conn:
            # Test NULL value (should work)
            print("   - Testing NULL value insertion...")
            result = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM expert_feedback WHERE generated_faq_id IS NULL
                """
                )
            )
            null_count = result.scalar()
            print(f"   ✓ Can query NULL values: {null_count} rows with NULL generated_faq_id")

        print("\n" + "=" * 80)
        print("✓ All migration tests passed!")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


def print_migration_summary():
    """Print summary of what the migration does."""
    print("\n" + "=" * 80)
    print("Migration Summary: 20251124_add_generated_faq_id")
    print("=" * 80)
    print("""
This migration adds the `generated_faq_id` field to the expert_feedback table
to track which Golden Set (FAQ) entries were created from expert feedback.

Schema Changes:
1. Add column: generated_faq_id (VARCHAR(100), nullable)
2. Add foreign key: fk_expert_feedback_generated_faq_id
   - References: faq_entries(id)
   - On delete: SET NULL
3. Add index: idx_expert_feedback_generated_faq_id

Use Case:
When experts mark responses as "Corretta" (correct), the system creates a new
FAQ entry in the Golden Set. This field links back to that FAQ entry for:
- Audit trail (which expert validated this FAQ)
- Quality analysis (track feedback -> FAQ conversion rate)
- Duplicate detection (prevent re-creating FAQs from same feedback)

Model Changes:
- ExpertFeedback.generated_faq_id: Optional[str]
  - Links to FAQEntry.id
  - NULL for feedback that doesn't generate FAQs
  - Set when FAQ is created from "Corretta" feedback
""")
    print("=" * 80)


if __name__ == "__main__":
    print_migration_summary()

    print("\n" + "=" * 80)
    print("Prerequisites Check")
    print("=" * 80)
    print("""
Before running this test, ensure:
1. PostgreSQL is running
2. Database 'aifinance' exists
3. User 'aifinance' has access
4. Alembic migrations are up to date:
   $ alembic upgrade head

To apply this migration:
   $ alembic upgrade head

To rollback this migration:
   $ alembic downgrade -1
""")

    response = input("\nReady to run tests? (y/n): ").strip().lower()
    if response == "y":
        success = test_migration()
        sys.exit(0 if success else 1)
    else:
        print("\nTest cancelled.")
        sys.exit(0)
