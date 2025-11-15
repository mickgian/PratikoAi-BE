"""Node wrapper for Step 104: Stream Check."""

from typing import Any, Dict

from app.core.langgraph.node_utils import mirror
from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.streaming import step_104__stream_check

STEP = 104


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


async def node_step_104(state: RAGState) -> RAGState:
    """Node wrapper for Step 104: Determine if streaming is requested."""
    rag_step_log(STEP, "enter", streaming=state.get("streaming"))
    with rag_step_timer(STEP):
        res = await step_104__stream_check(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        streaming = state.setdefault("streaming", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "streaming_requested" in res:
            streaming["requested"] = res["streaming_requested"]
            decisions["streaming_requested"] = res["streaming_requested"]
        elif "stream_requested" in res:
            streaming["requested"] = res["stream_requested"]
            decisions["streaming_requested"] = res["stream_requested"]
        mirror(
            state,
            "streaming_enabled",
            bool(res.get("streaming_enabled", res.get("streaming_requested", res.get("stream_requested", False)))),
        )

        _merge(streaming, res.get("streaming_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", requested=streaming.get("requested"))
    return state
