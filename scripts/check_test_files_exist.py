#!/usr/bin/env python3
"""
Pre-commit hook: Verify test files exist for new feature files.
Enforces TDD by blocking commits of feature code without corresponding tests.

ADR-012: Enhanced Pre-commit Test Enforcement
"""

import os
import sys
from pathlib import Path


def generate_test_path(feature_file: str) -> str:
    """
    Generate expected test file path from feature file path.

    Examples:
        app/services/cache_service.py -> tests/services/test_cache_service.py
        app/api/v1/expert_feedback.py -> tests/api/test_expert_feedback.py
    """
    # Remove 'app/' prefix and replace with 'tests/'
    relative_path = feature_file.replace("app/", "", 1)

    # Get directory and filename
    parts = Path(relative_path).parts
    directory = "/".join(parts[:-1]) if len(parts) > 1 else ""
    filename = parts[-1]

    # Add 'test_' prefix to filename
    test_filename = f"test_{filename}"

    # Construct test path
    if directory:
        test_path = f"tests/{directory}/{test_filename}"
    else:
        test_path = f"tests/{test_filename}"

    return test_path


def main():
    """Check that all staged feature files have corresponding test files."""
    staged_files = sys.argv[1:]  # Git passes staged files as arguments

    feature_files = [f for f in staged_files if f.startswith("app/") and f.endswith(".py")]

    if not feature_files:
        sys.exit(0)  # No feature files to check

    missing_tests = []
    for feature_file in feature_files:
        # Skip __init__.py files
        if feature_file.endswith("__init__.py"):
            continue

        test_file_path = generate_test_path(feature_file)

        # Check if test file exists
        if not os.path.exists(test_file_path):
            missing_tests.append((feature_file, test_file_path))

    if missing_tests:
        print("\n❌ TDD VIOLATION: Missing test files for feature code")
        print("\nThe following feature files lack corresponding test files:")
        for feature_file, expected_test_file in missing_tests:
            print(f"\n  Feature: {feature_file}")
            print(f"  Expected test: {expected_test_file}")

        print("\n⚠️  You must create test files BEFORE committing feature code.")
        print("📖 See docs/architecture/decisions/ADR-012.md for TDD requirements.")
        print("\n🔓 To bypass this check (EMERGENCY ONLY):")
        print("   git commit --no-verify -m 'HOTFIX: ...'")
        sys.exit(1)

    print("✅ TDD Check: All feature files have corresponding test files")
    sys.exit(0)


if __name__ == "__main__":
    main()
