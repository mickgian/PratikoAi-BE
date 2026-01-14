"""Hybrid PostgreSQL Retriever.

Combines FTS (tsvector) and vector similarity (pgvector) for retrieval.
Applies recency boost using kb_epoch timestamp.
Falls back to FTS-only if vector search unavailable.
"""

import time
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    CONTEXT_TOP_K,
    HYBRID_WEIGHT_FTS,
    HYBRID_WEIGHT_RECENCY,
    HYBRID_WEIGHT_VEC,
)
from app.core.embed import (
    embedding_to_pgvector,
    generate_embedding,
)


async def hybrid_retrieve(
    session: AsyncSession,
    query: str,
    top_k: int = None,
    fts_weight: float = None,
    vector_weight: float = None,
    recency_weight: float = None,
    recency_days: int = 365,
) -> list[dict[str, Any]]:
    """Hybrid retrieval using FTS + vector + recency.

    Args:
        session: Database session
        query: Search query
        top_k: Number of results to return (defaults to CONTEXT_TOP_K from config)
        fts_weight: Weight for FTS score (defaults to HYBRID_WEIGHT_FTS from config)
        vector_weight: Weight for vector score (defaults to HYBRID_WEIGHT_VEC from config)
        recency_weight: Weight for recency score (defaults to HYBRID_WEIGHT_RECENCY from config)
        recency_days: Days for recency boost calculation (default 365)

    Returns:
        List of result dictionaries with scores
    """
    # Use config defaults if not provided
    if top_k is None:
        top_k = CONTEXT_TOP_K
    if fts_weight is None:
        fts_weight = HYBRID_WEIGHT_FTS
    if vector_weight is None:
        vector_weight = HYBRID_WEIGHT_VEC
    if recency_weight is None:
        recency_weight = HYBRID_WEIGHT_RECENCY
    # Generate embedding for query
    query_embedding_vec = await generate_embedding(query)

    if not query_embedding_vec:
        print("⚠️  Vector embedding failed, falling back to FTS only")
        return await fts_only_retrieve(session, query, top_k)

    query_embedding_str = embedding_to_pgvector(query_embedding_vec)

    # Current timestamp for recency calculation
    now = time.time()

    # Hybrid query combining FTS, vector, and recency
    # JOIN knowledge_items to get document metadata
    sql = text(
        """
        WITH ranked AS (
            SELECT
                kc.id,
                kc.knowledge_item_id,
                kc.chunk_text,
                kc.chunk_index,
                kc.source_url,
                kc.document_title,
                kc.kb_epoch,

                -- Metadata from knowledge_items
                ki.source AS document_source,
                ki.category,
                ki.subcategory,
                ki.extraction_method,
                ki.text_quality,
                ki.tier,  -- DEV-242 Phase 11: Tier for ranking

                -- FTS score (normalized)
                ts_rank_cd(kc.search_vector, websearch_to_tsquery('italian', :query)) AS fts_score,

                -- Vector similarity score (cosine distance -> similarity)
                1 - (kc.embedding <=> CAST(:embedding AS vector)) AS vector_score,

                -- Recency score (exponential decay)
                EXP(-(:now - kc.kb_epoch) / (:recency_days * 86400.0)) AS recency_score

            FROM knowledge_chunks kc
            INNER JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id
            WHERE
                -- Exclude junk chunks
                kc.junk = FALSE
                -- FTS filter
                AND kc.search_vector @@ websearch_to_tsquery('italian', :query)
                -- Vector filter (distance < 1.0 for broader matching)
                AND (kc.embedding <=> CAST(:embedding AS vector)) < 1.0
        )
        SELECT
            *,
            -- Combined score
            (:fts_weight * fts_score +
             :vector_weight * vector_score +
             :recency_weight * recency_score) AS combined_score
        FROM ranked
        ORDER BY combined_score DESC
        LIMIT :top_k;
    """
    )

    result = await session.execute(
        sql,
        {
            "query": query,
            "embedding": query_embedding_str,
            "now": now,
            "recency_days": recency_days,
            "fts_weight": fts_weight,
            "vector_weight": vector_weight,
            "recency_weight": recency_weight,
            "top_k": top_k,
        },
    )

    rows = result.fetchall()

    # Convert to dict
    results = []
    for row in rows:
        results.append(
            {
                "chunk_id": row.id,
                "knowledge_item_id": row.knowledge_item_id,
                "chunk_text": row.chunk_text,
                "chunk_index": row.chunk_index,
                "source_url": row.source_url,
                "document_title": row.document_title,
                "kb_epoch": row.kb_epoch,
                # NEW: Document metadata from knowledge_items
                "document_source": row.document_source,
                "category": row.category,
                "subcategory": row.subcategory,
                "extraction_method": row.extraction_method,
                "text_quality": float(row.text_quality) if row.text_quality else None,
                "tier": row.tier,  # DEV-242 Phase 11
                # Scores
                "fts_score": float(row.fts_score) if row.fts_score else 0.0,
                "vector_score": float(row.vector_score) if row.vector_score else 0.0,
                "recency_score": float(row.recency_score) if row.recency_score else 0.0,
                "combined_score": float(row.combined_score) if row.combined_score else 0.0,
            }
        )

    return results


