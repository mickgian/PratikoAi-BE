"""Expert FAQ Retrieval Service - Performance Optimized Version.

Provides semantic search over approved expert FAQ candidates using pgvector
with Redis caching for embeddings and results.

Performance Optimizations:
- Redis caching for OpenAI embeddings (reduces API calls by 95%+)
- Redis caching for FAQ search results (5-minute TTL)
- Batch embedding generation for multiple queries
- Prometheus metrics for monitoring
- Query optimization with proper indexes

Performance Targets:
- p50 latency: <20ms (cache hit)
- p95 latency: <50ms (embedding cached, search executed)
- p99 latency: <100ms (cold cache)
- Cache hit rate: >80%
"""

import hashlib
import json
import logging
import re
import time
from typing import Dict, List, Optional

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from prometheus_client import Counter, Histogram

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from app.core.config import settings
from app.core.embed import generate_embedding, generate_embeddings_batch
from app.models.faq_automation import FAQCandidate

logger = logging.getLogger(__name__)

# Prometheus metrics (if available)
if PROMETHEUS_AVAILABLE:
    faq_retrieval_latency = Histogram(
        "faq_retrieval_latency_seconds", "FAQ retrieval latency", ["cache_status", "similarity_threshold"]
    )

    faq_cache_hits = Counter("faq_cache_hits_total", "FAQ cache hits by type", ["cache_type"])

    faq_cache_misses = Counter("faq_cache_misses_total", "FAQ cache misses by type", ["cache_type"])

    faq_embedding_generation_latency = Histogram(
        "faq_embedding_generation_seconds", "Time to generate embeddings via OpenAI API"
    )


