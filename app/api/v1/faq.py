"""
FAQ API endpoints for the Intelligent FAQ System.

This module provides REST API endpoints for FAQ management, semantic search,
and analytics with comprehensive cost optimization and performance monitoring.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.database import get_async_db
from app.models.faq import (
    FAQEntry, FAQUsageLog, FAQCategory, FAQAnalyticsSummary,
    UpdateSensitivity
)
from app.services.intelligent_faq_service import (
    IntelligentFAQService, FAQResponse, create_faq_entry, 
    update_faq_entry, get_faq_by_category, search_faqs_by_tags
)
from app.services.italian_query_normalizer import ItalianQueryNormalizer
from app.utils.auth import get_current_user, get_current_admin_user
from app.schemas.auth import User


router = APIRouter(prefix="/faq", tags=["FAQ"])
settings = get_settings()


# Pydantic models for API requests/responses
from pydantic import BaseModel, Field


class FAQQueryRequest(BaseModel):
    """Request model for FAQ queries."""
    query: str = Field(..., description="User's question", min_length=3, max_length=500)
    context: Optional[str] = Field(None, description="Additional context", max_length=200)
    user_preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")


class FAQQueryResponse(BaseModel):
    """Response model for FAQ queries."""
    answer: str = Field(..., description="FAQ answer or variation")
    faq_id: Optional[str] = Field(None, description="FAQ entry ID if matched")
    similarity_score: float = Field(..., description="Semantic similarity score")
    from_cache: bool = Field(..., description="Whether response came from cache")
    generation_cost_euros: float = Field(..., description="Cost of response generation")
    response_time_ms: float = Field(..., description="Total response time")
    needs_review: bool = Field(False, description="Whether FAQ needs review")
    category: Optional[str] = Field(None, description="FAQ category")
    tags: Optional[List[str]] = Field(None, description="FAQ tags")


class FAQCreateRequest(BaseModel):
    """Request model for creating FAQ entries."""
    question: str = Field(..., description="FAQ question", min_length=10, max_length=500)
    answer: str = Field(..., description="FAQ answer", min_length=20, max_length=2000)
    category: str = Field("generale", description="FAQ category")
    tags: Optional[List[str]] = Field(None, description="FAQ tags")
    update_sensitivity: UpdateSensitivity = Field(UpdateSensitivity.MEDIUM, description="Update sensitivity")


class FAQUpdateRequest(BaseModel):
    """Request model for updating FAQ entries."""
    question: Optional[str] = Field(None, description="FAQ question", min_length=10, max_length=500)
    answer: Optional[str] = Field(None, description="FAQ answer", min_length=20, max_length=2000)
    tags: Optional[List[str]] = Field(None, description="FAQ tags")
    change_reason: Optional[str] = Field(None, description="Reason for change", max_length=200)


class FAQFeedbackRequest(BaseModel):
    """Request model for FAQ feedback."""
    usage_log_id: str = Field(..., description="Usage log ID")
    was_helpful: bool = Field(..., description="Whether response was helpful")
    followup_needed: bool = Field(False, description="Whether followup is needed")
    comments: Optional[str] = Field(None, description="User comments", max_length=500)


class FAQEntryResponse(BaseModel):
    """Response model for FAQ entries."""
    id: str
    question: str
    answer: str
    category: str
    tags: List[str]
    language: str
    last_validated: Optional[datetime]
    needs_review: bool
    update_sensitivity: str
    hit_count: int
    last_used: Optional[datetime]
    avg_helpfulness: Optional[float]
    version: int
    created_at: datetime
    updated_at: datetime


class FAQSearchResponse(BaseModel):
    """Response model for FAQ search results."""
    results: List[FAQEntryResponse]
    total_count: int
    query_time_ms: float
    normalized_query: Optional[str] = None


class FAQAnalyticsResponse(BaseModel):
    """Response model for FAQ analytics."""
    period_start: datetime
    period_end: datetime
    total_queries: int
    faq_responses: int
    full_llm_responses: int
    cache_hit_rate: float
    cost_savings_euros: float
    cost_savings_percent: float
    avg_helpfulness_score: float
    top_categories: List[Dict[str, Any]]
    top_faqs: List[Dict[str, Any]]


# API Endpoints

@router.post("/query", response_model=FAQQueryResponse)
async def query_faq(
    request: FAQQueryRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> FAQQueryResponse:
    """
    Query the FAQ system with semantic search and response variation.
    
    This endpoint:
    1. Normalizes the Italian query for better matching
    2. Performs semantic search across FAQ entries
    3. Generates or retrieves cached response variations
    4. Logs usage for analytics and cost tracking
    """
    try:
        # Initialize services
        normalizer = ItalianQueryNormalizer()
        faq_service = IntelligentFAQService(db, normalizer)
        
        # Handle the query
        faq_response = await faq_service.handle_query(
            query=request.query,
            user_id=current_user.id if current_user else None,
            context=request.context or ""
        )
        
        # Get additional FAQ metadata if we have a match
        category = None
        tags = None
        
        if faq_response.faq_id:
            faq_entry = await db.get(FAQEntry, faq_response.faq_id)
            if faq_entry:
                category = faq_entry.category
                tags = faq_entry.tags
        
        return FAQQueryResponse(
            answer=faq_response.answer,
            faq_id=faq_response.faq_id,
            similarity_score=faq_response.similarity_score,
            from_cache=faq_response.from_cache,
            generation_cost_euros=faq_response.generation_cost_euros,
            response_time_ms=faq_response.response_time_ms,
            needs_review=faq_response.needs_review,
            category=category,
            tags=tags
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing FAQ query: {str(e)}"
        )


@router.post("/feedback")
async def submit_feedback(
    request: FAQFeedbackRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Submit user feedback on FAQ responses.
    
    Feedback is used to improve FAQ quality and track user satisfaction.
    """
    try:
        faq_service = IntelligentFAQService(db)
        
        success = await faq_service.collect_feedback(
            usage_log_id=request.usage_log_id,
            was_helpful=request.was_helpful,
            followup_needed=request.followup_needed,
            comments=request.comments
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Usage log not found"
            )
        
        return {
            "success": True,
            "message": "Feedback submitted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error submitting feedback: {str(e)}"
        )


