"""Node wrapper for Step 13: Message Exists."""

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.platform import step_13__message_exists

STEP = 13


async def node_step_13(state: RAGState) -> RAGState:
    """Node wrapper for Step 13: Check if user message exists."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])

        # Call orchestrator (cast to dict for type compatibility)
        result = await step_13__message_exists(messages=messages, ctx=dict(state))

        # Merge result fields into state (preserving existing data)
        if isinstance(result, dict):
            # Selectively update state with known fields from result
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        rag_step_log(STEP, "exit", keys=list(state.keys()))

        return state