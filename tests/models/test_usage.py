"""Tests for usage tracking models."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models.usage import (
    CostAlert,
    CostCategory,
    CostOptimizationSuggestion,
    UsageEvent,
    UsageQuota,
    UsageType,
    UserUsageSummary,
)


class TestUsageType:
    """Test UsageType enum."""

    def test_usage_type_values(self):
        """Test that usage types have correct values."""
        assert UsageType.LLM_QUERY.value == "llm_query"
        assert UsageType.LLM_STREAM.value == "llm_stream"
        assert UsageType.CACHE_HIT.value == "cache_hit"
        assert UsageType.CACHE_MISS.value == "cache_miss"
        assert UsageType.API_REQUEST.value == "api_request"

    def test_usage_type_enum_members(self):
        """Test that all expected usage types exist."""
        expected_types = {"LLM_QUERY", "LLM_STREAM", "CACHE_HIT", "CACHE_MISS", "API_REQUEST"}
        actual_types = {member.name for member in UsageType}
        assert actual_types == expected_types


class TestCostCategory:
    """Test CostCategory enum."""

    def test_cost_category_values(self):
        """Test that cost categories have correct values."""
        assert CostCategory.LLM_INFERENCE.value == "llm_inference"
        assert CostCategory.STORAGE.value == "storage"
        assert CostCategory.COMPUTE.value == "compute"
        assert CostCategory.BANDWIDTH.value == "bandwidth"
        assert CostCategory.THIRD_PARTY.value == "third_party"

    def test_cost_category_enum_members(self):
        """Test that all expected cost categories exist."""
        expected_categories = {"LLM_INFERENCE", "STORAGE", "COMPUTE", "BANDWIDTH", "THIRD_PARTY"}
        actual_categories = {member.name for member in CostCategory}
        assert actual_categories == expected_categories


class TestUsageEvent:
    """Test UsageEvent model."""

    def test_create_usage_event_minimal(self):
        """Test creating usage event with minimal required fields."""
        event = UsageEvent(
            user_id="user_123",
            event_type=UsageType.LLM_QUERY,
        )

        assert event.user_id == "user_123"
        assert event.event_type == UsageType.LLM_QUERY
        assert event.session_id is None
        assert event.timestamp is not None
        assert event.error_occurred is False
        assert event.pii_detected is False

    def test_create_usage_event_full(self):
        """Test creating usage event with all fields."""
        timestamp = datetime.now(UTC)

        event = UsageEvent(
            user_id="user_123",
            session_id="session_456",
            event_type=UsageType.LLM_QUERY,
            timestamp=timestamp,
            provider="openai",
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_eur=0.01,
            cost_category=CostCategory.LLM_INFERENCE,
            response_time_ms=500,
            cache_hit=False,
            request_size=1024,
            response_size=2048,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            country_code="IT",
            error_occurred=False,
            error_type=None,
            pii_detected=True,
            pii_types='["email", "phone"]',
        )

        assert event.user_id == "user_123"
        assert event.session_id == "session_456"
        assert event.event_type == UsageType.LLM_QUERY
        assert event.timestamp == timestamp
        assert event.provider == "openai"
        assert event.model == "gpt-4"
        assert event.input_tokens == 100
        assert event.output_tokens == 50
        assert event.total_tokens == 150
        assert event.cost_eur == 0.01
        assert event.cost_category == CostCategory.LLM_INFERENCE
        assert event.response_time_ms == 500
        assert event.cache_hit is False
        assert event.request_size == 1024
        assert event.response_size == 2048
        assert event.ip_address == "192.168.1.1"
        assert event.user_agent == "Mozilla/5.0"
        assert event.country_code == "IT"
        assert event.error_occurred is False
        assert event.pii_detected is True
        assert event.pii_types == '["email", "phone"]'

    def test_usage_event_cache_hit(self):
        """Test usage event for cache hit."""
        event = UsageEvent(
            user_id="user_123",
            event_type=UsageType.CACHE_HIT,
            cache_hit=True,
            response_time_ms=10,
        )

        assert event.event_type == UsageType.CACHE_HIT
        assert event.cache_hit is True
        assert event.response_time_ms == 10

    def test_usage_event_with_error(self):
        """Test usage event with error."""
        event = UsageEvent(
            user_id="user_123",
            event_type=UsageType.LLM_QUERY,
            error_occurred=True,
            error_type="timeout",
        )

        assert event.error_occurred is True
        assert event.error_type == "timeout"


class TestUserUsageSummary:
    """Test UserUsageSummary model."""

    def test_create_summary_minimal(self):
        """Test creating user usage summary with minimal fields."""
        date = datetime.now(UTC)

        summary = UserUsageSummary(
            user_id="user_123",
            date=date,
        )

        assert summary.user_id == "user_123"
        assert summary.date == date
        assert summary.total_requests == 0
        assert summary.llm_requests == 0
        assert summary.cache_hits == 0
        assert summary.cache_misses == 0
        assert summary.total_tokens == 0
        assert summary.total_cost_eur == 0.0
        assert summary.cache_hit_rate == 0.0
        assert summary.error_rate == 0.0
        assert summary.pii_detections == 0
        assert summary.anonymization_rate == 0.0

    def test_create_summary_full(self):
        """Test creating user usage summary with all fields."""
        date = datetime.now(UTC)

        summary = UserUsageSummary(
            user_id="user_123",
            date=date,
            total_requests=100,
            llm_requests=80,
            cache_hits=60,
            cache_misses=40,
            total_input_tokens=5000,
            total_output_tokens=3000,
            total_tokens=8000,
            total_cost_eur=1.50,
            llm_cost_eur=1.20,
            avg_response_time_ms=250.5,
            cache_hit_rate=0.60,
            error_count=5,
            error_rate=0.05,
            model_usage='{"gpt-4": 50, "gpt-3.5": 30}',
            provider_usage='{"openai": 80}',
            pii_detections=10,
            anonymization_rate=0.10,
        )

        assert summary.total_requests == 100
        assert summary.llm_requests == 80
        assert summary.cache_hits == 60
        assert summary.cache_misses == 40
        assert summary.total_input_tokens == 5000
        assert summary.total_output_tokens == 3000
        assert summary.total_tokens == 8000
        assert summary.total_cost_eur == 1.50
        assert summary.llm_cost_eur == 1.20
        assert summary.avg_response_time_ms == 250.5
        assert summary.cache_hit_rate == 0.60
        assert summary.error_count == 5
        assert summary.error_rate == 0.05
        assert summary.pii_detections == 10
        assert summary.anonymization_rate == 0.10

    def test_summary_timestamps_auto_created(self):
        """Test that timestamps are automatically created."""
        date = datetime.now(UTC)
        summary = UserUsageSummary(user_id="user_123", date=date)

        assert summary.created_at is not None
        assert summary.updated_at is not None


class TestCostAlert:
    """Test CostAlert model."""

    def test_create_cost_alert_minimal(self):
        """Test creating cost alert with required fields."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(days=1)

        alert = CostAlert(
            alert_type="daily",
            threshold_eur=0.10,
            current_cost_eur=0.12,
            period_start=period_start,
            period_end=period_end,
        )

        assert alert.user_id is None  # System-wide alert
        assert alert.alert_type == "daily"
        assert alert.threshold_eur == 0.10
        assert alert.current_cost_eur == 0.12
        assert alert.period_start == period_start
        assert alert.period_end == period_end
        assert alert.notification_sent is False
        assert alert.acknowledged is False
        assert alert.acknowledged_at is None

    def test_create_cost_alert_user_specific(self):
        """Test creating user-specific cost alert."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(days=30)

        alert = CostAlert(
            user_id="user_123",
            alert_type="monthly",
            threshold_eur=2.00,
            current_cost_eur=2.15,
            period_start=period_start,
            period_end=period_end,
            notification_sent=True,
            notification_type="email",
            acknowledged=True,
        )

        assert alert.user_id == "user_123"
        assert alert.alert_type == "monthly"
        assert alert.current_cost_eur == 2.15
        assert alert.notification_sent is True
        assert alert.notification_type == "email"
        assert alert.acknowledged is True

    def test_cost_alert_with_extra_data(self):
        """Test cost alert with extra metadata."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(hours=1)

        alert = CostAlert(
            alert_type="threshold",
            threshold_eur=0.05,
            current_cost_eur=0.06,
            period_start=period_start,
            period_end=period_end,
            extra_data='{"spike_detected": true, "increase_percentage": 20}',
        )

        assert alert.extra_data is not None
        assert "spike_detected" in alert.extra_data


