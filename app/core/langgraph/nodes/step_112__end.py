"""Node wrapper for Step 112: End."""

from typing import Any, Dict

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.response import step_112__end

STEP = 112


def _merge(d: dict[str, Any], patch: dict[str, Any]) -> None:
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


async def node_step_112(state: RAGState) -> RAGState:
    """Node wrapper for Step 112: End terminal node."""
    rag_step_log(STEP, "enter", complete=state.get("complete"))
    with rag_step_timer(STEP):
        res = await step_112__end(
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
