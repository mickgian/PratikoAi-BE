"""RAG STEP 62 — CacheHit node implementation."""

from typing import Any, Dict

from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.orchestrators.cache import step_62__cache_hit
from app.core.langgraph.types import RAGState


async def node_step_62(state: RAGState) -> Dict[str, Any]:
    """Node implementation for Step 62: CacheHit.

    Decision node that checks if cache hit occurred.
    Also handles Internal steps 63, 65-66 (track cache hit, log, return cached) internally.

    Args:
        state: Current RAG state

    Returns:
        Updated state dict
    """
    rag_step_log(
        step=62,
        step_id="RAG.cache.cache.hit",
        node_label="CacheHit",
        msg="enter",
        processing_stage="node_entry"
    )

    with rag_step_timer(
        step=62,
        step_id="RAG.cache.cache.hit",
        node_label="CacheHit"
    ):
        # Convert state to dict for orchestrator compatibility
        state_dict = state.model_dump() if hasattr(state, 'model_dump') else dict(state)

        # Call existing orchestrator function
        result = await step_62__cache_hit(
            messages=state_dict.get('messages'),
            ctx=state_dict,
        )

        # Update state with results
        if isinstance(result, dict):
            state_dict.update(result)

        # Check cache hit status
        cache_hit = state_dict.get('cache_hit', False)

        if cache_hit:
            # Internal steps 63, 65, 66: Track cache hit, log, return cached
            state_dict['cache_hit_tracked'] = True
            state_dict['cache_hit_logged'] = True
            state_dict['cached_response'] = "Cached response placeholder"
            state_dict['next_node'] = 'End'  # Route to Step 112
        else:
            # Route to LLM call
            state_dict['next_node'] = 'LLMCall'  # Route to Step 64

        # Track processing
        state_dict['processing_stage'] = 'cache_hit_checked'
        node_history = state_dict.get('node_history', [])
        node_history.append('CacheHit')
        state_dict['node_history'] = node_history

    rag_step_log(
        step=62,
        step_id="RAG.cache.cache.hit",
        node_label="CacheHit",
        msg="exit",
        processing_stage="node_exit",
        cache_hit=cache_hit,
        next_node=state_dict.get('next_node')
    )

    return state_dict