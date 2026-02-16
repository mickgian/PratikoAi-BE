"""Rolling window service for usage-based billing (DEV-257).

Tracks user costs in 5h and 7d rolling windows using Redis sorted sets
for real-time checks with PostgreSQL as durable fallback.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone

from sqlalchemy import and_, delete, func, select

from app.core.config import settings
from app.core.logging import logger
from app.models.billing import BillingPlan, UsageWindow, UserCredit, WindowType
from app.services.database import database_service

# Window durations
WINDOW_DURATIONS = {
    WindowType.FIVE_HOUR: timedelta(hours=5),
    WindowType.SEVEN_DAY: timedelta(days=7),
}


@dataclass
class WindowCheckResult:
    """Result of a rolling window limit check."""

    allowed: bool
    reason: str | None = None
    window_type: str | None = None
    current_cost_eur: float = 0.0
    limit_cost_eur: float = 0.0
    reset_at: datetime | None = None
    credits_available: bool = False
    credit_balance: float = 0.0


@dataclass
class WindowUsageInfo:
    """Current usage across both windows."""

    cost_5h_eur: float = 0.0
    cost_7d_eur: float = 0.0


class RollingWindowService:
    """Manages rolling cost windows for usage-based billing."""

    async def check_limits(self, user_id: int, plan_slug: str) -> WindowCheckResult:
        """Check if user is within rolling window limits.

        Args:
            user_id: User ID
            plan_slug: Billing plan slug (base/pro/premium)

        Returns:
            WindowCheckResult with allowed status and details
        """
        plan = await self._get_plan(plan_slug)

        # Check 5h window
        cost_5h = await self._get_window_cost(user_id, WindowType.FIVE_HOUR)
        if cost_5h >= plan.window_5h_cost_limit_eur:
            credits_enabled, credit_balance = await self._get_credit_info(user_id)
            if credits_enabled and credit_balance > 0:
                return WindowCheckResult(
                    allowed=True,
                    window_type=WindowType.FIVE_HOUR,
                    current_cost_eur=cost_5h,
                    limit_cost_eur=plan.window_5h_cost_limit_eur,
                    credits_available=True,
                    credit_balance=credit_balance,
                )
            reset_at = await self.get_reset_time(user_id, WindowType.FIVE_HOUR)
            return WindowCheckResult(
                allowed=False,
                reason="Limite finestra 5h raggiunto",
                window_type=WindowType.FIVE_HOUR,
                current_cost_eur=cost_5h,
                limit_cost_eur=plan.window_5h_cost_limit_eur,
                reset_at=reset_at,
                credits_available=credits_enabled,
                credit_balance=credit_balance,
            )

        # Check 7d window
        cost_7d = await self._get_window_cost(user_id, WindowType.SEVEN_DAY)
        if cost_7d >= plan.window_7d_cost_limit_eur:
            credits_enabled, credit_balance = await self._get_credit_info(user_id)
            if credits_enabled and credit_balance > 0:
                return WindowCheckResult(
                    allowed=True,
                    window_type=WindowType.SEVEN_DAY,
                    current_cost_eur=cost_7d,
                    limit_cost_eur=plan.window_7d_cost_limit_eur,
                    credits_available=True,
                    credit_balance=credit_balance,
                )
            reset_at = await self.get_reset_time(user_id, WindowType.SEVEN_DAY)
            return WindowCheckResult(
                allowed=False,
                reason="Limite finestra 7 giorni raggiunto",
                window_type=WindowType.SEVEN_DAY,
                current_cost_eur=cost_7d,
                limit_cost_eur=plan.window_7d_cost_limit_eur,
                reset_at=reset_at,
                credits_available=credits_enabled,
                credit_balance=credit_balance,
            )

        return WindowCheckResult(allowed=True)

    async def record_usage(self, user_id: int, cost_eur: float, usage_event_id: int | None = None) -> None:
        """Record usage in both windows (Redis + PostgreSQL).

        Args:
            user_id: User ID
            cost_eur: Cost in EUR
            usage_event_id: Optional link to UsageEvent
        """
        now = datetime.now(UTC)

        # Write to PostgreSQL (durable store)
        async with database_service.get_db() as db:
            for window_type in [WindowType.FIVE_HOUR, WindowType.SEVEN_DAY]:
                window = UsageWindow(
                    user_id=user_id,
                    window_type=window_type,
                    cost_eur=cost_eur,
                    recorded_at=now,
                    usage_event_id=usage_event_id,
                )
                db.add(window)
            await db.commit()

        # Write to Redis (fast path)
        await self._record_to_redis(user_id, cost_eur, now, usage_event_id)

    async def get_current_usage(self, user_id: int) -> WindowUsageInfo:
        """Get current usage totals for both windows.

        Args:
            user_id: User ID

        Returns:
            WindowUsageInfo with both window costs
        """
        cost_5h = await self._get_window_cost(user_id, WindowType.FIVE_HOUR)
        cost_7d = await self._get_window_cost(user_id, WindowType.SEVEN_DAY)
        return WindowUsageInfo(cost_5h_eur=cost_5h, cost_7d_eur=cost_7d)

    async def get_reset_time(self, user_id: int, window_type: WindowType) -> datetime | None:
        """Get when the window will next have capacity.

        Returns the time when the oldest entry in the window expires.

        Args:
            user_id: User ID
            window_type: Which window to check

        Returns:
            datetime when oldest entry expires, or None if window is empty
        """
        oldest = await self._get_oldest_in_window(user_id, window_type)
        if oldest is None:
            return None
        duration = WINDOW_DURATIONS[window_type]
        return oldest + duration

    # --- Admin simulator methods ---

    async def replace_usage_for_window(
        self,
        user_id: int,
        window_type: WindowType,
        target_cost_eur: float,
    ) -> None:
        """Replace all usage in a window with a single record at target cost.

        Deletes existing PostgreSQL rows and Redis entries for the window,
        then inserts one new record if target_cost_eur > 0.

        Args:
            user_id: User ID
            window_type: Which window ('5h' or '7d')
            target_cost_eur: Desired total cost (0 to clear)
        """
        now = datetime.now(UTC)
        duration = WINDOW_DURATIONS[window_type]
        cutoff = now - duration

        # Clear PostgreSQL rows within the current window period
        async with database_service.get_db() as db:
            stmt = delete(UsageWindow).where(
                and_(
                    UsageWindow.user_id == user_id,
                    UsageWindow.window_type == window_type,
                    UsageWindow.recorded_at >= cutoff,  # type: ignore[operator]
                )
            )
            await db.execute(stmt)

            # Insert one record with the target cost
            if target_cost_eur > 0:
                window = UsageWindow(
                    user_id=user_id,
                    window_type=window_type,
                    cost_eur=target_cost_eur,
                    recorded_at=now,
                )
                db.add(window)

            await db.commit()

        # Clear and re-populate Redis
        try:
            from app.services.cache import cache_service

            redis_client = await cache_service._get_redis()
            if redis_client is not None:
                key = f"usage_window:{user_id}:{window_type}"
                await redis_client.delete(key)

                if target_cost_eur > 0:
                    ts = now.timestamp()
                    member = f"{target_cost_eur}:0:{ts}"
                    await redis_client.zadd(key, {member: ts})
                    ttl = int(duration.total_seconds()) + 3600
                    await redis_client.expire(key, ttl)
        except Exception as e:
            logger.warning("redis_replace_usage_failed", user_id=user_id, error=str(e))

    async def clear_usage(self, user_id: int) -> tuple[int, int]:
        """Clear all usage records for a user (both windows).

        Args:
            user_id: User ID

        Returns:
            Tuple of (pg_rows_deleted, redis_keys_deleted)
        """
        # Delete all PostgreSQL rows for this user
        async with database_service.get_db() as db:
            stmt = delete(UsageWindow).where(UsageWindow.user_id == user_id)
            result = await db.execute(stmt)
            pg_deleted = result.rowcount
            await db.commit()

        # Delete both Redis keys
        redis_deleted = 0
        try:
            from app.services.cache import cache_service

            redis_client = await cache_service._get_redis()
            if redis_client is not None:
                keys = [
                    f"usage_window:{user_id}:{WindowType.FIVE_HOUR}",
                    f"usage_window:{user_id}:{WindowType.SEVEN_DAY}",
                ]
                redis_deleted = await redis_client.delete(*keys)
        except Exception as e:
            logger.warning("redis_clear_usage_failed", user_id=user_id, error=str(e))

        return pg_deleted, redis_deleted

    # --- Internal methods ---

    async def _get_plan(self, plan_slug: str) -> BillingPlan:
        """Get billing plan by slug, defaulting to 'base'."""
        async with database_service.get_db() as db:
            query = select(BillingPlan).where(
                BillingPlan.slug == plan_slug,
                BillingPlan.is_active == True,  # noqa: E712
            )
            result = await db.execute(query)
            plan = result.scalar_one_or_none()

            if plan is None:
                # Fall back to base plan
                query = select(BillingPlan).where(BillingPlan.slug == "base")
                result = await db.execute(query)
                plan = result.scalar_one_or_none()

            if plan is None:
                # Absolute fallback with default limits
                logger.error("no_billing_plans_found", plan_slug=plan_slug)
                return BillingPlan(
                    slug="base",
                    name="Base",
                    price_eur_monthly=25.0,
                    monthly_cost_limit_eur=10.0,
                    window_5h_cost_limit_eur=2.50,
                    window_7d_cost_limit_eur=7.50,
                    credit_markup_factor=1.50,
                )

            return plan

    async def _get_window_cost(self, user_id: int, window_type: WindowType) -> float:
        """Get total cost in a rolling window from PostgreSQL."""
        duration = WINDOW_DURATIONS[window_type]
        cutoff = datetime.now(UTC) - duration

        try:
            # Try Redis first
            cost = await self._get_window_cost_redis(user_id, window_type, cutoff)
            if cost is not None:
                return cost
        except Exception:
            pass  # Fall through to PostgreSQL

        # PostgreSQL fallback
        async with database_service.get_db() as db:
            query = select(func.coalesce(func.sum(UsageWindow.cost_eur), 0.0)).where(
                and_(
                    UsageWindow.user_id == user_id,
                    UsageWindow.window_type == window_type,
                    UsageWindow.recorded_at >= cutoff,  # type: ignore[operator]
                )
            )
            result = await db.execute(query)
            return float(result.scalar() or 0.0)

    async def _get_credit_info(self, user_id: int) -> tuple[bool, float]:
        """Get credit enabled status and balance.

        Returns:
            Tuple of (extra_usage_enabled, balance_eur)
        """
        async with database_service.get_db() as db:
            query = select(UserCredit).where(UserCredit.user_id == user_id)
            result = await db.execute(query)
            credit = result.scalar_one_or_none()
            if credit is None:
                return False, 0.0
            return credit.extra_usage_enabled, credit.balance_eur

    async def _get_oldest_in_window(self, user_id: int, window_type: WindowType) -> datetime | None:
        """Get the oldest entry timestamp in the current window.

        Tries Redis first (fast path), falls back to PostgreSQL.
        """
        duration = WINDOW_DURATIONS[window_type]
        cutoff = datetime.now(UTC) - duration

        try:
            result = await self._get_oldest_in_window_redis(user_id, window_type, cutoff)
            if result is not None:
                return result
        except Exception:
            pass  # Fall through to PostgreSQL

        # PostgreSQL fallback
        async with database_service.get_db() as db:
            query = select(func.min(UsageWindow.recorded_at)).where(
                and_(
                    UsageWindow.user_id == user_id,
                    UsageWindow.window_type == window_type,
                    UsageWindow.recorded_at >= cutoff,  # type: ignore[operator]
                )
            )
            db_result = await db.execute(query)
            value = db_result.scalar()
            # Defensive: TIMESTAMPTZ returns aware datetimes, but guard against
            # unexpected naive values from driver edge cases
            if value is not None and value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            return value

    async def _get_oldest_in_window_redis(
        self,
        user_id: int,
        window_type: WindowType,
        cutoff: datetime,
    ) -> datetime | None:
        """Get oldest entry timestamp from Redis sorted set."""
        from app.services.cache import cache_service

        redis_client = await cache_service._get_redis()
        if redis_client is None:
            return None

        key = f"usage_window:{user_id}:{window_type}"
        cutoff_ts = cutoff.timestamp()

        # Get oldest entry within window (ascending by score/timestamp, limit 1)
        entries = await redis_client.zrangebyscore(key, cutoff_ts, "+inf", start=0, num=1)
        if not entries:
            return None

        entry_str = entries[0].decode() if isinstance(entries[0], bytes) else entries[0]
        # Member format: "cost:event_id:timestamp"
        ts = float(entry_str.split(":")[2])
        return datetime.fromtimestamp(ts, tz=UTC)

    async def _record_to_redis(
        self,
        user_id: int,
        cost_eur: float,
        timestamp: datetime,
        usage_event_id: int | None,
    ) -> None:
        """Record usage to Redis sorted sets for fast lookups."""
        try:
            from app.services.cache import cache_service

            redis_client = await cache_service._get_redis()
            if redis_client is None:
                return

            ts = timestamp.timestamp()
            member = f"{cost_eur}:{usage_event_id or 0}:{ts}"

            for window_type in [WindowType.FIVE_HOUR, WindowType.SEVEN_DAY]:
                key = f"usage_window:{user_id}:{window_type}"
                await redis_client.zadd(key, {member: ts})

                # Clean up expired entries
                duration = WINDOW_DURATIONS[window_type]
                cutoff = (timestamp - duration).timestamp()
                await redis_client.zremrangebyscore(key, "-inf", cutoff)

                # Set TTL to window duration + 1h buffer
                ttl = int(duration.total_seconds()) + 3600
                await redis_client.expire(key, ttl)

        except Exception as e:
            logger.warning("redis_window_write_failed", user_id=user_id, error=str(e))

    async def _get_window_cost_redis(self, user_id: int, window_type: WindowType, cutoff: datetime) -> float | None:
        """Get window cost from Redis sorted set."""
        from app.services.cache import cache_service

        redis_client = await cache_service._get_redis()
        if redis_client is None:
            return None

        key = f"usage_window:{user_id}:{window_type}"
        cutoff_ts = cutoff.timestamp()

        # Get all entries within window
        entries = await redis_client.zrangebyscore(key, cutoff_ts, "+inf")
        if not entries:
            return 0.0

        total = 0.0
        for entry in entries:
            entry_str = entry.decode() if isinstance(entry, bytes) else entry
            cost_str = entry_str.split(":")[0]
            total += float(cost_str)

        return total


# Global instance
rolling_window_service = RollingWindowService()
