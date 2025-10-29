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
        # Call orchestrator with business inputs only (sync function)
        res = step_54__primary_provider(ctx=dict(state))

        # Map orchestrator outputs to canonical state keys (additive)
        provider = state.setdefault("provider", {})
        decisions = state.setdefault("decisions", {})

        # Map fields with name translation if needed
        # DON'T store provider object (has circular refs) - extract metadata only
        if "provider" in res and res["provider"]:
            prov_obj = res["provider"]
            # Extract serializable metadata only
            provider["provider_type"] = res.get("provider_type") or (
                prov_obj.provider_type.value if hasattr(prov_obj.provider_type, 'value') else str(prov_obj.provider_type)
            )
            provider["model"] = res.get("model") or getattr(prov_obj, 'model', None)
            provider["cost_per_token"] = res.get("cost_per_token") or getattr(prov_obj, 'cost_per_token', 0.0)
        provider["strategy"] = "PRIMARY"

        # Merge any extra structured data
        _merge(provider, res.get("provider_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", selected=provider.get("selected"))
    return state