"""Node wrapper for Step 3: Valid Check."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.platform import step_3__valid_check
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 3


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


async def node_step_3(state: RAGState) -> RAGState:
    """Node wrapper for Step 3: Valid Check (Decision)."""
    rag_step_log(STEP, "enter", keys=list(state.keys()))
    with rag_step_timer(STEP):
        res = await step_3__valid_check(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "is_valid" in res:
            decisions["request_valid"] = res["is_valid"]
            decisions["is_valid"] = res["is_valid"]

        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", request_valid=decisions.get("request_valid"))
    return state
