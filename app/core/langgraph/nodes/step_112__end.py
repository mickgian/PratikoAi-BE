"""RAG STEP 112 — End node implementation."""

from typing import Any, Dict

from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.orchestrators.response import step_112__end
from app.core.langgraph.types import RAGState


async def node_step_112(state: RAGState) -> Dict[str, Any]:
    """Node implementation for Step 112: End.

    Final response boundary that returns response to user.
    Terminal node in the Phase 1A graph.

    Args:
        state: Current RAG state

    Returns:
        Updated state dict
    """
    rag_step_log(
        step=112,
        step_id="RAG.response.return.response.to.user",
        node_label="End",
        msg="enter",
        processing_stage="node_entry"
    )

    with rag_step_timer(
        step=112,
        step_id="RAG.response.return.response.to.user",
        node_label="End"
    ):
        # Convert state to dict for orchestrator compatibility
        state_dict = state.model_dump() if hasattr(state, 'model_dump') else dict(state)

        # Call existing orchestrator function
        result = await step_112__end(
            messages=state_dict.get('messages'),
            ctx=state_dict,
        )

        # Update state with results
        if isinstance(result, dict):
            state_dict.update(result)

        # Prepare final response
        if state_dict.get('error_code'):
            # Error response
            state_dict['final_response'] = {
                'error': state_dict.get('error_message', 'Unknown error'),
                'status_code': state_dict.get('error_code', 500)
            }
        elif state_dict.get('cached_response'):
            # Cached response
            state_dict['final_response'] = {
                'content': state_dict['cached_response'],
                'source': 'cache'
            }
        elif state_dict.get('llm_response'):
            # LLM response
            state_dict['final_response'] = {
                'content': state_dict['llm_response'],
                'source': 'llm'
            }
        else:
            # Default response
            state_dict['final_response'] = {
                'content': 'Response processed successfully',
                'source': 'default'
            }

        # Track processing
        state_dict['processing_stage'] = 'completed'
        node_history = state_dict.get('node_history', [])
        node_history.append('End')
        state_dict['node_history'] = node_history

    rag_step_log(
        step=112,
        step_id="RAG.response.return.response.to.user",
        node_label="End",
        msg="exit",
        processing_stage="node_exit",
        response_source=state_dict.get('final_response', {}).get('source'),
        node_path=state_dict.get('node_history')
    )

    return state_dict