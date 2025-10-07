"""Node wrapper for Step 7: Anonymize Text."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import privacy as orchestrators

STEP = 7


async def node_step_7(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 7: Anonymize Text.

    Delegates to the orchestrator and updates state with anonymized content.
    """
    privacy = state.setdefault("privacy", {})

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator (cast to dict for type compatibility)
        result = await orchestrators.step_7__anonymize_text(ctx=dict(state), messages=state.get("messages"))

        # Merge result fields into state (preserving existing data)
        if isinstance(result, dict):
            if "anonymized_input" in result:
                privacy["anonymized_input"] = result["anonymized_input"]
            if "anonymized_messages" in result:
                privacy["anonymized_messages"] = result["anonymized_messages"]
            if "anonymization_applied" in result:
                privacy["anonymization_applied"] = bool(result["anonymization_applied"])

        rag_types.rag_step_log(STEP, "exit", privacy=privacy, anonymization_applied=privacy.get("anonymization_applied"))

    return state
