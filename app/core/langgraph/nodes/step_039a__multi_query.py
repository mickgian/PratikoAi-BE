"""Step 39a: Multi-Query Expansion Node (DEV-195).

LangGraph node wrapper that integrates MultiQueryGeneratorService for
query expansion. Generates BM25, vector, and entity-focused query variants.

The node:
1. Checks routing_decision to determine if expansion is needed
2. Skips for CHITCHAT and THEORETICAL_DEFINITION routes
3. DEV-245: Expands short queries (<5 words) using conversation context
4. Calls MultiQueryGeneratorService.generate() for variants
5. Stores serialized QueryVariants in state["query_variants"]
6. Falls back to original query on any error

Usage in graph:
    graph.add_node("step_39a_multi_query", node_step_39a)
"""

import logging
import re
from typing import TYPE_CHECKING, Any

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.schemas.router import ExtractedEntity

# Lazy import to avoid database connection during module load
if TYPE_CHECKING:
    from app.services.multi_query_generator import MultiQueryGeneratorService

logger = logging.getLogger(__name__)

STEP_NUM = 39
STEP_ID = "RAG.query.multi_query"
NODE_LABEL = "step_039a_multi_query"

# Routes that should skip multi-query expansion
# NOTE: theoretical_definition was removed (ADR-022) because queries like
# "Parlami della rottamazione quinquies" need document_references extraction
SKIP_EXPANSION_ROUTES = {"chitchat"}

# DEV-245: Threshold for short query expansion
# Queries with fewer words than this will be expanded with conversation context
SHORT_QUERY_THRESHOLD = 5

# DEV-245: Italian stop words to filter out when extracting topics
ITALIAN_STOP_WORDS = {
    "il",
    "la",
    "lo",
    "i",
    "gli",
    "le",
    "un",
    "una",
    "uno",
    "di",
    "a",
    "da",
    "in",
    "con",
    "su",
    "per",
    "tra",
    "fra",
    "e",
    "ed",
    "o",
    "ma",
    "che",
    "chi",
    "cui",
    "non",
    "più",
    "come",
    "dove",
    "quando",
    "perché",
    "se",
    "anche",
    "solo",
    "sempre",
    "mai",
    "già",
    "ancora",
    "proprio",
    "questo",
    "quello",
    "cosa",
    "fatto",
    "essere",
    "avere",
    "fare",
    "dire",
    "vedere",
    "sapere",
    "potere",
    "volere",
    "dovere",
    "andare",
    "stare",
    "venire",
    "dare",
    "bene",
    "male",
    "molto",
    "poco",
    "tanto",
    "tutto",
    "niente",
    "nulla",
    "qualcosa",
}


def _expand_short_query(query: str, messages: list[dict] | None) -> str:
    """DEV-245: Expand short queries using conversation context.

    When a user asks a short follow-up question like "e l'IRAP?", we need to
    prepend the conversation topic to make retrieval effective.

    Example:
        - Previous messages: discussion about "rottamazione quinquies"
        - Short query: "e l'irap"
        - Expanded: "rottamazione quinquies IRAP imposta regionale"

    Args:
        query: The user's query (potentially short)
        messages: Conversation history from state["messages"]

    Returns:
        The original query if >= 5 words, or expanded query with context
    """
    # Count words in query
    words = query.strip().split()
    word_count = len(words)

    # If query is long enough, no expansion needed
    if word_count >= SHORT_QUERY_THRESHOLD:
        return query

    # No messages, can't expand
    if not messages:
        logger.info(
            "short_query_no_expansion",
            reason="no_conversation_history",
            word_count=word_count,
        )
        return query

    # Extract topics from recent conversation history (last 4 messages = 2 exchanges)
    topics: list[str] = []
    recent_messages = messages[-4:] if len(messages) > 4 else messages

    for msg in recent_messages:
        content = ""
        role = ""

        # Handle both dict and LangChain message objects
        if isinstance(msg, dict):
            content = msg.get("content", "")
            role = msg.get("role", "")
        else:
            content = getattr(msg, "content", "") or ""
            role = getattr(msg, "type", "") or getattr(msg, "role", "")

        # Focus on user messages for topic extraction
        if role in ("user", "human"):
            # Extract meaningful words (3+ chars, not stop words)
            msg_words = re.findall(r"\b\w{3,}\b", content.lower())
            for word in msg_words:
                if word not in ITALIAN_STOP_WORDS and word not in topics:
                    topics.append(word)

    # Limit to top 5 most recent topics
    topics = topics[:5]

    if not topics:
        logger.info(
            "short_query_no_expansion",
            reason="no_topics_found",
            word_count=word_count,
        )
        return query

    # Build expanded query: topics + original query
    expanded = f"{' '.join(topics)} {query}"

    logger.info(
        "short_query_expanded",
        original_query=query,
        word_count=word_count,
        topics_added=topics,
        expanded_query=expanded[:100],
    )

    return expanded


