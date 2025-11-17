"""Regulatory Updates API endpoints for Dynamic Knowledge Collection System.

These endpoints provide access to Italian regulatory documents and
allow manual triggering of document collection processes.
"""

import time
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_session
from app.core.database import get_async_session
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.regulatory_documents import DocumentProcessingLog, FeedStatus, ProcessingStatus, RegulatoryDocument
from app.models.session import Session
from app.services.dynamic_knowledge_collector import DynamicKnowledgeCollector
from app.services.rss_feed_monitor import FeedHealthMonitor
from app.services.scheduler_service import scheduler_service

router = APIRouter()


class TriggerCollectionRequest(BaseModel):
    """Request model for triggering document collection."""

    sources: list[str] | None = Field(
        default=None, description="Specific sources to collect from (e.g., ['agenzia_entrate', 'inps'])"
    )
    immediate: bool = Field(
        default=True, description="Whether to run collection immediately or schedule for next interval"
    )


class DocumentSearchRequest(BaseModel):
    """Request model for searching regulatory documents."""

    query: str | None = Field(default=None, description="Search query")
    source: str | None = Field(default=None, description="Filter by source authority")
    document_type: str | None = Field(default=None, description="Filter by document type")
    date_from: datetime | None = Field(default=None, description="Filter by date from")
    date_to: datetime | None = Field(default=None, description="Filter by date to")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Results offset")


@router.get(
    "/documents",
    summary="Get regulatory documents",
    description="Retrieve regulatory documents with optional filtering and pagination",
)
@limiter.limit("100 per hour")
async def get_regulatory_documents(
    request: Request,
    source: str | None = Query(None, description="Filter by source (agenzia_entrate, inps, etc.)"),
    document_type: str | None = Query(None, description="Filter by document type"),
    status: str | None = Query("active", description="Filter by status"),
    date_from: datetime | None = Query(None, description="Filter by date from"),
    date_to: datetime | None = Query(None, description="Filter by date to"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_async_session),
):
    """Get regulatory documents with filtering and pagination."""
    try:
        start_time = time.time()

        # Build query
        query = select(RegulatoryDocument).where(RegulatoryDocument.status == status)

        # Add filters
        if source:
            query = query.where(RegulatoryDocument.source == source)

        if document_type:
            query = query.where(RegulatoryDocument.source_type == document_type)

        if date_from:
            query = query.where(RegulatoryDocument.published_date >= date_from)

        if date_to:
            query = query.where(RegulatoryDocument.published_date <= date_to)

        # Order by most recent first
        query = query.order_by(desc(RegulatoryDocument.published_date))

        # Add pagination
        query = query.offset(offset).limit(limit)

        # Execute query
        result = await db.execute(query)
        documents = result.scalars().all()

        # Convert to response format
        documents_data = []
        for doc in documents:
            doc_data = {
                "id": doc.id,
                "title": doc.title,
                "source": doc.source,
                "source_type": doc.source_type,
                "authority": doc.authority,
                "url": doc.url,
                "published_date": doc.published_date.isoformat() if doc.published_date else None,
                "document_number": doc.document_number,
                "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                "content_length": len(doc.content),
                "version": doc.version,
                "status": doc.status,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat(),
                "metadata": doc.metadata,
            }
            documents_data.append(doc_data)

        # Get total count for pagination
        count_query = select(func.count(RegulatoryDocument.id)).where(RegulatoryDocument.status == status)

        if source:
            count_query = count_query.where(RegulatoryDocument.source == source)
        if document_type:
            count_query = count_query.where(RegulatoryDocument.source_type == document_type)
        if date_from:
            count_query = count_query.where(RegulatoryDocument.published_date >= date_from)
        if date_to:
            count_query = count_query.where(RegulatoryDocument.published_date <= date_to)

        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "regulatory_documents_retrieved",
            user_id=session.user_id,
            results_count=len(documents_data),
            total_count=total_count,
            filters={
                "source": source,
                "document_type": document_type,
                "status": status,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
            },
            response_time_ms=response_time_ms,
        )

        return JSONResponse(
            {
                "documents": documents_data,
                "pagination": {
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset,
                    "page": offset // limit + 1,
                    "total_pages": (total_count + limit - 1) // limit,
                },
                "filters": {
                    "source": source,
                    "document_type": document_type,
                    "status": status,
                    "date_from": date_from.isoformat() if date_from else None,
                    "date_to": date_to.isoformat() if date_to else None,
                },
                "response_time_ms": round(response_time_ms, 2),
            }
        )

    except Exception as e:
        logger.error("regulatory_documents_retrieval_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve regulatory documents")


