"""Node wrapper for Step 39a: Multi-Query Expansion. DEV-250: Thin wrapper using query_reformulation service."""

import logging
from typing import TYPE_CHECKING

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.schemas.router import ExtractedEntity
from app.services.query_reformulation import (
    SKIP_EXPANSION_ROUTES,
    create_fallback_result,
    create_skip_result,
    reformulate_short_query_llm,
    variants_to_dict,
)

if TYPE_CHECKING:
    from app.services.multi_query_generator import MultiQueryGeneratorService

logger = logging.getLogger(__name__)

STEP_NUM = 39
STEP_ID = "RAG.query.multi_query"
NODE_LABEL = "step_039a_multi_query"


async def node_step_39a(state: RAGState) -> RAGState:
    """Multi-Query Expansion node for generating query variants.

    Integrates MultiQueryGeneratorService to create optimized query variants
    for different search types (BM25, vector, entity).

    DEV-245: Includes short query expansion using conversation context.
    """
    user_query = state.get("user_query", "")
    routing_decision = state.get("routing_decision", {})
    route = routing_decision.get("route", "technical_research")
    messages = state.get("messages", [])

    expanded_query = await reformulate_short_query_llm(user_query, messages)
    query_was_expanded = expanded_query != user_query

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.enter",
        query_length=len(user_query) if user_query else 0,
        route=route,
        query_expanded=query_was_expanded,
    )

    with rag_step_timer(STEP_NUM, STEP_ID, NODE_LABEL):
        if route in SKIP_EXPANSION_ROUTES:
            logger.info(f"Step {NODE_LABEL}: Skipping expansion for route {route}")
            query_variants = create_skip_result(user_query, route)
        else:
            try:
                from app.core.llm.model_config import get_model_config
                from app.services.multi_query_generator import MultiQueryGeneratorService

                entities_data = routing_decision.get("entities", [])
                entities = [
                    ExtractedEntity(
                        text=e.get("text", ""), type=e.get("type", ""), confidence=e.get("confidence", 0.0)
                    )
                    for e in entities_data
                ]

                config = get_model_config()
                service = MultiQueryGeneratorService(config=config)
                variants = await service.generate(query=expanded_query, entities=entities)

                query_variants = variants_to_dict(variants)
                semantic_exp_count = len(query_variants.get("semantic_expansions") or [])
                logger.info(
                    f"Step {NODE_LABEL}: Generated variants - bm25={len(query_variants['bm25_query'])} chars, "
                    f"vector={len(query_variants['vector_query'])} chars, semantic_expansions={semantic_exp_count}"
                )

            except Exception as e:
                logger.warning(f"Step {NODE_LABEL}: Multi-query error, using fallback: {e}")
                query_variants = create_fallback_result(expanded_query)

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.exit",
        skipped=query_variants.get("skipped", False),
        fallback=query_variants.get("fallback", False),
        semantic_expansions_count=len(query_variants.get("semantic_expansions") or []),
    )

    return {**state, "query_variants": query_variants}
