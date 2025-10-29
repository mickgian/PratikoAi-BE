#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate or synchronize Claude-Code–ready GitHub issues for RAG steps
— now baseline-aware (auto investigation), functional-alignment focused,
with label updates and recreate support.

What this does
- Builds or reuses a baseline cache (.rag_alignment_index.json) with evidence per step
- Injects STEP 0 — Investigation into each issue (neighbors, refs, orchestrator presence, runtime hits)
- Demands functional alignment (thin orchestrators, real control semantics) — not logs-only
- Create new issues, sync/update existing (open or closed), optionally reopen closed
- Optional recreate: close prior issue as "superseded" and open a fresh one
- Update labels: add needs/functional-align, set status/partial, remove status/implemented
- Neighbor enrichment from Mermaid
- Idempotent; has dry-run; supports filters (steps, ranges, category, status) and limit

Usage examples
  # Preview (no GitHub calls)
  python scripts/rag_issue_prompter.py --dry-run --sync --status "❌,🔌" --neighbors --from-baseline --refresh-baseline --limit 10

  # Create issues for specific ranges, include neighbors + baseline
  python scripts/rag_issue_prompter.py --create --steps 48-58,69-73 --labels "team/rag" --from-baseline

  # Sync/update bodies for all non-implemented steps, update labels, reopen closed
  python scripts/rag_issue_prompter.py --sync --status "❌,🔌,🟡" --update-labels --neighbors --from-baseline --reopen-closed

  # Recreate a few steps (close old as superseded, open fresh)
  python scripts/rag_issue_prompter.py --create --recreate --steps 51,52 --update-labels --neighbors --from-baseline

Requirements
  - GitHub CLI `gh` installed & authenticated
  - ripgrep `rg` installed (optional but recommended for richer baseline)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import yaml

# ---------- Paths ----------
ROOT = Path(__file__).resolve().parents[1]
STEPS_DIR = ROOT / "docs" / "architecture" / "steps"
STEPS_REGISTRY = ROOT / "docs" / "architecture" / "rag_steps.yml"
DASHBOARD = ROOT / "docs" / "architecture" / "rag_conformance.md"
MERMAID = ROOT / "docs" / "architecture" / "diagrams" / "pratikoai_rag_hybrid.mmd"
BASELINE = ROOT / ".rag_alignment_index.json"
RUNTIME_LOG = ROOT / ".rag_runtime_log.jsonl"

# ---------- Labels / Defaults ----------
DEFAULT_LABELS = ["rag"]
STATUS_LABEL_MAP = {
    "✅": "status/implemented",
    "🟡": "status/partial",
    "🔌": "status/not-wired",
    "❌": "status/missing",
    "❓": "status/unknown",
}

MASTER_GUARDRAILS = '''\
**MASTER_GUARDRAILS (READ FIRST)**
- Mermaid is the single source of truth: docs/architecture/diagrams/pratikoai_rag_hybrid.mmd
- Steps registry: docs/architecture/rag_steps.yml
- Baseline cache REQUIRED: the "STEP 0 — Investigation" below is generated from .rag_alignment_index.json
- No hallucinations. Do NOT write code until you review the Investigation section evidence (file:line).
- Observability is necessary but not sufficient. Each step must enforce the control semantics in Mermaid (thin orchestration), not just logs.
- Preserve business logic. Only expose/wire coordination points. Add a parity test proving outputs unchanged before vs after.
- Keep diffs minimal; only touch files on the PR allowlist you list in the Investigation.
- After changes: `python scripts/rag_code_graph.py --write` and `python scripts/rag_audit.py --write`
'''

INVESTIGATION_TEMPLATE = '''\
### STEP 0 — Investigation (auto-generated)

**Neighbors (from Mermaid)**
- Incoming: {incoming}
- Outgoing: {outgoing}

**Baseline status**
- Status: `{status}`  | Runtime hits: {runtime_hits}
- Orchestrator stub present: {orchestrator}

**Code refs (sample)**
{code_refs}

**Tests mentioning this step**
{tests_refs}

**Delta plan (fill before coding)**
- Minimal orchestrator/wiring changes to make reality == Mermaid (no business-logic changes):
- Tests to add (unit + prev→this→next integration + parity):
- Exact files to touch (allowlist):
'''

