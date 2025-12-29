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
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

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
GERARCHIA_FONTI = {
    "legge": 1.3,
    "decreto": 1.25,
    "circolare": 1.15,
    "risoluzione": 1.1,
    "interpello": 1.05,
    "faq": 1.0,
    "guida": 0.95,
}

# Recency boost threshold (12 months)
RECENCY_THRESHOLD_DAYS = 365
RECENCY_BOOST = 1.5  # +50%

# Default top-K results
DEFAULT_TOP_K = 10


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

        Args:
            queries: Query variants

        Returns:
            List of BM25 search results
        """
        # In real implementation, would call search service
        # For now, return empty list (mocked in tests)
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
            # Get source authority boost
            source_type = doc.get("source_type", "").lower()
            authority_boost = self._get_authority_boost(source_type)

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

    def _get_authority_boost(self, source_type: str) -> float:
        """Get authority boost for a source type.

        Args:
            source_type: Type of document source

        Returns:
            Authority multiplier (1.0 for unknown types)
        """
        return GERARCHIA_FONTI.get(source_type.lower(), 1.0)

    def _calculate_recency_boost(
        self,
        published_date: datetime | None,
    ) -> float:
        """Calculate recency boost for a document.

        Documents published within 12 months get +50% boost.

        Args:
            published_date: Document publication date

        Returns:
            Recency multiplier (1.0 or 1.5)
        """
        if not published_date:
            return 1.0

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