def _variants_to_dict(variants: Any) -> dict[str, Any]:
    """Convert QueryVariants to a serializable dict for state storage."""
    return {
        "bm25_query": variants.bm25_query,
        "vector_query": variants.vector_query,
        "entity_query": variants.entity_query,
        "original_query": variants.original_query,
        "document_references": variants.document_references,  # ADR-022
        "semantic_expansions": variants.semantic_expansions,  # DEV-242
        "skipped": False,
        "fallback": False,
    }


def _create_skip_result(query: str, reason: str) -> dict[str, Any]:
    """Create a skip result when expansion is not needed."""
    return {
        "bm25_query": query,
        "vector_query": query,
        "entity_query": query,
        "original_query": query,
        "document_references": None,
        "semantic_expansions": None,  # DEV-242
        "skipped": True,
        "skip_reason": reason,
        "fallback": False,
    }


def _create_fallback_result(query: str) -> dict[str, Any]:
    """Create a fallback result using original query for all variants."""
    return {
        "bm25_query": query,
        "vector_query": query,
        "entity_query": query,
        "original_query": query,
        "document_references": None,
        "semantic_expansions": None,  # DEV-242
        "skipped": False,
        "fallback": True,
    }


async def node_step_39a(state: RAGState) -> RAGState:
    """Multi-Query Expansion node for generating query variants.

    This node integrates MultiQueryGeneratorService to create optimized
    query variants for different search types (BM25, vector, entity).

    DEV-245: Now includes short query expansion using conversation context.
    Queries with <5 words are expanded with topics from recent messages.

    Args:
        state: Current RAG state containing user_query and routing_decision

    Returns:
        Updated state with query_variants dict
    """
    user_query = state.get("user_query", "")
    routing_decision = state.get("routing_decision", {})
    route = routing_decision.get("route", "technical_research")
    messages = state.get("messages", [])  # DEV-245: Get conversation history

    # DEV-245: Expand short queries using conversation context
    # This helps queries like "e l'IRAP?" get proper retrieval context
    expanded_query = _expand_short_query(user_query, messages)
    query_was_expanded = expanded_query != user_query

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.enter",
        query_length=len(user_query) if user_query else 0,
        route=route,
        query_expanded=query_was_expanded,  # DEV-245
    )

    with rag_step_timer(STEP_NUM, STEP_ID, NODE_LABEL):
        # Check if we should skip expansion
        if route in SKIP_EXPANSION_ROUTES:
            logger.info(f"Step {NODE_LABEL}: Skipping expansion for route {route}")
            query_variants = _create_skip_result(user_query, route)
        else:
            try:
                # Lazy imports to avoid database connection during module load
                from app.core.llm.model_config import get_model_config
                from app.services.multi_query_generator import MultiQueryGeneratorService

                # Extract entities from routing decision
                entities_data = routing_decision.get("entities", [])
                entities = [
                    ExtractedEntity(
                        text=e.get("text", ""),
                        type=e.get("type", ""),
                        confidence=e.get("confidence", 0.0),
                    )
                    for e in entities_data
                ]

                # Initialize service and generate variants
                # DEV-245: Use expanded query for better retrieval on short queries
                config = get_model_config()
                service = MultiQueryGeneratorService(config=config)
                variants = await service.generate(query=expanded_query, entities=entities)

                query_variants = _variants_to_dict(variants)

                semantic_exp_count = len(query_variants.get("semantic_expansions") or [])
                logger.info(
                    f"Step {NODE_LABEL}: Generated variants - "
                    f"bm25={len(query_variants['bm25_query'])} chars, "
                    f"vector={len(query_variants['vector_query'])} chars, "
                    f"semantic_expansions={semantic_exp_count}"
                )

            except Exception as e:
                logger.warning(f"Step {NODE_LABEL}: Multi-query error, using fallback: {e}")
                query_variants = _create_fallback_result(user_query)

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.exit",
        skipped=query_variants.get("skipped", False),
        fallback=query_variants.get("fallback", False),
        semantic_expansions_count=len(query_variants.get("semantic_expansions") or []),
    )

    return {
        **state,
        "query_variants": query_variants,
    }
