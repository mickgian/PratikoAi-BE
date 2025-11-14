"""Node wrapper for Step 6: Privacy Check."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.core.langgraph.node_utils import mirror
from app.orchestrators.privacy import step_6__privacy_check
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 6


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


async def node_step_6(state: RAGState) -> RAGState:
    """Node wrapper for Step 6: Privacy Check (Decision)."""
    rag_step_log(STEP, "enter", keys=list(state.keys()))
    with rag_step_timer(STEP):
        res = await step_6__privacy_check(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        privacy = state.setdefault("privacy", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "privacy_enabled" in res:
            privacy["enabled"] = res["privacy_enabled"]
        elif "enabled" in res:
            privacy["enabled"] = res["enabled"]
        mirror(state, "privacy_enabled", bool(res.get("enabled", res.get("privacy_enabled", False))))
        if "anonymize_required" in res:
            mirror(state, "anonymize_required", bool(res["anonymize_required"]))
        if "privacy_ok" in res:
            decisions["privacy_ok"] = res["privacy_ok"]

        _merge(privacy, res.get("privacy_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", enabled=privacy.get("enabled"), privacy_ok=decisions.get("privacy_ok"))
    return state
