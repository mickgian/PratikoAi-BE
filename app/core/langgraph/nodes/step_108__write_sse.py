"""Node wrapper for Step 108: Write SSE."""

from typing import Any, Dict

from app.core.langgraph.node_utils import mirror
from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.streaming import step_108__write_sse

STEP = 108


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


async def node_step_108(state: RAGState) -> RAGState:
    """Node wrapper for Step 108: Format chunks into SSE format."""
    rag_step_log(STEP, "enter", streaming=state.get("streaming"))
    with rag_step_timer(STEP):
        res = await step_108__write_sse(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        streaming = state.setdefault("streaming", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "chunks_sent" in res:
            streaming["chunks_sent"] = res["chunks_sent"]
        if "write_success" in res:
            streaming["write_success"] = res["write_success"]
        mirror(state, "write_success", bool(res.get("write_success", False)))
        if "chunks_written" in res:
            mirror(state, "chunks_written", res["chunks_written"])

        _merge(streaming, res.get("streaming_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", chunks_sent=streaming.get("chunks_sent"))
    return state
