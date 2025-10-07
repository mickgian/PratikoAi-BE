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
        # Call orchestrator
        result = await step_83__faqquery(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store tool results
        if "tools" not in state:
            state["tools"] = {}
        state["tools"]["faq_results"] = result
        state["tools"]["executed"] = "faq"

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state