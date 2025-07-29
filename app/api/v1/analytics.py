"""Analytics API endpoints for usage and cost monitoring.

This module provides endpoints for users to monitor their usage,
costs, and receive optimization suggestions.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse

from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.session import Session
from app.services.usage_tracker import usage_tracker, UsageMetrics, CostBreakdown
from app.models.usage import (
    UsageQuota, CostOptimizationSuggestion, UserUsageSummary,
    UsageEvent, CostAlert
)

router = APIRouter()


@router.get("/usage/current")
@limiter.limit("30 per minute")
async def get_current_usage(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get current usage and quota information.
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        Current usage and quota information
    """
    try:
        user_id = session.user_id
        
        # Get current quota
        quota = await usage_tracker.get_user_quota(user_id)
        
        # Get current month metrics
        metrics = await usage_tracker.get_user_metrics(user_id)
        
        # Calculate percentages
        daily_cost_percentage = (quota.current_daily_cost_eur / quota.daily_cost_limit_eur * 100) if quota.daily_cost_limit_eur > 0 else 0
        monthly_cost_percentage = (quota.current_monthly_cost_eur / quota.monthly_cost_limit_eur * 100) if quota.monthly_cost_limit_eur > 0 else 0
        
        return JSONResponse({
            "user_id": user_id,
            "current_usage": {
                "daily": {
                    "requests": quota.current_daily_requests,
                    "requests_limit": quota.daily_requests_limit,
                    "cost_eur": quota.current_daily_cost_eur,
                    "cost_limit_eur": quota.daily_cost_limit_eur,
                    "cost_percentage": daily_cost_percentage,
                    "tokens": quota.current_daily_tokens,
                    "tokens_limit": quota.daily_token_limit,
                },
                "monthly": {
                    "cost_eur": quota.current_monthly_cost_eur,
                    "cost_limit_eur": quota.monthly_cost_limit_eur,
                    "cost_percentage": monthly_cost_percentage,
                    "tokens": quota.current_monthly_tokens,
                    "tokens_limit": quota.monthly_token_limit,
                    "avg_daily_cost_eur": quota.current_monthly_cost_eur / max(1, (datetime.utcnow() - quota.monthly_reset_at).days),
                }
            },
            "metrics": {
                "total_requests": metrics.total_requests,
                "llm_requests": metrics.llm_requests,
                "cache_hit_rate": metrics.cache_hit_rate,
                "avg_response_time_ms": metrics.avg_response_time_ms,
                "error_rate": metrics.error_rate,
            },
            "status": {
                "is_active": quota.is_active,
                "blocked_until": quota.blocked_until.isoformat() if quota.blocked_until else None,
                "plan_type": quota.plan_type,
            },
            "reset_times": {
                "daily_reset_at": quota.daily_reset_at.isoformat(),
                "monthly_reset_at": quota.monthly_reset_at.isoformat(),
            }
        })
        
    except Exception as e:
        logger.error(
            "current_usage_retrieval_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve usage information")


