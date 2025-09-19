#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Focused RAG audit: audit only selected steps (much faster than full run).

Usage:
  python scripts/rag_audit_focus.py --steps 20
  python scripts/rag_audit_focus.py --steps 20,39,59,79,82,64 --verbose
  python scripts/rag_audit_focus.py --steps 20,39 --dry-run
"""
import argparse, sys
from pathlib import Path

def parse_csv_ints(s: str):
    return sorted({int(x.strip()) for x in s.split(",") if x.strip()})

def main():
    ap = argparse.ArgumentParser(description="Focused RAG audit")
    ap.add_argument("--steps", required=True, help="Comma-separated step numbers to audit (e.g., 20,39,59)")
    ap.add_argument("--dry-run", action="store_true", help="Do not write docs/dashboard")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    base = Path(__file__).parent.parent
    sys.path.insert(0, str(base / "scripts"))
    from rag_audit import RAGAuditor

    steps_file = base / "docs/architecture/rag_steps.yml"
    code_index = base / "build/rag_code_index.json"

    keep = set(parse_csv_ints(args.steps))

    auditor = RAGAuditor(steps_file, code_index, verbose=args.verbose)
    auditor.load_data()
    auditor.steps = [s for s in auditor.steps if s["step"] in keep]

    if not auditor.steps:
        print(f"No steps matched: {sorted(keep)}")
        return 0

    print(f"🔎 Auditing steps: {', '.join(str(s['step']) for s in auditor.steps)}")
    summary = auditor.audit_all_steps()

    if not args.dry_run:
        print("📝 Updating step docs…")
        auditor.update_step_docs(base)
        print("📊 Updating conformance dashboard…")
        auditor.update_conformance_dashboard(base)
        print("✅ Done.")

    print("\n📊 Summary:")
    print(f"  Total: {len(auditor.steps)}")
    for k in ["✅","🟡","🔌","❌"]:
        print(f"  {k}: {summary['by_status'].get(k,0)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
