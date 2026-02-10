"""Pydantic schemas for multi-model LLM comparison feature (DEV-256)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# Request schemas
class ComparisonRequest(BaseModel):
    """Request to run a multi-model comparison."""

    model_config = {"extra": "ignore"}

    query: str = Field(..., min_length=1, max_length=2000, description="Query to compare")
    model_ids: list[str] | None = Field(
        default=None,
        min_length=2,
        max_length=6,
        description="Model IDs to compare (e.g., ['openai:gpt-4o', 'anthropic:claude-3-sonnet']). If None, uses user preferences.",
    )


class VoteRequest(BaseModel):
    """Request to submit a vote for the best model."""

    model_config = {"extra": "ignore"}

    batch_id: str = Field(..., description="Batch ID of the comparison session")
    winner_model_id: str = Field(..., description="Model ID of the winner (e.g., 'openai:gpt-4o')")
    comment: str | None = Field(default=None, max_length=1000, description="Optional comment about the vote")


class ModelPreferencesRequest(BaseModel):
    """Request to update user model preferences."""

    model_config = {"extra": "ignore"}

    enabled_model_ids: list[str] = Field(
        ...,
        min_length=2,
        description="List of model IDs to enable for comparisons",
    )


class ExistingModelResponse(BaseModel):
    """Response from the current model (from main chat)."""

    model_config = {"extra": "ignore"}

    model_id: str = Field(..., description="Model ID (e.g., 'openai:gpt-4o')")
    response_text: str = Field(..., description="Response text from main chat")
    latency_ms: int = Field(..., description="Latency in milliseconds")
    cost_eur: float | None = Field(default=None, description="Cost in euros")
    input_tokens: int | None = Field(default=None, description="Input tokens used")
    output_tokens: int | None = Field(default=None, description="Output tokens used")
    trace_id: str | None = Field(default=None, description="Langfuse trace ID")


class ComparisonWithExistingRequest(BaseModel):
    """Request for comparison with an existing response from main chat."""

    model_config = {"extra": "ignore"}

    query: str = Field(..., min_length=1, max_length=2000, description="Query to compare")
    existing_response: ExistingModelResponse = Field(..., description="Existing response from main chat to reuse")
    enriched_prompt: str | None = Field(
        default=None,
        description="DEV-256: Full prompt sent to LLM including KB context, web results, system prompt, etc.",
    )
    model_ids: list[str] | None = Field(
        default=None,
        min_length=2,
        max_length=6,
        description="DEV-257: Model IDs to compare (user-selected from chat). If None, uses default best models.",
    )


# Pending comparison schemas (for storing comparison data from main chat)
class CreatePendingComparisonRequest(BaseModel):
    """Request to store pending comparison data from main chat."""

    model_config = {"extra": "ignore"}

    query: str = Field(..., min_length=1, max_length=2000, description="The user's question")
    response: str = Field(..., min_length=1, description="The AI response from main chat")
    model_id: str = Field(..., description="Model ID that generated the response (e.g., 'openai:gpt-4o')")
    enriched_prompt: str | None = Field(
        default=None,
        description="DEV-256: Full prompt sent to LLM including KB context, web results, system prompt, etc.",
    )
    # DEV-256: Metrics from the original response
    latency_ms: int | None = Field(default=None, description="Response latency in milliseconds")
    cost_eur: float | None = Field(default=None, description="Estimated cost in EUR")
    input_tokens: int | None = Field(default=None, description="Number of input tokens")
    output_tokens: int | None = Field(default=None, description="Number of output tokens")
    trace_id: str | None = Field(default=None, description="Langfuse trace ID")


class PendingComparisonResponse(BaseModel):
    """Response after creating a pending comparison."""

    pending_id: str = Field(..., description="UUID of the pending comparison")


class PendingComparisonData(BaseModel):
    """Data retrieved from a pending comparison."""

    query: str = Field(..., description="The user's question")
    response: str = Field(..., description="The AI response")
    model_id: str = Field(..., description="Model ID that generated the response")
    enriched_prompt: str | None = Field(
        default=None,
        description="DEV-256: Full prompt sent to LLM including KB context, web results, etc.",
    )
    # DEV-256: Metrics from the original response
    latency_ms: int | None = Field(default=None, description="Response latency in milliseconds")
    cost_eur: float | None = Field(default=None, description="Estimated cost in EUR")
    input_tokens: int | None = Field(default=None, description="Number of input tokens")
    output_tokens: int | None = Field(default=None, description="Number of output tokens")
    trace_id: str | None = Field(default=None, description="Langfuse trace ID")


# Response schemas
class ModelResponseInfo(BaseModel):
    """Information about a single model's response in a comparison."""

    model_id: str = Field(..., description="Model identifier (e.g., 'openai:gpt-4o')")
    provider: str
    model_name: str
    response_text: str
    latency_ms: int
    cost_eur: float | None
    input_tokens: int | None
    output_tokens: int | None
    status: str  # success, error, timeout
    error_message: str | None = None
    trace_id: str


class ComparisonResponse(BaseModel):
    """Response containing all model responses for a comparison."""

    batch_id: str
    query: str
    responses: list[ModelResponseInfo]
    created_at: datetime


class VoteResponse(BaseModel):
    """Response after submitting a vote."""

    success: bool
    message: str
    winner_model_id: str
    elo_changes: dict[str, float] | None = None  # model_id -> rating change


class AvailableModel(BaseModel):
    """Information about an available model."""

    model_id: str = Field(..., description="Model identifier (e.g., 'openai:gpt-4o')")
    provider: str
    model_name: str
    display_name: str
    is_enabled: bool = True
    is_best: bool = Field(default=False, description="Best model for its provider")
    is_current: bool = Field(default=False, description="Current production model")
    is_disabled: bool = Field(
        default=False, description="DEV-256: Provider is globally disabled (show in UI as disabled)"
    )
    elo_rating: float | None = None
    total_comparisons: int = 0
    wins: int = 0


class AvailableModelsResponse(BaseModel):
    """Response containing all available models with user preferences."""

    models: list[AvailableModel]


class ModelRanking(BaseModel):
    """Model ranking in the leaderboard."""

    rank: int
    model_id: str
    provider: str
    model_name: str
    display_name: str
    elo_rating: float
    total_comparisons: int
    wins: int
    win_rate: float


class LeaderboardResponse(BaseModel):
    """Response containing model leaderboard."""

    rankings: list[ModelRanking]
    last_updated: datetime


class ComparisonStats(BaseModel):
    """Statistics about a user's comparison activity."""

    total_comparisons: int
    total_votes: int
    comparisons_this_week: int
    votes_this_week: int
    favorite_model: str | None = None
    favorite_model_vote_count: int = 0


class ComparisonStatsResponse(BaseModel):
    """Response containing user comparison statistics."""

    stats: ComparisonStats


class ComparisonSessionSummary(BaseModel):
    """Summary of a comparison session for history."""

    session_id: UUID
    batch_id: str
    query: str
    models_compared: list[str]
    winner_model: str | None
    created_at: datetime


class ComparisonHistoryResponse(BaseModel):
    """Response containing user's comparison history."""

    sessions: list[ComparisonSessionSummary]
    total: int
    page: int
    page_size: int