@router.get("/search", response_model=FAQSearchResponse)
async def search_faqs(
    q: str = Query(..., description="Search query", min_length=3),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> FAQSearchResponse:
    """
    Search FAQ entries with filtering options.
    
    Supports semantic search, category filtering, and tag-based filtering.
    """
    import time
    start_time = time.perf_counter()
    
    try:
        # Normalize query for better search
        normalizer = ItalianQueryNormalizer()
        normalized_result = normalizer.normalize(q)
        normalized_query = normalized_result.normalized_query
        
        # Build search query
        query = select(FAQEntry).where(FAQEntry.needs_review == False)
        
        if category:
            query = query.where(FAQEntry.category == category)
        
        # Apply offset and limit
        query = query.offset(offset).limit(limit)
        
        # Execute search (simplified - would use full-text search in production)
        result = await db.execute(query)
        faqs = result.scalars().all()
        
        # Filter by tags if specified
        if tags:
            faqs = [faq for faq in faqs if any(tag in faq.tags for tag in tags)]
        
        # Convert to response models
        faq_responses = []
        for faq in faqs:
            faq_responses.append(FAQEntryResponse(
                id=faq.id,
                question=faq.question,
                answer=faq.answer,
                category=faq.category,
                tags=faq.tags or [],
                language=faq.language,
                last_validated=faq.last_validated,
                needs_review=faq.needs_review,
                update_sensitivity=faq.update_sensitivity.value,
                hit_count=faq.hit_count,
                last_used=faq.last_used,
                avg_helpfulness=faq.avg_helpfulness,
                version=faq.version,
                created_at=faq.created_at,
                updated_at=faq.updated_at
            ))
        
        end_time = time.perf_counter()
        query_time_ms = (end_time - start_time) * 1000
        
        return FAQSearchResponse(
            results=faq_responses,
            total_count=len(faq_responses),
            query_time_ms=query_time_ms,
            normalized_query=normalized_query
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching FAQs: {str(e)}"
        )


@router.get("/categories")
async def get_categories(
    include_stats: bool = Query(False, description="Include category statistics"),
    db: AsyncSession = Depends(get_async_db)
) -> List[Dict[str, Any]]:
    """
    Get all FAQ categories with optional statistics.
    """
    try:
        query = select(FAQCategory).where(FAQCategory.is_active == True).order_by(FAQCategory.sort_order)
        result = await db.execute(query)
        categories = result.scalars().all()
        
        category_list = []
        for category in categories:
            category_data = {
                "id": category.id,
                "name": category.name,
                "display_name": category.display_name,
                "description": category.description,
                "parent_category": category.parent_category,
                "sort_order": category.sort_order
            }
            
            if include_stats:
                category_data.update({
                    "faq_count": category.faq_count,
                    "total_hits": category.total_hits,
                    "avg_helpfulness": category.avg_helpfulness
                })
            
            category_list.append(category_data)
        
        return category_list
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching categories: {str(e)}"
        )


