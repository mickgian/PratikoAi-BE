"""Node wrapper for Step 79: Tool Type."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.routing import step_79__tool_type

STEP = 79


async def node_step_79(state: RAGState) -> RAGState:
    """Node wrapper for Step 79: Determine tool type decision node."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_79__tool_type(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        # Extract tool type from orchestrator result
        tool_type = new_state.get("tool_type", "kb")  # Default to kb

        # Update tools state with type
        if "tools" not in new_state:
            new_state["tools"] = {}
        new_state["tools"]["type"] = tool_type

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state