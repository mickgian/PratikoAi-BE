"""Node wrapper for Step 55: Estimate Cost."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.core.langgraph.node_utils import ns, mirror
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.providers import step_55__estimate_cost

STEP = 55


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


async def node_step_55(state: RAGState) -> RAGState:
    """Node wrapper for Step 55: Estimate Cost."""
    rag_step_log(STEP, "enter", provider=state.get("provider", {}).get("selected"))
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only
        res = await step_55__estimate_cost(ctx=dict(state))

        # Map orchestrator outputs to canonical state keys (additive)
        provider = ns(state, "provider")
        decisions = state.setdefault("decisions", {})

        # Map fields with name translation (CRITICAL: estimated_cost -> estimate)
        if "estimated_cost" in res:
            provider["estimate"] = res["estimated_cost"]
        elif "cost_estimate" in res:
            provider["estimate"] = res["cost_estimate"]
        mirror(state, "cost_estimate", res.get("cost_estimate", res.get("estimated_cost")))
        if "cost_details" in res:
            provider["cost_details"] = res["cost_details"]
        # Also handle within_budget if returned by estimate (for test compatibility)
        if "within_budget" in res:
            provider["budget_ok"] = res["within_budget"]
            mirror(state, "within_budget", res["within_budget"])

        # Merge any extra structured data
        _merge(provider, res.get("provider_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", estimate=provider.get("estimate"))
    return state