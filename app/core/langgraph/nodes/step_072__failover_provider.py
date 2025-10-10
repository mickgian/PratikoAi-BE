"""Node wrapper for Step 72: Failover Provider."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.providers import step_72__get_failover_provider
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 72


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


async def node_step_72(state: RAGState) -> RAGState:
    """Node wrapper for Step 72: Get failover provider."""
    rag_step_log(STEP, "enter", provider=state.get("provider"))
    with rag_step_timer(STEP):
        res = await step_72__get_failover_provider(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        provider = state.setdefault("provider", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "failover" in res:
            provider["failover"] = res["failover"]

        _merge(provider, res.get("provider_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", failover=provider.get("failover"))
    return state