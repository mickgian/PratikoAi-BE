"""Performance monitoring and optimization API endpoints."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.performance import (
    database_optimizer,
    response_compressor,
    performance_monitor,
    cdn_manager
)
from app.models.session import Session


router = APIRouter()


class OptimizeQueryRequest(BaseModel):
    """Request to optimize a database query."""
    query: str = Field(..., min_length=1, max_length=10000, description="SQL query to optimize")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Query parameters")


class PurgeAssetRequest(BaseModel):
    """Request to purge CDN assets."""
    asset_ids: List[str] = Field(..., min_items=1, max_items=100, description="Asset IDs to purge")


class RegionOptimizationRequest(BaseModel):
    """Request to optimize content for a specific region."""
    region: str = Field(..., description="Target region")
    content_urls: List[str] = Field(..., min_items=1, max_items=50, description="URLs to optimize")


@router.get("/overview")
@limiter.limit("30 per hour")
async def get_performance_overview(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get comprehensive performance overview.
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        Performance overview data
    """
    try:
        # Get performance summary from monitor
        performance_summary = performance_monitor.get_performance_summary()
        
        # Get database performance
        database_summary = database_optimizer.get_performance_summary()
        
        # Get compression statistics
        compression_stats = response_compressor.get_compression_statistics()
        
        # Get CDN statistics
        cdn_stats = cdn_manager.get_cdn_statistics()
        
        # Get cache statistics
        cache_stats = performance_monitor.get_cache_statistics()
        
        overview = {
            "timestamp": datetime.utcnow().isoformat(),
            "system_performance": performance_summary.get("system_metrics", {}),
            "request_performance": performance_summary.get("request_metrics", {}),
            "top_endpoints": performance_summary.get("top_endpoints", []),
            "slowest_endpoints": performance_summary.get("slowest_endpoints", []),
            "database_performance": {
                "total_queries": database_summary.get("total_unique_queries", 0),
                "avg_query_time": database_summary.get("average_query_time", 0),
                "slow_queries": database_summary.get("slow_queries_count", 0)
            },
            "compression_performance": {
                "compression_rate": compression_stats.get("compression_rate", 0),
                "bandwidth_saved_percent": compression_stats.get("bandwidth_saved_percent", 0),
                "avg_compression_time_ms": compression_stats.get("avg_compression_time_ms", 0)
            },
            "cdn_performance": {
                "cache_hit_rate": cdn_stats.get("cache_hit_rate", 0),
                "bandwidth_saved_percent": cdn_stats.get("bandwidth_saved_percent", 0),
                "total_assets": cdn_stats.get("total_assets", 0)
            },
            "cache_performance": cache_stats,
            "active_alerts": performance_summary.get("active_alerts", [])
        }
        
        logger.info(
            "performance_overview_retrieved",
            user_id=session.user_id,
            system_cpu=overview["system_performance"].get("cpu_percent", 0),
            total_requests=overview["request_performance"].get("total_requests", 0)
        )
        
        return response_compressor.create_optimized_response(
            overview, request, optimize_payload=True
        )
        
    except Exception as e:
        logger.error(
            "performance_overview_failed",
            user_id=session.user_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve performance overview")


@router.get("/database/stats")
@limiter.limit("20 per hour")
async def get_database_performance(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get database performance statistics.
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        Database performance data
    """
    try:
        # Get comprehensive database statistics
        db_summary = database_optimizer.get_performance_summary()
        
        # Get slow queries analysis
        slow_queries = await database_optimizer.analyze_slow_queries(limit=10)
        
        # Get connection pool statistics
        pool_stats = await database_optimizer.get_pool_statistics()
        
        # Get index recommendations
        index_recommendations = await database_optimizer.generate_index_recommendations()
        
        database_performance = {
            "summary": db_summary,
            "slow_queries": [
                {
                    "query_hash": q.query_hash,
                    "avg_time": round(q.avg_time, 4),
                    "execution_count": q.execution_count,
                    "total_time": round(q.total_time, 2),
                    "query_preview": q.query_text[:200] + "..." if len(q.query_text) > 200 else q.query_text
                }
                for q in slow_queries
            ],
            "connection_pool": pool_stats,
            "index_recommendations": [
                {
                    "table": rec.table_name,
                    "columns": rec.columns,
                    "index_type": rec.index_type,
                    "reason": rec.reason,
                    "estimated_benefit": round(rec.estimated_benefit, 2)
                }
                for rec in index_recommendations
            ],
            "optimization_opportunities": len(index_recommendations)
        }
        
        logger.info(
            "database_performance_retrieved",
            user_id=session.user_id,
            slow_queries_count=len(slow_queries),
            recommendations_count=len(index_recommendations)
        )
        
        return response_compressor.create_optimized_response(
            database_performance, request
        )
        
    except Exception as e:
        logger.error(
            "database_performance_retrieval_failed",
            user_id=session.user_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve database performance")


@router.post("/database/optimize-query")
@limiter.limit("10 per hour")
async def optimize_database_query(
    request: Request,
    optimize_request: OptimizeQueryRequest,
    session: Session = Depends(get_current_session),
):
    """Optimize a database query for better performance.
    
    Args:
        request: FastAPI request object
        optimize_request: Query optimization parameters
        session: Current user session
        
    Returns:
        Query optimization results
    """
    try:
        # Optimize the query
        optimized_query, execution_hints = await database_optimizer.optimize_query_execution(
            optimize_request.query,
            optimize_request.parameters
        )
        
        optimization_result = {
            "original_query": optimize_request.query,
            "optimized_query": optimized_query,
            "execution_hints": execution_hints,
            "optimization_applied": execution_hints.get("optimization_applied", False),
            "optimization_reason": execution_hints.get("optimization_reason"),
            "recommendations": []
        }
        
        # Add specific recommendations based on query analysis
        query_upper = optimize_request.query.upper()
        
        if "SELECT *" in query_upper:
            optimization_result["recommendations"].append(
                "Consider selecting only required columns instead of using SELECT *"
            )
        
        if "ORDER BY" in query_upper and "LIMIT" not in query_upper:
            optimization_result["recommendations"].append(
                "Consider adding LIMIT clause to ORDER BY queries"
            )
        
        if query_upper.count("JOIN") > 3:
            optimization_result["recommendations"].append(
                "Complex JOIN operations detected - consider query restructuring"
            )
        
        logger.info(
            "database_query_optimized",
            user_id=session.user_id,
            optimization_applied=optimization_result["optimization_applied"],
            recommendations_count=len(optimization_result["recommendations"])
        )
        
        return JSONResponse(optimization_result)
        
    except Exception as e:
        logger.error(
            "database_query_optimization_failed",
            user_id=session.user_id,
            query_length=len(optimize_request.query),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Query optimization failed")


@router.post("/database/optimize-pool")
@limiter.limit("5 per hour")
async def optimize_connection_pool(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Optimize database connection pool settings.
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        Pool optimization results
    """
    try:
        # Check admin permissions (simplified)
        if not session.user_id.startswith("admin_"):
            raise HTTPException(
                status_code=403,
                detail="Admin privileges required for connection pool optimization"
            )
        
        # Optimize connection pool
        optimization_results = await database_optimizer.optimize_connection_pool()
        
        logger.info(
            "connection_pool_optimized",
            admin_user_id=session.user_id,
            optimization_applied=optimization_results.get("optimization_applied", False),
            improvements_count=len(optimization_results.get("improvements", []))
        )
        
        return JSONResponse(optimization_results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "connection_pool_optimization_failed",
            user_id=session.user_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Connection pool optimization failed")


@router.get("/compression/stats")
@limiter.limit("20 per hour")
async def get_compression_statistics(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get response compression statistics.
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        Compression statistics
    """
    try:
        compression_stats = response_compressor.get_compression_statistics()
        
        logger.debug(
            "compression_statistics_retrieved",
            user_id=session.user_id,
            compression_rate=compression_stats.get("compression_rate", 0)
        )
        
        return JSONResponse(compression_stats)
        
    except Exception as e:
        logger.error(
            "compression_statistics_failed",
            user_id=session.user_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve compression statistics")


@router.post("/compression/reset-stats")
@limiter.limit("5 per hour")
async def reset_compression_statistics(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Reset compression statistics (admin only).
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        Reset confirmation
    """
    try:
        # Check admin permissions
        if not session.user_id.startswith("admin_"):
            raise HTTPException(
                status_code=403,
                detail="Admin privileges required to reset compression statistics"
            )
        
        success = response_compressor.reset_statistics()
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to reset compression statistics")
        
        logger.info(
            "compression_statistics_reset",
            admin_user_id=session.user_id
        )
        
        return JSONResponse({
            "success": True,
            "message": "Compression statistics reset successfully",
            "reset_at": datetime.utcnow().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "compression_statistics_reset_failed",
            user_id=session.user_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Compression statistics reset failed")


@router.get("/cdn/stats")
@limiter.limit("20 per hour")
async def get_cdn_statistics(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get CDN performance statistics.
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        CDN statistics
    """
    try:
        cdn_stats = cdn_manager.get_cdn_statistics()
        
        logger.debug(
            "cdn_statistics_retrieved",
            user_id=session.user_id,
            cache_hit_rate=cdn_stats.get("cache_hit_rate", 0),
            total_assets=cdn_stats.get("total_assets", 0)
        )
        
        return response_compressor.create_optimized_response(
            cdn_stats, request
        )
        
    except Exception as e:
        logger.error(
            "cdn_statistics_failed",
            user_id=session.user_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve CDN statistics")


@router.post("/cdn/purge")
@limiter.limit("10 per hour")
async def purge_cdn_assets(
    request: Request,
    purge_request: PurgeAssetRequest,
    session: Session = Depends(get_current_session),
):
    """Purge assets from CDN cache.
    
    Args:
        request: FastAPI request object
        purge_request: Asset purge parameters
        session: Current user session
        
    Returns:
        Purge results
    """
    try:
        # Purge assets
        purge_results = cdn_manager.purge_asset_cache(purge_request.asset_ids)
        
        successful_purges = sum(1 for success in purge_results.values() if success)
        
        logger.info(
            "cdn_assets_purged",
            user_id=session.user_id,
            requested_count=len(purge_request.asset_ids),
            successful_count=successful_purges
        )
        
        return JSONResponse({
            "success": successful_purges == len(purge_request.asset_ids),
            "results": purge_results,
            "requested_count": len(purge_request.asset_ids),
            "successful_count": successful_purges,
            "failed_count": len(purge_request.asset_ids) - successful_purges,
            "purged_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(
            "cdn_asset_purge_failed",
            user_id=session.user_id,
            asset_count=len(purge_request.asset_ids),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="CDN asset purge failed")


@router.post("/cdn/optimize-region")
@limiter.limit("5 per hour")
async def optimize_for_region(
    request: Request,
    optimization_request: RegionOptimizationRequest,
    session: Session = Depends(get_current_session),
):
    """Optimize content delivery for a specific region.
    
    Args:
        request: FastAPI request object
        optimization_request: Region optimization parameters
        session: Current user session
        
    Returns:
        Regional optimization results
    """
    try:
        # Optimize content for region
        optimized_urls = await cdn_manager.optimize_for_region(
            optimization_request.region,
            optimization_request.content_urls
        )
        
        optimization_result = {
            "region": optimization_request.region,
            "original_urls": optimization_request.content_urls,
            "optimized_urls": optimized_urls,
            "optimization_count": len(optimized_urls),
            "optimized_at": datetime.utcnow().isoformat()
        }
        
        logger.info(
            "content_optimized_for_region",
            user_id=session.user_id,
            region=optimization_request.region,
            urls_count=len(optimization_request.content_urls)
        )
        
        return JSONResponse(optimization_result)
        
    except Exception as e:
        logger.error(
            "regional_optimization_failed",
            user_id=session.user_id,
            region=optimization_request.region,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Regional optimization failed")


@router.get("/monitoring/endpoints")
@limiter.limit("20 per hour")
async def get_endpoint_performance(
    request: Request,
    session: Session = Depends(get_current_session),
    endpoint_pattern: Optional[str] = Query(default=None, description="Filter endpoints by pattern"),
):
    """Get detailed endpoint performance metrics.
    
    Args:
        request: FastAPI request object
        session: Current user session
        endpoint_pattern: Optional pattern to filter endpoints
        
    Returns:
        Endpoint performance data
    """
    try:
        endpoint_details = performance_monitor.get_endpoint_details(endpoint_pattern)
        
        logger.debug(
            "endpoint_performance_retrieved",
            user_id=session.user_id,
            endpoints_count=len(endpoint_details),
            filter_pattern=endpoint_pattern
        )
        
        return response_compressor.create_optimized_response(
            {
                "endpoints": endpoint_details,
                "count": len(endpoint_details),
                "filter_pattern": endpoint_pattern,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            request
        )
        
    except Exception as e:
        logger.error(
            "endpoint_performance_retrieval_failed",
            user_id=session.user_id,
            endpoint_pattern=endpoint_pattern,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve endpoint performance")


@router.get("/monitoring/alerts")
@limiter.limit("30 per hour")
async def get_performance_alerts(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get current performance alerts.
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        Current performance alerts
    """
    try:
        performance_summary = performance_monitor.get_performance_summary()
        
        alerts_data = {
            "active_alerts": performance_summary.get("active_alerts", []),
            "recent_alerts": performance_summary.get("recent_alerts", []),
            "alert_count": len(performance_summary.get("active_alerts", [])),
            "thresholds": performance_summary.get("performance_thresholds", {}),
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
        logger.debug(
            "performance_alerts_retrieved",
            user_id=session.user_id,
            active_alerts_count=alerts_data["alert_count"]
        )
        
        return JSONResponse(alerts_data)
        
    except Exception as e:
        logger.error(
            "performance_alerts_retrieval_failed",
            user_id=session.user_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve performance alerts")