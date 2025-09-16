#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG STEP 26 — KnowledgeSearch.context_topk fetch recent KB for changes
(ID: RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes)

Adapter for auditor mapping. Keep side-effect free; business logic lives in
KnowledgeSearchService.fetch_recent_kb_for_changes().
"""
from typing import Any, Dict

try:
    from app.observability.rag_logging import rag_step_log
except Exception:  # pragma: no cover
    def rag_step_log(*args, **kwargs):  # fallback no-op
        return None

STEP = 26
STEP_ID = "RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes"
NODE_LABEL = "KBContextCheck"
CATEGORY = "kb"
TYPE = "process"

__all__ = ["run", "step_26_rag_kb_knowledgesearch_context_topk_fetch_recent_kb_for_changes"]


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    trace_id = payload.get("trace_id") if isinstance(payload, dict) else None
    try:
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="N/A",
            confidence=1.0,
            reasons=["adapter_sentinel"],
            trace_id=trace_id,
        )
    except Exception:
        pass
    return {"step": STEP, "step_id": STEP_ID, "node": NODE_LABEL, "ok": True}


def step_26_rag_kb_knowledgesearch_context_topk_fetch_recent_kb_for_changes(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Canonical symbol for auditor; delegates to run()."""
    return run(payload)
