"""Node wrapper for Step 79: Tool Type."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.routing import step_79__tool_type
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 79


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


async def node_step_79(state: RAGState) -> RAGState:
    """Node wrapper for Step 79: Determine tool type decision node."""
    rag_step_log(STEP, "enter", tools=state.get("tools"))
    with rag_step_timer(STEP):
        res = await step_79__tool_type(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        tools = state.setdefault("tools", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "tool_type" in res:
            tools["tool_type"] = res["tool_type"]
            decisions["tool_type"] = res["tool_type"]

        _merge(tools, res.get("tools_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", tool_type=tools.get("tool_type"))
    return state