class TestUsageQuota:
    """Test UsageQuota model."""

    def test_create_usage_quota_defaults(self):
        """Test creating usage quota with default values."""
        quota = UsageQuota(user_id="user_123")

        assert quota.user_id == "user_123"
        assert quota.daily_requests_limit == 100
        assert quota.daily_cost_limit_eur == 0.10
        assert quota.monthly_cost_limit_eur == 2.00
        assert quota.daily_token_limit == 50000
        assert quota.monthly_token_limit == 1000000
        assert quota.current_daily_requests == 0
        assert quota.current_daily_cost_eur == 0.0
        assert quota.current_monthly_cost_eur == 0.0
        assert quota.current_daily_tokens == 0
        assert quota.current_monthly_tokens == 0
        assert quota.is_active is True
        assert quota.blocked_until is None
        assert quota.plan_type == "basic"

    def test_create_usage_quota_custom_limits(self):
        """Test creating usage quota with custom limits."""
        quota = UsageQuota(
            user_id="user_456",
            daily_requests_limit=500,
            daily_cost_limit_eur=0.50,
            monthly_cost_limit_eur=10.00,
            daily_token_limit=250000,
            monthly_token_limit=5000000,
            plan_type="premium",
        )

        assert quota.user_id == "user_456"
        assert quota.daily_requests_limit == 500
        assert quota.daily_cost_limit_eur == 0.50
        assert quota.monthly_cost_limit_eur == 10.00
        assert quota.daily_token_limit == 250000
        assert quota.monthly_token_limit == 5000000
        assert quota.plan_type == "premium"

    def test_usage_quota_with_current_usage(self):
        """Test usage quota with current usage tracking."""
        quota = UsageQuota(
            user_id="user_123",
            current_daily_requests=75,
            current_daily_cost_eur=0.08,
            current_monthly_cost_eur=1.50,
            current_daily_tokens=30000,
            current_monthly_tokens=600000,
        )

        assert quota.current_daily_requests == 75
        assert quota.current_daily_cost_eur == 0.08
        assert quota.current_monthly_cost_eur == 1.50
        assert quota.current_daily_tokens == 30000
        assert quota.current_monthly_tokens == 600000

    def test_usage_quota_blocked(self):
        """Test usage quota in blocked state."""
        blocked_until = datetime.now(UTC) + timedelta(hours=1)

        quota = UsageQuota(
            user_id="user_123",
            is_active=False,
            blocked_until=blocked_until,
        )

        assert quota.is_active is False
        assert quota.blocked_until == blocked_until

    def test_usage_quota_timestamps_auto_created(self):
        """Test that timestamps are automatically created."""
        quota = UsageQuota(user_id="user_123")

        assert quota.created_at is not None
        assert quota.updated_at is not None
        assert quota.daily_reset_at is not None
        assert quota.monthly_reset_at is not None


