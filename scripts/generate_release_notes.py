#!/usr/bin/env python3
"""Generate release notes from git commits and store them in the database.

Reads conventional commits since the last version tag and generates:
- technical_notes: Detailed commit list for QA/internal teams
- user_notes: User-friendly summary in Italian for production

Usage:
    python scripts/generate_release_notes.py                    # Generate for current VERSION
    python scripts/generate_release_notes.py --version 0.3.0    # Generate for specific version
    python scripts/generate_release_notes.py --dry-run           # Preview without saving
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

VERSION_FILE = Path(__file__).parent.parent / "VERSION"

# Conventional commit type to Italian label mapping
COMMIT_TYPE_LABELS = {
    "feat": "Nuova funzionalità",
    "fix": "Correzione",
    "perf": "Miglioramento prestazioni",
    "refactor": "Miglioramento interno",
    "docs": "Documentazione",
    "style": "Stile",
    "test": "Test",
    "ci": "Infrastruttura",
    "chore": "Manutenzione",
    "build": "Build",
}


def get_current_version() -> str:
    """Read current version from VERSION file."""
    return VERSION_FILE.read_text().strip()


def get_commits_since_tag() -> list[dict[str, str]]:
    """Get structured commit info since the last version tag."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
        )
        range_spec = f"{result.stdout.strip()}..HEAD" if result.returncode == 0 else ""

        cmd = ["git", "log", "--pretty=format:%H|%s|%an"]
        if range_spec:
            cmd.insert(2, range_spec)

        log_result = subprocess.run(cmd, capture_output=True, text=True)
        commits = []
        for line in log_result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append({"hash": parts[0][:8], "message": parts[1], "author": parts[2]})
        return commits
    except FileNotFoundError:
        print("Error: git not found", file=sys.stderr)
        sys.exit(1)


def parse_commit_type(message: str) -> str:
    """Extract conventional commit type from message."""
    match = re.match(r"^(\w+?)(?:\(.+?\))?!?:", message)
    if match:
        return match.group(1).lower()
    return "other"


def generate_technical_notes(version: str, commits: list[dict[str, str]]) -> str:
    """Generate technical release notes with full commit details."""
    lines = [f"# Release {version}", f"Released: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}", ""]

    categorized: dict[str, list[dict[str, str]]] = {}
    for commit in commits:
        commit_type = parse_commit_type(commit["message"])
        categorized.setdefault(commit_type, []).append(commit)

    type_order = ["feat", "fix", "perf", "refactor", "docs", "test", "ci", "chore", "build", "other"]
    for commit_type in type_order:
        if commit_type not in categorized:
            continue
        label = COMMIT_TYPE_LABELS.get(commit_type, commit_type.capitalize())
        lines.append(f"## {label}")
        for commit in categorized[commit_type]:
            lines.append(f"- {commit['message']} ({commit['hash']})")
        lines.append("")

    lines.append(f"Total commits: {len(commits)}")
    return "\n".join(lines)


def generate_user_notes(version: str, commits: list[dict[str, str]]) -> str:
    """Generate user-friendly release notes in Italian."""
    features = []
    fixes = []
    improvements = []

    for commit in commits:
        commit_type = parse_commit_type(commit["message"])
        # Strip the conventional commit prefix for user display
        clean_msg = re.sub(r"^\w+(?:\(.+?\))?!?:\s*", "", commit["message"])

        if commit_type == "feat":
            features.append(clean_msg)
        elif commit_type == "fix":
            fixes.append(clean_msg)
        elif commit_type in ("perf", "refactor"):
            improvements.append(clean_msg)

    lines = [f"Versione {version}", ""]

    if features:
        lines.append("Novità:")
        for f in features:
            lines.append(f"- {f}")
        lines.append("")

    if fixes:
        lines.append("Correzioni:")
        for f in fixes:
            lines.append(f"- {f}")
        lines.append("")

    if improvements:
        lines.append("Miglioramenti:")
        for i in improvements:
            lines.append(f"- {i}")
        lines.append("")

    if not features and not fixes and not improvements:
        lines.append("Miglioramenti interni e ottimizzazioni.")

    return "\n".join(lines)


def save_to_database(version: str, user_notes: str, technical_notes: str) -> bool:
    """Save release note to the database."""
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env.development")

        from sqlalchemy import create_engine, select
        from sqlmodel import Session

        from app.models.release_note import ReleaseNote

        db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
        if not db_url:
            print("Warning: No DATABASE_URL set, skipping database save", file=sys.stderr)
            return False

        db_url = db_url.replace("+asyncpg", "")
        engine = create_engine(db_url)

        with Session(engine) as session:
            existing = session.exec(select(ReleaseNote).where(ReleaseNote.version == version)).first()
            if existing:
                existing.user_notes = user_notes
                existing.technical_notes = technical_notes
                print(f"Updated existing release note for v{version}")
            else:
                note = ReleaseNote(
                    version=version,
                    user_notes=user_notes,
                    technical_notes=technical_notes,
                    released_at=datetime.now(UTC),
                )
                session.add(note)
                print(f"Created new release note for v{version}")

            session.commit()
        return True
    except Exception as e:
        print(f"Warning: Could not save to database: {e}", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate release notes")
    parser.add_argument("--version", type=str, help="Version to generate notes for")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    args = parser.parse_args()

    version = args.version or get_current_version()
    commits = get_commits_since_tag()

    if not commits:
        print("No commits found since last tag.")
        return

    print(f"Generating release notes for v{version} ({len(commits)} commits)")

    technical_notes = generate_technical_notes(version, commits)
    user_notes = generate_user_notes(version, commits)

    print("\n=== Technical Notes ===")
    print(technical_notes)
    print("\n=== User Notes (Italian) ===")
    print(user_notes)

    if args.dry_run:
        print("\nDry run — no changes saved.")
        return

    saved = save_to_database(version, user_notes, technical_notes)
    if saved:
        print(f"\nRelease notes for v{version} saved to database.")
    else:
        print("\nRelease notes generated but not saved to database.")


if __name__ == "__main__":
    main()
