"""Node wrapper for Step 67: LLM Success."""

from typing import Any, Dict

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.llm import step_67__llmsuccess

STEP = 67


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


async def node_step_67(state: RAGState) -> RAGState:
    """Node wrapper for Step 67: LLM Success."""
    llm_success = state.get("llm", {}).get("success", True)
    rag_step_log(STEP, "enter", llm_success=llm_success)
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only
        res = await step_67__llmsuccess(messages=state.get("messages"), ctx=dict(state))

        # Map orchestrator outputs to canonical state keys (additive)
        llm = state.setdefault("llm", {})
        decisions = state.setdefault("decisions", {})

        # Store decision result for routing
        if "llm_success" in res:
            decisions["llm_success"] = res["llm_success"]
        else:
            decisions["llm_success"] = llm.get("success", True)

        # Merge any extra structured data
        _merge(llm, res.get("llm_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", llm_success=decisions.get("llm_success"))
    return state
