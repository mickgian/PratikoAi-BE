#!/usr/bin/env python3
"""
next_issue.py — Print the "next" open RAG issue (by ascending number) and a mini checklist.
Requires: GitHub CLI `gh` (authenticated)

Usage:
  python scripts/next_issue.py                            # default labels: rag,team/rag,priority/high
  python scripts/next_issue.py --labels "rag,team/rag"    # custom labels
  python scripts/next_issue.py --state open               # open|closed|all (default: open)
  python scripts/next_issue.py --repo owner/repo          # override detected repo
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def have_gh() -> bool:
    return shutil.which("gh") is not None


def gh_json(args: list[str]) -> Any:
    """Run `gh` with args and parse JSON output."""
    try:
        res = subprocess.run(
            ["gh"] + args,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        die("ERROR: gh CLI not found. Install and authenticate first.")
    except subprocess.CalledProcessError as e:
        msg = e.stderr or e.stdout or str(e)
        die(f"ERROR: gh command failed: {' '.join(args)}\n{msg.strip()}")
    out = res.stdout or ""
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        die(f"ERROR: Failed to parse JSON from gh output for: {' '.join(args)}\nRaw:\n{out[:4000]}")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Show the next RAG issue and a ready-to-run checklist.")
    ap.add_argument(
        "--labels",
        type=str,
        help="Comma-separated labels to filter (default from env RAG_LABELS or 'rag,team/rag,priority/high').",
    )
    ap.add_argument(
        "--state",
        type=str,
        choices=["open", "closed", "all"],
        help="Issue state (default from env RAG_STATE or 'open').",
    )
    ap.add_argument("--repo", type=str, help="Override repo (e.g., owner/repo). Default: current git repo.")
    return ap.parse_args()


def split_csv(val: str | None) -> list[str]:
    if not val:
        return []
    return [x.strip() for x in val.split(",") if x.strip()]


def main() -> int:
    if not have_gh():
        die("ERROR: gh CLI not found. Install and authenticate first.")

    # Defaults (overridable by flags or env)
    default_labels = os.getenv("RAG_LABELS", "rag,team/rag,priority/high")
    default_state = os.getenv("RAG_STATE", "open")
    default_repo = os.getenv("RAG_REPO", "")

    args = parse_args()
    labels_csv = args.labels if args.labels is not None else default_labels
    state = args.state if args.state is not None else default_state
    repo = args.repo if args.repo is not None else default_repo

    label_list = split_csv(labels_csv)

    # Build gh args for listing
    gh_list_args = ["issue", "list", "--state", state, "--json", "number,title,labels,createdAt", "--limit", "1000"]
    for lbl in label_list:
        gh_list_args += ["--label", lbl]
    if repo:
        gh_list_args += ["--repo", repo]

    issues = gh_json(gh_list_args)
    if not isinstance(issues, list):
        die("ERROR: Unexpected response from gh when listing issues.")

    # Sort by number asc and pick the first
    issues_sorted = sorted(issues, key=lambda i: i.get("number", 10**12))
    if not issues_sorted:
        print(f"No matching issues for labels: {labels_csv} (state: {state})")
        return 0

    next_issue = issues_sorted[0]
    num = next_issue.get("number")
    if not isinstance(num, int):
        die("ERROR: Could not determine issue number from gh output.")

    # View full issue
    gh_view_args = ["issue", "view", str(num), "--json", "number,title,body,labels,url"]
    if repo:
        gh_view_args += ["--repo", repo]
    issue = gh_json(gh_view_args)

    title: str = issue.get("title") or ""
    body: str = issue.get("body") or ""
    url: str = issue.get("url") or ""
    labels_str = ", ".join(lab.get("name") for lab in issue.get("labels", []) if isinstance(lab, dict))

    # Extract step number and step id from title
    # Expected: "Implement RAG STEP N — ... (RAG.something...)"
    step_num = None
    m = re.search(r"RAG STEP\s+(\d+)", title)
    if m:
        try:
            step_num = int(m.group(1))
        except ValueError:
            step_num = None

    step_id = None
    m2 = re.search(r"\((RAG[^)]*)\)", title)
    if m2:
        step_id = m2.group(1)

    # Short slug for branch
    short_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "rag-step"

    # Print the formatted output
    print("========================================")
    print("NEXT RAG ISSUE")
    print("========================================")
    print(f"#{num}  {title}")
    print(f"URL: {url}")
    print(f"Labels: {labels_str}")
    print(f"Step: {step_num if step_num is not None else '?'}   StepID: {step_id or '?'}\n")

    print("----- Issue Body (truncated to 500 chars) -----")
    snippet = body[:500]
    print(snippet)
    if len(body) > 500:
        print("...(truncated)")
    print("-----------------------------------------------\n")

    # Mini checklist block
    print("MINI CHECKLIST (copy & run)")
    print("-----------------------------------------------")
    print("# 0) Inspect full issue:")
    if repo:
        print(f"gh issue view {num} --web --repo {repo}")
    else:
        print(f"gh issue view {num} --web")

    # Branch name
    step_str = str(step_num) if step_num is not None else "unknown"
    print("\n# 1) Create working branch:")
    print(f'git checkout -b "rag/step-{step_str}-{short_slug}"')

    # Tests/domain work
    sid_disp = step_id or "RAG.unknown"
    print("\n# 2) Tests first (unit/integration) for the step behavior (see Step Doc & AUTO-AUDIT suggestions)")
    print(f"#    docs/architecture/steps/STEP-{step_str}-{sid_disp}.md")

    # Implement code + logging
    print("\n# 3) Implement minimal code to pass tests.")
    print("#    Add structured logging at the step boundary:")
    print("#      from app.observability.rag_logging import rag_step_log, rag_step_timer")
    print(
        f'#      rag_step_log(step={step_str if step_num else 0}, id="{sid_disp}", node="...", msg="...", attrs={{...}})'
    )

    # Re-run audit
    print("\n# 4) Re-run audit:")
    print("python scripts/rag_code_graph.py --write")
    print("python scripts/rag_audit.py --write")

    # Commit / push / PR
    print("\n# 5) Commit (reference issue to auto-close on merge):")
    print("git add -A")
    print(f'git commit -m "feat(rag): STEP {step_str} — {title} (Closes #{num})"')

    print("\n# 6) Push & open PR:")
    print(f'git push -u origin "rag/step-{step_str}-{short_slug}"')
    if repo:
        print(
            f'gh pr create --title "RAG STEP {step_str}: {title}" --body "Implements STEP {step_str}. See issue #{num}." --repo {repo}'
        )
    else:
        print(
            f'gh pr create --title "RAG STEP {step_str}: {title}" --body "Implements STEP {step_str}. See issue #{num}."'
        )

    print("\n# 7) Merge when green:")
    if repo:
        print("gh pr merge --squash --delete-branch --repo {repo}")
    else:
        print("gh pr merge --squash --delete-branch")
    print("-----------------------------------------------")

    return 0


if __name__ == "__main__":
    sys.exit(main())
