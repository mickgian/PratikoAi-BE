"""Node wrapper for Step 54: Primary Provider."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.providers import step_54__primary_provider

STEP = 54


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


async def node_step_54(state: RAGState) -> RAGState:
    """Node wrapper for Step 54: Primary Provider."""
    rag_step_log(STEP, "enter", strategy="PRIMARY")
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only
        res = await step_54__primary_provider(ctx=dict(state))

        # Map orchestrator outputs to canonical state keys (additive)
        provider = state.setdefault("provider", {})
        decisions = state.setdefault("decisions", {})

        # Map fields with name translation if needed
        if "provider" in res:
            provider["selected"] = res["provider"]
        provider["strategy"] = "PRIMARY"

        # Merge any extra structured data
        _merge(provider, res.get("provider_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", selected=provider.get("selected"))
    return state