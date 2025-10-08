"""Node wrapper for Step 27: KB Delta."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.golden import step_27__kbdelta

STEP = 27


async def node_step_27(state: RAGState) -> RAGState:
    """Node wrapper for Step 27: KB newer than Golden or conflicting tags check."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()), kb=state.get("kb"), golden=state.get("golden"))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        result = await step_27__kbdelta(messages=messages, ctx=dict(state))

        # Merge result back into state additively
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store KB delta result in nested dict (additive)
        kb = state.setdefault("kb", {})
        kb["delta"] = result.get("kb_has_delta", False) if isinstance(result, dict) else False
        kb["conflict_reason"] = result.get("conflict_reason") if isinstance(result, dict) else None

        # Store decision for routing
        decisions = state.setdefault("decisions", {})
        decisions["kb_required"] = kb.get("delta", False)

        # Log metric for KB override tracking
        if kb.get("delta"):
            rag_step_log(STEP, "metric",
                        metric="kb_override",
                        signature=state.get("query_signature"),
                        override=True,
                        reason=kb.get("conflict_reason"))

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    kb_has_delta=kb.get("delta"),
                    decisions=decisions)
        return state
