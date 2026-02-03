"""Tree of Thoughts orchestration for complex queries.

Executes multi-hypothesis reasoning with source-weighted scoring.
"""

from typing import TYPE_CHECKING, Any

from app.core.logging import logger

if TYPE_CHECKING:
    from app.services.tree_of_thoughts_reasoner import ToTResult, TreeOfThoughtsReasoner

# Type alias for RAG state dict
RAGStateDict = dict[str, Any]

# Cached reasoner instance
_tot_reasoner_instance: "TreeOfThoughtsReasoner | None" = None


def get_tot_reasoner() -> "TreeOfThoughtsReasoner":
    """Get or create TreeOfThoughtsReasoner instance (lazy loading)."""
    global _tot_reasoner_instance
    if _tot_reasoner_instance is None:
        from app.services.tree_of_thoughts_reasoner import get_tree_of_thoughts_reasoner

        _tot_reasoner_instance = get_tree_of_thoughts_reasoner()
    return _tot_reasoner_instance


def extract_user_message(state: RAGStateDict) -> str:
    """Extract user message from state."""
    user_message = state.get("user_message", "")
    if not user_message:
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, dict) and msg.get("role") == "user":
                return msg.get("content", "")
    return user_message


async def use_tree_of_thoughts(state: RAGStateDict, complexity: str) -> "ToTResult":
    """Execute Tree of Thoughts reasoning for complex queries.

    DEV-226: Uses TreeOfThoughtsReasoner for multi-hypothesis reasoning
    with source-weighted scoring for complex and multi_domain queries.

    Args:
        state: RAG state with query and KB sources
        complexity: Query complexity ("complex" or "multi_domain")

    Returns:
        ToTResult with selected hypothesis and reasoning trace
    """
    user_message = extract_user_message(state)
    reasoner = get_tot_reasoner()

    # DEV-251: Pass conversation history for follow-up context
    conversation_history = state.get("messages", [])

    # DEV-251 Part 3.1: Extract is_followup from routing_decision
    routing_decision = state.get("routing_decision", {})
    is_followup = routing_decision.get("is_followup", False)

    logger.info(
        "tot_orchestrator_is_followup",
        is_followup=is_followup,
        query_length=len(user_message),
    )

    return await reasoner.reason(
        query=user_message,
        kb_sources=state.get("kb_sources_metadata", []),
        complexity=complexity,
        domains=state.get("detected_domains") if complexity == "multi_domain" else None,
        conversation_history=conversation_history,
        is_followup=is_followup,
    )
