"""SQLModel tables for multi-model LLM comparison feature (DEV-256)."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship

from app.models.base import BaseModel


class ComparisonStatus(str, Enum):
    """Status of a model response in a comparison."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class ModelComparisonSession(BaseModel, table=True):  # type: ignore[call-arg]
    """Stores a comparison session where multiple models respond to the same query.

    Attributes:
        id: Primary key (UUID)
        batch_id: Unique identifier linking Langfuse traces for this comparison
        user_id: FK to user who initiated the comparison
        query_text: The query submitted for comparison (max 2000 chars)
        query_hash: SHA256 hash for grouping similar queries
        models_compared: JSON array of model_ids (e.g., ["openai:gpt-4o", "anthropic:claude-3-sonnet"])
        winner_model: The model_id voted as best (nullable until voted)
        vote_timestamp: When the vote was cast
        vote_comment: Optional comment from the user about their vote
        created_at: When the comparison was initiated (inherited from BaseModel)
    """

    __tablename__ = "model_comparison_sessions"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    batch_id: str = Field(unique=True, index=True, max_length=64)
    user_id: int = Field(foreign_key="user.id", index=True)
    query_text: str = Field(max_length=2000)
    query_hash: str = Field(index=True, max_length=64)
    models_compared: str = Field(max_length=500)  # JSON array of model_ids
    winner_model: str | None = Field(default=None, max_length=100)
    vote_timestamp: datetime | None = Field(default=None)
    vote_comment: str | None = Field(default=None, max_length=1000)

    # Relationships
    responses: list["ModelComparisonResponse"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class ModelComparisonResponse(BaseModel, table=True):  # type: ignore[call-arg]
    """Stores individual model responses within a comparison session.

    Attributes:
        id: Primary key (UUID)
        session_id: FK to the parent comparison session
        provider: Provider name (openai, anthropic, gemini, mistral)
        model_name: Specific model name (gpt-4o, claude-3-sonnet, etc.)
        response_text: The model's response content
        trace_id: Langfuse trace ID for this specific response
        latency_ms: Time taken to generate the response
        cost_eur: Estimated cost in EUR (nullable if not available)
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
        status: Response status (success, error, timeout)
        error_message: Error details if status is not success
        created_at: When this response was generated (inherited from BaseModel)
    """

    __tablename__ = "model_comparison_responses"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    session_id: UUID = Field(foreign_key="model_comparison_sessions.id", index=True)
    provider: str = Field(max_length=50, index=True)
    model_name: str = Field(max_length=100, index=True)
    response_text: str = Field(default="")
    trace_id: str = Field(max_length=64)
    latency_ms: int = Field(default=0)
    cost_eur: float | None = Field(default=None)
    input_tokens: int | None = Field(default=None)
    output_tokens: int | None = Field(default=None)
    status: str = Field(default=ComparisonStatus.SUCCESS.value, max_length=20)
    error_message: str | None = Field(default=None, max_length=1000)

    # Relationships
    session: ModelComparisonSession = Relationship(back_populates="responses")


class ModelEloRating(BaseModel, table=True):  # type: ignore[call-arg]
    """Tracks Elo ratings for each model based on user votes.

    Elo rating system:
    - Initial rating: 1500.0
    - K-factor: 32
    - Min: 0, Max: 3000 (to prevent overflow)

    Attributes:
        id: Primary key
        provider: Provider name
        model_name: Model name (unique per provider)
        elo_rating: Current Elo rating (default 1500.0)
        total_comparisons: Total number of comparisons this model participated in
        wins: Total number of wins
        last_updated: When the rating was last updated
    """

    __tablename__ = "model_elo_ratings"

    id: int = Field(default=None, primary_key=True)
    provider: str = Field(max_length=50, index=True)
    model_name: str = Field(max_length=100, index=True)
    elo_rating: float = Field(default=1500.0)
    total_comparisons: int = Field(default=0)
    wins: int = Field(default=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """SQLModel config."""

        # Unique constraint on (provider, model_name)
        pass


class UserModelPreference(BaseModel, table=True):  # type: ignore[call-arg]
    """Stores user preferences for which models to include in comparisons.

    Attributes:
        id: Primary key
        user_id: FK to user
        provider: Provider name
        model_name: Model name
        is_enabled: Whether this model is enabled for comparisons
    """

    __tablename__ = "user_model_preferences"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    provider: str = Field(max_length=50)
    model_name: str = Field(max_length=100)
    is_enabled: bool = Field(default=True)

    class Config:
        """SQLModel config."""

        # Unique constraint on (user_id, provider, model_name)
        pass


class PendingComparison(BaseModel, table=True):  # type: ignore[call-arg]
    """Temporary storage for pending comparison data from main chat.

    Stores the query and response from main chat so the comparison page
    can retrieve it. Auto-expires after 1 hour for cleanup.

    Attributes:
        id: Primary key (UUID)
        user_id: FK to user who initiated the comparison
        query: The user's question (max 2000 chars recommended)
        response: The AI response (can be very long)
        model_id: The model that generated the response (e.g., "openai:gpt-4o")
        enriched_prompt: DEV-256: Full prompt sent to LLM including KB context, web results, etc.
        latency_ms: DEV-256: Response latency in milliseconds
        cost_eur: DEV-256: Estimated cost in EUR
        input_tokens: DEV-256: Number of input tokens
        output_tokens: DEV-256: Number of output tokens
        trace_id: DEV-256: Langfuse trace ID for the original response
        created_at: When the pending comparison was created
        expires_at: When this record should be deleted (for cleanup job)
    """

    __tablename__ = "pending_comparison"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    query: str  # TEXT - can be long
    response: str  # TEXT - can be very long
    model_id: str = Field(max_length=100)
    enriched_prompt: str | None = Field(default=None)  # DEV-256: Full LLM prompt with context
    latency_ms: int | None = Field(default=None)  # DEV-256: Response latency
    cost_eur: float | None = Field(default=None)  # DEV-256: Estimated cost
    input_tokens: int | None = Field(default=None)  # DEV-256: Input token count
    output_tokens: int | None = Field(default=None)  # DEV-256: Output token count
    trace_id: str | None = Field(default=None, max_length=64)  # DEV-256: Langfuse trace ID
    expires_at: datetime
