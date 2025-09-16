#!/usr/bin/env python3
from typing import Any, Dict

try:
    from app.observability.rag_logging import rag_step_log
except Exception:  # pragma: no cover
    def rag_step_log(*args, **kwargs):
        return None

STEP = 45
STEP_ID = "RAG.prompting.system.message.exists"
NODE_LABEL = "CheckSysMsg"
CATEGORY = "prompting"
TYPE = "decision"

__all__ = ["run", "step_45_rag_prompting_system_message_exists"]


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
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


def step_45_rag_prompting_system_message_exists(payload: Dict[str, Any]) -> Dict[str, Any]:
    return run(payload)
