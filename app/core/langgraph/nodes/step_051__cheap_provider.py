"""Node wrapper for Step 51: Cheap Provider."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.providers import step_51__cheap_provider

STEP = 51


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


async def node_step_51(state: RAGState) -> RAGState:
    """Node wrapper for Step 51: Cheap Provider."""
    rag_step_log(STEP, "enter", strategy="CHEAP")
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only
        res = await step_51__cheap_provider(ctx=dict(state))

        # Map orchestrator outputs to canonical state keys (additive)
        provider = state.setdefault("provider", {})
        decisions = state.setdefault("decisions", {})

        # Map fields with name translation if needed
        if "provider" in res:
            provider["selected"] = res["provider"]
        provider["strategy"] = "CHEAP"

        # Merge any extra structured data
        _merge(provider, res.get("provider_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", selected=provider.get("selected"))
    return state