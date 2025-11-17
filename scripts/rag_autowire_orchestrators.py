#!/usr/bin/env python3
"""
Config-driven autowiring of orchestrator calls into real code.

- Reads docs/architecture/rag_steps.yml to resolve step → node_id/node_label/category/type
- Reads docs/architecture/autoroute.yml to know WHERE to inject each slice
- Ensures orchestrator stubs exist (calls rag_orchestrator_scaffold.py)
- Inserts idempotent marker blocks that call ORCH.step_{N}__{snake(node_id)}(...)
- Never changes core logic: try/except and comment guards make it safe to run repeatedly

Usage:
  python scripts/rag_autowire_orchestrators.py --all
  python scripts/rag_autowire_orchestrators.py --slice providers --dry-run
  python scripts/rag_autowire_orchestrators.py --slice cache
  python scripts/rag_autowire_orchestrators.py --slice retry

Slices & target functions are defined in docs/architecture/autoroute.yml.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[1]
STEPS_YML = ROOT / "docs" / "architecture" / "rag_steps.yml"
AUTOROUTE_YML = ROOT / "docs" / "architecture" / "autoroute.yml"
ORCH_INIT = ROOT / "app" / "orchestrators" / "__init__.py"
SCAFFOLDER = ROOT / "scripts" / "rag_orchestrator_scaffold.py"

# --------------------------------------------------------------------------------------
# Utils
# --------------------------------------------------------------------------------------


def run(cmd: list[str]) -> str:
    res = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr or res.stdout or f"Command failed: {' '.join(cmd)}")
    return res.stdout


def snakeify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return (s or "node").lower()


def load_steps_registry() -> dict[int, dict[str, Any]]:
    data = yaml.safe_load(STEPS_YML.read_text(encoding="utf-8")) or {}
    bynum: dict[int, dict[str, Any]] = {}
    for st in data.get("steps", []):
        step = int(st["step"])
        st.setdefault("node_label", st.get("node_label") or st.get("label") or "")
        st.setdefault("node_id", st.get("node_id") or snakeify(st.get("node_label", "")))
        st.setdefault("category", st.get("category") or "misc")
        st.setdefault("type", st.get("type") or "process")
        bynum[step] = st
    return bynum


def load_autoroute() -> dict[str, Any]:
    if not AUTOROUTE_YML.exists():
        raise SystemExit(f"Missing autoroute config: {AUTOROUTE_YML}")
    return yaml.safe_load(AUTOROUTE_YML.read_text(encoding="utf-8")) or {}


def ensure_scaffold(dry: bool):
    if not SCAFFOLDER.exists():
        print("⚠️  Scaffolder not found:", SCAFFOLDER)
        return
    if dry:
        print("• (dry-run) would run scaffolder")
        return
    run([sys.executable, str(SCAFFOLDER)])


def parse_step_specs(specs: list[Any]) -> list[int]:
    """
    Accepts: [51, "52-58", "41,42,43", " 60 - 61 "]
    Returns: [51, 52, 53, ..., 61] (deduped, sorted)
    """
    out: list[int] = []
    for spec in specs or []:
        if isinstance(spec, int):
            out.append(spec)
            continue
        s = str(spec).strip()
        if not s:
            continue
        for token in s.split(","):
            token = token.strip()
            if not token:
                continue
            if "-" in token:
                a, b = [t.strip() for t in token.split("-", 1)]
                if a.isdigit() and b.isdigit():
                    a_i, b_i = int(a), int(b)
                    rng = range(min(a_i, b_i), max(a_i, b_i) + 1)
                    out.extend(list(rng))
            elif token.isdigit():
                out.append(int(token))
    # dedupe + sort
    return sorted(set(out))


def ensure_orchestrators_import(text: str) -> str:
    if "from app import orchestrators as ORCH" in text:
        return text
    # insert after first import block
    lines = text.splitlines()
    insert_at = 0
    for i, line in enumerate(lines[:200]):
        if line.startswith("from ") or line.startswith("import "):
            insert_at = i + 1
    lines.insert(insert_at, "from app import orchestrators as ORCH  # auto-wired by rag_autowire_orchestrators")
    return "\n".join(lines) + "\n"


def find_function_block(text: str, func_name: str) -> tuple[int, int, str] | None:
    """
    Returns (start_index, end_index, body_indent) for a def func_name(...):
    body_indent is the indent to use inside the function.
    """
    m = re.search(rf"^def\s+{re.escape(func_name)}\s*\(", text, re.MULTILINE)
    if not m:
        return None
    start = m.start()
    # naive function end: next def/class at col 0 or EOF
    search_region = text[m.end() :]
    end = len(text)
    next_def = re.search(r"^(def |class )", search_region, re.MULTILINE)
    if next_def:
        end = m.end() + next_def.start()

    # compute indent of body
    header_line = text[start : text.find("\n", start) + 1]
    header_indent = re.match(r"^(\s*)", header_line).group(1)
    body_indent = header_indent + " " * 4
    return (start, end, body_indent)


def split_header_body(func_text: str, body_indent: str) -> tuple[str, str]:
    """
    Split function text into header + body (keeping docstring together).
    Insertions will go at the top of the body.
    """
    lines = func_text.splitlines()
    # First line is def ...
    # If docstring starts on second line with same indent, skip until close
    body_start_idx = 1
    if len(lines) > 1 and re.match(rf'^{re.escape(body_indent)}("""|\'\'\')', lines[1] or ""):
        for i in range(2, min(len(lines), 500)):
            if re.match(rf'^{re.escape(body_indent)}("""|\'\'\')', lines[i] or ""):
                body_start_idx = i + 1
                break
    header = "\n".join(lines[:body_start_idx])
    body = "\n".join(lines[body_start_idx:])
    return header, body


