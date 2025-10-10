"""Node wrapper for Step 75: Tool Check."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.response import step_75__tool_check
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 75


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


async def node_step_75(state: RAGState) -> RAGState:
    """Node wrapper for Step 75: Check if tools are needed."""
    rag_step_log(STEP, "enter", tools=state.get("tools"))
    with rag_step_timer(STEP):
        res = await step_75__tool_check(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        tools = state.setdefault("tools", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "has_tool_calls" in res:
            tools["has_tool_calls"] = res["has_tool_calls"]
            decisions["has_tool_calls"] = res["has_tool_calls"]

        _merge(tools, res.get("tools_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", has_tool_calls=tools.get("has_tool_calls"))
    return state