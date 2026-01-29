"""Node wrapper for Step 39c: Parallel Retrieval. DEV-250: Thin wrapper using retrieval_result_builders."""

import logging
from typing import TYPE_CHECKING

from app.core.config import CONTEXT_TOP_K
from app.core.langgraph.types import RAGState
from app.core.logging import logger as structlog_logger
from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.services.retrieval_result_builders import (
    create_retrieval_error_result,
    create_retrieval_skip_result,
    retrieval_result_to_dict,
)

if TYPE_CHECKING:
    from app.services.parallel_retrieval import ParallelRetrievalService

logger = logging.getLogger(__name__)

STEP_NUM = 39
STEP_ID = "RAG.retrieval.parallel"
NODE_LABEL = "step_039c_parallel_retrieval"


async def node_step_39c(state: RAGState) -> RAGState:
    """Parallel Retrieval node for hybrid document search.

    Executes BM25, vector, and HyDE searches in parallel with RRF fusion.
    """
    routing_decision = state.get("routing_decision", {})
    needs_retrieval = routing_decision.get("needs_retrieval", True)
    user_query = state.get("user_query", "")

    rag_step_log(STEP_NUM, STEP_ID, f"{NODE_LABEL}.enter", needs_retrieval=needs_retrieval)

    with rag_step_timer(STEP_NUM, STEP_ID, NODE_LABEL):
        if not needs_retrieval:
            logger.info(f"Step {NODE_LABEL}: Skipping retrieval - not needed")
            retrieval_result = create_retrieval_skip_result("no_retrieval_needed")
        else:
            try:
                from app.models.database import AsyncSessionLocal
                from app.services.hyde_generator import HyDEResult
                from app.services.multi_query_generator import QueryVariants
                from app.services.parallel_retrieval import ParallelRetrievalService
                from app.services.search_service import SearchService

                query_variants_dict = state.get("query_variants", {})
                if query_variants_dict.get("skipped"):
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
                        document_references=query_variants_dict.get("document_references"),
                        semantic_expansions=query_variants_dict.get("semantic_expansions"),
                    )

                hyde_dict = state.get("hyde_result", {})
                hyde_result = HyDEResult(
                    hypothetical_document=hyde_dict.get("hypothetical_document", ""),
                    word_count=hyde_dict.get("word_count", 0),
                    skipped=hyde_dict.get("skipped", True),
                    skip_reason=hyde_dict.get("skip_reason"),
                )

                async with AsyncSessionLocal() as db_session:
                    search_service = SearchService(db_session=db_session)
                    service = ParallelRetrievalService(search_service=search_service, embedding_service=None)

                    messages = state.get("messages", [])
                    topic_keywords = state.get("topic_keywords")

                    structlog_logger.info(
                        "DEV245_step039c_topic_keywords",
                        topic_keywords=topic_keywords,
                        will_be_passed_to_brave=topic_keywords is not None,
                        user_query_preview=user_query[:50] if user_query else "N/A",
                    )

                    result = await service.retrieve(
                        queries=query_variants,
                        hyde=hyde_result,
                        top_k=CONTEXT_TOP_K,
                        messages=messages,
                        topic_keywords=topic_keywords,
                    )
                    retrieval_result = retrieval_result_to_dict(result)

                    logger.info(
                        f"Step {NODE_LABEL}: Retrieved {len(retrieval_result['documents'])} docs "
                        f"from {retrieval_result['total_found']} total in {retrieval_result['search_time_ms']:.1f}ms"
                    )

                    chunk_ids = [
                        doc.get("metadata", {}).get("chunk_id") for doc in retrieval_result.get("documents", [])
                    ]
                    logger.info(f"Step {NODE_LABEL}: Chunk IDs retrieved: {chunk_ids}")

            except Exception as e:
                logger.warning(f"Step {NODE_LABEL}: Retrieval error: {e}")
                retrieval_result = create_retrieval_error_result()

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.exit",
        doc_count=len(retrieval_result.get("documents", [])),
        total_found=retrieval_result.get("total_found", 0),
        skipped=retrieval_result.get("skipped", False),
    )

    search_keywords = retrieval_result.get("search_keywords")
    search_keywords_with_scores = retrieval_result.get("search_keywords_with_scores")

    return {
        **state,
        "retrieval_result": retrieval_result,
        "search_keywords": search_keywords,
        "search_keywords_with_scores": search_keywords_with_scores,
    }
