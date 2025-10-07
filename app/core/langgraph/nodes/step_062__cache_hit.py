"""Node wrapper for Step 62: Cache Hit."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.cache import step_62__cache_hit

STEP = 62


async def node_step_62(state: RAGState) -> RAGState:
    """Node wrapper for Step 62: Cache hit decision node."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        # Convert RAGState to the format expected by orchestrator
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_62__cache_hit(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # This is a decision node - read cache state from previous step
        cache_hit = state.get("cache", {}).get("hit", False)

        # Store decision result for routing
        state["cache_hit_decision"] = cache_hit

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state