"""Node wrapper for Step 26: KB Context Check."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.core.langgraph.node_utils import mirror
from app.orchestrators.kb import step_26__kbcontext_check as step_26__kb_context_check
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

# Re-export for test patching
__all__ = ["node_step_26", "step_26__kb_context_check"]

STEP = 26


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


async def node_step_26(state: RAGState) -> RAGState:
    """Node wrapper for Step 26: Fetch recent KB for changes."""
    rag_step_log(STEP, "enter", kb=state.get("kb"))
    with rag_step_timer(STEP):
        res = await step_26__kb_context_check(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        kb = state.setdefault("kb", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "recent_context" in res:
            kb["recent_context"] = res["recent_context"]
        if "has_recent_changes" in res:
            kb["has_recent_changes"] = res["has_recent_changes"]
        mirror(state, "kb_required", bool(res.get("has_recent_changes", False)))

        _merge(kb, res.get("kb_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", has_recent_changes=kb.get("has_recent_changes"))
    return state
