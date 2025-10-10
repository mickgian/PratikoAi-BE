"""Node wrapper for Step 58: Cheaper Provider."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.core.langgraph.node_utils import mirror
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.providers import step_58__cheaper_provider

STEP = 58


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


async def node_step_58(state: RAGState) -> RAGState:
    """Node wrapper for Step 58: Cheaper Provider."""
    rag_step_log(STEP, "enter", provider=state.get("provider", {}).get("selected"))
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only
        res = await step_58__cheaper_provider(ctx=dict(state))

        # Map orchestrator outputs to canonical state keys (additive)
        provider = state.setdefault("provider", {})
        decisions = state.setdefault("decisions", {})

        # Map fields with name translation (CRITICAL: cheaper_found)
        if "provider" in res:
            provider["selected"] = res["provider"]
        if "cheaper_found" in res:
            provider["cheaper_found"] = res["cheaper_found"]
        elif "found" in res:
            provider["cheaper_found"] = res["found"]
        mirror(state, "cheaper_provider_found", bool(res.get("found", res.get("cheaper_found", False))))

        if "fallback_strategy" in res:
            provider["fallback_strategy"] = res["fallback_strategy"]

        # Merge any extra structured data
        _merge(provider, res.get("provider_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", cheaper_found=provider.get("cheaper_found"))
    return state