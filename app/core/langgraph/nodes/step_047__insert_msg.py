"""Node wrapper for Step 47: Insert Message.

Internal step - inserts new system message with selected prompt.
"""

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.prompting import step_47__insert_msg

STEP = 47


async def node_step_47(state: RAGState) -> RAGState:
    """Node wrapper for Step 47: Insert system message.

    Args:
        state: Current RAG state with messages and selected prompt

    Returns:
        Updated state with inserted system message
    """
    message_count = len(state.get("messages", []))
    rag_step_log(STEP, "enter", message_count=message_count)

    with rag_step_timer(STEP):
        # Call sync orchestrator - returns updated messages list
        updated_messages = step_47__insert_msg(messages=state.get("messages", []), ctx=dict(state))

        # Update messages with inserted system message
        if updated_messages is not None:
            state["messages"] = updated_messages
            state["sys_msg_inserted"] = True
        else:
            state["sys_msg_inserted"] = False

    rag_step_log(
        STEP, "exit", inserted=state.get("sys_msg_inserted"), new_message_count=len(state.get("messages", []))
    )
    return state
