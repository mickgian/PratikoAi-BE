"""Node wrapper for Step 4: GDPR Log."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import privacy as orchestrators

STEP = 4


async def node_step_4(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 4: GDPR Log.

    Delegates to the orchestrator and updates state with GDPR processing log.
    """
    privacy = state.setdefault("privacy", {})

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator (cast to dict for type compatibility)
        result = await orchestrators.step_4__gdprlog(ctx=dict(state), messages=state.get("messages"))

        # Merge result fields into state (preserving existing data)
        if isinstance(result, dict):
            if "gdpr_logged" in result:
                privacy["gdpr_logged"] = bool(result["gdpr_logged"])
            if "processing_recorded" in result:
                privacy["processing_recorded"] = bool(result["processing_recorded"])
            if "processing_id" in result:
                privacy["processing_id"] = result["processing_id"]

        rag_types.rag_step_log(STEP, "exit", privacy=privacy, gdpr_logged=privacy.get("gdpr_logged"))

    return state
