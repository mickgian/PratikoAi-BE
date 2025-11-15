"""Pydantic schemas for metrics API endpoints."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class MetricResultResponse(BaseModel):
    """Response model for individual metric result."""

    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Current metric value")
    target: float = Field(..., description="Target metric value")
    status: str = Field(..., description="Metric status (PASS/FAIL/WARNING/UNKNOWN)")
    unit: str = Field(..., description="Metric unit")
    description: str = Field(..., description="Metric description")
    timestamp: datetime = Field(..., description="Metric collection timestamp")


class MetricsReportResponse(BaseModel):
    """Response model for complete metrics report."""

    environment: str = Field(..., description="Environment name")
    timestamp: datetime = Field(..., description="Report generation timestamp")
    technical_metrics: list[MetricResultResponse] = Field(..., description="Technical metrics")
    business_metrics: list[MetricResultResponse] = Field(..., description="Business metrics")
    overall_health_score: float = Field(..., description="Overall health score (0-100)")
    alerts: list[str] = Field(..., description="Active alerts")
    recommendations: list[str] = Field(..., description="Improvement recommendations")


class EnvironmentMetricsResponse(BaseModel):
    """Response model for environment-specific metrics."""

    environment: str = Field(..., description="Environment name")
    health_score: float = Field(..., description="Environment health score")
    alert_count: int = Field(..., description="Number of active alerts")
    critical_alerts: int = Field(..., description="Number of critical alerts")
    timestamp: datetime = Field(..., description="Metrics timestamp")


class ScheduledTaskResponse(BaseModel):
    """Response model for scheduled task status."""

    name: str = Field(..., description="Task name")
    enabled: bool = Field(..., description="Whether task is enabled")
    interval: str = Field(..., description="Task execution interval")
    last_run: datetime | None = Field(None, description="Last execution time")
    next_run: datetime | None = Field(None, description="Next scheduled execution time")
    overdue: bool = Field(..., description="Whether task is overdue")


class EmailReportRequest(BaseModel):
    """Request model for sending email reports."""

    recipient_emails: list[EmailStr] = Field(..., description="List of email addresses to send report to")
    environments: list[str] = Field(
        default=["development", "staging", "production"], description="List of environments to include in report"
    )

    class Config:
        schema_extra = {
            "example": {
                "recipient_emails": ["admin@pratikoai.com", "dev-team@pratikoai.com"],
                "environments": ["development", "staging", "production"],
            }
        }


class HealthSummaryResponse(BaseModel):
    """Response model for system health summary."""

    overall_health_score: float = Field(..., description="Overall system health score")
    environments: dict = Field(..., description="Per-environment health data")
    total_environments: int = Field(..., description="Total number of environments")
    healthy_environments: int = Field(..., description="Number of healthy environments")
    timestamp: datetime = Field(..., description="Summary generation timestamp")


class SchedulerStatusResponse(BaseModel):
    """Response model for scheduler status."""

    scheduler_running: bool = Field(..., description="Whether scheduler is running")
    tasks: dict = Field(..., description="Status of all scheduled tasks")
    timestamp: datetime = Field(..., description="Status check timestamp")


class TaskExecutionResponse(BaseModel):
    """Response model for task execution requests."""

    message: str = Field(..., description="Execution status message")
    timestamp: datetime = Field(..., description="Request timestamp")