class TestCostOptimizationSuggestion:
    """Test CostOptimizationSuggestion model."""

    def test_create_suggestion_minimal(self):
        """Test creating cost optimization suggestion with required fields."""
        suggestion = CostOptimizationSuggestion(
            suggestion_type="model_switch",
            title="Switch to GPT-3.5 for simple queries",
            description="Use GPT-3.5 instead of GPT-4 for straightforward questions",
            estimated_savings_eur=0.50,
            estimated_savings_percentage=25.0,
            confidence_score=0.85,
            implementation_effort="low",
        )

        assert suggestion.suggestion_type == "model_switch"
        assert suggestion.title == "Switch to GPT-3.5 for simple queries"
        assert suggestion.estimated_savings_eur == 0.50
        assert suggestion.estimated_savings_percentage == 25.0
        assert suggestion.confidence_score == 0.85
        assert suggestion.implementation_effort == "low"
        assert suggestion.auto_implementable is False
        assert suggestion.status == "pending"
        assert suggestion.actual_savings_eur is None
        assert suggestion.effectiveness_score is None

    def test_create_suggestion_user_specific(self):
        """Test creating user-specific optimization suggestion."""
        suggestion = CostOptimizationSuggestion(
            user_id="user_123",
            suggestion_type="caching",
            title="Enable aggressive caching",
            description="Cache responses for repetitive queries",
            estimated_savings_eur=0.30,
            estimated_savings_percentage=15.0,
            confidence_score=0.92,
            implementation_effort="medium",
            auto_implementable=True,
        )

        assert suggestion.user_id == "user_123"
        assert suggestion.suggestion_type == "caching"
        assert suggestion.auto_implementable is True

    def test_suggestion_implemented(self):
        """Test implemented suggestion with results."""
        implemented_at = datetime.now(UTC)

        suggestion = CostOptimizationSuggestion(
            suggestion_type="model_switch",
            title="Optimize model selection",
            description="Use smaller models when possible",
            estimated_savings_eur=0.60,
            estimated_savings_percentage=30.0,
            confidence_score=0.88,
            implementation_effort="low",
            status="implemented",
            implemented_at=implemented_at,
            actual_savings_eur=0.55,
            effectiveness_score=0.92,
        )

        assert suggestion.status == "implemented"
        assert suggestion.implemented_at == implemented_at
        assert suggestion.actual_savings_eur == 0.55
        assert suggestion.effectiveness_score == 0.92

    def test_suggestion_with_extra_data(self):
        """Test suggestion with additional metadata."""
        suggestion = CostOptimizationSuggestion(
            suggestion_type="batch_processing",
            title="Batch similar queries",
            description="Process similar queries together",
            estimated_savings_eur=0.40,
            estimated_savings_percentage=20.0,
            confidence_score=0.78,
            implementation_effort="high",
            extra_data='{"analysis_period_days": 30, "sample_size": 1000}',
        )

        assert suggestion.extra_data is not None
        assert "analysis_period_days" in suggestion.extra_data

    def test_suggestion_statuses(self):
        """Test different suggestion statuses."""
        pending = CostOptimizationSuggestion(
            suggestion_type="test",
            title="Test",
            description="Test",
            estimated_savings_eur=0.10,
            estimated_savings_percentage=5.0,
            confidence_score=0.70,
            implementation_effort="low",
            status="pending",
        )

        accepted = CostOptimizationSuggestion(
            suggestion_type="test",
            title="Test",
            description="Test",
            estimated_savings_eur=0.10,
            estimated_savings_percentage=5.0,
            confidence_score=0.70,
            implementation_effort="low",
            status="accepted",
        )

        rejected = CostOptimizationSuggestion(
            suggestion_type="test",
            title="Test",
            description="Test",
            estimated_savings_eur=0.10,
            estimated_savings_percentage=5.0,
            confidence_score=0.70,
            implementation_effort="low",
            status="rejected",
        )

        assert pending.status == "pending"
        assert accepted.status == "accepted"
        assert rejected.status == "rejected"