CLAUDE_CODE_SECTION = '''
### Claude Code Instructions (Copy-Paste Ready)

**Transformation Required**
- Current: {current_implementation}
- Target: {target_implementation}
- Action: {transformation_notes}

**Test Requirements**
{test_requirements}

**Executable Commands**
```bash
{claude_commands}
```
'''

BEHAVIORAL_DOD = '''\
**Behavioral Definition of Done**
- This step must change or validate program flow/data according to the Mermaid diagram (NOT logs-only).
- A parity test proves behavior is identical before vs after introducing the orchestrator.
- A prev→this→next integration test shows this node is invoked in the correct position between neighbors.
'''

NEIGHBOR_CONTRACTS_HEADER = "### Neighbor Contracts (from Mermaid)"
NEIGHBOR_ITEM_FMT = "- **{direction}**: `{node_id}` — {label}"

STEP_TITLE_RE = re.compile(r"^Implement RAG STEP (\d+)\b")

# ---------- Helpers: system ----------
def gh_available() -> bool:
    try:
        subprocess.run(["gh", "--version"], check=True, capture_output=True)
        return True
    except Exception:
        return False

def rg_available() -> bool:
    try:
        subprocess.run(["rg", "--version"], check=True, capture_output=True)
        return True
    except Exception:
        return False

def run_cmd(args: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)

# ---------- Helpers: gh ----------
def gh_json(args: List[str]) -> Any:
    res = run_cmd(["gh", *args])
    if res.returncode != 0:
        raise RuntimeError(res.stderr or res.stdout or f"gh {' '.join(args)} failed")
    return json.loads(res.stdout or "[]")

def gh_text(args: List[str]) -> str:
    res = run_cmd(["gh", *args])
    if res.returncode != 0:
        raise RuntimeError(res.stderr or res.stdout or f"gh {' '.join(args)} failed")
    return (res.stdout or "").strip()

# ---------- Load registry & audit ----------
def load_steps_registry() -> List[Dict]:
    if not STEPS_REGISTRY.exists():
        print(f"ERROR: Steps registry missing: {STEPS_REGISTRY}")
        sys.exit(1)
    return yaml.safe_load(STEPS_REGISTRY.read_text(encoding="utf-8")).get("steps", [])

def parse_step_doc(step_num: int, step_id: str) -> Tuple[str, Dict]:
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

