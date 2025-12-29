"""Step 39b: HyDE Generation Node (DEV-195).

LangGraph node wrapper that integrates HyDEGeneratorService for
hypothetical document generation to improve vector search retrieval.

The node:
1. Checks routing_decision to determine if HyDE is needed
2. Skips for CHITCHAT and CALCULATOR routes (handled by service)
3. Calls HyDEGeneratorService.generate() for hypothetical document
4. Stores serialized HyDEResult in state["hyde_result"]
5. Returns skipped result on any error

Usage in graph:
    graph.add_node("step_39b_hyde", node_step_39b)
"""

import logging
from typing import TYPE_CHECKING, Any

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.schemas.router import RoutingCategory

# Lazy import to avoid database connection during module load
if TYPE_CHECKING:
    from app.services.hyde_generator import HyDEGeneratorService

logger = logging.getLogger(__name__)

STEP_NUM = 39
STEP_ID = "RAG.query.hyde"
NODE_LABEL = "step_039b_hyde"


def _hyde_result_to_dict(result: Any) -> dict[str, Any]:
    """Convert HyDEResult to a serializable dict for state storage."""
    return {
        "hypothetical_document": result.hypothetical_document,
        "word_count": result.word_count,
        "skipped": result.skipped,
        "skip_reason": result.skip_reason,
    }


def _create_error_result() -> dict[str, Any]:
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
        "golden_set": RoutingCategory.GOLDEN_SET,
    }
    return route_map.get(route, RoutingCategory.TECHNICAL_RESEARCH)


async def node_step_39b(state: RAGState) -> RAGState:
    """HyDE Generation node for creating hypothetical documents.

    This node integrates HyDEGeneratorService to generate a hypothetical
    document in Italian bureaucratic style for improved vector search.

    Args:
        state: Current RAG state containing user_query and routing_decision

    Returns:
        Updated state with hyde_result dict
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
        try:
            # Lazy imports to avoid database connection during module load
            from app.core.llm.model_config import get_model_config
            from app.services.hyde_generator import HyDEGeneratorService

            # Convert route string to RoutingCategory
            routing_category = _route_to_category(route)

            # Initialize service and generate
            config = get_model_config()
            service = HyDEGeneratorService(config=config)
            result = await service.generate(
                query=user_query,
                routing=routing_category,
            )

            hyde_result = _hyde_result_to_dict(result)

            if hyde_result["skipped"]:
                logger.info(f"Step {NODE_LABEL}: HyDE skipped - {hyde_result['skip_reason']}")
            else:
                logger.info(f"Step {NODE_LABEL}: Generated HyDE document - " f"{hyde_result['word_count']} words")

        except Exception as e:
            logger.warning(f"Step {NODE_LABEL}: HyDE error, skipping: {e}")
            hyde_result = _create_error_result()

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.exit",
        skipped=hyde_result.get("skipped", False),
        word_count=hyde_result.get("word_count", 0),
    )

    return {
        **state,
        "hyde_result": hyde_result,
    }
