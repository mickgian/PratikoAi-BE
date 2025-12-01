#!/usr/bin/env python3
"""
Pre-commit hook: Verify new test files have minimum number of test functions.
Prevents placeholder test files with insufficient coverage.

ADR-012: Enhanced Pre-commit Test Enforcement
"""

import argparse
import re
import subprocess
import sys


def count_test_functions(test_file: str) -> int:
    """Count number of test functions in a test file."""
    try:
        with open(test_file) as f:
            content = f.read()

        # Count functions starting with 'test_'
        test_functions = re.findall(r"^\s*def\s+(test_\w+)\s*\(", content, re.MULTILINE)
        return len(test_functions)
    except FileNotFoundError:
        return 0


def is_new_file(file_path: str) -> bool:
    """Check if file is newly added (not previously committed)."""
    result = subprocess.run(["git", "diff", "--cached", "--name-status", file_path], capture_output=True, text=True)
    return result.stdout.startswith("A\t")  # 'A' = Added


def main():
    parser = argparse.ArgumentParser(description="Check minimum test count in new test files")
    parser.add_argument("--min-tests", type=int, default=3, help="Minimum number of test functions required")
    parser.add_argument("files", nargs="*", help="Test files to check")

    args = parser.parse_args()

    new_test_files = [f for f in args.files if is_new_file(f)]

    if not new_test_files:
        sys.exit(0)  # No new test files to check

    insufficient_tests = []
    for test_file in new_test_files:
        test_count = count_test_functions(test_file)
        if test_count < args.min_tests:
            insufficient_tests.append((test_file, test_count))

    if insufficient_tests:
        print("\n❌ TDD VIOLATION: Insufficient test functions in new test files")
        print(f"\nMinimum required: {args.min_tests} test functions per file")
        print("\nThe following test files have too few tests:")
        for test_file, count in insufficient_tests:
            print(f"\n  File: {test_file}")
            print(f"  Found: {count} test functions")
            print(f"  Required: {args.min_tests} test functions")

        print("\n⚠️  Write comprehensive tests covering happy path, error cases, and edge cases.")
        print("📖 See docs/architecture/decisions/ADR-012.md for TDD requirements.")
        sys.exit(1)

    print(f"✅ TDD Check: All new test files have ≥{args.min_tests} test functions")
    sys.exit(0)


if __name__ == "__main__":
    main()
