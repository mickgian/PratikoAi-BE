"""Node wrapper for Step 8: Init Agent."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.response import step_8__init_agent
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 8


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


async def node_step_8(state: RAGState) -> RAGState:
    """Node wrapper for Step 8: Initialize Workflow."""
    rag_step_log(STEP, "enter", keys=list(state.keys()))
    with rag_step_timer(STEP):
        res = await step_8__init_agent(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "agent_initialized" in res:
            state["agent_initialized"] = res["agent_initialized"]

        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", agent_initialized=state.get("agent_initialized"))
    return state
