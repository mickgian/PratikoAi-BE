"""Node wrapper for Step 48: Select Provider."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.core.langgraph.node_utils import ns, mirror
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.providers import step_48__select_provider

STEP = 48


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


async def node_step_48(state: RAGState) -> RAGState:
    """Node wrapper for Step 48: Select Provider."""
    rag_step_log(STEP, "enter", strategy=state.get("route_strategy"))
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only (sync function)
        res = step_48__select_provider(ctx=dict(state))

        # Map orchestrator outputs to canonical state keys (additive)
        provider = ns(state, "provider")
        decisions = state.setdefault("decisions", {})

        # Map fields with name translation if needed
        if "strategy" in res:
            provider["strategy"] = res["strategy"]
        if "provider" in res:
            provider["selected"] = res["provider"]
            # Flatten for tests
            if isinstance(res["provider"], dict):
                provider["name"] = res["provider"].get("name", provider.get("name"))
                provider["model"] = res["provider"].get("model", provider.get("model"))
            mirror(state, "provider_selected", True)

        # Merge any extra structured data
        _merge(provider, res.get("provider_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", strategy=provider.get("strategy"))
    return state