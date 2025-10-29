"""Node wrapper for Step 20: Golden Fast Gate."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.core.langgraph.node_utils import mirror
from app.orchestrators.golden import step_20__golden_fast_gate
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 20


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


async def node_step_20(state: RAGState) -> RAGState:
    """Node wrapper for Step 20: Golden fast-path eligible check."""
    rag_step_log(STEP, "enter", golden=state.get("golden"))
    with rag_step_timer(STEP):
        res = await step_20__golden_fast_gate(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        golden = state.setdefault("golden", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        if "golden_eligible" in res:
            golden["eligible"] = res["golden_eligible"]
            decisions["golden_eligible"] = res["golden_eligible"]
        mirror(state, "golden_eligible", bool(res.get("golden_eligible", False)))
        if "should_check_golden" in res:
            mirror(state, "should_check_golden", bool(res["should_check_golden"]))

        _merge(golden, res.get("golden_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", eligible=golden.get("eligible"))
    return state
