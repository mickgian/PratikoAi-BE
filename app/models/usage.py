"""Usage tracking models for cost monitoring and analytics.

This module defines database models for tracking LLM usage, costs,
and user consumption patterns to maintain the €2/user/month target.
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint
from enum import Enum


class UsageType(str, Enum):
    """Types of usage events to track."""
    LLM_QUERY = "llm_query"
    LLM_STREAM = "llm_stream"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    API_REQUEST = "api_request"


class CostCategory(str, Enum):
    """Categories of costs for tracking."""
    LLM_INFERENCE = "llm_inference"
    STORAGE = "storage"
    COMPUTE = "compute"
    BANDWIDTH = "bandwidth"
    THIRD_PARTY = "third_party"


class UsageEvent(SQLModel, table=True):
    """Individual usage event record."""
    
    __tablename__ = "usage_events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # User and session information
    user_id: str = Field(index=True, description="User identifier")
    session_id: Optional[str] = Field(default=None, index=True, description="Session identifier")
    
    # Event details
    event_type: UsageType = Field(description="Type of usage event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # LLM specific fields
    provider: Optional[str] = Field(default=None, description="LLM provider (openai, anthropic)")
    model: Optional[str] = Field(default=None, description="Model used")
    input_tokens: Optional[int] = Field(default=None, description="Input tokens consumed")
    output_tokens: Optional[int] = Field(default=None, description="Output tokens generated")
    total_tokens: Optional[int] = Field(default=None, description="Total tokens used")
    
    # Cost information
    cost_eur: Optional[float] = Field(default=None, description="Cost in EUR")
    cost_category: Optional[CostCategory] = Field(default=None, description="Cost category")
    
    # Performance metrics
    response_time_ms: Optional[int] = Field(default=None, description="Response time in milliseconds")
    cache_hit: Optional[bool] = Field(default=None, description="Whether request was served from cache")
    
    # Request metadata
    request_size: Optional[int] = Field(default=None, description="Request size in bytes")
    response_size: Optional[int] = Field(default=None, description="Response size in bytes")
    
    # Geographic and technical info
    ip_address: Optional[str] = Field(default=None, description="Client IP address (anonymized)")
    user_agent: Optional[str] = Field(default=None, description="Client user agent")
    country_code: Optional[str] = Field(default=None, description="Country code")
    
    # Error tracking
    error_occurred: bool = Field(default=False, description="Whether an error occurred")
    error_type: Optional[str] = Field(default=None, description="Type of error if any")
    
    # Anonymization info
    pii_detected: bool = Field(default=False, description="Whether PII was detected and anonymized")
    pii_types: Optional[str] = Field(default=None, description="JSON array of PII types found")


class UserUsageSummary(SQLModel, table=True):
    """Daily usage summary per user for efficient querying."""
    
    __tablename__ = "user_usage_summaries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # User and time period
    user_id: str = Field(index=True, description="User identifier")
    date: datetime = Field(index=True, description="Date for this summary")
    
    # Usage counts
    total_requests: int = Field(default=0, description="Total requests made")
    llm_requests: int = Field(default=0, description="LLM requests made")
    cache_hits: int = Field(default=0, description="Cache hits")
    cache_misses: int = Field(default=0, description="Cache misses")
    
    # Token usage
    total_input_tokens: int = Field(default=0, description="Total input tokens")
    total_output_tokens: int = Field(default=0, description="Total output tokens")
    total_tokens: int = Field(default=0, description="Total tokens used")
    
    # Cost tracking
    total_cost_eur: float = Field(default=0.0, description="Total cost in EUR")
    llm_cost_eur: float = Field(default=0.0, description="LLM-specific costs")
    
    # Performance metrics
    avg_response_time_ms: Optional[float] = Field(default=None, description="Average response time")
    cache_hit_rate: float = Field(default=0.0, description="Cache hit rate (0-1)")
    
    # Error tracking
    error_count: int = Field(default=0, description="Number of errors")
    error_rate: float = Field(default=0.0, description="Error rate (0-1)")
    
    # Model usage breakdown (JSON)
    model_usage: Optional[str] = Field(default=None, description="JSON object with model usage stats")
    provider_usage: Optional[str] = Field(default=None, description="JSON object with provider usage stats")
    
    # Data quality metrics
    pii_detections: int = Field(default=0, description="Number of PII detections")
    anonymization_rate: float = Field(default=0.0, description="Rate of requests with PII (0-1)")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Unique constraint on user_id + date
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="unique_user_date_summary"),
    )


class CostAlert(SQLModel, table=True):
    """Cost alert tracking for budget management."""
    
    __tablename__ = "cost_alerts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Alert configuration
    user_id: Optional[str] = Field(default=None, index=True, description="User ID (null for system-wide)")
    alert_type: str = Field(description="Type of alert (daily, monthly, threshold)")
    threshold_eur: float = Field(description="Cost threshold in EUR")
    
    # Alert status
    triggered_at: datetime = Field(default_factory=datetime.utcnow, description="When alert was triggered")
    current_cost_eur: float = Field(description="Current cost when alert triggered")
    
    # Alert details
    period_start: datetime = Field(description="Start of the period being monitored")
    period_end: datetime = Field(description="End of the period being monitored")
    
    # Notification status
    notification_sent: bool = Field(default=False, description="Whether notification was sent")
    notification_type: Optional[str] = Field(default=None, description="Type of notification sent")
    
    # Additional data
    extra_data: Optional[str] = Field(default=None, description="Additional metadata as JSON")
    acknowledged: bool = Field(default=False, description="Whether alert was acknowledged")
    acknowledged_at: Optional[datetime] = Field(default=None, description="When alert was acknowledged")


class UsageQuota(SQLModel, table=True):
    """User usage quotas and limits."""
    
    __tablename__ = "usage_quotas"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # User information
    user_id: str = Field(unique=True, index=True, description="User identifier")
    
    # Quota limits
    daily_requests_limit: int = Field(default=100, description="Daily request limit")
    daily_cost_limit_eur: float = Field(default=0.10, description="Daily cost limit in EUR")
    monthly_cost_limit_eur: float = Field(default=2.00, description="Monthly cost limit in EUR")
    
    # Token limits
    daily_token_limit: int = Field(default=50000, description="Daily token limit")
    monthly_token_limit: int = Field(default=1000000, description="Monthly token limit")
    
    # Current usage (reset daily/monthly)
    current_daily_requests: int = Field(default=0, description="Current daily requests")
    current_daily_cost_eur: float = Field(default=0.0, description="Current daily cost")
    current_monthly_cost_eur: float = Field(default=0.0, description="Current monthly cost")
    current_daily_tokens: int = Field(default=0, description="Current daily tokens")
    current_monthly_tokens: int = Field(default=0, description="Current monthly tokens")
    
    # Reset tracking
    daily_reset_at: datetime = Field(default_factory=datetime.utcnow, description="Last daily reset")
    monthly_reset_at: datetime = Field(default_factory=datetime.utcnow, description="Last monthly reset")
    
    # Status
    is_active: bool = Field(default=True, description="Whether quota is active")
    blocked_until: Optional[datetime] = Field(default=None, description="Blocked until this time")
    
    # Metadata
    plan_type: str = Field(default="basic", description="User's plan type")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CostOptimizationSuggestion(SQLModel, table=True):
    """AI-generated cost optimization suggestions."""
    
    __tablename__ = "cost_optimization_suggestions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Target
    user_id: Optional[str] = Field(default=None, index=True, description="User ID (null for system-wide)")
    
    # Suggestion details
    suggestion_type: str = Field(description="Type of suggestion (model_switch, caching, etc.)")
    title: str = Field(description="Suggestion title")
    description: str = Field(description="Detailed description")
    
    # Impact estimation
    estimated_savings_eur: float = Field(description="Estimated monthly savings in EUR")
    estimated_savings_percentage: float = Field(description="Estimated savings percentage")
    confidence_score: float = Field(description="Confidence in the suggestion (0-1)")
    
    # Implementation
    implementation_effort: str = Field(description="Implementation effort (low, medium, high)")
    auto_implementable: bool = Field(default=False, description="Can be auto-implemented")
    
    # Status
    status: str = Field(default="pending", description="pending, accepted, rejected, implemented")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    implemented_at: Optional[datetime] = Field(default=None)
    
    # Results tracking
    actual_savings_eur: Optional[float] = Field(default=None, description="Actual savings achieved")
    effectiveness_score: Optional[float] = Field(default=None, description="How effective the suggestion was")
    
    # Metadata
    extra_data: Optional[str] = Field(default=None, description="Additional data as JSON")