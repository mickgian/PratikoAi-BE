"""Node wrapper for Step 6: Privacy Check."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import privacy as orchestrators

STEP = 6


async def node_step_6(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 6: Privacy Check (Decision).

    Delegates to the orchestrator and updates state with privacy check results.
    """
    privacy = state.setdefault("privacy", {})
    decisions = state.setdefault("decisions", {})

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator (cast to dict for type compatibility)
        result = await orchestrators.step_6__privacy_check(ctx=dict(state), messages=state.get("messages"))

        # Merge result fields into state (preserving existing data)
        if isinstance(result, dict):
            if "privacy_enabled" in result:
                privacy["enabled"] = bool(result["privacy_enabled"])
            if "anonymize_requests" in result:
                privacy["anonymize_requests"] = bool(result["anonymize_requests"])
            if "privacy_ok" in result:
                decisions["privacy_ok"] = bool(result["privacy_ok"])

        rag_types.rag_step_log(STEP, "exit", privacy=privacy, decisions=decisions)

    return state
