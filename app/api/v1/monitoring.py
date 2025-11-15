"""Monitoring API endpoints for Prometheus metrics.

This module provides endpoints for Prometheus to scrape metrics
and for administrators to check monitoring status.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST

from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.logging import logger
from app.core.monitoring.metrics import get_metrics_content, get_registry
from app.models.session import Session

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
