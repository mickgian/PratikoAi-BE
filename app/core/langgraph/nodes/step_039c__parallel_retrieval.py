"""Step 39c: Parallel Retrieval Node (DEV-195).

LangGraph node wrapper that integrates ParallelRetrievalService for
hybrid search with RRF fusion and source authority ranking.

The node:
1. Checks routing_decision.needs_retrieval
2. Skips if retrieval is not needed (CHITCHAT, CALCULATOR)
3. Reconstructs QueryVariants and HyDEResult from state
4. Calls ParallelRetrievalService.retrieve() for document search
5. Stores serialized RetrievalResult in state["retrieval_result"]
6. Returns empty result on any error

Usage in graph:
    graph.add_node("step_39c_parallel_retrieval", node_step_39c)
"""

import logging
from typing import TYPE_CHECKING, Any

from app.core.config import CONTEXT_TOP_K
from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log, rag_step_timer

# Lazy import to avoid database connection during module load
if TYPE_CHECKING:
    from app.services.parallel_retrieval import ParallelRetrievalService

logger = logging.getLogger(__name__)

STEP_NUM = 39
STEP_ID = "RAG.retrieval.parallel"
NODE_LABEL = "step_039c_parallel_retrieval"


def _retrieval_result_to_dict(result: Any) -> dict[str, Any]:
    """Convert RetrievalResult to a serializable dict for state storage."""
    documents = []
    for doc in result.documents:
        doc_dict = {
            "document_id": doc.document_id,
            "content": doc.content,
            "score": doc.score,
            "rrf_score": doc.rrf_score,
            "source_type": doc.source_type,
            "source_name": doc.source_name,
            "published_date": doc.published_date.isoformat() if doc.published_date else None,
            # DEV-244 FIX: Extract source_url from metadata for kb_sources_metadata
            # Without this, the Fonti dropdown won't have URLs and won't display
            "source_url": doc.metadata.get("source_url"),
            "metadata": doc.metadata,
        }
        documents.append(doc_dict)

    return {
        "documents": documents,
        "total_found": result.total_found,
        "search_time_ms": result.search_time_ms,
        "search_keywords": result.search_keywords,  # DEV-245 Phase 4.2.1
        "search_keywords_with_scores": result.search_keywords_with_scores,  # DEV-245 Phase 5.12
        "skipped": False,
        "error": False,
    }


def _create_skip_result(reason: str) -> dict[str, Any]:
    """Create a skip result when retrieval is not needed."""
    return {
        "documents": [],
        "total_found": 0,
        "search_time_ms": 0.0,
        "skipped": True,
        "skip_reason": reason,
        "error": False,
    }


def _create_error_result() -> dict[str, Any]:
    """Create an error result when retrieval fails."""
    return {
        "documents": [],
        "total_found": 0,
        "search_time_ms": 0.0,
        "skipped": False,
        "error": True,
    }


