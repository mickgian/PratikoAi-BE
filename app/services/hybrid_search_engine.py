"""
Hybrid Search Engine for Advanced Vector Search Features.

Combines PostgreSQL full-text search with Pinecone vector embeddings
to boost answer quality from 65% to 85%+ with <300ms search latency.
"""

import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.services.embedding_service import EmbeddingService
from app.services.query_normalizer import QueryNormalizer
from app.services.cache import CacheService


@dataclass
class SearchResult:
    """Unified search result from hybrid search"""
    id: str
    content: str
    source_type: str  # 'faq', 'knowledge', 'regulation', 'circular'
    relevance_score: float
    keyword_score: float = 0.0
    vector_score: float = 0.0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class HybridSearchEngine:
    """
    Advanced hybrid search combining keyword and vector search.
    
    Provides sub-300ms search with improved accuracy by combining:
    - PostgreSQL full-text search (keyword matching)
    - Pinecone vector similarity search (semantic matching)
    - Italian query expansion
    - Multi-source result ranking
    """
    
    def __init__(
        self,
        postgres_service: AsyncSession,
        pinecone_service,
        embedding_service: EmbeddingService,
        normalizer: QueryNormalizer,
        cache_service: Optional[CacheService] = None
    ):
        self.postgres = postgres_service
        self.pinecone = pinecone_service
        self.embeddings = embedding_service
        self.normalizer = normalizer
        self.cache = cache_service
        
        # Tunable hybrid search parameters
        self.keyword_weight = 0.4
        self.vector_weight = 0.6
        self.similarity_threshold = 0.75
        self.max_results = 20
        
        # Performance optimization settings
        self.search_timeout_seconds = 0.25  # 250ms timeout
        self.embedding_cache_ttl = 3600  # 1 hour
        self.result_cache_ttl = 1800  # 30 minutes
    
    async def search(
        self,
        query: str,
        search_types: List[str] = ['faq', 'knowledge', 'regulation', 'circular'],
        date_filter: Optional[datetime] = None,
        limit: int = 10,
        use_cache: bool = True
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining keyword and vector search.
        
        Args:
            query: Search query in Italian
            search_types: Types of content to search
            date_filter: Only include content after this date
            limit: Maximum number of results to return
            use_cache: Whether to use cached results
            
        Returns:
            List of SearchResult objects ranked by relevance
        """
        search_start = time.time()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(query, search_types, date_filter, limit)
            if use_cache and self.cache:
                cached_results = await self.cache.get(cache_key)
                if cached_results:
                    logger.debug(f"Cache hit for query: {query[:50]}...")
                    return cached_results
            
            # Normalize and expand query
            normalized_query = await self.normalizer.normalize(query)
            expanded_queries = await self.expand_query(normalized_query)
            
            logger.info(f"Hybrid search: '{query}' -> '{normalized_query}' + {len(expanded_queries)} expansions")
            
            # Execute parallel searches with timeout
            try:
                search_tasks = [
                    asyncio.wait_for(
                        self._keyword_search(normalized_query, expanded_queries, search_types, date_filter),
                        timeout=self.search_timeout_seconds
                    ),
                    asyncio.wait_for(
                        self._vector_search(query, search_types, date_filter),
                        timeout=self.search_timeout_seconds
                    )
                ]
                
                keyword_results, vector_results = await asyncio.gather(
                    *search_tasks,
                    return_exceptions=True
                )
                
                # Handle search failures gracefully
                if isinstance(keyword_results, Exception):
                    logger.warning(f"Keyword search failed: {keyword_results}")
                    keyword_results = []
                
                if isinstance(vector_results, Exception):
                    logger.warning(f"Vector search failed: {vector_results}")
                    vector_results = []
                
            except asyncio.TimeoutError:
                logger.warning(f"Search timeout exceeded for query: {query}")
                return []
            
            # Merge and rank results
            merged_results = self._merge_results(keyword_results, vector_results)
            
            if not merged_results:
                logger.info(f"No results found for query: {query}")
                return []
            
            # Advanced re-ranking
            ranked_results = await self._rerank_results(merged_results, query, normalized_query)
            
            # Limit and finalize results
            final_results = ranked_results[:limit]
            
            # Cache results
            if use_cache and self.cache and final_results:
                await self.cache.setex(cache_key, self.result_cache_ttl, final_results)
            
            search_time = (time.time() - search_start) * 1000
            logger.info(f"Hybrid search completed in {search_time:.1f}ms: {len(final_results)} results")
            
            # Ensure performance requirement
            if search_time > 300:
                logger.warning(f"Search exceeded 300ms target: {search_time:.1f}ms")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed for query '{query}': {e}")
            return []
    
    async def _keyword_search(
        self,
        query: str,
        expanded_queries: List[str],
        search_types: List[str],
        date_filter: Optional[datetime] = None
    ) -> List[Dict]:
        """Execute PostgreSQL full-text search with query expansion"""
        
        try:
            # Build comprehensive search query
            search_terms = [query] + expanded_queries[:5]  # Limit expansions
            
            # Create tsquery with OR conditions for expanded terms
            tsquery_parts = []
            for term in search_terms:
                # Escape special characters and create phrase query
                escaped_term = term.replace("'", "''").replace("&", "").replace("|", "")
                if len(escaped_term.strip()) > 0:
                    tsquery_parts.append(f"'{escaped_term}'")
            
            if not tsquery_parts:
                return []
            
            tsquery = " | ".join(tsquery_parts)
            
            # Build dynamic query based on available sources
            date_clause = "AND updated_at >= :date_filter" if date_filter else ""
            
            search_query = f"""
            WITH search_results AS (
                -- FAQ entries
                SELECT 
                    id,
                    question || ' ' || answer as content,
                    'faq' as source_type,
                    ts_rank_cd(search_vector, to_tsquery('italian', :tsquery)) as rank,
                    category,
                    tags,
                    updated_at,
                    usage_count,
                    quality_score
                FROM faq_entries 
                WHERE search_vector @@ to_tsquery('italian', :tsquery)
                AND 'faq' = ANY(:search_types)
                {date_clause}
                
                UNION ALL
                
                -- Knowledge base articles  
                SELECT
                    id,
                    title || ' ' || content as content,
                    'knowledge' as source_type,
                    ts_rank_cd(search_vector, to_tsquery('italian', :tsquery)) as rank,
                    category,
                    tags,
                    updated_at,
                    view_count as usage_count,
                    confidence_score as quality_score
                FROM knowledge_articles
                WHERE search_vector @@ to_tsquery('italian', :tsquery)
                AND 'knowledge' = ANY(:search_types)
                {date_clause}
                
                UNION ALL
                
                -- Regulatory documents
                SELECT
                    id,
                    title || ' ' || summary as content,
                    'regulation' as source_type,
                    ts_rank_cd(search_vector, to_tsquery('italian', :tsquery)) as rank,
                    document_type as category,
                    subject_tags as tags,
                    publication_date as updated_at,
                    0 as usage_count,
                    1.0 as quality_score
                FROM regulatory_documents
                WHERE search_vector @@ to_tsquery('italian', :tsquery)
                AND 'regulation' = ANY(:search_types)
                {date_clause}
                
                UNION ALL
                
                -- Circulars and interpretations
                SELECT
                    id,
                    title || ' ' || content as content,
                    'circular' as source_type,
                    ts_rank_cd(search_vector, to_tsquery('italian', :tsquery)) as rank,
                    circular_type as category,
                    topics as tags,
                    issue_date as updated_at,
                    0 as usage_count,
                    authority_score as quality_score
                FROM tax_circulars
                WHERE search_vector @@ to_tsquery('italian', :tsquery)
                AND 'circular' = ANY(:search_types)
                {date_clause}
            )
            SELECT 
                id,
                content,
                source_type,
                rank,
                category,
                tags,
                updated_at,
                usage_count,
                quality_score
            FROM search_results
            WHERE rank > 0.1  -- Filter very low relevance
            ORDER BY rank DESC, quality_score DESC
            LIMIT :max_results
            """
            
            # Execute search
            params = {
                'tsquery': tsquery,
                'search_types': search_types,
                'max_results': self.max_results
            }
            
            if date_filter:
                params['date_filter'] = date_filter
            
            result = await self.postgres.execute(text(search_query), params)
            rows = result.fetchall()
            
            # Convert to result format
            keyword_results = []
            for row in rows:
                keyword_results.append({
                    'id': str(row.id),
                    'content': row.content[:1000],  # Truncate long content
                    'source_type': row.source_type,
                    'keyword_score': float(row.rank),
                    'metadata': {
                        'category': row.category,
                        'tags': row.tags or [],
                        'updated_at': row.updated_at.isoformat() if row.updated_at else None,
                        'usage_count': row.usage_count or 0,
                        'quality_score': float(row.quality_score or 0.5)
                    }
                })
            
            logger.debug(f"Keyword search found {len(keyword_results)} results")
            return keyword_results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    async def _vector_search(
        self,
        query: str,
        search_types: List[str],
        date_filter: Optional[datetime] = None
    ) -> List[Dict]:
        """Execute Pinecone vector similarity search"""
        
        try:
            # Generate or retrieve cached embedding
            embedding_cache_key = f"embedding:{hashlib.md5(query.encode()).hexdigest()}"
            
            if self.cache:
                cached_embedding = await self.cache.get(embedding_cache_key)
                if cached_embedding:
                    query_embedding = cached_embedding
                else:
                    query_embedding = await self.embeddings.embed(query)
                    await self.cache.setex(embedding_cache_key, self.embedding_cache_ttl, query_embedding)
            else:
                query_embedding = await self.embeddings.embed(query)
            
            if not query_embedding:
                logger.warning("Failed to generate query embedding")
                return []
            
            # Build metadata filter
            metadata_filter = {"source_type": {"$in": search_types}}
            
            if date_filter:
                metadata_filter["updated_at"] = {
                    "$gte": date_filter.isoformat()
                }
            
            # Execute vector search in Pinecone
            search_results = self.pinecone.query(
                vector=query_embedding,
                top_k=self.max_results,
                include_metadata=True,
                filter=metadata_filter,
                namespace="italian_tax_content"
            )
            
            # Process results
            vector_results = []
            for match in search_results.get('matches', []):
                # Filter by similarity threshold
                if match['score'] < self.similarity_threshold:
                    continue
                
                metadata = match.get('metadata', {})
                
                vector_results.append({
                    'id': match['id'],
                    'content': metadata.get('content', '')[:1000],  # Truncate
                    'source_type': metadata.get('source_type', 'unknown'),
                    'vector_score': float(match['score']),
                    'metadata': {
                        'category': metadata.get('category'),
                        'tags': metadata.get('tags', []),
                        'updated_at': metadata.get('updated_at'),
                        'usage_count': metadata.get('usage_count', 0),
                        'quality_score': metadata.get('quality_score', 0.5),
                        'concepts': metadata.get('concepts', [])
                    }
                })
            
            logger.debug(f"Vector search found {len(vector_results)} results above threshold {self.similarity_threshold}")
            return vector_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _merge_results(
        self,
        keyword_results: List[Dict],
        vector_results: List[Dict]
    ) -> List[SearchResult]:
        """Merge and deduplicate keyword and vector results"""
        
        merged = {}
        
        # Process keyword results
        for result in keyword_results:
            result_id = result['id']
            merged[result_id] = SearchResult(
                id=result_id,
                content=result['content'],
                source_type=result['source_type'],
                keyword_score=result['keyword_score'],
                vector_score=0.0,
                relevance_score=result['keyword_score'] * self.keyword_weight,
                metadata=result['metadata']
            )
        
        # Process vector results and merge with existing
        for result in vector_results:
            result_id = result['id']
            if result_id in merged:
                # Update existing result with vector score
                existing = merged[result_id]
                existing.vector_score = result['vector_score']
                existing.relevance_score = (
                    existing.keyword_score * self.keyword_weight +
                    result['vector_score'] * self.vector_weight
                )
                # Merge metadata
                existing.metadata.update(result['metadata'])
            else:
                # Create new result from vector search
                merged[result_id] = SearchResult(
                    id=result_id,
                    content=result['content'],
                    source_type=result['source_type'],
                    keyword_score=0.0,
                    vector_score=result['vector_score'],
                    relevance_score=result['vector_score'] * self.vector_weight,
                    metadata=result['metadata']
                )
        
        return list(merged.values())
    
    async def _rerank_results(
        self,
        results: List[SearchResult],
        original_query: str,
        normalized_query: str
    ) -> List[SearchResult]:
        """Advanced re-ranking considering multiple factors"""
        
        for result in results:
            # Source type boosting
            source_boost = self._get_source_boost(result.source_type)
            result.relevance_score *= source_boost
            
            # Recency boost for regulations and circulars
            result.relevance_score *= self._get_recency_boost(result)
            
            # Quality boost based on usage and ratings
            result.relevance_score *= self._get_quality_boost(result)
            
            # Content length penalty for very short results
            result.relevance_score *= self._get_length_penalty(result)
            
            # Exact match boost
            result.relevance_score *= self._get_exact_match_boost(result, normalized_query)
        
        # Sort by final relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results
    
    def _get_source_boost(self, source_type: str) -> float:
        """Get relevance boost based on source type"""
        boost_factors = {
            'faq': 1.3,        # FAQs are curated and highly relevant
            'regulation': 1.2,  # Official regulations are authoritative  
            'circular': 1.15,   # Official interpretations
            'knowledge': 1.0    # General knowledge base
        }
        return boost_factors.get(source_type, 1.0)
    
    def _get_recency_boost(self, result: SearchResult) -> float:
        """Get boost based on content recency"""
        
        updated_at = result.metadata.get('updated_at')
        if not updated_at:
            return 1.0
        
        try:
            update_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            days_old = (datetime.now() - update_date).days
            
            # Boost recent regulatory updates
            if result.source_type in ['regulation', 'circular']:
                if days_old < 30:
                    return 1.25
                elif days_old < 90:
                    return 1.15
                elif days_old < 365:
                    return 1.0
                else:
                    return 0.9  # Slight penalty for very old regulations
            
            return 1.0
            
        except (ValueError, TypeError):
            return 1.0
    
    def _get_quality_boost(self, result: SearchResult) -> float:
        """Get boost based on content quality indicators"""
        
        quality_score = result.metadata.get('quality_score', 0.5)
        usage_count = result.metadata.get('usage_count', 0)
        
        # Quality score boost
        quality_boost = min(quality_score / 0.7, 1.3)  # Cap at 1.3x
        
        # Usage popularity boost (for FAQs)
        usage_boost = 1.0
        if result.source_type == 'faq' and usage_count > 0:
            usage_boost = min(1 + (usage_count / 100), 1.2)  # Cap at 1.2x
        
        return quality_boost * usage_boost
    
    def _get_length_penalty(self, result: SearchResult) -> float:
        """Apply penalty for very short content"""
        
        content_length = len(result.content.strip())
        
        if content_length < 50:
            return 0.8  # Penalty for very short content
        elif content_length < 100:
            return 0.9  # Small penalty for short content
        else:
            return 1.0  # No penalty for adequate length
    
    def _get_exact_match_boost(self, result: SearchResult, normalized_query: str) -> float:
        """Boost results with exact phrase matches"""
        
        content_lower = result.content.lower()
        query_lower = normalized_query.lower()
        
        # Check for exact phrase match
        if query_lower in content_lower:
            return 1.2
        
        # Check for word matches
        query_words = query_lower.split()
        content_words = content_lower.split()
        
        if len(query_words) > 1:
            matches = sum(1 for word in query_words if word in content_words)
            match_ratio = matches / len(query_words)
            
            if match_ratio >= 0.8:
                return 1.1
            elif match_ratio >= 0.6:
                return 1.05
        
        return 1.0
    
    async def expand_query(self, query: str, max_expansions: int = 5) -> List[str]:
        """Expand query with Italian tax terminology - placeholder for query expansion service"""
        
        # This will be replaced by the dedicated ItalianTaxQueryExpander
        # For now, provide basic expansion
        
        expansions = []
        
        # Basic Italian tax term expansions
        query_lower = query.lower()
        
        expansion_map = {
            'iva': ['imposta valore aggiunto', 'aliquota iva'],
            'irpef': ['imposta reddito persone fisiche'],
            'partita iva': ['p.iva', 'piva', 'libero professionista'],
            'fattura': ['fatturazione', 'fattura elettronica'],
            'f24': ['modello f24', 'versamento f24'],
            'dichiarazione': ['dichiarazione redditi', 'modello 730'],
            'regime forfettario': ['forfettario', 'regime semplificato']
        }
        
        for term, expansions_list in expansion_map.items():
            if term in query_lower:
                expansions.extend(expansions_list[:2])  # Limit per term
        
        return expansions[:max_expansions]
    
    def _generate_cache_key(
        self,
        query: str,
        search_types: List[str],
        date_filter: Optional[datetime],
        limit: int
    ) -> str:
        """Generate cache key for search results"""
        
        key_parts = [
            query,
            ','.join(sorted(search_types)),
            date_filter.isoformat() if date_filter else 'none',
            str(limit)
        ]
        
        key_string = '|'.join(key_parts)
        return f"hybrid_search:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    async def get_search_statistics(self) -> Dict[str, Any]:
        """Get search performance statistics"""
        
        try:
            if not self.cache:
                return {"error": "Cache service not available"}
            
            # Get cache statistics
            cache_stats = await self.cache.get("search_stats") or {}
            
            return {
                "cache_hit_rate": cache_stats.get("hit_rate", 0.0),
                "avg_search_time_ms": cache_stats.get("avg_time", 0.0),
                "total_searches": cache_stats.get("total", 0),
                "keyword_search_success": cache_stats.get("keyword_success", 0.0),
                "vector_search_success": cache_stats.get("vector_success", 0.0),
                "source_distribution": cache_stats.get("sources", {}),
                "performance_target_met": cache_stats.get("avg_time", 0.0) < 300
            }
            
        except Exception as e:
            logger.error(f"Failed to get search statistics: {e}")
            return {"error": str(e)}
    
    async def tune_parameters(
        self,
        keyword_weight: Optional[float] = None,
        vector_weight: Optional[float] = None,
        similarity_threshold: Optional[float] = None
    ) -> Dict[str, float]:
        """Tune hybrid search parameters"""
        
        if keyword_weight is not None:
            if 0.0 <= keyword_weight <= 1.0:
                self.keyword_weight = keyword_weight
            else:
                raise ValueError("Keyword weight must be between 0 and 1")
        
        if vector_weight is not None:
            if 0.0 <= vector_weight <= 1.0:
                self.vector_weight = vector_weight
            else:
                raise ValueError("Vector weight must be between 0 and 1")
        
        if similarity_threshold is not None:
            if 0.0 <= similarity_threshold <= 1.0:
                self.similarity_threshold = similarity_threshold
            else:
                raise ValueError("Similarity threshold must be between 0 and 1")
        
        # Normalize weights if both provided
        if keyword_weight is not None and vector_weight is not None:
            total_weight = self.keyword_weight + self.vector_weight
            if total_weight > 0:
                self.keyword_weight /= total_weight
                self.vector_weight /= total_weight
        
        logger.info(
            f"Search parameters updated: keyword_weight={self.keyword_weight:.2f}, "
            f"vector_weight={self.vector_weight:.2f}, threshold={self.similarity_threshold:.2f}"
        )
        
        return {
            "keyword_weight": self.keyword_weight,
            "vector_weight": self.vector_weight,
            "similarity_threshold": self.similarity_threshold
        }