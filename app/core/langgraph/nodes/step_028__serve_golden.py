"""Node wrapper for Step 28: Serve Golden."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.core.langgraph.node_utils import mirror
from app.orchestrators.golden import step_28__serve_golden
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 28


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


async def node_step_28(state: RAGState) -> RAGState:
    """Node wrapper for Step 28: Serve Golden answer with citations."""
    rag_step_log(STEP, "enter", golden=state.get("golden"))
    with rag_step_timer(STEP):
        res = await step_28__serve_golden(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        golden = state.setdefault("golden", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "answer" in res:
            golden["answer"] = res["answer"]
        if "citations" in res:
            golden["citations"] = res["citations"]
        golden["served"] = True
        mirror(state, "golden_served", True)
        if "complete" in res:
            mirror(state, "complete", bool(res["complete"]))

        _merge(golden, res.get("golden_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", served=golden.get("served"))
    return state
