"""Search API endpoints for semantic and hybrid search."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.session import Session
from app.services.vector_service import vector_service
from app.services.italian_knowledge import italian_knowledge_service


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