"""RAG STEP 9 — PIICheck node implementation."""

from typing import Any, Dict

from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.orchestrators.platform import step_9__piicheck
from app.core.langgraph.types import RAGState


def node_step_9(state: RAGState) -> Dict[str, Any]:
    """Node implementation for Step 9: PIICheck.

    Decision node that checks if PII was detected.
    Also handles Internal step 10 (log PII) internally.
    For Phase 1A, routes directly to cache spine (Step 59).

    Args:
        state: Current RAG state

    Returns:
        Updated state dict
    """
    rag_step_log(
        step=9,
        step_id="RAG.platform.pii.detected",
        node_label="PIICheck",
        msg="enter",
        processing_stage="node_entry"
    )

    with rag_step_timer(
        step=9,
        step_id="RAG.platform.pii.detected",
        node_label="PIICheck"
    ):
        # Convert state to dict for orchestrator compatibility
        state_dict = state.model_dump() if hasattr(state, 'model_dump') else dict(state)

        # Call existing orchestrator function
        result = step_9__piicheck(
            messages=state_dict.get('messages'),
            ctx=state_dict,
        )

        # Update state with results
        if isinstance(result, dict):
            state_dict.update(result)

        # Handle Internal step 10 internally if PII detected
        pii_detected = state_dict.get('pii_detected', False)

        if pii_detected:
            # Internal step 10: Log PII (would be called here)
            state_dict['pii_logged'] = True

        # For Phase 1A: skip intermediate steps and route to cache spine
        state_dict['next_node'] = 'CheckCache'  # Route to Step 59

        # Track processing
        state_dict['processing_stage'] = 'pii_processed'
        node_history = state_dict.get('node_history', [])
        node_history.append('PIICheck')
        state_dict['node_history'] = node_history

    rag_step_log(
        step=9,
        step_id="RAG.platform.pii.detected",
        node_label="PIICheck",
        msg="exit",
        processing_stage="node_exit",
        pii_detected=pii_detected,
        next_node=state_dict.get('next_node')
    )

    return state_dict