@router.get(
    "/documents/{document_id}",
    summary="Get specific regulatory document",
    description="Retrieve a specific regulatory document by ID",
)
@limiter.limit("200 per hour")
async def get_regulatory_document(
    request: Request,
    document_id: str,
    include_content: bool = Query(True, description="Include full document content"),
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_async_session),
):
    """Get a specific regulatory document by ID."""
    try:
        # Find document
        query = select(RegulatoryDocument).where(RegulatoryDocument.id == document_id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Build response
        doc_data = {
            "id": document.id,
            "title": document.title,
            "source": document.source,
            "source_type": document.source_type,
            "authority": document.authority,
            "url": document.url,
            "published_date": document.published_date.isoformat() if document.published_date else None,
            "document_number": document.document_number,
            "version": document.version,
            "status": document.status,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat(),
            "processed_at": document.processed_at.isoformat() if document.processed_at else None,
            "metadata": document.metadata,
            "content_hash": document.content_hash,
            "importance_score": document.importance_score,
            "topics": document.topics,
        }

        if include_content:
            doc_data["content"] = document.content
            doc_data["content_length"] = len(document.content)
        else:
            doc_data["content_preview"] = (
                document.content[:500] + "..." if len(document.content) > 500 else document.content
            )
            doc_data["content_length"] = len(document.content)

        # Check for related versions
        if document.previous_version_id:
            # Find previous version
            prev_query = select(RegulatoryDocument).where(RegulatoryDocument.id == document.previous_version_id)
            prev_result = await db.execute(prev_query)
            prev_doc = prev_result.scalar_one_or_none()
            if prev_doc:
                doc_data["previous_version"] = {
                    "id": prev_doc.id,
                    "version": prev_doc.version,
                    "title": prev_doc.title,
                    "updated_at": prev_doc.updated_at.isoformat(),
                }

        # Find newer versions
        newer_query = (
            select(RegulatoryDocument)
            .where(RegulatoryDocument.previous_version_id == document_id)
            .order_by(desc(RegulatoryDocument.version))
        )
        newer_result = await db.execute(newer_query)
        newer_docs = newer_result.scalars().all()

        if newer_docs:
            doc_data["newer_versions"] = [
                {
                    "id": newer_doc.id,
                    "version": newer_doc.version,
                    "title": newer_doc.title,
                    "updated_at": newer_doc.updated_at.isoformat(),
                }
                for newer_doc in newer_docs
            ]

        logger.info(
            "regulatory_document_retrieved",
            user_id=session.user_id,
            document_id=document_id,
            include_content=include_content,
        )

        return JSONResponse(doc_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "regulatory_document_retrieval_failed",
            session_id=session.id,
            document_id=document_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve regulatory document")


@router.post(
    "/collect/trigger",
    summary="Trigger document collection",
    description="Manually trigger collection of regulatory documents",
)
@limiter.limit("5 per hour")
async def trigger_document_collection(
    request: Request,
    collection_request: TriggerCollectionRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_async_session),
):
    """Trigger manual collection of regulatory documents."""
    try:
        logger.info(
            "manual_collection_triggered",
            user_id=session.user_id,
            sources=collection_request.sources,
            immediate=collection_request.immediate,
        )

        if collection_request.immediate:
            # Run collection immediately in background
            background_tasks.add_task(run_immediate_collection, collection_request.sources, db, session.user_id)

            return JSONResponse(
                {
                    "status": "triggered",
                    "message": "Document collection started in background",
                    "sources": collection_request.sources,
                    "triggered_by": session.user_id,
                    "triggered_at": datetime.now(UTC).isoformat(),
                }
            )
        else:
            # Trigger via scheduler service
            result = await scheduler_service.trigger_immediate_collection(sources=collection_request.sources)

            return JSONResponse(
                {
                    "status": "scheduled",
                    "message": "Document collection scheduled",
                    "scheduler_result": result,
                    "triggered_by": session.user_id,
                    "triggered_at": datetime.now(UTC).isoformat(),
                }
            )

    except Exception as e:
        logger.error(
            "collection_trigger_failed",
            session_id=session.id,
            sources=collection_request.sources,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to trigger document collection")


@router.get(
    "/collect/status",
    summary="Get collection status",
    description="Get status of scheduled and recent collection jobs",
)
@limiter.limit("60 per hour")
async def get_collection_status(
    request: Request, session: Session = Depends(get_current_session), db: AsyncSession = Depends(get_async_session)
):
    """Get status of document collection jobs."""
    try:
        # Get scheduler status
        scheduler_status = await scheduler_service.get_job_status()

        # Get recent processing logs
        recent_logs_query = (
            select(DocumentProcessingLog)
            .where(DocumentProcessingLog.created_at >= datetime.now(UTC) - timedelta(hours=24))
            .order_by(desc(DocumentProcessingLog.created_at))
            .limit(50)
        )

        logs_result = await db.execute(recent_logs_query)
        recent_logs = logs_result.scalars().all()

        # Convert logs to response format
        logs_data = []
        for log in recent_logs:
            log_data = {
                "id": log.id,
                "document_url": log.document_url,
                "operation": log.operation,
                "status": log.status,
                "processing_time_ms": log.processing_time_ms,
                "error_message": log.error_message,
                "triggered_by": log.triggered_by,
                "feed_url": log.feed_url,
                "created_at": log.created_at.isoformat(),
            }
            logs_data.append(log_data)

        # Get collection statistics
        stats_query = select(
            func.count(DocumentProcessingLog.id).label("total_operations"),
            func.sum(func.case((DocumentProcessingLog.status == "success", 1), else_=0)).label(
                "successful_operations"
            ),
            func.sum(func.case((DocumentProcessingLog.status == "failed", 1), else_=0)).label("failed_operations"),
            func.avg(DocumentProcessingLog.processing_time_ms).label("avg_processing_time_ms"),
        ).where(DocumentProcessingLog.created_at >= datetime.now(UTC) - timedelta(hours=24))

        stats_result = await db.execute(stats_query)
        stats_row = stats_result.first()

        collection_stats = {
            "total_operations_24h": stats_row.total_operations or 0,
            "successful_operations_24h": stats_row.successful_operations or 0,
            "failed_operations_24h": stats_row.failed_operations or 0,
            "avg_processing_time_ms": round(stats_row.avg_processing_time_ms or 0, 2),
            "success_rate_24h": round(
                (stats_row.successful_operations or 0) / max(stats_row.total_operations or 1, 1) * 100, 2
            ),
        }

        logger.info("collection_status_retrieved", user_id=session.user_id, recent_logs_count=len(logs_data))

        return JSONResponse(
            {
                "scheduler_status": scheduler_status,
                "recent_processing_logs": logs_data,
                "collection_statistics": collection_stats,
                "status_timestamp": datetime.now(UTC).isoformat(),
            }
        )

    except Exception as e:
        logger.error("collection_status_retrieval_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve collection status")


@router.get("/feeds/health", summary="Get feed health status", description="Get health status of all RSS feeds")
@limiter.limit("30 per hour")
async def get_feeds_health(
    request: Request, session: Session = Depends(get_current_session), db: AsyncSession = Depends(get_async_session)
):
    """Get health status of all RSS feeds."""
    try:
        # Get feed health from database
        feeds_query = select(FeedStatus).order_by(desc(FeedStatus.last_checked))
        feeds_result = await db.execute(feeds_query)
        feed_statuses = feeds_result.scalars().all()

        # Convert to response format
        feeds_data = []
        for feed in feed_statuses:
            feed_data = {
                "id": feed.id,
                "feed_url": feed.feed_url,
                "source": feed.source,
                "feed_type": feed.feed_type,
                "status": feed.status,
                "last_checked": feed.last_checked.isoformat(),
                "last_success": feed.last_success.isoformat() if feed.last_success else None,
                "response_time_ms": feed.response_time_ms,
                "items_found": feed.items_found,
                "consecutive_errors": feed.consecutive_errors,
                "total_errors": feed.errors,
                "last_error": feed.last_error,
                "last_error_at": feed.last_error_at.isoformat() if feed.last_error_at else None,
                "enabled": feed.enabled,
            }
            feeds_data.append(feed_data)

        # Calculate summary statistics
        total_feeds = len(feeds_data)
        healthy_feeds = sum(1 for f in feeds_data if f["status"] == "healthy")
        unhealthy_feeds = sum(1 for f in feeds_data if f["status"] == "unhealthy")
        error_feeds = sum(1 for f in feeds_data if f["status"] == "error")

        # Get recent health check from actual feed monitor
        try:
            health_monitor = FeedHealthMonitor()
            recent_health = await health_monitor.get_feed_status_summary()
        except Exception as e:
            logger.warning("failed_to_get_recent_feed_health", error=str(e))
            recent_health = None

        logger.info(
            "feeds_health_retrieved", user_id=session.user_id, total_feeds=total_feeds, healthy_feeds=healthy_feeds
        )

        return JSONResponse(
            {
                "feeds": feeds_data,
                "summary": {
                    "total_feeds": total_feeds,
                    "healthy_feeds": healthy_feeds,
                    "unhealthy_feeds": unhealthy_feeds,
                    "error_feeds": error_feeds,
                    "health_percentage": round(healthy_feeds / max(total_feeds, 1) * 100, 1),
                },
                "recent_health_check": recent_health,
                "status_timestamp": datetime.now(UTC).isoformat(),
            }
        )

    except Exception as e:
        logger.error("feeds_health_retrieval_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve feed health status")


@router.get(
    "/sources",
    summary="Get available sources",
    description="Get list of available regulatory sources and their statistics",
)
@limiter.limit("100 per hour")
async def get_regulatory_sources(
    request: Request, session: Session = Depends(get_current_session), db: AsyncSession = Depends(get_async_session)
):
    """Get list of available regulatory sources and statistics."""
    try:
        # Get source statistics
        sources_query = (
            select(
                RegulatoryDocument.source,
                RegulatoryDocument.authority,
                func.count(RegulatoryDocument.id).label("total_documents"),
                func.count(func.case((RegulatoryDocument.status == "active", 1), else_=None)).label(
                    "active_documents"
                ),
                func.max(RegulatoryDocument.published_date).label("latest_document_date"),
                func.min(RegulatoryDocument.published_date).label("earliest_document_date"),
            )
            .group_by(RegulatoryDocument.source, RegulatoryDocument.authority)
            .order_by(desc("total_documents"))
        )

        sources_result = await db.execute(sources_query)
        sources_data = []

        for row in sources_result:
            source_data = {
                "source": row.source,
                "authority": row.authority,
                "total_documents": row.total_documents,
                "active_documents": row.active_documents,
                "latest_document_date": row.latest_document_date.isoformat() if row.latest_document_date else None,
                "earliest_document_date": row.earliest_document_date.isoformat()
                if row.earliest_document_date
                else None,
            }

            # Get document types for this source
            types_query = (
                select(RegulatoryDocument.source_type, func.count(RegulatoryDocument.id).label("count"))
                .where(RegulatoryDocument.source == row.source)
                .group_by(RegulatoryDocument.source_type)
            )

            types_result = await db.execute(types_query)
            document_types = {type_row.source_type: type_row.count for type_row in types_result}
            source_data["document_types"] = document_types

            sources_data.append(source_data)

        # Get total statistics
        total_query = select(
            func.count(RegulatoryDocument.id).label("total_documents"),
            func.count(func.case((RegulatoryDocument.status == "active", 1), else_=None)).label("active_documents"),
        )
        total_result = await db.execute(total_query)
        total_row = total_result.first()

        logger.info(
            "regulatory_sources_retrieved",
            user_id=session.user_id,
            sources_count=len(sources_data),
            total_documents=total_row.total_documents,
        )

        return JSONResponse(
            {
                "sources": sources_data,
                "summary": {
                    "total_sources": len(sources_data),
                    "total_documents": total_row.total_documents,
                    "active_documents": total_row.active_documents,
                },
                "status_timestamp": datetime.now(UTC).isoformat(),
            }
        )

    except Exception as e:
        logger.error("regulatory_sources_retrieval_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve regulatory sources")


async def run_immediate_collection(sources: list[str] | None, db: AsyncSession, user_id: str) -> None:
    """Run immediate collection in background task."""
    try:
        collector = DynamicKnowledgeCollector(db)

        if sources:
            results = await collector.collect_from_specific_sources(sources)
        else:
            results = await collector.collect_and_process_updates()

        # Log results
        total_new_docs = sum(len(r.get("new_documents", [])) for r in results if r.get("success"))
        successful_sources = sum(1 for r in results if r.get("success"))

        logger.info(
            "immediate_collection_completed",
            user_id=user_id,
            sources=sources,
            total_sources=len(results),
            successful_sources=successful_sources,
            total_new_documents=total_new_docs,
        )

    except Exception as e:
        logger.error("immediate_collection_failed", user_id=user_id, sources=sources, error=str(e), exc_info=True)
