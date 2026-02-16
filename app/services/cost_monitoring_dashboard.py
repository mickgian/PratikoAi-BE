"""Cost Monitoring Dashboard Service (DEV-239).

Provides real-time visibility into LLM costs per query, model,
and complexity level with daily/weekly aggregates.

Coverage Target: 90%+ for new code.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select

from app.core.logging import logger
from app.models.usage import CostCategory, UsageEvent, UsageType
from app.services.database import database_service


class CostMonitoringDashboard:
    """Dashboard service for LLM cost monitoring and analysis.

    Provides:
    - Cost per query tracking
    - Cost breakdown by model
    - Cost breakdown by complexity
    - Daily/weekly cost aggregates
    """

    def __init__(self):
        """Initialize the cost monitoring dashboard."""
        self._default_lookback_days = 30

    async def get_query_costs(
        self,
        user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get individual query costs.

        Args:
            user_id: Optional user ID filter
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of query cost records
        """
        return await self._fetch_query_costs(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    async def _fetch_query_costs(
        self,
        user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch query costs from database.

        Args:
            user_id: Optional user ID filter
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of query cost records
        """
        try:
            async with database_service.get_db() as db:
                query = select(UsageEvent).where(
                    and_(
                        UsageEvent.event_type == UsageType.LLM_QUERY,
                        UsageEvent.cost_eur.isnot(None),  # type: ignore[union-attr]
                    )
                )

                if user_id:
                    query = query.where(UsageEvent.user_id == user_id)  # type: ignore[arg-type,comparison-overlap]

                query = query.order_by(UsageEvent.timestamp.desc()).limit(limit).offset(offset)  # type: ignore[union-attr,attr-defined]

                result = await db.execute(query)
                events = result.scalars().all()

                return [
                    {
                        "request_id": str(e.id),
                        "user_id": e.user_id,
                        "model": e.model,
                        "complexity": self._infer_complexity(e.model),
                        "cost_euros": float(e.cost_eur or 0),
                        "tokens_input": e.input_tokens or 0,
                        "tokens_output": e.output_tokens or 0,
                        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                    }
                    for e in events
                ]

        except Exception as e:
            logger.error("fetch_query_costs_failed", error=str(e), user_id=user_id)
            return []

    def _infer_complexity(self, model: str | None) -> str:
        """Infer complexity from model name.

        Args:
            model: Model name

        Returns:
            Inferred complexity level
        """
        if not model:
            return "unknown"
        if "mini" in model.lower():
            return "simple"
        if "4o" in model or "gpt-4" in model:
            return "complex"
        return "simple"

    async def get_cost_by_model(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Get cost breakdown by model.

        Args:
            start_date: Start of period (default: 30 days ago)
            end_date: End of period (default: now)

        Returns:
            Dict mapping model name to cost metrics
        """
        return await self._aggregate_costs_by_model(start_date, end_date)

    async def _aggregate_costs_by_model(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Aggregate costs by model from database.

        Args:
            start_date: Start of period
            end_date: End of period

        Returns:
            Dict mapping model name to cost metrics
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=self._default_lookback_days)
        if not end_date:
            end_date = datetime.utcnow()

        try:
            async with database_service.get_db() as db:
                query = (
                    select(
                        UsageEvent.model,
                        func.sum(UsageEvent.cost_eur).label("total_cost"),
                        func.count(UsageEvent.id).label("query_count"),
                    )
                    .where(
                        and_(
                            UsageEvent.event_type == UsageType.LLM_QUERY,
                            UsageEvent.timestamp >= start_date,
                            UsageEvent.timestamp <= end_date,
                            UsageEvent.model.isnot(None),  # type: ignore[union-attr]
                        )
                    )
                    .group_by(UsageEvent.model)
                )

                result = await db.execute(query)
                rows = result.all()

                breakdown = {}
                for model, total_cost, query_count in rows:
                    if model:
                        total = float(total_cost or 0)
                        count = int(query_count or 0)
                        breakdown[model] = {
                            "total_cost": total,
                            "query_count": count,
                            "avg_cost": total / count if count > 0 else 0,
                        }

                return breakdown

        except Exception as e:
            logger.error("aggregate_costs_by_model_failed", error=str(e))
            return {}

    async def get_cost_by_complexity(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Get cost breakdown by complexity level.

        Args:
            start_date: Start of period
            end_date: End of period

        Returns:
            Dict mapping complexity to cost metrics
        """
        return await self._aggregate_costs_by_complexity(start_date, end_date)

    async def _aggregate_costs_by_complexity(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Aggregate costs by complexity from database.

        Uses model name to infer complexity.

        Args:
            start_date: Start of period
            end_date: End of period

        Returns:
            Dict mapping complexity to cost metrics
        """
        # Get model breakdown first
        model_breakdown = await self._aggregate_costs_by_model(start_date, end_date)

        # Aggregate by complexity
        complexity_totals: dict[str, dict[str, float]] = {
            "simple": {"total_cost": 0.0, "query_count": 0},
            "complex": {"total_cost": 0.0, "query_count": 0},
            "multi_domain": {"total_cost": 0.0, "query_count": 0},
        }

        total_cost = 0.0

        for model, metrics in model_breakdown.items():
            complexity = self._infer_complexity(model)
            if complexity in complexity_totals:
                complexity_totals[complexity]["total_cost"] += metrics["total_cost"]
                complexity_totals[complexity]["query_count"] += metrics["query_count"]
                total_cost += metrics["total_cost"]

        # Calculate percentages
        result = {}
        for complexity, metrics in complexity_totals.items():
            result[complexity] = {
                "total_cost": metrics["total_cost"],
                "query_count": int(metrics["query_count"]),
                "percentage": (metrics["total_cost"] / total_cost * 100) if total_cost > 0 else 0,
            }

        return result

    async def get_daily_aggregates(
        self,
        days: int = 7,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get daily cost aggregates.

        Args:
            days: Number of days to look back
            user_id: Optional user ID filter

        Returns:
            List of daily aggregate records
        """
        return await self._fetch_daily_aggregates(days, user_id)

    async def _fetch_daily_aggregates(
        self,
        days: int = 7,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch daily aggregates from database.

        Args:
            days: Number of days to look back
            user_id: Optional user ID filter

        Returns:
            List of daily aggregate records
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        try:
            async with database_service.get_db() as db:
                date_col = func.date(UsageEvent.timestamp).label("date")

                query = (
                    select(
                        date_col,
                        func.sum(UsageEvent.cost_eur).label("total_cost"),
                        func.count(UsageEvent.id).label("query_count"),
                    )
                    .where(
                        and_(
                            UsageEvent.event_type == UsageType.LLM_QUERY,
                            UsageEvent.timestamp >= start_date,
                        )
                    )
                    .group_by(date_col)
                    .order_by(date_col.desc())
                )

                if user_id:
                    query = query.where(UsageEvent.user_id == user_id)  # type: ignore[arg-type,comparison-overlap]

                result = await db.execute(query)
                rows = result.all()

                return [
                    {
                        "date": str(date),
                        "total_cost": float(total_cost or 0),
                        "query_count": int(query_count or 0),
                    }
                    for date, total_cost, query_count in rows
                ]

        except Exception as e:
            logger.error("fetch_daily_aggregates_failed", error=str(e))
            return []

    async def get_weekly_aggregates(
        self,
        weeks: int = 4,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get weekly cost aggregates.

        Args:
            weeks: Number of weeks to look back
            user_id: Optional user ID filter

        Returns:
            List of weekly aggregate records
        """
        return await self._fetch_weekly_aggregates(weeks, user_id)

    async def _fetch_weekly_aggregates(
        self,
        weeks: int = 4,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch weekly aggregates from database.

        Args:
            weeks: Number of weeks to look back
            user_id: Optional user ID filter

        Returns:
            List of weekly aggregate records
        """
        start_date = datetime.utcnow() - timedelta(weeks=weeks)

        try:
            async with database_service.get_db() as db:
                # Use date_trunc for week start
                week_start = func.date_trunc("week", UsageEvent.timestamp).label("week_start")

                query = (
                    select(
                        week_start,
                        func.sum(UsageEvent.cost_eur).label("total_cost"),
                        func.count(UsageEvent.id).label("query_count"),
                    )
                    .where(
                        and_(
                            UsageEvent.event_type == UsageType.LLM_QUERY,
                            UsageEvent.timestamp >= start_date,
                        )
                    )
                    .group_by(week_start)
                    .order_by(week_start.desc())
                )

                if user_id:
                    query = query.where(UsageEvent.user_id == user_id)  # type: ignore[arg-type,comparison-overlap]

                result = await db.execute(query)
                rows = result.all()

                return [
                    {
                        "week_start": str(week_start.date()) if week_start else None,
                        "total_cost": float(total_cost or 0),
                        "query_count": int(query_count or 0),
                    }
                    for week_start, total_cost, query_count in rows
                ]

        except Exception as e:
            logger.error("fetch_weekly_aggregates_failed", error=str(e))
            return []

    async def _calculate_total_cost(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> float:
        """Calculate total cost for period.

        Args:
            start_date: Start of period
            end_date: End of period

        Returns:
            Total cost in euros
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=self._default_lookback_days)
        if not end_date:
            end_date = datetime.utcnow()

        try:
            async with database_service.get_db() as db:
                query = select(func.sum(UsageEvent.cost_eur)).where(
                    and_(
                        UsageEvent.event_type == UsageType.LLM_QUERY,
                        UsageEvent.timestamp >= start_date,
                        UsageEvent.timestamp <= end_date,
                    )
                )

                result = await db.execute(query)
                total = result.scalar()

                return float(total or 0)

        except Exception as e:
            logger.error("calculate_total_cost_failed", error=str(e))
            return 0.0

    async def get_dashboard_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Get complete dashboard summary.

        Args:
            start_date: Start of period (default: 30 days ago)
            end_date: End of period (default: now)

        Returns:
            Complete dashboard data with all sections
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=self._default_lookback_days)
        if not end_date:
            end_date = datetime.utcnow()

        # Fetch all data in parallel (conceptually)
        by_model = await self.get_cost_by_model(start_date, end_date)
        by_complexity = await self.get_cost_by_complexity(start_date, end_date)
        daily_trend = await self.get_daily_aggregates(days=7)
        total_cost = await self._calculate_total_cost(start_date, end_date)

        return {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_cost": total_cost,
            "by_model": by_model,
            "by_complexity": by_complexity,
            "daily_trend": daily_trend,
            "target_cost_per_user_eur": 2.00,
        }


# Global instance
cost_monitoring_dashboard = CostMonitoringDashboard()


def get_cost_monitoring_dashboard() -> CostMonitoringDashboard:
    """Get the cost monitoring dashboard instance.

    Returns:
        CostMonitoringDashboard singleton
    """
    return cost_monitoring_dashboard
