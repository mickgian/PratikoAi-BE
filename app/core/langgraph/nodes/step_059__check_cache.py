"""Node wrapper for Step 59: Check Cache."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.core.langgraph.node_utils import ns, mirror
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.cache import step_59__check_cache

STEP = 59


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


async def node_step_59(state: RAGState) -> RAGState:
    """Node wrapper for Step 59: Check Cache."""
    rag_step_log(STEP, "enter", cache_key=state.get("cache_key"))
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only
        res = await step_59__check_cache(
            messages=state.get("messages"),
            ctx=dict(state)
        )

        # Map orchestrator outputs to canonical state keys (additive)
        cache = ns(state, "cache")
        decisions = state.setdefault("decisions", {})

        # Map fields with name translation if needed
        if "cache_key" in res:
            cache["key"] = res["cache_key"]

        # Ensure hit is explicitly set
        if "hit" in res:
            cache["hit"] = bool(res["hit"])
        elif "cache_hit" in res:
            cache["hit"] = bool(res["cache_hit"])
        else:
            cache.setdefault("hit", False)

        # Handle cached response
        if cache.get("hit"):
            cached = res.get("value") or res.get("cached_response")
            if cached is not None:
                cache["value"] = cached
                mirror(state, "cached_response", cached)

        # Merge any extra structured data
        _merge(cache, res.get("cache_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", cache_hit=cache.get("hit"))
    return state