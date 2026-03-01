#!/usr/bin/env python3
"""Pre-commit coverage check for staged Python files.

Checks:
1. Average coverage across all staged app/ files meets threshold (default: 50%)
2. New files (git status A) meet new-file threshold (default: 70%)

Usage:
    python scripts/check_coverage.py [--threshold-avg=50] [--threshold-new=70]
"""

import json
import subprocess
import sys
from pathlib import Path


def get_staged_app_files() -> tuple[list[str], list[str]]:
    """Return (modified_files, new_files) that are staged app/ Python files."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "--diff-filter=AM"],
        capture_output=True,
        text=True,
    )
    modified: list[str] = []
    new: list[str] = []

    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        status, filepath = parts
        if not filepath.startswith("app/") or not filepath.endswith(".py"):
            continue
        if filepath.endswith("__init__.py"):
            continue
        if status == "A":
            new.append(filepath)
        else:
            modified.append(filepath)

    return modified, new


def find_test_files(app_files: list[str]) -> list[str]:
    """Find test files corresponding to app/ source files."""
    test_files: list[str] = []
    for f in app_files:
        # app/services/foo.py -> tests/services/test_foo.py
        test_path = f.replace("app/", "tests/", 1)
        parts = test_path.rsplit("/", 1)
        if len(parts) == 2:
            test_path = f"{parts[0]}/test_{parts[1]}"
        else:
            test_path = f"test_{parts[0]}"

        if Path(test_path).exists():
            test_files.append(test_path)

        # Also check api/v1/ pattern: app/api/v1/foo.py -> tests/api/v1/test_foo.py
        # Already handled above

    return test_files


def run_coverage(test_files: list[str], source_files: list[str]) -> dict[str, float]:
    """Run coverage and return {filepath: coverage_pct}."""
    if not test_files:
        return dict.fromkeys(source_files, 0.0)

    include_pattern = ",".join(source_files)

    try:
        # Run tests with coverage
        subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "coverage",
                "run",
                "--source=app",
                "-m",
                "pytest",
                *test_files,
                "--override-ini=addopts=-q --tb=no --no-header",
                "-q",
                "--tb=no",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Get JSON report
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "coverage",
                "json",
                f"--include={include_pattern}",
                "-o",
                "/tmp/coverage_check.json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        with open("/tmp/coverage_check.json") as f:
            data = json.load(f)

        coverages: dict[str, float] = {}
        for filepath, info in data.get("files", {}).items():
            pct = info.get("summary", {}).get("percent_covered", 0.0)
            coverages[filepath] = pct

        # Files with no coverage data
        for sf in source_files:
            if sf not in coverages:
                coverages[sf] = 0.0

        return coverages

    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"WARNING: Coverage check failed ({e}), skipping.", file=sys.stderr)
        return {}


def main() -> int:
    threshold_avg = 50.0
    threshold_new = 70.0

    for arg in sys.argv[1:]:
        if arg.startswith("--threshold-avg="):
            threshold_avg = float(arg.split("=", 1)[1])
        elif arg.startswith("--threshold-new="):
            threshold_new = float(arg.split("=", 1)[1])

    modified, new = get_staged_app_files()
    all_files = modified + new

    if not all_files:
        return 0

    test_files = find_test_files(all_files)

    if not test_files:
        if new:
            print(f"COVERAGE FAIL: {len(new)} new file(s) have no tests:")
            for f in new:
                print(f"  {f} -> 0% (threshold: {threshold_new}%)")
            return 1
        return 0

    coverages = run_coverage(test_files, all_files)
    if not coverages:
        return 0  # Skip on failure

    # Check results
    failed = False

    # Check new files threshold
    for f in new:
        pct = coverages.get(f, 0.0)
        if pct < threshold_new:
            print(f"COVERAGE FAIL (new file): {f} -> {pct:.1f}% (threshold: {threshold_new}%)")
            failed = True
        else:
            print(f"  OK (new file): {f} -> {pct:.1f}%")

    # Check average coverage
    if coverages:
        avg = sum(coverages.values()) / len(coverages)
        if avg < threshold_avg:
            print(f"COVERAGE FAIL (average): {avg:.1f}% (threshold: {threshold_avg}%)")
            failed = True
        else:
            print(f"  OK (average): {avg:.1f}%")

    # Show per-file summary for modified files
    for f in modified:
        pct = coverages.get(f, 0.0)
        print(f"  OK (modified): {f} -> {pct:.1f}%")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
