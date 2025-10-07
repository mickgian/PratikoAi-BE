"""Node wrapper for Step 2: Start."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.platform import step_2__start

STEP = 2


def node_step_2(state: RAGState) -> RAGState:
    """Node wrapper for Step 2: Start processing."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])

        # Call orchestrator (cast to dict for type compatibility)
        result = step_2__start(messages=messages, ctx=dict(state))

        # Merge result fields into state (preserving existing data)
        if isinstance(result, dict):
            # Selectively update state with known fields from result
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        rag_step_log(STEP, "exit", keys=list(state.keys()))

        return state