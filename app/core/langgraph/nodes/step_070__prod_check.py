"""Node wrapper for Step 70: Prod Check."""

from typing import Any, Dict

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.platform import step_70__prod_check

STEP = 70


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


async def node_step_70(state: RAGState) -> RAGState:
    """Node wrapper for Step 70: Production environment check decision node."""
    rag_step_log(STEP, "enter", llm=state.get("llm"))
    with rag_step_timer(STEP):
        res = await step_70__prod_check(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        llm = state.setdefault("llm", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "prod_check" in res:
            llm["prod_check"] = res["prod_check"]
        if "failover_needed" in res:
            decisions["failover_needed"] = res["failover_needed"]

        _merge(llm, res.get("llm_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", failover_needed=decisions.get("failover_needed"))
    return state
