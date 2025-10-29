"""Node wrapper for Step 82: Doc Ingest Tool."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.preflight import step_82__doc_ingest
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 82


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


async def node_step_82(state: RAGState) -> RAGState:
    """Node wrapper for Step 82: Execute document ingest tool."""
    rag_step_log(STEP, "enter", tools=state.get("tools"))
    with rag_step_timer(STEP):
        res = await step_82__doc_ingest(
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