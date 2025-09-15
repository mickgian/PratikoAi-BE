#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seed/ensure GitHub issue labels used by the PratikoAI RAG pipeline.

- Creates core labels: rag, team/rag, priority/*, status/*, area/*, sprint/*.
- Optionally creates step/* for every step in docs/architecture/rag_steps.yml.
- Idempotent: uses `gh label create --force` so re-runs are safe.
- Requires: GitHub CLI `gh` (authenticated).

Usage:
  python scripts/rag_labels.py                      # create core labels (no step/*)
  python scripts/rag_labels.py --with-steps        # also create step/1..N (N read from rag_steps.yml)
  python scripts/rag_labels.py --repo owner/repo   # target a specific repo
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).parent.parent
STEPS_REGISTRY = BASE_DIR / "docs/architecture/rag_steps.yml"

# Minimal YAML loader without PyYAML dependency fallback
def _load_yaml_fast(path: Path) -> Dict:
    try:
        import yaml  # type: ignore
    except Exception:
        # Extremely tiny fallback: assume file has a "steps:" top key and we only need len(steps)
        text = path.read_text(encoding="utf-8")
        # crude count of "- step:" occurrences
        count = text.count("\n  - step:")
        return {"steps": [{"step": i+1} for i in range(count)]}
    else:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

def run(cmd: List[str], repo: str = "") -> None:
    args = ["gh"] + cmd
    if repo:
        args += ["--repo", repo]
    try:
        subprocess.run(args, check=True)
    except subprocess.CalledProcessError as e:
        # show a compact error but keep going if it's a harmless conflict
        msg = (e.stderr or e.stdout or str(e)).strip()
        print(f"⚠️  gh error on: {' '.join(args)}\n    {msg}")

def ensure_label(name: str, color: str, desc: str, repo: str = "") -> None:
    # --force is idempotent: creates or updates
    run(["label", "create", name, "--color", color, "--description", desc, "--force"], repo=repo)

def main() -> int:
    ap = argparse.ArgumentParser(description="Seed/ensure GitHub labels for RAG workflow")
    ap.add_argument("--with-steps", action="store_true", help="Also create step/{n} labels for all steps in rag_steps.yml")
    ap.add_argument("--repo", type=str, default="", help="owner/repo to target (defaults to current git repo)")
    args = ap.parse_args()

    # Core labels
    ensure_label("rag", "0E8A16", "RAG work item", repo=args.repo)
    ensure_label("team/rag", "0366D6", "RAG team", repo=args.repo)

    # Priorities
    ensure_label("priority/high",   "D73A4A", "High priority", repo=args.repo)
    ensure_label("priority/medium", "FBCA04", "Medium priority", repo=args.repo)
    ensure_label("priority/low",    "C5DEF5", "Low priority", repo=args.repo)

    # Statuses
    ensure_label("status/implemented", "0E8A16", "✅ Implemented", repo=args.repo)
    ensure_label("status/partial",     "FBCA04", "🟡 Partial", repo=args.repo)
    ensure_label("status/not-wired",   "C5DEF5", "🔌 Exists, not wired", repo=args.repo)
    ensure_label("status/missing",     "D73A4A", "❌ Missing", repo=args.repo)
    ensure_label("status/unknown",     "BFDADC", "❓ Unknown", repo=args.repo)

    # Areas (categories from the blueprint)
    areas = [
        "cache","ccnl","classify","docs","facts","feedback","golden","kb",
        "llm","metrics","platform","preflight","privacy","prompting","providers",
        "response","routing","streaming"
    ]
    for a in areas:
        ensure_label(f"area/{a}", "5319E7", f"Area: {a}", repo=args.repo)

    # Sprints (from rag_sprints.md)
    sprints = [
        "sprint/1-core","sprint/2-retrieval","sprint/3-providers-cache","sprint/4-doc-ingest-I",
        "sprint/5-doc-ingest-II","sprint/6-golden","sprint/7-kb-rss","sprint/8-classify-facts",
        "sprint/9-response-streaming","sprint/10-feedback","sprint/11-platform-privacy"
    ]
    for s in sprints:
        ensure_label(s, "A2EEEF", f"Sprint bucket: {s}", repo=args.repo)

    # Step labels (optional)
    if args.with_steps:
        if not STEPS_REGISTRY.exists():
            print(f"ERROR: Cannot find steps registry: {STEPS_REGISTRY}")
            return 1
        data = _load_yaml_fast(STEPS_REGISTRY)
        steps = data.get("steps", [])
        total = len(steps)
        if not total:
            print("WARNING: 0 steps found in rag_steps.yml; skipping step/* labels.")
        else:
            print(f"Creating step/* labels for {total} steps...")
            for s in steps:
                n = s.get("step")
                if not isinstance(n, int):
                    continue
                ensure_label(f"step/{n}", "E99695", f"RAG step {n}", repo=args.repo)

    print("✅ Labels ensured.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
