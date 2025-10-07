"""Node wrapper for Step 81: CCNL Tool."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.ccnl import step_81__ccnlquery

STEP = 81


async def node_step_81(state: RAGState) -> RAGState:
    """Node wrapper for Step 81: Execute CCNL query tool."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_81__ccnlquery(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store tool results
        if "tools" not in state:
            state["tools"] = {}
        state["tools"]["ccnl_results"] = result
        state["tools"]["executed"] = "ccnl"

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state