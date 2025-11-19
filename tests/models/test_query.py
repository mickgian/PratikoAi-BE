"""Tests for query models."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.models.query import (
    LLMResponse,
    QueryErrorResponse,
    QueryMetrics,
    QueryRequest,
    QueryResponse,
    QueryResponseSchema,
    QueryStatus,
    QueryType,
)


class TestQueryStatus:
    """Test QueryStatus enum."""

    def test_status_values(self):
        """Test that query statuses have correct values."""
        assert QueryStatus.PENDING.value == "pending"
        assert QueryStatus.PROCESSING.value == "processing"
        assert QueryStatus.COMPLETED.value == "completed"
        assert QueryStatus.FAILED.value == "failed"
        assert QueryStatus.RETRYING.value == "retrying"


class TestQueryType:
    """Test QueryType enum."""

    def test_type_values(self):
        """Test that query types have correct values."""
        assert QueryType.CHAT.value == "chat"
        assert QueryType.COMPLETION.value == "completion"
        assert QueryType.CLASSIFICATION.value == "classification"
        assert QueryType.EXTRACTION.value == "extraction"
        assert QueryType.ANALYSIS.value == "analysis"


class TestLLMResponse:
    """Test LLMResponse dataclass."""

    def test_create_llm_response_minimal(self):
        """Test creating LLM response with minimal data."""
        response = LLMResponse(
            text="Test response",
            model="gpt-4",
            provider="openai",
            tokens_used=100,
            cost=0.01,
            processing_time=1.5,
            response_metadata={},
        )

        assert response.text == "Test response"
        assert response.model == "gpt-4"
        assert response.provider == "openai"
        assert response.tokens_used == 100
        assert response.cost == 0.01
        assert response.processing_time == 1.5
        assert "timestamp" in response.response_metadata

    def test_create_llm_response_with_metadata(self):
        """Test creating LLM response with existing metadata."""
        metadata = {"custom_field": "value", "timestamp": "2025-01-01T00:00:00"}

        response = LLMResponse(
            text="Test",
            model="gpt-4",
            provider="openai",
            tokens_used=50,
            cost=0.005,
            processing_time=0.5,
            response_metadata=metadata,
        )

        assert response.response_metadata["custom_field"] == "value"
        assert response.response_metadata["timestamp"] == "2025-01-01T00:00:00"

    def test_llm_response_adds_timestamp(self):
        """Test that __post_init__ adds timestamp if not present."""
        response = LLMResponse(
            text="Test",
            model="gpt-4",
            provider="openai",
            tokens_used=50,
            cost=0.005,
            processing_time=0.5,
            response_metadata={},
        )

        assert "timestamp" in response.response_metadata
        # Verify timestamp is recent (within last minute)
        timestamp_str = response.response_metadata["timestamp"]
        assert isinstance(timestamp_str, str)


class TestQueryResponse:
    """Test QueryResponse dataclass."""

    def test_create_query_response_minimal(self):
        """Test creating query response with required fields."""
        created_at = datetime.now(UTC)

        response = QueryResponse(
            query_id="query_123",
            user_id="user_456",
            response="Test response",
            status=QueryStatus.COMPLETED,
            model_used="gpt-4",
            provider_used="openai",
            tokens_used=100,
            cost=0.01,
            processing_time=2.0,
            created_at=created_at,
        )

        assert response.query_id == "query_123"
        assert response.user_id == "user_456"
        assert response.response == "Test response"
        assert response.status == QueryStatus.COMPLETED
        assert response.completed_at is None
        assert response.error_message is None
        assert response.retry_count == 0
        assert response.query_metadata == {}

    def test_create_query_response_full(self):
        """Test creating query response with all fields."""
        created_at = datetime.now(UTC)
        completed_at = created_at + timedelta(seconds=2)
        metadata = {"key": "value"}

        response = QueryResponse(
            query_id="query_123",
            user_id="user_456",
            response="Test response",
            status=QueryStatus.COMPLETED,
            model_used="gpt-4",
            provider_used="openai",
            tokens_used=100,
            cost=0.01,
            processing_time=2.0,
            created_at=created_at,
            completed_at=completed_at,
            error_message="No error",
            retry_count=2,
            query_metadata=metadata,
        )

        assert response.completed_at == completed_at
        assert response.error_message == "No error"
        assert response.retry_count == 2
        assert response.query_metadata == metadata

    def test_query_response_initializes_metadata(self):
        """Test that __post_init__ initializes query_metadata if None."""
        response = QueryResponse(
            query_id="query_123",
            user_id="user_456",
            response="Test",
            status=QueryStatus.PENDING,
            model_used="gpt-4",
            provider_used="openai",
            tokens_used=0,
            cost=0.0,
            processing_time=0.0,
            created_at=datetime.now(UTC),
            query_metadata=None,
        )

        assert response.query_metadata == {}


class TestQueryRequest:
    """Test QueryRequest Pydantic model."""

    def test_create_query_request_minimal(self):
        """Test creating query request with minimal required fields."""
        request = QueryRequest(
            prompt="What is Python?",
            user_id="user_123",
        )

        assert request.prompt == "What is Python?"
        assert request.user_id == "user_123"
        assert request.query_type == QueryType.CHAT
        assert request.model is None
        assert request.preferred_provider == "openai"
        assert request.allow_fallback is True
        assert request.context == {}

    def test_create_query_request_full(self):
        """Test creating query request with all fields."""
        context = {"source": "web"}

        request = QueryRequest(
            prompt="Explain AI",
            user_id="user_456",
            query_type=QueryType.ANALYSIS,
            model="gpt-4",
            max_tokens=500,
            temperature=0.7,
            system_prompt="You are a helpful assistant",
            preferred_provider="anthropic",
            allow_fallback=False,
            timeout=60.0,
            conversation_id="conv_789",
            context=context,
        )

        assert request.query_type == QueryType.ANALYSIS
        assert request.model == "gpt-4"
        assert request.max_tokens == 500
        assert request.temperature == 0.7
        assert request.system_prompt == "You are a helpful assistant"
        assert request.preferred_provider == "anthropic"
        assert request.allow_fallback is False
        assert request.timeout == 60.0
        assert request.conversation_id == "conv_789"
        assert request.context == context

    def test_query_request_validation_empty_prompt(self):
        """Test that empty prompt is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(prompt="", user_id="user_123")

        assert "prompt" in str(exc_info.value)

    def test_query_request_validation_long_prompt(self):
        """Test that overly long prompt is rejected."""
        long_prompt = "x" * 10001  # Exceeds max_length of 10000

        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(prompt=long_prompt, user_id="user_123")

        assert "prompt" in str(exc_info.value)

    def test_query_request_validation_max_tokens(self):
        """Test max_tokens validation."""
        with pytest.raises(ValidationError):
            QueryRequest(prompt="Test", user_id="user_123", max_tokens=5000)  # Exceeds le=4000

    def test_query_request_validation_temperature(self):
        """Test temperature validation."""
        with pytest.raises(ValidationError):
            QueryRequest(prompt="Test", user_id="user_123", temperature=3.0)  # Exceeds le=2.0

    def test_query_request_validation_timeout(self):
        """Test timeout validation."""
        with pytest.raises(ValidationError):
            QueryRequest(prompt="Test", user_id="user_123", timeout=400.0)  # Exceeds le=300.0


