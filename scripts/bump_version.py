#!/usr/bin/env python3
"""Automated version bumping based on conventional commits.

Reads git log since the last version tag and determines the appropriate
SemVer bump based on commit prefixes:
  - feat: -> MINOR bump
  - fix:, chore:, docs:, refactor:, style:, test:, perf:, ci: -> PATCH bump
  - BREAKING CHANGE or feat!: or fix!: -> MAJOR bump

Usage:
    python scripts/bump_version.py           # Auto-detect bump type
    python scripts/bump_version.py --major   # Force major bump
    python scripts/bump_version.py --minor   # Force minor bump
    python scripts/bump_version.py --patch   # Force patch bump
    python scripts/bump_version.py --dry-run # Show what would happen
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

VERSION_FILE = Path(__file__).parent.parent / "VERSION"


def get_current_version() -> str:
    """Read current version from VERSION file."""
    return VERSION_FILE.read_text().strip()


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse semver string into (major, minor, patch)."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version)
    if not match:
        print(f"Error: invalid version format '{version}'", file=sys.stderr)
        sys.exit(1)
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def get_commits_since_tag() -> list[str]:
    """Get commit messages since the last version tag."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            last_tag = result.stdout.strip()
            log_result = subprocess.run(
                ["git", "log", f"{last_tag}..HEAD", "--pretty=format:%s"],
                capture_output=True,
                text=True,
            )
            return [line for line in log_result.stdout.strip().split("\n") if line]
        else:
            log_result = subprocess.run(
                ["git", "log", "--pretty=format:%s"],
                capture_output=True,
                text=True,
            )
            return [line for line in log_result.stdout.strip().split("\n") if line]
    except FileNotFoundError:
        print("Error: git not found", file=sys.stderr)
        sys.exit(1)


def determine_bump_type(commits: list[str]) -> str:
    """Determine bump type from conventional commit messages.

    Returns: 'major', 'minor', or 'patch'
    """
    has_breaking = False
    has_feat = False

    for msg in commits:
        lower = msg.lower()
        if "breaking change" in lower or "!" in msg.split(":")[0]:
            has_breaking = True
        if lower.startswith("feat"):
            has_feat = True

    if has_breaking:
        return "major"
    if has_feat:
        return "minor"
    return "patch"


def bump_version(current: str, bump_type: str) -> str:
    """Apply bump to current version."""
    major, minor, patch = parse_version(current)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:
        return f"{major}.{minor}.{patch + 1}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Bump application version")
    parser.add_argument("--major", action="store_true", help="Force major bump")
    parser.add_argument("--minor", action="store_true", help="Force minor bump")
    parser.add_argument("--patch", action="store_true", help="Force patch bump")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = parser.parse_args()

    current = get_current_version()
    print(f"Current version: {current}")

    if args.major:
        bump_type = "major"
    elif args.minor:
        bump_type = "minor"
    elif args.patch:
        bump_type = "patch"
    else:
        commits = get_commits_since_tag()
        print(f"Found {len(commits)} commits since last tag")
        bump_type = determine_bump_type(commits)

    new_version = bump_version(current, bump_type)
    print(f"Bump type: {bump_type}")
    print(f"New version: {new_version}")

    if args.dry_run:
        print("Dry run — no changes made.")
        return

    VERSION_FILE.write_text(f"{new_version}\n")
    print(f"VERSION file updated to {new_version}")

    subprocess.run(["git", "tag", f"v{new_version}"], check=False)
    print(f"Git tag v{new_version} created")


if __name__ == "__main__":
    main()
