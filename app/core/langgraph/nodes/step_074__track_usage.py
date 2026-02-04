"""Node wrapper for Step 74: Track Usage."""

from typing import Any, Dict

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.metrics import step_74__track_usage

STEP = 74


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


async def node_step_74(state: RAGState) -> RAGState:
    """Node wrapper for Step 74: Track LLM usage metrics."""
    rag_step_log(STEP, "enter", metrics=state.get("metrics"))
    with rag_step_timer(STEP):
        # DEV-254: Extract correct field names from state for the orchestrator.
        # step_064 stores model as "model_used" and provider as a dict.
        model = state.get("model_used") or (state.get("llm") or {}).get("model_used")
        provider_raw = state.get("provider")
        provider = provider_raw.get("selected") if isinstance(provider_raw, dict) else provider_raw

        res = await step_74__track_usage(
            messages=state.get("messages"),
            ctx=dict(state),
            model=model,
            provider=provider,
        )

        # Map to canonical state keys
        metrics = state.setdefault("metrics", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        _merge(metrics, res)
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", tracked=metrics.get("tracked"))
    return state
