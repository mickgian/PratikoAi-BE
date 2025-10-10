"""Node wrapper for Step 111: Collect Metrics."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.metrics import step_111__collect_metrics
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 111


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


async def node_step_111(state: RAGState) -> RAGState:
    """Node wrapper for Step 111: Collect usage metrics."""
    rag_step_log(STEP, "enter", metrics=state.get("metrics"))
    with rag_step_timer(STEP):
        res = await step_111__collect_metrics(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        metrics = state.setdefault("metrics", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        _merge(metrics, res)
        _merge(decisions, res.get("decisions", {}))

        # Set complete metadata
        state["complete"] = True

    rag_step_log(STEP, "exit", collected=metrics.get("collected"))
    return state