class TestQueryResponseSchema:
    """Test QueryResponseSchema Pydantic model."""

    def test_create_response_schema_minimal(self):
        """Test creating response schema with minimal fields."""
        created_at = datetime.now(UTC)

        schema = QueryResponseSchema(
            query_id="query_123",
            response="Test response",
            status=QueryStatus.COMPLETED,
            model_used="gpt-4",
            provider_used="openai",
            tokens_used=100,
            cost=0.01,
            processing_time=2.0,
            created_at=created_at,
        )

        assert schema.query_id == "query_123"
        assert schema.response == "Test response"
        assert schema.status == QueryStatus.COMPLETED
        assert schema.completed_at is None
        assert schema.retry_count == 0
        assert schema.was_fallback is False

    def test_create_response_schema_full(self):
        """Test creating response schema with all fields."""
        created_at = datetime.now(UTC)
        completed_at = created_at + timedelta(seconds=2)

        schema = QueryResponseSchema(
            query_id="query_123",
            response="Test response",
            status=QueryStatus.COMPLETED,
            model_used="gpt-4",
            provider_used="openai",
            tokens_used=100,
            cost=0.01,
            processing_time=2.0,
            created_at=created_at,
            completed_at=completed_at,
            retry_count=3,
            was_fallback=True,
        )

        assert schema.completed_at == completed_at
        assert schema.retry_count == 3
        assert schema.was_fallback is True


