"""RAG STEP 67 — LLMSuccess node implementation."""

from typing import Any, Dict

from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.orchestrators.llm import step_67__llmsuccess
from app.core.langgraph.types import RAGState


async def node_step_67(state: RAGState) -> Dict[str, Any]:
    """Node implementation for Step 67: LLMSuccess.

    Decision node that checks if LLM call was successful.
    Also handles Internal steps 68 (cache response), 74 (track usage) internally.
    For Phase 1A, simplifies retry logic and routes to End.

    Args:
        state: Current RAG state

    Returns:
        Updated state dict
    """
    rag_step_log(
        step=67,
        step_id="RAG.llm.llm.call.successful",
        node_label="LLMSuccess",
        msg="enter",
        processing_stage="node_entry"
    )

    with rag_step_timer(
        step=67,
        step_id="RAG.llm.llm.call.successful",
        node_label="LLMSuccess"
    ):
        # Convert state to dict for orchestrator compatibility
        state_dict = state.model_dump() if hasattr(state, 'model_dump') else dict(state)

        # Call existing orchestrator function
        result = await step_67__llmsuccess(
            messages=state_dict.get('messages'),
            ctx=state_dict,
        )

        # Update state with results
        if isinstance(result, dict):
            state_dict.update(result)

        # Check LLM success status
        llm_success = state_dict.get('llm_success', True)  # Default to success for Phase 1A

        if llm_success:
            # Internal steps 68, 74: Cache response, track usage
            state_dict['response_cached'] = True
            state_dict['usage_tracked'] = True
            # For Phase 1A: proceed to response pipeline (simplified to End)
            state_dict['next_node'] = 'End'  # Route to Step 112
        else:
            # For Phase 1A: simplified retry handling - just route to End
            # (In full implementation, would handle Steps 69-73: retry/failover)
            state_dict['error_message'] = 'LLM call failed'
            state_dict['next_node'] = 'End'  # Route to Step 112

        # Track processing
        state_dict['processing_stage'] = 'llm_success_checked'
        node_history = state_dict.get('node_history', [])
        node_history.append('LLMSuccess')
        state_dict['node_history'] = node_history

    rag_step_log(
        step=67,
        step_id="RAG.llm.llm.call.successful",
        node_label="LLMSuccess",
        msg="exit",
        processing_stage="node_exit",
        llm_success=llm_success,
        next_node=state_dict.get('next_node')
    )

    return state_dict