async def fts_only_retrieve(session: AsyncSession, query: str, top_k: int = 10) -> list[dict[str, Any]]:
    """FTS-only retrieval (fallback when vector search unavailable).

    Args:
        session: Database session
        query: Search query
        top_k: Number of results to return

    Returns:
        List of result dictionaries
    """
    sql = text(
        """
        SELECT
            kc.id,
            kc.knowledge_item_id,
            kc.chunk_text,
            kc.chunk_index,
            kc.source_url,
            kc.document_title,
            kc.kb_epoch,
            -- Metadata from knowledge_items
            ki.source AS document_source,
            ki.category,
            ki.subcategory,
            ki.extraction_method,
            ki.text_quality,
            ki.tier,  -- DEV-242 Phase 11: Tier for ranking
            ts_rank_cd(kc.search_vector, websearch_to_tsquery('italian', :query)) AS fts_score
        FROM knowledge_chunks kc
        INNER JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id
        WHERE kc.junk = FALSE
          AND kc.search_vector @@ websearch_to_tsquery('italian', :query)
        ORDER BY fts_score DESC
        LIMIT :top_k;
    """
    )

    result = await session.execute(sql, {"query": query, "top_k": top_k})
    rows = result.fetchall()

    results = []
    for row in rows:
        results.append(
            {
                "chunk_id": row.id,
                "knowledge_item_id": row.knowledge_item_id,
                "chunk_text": row.chunk_text,
                "chunk_index": row.chunk_index,
                "source_url": row.source_url,
                "document_title": row.document_title,
                "kb_epoch": row.kb_epoch,
                # NEW: Document metadata from knowledge_items
                "document_source": row.document_source,
                "category": row.category,
                "subcategory": row.subcategory,
                "extraction_method": row.extraction_method,
                "text_quality": float(row.text_quality) if row.text_quality else None,
                "tier": row.tier,  # DEV-242 Phase 11
                # Scores
                "fts_score": float(row.fts_score) if row.fts_score else 0.0,
                "vector_score": 0.0,
                "recency_score": 0.0,
                "combined_score": float(row.fts_score) if row.fts_score else 0.0,
            }
        )

    return results


async def explain_hybrid_query(session: AsyncSession, query: str) -> str:
    """Get EXPLAIN ANALYZE output for hybrid query (diagnostics).

    Args:
        session: Database session
        query: Search query

    Returns:
        EXPLAIN output as string
    """
    query_embedding_vec = await generate_embedding(query)
    if not query_embedding_vec:
        return "ERROR: Could not generate embedding"

    query_embedding_str = embedding_to_pgvector(query_embedding_vec)
    now = time.time()

    sql = text(
        """
        EXPLAIN ANALYZE
        WITH ranked AS (
            SELECT
                kc.id,
                kc.chunk_text,
                ts_rank_cd(kc.search_vector, websearch_to_tsquery('italian', :query)) AS fts_score,
                1 - (kc.embedding <=> :embedding::vector) AS vector_score,
                EXP(-(:now - kc.kb_epoch) / (365.0 * 86400.0)) AS recency_score
            FROM knowledge_chunks kc
            WHERE
                kc.junk = FALSE
                AND kc.search_vector @@ websearch_to_tsquery('italian', :query)
                AND (kc.embedding <=> :embedding::vector) < 0.5
        )
        SELECT *,
            (:fts_weight * fts_score + :vector_weight * vector_score + :recency_weight * recency_score) AS combined_score
        FROM ranked
        ORDER BY combined_score DESC
        LIMIT :top_k;
    """
    )

    result = await session.execute(
        sql,
        {
            "query": query,
            "embedding": query_embedding_str,
            "now": now,
            "fts_weight": HYBRID_WEIGHT_FTS,
            "vector_weight": HYBRID_WEIGHT_VEC,
            "recency_weight": HYBRID_WEIGHT_RECENCY,
            "top_k": CONTEXT_TOP_K,
        },
    )

    rows = result.fetchall()
    return "\n".join(str(row) for row in rows)
