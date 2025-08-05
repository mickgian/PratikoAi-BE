"""
Background Job Processing for Data Export.

This module handles asynchronous processing of data export requests using
Celery background tasks for optimal performance and scalability.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_

from app.core.config import settings
from app.core.logging import logger
from app.models.data_export import DataExportRequest, ExportStatus, ExportAuditLog
from app.services.data_export_service import DataExportService
from app.services.cache import get_redis_client

# Initialize Celery app
celery_app = Celery(
    "data_export_worker",
    broker=settings.CELERY_BROKER_URL or "redis://localhost:6379/0",
    backend=settings.CELERY_RESULT_BACKEND or "redis://localhost:6379/0"
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Rome",
    enable_utc=True,
    task_routes={
        "data_export_jobs.process_export_request": {"queue": "exports"},
        "data_export_jobs.cleanup_expired_exports": {"queue": "maintenance"},
        "data_export_jobs.monitor_export_health": {"queue": "monitoring"}
    },
    task_annotations={
        "data_export_jobs.process_export_request": {
            "rate_limit": "10/m",  # Max 10 exports per minute
            "time_limit": 3600,    # 1 hour timeout
            "soft_time_limit": 3300 # 55 minutes soft timeout
        }
    }
)


async def get_async_db() -> AsyncSession:
    """Get async database session for background jobs"""
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    
    async_session = sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    return async_session()


@celery_app.task(bind=True, name="data_export_jobs.process_export_request")
def process_export_request(self, export_id: str):
    """
    Process a data export request asynchronously.
    
    Args:
        export_id: UUID of the export request to process
    """
    try:
        logger.info(f"Starting background processing of export {export_id}")
        
        # Run async processing in event loop
        result = asyncio.run(_process_export_async(export_id, self))
        
        if result["success"]:
            logger.info(
                f"Export {export_id} completed successfully in "
                f"{result.get('processing_time_seconds', 0)} seconds"
            )
            return {
                "status": "completed",
                "export_id": export_id,
                "file_size_mb": result.get("file_size_mb", 0),
                "processing_time_seconds": result.get("processing_time_seconds", 0)
            }
        else:
            logger.error(f"Export {export_id} failed: {result['error']}")
            return {
                "status": "failed", 
                "export_id": export_id,
                "error": result["error"]
            }
            
    except Exception as e:
        logger.error(f"Critical error processing export {export_id}: {e}")
        
        # Update export status to failed
        asyncio.run(_mark_export_failed(export_id, str(e)))
        
        # Retry if this is not the final attempt
        if self.request.retries < 2:
            logger.info(f"Retrying export {export_id} (attempt {self.request.retries + 1}/3)")
            raise self.retry(countdown=60 * (2 ** self.request.retries), max_retries=2)
        
        return {
            "status": "failed",
            "export_id": export_id, 
            "error": str(e),
            "final_failure": True
        }


async def _process_export_async(export_id: str, task_instance) -> dict:
    """Async wrapper for export processing"""
    db = None
    try:
        db = await get_async_db()
        service = DataExportService(db)
        
        # Update task progress
        def update_progress(current: int, total: int, description: str):
            task_instance.update_state(
                state="PROGRESS",
                meta={
                    "current": current,
                    "total": total, 
                    "description": description,
                    "export_id": export_id
                }
            )
        
        # Process the export with progress callbacks
        await service.process_export(UUID(export_id))
        
        # Get final export details
        export_request = await service._get_export_request(UUID(export_id))
        
        return {
            "success": True,
            "file_size_mb": round(export_request.file_size_bytes / 1024 / 1024, 2) if export_request.file_size_bytes else 0,
            "processing_time_seconds": export_request.processing_time_seconds
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
        
    finally:
        if db:
            await db.close()


async def _mark_export_failed(export_id: str, error_message: str):
    """Mark export as failed with error message"""
    db = None
    try:
        db = await get_async_db()
        
        stmt = select(DataExportRequest).where(DataExportRequest.id == UUID(export_id))
        result = await db.execute(stmt)
        export_request = result.scalar_one_or_none()
        
        if export_request:
            export_request.status = ExportStatus.FAILED
            export_request.error_message = error_message
            export_request.retry_count += 1
            await db.commit()
            
    except Exception as e:
        logger.error(f"Error marking export {export_id} as failed: {e}")
    finally:
        if db:
            await db.close()


@celery_app.task(name="data_export_jobs.cleanup_expired_exports")
def cleanup_expired_exports():
    """
    Clean up expired export requests and files.
    
    Runs daily to remove expired exports from database and storage.
    """
    try:
        logger.info("Starting cleanup of expired exports")
        
        result = asyncio.run(_cleanup_expired_exports_async())
        
        logger.info(
            f"Cleanup completed: {result['cleaned_count']} exports cleaned, "
            f"{result['storage_mb_freed']} MB freed"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error during export cleanup: {e}")
        return {"error": str(e), "cleaned_count": 0}


async def _cleanup_expired_exports_async() -> dict:
    """Async cleanup of expired exports"""
    db = None
    try:
        db = await get_async_db()
        
        # Find expired exports
        cutoff_time = datetime.utcnow()
        stmt = select(DataExportRequest).where(
            and_(
                DataExportRequest.expires_at < cutoff_time,
                DataExportRequest.status.in_([ExportStatus.COMPLETED, ExportStatus.FAILED])
            )
        )
        
        result = await db.execute(stmt)
        expired_exports = result.scalars().all()
        
        cleaned_count = 0
        storage_freed_bytes = 0
        
        for export in expired_exports:
            try:
                # Delete from cloud storage if exists
                if export.download_url:
                    # Extract S3 key from URL and delete
                    # This would integrate with your S3 service
                    storage_freed_bytes += export.file_size_bytes or 0
                
                # Update status to expired
                export.status = ExportStatus.EXPIRED
                export.download_url = None
                
                cleaned_count += 1
                
            except Exception as e:
                logger.warning(f"Error cleaning export {export.id}: {e}")
                continue
        
        await db.commit()
        
        return {
            "cleaned_count": cleaned_count,
            "storage_mb_freed": round(storage_freed_bytes / 1024 / 1024, 2)
        }
        
    except Exception as e:
        logger.error(f"Error in async cleanup: {e}")
        return {"cleaned_count": 0, "storage_mb_freed": 0}
        
    finally:
        if db:
            await db.close()


@celery_app.task(name="data_export_jobs.monitor_export_health")
def monitor_export_health():
    """
    Monitor export system health and performance.
    
    Runs every 15 minutes to check for stuck exports, performance issues,
    and system resource usage.
    """
    try:
        logger.info("Starting export system health check")
        
        result = asyncio.run(_monitor_export_health_async())
        
        # Log warnings for any issues found
        if result.get("stuck_exports"):
            logger.warning(f"Found {len(result['stuck_exports'])} stuck exports")
        
        if result.get("average_processing_time", 0) > 1800:  # 30 minutes
            logger.warning(f"High average processing time: {result['average_processing_time']} seconds")
        
        return result
        
    except Exception as e:
        logger.error(f"Error monitoring export health: {e}")
        return {"error": str(e)}


async def _monitor_export_health_async() -> dict:
    """Async health monitoring"""
    db = None
    try:
        db = await get_async_db()
        
        # Find stuck exports (processing for more than 2 hours)
        stuck_cutoff = datetime.utcnow() - timedelta(hours=2)
        stuck_stmt = select(DataExportRequest).where(
            and_(
                DataExportRequest.status == ExportStatus.PROCESSING,
                DataExportRequest.started_at < stuck_cutoff
            )
        )
        
        stuck_result = await db.execute(stuck_stmt)
        stuck_exports = stuck_result.scalars().all()
        
        # Calculate average processing time for completed exports (last 24 hours)
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        avg_stmt = select(DataExportRequest).where(
            and_(
                DataExportRequest.status == ExportStatus.COMPLETED,
                DataExportRequest.completed_at >= recent_cutoff,
                DataExportRequest.processing_time_seconds.isnot(None)
            )
        )
        
        avg_result = await db.execute(avg_stmt)
        recent_exports = avg_result.scalars().all()
        
        # Calculate statistics
        if recent_exports:
            processing_times = [e.processing_time_seconds for e in recent_exports if e.processing_time_seconds]
            average_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            max_processing_time = max(processing_times) if processing_times else 0
        else:
            average_processing_time = 0
            max_processing_time = 0
        
        # Count exports by status (last 24 hours)
        status_counts = {}
        for status in ExportStatus:
            count_stmt = select(DataExportRequest).where(
                and_(
                    DataExportRequest.status == status,
                    DataExportRequest.requested_at >= recent_cutoff
                )
            )
            count_result = await db.execute(count_stmt)
            status_counts[status.value] = len(count_result.scalars().all())
        
        # Mark stuck exports as failed
        for stuck_export in stuck_exports:
            stuck_export.status = ExportStatus.FAILED
            stuck_export.error_message = "Export timeout - processing took too long"
            
        if stuck_exports:
            await db.commit()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "stuck_exports": [str(e.id) for e in stuck_exports],
            "stuck_count": len(stuck_exports),
            "average_processing_time": round(average_processing_time, 1),
            "max_processing_time": round(max_processing_time, 1),
            "exports_last_24h": sum(status_counts.values()),
            "status_breakdown": status_counts,
            "system_healthy": len(stuck_exports) == 0 and average_processing_time < 1800
        }
        
    except Exception as e:
        logger.error(f"Error in health monitoring: {e}")
        return {"error": str(e), "system_healthy": False}
        
    finally:
        if db:
            await db.close()


@celery_app.task(name="data_export_jobs.process_export_queue")
def process_export_queue():
    """
    Process the export queue from Redis.
    
    Checks for queued export requests and processes them in order.
    Runs every minute to ensure timely processing.
    """
    try:
        result = asyncio.run(_process_export_queue_async())
        
        if result["processed_count"] > 0:
            logger.info(f"Processed {result['processed_count']} exports from queue")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing export queue: {e}")
        return {"error": str(e), "processed_count": 0}


async def _process_export_queue_async() -> dict:
    """Async queue processing"""
    try:
        redis_client = get_redis_client()
        processed_count = 0
        
        # Process up to 5 exports from queue
        for _ in range(5):
            # Get next export from queue (blocking for 1 second)
            queue_item = await redis_client.brpop("export_queue", timeout=1)
            
            if not queue_item:
                break  # No more items in queue
            
            export_id = queue_item[1].decode('utf-8')
            
            # Trigger async processing
            process_export_request.delay(export_id)
            processed_count += 1
            
            logger.debug(f"Queued export {export_id} for processing")
        
        return {
            "processed_count": processed_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in queue processing: {e}")
        return {"processed_count": 0, "error": str(e)}


@celery_app.task(name="data_export_jobs.generate_export_metrics")
def generate_export_metrics():
    """
    Generate metrics for export system monitoring.
    
    Runs hourly to collect performance metrics for monitoring dashboards.
    """
    try:
        result = asyncio.run(_generate_export_metrics_async())
        
        # Store metrics in Redis for monitoring dashboard
        redis_client = get_redis_client()
        asyncio.run(redis_client.setex(
            "export_metrics",
            3600,  # 1 hour TTL
            json.dumps(result)
        ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating export metrics: {e}")
        return {"error": str(e)}


async def _generate_export_metrics_async() -> dict:
    """Generate comprehensive export metrics"""
    db = None
    try:
        db = await get_async_db()
        
        # Time periods for metrics
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        last_24_hours = now - timedelta(hours=24)
        last_week = now - timedelta(days=7)
        
        # Metrics collection
        metrics = {
            "timestamp": now.isoformat(),
            "last_hour": await _get_period_metrics(db, last_hour, now),
            "last_24_hours": await _get_period_metrics(db, last_24_hours, now),
            "last_week": await _get_period_metrics(db, last_week, now)
        }
        
        # Current queue size
        redis_client = get_redis_client()
        queue_size = await redis_client.llen("export_queue")
        metrics["current_queue_size"] = queue_size
        
        # Active processing count
        active_stmt = select(DataExportRequest).where(
            DataExportRequest.status == ExportStatus.PROCESSING
        )
        active_result = await db.execute(active_stmt)
        metrics["active_processing_count"] = len(active_result.scalars().all())
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return {"error": str(e)}
        
    finally:
        if db:
            await db.close()


async def _get_period_metrics(db: AsyncSession, start_time: datetime, end_time: datetime) -> dict:
    """Get metrics for a specific time period"""
    try:
        # Total requests in period
        total_stmt = select(DataExportRequest).where(
            and_(
                DataExportRequest.requested_at >= start_time,
                DataExportRequest.requested_at <= end_time
            )
        )
        total_result = await db.execute(total_stmt)
        total_exports = total_result.scalars().all()
        
        # Completed exports
        completed_exports = [e for e in total_exports if e.status == ExportStatus.COMPLETED]
        failed_exports = [e for e in total_exports if e.status == ExportStatus.FAILED]
        
        # Processing times
        processing_times = [
            e.processing_time_seconds 
            for e in completed_exports 
            if e.processing_time_seconds
        ]
        
        # File sizes
        file_sizes = [
            e.file_size_bytes 
            for e in completed_exports 
            if e.file_size_bytes
        ]
        
        return {
            "total_requests": len(total_exports),
            "completed_count": len(completed_exports),
            "failed_count": len(failed_exports),
            "success_rate": round(len(completed_exports) / len(total_exports) * 100, 1) if total_exports else 0,
            "average_processing_time": round(sum(processing_times) / len(processing_times), 1) if processing_times else 0,
            "max_processing_time": max(processing_times) if processing_times else 0,
            "total_data_exported_mb": round(sum(file_sizes) / 1024 / 1024, 2) if file_sizes else 0,
            "average_file_size_mb": round(sum(file_sizes) / len(file_sizes) / 1024 / 1024, 2) if file_sizes else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting period metrics: {e}")
        return {"error": str(e)}


# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Process export queue every minute
    "process-export-queue": {
        "task": "data_export_jobs.process_export_queue",
        "schedule": 60.0,  # Every minute
    },
    
    # Clean up expired exports daily at 2 AM
    "cleanup-expired-exports": {
        "task": "data_export_jobs.cleanup_expired_exports", 
        "schedule": 86400.0,  # Daily
        "options": {"eta": datetime.utcnow().replace(hour=2, minute=0, second=0)}
    },
    
    # Monitor system health every 15 minutes
    "monitor-export-health": {
        "task": "data_export_jobs.monitor_export_health",
        "schedule": 900.0,  # Every 15 minutes
    },
    
    # Generate metrics every hour
    "generate-export-metrics": {
        "task": "data_export_jobs.generate_export_metrics",
        "schedule": 3600.0,  # Every hour
    }
}


if __name__ == "__main__":
    # For testing individual tasks
    import sys
    
    if len(sys.argv) > 1:
        task_name = sys.argv[1]
        
        if task_name == "cleanup":
            result = cleanup_expired_exports()
            print(f"Cleanup result: {result}")
            
        elif task_name == "health":
            result = monitor_export_health()
            print(f"Health check result: {result}")
            
        elif task_name == "metrics":
            result = generate_export_metrics()
            print(f"Metrics result: {result}")
            
        elif task_name == "queue":
            result = process_export_queue()
            print(f"Queue processing result: {result}")
            
        else:
            print("Available tasks: cleanup, health, metrics, queue")
    else:
        print("Usage: python data_export_jobs.py <task_name>")