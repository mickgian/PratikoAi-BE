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
from app.services.multi_query_generator import QueryVariants

# RRF constant (k=60 per Section 13.7.2)
RRF_K = 60

# Search type weights per Section 13.7.2
SEARCH_WEIGHTS = {
    "bm25": 0.3,
    "vector": 0.4,
    "hyde": 0.3,
}

# Source authority hierarchy per Section 13.7.4
# DEV-242 Phase 17: Increased boosts to prioritize full laws over summaries
GERARCHIA_FONTI = {
    "legge": 1.8,  # Was 1.3 - increased to ensure laws rank above summaries
    "decreto": 1.6,  # Was 1.25
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
    """

    documents: list[RankedDocument]
    total_found: int
    search_time_ms: float


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
    ) -> RetrievalResult:
        """Execute parallel retrieval and fuse results.

        Runs BM25, vector, and HyDE searches in parallel, combines
        using RRF, applies boosts, and returns top-K documents.

        Args:
            queries: Query variants from MultiQueryGenerator
            hyde: HyDE result from HyDEGenerator
            top_k: Number of top documents to return

        Returns:
            RetrievalResult with ranked documents
        """
        start_time = time.perf_counter()

        try:
            # Execute all searches in parallel
            search_results = await self._execute_parallel_searches(queries, hyde)

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

            return RetrievalResult(
                documents=ranked_docs,
                total_found=total_found,
                search_time_ms=elapsed_ms,
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
            )

    async def _execute_parallel_searches(
        self,
        queries: QueryVariants,
        hyde: HyDEResult,
    ) -> list[list[dict[str, Any]]]:
        """Execute all searches in parallel.

        Args:
            queries: Query variants
            hyde: HyDE result

        Returns:
            List of search results [bm25_results, vector_results, hyde_results]
        """
        # Create search tasks
        tasks = [
            self._search_bm25(queries),
            self._search_vector(queries),
            self._search_hyde(hyde),
        ]

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed: list[list[dict[str, Any]]] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.warning(
                    "search_task_failed",
                    task_index=i,
                    error=str(result),
                )
                processed.append([])
            else:
                processed.append(result)

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
                    "metadata": {
                        "title": result.title,
                        "source": result.source,
                        "category": result.category,
                        "chunk_id": result.id,
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

    def _rrf_fusion(
        self,
        search_results: list[list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Combine search results using Reciprocal Rank Fusion.

        RRF formula: score = sum(weight / (k + rank))
        where k=60 and weight depends on search type.

        Args:
            search_results: List of [bm25, vector, hyde] results

        Returns:
            Fused and ranked documents
        """
        search_types = ["bm25", "vector", "hyde"]
        doc_scores: dict[str, dict[str, Any]] = {}

        for search_type, results in zip(search_types, search_results, strict=False):
            weight = SEARCH_WEIGHTS.get(search_type, 0.3)

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

        # Sort by RRF score descending
        fused = list(doc_scores.values())
        fused.sort(key=lambda x: x.get("rrf_score", 0), reverse=True)

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

            boosted_doc = {
                **doc,
                "rrf_score": boosted_rrf,
                "authority_boost": authority_boost,
                "recency_boost": recency_boost,
            }
            boosted.append(boosted_doc)

        # Re-sort by boosted score
        boosted.sort(key=lambda x: x.get("rrf_score", 0), reverse=True)

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
            Deduplicated list with highest-scoring versions
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

        return list(seen.values())

    def _get_top_k(
        self,
        docs: list[dict[str, Any]],
        k: int = DEFAULT_TOP_K,
    ) -> list[dict[str, Any]]:
        """Get top-K documents by RRF score.

        Args:
            docs: List of documents
            k: Number of documents to return

        Returns:
            Top-K documents sorted by score descending
        """
        # Sort by RRF score descending
        sorted_docs = sorted(
            docs,
            key=lambda x: x.get("rrf_score", 0),
            reverse=True,
        )

        return sorted_docs[:k]

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
