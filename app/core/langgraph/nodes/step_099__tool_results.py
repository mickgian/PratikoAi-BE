"""Node wrapper for Step 99: Tool Results."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.platform import step_99__tool_results
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 99


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


async def node_step_99(state: RAGState) -> RAGState:
    """Node wrapper for Step 99: Process and aggregate tool results."""
    rag_step_log(STEP, "enter", tools=state.get("tools"))
    with rag_step_timer(STEP):
        res = await step_99__tool_results(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        tools = state.setdefault("tools", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "results_returned" in res:
            tools["results_returned"] = res["results_returned"]

        _merge(tools, res.get("tools_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", results_returned=tools.get("results_returned"))
    return state