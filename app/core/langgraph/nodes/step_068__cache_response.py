"""Node wrapper for Step 68: Cache Response."""

from typing import Any, Dict

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.cache import step_68__cache_response

STEP = 68


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


async def node_step_68(state: RAGState) -> RAGState:
    """Node wrapper for Step 68: Cache LLM response."""
    rag_step_log(STEP, "enter", cache=state.get("cache"))
    with rag_step_timer(STEP):
        res = await step_68__cache_response(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        cache = state.setdefault("cache", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "stored" in res:
            cache["stored"] = res["stored"]

        _merge(cache, res.get("cache_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", stored=cache.get("stored"))
    return state
