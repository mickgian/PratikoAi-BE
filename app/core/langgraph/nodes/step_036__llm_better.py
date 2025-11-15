"""Node wrapper for Step 36: LLM Better Check.

Internal step - compares LLM vs rule-based classification quality.
"""

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.llm import step_36__llmbetter

STEP = 36


async def node_step_36(state: RAGState) -> RAGState:
    """Node wrapper for Step 36: Compare LLM vs rule-based quality.

    Args:
        state: Current RAG state with both classifications

    Returns:
        Updated state with comparison result
    """
    rag_step_log(STEP, "enter")

    with rag_step_timer(STEP):
        res = await step_36__llmbetter(messages=state.get("messages", []), ctx=dict(state))

        # Store comparison result
        classification = state.setdefault("classification", {})
        classification["llm_is_better"] = res.get("llm_is_better", False)
        classification["comparison_reasoning"] = res.get("reasoning")

    rag_step_log(STEP, "exit", llm_is_better=classification.get("llm_is_better"))
    return state
