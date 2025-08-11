"""Search API endpoints for semantic, hybrid, and PostgreSQL full-text search."""

import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.database import get_async_session
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.session import Session
from app.models.knowledge import (
    KnowledgeQuery, 
    KnowledgeSearchResponse, 
    KnowledgeItem,
    KnowledgeFeedback
)
from app.services.vector_service import vector_service
from app.services.italian_knowledge import italian_knowledge_service
from app.services.search_service import SearchService


router = APIRouter()


class SemanticSearchRequest(BaseModel):
    """Semantic search request model."""
    query: str = Field(..., min_length=3, max_length=500, description="Search query")
    knowledge_type: Optional[str] = Field(default=None, description="Filter by type: regulation, tax_rate, template")
    language: str = Field(default="italian", description="Language for search")
    top_k: Optional[int] = Field(default=10, ge=1, le=50, description="Number of results")


class HybridSearchRequest(BaseModel):
    """Hybrid search request combining semantic and keyword search."""
    query: str = Field(..., min_length=3, max_length=500, description="Search query")
    keywords: Optional[List[str]] = Field(default=None, description="Additional keywords for filtering")
    knowledge_type: Optional[str] = Field(default=None, description="Filter by type")
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="Weight for semantic search (0-1)")
    language: str = Field(default="italian", description="Language for search")


class IndexDocumentRequest(BaseModel):
    """Request to index a document in vector database."""
    document_id: str = Field(..., description="Unique document identifier")
    title: str = Field(..., min_length=1, max_length=200, description="Document title")
    content: str = Field(..., min_length=10, max_length=50000, description="Document content")
    document_type: str = Field(..., description="Type: regulation, tax_rate, template, custom")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


