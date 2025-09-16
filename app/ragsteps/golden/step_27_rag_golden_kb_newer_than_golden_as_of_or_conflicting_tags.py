#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG STEP 27 — KB newer than Golden as of or conflicting tags?
(RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags)

Adapter is a side-effect-free symbol so the auditor can find this step.
Business logic lives in the service (kb_delta_decision.py).
"""
from typing import Any, Dict

try:
    from app.observability.rag_logging import rag_step_log
except Exception:  # pragma: no cover
    def rag_step_log(*args, **kwargs):
        return None

STEP = 27
STEP_ID = "RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags"
NODE_LABEL = "KBDelta"
CATEGORY = "golden"
TYPE = "decision"

__all__ = [
    "run",
    "step_27_rag_golden_kb_newer_than_golden_as_of_or_conflicting_tags",
]


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Adapter for RAG STEP 27 (KBDelta)."""
    try:
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="adapter_sentinel",
            confidence=1.0,
            reasons=["adapter_mapping"],
            trace_id=payload.get("trace_id") if isinstance(payload, dict) else None,
        )
    except Exception:
        pass
    return {"step": STEP, "step_id": STEP_ID, "node": NODE_LABEL, "ok": True}


def step_27_rag_golden_kb_newer_than_golden_as_of_or_conflicting_tags(
        payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Canonical symbol wrapper for auditor."""
    return run(payload)
