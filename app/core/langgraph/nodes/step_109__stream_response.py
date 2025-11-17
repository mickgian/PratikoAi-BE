"""Node wrapper for Step 109: Stream Response."""

from typing import Any, Dict

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.streaming import step_109__stream_response

STEP = 109


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


async def node_step_109(state: RAGState) -> RAGState:
    """Node wrapper for Step 109: Create StreamingResponse with SSE chunks."""
    rag_step_log(STEP, "enter", streaming=state.get("streaming"))
    with rag_step_timer(STEP):
        res = await step_109__stream_response(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        streaming = state.setdefault("streaming", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "response_sent" in res:
            streaming["response_sent"] = res["response_sent"]

        _merge(streaming, res.get("streaming_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", response_sent=streaming.get("response_sent"))
    return state
