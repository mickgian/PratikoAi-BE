"""Node wrapper for Step 62: Cache Hit."""

from typing import Any, Dict

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.cache import step_62__cache_hit

STEP = 62


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


async def node_step_62(state: RAGState) -> RAGState:
    """Node wrapper for Step 62: Cache Hit."""
    cache_hit = state.get("cache", {}).get("hit", False)
    rag_step_log(STEP, "enter", cache_hit=cache_hit)
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only
        res = await step_62__cache_hit(messages=state.get("messages"), ctx=dict(state))

        # Map orchestrator outputs to canonical state keys (additive)
        cache = state.setdefault("cache", {})
        decisions = state.setdefault("decisions", {})

        # Store decision result for routing
        if "cache_hit_decision" in res:
            decisions["cache_hit"] = res["cache_hit_decision"]
        else:
            decisions["cache_hit"] = cache.get("hit", False)

        # Merge any extra structured data
        _merge(cache, res.get("cache_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", cache_hit=decisions.get("cache_hit"))
    return state
