"""Step 39ab: Parallel Query Expansion (MultiQuery + HyDE).

Performance optimization: runs MultiQuery and HyDE generation concurrently
instead of sequentially. Both steps are independent LLM calls that only
depend on user_query and routing_decision from state.

Saves ~4-5s per request by overlapping two LLM API calls.
"""

import asyncio
import logging
from typing import Any

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.schemas.router import ExtractedEntity, RoutingCategory
from app.services.query_reformulation import (
    SKIP_EXPANSION_ROUTES,
    create_fallback_result,
    create_skip_result,
    reformulate_short_query_llm,
    variants_to_dict,
)

logger = logging.getLogger(__name__)

STEP_NUM = 39
STEP_ID = "RAG.query.parallel_expansion"
NODE_LABEL = "step_039ab_parallel_expansion"


def _hyde_result_to_dict(result: Any) -> dict[str, Any]:
    """Convert HyDEResult to a serializable dict for state storage."""
    return {
        "hypothetical_document": result.hypothetical_document,
        "word_count": result.word_count,
        "skipped": result.skipped,
        "skip_reason": result.skip_reason,
    }


def _create_hyde_error_result() -> dict[str, Any]:
    """Create an error result when HyDE generation fails."""
    return {
        "hypothetical_document": "",
        "word_count": 0,
        "skipped": True,
        "skip_reason": "error",
    }


def _route_to_category(route: str) -> RoutingCategory:
    """Convert route string to RoutingCategory enum."""
    route_map = {
        "chitchat": RoutingCategory.CHITCHAT,
        "calculator": RoutingCategory.CALCULATOR,
        "theoretical_definition": RoutingCategory.THEORETICAL_DEFINITION,
        "technical_research": RoutingCategory.TECHNICAL_RESEARCH,
        "normative_reference": RoutingCategory.NORMATIVE_REFERENCE,
        "golden_set": RoutingCategory.NORMATIVE_REFERENCE,
    }
    return route_map.get(route, RoutingCategory.TECHNICAL_RESEARCH)


async def _run_multi_query(
    user_query: str,
    route: str,
    routing_decision: dict,
    messages: list,
) -> dict[str, Any]:
    """Run multi-query expansion (extracted from node_step_39a logic)."""
    if route in SKIP_EXPANSION_ROUTES:
        return create_skip_result(user_query, route)

    expanded_query = await reformulate_short_query_llm(user_query, messages)

    try:
        from app.core.llm.model_config import get_model_config
        from app.services.multi_query_generator import MultiQueryGeneratorService

        entities_data = routing_decision.get("entities", [])
        entities = [
            ExtractedEntity(
                text=e.get("text", ""),
                type=e.get("type", ""),
                confidence=e.get("confidence", 0.0),
            )
            for e in entities_data
        ]

        config = get_model_config()
        service = MultiQueryGeneratorService(config=config)
        variants = await service.generate(query=expanded_query, entities=entities)
        return variants_to_dict(variants)

    except Exception as e:
        logger.warning(f"Step {NODE_LABEL}: Multi-query error, using fallback: {e}")
        return create_fallback_result(expanded_query)


async def _run_hyde(user_query: str, route: str) -> dict[str, Any]:
    """Run HyDE generation (extracted from node_step_39b logic)."""
    try:
        from app.core.llm.model_config import get_model_config
        from app.services.hyde_generator import HyDEGeneratorService

        routing_category = _route_to_category(route)
        config = get_model_config()
        service = HyDEGeneratorService(config=config)
        result = await service.generate(query=user_query, routing=routing_category)
        return _hyde_result_to_dict(result)

    except Exception as e:
        logger.warning(f"Step {NODE_LABEL}: HyDE error, skipping: {e}")
        return _create_hyde_error_result()


async def node_step_39ab(state: RAGState) -> RAGState:
    """Parallel Query Expansion: runs MultiQuery and HyDE concurrently.

    Both MultiQuery and HyDE are independent LLM calls that only depend
    on user_query and routing_decision. Running them in parallel saves
    ~4-5s per request.
    """
    user_query = state.get("user_query", "")
    routing_decision = state.get("routing_decision", {})
    route = routing_decision.get("route", "technical_research")
    messages = state.get("messages", [])

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.enter",
        query_length=len(user_query) if user_query else 0,
        route=route,
    )

    with rag_step_timer(STEP_NUM, STEP_ID, NODE_LABEL):
        # Run both LLM calls in parallel
        query_variants, hyde_result = await asyncio.gather(
            _run_multi_query(user_query, route, routing_decision, messages),
            _run_hyde(user_query, route),
        )

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.exit",
        multi_query_skipped=query_variants.get("skipped", False),
        hyde_skipped=hyde_result.get("skipped", False),
        hyde_word_count=hyde_result.get("word_count", 0),
    )

    return {**state, "query_variants": query_variants, "hyde_result": hyde_result}
