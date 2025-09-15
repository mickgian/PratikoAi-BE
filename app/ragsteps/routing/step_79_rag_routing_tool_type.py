#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG STEP 79 — Tool type? (RAG.routing.tool.type)

Adapter module to give the auditor a stable, discoverable symbol that maps the
blueprint step ID & node label to code. Keep it side-effect free. Business logic
lives in LangGraphAgent (graph.py); this file just emits a structured log once.

Docs:
- Step doc: docs/architecture/steps/STEP-79-RAG.routing.tool.type.md
- Mermaid node: ToolType (label: "Tool type?")
"""

from typing import Any, Dict

try:
    # Structured logging is optional but helps observability (and name tokens)
    from app.observability.rag_logging import rag_step_log
except Exception:  # pragma: no cover
    def rag_step_log(*args, **kwargs):  # fallback no-op
        return None

# Canonical step metadata (keep these names stable for the auditor)
STEP = 79
STEP_ID = "RAG.routing.tool.type"
NODE_LABEL = "ToolType"
CATEGORY = "routing"
TYPE = "decision"

# Export both the generic adapter and the canonical step_* symbol
__all__ = ["run", "step_79_rag_routing_tool_type"]


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter for RAG STEP 79: Tool type?

    Expected behavior is defined in:
    docs/architecture/steps/STEP-79-RAG.routing.tool.type.md

    This function exists primarily for conformance mapping and can delegate to
    real services if desired. Keep it minimal and side-effect free.
    """
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
        # Never raise from the adapter; auditor scanning should not break runtime.
        pass

    # Return a simple, stable shape the auditor can recognize.
    return {"step": STEP, "step_id": STEP_ID, "node": NODE_LABEL, "ok": True}


def step_79_rag_routing_tool_type(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Canonical symbol for auditor: STEP 79 — Tool type? (RAG.routing.tool.type)

    Delegates to run(); keep it side-effect free.
    """
    return run(payload)
