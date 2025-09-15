#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate GitHub issues (Claude Code–ready) for PratikoAI RAG steps.

- Builds one issue per step using:
  - Master Guardrails (prepend to every body)
  - Per-step "Task" section with TDD + acceptance criteria
  - AUTO-AUDIT suggestions parsed from the step docs
- Skips duplicates (checks with `gh issue list`)
- Lets you filter by step numbers, category, and audit status.
- Idempotent. No local backlog files are created.

Usage examples:
  # Pure preview (no gh needed)
  python scripts/rag_issue_prompter.py --dry-run
  python scripts/rag_issue_prompter.py --dry-run --status "❌,🔌" --steps 20,39,59,79,82,64

  # Preview with same flags as creation (still no gh needed)
  python scripts/rag_issue_prompter.py --create --dry-run

  # Actually create (requires GitHub CLI `gh` installed and authenticated)
  python scripts/rag_issue_prompter.py --create --steps 20,39,59,79,82,64 --assignee your-gh-user
  python scripts/rag_issue_prompter.py --create --status "❌,🔌" --labels "priority/high"
  python scripts/rag_issue_prompter.py --create --category golden,kb
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

BASE_DIR = Path(__file__).parent.parent
STEPS_DIR = BASE_DIR / "docs/architecture/steps"
STEPS_REGISTRY = BASE_DIR / "docs/architecture/rag_steps.yml"
DASHBOARD = BASE_DIR / "docs/architecture/rag_conformance.md"
MERMAID = BASE_DIR / "docs/architecture/diagrams/pratikoai_rag.mmd"

# Note: Avoid triple backtick fences here to prevent accidental quote breakage in some editors.
MASTER_GUARDRAILS = '''\
**Mode & repo rules (DO NOT SKIP)**
- Mermaid single source of truth: docs/architecture/diagrams/pratikoai_rag.mmd
- Step docs live in docs/architecture/steps/STEP-*.md
- Conformance dashboard: docs/architecture/rag_conformance.md. Do NOT create docs/backlog/ files.
- Use TDD: write/adjust tests first, then code.
- No broad refactors or file moves unless explicitly requested in this step.
- Use structured logs via:
  from app.observability.rag_logging import rag_step_log, rag_step_timer
  Example:
    rag_step_log(step=STEP_NUMBER, id="RAG.<category>.<slug>", node="NodeName", msg="...", attrs={...})
- After changes, regenerate audit:
    python scripts/rag_code_graph.py --write
    python scripts/rag_audit.py --write
- Keep diffs minimal and idempotent. If touching config, use feature flags and safe defaults.
'''

DEFAULT_LABELS = ["rag"]
STATUS_LABEL_MAP = {
    "✅": "status/implemented",
    "🟡": "status/partial",
    "🔌": "status/not-wired",
    "❌": "status/missing",
    "❓": "status/unknown",
}

