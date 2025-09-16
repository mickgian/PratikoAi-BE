#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapter for RAG STEP 40 — BuildContext."""

from typing import Any, Dict

try:
    from app.observability.rag_logging import rag_step_log
except Exception:  # pragma: no cover
    def rag_step_log(*args, **kwargs):  # fallback no-op
        return None

STEP = 40
STEP_ID = "RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts"
NODE_LABEL = "BuildContext"
CATEGORY = "facts"
TYPE = "process"

__all__ = ["run", "step_40_rag_facts_contextbuilder_merge_facts_and_kb_docs_and_optional_doc_facts"]


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        rag_step_log(
            STEP, STEP_ID, NODE_LABEL,
            decision="N/A", confidence=1.0, reasons=["adapter_sentinel"],
            trace_id=payload.get("trace_id") if isinstance(payload, dict) else None,
        )
    except Exception:
        pass
    return {"step": STEP, "step_id": STEP_ID, "node": NODE_LABEL, "ok": True}


def step_40_rag_facts_contextbuilder_merge_facts_and_kb_docs_and_optional_doc_facts(payload: Dict[str, Any]) -> Dict[
    str, Any]:
    return run(payload)