class TestQueryErrorResponse:
    """Test QueryErrorResponse Pydantic model."""

    def test_create_error_response_minimal(self):
        """Test creating error response with minimal fields."""
        error = QueryErrorResponse(
            query_id="query_123",
            error_type="ValueError",
            error_message="Invalid input",
            user_message="Please check your input",
        )

        assert error.query_id == "query_123"
        assert error.error_type == "ValueError"
        assert error.error_message == "Invalid input"
        assert error.user_message == "Please check your input"
        assert error.status == QueryStatus.FAILED
        assert error.retry_count == 0
        assert error.can_retry is False
        assert error.estimated_retry_delay is None
        assert error.processing_time == 0.0

    def test_create_error_response_full(self):
        """Test creating error response with all fields."""
        error = QueryErrorResponse(
            query_id="query_123",
            error_type="TimeoutError",
            error_message="Request timed out",
            user_message="Request took too long",
            status=QueryStatus.RETRYING,
            retry_count=2,
            can_retry=True,
            estimated_retry_delay=30.0,
            provider_attempted="openai",
            model_attempted="gpt-4",
            processing_time=5.0,
        )

        assert error.status == QueryStatus.RETRYING
        assert error.retry_count == 2
        assert error.can_retry is True
        assert error.estimated_retry_delay == 30.0
        assert error.provider_attempted == "openai"
        assert error.model_attempted == "gpt-4"
        assert error.processing_time == 5.0

    def test_error_response_timestamp_default(self):
        """Test that timestamp has a default value."""
        error = QueryErrorResponse(
            query_id="query_123",
            error_type="Error",
            error_message="Test",
            user_message="Test",
        )

        assert error.timestamp is not None
        assert isinstance(error.timestamp, datetime)


class TestQueryMetrics:
    """Test QueryMetrics Pydantic model."""

    def test_create_metrics_minimal(self):
        """Test creating metrics with minimal data."""
        start_time = datetime.now(UTC)
        end_time = start_time + timedelta(hours=1)

        metrics = QueryMetrics(
            start_time=start_time,
            end_time=end_time,
        )

        assert metrics.total_queries == 0
        assert metrics.successful_queries == 0
        assert metrics.failed_queries == 0
        assert metrics.retry_attempts == 0
        assert metrics.average_processing_time == 0.0
        assert metrics.total_cost == 0.0
        assert metrics.total_tokens == 0
        assert metrics.provider_stats == {}

    def test_create_metrics_full(self):
        """Test creating metrics with full data."""
        start_time = datetime.now(UTC)
        end_time = start_time + timedelta(hours=1)
        provider_stats = {
            "openai": {"queries": 10, "cost": 0.50},
            "anthropic": {"queries": 5, "cost": 0.25},
        }

        metrics = QueryMetrics(
            total_queries=15,
            successful_queries=14,
            failed_queries=1,
            retry_attempts=3,
            average_processing_time=2.5,
            total_cost=0.75,
            total_tokens=1500,
            provider_stats=provider_stats,
            start_time=start_time,
            end_time=end_time,
        )

        assert metrics.total_queries == 15
        assert metrics.successful_queries == 14
        assert metrics.failed_queries == 1
        assert metrics.retry_attempts == 3
        assert metrics.provider_stats == provider_stats

    def test_metrics_success_rate(self):
        """Test success rate calculation."""
        start_time = datetime.now(UTC)
        end_time = start_time + timedelta(hours=1)

        metrics = QueryMetrics(
            total_queries=100,
            successful_queries=95,
            failed_queries=5,
            start_time=start_time,
            end_time=end_time,
        )

        assert metrics.success_rate == 95.0

    def test_metrics_success_rate_zero_queries(self):
        """Test success rate with zero queries."""
        start_time = datetime.now(UTC)
        end_time = start_time + timedelta(hours=1)

        metrics = QueryMetrics(
            start_time=start_time,
            end_time=end_time,
        )

        assert metrics.success_rate == 0.0

    def test_metrics_failure_rate(self):
        """Test failure rate calculation."""
        start_time = datetime.now(UTC)
        end_time = start_time + timedelta(hours=1)

        metrics = QueryMetrics(
            total_queries=100,
            successful_queries=92,
            failed_queries=8,
            start_time=start_time,
            end_time=end_time,
        )

        assert metrics.failure_rate == 8.0

    def test_metrics_average_cost_per_query(self):
        """Test average cost per query calculation."""
        start_time = datetime.now(UTC)
        end_time = start_time + timedelta(hours=1)

        metrics = QueryMetrics(
            total_queries=50,
            total_cost=5.0,
            start_time=start_time,
            end_time=end_time,
        )

        assert metrics.average_cost_per_query == 0.1

    def test_metrics_average_cost_zero_queries(self):
        """Test average cost with zero queries."""
        start_time = datetime.now(UTC)
        end_time = start_time + timedelta(hours=1)

        metrics = QueryMetrics(
            total_queries=0,
            total_cost=0.0,
            start_time=start_time,
            end_time=end_time,
        )

        assert metrics.average_cost_per_query == 0.0
