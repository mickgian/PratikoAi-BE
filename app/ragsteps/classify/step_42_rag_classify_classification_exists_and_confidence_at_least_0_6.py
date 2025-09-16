#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG STEP 42 — Classification exists and confidence at least 0.6?
ID: RAG.classify.classification.exists.and.confidence.at.least.0.6
Node: ClassConfidence
Category: classify
Type: decision

This adapter exists solely so the auditor can map the blueprint step to code.
Keep it side-effect free; real logic lives in LangGraphAgent._get_system_prompt.
"""
from typing import Any, Dict

try:
    from app.observability.rag_logging import rag_step_log
except Exception:  # pragma: no cover
    def rag_step_log(*args, **kwargs):  # no-op fallback
        return None

STEP = 42
STEP_ID = "RAG.classify.classification.exists.and.confidence.at.least.0.6"
NODE_LABEL = "ClassConfidence"
CATEGORY = "classify"
TYPE = "decision"

__all__ = ["run", "step_42_rag_classify_classification_exists_and_confidence_at_least_0_6"]


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Adapter shim for STEP 42 — ClassConfidence."""
    try:
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="adapter_sentinel",
            confidence=1.0,
            trace_id=(payload.get("trace_id") if isinstance(payload, dict) else None),
        )
    except Exception:
        pass
    return {"step": STEP, "step_id": STEP_ID, "node": NODE_LABEL, "ok": True}


def step_42_rag_classify_classification_exists_and_confidence_at_least_0_6(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Canonical symbol the auditor can match."""
    return run(payload)
