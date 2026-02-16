"""Parallel Hybrid Retrieval Service for DEV-190.

Implements parallel search with RRF fusion and source authority per Section 13.7.
Combines BM25, vector, and HyDE search results using Reciprocal Rank Fusion.

Usage:
    from app.services.parallel_retrieval import ParallelRetrievalService

    service = ParallelRetrievalService(
        search_service=search_service,
        embedding_service=embedding_service,
    )
    result = await service.retrieve(query_variants, hyde_result)
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Optional

from app.core.config import HYBRID_K_FTS
from app.core.logging import logger
from app.services.hyde_generator import HyDEResult
from app.services.italian_stop_words import STOP_WORDS
from app.services.multi_query_generator import QueryVariants

# RRF constant (k=60 per Section 13.7.2)
RRF_K = 60

# Search type weights per Section 13.7.2
# DEV-244: Added authority search to ensure official sources are always considered
# DEV-245: Added brave (web search) for Parallel Hybrid RAG
# Note: brave weight is loaded from settings.BRAVE_SEARCH_WEIGHT at runtime
SEARCH_WEIGHTS = {
    "bm25": 0.3,
    "vector": 0.35,
    "hyde": 0.25,
    "authority": 0.2,  # DEV-244: Increased from 0.1 to boost official sources
    "brave": 0.3,  # DEV-245: Default, overridden by BRAVE_SEARCH_WEIGHT env var
}


def _get_search_weights() -> dict[str, float]:
    """Get search weights with runtime-configurable brave weight.

    DEV-245: Allows tuning brave weight via BRAVE_SEARCH_WEIGHT env var.
    """
    from app.core.config import settings

    weights = SEARCH_WEIGHTS.copy()
    weights["brave"] = settings.BRAVE_SEARCH_WEIGHT
    return weights


# Source authority hierarchy per Section 13.7.4
# DEV-242 Phase 17: Increased boosts to prioritize full laws over summaries
GERARCHIA_FONTI = {
    "legge": 1.8,  # Was 1.3 - increased to ensure laws rank above summaries
    "decreto": 1.6,  # Was 1.25
    "normativa": 1.4,  # DEV-250: Official regulatory documents (Regole AdER, etc.)
    "circolare": 1.3,  # Was 1.15
    "risoluzione": 1.2,  # Was 1.1
    "interpello": 1.1,  # Was 1.05
    "faq": 1.0,
    "guida": 0.8,  # Was 0.95 - penalty for summaries
}

# DEV-242 Phase 18: Source-based authority boost
# Gazzetta Ufficiale documents should rank higher than ministry summaries
SOURCE_AUTHORITY = {
    "gazzetta_ufficiale": 1.3,  # Official law source gets 30% boost
    "agenzia_entrate": 1.2,
    "agenzia_entrate_riscossione": 1.2,  # DEV-244: ADeR official source
    "inps": 1.2,
    "corte_cassazione": 1.15,
    "ministero_economia_documenti": 0.9,  # Summaries penalized
    "ministero_lavoro_news": 0.9,
}

# Recency boost threshold (12 months)
RECENCY_THRESHOLD_DAYS = 365
RECENCY_BOOST = 1.5  # +50%

# Default top-K results
DEFAULT_TOP_K = 10

# DEV-244: High-authority sources that get reserved slots in top-K results
# These official sources should never be pushed out by news articles
HIGH_AUTHORITY_SOURCES = {
    "gazzetta_ufficiale",
    "agenzia_entrate",
    "agenzia_entrate_riscossione",
    "inps",
    "corte_cassazione",
}

# Maximum reserved slots for high-authority sources
MAX_RESERVED_SLOTS = 3

# DEV-245 Phase 3.8: Reserve slots for web results to ensure they appear in Fonti
# Web results from Brave search need guaranteed inclusion regardless of RRF score
WEB_RESERVED_SLOTS = 2


def _normalize_document_patterns(refs: list[str] | None) -> list[str]:
    """Normalize document reference patterns for ILIKE matching.

    DEV-242 Phase 9: LLM may generate patterns like "Legge 199/2025" but
    actual Italian law titles use "LEGGE 30 dicembre 2025, n. 199".
    This function expands patterns to improve matching.

    Args:
        refs: List of document references from LLM

    Returns:
        Expanded list of normalized patterns for ILIKE matching

    Example:
        Input: ["Legge 199/2025", "Legge di Bilancio 2026"]
        Output: ["Legge 199/2025", "n. 199", "199", "Legge di Bilancio 2026"]
    """
    if not refs:
        return []

    patterns = []
    for ref in refs:
        # Always include the original pattern
        patterns.append(ref)

        # Extract law number patterns: "Legge 199/2025" → "n. 199", "199"
        if match := re.search(r"(\d+)/(\d+)", ref):
            number = match.group(1)
            # Add "n. XXX" pattern (matches Italian law title format)
            patterns.append(f"n. {number}")
            # Add just the number as fallback
            patterns.append(number)

        # Extract standalone numbers from patterns like "n. 199" or "DL 145"
        if match := re.search(r"n\.\s*(\d+)", ref, re.IGNORECASE):
            number = match.group(1)
            if number not in patterns:
                patterns.append(number)

    # Remove duplicates while preserving order
    seen = set()
    unique_patterns = []
    for p in patterns:
        if p not in seen:
            seen.add(p)
            unique_patterns.append(p)

    return unique_patterns


@dataclass
class RankedDocument:
    """A document with ranking scores and metadata.

    Attributes:
        document_id: Unique identifier for the document
        content: Document text content
        score: Original search score
        rrf_score: Final RRF-computed score
        source_type: Type of source (legge, circolare, faq, etc.)
        source_name: Name of the source document
        published_date: Publication date
        metadata: Additional metadata dictionary
    """

    document_id: str
    content: str
    score: float
    rrf_score: float
    source_type: str
    source_name: str
    published_date: datetime | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Result from parallel retrieval.

    Attributes:
        documents: List of ranked documents
        total_found: Total number of documents found across all searches
        search_time_ms: Total search time in milliseconds
        search_keywords: DEV-245 Phase 4.2.1 - Keywords used for Brave search (for downstream filtering)
        search_keywords_with_scores: DEV-245 Phase 5.12 - Keywords with YAKE scores for evaluation
    """

    documents: list[RankedDocument]
    total_found: int
    search_time_ms: float
    search_keywords: list[str] | None = None  # DEV-245 Phase 4.2.1: For consistent web filtering
    search_keywords_with_scores: list[dict] | None = None  # DEV-245 Phase 5.12: YAKE scores


