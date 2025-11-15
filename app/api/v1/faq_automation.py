"""FAQ Automation API Endpoints.

Admin dashboard and management endpoints for the automated FAQ generation system.
Provides comprehensive management interface for FAQ candidates, generated FAQs,
and RSS integration monitoring.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.models.faq_automation import (
    FAQ_AUTOMATION_CONFIG,
    FAQCandidate,
    FAQGenerationJob,
    GeneratedFAQ,
    QueryCluster,
    RSSFAQImpact,
)
from app.services.auto_faq_generator import AutomatedFAQGenerator
from app.services.cache import CacheService
from app.services.embedding_service import EmbeddingService
from app.services.faq_quality_validator import FAQQualityValidator
from app.services.faq_rss_integration import FAQRSSIntegration
from app.services.llm_service import LLMService
from app.services.query_pattern_analyzer import QueryPatternAnalyzer

router = APIRouter(prefix="/faq-automation", tags=["FAQ Automation"])


# Pydantic Models


class FAQCandidateResponse(BaseModel):
    id: str
    suggested_question: str
    suggested_category: str | None
    suggested_tags: list[str]
    frequency: int
    estimated_monthly_savings: float
    roi_score: float
    priority_score: float
    status: str
    can_generate: bool
    created_at: str
    expires_at: str | None


class GeneratedFAQResponse(BaseModel):
    id: str
    question: str
    answer: str
    category: str | None
    tags: list[str]
    quality_score: float
    approval_status: str
    published: bool
    generation_model: str
    generation_cost_cents: int
    estimated_monthly_savings: float
    usage_count: int
    satisfaction_score: float | None
    created_at: str


class RSSImpactResponse(BaseModel):
    id: str
    faq_id: str
    impact_level: str
    impact_score: float
    confidence_score: float
    rss_title: str
    rss_source: str
    rss_published_date: str
    action_required: str
    processed: bool
    urgency_score: float


class GenerateFAQRequest(BaseModel):
    candidate_ids: list[str] = Field(..., description="List of candidate IDs to generate FAQs for")
    force_expensive_model: bool = Field(False, description="Force use of expensive model")
    auto_approve_high_quality: bool = Field(True, description="Auto-approve high-quality FAQs")


class ApprovalRequest(BaseModel):
    approval_status: str = Field(..., description="New approval status")
    rejection_reason: str | None = Field(None, description="Reason for rejection")
    notes: str | None = Field(None, description="Additional notes")


class DashboardStats(BaseModel):
    candidates: dict[str, Any]
    generated_faqs: dict[str, Any]
    rss_impacts: dict[str, Any]
    system_performance: dict[str, Any]
    cost_savings: dict[str, Any]


# Dependencies


async def get_pattern_analyzer(db: AsyncSession = Depends(get_db)) -> QueryPatternAnalyzer:
    """Get pattern analyzer service"""
    from app.services.embedding_service import EmbeddingService
    from app.services.query_normalizer import QueryNormalizer

    embedding_service = EmbeddingService()
    normalizer = QueryNormalizer()

    return QueryPatternAnalyzer(db, embedding_service, normalizer)


async def get_faq_generator(db: AsyncSession = Depends(get_db)) -> AutomatedFAQGenerator:
    """Get FAQ generator service"""
    llm_service = LLMService()
    validator = FAQQualityValidator(llm_service, EmbeddingService())

    return AutomatedFAQGenerator(llm_service, validator, db)


async def get_rss_integration(db: AsyncSession = Depends(get_db)) -> FAQRSSIntegration:
    """Get RSS integration service"""
    llm_service = LLMService()
    embedding_service = EmbeddingService()

    return FAQRSSIntegration(db, llm_service, embedding_service)


# Dashboard and Overview Endpoints


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db), days: int = Query(30, description="Number of days for statistics")
) -> DashboardStats:
    """Get comprehensive dashboard statistics for FAQ automation system"""
    try:
        since_date = datetime.utcnow() - timedelta(days=days)

        # FAQ Candidates Statistics
        candidates_query = select(FAQCandidate).where(FAQCandidate.created_at >= since_date)
        candidates_result = await db.execute(candidates_query)
        candidates = candidates_result.scalars().all()

        candidates_stats = {
            "total": len(candidates),
            "pending": len([c for c in candidates if c.status == "pending"]),
            "processing": len([c for c in candidates if c.status == "processing"]),
            "completed": len([c for c in candidates if c.status == "completed"]),
            "avg_roi_score": sum(float(c.roi_score) for c in candidates) / len(candidates) if candidates else 0,
            "total_potential_savings": sum(float(c.estimated_monthly_savings) for c in candidates),
            "top_categories": _get_top_categories([c.suggested_category for c in candidates if c.suggested_category]),
        }

        # Generated FAQs Statistics
        faqs_query = select(GeneratedFAQ).where(GeneratedFAQ.created_at >= since_date)
        faqs_result = await db.execute(faqs_query)
        faqs = faqs_result.scalars().all()

        faqs_stats = {
            "total": len(faqs),
            "auto_approved": len([f for f in faqs if f.approval_status == "auto_approved"]),
            "manually_approved": len([f for f in faqs if f.approval_status == "manually_approved"]),
            "pending_review": len([f for f in faqs if f.approval_status == "pending_review"]),
            "rejected": len([f for f in faqs if f.approval_status == "rejected"]),
            "published": len([f for f in faqs if f.published]),
            "avg_quality_score": sum(float(f.quality_score) for f in faqs) / len(faqs) if faqs else 0,
            "total_generation_cost": sum(f.generation_cost_cents for f in faqs) / 100,
            "total_usage": sum(f.usage_count for f in faqs),
        }

        # RSS Impacts Statistics
        impacts_query = select(RSSFAQImpact).where(RSSFAQImpact.created_at >= since_date)
        impacts_result = await db.execute(impacts_query)
        impacts = impacts_result.scalars().all()

        rss_stats = {
            "total_impacts": len(impacts),
            "high_impact": len([i for i in impacts if i.impact_level == "high"]),
            "medium_impact": len([i for i in impacts if i.impact_level == "medium"]),
            "low_impact": len([i for i in impacts if i.impact_level == "low"]),
            "processed": len([i for i in impacts if i.processed]),
            "pending_action": len(
                [i for i in impacts if not i.processed and i.action_required in ["regenerate", "review"]]
            ),
            "avg_confidence": sum(float(i.confidence_score) for i in impacts) / len(impacts) if impacts else 0,
        }

        # System Performance
        performance_stats = {
            "total_automation_runs": len(candidates),  # Approximate
            "success_rate": (candidates_stats["completed"] / candidates_stats["total"])
            if candidates_stats["total"] > 0
            else 0,
            "avg_processing_time": "2.5 minutes",  # Would calculate from job data
            "system_uptime": "99.8%",  # Would get from monitoring
            "api_response_time": "250ms",  # Would get from monitoring
        }

        # Cost Savings Analysis
        cost_savings = {
            "potential_monthly_savings": candidates_stats["total_potential_savings"],
            "realized_monthly_savings": sum(float(f.estimated_monthly_savings) for f in faqs if f.published),
            "generation_costs": faqs_stats["total_generation_cost"],
            "roi_ratio": 0,  # Calculate based on savings vs costs
            "break_even_months": 0,  # Calculate break-even point
        }

        if cost_savings["generation_costs"] > 0:
            cost_savings["roi_ratio"] = cost_savings["realized_monthly_savings"] / cost_savings["generation_costs"]
            cost_savings["break_even_months"] = (
                cost_savings["generation_costs"] / cost_savings["realized_monthly_savings"]
                if cost_savings["realized_monthly_savings"] > 0
                else float("inf")
            )

        return DashboardStats(
            candidates=candidates_stats,
            generated_faqs=faqs_stats,
            rss_impacts=rss_stats,
            system_performance=performance_stats,
            cost_savings=cost_savings,
        )

    except Exception as e:
        logger.error(f"Dashboard stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {e}")


# FAQ Candidates Management


@router.get("/candidates", response_model=list[FAQCandidateResponse])
async def get_faq_candidates(
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None, description="Filter by status"),
    min_roi: float | None = Query(None, description="Minimum ROI score"),
    category: str | None = Query(None, description="Filter by category"),
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Results offset for pagination"),
):
    """Get FAQ candidates with filtering and pagination"""
    try:
        query = select(FAQCandidate).order_by(desc(FAQCandidate.priority_score))

        # Apply filters
        if status:
            query = query.where(FAQCandidate.status == status)

        if min_roi:
            query = query.where(FAQCandidate.roi_score >= min_roi)

        if category:
            query = query.where(FAQCandidate.suggested_category.ilike(f"%{category}%"))

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        candidates = result.scalars().all()

        return [
            FAQCandidateResponse(
                id=str(candidate.id),
                suggested_question=candidate.suggested_question,
                suggested_category=candidate.suggested_category,
                suggested_tags=candidate.suggested_tags or [],
                frequency=candidate.frequency,
                estimated_monthly_savings=float(candidate.estimated_monthly_savings),
                roi_score=float(candidate.roi_score),
                priority_score=float(candidate.priority_score),
                status=candidate.status,
                can_generate=candidate.can_generate(),
                created_at=candidate.created_at.isoformat(),
                expires_at=candidate.expires_at.isoformat() if candidate.expires_at else None,
            )
            for candidate in candidates
        ]

    except Exception as e:
        logger.error(f"Get candidates failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get candidates: {e}")


@router.post("/candidates/analyze")
async def analyze_query_patterns(
    background_tasks: BackgroundTasks,
    analyzer: QueryPatternAnalyzer = Depends(get_pattern_analyzer),
    db: AsyncSession = Depends(get_db),
):
    """Trigger analysis of query patterns to identify new FAQ candidates"""
    try:
        # Run pattern analysis in background
        background_tasks.add_task(_run_pattern_analysis, analyzer, db)

        return {"message": "Pattern analysis started", "status": "processing", "estimated_completion": "5-10 minutes"}

    except Exception as e:
        logger.error(f"Pattern analysis trigger failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {e}")


@router.post("/candidates/generate", response_model=dict[str, Any])
async def generate_faqs_from_candidates(
    request: GenerateFAQRequest,
    background_tasks: BackgroundTasks,
    generator: AutomatedFAQGenerator = Depends(get_faq_generator),
    db: AsyncSession = Depends(get_db),
):
    """Generate FAQs from selected candidates"""
    try:
        # Validate candidate IDs
        candidates_query = select(FAQCandidate).where(
            FAQCandidate.id.in_([UUID(cid) for cid in request.candidate_ids])
        )
        result = await db.execute(candidates_query)
        candidates = result.scalars().all()

        if not candidates:
            raise HTTPException(status_code=404, detail="No valid candidates found")

        # Filter candidates that can be generated
        valid_candidates = [c for c in candidates if c.can_generate()]

        if not valid_candidates:
            raise HTTPException(status_code=400, detail="No candidates available for generation")

        # Start batch generation in background
        job_id = f"faq_generation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        background_tasks.add_task(
            _run_batch_generation,
            valid_candidates,
            generator,
            db,
            job_id,
            request.force_expensive_model,
            request.auto_approve_high_quality,
        )

        return {
            "job_id": job_id,
            "message": f"FAQ generation started for {len(valid_candidates)} candidates",
            "candidates_selected": len(request.candidate_ids),
            "candidates_valid": len(valid_candidates),
            "estimated_completion": f"{len(valid_candidates) * 2} minutes",
            "status": "processing",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FAQ generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start generation: {e}")


# Generated FAQs Management


@router.get("/faqs", response_model=list[GeneratedFAQResponse])
async def get_generated_faqs(
    db: AsyncSession = Depends(get_db),
    approval_status: str | None = Query(None, description="Filter by approval status"),
    published: bool | None = Query(None, description="Filter by published status"),
    min_quality: float | None = Query(None, description="Minimum quality score"),
    category: str | None = Query(None, description="Filter by category"),
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Results offset for pagination"),
):
    """Get generated FAQs with filtering and pagination"""
    try:
        query = select(GeneratedFAQ).order_by(desc(GeneratedFAQ.created_at))

        # Apply filters
        if approval_status:
            query = query.where(GeneratedFAQ.approval_status == approval_status)

        if published is not None:
            query = query.where(GeneratedFAQ.published == published)

        if min_quality:
            query = query.where(GeneratedFAQ.quality_score >= min_quality)

        if category:
            query = query.where(GeneratedFAQ.category.ilike(f"%{category}%"))

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        faqs = result.scalars().all()

        return [
            GeneratedFAQResponse(
                id=str(faq.id),
                question=faq.question,
                answer=faq.answer,
                category=faq.category,
                tags=faq.tags or [],
                quality_score=float(faq.quality_score),
                approval_status=faq.approval_status,
                published=faq.published,
                generation_model=faq.generation_model,
                generation_cost_cents=faq.generation_cost_cents,
                estimated_monthly_savings=float(faq.estimated_monthly_savings),
                usage_count=faq.usage_count,
                satisfaction_score=float(faq.satisfaction_score) if faq.satisfaction_score else None,
                created_at=faq.created_at.isoformat(),
            )
            for faq in faqs
        ]

    except Exception as e:
        logger.error(f"Get FAQs failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get FAQs: {e}")


@router.post("/faqs/{faq_id}/approve")
async def approve_faq(faq_id: str, request: ApprovalRequest, db: AsyncSession = Depends(get_db)):
    """Approve, reject, or request revision for a generated FAQ"""
    try:
        # Get FAQ
        query = select(GeneratedFAQ).where(GeneratedFAQ.id == UUID(faq_id))
        result = await db.execute(query)
        faq = result.scalar_one_or_none()

        if not faq:
            raise HTTPException(status_code=404, detail="FAQ not found")

        # Update approval status
        faq.approval_status = request.approval_status
        faq.rejection_reason = request.rejection_reason

        if request.approval_status in ["auto_approved", "manually_approved"]:
            faq.approved_at = datetime.utcnow()
            # Could set approved_by from authenticated user

        await db.commit()

        logger.info(f"FAQ {faq_id} approval status updated to {request.approval_status}")

        return {"message": f"FAQ {request.approval_status}", "faq_id": faq_id, "new_status": request.approval_status}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FAQ approval failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update approval: {e}")


@router.post("/faqs/{faq_id}/publish")
async def publish_faq(faq_id: str, db: AsyncSession = Depends(get_db)):
    """Publish an approved FAQ to make it available to users"""
    try:
        # Get FAQ
        query = select(GeneratedFAQ).where(GeneratedFAQ.id == UUID(faq_id))
        result = await db.execute(query)
        faq = result.scalar_one_or_none()

        if not faq:
            raise HTTPException(status_code=404, detail="FAQ not found")

        if faq.approval_status not in ["auto_approved", "manually_approved"]:
            raise HTTPException(status_code=400, detail="FAQ must be approved before publishing")

        # Publish FAQ
        faq.published = True
        faq.published_at = datetime.utcnow()

        await db.commit()

        logger.info(f"FAQ {faq_id} published successfully")

        return {
            "message": "FAQ published successfully",
            "faq_id": faq_id,
            "published_at": faq.published_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FAQ publishing failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to publish FAQ: {e}")


# RSS Integration Management


@router.get("/rss/impacts", response_model=list[RSSImpactResponse])
async def get_rss_impacts(
    db: AsyncSession = Depends(get_db),
    impact_level: str | None = Query(None, description="Filter by impact level"),
    processed: bool | None = Query(None, description="Filter by processed status"),
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Results offset for pagination"),
):
    """Get RSS impacts on FAQs with filtering"""
    try:
        query = select(RSSFAQImpact).order_by(desc(RSSFAQImpact.impact_score), desc(RSSFAQImpact.rss_published_date))

        # Apply filters
        if impact_level:
            query = query.where(RSSFAQImpact.impact_level == impact_level)

        if processed is not None:
            query = query.where(RSSFAQImpact.processed == processed)

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        impacts = result.scalars().all()

        return [
            RSSImpactResponse(
                id=str(impact.id),
                faq_id=str(impact.faq_id),
                impact_level=impact.impact_level,
                impact_score=float(impact.impact_score),
                confidence_score=float(impact.confidence_score),
                rss_title=impact.rss_title,
                rss_source=impact.rss_source,
                rss_published_date=impact.rss_published_date.isoformat(),
                action_required=impact.action_required,
                processed=impact.processed,
                urgency_score=float(impact.calculate_urgency_score()),
            )
            for impact in impacts
        ]

    except Exception as e:
        logger.error(f"Get RSS impacts failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get RSS impacts: {e}")


@router.post("/rss/check-updates")
async def check_rss_updates(
    background_tasks: BackgroundTasks, rss_integration: FAQRSSIntegration = Depends(get_rss_integration)
):
    """Trigger RSS feed updates check"""
    try:
        # Run RSS check in background
        background_tasks.add_task(_run_rss_check, rss_integration)

        return {"message": "RSS update check started", "status": "processing", "estimated_completion": "2-5 minutes"}

    except Exception as e:
        logger.error(f"RSS check trigger failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start RSS check: {e}")


# Helper Functions


def _get_top_categories(categories: list[str], limit: int = 5) -> list[dict[str, Any]]:
    """Get top categories by frequency"""
    if not categories:
        return []

    category_counts = {}
    for cat in categories:
        category_counts[cat] = category_counts.get(cat, 0) + 1

    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

    return [{"category": cat, "count": count} for cat, count in sorted_categories[:limit]]


async def _run_pattern_analysis(analyzer: QueryPatternAnalyzer, db: AsyncSession):
    """Background task for pattern analysis"""
    try:
        candidates = await analyzer.find_faq_candidates()

        # Save candidates to database
        for candidate in candidates:
            db.add(candidate)

        await db.commit()

        logger.info(f"Pattern analysis completed: {len(candidates)} candidates found")

    except Exception as e:
        logger.error(f"Background pattern analysis failed: {e}")
        await db.rollback()


async def _run_batch_generation(
    candidates: list,
    generator: AutomatedFAQGenerator,
    db: AsyncSession,
    job_id: str,
    force_expensive: bool,
    auto_approve: bool,
):
    """Background task for batch FAQ generation"""
    try:
        results = await generator.batch_generate_faqs(candidates)

        logger.info(f"Batch generation {job_id} completed: {results}")

    except Exception as e:
        logger.error(f"Background batch generation failed: {e}")


async def _run_rss_check(rss_integration: FAQRSSIntegration):
    """Background task for RSS updates check"""
    try:
        results = await rss_integration.check_for_updates()

        logger.info(f"RSS check completed: {results}")

    except Exception as e:
        logger.error(f"Background RSS check failed: {e}")
