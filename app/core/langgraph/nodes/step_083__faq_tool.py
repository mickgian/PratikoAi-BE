"""Node wrapper for Step 83: FAQ Tool."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.golden import step_83__faqquery

STEP = 83


async def node_step_83(state: RAGState) -> RAGState:
    """Node wrapper for Step 83: Execute FAQ query tool."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_83__faqquery(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        # Store tool results
        if "tools" not in new_state:
            new_state["tools"] = {}
        new_state["tools"]["faq_results"] = result
        new_state["tools"]["executed"] = "faq"

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state