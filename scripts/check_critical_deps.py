#!/usr/bin/env python3
"""Pre-commit hook to check critical dependencies in pyproject.toml"""

import sys
from pathlib import Path


def main():
    # Read pyproject.toml
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("❌ pyproject.toml not found")
        sys.exit(1)

    content = pyproject_path.read_text()

    # Define critical dependencies
    critical_deps = ["pgvector", "asyncpg", "feedparser", "sentence-transformers"]

    # Check for missing dependencies
    missing = [dep for dep in critical_deps if dep not in content]

    if missing:
        print(f"❌ Missing critical dependencies: {missing}")
        sys.exit(1)
    else:
        print("✅ All critical dependencies present")
        sys.exit(0)


if __name__ == "__main__":
    main()
