"""Node wrapper for Step 66: Return Cached."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.cache import step_66__return_cached

STEP = 66


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


async def node_step_66(state: RAGState) -> RAGState:
    """Node wrapper for Step 66: Return Cached."""
    rag_step_log(STEP, "enter", cache_hit=state.get("cache", {}).get("hit"))
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only
        res = await step_66__return_cached(
            messages=state.get("messages"),
            ctx=dict(state)
        )

        # Map orchestrator outputs to canonical state keys (additive)
        cache = state.setdefault("cache", {})
        decisions = state.setdefault("decisions", {})

        # Mark that we're returning cached response
        if cache.get("hit"):
            cache["returning"] = True

        # Merge any extra structured data
        _merge(cache, res.get("cache_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", returning_cached=cache.get("returning"))
    return state