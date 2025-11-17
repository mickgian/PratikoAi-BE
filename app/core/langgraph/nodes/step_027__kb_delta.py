"""Node wrapper for Step 27: KB Delta."""

from typing import Any, Dict

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.golden import step_27__kbdelta

# Re-export for test patching
step_27__kb_delta = step_27__kbdelta
__all__ = ["node_step_27", "step_27__kb_delta"]

STEP = 27


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


async def node_step_27(state: RAGState) -> RAGState:
    """Node wrapper for Step 27: KB newer than Golden or conflicting tags check."""
    rag_step_log(STEP, "enter", kb=state.get("kb"))
    with rag_step_timer(STEP):
        res = await step_27__kbdelta(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        kb = state.setdefault("kb", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "kb_has_delta" in res:
            kb["has_delta"] = res["kb_has_delta"]
            decisions["kb_required"] = res["kb_has_delta"]

        _merge(kb, res.get("kb_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", has_delta=kb.get("has_delta"))
    return state
