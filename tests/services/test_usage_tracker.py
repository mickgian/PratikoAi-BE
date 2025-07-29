"""Tests for usage tracking functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.services.usage_tracker import UsageTracker, usage_tracker, UsageMetrics, CostBreakdown
from app.core.llm.base import LLMResponse
from app.models.usage import UsageEvent, UsageQuota, UsageType, CostCategory


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return LLMResponse(
        content="Test response",
        model="gpt-4o-mini",
        provider="openai",
        tokens_used={"input": 100, "output": 50},
        cost_estimate=0.002,
        finish_reason="stop",
        tool_calls=None
    )


class TestUsageTracker:
    """Test cases for the usage tracker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = UsageTracker()

    @pytest.mark.asyncio
    @patch('app.services.usage_tracker.database_service')
    async def test_track_llm_usage(self, mock_db, mock_llm_response):
        """Test tracking LLM usage."""
        mock_db.get_db.return_value.__aenter__.return_value = AsyncMock()
        
        user_id = "test_user_123"
        session_id = "test_session_456"
        
        usage_event = await self.tracker.track_llm_usage(
            user_id=user_id,
            session_id=session_id,
            provider="openai",
            model="gpt-4o-mini",
            llm_response=mock_llm_response,
            response_time_ms=1500,
            cache_hit=False
        )
        
        assert usage_event.user_id == user_id
        assert usage_event.session_id == session_id
        assert usage_event.provider == "openai"
        assert usage_event.model == "gpt-4o-mini"
        assert usage_event.input_tokens == 100
        assert usage_event.output_tokens == 50
        assert usage_event.total_tokens == 150
        assert usage_event.cost_eur == 0.002
        assert usage_event.response_time_ms == 1500
        assert usage_event.cache_hit is False

    @pytest.mark.asyncio
    @patch('app.services.usage_tracker.database_service')
    async def test_track_cache_hit(self, mock_db, mock_llm_response):
        """Test tracking cache hits (zero cost)."""
        mock_db.get_db.return_value.__aenter__.return_value = AsyncMock()
        
        usage_event = await self.tracker.track_llm_usage(
            user_id="test_user",
            session_id="test_session",
            provider="openai",
            model="gpt-4o-mini",
            llm_response=mock_llm_response,
            response_time_ms=50,
            cache_hit=True
        )
        
        assert usage_event.cache_hit is True
        assert usage_event.cost_eur == 0.0  # No cost for cache hits
        assert usage_event.total_tokens == 0  # No tokens consumed for cache hits

    @pytest.mark.asyncio
    @patch('app.services.usage_tracker.database_service')
    async def test_track_api_request(self, mock_db):
        """Test tracking general API requests."""
        mock_db.get_db.return_value.__aenter__.return_value = AsyncMock()
        
        usage_event = await self.tracker.track_api_request(
            user_id="test_user",
            session_id="test_session",
            endpoint="/api/v1/messages",
            method="GET",
            response_time_ms=200,
            request_size=1024,
            response_size=2048
        )
        
        assert usage_event.event_type == UsageType.API_REQUEST
        assert usage_event.response_time_ms == 200
        assert usage_event.request_size == 1024
        assert usage_event.response_size == 2048
        assert usage_event.cost_category == CostCategory.COMPUTE

    @pytest.mark.asyncio
    @patch('app.services.usage_tracker.database_service')
    async def test_get_user_quota_new_user(self, mock_db):
        """Test getting quota for new user (creates default)."""
        mock_db_session = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value = mock_db_session
        
        # Mock no existing quota
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        quota = await self.tracker.get_user_quota("new_user")
        
        assert quota.user_id == "new_user"
        assert quota.daily_cost_limit_eur == 0.10
        assert quota.monthly_cost_limit_eur == 2.00
        assert quota.is_active is True

    @pytest.mark.asyncio 
    @patch('app.services.usage_tracker.database_service')
    async def test_check_quota_limits_within_limits(self, mock_db):
        """Test quota check when user is within limits."""
        mock_db_session = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value = mock_db_session
        
        # Mock existing quota within limits
        quota = UsageQuota(
            user_id="test_user",
            daily_requests_limit=100,
            current_daily_requests=50,
            daily_cost_limit_eur=0.10,
            current_daily_cost_eur=0.05,
            monthly_cost_limit_eur=2.00,
            current_monthly_cost_eur=1.00,
            is_active=True
        )
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = quota
        
        is_allowed, reason = await self.tracker.check_quota_limits("test_user")
        
        assert is_allowed is True
        assert reason is None

    @pytest.mark.asyncio
    @patch('app.services.usage_tracker.database_service')
    async def test_check_quota_limits_exceeded(self, mock_db):
        """Test quota check when limits are exceeded."""
        mock_db_session = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value = mock_db_session
        
        # Mock quota with exceeded daily cost limit
        quota = UsageQuota(
            user_id="test_user",
            daily_cost_limit_eur=0.10,
            current_daily_cost_eur=0.15,  # Exceeded
            is_active=True
        )
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = quota
        
        is_allowed, reason = await self.tracker.check_quota_limits("test_user")
        
        assert is_allowed is False
        assert "Daily cost limit exceeded" in reason

    @pytest.mark.asyncio
    @patch('app.services.usage_tracker.database_service')
    async def test_get_user_metrics(self, mock_db):
        """Test getting user metrics."""
        mock_db_session = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value = mock_db_session
        
        # Mock usage events
        mock_events = [
            UsageEvent(
                user_id="test_user",
                event_type=UsageType.LLM_QUERY,
                total_tokens=100,
                cost_eur=0.002,
                response_time_ms=1000,
                cache_hit=False,
                error_occurred=False
            ),
            UsageEvent(
                user_id="test_user", 
                event_type=UsageType.LLM_QUERY,
                total_tokens=50,
                cost_eur=0.0,  # Cache hit
                response_time_ms=50,
                cache_hit=True,
                error_occurred=False
            )
        ]
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = mock_events
        
        metrics = await self.tracker.get_user_metrics("test_user")
        
        assert metrics.total_requests == 2
        assert metrics.llm_requests == 2
        assert metrics.cache_hits == 1
        assert metrics.cache_misses == 1
        assert metrics.cache_hit_rate == 0.5
        assert metrics.total_tokens == 150
        assert metrics.total_cost_eur == 0.002
        assert metrics.error_rate == 0.0

    @pytest.mark.asyncio
    @patch('app.services.usage_tracker.database_service')
    async def test_get_cost_breakdown(self, mock_db):
        """Test getting cost breakdown by category."""
        mock_db_session = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value = mock_db_session
        
        # Mock cost data by category
        mock_db_session.execute.return_value.all.return_value = [
            (CostCategory.LLM_INFERENCE, 1.50),
            (CostCategory.STORAGE, 0.30),
            (CostCategory.COMPUTE, 0.20)
        ]
        
        breakdown = await self.tracker.get_cost_breakdown("test_user")
        
        assert breakdown.llm_inference == 1.50
        assert breakdown.storage == 0.30
        assert breakdown.compute == 0.20
        assert breakdown.total == 2.00

    @pytest.mark.asyncio
    @patch('app.services.usage_tracker.database_service')
    async def test_generate_optimization_suggestions(self, mock_db):
        """Test generating optimization suggestions."""
        mock_db_session = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value = mock_db_session
        
        # Mock user metrics that warrant suggestions
        with patch.object(self.tracker, 'get_user_metrics') as mock_get_metrics:
            mock_get_metrics.return_value = UsageMetrics(
                total_requests=100,
                llm_requests=100,
                cache_hit_rate=0.3,  # Low cache hit rate
                total_cost_eur=1.5,  # High cost
            )
            
            await self.tracker.generate_optimization_suggestions("test_user")
            
            # Should have added suggestions to database
            assert mock_db_session.add.call_count >= 1  # At least one suggestion

    @pytest.mark.asyncio
    @patch('app.services.usage_tracker.database_service')
    async def test_get_system_metrics(self, mock_db):
        """Test getting system-wide metrics."""
        mock_db_session = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value = mock_db_session
        
        # Mock system data
        mock_db_session.execute.return_value.scalar.side_effect = [
            10,    # Total users
            25.0,  # Total cost
        ]
        
        # Mock model usage data
        mock_db_session.execute.return_value.all.return_value = [
            ("gpt-4o-mini", 150, 15.0),
            ("claude-3-haiku", 50, 10.0)
        ]
        
        metrics = await self.tracker.get_system_metrics()
        
        assert metrics["total_users"] == 10
        assert metrics["total_cost_eur"] == 25.0
        assert metrics["avg_cost_per_user_eur"] == 2.5
        assert len(metrics["model_usage"]) == 2

    def test_alert_thresholds(self):
        """Test alert threshold configuration."""
        assert "daily_cost" in self.tracker._alert_thresholds
        assert "monthly_cost" in self.tracker._alert_thresholds
        assert self.tracker._alert_thresholds["monthly_cost"] == 2.00

    @pytest.mark.asyncio
    @patch('app.services.usage_tracker.database_service')
    async def test_cost_alert_creation(self, mock_db):
        """Test cost alert creation when thresholds exceeded."""
        mock_db_session = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value = mock_db_session
        
        # Mock no existing alert
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        await self.tracker._create_alert(
            user_id="test_user",
            alert_type="daily_threshold",
            threshold_eur=0.10,
            current_cost_eur=0.15
        )
        
        # Should have added alert to database
        mock_db_session.add.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.usage_tracker.database_service')
    async def test_update_user_quota(self, mock_db):
        """Test updating user quota with new usage."""
        mock_db_session = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value = mock_db_session
        
        # Mock existing quota
        quota = UsageQuota(
            user_id="test_user",
            current_daily_cost_eur=0.05,
            current_monthly_cost_eur=1.00,
            current_daily_tokens=1000,
            current_monthly_tokens=50000,
            current_daily_requests=10
        )
        
        with patch.object(self.tracker, 'get_user_quota', return_value=quota):
            await self.tracker._update_user_quota(
                user_id="test_user",
                cost_eur=0.002,
                tokens=100
            )
            
            assert quota.current_daily_cost_eur == 0.052
            assert quota.current_monthly_cost_eur == 1.002
            assert quota.current_daily_tokens == 1100
            assert quota.current_monthly_tokens == 50100
            assert quota.current_daily_requests == 11


