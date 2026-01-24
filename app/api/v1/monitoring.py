"""Monitoring API endpoints for Prometheus metrics and cost monitoring.

This module provides endpoints for Prometheus to scrape metrics,
for administrators to check monitoring status, and the cost monitoring
dashboard (DEV-239).
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST

from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.logging import logger
from app.core.monitoring.metrics import get_metrics_content, get_registry
from app.models.session import Session
from app.services.cost_monitoring_dashboard import get_cost_monitoring_dashboard

router = APIRouter()


@router.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Prometheus metrics endpoint.

    This endpoint provides all application metrics in Prometheus format.
    No authentication required for Prometheus scraping.

    Returns:
        Plain text response with Prometheus metrics
    """
    try:
        metrics_content = get_metrics_content()

        logger.debug("prometheus_metrics_requested", metrics_size=len(metrics_content))

        return Response(content=metrics_content, media_type=CONTENT_TYPE_LATEST)

    except Exception as e:
        logger.error("prometheus_metrics_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate metrics")


@router.get("/health/metrics")
async def get_metrics_health():
    """Check metrics collection health.

    Returns basic information about metrics collection status.
    No authentication required for health checks.

    Returns:
        dict: Metrics system health information
    """
    try:
        registry = get_registry()

        # Count collectors and metrics
        collector_count = len(registry._collector_to_names)
        metric_names = []

        for collector in registry._collector_to_names.keys():
            try:
                # Get metric samples to count active metrics
                for metric in collector.collect():
                    metric_names.append(metric.name)
            except Exception:
                # Skip problematic collectors
                continue

        metrics_health = {
            "status": "healthy",
            "metrics_system": "prometheus",
            "collectors_registered": collector_count,
            "metrics_active": len(metric_names),
            "environment": settings.ENVIRONMENT.value,
            "version": settings.VERSION,
        }

        logger.info("metrics_health_check", collectors=collector_count, metrics=len(metric_names))

        return metrics_health

    except Exception as e:
        logger.error("metrics_health_check_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Metrics health check failed")


@router.get("/metrics/list")
async def list_available_metrics(session: Session = Depends(get_current_session)):
    """List all available metrics (admin only).

    Returns detailed information about all registered metrics.
    Requires authentication.

    Args:
        session: Current user session

    Returns:
        dict: List of all available metrics with descriptions
    """
    try:
        registry = get_registry()
        metrics_info = []

        for collector in registry._collector_to_names.keys():
            try:
                for metric in collector.collect():
                    metric_info = {
                        "name": metric.name,
                        "type": metric.type,
                        "help": metric.documentation,
                        "labels": [],
                    }

                    # Get sample labels
                    for sample in metric.samples:
                        if sample.labels not in metric_info["labels"]:
                            metric_info["labels"].append(dict(sample.labels))

                    metrics_info.append(metric_info)

            except Exception as e:
                logger.warning("metric_info_extraction_failed", collector=str(collector), error=str(e))
                continue

        logger.info("metrics_list_requested", user_id=session.user_id, metrics_count=len(metrics_info))

        return {
            "metrics": metrics_info,
            "total_count": len(metrics_info),
            "environment": settings.ENVIRONMENT.value,
        }

    except Exception as e:
        logger.error("metrics_list_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list metrics")


@router.get("/metrics/summary")
async def get_metrics_summary(session: Session = Depends(get_current_session)):
    """Get a summary of key metrics (admin only).

    Returns summary of important business and system metrics.
    Requires authentication.

    Args:
        session: Current user session

    Returns:
        dict: Summary of key metrics
    """
    try:
        from app.core.monitoring.metrics import (
            active_subscriptions,
            active_users,
            cache_hit_ratio,
            llm_cost_total,
            monthly_revenue,
        )

        # This is a simplified summary - in production you'd query actual values
        summary = {
            "business_metrics": {
                "target_arr_eur": 25000,
                "current_mrr_eur": "See monthly_revenue metric",
                "target_subscriptions": 50,
                "current_subscriptions": "See active_subscriptions metric",
            },
            "performance_metrics": {
                "target_cost_per_user_eur": 2.00,
                "cache_hit_target": 0.80,
                "response_time_target_ms": 500,
            },
            "system_status": {
                "environment": settings.ENVIRONMENT.value,
                "version": settings.VERSION,
                "metrics_enabled": True,
            },
        }

        logger.info("metrics_summary_requested", user_id=session.user_id)

        return summary

    except Exception as e:
        logger.error("metrics_summary_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get metrics summary")


# =============================================================================
# Cost Monitoring Dashboard Endpoints (DEV-239)
# =============================================================================


@router.get("/costs/dashboard")
async def get_cost_dashboard(
    start_date: datetime | None = Query(None, description="Start of period"),
    end_date: datetime | None = Query(None, description="End of period"),
    session: Session = Depends(get_current_session),
) -> dict[str, Any]:
    """Get complete cost monitoring dashboard summary.

    Returns cost breakdown by model, complexity, and daily trends.
    Requires authentication.

    Args:
        start_date: Optional start of period (default: 30 days ago)
        end_date: Optional end of period (default: now)
        session: Current user session

    Returns:
        Complete dashboard data with all cost metrics
    """
    try:
        dashboard = get_cost_monitoring_dashboard()
        result = await dashboard.get_dashboard_summary(start_date, end_date)

        logger.info(
            "cost_dashboard_requested",
            user_id=session.user_id,
            start_date=str(start_date),
            end_date=str(end_date),
        )

        return result

    except Exception as e:
        logger.error("cost_dashboard_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get cost dashboard")


