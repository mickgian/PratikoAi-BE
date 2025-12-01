"""Node wrapper for Step 24: Golden Lookup."""

from typing import Any, Dict

from app.core.langgraph.node_utils import mirror
from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.preflight import step_24__golden_lookup

STEP = 24


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


async def node_step_24(state: RAGState) -> RAGState:
    """Node wrapper for Step 24: Match by signature or semantic search."""
    rag_step_log(STEP, "enter", golden=state.get("golden"))
    with rag_step_timer(STEP):
        res = await step_24__golden_lookup(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        golden = state.setdefault("golden", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "match_found" in res:
            golden["match_found"] = res["match_found"]
        mirror(state, "match_found", bool(res.get("match_found", False)))
        mirror(state, "golden_hit", bool(res.get("match_found", False)))
        if "high_confidence_match" in res:
            mirror(state, "high_confidence_match", bool(res["high_confidence_match"]))
        if "similarity_score" in res:
            mirror(state, "similarity_score", res["similarity_score"])
        if "lookup" in res:
            golden["lookup"] = res["lookup"]

        # Map golden_match to state so Step 25 can read it
        if "golden_match" in res:
            state["golden_match"] = res["golden_match"]
            golden["match"] = res["golden_match"]

        _merge(golden, res.get("golden_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", match_found=golden.get("match_found"))
    return state
