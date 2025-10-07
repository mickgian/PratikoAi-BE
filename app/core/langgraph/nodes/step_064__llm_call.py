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
        # Call orchestrator
        result = await step_64__llmcall(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Populate consistent LLM state keys
        llm_request = state.get("llm_request")
        llm_response = state.get("llm_response")

        # Initialize LLM state structure
        if "llm" not in state:
            state["llm"] = {}

        state["llm"]["request"] = llm_request
        state["llm"]["response"] = llm_response
        state["llm"]["success"] = llm_response is not None

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state