class ParallelRetrievalService:
    """Service for parallel hybrid retrieval with RRF fusion.

    Executes BM25, vector, and HyDE searches in parallel, then combines
    results using Reciprocal Rank Fusion with source authority and
    recency boosts.

    Example:
        service = ParallelRetrievalService(
            search_service=search_service,
            embedding_service=embedding_service,
        )

        result = await service.retrieve(
            queries=query_variants,
            hyde=hyde_result,
        )
        for doc in result.documents:
            print(f"{doc.source_name}: {doc.rrf_score:.4f}")
    """

    def __init__(
        self,
        search_service: Any,
        embedding_service: Any,
    ):
        """Initialize the parallel retrieval service.

        Args:
            search_service: Service for BM25/text search
            embedding_service: Service for vector embeddings
        """
        self._search_service = search_service
        self._embedding_service = embedding_service

    async def retrieve(
        self,
        queries: QueryVariants,
        hyde: HyDEResult,
        top_k: int = DEFAULT_TOP_K,
        messages: list[dict] | None = None,
        topic_keywords: list[str] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> RetrievalResult:
        """Execute parallel retrieval and fuse results.

        Runs BM25, vector, and HyDE searches in parallel, combines
        using RRF, applies boosts, and returns top-K documents.

        DEV-245 Phase 3.9: Accepts messages for context-aware keyword ordering
        in Brave web search. This ensures follow-up queries use correct
        keyword order (context first, then new keywords).

        DEV-245 Phase 5.3: Accepts topic_keywords for long conversation support.
        When provided, uses these as context keywords instead of extracting from
        messages[-4:], ensuring the main topic is never lost at Q4+.

        Args:
            queries: Query variants from MultiQueryGenerator
            hyde: HyDE result from HyDEGenerator
            top_k: Number of top documents to return
            messages: Conversation history for context-aware keyword ordering
            topic_keywords: Pre-extracted topic keywords from state (Phase 5.3)
            user_id: DEV-257: User ID for Brave API cost tracking
            session_id: DEV-257: Session ID for Brave API cost tracking

        Returns:
            RetrievalResult with ranked documents
        """
        start_time = time.perf_counter()

        # DEV-245 Phase 4.2.1: Extract search keywords upfront for downstream filtering
        # This ensures Step 040 uses the SAME keywords as Brave search for web filtering
        # DEV-245 Phase 5.3: Use topic_keywords from state if provided (for long conversations)
        # DEV-245 Phase 5.12: Also extract scores for evaluation
        search_keywords: list[str] | None = None
        search_keywords_with_scores: list[dict] | None = None
        if queries.original_query:
            search_keywords = self._extract_search_keywords_with_context(
                queries.original_query, messages, topic_keywords
            )
            # DEV-245 Phase 5.12: Extract scores from raw query (before context reordering)
            _, search_keywords_with_scores = self._extract_search_keywords(queries.original_query)
            logger.debug(
                "search_keywords_extracted_for_downstream",
                keywords=search_keywords,
                keywords_with_scores=search_keywords_with_scores,
                query_preview=queries.original_query[:50],
                using_topic_keywords=topic_keywords is not None,
            )

        try:
            # Execute all searches in parallel
            # DEV-245 Phase 3.9: Pass messages for context-aware keyword ordering
            # DEV-245 Phase 5.3: Pass topic_keywords for long conversation support
            # DEV-257: Pass user_id/session_id for Brave cost tracking
            search_results = await self._execute_parallel_searches(
                queries, hyde, messages, topic_keywords, user_id, session_id
            )

            # Combine using RRF
            fused = self._rrf_fusion(search_results)

            # Apply authority and recency boosts
            boosted = self._apply_boosts(fused)

            # Deduplicate by document_id
            deduped = self._deduplicate(boosted)

            # Get top-K results
            top_docs = self._get_top_k(deduped, k=top_k)

            # Convert to RankedDocument objects
            ranked_docs = self._to_ranked_documents(top_docs)

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            total_found = sum(len(r) for r in search_results)

            logger.info(
                "parallel_retrieval_complete",
                total_found=total_found,
                returned=len(ranked_docs),
                search_time_ms=elapsed_ms,
            )

            # DEV-245: Enhanced retrieval logging for debugging hallucinations
            # Log details of retrieved documents so we can compare against cited docs
            if ranked_docs:
                retrieved_doc_details = []
                for doc in ranked_docs:
                    retrieved_doc_details.append(
                        {
                            "id": doc.document_id[:20] if doc.document_id else "?",
                            "source": doc.metadata.get("source", "?")[:30],
                            "title": (doc.source_name or "?")[:50],
                            "score": round(doc.rrf_score, 4),
                            "type": doc.source_type[:20] if doc.source_type else "?",
                        }
                    )

                # Log summary for easy debugging
                sources_retrieved = list({d["source"] for d in retrieved_doc_details})

                # DEV-245: Calculate web result contribution metrics
                web_result_count = sum(
                    1
                    for doc in ranked_docs
                    if doc.metadata.get("is_web_result", False) or doc.metadata.get("source", "").startswith("brave_")
                )
                has_ai_summary = any(doc.metadata.get("is_ai_synthesis", False) for doc in ranked_docs)

                logger.info(
                    "DEV245_retrieval_docs_summary",
                    query=str(queries.original_query)[:100] if hasattr(queries, "original_query") else "?",
                    retrieved_count=len(ranked_docs),
                    sources=sources_retrieved,
                    top_3_titles=[d["title"] for d in retrieved_doc_details[:3]],
                    # DEV-245: Web result contribution metrics
                    web_results_in_final=web_result_count,
                    web_contribution_pct=round(web_result_count / len(ranked_docs) * 100, 1) if ranked_docs else 0,
                    has_brave_ai_summary=has_ai_summary,
                )

                # Log full details at debug level for deep investigation
                logger.debug(
                    "DEV245_retrieval_docs_detail",
                    documents=retrieved_doc_details,
                )

            return RetrievalResult(
                documents=ranked_docs,
                total_found=total_found,
                search_time_ms=elapsed_ms,
                search_keywords=search_keywords,  # DEV-245 Phase 4.2.1
                search_keywords_with_scores=search_keywords_with_scores,  # DEV-245 Phase 5.12
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "parallel_retrieval_error",
                error=str(e),
                search_time_ms=elapsed_ms,
            )
            # Return empty result on error
            return RetrievalResult(
                documents=[],
                total_found=0,
                search_time_ms=elapsed_ms,
                search_keywords=search_keywords,  # DEV-245 Phase 4.2.1: Still pass keywords if extracted
                search_keywords_with_scores=search_keywords_with_scores,  # DEV-245 Phase 5.12
            )

    async def _execute_parallel_searches(
        self,
        queries: QueryVariants,
        hyde: HyDEResult,
        messages: list[dict] | None = None,
        topic_keywords: list[str] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> list[list[dict[str, Any]]]:
        """Execute searches with KB sequential, Brave parallel.

        DEV-245: Now includes Brave web search for Parallel Hybrid RAG.
        This enables single-LLM architecture by moving web search to retrieval phase.

        DEV-244 FIX: KB searches (bm25, vector, hyde, authority) MUST run sequentially
        because they share the same SQLAlchemy AsyncSession which doesn't support
        concurrent operations. Brave search runs in parallel since it uses HTTP only.

        DEV-245 Phase 3.9: Passes messages to Brave search for context-aware keyword ordering.
        DEV-245 Phase 5.3: Passes topic_keywords for long conversation support.
        DEV-257: Passes user_id/session_id for Brave API cost tracking.

        Args:
            queries: Query variants
            hyde: HyDE result
            messages: Conversation history for context-aware keyword ordering
            topic_keywords: Pre-extracted topic keywords from state (Phase 5.3)
            user_id: DEV-257: User ID for Brave API cost tracking
            session_id: DEV-257: Session ID for Brave API cost tracking

        Returns:
            List of search results [bm25, vector, hyde, authority, brave]
        """
        # DEV-245: Log start of search execution for Docker debugging
        logger.info(
            "parallel_searches_starting",
            query_preview=queries.original_query[:80] if queries.original_query else "N/A",
            has_hyde=hyde is not None and hyde.hypothetical_document is not None,
            search_types=["bm25", "vector", "hyde", "authority", "brave"],
        )

        # DEV-244 FIX: Run KB searches SEQUENTIALLY to avoid SQLAlchemy session concurrency error
        # The AsyncSession doesn't support concurrent operations from the same session.
        # Brave search can run in parallel since it only uses HTTP (no DB session).

        # Start Brave search in background (doesn't use DB session)
        # DEV-245 Phase 3.9: Pass messages for context-aware keyword ordering
        # DEV-245 Phase 5.3: Pass topic_keywords for long conversation support
        # DEV-257: Pass user_id/session_id for cost tracking
        brave_task = asyncio.create_task(
            self._search_brave(
                queries, messages=messages, topic_keywords=topic_keywords, user_id=user_id, session_id=session_id
            )
        )

        # Run KB searches sequentially
        source_counts: dict[str, int] = {}
        processed: list[list[dict[str, Any]]] = []

        # 1. BM25 search
        try:
            bm25_results = await self._search_bm25(queries)
            processed.append(bm25_results)
            source_counts["bm25"] = len(bm25_results)
        except Exception as e:
            logger.warning("search_task_failed", search_type="bm25", error=str(e))
            processed.append([])
            source_counts["bm25"] = 0

        # 2. Vector search
        try:
            vector_results = await self._search_vector(queries)
            processed.append(vector_results)
            source_counts["vector"] = len(vector_results)
        except Exception as e:
            logger.warning("search_task_failed", search_type="vector", error=str(e))
            processed.append([])
            source_counts["vector"] = 0

        # 3. HyDE search
        try:
            hyde_results = await self._search_hyde(hyde)
            processed.append(hyde_results)
            source_counts["hyde"] = len(hyde_results)
        except Exception as e:
            logger.warning("search_task_failed", search_type="hyde", error=str(e))
            processed.append([])
            source_counts["hyde"] = 0

        # 4. Authority search (already runs sequentially internally)
        try:
            authority_results = await self._search_authority_sources(queries)
            processed.append(authority_results)
            source_counts["authority"] = len(authority_results)
        except Exception as e:
            logger.warning("search_task_failed", search_type="authority", error=str(e))
            processed.append([])
            source_counts["authority"] = 0

        # 5. Wait for Brave search (was running in parallel)
        try:
            brave_results = await brave_task
            processed.append(brave_results)
            source_counts["brave"] = len(brave_results)
        except Exception as e:
            logger.warning("search_task_failed", search_type="brave", error=str(e))
            processed.append([])
            source_counts["brave"] = 0

        # DEV-245: Log source distribution for Docker debugging
        logger.info(
            "parallel_searches_complete",
            source_counts=source_counts,
            total_raw_results=sum(source_counts.values()),
            brave_results=source_counts.get("brave", 0),
            kb_results=source_counts.get("bm25", 0) + source_counts.get("vector", 0) + source_counts.get("hyde", 0),
        )

        return processed

    async def _search_bm25(
        self,
        queries: QueryVariants,
    ) -> list[dict[str, Any]]:
        """Execute BM25 searches for all query variants.

        ADR-022: Uses document_references from LLM to filter search by title.
        DEV-242: Uses semantic_expansions to bridge terminology gaps.
        Falls back to regular search if filtered search returns no results.

        Args:
            queries: Query variants (may include document_references and semantic_expansions)

        Returns:
            List of BM25 search results
        """
        if not self._search_service:
            logger.warning("bm25_search_skipped", reason="no_search_service")
            return []

        try:
            # DEV-242: Use bm25_query from query variants for BM25 search
            search_query = queries.bm25_query or queries.original_query

            # DEV-242 Phase 16: Expand query with semantic_expansions to bridge terminology gaps
            # E.g., "rottamazione quinquies" → "rottamazione quinquies pace fiscale pacificazione definizione"
            # This helps FTS find documents using official legal terminology
            if queries.semantic_expansions:
                # Append semantic expansions to the query for better FTS matching
                semantic_terms = " ".join(queries.semantic_expansions)
                search_query = f"{search_query} {semantic_terms}"
                logger.info(
                    "bm25_semantic_expansion",
                    original_query=queries.original_query[:100] if queries.original_query else "",
                    expanded_query=search_query[:200] if search_query else "",
                    semantic_expansions=queries.semantic_expansions,
                )

            logger.info(
                "bm25_search_executing",
                query=search_query[:100] if search_query else "EMPTY",
                original_query=queries.original_query[:100] if queries.original_query else "",
                has_document_refs=bool(queries.document_references),
                has_semantic_expansions=bool(queries.semantic_expansions),
            )

            results = []

            # ADR-022: If LLM identified specific documents, search within those first
            if queries.document_references:
                # DEV-242 Phase 9: Normalize patterns for better ILIKE matching
                # E.g., "Legge 199/2025" → ["Legge 199/2025", "n. 199", "199"]
                normalized_patterns = _normalize_document_patterns(queries.document_references)

                logger.info(
                    "bm25_search_with_document_filter",
                    document_references=queries.document_references,
                    normalized_patterns=normalized_patterns,
                )

                # Priority search: filter to identified documents
                # DEV-242 Phase 30: Use HYBRID_K_FTS config instead of hardcoded 20
                results = await self._search_service.search(
                    query=search_query,
                    limit=HYBRID_K_FTS,
                    title_patterns=normalized_patterns,
                )

                if results:
                    logger.info(
                        "bm25_document_filter_success",
                        count=len(results),
                        document_references=queries.document_references,
                    )
                else:
                    # Fallback: document filter found no results
                    logger.info(
                        "bm25_document_filter_fallback",
                        reason="no_results",
                        document_references=queries.document_references,
                    )
                    # Fall through to regular search

            # Regular search (no filter, or fallback from empty filter results)
            # DEV-242 Phase 30: Use HYBRID_K_FTS config instead of hardcoded 20
            if not results:
                results = await self._search_service.search(
                    query=search_query,
                    limit=HYBRID_K_FTS,
                )

            # DEV-244 FIX: If strict AND search returns 0 results, try OR fallback
            # websearch_to_tsquery requires ALL terms to match, which is too strict
            # for long queries with semantic expansions. plainto_tsquery uses OR logic.
            if not results:
                logger.info(
                    "bm25_and_search_zero_results_trying_or_fallback",
                    query=search_query[:100] if search_query else "",
                )
                results = await self._search_service.search_with_or_fallback(
                    query=search_query,
                    limit=HYBRID_K_FTS,
                )

            # Convert SearchResult objects to dicts
            docs: list[dict[str, Any]] = []
            for result in results:
                doc = {
                    # DEV-242 Phase 27: Use chunk ID for deduplication to keep multiple chunks per document
                    # Before: knowledge_item_id caused all chunks from same doc to dedupe to one
                    "document_id": str(result.id),
                    "content": result.content or "",
                    "score": result.rank_score,
                    "source_type": result.category or "",
                    "source": result.source or "",  # DEV-242 Phase 22: Add for SOURCE_AUTHORITY matching
                    # DEV-242: Use title first (e.g., "LEGGE 30 dicembre 2025, n. 199")
                    # then fall back to source (e.g., "gazzetta_ufficiale_reingest")
                    "source_name": result.title or result.source or "",
                    "published_date": result.publication_date,
                    # DEV-242 Phase 42: Add source_url for citation links
                    "source_url": result.source_url,
                    "metadata": {
                        "title": result.title,
                        "source": result.source,
                        "category": result.category,
                        "chunk_id": result.id,
                        "source_url": result.source_url,  # Also in metadata for context builder
                    },
                }
                docs.append(doc)

            logger.info(
                "bm25_search_complete",
                query=search_query[:50] if search_query else "",
                results_count=len(docs),
            )
            return docs

        except Exception as e:
            logger.error("bm25_search_error", error=str(e))
            return []

    async def _search_vector(
        self,
        queries: QueryVariants,
    ) -> list[dict[str, Any]]:
        """Execute vector searches for all query variants.

        Args:
            queries: Query variants

        Returns:
            List of vector search results
        """
        # In real implementation, would call embedding service
        # For now, return empty list (mocked in tests)
        return []

    async def _search_hyde(
        self,
        hyde: HyDEResult,
    ) -> list[dict[str, Any]]:
        """Execute HyDE-based vector search.

        Args:
            hyde: HyDE result

        Returns:
            List of HyDE search results (empty if HyDE was skipped)
        """
        if hyde.skipped:
            return []

        # In real implementation, would embed HyDE doc and search
        # For now, return empty list (mocked in tests)
        return []

    async def _search_authority_sources(
        self,
        queries: QueryVariants,
        limit_per_source: int = 2,
    ) -> list[dict[str, Any]]:
        """Fetch top chunks from each high-authority source.

        DEV-244: Ensures official sources (Gazzetta, ADeR, etc.) are ALWAYS
        considered in RRF fusion, even if they don't rank high in pure FTS.

        Args:
            queries: Query variants
            limit_per_source: Max results per authority source

        Returns:
            List of search results from authority sources
        """
        if not self._search_service:
            return []

        search_query = queries.bm25_query or queries.original_query

        # DEV-250 FIX: Apply semantic expansion to authority search (same as _search_bm25)
        # This ensures official law documents are found even when using colloquial terms
        # E.g., "rottamazione quinquies" → expands to include "definizione agevolata"
        # which matches the official LEGGE 199/2025 terminology
        if queries.semantic_expansions:
            semantic_terms = " ".join(queries.semantic_expansions)
            search_query = f"{search_query} {semantic_terms}"
            logger.info(
                "authority_search_semantic_expansion",
                original_query=queries.bm25_query or queries.original_query,
                expanded_query=search_query[:200],
                semantic_expansions=queries.semantic_expansions,
            )

        # DEV-244 FIX: Execute searches SEQUENTIALLY to avoid SQLAlchemy session concurrency error
        # The AsyncSession doesn't support concurrent operations from the same session.
        # Running sequentially adds ~100-200ms but avoids "concurrent operations not permitted" error.
        all_docs: list[dict[str, Any]] = []
        source_list = list(HIGH_AUTHORITY_SOURCES)

        for source in source_list:
            try:
                result = await self._search_service.search(
                    query=search_query,
                    limit=limit_per_source,
                    source_pattern=source,  # Exact match filter
                )
                # Convert SearchResult to dict format
                for doc in result:
                    all_docs.append(
                        {
                            "document_id": str(doc.id),
                            "content": doc.content,
                            "source": doc.source,
                            "source_url": doc.source_url,
                            "source_name": doc.title,
                            "source_type": doc.category,
                            "published_date": doc.publication_date,
                            "score": doc.rank,
                            "highlight": doc.highlight,
                            "metadata": {
                                "knowledge_item_id": str(doc.knowledge_item_id),
                                "source_url": doc.source_url,
                            },
                        }
                    )
            except Exception as e:
                logger.warning(
                    "authority_search_failed",
                    source=source,
                    error=str(e),
                )

        logger.info(
            "authority_search_complete",
            total_results=len(all_docs),
            sources_found=list({d["source"] for d in all_docs}),
        )

        return all_docs

    def _extract_search_keywords(self, query: str) -> tuple[list[str], list[dict]]:
        """DEV-245 Phase 5.13: Extract keywords using stop word list filtering.

        Natural language questions don't search well. Converting to keywords:
        "L'IRAP può essere inclusa nella rottamazione quinquies?"
        → ["irap", "rottamazione", "quinquies"]

        DEV-245 Phase 5.13: Reverted from YAKE to stop word lists.
        YAKE didn't work well for short Italian fiscal queries - it prioritized
        verbs like "recepira" over domain terms like "rottamazione".

        DEV-245 Phase 5.14: Uses centralized STOP_WORDS from italian_stop_words module.
        This includes comprehensive verb conjugations (future, conditional, imperative)
        to fix the "recepira" problem where future tense verbs slipped through.

        Args:
            query: The reformulated user query (natural language)

        Returns:
            Tuple of (keywords, keywords_with_scores) for logging/evaluation.
            - keywords: List of significant keywords (lowercase), max 5
            - keywords_with_scores: Empty list (no scores with stop word approach)
        """
        # DEV-245 Phase 5.14: Use centralized stop words module
        # Includes comprehensive verb conjugations to fix "recepira" problem

        if not query:
            return [], []

        # Normalize and tokenize
        query_lower = query.lower()
        # Handle Italian contractions: "dell'irap" → "dell irap"
        query_lower = re.sub(r"[''`]", " ", query_lower)
        # Split on non-alphanumeric (keep accented chars)
        words = re.findall(r"[a-zàèéìòùáéíóú]+", query_lower)

        # Filter stop words and short words
        keywords = []
        for word in words:
            if word not in STOP_WORDS and len(word) > 2:
                keywords.append(word)

        # Deduplicate while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        # Limit to top 5
        result = unique_keywords[:5]

        logger.info(
            "DEV245_stop_word_keyword_extraction",
            query_preview=query[:50] if query else "N/A",
            keywords=result,
        )

        # Return empty scores list (no scoring with stop word approach)
        return result, []

    def _extract_search_keywords_with_context(
        self,
        query: str,
        messages: list[dict] | None = None,
        topic_keywords: list[str] | None = None,
    ) -> list[str]:
        """DEV-245 Phase 3.9: Extract keywords with context-first ordering.

        CRITICAL: Do NOT remove this method - it ensures Brave search uses
        optimal keyword ordering for follow-up queries.

        Industry standard (BruceClay): "Most relevant keyword first"

        For follow-up queries, orders keywords so conversation context comes first,
        then new keywords from the follow-up.

        Example:
            - Context: "parlami della rottamazione quinquies"
            - Follow-up: "L'IRAP può essere inclusa nella rottamazione quinquies?"
            - Result: ["rottamazione", "quinquies", "irap"] (context first!)
            - Brave search: "rottamazione quinquies irap 2026" ✅
            - NOT: "irap rottamazione quinquies 2026" ❌

        DEV-245 Phase 5.3: Added topic_keywords parameter.
            If topic_keywords is provided, use those as context keywords (from state).
            This ensures the main topic is NEVER lost, even at Q4+ where messages[-4:]
            would exclude the first query/response.

        Args:
            query: The reformulated user query
            messages: Conversation history for context extraction
            topic_keywords: Pre-extracted topic keywords from state (Phase 5.3)

        Returns:
            List of keywords ordered: context keywords first, then new keywords
        """
        # Extract all keywords from reformulated query
        # DEV-245 Phase 5.12: _extract_search_keywords now returns (keywords, scores)
        all_keywords, _ = self._extract_search_keywords(query)

        # DEV-245 Phase 5.3: Check for topic_keywords FIRST before early return
        # If we have topic_keywords, we need to add them even if query has few keywords
        # DEV-245 Phase 5.4: Type safety - validate topic_keywords is actually a list
        if topic_keywords and isinstance(topic_keywords, list):
            # Use pre-extracted topic keywords from state (industry standard approach)
            # IMPORTANT: We ADD topic_keywords to the result, not just use them for ordering
            # This ensures the main topic is always in the search, even if not mentioned in query
            context_keywords = set(topic_keywords)
            logger.debug(
                "phase53_using_topic_keywords",
                topic_keywords=topic_keywords,
            )

            # Combine: topic keywords first (context), then new query keywords
            new_keywords = [kw for kw in all_keywords if kw not in context_keywords]
            result = list(topic_keywords) + new_keywords
            result = result[:5]  # Cap at 5 keywords

            # Log for debugging
            if new_keywords:
                logger.debug(
                    "phase53_keyword_ordering",
                    topic_keywords=topic_keywords,
                    query_keywords=all_keywords,
                    combined=result,
                )

            return result

        if len(all_keywords) <= 2:
            return all_keywords  # No reordering needed

        # DEV-245 Phase 5.3: Fallback path (no topic_keywords provided)
        # Extract context from messages for reordering
        fallback_context_keywords: set[str] = set()

        if messages:
            # Fallback: extract from messages (legacy behavior for backwards compat)
            # Find context keywords from conversation history (last 4 messages)
            for msg in reversed(messages[-4:]):
                # Handle both dict and LangChain message objects
                if isinstance(msg, dict):
                    # DEV-245 Phase 3.9.2: Check BOTH keys - dicts may use "role" (OpenAI)
                    # or "type" (LangChain serialization format)
                    role = msg.get("role") or msg.get("type", "")
                    content = msg.get("content", "")
                else:
                    role = getattr(msg, "role", "") or getattr(msg, "type", "")
                    content = getattr(msg, "content", "") or ""

                # DEV-245 Phase 3.9.1: Only extract context from ASSISTANT messages
                # User messages include the current follow-up query which would
                # incorrectly add new keywords to context, breaking the ordering
                if role in ("assistant", "ai") and content:
                    # Extract keywords from context message (first 500 chars)
                    # DEV-245 Phase 5.12: _extract_search_keywords now returns (keywords, scores)
                    msg_keywords, _ = self._extract_search_keywords(content[:500])
                    fallback_context_keywords.update(msg_keywords[:5])

        # Separate: context keywords vs new keywords
        # Preserve order from all_keywords but reorder based on context
        context_first = [kw for kw in all_keywords if kw in fallback_context_keywords]
        new_keywords = [kw for kw in all_keywords if kw not in fallback_context_keywords]

        result = context_first + new_keywords

        # Log for debugging keyword ordering
        if context_first and new_keywords:
            logger.debug(
                "keyword_context_ordering",
                original_order=all_keywords,
                context_keywords=list(fallback_context_keywords)[:5],
                reordered=result,
            )

        return result

    async def _search_brave(
        self,
        queries: QueryVariants,
        max_results: int = 5,
        messages: list[dict] | None = None,
        topic_keywords: list[str] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search the web using Brave Search API for Parallel Hybrid RAG.

        DEV-245: Moved web search from post-LLM (Step 100) to retrieval phase.
        This enables single-LLM architecture with ~50% faster responses.

        Web results are weighted lower than KB sources (0.15 vs 0.3-0.4) to ensure
        KB remains authoritative while web provides recent/practical context.

        DEV-245 Phase 5.3: Added topic_keywords for long conversation support.
        DEV-257: Added user_id/session_id for Brave API cost tracking.

        Args:
            queries: Query variants containing original_query
            max_results: Maximum number of web results to return
            topic_keywords: Pre-extracted topic keywords from state (Phase 5.3)
            user_id: DEV-257: User ID for cost tracking
            session_id: DEV-257: Session ID for cost tracking

        Returns:
            List of web search results in standard document format
        """
        try:
            from app.core.config import settings

            if not settings.BRAVE_SEARCH_API_KEY:
                logger.debug("brave_search_skipped", reason="no_api_key")
                return []

            original_query = queries.original_query
            if not original_query:
                # DEV-245 Phase 3.3: Log when query is empty for easier debugging
                logger.warning("brave_search_skipped", reason="empty_original_query")
                return []

            # DEV-245 Phase 3.9: Use context-aware keyword extraction for follow-up queries
            # Orders keywords: context first, then new keywords from follow-up
            # "e l'irap?" after "rottamazione quinquies" → "rottamazione quinquies irap"
            # DEV-245 Phase 5.3: Pass topic_keywords for long conversation support
            search_keywords = self._extract_search_keywords_with_context(original_query, messages, topic_keywords)
            query = " ".join(search_keywords)

            # DEV-245 Phase 3.9.1: Removed automatic year suffix per user feedback
            # Let Brave search naturally without forcing a year

            logger.info(
                "brave_parallel_search_starting",
                original_query=original_query[:80],
                search_query=query,
                keywords=search_keywords,
            )

            import httpx

            headers = {
                "X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY,
                "Accept": "application/json",
            }

            # DEV-245: Track API latency for monitoring
            api_start_time = time.perf_counter()
            docs: list[dict[str, Any]] = []

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={
                        "q": query,
                        "summary": 1,  # Request AI summary
                        "count": max_results,
                    },
                    headers=headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                # Parse web results into document format
                web_results = data.get("web", {}).get("results", [])

                for i, result in enumerate(web_results[:max_results]):
                    url = result.get("url", "")
                    title = result.get("title", "")
                    snippet = result.get("description", "")

                    # Create document in same format as KB results
                    doc = {
                        "document_id": f"web_{i}_{hash(url) % 100000}",
                        "content": f"{title}\n\n{snippet}",
                        "score": 1.0 - (i * 0.1),  # Descending score by rank
                        "source_type": "web",
                        "source": "brave_web_search",
                        "source_name": title,
                        "source_url": url,
                        "published_date": None,  # Web results don't have reliable dates
                        "metadata": {
                            "title": title,
                            "source": "brave_web_search",
                            "source_url": url,
                            "is_web_result": True,
                        },
                    }
                    docs.append(doc)

                # Also check for AI summary (within same client context)
                summarizer_key = data.get("summarizer", {}).get("key")
                if summarizer_key:
                    try:
                        summary_response = await client.get(
                            "https://api.search.brave.com/res/v1/summarizer/search",
                            params={"key": summarizer_key},
                            headers=headers,
                            timeout=10.0,
                        )
                        if summary_response.status_code == 200:
                            summary_data = summary_response.json()
                            if summary_data.get("status") == "complete":
                                summary_text = summary_data.get("summary", {}).get("text", "")
                                if summary_text:
                                    # Add AI summary as a high-priority web result
                                    docs.insert(
                                        0,
                                        {
                                            "document_id": f"web_ai_summary_{hash(query) % 100000}",
                                            "content": f"[Sintesi AI dal Web]\n\n{summary_text}",
                                            "score": 1.5,  # Higher score for AI synthesis
                                            "source_type": "web_ai_summary",
                                            "source": "brave_ai_summary",
                                            "source_name": "Brave AI Sintesi",
                                            "source_url": None,
                                            "published_date": None,
                                            "metadata": {
                                                "title": "Brave AI Sintesi",
                                                "source": "brave_ai_summary",
                                                "is_web_result": True,
                                                "is_ai_synthesis": True,
                                            },
                                        },
                                    )
                    except Exception as summary_err:
                        logger.debug("brave_summary_skipped", error=str(summary_err))

            # DEV-245: Log API latency and results for monitoring
            api_latency_ms = (time.perf_counter() - api_start_time) * 1000

            # DEV-257: Track Brave API cost
            has_ai_summary = any(d.get("metadata", {}).get("is_ai_synthesis") for d in docs)
            api_calls = 1 + (1 if has_ai_summary else 0)
            if user_id:
                await self._track_brave_cost(
                    user_id=user_id,
                    session_id=session_id,
                    api_calls=api_calls,
                    latency_ms=round(api_latency_ms),
                )

            logger.info(
                "brave_parallel_search_complete",
                query=query[:50],
                results_count=len(docs),
                has_ai_summary=has_ai_summary,
                latency_ms=round(api_latency_ms, 2),
            )

            return docs

        except Exception as e:
            logger.warning(
                "brave_parallel_search_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    # DEV-257: Brave Search API cost per query (~$3/1000 queries)
    BRAVE_COST_PER_QUERY_EUR = 0.003

    async def _track_brave_cost(
        self,
        user_id: str | None,
        session_id: str | None,
        api_calls: int,
        latency_ms: int,
    ) -> None:
        """Track Brave Search API cost for usage reporting.

        DEV-257: Mirrors BraveSearchClient._track_brave_api_usage() pattern.
        Wraps in try/except so tracking failures don't break search.

        Args:
            user_id: User ID (skips if None)
            session_id: Session ID
            api_calls: Number of API calls (1 for search, +1 if AI summary)
            latency_ms: Total API response time in milliseconds
        """
        if not user_id:
            logger.debug(
                "brave_parallel_cost_tracking_skipped",
                reason="no_user_id",
                api_calls=api_calls,
            )
            return

        try:
            from app.services.usage_tracker import usage_tracker

            cost_eur = api_calls * self.BRAVE_COST_PER_QUERY_EUR
            effective_session_id = session_id or "parallel_retrieval"

            await usage_tracker.track_third_party_api(
                user_id=user_id,
                session_id=effective_session_id,
                api_type="brave_search",
                cost_eur=cost_eur,
                response_time_ms=latency_ms,
                request_count=api_calls,
                error_occurred=False,
            )

            logger.debug(
                "brave_parallel_cost_tracked",
                user_id=user_id,
                api_calls=api_calls,
                cost_eur=cost_eur,
            )

        except Exception as e:
            logger.warning(
                "brave_parallel_cost_tracking_failed",
                error=str(e),
                user_id=user_id,
            )

    def _rrf_fusion(
        self,
        search_results: list[list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Combine search results using Reciprocal Rank Fusion.

        RRF formula: score = sum(weight / (k + rank))
        where k=60 and weight depends on search type.

        DEV-245: Now includes brave (web) results for Parallel Hybrid RAG.

        Args:
            search_results: List of [bm25, vector, hyde, authority, brave] results

        Returns:
            Fused and ranked documents
        """
        # DEV-244: Added authority, DEV-245: Added brave
        search_types = ["bm25", "vector", "hyde", "authority", "brave"]
        doc_scores: dict[str, dict[str, Any]] = {}

        # DEV-245: Use dynamic weights (brave weight from config)
        weights = _get_search_weights()
        for search_type, results in zip(search_types, search_results, strict=False):
            weight = weights.get(search_type, 0.3)

            for rank, doc in enumerate(results, start=1):
                doc_id = doc.get("document_id")
                if not doc_id:
                    continue

                # RRF score contribution
                rrf_contribution = weight / (RRF_K + rank)

                if doc_id in doc_scores:
                    doc_scores[doc_id]["rrf_score"] += rrf_contribution
                    # Keep highest original score
                    if doc.get("score", 0) > doc_scores[doc_id].get("score", 0):
                        doc_scores[doc_id].update(doc)
                else:
                    doc_scores[doc_id] = {
                        **doc,
                        "rrf_score": rrf_contribution,
                    }

        # Sort by RRF score descending with document_id tiebreaker for determinism
        # DEV-244 FIX: Stable sort ensures consistent results across identical queries
        fused = list(doc_scores.values())
        fused.sort(key=lambda x: (-x.get("rrf_score", 0), x.get("document_id", "")))

        return fused

    def _apply_boosts(
        self,
        docs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply authority and recency boosts to documents.

        Args:
            docs: List of documents with RRF scores

        Returns:
            Documents with boosted scores
        """
        boosted = []

        for doc in docs:
            # Get source authority boost (DEV-242 Phase 17-18)
            source_type = doc.get("source_type", "").lower()
            source = doc.get("source", "").lower()  # DEV-242: Also use source field
            authority_boost = self._get_authority_boost(source_type, source)

            # Get recency boost
            published_date = doc.get("published_date")
            recency_boost = self._calculate_recency_boost(published_date)

            # Apply boosts to RRF score
            original_rrf = doc.get("rrf_score", 0)
            boosted_rrf = original_rrf * authority_boost * recency_boost

            # DEV-250 FIX: Also store authority_boost in metadata so it survives
            # RankedDocument transformation chain to kb_metadata_builder
            existing_metadata = doc.get("metadata", {})
            boosted_doc = {
                **doc,
                "rrf_score": boosted_rrf,
                "authority_boost": authority_boost,
                "recency_boost": recency_boost,
                "metadata": {
                    **existing_metadata,
                    "authority_boost": authority_boost,  # Survives transformation chain
                },
            }
            boosted.append(boosted_doc)

        # Re-sort by boosted score with document_id tiebreaker for determinism
        # DEV-244 FIX: Stable sort ensures consistent results across identical queries
        boosted.sort(key=lambda x: (-x.get("rrf_score", 0), x.get("document_id", "")))

        return boosted

    def _get_authority_boost(self, source_type: str, source: str = "") -> float:
        """Get authority boost for a source type and source.

        DEV-242 Phase 17-18: Combines document type boost (GERARCHIA_FONTI)
        with source authority boost (SOURCE_AUTHORITY) to ensure full law
        documents rank higher than summaries.

        Args:
            source_type: Type of document (e.g., "legge", "decreto")
            source: Source field from database (e.g., "gazzetta_ufficiale")

        Returns:
            Combined authority multiplier (1.0 for unknown types)
        """
        # Get document type boost (from title pattern matching)
        type_boost = GERARCHIA_FONTI.get(source_type.lower(), 1.0)

        # Get source authority boost (from database source field)
        source_boost = SOURCE_AUTHORITY.get(source.lower(), 1.0)

        # Combine boosts (multiplicative)
        combined_boost = type_boost * source_boost

        return combined_boost

    def _calculate_recency_boost(
        self,
        published_date: datetime | date | None,
    ) -> float:
        """Calculate recency boost for a document.

        Documents published within 12 months get +50% boost.

        Args:
            published_date: Document publication date (datetime or date)

        Returns:
            Recency multiplier (1.0 or 1.5)
        """
        if not published_date:
            return 1.0

        # DEV-242: Convert date to datetime for comparison
        if isinstance(published_date, date) and not isinstance(published_date, datetime):
            published_date = datetime.combine(published_date, datetime.min.time())

        threshold = datetime.now() - timedelta(days=RECENCY_THRESHOLD_DAYS)

        if published_date >= threshold:
            return RECENCY_BOOST  # +50%

        return 1.0

    def _deduplicate(
        self,
        docs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Remove duplicate documents, keeping highest score.

        Args:
            docs: List of documents (may contain duplicates)

        Returns:
            Deduplicated list with highest-scoring versions, sorted deterministically
        """
        seen: dict[str, dict[str, Any]] = {}

        for doc in docs:
            doc_id = doc.get("document_id")
            if not doc_id:
                continue

            if doc_id not in seen:
                seen[doc_id] = doc
            elif doc.get("score", 0) > seen[doc_id].get("score", 0):
                # Keep version with higher original score
                seen[doc_id] = doc

        # DEV-244 FIX: Sort by RRF score descending with document_id tiebreaker
        # This ensures deterministic ordering after deduplication
        # Without this, dict.values() order could vary, causing inconsistent results
        return sorted(
            seen.values(),
            key=lambda x: (-x.get("rrf_score", 0), x.get("document_id", "")),
        )

    def _get_top_k(
        self,
        docs: list[dict[str, Any]],
        k: int = DEFAULT_TOP_K,
    ) -> list[dict[str, Any]]:
        """Get top-K documents with reserved slots for official AND web sources.

        DEV-244: Reserved slots for HIGH_AUTHORITY_SOURCES (official KB)
        DEV-245 Phase 3.8: Reserved slots for web results (Brave)

        This ensures:
        1. Official sources (ADeR, Gazzetta) always appear in Fonti
        2. Web sources from Brave search always appear in Fonti
        3. Quality ordering is preserved within each category

        Args:
            docs: List of documents
            k: Number of documents to return

        Returns:
            Top-K documents sorted by score descending
        """

        def sort_key(x: dict[str, Any]) -> tuple[float, str]:
            return (-x.get("rrf_score", 0), x.get("document_id", ""))

        # Step 1: Separate into official KB, web, and other
        source_best: dict[str, dict[str, Any]] = {}
        web_results: list[dict[str, Any]] = []
        other: list[dict[str, Any]] = []

        for doc in docs:
            source = doc.get("source", "").lower()
            metadata = doc.get("metadata", {}) or {}

            # DEV-245 Phase 3.8: Detect web results using multiple markers
            is_web = (
                metadata.get("is_web_result", False)
                or source.startswith("brave_")
                or doc.get("source_type", "") in ("web", "web_ai_summary")
            )

            if source in HIGH_AUTHORITY_SOURCES:
                # Keep only the highest-scoring chunk per official source type
                if source not in source_best or doc.get("rrf_score", 0) > source_best[source].get("rrf_score", 0):
                    source_best[source] = doc
            elif is_web:
                # DEV-245 Phase 3.8: Separate web results for reserved slots
                web_results.append(doc)
            else:
                other.append(doc)

        # Step 2: Reserve slots for official sources (up to MAX_RESERVED_SLOTS=3)
        official_diverse = sorted(source_best.values(), key=sort_key)
        reserved_official = min(MAX_RESERVED_SLOTS, len(official_diverse), k)
        top_official = official_diverse[:reserved_official]

        # Step 3: DEV-245 Phase 3.8: Reserve slots for web results (up to WEB_RESERVED_SLOTS=2)
        web_results.sort(key=sort_key)
        remaining_after_official = k - len(top_official)
        reserved_web = min(WEB_RESERVED_SLOTS, len(web_results), remaining_after_official)
        top_web = web_results[:reserved_web]

        # Step 4: Fill remaining slots with other sources
        other.sort(key=sort_key)
        remaining_slots = k - len(top_official) - len(top_web)
        top_other = other[:remaining_slots]

        # Step 5: Combine and re-sort for final ordering
        combined = top_official + top_web + top_other
        combined.sort(key=sort_key)

        # DEV-245 Phase 3.8: Log web reservation results for debugging
        if web_results:
            logger.debug(
                "top_k_web_reservation",
                total_web_available=len(web_results),
                web_reserved=len(top_web),
                official_reserved=len(top_official),
                other_included=len(top_other),
            )

        return combined

    def _to_ranked_documents(
        self,
        docs: list[dict[str, Any]],
    ) -> list[RankedDocument]:
        """Convert dictionary documents to RankedDocument objects.

        Args:
            docs: List of document dictionaries

        Returns:
            List of RankedDocument objects
        """
        ranked = []

        for doc in docs:
            ranked_doc = RankedDocument(
                document_id=doc.get("document_id", ""),
                content=doc.get("content", ""),
                score=doc.get("score", 0.0),
                rrf_score=doc.get("rrf_score", 0.0),
                source_type=doc.get("source_type", ""),
                source_name=doc.get("source_name", ""),
                published_date=doc.get("published_date"),
                metadata=doc.get("metadata", {}),
            )
            ranked.append(ranked_doc)

        return ranked
