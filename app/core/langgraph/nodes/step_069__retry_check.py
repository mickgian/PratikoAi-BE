"""Node wrapper for Step 69: Retry Check."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.platform import step_69__retry_check
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 69


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


async def node_step_69(state: RAGState) -> RAGState:
    """Node wrapper for Step 69: Retry check decision node."""
    rag_step_log(STEP, "enter", llm=state.get("llm"))
    with rag_step_timer(STEP):
        res = await step_69__retry_check(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        llm = state.setdefault("llm", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "retry_allowed" in res:
            llm["retry_allowed"] = res["retry_allowed"]
            decisions["retry_allowed"] = res["retry_allowed"]

        _merge(llm, res.get("llm_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", retry_allowed=llm.get("retry_allowed"))
    return state