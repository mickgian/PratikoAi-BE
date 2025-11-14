"""Health check endpoints for system components."""

from datetime import (
    datetime,
    timezone,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.logging import logger
from app.models.database import get_db
from app.models.regulatory_documents import (
    FeedStatus,
    RegulatoryDocument,
)
from app.models.user import User
from app.services.dynamic_knowledge_collector import DynamicKnowledgeCollector
from app.services.scheduler_service import scheduler_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/rss")
async def rss_health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Check RSS feed collection health.

    Returns:
        - Scheduler status (enabled, last run, next run)
        - Feed status for all configured feeds
        - Document collection statistics
        - Overall health status
    """
    try:
        # Get scheduler status
        scheduler_tasks = scheduler_service.get_task_status()
        rss_task = scheduler_tasks.get("rss_feeds_4h", {})

        # Get feed status from database
        result = await db.execute(select(FeedStatus).order_by(FeedStatus.last_checked.desc()))
        feeds = result.scalars().all()

        # Get document collection stats
        doc_stats_result = await db.execute(
            select(
                RegulatoryDocument.source,
                func.count(RegulatoryDocument.id).label("count"),
                func.max(RegulatoryDocument.created_at).label("last_collected"),
            ).group_by(RegulatoryDocument.source)
        )
        doc_stats = doc_stats_result.all()

        # Calculate total documents
        total_documents = sum(stat.count for stat in doc_stats)

        # Determine overall health
        healthy_feeds = sum(1 for f in feeds if f.status == "healthy" or f.consecutive_errors == 0)
        total_feeds = len(feeds)

        health_status = (
            "healthy"
            if healthy_feeds == total_feeds
            else "degraded" if healthy_feeds > 0 else "unhealthy" if total_feeds > 0 else "no_data"
        )

        return {
            "status": health_status,
            "scheduler": {
                "enabled": rss_task.get("enabled", False),
                "last_run": rss_task.get("last_run"),
                "next_run": rss_task.get("next_run"),
                "overdue": rss_task.get("overdue", False),
                "interval": rss_task.get("interval", "unknown"),
            },
            "feeds": [
                {
                    "feed_name": f.source or "unknown",
                    "feed_type": f.feed_type or "unknown",
                    "url": f.feed_url,
                    "status": f.status,
                    "last_checked": f.last_checked.isoformat() if f.last_checked else None,
                    "last_success": f.last_success.isoformat() if f.last_success else None,
                    "items_found": f.items_found,
                    "response_time_ms": f.response_time_ms,
                    "consecutive_errors": f.consecutive_errors,
                    "total_errors": f.errors,
                    "last_error": f.last_error,
                    "enabled": f.enabled,
                }
                for f in feeds
            ],
            "documents": {
                "total": total_documents,
                "by_source": [
                    {
                        "source": stat.source,
                        "count": stat.count,
                        "last_collected": stat.last_collected.isoformat() if stat.last_collected else None,
                    }
                    for stat in doc_stats
                ],
            },
            "summary": {
                "total_feeds": total_feeds,
                "healthy_feeds": healthy_feeds,
                "unhealthy_feeds": total_feeds - healthy_feeds,
                "total_documents_collected": total_documents,
            },
        }

    except Exception as e:
        logger.error("rss_health_check_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get RSS health status: {str(e)}")


@router.get("/rss/feeds")
async def get_feed_status(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Get detailed status for all RSS feeds.

    Returns list of all configured feeds with their health metrics.
    """
    try:
        result = await db.execute(select(FeedStatus).order_by(FeedStatus.source, FeedStatus.feed_type))
        feeds = result.scalars().all()

        return [
            {
                "id": f.id,
                "source": f.source,
                "feed_type": f.feed_type,
                "url": f.feed_url,
                "status": f.status,
                "enabled": f.enabled,
                "last_checked": f.last_checked.isoformat() if f.last_checked else None,
                "last_success": f.last_success.isoformat() if f.last_success else None,
                "last_error_at": f.last_error_at.isoformat() if f.last_error_at else None,
                "items_found": f.items_found,
                "response_time_ms": f.response_time_ms,
                "consecutive_errors": f.consecutive_errors,
                "total_errors": f.errors,
                "last_error": f.last_error,
                "check_interval_minutes": f.check_interval_minutes,
            }
            for f in feeds
        ]

    except Exception as e:
        logger.error("get_feed_status_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get feed status: {str(e)}")


@router.get("/rss/documents")
async def get_document_stats(db: AsyncSession = Depends(get_db), limit: int = 20) -> Dict[str, Any]:
    """
    Get recent document collection statistics.

    Args:
        limit: Number of recent documents to return (default: 20)

    Returns:
        - Total document count
        - Recent documents
        - Stats by source
    """
    try:
        # Get total count
        count_result = await db.execute(select(func.count(RegulatoryDocument.id)))
        total_count = count_result.scalar()

        # Get recent documents
        recent_result = await db.execute(
            select(RegulatoryDocument).order_by(RegulatoryDocument.created_at.desc()).limit(limit)
        )
        recent_docs = recent_result.scalars().all()

        # Get stats by source and status
        stats_result = await db.execute(
            select(
                RegulatoryDocument.source, RegulatoryDocument.status, func.count(RegulatoryDocument.id).label("count")
            ).group_by(RegulatoryDocument.source, RegulatoryDocument.status)
        )
        stats = stats_result.all()

        return {
            "total_documents": total_count,
            "recent_documents": [
                {
                    "id": doc.id,
                    "source": doc.source,
                    "source_type": doc.source_type,
                    "title": doc.title,
                    "url": doc.url,
                    "status": doc.status.value if hasattr(doc.status, "value") else doc.status,
                    "published_date": doc.published_date.isoformat() if doc.published_date else None,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                }
                for doc in recent_docs
            ],
            "stats_by_source": [
                {
                    "source": stat.source,
                    "status": stat.status.value if hasattr(stat.status, "value") else stat.status,
                    "count": stat.count,
                }
                for stat in stats
            ],
        }

    except Exception as e:
        logger.error("get_document_stats_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get document stats: {str(e)}")


@router.post("/rss/collect")
async def trigger_manual_rss_collection(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    sources: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Manually trigger RSS feed collection.

    This endpoint allows authenticated users to trigger RSS collection on-demand
    without waiting for the scheduled collection (which runs every 4 hours).

    Args:
        sources: Optional list of source names to filter (e.g., ["agenzia_entrate", "inps"])
                If not provided, collects from all configured feeds
        current_user: Authenticated user (required)
        db: Database session

    Returns:
        - Collection results with statistics
        - Processing time
        - New documents found
        - Errors encountered

    Note:
        This operation may take several minutes depending on feed responsiveness
        and the number of new documents to process.
    """
    start_time = datetime.now(timezone.utc)

    try:
        logger.info(
            "manual_rss_collection_triggered", user_id=current_user.id, user_email=current_user.email, sources=sources
        )

        # Create collector instance
        collector = DynamicKnowledgeCollector(db)

        # Collect from all or specific sources
        if sources and len(sources) > 0:
            logger.info("collecting_from_specific_sources", sources=sources)
            results = await collector.collect_from_specific_sources(sources)
        else:
            logger.info("collecting_from_all_sources")
            results = await collector.collect_and_process_updates()

        # Calculate total statistics
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        total_feeds = len(results)
        successful_feeds = sum(1 for r in results if r.get("success", False))
        failed_feeds = total_feeds - successful_feeds
        total_new_documents = sum(len(r.get("new_documents", [])) for r in results if r.get("success", False))

        # Get collector statistics
        stats = collector.get_processing_stats()

        logger.info(
            "manual_rss_collection_completed",
            user_id=current_user.id,
            processing_time_seconds=processing_time,
            total_feeds=total_feeds,
            successful_feeds=successful_feeds,
            failed_feeds=failed_feeds,
            total_new_documents=total_new_documents,
        )

        return {
            "success": True,
            "triggered_by": {"user_id": current_user.id, "user_email": current_user.email},
            "triggered_at": start_time.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "processing_time_seconds": processing_time,
            "summary": {
                "total_feeds": total_feeds,
                "successful_feeds": successful_feeds,
                "failed_feeds": failed_feeds,
                "total_new_documents": total_new_documents,
            },
            "collector_stats": stats,
            "feed_results": results,
        }

    except Exception as e:
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        logger.error(
            "manual_rss_collection_failed",
            user_id=current_user.id,
            processing_time_seconds=processing_time,
            error=str(e),
            exc_info=True,
        )

        raise HTTPException(status_code=500, detail=f"RSS collection failed: {str(e)}")
