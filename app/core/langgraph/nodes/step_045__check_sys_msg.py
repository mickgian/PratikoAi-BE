"""Node wrapper for Step 45: Check System Message.

Internal step - checks if system message already exists in message list.
"""

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.prompting import step_45__check_sys_msg

STEP = 45


async def node_step_45(state: RAGState) -> RAGState:
    """Node wrapper for Step 45: Check if system message exists.

    Args:
        state: Current RAG state with messages

    Returns:
        Updated state with system message check result
    """
    message_count = len(state.get("messages", []))
    rag_step_log(STEP, "enter", message_count=message_count)

    with rag_step_timer(STEP):
        # Call sync orchestrator
        res = step_45__check_sys_msg(messages=state.get("messages", []), ctx=dict(state))

        # Store check result
        state["sys_msg_exists"] = res.get("sys_msg_exists", False)
        state["sys_msg_index"] = res.get("sys_msg_index")

    rag_step_log(STEP, "exit", sys_msg_exists=state.get("sys_msg_exists"), sys_msg_index=state.get("sys_msg_index"))
    return state
