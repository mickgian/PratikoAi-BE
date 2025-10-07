"""Node wrapper for Step 9: PII Check."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import platform as orchestrators

STEP = 9


async def node_step_9(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 9: PII Check (Decision).

    Delegates to the orchestrator and updates state with PII detection results.
    """
    privacy = state.setdefault("privacy", {})
    decisions = state.setdefault("decisions", {})

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator (cast to dict for type compatibility)
        result = await orchestrators.step_9__piicheck(ctx=dict(state), messages=state.get("messages"))

        # Merge result fields into state (preserving existing data)
        if isinstance(result, dict):
            if "pii_detected" in result:
                privacy["pii_detected"] = bool(result["pii_detected"])
                decisions["pii_detected"] = bool(result["pii_detected"])
            if "pii_entities" in result:
                privacy["pii_entities"] = result["pii_entities"]

        rag_types.rag_step_log(STEP, "exit", privacy=privacy, pii_detected=privacy.get("pii_detected"))

    return state
