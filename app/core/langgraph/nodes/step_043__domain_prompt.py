"""Node wrapper for Step 43: Domain Prompt.

Internal step - retrieves domain-specific prompt based on classification.
"""

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.classify import step_43__domain_prompt

STEP = 43


async def node_step_43(state: RAGState) -> RAGState:
    """Node wrapper for Step 43: Get domain-specific prompt.

    Args:
        state: Current RAG state with classification

    Returns:
        Updated state with domain prompt
    """
    classification = state.get("classification", {})
    domain = classification.get("domain")

    rag_step_log(STEP, "enter", domain=domain)

    with rag_step_timer(STEP):
        res = await step_43__domain_prompt(messages=state.get("messages", []), ctx=dict(state))

        # Store domain prompt result
        state["domain_prompt"] = res.get("domain_prompt", "")
        state["prompt_metadata"] = state.get("prompt_metadata", {})
        state["prompt_metadata"]["domain_generated"] = res.get("prompt_generated", False)
        state["prompt_metadata"]["prompt_length"] = res.get("prompt_length", 0)

    rag_step_log(STEP, "exit", prompt_generated=state["prompt_metadata"].get("domain_generated"))
    return state
