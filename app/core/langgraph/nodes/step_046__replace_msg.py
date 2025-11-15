"""Node wrapper for Step 46: Replace Message.

Internal step - replaces existing system message with selected prompt.
"""

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.prompting import step_46__replace_msg

STEP = 46


async def node_step_46(state: RAGState) -> RAGState:
    """Node wrapper for Step 46: Replace system message.

    Args:
        state: Current RAG state with messages and selected prompt

    Returns:
        Updated state with replaced system message
    """
    sys_msg_index = state.get("sys_msg_index")
    rag_step_log(STEP, "enter", sys_msg_index=sys_msg_index)

    with rag_step_timer(STEP):
        # Call sync orchestrator - returns updated messages list
        updated_messages = step_46__replace_msg(messages=state.get("messages", []), ctx=dict(state))

        # Update messages with replaced system message
        if updated_messages is not None:
            state["messages"] = updated_messages
            state["sys_msg_replaced"] = True
        else:
            state["sys_msg_replaced"] = False

    rag_step_log(STEP, "exit", replaced=state.get("sys_msg_replaced"))
    return state
