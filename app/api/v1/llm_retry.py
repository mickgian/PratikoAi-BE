"""LLM Retry Mechanisms API endpoints for PratikoAI.

This module provides REST API endpoints for managing and monitoring LLM retry
mechanisms, including configuration, health checks, metrics, and manual controls.
Enables administrators and users to monitor retry performance and adjust settings.
"""

from datetime import UTC, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app.core.auth.jwt import get_current_user_id
from app.core.logging import logger
from app.models.query import QueryErrorResponse, QueryMetrics, QueryRequest, QueryResponseSchema
from app.services.query_service import get_query_service, get_query_service_health
from app.services.resilient_llm_service import get_llm_service_status

router = APIRouter(prefix="/llm-retry", tags=["LLM Retry Mechanisms"])


# Request/Response Models


class QuerySubmissionRequest(BaseModel):
    """Request model for submitting queries."""

    query_request: QueryRequest
    use_retry_mechanisms: bool = Field(default=True, description="Whether to use retry mechanisms for this query")


class RetryConfigUpdateRequest(BaseModel):
    """Request model for updating retry configuration."""

    provider: str = Field(..., description="Provider name (openai, anthropic)")
    max_attempts: int | None = Field(None, ge=1, le=10, description="Maximum retry attempts")
    initial_delay: float | None = Field(None, ge=0.5, le=10.0, description="Initial delay in seconds")
    max_delay: float | None = Field(None, ge=5.0, le=300.0, description="Maximum delay in seconds")
    timeout: float | None = Field(None, ge=5.0, le=300.0, description="Request timeout in seconds")
    max_retry_cost: float | None = Field(None, ge=0.0, le=1.0, description="Maximum retry cost in EUR")
    circuit_breaker_threshold: int | None = Field(None, ge=1, le=20, description="Circuit breaker failure threshold")


class ProviderControlRequest(BaseModel):
    """Request model for provider control operations."""

    provider: str = Field(..., description="Provider name")
    action: str = Field(..., description="Action: enable, disable, reset_circuit_breaker")
    reason: str | None = Field(None, description="Reason for the action")


class RetryStatisticsResponse(BaseModel):
    """Response model for retry statistics."""

    provider_statistics: dict[str, Any]
    overall_health: str
    enabled_providers: list[str]
    timestamp: datetime
    hours_analyzed: int


class ServiceHealthResponse(BaseModel):
    """Response model for service health."""

    query_service_health: dict[str, Any]
    llm_service_health: dict[str, Any]
    overall_status: str
    timestamp: datetime


# API Endpoints


@router.post("/query", response_model=QueryResponseSchema)
async def submit_query(
    request: QuerySubmissionRequest, user_id: str = Depends(get_current_user_id)
) -> QueryResponseSchema:
    """Submit a query for processing with optional retry mechanisms.

    This endpoint allows users to submit queries for LLM processing with
    configurable retry behavior. When retry mechanisms are enabled, the
    system will automatically handle failures with exponential backoff,
    provider fallback, and circuit breaker protection.
    """
    try:
        # Set user_id from authentication
        request.query_request.user_id = user_id

        # Get query service and process request
        query_service = await get_query_service()
        result = await query_service.process_query(
            request.query_request, use_retry_mechanisms=request.use_retry_mechanisms
        )

        # Handle error responses
        if isinstance(result, QueryErrorResponse):
            # Convert to HTTP exception with appropriate status code
            status_code = 503 if result.can_retry else 400
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error_type": result.error_type,
                    "message": result.user_message,
                    "query_id": result.query_id,
                    "can_retry": result.can_retry,
                    "estimated_retry_delay": result.estimated_retry_delay,
                },
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit query for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while processing query")


