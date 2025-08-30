"""
Query models for LLM interactions in PratikoAI.

This module defines data models for LLM queries, responses, and metadata tracking
used throughout the retry mechanism and LLM service infrastructure.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field


class QueryStatus(str, Enum):
    """Status of a query request."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class QueryType(str, Enum):
    """Type of query being processed."""
    CHAT = "chat"
    COMPLETION = "completion"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    ANALYSIS = "analysis"


@dataclass
class LLMResponse:
    """
    Response from LLM provider with metadata.
    
    This matches the interface expected by the retry mechanisms
    and provides comprehensive tracking information.
    """
    text: str
    model: str
    provider: str
    tokens_used: int
    cost: float
    processing_time: float
    response_metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Add timestamp if not present."""
        if 'timestamp' not in self.response_metadata:
            self.response_metadata['timestamp'] = datetime.now(timezone.utc).isoformat()


@dataclass
class QueryResponse:
    """Complete query response with tracking information."""
    query_id: str
    user_id: str
    response: str
    status: QueryStatus
    model_used: str
    provider_used: str
    tokens_used: int
    cost: float
    processing_time: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    query_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.query_metadata is None:
            self.query_metadata = {}


class QueryRequest(BaseModel):
    """Pydantic model for incoming query requests."""
    
    prompt: str = Field(..., description="The query prompt", min_length=1, max_length=10000)
    user_id: str = Field(..., description="User identifier")
    query_type: QueryType = Field(default=QueryType.CHAT, description="Type of query")
    
    # Optional parameters
    model: Optional[str] = Field(None, description="Specific model to use")
    max_tokens: Optional[int] = Field(None, ge=1, le=4000, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature")
    system_prompt: Optional[str] = Field(None, max_length=5000, description="System prompt")
    
    # Retry configuration
    preferred_provider: str = Field(default="openai", description="Preferred LLM provider")
    allow_fallback: bool = Field(default=True, description="Allow fallback to other providers")
    timeout: Optional[float] = Field(None, ge=5.0, le=300.0, description="Request timeout in seconds")
    
    # Metadata
    conversation_id: Optional[str] = Field(None, description="Conversation identifier")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QueryResponseSchema(BaseModel):
    """Pydantic schema for query responses."""
    
    query_id: str
    response: str
    status: QueryStatus
    model_used: str
    provider_used: str
    tokens_used: int
    cost: float
    processing_time: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    was_fallback: bool = False
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QueryErrorResponse(BaseModel):
    """Error response for failed queries."""
    
    query_id: str
    error_type: str
    error_message: str
    user_message: str
    status: QueryStatus = QueryStatus.FAILED
    retry_count: int = 0
    can_retry: bool = False
    estimated_retry_delay: Optional[float] = None
    
    # Technical details for debugging
    provider_attempted: Optional[str] = None
    model_attempted: Optional[str] = None
    processing_time: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QueryMetrics(BaseModel):
    """Metrics for query processing."""
    
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    retry_attempts: int = 0
    average_processing_time: float = 0.0
    total_cost: float = 0.0
    total_tokens: int = 0
    
    # Provider breakdown
    provider_stats: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Time window
    start_time: datetime
    end_time: datetime
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_queries == 0:
            return 0.0
        return (self.successful_queries / self.total_queries) * 100
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        return 100.0 - self.success_rate
    
    @property
    def average_cost_per_query(self) -> float:
        """Calculate average cost per query."""
        if self.total_queries == 0:
            return 0.0
        return self.total_cost / self.total_queries


# Export main models
__all__ = [
    'QueryStatus',
    'QueryType', 
    'LLMResponse',
    'QueryResponse',
    'QueryRequest',
    'QueryResponseSchema',
    'QueryErrorResponse',
    'QueryMetrics'
]