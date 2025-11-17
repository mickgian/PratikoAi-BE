#!/usr/bin/env python3
"""
Auto-scaffold orchestrator modules and step stubs from either:
- docs/architecture/rag_steps.yml  (preferred if present), OR
- docs/architecture/steps/STEP-*.md (parses your Markdown step docs)

Creates/updates:
- app/orchestrators/<category>.py  (one function per step)
- app/orchestrators/__init__.py

Each stub is named:
    def step_{NUM}__{slug}(*, messages=None, ctx=None, **kwargs): ...

Usage:
  python scripts/rag_orchestrator_scaffold.py
  python scripts/rag_orchestrator_scaffold.py --only-categories providers,cache
  python scripts/rag_orchestrator_scaffold.py --only-steps 51,52,53
  python scripts/rag_orchestrator_scaffold.py --dry-run
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parents[1]
ORCH_DIR = ROOT / "app" / "orchestrators"
STEPS_YML = ROOT / "docs" / "architecture" / "rag_steps.yml"
STEPS_DIR = ROOT / "docs" / "architecture" / "steps"

HEADER = """# AUTO-GENERATED ORCHESTRATOR STUBS (safe to edit below stubs)
# These functions are the functional *nodes* that mirror the Mermaid diagram.
# Implement thin coordination here (call services/factories), not core business logic.

from contextlib import nullcontext
from typing import Any, Dict, List, Optional

try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover
    def rag_step_log(**kwargs): return None
    def rag_step_timer(*args, **kwargs): return nullcontext()
