"""
Knowledge Search Service - RAG STEP 39 Implementation.

Implements RAG STEP 39 — KBPreFetch

This service implements hybrid search combining BM25 text search, vector semantic search,
and recency boost to retrieve the most relevant knowledge items for user queries.

Based on Mermaid diagram: KBPreFetch (KnowledgeSearch.retrieve_topk BM25 and vectors and recency boost)
"""

import time
import math
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from sqlalchemy.sql import Select

from app.models.knowledge import KnowledgeItem
from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.services.search_service import SearchService, SearchResult as BaseSearchResult
from app.core.logging import logger

STEP_NUM = 39
STEP_ID = "RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost"
NODE_LABEL = "KBPreFetch"


class SearchMode(str, Enum):
    """Search mode for knowledge retrieval."""
    HYBRID = "hybrid"      # BM25 + vector + recency (default)
    BM25_ONLY = "bm25_only"  # BM25 text search only
    VECTOR_ONLY = "vector_only"  # Vector semantic search only


@dataclass
class KnowledgeSearchConfig:
    """Configuration for knowledge search service."""
    bm25_weight: float = 0.4       # Weight for BM25 text search scores
    vector_weight: float = 0.4     # Weight for vector similarity scores  
    recency_weight: float = 0.2    # Weight for recency boost
    max_results: int = 10          # Maximum number of results to return
    min_score_threshold: float = 0.1  # Minimum combined score threshold
    recency_decay_days: int = 90   # Days for recency decay calculation
    vector_top_k: int = 50         # Top-k results from vector search
    bm25_top_k: int = 50           # Top-k results from BM25 search
    
    def __post_init__(self):
        """Validate configuration weights sum to 1.0."""
        total_weight = self.bm25_weight + self.vector_weight + self.recency_weight
        if not math.isclose(total_weight, 1.0, rel_tol=1e-5):
            raise ValueError(f"Search weights must sum to 1.0, got {total_weight}")


