"""Node wrapper for Step 10: Log PII."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.platform import step_10__log_pii
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 10


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


async def node_step_10(state: RAGState) -> RAGState:
    """Node wrapper for Step 10: Log PII Anonymization."""
    rag_step_log(STEP, "enter", keys=list(state.keys()))
    with rag_step_timer(STEP):
        res = await step_10__log_pii(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        privacy = state.setdefault("privacy", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "pii_logged" in res:
            privacy["pii_logged"] = res["pii_logged"]

        _merge(privacy, res.get("privacy_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", pii_logged=privacy.get("pii_logged"))
    return state