"""

FUNC_TEMPLATE = '''
def {fname}(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP {step} — {node_label}
    ID: {step_id}
    Type: {type} | Category: {category} | Node: {node_id}

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer({step}, {step_id_repr}, {node_id_repr}, stage="start"):
        rag_step_log(step={step}, step_id={step_id_repr}, node_label={node_id_repr},
                     category={category_repr}, type={type_repr}, stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step={step}, step_id={step_id_repr}, node_label={node_id_repr},
                     processing_stage="completed")
        return result
'''

INIT_HEADER = """# Expose orchestrator functions for test imports and wiring.
# This file is updated by rag_orchestrator_scaffold.py (idempotent).
"""

# ---------- utils ----------


def snakeify(s: str) -> str:
    s = s or ""
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"_+", "_", s)
    return s.lower() or "node"


def ensure_file(p: Path, header: str, *, dry: bool):
    if not p.exists() and not dry:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(header, encoding="utf-8")


def function_exists(text: str, fname: str) -> bool:
    pat = rf"^def\s+{re.escape(fname)}\s*\("
    return re.search(pat, text, re.MULTILINE) is not None


def append_stub(mod_path: Path, stub: str, *, dry: bool):
    if dry:
        return
    with mod_path.open("a", encoding="utf-8") as f:
        f.write(stub)


def scan_functions_in_file(p: Path) -> list[str]:
    text = p.read_text(encoding="utf-8")
    return re.findall(r"^def\s+([a-zA-Z0-9_]+)\s*\(", text, re.MULTILINE)


def build_stub(step: int, step_id: str, node_id: str, node_label: str, typ: str, category: str, fname: str) -> str:
    return FUNC_TEMPLATE.format(
        fname=fname,
        step=step,
        step_id=step_id,
        node_id=node_id,
        node_label=node_label,
        type=typ,
        category=category,
        step_id_repr=repr(step_id),
        node_id_repr=repr(node_id),
        category_repr=repr(category),
        type_repr=repr(typ),
    )


# ---------- loaders ----------


def load_steps_from_yaml() -> list[dict[str, Any]]:
    if not STEPS_YML.exists():
        return []
    raw = yaml.safe_load(STEPS_YML.read_text(encoding="utf-8")) or {}
    steps: list[dict[str, Any]] = raw.get("steps", [])
    normd: list[dict[str, Any]] = []
    for st in steps:
        step = int(st.get("step"))
        step_id = st.get("id") or ""
        node_label = st.get("node_label") or st.get("label") or st.get("node") or ""
        node_id = st.get("node_id") or snakeify(node_label)
        category = st.get("category") or "misc"
        typ = st.get("type") or "process"
        normd.append(
            {
                "step": step,
                "id": step_id,
                "node_label": node_label,
                "node_id": node_id,
                "category": category,
                "type": typ,
            }
        )
    return normd


MD_H1_RE = re.compile(
    r"^#\s*RAG\s+STEP\s+(?P<num>\d+)\s+—\s+(?P<label>.+?)\s*\((?P<id>RAG\.[^)]+)\)\s*$", re.MULTILINE
)
MD_TYPE_RE = re.compile(r"^\*\*Type:\*\*\s*(?P<type>\w+)", re.MULTILINE)
MD_CAT_RE = re.compile(r"^\*\*Category:\*\*\s*(?P<cat>\w+)", re.MULTILINE)
MD_NODE_RE = re.compile(r"^\*\*Node ID:\*\*\s*`(?P<node>[^`]+)`", re.MULTILINE)


def load_steps_from_markdown() -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if not STEPS_DIR.exists():
        return steps

    for md in sorted(STEPS_DIR.glob("STEP-*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")

        # H1 line
        m = MD_H1_RE.search(text)
        if not m:
            # fallback: try filename for number/id
            try:
                num = int(re.search(r"STEP-(\d+)", md.name).group(1))
            except Exception:
                continue
            step_id = ""
            node_label = md.stem
        else:
            num = int(m.group("num"))
            node_label = m.group("label").strip()
            step_id = m.group("id").strip()

        # Type / Category / Node ID
        typ = (MD_TYPE_RE.search(text).group("type") if MD_TYPE_RE.search(text) else "process").strip()
        cat = (MD_CAT_RE.search(text).group("cat") if MD_CAT_RE.search(text) else "misc").strip()
        node_id = (MD_NODE_RE.search(text).group("node") if MD_NODE_RE.search(text) else snakeify(node_label)).strip()

        steps.append(
            {
                "step": num,
                "id": step_id,
                "node_label": node_label,
                "node_id": node_id,
                "category": cat,
                "type": typ,
            }
        )
    return steps


def load_steps() -> list[dict[str, Any]]:
    # Prefer YAML; fall back to scanning Markdown
    steps = load_steps_from_yaml()
    if steps:
        return steps
    return load_steps_from_markdown()


# ---------- writers ----------


def update_category_module(cat: str, steps: list[dict[str, Any]], *, dry: bool) -> list[str]:
    mod_name = snakeify(cat)
    mod_path = ORCH_DIR / f"{mod_name}.py"
    ensure_file(mod_path, HEADER, dry=dry)
    text = mod_path.read_text(encoding="utf-8") if mod_path.exists() else HEADER

    added: list[str] = []
    for st in steps:
        step = st["step"]
        step_id = st["id"]
        node_id = st["node_id"]
        node_label = st["node_label"]
        typ = st["type"]
        category = st["category"]

        base_slug = snakeify(node_id or node_label or f"step_{step}")
        fname = f"step_{step}__{base_slug}"

        if function_exists(text, fname):
            continue

        stub = build_stub(step, step_id, node_id, node_label, typ, category, fname)
        append_stub(mod_path, stub, dry=dry)
        text += stub
        added.append(f"{mod_name}.{fname}")
    return added


def update_init(categories: list[str], *, dry: bool):
    init_path = ORCH_DIR / "__init__.py"
    lines: list[str] = [INIT_HEADER]
    exports: list[str] = []

    for cat in sorted(categories, key=lambda x: snakeify(x)):
        mod = snakeify(cat)
        mod_file = ORCH_DIR / f"{mod}.py"
        if not mod_file.exists():
            continue
        fns = scan_functions_in_file(mod_file)
        if not fns:
            continue
        fns_sorted = sorted({fn for fn in fns if not fn.startswith("_")})
        lines.append(f"from .{mod} import {', '.join(fns_sorted)}")
        exports.extend(fns_sorted)

    if exports:
        lines += ["", f"__all__ = [{', '.join(repr(x) for x in sorted(set(exports)))}]"]
    else:
        lines += ["", "__all__: list[str] = []"]

    if not dry:
        init_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------- main ----------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-categories", type=str, help="Comma list of categories to scaffold")
    ap.add_argument("--only-steps", type=str, help="Comma list of step numbers to scaffold")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    steps = load_steps()
    if not steps:
        print("No steps found (neither rag_steps.yml nor STEP-*.md parsed).")
        return 2

    if args.only_steps:
        keep_steps = {int(x.strip()) for x in args.only_steps.split(",") if x.strip().isdigit()}
        steps = [s for s in steps if s["step"] in keep_steps]

    if args.only_categories:
        keep_cats = {x.strip() for x in args.only_categories.split(",") if x.strip()}
        steps = [s for s in steps if s["category"] in keep_cats]

    if not steps:
        print("No steps to scaffold (filters too strict?).")
        return 0

    ORCH_DIR.mkdir(parents=True, exist_ok=True)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for st in steps:
        grouped.setdefault(st["category"] or "misc", []).append(st)

    total_new = 0
    for cat, group in sorted(grouped.items(), key=lambda kv: snakeify(kv[0])):
        group_sorted = sorted(group, key=lambda x: x["step"])
        added = update_category_module(cat, group_sorted, dry=args.dry_run)
        total_new += len(added)
        if added:
            print(f"🧩 {cat} → {snakeify(cat)}.py: added {len(added)} function stub(s)")
        else:
            print(f"✔ {cat} → {snakeify(cat)}.py: no new stubs")

    update_init(list(grouped.keys()), dry=args.dry_run)
    print(f"✅ Done. New stubs: {total_new}  (dry-run={args.dry_run})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
