"""Expert FAQ Retrieval Service - Semantic similarity search over approved FAQ candidates.

Provides semantic search over approved expert FAQ candidates using pgvector
for efficient vector similarity queries. Enables finding matching FAQs even
when questions are phrased differently.

Key Features:
- Semantic similarity search using OpenAI embeddings
- pgvector IVFFlat index for fast approximate nearest neighbor search
- Approval status filtering (only returns approved FAQs)
- Configurable similarity threshold
- In-memory embedding cache for repeated queries

Performance:
- Typical query time: 10-20ms for 10K records
- Target p95 latency: <100ms
- Cache hit rate target: ≥60%

Integration Points:
- LangGraph Step 24: Golden Set retrieval
- Expert feedback loop: FAQ candidate creation
- Hybrid search: FTS + Vector + Recency scoring
"""

import hashlib
import logging
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embed import generate_embedding
from app.models.faq_automation import FAQApprovalStatus, FAQCandidate

logger = logging.getLogger(__name__)


class ExpertFAQRetrievalService:
    """Service for retrieving expert FAQ candidates using semantic similarity search.

    Uses pgvector for efficient cosine similarity queries over question embeddings.
    Implements caching to reduce OpenAI API calls for repeated queries.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize the retrieval service.

        Args:
            db_session: Async SQLAlchemy session for database operations
        """
        self.db = db_session
        self.embedding_cache: dict[str, list[float]] = {}

    async def find_matching_faqs(self, query: str, min_similarity: float = 0.85, max_results: int = 10) -> list[dict]:
        """Find FAQ candidates that semantically match the query.

        Performs semantic similarity search using pgvector cosine similarity.
        Only returns FAQs with approval_status = 'auto_approved' or 'manually_approved'.

        Args:
            query: User's question text
            min_similarity: Minimum cosine similarity threshold (0.0-1.0)
            max_results: Maximum number of results to return

        Returns:
            List of FAQ dictionaries with question, answer, similarity score.
            Sorted by similarity descending.

        Example:
            >>> service = ExpertFAQRetrievalService(db)
            >>> faqs = await service.find_matching_faqs("Cos'è l'IVA?", min_similarity=0.85)
            >>> print(faqs[0]['similarity_score'])  # 0.92
        """
        # Handle empty queries
        if not query or not query.strip():
            logger.debug("Empty query provided, returning no results")
            return []

        try:
            # Generate embedding for query
            query_embedding = await self._generate_embedding(query)

            if not query_embedding:
                logger.warning(f"Failed to generate embedding for query: {query[:50]}")
                return []

            # Build SQL query with pgvector similarity
            # Note: <=> operator returns cosine distance (1 - cosine similarity)
            # So we convert to similarity: 1 - distance
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
                    # cosine_distance <= (1 - min_similarity) means similarity >= min_similarity
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

            # Convert to dictionaries
            faqs = []
            for row in rows:
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

            logger.info(
                f"Found {len(faqs)} matching FAQs for query",
                extra={
                    "query_preview": query[:50],
                    "query_length": len(query),
                    "min_similarity": min_similarity,
                    "results_count": len(faqs),
                    "top_similarity": faqs[0]["similarity_score"] if faqs else None,
                },
            )

            return faqs

        except Exception as e:
            logger.error(
                f"Error finding matching FAQs: {e}",
                exc_info=True,
                extra={"query_preview": query[:50] if query else None},
            )
            return []

    async def get_by_signature(self, query_signature: str) -> dict | None:
        """Retrieve FAQ by exact query signature match.

        Faster than semantic search - used for exact question matches.
        The signature is computed as SHA-256 hash of normalized query text.

        Args:
            query_signature: Hash-based signature of the query (SHA-256 hex)

        Returns:
            FAQ dictionary if found, None otherwise.
            Includes similarity_score=1.0 for exact matches.

        Note:
            This optimization requires a query_signature column in the table.
            Currently not implemented - falls back to None.
            Future enhancement: Add query_signature column and index.
        """
        try:
            # TODO: Implement signature-based lookup when query_signature column exists
            # For now, return None (semantic search will be used instead)
            logger.debug(
                "Signature-based lookup not yet implemented", extra={"query_signature": query_signature[:16] + "..."}
            )
            return None

        except Exception as e:
            logger.error(
                f"Error retrieving FAQ by signature: {e}",
                exc_info=True,
                extra={"query_signature": query_signature[:16] + "..."},
            )
            return None

    async def _generate_embedding(self, text: str) -> list[float] | None:
        """Generate vector embedding for text using OpenAI API.

        Uses in-memory caching to reduce API calls for repeated queries.

        Args:
            text: Text to embed (typically a question)

        Returns:
            Vector of 1536 dimensions (OpenAI ada-002), or None if generation fails
        """
        # Check cache first (keyed by text hash for memory efficiency)
        cache_key = hashlib.sha256(text.encode()).hexdigest()

        if cache_key in self.embedding_cache:
            logger.debug("Using cached embedding", extra={"cache_key": cache_key[:16] + "..."})
            return self.embedding_cache[cache_key]

        try:
            # Generate embedding using OpenAI
            embedding = await generate_embedding(text)

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
            self.embedding_cache[cache_key] = embedding

            logger.debug(
                "Generated embedding successfully",
                extra={
                    "text_preview": text[:50],
                    "embedding_dim": len(embedding),
                    "cache_size": len(self.embedding_cache),
                },
            )

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}", exc_info=True, extra={"text_preview": text[:50]})
            return None
