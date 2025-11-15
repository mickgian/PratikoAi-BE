"""Node wrapper for Step 50: Strategy Type (Decision)."""

from typing import Any, Dict

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.platform import step_50__strategy_type

STEP = 50


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


async def node_step_50(state: RAGState) -> RAGState:
    """Node wrapper for Step 50: Strategy Type (Decision)."""
    rag_step_log(STEP, "enter", strategy=state.get("route_strategy"))
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only
        res = await step_50__strategy_type(ctx=dict(state))

        # Map orchestrator outputs to canonical state keys (additive)
        provider = state.setdefault("provider", {})
        decisions = state.setdefault("decisions", {})

        # Map fields with name translation if needed (CRITICAL mapping)
        if "strategy_type" in res:
            decisions["strategy_type"] = res["strategy_type"]
            provider["strategy_type"] = res["strategy_type"]

        # Merge any extra structured data
        _merge(provider, res.get("provider_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", strategy_type=decisions.get("strategy_type"))
    return state
