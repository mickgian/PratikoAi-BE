#!/usr/bin/env python3
"""
Pre-commit script to check for sensitive data in files being committed.

This script prevents accidental commits of:
- Personal email addresses
- API keys
- Passwords
- Other sensitive information
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import (
    List,
    Tuple,
)

# Patterns to detect sensitive data
SENSITIVE_PATTERNS = [
    # Personal email detection (specific known emails)
    (r"michele\.giannone@gmail\.com", "Personal email address"),
    # Generic personal email patterns
    (r"\b[a-zA-Z0-9._%+-]+@(gmail|yahoo|hotmail|outlook)\.(com|it|net|org)\b", "Personal email address"),
    # API Keys patterns
    (r"sk_live_[a-zA-Z0-9]{24,}", "Stripe live API key"),
    (r"sk-proj-[a-zA-Z0-9]{48,}", "OpenAI API key"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    # Generic secret patterns
    (r'(password|passwd|pwd)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded password"),
    (r'(secret|token)\s*=\s*["\'][^"\']{16,}["\']', "Hardcoded secret/token"),
    # Private keys
    (r"-----BEGIN (RSA |EC )?PRIVATE KEY-----", "Private key"),
    # Database URLs with credentials
    (r"postgresql://[^:]+:[^@]+@[^/]+/\w+", "Database URL with credentials"),
    (r"mysql://[^:]+:[^@]+@[^/]+/\w+", "Database URL with credentials"),
    # JWT secrets (if they look like real secrets)
    (r'JWT_SECRET_KEY\s*=\s*["\'][^"\']{32,}["\']', "JWT secret key"),
]

# File extensions to check
CHECKED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".env",
    ".example",
    ".config",
    ".conf",
}

# Files/patterns to exclude from checks
EXCLUDED_PATTERNS = [
    r"\.env$",  # Actual .env files (not .env.example)
    r"\.env\.\w+$",  # .env.development, .env.production, etc.
    r"\.github/workflows/",  # GitHub Actions workflows (contain test credentials for CI)
    r"docker-compose.*\.yml$",  # Docker Compose files use env var references, not real secrets
    r"__pycache__",
    r"\.git/",
    r"node_modules/",
    r"\.pytest_cache/",
]


def get_staged_files() -> list[str]:
    """Get list of files staged for commit."""
    try:
        result = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True)
        return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except subprocess.CalledProcessError:
        print("Error: Could not get staged files")
        sys.exit(1)


def should_check_file(filepath: str) -> bool:
    """Determine if a file should be checked for sensitive data."""
    path = Path(filepath)

    # Check if file is excluded
    for pattern in EXCLUDED_PATTERNS:
        if re.search(pattern, filepath):
            return False

    # Check if file extension is in our check list
    return path.suffix.lower() in CHECKED_EXTENSIONS


def check_file_for_sensitive_data(filepath: str) -> list[tuple[int, str, str]]:
    """Check a file for sensitive data patterns."""
    issues = []

    try:
        with open(filepath, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                # Skip lines with pragma allowlist comment
                if "pragma: allowlist secret" in line:
                    continue

                for pattern, description in SENSITIVE_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Don't flag example, placeholder, or test values
                        if any(
                            placeholder in line.lower()
                            for placeholder in [
                                "example",
                                "your-",
                                "placeholder",
                                "changeme",
                                "xxx",
                                "test-",
                                "mock-",
                                "fake-",
                            ]
                        ):
                            continue

                        # Don't flag test files with obvious test values
                        if "/test" in filepath.lower() and any(
                            test_indicator in line.lower() for test_indicator in ["test@", "test-", "mock", "fake"]
                        ):
                            continue

                        issues.append((line_num, description, line.strip()))
    except Exception as e:
        print(f"Warning: Could not check {filepath}: {e}")

    return issues


def main():
    """Main function to check all staged files."""
    print("🔍 Checking staged files for sensitive data...")

    staged_files = get_staged_files()
    if not staged_files:
        print("No files staged for commit.")
        return 0

    all_issues = []

    for filepath in staged_files:
        if should_check_file(filepath):
            issues = check_file_for_sensitive_data(filepath)
            if issues:
                all_issues.append((filepath, issues))

    if all_issues:
        print("\n❌ SENSITIVE DATA DETECTED! Commit blocked.\n")

        for filepath, issues in all_issues:
            print(f"📄 {filepath}:")
            for line_num, description, line_content in issues:
                print(f"   Line {line_num}: {description}")
                print(f"   > {line_content[:100]}...")
            print()

        print("🛡️ Security Tips:")
        print("- Use environment variables for sensitive data")
        print("- Add example values with placeholders (your-email@example.com)")
        print("- Never commit real API keys, passwords, or personal emails")
        print("- Check .gitignore includes all .env files")
        print("\nTo bypass this check (NOT RECOMMENDED):")
        print("  git commit --no-verify")

        return 1

    print("✅ No sensitive data detected in staged files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
