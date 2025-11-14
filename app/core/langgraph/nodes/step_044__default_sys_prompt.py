"""Node wrapper for Step 44: Default System Prompt.

Internal step - uses default SYSTEM_PROMPT when classification confidence is low.
"""

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.prompting import step_44__default_sys_prompt

STEP = 44


async def node_step_44(state: RAGState) -> RAGState:
    """Node wrapper for Step 44: Use default system prompt.

    Args:
        state: Current RAG state

    Returns:
        Updated state with default prompt
    """
    rag_step_log(STEP, "enter", using_default=True)

    with rag_step_timer(STEP):
        # Call sync orchestrator - returns a string (the prompt)
        prompt = step_44__default_sys_prompt(messages=state.get("messages", []), ctx=dict(state))

        # Store default prompt (use both keys for compatibility)
        prompt_str = prompt if isinstance(prompt, str) else ""
        state["selected_prompt"] = prompt_str  # For step 41
        state["system_prompt"] = prompt_str  # For step 47
        state["prompt_metadata"] = state.get("prompt_metadata", {})
        state["prompt_metadata"]["prompt_type"] = "default"
        state["prompt_metadata"]["prompt_selected"] = bool(prompt)

    rag_step_log(STEP, "exit", prompt_set=state["prompt_metadata"].get("prompt_selected"))
    return state
