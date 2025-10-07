"""Node wrapper for Step 10: Log PII."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import platform as orchestrators

STEP = 10


async def node_step_10(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 10: Log PII Anonymization.

    Delegates to the orchestrator and logs PII anonymization details.
    """
    privacy = state.setdefault("privacy", {})

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator (cast to dict for type compatibility)
        result = await orchestrators.step_10__log_pii(ctx=dict(state), messages=state.get("messages"))

        # Merge result fields into state (preserving existing data)
        if isinstance(result, dict):
            if "pii_logged" in result:
                privacy["pii_logged"] = bool(result["pii_logged"])
            if "log_timestamp" in result:
                privacy["log_timestamp"] = result["log_timestamp"]

        rag_types.rag_step_log(STEP, "exit", privacy=privacy, pii_logged=privacy.get("pii_logged"))

    return state