@router.get("/costs/queries")
async def get_query_costs(
    user_id: str | None = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: Session = Depends(get_current_session),
) -> list[dict[str, Any]]:
    """Get individual query costs.

    Returns per-query cost data with model, complexity, and timestamps.
    Requires authentication.

    Args:
        user_id: Optional user ID filter
        limit: Maximum number of results (1-1000)
        offset: Pagination offset
        session: Current user session

    Returns:
        List of query cost records
    """
    try:
        dashboard = get_cost_monitoring_dashboard()
        result = await dashboard.get_query_costs(user_id=user_id, limit=limit, offset=offset)

        logger.info(
            "query_costs_requested",
            requesting_user_id=session.user_id,
            filter_user_id=user_id,
            limit=limit,
            offset=offset,
            result_count=len(result),
        )

        return result

    except Exception as e:
        logger.error("query_costs_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get query costs")


@router.get("/costs/by-model")
async def get_cost_by_model(
    start_date: datetime | None = Query(None, description="Start of period"),
    end_date: datetime | None = Query(None, description="End of period"),
    session: Session = Depends(get_current_session),
) -> dict[str, dict[str, Any]]:
    """Get cost breakdown by model.

    Returns total cost, query count, and average cost per model.
    Requires authentication.

    Args:
        start_date: Optional start of period
        end_date: Optional end of period
        session: Current user session

    Returns:
        Dict mapping model name to cost metrics
    """
    try:
        dashboard = get_cost_monitoring_dashboard()
        result = await dashboard.get_cost_by_model(start_date, end_date)

        logger.info(
            "cost_by_model_requested",
            user_id=session.user_id,
            start_date=str(start_date),
            end_date=str(end_date),
            model_count=len(result),
        )

        return result

    except Exception as e:
        logger.error("cost_by_model_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get cost by model")


@router.get("/costs/by-complexity")
async def get_cost_by_complexity(
    start_date: datetime | None = Query(None, description="Start of period"),
    end_date: datetime | None = Query(None, description="End of period"),
    session: Session = Depends(get_current_session),
) -> dict[str, dict[str, Any]]:
    """Get cost breakdown by query complexity.

    Returns total cost, query count, and percentage by complexity level.
    Requires authentication.

    Args:
        start_date: Optional start of period
        end_date: Optional end of period
        session: Current user session

    Returns:
        Dict mapping complexity level to cost metrics
    """
    try:
        dashboard = get_cost_monitoring_dashboard()
        result = await dashboard.get_cost_by_complexity(start_date, end_date)

        logger.info(
            "cost_by_complexity_requested",
            user_id=session.user_id,
            start_date=str(start_date),
            end_date=str(end_date),
        )

        return result

    except Exception as e:
        logger.error("cost_by_complexity_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get cost by complexity")


@router.get("/costs/daily")
async def get_daily_costs(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    user_id: str | None = Query(None, description="Filter by user ID"),
    session: Session = Depends(get_current_session),
) -> list[dict[str, Any]]:
    """Get daily cost aggregates.

    Returns daily total cost and query count.
    Requires authentication.

    Args:
        days: Number of days to look back (1-90)
        user_id: Optional user ID filter
        session: Current user session

    Returns:
        List of daily aggregate records
    """
    try:
        dashboard = get_cost_monitoring_dashboard()
        result = await dashboard.get_daily_aggregates(days=days, user_id=user_id)

        logger.info(
            "daily_costs_requested",
            requesting_user_id=session.user_id,
            filter_user_id=user_id,
            days=days,
            result_count=len(result),
        )

        return result

    except Exception as e:
        logger.error("daily_costs_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get daily costs")


@router.get("/costs/weekly")
async def get_weekly_costs(
    weeks: int = Query(4, ge=1, le=52, description="Number of weeks to look back"),
    user_id: str | None = Query(None, description="Filter by user ID"),
    session: Session = Depends(get_current_session),
) -> list[dict[str, Any]]:
    """Get weekly cost aggregates.

    Returns weekly total cost and query count.
    Requires authentication.

    Args:
        weeks: Number of weeks to look back (1-52)
        user_id: Optional user ID filter
        session: Current user session

    Returns:
        List of weekly aggregate records
    """
    try:
        dashboard = get_cost_monitoring_dashboard()
        result = await dashboard.get_weekly_aggregates(weeks=weeks, user_id=user_id)

        logger.info(
            "weekly_costs_requested",
            requesting_user_id=session.user_id,
            filter_user_id=user_id,
            weeks=weeks,
            result_count=len(result),
        )

        return result

    except Exception as e:
        logger.error("weekly_costs_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get weekly costs")
