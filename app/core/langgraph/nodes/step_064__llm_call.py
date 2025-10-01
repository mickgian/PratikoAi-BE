"""RAG STEP 64 — LLMCall node implementation."""

from typing import Any, Dict

from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.orchestrators.providers import step_64__llmcall
from app.core.langgraph.types import RAGState


async def node_step_64(state: RAGState) -> Dict[str, Any]:
    """Node implementation for Step 64: LLMCall.

    Makes LLM API call using selected provider.
    Routes to Step 67 (LLMSuccess) to check call result.

    Args:
        state: Current RAG state

    Returns:
        Updated state dict
    """
    rag_step_log(
        step=64,
        step_id="RAG.providers.llmprovider.chat.completion.make.api.call",
        node_label="LLMCall",
        msg="enter",
        processing_stage="node_entry"
    )

    with rag_step_timer(
        step=64,
        step_id="RAG.providers.llmprovider.chat.completion.make.api.call",
        node_label="LLMCall"
    ):
        # Convert state to dict for orchestrator compatibility
        state_dict = state.model_dump() if hasattr(state, 'model_dump') else dict(state)

        # Call existing orchestrator function
        result = await step_64__llmcall(
            messages=state_dict.get('messages'),
            ctx=state_dict,
        )

        # Update state with results
        if isinstance(result, dict):
            state_dict.update(result)

        # Always route to Step 67 (LLMSuccess check)
        state_dict['next_node'] = 'LLMSuccess'

        # Track processing
        state_dict['processing_stage'] = 'llm_called'
        node_history = state_dict.get('node_history', [])
        node_history.append('LLMCall')
        state_dict['node_history'] = node_history

    rag_step_log(
        step=64,
        step_id="RAG.providers.llmprovider.chat.completion.make.api.call",
        node_label="LLMCall",
        msg="exit",
        processing_stage="node_exit",
        llm_response_present=bool(state_dict.get('llm_response')),
        next_node=state_dict.get('next_node')
    )

    return state_dict