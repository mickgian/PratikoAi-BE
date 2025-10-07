"""Node wrapper for Step 67: LLM Success."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.llm import step_67__llmsuccess

STEP = 67


async def node_step_67(state: RAGState) -> RAGState:
    """Node wrapper for Step 67: LLM success decision node."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        # Convert RAGState to the format expected by orchestrator
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_67__llmsuccess(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # This is a decision node - read LLM success from previous step
        llm_success = state.get("llm", {}).get("success", True)

        # Store decision result for routing
        state["llm_success_decision"] = llm_success

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state