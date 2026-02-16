"""Tests for RollingWindowService (DEV-257).

TDD: Tests written FIRST before implementation.
Tests rolling cost windows (5h, 7d) with Redis + PostgreSQL dual-write.
"""

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.billing import BillingPlan, UsageWindow, UserCredit, WindowType
from app.services.rolling_window_service import (
    RollingWindowService,
    WindowCheckResult,
    WindowUsageInfo,
)


@pytest.fixture
def service():
    return RollingWindowService()


@pytest.fixture
def base_plan():
    return BillingPlan(
        id=1,
        slug="base",
        name="Base",
        price_eur_monthly=25.0,
        monthly_cost_limit_eur=10.0,
        window_5h_cost_limit_eur=2.50,
        window_7d_cost_limit_eur=7.50,
        credit_markup_factor=1.50,
    )


@pytest.fixture
def pro_plan():
    return BillingPlan(
        id=2,
        slug="pro",
        name="Pro",
        price_eur_monthly=75.0,
        monthly_cost_limit_eur=30.0,
        window_5h_cost_limit_eur=5.00,
        window_7d_cost_limit_eur=22.50,
        credit_markup_factor=1.30,
    )


@pytest.fixture
def premium_plan():
    return BillingPlan(
        id=3,
        slug="premium",
        name="Premium",
        price_eur_monthly=150.0,
        monthly_cost_limit_eur=60.0,
        window_5h_cost_limit_eur=10.00,
        window_7d_cost_limit_eur=45.00,
        credit_markup_factor=1.20,
    )


class TestCheckLimits:
    """Tests for check_limits method."""

    @pytest.mark.asyncio
    async def test_within_5h_allows(self, service, base_plan):
        """User within 5h limit should be allowed."""
        with (
            patch.object(service, "_get_plan", return_value=base_plan),
            patch.object(service, "_get_window_cost", return_value=0.20),
            patch.object(service, "_get_credit_info", return_value=(False, 0.0)),
        ):
            result = await service.check_limits(user_id=1, plan_slug="base")
            assert result.allowed is True
            assert result.reason is None

    @pytest.mark.asyncio
    async def test_exceeds_5h_blocks(self, service, base_plan):
        """User exceeding 5h limit should be blocked with reset_at populated."""
        fake_reset = datetime(2025, 6, 15, 16, 7, 0, tzinfo=UTC)
        with (
            patch.object(service, "_get_plan", return_value=base_plan),
            patch.object(
                service,
                "_get_window_cost",
                side_effect=lambda uid, wt: 2.50 if wt == WindowType.FIVE_HOUR else 3.00,
            ),
            patch.object(service, "_get_credit_info", return_value=(False, 0.0)),
            patch.object(service, "get_reset_time", return_value=fake_reset),
        ):
            result = await service.check_limits(user_id=1, plan_slug="base")
            assert result.allowed is False
            assert result.window_type == "5h"
            assert result.current_cost_eur == 2.50
            assert result.limit_cost_eur == 2.50
            assert result.reset_at == fake_reset

    @pytest.mark.asyncio
    async def test_exceeds_7d_blocks_despite_5h_budget(self, service, base_plan):
        """User within 5h but exceeding 7d should be blocked with reset_at populated."""
        fake_reset = datetime(2025, 6, 20, 10, 0, 0, tzinfo=UTC)
        with (
            patch.object(service, "_get_plan", return_value=base_plan),
            patch.object(
                service,
                "_get_window_cost",
                side_effect=lambda uid, wt: 0.20 if wt == WindowType.FIVE_HOUR else 7.50,
            ),
            patch.object(service, "_get_credit_info", return_value=(False, 0.0)),
            patch.object(service, "get_reset_time", return_value=fake_reset),
        ):
            result = await service.check_limits(user_id=1, plan_slug="base")
            assert result.allowed is False
            assert result.window_type == "7d"
            assert result.current_cost_eur == 7.50
            assert result.reset_at == fake_reset

    @pytest.mark.asyncio
    async def test_with_credits_enabled_allows_overage(self, service, base_plan):
        """User over limit but with credits enabled + balance should be allowed."""
        with (
            patch.object(service, "_get_plan", return_value=base_plan),
            patch.object(
                service,
                "_get_window_cost",
                side_effect=lambda uid, wt: 2.60 if wt == WindowType.FIVE_HOUR else 3.00,
            ),
            patch.object(service, "_get_credit_info", return_value=(True, 10.0)),
        ):
            result = await service.check_limits(user_id=1, plan_slug="base")
            assert result.allowed is True
            assert result.credits_available is True
            assert result.credit_balance == 10.0

    @pytest.mark.asyncio
    async def test_exact_limit_blocks(self, service, base_plan):
        """Exact limit hit should block (>=)."""
        with (
            patch.object(service, "_get_plan", return_value=base_plan),
            patch.object(
                service,
                "_get_window_cost",
                side_effect=lambda uid, wt: 2.50 if wt == WindowType.FIVE_HOUR else 3.00,
            ),
            patch.object(service, "_get_credit_info", return_value=(False, 0.0)),
            patch.object(service, "get_reset_time", return_value=None),
        ):
            result = await service.check_limits(user_id=1, plan_slug="base")
            assert result.allowed is False

    @pytest.mark.asyncio
    async def test_no_plan_defaults_to_base(self, service, base_plan):
        """Unknown plan slug should fall back to base plan."""
        with (
            patch.object(service, "_get_plan", return_value=base_plan),
            patch.object(service, "_get_window_cost", return_value=0.10),
            patch.object(service, "_get_credit_info", return_value=(False, 0.0)),
        ):
            result = await service.check_limits(user_id=1, plan_slug="nonexistent")
            assert result.allowed is True


