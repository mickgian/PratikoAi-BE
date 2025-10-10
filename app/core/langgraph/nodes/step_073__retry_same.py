"""Node wrapper for Step 73: Retry Same."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.providers import step_73__retry_same
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 73


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


async def node_step_73(state: RAGState) -> RAGState:
    """Node wrapper for Step 73: Retry with same provider."""
    rag_step_log(STEP, "enter", provider=state.get("provider"))
    with rag_step_timer(STEP):
        res = await step_73__retry_same(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        provider = state.setdefault("provider", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "retry_same" in res:
            provider["retry_same"] = res["retry_same"]

        _merge(provider, res.get("provider_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", retry_same=provider.get("retry_same"))
    return state