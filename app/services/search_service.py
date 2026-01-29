"""PostgreSQL Full-Text Search Service
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

# DEV-242 Phase 7: Topic-based synonym expansion for FTS
# Maps colloquial tax terms to their ACTUAL legal equivalents found in law text
# NOTE: Phrases like "definizione agevolata" work because FTS matches individual terms
# DEV-XXX: Simplified to broad categories for scalability
TOPIC_SYNONYMS = {
    # Broad category for fiscal amnesty procedures
    "rottamazione": [
        "definizione agevolata",  # DEV-250: Exact phrase from LEGGE 199/2025
        "definizione",  # Generic term used in all rottamazione/sanatoria laws
        "pace fiscale",
        "pacificazione",
        "stralcio",
    ],
    "saldo e stralcio": [
        "definizione agevolata",  # DEV-250: Exact phrase from law text
        "definizione",
        "stralcio debiti",
    ],
}


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
    source: str | None = None
    source_url: str | None = None
    updated_at: datetime | None = None
    knowledge_item_id: int | None = None  # Parent document ID for chunks
    chunk_index: int | None = None  # Chunk position in document
    publication_date: date | None = None  # Publication date from RSS/database


class SearchService:
    """PostgreSQL Full-Text Search service with Italian language support.

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
        category: str | None = None,
        min_rank: float = 0.01,
        source_pattern: str | None = None,
        publication_year: int | None = None,
        title_patterns: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> list[SearchResult]:
        """Perform full-text search on knowledge items.

        Args:
            query: Search query string
            limit: Maximum number of results
            offset: Pagination offset
            category: Filter by category
            min_rank: Minimum rank score threshold
            source_pattern: Source filter pattern (for LIKE matching, e.g., "agenzia_entrate%")
            publication_year: Filter by publication year (e.g., 2025)
            title_patterns: List of title filter patterns (for ILIKE matching on document numbers,
                           e.g., ["n. 64", "numero 64", "risoluzione n. 64"]). Uses OR for multiple.
            topics: List of topic tags to filter by (uses GIN index with && overlap operator).
                   Documents matching ANY of the topics will be returned.

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
        # FIX: Include source_pattern, publication_year, and topics in cache key to avoid incorrect cache hits
        topics_key = ",".join(sorted(topics)) if topics else ""
        cache_key = (
            f"search:{normalized_query}:{category}:{source_pattern}:{publication_year}:{topics_key}:{limit}:{offset}"
        )
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
            normalized_query,
            limit,
            offset,
            category,
            min_rank,
            source_pattern,
            publication_year,
            title_patterns,
            topics,
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
        category: str | None,
        min_rank: float,
        source_pattern: str | None = None,
        publication_year: int | None = None,
        title_patterns: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> list[SearchResult]:
        """Execute the PostgreSQL full-text search query using strict AND matching"""
        # CRITICAL FIX: Use Python conditionals to build separate SQL for title vs FTS
        # This prevents tsquery evaluation in FROM clause from blocking title ILIKE matching

        if title_patterns:
            # PATH A: Title-based search with FTS ranking (DEV-242 Phase 8)
            # Filters by title ILIKE, but ALSO applies FTS ranking to prioritize
            # query-relevant chunks instead of just returning from document start.
            logger.info(
                "search_path_title_based_with_fts",
                title_patterns=title_patterns,
                patterns_count=len(title_patterns),
                search_term=query[:100] if query else "",
                reason="title_filter_with_fts_ranking",
            )

            # Build dynamic OR conditions for title patterns (max 7 patterns)
            patterns_to_use = title_patterns[:7]
            pattern_conditions = " OR ".join(
                [f"ki.title ILIKE '%' || :pattern_{i} || '%'" for i in range(len(patterns_to_use))]
            )

            # DEV-242 Phase 8: Add FTS ranking within title-filtered results
            # This ensures chunks containing query terms (e.g., "definizione", "comma 82")
            # are prioritized over chunks from the beginning of the document.
            # CRITICAL: Use OR logic (|) not AND (&) because we want to rank by ANY matching term,
            # not require ALL terms to match. The document is already filtered by title.
            search_query = text(
                rf"""
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
                        -- DEV-242 Phase 8: FTS rank using OR logic for query-relevant chunks
                        -- Convert "term1 term2" to "term1 | term2" for OR matching
                        ts_rank(
                            kc.search_vector,
                            to_tsquery('italian', regexp_replace(:search_term, '\s+', ' | ', 'g')),
                            32
                        ) AS rank,
                        CASE
                            WHEN kc.search_vector @@ to_tsquery('italian', regexp_replace(:search_term, '\s+', ' | ', 'g'))
                            THEN ts_headline(
                                'italian',
                                kc.chunk_text,
                                to_tsquery('italian', regexp_replace(:search_term, '\s+', ' | ', 'g')),
                                'StartSel=<b>, StopSel=</b>, MaxWords=30, MinWords=15'
                            )
                            ELSE LEFT(kc.chunk_text, 2000)  -- DEV-242 Phase 14A: 10x increase to preserve specific values
                        END AS highlight
                    FROM
                        knowledge_chunks kc
                        JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id
                    WHERE
                        ({pattern_conditions})
                        AND kc.junk = FALSE
                        AND ki.category = COALESCE(:category, ki.category)
                        AND ki.source LIKE COALESCE(:source_pattern, '%')
                        AND (CAST(:publication_year AS INTEGER) IS NULL
                             OR EXTRACT(YEAR FROM ki.publication_date) = CAST(:publication_year AS INTEGER)
                             OR ki.publication_date IS NULL)
                        AND (CARDINALITY(CAST(:topics_filter AS text[])) = 0 OR ki.topics && CAST(:topics_filter AS text[]))
                    ORDER BY
                        -- DEV-242 Phase 8: FTS rank first, then fallback to chunk_index
                        rank DESC,
                        ki.relevance_score DESC,
                        kc.chunk_index ASC,
                        kc.id ASC  -- DEV-244: Deterministic tie-breaker (primary key)
                    LIMIT :limit
                    OFFSET :offset
                )
                SELECT * FROM search_results
            """
            )

            # Build params dict with pattern_0, pattern_1, etc.
            params = {
                "search_term": query,  # DEV-242 Phase 8: Add search term for FTS ranking
                "category": category,
                "source_pattern": source_pattern,
                "publication_year": publication_year,
                "topics_filter": topics or [],  # Always pass array (empty if no topics)
                "limit": limit,
                "offset": offset,
            }
            for i, pattern in enumerate(patterns_to_use):
                params[f"pattern_{i}"] = pattern

            # Execute title-based query with FTS ranking
            result = await self.db.execute(search_query, params)
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
                        -- DEV-242: CASE for topic-only matches (no FTS rank)
                        CASE
                            WHEN kc.search_vector @@ query THEN ts_rank(kc.search_vector, query, 32)
                            ELSE 0.8  -- Topic-match default rank (high priority)
                        END AS rank,
                        CASE
                            WHEN kc.search_vector @@ query THEN ts_headline(
                                'italian',
                                kc.chunk_text,
                                query,
                                'StartSel=<b>, StopSel=</b>, MaxWords=30, MinWords=15'
                            )
                            ELSE LEFT(kc.chunk_text, 2000)  -- DEV-242 Phase 14A: 10x increase to preserve specific values  -- No highlight for topic-only
                        END AS highlight
                    FROM
                        knowledge_chunks kc
                        JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id,
                        websearch_to_tsquery('italian', :search_term) query
                    WHERE
                        -- DEV-242: FTS OR topic match (topics as alternative path)
                        (
                            kc.search_vector @@ query
                            OR (CARDINALITY(CAST(:topics_filter AS text[])) > 0 AND ki.topics && CAST(:topics_filter AS text[]))
                        )
                        -- Rank filter: apply only to FTS matches
                        AND (
                            NOT (kc.search_vector @@ query)
                            OR ts_rank(kc.search_vector, query, 32) >= :min_rank
                        )
                        AND kc.junk = FALSE
                        AND ki.category = COALESCE(:category, ki.category)
                        AND ki.source LIKE COALESCE(:source_pattern, '%')
                        AND (CAST(:publication_year AS INTEGER) IS NULL OR EXTRACT(YEAR FROM ki.publication_date) = CAST(:publication_year AS INTEGER))
                    ORDER BY
                        rank DESC,
                        ki.relevance_score DESC,
                        kc.chunk_index ASC,
                        kc.id ASC  -- DEV-244: Deterministic tie-breaker (primary key)
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
                    "topics_filter": topics or [],  # Always pass array (empty if no topics)
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
        category: str | None = None,
        min_rank: float = 0.01,
        source_pattern: str | None = None,
        publication_year: int | None = None,
        title_patterns: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> list[SearchResult]:
        """Perform full-text search with true OR matching (more relaxed than AND).

        DEV-244 FIX: Uses to_tsquery with | operator for TRUE OR matching.
        Previous implementation incorrectly used plainto_tsquery which still uses AND logic.

        This is typically used as fallback when strict AND search returns no results.

        Args:
            query: Search query string
            limit: Maximum number of results
            offset: Pagination offset
            category: Filter by category
            min_rank: Minimum rank score threshold
            source_pattern: Source filter pattern (for LIKE matching, e.g., "agenzia_entrate%")
            title_patterns: List of title filter patterns (for ILIKE matching on document numbers).
            topics: List of topic tags to filter by (uses GIN index with && overlap operator).

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

        if title_patterns:
            # PATH A: Title-based search with FTS ranking (DEV-242 Phase 8)
            # Filters by title ILIKE, but ALSO applies FTS ranking to prioritize
            # query-relevant chunks instead of just returning from document start.
            logger.info(
                "or_fallback_search_path_title_based_with_fts",
                title_patterns=title_patterns,
                patterns_count=len(title_patterns),
                search_term=normalized_query[:100] if normalized_query else "",
                reason="title_filter_with_fts_ranking",
            )

            # Build dynamic OR conditions for title patterns (max 7 patterns)
            patterns_to_use = title_patterns[:7]
            pattern_conditions = " OR ".join(
                [f"ki.title ILIKE '%' || :pattern_{i} || '%'" for i in range(len(patterns_to_use))]
            )

            # DEV-242 Phase 8: Add FTS ranking within title-filtered results
            # CRITICAL: Use OR logic (|) not AND (&) for ranking - document already filtered by title
            search_query = text(
                rf"""
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
                        -- DEV-242 Phase 8: FTS rank using OR logic for query-relevant chunks
                        ts_rank(
                            kc.search_vector,
                            to_tsquery('italian', regexp_replace(:search_term, '\s+', ' | ', 'g')),
                            32
                        ) AS rank,
                        CASE
                            WHEN kc.search_vector @@ to_tsquery('italian', regexp_replace(:search_term, '\s+', ' | ', 'g'))
                            THEN ts_headline(
                                'italian',
                                kc.chunk_text,
                                to_tsquery('italian', regexp_replace(:search_term, '\s+', ' | ', 'g')),
                                'StartSel=<b>, StopSel=</b>, MaxWords=30, MinWords=15'
                            )
                            ELSE LEFT(kc.chunk_text, 2000)  -- DEV-242 Phase 14A: 10x increase to preserve specific values
                        END AS highlight
                    FROM
                        knowledge_chunks kc
                        JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id
                    WHERE
                        ({pattern_conditions})
                        AND kc.junk = FALSE
                        AND ki.category = COALESCE(:category, ki.category)
                        AND ki.source LIKE COALESCE(:source_pattern, '%')
                        AND (CAST(:publication_year AS INTEGER) IS NULL
                             OR EXTRACT(YEAR FROM ki.publication_date) = CAST(:publication_year AS INTEGER)
                             OR ki.publication_date IS NULL)
                        AND (CARDINALITY(CAST(:topics_filter AS text[])) = 0 OR ki.topics && CAST(:topics_filter AS text[]))
                    ORDER BY
                        -- DEV-242 Phase 8: FTS rank first, then fallback to chunk_index
                        rank DESC,
                        ki.relevance_score DESC,
                        kc.chunk_index ASC,
                        kc.id ASC  -- DEV-244: Deterministic tie-breaker (primary key)
                    LIMIT :limit
                    OFFSET :offset
                )
                SELECT * FROM search_results
            """
            )

            # Build params dict with pattern_0, pattern_1, etc.
            params = {
                "search_term": normalized_query,  # DEV-242 Phase 8: Add search term for FTS ranking
                "category": category,
                "source_pattern": source_pattern,
                "publication_year": publication_year,
                "topics_filter": topics or [],  # Always pass array (empty if no topics)
                "limit": limit,
                "offset": offset,
            }
            for i, pattern in enumerate(patterns_to_use):
                params[f"pattern_{i}"] = pattern

            # Execute title-based query with FTS ranking
            result = await self.db.execute(search_query, params)
        else:
            # PATH B: FTS-based OR search (using to_tsquery with | for true OR matching)
            # This path is triggered for natural language queries like "contratti locazione"
            # DEV-244 FIX: plainto_tsquery uses AND logic, not OR! We must use to_tsquery
            # with regexp_replace to convert "term1 term2" to "term1 | term2" for OR matching.
            logger.info(
                "or_fallback_search_path_fts_based",
                query=normalized_query,
                reason="using_or_fallback_full_text_search",
            )

            search_query = text(
                r"""
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
                        -- DEV-244 FIX: Use OR tsquery for ranking
                        CASE
                            WHEN kc.search_vector @@ query THEN ts_rank(kc.search_vector, query, 32)
                            ELSE 0.8  -- Topic-match default rank (high priority)
                        END AS rank,
                        CASE
                            WHEN kc.search_vector @@ query THEN ts_headline(
                                'italian',
                                kc.chunk_text,
                                query,
                                'StartSel=<b>, StopSel=</b>, MaxWords=30, MinWords=15'
                            )
                            ELSE LEFT(kc.chunk_text, 2000)
                        END AS highlight
                    FROM
                        knowledge_chunks kc
                        JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id,
                        -- DEV-244 FIX: Use to_tsquery with | (OR) instead of plainto_tsquery (AND)
                        -- regexp_replace converts "term1 term2 term3" to "term1 | term2 | term3"
                        to_tsquery('italian', regexp_replace(:search_term, '\s+', ' | ', 'g')) query
                    WHERE
                        -- DEV-244 FIX: OR matching - document matches if ANY term is present
                        (
                            kc.search_vector @@ query
                            OR (CARDINALITY(CAST(:topics_filter AS text[])) > 0 AND ki.topics && CAST(:topics_filter AS text[]))
                        )
                        -- Rank filter: apply only to FTS matches
                        AND (
                            NOT (kc.search_vector @@ query)
                            OR ts_rank(kc.search_vector, query, 32) >= :min_rank
                        )
                        AND kc.junk = FALSE
                        AND ki.category = COALESCE(:category, ki.category)
                        AND ki.source LIKE COALESCE(:source_pattern, '%')
                        AND (CAST(:publication_year AS INTEGER) IS NULL OR EXTRACT(YEAR FROM ki.publication_date) = CAST(:publication_year AS INTEGER))
                    ORDER BY
                        rank DESC,
                        ki.relevance_score DESC,
                        kc.chunk_index ASC,
                        kc.id ASC  -- DEV-244: Deterministic tie-breaker (primary key)
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
                    "topics_filter": topics or [],  # Always pass array (empty if no topics)
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
        """Normalize Italian query for better search results.

        - Remove extra whitespace
        - Handle special characters
        - DEV-242 Phase 6: Expand colloquial tax terms with legal synonyms for FTS

        Note: We use websearch_to_tsquery which handles natural language queries,
        so we don't add :* prefix matching syntax (that's for to_tsquery only).
        """
        # DEV-242 DEBUG: Log input query to trace expansion
        logger.info(
            "normalize_italian_query_entry",
            input_query=query[:200] if query else "EMPTY",
            query_length=len(query) if query else 0,
        )

        # Remove extra whitespace
        query = " ".join(query.split())

        # Handle dangerous SQL characters (though we use parameterized queries)
        query = re.sub(r"[;\'\"\\]", " ", query)

        # DEV-242 Phase 6: Synonym expansion for FTS
        # Critical fix: Italian laws use "definizione agevolata" instead of "rottamazione"
        # Without this expansion, FTS returns 0 results for "rottamazione" queries
        query_lower = query.lower()
        synonyms_to_add = []

        # Check longer phrases first (more specific), then shorter ones
        for term, synonyms in sorted(TOPIC_SYNONYMS.items(), key=lambda x: -len(x[0])):
            if term in query_lower:
                # Add first 2 synonyms to avoid query explosion
                synonyms_to_add.extend(synonyms[:2])
                logger.info(
                    "synonym_expansion_triggered",
                    original_query=query[:100],
                    matched_term=term,
                    added_synonyms=synonyms[:2],
                    reason="dev_242_phase6_fts_fix",
                )
                break  # Only expand first match to avoid bloated queries

        if synonyms_to_add:
            # Append synonyms to original query (websearch_to_tsquery will OR them)
            expanded_query = f"{query} {' '.join(synonyms_to_add)}"
            logger.info(
                "query_expanded_with_synonyms",
                original=query[:100],
                expanded=expanded_query[:200],
                synonyms_added=len(synonyms_to_add),
            )
            return expanded_query

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

    async def update_search_vectors(self, knowledge_ids: list[str] | None = None):
        """Manually update search vectors for knowledge items.

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

    async def get_search_suggestions(self, partial_query: str, limit: int = 5) -> list[str]:
        """Get search suggestions based on partial query.

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
                from typing import cast

                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    return cast(list[str], json.loads(cached_data))
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
