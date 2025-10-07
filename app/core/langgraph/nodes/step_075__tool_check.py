"""Node wrapper for Step 75: Tool Check."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.response import step_75__tool_check

STEP = 75


async def node_step_75(state: RAGState) -> RAGState:
    """Node wrapper for Step 75: Check if tools are needed."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_75__tool_check(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Check if tools are requested
        tools_requested = state.get("tools_requested", False)

        # Update tools state
        if "tools" not in state:
            state["tools"] = {}
        state["tools"]["requested"] = tools_requested

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state