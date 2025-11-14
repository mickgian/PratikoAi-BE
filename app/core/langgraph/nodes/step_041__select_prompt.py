"""Node wrapper for Step 41: Select Prompt.

Canonical node - selects appropriate system prompt based on classification.
"""

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.prompting import step_41__select_prompt

STEP = 41


async def node_step_41(state: RAGState) -> RAGState:
    """Node wrapper for Step 41: Select appropriate prompt.

    Delegates to step_41__select_prompt orchestrator and maps selected
    prompt to state.

    Args:
        state: Current RAG state with classification data

    Returns:
        Updated state with selected prompt
    """
    classification = state.get("classification", {})
    domain = classification.get("domain")
    confidence = classification.get("confidence", 0.0)

    rag_step_log(STEP, "enter", domain=domain, confidence=confidence)

    with rag_step_timer(STEP):
        # Call orchestrator with context from state
        res = await step_41__select_prompt(messages=state.get("messages", []), ctx=dict(state))

        # Map orchestrator output to canonical state keys
        # Store as both selected_prompt and system_prompt for compatibility
        prompt_str = res.get("selected_prompt", "")
        state["selected_prompt"] = prompt_str  # For step 41 tracking
        state["system_prompt"] = prompt_str  # For step 47 insertion
        state["prompt_metadata"] = {
            "prompt_type": res.get("prompt_type", "default"),
            "domain": res.get("domain"),
            "action": res.get("action"),
            "classification_confidence": res.get("classification_confidence", 0.0),
            "prompt_selected": res.get("prompt_selected", False),
            "timestamp": res.get("timestamp"),
        }

    rag_step_log(
        STEP,
        "exit",
        prompt_type=state["prompt_metadata"]["prompt_type"],
        prompt_selected=state["prompt_metadata"]["prompt_selected"],
    )
    return state
