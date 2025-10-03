"""Node wrapper for Step 74: Track Usage."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.metrics import step_74__track_usage

STEP = 74


async def node_step_74(state: RAGState) -> RAGState:
    """Node wrapper for Step 74: Track LLM usage metrics."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_74__track_usage(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        # Update metrics tracking status
        if "metrics" not in new_state:
            new_state["metrics"] = {}
        new_state["metrics"]["usage_tracked"] = True

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state