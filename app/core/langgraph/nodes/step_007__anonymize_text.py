"""Node wrapper for Step 7: Anonymize Text."""

from typing import Any, Dict

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.privacy import step_7__anonymize_text

STEP = 7


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


async def node_step_7(state: RAGState) -> RAGState:
    """Node wrapper for Step 7: Anonymize Text."""
    rag_step_log(STEP, "enter", keys=list(state.keys()))
    with rag_step_timer(STEP):
        res = await step_7__anonymize_text(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        privacy = state.setdefault("privacy", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "anonymized_text" in res:
            privacy["anonymized_input"] = res["anonymized_text"]
        if "anonymized_messages" in res:
            privacy["anonymized_messages"] = res["anonymized_messages"]

        _merge(privacy, res.get("privacy_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", anonymized=bool(privacy.get("anonymized_input")))
    return state
