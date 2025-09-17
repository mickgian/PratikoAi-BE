# app/ragsteps/prompting/step_46_rag_prompting_replace_system_message.py
from typing import Any, Dict

try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover
    from contextlib import nullcontext
    def rag_step_log(*_, **__): ...
    def rag_step_timer(*_, **__): return nullcontext()

STEP = 46
STEP_ID = "RAG.prompting.replace.system.message"
NODE_LABEL = "ReplaceMsg"

__all__ = ["run", "step_46_rag_prompting_replace_system_message"]

def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    trace_id = payload.get("trace_id") if isinstance(payload, dict) else None
    with rag_step_timer(STEP, STEP_ID, NODE_LABEL, stage="adapter"):
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            action_taken="replace",
            confidence=1.0,
            reasons=["adapter_sentinel"],
            trace_id=trace_id,
        )
    return {"step": STEP, "step_id": STEP_ID, "node": NODE_LABEL, "ok": True}

def step_46_rag_prompting_replace_system_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    return run(payload)
