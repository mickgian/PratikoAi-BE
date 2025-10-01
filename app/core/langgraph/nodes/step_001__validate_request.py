"""RAG STEP 1 — ValidateRequest node implementation."""

from typing import Any, Dict

from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.orchestrators.platform import step_1__validate_request
from app.core.langgraph.types import RAGState


async def node_step_1(state: RAGState) -> Dict[str, Any]:
    """Node implementation for Step 1: ValidateRequest.

    Thin wrapper around existing orchestrator function.

    Args:
        state: Current RAG state

    Returns:
        Updated state dict
    """
    rag_step_log(
        step=1,
        step_id="RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate",
        node_label="ValidateRequest",
        msg="enter",
        processing_stage="node_entry"
    )

    with rag_step_timer(
        step=1,
        step_id="RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate",
        node_label="ValidateRequest"
    ):
        # Convert state to dict for orchestrator compatibility
        state_dict = state.model_dump() if hasattr(state, 'model_dump') else dict(state)

        # Call existing orchestrator function
        result = await step_1__validate_request(
            messages=state_dict.get('messages'),
            ctx=state_dict,
        )

        # Update state with results
        if isinstance(result, dict):
            state_dict.update(result)

        # Track processing
        state_dict['processing_stage'] = 'validated'
        node_history = state_dict.get('node_history', [])
        node_history.append('ValidateRequest')
        state_dict['node_history'] = node_history

    rag_step_log(
        step=1,
        step_id="RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate",
        node_label="ValidateRequest",
        msg="exit",
        processing_stage="node_exit",
        request_valid=state_dict.get('request_valid'),
        user_authenticated=state_dict.get('user_authenticated')
    )

    return state_dict