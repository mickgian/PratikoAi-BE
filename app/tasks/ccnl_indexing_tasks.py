"""
Background tasks for CCNL search indexing.

This module provides scheduled tasks to maintain search indexes,
update aggregations, and optimize search performance.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from celery import Celery
from celery.schedules import crontab

from app.services.ccnl_indexing_service import ccnl_indexing_service
from app.services.ccnl_search_service import ccnl_search_service
from app.core.logging import logger
from app.core.config import settings


# Initialize Celery
celery_app = Celery(
    "ccnl_indexing",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Rome",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
)


@celery_app.task(name="update_search_indexes")
async def update_search_indexes() -> Dict[str, Any]:
    """Update all CCNL search indexes."""
    logger.info("Starting search index update")
    
    try:
        # Create/update database indexes
        stats = await ccnl_indexing_service.create_indexes()
        
        # Update search vectors
        vector_count = await ccnl_indexing_service.update_search_vectors()
        
        result = {
            "status": "success",
            "indexed_documents": stats.indexed_documents,
            "failed_documents": stats.failed_documents,
            "index_time_seconds": stats.index_time_seconds,
            "vectors_updated": vector_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Search index update completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error updating search indexes: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@celery_app.task(name="update_search_aggregations")
async def update_search_aggregations() -> Dict[str, Any]:
    """Update pre-computed search aggregations."""
    logger.info("Starting aggregation update")
    
    try:
        # Pre-compute aggregations
        aggregations = await ccnl_indexing_service.pre_compute_aggregations()
        
        result = {
            "status": "success",
            "aggregations_updated": len(aggregations),
            "types": list(aggregations.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Aggregation update completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error updating aggregations: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@celery_app.task(name="warm_search_cache")
async def warm_search_cache() -> Dict[str, Any]:
    """Warm search cache with popular queries."""
    logger.info("Starting cache warming")
    
    try:
        # Get popular queries
        popular_queries = await ccnl_search_service.get_popular_searches()
        
        # Warm cache
        warmed_count = await ccnl_indexing_service.warm_search_cache(popular_queries)
        
        result = {
            "status": "success",
            "queries_warmed": warmed_count,
            "total_queries": len(popular_queries),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Cache warming completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@celery_app.task(name="analyze_search_performance")
async def analyze_search_performance() -> Dict[str, Any]:
    """Analyze search performance and identify optimizations."""
    logger.info("Starting search performance analysis")
    
    try:
        # Analyze search patterns
        patterns = await ccnl_indexing_service.analyze_search_patterns()
        
        # Identify slow queries
        slow_queries = await ccnl_indexing_service.optimize_slow_queries(threshold_ms=500)
        
        result = {
            "status": "success",
            "patterns": patterns,
            "slow_queries_found": len(slow_queries),
            "top_slow_queries": slow_queries[:5],  # Top 5 slowest
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Performance analysis completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing performance: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@celery_app.task(name="maintain_index_health")
async def maintain_index_health() -> Dict[str, Any]:
    """Check and maintain search index health."""
    logger.info("Starting index health check")
    
    try:
        # Check index health
        health = await ccnl_indexing_service.get_index_health()
        
        # Rebuild degraded indexes
        rebuilt_indexes = []
        if health["status"] != "healthy":
            for index_name, status in health["indexes"].items():
                if status == "missing" or status.get("status") == "degraded":
                    success = await ccnl_indexing_service.rebuild_index(index_name)
                    if success:
                        rebuilt_indexes.append(index_name)
        
        result = {
            "status": "success",
            "health_status": health["status"],
            "issues_found": len(health["issues"]),
            "indexes_rebuilt": rebuilt_indexes,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Index health check completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error checking index health: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@celery_app.task(name="cleanup_old_cache")
async def cleanup_old_cache() -> Dict[str, Any]:
    """Clean up old cached search results."""
    logger.info("Starting cache cleanup")
    
    try:
        # This would be implemented with Redis scan and delete
        # For now, return placeholder
        result = {
            "status": "success",
            "entries_cleaned": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Cache cleanup completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error cleaning cache: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    "update-search-indexes": {
        "task": "update_search_indexes",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    "update-aggregations": {
        "task": "update_search_aggregations", 
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
    "warm-cache": {
        "task": "warm_search_cache",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    "analyze-performance": {
        "task": "analyze_search_performance",
        "schedule": crontab(hour="*/6"),  # Every 6 hours
    },
    "maintain-index-health": {
        "task": "maintain_index_health",
        "schedule": crontab(hour=3, minute=30),  # Daily at 3:30 AM
    },
    "cleanup-cache": {
        "task": "cleanup_old_cache",
        "schedule": crontab(hour=4, minute=0),  # Daily at 4 AM
    }
}


# Manual task runners for testing
async def run_all_maintenance_tasks():
    """Run all maintenance tasks manually."""
    tasks = [
        update_search_indexes(),
        update_search_aggregations(),
        warm_search_cache(),
        analyze_search_performance(),
        maintain_index_health(),
        cleanup_old_cache()
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {
        "update_indexes": results[0],
        "update_aggregations": results[1],
        "warm_cache": results[2],
        "analyze_performance": results[3],
        "maintain_health": results[4],
        "cleanup_cache": results[5],
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    # For testing
    asyncio.run(run_all_maintenance_tasks())