class TestGlobalUsageTrackerInstance:
    """Test the global usage tracker instance."""

    def test_global_instance_available(self):
        """Test that global usage tracker instance is available."""
        assert usage_tracker is not None
        assert isinstance(usage_tracker, UsageTracker)

    def test_alert_thresholds_configured(self):
        """Test that alert thresholds are properly configured."""
        assert usage_tracker._alert_thresholds["monthly_cost"] == 2.00
        assert usage_tracker._alert_thresholds["daily_cost"] == 0.10


class TestUsageMetrics:
    """Test the UsageMetrics dataclass."""

    def test_default_values(self):
        """Test default values for usage metrics."""
        metrics = UsageMetrics()
        assert metrics.total_requests == 0
        assert metrics.total_cost_eur == 0.0
        assert metrics.cache_hit_rate == 0.0

    def test_custom_values(self):
        """Test setting custom values."""
        metrics = UsageMetrics(
            total_requests=100,
            total_cost_eur=1.50,
            cache_hit_rate=0.75
        )
        assert metrics.total_requests == 100
        assert metrics.total_cost_eur == 1.50
        assert metrics.cache_hit_rate == 0.75


class TestCostBreakdown:
    """Test the CostBreakdown dataclass."""

    def test_to_dict_conversion(self):
        """Test converting cost breakdown to dictionary."""
        breakdown = CostBreakdown(
            llm_inference=1.50,
            storage=0.30,
            compute=0.20,
            total=2.00
        )
        
        result = breakdown.to_dict()
        
        assert result["llm_inference"] == 1.50
        assert result["storage"] == 0.30
        assert result["compute"] == 0.20
        assert result["total"] == 2.00

    def test_default_values(self):
        """Test default values for cost breakdown."""
        breakdown = CostBreakdown()
        assert breakdown.total == 0.0
        assert breakdown.llm_inference == 0.0