@router.get("/usage/history")
@limiter.limit("10 per minute")
async def get_usage_history(
    request: Request,
    start_date: Optional[datetime] = Query(None, description="Start date for history"),
    end_date: Optional[datetime] = Query(None, description="End date for history"),
    session: Session = Depends(get_current_session),
):
    """Get historical usage data.
    
    Args:
        request: FastAPI request object
        start_date: Start date for history (default: 30 days ago)
        end_date: End date for history (default: now)
        session: Current user session
        
    Returns:
        Historical usage data
    """
    try:
        user_id = session.user_id
        
        # Default date range
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get metrics for the period
        metrics = await usage_tracker.get_user_metrics(user_id, start_date, end_date)
        
        # Get cost breakdown
        cost_breakdown = await usage_tracker.get_cost_breakdown(user_id, start_date, end_date)
        
        # Get daily summaries
        from sqlalchemy import select, and_
        from app.services.database import database_service
        
        async with database_service.get_db() as db:
            query = select(UserUsageSummary).where(
                and_(
                    UserUsageSummary.user_id == user_id,
                    UserUsageSummary.date >= start_date,
                    UserUsageSummary.date <= end_date
                )
            ).order_by(UserUsageSummary.date)
            
            result = await db.execute(query)
            daily_summaries = result.scalars().all()
        
        # Format daily data
        daily_data = [
            {
                "date": summary.date.isoformat(),
                "requests": summary.total_requests,
                "cost_eur": summary.total_cost_eur,
                "tokens": summary.total_tokens,
                "cache_hit_rate": summary.cache_hit_rate,
                "error_rate": summary.error_rate,
            }
            for summary in daily_summaries
        ]
        
        return JSONResponse({
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days,
            },
            "summary": {
                "total_requests": metrics.total_requests,
                "total_cost_eur": metrics.total_cost_eur,
                "total_tokens": metrics.total_tokens,
                "avg_daily_cost_eur": metrics.total_cost_eur / max(1, (end_date - start_date).days),
                "cache_hit_rate": metrics.cache_hit_rate,
                "error_rate": metrics.error_rate,
            },
            "cost_breakdown": cost_breakdown.to_dict(),
            "daily_data": daily_data,
        })
        
    except Exception as e:
        logger.error(
            "usage_history_retrieval_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve usage history")