# ---------- Mermaid neighbors ----------
def parse_mermaid_neighbors() -> Tuple[Dict[str, str], Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Returns:
      nodes_by_id: {node_id: label}
      incoming: {node_id: [prev_ids]}
      outgoing: {node_id: [next_ids]}
    """
    if not MERMAID.exists():
        return {}, {}, {}
    text = MERMAID.read_text(encoding="utf-8")

    nodes_by_id: Dict[str, str] = {}
    # Node forms:  A[Label]  or  A{Label}  (we allow both)
    for m in re.finditer(r"^\s*([A-Za-z0-9_]+)\s*\[(.*?)\]", text, re.MULTILINE):
        node_id, label = m.group(1), m.group(2)
        nodes_by_id[node_id] = re.sub(r"<br/?>", " — ", label)
    for m in re.finditer(r"^\s*([A-Za-z0-9_]+)\s*\{(.*?)\}", text, re.MULTILINE):
        node_id, label = m.group(1), m.group(2)
        nodes_by_id[node_id] = re.sub(r"<br/?>", " — ", label)

    incoming: Dict[str, List[str]] = {}
    outgoing: Dict[str, List[str]] = {}
    for m in re.finditer(r"^\s*([A-Za-z0-9_]+)\s*-->\s*([A-Za-z0-9_]+)", text, re.MULTILINE):
        a, b = m.group(1), m.group(2)
        outgoing.setdefault(a, []).append(b)
        incoming.setdefault(b, []).append(a)

    return nodes_by_id, incoming, outgoing

# ---------- Baseline (evidence) ----------
def rg(pattern: str, paths: Tuple[str, ...] = ("app", "tests")) -> List[str]:
    if not rg_available():
        return []
    try:
        out = subprocess.check_output(["rg", "-n", "-S", pattern, *paths], text=True, cwd=ROOT)
        return [ln for ln in out.strip().splitlines() if ln.strip()]
    except subprocess.CalledProcessError:
        return []

def parse_mermaid_edges_for_neighbors():
    _, inc, out = parse_mermaid_neighbors()
    return inc, out

def status_from_refs(has_orch: bool, has_log_anchor: bool, has_any_code: bool, wired_runtime: bool = False) -> str:
    if wired_runtime:
        return "implemented_and_wired"
    if has_orch and has_log_anchor:
        return "exists_not_wired"
    if has_any_code or has_log_anchor:
        return "implemented_logs_only"
    return "missing"

def build_baseline_cache() -> Dict[str, Dict]:
    steps = load_steps_registry()
    incoming, outgoing = parse_mermaid_edges_for_neighbors()

    runtime_hits: Dict[int, int] = {}
    if RUNTIME_LOG.exists():
        for line in RUNTIME_LOG.read_text(encoding="utf-8").splitlines():
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict) and "step" in obj:
                s = int(obj["step"])
                runtime_hits[s] = runtime_hits.get(s, 0) + 1

    idx: Dict[str, Dict] = {}
    for s in steps:
        step = int(s["step"])
        step_id = s["id"]
        node_label = s.get("node_label") or ""
        node_id = s.get("node_id") or ""
        category = s.get("category") or "misc"
        type_ = s.get("type") or "process"

        inc = incoming.get(node_id, [])
        out = outgoing.get(node_id, [])

        # Evidence scans (robust, not relying on “nice” names)
        refs_stepnum = rg(fr"rag_step_log\([^)]*step\s*=\s*{step}\b\)")
        refs_stepid  = rg(re.escape(step_id)) if step_id else []
        refs_node    = rg(fr"\b{re.escape(node_id)}\b") if node_id else []
        refs_label   = rg(re.escape(node_label)) if node_label else []

        # Orchestrator presence — match generic scaffolded stubs:
        # def step_<N>__<slug>(
        orch_fn_hits = rg(fr"^def\s+step_{step}__\w+\s*\(", paths=("app",))
        orch_file = orch_fn_hits[0].split(":")[0] if orch_fn_hits else None

        test_hits = rg(fr"STEP[-_ ]?{step}\b", paths=("tests",))

        has_log_anchor = bool(refs_stepnum or refs_stepid)
        has_any_code   = bool(refs_node or refs_label or orch_fn_hits)
        wired          = step in runtime_hits

        st = status_from_refs(bool(orch_fn_hits), has_log_anchor, has_any_code, wired_runtime=wired)

        idx[str(step)] = {
            "step": step, "id": step_id, "node_id": node_id, "node_label": node_label,
            "category": category, "type": type_,
            "neighbors": {"incoming": inc, "outgoing": out},
            "code_refs": {
                "by_stepnum": refs_stepnum[:20],
                "by_stepid":  refs_stepid[:20],
                "by_nodeid":  refs_node[:20],
                "by_label":   refs_label[:20],
            },
            "orchestrator": orch_file is not None,
            "tests_refs": test_hits[:20],
            "runtime_hits": runtime_hits.get(step, 0),
            "status": st,
        }

    BASELINE.write_text(json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8")
    return idx

def load_baseline(existing_ok: bool, refresh: bool) -> Dict[str, Dict]:
    if refresh or not BASELINE.exists():
        return build_baseline_cache()
    try:
        return json.loads(BASELINE.read_text(encoding="utf-8"))
    except Exception:
        return build_baseline_cache()

def build_code_refs_block(code_refs: Dict[str, List[str]]) -> str:
    def fmt(lines: List[str]) -> str:
        if not lines:
            return "  - (none)"
        out = []
        for ln in lines[:5]:
            out.append(f"  - {ln}")
        return "\n".join(out)
    return "\n".join([
        f"- by_stepnum:\n{fmt(code_refs.get('by_stepnum', []))}",
        f"- by_stepid:\n{fmt(code_refs.get('by_stepid', []))}",
        f"- by_nodeid:\n{fmt(code_refs.get('by_nodeid', []))}",
        f"- by_label:\n{fmt(code_refs.get('by_label', []))}",
    ])

def investigation_block_from_baseline(rec: Optional[Dict], include_neighbors: bool) -> str:
    if not rec:
        return "### STEP 0 — Investigation\n- Baseline missing. Run: `python scripts/rag_issue_prompter.py --from-baseline --refresh-baseline --dry-run`\n"
    incoming = ", ".join(rec["neighbors"]["incoming"]) if (include_neighbors and rec["neighbors"]["incoming"]) else ("(hidden)" if not include_neighbors else "-")
    outgoing = ", ".join(rec["neighbors"]["outgoing"]) if (include_neighbors and rec["neighbors"]["outgoing"]) else ("(hidden)" if not include_neighbors else "-")
    code_refs = build_code_refs_block(rec.get("code_refs", {}))
    tests_refs = "\n".join([f"- {x}" for x in rec.get("tests_refs", [])[:5]]) or "- (none)"
    return INVESTIGATION_TEMPLATE.format(
        incoming=incoming or "-",
        outgoing=outgoing or "-",
        status=rec.get("status", "?"),
        runtime_hits=rec.get("runtime_hits", 0),
        orchestrator="yes" if rec.get("orchestrator") else "no",
        code_refs=code_refs,
        tests_refs=tests_refs
    )

# ---------- Issue body ----------
def build_issue_title(step_num: int, node_label: str, step_id: str) -> str:
    return f"Implement RAG STEP {step_num} — {node_label} ({step_id})"

def build_issue_body(
    step: Dict,
    audit: Dict,
    include_guardrails: bool,
    include_neighbors: bool,
    baseline_rec: Optional[Dict]
) -> str:
    step_num = step["step"]
    node_label = step["node_label"]
    step_id = step["id"]
    node_id = step["node_id"]
    step_type = step["type"]
    category = step["category"]

    if audit.get("suggestions"):
        checklist = "\n".join(f"- [ ] {s}" for s in audit["suggestions"])
    else:
        checklist = "- [ ] Implement per step doc and TDD template"

    guard = (MASTER_GUARDRAILS + "\n") if include_guardrails else ""

    # Neighbor contracts (from Mermaid)
    neighbors_block = ""
    if include_neighbors:
        nodes_by_id, incoming, outgoing = parse_mermaid_neighbors()
        prevs = incoming.get(node_id, [])
        nexts = outgoing.get(node_id, [])
        lines = []
        if prevs:
            for nid in prevs:
                lines.append(NEIGHBOR_ITEM_FMT.format(direction="Prev", node_id=nid, label=nodes_by_id.get(nid, "")))
        if nexts:
            for nid in nexts:
                lines.append(NEIGHBOR_ITEM_FMT.format(direction="Next", node_id=nid, label=nodes_by_id.get(nid, "")))
        if lines:
            neighbors_block = f"\n{NEIGHBOR_CONTRACTS_HEADER}\n" + "\n".join(lines) + "\n"

    investigation = investigation_block_from_baseline(baseline_rec, include_neighbors=include_neighbors)

    # Add Claude Code instructions if available
    claude_code_section = ""
    if baseline_rec and "claude_code_instructions" in baseline_rec:
        test_requirements = "\n".join([f"- {req}" for req in baseline_rec.get("test_requirements", [])])
        claude_commands = "\n".join(baseline_rec.get("claude_code_instructions", []))
        claude_code_section = CLAUDE_CODE_SECTION.format(
            current_implementation=baseline_rec.get("current_implementation", "See investigation above"),
            target_implementation=baseline_rec.get("target_implementation", "See investigation above"),
            transformation_notes=baseline_rec.get("transformation_notes", "Extract and refactor per blueprint"),
            test_requirements=test_requirements or "- See acceptance criteria",
            claude_commands=claude_commands or "# See investigation for manual steps"
        )

    body = f'''\
{guard}**Task: Implement RAG STEP {step_num} — {node_label} (`{step_id}`)**

{investigation}

{claude_code_section}

**Scope**
- Align code with the approved RAG blueprint (Mermaid is the source of truth).
- Implement exactly this step and minimal wiring to/from neighbors. No repo-wide refactors.
- If the current implementation collapses multiple diagram nodes into a single factory/service, add a thin **orchestrator** that matches the diagram and preserves behavior (prove with parity tests).

**Files of interest**
- Mermaid diagram: docs/architecture/diagrams/pratikoai_rag_hybrid.mmd
- Step doc: docs/architecture/steps/STEP-{step_num}-{step_id}.md
- Observability: app/observability/rag_logging.py

**What to do (TDD)**
1) Tests first: unit + prev/this/next integration + parity (prove identical behavior).
2) Implement the minimal code to pass tests (thin orchestrator / wiring).
3) Logging: add rag_step_log(...) and optionally rag_step_timer(...).
4) Docs sync: run audit tools and ensure the step doc auto-audit block reflects progress.

**Blueprint alignment (must-do)**
- Create/adjust a dedicated function/class that implements this node’s control semantics (not just a log wrapper).
- Wire it from the exact previous node(s) and to the next node(s) shown in Mermaid.
- If core logic already lives in a factory/service, wrap it with an orchestrator that:
  - passes through the same inputs/outputs,
  - contains only coordination logic,
  - adds structured logs and timing,
  - keeps behavior identical (**prove with parity tests**).
- Update Mermaid only if the code truly cannot be expressed as separate nodes without changing behavior. Default: adapt the code to the blueprint.

**Integration tasks (neighbors)**
- Connect to previous node(s) and next node(s) **exactly** as in Mermaid.
{neighbors_block}**Acceptance criteria**
- Tests pass locally.
- `python scripts/rag_audit.py --write` updates this step’s status away from ❌/🔌.
- No new folders like docs/backlog/.
- Structured log lines present for this step:  RAG STEP {step_num} ({step_id})
- {BEHAVIORAL_DOD}

**Implementation Checklist (from AUTO-AUDIT)**
{checklist}

**Links**
- Step doc: docs/architecture/steps/STEP-{step_num}-{step_id}.md
- Conformance dashboard: docs/architecture/rag_conformance.md
- Mermaid: docs/architecture/diagrams/pratikoai_rag_hybrid.mmd

**Meta**
- Step: {step_num}
- Type: {step_type}
- Category: {category}
- Node: {node_id}
- Current doc status: {audit.get('status','❓')} (confidence: {audit.get('confidence',0.0):.2f})
'''
    return body

# ---------- Existing issues helpers ----------
def list_all_step_issues() -> List[Dict]:
    data = gh_json(["issue", "list", "--state", "all", "--limit", "1000", "--json", "number,title,state,labels,url"])
    out = []
    for it in data:
        title = it.get("title", "")
        labels = it.get("labels", [])
        if title.startswith("Implement RAG STEP "):
            out.append(it)
            continue
        for lab in labels:
            if lab.get("name", "").startswith("step/"):
                out.append(it)
                break
    return out

def parse_step_from_title(title: str) -> Optional[int]:
    m = STEP_TITLE_RE.search(title or "")
    return int(m.group(1)) if m else None

def parse_step_from_labels(labels: List[Dict]) -> Optional[int]:
    for lab in labels or []:
        name = lab.get("name", "")
        if name.startswith("step/"):
            try:
                return int(name.split("/", 1)[1])
            except Exception:
                pass
    return None

def find_existing_issue_for_step(issues: List[Dict], step_num: int) -> Optional[Dict]:
    for it in issues:
        num = parse_step_from_title(it.get("title","")) or parse_step_from_labels(it.get("labels",[]))
        if num == step_num:
            return it
    return None

# ---------- Creation / Editing ----------
def build_labels_for_creation(step: Dict, audit: Dict, extra_labels: List[str], force_functional_align: bool) -> List[str]:
    labels = list(DEFAULT_LABELS)
    labels.append(f"step/{step['step']}")
    labels.append(f"area/{step['category']}")
    status_label = STATUS_LABEL_MAP.get(audit.get("status","❓"), "status/unknown")
    labels.append(status_label)
    if force_functional_align:
        labels.append("needs/functional-align")
    labels.extend(extra_labels)
    # dedupe while preserving order
    seen = set()
    ordered = []
    for lab in labels:
        if lab not in seen and lab:
            seen.add(lab)
            ordered.append(lab)
    return ordered

def edit_issue_labels(number: int, add: List[str], remove: List[str]) -> None:
    for lab in add:
        try:
            gh_text(["issue","edit",str(number),"--add-label",lab])
        except Exception:
            pass
    for lab in remove:
        try:
            gh_text(["issue","edit",str(number),"--remove-label",lab])
        except Exception:
            pass

def reopen_if_closed(issue: Dict) -> None:
    if (issue.get("state","").lower() == "closed"):
        gh_text(["issue","reopen", str(issue["number"])])

def close_as_superseded(old_issue: Dict, new_url: str) -> None:
    num = str(old_issue["number"])
    try:
        gh_text(["issue","comment", num, "-b", f"Superseded by: {new_url}"])
    except Exception:
        pass
    try:
        gh_text(["issue","edit", num, "--add-label", "superseded"])
    except Exception:
        pass
    try:
        gh_text(["issue","close", num])
    except Exception:
        pass

def write_temp_body(body: str, step_num: int) -> Path:
    tmp = ROOT / f".tmp_issue_step_{step_num}.md"
    tmp.write_text(body, encoding="utf-8")
    return tmp

def create_issue(title: str, body: str, labels: List[str], assignee: Optional[str]) -> str:
    cmd = ["gh", "issue", "create", "--title", title, "--body", body]
    if labels:
        cmd.extend(["--label", ",".join(labels)])
    if assignee:
        cmd.extend(["--assignee", assignee])
    res = run_cmd(cmd)
    if res.returncode != 0:
        raise RuntimeError(res.stderr or res.stdout or "gh issue create failed")
    return (res.stdout or "").strip()

# ---------- Arg parsing ----------
def parse_list_arg(val: Optional[str]) -> List[str]:
    if not val:
        return []
    parts = [v.strip() for v in val.split(",") if v.strip()]
    out: List[str] = []
    for p in parts:
        if re.match(r"^\d+-\d+$", p):
            a, b = p.split("-")
            out.extend([str(i) for i in range(int(a), int(b) + 1)])
        else:
            out.append(p)
    return out

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser(description="Create or synchronize GitHub issues for RAG steps (functional alignment, baseline-aware).")
    mode = ap.add_mutually_exclusive_group(required=False)
    mode.add_argument("--create", action="store_true", help="Create new issues for filtered steps. Skips existing unless --recreate.")
    mode.add_argument("--sync", action="store_true", help="Update existing issues in-place (rewrite body).")

    ap.add_argument("--recreate", action="store_true", help="If an issue exists for a step, close it as 'superseded' and create a fresh one.")
    ap.add_argument("--update-labels", action="store_true", help="Normalize labels: add needs/functional-align, set status/partial, remove status/implemented.")
    ap.add_argument("--reopen-closed", action="store_true", help="(When --sync) reopen matching closed issues before updating.")

    ap.add_argument("--neighbors", action="store_true", help="Enrich body with neighbor contracts from Mermaid.")
    ap.add_argument("--from-baseline", action="store_true", help="Embed STEP 0 — Investigation from baseline cache.")
    ap.add_argument("--refresh-baseline", action="store_true", help="Rebuild baseline cache before generating issues.")
    ap.add_argument("--limit", type=int, help="Limit number of issues to create/update.")

    ap.add_argument("--steps", type=str, help="Comma-separated step numbers or ranges (e.g., 20,39,59 or 48-58,69-73)")
    ap.add_argument("--category", type=str, help="Comma-separated categories to include (e.g., golden,kb,cache)")
    ap.add_argument("--status", type=str, help="Comma-separated doc audit statuses to include (e.g., ❌,🔌,🟡). Default excludes ✅.")
    ap.add_argument("--include-implemented", action="store_true", help="Include ✅ steps too (default is to skip them).")

    ap.add_argument("--assignee", type=str, help="GitHub username to assign issues to")
    ap.add_argument("--labels", type=str, help="Comma-separated extra labels to add (e.g., priority/high,team/rag)")
    ap.add_argument("--no-guardrails", action="store_true", help="Do not include the Master Guardrails block in the body")
    ap.add_argument("--dry-run", action="store_true", help="Preview only; do not call gh")
    args = ap.parse_args()

    # Validate gh if we’ll call it
    if (args.create or args.sync or args.recreate or args.update_labels) and not args.dry_run and not gh_available():
        print("ERROR: GitHub CLI `gh` not found. Install and authenticate.")
        return 1

    # Load steps
    steps = load_steps_registry()
    filter_steps = set(int(s) for s in parse_list_arg(args.steps)) if args.steps else None
    filter_cats = set(parse_list_arg(args.category)) if args.category else None
    filter_status = set(parse_list_arg(args.status)) if args.status else None
    extra_labels = parse_list_arg(args.labels)

    # Baseline (optional but recommended)
    baseline: Dict[str, Dict] = {}
    if args.from_baseline:
        baseline = load_baseline(existing_ok=True, refresh=args.refresh_baseline)
        print(f"🔎 Baseline ready with {len(baseline)} steps.")

    # Build candidates
    candidates: List[Dict] = []
    for step in steps:
        s_num = int(step["step"])
        s_cat = step["category"]
        if filter_steps and s_num not in filter_steps:
            continue
        if filter_cats and s_cat not in filter_cats:
            continue
        _, audit = parse_step_doc(step["step"], step["id"])
        s_status = audit.get("status", "❓")
        if not args.include_implemented and s_status == "✅":
            if not (filter_status and s_status in filter_status):
                continue
        if filter_status and s_status not in filter_status:
            continue
        step["_audit"] = audit
        candidates.append(step)

    if args.limit:
        candidates = candidates[: args.limit]

    if not candidates:
        print("Nothing to do with current filters.")
        return 0

    # Existing issues map (by step)
    existing: Dict[int, Dict] = {}
    if not args.dry_run:
        try:
            all_step_issues = list_all_step_issues()
            for it in all_step_issues:
                step_num = parse_step_from_title(it.get("title","")) or parse_step_from_labels(it.get("labels",[]))
                if step_num:
                    existing[int(step_num)] = it
        except Exception as e:
            print(f"⚠️  Warning: Unable to list existing issues via gh: {e}")

    # Decide default mode: create if neither set
    do_create = args.create or (not args.sync)

    created = 0
    updated = 0
    superseded = 0
    skipped = 0
    reopened = 0

    print(f"Processing {len(candidates)} step(s)...")
    for step in candidates:
        step_num = int(step["step"])
        node_label = step["node_label"]
        step_id = step["id"]
        audit = step["_audit"]
        title = build_issue_title(step_num, node_label, step_id)

        baseline_rec = baseline.get(str(step_num)) if args.from_baseline else None
        body = build_issue_body(
            step=step,
            audit=audit,
            include_guardrails=not args.no_guardrails,
            include_neighbors=args.neighbors,
            baseline_rec=baseline_rec,
        )

        exists = existing.get(step_num)

        if do_create:
            if exists and not args.recreate:
                print(f"⏭️  Skip (exists)  STEP {step_num}  {title}")
                skipped += 1
                continue

            labels = build_labels_for_creation(step, audit, extra_labels, force_functional_align=True)

            if args.dry_run:
                action = "Would recreate" if (exists and args.recreate) else "Would create"
                print(f"📝 {action}: STEP {step_num}  {title}")
            else:
                try:
                    new_url = create_issue(title, body, labels, args.assignee)
                    print(f"✅ Created: STEP {step_num}  -> {new_url}")
                    created += 1
                    if exists and args.recreate:
                        close_as_superseded(exists, new_url)
                        superseded += 1
                except Exception as e:
                    print(f"❌ Failed create/recreate STEP {step_num}: {e}")

        if args.sync:
            if not exists:
                print(f"⏭️  Skip sync (no existing issue)  STEP {step_num}")
                skipped += 1
                continue

            if args.dry_run:
                note = []
                if exists.get("state","").lower() == "closed" and args.reopen_closed:
                    note.append("reopen")
                if args.update_labels:
                    note.append("update labels")
                print(f"♻️  Would sync body ({', '.join(note) or 'body only'}): STEP {step_num}  #{exists['number']}")
            else:
                try:
                    if exists.get("state","").lower() == "closed" and args.reopen_closed:
                        reopen_if_closed(exists)
                        reopened += 1
                    tmp = write_temp_body(body, step_num)
                    gh_text(["issue","edit",str(exists["number"]), "--body-file", str(tmp)])
                    if args.update_labels:
                        edit_issue_labels(
                            exists["number"],
                            add=["needs/functional-align", "status/partial"] + extra_labels,
                            remove=["status/implemented"],
                        )
                    if args.assignee:
                        try:
                            gh_text(["issue","edit",str(exists["number"]),"--assignee",args.assignee])
                        except Exception:
                            pass
                    print(f"🔧 Synced: STEP {step_num}  -> issue #{exists['number']}")
                    updated += 1
                except Exception as e:
                    print(f"❌ Failed to sync STEP {step_num}: {e}")

    print(f"\nDone. Created: {created}  |  Synced: {updated}  |  Reopened: {reopened}  |  Superseded: {superseded}  |  Skipped: {skipped}")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
