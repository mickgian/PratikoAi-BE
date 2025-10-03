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
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_62__cache_hit(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        # This is a decision node - read cache state from previous step
        cache_hit = new_state.get("cache", {}).get("hit", False)

        # Store decision result for routing
        new_state["cache_hit_decision"] = cache_hit

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state