def load_steps_registry() -> List[Dict]:
    if not STEPS_REGISTRY.exists():
        print(f"ERROR: Steps registry missing: {STEPS_REGISTRY}")
        sys.exit(1)
    with open(STEPS_REGISTRY, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("steps", [])

def parse_step_doc(step_num: int, step_id: str) -> Tuple[str, Dict]:
    """
    Return full text and parsed AUTO-AUDIT block (status, confidence, suggestions).
    """
    doc_path = STEPS_DIR / f"STEP-{step_num}-{step_id}.md"
    if not doc_path.exists():
        return "", {"status": "❓", "confidence": 0.0, "suggestions": []}
    text = doc_path.read_text(encoding="utf-8")

    audit = {"status": "❓", "confidence": 0.0, "suggestions": []}
    m = re.search(r"<!-- AUTO-AUDIT:BEGIN -->(.*?)<!-- AUTO-AUDIT:END -->", text, re.DOTALL)
    if m:
        block = m.group(1)
        sm = re.search(r"Status:\s*([✅🟡🔌❌❓])\s*\|\s*Confidence:\s*([\d.]+)", block)
        if sm:
            audit["status"] = sm.group(1)
            try:
                audit["confidence"] = float(sm.group(2))
            except ValueError:
                audit["confidence"] = 0.0
        sug_section = re.search(r"Suggested next TDD actions:(.*?)(?=\n\n|\n<!--|\Z)", block, re.DOTALL)
        if sug_section:
            lines = [ln.strip() for ln in sug_section.group(1).strip().splitlines()]
            for ln in lines:
                if ln.startswith("- "):
                    audit["suggestions"].append(ln[2:])
    return text, audit

def gh_available() -> bool:
    try:
        subprocess.run(["gh", "--version"], check=True, capture_output=True)
        return True
    except Exception:
        return False

def get_existing_issue_titles() -> List[str]:
    try:
        out = subprocess.run(
            ["gh", "issue", "list", "--state", "open", "--json", "title", "--limit", "1000"],
            check=True, capture_output=True, text=True, cwd=BASE_DIR,
        )
        data = json.loads(out.stdout or "[]")
        return [d["title"] for d in data]
    except Exception as e:
        print(f"⚠️  Warning: Could not list existing issues via gh: {e}")
        return []

def build_issue_title(step_num: int, node_label: str, step_id: str) -> str:
    return f"Implement RAG STEP {step_num} — {node_label} ({step_id})"

def build_issue_body(step: Dict, audit: Dict, include_guardrails: bool = True) -> str:
    step_num = step["step"]
    node_label = step["node_label"]
    step_id = step["id"]
    node_id = step["node_id"]
    step_type = step["type"]
    category = step["category"]

    # Checklist from AUTO-AUDIT suggestions (if any)
    if audit.get("suggestions"):
        checklist = "\n".join(f"- [ ] {s}" for s in audit["suggestions"])
    else:
        checklist = "- [ ] Implement per step doc and TDD template"

    guard = MASTER_GUARDRAILS if include_guardrails else ""
    body = f'''\
{guard}

**Task: Implement RAG STEP {step_num} — {node_label} (`{step_id}`)**

**Scope**
- Align code with the approved RAG blueprint (Mermaid is the source of truth).
- Implement exactly this step and minimal wiring to/from neighbors. No repo-wide refactors.

**Files of interest**
- Mermaid diagram: docs/architecture/diagrams/pratikoai_rag.mmd
- Step doc: docs/architecture/steps/STEP-{step_num}-{step_id}.md
- Observability: app/observability/rag_logging.py

**What to do (TDD)**
1) Tests first: unit/integration covering the expected behavior of this step.
2) Implement the minimal code to pass tests.
3) Logging: add rag_step_log(...) and optionally rag_step_timer(...).
4) Docs sync: run audit tools and ensure the step doc auto-audit block reflects progress.

**Acceptance criteria**
- Tests pass locally.
- python scripts/rag_audit.py --write updates this step’s status away from ❌/🔌.
- No new folders like docs/backlog/.
- Structured log lines present for this step:
  RAG STEP {step_num} ({step_id})

**Implementation Checklist (from AUTO-AUDIT)**
{checklist}

**Links**
- Step doc: docs/architecture/steps/STEP-{step_num}-{step_id}.md
- Conformance dashboard: docs/architecture/rag_conformance.md
- Mermaid: docs/architecture/diagrams/pratikoai_rag.mmd

**Meta**
- Step: {step_num}
- Type: {step_type}
- Category: {category}
- Node: {node_id}
- Current status: {audit.get('status','❓')} (confidence: {audit.get('confidence',0.0):.2f})
'''
    return body

def parse_list_arg(val: Optional[str]) -> List[str]:
    if not val:
        return []
    return [v.strip() for v in val.split(",") if v.strip()]

def main():
    ap = argparse.ArgumentParser(description="Generate Claude-Code–ready GitHub issues for RAG steps")
    ap.add_argument("--create", action="store_true", help="Actually create issues via gh")
    ap.add_argument("--dry-run", action="store_true", help="Preview only, do not call gh")
    ap.add_argument("--steps", type=str, help="Comma-separated step numbers to include (e.g., 20,39,59)")
    ap.add_argument("--category", type=str, help="Comma-separated categories to include (e.g., golden,kb,cache)")
    ap.add_argument("--status", type=str, help="Comma-separated audit statuses to include (e.g., ❌,🔌,🟡). Defaults to all non-✅.")
    ap.add_argument("--assignee", type=str, help="GitHub username to assign issues to")
    ap.add_argument("--labels", type=str, help="Comma-separated extra labels to add (e.g., priority/high,team/rag)")
    ap.add_argument("--include-implemented", action="store_true", help="Include ✅ steps too")
    ap.add_argument("--no-guardrails", action="store_true", help="Do not include the Master Guardrails block")
    args = ap.parse_args()

    steps = load_steps_registry()

    filter_steps = set(int(s) for s in parse_list_arg(args.steps)) if args.steps else None
    filter_cats = set(parse_list_arg(args.category)) if args.category else None
    filter_status = set(parse_list_arg(args.status)) if args.status else None

    # Only require GitHub CLI if we will actually create (not during dry-run)
    if args.create and not args.dry_run and not gh_available():
        print("ERROR: GitHub CLI `gh` not found. Install and authenticate before using --create.")
        sys.exit(1)

    existing_titles = get_existing_issue_titles() if (args.create and not args.dry_run) else []

    to_create: List[Tuple[str, str, Dict]] = []

    for step in steps:
        step_num = step["step"]
        step_id = step["id"]
        node_label = step["node_label"]
        category = step["category"]

        if filter_steps and step_num not in filter_steps:
            continue
        if filter_cats and category not in filter_cats:
            continue

        _, audit = parse_step_doc(step_num, step_id)
        current_status = audit.get("status", "❓")

        if not args.include_implemented and current_status == "✅":
            continue
        if filter_status and current_status not in filter_status:
            continue

        title = build_issue_title(step_num, node_label, step_id)
        body = build_issue_body(step, audit, include_guardrails=not args.no_guardrails)

        to_create.append((title, body, step))

    if not to_create:
        print("Nothing to do with current filters.")
        return 0

    # Dry-run preview
    if args.dry_run or not args.create:
        print(f"🔍 Would create {len(to_create)} issues:")
        for i, (title, _, step) in enumerate(to_create[:10], 1):
            print(f"  {i:>2}. #{step['step']}  {title}")
        if len(to_create) > 10:
            print(f"  ... and {len(to_create)-10} more")
        # If not creating, or dry-run requested, stop here
        if not args.create or args.dry_run:
            return 0

    # Create issues via gh
    created = 0
    skipped = 0
    extra_labels = parse_list_arg(args.labels)
    for title, body, step in to_create:
        if title in existing_titles:
            print(f"⏭️  Skip (exists): {title}")
            skipped += 1
            continue

        labels = list(DEFAULT_LABELS)
        labels.append(f"step/{step['step']}")
        labels.append(f"area/{step['category']}")
        # Add status label
        _, audit = parse_step_doc(step["step"], step["id"])
        status_label = STATUS_LABEL_MAP.get(audit.get("status", "❓"), "status/unknown")
        labels.append(status_label)
        labels.extend(extra_labels)

        cmd = [
            "gh", "issue", "create",
            "--title", title,
            "--body", body,
            "--label", ",".join(labels)
        ]
        if args.assignee:
            cmd.extend(["--assignee", args.assignee])

        try:
            res = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=BASE_DIR)
            url = (res.stdout or "").strip()
            print(f"✅ Created: {title}  -> {url}")
            created += 1
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create: {title}")
            if e.stderr:
                print(e.stderr)
            else:
                print(str(e))

    print(f"\nDone. Created: {created}, Skipped (exists): {skipped}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