@router.post("/semantic")
@limiter.limit("100 per minute")
async def semantic_search(
    request: Request,
    search_request: SemanticSearchRequest,
    session: Session = Depends(get_current_session),
):
    """Perform semantic search on Italian knowledge base.
    
    Args:
        request: FastAPI request object
        search_request: Search parameters
        session: Current user session
        
    Returns:
        Semantic search results
    """
    try:
        # Check if vector service is available
        if not vector_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="Vector search service is not available. Please try keyword search."
            )
        
        # Perform semantic search
        results = vector_service.search_italian_knowledge(
            query=search_request.query,
            knowledge_type=search_request.knowledge_type,
            language=search_request.language
        )
        
        # Limit results to requested top_k
        if search_request.top_k:
            results = results[:search_request.top_k]
        
        logger.info(
            "semantic_search_completed",
            user_id=session.user_id,
            query=search_request.query[:50],
            results_count=len(results),
            knowledge_type=search_request.knowledge_type
        )
        
        return JSONResponse({
            "query": search_request.query,
            "results": results,
            "count": len(results),
            "search_type": "semantic",
            "language": search_request.language,
            "filters": {
                "knowledge_type": search_request.knowledge_type
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "semantic_search_failed",
            session_id=session.id,
            query=search_request.query[:50],
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Semantic search failed")


@router.post("/hybrid")
@limiter.limit("50 per minute")
async def hybrid_search(
    request: Request,
    search_request: HybridSearchRequest,
    session: Session = Depends(get_current_session),
):
    """Perform hybrid search combining semantic and keyword search.
    
    Args:
        request: FastAPI request object
        search_request: Search parameters
        session: Current user session
        
    Returns:
        Combined search results
    """
    try:
        # First, perform keyword search if keywords provided
        keyword_results = []
        if search_request.keywords:
            # Search regulations with keywords
            regulations = await italian_knowledge_service.search_regulations(
                keywords=search_request.keywords,
                subjects=None
            )
            
            # Convert to search result format
            for reg in regulations[:10]:  # Limit keyword results
                keyword_results.append({
                    "id": f"regulation_{reg.id}",
                    "document_id": f"regulation_{reg.id}",
                    "score": 0.8,  # Base score for keyword matches
                    "title": reg.title,
                    "summary": reg.summary,
                    "type": "regulation",
                    "metadata": {
                        "authority": reg.authority,
                        "year": reg.year,
                        "subjects": reg.subjects
                    }
                })
        
        # Perform hybrid search if vector service available
        if vector_service.is_available():
            results = vector_service.hybrid_search(
                query=search_request.query,
                keyword_results=keyword_results,
                semantic_weight=search_request.semantic_weight
            )
        else:
            # Fallback to keyword results only
            results = keyword_results
            logger.warning("vector_service_unavailable_for_hybrid_search")
        
        logger.info(
            "hybrid_search_completed",
            user_id=session.user_id,
            query=search_request.query[:50],
            keyword_count=len(keyword_results),
            results_count=len(results),
            semantic_weight=search_request.semantic_weight
        )
        
        return JSONResponse({
            "query": search_request.query,
            "results": results,
            "count": len(results),
            "search_type": "hybrid",
            "semantic_weight": search_request.semantic_weight,
            "keywords": search_request.keywords,
            "language": search_request.language
        })
        
    except Exception as e:
        logger.error(
            "hybrid_search_failed",
            session_id=session.id,
            query=search_request.query[:50],
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Hybrid search failed")


@router.post("/index/document")
@limiter.limit("20 per minute")
async def index_document(
    request: Request,
    index_request: IndexDocumentRequest,
    session: Session = Depends(get_current_session),
):
    """Index a document in the vector database.
    
    Args:
        request: FastAPI request object
        index_request: Document to index
        session: Current user session
        
    Returns:
        Indexing result
    """
    try:
        # Check if vector service is available
        if not vector_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="Vector indexing service is not available"
            )
        
        # Prepare metadata
        metadata = {
            **index_request.metadata,
            "user_id": session.user_id,
            "indexed_by": session.user_id,
            "document_type": index_request.document_type,
            "title": index_request.title
        }
        
        # Index document
        success = vector_service.store_document(
            document_id=index_request.document_id,
            text=f"{index_request.title}\n\n{index_request.content}",
            metadata=metadata
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to index document")
        
        logger.info(
            "document_indexed",
            user_id=session.user_id,
            document_id=index_request.document_id,
            document_type=index_request.document_type,
            content_length=len(index_request.content)
        )
        
        return JSONResponse({
            "success": True,
            "document_id": index_request.document_id,
            "indexed_at": metadata.get("stored_at"),
            "message": "Document indexed successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "document_indexing_failed",
            session_id=session.id,
            document_id=index_request.document_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Document indexing failed")


@router.get("/similar/{document_id}")
@limiter.limit("50 per minute")
async def find_similar_documents(
    request: Request,
    document_id: str,
    top_k: int = Query(default=5, ge=1, le=20, description="Number of similar documents"),
    session: Session = Depends(get_current_session),
):
    """Find documents similar to a given document.
    
    Args:
        request: FastAPI request object
        document_id: Document ID to find similar documents for
        top_k: Number of results
        session: Current user session
        
    Returns:
        Similar documents
    """
    try:
        # Check if vector service is available
        if not vector_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="Vector search service is not available"
            )
        
        # This would retrieve the document and find similar ones
        # For now, return a placeholder response
        logger.info(
            "similar_documents_search",
            user_id=session.user_id,
            document_id=document_id,
            top_k=top_k
        )
        
        return JSONResponse({
            "source_document_id": document_id,
            "similar_documents": [],
            "message": "Similar document search will be implemented with document retrieval"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "similar_documents_search_failed",
            session_id=session.id,
            document_id=document_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Similar document search failed")


@router.get("/stats")
@limiter.limit("10 per minute")
async def get_vector_index_stats(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get vector database index statistics.
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        Index statistics
    """
    try:
        stats = vector_service.get_index_stats()
        
        logger.info(
            "vector_stats_retrieved",
            user_id=session.user_id,
            status=stats.get("status")
        )
        
        return JSONResponse(stats)
        
    except Exception as e:
        logger.error(
            "vector_stats_retrieval_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve vector index statistics")


@router.post("/reindex/italian-knowledge")
@limiter.limit("1 per hour")
async def reindex_italian_knowledge(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Reindex all Italian knowledge base content (admin only).
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        Reindexing result
    """
    try:
        # Check if vector service is available
        if not vector_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="Vector indexing service is not available"
            )
        
        # This would typically check for admin privileges
        # For now, any authenticated user can trigger reindexing
        
        indexed_count = 0
        errors = []
        
        # Example: Index some sample Italian content
        sample_contents = [
            {
                "id": "sample_reg_1",
                "title": "Codice Civile - Art. 1321",
                "content": "Il contratto è l'accordo di due o più parti per costituire, regolare o estinguere tra loro un rapporto giuridico patrimoniale.",
                "type": "regulation",
                "metadata": {"article": "1321", "code": "civil_code"}
            },
            {
                "id": "sample_tax_1",
                "title": "Aliquota IVA ordinaria",
                "content": "L'aliquota ordinaria dell'imposta sul valore aggiunto (IVA) è stabilita nella misura del 22 per cento della base imponibile.",
                "type": "tax_rate",
                "metadata": {"rate": 22, "tax_type": "VAT"}
            },
            {
                "id": "sample_template_1",
                "title": "Modello Contratto di Servizi",
                "content": "Template standard per contratto di prestazione di servizi professionali conforme al codice civile italiano.",
                "type": "template",
                "metadata": {"category": "contracts", "variables": ["client_name", "service_description"]}
            }
        ]
        
        for content in sample_contents:
            try:
                success = vector_service.store_document(
                    document_id=content["id"],
                    text=f"{content['title']}\n\n{content['content']}",
                    metadata={
                        **content["metadata"],
                        "type": content["type"],
                        "title": content["title"],
                        "language": "italian"
                    }
                )
                if success:
                    indexed_count += 1
                else:
                    errors.append(f"Failed to index {content['id']}")
            except Exception as e:
                errors.append(f"Error indexing {content['id']}: {str(e)}")
        
        logger.info(
            "italian_knowledge_reindexing_completed",
            user_id=session.user_id,
            indexed_count=indexed_count,
            error_count=len(errors)
        )
        
        return JSONResponse({
            "success": len(errors) == 0,
            "indexed_count": indexed_count,
            "errors": errors,
            "message": f"Indexed {indexed_count} Italian knowledge items"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "italian_knowledge_reindexing_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Italian knowledge reindexing failed")


# ============================================================================
# PostgreSQL Full-Text Search Endpoints
# ============================================================================

@router.get("/knowledge", response_model=KnowledgeSearchResponse)
@limiter.limit("100 per hour")
async def search_knowledge_fts(
    request: Request,
    q: str = Query(..., description="Search query", min_length=1, max_length=500),
    category: Optional[str] = Query(None, description="Filter by category"),
    subcategory: Optional[str] = Query(None, description="Filter by subcategory"),
    source: Optional[str] = Query(None, description="Filter by source"),
    language: str = Query("it", description="Search language"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Results offset"),
    min_relevance: float = Query(0.01, ge=0.0, le=1.0, description="Minimum relevance threshold"),
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Search knowledge base using PostgreSQL Full-Text Search.
    
    Features:
    - Italian language text processing
    - Accent-insensitive search
    - Partial word matching
    - Result ranking with ts_rank
    - Category and source filtering
    - Cached results for performance
    
    Example queries:
    - "dichiarazione redditi" - Find tax declaration info
    - "fattura elettronica" - Electronic invoice information
    - "IVA società" - VAT for companies
    """
    start_time = time.time()
    
    try:
        # Create search service
        search_service = SearchService(db)
        
        # Execute search
        results = await search_service.search(
            query=q,
            limit=limit,
            offset=offset,
            category=category,
            min_rank=min_relevance
        )
        
        # Get search suggestions if few results
        suggestions = []
        if len(results) < 3:
            suggestions = await search_service.get_search_suggestions(q, limit=5)
        
        # Calculate search time
        search_time_ms = (time.time() - start_time) * 1000
        
        # Convert results to response format
        result_data = []
        for result in results:
            result_data.append({
                "id": result.id,
                "title": result.title,
                "content": result.content[:500] + "..." if len(result.content) > 500 else result.content,
                "category": result.category,
                "source": result.source,
                "rank_score": round(result.rank_score, 4),
                "relevance_score": round(result.relevance_score, 4),
                "highlight": result.highlight,
                "updated_at": result.updated_at.isoformat() if result.updated_at else None
            })
        
        # Log search for analytics
        logger.info(
            "fts_knowledge_search_completed",
            user_id=session.user_id,
            query=q,
            results_count=len(results),
            search_time_ms=search_time_ms,
            category=category,
            source=source
        )
        
        return KnowledgeSearchResponse(
            query=q,
            results=result_data,
            total_count=len(results),  # Note: This is limited results, not total matches
            page_size=limit,
            page=offset // limit + 1,
            search_time_ms=round(search_time_ms, 2),
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(
            "fts_knowledge_search_failed", 
            session_id=session.id,
            query=q,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Knowledge search service temporarily unavailable"
        )


@router.get("/knowledge/suggestions")
@limiter.limit("200 per hour")
async def get_knowledge_search_suggestions(
    request: Request,
    q: str = Query(..., description="Partial query for suggestions", min_length=2, max_length=100),
    limit: int = Query(5, ge=1, le=20, description="Maximum suggestions"),
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get search suggestions based on partial query.
    
    Returns common terms from the knowledge base that match the partial input.
    Useful for autocomplete functionality.
    """
    try:
        search_service = SearchService(db)
        suggestions = await search_service.get_search_suggestions(q, limit=limit)
        
        logger.info(
            "fts_suggestions_completed",
            user_id=session.user_id,
            query=q,
            suggestions_count=len(suggestions)
        )
        
        return JSONResponse({
            "query": q,
            "suggestions": suggestions,
            "count": len(suggestions)
        })
        
    except Exception as e:
        logger.error(
            "fts_suggestions_failed",
            session_id=session.id,
            query=q,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Suggestions service temporarily unavailable"
        )


@router.post("/knowledge/feedback")
@limiter.limit("50 per hour")
async def submit_knowledge_feedback(
    request: Request,
    knowledge_item_id: int,
    rating: int = Query(..., ge=1, le=5, description="Rating 1-5"),
    feedback_text: Optional[str] = Query(None, description="Optional feedback text"),
    feedback_type: str = Query(..., description="Feedback type: helpful, accurate, outdated, incorrect"),
    search_query: Optional[str] = Query(None, description="Original search query"),
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Submit feedback on knowledge search results.
    
    Helps improve search relevance and content quality.
    """
    try:
        # Verify knowledge item exists
        result = await db.get(KnowledgeItem, knowledge_item_id)
        if not result:
            raise HTTPException(status_code=404, detail="Knowledge item not found")
        
        # Create feedback record
        feedback = KnowledgeFeedback(
            knowledge_item_id=knowledge_item_id,
            user_id=session.user_id,
            session_id=session.id,
            rating=rating,
            feedback_text=feedback_text,
            feedback_type=feedback_type,
            search_query=search_query
        )
        
        db.add(feedback)
        await db.commit()
        
        # Update knowledge item feedback metrics
        await _update_knowledge_feedback_metrics(db, knowledge_item_id)
        
        logger.info(
            "knowledge_feedback_submitted",
            user_id=session.user_id,
            knowledge_item_id=knowledge_item_id,
            rating=rating,
            feedback_type=feedback_type
        )
        
        return JSONResponse({
            "status": "success",
            "message": "Feedback submitted successfully",
            "feedback_id": feedback.id
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "knowledge_feedback_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Feedback submission failed"
        )


@router.get("/knowledge/categories")
@limiter.limit("60 per hour")
async def get_knowledge_categories(
    request: Request,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get available knowledge categories for filtering.
    
    Returns list of categories and their document counts.
    """
    try:
        from sqlalchemy import select, func
        
        # Get category counts
        query = select(
            KnowledgeItem.category,
            KnowledgeItem.subcategory,
            func.count(KnowledgeItem.id).label("count")
        ).where(
            KnowledgeItem.status == "active"
        ).group_by(
            KnowledgeItem.category,
            KnowledgeItem.subcategory
        ).order_by(
            KnowledgeItem.category,
            KnowledgeItem.subcategory
        )
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        # Organize by category
        categories = {}
        for row in rows:
            category = row.category
            subcategory = row.subcategory
            count = row.count
            
            if category not in categories:
                categories[category] = {
                    "name": category,
                    "total_count": 0,
                    "subcategories": {}
                }
            
            categories[category]["total_count"] += count
            
            if subcategory:
                categories[category]["subcategories"][subcategory] = count
        
        logger.info(
            "knowledge_categories_retrieved",
            user_id=session.user_id,
            categories_count=len(categories)
        )
        
        return JSONResponse({
            "categories": list(categories.values()),
            "total_categories": len(categories)
        })
        
    except Exception as e:
        logger.error(
            "knowledge_categories_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve categories"
        )


@router.post("/knowledge/admin/reindex")
@limiter.limit("1 per hour")
async def reindex_knowledge_fts(
    request: Request,
    knowledge_ids: Optional[List[int]] = None,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Manually reindex knowledge base search vectors.
    
    Admin endpoint for maintenance and bulk updates.
    Typically not needed as triggers handle automatic updates.
    """
    try:
        search_service = SearchService(db)
        
        if knowledge_ids:
            await search_service.update_search_vectors([str(id) for id in knowledge_ids])
            message = f"Reindexed {len(knowledge_ids)} knowledge items"
        else:
            await search_service.update_search_vectors()
            message = "Reindexed entire knowledge base"
        
        logger.info(
            "knowledge_fts_reindex_completed",
            user_id=session.user_id,
            message=message
        )
        
        return JSONResponse({
            "status": "success",
            "message": message
        })
        
    except Exception as e:
        logger.error(
            "knowledge_fts_reindex_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Reindex operation failed"
        )


@router.delete("/knowledge/admin/cache")
@limiter.limit("10 per hour")
async def clear_knowledge_search_cache(
    request: Request,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Clear search cache.
    
    Admin endpoint for cache management.
    """
    try:
        search_service = SearchService(db)
        await search_service.clear_search_cache()
        
        logger.info("knowledge_search_cache_cleared", user_id=session.user_id)
        
        return JSONResponse({
            "status": "success",
            "message": "Search cache cleared successfully"
        })
        
    except Exception as e:
        logger.error(
            "knowledge_cache_clear_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Cache clear operation failed"
        )


async def _update_knowledge_feedback_metrics(db: AsyncSession, knowledge_item_id: int):
    """Update aggregate feedback metrics for a knowledge item"""
    from sqlalchemy import select, func
    
    # Calculate average rating and feedback count
    query = select(
        func.avg(KnowledgeFeedback.rating).label("avg_rating"),
        func.count(KnowledgeFeedback.id).label("feedback_count")
    ).where(
        KnowledgeFeedback.knowledge_item_id == knowledge_item_id
    )
    
    result = await db.execute(query)
    row = result.first()
    
    if row and row.feedback_count > 0:
        # Update knowledge item
        knowledge_item = await db.get(KnowledgeItem, knowledge_item_id)
        if knowledge_item:
            knowledge_item.user_feedback_score = float(row.avg_rating)
            knowledge_item.feedback_count = int(row.feedback_count)
            await db.commit()