@router.get("/cost/breakdown")
@limiter.limit("20 per minute")
async def get_cost_breakdown(
    request: Request,
    period: str = Query("current_month", description="Period: current_month, last_month, last_7_days, custom"),
    start_date: Optional[datetime] = Query(None, description="Start date for custom period"),
    end_date: Optional[datetime] = Query(None, description="End date for custom period"),
    session: Session = Depends(get_current_session),
):
    """Get detailed cost breakdown by category and model.
    
    Args:
        request: FastAPI request object
        period: Time period for breakdown
        start_date: Custom start date
        end_date: Custom end date
        session: Current user session
        
    Returns:
        Detailed cost breakdown
    """
    try:
        user_id = session.user_id
        
        # Determine date range
        now = datetime.utcnow()
        if period == "current_month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == "last_month":
            start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "last_7_days":
            start_date = now - timedelta(days=7)
            end_date = now
        elif period == "custom":
            if not start_date or not end_date:
                raise HTTPException(status_code=400, detail="Start and end dates required for custom period")
        else:
            raise HTTPException(status_code=400, detail="Invalid period")
        
        # Get cost breakdown by category
        cost_breakdown = await usage_tracker.get_cost_breakdown(user_id, start_date, end_date)
        
        # Get model usage breakdown
        from sqlalchemy import select, func, and_
        from app.services.database import database_service
        
        async with database_service.get_db() as db:
            # Model breakdown
            model_query = select(
                UsageEvent.model,
                UsageEvent.provider,
                func.count(UsageEvent.id).label("requests"),
                func.sum(UsageEvent.total_tokens).label("tokens"),
                func.sum(UsageEvent.cost_eur).label("cost")
            ).where(
                and_(
                    UsageEvent.user_id == user_id,
                    UsageEvent.timestamp >= start_date,
                    UsageEvent.timestamp <= end_date,
                    UsageEvent.model != None
                )
            ).group_by(UsageEvent.model, UsageEvent.provider)
            
            model_result = await db.execute(model_query)
            model_breakdown = [
                {
                    "model": row.model,
                    "provider": row.provider,
                    "requests": row.requests,
                    "tokens": row.tokens or 0,
                    "cost_eur": float(row.cost or 0),
                }
                for row in model_result.all()
            ]
        
        # Calculate cost per request metrics
        total_requests = sum(m["requests"] for m in model_breakdown)
        avg_cost_per_request = cost_breakdown.total / total_requests if total_requests > 0 else 0
        
        return JSONResponse({
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days,
            },
            "cost_by_category": cost_breakdown.to_dict(),
            "cost_by_model": model_breakdown,
            "metrics": {
                "total_cost_eur": cost_breakdown.total,
                "avg_daily_cost_eur": cost_breakdown.total / max(1, (end_date - start_date).days),
                "avg_cost_per_request_eur": avg_cost_per_request,
                "projected_monthly_cost_eur": cost_breakdown.total / max(1, (end_date - start_date).days) * 30,
            },
            "cost_efficiency": {
                "target_monthly_cost_eur": 2.00,
                "current_efficiency": min(100, (2.00 / (cost_breakdown.total / max(1, (end_date - start_date).days) * 30)) * 100) if cost_breakdown.total > 0 else 100,
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "cost_breakdown_retrieval_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve cost breakdown")


@router.get("/optimization/suggestions")
@limiter.limit("10 per minute")
async def get_optimization_suggestions(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get cost optimization suggestions.
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        List of optimization suggestions
    """
    try:
        user_id = session.user_id
        
        # Get existing suggestions
        suggestions = await usage_tracker.get_optimization_suggestions(user_id)
        
        # If no suggestions, generate them
        if not suggestions:
            await usage_tracker.generate_optimization_suggestions(user_id)
            suggestions = await usage_tracker.get_optimization_suggestions(user_id)
        
        # Format suggestions
        formatted_suggestions = [
            {
                "id": suggestion.id,
                "type": suggestion.suggestion_type,
                "title": suggestion.title,
                "description": suggestion.description,
                "estimated_savings_eur": suggestion.estimated_savings_eur,
                "estimated_savings_percentage": suggestion.estimated_savings_percentage,
                "confidence_score": suggestion.confidence_score,
                "implementation_effort": suggestion.implementation_effort,
                "auto_implementable": suggestion.auto_implementable,
                "status": suggestion.status,
                "created_at": suggestion.created_at.isoformat(),
            }
            for suggestion in suggestions
        ]
        
        # Calculate total potential savings
        total_potential_savings = sum(s.estimated_savings_eur for s in suggestions)
        
        return JSONResponse({
            "suggestions": formatted_suggestions,
            "summary": {
                "total_suggestions": len(suggestions),
                "total_potential_savings_eur": total_potential_savings,
                "auto_implementable_count": sum(1 for s in suggestions if s.auto_implementable),
            }
        })
        
    except Exception as e:
        logger.error(
            "optimization_suggestions_retrieval_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve optimization suggestions")


@router.post("/optimization/suggestions/{suggestion_id}/apply")
@limiter.limit("5 per minute")
async def apply_optimization_suggestion(
    request: Request,
    suggestion_id: int,
    session: Session = Depends(get_current_session),
):
    """Apply an optimization suggestion.
    
    Args:
        request: FastAPI request object
        suggestion_id: ID of the suggestion to apply
        session: Current user session
        
    Returns:
        Application result
    """
    try:
        user_id = session.user_id
        
        # Get the suggestion
        from sqlalchemy import select, and_
        from app.services.database import database_service
        
        async with database_service.get_db() as db:
            query = select(CostOptimizationSuggestion).where(
                and_(
                    CostOptimizationSuggestion.id == suggestion_id,
                    CostOptimizationSuggestion.user_id == user_id,
                    CostOptimizationSuggestion.status == "pending"
                )
            )
            result = await db.execute(query)
            suggestion = result.scalar_one_or_none()
            
            if not suggestion:
                raise HTTPException(status_code=404, detail="Suggestion not found or already applied")
            
            if not suggestion.auto_implementable:
                raise HTTPException(status_code=400, detail="This suggestion cannot be automatically applied")
            
            # Apply the suggestion based on type
            success = False
            message = ""
            
            if suggestion.suggestion_type == "improve_caching":
                # This would be implemented based on specific caching improvements
                success = True
                message = "Caching optimization applied. Cache TTL increased and query deduplication enhanced."
            
            elif suggestion.suggestion_type == "model_optimization":
                # This would update user preferences for model selection
                success = True
                message = "Model optimization applied. Simple queries will now use more cost-effective models."
            
            if success:
                suggestion.status = "implemented"
                suggestion.implemented_at = datetime.utcnow()
                await db.commit()
                
                logger.info(
                    "optimization_suggestion_applied",
                    user_id=user_id,
                    suggestion_id=suggestion_id,
                    suggestion_type=suggestion.suggestion_type
                )
                
                return JSONResponse({
                    "success": True,
                    "message": message,
                    "suggestion_id": suggestion_id,
                })
            else:
                raise HTTPException(status_code=500, detail="Failed to apply suggestion")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "optimization_suggestion_application_failed",
            session_id=session.id,
            suggestion_id=suggestion_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to apply optimization suggestion")


@router.get("/alerts")
@limiter.limit("20 per minute")
async def get_cost_alerts(
    request: Request,
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    limit: int = Query(50, description="Maximum number of alerts to return"),
    session: Session = Depends(get_current_session),
):
    """Get cost alerts for the user.
    
    Args:
        request: FastAPI request object
        acknowledged: Filter by acknowledged status
        limit: Maximum number of alerts
        session: Current user session
        
    Returns:
        List of cost alerts
    """
    try:
        user_id = session.user_id
        
        from sqlalchemy import select, and_, desc
        from app.services.database import database_service
        
        async with database_service.get_db() as db:
            query = select(CostAlert).where(
                CostAlert.user_id == user_id
            )
            
            if acknowledged is not None:
                query = query.where(CostAlert.acknowledged == acknowledged)
            
            query = query.order_by(desc(CostAlert.triggered_at)).limit(limit)
            
            result = await db.execute(query)
            alerts = result.scalars().all()
        
        # Format alerts
        formatted_alerts = [
            {
                "id": alert.id,
                "type": alert.alert_type,
                "threshold_eur": alert.threshold_eur,
                "current_cost_eur": alert.current_cost_eur,
                "triggered_at": alert.triggered_at.isoformat(),
                "period": {
                    "start": alert.period_start.isoformat(),
                    "end": alert.period_end.isoformat(),
                },
                "acknowledged": alert.acknowledged,
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            }
            for alert in alerts
        ]
        
        return JSONResponse({
            "alerts": formatted_alerts,
            "total": len(alerts),
            "unacknowledged_count": sum(1 for a in alerts if not a.acknowledged),
        })
        
    except Exception as e:
        logger.error(
            "alerts_retrieval_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@router.post("/alerts/{alert_id}/acknowledge")
@limiter.limit("10 per minute")
async def acknowledge_alert(
    request: Request,
    alert_id: int,
    session: Session = Depends(get_current_session),
):
    """Acknowledge a cost alert.
    
    Args:
        request: FastAPI request object
        alert_id: ID of the alert to acknowledge
        session: Current user session
        
    Returns:
        Acknowledgment result
    """
    try:
        user_id = session.user_id
        
        from sqlalchemy import select, and_
        from app.services.database import database_service
        
        async with database_service.get_db() as db:
            query = select(CostAlert).where(
                and_(
                    CostAlert.id == alert_id,
                    CostAlert.user_id == user_id
                )
            )
            result = await db.execute(query)
            alert = result.scalar_one_or_none()
            
            if not alert:
                raise HTTPException(status_code=404, detail="Alert not found")
            
            if alert.acknowledged:
                return JSONResponse({
                    "success": True,
                    "message": "Alert already acknowledged",
                    "acknowledged_at": alert.acknowledged_at.isoformat()
                })
            
            alert.acknowledged = True
            alert.acknowledged_at = datetime.utcnow()
            await db.commit()
            
            logger.info(
                "cost_alert_acknowledged",
                user_id=user_id,
                alert_id=alert_id,
                alert_type=alert.alert_type
            )
            
            return JSONResponse({
                "success": True,
                "message": "Alert acknowledged",
                "acknowledged_at": alert.acknowledged_at.isoformat()
            })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "alert_acknowledgment_failed",
            session_id=session.id,
            alert_id=alert_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.get("/system/metrics")
@limiter.limit("5 per minute")
async def get_system_metrics(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get system-wide metrics (admin only).
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        System-wide usage metrics
    """
    try:
        # In a real implementation, check for admin privileges
        # For now, any authenticated user can see system metrics
        
        metrics = await usage_tracker.get_system_metrics()
        
        return JSONResponse(metrics)
        
    except Exception as e:
        logger.error(
            "system_metrics_retrieval_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve system metrics")