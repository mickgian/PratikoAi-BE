"""Node wrapper for Step 105: Stream Setup."""

from typing import Any, Dict

from app.core.langgraph.node_utils import mirror
from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.streaming import step_105__stream_setup

STEP = 105


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


async def node_step_105(state: RAGState) -> RAGState:
    """Node wrapper for Step 105: Setup SSE streaming infrastructure."""
    rag_step_log(STEP, "enter", streaming=state.get("streaming"))
    with rag_step_timer(STEP):
        res = await step_105__stream_setup(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        streaming = state.setdefault("streaming", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "setup" in res:
            streaming["setup"] = res["setup"]
        if "sse_ready" in res:
            streaming["sse_ready"] = res["sse_ready"]
        mirror(state, "sse_ready", bool(res.get("sse_ready", False)))
        if "generator_created" in res:
            mirror(state, "generator_created", bool(res["generator_created"]))

        _merge(streaming, res.get("streaming_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", setup=streaming.get("setup"))
    return state
