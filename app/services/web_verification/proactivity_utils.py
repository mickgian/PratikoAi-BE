"""Proactivity utilities for post-response processing.

DEV-250: Extracted from step_100__post_proactivity.py to reduce node size.
"""

from typing import Any

from app.core.langgraph.types import RAGState


def build_proactivity_update(
    preserve_pre_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build proactivity state update.

    Args:
        preserve_pre_response: Pre-response data to preserve

    Returns:
        Dict with proactivity field for state update
    """
    pre_response = preserve_pre_response or {"question": None, "skip_rag": False}

    return {
        "proactivity": {
            "pre_response": pre_response,
            "post_response": {
                # DEV-245 Phase 5.15: Actions removed per user feedback
            },
        },
    }


def get_response_content(state: RAGState) -> str:
    """Extract LLM response content from state.

    Args:
        state: Current RAG state

    Returns:
        Response content string
    """
    llm_data = state.get("llm") or {}
    llm_response = llm_data.get("response") if isinstance(llm_data, dict) else None

    if llm_response is None:
        return ""

    if isinstance(llm_response, dict):
        return llm_response.get("content", "")
    elif hasattr(llm_response, "content"):
        return llm_response.content or ""
    elif isinstance(llm_response, str):
        return llm_response

    return ""
