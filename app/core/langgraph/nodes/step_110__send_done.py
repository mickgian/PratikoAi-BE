"""Node wrapper for Step 110: Send Done."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.platform import step_110__send_done
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 110


def _merge(d: Dict[str, Any], patch: Dict[str, Any]) -> None:
    """Recursively merge patch into d (additive)."""
    for k, v in (patch or {}).items():
        if isinstance(v, dict):
            d.setdefault(k, {})
            if isinstance(d[k], dict):
                _merge(d[k], v)
            else:
                d[k] = v
        else:
            d[k] = v


async def node_step_110(state: RAGState) -> RAGState:
    """Node wrapper for Step 110: Send DONE frame to terminate streaming."""
    rag_step_log(STEP, "enter", streaming=state.get("streaming"))
    with rag_step_timer(STEP):
        res = await step_110__send_done(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        streaming = state.setdefault("streaming", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "done" in res:
            streaming["done"] = res["done"]

        _merge(streaming, res.get("streaming_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", done=streaming.get("done"))
    return state