async def node_step_39c(state: RAGState) -> RAGState:
    """Parallel Retrieval node for hybrid document search.

    This node integrates ParallelRetrievalService to execute BM25,
    vector, and HyDE searches in parallel with RRF fusion.

    Args:
        state: Current RAG state with query_variants and hyde_result

    Returns:
        Updated state with retrieval_result dict
    """
    routing_decision = state.get("routing_decision", {})
    needs_retrieval = routing_decision.get("needs_retrieval", True)
    user_query = state.get("user_query", "")

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.enter",
        needs_retrieval=needs_retrieval,
    )

    with rag_step_timer(STEP_NUM, STEP_ID, NODE_LABEL):
        # Check if retrieval is needed
        if not needs_retrieval:
            logger.info(f"Step {NODE_LABEL}: Skipping retrieval - not needed")
            retrieval_result = _create_skip_result("no_retrieval_needed")
        else:
            try:
                # Lazy imports
                from app.models.database import AsyncSessionLocal
                from app.services.hyde_generator import HyDEResult
                from app.services.multi_query_generator import QueryVariants
                from app.services.parallel_retrieval import ParallelRetrievalService
                from app.services.search_service import SearchService

                # Reconstruct QueryVariants from state
                query_variants_dict = state.get("query_variants", {})
                if query_variants_dict.get("skipped"):
                    # Use original query for all if skipped
                    query_variants = QueryVariants(
                        bm25_query=user_query,
                        vector_query=user_query,
                        entity_query=user_query,
                        original_query=user_query,
                    )
                else:
                    query_variants = QueryVariants(
                        bm25_query=query_variants_dict.get("bm25_query", user_query),
                        vector_query=query_variants_dict.get("vector_query", user_query),
                        entity_query=query_variants_dict.get("entity_query", user_query),
                        original_query=query_variants_dict.get("original_query", user_query),
                        document_references=query_variants_dict.get("document_references"),  # ADR-022
                        semantic_expansions=query_variants_dict.get("semantic_expansions"),  # DEV-242 Phase 24
                    )

                # Reconstruct HyDEResult from state
                hyde_dict = state.get("hyde_result", {})
                hyde_result = HyDEResult(
                    hypothetical_document=hyde_dict.get("hypothetical_document", ""),
                    word_count=hyde_dict.get("word_count", 0),
                    skipped=hyde_dict.get("skipped", True),
                    skip_reason=hyde_dict.get("skip_reason"),
                )

                # DEV-242: Initialize service with REAL SearchService for BM25 search
                # Create async session for database access
                async with AsyncSessionLocal() as db_session:
                    search_service = SearchService(db_session=db_session)

                    service = ParallelRetrievalService(
                        search_service=search_service,
                        embedding_service=None,  # Vector search still uses placeholder
                    )
                    # DEV-245 Phase 3.9: Pass messages for context-aware keyword ordering
                    # in Brave web search (context keywords first, then new keywords)
                    messages = state.get("messages", [])
                    # DEV-245 Phase 5.3: Pass topic_keywords for long conversation support
                    # These keywords persist across all turns, preventing context loss at Q4+
                    topic_keywords = state.get("topic_keywords")

                    # DEV-245 Phase 5.10: Debug log at step_039c before Brave search
                    # Use structlog for debug logging (supports kwargs)
                    from app.core.logging import logger as structlog_logger

                    structlog_logger.info(
                        "DEV245_step039c_topic_keywords",
                        topic_keywords=topic_keywords,
                        will_be_passed_to_brave=topic_keywords is not None,
                        user_query_preview=user_query[:50] if user_query else "N/A",
                    )

                    result = await service.retrieve(
                        queries=query_variants,
                        hyde=hyde_result,
                        top_k=CONTEXT_TOP_K,  # DEV-242 Phase 26: Use config value (20) instead of default (10)
                        messages=messages,
                        topic_keywords=topic_keywords,
                    )

                    retrieval_result = _retrieval_result_to_dict(result)

                    logger.info(
                        f"Step {NODE_LABEL}: Retrieved {len(retrieval_result['documents'])} docs "
                        f"from {retrieval_result['total_found']} total in "
                        f"{retrieval_result['search_time_ms']:.1f}ms"
                    )

                    # DEV-242 Phase 25: Log chunk IDs to debug which chunks are in TOP-K
                    chunk_ids = [
                        doc.get("metadata", {}).get("chunk_id") for doc in retrieval_result.get("documents", [])
                    ]
                    logger.info(f"Step {NODE_LABEL}: Chunk IDs retrieved: {chunk_ids}")

            except Exception as e:
                logger.warning(f"Step {NODE_LABEL}: Retrieval error: {e}")
                retrieval_result = _create_error_result()

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.exit",
        doc_count=len(retrieval_result.get("documents", [])),
        total_found=retrieval_result.get("total_found", 0),
        skipped=retrieval_result.get("skipped", False),
    )

    # DEV-245 Phase 4.2.1: Store search keywords in state for downstream filtering
    # This ensures Step 040 uses the SAME keywords as Brave search for web filtering
    search_keywords = retrieval_result.get("search_keywords")
    # DEV-245 Phase 5.12: Store keyword scores for evaluation
    search_keywords_with_scores = retrieval_result.get("search_keywords_with_scores")

    return {
        **state,
        "retrieval_result": retrieval_result,
        "search_keywords": search_keywords,  # DEV-245 Phase 4.2.1
        "search_keywords_with_scores": search_keywords_with_scores,  # DEV-245 Phase 5.12
    }