def build_block(slice_name: str, steps: list[int], bynum: dict[int, dict[str, Any]], indent: str) -> str:
    start_mark = f"# [AUTO-ORCH {slice_name} START]"
    end_mark = f"# [AUTO-ORCH {slice_name} END]"
    lines = [
        f"{indent}{start_mark}",
        f"{indent}# Auto-generated orchestration hooks for Mermaid-aligned nodes.",
        f"{indent}# Safe-by-default: wrapped in try/except; keeps existing behavior intact.",
        f"{indent}try:",
        f"{indent}    _orch_ctx = dict(**locals())  # pass current local context",
    ]
    for n in steps:
        st = bynum.get(n)
        if not st:
            lines.append(f"{indent}    # WARN: step {n} not found in rag_steps.yml")
            continue
        node_id = st["node_id"]
        fname = f"step_{n}__{snakeify(node_id)}"
        lines.append(f"{indent}    ORCH.{fname}(messages=locals().get('messages'), ctx=_orch_ctx)")
    lines += [
        f"{indent}except Exception:",  # never break the main path on orchestration errors
        f"{indent}    pass",
        f"{indent}{end_mark}",
        "",
    ]
    return "\n".join(lines)


def inject_slice(
    target_file: Path, func_name: str, slice_name: str, steps: list[int], bynum: dict[int, dict[str, Any]], dry: bool
) -> bool:
    text = target_file.read_text(encoding="utf-8")

    loc = find_function_block(text, func_name)
    if not loc:
        print(f"  ⚠️  Cannot find {func_name}() in {target_file}")
        return False
    start, end, indent = loc
    func_text = text[start:end]

    # idempotency
    start_mark = f"# [AUTO-ORCH {slice_name} START]"
    end_mark = f"# [AUTO-ORCH {slice_name} END]"
    if start_mark in func_text and end_mark in func_text:
        print(f"  • {slice_name}: already wired in {target_file} (markers present)")
        return True

    header, body = split_header_body(func_text, indent)
    block = build_block(slice_name, steps, bynum, indent)

    # ensure import
    new_text = ensure_orchestrators_import(text)

    # re-fetch indices because text may have changed after import insertion
    loc2 = find_function_block(new_text, func_name)
    if not loc2:
        print(f"  ❌ Unexpected: lost {func_name} after import insertion")
        return False
    s2, e2, ind2 = loc2
    ftxt2 = new_text[s2:e2]
    h2, b2 = split_header_body(ftxt2, ind2)

    patched = new_text[:s2] + h2 + "\n" + block + b2 + new_text[e2:]
    if dry:
        print(f"  • (dry-run) would inject {slice_name} ({len(steps)} steps) into {target_file}:{func_name}")
        return True

    target_file.write_text(patched, encoding="utf-8")
    print(f"  ✅ Injected {slice_name} ({len(steps)} steps) into {target_file}:{func_name}")
    return True


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description="Autowire orchestrator calls into real code, from autoroute.yml.")
    ap.add_argument(
        "--slice",
        help="Name of a slice in autoroute.yml to process (e.g., providers, cache, retry, entry, prompting, tools, docs, response, feedback, rss)",
    )
    ap.add_argument("--all", action="store_true", help="Process all slices from autoroute.yml")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not STEPS_YML.exists():
        raise SystemExit(f"Missing steps registry: {STEPS_YML}")
    if not AUTOROUTE_YML.exists():
        raise SystemExit(f"Missing autoroute config: {AUTOROUTE_YML}")

    # 1) ensure orchestrator stubs exist
    ensure_scaffold(args.dry_run)

    # 2) load registries
    steps_by_num = load_steps_registry()
    config = load_autoroute()
    slices = config.get("slices", {})

    # 3) choose which slices
    to_run = slices
    if args.slice:
        if args.slice not in slices:
            print(f"Slice '{args.slice}' not in autoroute.yml; available: {', '.join(slices.keys())}")
            return 2
        to_run = {args.slice: slices[args.slice]}
    elif not args.all:
        print("Nothing to do: pass --slice <name> or --all")
        return 0

    # 4) process each slice
    total = 0
    for name, spec in to_run.items():
        file_rel = spec.get("target_file")
        func_name = spec.get("target_function")
        step_specs = spec.get("steps", [])
        if not (file_rel and func_name and step_specs):
            print(f"⚠️  Slice '{name}' missing target_file/target_function/steps")
            continue

        steps = parse_step_specs(step_specs)
        if not steps:
            print(f"⚠️  Slice '{name}' has no steps after parsing")
            continue

        target = ROOT / file_rel
        if not target.exists():
            print(f"⚠️  Slice '{name}' target file missing: {target}")
            continue

        ok = inject_slice(target, func_name, name, steps, steps_by_num, args.dry_run)
        if ok:
            total += len(steps)

    print(
        f"\nDone. {'Previewed' if args.dry_run else 'Processed'} {len(to_run)} slice(s); wired {total} step call(s)."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
