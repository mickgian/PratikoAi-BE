#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create (idempotently) all GitHub issue labels needed by the RAG workflow.

- Core labels (rag, needs/functional-align)
- Status labels (status/*)
- Area labels (area/*)
- Step labels (step/1..N, default N=135)

Usage:
  python scripts/rag_labels_bootstrap.py
  python scripts/rag_labels_bootstrap.py --steps-max 135
  python scripts/rag_labels_bootstrap.py --areas providers,cache,kb
  python scripts/rag_labels_bootstrap.py --dry-run

Requirements:
  - Run from the repo root (where `.git` lives)
  - GitHub CLI (`gh`) installed and authenticated for this repo
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from typing import Dict, Iterable, List, Set


CORE_LABELS: Dict[str, Dict] = {
    "rag": {"color": "6f42c1", "description": "RAG work item"},
    "needs/functional-align": {
        "color": "1f6feb",
        "description": "Implement real node behavior (not logs-only)",
    },
}

STATUS_LABELS: Dict[str, Dict] = {
    "status/implemented": {"color": "0e8a16", "description": "✅ Implemented"},
    "status/partial": {"color": "fbca04", "description": "🟡 Partial"},
    "status/not-wired": {"color": "c2e0c6", "description": "🔌 Exists, not wired"},
    "status/missing": {"color": "b60205", "description": "❌ Missing"},
    "status/unknown": {"color": "d4c5f9", "description": "❓ Unknown"},
}

DEFAULT_AREAS: List[str] = [
    "platform",
    "privacy",
    "response",
    "preflight",
    "classify",
    "facts",
    "docs",
    "golden",
    "kb",
    "llm",
    "providers",
    "cache",
    "ccnl",
    "routing",
    "streaming",
    "metrics",
    "feedback",
]

AREA_COLOR = "0366d6"
STEP_COLOR = "ededed"


def run_gh(args: List[str], *, check: bool = True) -> subprocess.CompletedProcess:
    """Run a gh command and return the process."""
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f"gh {' '.join(args)} failed")
    return proc


def ensure_gh_available() -> None:
    if shutil.which("gh") is None:
        raise SystemExit("ERROR: GitHub CLI `gh` not found on PATH.")
    try:
        run_gh(["repo", "view"], check=True)
    except Exception as e:
        raise SystemExit(
            "ERROR: `gh repo view` failed. Ensure you run from the repo root and are authenticated.\n"
            f"Details: {e}"
        )


def list_existing_labels() -> Set[str]:
    try:
        proc = run_gh(["label", "list", "--json", "name"], check=True)
        data = json.loads(proc.stdout or "[]")
        return {item.get("name", "") for item in data if item.get("name")}
    except Exception:
        # Fallback: empty set; we'll attempt create and ignore 'already exists'.
        return set()


def create_label(name: str, color: str, description: str = "", *, dry_run: bool = False) -> None:
    if dry_run:
        print(f"[dry-run] gh label create '{name}' -c {color} -d '{description}'")
        return
    # Try create; ignore error if already exists
    args = ["label", "create", name, "-c", color]
    if description:
        args += ["-d", description]
    proc = run_gh(args, check=False)
    if proc.returncode == 0:
        print(f"✅ created: {name}")
    else:
        # If it already exists, gh returns non-zero. We treat as ok.
        print(f"ℹ️  exists or could not create '{name}': {proc.stderr.strip() or proc.stdout.strip()}")


def ensure_labels(core: Dict[str, Dict], status: Dict[str, Dict],
                  areas: Iterable[str], steps_max: int,
                  *, dry_run: bool = False) -> None:
    existing = list_existing_labels()

    # Core
    for name, meta in core.items():
        if name not in existing:
            create_label(name, meta["color"], meta.get("description", ""), dry_run=dry_run)
        else:
            print(f"✔ core: {name} exists")

    # Status
    for name, meta in status.items():
        if name not in existing:
            create_label(name, meta["color"], meta.get("description", ""), dry_run=dry_run)
        else:
            print(f"✔ status: {name} exists")

    # Areas
    for area in areas:
        label = f"area/{area}"
        if label not in existing:
            create_label(label, AREA_COLOR, f"Area: {area}", dry_run=dry_run)
        else:
            print(f"✔ area: {label} exists")

    # Steps
    for i in range(1, steps_max + 1):
        label = f"step/{i}"
        if label not in existing:
            create_label(label, STEP_COLOR, f"RAG step {i}", dry_run=dry_run)
        else:
            print(f"✔ step: {label} exists")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Bootstrap GitHub labels for RAG workflow.")
    ap.add_argument(
        "--steps-max",
        type=int,
        default=135,
        help="Highest step number to label (default: 135).",
    )
    ap.add_argument(
        "--areas",
        type=str,
        default=",".join(DEFAULT_AREAS),
        help="Comma-separated list of area labels to ensure (default: a standard set).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print gh commands instead of executing.",
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_gh_available()
    areas = [a.strip() for a in args.areas.split(",") if a.strip()]
    print(f"Repo detected by `gh repo view`. Creating labels up to step/{args.steps_max} …\n")
    ensure_labels(CORE_LABELS, STATUS_LABELS, areas, args.steps_max, dry_run=args.dry_run)
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
