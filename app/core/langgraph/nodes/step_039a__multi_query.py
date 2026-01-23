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

# DEV-245: Threshold for short query reformulation
# Queries with fewer words than this will be reformulated using LLM
SHORT_QUERY_THRESHOLD = 5


async def _reformulate_short_query_llm(query: str, messages: list[dict] | None) -> str:
    """DEV-245: Use LLM to reformulate short follow-up queries into complete questions.

    Industry-standard approach used by Google, Perplexity, and ChatGPT.
    Semantic reformulation is more effective than keyword prepending.

    Example:
        - Previous response: discussion about "rottamazione quinquies"
        - Short query: "e l'irap?"
        - Reformulated: "L'IRAP può essere inclusa nella rottamazione quinquies?"

    Args:
        query: The user's query (potentially short/incomplete)
        messages: Conversation history from state["messages"]

    Returns:
        The reformulated query if short, or original query if >= 5 words
    """
    words = query.strip().split()
    word_count = len(words)

    # If query is long enough, no reformulation needed
    if word_count >= SHORT_QUERY_THRESHOLD:
        return query

    # No messages, can't reformulate
    if not messages:
        logger.info(f"short_query_no_reformulation: reason=no_conversation_history, word_count={word_count}")
        return query

    # Get last assistant message as context (more relevant than user messages)
    last_assistant_content: str | None = None
    for msg in reversed(messages):
        if isinstance(msg, dict):
            role = msg.get("role", "")
            if role in ("assistant", "ai"):
                last_assistant_content = (msg.get("content") or "")[:500]
                break
        else:
            msg_type = getattr(msg, "type", "") or getattr(msg, "role", "")
            if msg_type in ("assistant", "ai"):
                last_assistant_content = (getattr(msg, "content", "") or "")[:500]
                break

    if not last_assistant_content:
        logger.info(f"short_query_no_reformulation: reason=no_assistant_context, word_count={word_count}")
        return query

    # Build reformulation prompt
    prompt = f"""Reformula questa domanda breve in una domanda completa e autonoma.

Contesto della risposta precedente:
{last_assistant_content}

Domanda breve dell'utente: "{query}"

REGOLE:
- Rispondi SOLO con la domanda riformulata
- Nessuna spiegazione o preambolo
- La domanda deve essere comprensibile senza contesto

Esempio: "e l'imu?" dopo discussione su rottamazione → "L'IMU può essere inclusa nella rottamazione quinquies?"
"""

    try:
        from openai import AsyncOpenAI

        from app.core.llm.model_config import ModelTier, get_model_config

        config = get_model_config()  # Get singleton (no args)
        model = config.get_model(ModelTier.BASIC)  # gpt-4o-mini for fast reformulation
        client = AsyncOpenAI()

        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100,
        )

        reformulated = (response.choices[0].message.content or "").strip()

        # Clean up common LLM artifacts
        reformulated = reformulated.strip('"').strip("'")

        # Validate we got something meaningful
        if not reformulated or len(reformulated) < 5:
            logger.warning(f"short_query_reformulation_invalid: original={query!r}, result={reformulated!r}")
            return query

        logger.info(f"short_query_reformulated_llm: original={query!r}, reformulated={reformulated!r}")

        return reformulated

    except Exception as e:
        logger.warning(f"short_query_reformulation_failed: error={e}, query={query!r}")
        return query  # Fallback to original


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

    # DEV-245: Reformulate short follow-up queries into complete questions
    # Uses LLM (gpt-4o-mini) for semantic reformulation, ~100ms latency
    # e.g., "e l'irap?" → "L'IRAP può essere inclusa nella rottamazione quinquies?"
    expanded_query = await _reformulate_short_query_llm(user_query, messages)
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
                # DEV-245 Phase 3.3: Use expanded_query (reformulated) instead of user_query
                # This preserves conversation context even when multi-query generation fails
                query_variants = _create_fallback_result(expanded_query)

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
