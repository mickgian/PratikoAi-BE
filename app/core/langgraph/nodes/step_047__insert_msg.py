"""Node wrapper for Step 47: Insert Message.

Internal step - inserts new system message with selected prompt.
"""

from app.core.langgraph.types import RAGState
from app.core.logging import logger as step47_logger
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

    # DEV-007 DIAGNOSTIC: Log what system_prompt is being used
    system_prompt = state.get("system_prompt", "")
    step47_logger.info(
        "DEV007_step47_system_prompt_before_insert",
        extra={
            "prompt_length": len(system_prompt),
            "prompt_preview_end": system_prompt[-1500:] if len(system_prompt) > 1500 else system_prompt,
            "contains_kb_context_header": "# Relevant Knowledge Base Context" in system_prompt,
            "contains_payslip_8": "Payslip 8" in system_prompt or "PAYSLIP_8" in system_prompt,
            "contains_payslip_9": "Payslip 9" in system_prompt or "PAYSLIP_9" in system_prompt,
        },
    )

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
