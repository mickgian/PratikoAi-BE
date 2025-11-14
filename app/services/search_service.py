"""
PostgreSQL Full-Text Search Service
Implements efficient text search with Italian language support
"""

import re
from dataclasses import dataclass
from datetime import (
    date,
    datetime,
    timedelta,
)
from typing import (
    List,
    Optional,
)

from sqlalchemy import (
    func,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.config import settings
from app.core.logging import logger
from app.models.knowledge import KnowledgeItem
from app.services.cache import cache_service


@dataclass
class SearchResult:
    """Search result with ranking and highlighting"""

    id: str
    title: str
    content: str
    category: str
    rank_score: float
    relevance_score: float
    highlight: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    updated_at: Optional[datetime] = None
    knowledge_item_id: Optional[int] = None  # Parent document ID for chunks
    chunk_index: Optional[int] = None  # Chunk position in document
    publication_date: Optional[date] = None  # Publication date from RSS/database


class SearchService:
    """
    PostgreSQL Full-Text Search service with Italian language support.

    Features:
    - Italian language text search configuration
    - Accent-insensitive search
    - Partial word matching
    - Result ranking with ts_rank
    - Redis caching for performance
    - Query normalization
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.cache = cache_service
        self.cache_ttl = 3600  # 1 hour cache

    async def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category: Optional[str] = None,
        min_rank: float = 0.01,
        source_pattern: Optional[str] = None,
        publication_year: Optional[int] = None,
        title_pattern: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Perform full-text search on knowledge items.

        Args:
            query: Search query string
            limit: Maximum number of results
            offset: Pagination offset
            category: Filter by category
            min_rank: Minimum rank score threshold
            source_pattern: Source filter pattern (for LIKE matching, e.g., "agenzia_entrate%")
            publication_year: Filter by publication year (e.g., 2025)
            title_pattern: Title filter pattern (for LIKE matching on document numbers, e.g., "n. 64")

        Returns:
            List of SearchResult objects ordered by relevance
        """
        # Clean and validate query
        query = query.strip()
        if not query:
            return []

        # Normalize query for Italian text
        normalized_query = self._normalize_italian_query(query)

        # Check cache (using Redis client directly for custom keys)
        cache_key = f"search:{normalized_query}:{category}:{limit}:{offset}"
        redis_client = await self.cache._get_redis()
        cached_results = None
        if redis_client:
            try:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    import json

                    cached_results = json.loads(cached_data)

                    # FIX: Parse datetime strings back to objects after cache deserialization
                    # JSON serialization converts datetime objects to ISO strings
                    # We must convert them back to avoid "'str' object has no attribute 'tzinfo'" errors
                    for result in cached_results:
                        if "updated_at" in result and isinstance(result["updated_at"], str):
                            try:
                                result["updated_at"] = datetime.fromisoformat(
                                    result["updated_at"].replace("Z", "+00:00")
                                )
                            except Exception:
                                result["updated_at"] = None

                        if "publication_date" in result and isinstance(result["publication_date"], str):
                            try:
                                result["publication_date"] = datetime.fromisoformat(result["publication_date"]).date()
                            except Exception:
                                result["publication_date"] = None

                    return [SearchResult(**r) for r in cached_results]
            except Exception:
                pass  # Cache miss or error, continue with search

        # Build and execute search query
        results = await self._execute_search(
            normalized_query, limit, offset, category, min_rank, source_pattern, publication_year, title_pattern
        )

        # Cache results
        if results and redis_client:
            try:
                import json

                serialized_results = [self._serialize_result(r) for r in results]
                await redis_client.setex(cache_key, self.cache_ttl, json.dumps(serialized_results, ensure_ascii=False))
            except Exception:
                pass  # Cache write failed, but search succeeded

        return results

    async def _execute_search(
        self,
        query: str,
        limit: int,
        offset: int,
        category: Optional[str],
        min_rank: float,
        source_pattern: Optional[str] = None,
        publication_year: Optional[int] = None,
        title_pattern: Optional[str] = None,
    ) -> List[SearchResult]:
        """Execute the PostgreSQL full-text search query using strict AND matching"""
        # CRITICAL FIX: Use Python conditionals to build separate SQL for title vs FTS
        # This prevents tsquery evaluation in FROM clause from blocking title ILIKE matching

        if title_pattern:
            # PATH A: Title-based search (NO FTS, no tsquery in FROM clause)
            # This path is triggered for document number queries like "Risoluzione n. 64"
            logger.info(
                "search_path_title_based",
                title_pattern=title_pattern,
                reason="bypassing_fts_for_document_number_search",
            )

            search_query = text(
                """
                WITH search_results AS (
                    SELECT
                        kc.id,
                        ki.title,
                        kc.chunk_text as content,
                        ki.category,
                        ki.source,
                        ki.source_url,
                        ki.relevance_score,
                        ki.updated_at,
                        ki.publication_date,
                        kc.knowledge_item_id,
                        kc.chunk_index,
                        1.0 AS rank,
                        kc.chunk_text AS highlight
                    FROM
                        knowledge_chunks kc
                        JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id
                    WHERE
                        ki.title ILIKE '%' || :title_pattern || '%'
                        AND kc.junk = FALSE
                        AND ki.category = COALESCE(:category, ki.category)
                        AND ki.source LIKE COALESCE(:source_pattern, '%')
                        AND (CAST(:publication_year AS INTEGER) IS NULL OR EXTRACT(YEAR FROM ki.publication_date) = CAST(:publication_year AS INTEGER))
                    ORDER BY
                        ki.relevance_score DESC,
                        kc.chunk_index ASC
                    LIMIT :limit
                    OFFSET :offset
                )
                SELECT * FROM search_results
            """
            )

            # Execute title-based query (no search_term or min_rank needed)
            result = await self.db.execute(
                search_query,
                {
                    "title_pattern": title_pattern,
                    "category": category,
                    "source_pattern": source_pattern,
                    "publication_year": publication_year,
                    "limit": limit,
                    "offset": offset,
                },
            )
        else:
            # PATH B: FTS-based search (standard tsquery logic)
            # This path is triggered for natural language queries like "contratti locazione"
            logger.info("search_path_fts_based", query=query, reason="using_full_text_search")

            search_query = text(
                """
                WITH search_results AS (
                    SELECT
                        kc.id,
                        ki.title,
                        kc.chunk_text as content,
                        ki.category,
                        ki.source,
                        ki.source_url,
                        ki.relevance_score,
                        ki.updated_at,
                        ki.publication_date,
                        kc.knowledge_item_id,
                        kc.chunk_index,
                        ts_rank(kc.search_vector, query, 32) AS rank,
                        ts_headline(
                            'italian',
                            kc.chunk_text,
                            query,
                            'StartSel=<b>, StopSel=</b>, MaxWords=30, MinWords=15'
                        ) AS highlight
                    FROM
                        knowledge_chunks kc
                        JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id,
                        websearch_to_tsquery('italian', :search_term) query
                    WHERE
                        kc.search_vector @@ query
                        AND ts_rank(kc.search_vector, query, 32) >= :min_rank
                        AND kc.junk = FALSE
                        AND ki.category = COALESCE(:category, ki.category)
                        AND ki.source LIKE COALESCE(:source_pattern, '%')
                        AND (CAST(:publication_year AS INTEGER) IS NULL OR EXTRACT(YEAR FROM ki.publication_date) = CAST(:publication_year AS INTEGER))
                    ORDER BY
                        rank DESC,
                        ki.relevance_score DESC,
                        kc.chunk_index ASC
                    LIMIT :limit
                    OFFSET :offset
                )
                SELECT * FROM search_results
            """
            )

            # Execute FTS query
            result = await self.db.execute(
                search_query,
                {
                    "search_term": query,
                    "category": category,
                    "source_pattern": source_pattern,
                    "publication_year": publication_year,
                    "min_rank": min_rank,
                    "limit": limit,
                    "offset": offset,
                },
            )

        rows = result.fetchall()

        # Convert to SearchResult objects
        search_results = []
        for row in rows:
            search_results.append(
                SearchResult(
                    id=str(row.id),
                    title=row.title,
                    content=row.content,
                    category=row.category,
                    rank_score=float(row.rank),
                    relevance_score=float(row.relevance_score),
                    highlight=row.highlight,
                    source=row.source,
                    source_url=row.source_url,
                    updated_at=row.updated_at,
                    knowledge_item_id=row.knowledge_item_id,
                    chunk_index=row.chunk_index,
                    publication_date=row.publication_date,
                )
            )

        # Diagnostic logging for zero results
        if not search_results and query:
            logger.warning(
                "bm25_search_zero_results",
                query=query,
                category=category,
                min_rank=min_rank,
                search_type="strict_AND_websearch_to_tsquery",
                suggestion="Will trigger OR fallback in knowledge_search_service",
            )

        return search_results

    async def search_with_or_fallback(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category: Optional[str] = None,
        min_rank: float = 0.01,
        source_pattern: Optional[str] = None,
        publication_year: Optional[int] = None,
        title_pattern: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Perform full-text search with OR matching (more relaxed than AND).
        Uses plainto_tsquery which creates OR queries for better recall.

        This is typically used as fallback when strict AND search returns no results.

        Args:
            query: Search query string
            limit: Maximum number of results
            offset: Pagination offset
            category: Filter by category
            min_rank: Minimum rank score threshold
            source_pattern: Source filter pattern (for LIKE matching, e.g., "agenzia_entrate%")

        Returns:
            List of SearchResult objects ordered by relevance
        """
        # Clean and validate query
        query = query.strip()
        if not query:
            return []

        # Normalize query for Italian text
        normalized_query = self._normalize_italian_query(query)

        # CRITICAL FIX: Use Python conditionals to build separate SQL for title vs FTS
        # This prevents tsquery evaluation in FROM clause from blocking title ILIKE matching

        if title_pattern:
            # PATH A: Title-based search (NO FTS, no tsquery in FROM clause)
            # This path is triggered for document number queries like "Risoluzione n. 64"
            logger.info(
                "or_fallback_search_path_title_based",
                title_pattern=title_pattern,
                reason="bypassing_fts_for_document_number_search",
            )

            search_query = text(
                """
                WITH search_results AS (
                    SELECT
                        kc.id,
                        ki.title,
                        kc.chunk_text as content,
                        ki.category,
                        ki.source,
                        ki.source_url,
                        ki.relevance_score,
                        ki.updated_at,
                        ki.publication_date,
                        kc.knowledge_item_id,
                        kc.chunk_index,
                        1.0 AS rank,
                        kc.chunk_text AS highlight
                    FROM
                        knowledge_chunks kc
                        JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id
                    WHERE
                        ki.title ILIKE '%' || :title_pattern || '%'
                        AND kc.junk = FALSE
                        AND ki.category = COALESCE(:category, ki.category)
                        AND ki.source LIKE COALESCE(:source_pattern, '%')
                        AND (CAST(:publication_year AS INTEGER) IS NULL OR EXTRACT(YEAR FROM ki.publication_date) = CAST(:publication_year AS INTEGER))
                    ORDER BY
                        ki.relevance_score DESC,
                        kc.chunk_index ASC
                    LIMIT :limit
                    OFFSET :offset
                )
                SELECT * FROM search_results
            """
            )

            # Execute title-based query (no search_term or min_rank needed)
            result = await self.db.execute(
                search_query,
                {
                    "title_pattern": title_pattern,
                    "category": category,
                    "source_pattern": source_pattern,
                    "publication_year": publication_year,
                    "limit": limit,
                    "offset": offset,
                },
            )
        else:
            # PATH B: FTS-based OR search (using plainto_tsquery for better recall)
            # This path is triggered for natural language queries like "contratti locazione"
            logger.info(
                "or_fallback_search_path_fts_based",
                query=normalized_query,
                reason="using_or_fallback_full_text_search",
            )

            search_query = text(
                """
                WITH search_results AS (
                    SELECT
                        kc.id,
                        ki.title,
                        kc.chunk_text as content,
                        ki.category,
                        ki.source,
                        ki.source_url,
                        ki.relevance_score,
                        ki.updated_at,
                        ki.publication_date,
                        kc.knowledge_item_id,
                        kc.chunk_index,
                        ts_rank(kc.search_vector, query, 32) AS rank,
                        ts_headline(
                            'italian',
                            kc.chunk_text,
                            query,
                            'StartSel=<b>, StopSel=</b>, MaxWords=30, MinWords=15'
                        ) AS highlight
                    FROM
                        knowledge_chunks kc
                        JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id,
                        plainto_tsquery('italian', :search_term) query
                    WHERE
                        kc.search_vector @@ query
                        AND ts_rank(kc.search_vector, query, 32) >= :min_rank
                        AND kc.junk = FALSE
                        AND ki.category = COALESCE(:category, ki.category)
                        AND ki.source LIKE COALESCE(:source_pattern, '%')
                        AND (CAST(:publication_year AS INTEGER) IS NULL OR EXTRACT(YEAR FROM ki.publication_date) = CAST(:publication_year AS INTEGER))
                    ORDER BY
                        rank DESC,
                        ki.relevance_score DESC,
                        kc.chunk_index ASC
                    LIMIT :limit
                    OFFSET :offset
                )
                SELECT * FROM search_results
            """
            )

            # Execute OR fallback FTS query
            result = await self.db.execute(
                search_query,
                {
                    "search_term": normalized_query,
                    "category": category,
                    "source_pattern": source_pattern,
                    "publication_year": publication_year,
                    "min_rank": min_rank,
                    "limit": limit,
                    "offset": offset,
                },
            )

        rows = result.fetchall()

        # Convert to SearchResult objects
        search_results = []
        for row in rows:
            search_results.append(
                SearchResult(
                    id=str(row.id),
                    title=row.title,
                    content=row.content,
                    category=row.category,
                    rank_score=float(row.rank),
                    relevance_score=float(row.relevance_score),
                    highlight=row.highlight,
                    source=row.source,
                    source_url=row.source_url,
                    updated_at=row.updated_at,
                    knowledge_item_id=row.knowledge_item_id,
                    chunk_index=row.chunk_index,
                    publication_date=row.publication_date,
                )
            )

        return search_results

    def _normalize_italian_query(self, query: str) -> str:
        """
        Normalize Italian query for better search results.

        - Remove extra whitespace
        - Handle special characters

        Note: We use websearch_to_tsquery which handles natural language queries,
        so we don't add :* prefix matching syntax (that's for to_tsquery only).
        """
        # Remove extra whitespace
        query = " ".join(query.split())

        # Handle dangerous SQL characters (though we use parameterized queries)
        query = re.sub(r"[;\'\"\\]", " ", query)

        return query

    def _serialize_result(self, result: SearchResult) -> dict:
        """Serialize SearchResult for caching"""
        return {
            "id": result.id,
            "title": result.title,
            "content": result.content,
            "category": result.category,
            "rank_score": result.rank_score,
            "relevance_score": result.relevance_score,
            "highlight": result.highlight,
            "source": result.source,
            "source_url": result.source_url,
            "updated_at": result.updated_at.isoformat() if result.updated_at else None,
            "knowledge_item_id": result.knowledge_item_id,
            "chunk_index": result.chunk_index,
            "publication_date": result.publication_date.isoformat() if result.publication_date else None,
        }

    async def update_search_vectors(self, knowledge_ids: Optional[List[str]] = None):
        """
        Manually update search vectors for knowledge items.

        This is typically handled by database triggers, but can be called
        manually for maintenance or bulk updates.
        """
        if knowledge_ids:
            query = text(
                """
                UPDATE knowledge_items
                SET search_vector =
                    setweight(to_tsvector('italian', COALESCE(title, '')), 'A') ||
                    setweight(to_tsvector('italian', COALESCE(content, '')), 'B')
                WHERE id = ANY(:ids)
            """
            )
            await self.db.execute(query, {"ids": knowledge_ids})
        else:
            # Update all records
            query = text(
                """
                UPDATE knowledge_items
                SET search_vector =
                    setweight(to_tsvector('italian', COALESCE(title, '')), 'A') ||
                    setweight(to_tsvector('italian', COALESCE(content, '')), 'B')
            """
            )
            await self.db.execute(query)

        await self.db.commit()

        # Clear search cache after vector update
        await self.cache.clear_cache("search:*")

    async def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """
        Get search suggestions based on partial query.

        Returns common terms from the knowledge base that match the partial query.
        """
        if len(partial_query) < 2:
            return []

        # Cache key for suggestions
        cache_key = f"suggestions:{partial_query.lower()}:{limit}"
        redis_client = await self.cache._get_redis()
        if redis_client:
            try:
                import json

                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            except Exception:
                pass

        # Query for suggestions using ts_stat
        query = text(
            """
            SELECT DISTINCT word
            FROM (
                SELECT word
                FROM ts_stat(
                    'SELECT search_vector FROM knowledge_items'
                )
                WHERE word ILIKE :pattern
                ORDER BY nentry DESC
                LIMIT :limit
            ) suggestions
        """
        )

        result = await self.db.execute(query, {"pattern": f"{partial_query}%", "limit": limit})

        suggestions = [row[0] for row in result]

        # Cache suggestions
        if suggestions and redis_client:
            try:
                import json

                await redis_client.setex(cache_key, 1800, json.dumps(suggestions))  # 30 min cache
            except Exception:
                pass

        return suggestions

    async def clear_search_cache(self):
        """Clear all search-related cache entries"""
        await self.cache.clear_cache("search:*")
        await self.cache.clear_cache("suggestions:*")
