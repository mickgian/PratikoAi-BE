"""Node wrapper for Step 53: Balance Provider."""

from typing import Any, Dict

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.providers import step_53__balance_provider

STEP = 53


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


async def node_step_53(state: RAGState) -> RAGState:
    """Node wrapper for Step 53: Balance Provider."""
    rag_step_log(STEP, "enter", strategy="BALANCED")
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only (sync function)
        res = step_53__balance_provider(ctx=dict(state))

        # Map orchestrator outputs to canonical state keys (additive)
        provider = state.setdefault("provider", {})
        decisions = state.setdefault("decisions", {})

        # Map fields with name translation if needed
        # DON'T store provider object (has circular refs) - extract metadata only
        if "provider" in res and res["provider"]:
            prov_obj = res["provider"]
            provider["provider_type"] = res.get("provider_type") or (
                prov_obj.provider_type.value
                if hasattr(prov_obj.provider_type, "value")
                else str(prov_obj.provider_type)
            )
            provider["model"] = res.get("model") or getattr(prov_obj, "model", None)
            provider["cost_per_token"] = res.get("cost_per_token") or getattr(prov_obj, "cost_per_token", 0.0)
        provider["strategy"] = "BALANCED"

        # Merge any extra structured data
        _merge(provider, res.get("provider_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", selected=provider.get("selected"))
    return state