class TestRecordUsage:
    """Tests for record_usage method."""

    @pytest.mark.asyncio
    async def test_record_usage_writes_to_postgres(self, service):
        """record_usage should persist UsageWindow records."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.services.rolling_window_service.database_service") as mock_db_svc,
            patch.object(service, "_record_to_redis", return_value=None),
        ):
            mock_db_svc.get_db.return_value = mock_db
            await service.record_usage(user_id=1, cost_eur=0.05, usage_event_id=42)

            # Should have added 2 windows (5h and 7d)
            assert mock_db.add.call_count == 2
            added_windows = [call.args[0] for call in mock_db.add.call_args_list]
            window_types = {w.window_type for w in added_windows}
            assert window_types == {"5h", "7d"}
            for w in added_windows:
                assert w.cost_eur == 0.05
                assert w.user_id == 1
                assert w.usage_event_id == 42


class TestGetCurrentUsage:
    """Tests for get_current_usage method."""

    @pytest.mark.asyncio
    async def test_returns_window_totals(self, service):
        """get_current_usage should return both window totals."""
        with patch.object(
            service,
            "_get_window_cost",
            side_effect=lambda uid, wt: 0.30 if wt == WindowType.FIVE_HOUR else 1.50,
        ):
            info = await service.get_current_usage(user_id=1)
            assert isinstance(info, WindowUsageInfo)
            assert info.cost_5h_eur == 0.30
            assert info.cost_7d_eur == 1.50


class TestGetResetTime:
    """Tests for get_reset_time method."""

    @pytest.mark.asyncio
    async def test_get_reset_time_5h(self, service):
        """5h reset time should be ~5h from oldest entry in window."""
        now = datetime.utcnow()
        oldest = now - timedelta(hours=3)  # 3h ago
        with patch.object(service, "_get_oldest_in_window", return_value=oldest):
            reset_time = await service.get_reset_time(user_id=1, window_type=WindowType.FIVE_HOUR)
            assert reset_time is not None
            # oldest + 5h = 2h from now
            expected = oldest + timedelta(hours=5)
            assert abs((reset_time - expected).total_seconds()) < 2

    @pytest.mark.asyncio
    async def test_get_reset_time_7d(self, service):
        """7d reset time should be ~7d from oldest entry in window."""
        now = datetime.utcnow()
        oldest = now - timedelta(days=5)
        with patch.object(service, "_get_oldest_in_window", return_value=oldest):
            reset_time = await service.get_reset_time(user_id=1, window_type=WindowType.SEVEN_DAY)
            assert reset_time is not None
            expected = oldest + timedelta(days=7)
            assert abs((reset_time - expected).total_seconds()) < 2

    @pytest.mark.asyncio
    async def test_get_reset_time_empty_window(self, service):
        """Empty window should return None."""
        with patch.object(service, "_get_oldest_in_window", return_value=None):
            reset_time = await service.get_reset_time(user_id=1, window_type=WindowType.FIVE_HOUR)
            assert reset_time is None


class TestGetOldestInWindowRedis:
    """Tests for _get_oldest_in_window Redis fallback."""

    @pytest.mark.asyncio
    async def test_redis_returns_oldest_timestamp(self, service):
        """Should parse oldest entry timestamp from Redis sorted set."""
        now = datetime.now(tz=UTC)
        oldest_ts = (now - timedelta(hours=2)).timestamp()
        member = f"0.05:42:{oldest_ts}"

        mock_redis = AsyncMock()
        mock_redis.zrangebyscore = AsyncMock(return_value=[member.encode()])

        mock_cache = MagicMock()
        mock_cache._get_redis = AsyncMock(return_value=mock_redis)

        cutoff = now - timedelta(hours=5)
        with patch("app.services.cache.cache_service", mock_cache):
            result = await service._get_oldest_in_window_redis(
                user_id=1,
                window_type=WindowType.FIVE_HOUR,
                cutoff=cutoff,
            )

        assert result is not None
        assert abs(result.timestamp() - oldest_ts) < 1

    @pytest.mark.asyncio
    async def test_redis_returns_none_when_no_entries(self, service):
        """Should return None when Redis has no entries in window."""
        mock_redis = AsyncMock()
        mock_redis.zrangebyscore = AsyncMock(return_value=[])

        mock_cache = MagicMock()
        mock_cache._get_redis = AsyncMock(return_value=mock_redis)

        cutoff = datetime.now(tz=UTC) - timedelta(hours=5)
        with patch("app.services.cache.cache_service", mock_cache):
            result = await service._get_oldest_in_window_redis(
                user_id=1,
                window_type=WindowType.FIVE_HOUR,
                cutoff=cutoff,
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_redis_returns_none_when_unavailable(self, service):
        """Should return None when Redis client is unavailable."""
        mock_cache = MagicMock()
        mock_cache._get_redis = AsyncMock(return_value=None)

        cutoff = datetime.now(tz=UTC) - timedelta(hours=5)
        with patch("app.services.cache.cache_service", mock_cache):
            result = await service._get_oldest_in_window_redis(
                user_id=1,
                window_type=WindowType.FIVE_HOUR,
                cutoff=cutoff,
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_oldest_in_window_tries_redis_first(self, service):
        """_get_oldest_in_window should try Redis before PostgreSQL."""
        now = datetime.now(tz=UTC)
        redis_oldest = now - timedelta(hours=2)

        with patch.object(
            service,
            "_get_oldest_in_window_redis",
            return_value=redis_oldest,
        ):
            result = await service._get_oldest_in_window(
                user_id=1,
                window_type=WindowType.FIVE_HOUR,
            )

        assert result == redis_oldest

    @pytest.mark.asyncio
    async def test_oldest_in_window_falls_back_to_postgres(self, service):
        """Should fall back to PostgreSQL when Redis returns None.

        PostgreSQL TIMESTAMP WITHOUT TIME ZONE returns naive datetimes;
        the service normalizes them to UTC-aware.
        """
        pg_oldest = datetime.utcnow() - timedelta(hours=3)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = pg_oldest
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)

        with (
            patch.object(service, "_get_oldest_in_window_redis", return_value=None),
            patch("app.services.rolling_window_service.database_service") as mock_db_svc,
        ):
            mock_db_svc.get_db.return_value = mock_db
            result = await service._get_oldest_in_window(
                user_id=1,
                window_type=WindowType.FIVE_HOUR,
            )

        assert result == pg_oldest.replace(tzinfo=UTC)

    @pytest.mark.asyncio
    async def test_oldest_in_window_handles_redis_exception(self, service):
        """Should fall back to PostgreSQL when Redis raises an exception.

        PostgreSQL TIMESTAMP WITHOUT TIME ZONE returns naive datetimes;
        the service normalizes them to UTC-aware.
        """
        pg_oldest = datetime.utcnow() - timedelta(hours=1)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = pg_oldest
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)

        with (
            patch.object(
                service,
                "_get_oldest_in_window_redis",
                side_effect=Exception("Redis down"),
            ),
            patch("app.services.rolling_window_service.database_service") as mock_db_svc,
        ):
            mock_db_svc.get_db.return_value = mock_db
            result = await service._get_oldest_in_window(
                user_id=1,
                window_type=WindowType.FIVE_HOUR,
            )

        assert result == pg_oldest.replace(tzinfo=UTC)


class TestReplaceUsageForWindow:
    """Tests for replace_usage_for_window (admin simulator)."""

    @pytest.mark.asyncio
    async def test_replace_usage_sets_exact_cost(self, service):
        """Should delete existing rows and insert one with target cost."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=MagicMock(rowcount=3))

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.zadd = AsyncMock()
        mock_redis.expire = AsyncMock()

        mock_cache = MagicMock()
        mock_cache._get_redis = AsyncMock(return_value=mock_redis)

        with (
            patch("app.services.rolling_window_service.database_service") as mock_db_svc,
            patch("app.services.cache.cache_service", mock_cache),
        ):
            mock_db_svc.get_db.return_value = mock_db
            await service.replace_usage_for_window(
                user_id=1,
                window_type=WindowType.FIVE_HOUR,
                target_cost_eur=1.25,
            )

        # Should have executed DELETE then INSERT
        assert mock_db.execute.call_count >= 1
        assert mock_db.add.call_count == 1
        added_window = mock_db.add.call_args[0][0]
        assert added_window.cost_eur == 1.25
        assert added_window.window_type == WindowType.FIVE_HOUR
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_replace_usage_zero_clears_only(self, service):
        """Setting target_cost=0 should delete rows without inserting."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=MagicMock(rowcount=2))

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=1)

        mock_cache = MagicMock()
        mock_cache._get_redis = AsyncMock(return_value=mock_redis)

        with (
            patch("app.services.rolling_window_service.database_service") as mock_db_svc,
            patch("app.services.cache.cache_service", mock_cache),
        ):
            mock_db_svc.get_db.return_value = mock_db
            await service.replace_usage_for_window(
                user_id=1,
                window_type=WindowType.FIVE_HOUR,
                target_cost_eur=0.0,
            )

        # Should have executed DELETE but NOT add
        assert mock_db.execute.call_count >= 1
        assert mock_db.add.call_count == 0
        assert mock_db.commit.called


class TestClearUsage:
    """Tests for clear_usage (admin simulator)."""

    @pytest.mark.asyncio
    async def test_clear_usage_removes_all_records(self, service):
        """Should delete all UsageWindow rows and both Redis keys."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=2)

        mock_cache = MagicMock()
        mock_cache._get_redis = AsyncMock(return_value=mock_redis)

        with (
            patch("app.services.rolling_window_service.database_service") as mock_db_svc,
            patch("app.services.cache.cache_service", mock_cache),
        ):
            mock_db_svc.get_db.return_value = mock_db
            pg_deleted, redis_deleted = await service.clear_usage(user_id=1)

        assert pg_deleted == 5
        assert redis_deleted == 2

    @pytest.mark.asyncio
    async def test_clear_usage_idempotent_when_empty(self, service):
        """Clearing already-empty usage should return zeros."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=0)

        mock_cache = MagicMock()
        mock_cache._get_redis = AsyncMock(return_value=mock_redis)

        with (
            patch("app.services.rolling_window_service.database_service") as mock_db_svc,
            patch("app.services.cache.cache_service", mock_cache),
        ):
            mock_db_svc.get_db.return_value = mock_db
            pg_deleted, redis_deleted = await service.clear_usage(user_id=1)

        assert pg_deleted == 0
        assert redis_deleted == 0
