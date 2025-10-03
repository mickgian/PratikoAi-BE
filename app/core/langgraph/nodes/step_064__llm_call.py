"""Node wrapper for Step 64: LLM Call."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.providers import step_64__llmcall

STEP = 64


async def node_step_64(state: RAGState) -> RAGState:
    """Node wrapper for Step 64: Make LLM API call."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        # Convert RAGState to the format expected by orchestrator
        messages = state.get("messages", [])
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_64__llmcall(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        # Populate consistent LLM state keys
        llm_request = new_state.get("llm_request")
        llm_response = new_state.get("llm_response")

        # Initialize LLM state structure
        if "llm" not in new_state:
            new_state["llm"] = {}

        new_state["llm"]["request"] = llm_request
        new_state["llm"]["response"] = llm_response
        new_state["llm"]["success"] = llm_response is not None

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state