@router.get("/analytics", response_model=FAQAnalyticsResponse)
async def get_analytics(
    period_days: int = Query(7, ge=1, le=90, description="Analytics period in days"),
    period_type: str = Query("daily", pattern="^(daily|weekly|monthly)$", description="Period type"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_db)
) -> FAQAnalyticsResponse:
    """
    Get FAQ system analytics and performance metrics.
    
    Requires admin privileges.
    """
    try:
        # Calculate period
        period_end = datetime.now(timezone.utc)
        period_start = period_end - timedelta(days=period_days)
        
        faq_service = IntelligentFAQService(db)
        
        analytics = await faq_service.get_analytics_summary(
            period_start=period_start,
            period_end=period_end,
            period_type=period_type
        )
        
        return FAQAnalyticsResponse(**analytics)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching analytics: {str(e)}"
        )


# Admin endpoints for FAQ management

@router.post("/admin/entries", response_model=FAQEntryResponse)
async def create_faq(
    request: FAQCreateRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_db)
) -> FAQEntryResponse:
    """
    Create a new FAQ entry.
    
    Requires admin privileges.
    """
    try:
        faq_entry = await create_faq_entry(
            db=db,
            question=request.question,
            answer=request.answer,
            category=request.category,
            tags=request.tags,
            update_sensitivity=request.update_sensitivity
        )
        
        return FAQEntryResponse(
            id=faq_entry.id,
            question=faq_entry.question,
            answer=faq_entry.answer,
            category=faq_entry.category,
            tags=faq_entry.tags or [],
            language=faq_entry.language,
            last_validated=faq_entry.last_validated,
            needs_review=faq_entry.needs_review,
            update_sensitivity=faq_entry.update_sensitivity.value,
            hit_count=faq_entry.hit_count,
            last_used=faq_entry.last_used,
            avg_helpfulness=faq_entry.avg_helpfulness,
            version=faq_entry.version,
            created_at=faq_entry.created_at,
            updated_at=faq_entry.updated_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error creating FAQ: {str(e)}"
        )


@router.put("/admin/entries/{faq_id}", response_model=FAQEntryResponse)
async def update_faq(
    faq_id: str,
    request: FAQUpdateRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_db)
) -> FAQEntryResponse:
    """
    Update an existing FAQ entry with versioning.
    
    Requires admin privileges.
    """
    try:
        faq_entry = await update_faq_entry(
            db=db,
            faq_id=faq_id,
            question=request.question,
            answer=request.answer,
            tags=request.tags,
            change_reason=request.change_reason
        )
        
        if not faq_entry:
            raise HTTPException(
                status_code=404,
                detail="FAQ entry not found"
            )
        
        return FAQEntryResponse(
            id=faq_entry.id,
            question=faq_entry.question,
            answer=faq_entry.answer,
            category=faq_entry.category,
            tags=faq_entry.tags or [],
            language=faq_entry.language,
            last_validated=faq_entry.last_validated,
            needs_review=faq_entry.needs_review,
            update_sensitivity=faq_entry.update_sensitivity.value,
            hit_count=faq_entry.hit_count,
            last_used=faq_entry.last_used,
            avg_helpfulness=faq_entry.avg_helpfulness,
            version=faq_entry.version,
            created_at=faq_entry.created_at,
            updated_at=faq_entry.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error updating FAQ: {str(e)}"
        )


