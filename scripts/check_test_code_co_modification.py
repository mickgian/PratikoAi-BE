#!/usr/bin/env python3
"""
Pre-commit hook: Verify tests are modified when feature code is modified.
Enforces TDD by warning when feature changes lack test updates.

ADR-012: Enhanced Pre-commit Test Enforcement
"""

import os
import subprocess
import sys
from pathlib import Path


def get_staged_files() -> list[str]:
    """Get list of staged files from git."""
    result = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True)
    return result.stdout.strip().split("\n") if result.stdout.strip() else []


def generate_test_path(feature_file: str) -> str:
    """Generate expected test file path from feature file path."""
    relative_path = feature_file.replace("app/", "", 1)
    parts = Path(relative_path).parts
    directory = "/".join(parts[:-1]) if len(parts) > 1 else ""
    filename = parts[-1]
    test_filename = f"test_{filename}"

    if directory:
        return f"tests/{directory}/{test_filename}"
    return f"tests/{test_filename}"


def main():
    """Check that feature modifications are accompanied by test modifications."""
    staged_files = get_staged_files()

    modified_feature_files = [
        f for f in staged_files if f.startswith("app/") and f.endswith(".py") and not f.endswith("__init__.py")
    ]

    if not modified_feature_files:
        sys.exit(0)  # No feature files modified

    modified_test_files = [f for f in staged_files if f.startswith("tests/")]

    missing_test_updates = []
    for feature_file in modified_feature_files:
        expected_test_file = generate_test_path(feature_file)

        # Check if corresponding test file is in staged changes
        if expected_test_file not in modified_test_files:
            missing_test_updates.append((feature_file, expected_test_file))

    if missing_test_updates:
        print("\n⚠️  WARNING: Feature modified without test update")
        print("\nThe following feature files were modified but their tests were not:")
        for feature_file, expected_test_file in missing_test_updates:
            print(f"\n  Feature: {feature_file}")
            print(f"  Expected test: {expected_test_file}")

            # Check if test file exists but wasn't modified
            if os.path.exists(expected_test_file):
                print("  ℹ️  Test file exists but was not updated")
            else:
                print("  ❌ Test file does not exist")

        print("\n⚠️  Consider updating tests to reflect feature changes.")
        print("📖 See docs/architecture/decisions/ADR-012.md for TDD requirements.")

        # Currently WARNING only (exit 0), can be changed to ERROR (exit 1)
        sys.exit(0)

    print("✅ TDD Check: Feature modifications include test updates")
    sys.exit(0)


if __name__ == "__main__":
    main()