class ExpertFAQRetrievalServiceOptimized:
    """Performance-optimized service for retrieving expert FAQ candidates.

    Uses pgvector for efficient cosine similarity queries over question embeddings.
    Implements Redis caching for both embeddings and search results.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize the retrieval service.

        Args:
            db_session: Async SQLAlchemy session for database operations
        """
        self.db = db_session
        self._redis_client: redis.Redis | None = None
        self._redis_available = REDIS_AVAILABLE and settings.CACHE_ENABLED

        # Cache TTLs (configurable via settings)
        self.embedding_cache_ttl = getattr(settings, "FAQ_EMBEDDING_CACHE_TTL", 3600)  # 1 hour
        self.result_cache_ttl = getattr(settings, "FAQ_RESULT_CACHE_TTL", 300)  # 5 minutes

        # Default search parameters
        self.default_min_similarity = getattr(settings, "FAQ_MIN_SIMILARITY", 0.85)
        self.default_max_results = getattr(settings, "FAQ_MAX_RESULTS", 10)

        logger.info(
            "ExpertFAQRetrievalServiceOptimized initialized",
            extra={
                "redis_available": self._redis_available,
                "embedding_cache_ttl": self.embedding_cache_ttl,
                "result_cache_ttl": self.result_cache_ttl,
            },
        )

    async def _get_redis(self) -> redis.Redis | None:
        """Get Redis connection with connection pooling.

        Returns:
            Redis connection or None if Redis is unavailable
        """
        if not self._redis_available:
            return None

        if self._redis_client is None:
            try:
                self._redis_client = await redis.from_url(
                    settings.REDIS_URL,
                    password=settings.REDIS_PASSWORD or None,
                    db=settings.REDIS_DB,
                    max_connections=settings.REDIS_MAX_CONNECTIONS,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    decode_responses=False,  # We'll handle JSON encoding/decoding
                )

                # Test connection
                await self._redis_client.ping()
                logger.info("Redis connection established for FAQ retrieval service")

            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. FAQ caching disabled.", extra={"error": str(e)})
                self._redis_available = False
                return None

        return self._redis_client

    async def find_matching_faqs(
        self, query: str, min_similarity: float | None = None, max_results: int | None = None
    ) -> list[dict]:
        """Find FAQ candidates that semantically match the query.

        Performs semantic similarity search using pgvector cosine similarity with
        Redis caching for both embeddings and results.

        Args:
            query: User's question text
            min_similarity: Minimum cosine similarity threshold (0.0-1.0)
            max_results: Maximum number of results to return

        Returns:
            List of FAQ dictionaries with question, answer, similarity score.
            Sorted by similarity descending.

        Example:
            >>> service = ExpertFAQRetrievalServiceOptimized(db)
            >>> faqs = await service.find_matching_faqs("Cos'è l'IVA?")
            >>> print(faqs[0]['similarity_score'])  # 0.92
        """
        start_time = time.time()
        cache_status = "miss"

        # Use defaults if not provided
        if min_similarity is None:
            min_similarity = self.default_min_similarity
        if max_results is None:
            max_results = self.default_max_results

        # Handle empty queries
        if not query or not query.strip():
            logger.debug("Empty query provided, returning no results")
            return []

        try:
            # Try result cache first (fastest path)
            cached_results = await self._get_cached_results(query, min_similarity, max_results)
            if cached_results is not None:
                cache_status = "result_hit"
                if PROMETHEUS_AVAILABLE:
                    faq_cache_hits.labels(cache_type="result").inc()

                logger.info(
                    f"FAQ result cache HIT for query: {query[:50]}",
                    extra={
                        "cache_status": "result_hit",
                        "results_count": len(cached_results),
                        "latency_ms": (time.time() - start_time) * 1000,
                    },
                )

                if PROMETHEUS_AVAILABLE:
                    latency = time.time() - start_time
                    faq_retrieval_latency.labels(
                        cache_status="result_hit", similarity_threshold=min_similarity
                    ).observe(latency)

                return cached_results

            if PROMETHEUS_AVAILABLE:
                faq_cache_misses.labels(cache_type="result").inc()

            # Generate embedding for query (with caching)
            query_embedding = await self._generate_embedding_cached(query)

            if not query_embedding:
                logger.warning(f"Failed to generate embedding for query: {query[:50]}")
                return []

            # Perform semantic search with entity validation
            results = await self._semantic_search(
                query_embedding=query_embedding, min_similarity=min_similarity, max_results=max_results, query=query
            )

            # Cache results for future queries
            await self._cache_results(query, min_similarity, max_results, results)

            cache_status = "embedding_hit" if self._redis_available else "miss"

            latency = time.time() - start_time
            logger.info(
                f"FAQ search completed: {len(results)} results in {latency*1000:.2f}ms",
                extra={
                    "query_preview": query[:50],
                    "cache_status": cache_status,
                    "results_count": len(results),
                    "latency_ms": latency * 1000,
                    "min_similarity": min_similarity,
                },
            )

            if PROMETHEUS_AVAILABLE:
                faq_retrieval_latency.labels(cache_status=cache_status, similarity_threshold=min_similarity).observe(
                    latency
                )

            return results

        except Exception as e:
            logger.error(
                f"Error finding matching FAQs: {e}",
                exc_info=True,
                extra={"query_preview": query[:50] if query else None},
            )
            return []

    async def _get_cached_results(self, query: str, min_similarity: float, max_results: int) -> list[dict] | None:
        """Try to retrieve cached FAQ results.

        Args:
            query: User's question text
            min_similarity: Similarity threshold used
            max_results: Max results requested

        Returns:
            Cached results or None if cache miss
        """
        redis_client = await self._get_redis()
        if not redis_client:
            return None

        try:
            cache_key = self._generate_result_cache_key(query, min_similarity, max_results)
            cached_data = await redis_client.get(cache_key)

            if cached_data:
                results = json.loads(cached_data)
                logger.debug(f"FAQ result cache HIT: {cache_key[:32]}...")
                return results

            logger.debug(f"FAQ result cache MISS: {cache_key[:32]}...")
            return None

        except Exception as e:
            logger.warning(f"Error reading FAQ result cache: {e}")
            return None

    async def _cache_results(self, query: str, min_similarity: float, max_results: int, results: list[dict]) -> None:
        """Cache FAQ search results.

        Args:
            query: User's question text
            min_similarity: Similarity threshold used
            max_results: Max results requested
            results: Results to cache
        """
        redis_client = await self._get_redis()
        if not redis_client:
            return

        try:
            cache_key = self._generate_result_cache_key(query, min_similarity, max_results)
            cached_data = json.dumps(results)

            await redis_client.setex(cache_key, self.result_cache_ttl, cached_data)

            logger.debug(
                f"FAQ results cached: {cache_key[:32]}... TTL={self.result_cache_ttl}s",
                extra={"results_count": len(results)},
            )

        except Exception as e:
            logger.warning(f"Error caching FAQ results: {e}")

    def _generate_result_cache_key(self, query: str, min_similarity: float, max_results: int) -> str:
        """Generate cache key for FAQ search results.

        Args:
            query: User's question text
            min_similarity: Similarity threshold
            max_results: Max results

        Returns:
            Cache key string
        """
        # Include query hash, similarity threshold, and max results
        query_hash = hashlib.sha256(query.strip().lower().encode()).hexdigest()
        return f"faq_result:v1:{query_hash}:{min_similarity:.2f}:{max_results}"

    async def _generate_embedding_cached(self, text: str) -> list[float] | None:
        """Generate vector embedding with Redis caching.

        Args:
            text: Text to embed (typically a question)

        Returns:
            Vector of 1536 dimensions (OpenAI ada-002), or None if generation fails
        """
        # Check Redis cache first
        redis_client = await self._get_redis()
        if redis_client:
            try:
                cache_key = self._generate_embedding_cache_key(text)
                cached_embedding = await redis_client.get(cache_key)

                if cached_embedding:
                    embedding = json.loads(cached_embedding)
                    logger.debug(f"Embedding cache HIT: {cache_key[:32]}...")

                    if PROMETHEUS_AVAILABLE:
                        faq_cache_hits.labels(cache_type="embedding").inc()

                    return embedding

                if PROMETHEUS_AVAILABLE:
                    faq_cache_misses.labels(cache_type="embedding").inc()

            except Exception as e:
                logger.warning(f"Error reading embedding cache: {e}")

        # Generate new embedding
        start_time = time.time()

        try:
            embedding = await generate_embedding(text)

            if PROMETHEUS_AVAILABLE:
                latency = time.time() - start_time
                faq_embedding_generation_latency.observe(latency)

            if not embedding:
                logger.warning(f"Embedding generation returned None for text: {text[:50]}")
                return None

            # Validate embedding dimension
            if len(embedding) != 1536:
                logger.error(
                    f"Invalid embedding dimension: {len(embedding)}, expected 1536", extra={"text_preview": text[:50]}
                )
                return None

            # Cache for future use
            if redis_client:
                try:
                    cache_key = self._generate_embedding_cache_key(text)
                    await redis_client.setex(cache_key, self.embedding_cache_ttl, json.dumps(embedding))
                    logger.debug(f"Embedding cached: {cache_key[:32]}... TTL={self.embedding_cache_ttl}s")
                except Exception as e:
                    logger.warning(f"Error caching embedding: {e}")

            logger.debug(
                "Generated embedding successfully",
                extra={
                    "text_preview": text[:50],
                    "embedding_dim": len(embedding),
                    "generation_time_ms": (time.time() - start_time) * 1000,
                },
            )

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}", exc_info=True, extra={"text_preview": text[:50]})
            return None

    def _generate_embedding_cache_key(self, text: str) -> str:
        """Generate cache key for embeddings.

        Args:
            text: Text to embed

        Returns:
            Cache key string
        """
        text_hash = hashlib.sha256(text.strip().encode()).hexdigest()
        return f"embedding:v1:{text_hash}"

    def _extract_entities(self, text: str) -> dict[str, set[str]]:
        """Extract key entities from text for validation.

        Extracts:
        - document_numbers: risoluzione 63, circolare 12, etc.
        - years: 2024, 2025, etc.
        - article_numbers: art. 1, articolo 12, etc.
        - decree_numbers: decreto 123, DL 45, etc.

        Args:
            text: Text to extract entities from

        Returns:
            Dict with entity type as key and set of extracted values.
        """
        text_lower = text.lower()
        entities: dict[str, set[str]] = {
            "document_numbers": set(),
            "years": set(),
            "article_numbers": set(),
            "decree_numbers": set(),
        }

        # Document numbers (risoluzione, circolare, interpello)
        doc_patterns = [
            r"risoluzione\s*(?:n\.?\s*)?(\d+)",
            r"circolare\s*(?:n\.?\s*)?(\d+)",
            r"interpello\s*(?:n\.?\s*)?(\d+)",
        ]
        for pattern in doc_patterns:
            for match in re.finditer(pattern, text_lower):
                entities["document_numbers"].add(match.group(1))

        # Years (4 digits, 2020-2030 range for relevance)
        year_pattern = r"\b(202[0-9]|2030)\b"
        for match in re.finditer(year_pattern, text_lower):
            entities["years"].add(match.group(1))

        # Article numbers
        article_patterns = [
            r"(?:art\.?|articolo)\s*(\d+)",
            r"comma\s*(\d+)",
        ]
        for pattern in article_patterns:
            for match in re.finditer(pattern, text_lower):
                entities["article_numbers"].add(match.group(1))

        # Decree numbers
        decree_patterns = [
            r"(?:decreto|d\.?l\.?|d\.?lgs\.?)\s*(?:n\.?\s*)?(\d+)",
        ]
        for pattern in decree_patterns:
            for match in re.finditer(pattern, text_lower):
                entities["decree_numbers"].add(match.group(1))

        return entities

    def _validate_entity_match(self, query: str, faq_question: str) -> bool:
        """Validate that key entities match between query and FAQ.

        Rules:
        - If query contains specific entities, FAQ must contain the SAME entities
        - Empty entity sets are ignored (no constraint)
        - All non-empty entity types must have at least one matching value

        Args:
            query: User's question
            faq_question: Stored FAQ question

        Returns:
            True if entities match (or no entities in query), False otherwise
        """
        query_entities = self._extract_entities(query)
        faq_entities = self._extract_entities(faq_question)

        # Check each entity type
        for entity_type, query_values in query_entities.items():
            if not query_values:
                # No entities of this type in query - skip
                continue

            faq_values = faq_entities.get(entity_type, set())

            if not faq_values:
                # Query has entities but FAQ doesn't - reject
                logger.debug(f"Entity mismatch: query has {entity_type}={query_values} but FAQ has none")
                return False

            # Check if ANY query entity matches ANY FAQ entity
            if not query_values.intersection(faq_values):
                # No overlap - reject
                logger.debug(f"Entity mismatch: query {entity_type}={query_values} vs FAQ {entity_type}={faq_values}")
                return False

        return True

    async def _semantic_search(
        self, query_embedding: list[float], min_similarity: float, max_results: int, query: str = ""
    ) -> list[dict]:
        """Perform semantic similarity search using pgvector.

        Args:
            query_embedding: Query vector (1536 dimensions)
            min_similarity: Minimum cosine similarity threshold
            max_results: Maximum results to return
            query: Original query text for entity validation

        Returns:
            List of FAQ dictionaries sorted by similarity
        """
        try:
            # Build optimized SQL query with pgvector similarity
            # Note: <=> operator returns cosine distance (1 - cosine similarity)
            stmt = (
                select(
                    FAQCandidate.id,
                    FAQCandidate.suggested_question,
                    FAQCandidate.best_response_content,
                    FAQCandidate.suggested_category,
                    FAQCandidate.regulatory_references,
                    FAQCandidate.priority_score,
                    FAQCandidate.status,
                    # Calculate similarity: 1 - cosine_distance
                    (1 - FAQCandidate.question_embedding.cosine_distance(query_embedding)).label("similarity"),
                )
                .where(
                    # Only return approved FAQs
                    FAQCandidate.status.in_(["auto_approved", "manually_approved"]),
                    # Ensure embedding exists
                    FAQCandidate.question_embedding.isnot(None),
                    # Filter by similarity threshold
                    FAQCandidate.question_embedding.cosine_distance(query_embedding) <= (1 - min_similarity),
                )
                .order_by(
                    # Order by similarity descending (lowest distance first)
                    FAQCandidate.question_embedding.cosine_distance(query_embedding)
                )
                .limit(max_results)
            )

            result = await self.db.execute(stmt)
            rows = result.fetchall()

            # Convert to dictionaries, filtering entity mismatches
            faqs = []
            for row in rows:
                # Validate entity match before including (if query provided)
                if query and not self._validate_entity_match(query, row.suggested_question):
                    logger.debug(
                        "Filtered FAQ due to entity mismatch",
                        extra={"query": query[:50], "faq_question": row.suggested_question[:50]},
                    )
                    continue  # Skip - entity mismatch

                faq = {
                    "faq_id": str(row.id),
                    "question": row.suggested_question,
                    "answer": row.best_response_content,
                    "similarity_score": float(row.similarity),
                    "category": row.suggested_category,
                    "regulatory_references": row.regulatory_references or [],
                    "priority_score": float(row.priority_score) if row.priority_score else 0.0,
                    "approval_status": row.status,
                }
                faqs.append(faq)

            return faqs

        except Exception as e:
            logger.error(
                f"Error in semantic search: {e}",
                exc_info=True,
                extra={"min_similarity": min_similarity, "max_results": max_results},
            )
            return []

    async def find_matching_faqs_batch(
        self, queries: list[str], min_similarity: float | None = None, max_results: int | None = None
    ) -> list[list[dict]]:
        """Find matching FAQs for multiple queries in batch.

        Optimizes embedding generation by batching OpenAI API calls.

        Args:
            queries: List of user questions
            min_similarity: Minimum cosine similarity threshold
            max_results: Maximum results per query

        Returns:
            List of result lists (one per query)
        """
        if not queries:
            return []

        # Use defaults if not provided
        if min_similarity is None:
            min_similarity = self.default_min_similarity
        if max_results is None:
            max_results = self.default_max_results

        try:
            # Generate embeddings in batch
            embeddings = await generate_embeddings_batch(queries)

            # Perform searches with entity validation
            results = []
            for query, embedding in zip(queries, embeddings, strict=False):
                if embedding:
                    faq_results = await self._semantic_search(
                        query_embedding=embedding, min_similarity=min_similarity, max_results=max_results, query=query
                    )
                    results.append(faq_results)
                else:
                    logger.warning(f"Failed to generate embedding for batch query: {query[:50]}")
                    results.append([])

            return results

        except Exception as e:
            logger.error(f"Error in batch FAQ retrieval: {e}", exc_info=True)
            # Return empty results for all queries
            return [[] for _ in queries]

    async def close(self) -> None:
        """Close Redis connection pool."""
        if self._redis_client:
            try:
                await self._redis_client.close()
                logger.info("Redis connection closed for FAQ retrieval service")
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