@dataclass
class SearchResult:
    """Enhanced search result with hybrid scoring."""
    id: str
    title: str
    content: str
    category: str
    score: float                    # Final combined score
    source: str
    updated_at: Optional[datetime] = None
    
    # Individual scoring components
    bm25_score: Optional[float] = None
    vector_score: Optional[float] = None
    recency_score: Optional[float] = None
    
    # Search metadata
    search_method: str = field(default="hybrid")
    rank_position: Optional[int] = None
    highlight: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for structured logging."""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "score": self.score,
            "source": self.source,
            "bm25_score": self.bm25_score,
            "vector_score": self.vector_score,
            "recency_score": self.recency_score,
            "search_method": self.search_method,
            "rank_position": self.rank_position,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class KnowledgeSearchService:
    """Service for hybrid knowledge search with BM25, vector search and recency boost."""
    
    def __init__(
        self,
        db_session: AsyncSession,
        vector_service: Any = None,
        config: Optional[KnowledgeSearchConfig] = None
    ):
        """Initialize knowledge search service."""
        self.db = db_session
        self.vector_service = vector_service
        self.config = config or KnowledgeSearchConfig()
        
        # Initialize BM25 search service
        self.search_service = SearchService(db_session)
        
        # Cache for performance optimization
        self._embedding_cache: Dict[str, List[float]] = {}
        self._query_cache: Dict[str, List[SearchResult]] = {}
        
    async def retrieve_topk(self, query_data: Dict[str, Any]) -> List[SearchResult]:
        """
        Retrieve top-k knowledge items using hybrid search.
        
        Args:
            query_data: Dictionary containing:
                - query: The user's query text
                - canonical_facts: List of extracted canonical facts (optional)
                - user_id: User identifier
                - session_id: Session identifier
                - trace_id: Trace identifier for logging
                - search_mode: SearchMode enum (optional, defaults to HYBRID)
                - filters: Dictionary of filters (category, source, etc.)
                - max_results: Maximum results to return (optional)
        
        Returns:
            List of SearchResult objects ordered by combined relevance score
        """
        start_time = time.perf_counter()
        
        try:
            # Extract and validate query parameters
            query = query_data.get("query", "").strip()
            if not query:
                return []
            
            canonical_facts = query_data.get("canonical_facts", [])
            search_mode = SearchMode(query_data.get("search_mode", SearchMode.HYBRID))
            filters = query_data.get("filters", {})
            max_results = query_data.get("max_results", self.config.max_results)
            trace_id = query_data.get("trace_id")
            
            # Use timer context manager for performance logging
            with rag_step_timer(
                STEP_NUM, 
                STEP_ID, 
                NODE_LABEL,
                query=query,
                search_mode=search_mode.value,
                trace_id=trace_id
            ):
                # Perform search based on mode
                if search_mode == SearchMode.BM25_ONLY:
                    bm25_raw_results = await self._perform_bm25_search(query, canonical_facts, max_results, filters)
                    # Convert BM25 dict results to SearchResult objects
                    results = []
                    for bm25_result in bm25_raw_results:
                        search_result = SearchResult(
                            id=str(bm25_result["id"]),
                            title=bm25_result["title"],
                            content=bm25_result["content"],
                            category=bm25_result["category"],
                            score=bm25_result["rank_score"],
                            source=bm25_result["source"],
                            updated_at=bm25_result["updated_at"],
                            bm25_score=bm25_result["rank_score"],
                            search_method="bm25"
                        )
                        results.append(search_result)
                
                elif search_mode == SearchMode.VECTOR_ONLY:
                    results = await self._perform_vector_search(query, canonical_facts, filters)
                    for result in results:
                        result.search_method = "vector"
                    results = results[:max_results]
                
                else:  # HYBRID mode
                    results = await self._perform_hybrid_search(query, canonical_facts, filters, max_results)
                
                # Apply final ranking and filtering
                results = self._apply_final_ranking(results, max_results)
                
                # Log successful search
                rag_step_log(
                    step=STEP_NUM,
                    step_id=STEP_ID,
                    node_label=NODE_LABEL,
                    query=query,
                    results_count=len(results),
                    search_mode=search_mode.value,
                    trace_id=trace_id,
                    avg_score=sum(r.score for r in results) / len(results) if results else 0.0,
                    top_categories=[r.category for r in results[:3]]
                )
                
                return results
                
        except Exception as exc:
            # Calculate latency even on error
            end_time = time.perf_counter()
            latency_ms = round((end_time - start_time) * 1000.0, 2)
            
            # Log error
            rag_step_log(
                step=STEP_NUM,
                step_id=STEP_ID, 
                node_label=NODE_LABEL,
                level="ERROR",
                query=query_data.get("query", ""),
                error=str(exc),
                latency_ms=latency_ms,
                trace_id=query_data.get("trace_id")
            )
            
            # Return empty results on error (graceful degradation)
            logger.error("knowledge_search_error", error=str(exc), trace_id=query_data.get("trace_id"))
            return []
    
    async def _perform_hybrid_search(
        self, 
        query: str, 
        canonical_facts: List[str],
        filters: Dict[str, Any],
        max_results: int
    ) -> List[SearchResult]:
        """Perform hybrid search combining BM25, vector search and recency boost."""
        
        # Perform both searches concurrently for better performance
        import asyncio
        
        bm25_task = asyncio.create_task(
            self._perform_bm25_search(query, canonical_facts, self.config.bm25_top_k, filters)
        )
        
        vector_task = asyncio.create_task(
            self._perform_vector_search(query, canonical_facts, filters)
        )
        
        # Wait for both searches to complete
        bm25_results, vector_results = await asyncio.gather(bm25_task, vector_task)
        
        # Convert BM25 results to SearchResult format
        bm25_search_results = []
        for bm25_result in bm25_results:
            search_result = SearchResult(
                id=str(bm25_result["id"]),
                title=bm25_result["title"],
                content=bm25_result["content"],
                category=bm25_result["category"],
                score=0.0,  # Will be calculated in hybrid scoring
                source=bm25_result["source"],
                updated_at=bm25_result["updated_at"],
                bm25_score=bm25_result["rank_score"],
                search_method="hybrid"
            )
            bm25_search_results.append(search_result)
        
        # Combine and deduplicate results
        combined_results = self._combine_and_deduplicate_results(bm25_search_results, vector_results)
        
        # Apply hybrid scoring
        scored_results = self._apply_hybrid_scoring(combined_results)
        
        # Sort by combined score
        scored_results.sort(key=lambda x: x.score, reverse=True)
        
        return scored_results[:max_results]
    
    async def _perform_bm25_search(
        self,
        query: str,
        canonical_facts: List[str], 
        max_results: int,
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Perform BM25 full-text search using existing SearchService."""
        
        # Use canonical facts if available for better search
        search_query = query
        if canonical_facts:
            # Enhance query with canonical facts
            facts_query = " ".join(canonical_facts)
            search_query = f"{query} {facts_query}"
        
        # Extract filters
        category = filters.get("category")
        min_rank = filters.get("min_rank", 0.01)
        
        # Perform search using existing search service
        search_results = await self.search_service.search(
            query=search_query,
            limit=max_results,
            offset=0,
            category=category,
            min_rank=min_rank
        )
        
        # Convert to dict format for consistency
        bm25_results = []
        for result in search_results:
            bm25_results.append({
                "id": result.id,
                "title": result.title,
                "content": result.content,
                "category": result.category,
                "source": result.source or "unknown",
                "rank_score": result.rank_score,
                "relevance_score": result.relevance_score,
                "updated_at": result.updated_at,
                "highlight": result.highlight
            })
        
        return bm25_results
    
    async def _perform_vector_search(
        self,
        query: str,
        canonical_facts: List[str],
        filters: Dict[str, Any]
    ) -> List[SearchResult]:
        """Perform vector semantic search."""
        
        if not self.vector_service or not self.vector_service.is_available():
            # Graceful degradation - return empty results if vector service unavailable
            logger.warning("vector_service_unavailable", query=query)
            return []
        
        try:
            # Create embedding for query
            query_text = query
            if canonical_facts:
                # Enhance with canonical facts
                query_text = f"{query} {' '.join(canonical_facts)}"
            
            embedding = self.vector_service.create_embedding(query_text)
            if not embedding:
                logger.warning("vector_embedding_failed", query=query)
                return []
            
            # Perform vector search
            vector_results = self.vector_service.search_similar(
                embedding=embedding,
                top_k=self.config.vector_top_k,
                filters=filters
            )
            
            # Convert to SearchResult format
            search_results = []
            for i, result in enumerate(vector_results):
                search_result = SearchResult(
                    id=str(result["id"]),
                    title=result.get("metadata", {}).get("title", "Unknown Title"),
                    content=result.get("metadata", {}).get("content", ""),
                    category=result.get("metadata", {}).get("category", "unknown"),
                    score=0.0,  # Will be calculated in hybrid scoring
                    source=result.get("metadata", {}).get("source", "vector_db"),
                    vector_score=float(result["score"]),
                    search_method="hybrid",
                    rank_position=i + 1,
                    metadata=result.get("metadata", {})
                )
                search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            logger.error("vector_search_error", error=str(e), query=query)
            return []
    
    def _combine_and_deduplicate_results(
        self, 
        bm25_results: List[SearchResult],
        vector_results: List[SearchResult]
    ) -> List[SearchResult]:
        """Combine results from BM25 and vector search, removing duplicates."""
        
        results_by_id: Dict[str, SearchResult] = {}
        
        # Add BM25 results
        for result in bm25_results:
            results_by_id[result.id] = result
        
        # Add vector results, merging with BM25 results if duplicate IDs found
        for result in vector_results:
            if result.id in results_by_id:
                # Merge vector score into existing result
                existing = results_by_id[result.id]
                existing.vector_score = result.vector_score
                # Use better metadata if vector result has more info
                if len(result.metadata) > len(existing.metadata):
                    existing.metadata.update(result.metadata)
            else:
                results_by_id[result.id] = result
        
        return list(results_by_id.values())
    
    def _apply_hybrid_scoring(self, results: List[SearchResult]) -> List[SearchResult]:
        """Apply hybrid scoring combining BM25, vector similarity, and recency boost."""
        
        if not results:
            return results
        
        # Normalize scores to 0-1 range for fair combination
        bm25_scores = [r.bm25_score for r in results if r.bm25_score is not None]
        vector_scores = [r.vector_score for r in results if r.vector_score is not None]
        
        max_bm25 = max(bm25_scores) if bm25_scores else 1.0
        max_vector = max(vector_scores) if vector_scores else 1.0
        
        # Avoid division by zero
        max_bm25 = max(max_bm25, 0.001)
        max_vector = max(max_vector, 0.001)
        
        # Apply hybrid scoring to each result
        for result in results:
            # Normalize individual scores
            norm_bm25 = (result.bm25_score or 0.0) / max_bm25
            norm_vector = (result.vector_score or 0.0) / max_vector
            
            # Calculate recency boost
            recency_boost = self._calculate_recency_boost(result.updated_at)
            result.recency_score = recency_boost
            
            # Combine scores using configured weights
            combined_score = (
                self.config.bm25_weight * norm_bm25 +
                self.config.vector_weight * norm_vector +
                self.config.recency_weight * recency_boost
            )
            
            result.score = combined_score
        
        return results
    
    def _calculate_recency_boost(self, updated_at: Optional[datetime]) -> float:
        """Calculate recency boost based on document age."""
        
        if not updated_at:
            return 0.0  # No boost for documents without timestamp
        
        # Ensure timezone-aware comparison
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        age_days = (now - updated_at).total_seconds() / 86400  # Convert to days
        
        # Apply exponential decay: newer documents get higher boost
        decay_factor = math.exp(-age_days / self.config.recency_decay_days)
        
        # Scale to 0-1 range
        recency_boost = min(max(decay_factor, 0.0), 1.0)
        
        return recency_boost
    
    def _apply_final_ranking(self, results: List[SearchResult], max_results: int) -> List[SearchResult]:
        """Apply final ranking and filtering."""
        
        # Filter by minimum score threshold
        filtered_results = [
            r for r in results 
            if r.score >= self.config.min_score_threshold
        ]
        
        # Sort by combined score (already done but ensure consistency)
        filtered_results.sort(key=lambda x: x.score, reverse=True)
        
        # Add rank positions
        for i, result in enumerate(filtered_results[:max_results]):
            result.rank_position = i + 1
        
        return filtered_results[:max_results]
    
    async def fetch_recent_kb_for_changes(self, query_data: Dict[str, Any]) -> List[SearchResult]:
        """
        RAG STEP 26 — KnowledgeSearch.context_topk fetch recent KB for changes.
        
        This method specifically fetches recent KB changes when a Golden Set hit occurs,
        to determine if KB has newer or conflicting information that should be merged
        with the Golden Set response.
        
        Args:
            query_data: Dictionary containing:
                - query: The user's query text
                - canonical_facts: List of extracted canonical facts (optional)
                - user_id: User identifier
                - session_id: Session identifier
                - trace_id: Trace identifier for logging
                - golden_timestamp: Timestamp of the Golden Set entry
                - context_check: Flag indicating this is for context checking
                - recency_threshold_days: Days threshold for considering "recent" (default: 14)
                - golden_metadata: Golden Set metadata for conflict detection (optional)
        
        Returns:
            List of SearchResult objects with recent KB changes that might conflict
            or provide newer information than the Golden Set
        """
        start_time = time.perf_counter()
        
        # Extract parameters
        query = query_data.get("query", "").strip()
        trace_id = query_data.get("trace_id")
        golden_timestamp = query_data.get("golden_timestamp")
        recency_threshold_days = query_data.get("recency_threshold_days", 14)
        golden_metadata = query_data.get("golden_metadata", {})
        
        # RAG STEP 26 constants
        STEP_NUM = 26
        STEP_ID = "RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes"
        NODE_LABEL = "KBContextCheck"
        
        try:
            # Use timer context manager for performance tracking
            with rag_step_timer(
                STEP_NUM,
                STEP_ID,
                NODE_LABEL,
                query=query,
                trace_id=trace_id
            ):
                # Initial logging
                rag_step_log(
                    step=STEP_NUM,
                    step_id=STEP_ID,
                    node_label=NODE_LABEL,
                    query=query,
                    trace_id=trace_id,
                    golden_timestamp=golden_timestamp.isoformat() if golden_timestamp else None,
                    recency_threshold_days=recency_threshold_days,
                    processing_stage="started"
                )
                
                if not query:
                    rag_step_log(
                        step=STEP_NUM,
                        step_id=STEP_ID,
                        node_label=NODE_LABEL,
                        trace_id=trace_id,
                        processing_stage="empty_query",
                        recent_changes_count=0
                    )
                    return []
                
                # Perform hybrid search to get potential recent changes
                canonical_facts = query_data.get("canonical_facts", [])
                filters = query_data.get("filters", {})
                max_results = query_data.get("max_results", self.config.max_results * 2)  # Get more for filtering
                
                # Search for recent knowledge items
                all_results = await self._perform_hybrid_search(query, canonical_facts, filters, max_results)
                
                # Filter for recent changes
                recent_results = self._filter_recent_changes(
                    all_results, 
                    golden_timestamp, 
                    recency_threshold_days
                )
                
                # Detect potential conflicts with Golden Set
                conflict_results = self._detect_conflicts_with_golden(recent_results, golden_metadata)
                
                # Final filtering and ranking for context
                context_results = self._rank_for_context_check(conflict_results)
                
                # Log results
                rag_step_log(
                    step=STEP_NUM,
                    step_id=STEP_ID,
                    node_label=NODE_LABEL,
                    query=query,
                    trace_id=trace_id,
                    recent_changes_count=len(context_results),
                    potential_conflicts=len([r for r in context_results if r.metadata.get("conflict_detected")]),
                    golden_timestamp=golden_timestamp.isoformat() if golden_timestamp else None,
                    processing_stage="completed"
                )
                
                if len(context_results) == 0:
                    rag_step_log(
                        step=STEP_NUM,
                        step_id=STEP_ID,
                        node_label=NODE_LABEL,
                        query=query,
                        trace_id=trace_id,
                        processing_stage="no_recent_changes",
                        message="No recent KB changes found newer than Golden Set"
                    )
                
                return context_results
                
        except Exception as exc:
            # Calculate latency even on error
            end_time = time.perf_counter()
            latency_ms = round((end_time - start_time) * 1000.0, 2)
            
            # Log error
            rag_step_log(
                step=STEP_NUM,
                step_id=STEP_ID,
                node_label=NODE_LABEL,
                level="ERROR",
                query=query,
                error=str(exc),
                latency_ms=latency_ms,
                trace_id=trace_id,
                processing_stage="error"
            )
            
            # Return empty results on error (graceful degradation)
            logger.error("kb_context_check_error", error=str(exc), trace_id=trace_id)
            return []
    
    def _filter_recent_changes(
        self, 
        results: List[SearchResult], 
        golden_timestamp: Optional[datetime], 
        recency_threshold_days: int
    ) -> List[SearchResult]:
        """Filter results to only include recent changes."""
        
        if not results:
            return []
        
        now = datetime.now(timezone.utc)
        
        # Calculate cutoff time - use the more recent of golden_timestamp or recency_threshold
        cutoff_time = now - timedelta(days=recency_threshold_days)
        if golden_timestamp:
            # Ensure timezone-aware comparison
            if golden_timestamp.tzinfo is None:
                golden_timestamp = golden_timestamp.replace(tzinfo=timezone.utc)
            cutoff_time = max(cutoff_time, golden_timestamp)
        
        # Filter for recent results
        recent_results = []
        for result in results:
            if result.updated_at:
                # Ensure timezone-aware comparison
                updated_at = result.updated_at
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                
                if updated_at > cutoff_time:
                    recent_results.append(result)
        
        return recent_results
    
    def _detect_conflicts_with_golden(
        self, 
        results: List[SearchResult], 
        golden_metadata: Dict[str, Any]
    ) -> List[SearchResult]:
        """Detect potential conflicts between KB results and Golden Set."""
        
        if not results or not golden_metadata:
            return results
        
        golden_category = golden_metadata.get("category", "")
        golden_tags = set(golden_metadata.get("tags", []))
        
        for result in results:
            conflict_detected = False
            conflict_reasons = []
            
            # Check category conflicts
            if golden_category and result.category == golden_category:
                # Same category might indicate conflicting information
                conflict_detected = True
                conflict_reasons.append("same_category")
            
            # Check for conflict tags in metadata
            result_tags = set(result.metadata.get("conflict_tags", []))
            if result_tags.intersection({"supersedes_previous", "rate_change", "law_change"}):
                conflict_detected = True
                conflict_reasons.append("explicit_conflict_tags")
            
            # Check for overlapping content indicators
            if golden_tags and result.metadata.get("tags"):
                result_tag_set = set(result.metadata.get("tags", []))
                if golden_tags.intersection(result_tag_set):
                    conflict_detected = True
                    conflict_reasons.append("overlapping_tags")
            
            # Store conflict information in metadata
            if conflict_detected:
                result.metadata["conflict_detected"] = True
                result.metadata["conflict_reasons"] = conflict_reasons
                
                # Log potential conflict
                logger.info(
                    "potential_conflict_detected",
                    kb_result_id=result.id,
                    kb_title=result.title,
                    conflict_reasons=conflict_reasons,
                    golden_category=golden_category
                )
        
        return results
    
    def _rank_for_context_check(self, results: List[SearchResult]) -> List[SearchResult]:
        """Apply specialized ranking for context checking."""
        
        if not results:
            return []
        
        # Sort by combination of recency and conflict importance
        def context_score(result: SearchResult) -> float:
            base_score = result.score
            
            # Boost for recent updates
            recency_boost = result.recency_score or 0.0
            
            # Boost for potential conflicts
            conflict_boost = 0.2 if result.metadata.get("conflict_detected") else 0.0
            
            return base_score + (0.3 * recency_boost) + conflict_boost
        
        # Sort by context score
        results.sort(key=context_score, reverse=True)
        
        # Apply final filtering - limit to most relevant for context
        max_context_results = min(5, len(results))  # At most 5 context items
        
        return results[:max_context_results]


# Convenience function for direct usage
async def retrieve_knowledge_topk(query_data: Dict[str, Any]) -> List[SearchResult]:
    """
    Convenience function to retrieve top-k knowledge items.
    
    Args:
        query_data: Query data dictionary with db_session and vector_service
        
    Returns:
        List of SearchResult objects
    """
    db_session = query_data.pop("db_session")
    vector_service = query_data.pop("vector_service", None)
    
    service = KnowledgeSearchService(
        db_session=db_session,
        vector_service=vector_service
    )
    
    return await service.retrieve_topk(query_data)