@router.get("/admin/entries/{faq_id}", response_model=FAQEntryResponse)
async def get_faq(
    faq_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_db)
) -> FAQEntryResponse:
    """
    Get a specific FAQ entry by ID.
    
    Requires admin privileges.
    """
    try:
        faq_entry = await db.get(FAQEntry, faq_id)
        
        if not faq_entry:
            raise HTTPException(
                status_code=404,
                detail="FAQ entry not found"
            )
        
        return FAQEntryResponse(
            id=faq_entry.id,
            question=faq_entry.question,
            answer=faq_entry.answer,
            category=faq_entry.category,
            tags=faq_entry.tags or [],
            language=faq_entry.language,
            last_validated=faq_entry.last_validated,
            needs_review=faq_entry.needs_review,
            update_sensitivity=faq_entry.update_sensitivity.value,
            hit_count=faq_entry.hit_count,
            last_used=faq_entry.last_used,
            avg_helpfulness=faq_entry.avg_helpfulness,
            version=faq_entry.version,
            created_at=faq_entry.created_at,
            updated_at=faq_entry.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching FAQ: {str(e)}"
        )


@router.delete("/admin/entries/{faq_id}")
async def delete_faq(
    faq_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """
    Delete a FAQ entry (soft delete - marks as needs review).
    
    Requires admin privileges.
    """
    try:
        faq_entry = await db.get(FAQEntry, faq_id)
        
        if not faq_entry:
            raise HTTPException(
                status_code=404,
                detail="FAQ entry not found"
            )
        
        # Soft delete by marking as needs review
        faq_entry.needs_review = True
        faq_entry.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        return {
            "success": True,
            "message": "FAQ entry marked for review (soft delete)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting FAQ: {str(e)}"
        )


@router.get("/admin/entries", response_model=FAQSearchResponse)
async def list_faqs(
    category: Optional[str] = Query(None, description="Filter by category"),
    needs_review: Optional[bool] = Query(None, description="Filter by review status"),
    limit: int = Query(50, ge=1, le=200, description="Number of results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_db)
) -> FAQSearchResponse:
    """
    List FAQ entries with admin filtering options.
    
    Requires admin privileges.
    """
    import time
    start_time = time.perf_counter()
    
    try:
        # Build query
        query = select(FAQEntry)
        
        if category:
            query = query.where(FAQEntry.category == category)
        
        if needs_review is not None:
            query = query.where(FAQEntry.needs_review == needs_review)
        
        # Apply ordering, offset and limit
        query = query.order_by(FAQEntry.updated_at.desc()).offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        faqs = result.scalars().all()
        
        # Convert to response models
        faq_responses = []
        for faq in faqs:
            faq_responses.append(FAQEntryResponse(
                id=faq.id,
                question=faq.question,
                answer=faq.answer,
                category=faq.category,
                tags=faq.tags or [],
                language=faq.language,
                last_validated=faq.last_validated,
                needs_review=faq.needs_review,
                update_sensitivity=faq.update_sensitivity.value,
                hit_count=faq.hit_count,
                last_used=faq.last_used,
                avg_helpfulness=faq.avg_helpfulness,
                version=faq.version,
                created_at=faq.created_at,
                updated_at=faq.updated_at
            ))
        
        end_time = time.perf_counter()
        query_time_ms = (end_time - start_time) * 1000
        
        return FAQSearchResponse(
            results=faq_responses,
            total_count=len(faq_responses),
            query_time_ms=query_time_ms
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing FAQs: {str(e)}"
        )


# Health check endpoint
@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    FAQ system health check.
    """
    return {
        "status": "healthy",
        "service": "Intelligent FAQ System",
        "version": "1.0.0",
        "features": [
            "Semantic search with Italian language support",
            "GPT-3.5 response variation",
            "Obsolescence detection",
            "Cost optimization",
            "Usage analytics"
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }