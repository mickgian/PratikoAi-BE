"""Node wrapper for Step 57: Create Provider."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.core.langgraph.node_utils import mirror
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.providers import step_57__create_provider

STEP = 57


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


async def node_step_57(state: RAGState) -> RAGState:
    """Node wrapper for Step 57: Create Provider."""
    rag_step_log(STEP, "enter", provider=state.get("provider", {}).get("selected"))
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only
        res = await step_57__create_provider(ctx=dict(state))

        # Map orchestrator outputs to canonical state keys (additive)
        provider = state.setdefault("provider", {})
        decisions = state.setdefault("decisions", {})

        # Map fields with name translation if needed
        if "provider_created" in res:
            provider["created"] = res["provider_created"]
        elif "created" in res:
            provider["created"] = res["created"]
        elif "provider_ready" in res:
            provider["created"] = res["provider_ready"]
        mirror(state, "provider_ready", bool(res.get("provider_ready", res.get("created", res.get("provider_created", False)))))

        if "provider_instance" in res:
            provider["instance"] = res["provider_instance"]
            mirror(state, "provider_instance", res["provider_instance"])

        # Merge any extra structured data
        _merge(provider, res.get("provider_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", created=provider.get("created"))
    return state