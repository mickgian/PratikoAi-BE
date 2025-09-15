# -*- coding: utf-8 -*-
"""
RAG STEP 64 — LLMProvider.chat_completion Make API call
ID: RAG.providers.llmprovider.chat.completion.make.api.call
Type: process
Category: providers

Purpose
-------
Adapter to align code symbols to the blueprint step for conformance.
No business logic here; real work happens in the provider classes.
"""

from typing import Any, Dict

try:
    from app.observability.rag_logging import rag_step_log
except Exception:  # pragma: no cover
    def rag_step_log(**kwargs):
        return None

STEP = 64
STEP_ID = "RAG.providers.llmprovider.chat.completion.make.api.call"
NODE_LABEL = "LLMCall"  # short Mermaid node label works best
CATEGORY = "providers"
TYPE = "process"

__all__ = ["run"]


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Conformance adapter for STEP 64."""
    try:
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="N/A",
            confidence=1.0,
            reasons=["adapter_sentinel"],
            trace_id=payload.get("trace_id") if isinstance(payload, dict) else None,
        )
    except Exception:
        pass
    return {"step": STEP, "step_id": STEP_ID, "node": NODE_LABEL, "ok": True}
