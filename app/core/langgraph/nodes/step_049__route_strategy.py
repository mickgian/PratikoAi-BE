"""Node wrapper for Step 49: Route Strategy."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.facts import step_49__route_strategy

STEP = 49


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


async def node_step_49(state: RAGState) -> RAGState:
    """Node wrapper for Step 49: Route Strategy."""
    rag_step_log(STEP, "enter", routing_strategy=state.get("route_strategy"))
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only (sync function)
        res = step_49__route_strategy(ctx=dict(state))

        # Map orchestrator outputs to canonical state keys (additive)
        provider = state.setdefault("provider", {})
        decisions = state.setdefault("decisions", {})

        # Map fields with name translation if needed
        if "routing_strategy" in res:
            provider["routing_strategy"] = res["routing_strategy"]
        elif "strategy" in res:
            provider["routing_strategy"] = res["strategy"]

        # Merge any extra structured data
        _merge(provider, res.get("provider_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", routing_strategy=provider.get("routing_strategy"))
    return state