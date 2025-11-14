"""
Metrics API endpoints for success metrics monitoring and reporting.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
from datetime import datetime

from app.services.metrics_service import metrics_service, Environment, MetricsReport
from app.services.email_service import email_service
from app.services.scheduler_service import scheduler_service
from app.schemas.metrics import (
    MetricsReportResponse,
    MetricResultResponse,
    EnvironmentMetricsResponse,
    ScheduledTaskResponse,
    EmailReportRequest
)

router = APIRouter()


@router.get("/report/{environment}", response_model=MetricsReportResponse)
async def get_metrics_report(environment: Environment):
    """Get comprehensive metrics report for a specific environment."""
    try:
        report = await metrics_service.generate_metrics_report(environment)
        
        return MetricsReportResponse(
            environment=report.environment.value,
            timestamp=report.timestamp,
            technical_metrics=[
                MetricResultResponse(
                    name=metric.name,
                    value=metric.value,
                    target=metric.target,
                    status=metric.status.value,
                    unit=metric.unit,
                    description=metric.description,
                    timestamp=metric.timestamp
                ) for metric in report.technical_metrics
            ],
            business_metrics=[
                MetricResultResponse(
                    name=metric.name,
                    value=metric.value,
                    target=metric.target,
                    status=metric.status.value,
                    unit=metric.unit,
                    description=metric.description,
                    timestamp=metric.timestamp
                ) for metric in report.business_metrics
            ],
            overall_health_score=report.overall_health_score,
            alerts=report.alerts,
            recommendations=report.recommendations
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate metrics report: {str(e)}")


@router.get("/report/all", response_model=List[MetricsReportResponse])
async def get_all_metrics_reports():
    """Get comprehensive metrics reports for all environments."""
    try:
        environments = [Environment.DEVELOPMENT, Environment.QA, Environment.PREPROD, Environment.PRODUCTION]
        reports = []
        
        for env in environments:
            try:
                report = await metrics_service.generate_metrics_report(env)
                
                reports.append(MetricsReportResponse(
                    environment=report.environment.value,
                    timestamp=report.timestamp,
                    technical_metrics=[
                        MetricResultResponse(
                            name=metric.name,
                            value=metric.value,
                            target=metric.target,
                            status=metric.status.value,
                            unit=metric.unit,
                            description=metric.description,
                            timestamp=metric.timestamp
                        ) for metric in report.technical_metrics
                    ],
                    business_metrics=[
                        MetricResultResponse(
                            name=metric.name,
                            value=metric.value,
                            target=metric.target,
                            status=metric.status.value,
                            unit=metric.unit,
                            description=metric.description,
                            timestamp=metric.timestamp
                        ) for metric in report.business_metrics
                    ],
                    overall_health_score=report.overall_health_score,
                    alerts=report.alerts,
                    recommendations=report.recommendations
                ))
            except Exception as e:
                # Log error but continue with other environments
                print(f"Failed to get report for {env.value}: {e}")
                continue
        
        return reports
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate metrics reports: {str(e)}")


@router.get("/technical/{environment}", response_model=List[MetricResultResponse])
async def get_technical_metrics(environment: Environment):
    """Get technical metrics for a specific environment."""
    try:
        metrics = await metrics_service.collect_technical_metrics(environment)
        
        return [
            MetricResultResponse(
                name=metric.name,
                value=metric.value,
                target=metric.target,
                status=metric.status.value,
                unit=metric.unit,
                description=metric.description,
                timestamp=metric.timestamp
            ) for metric in metrics
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to collect technical metrics: {str(e)}")


@router.get("/business/{environment}", response_model=List[MetricResultResponse])
async def get_business_metrics(environment: Environment):
    """Get business metrics for a specific environment."""
    try:
        metrics = await metrics_service.collect_business_metrics(environment)
        
        return [
            MetricResultResponse(
                name=metric.name,
                value=metric.value,
                target=metric.target,
                status=metric.status.value,
                unit=metric.unit,
                description=metric.description,
                timestamp=metric.timestamp
            ) for metric in metrics
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to collect business metrics: {str(e)}")


@router.get("/health-summary")
async def get_health_summary():
    """Get overall system health summary across all environments."""
    try:
        environments = [Environment.DEVELOPMENT, Environment.QA, Environment.PREPROD, Environment.PRODUCTION]
        summary = {}
        
        for env in environments:
            try:
                report = await metrics_service.generate_metrics_report(env)
                summary[env.value] = {
                    "health_score": report.overall_health_score,
                    "alert_count": len(report.alerts),
                    "critical_alerts": len([alert for alert in report.alerts if "CRITICAL" in alert]),
                    "timestamp": report.timestamp.isoformat()
                }
            except Exception as e:
                summary[env.value] = {
                    "health_score": 0.0,
                    "alert_count": 1,
                    "critical_alerts": 1,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        # Calculate overall system health
        valid_scores = [data["health_score"] for data in summary.values() if "error" not in data]
        overall_health = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
        
        return {
            "overall_health_score": overall_health,
            "environments": summary,
            "total_environments": len(environments),
            "healthy_environments": len([data for data in summary.values() if data["health_score"] >= 90]),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health summary: {str(e)}")


@router.post("/email-report")
async def send_email_report(request: EmailReportRequest, background_tasks: BackgroundTasks):
    """Send metrics report via email."""
    try:
        # Validate environments
        environments = []
        for env_str in request.environments:
            try:
                environments.append(Environment(env_str))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid environment: {env_str}")
        
        # Send email in background
        background_tasks.add_task(
            email_service.send_metrics_report,
            request.recipient_emails,
            environments
        )
        
        return {
            "message": f"Metrics report scheduled to be sent to {len(request.recipient_emails)} recipients",
            "recipients": request.recipient_emails,
            "environments": request.environments,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule email report: {str(e)}")


@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get status of scheduled tasks."""
    try:
        status = scheduler_service.get_task_status()
        
        return {
            "scheduler_running": scheduler_service.running,
            "tasks": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")


@router.post("/scheduler/run-task/{task_name}")
async def run_scheduled_task(task_name: str, background_tasks: BackgroundTasks):
    """Manually run a scheduled task."""
    try:
        # Run task in background
        background_tasks.add_task(scheduler_service.run_task_now, task_name)
        
        return {
            "message": f"Task '{task_name}' scheduled to run immediately",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run task: {str(e)}")


@router.post("/scheduler/enable-task/{task_name}")
async def enable_scheduled_task(task_name: str):
    """Enable a scheduled task."""
    try:
        success = scheduler_service.enable_task(task_name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_name}")
        
        return {
            "message": f"Task '{task_name}' enabled",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable task: {str(e)}")


@router.post("/scheduler/disable-task/{task_name}")
async def disable_scheduled_task(task_name: str):
    """Disable a scheduled task."""
    try:
        success = scheduler_service.disable_task(task_name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_name}")
        
        return {
            "message": f"Task '{task_name}' disabled",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable task: {str(e)}")