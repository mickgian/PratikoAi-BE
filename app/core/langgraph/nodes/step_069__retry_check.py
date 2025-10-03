"""Node wrapper for Step 69: Retry Check."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.platform import step_69__retry_check

STEP = 69


async def node_step_69(state: RAGState) -> RAGState:
    """Node wrapper for Step 69: Retry check decision node."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_69__retry_check(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        # Decision logic based on orchestrator result
        # The orchestrator should set retry_allowed flag
        retry_allowed = new_state.get("retry_allowed", False)

        # Update llm state for retry tracking
        if "llm" not in new_state:
            new_state["llm"] = {}
        new_state["llm"]["retry_allowed"] = retry_allowed

        # Set retry count
        retry_count = new_state.get("llm", {}).get("retry_count", 0)
        new_state["llm"]["retry_count"] = retry_count + 1

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state