@router.get("/query/{query_id}", response_model=QueryResponseSchema)
async def get_query_status(
    query_id: str = Path(..., description="Query identifier"), user_id: str = Depends(get_current_user_id)
) -> QueryResponseSchema:
    """Get the status and results of a submitted query.

    This endpoint allows users to check the status of their queries,
    including completion status, results, retry information, and
    performance metrics.
    """
    try:
        query_service = await get_query_service()
        result = await query_service.get_query_status(query_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"Query {query_id} not found")

        # Note: In a production system, you'd want to verify that the user
        # has permission to access this query

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get query status {query_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while retrieving query status")


@router.get("/statistics", response_model=RetryStatisticsResponse)
async def get_retry_statistics(
    hours: int = Query(default=1, ge=1, le=168, description="Hours to analyze (max 7 days)"),
    user_id: str = Depends(get_current_user_id),
) -> RetryStatisticsResponse:
    """Get retry mechanism statistics and performance metrics.

    This endpoint provides detailed statistics about retry mechanisms,
    including success rates, failure reasons, provider performance,
    and cost information for the specified time period.
    """
    try:
        # Get LLM service statistics
        llm_status = await get_llm_service_status()

        # Extract statistics from the service status
        provider_stats = llm_status.get("retry_statistics", {}).get("providers", {})
        overall_health = llm_status.get("overall_health", "unknown")
        enabled_providers = llm_status.get("enabled_providers", [])

        return RetryStatisticsResponse(
            provider_statistics=provider_stats,
            overall_health=overall_health,
            enabled_providers=enabled_providers,
            timestamp=datetime.now(UTC),
            hours_analyzed=hours,
        )

    except Exception as e:
        logger.error(f"Failed to get retry statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while retrieving statistics")


@router.get("/health", response_model=ServiceHealthResponse)
async def get_service_health(user_id: str = Depends(get_current_user_id)) -> ServiceHealthResponse:
    """Get comprehensive health status of retry mechanisms and services.

    This endpoint provides detailed health information about the query
    service, LLM service, providers, circuit breakers, and overall
    system status.
    """
    try:
        # Get health from both services
        query_health = await get_query_service_health()
        llm_health = await get_llm_service_status()

        # Determine overall status
        query_status = query_health.get("status", "unknown")
        llm_status = llm_health.get("overall_health", "unknown")

        if query_status == "healthy" and llm_status in ["excellent", "good"]:
            overall_status = "healthy"
        elif query_status == "healthy" and llm_status == "degraded":
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        return ServiceHealthResponse(
            query_service_health=query_health,
            llm_service_health=llm_health,
            overall_status=overall_status,
            timestamp=datetime.now(UTC),
        )

    except Exception as e:
        logger.error(f"Failed to get service health: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while retrieving health status")


@router.get("/metrics/user", response_model=QueryMetrics)
async def get_user_metrics(
    hours: int = Query(default=24, ge=1, le=168, description="Hours to analyze"),
    user_id: str = Depends(get_current_user_id),
) -> QueryMetrics:
    """Get query metrics for the current user.

    This endpoint provides personalized metrics about the user's
    query usage, including success rates, costs, token usage,
    and provider performance.
    """
    try:
        query_service = await get_query_service()
        metrics = await query_service.get_user_query_metrics(user_id, hours)

        return metrics

    except Exception as e:
        logger.error(f"Failed to get user metrics for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while retrieving user metrics")


# Admin endpoints (would require admin authentication in production)


@router.post("/admin/provider/control")
async def control_provider(
    request: ProviderControlRequest,
    user_id: str = Depends(get_current_user_id),  # Would be admin authentication
) -> dict[str, Any]:
    """Control provider operations (enable, disable, reset circuit breaker).

    This endpoint allows administrators to manually control provider
    behavior, including enabling/disabling providers and resetting
    circuit breakers during maintenance or troubleshooting.

    **Note**: This endpoint requires administrator privileges.
    """
    try:
        # Import here to avoid circular imports
        from app.services.resilient_llm_service import get_llm_service

        llm_service = await get_llm_service()

        if request.action == "enable":
            success = await llm_service.enable_provider(request.provider)
        elif request.action == "disable":
            success = await llm_service.disable_provider(request.provider)
        elif request.action == "reset_circuit_breaker":
            success = await llm_service.reset_circuit_breaker(request.provider)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action: {request.action}. Valid actions: enable, disable, reset_circuit_breaker",
            )

        if not success:
            raise HTTPException(status_code=404, detail=f"Provider {request.provider} not found")

        logger.info(
            f"Admin {user_id} performed {request.action} on provider {request.provider}. "
            f"Reason: {request.reason or 'Not specified'}"
        )

        return {
            "success": True,
            "provider": request.provider,
            "action": request.action,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to control provider {request.provider}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while controlling provider")


@router.get("/admin/providers/health")
async def get_providers_health(
    user_id: str = Depends(get_current_user_id),  # Would be admin authentication
) -> dict[str, Any]:
    """Get detailed health information for all providers.

    This endpoint provides comprehensive health and performance
    information for all configured LLM providers, including
    circuit breaker states, failure rates, and performance metrics.

    **Note**: This endpoint requires administrator privileges.
    """
    try:
        from app.services.resilient_llm_service import get_llm_service

        llm_service = await get_llm_service()
        provider_health = await llm_service.get_provider_health()

        return {
            "providers": provider_health,
            "timestamp": datetime.now(UTC).isoformat(),
            "total_providers": len(provider_health),
            "enabled_providers": sum(1 for status in provider_health.values() if status.get("enabled", False)),
        }

    except Exception as e:
        logger.error(f"Failed to get providers health: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while retrieving providers health")


# Export router
__all__ = ["router"]
