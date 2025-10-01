"""RAG STEP 3 — ValidCheck node implementation."""

from typing import Any, Dict

from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.orchestrators.platform import step_3__valid_check
from app.core.langgraph.types import RAGState


def node_step_3(state: RAGState) -> Dict[str, Any]:
    """Node implementation for Step 3: ValidCheck.

    Decision node that determines if request is valid.
    Also handles Internal steps 4 (GDPR log) and 5 (Error400) internally.

    Args:
        state: Current RAG state

    Returns:
        Updated state dict
    """
    rag_step_log(
        step=3,
        step_id="RAG.platform.request.valid",
        node_label="ValidCheck",
        msg="enter",
        processing_stage="node_entry"
    )

    with rag_step_timer(
        step=3,
        step_id="RAG.platform.request.valid",
        node_label="ValidCheck"
    ):
        # Convert state to dict for orchestrator compatibility
        state_dict = state.model_dump() if hasattr(state, 'model_dump') else dict(state)

        # Call existing orchestrator function
        result = step_3__valid_check(
            messages=state_dict.get('messages'),
            ctx=state_dict,
        )

        # Update state with results
        if isinstance(result, dict):
            state_dict.update(result)

        # Handle Internal steps 4 & 5 internally
        request_valid = state_dict.get('request_valid', True)

        if request_valid:
            # Internal step 4: GDPR log (would be called here)
            state_dict['gdpr_logged'] = True
            state_dict['next_node'] = 'PrivacyCheck'  # Route to Step 6
        else:
            # Internal step 5: Error 400 (would be called here)
            state_dict['error_code'] = 400
            state_dict['error_message'] = 'Bad Request'
            state_dict['next_node'] = 'End'  # Route to Step 112

        # Track processing
        state_dict['processing_stage'] = 'validation_checked'
        node_history = state_dict.get('node_history', [])
        node_history.append('ValidCheck')
        state_dict['node_history'] = node_history

    rag_step_log(
        step=3,
        step_id="RAG.platform.request.valid",
        node_label="ValidCheck",
        msg="exit",
        processing_stage="node_exit",
        request_valid=request_valid,
        next_node=state_dict.get('next_node')
    )

    return state_dict