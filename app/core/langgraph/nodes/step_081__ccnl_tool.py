"""Node wrapper for Step 81: CCNL Tool."""

from typing import Any, Dict

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.ccnl import step_81__ccnlquery

STEP = 81


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


async def node_step_81(state: RAGState) -> RAGState:
    """Node wrapper for Step 81: Execute CCNL query tool."""
    rag_step_log(STEP, "enter", tools=state.get("tools"))
    with rag_step_timer(STEP):
        res = await step_81__ccnlquery(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        tools = state.setdefault("tools", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "results" in res:
            tools["results"] = res["results"]
        if "tool_success" in res:
            tools["tool_success"] = res["tool_success"]

        _merge(tools, res.get("tools_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", success=tools.get("tool_success"))
    return state
