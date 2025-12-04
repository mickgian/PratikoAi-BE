#!/usr/bin/env python3
"""
Validate RSS feeds in database match sandbox allowlist.

This script checks that all enabled RSS feeds in the database have their
domains included in the sandbox configuration's allowedNetworkDomains.

Usage:
    python scripts/validate_rss_sandbox.py
    uv run python scripts/validate_rss_sandbox.py

Exit codes:
    0: All RSS feeds are allowed by sandbox config
    1: Some RSS feeds are NOT in sandbox allowlist (violations found)
    2: Configuration error (missing files, invalid JSON, etc.)
"""

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_sandbox_config() -> dict[str, object] | None:
    """Load RSS domain configuration from .claude/rss-domains.json."""
    config_path = project_root / ".claude" / "rss-domains.json"

    if not config_path.exists():
        print(f"⚠️  RSS domain config not found: {config_path}")
        print("   Create .claude/rss-domains.json with allowedNetworkDomains list.")
        return None

    try:
        with open(config_path) as f:
            result: dict[str, object] = json.load(f)
            return result
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in sandbox config: {e}")
        return None


def get_allowed_domains(config: dict[str, object]) -> list[str]:
    """Extract allowed network domains from sandbox config."""
    sandboxing = config.get("sandboxing", {})
    if isinstance(sandboxing, dict):
        domains = sandboxing.get("allowedNetworkDomains", [])
        if isinstance(domains, list):
            return [str(d) for d in domains]
    return []


def domain_matches_pattern(domain: str, pattern: str) -> bool:
    """Check if a domain matches an allowlist pattern.

    Supports:
    - Exact match: "github.com" matches "github.com"
    - Wildcard: "*.gov.it" matches "www.agenziaentrate.gov.it"
    """
    if pattern.startswith("*."):
        # Wildcard match: *.gov.it matches any subdomain of gov.it
        suffix = pattern[2:]  # Remove "*."
        return domain == suffix or domain.endswith("." + suffix)
    else:
        # Exact match
        return domain == pattern


def is_domain_allowed(domain: str, allowed_domains: list[str]) -> bool:
    """Check if a domain is in the allowed list."""
    return any(domain_matches_pattern(domain, pattern) for pattern in allowed_domains)


def validate_feeds_sync() -> tuple[list[str], list[str]]:
    """Validate RSS feeds against sandbox config (synchronous version).

    Returns:
        Tuple of (allowed_feeds, violation_feeds)
    """
    # Import here to avoid import errors if database is not configured
    try:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        from app.core.config import settings
        from app.models.regulatory_documents import FeedStatus
    except ImportError as e:
        print(f"⚠️  Could not import database modules: {e}")
        print("   This is OK if running as pre-commit hook without database.")
        return [], []

    # Get database URL (convert async URL to sync if needed)
    db_url = str(settings.POSTGRES_URL)
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        engine = create_engine(db_url)
        with Session(engine) as session:
            # Query enabled feeds
            query = select(FeedStatus).where(FeedStatus.enabled == True)  # noqa: E712
            result = session.execute(query)
            feeds = result.scalars().all()

            if not feeds:
                print("ℹ️  No enabled RSS feeds found in database.")
                return [], []

            return feeds, []
    except Exception as e:
        print(f"⚠️  Could not connect to database: {e}")
        print("   This is OK if running as pre-commit hook without database.")
        return [], []


def main() -> int:
    """Main validation function."""
    print("🔍 Validating RSS feeds against sandbox allowlist...")
    print()

    # Load sandbox config
    config = load_sandbox_config()
    if config is None:
        return 2

    # Check if sandbox is enabled
    if not config.get("enabled", True):
        print("ℹ️  Sandbox is disabled in config. Skipping validation.")
        return 0

    # Get allowed domains
    allowed_domains = get_allowed_domains(config)
    if not allowed_domains:
        print("⚠️  No allowedNetworkDomains found in sandbox config.")
        return 2

    print(f"📋 Loaded {len(allowed_domains)} allowed domain patterns")

    # Try to get feeds from database
    try:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        from app.core.config import settings
        from app.models.regulatory_documents import FeedStatus

        # Get database URL (convert async URL to sync if needed)
        db_url = str(settings.POSTGRES_URL)
        if db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

        engine = create_engine(db_url)
        with Session(engine) as session:
            query = select(FeedStatus).where(FeedStatus.enabled == True)  # noqa: E712
            result = session.execute(query)
            feeds = result.scalars().all()
    except Exception as e:
        print(f"⚠️  Could not query database: {e}")
        print("   Skipping database validation (pre-commit mode).")
        print()
        print("✅ Sandbox config is valid (database check skipped)")
        return 0

    if not feeds:
        print("ℹ️  No enabled RSS feeds found in database.")
        print()
        print("✅ No feeds to validate")
        return 0

    print(f"📡 Found {len(feeds)} enabled RSS feeds")
    print()

    # Validate each feed
    allowed = []
    violations = []

    for feed in feeds:
        url = feed.feed_url
        parsed = urlparse(url)
        domain = parsed.netloc

        if is_domain_allowed(domain, allowed_domains):
            allowed.append((feed.source or "unknown", url, domain))
        else:
            violations.append((feed.source or "unknown", url, domain))

    # Report results
    if allowed:
        print("✅ Allowed feeds:")
        for source, url, domain in allowed:
            print(f"   [{source}] {domain}")

    if violations:
        print()
        print("❌ VIOLATIONS - feeds NOT in sandbox allowlist:")
        for source, url, domain in violations:
            print(f"   [{source}] {domain}")
            print(f"      URL: {url}")
        print()
        print("🔧 To fix, add these domains to .claude/rss-domains.json:")
        print('   "allowedNetworkDomains": [')
        for _, _, domain in violations:
            print(f'     "{domain}",')
        print("     ... existing domains ...")
        print("   ]")
        return 1

    print()
    print("✅ All RSS feeds are allowed by sandbox config")
    return 0


if __name__ == "__main__":
    sys.exit(main())
