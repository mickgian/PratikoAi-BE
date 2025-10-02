"""Node wrapper for Step 12: Extract Query."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.classify import step_12__extract_query

STEP = 12


async def node_step_12(state: RAGState) -> RAGState:
    """Node wrapper for Step 12: Extract user query from messages."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        # Convert RAGState to the format expected by orchestrator
        messages = state.get("messages", [])
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_12__extract_query(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state