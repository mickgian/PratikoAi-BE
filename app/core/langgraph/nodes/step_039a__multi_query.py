"""Step 39a: Multi-Query Expansion Node (DEV-195).

LangGraph node wrapper that integrates MultiQueryGeneratorService for
query expansion. Generates BM25, vector, and entity-focused query variants.

The node:
1. Checks routing_decision to determine if expansion is needed
2. Skips for CHITCHAT and THEORETICAL_DEFINITION routes
3. Calls MultiQueryGeneratorService.generate() for variants
4. Stores serialized QueryVariants in state["query_variants"]
5. Falls back to original query on any error

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
SKIP_EXPANSION_ROUTES = {"chitchat", "theoretical_definition"}


def _variants_to_dict(variants: Any) -> dict[str, Any]:
    """Convert QueryVariants to a serializable dict for state storage."""
    return {
        "bm25_query": variants.bm25_query,
        "vector_query": variants.vector_query,
        "entity_query": variants.entity_query,
        "original_query": variants.original_query,
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
        "skipped": False,
        "fallback": True,
    }


async def node_step_39a(state: RAGState) -> RAGState:
    """Multi-Query Expansion node for generating query variants.

    This node integrates MultiQueryGeneratorService to create optimized
    query variants for different search types (BM25, vector, entity).

    Args:
        state: Current RAG state containing user_query and routing_decision

    Returns:
        Updated state with query_variants dict
    """
    user_query = state.get("user_query", "")
    routing_decision = state.get("routing_decision", {})
    route = routing_decision.get("route", "technical_research")

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.enter",
        query_length=len(user_query) if user_query else 0,
        route=route,
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
                config = get_model_config()
                service = MultiQueryGeneratorService(config=config)
                variants = await service.generate(query=user_query, entities=entities)

                query_variants = _variants_to_dict(variants)

                logger.info(
                    f"Step {NODE_LABEL}: Generated variants - "
                    f"bm25={len(query_variants['bm25_query'])} chars, "
                    f"vector={len(query_variants['vector_query'])} chars"
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
    )

    return {
        **state,
        "query_variants": query_variants,
    }
