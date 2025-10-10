"""Node wrapper for Step 30: Return Complete."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.response import step_30__return_complete
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 30


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


async def node_step_30(state: RAGState) -> RAGState:
    """Node wrapper for Step 30: Return ChatResponse."""
    rag_step_log(STEP, "enter", complete=state.get("complete"))
    with rag_step_timer(STEP):
        res = await step_30__return_complete(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        response = state.setdefault("response", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "complete" in res:
            response["complete"] = res["complete"]
            state["complete"] = True

        _merge(response, res.get("response_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", complete=state.get("complete"))
    return state
