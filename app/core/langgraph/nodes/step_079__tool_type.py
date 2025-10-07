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
        # Call orchestrator
        result = await step_79__tool_type(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Extract tool type from orchestrator result
        tool_type = state.get("tool_type", "kb")  # Default to kb

        # Update tools state with type
        if "tools" not in state:
            state["tools"] = {}
        state["tools"]["type"] = tool_type

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state