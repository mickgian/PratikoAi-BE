"""Node wrapper for Step 4: GDPR Log."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.privacy import step_4__gdprlog
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 4


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


async def node_step_4(state: RAGState) -> RAGState:
    """Node wrapper for Step 4: GDPR Log."""
    rag_step_log(STEP, "enter", keys=list(state.keys()))
    with rag_step_timer(STEP):
        res = await step_4__gdprlog(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        privacy = state.setdefault("privacy", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "gdpr_logged" in res:
            privacy["gdpr_logged"] = res["gdpr_logged"]

        _merge(privacy, res.get("privacy_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", gdpr_logged=privacy.get("gdpr_logged"))
    return state
