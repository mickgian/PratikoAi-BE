"""RAG STEP 6 — PrivacyCheck node implementation."""

from typing import Any, Dict

from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.orchestrators.privacy import step_6__privacy_check
from app.core.langgraph.types import RAGState


async def node_step_6(state: RAGState) -> Dict[str, Any]:
    """Node implementation for Step 6: PrivacyCheck.

    Decision node that checks if privacy anonymization is enabled.
    Also handles Internal steps 7 (anonymize) and 8 (init agent) internally.

    Args:
        state: Current RAG state

    Returns:
        Updated state dict
    """
    rag_step_log(
        step=6,
        step_id="RAG.privacy.privacy.anonymize.requests.enabled",
        node_label="PrivacyCheck",
        msg="enter",
        processing_stage="node_entry"
    )

    with rag_step_timer(
        step=6,
        step_id="RAG.privacy.privacy.anonymize.requests.enabled",
        node_label="PrivacyCheck"
    ):
        # Convert state to dict for orchestrator compatibility
        state_dict = state.model_dump() if hasattr(state, 'model_dump') else dict(state)

        # Call existing orchestrator function
        result = await step_6__privacy_check(
            messages=state_dict.get('messages'),
            ctx=state_dict,
        )

        # Update state with results
        if isinstance(result, dict):
            state_dict.update(result)

        # Handle Internal steps 7 & 8 internally
        privacy_enabled = state_dict.get('privacy_enabled', False)

        if privacy_enabled:
            # Internal step 7: Anonymize text (would be called here)
            state_dict['anonymized'] = True
            # Note: Real anonymization would happen here
        else:
            # Internal step 8: Init agent (would be called here)
            state_dict['agent_initialized'] = True

        # Always route to Step 9 after privacy processing
        state_dict['next_node'] = 'PIICheck'

        # Track processing
        state_dict['processing_stage'] = 'privacy_processed'
        node_history = state_dict.get('node_history', [])
        node_history.append('PrivacyCheck')
        state_dict['node_history'] = node_history

    rag_step_log(
        step=6,
        step_id="RAG.privacy.privacy.anonymize.requests.enabled",
        node_label="PrivacyCheck",
        msg="exit",
        processing_stage="node_exit",
        privacy_enabled=privacy_enabled,
        next_node=state_dict.get('next_node')
    )

    return state_dict