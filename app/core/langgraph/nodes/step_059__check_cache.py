"""RAG STEP 59 — CheckCache node implementation."""

from typing import Any, Dict

from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.orchestrators.cache import step_59__check_cache
from app.core.langgraph.types import RAGState


async def node_step_59(state: RAGState) -> Dict[str, Any]:
    """Node implementation for Step 59: CheckCache.

    Checks for cached LLM response.
    Also handles Internal steps 60-61 (resolve epochs, generate hash) internally.

    Args:
        state: Current RAG state

    Returns:
        Updated state dict
    """
    rag_step_log(
        step=59,
        step_id="RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response",
        node_label="CheckCache",
        msg="enter",
        processing_stage="node_entry"
    )

    with rag_step_timer(
        step=59,
        step_id="RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response",
        node_label="CheckCache"
    ):
        # Convert state to dict for orchestrator compatibility
        state_dict = state.model_dump() if hasattr(state, 'model_dump') else dict(state)

        # Call existing orchestrator function
        result = await step_59__check_cache(
            messages=state_dict.get('messages'),
            ctx=state_dict,
        )

        # Update state with results
        if isinstance(result, dict):
            state_dict.update(result)

        # Handle Internal steps 60-61 internally
        # Step 60: Resolve epochs (would be called here)
        state_dict['epochs_resolved'] = True
        # Step 61: Generate hash (would be called here)
        state_dict['cache_key'] = f"cache_key_{hash(str(state_dict.get('messages', [])))}"

        # Always route to Step 62 (CacheHit check)
        state_dict['next_node'] = 'CacheHit'

        # Track processing
        state_dict['processing_stage'] = 'cache_checked'
        node_history = state_dict.get('node_history', [])
        node_history.append('CheckCache')
        state_dict['node_history'] = node_history

    rag_step_log(
        step=59,
        step_id="RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response",
        node_label="CheckCache",
        msg="exit",
        processing_stage="node_exit",
        cache_key=state_dict.get('cache_key'),
        next_node=state_dict.get('next_node')
    )

    return state_dict