"""Query complexity classification for LLM response generation.

Classifies queries as simple, complex, or multi_domain to route to appropriate models.
"""

from typing import TYPE_CHECKING, Any

from app.core.logging import logger

if TYPE_CHECKING:
    from app.services.llm_orchestrator import LLMOrchestrator

# Type alias for RAG state dict
RAGStateDict = dict[str, Any]

# Cached orchestrator instance
_orchestrator_instance: "LLMOrchestrator | None" = None


def get_llm_orchestrator() -> "LLMOrchestrator":
    """Get or create LLMOrchestrator instance (lazy loading)."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        from app.services.llm_orchestrator import get_llm_orchestrator as _get_orchestrator

        _orchestrator_instance = _get_orchestrator()
    return _orchestrator_instance


def extract_user_message(state: RAGStateDict) -> str:
    """Extract user message from state."""
    user_message = state.get("user_message", "")
    if not user_message:
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, dict) and msg.get("role") == "user":
                return msg.get("content", "")
    return user_message


async def classify_query_complexity(state: RAGStateDict) -> tuple[str, dict]:
    """Classify query complexity using LLMOrchestrator.

    Args:
        state: RAG state with user query and context

    Returns:
        Tuple of (complexity string, context dict for logging)
    """
    from app.services.llm_orchestrator import ComplexityContext

    try:
        orchestrator = get_llm_orchestrator()
        messages = state.get("messages", [])
        user_message = extract_user_message(state)
        detected_domains = state.get("detected_domains", [])

        context = ComplexityContext(
            domains=detected_domains,
            has_history=len(messages) > 1,
            has_documents=bool(state.get("kb_sources_metadata")),
        )
        complexity = await orchestrator.classify_complexity(user_message, context)

        return complexity.value, {
            "complexity": complexity.value,
            "domains": detected_domains,
            "has_history": context.has_history,
            "has_documents": context.has_documents,
        }
    except Exception as e:
        logger.warning("step64_complexity_classification_failed", error=str(e))
        return "simple", {"complexity": "simple", "fallback": True, "error": str(e)}
