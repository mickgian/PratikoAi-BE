"""Node wrapper for Step 26: KB Context Check."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.kb import step_26__kbcontext_check

STEP = 26


async def node_step_26(state: RAGState) -> RAGState:
    """Node wrapper for Step 26: Fetch recent KB for changes."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()), kb=state.get("kb"), golden=state.get("golden"))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        result = await step_26__kbcontext_check(messages=messages, ctx=dict(state))

        # Merge result back into state additively
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store KB context in nested dict (additive)
        kb = state.setdefault("kb", {})
        kb["docs"] = result.get("kb_docs", []) if isinstance(result, dict) else []
        kb["epoch"] = result.get("kb_epoch") if isinstance(result, dict) else None
        kb["has_recent_changes"] = result.get("has_recent_changes", False) if isinstance(result, dict) else False

        # Log metric for KB override tracking
        if kb.get("has_recent_changes"):
            rag_step_log(STEP, "metric",
                        metric="kb_override",
                        signature=state.get("query_signature"),
                        override=True)

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    has_recent_changes=kb.get("has_recent_changes"),
                    kb=kb)
        return state
