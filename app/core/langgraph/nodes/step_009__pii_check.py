"""Node wrapper for Step 9: PII Check."""

from typing import Any, Dict

from app.core.langgraph.node_utils import mirror
from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.platform import step_9__piicheck as step_9__pii_check

# Re-export for test patching
__all__ = ["node_step_9", "step_9__pii_check"]

STEP = 9


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


async def node_step_9(state: RAGState) -> RAGState:
    """Node wrapper for Step 9: PII Check (Decision)."""
    rag_step_log(STEP, "enter", keys=list(state.keys()))
    with rag_step_timer(STEP):
        res = step_9__pii_check(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        privacy = state.setdefault("privacy", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "pii_detected" in res:
            privacy["pii_detected"] = res["pii_detected"]
            decisions["pii_detected"] = res["pii_detected"]
        mirror(state, "pii_detected", bool(res.get("pii_detected", False)))

        _merge(privacy, res.get("privacy_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", pii_detected=privacy.get("pii_detected"))
    return state
