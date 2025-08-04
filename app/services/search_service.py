"""
PostgreSQL Full-Text Search Service
Implements efficient text search with Italian language support
"""

import re
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.knowledge import KnowledgeItem
from app.services.cache import cache_service
from app.core.config import settings


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
    updated_at: Optional[datetime] = None


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
        min_rank: float = 0.01
    ) -> List[SearchResult]:
        """
        Perform full-text search on knowledge items.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            offset: Pagination offset
            category: Filter by category
            min_rank: Minimum rank score threshold
            
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
                    return [SearchResult(**r) for r in cached_results]
            except Exception:
                pass  # Cache miss or error, continue with search
        
        # Build and execute search query
        results = await self._execute_search(
            normalized_query, 
            limit, 
            offset, 
            category, 
            min_rank
        )
        
        # Cache results
        if results and redis_client:
            try:
                import json
                serialized_results = [self._serialize_result(r) for r in results]
                await redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(serialized_results, ensure_ascii=False)
                )
            except Exception:
                pass  # Cache write failed, but search succeeded
        
        return results
    
    async def _execute_search(
        self,
        query: str,
        limit: int,
        offset: int,
        category: Optional[str],
        min_rank: float
    ) -> List[SearchResult]:
        """Execute the PostgreSQL full-text search query"""
        # Build the search query with ts_rank
        search_query = text("""
            WITH search_results AS (
                SELECT 
                    ki.id,
                    ki.title,
                    ki.content,
                    ki.category,
                    ki.source,
                    ki.relevance_score,
                    ki.updated_at,
                    ts_rank(ki.search_vector, query, 32) AS rank,
                    ts_headline(
                        'italian',
                        ki.content,
                        query,
                        'StartSel=<b>, StopSel=</b>, MaxWords=30, MinWords=15'
                    ) AS highlight
                FROM 
                    knowledge_items ki,
                    websearch_to_tsquery('italian', :search_term) query
                WHERE 
                    ki.search_vector @@ query
                    AND (:category IS NULL OR ki.category = :category)
                    AND ts_rank(ki.search_vector, query, 32) >= :min_rank
                ORDER BY 
                    rank DESC,
                    ki.relevance_score DESC
                LIMIT :limit
                OFFSET :offset
            )
            SELECT * FROM search_results
        """)
        
        # Execute query
        result = await self.db.execute(
            search_query,
            {
                "search_term": query,
                "category": category,
                "min_rank": min_rank,
                "limit": limit,
                "offset": offset
            }
        )
        
        rows = result.fetchall()
        
        # Convert to SearchResult objects
        search_results = []
        for row in rows:
            search_results.append(SearchResult(
                id=str(row.id),
                title=row.title,
                content=row.content,
                category=row.category,
                rank_score=float(row.rank),
                relevance_score=float(row.relevance_score),
                highlight=row.highlight,
                source=row.source,
                updated_at=row.updated_at
            ))
        
        return search_results
    
    def _normalize_italian_query(self, query: str) -> str:
        """
        Normalize Italian query for better search results.
        
        - Remove extra whitespace
        - Handle special characters
        - Prepare for accent-insensitive search
        """
        # Remove extra whitespace
        query = ' '.join(query.split())
        
        # Handle dangerous SQL characters (though we use parameterized queries)
        query = re.sub(r'[;\'\"\\]', ' ', query)
        
        # For partial matching, we'll use prefix matching in PostgreSQL
        # Add :* to each word for prefix matching if the word is > 2 chars
        words = query.split()
        normalized_words = []
        
        for word in words:
            if len(word) > 2:
                # For partial matching support
                normalized_words.append(f"{word}:*")
            else:
                normalized_words.append(word)
        
        return ' '.join(normalized_words)
    
    def _serialize_result(self, result: SearchResult) -> dict:
        """Serialize SearchResult for caching"""
        return {
            'id': result.id,
            'title': result.title,
            'content': result.content,
            'category': result.category,
            'rank_score': result.rank_score,
            'relevance_score': result.relevance_score,
            'highlight': result.highlight,
            'source': result.source,
            'updated_at': result.updated_at.isoformat() if result.updated_at else None
        }
    
    async def update_search_vectors(self, knowledge_ids: Optional[List[str]] = None):
        """
        Manually update search vectors for knowledge items.
        
        This is typically handled by database triggers, but can be called
        manually for maintenance or bulk updates.
        """
        if knowledge_ids:
            query = text("""
                UPDATE knowledge_items
                SET search_vector = 
                    setweight(to_tsvector('italian', COALESCE(title, '')), 'A') ||
                    setweight(to_tsvector('italian', COALESCE(content, '')), 'B')
                WHERE id = ANY(:ids)
            """)
            await self.db.execute(query, {"ids": knowledge_ids})
        else:
            # Update all records
            query = text("""
                UPDATE knowledge_items
                SET search_vector = 
                    setweight(to_tsvector('italian', COALESCE(title, '')), 'A') ||
                    setweight(to_tsvector('italian', COALESCE(content, '')), 'B')
            """)
            await self.db.execute(query)
        
        await self.db.commit()
        
        # Clear search cache after vector update
        await self.cache.clear_cache("search:*")
    
    async def get_search_suggestions(
        self, 
        partial_query: str, 
        limit: int = 5
    ) -> List[str]:
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
        query = text("""
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
        """)
        
        result = await self.db.execute(
            query,
            {
                "pattern": f"{partial_query}%",
                "limit": limit
            }
        )
        
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