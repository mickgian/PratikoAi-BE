"""Node wrapper for Step 107: Single Pass Stream."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.core.langgraph.node_utils import mirror
from app.orchestrators.preflight import step_107__single_pass
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 107


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


async def node_step_107(state: RAGState) -> RAGState:
    """Node wrapper for Step 107: Wrap stream with single-pass protection."""
    rag_step_log(STEP, "enter", streaming=state.get("streaming"))
    with rag_step_timer(STEP):
        res = await step_107__single_pass(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        streaming = state.setdefault("streaming", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "single_pass" in res:
            streaming["single_pass"] = res["single_pass"]
        if "response_complete" in res:
            streaming["response_complete"] = res["response_complete"]
        mirror(state, "response_complete", bool(res.get("response_complete", False)))

        _merge(streaming, res.get("streaming_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", single_pass=streaming.get("single_pass"))
    return state
