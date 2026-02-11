"""Usage tracking service for cost monitoring and optimization.

This module provides comprehensive usage tracking, cost calculation,
and budget management to maintain the €2/user/month target.
"""

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.llm.base import LLMResponse
from app.core.logging import logger
from app.models.usage import (
    CostAlert,
    CostCategory,
    CostOptimizationSuggestion,
    UsageEvent,
    UsageQuota,
    UsageType,
    UserUsageSummary,
)
from app.services.database import database_service


@dataclass
class UsageMetrics:
    """Container for usage metrics."""

    total_requests: int = 0
    llm_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_tokens: int = 0
    total_cost_eur: float = 0.0
    avg_response_time_ms: float = 0.0
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0


@dataclass
class CostBreakdown:
    """Cost breakdown by category."""

    llm_inference: float = 0.0
    storage: float = 0.0
    compute: float = 0.0
    bandwidth: float = 0.0
    third_party: float = 0.0
    total: float = 0.0

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "llm_inference": self.llm_inference,
            "storage": self.storage,
            "compute": self.compute,
            "bandwidth": self.bandwidth,
            "third_party": self.third_party,
            "total": self.total,
        }


class UsageTracker:
    """Tracks and manages usage for cost control."""

    def __init__(self):
        """Initialize the usage tracker."""
        self._alert_thresholds = {
            "daily_cost": 0.10,  # €0.10 per day warning
            "monthly_cost": 2.00,  # €2.00 per month target
            "hourly_requests": 50,  # Rate limit warning
        }

    def _convert_user_id(self, user_id: str | int) -> int:
        """Convert user_id to int for database FK constraint.

        DEV-257: UsageEvent.user_id is FK to user.id (int), but callers often
        pass string user_ids from session data.

        Args:
            user_id: User identifier as string or int

        Returns:
            int: User ID as integer

        Raises:
            ValueError: If user_id cannot be converted to int
        """
        if isinstance(user_id, int):
            return user_id
        try:
            return int(user_id)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid user_id: {user_id!r} - must be numeric") from e

    async def track_llm_usage(
        self,
        user_id: str | int,
        session_id: str,
        provider: str,
        model: str,
        llm_response: LLMResponse,
        response_time_ms: int,
        cache_hit: bool = False,
        pii_detected: bool = False,
        pii_types: list[str] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UsageEvent:
        """Track LLM usage event and update quotas.

        Args:
            user_id: User identifier (str or int, will be converted to int)
            session_id: Session identifier
            provider: LLM provider name
            model: Model name
            llm_response: The LLM response with token and cost info
            response_time_ms: Response time in milliseconds
            cache_hit: Whether this was served from cache
            pii_detected: Whether PII was detected
            pii_types: Types of PII detected
            ip_address: Client IP (anonymized)
            user_agent: Client user agent

        Returns:
            UsageEvent: The created usage event

        Raises:
            ValueError: If user_id cannot be converted to int
        """
        # DEV-257: Convert user_id to int (UsageEvent.user_id is FK to user.id)
        user_id_int = self._convert_user_id(user_id)

        try:
            # Extract token information
            # tokens_used may be a dict (converted by caller) or int or None
            raw_tokens = llm_response.tokens_used
            tokens_used: dict[str, int] = raw_tokens if isinstance(raw_tokens, dict) else {}
            input_tokens = tokens_used.get("input", 0)
            output_tokens = tokens_used.get("output", 0)
            total_tokens = input_tokens + output_tokens

            # Get cost (0 if from cache)
            cost_eur = 0.0 if cache_hit else (llm_response.cost_estimate or 0.0)

            # Create usage event
            usage_event = UsageEvent(
                user_id=user_id_int,
                session_id=session_id,
                event_type=UsageType.LLM_QUERY,
                environment=settings.ENVIRONMENT.value,  # DEV-246: Track environment
                provider=provider,
                model=model,
                input_tokens=input_tokens if not cache_hit else 0,
                output_tokens=output_tokens if not cache_hit else 0,
                total_tokens=total_tokens if not cache_hit else 0,
                cost_eur=cost_eur,
                cost_category=CostCategory.LLM_INFERENCE,
                response_time_ms=response_time_ms,
                cache_hit=cache_hit,
                ip_address=ip_address,
                user_agent=user_agent,
                pii_detected=pii_detected,
                pii_types=json.dumps(pii_types) if pii_types else None,
                error_occurred=False,
            )

            # Save to database
            async with database_service.get_db() as db:  # type: ignore[attr-defined]  # type: ignore[attr-defined]
                db.add(usage_event)
                await db.commit()
                await db.refresh(usage_event)

            # Update quotas and check limits
            await self._update_user_quota(user_id_int, cost_eur, total_tokens)

            # Update daily summary
            await self._update_daily_summary(user_id_int, usage_event)

            # Check for alerts
            await self._check_cost_alerts(user_id_int, cost_eur)

            logger.info(
                "usage_tracked",
                user_id=user_id_int,
                provider=provider,
                model=model,
                cost_eur=cost_eur,
                tokens=total_tokens,
                cache_hit=cache_hit,
                response_time_ms=response_time_ms,
            )

            return usage_event

        except Exception as e:
            logger.error("usage_tracking_failed", user_id=user_id_int, error=str(e), exc_info=True)
            # Create minimal event for error tracking
            return UsageEvent(
                user_id=user_id_int,
                session_id=session_id,
                event_type=UsageType.LLM_QUERY,
                environment=settings.ENVIRONMENT.value,  # DEV-246: Track environment
                error_occurred=True,
                error_type=str(e),
            )

    async def track_api_request(
        self,
        user_id: str | int,
        session_id: str,
        endpoint: str,
        method: str,
        response_time_ms: int,
        request_size: int,
        response_size: int,
        error_occurred: bool = False,
        error_type: str | None = None,
    ) -> UsageEvent:
        """Track general API usage.

        Args:
            user_id: User identifier (str or int, will be converted to int)
            session_id: Session identifier
            endpoint: API endpoint
            method: HTTP method
            response_time_ms: Response time
            request_size: Request size in bytes
            response_size: Response size in bytes
            error_occurred: Whether an error occurred
            error_type: Type of error if any

        Returns:
            UsageEvent: The created usage event

        Raises:
            ValueError: If user_id cannot be converted to int
        """
        # DEV-257: Convert user_id to int (UsageEvent.user_id is FK to user.id)
        user_id_int = self._convert_user_id(user_id)

        usage_event = UsageEvent(
            user_id=user_id_int,
            session_id=session_id,
            event_type=UsageType.API_REQUEST,
            environment=settings.ENVIRONMENT.value,  # DEV-246: Track environment
            response_time_ms=response_time_ms,
            request_size=request_size,
            response_size=response_size,
            error_occurred=error_occurred,
            error_type=error_type,
            cost_category=CostCategory.COMPUTE,
        )

        async with database_service.get_db() as db:  # type: ignore[attr-defined]  # type: ignore[attr-defined]
            db.add(usage_event)
            await db.commit()

        return usage_event

    async def track_third_party_api(
        self,
        user_id: str | int,
        session_id: str,
        api_type: str,
        cost_eur: float,
        response_time_ms: int,
        request_count: int = 1,
        error_occurred: bool = False,
        error_type: str | None = None,
    ) -> UsageEvent:
        """Track third-party API usage (e.g., Brave Search API).

        DEV-246: Track third-party API costs separately for daily cost reporting.

        Args:
            user_id: User identifier (str or int, will be converted to int)
            session_id: Session identifier
            api_type: Type of API (e.g., "brave_search", "web_scraper")
            cost_eur: Cost in EUR for this API call
            response_time_ms: Response time in milliseconds
            request_count: Number of API requests (default: 1)
            error_occurred: Whether an error occurred
            error_type: Type of error if any

        Returns:
            UsageEvent: The created usage event

        Raises:
            ValueError: If user_id cannot be converted to int
        """
        # DEV-257: Convert user_id to int (UsageEvent.user_id is FK to user.id)
        user_id_int = self._convert_user_id(user_id)

        usage_event = UsageEvent(
            user_id=user_id_int,
            session_id=session_id,
            event_type=UsageType.API_REQUEST,
            environment=settings.ENVIRONMENT.value,  # DEV-246: Track environment
            api_type=api_type,  # DEV-246: Track API type for third-party breakdown
            cost_eur=cost_eur,
            cost_category=CostCategory.THIRD_PARTY,
            response_time_ms=response_time_ms,
            error_occurred=error_occurred,
            error_type=error_type,
        )

        try:
            async with database_service.get_db() as db:  # type: ignore[attr-defined]
                db.add(usage_event)
                await db.commit()
                await db.refresh(usage_event)

            logger.info(
                "third_party_api_tracked",
                user_id=user_id_int,
                api_type=api_type,
                cost_eur=cost_eur,
                environment=settings.ENVIRONMENT.value,
            )

            return usage_event

        except Exception as e:
            logger.error(
                "third_party_api_tracking_failed",
                user_id=user_id_int,
                api_type=api_type,
                error=str(e),
            )
            # Return event even on error (not persisted)
            return usage_event

    async def get_user_metrics(
        self, user_id: str, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> UsageMetrics:
        """Get usage metrics for a user.

        Args:
            user_id: User identifier
            start_date: Start date for metrics (default: beginning of current month)
            end_date: End date for metrics (default: now)

        Returns:
            UsageMetrics: Aggregated usage metrics
        """
        if not start_date:
            start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.utcnow()

        async with database_service.get_db() as db:  # type: ignore[attr-defined]  # type: ignore[attr-defined]
            # Get usage events
            query = select(UsageEvent).where(
                and_(
                    UsageEvent.user_id == user_id,  # type: ignore[comparison-overlap]
                    UsageEvent.timestamp >= start_date,
                    UsageEvent.timestamp <= end_date,
                )
            )
            result = await db.execute(query)
            events = result.scalars().all()

            # Calculate metrics
            metrics = UsageMetrics()
            response_times = []

            for event in events:
                metrics.total_requests += 1

                if event.event_type == UsageType.LLM_QUERY:
                    metrics.llm_requests += 1
                    if event.cache_hit:
                        metrics.cache_hits += 1
                    else:
                        metrics.cache_misses += 1

                if event.total_tokens:
                    metrics.total_tokens += event.total_tokens

                if event.cost_eur:
                    metrics.total_cost_eur += event.cost_eur

                if event.response_time_ms:
                    response_times.append(event.response_time_ms)

                if event.error_occurred:
                    metrics.error_rate += 1

            # Calculate rates
            if metrics.total_requests > 0:
                metrics.error_rate = metrics.error_rate / metrics.total_requests

            if metrics.llm_requests > 0:
                metrics.cache_hit_rate = metrics.cache_hits / metrics.llm_requests

            if response_times:
                metrics.avg_response_time_ms = sum(response_times) / len(response_times)

            return metrics

    async def get_cost_breakdown(
        self, user_id: str, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> CostBreakdown:
        """Get cost breakdown by category for a user.

        Args:
            user_id: User identifier
            start_date: Start date
            end_date: End date

        Returns:
            CostBreakdown: Costs broken down by category
        """
        if not start_date:
            start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.utcnow()

        async with database_service.get_db() as db:  # type: ignore[attr-defined]
            query = (
                select(UsageEvent.cost_category, func.sum(UsageEvent.cost_eur))
                .where(
                    and_(
                        UsageEvent.user_id == user_id,  # type: ignore[comparison-overlap]
                        UsageEvent.timestamp >= start_date,
                        UsageEvent.timestamp <= end_date,
                        UsageEvent.cost_eur.isnot(None),  # type: ignore[union-attr]
                    )
                )
                .group_by(UsageEvent.cost_category)
            )

            result = await db.execute(query)
            category_costs = result.all()

            breakdown = CostBreakdown()
            for category, cost in category_costs:
                if category == CostCategory.LLM_INFERENCE:
                    breakdown.llm_inference = float(cost or 0)
                elif category == CostCategory.STORAGE:
                    breakdown.storage = float(cost or 0)
                elif category == CostCategory.COMPUTE:
                    breakdown.compute = float(cost or 0)
                elif category == CostCategory.BANDWIDTH:
                    breakdown.bandwidth = float(cost or 0)
                elif category == CostCategory.THIRD_PARTY:
                    breakdown.third_party = float(cost or 0)

            breakdown.total = (
                breakdown.llm_inference
                + breakdown.storage
                + breakdown.compute
                + breakdown.bandwidth
                + breakdown.third_party
            )

            return breakdown

    async def get_user_quota(self, user_id: str) -> UsageQuota:
        """Get or create user quota.

        Args:
            user_id: User identifier

        Returns:
            UsageQuota: User's quota information
        """
        async with database_service.get_db() as db:  # type: ignore[attr-defined]
            query = select(UsageQuota).where(UsageQuota.user_id == user_id)  # type: ignore[comparison-overlap]
            result = await db.execute(query)
            quota = result.scalar_one_or_none()

            if not quota:
                # Create default quota
                quota = UsageQuota(
                    user_id=user_id,
                    daily_requests_limit=100,
                    daily_cost_limit_eur=0.10,
                    monthly_cost_limit_eur=2.00,
                    daily_token_limit=50000,
                    monthly_token_limit=1000000,
                )
                db.add(quota)
                await db.commit()
                await db.refresh(quota)

            # Check if reset is needed
            now = datetime.utcnow()

            # Daily reset
            if quota.daily_reset_at.date() < now.date():
                quota.current_daily_requests = 0
                quota.current_daily_cost_eur = 0.0
                quota.current_daily_tokens = 0
                quota.daily_reset_at = now

            # Monthly reset
            if quota.monthly_reset_at.month < now.month or quota.monthly_reset_at.year < now.year:
                quota.current_monthly_cost_eur = 0.0
                quota.current_monthly_tokens = 0
                quota.monthly_reset_at = now

            await db.commit()

            return cast(UsageQuota, quota)

    async def check_quota_limits(self, user_id: str) -> tuple[bool, str | None]:
        """Check if user is within quota limits.

        Args:
            user_id: User identifier

        Returns:
            Tuple[bool, Optional[str]]: (is_allowed, reason_if_blocked)
        """
        quota = await self.get_user_quota(user_id)

        if not quota.is_active:
            return False, "Quota is not active"

        if quota.blocked_until and quota.blocked_until > datetime.utcnow():
            return False, f"Blocked until {quota.blocked_until.isoformat()}"

        if quota.current_daily_requests >= quota.daily_requests_limit:
            return False, "Daily request limit exceeded"

        if quota.current_daily_cost_eur >= quota.daily_cost_limit_eur:
            return False, "Daily cost limit exceeded"

        if quota.current_monthly_cost_eur >= quota.monthly_cost_limit_eur:
            return False, "Monthly cost limit exceeded"

        if quota.current_daily_tokens >= quota.daily_token_limit:
            return False, "Daily token limit exceeded"

        if quota.current_monthly_tokens >= quota.monthly_token_limit:
            return False, "Monthly token limit exceeded"

        return True, None

    async def _update_user_quota(self, user_id: str, cost_eur: float, tokens: int):
        """Update user quota with new usage.

        Args:
            user_id: User identifier
            cost_eur: Cost in EUR
            tokens: Number of tokens used
        """
        async with database_service.get_db() as db:  # type: ignore[attr-defined]  # type: ignore[attr-defined]
            quota = await self.get_user_quota(user_id)

            quota.current_daily_requests += 1
            quota.current_daily_cost_eur += cost_eur
            quota.current_monthly_cost_eur += cost_eur
            quota.current_daily_tokens += tokens
            quota.current_monthly_tokens += tokens
            quota.updated_at = datetime.utcnow()

            await db.commit()

            # Check if user is approaching limits
            if quota.current_monthly_cost_eur / quota.monthly_cost_limit_eur > 0.8:
                logger.warning(
                    "user_approaching_monthly_limit",
                    user_id=user_id,
                    current_cost=quota.current_monthly_cost_eur,
                    limit=quota.monthly_cost_limit_eur,
                    percentage=quota.current_monthly_cost_eur / quota.monthly_cost_limit_eur * 100,
                )

    async def _update_daily_summary(self, user_id: str, event: UsageEvent):
        """Update daily usage summary.

        Args:
            user_id: User identifier
            event: Usage event to include in summary
        """
        today = date.today()

        async with database_service.get_db() as db:  # type: ignore[attr-defined]
            # Get or create summary
            query = select(UserUsageSummary).where(
                and_(
                    UserUsageSummary.user_id == user_id,  # type: ignore[comparison-overlap]
                    func.date(UserUsageSummary.date) == today,
                )
            )
            result = await db.execute(query)
            summary = result.scalar_one_or_none()

            if not summary:
                summary = UserUsageSummary(
                    user_id=user_id, date=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                )
                db.add(summary)

            # Update counts
            summary.total_requests += 1

            if event.event_type == UsageType.LLM_QUERY:
                summary.llm_requests += 1
                if event.cache_hit:
                    summary.cache_hits += 1
                else:
                    summary.cache_misses += 1

                # Update token counts
                if event.input_tokens:
                    summary.total_input_tokens += event.input_tokens
                if event.output_tokens:
                    summary.total_output_tokens += event.output_tokens
                if event.total_tokens:
                    summary.total_tokens += event.total_tokens

            # Update costs
            if event.cost_eur:
                summary.total_cost_eur += event.cost_eur
                if event.cost_category == CostCategory.LLM_INFERENCE:
                    summary.llm_cost_eur += event.cost_eur

            # Update error tracking
            if event.error_occurred:
                summary.error_count += 1

            # Update PII tracking
            if event.pii_detected:
                summary.pii_detections += 1

            # Recalculate rates
            if summary.total_requests > 0:
                summary.error_rate = summary.error_count / summary.total_requests
                summary.anonymization_rate = summary.pii_detections / summary.total_requests

            if summary.llm_requests > 0:
                summary.cache_hit_rate = summary.cache_hits / summary.llm_requests

            summary.updated_at = datetime.utcnow()

            await db.commit()

    async def _check_cost_alerts(self, user_id: str, new_cost: float):
        """Check if cost alerts should be triggered.

        Args:
            user_id: User identifier
            new_cost: New cost to add
        """
        quota = await self.get_user_quota(user_id)

        # Check daily threshold
        if quota.current_daily_cost_eur > self._alert_thresholds["daily_cost"]:
            await self._create_alert(
                user_id=user_id,
                alert_type="daily_threshold",
                threshold_eur=self._alert_thresholds["daily_cost"],
                current_cost_eur=quota.current_daily_cost_eur,
            )

        # Check monthly threshold (80% warning)
        monthly_threshold = self._alert_thresholds["monthly_cost"] * 0.8
        if quota.current_monthly_cost_eur > monthly_threshold:
            await self._create_alert(
                user_id=user_id,
                alert_type="monthly_warning",
                threshold_eur=monthly_threshold,
                current_cost_eur=quota.current_monthly_cost_eur,
            )

    async def _create_alert(self, user_id: str, alert_type: str, threshold_eur: float, current_cost_eur: float):
        """Create a cost alert.

        Args:
            user_id: User identifier
            alert_type: Type of alert
            threshold_eur: Threshold that was exceeded
            current_cost_eur: Current cost
        """
        async with database_service.get_db() as db:  # type: ignore[attr-defined]
            # Check if similar alert already exists today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            query = select(CostAlert).where(
                and_(
                    CostAlert.user_id == user_id,  # type: ignore[comparison-overlap]
                    CostAlert.alert_type == alert_type,
                    CostAlert.triggered_at >= today_start,
                )
            )
            result = await db.execute(query)
            existing_alert = result.scalar_one_or_none()

            if not existing_alert:
                alert = CostAlert(
                    user_id=user_id,
                    alert_type=alert_type,
                    threshold_eur=threshold_eur,
                    current_cost_eur=current_cost_eur,
                    period_start=today_start,
                    period_end=today_start + timedelta(days=1),
                )
                db.add(alert)
                await db.commit()

                logger.warning(
                    "cost_alert_triggered",
                    user_id=user_id,
                    alert_type=alert_type,
                    threshold=threshold_eur,
                    current_cost=current_cost_eur,
                )

    async def get_optimization_suggestions(
        self, user_id: str | None = None, limit: int = 10
    ) -> list[CostOptimizationSuggestion]:
        """Get cost optimization suggestions.

        Args:
            user_id: User ID (None for system-wide suggestions)
            limit: Maximum number of suggestions

        Returns:
            List of optimization suggestions
        """
        async with database_service.get_db() as db:  # type: ignore[attr-defined]
            query = select(CostOptimizationSuggestion).where(CostOptimizationSuggestion.status == "pending")

            if user_id:
                query = query.where(
                    or_(
                        CostOptimizationSuggestion.user_id == user_id,  # type: ignore[comparison-overlap]
                        CostOptimizationSuggestion.user_id.is_(None),  # type: ignore[union-attr]
                    )
                )

            query = query.order_by(
                CostOptimizationSuggestion.estimated_savings_eur.desc()  # type: ignore[attr-defined]
            ).limit(limit)

            result = await db.execute(query)
            return cast(list[CostOptimizationSuggestion], result.scalars().all())

    async def generate_optimization_suggestions(self, user_id: str):
        """Generate cost optimization suggestions for a user.

        Args:
            user_id: User identifier
        """
        # Get user metrics
        metrics = await self.get_user_metrics(user_id)

        suggestions = []

        # Suggestion 1: Improve cache usage
        if metrics.cache_hit_rate < 0.5 and metrics.llm_requests > 10:
            suggestions.append(
                CostOptimizationSuggestion(
                    user_id=user_id,
                    suggestion_type="improve_caching",
                    title="Improve Cache Utilization",
                    description=f"Your cache hit rate is {metrics.cache_hit_rate:.1%}. Improving it to 80% could save ~€{metrics.total_cost_eur * 0.3:.2f}/month",
                    estimated_savings_eur=metrics.total_cost_eur * 0.3,
                    estimated_savings_percentage=30.0,
                    confidence_score=0.8,
                    implementation_effort="low",
                    auto_implementable=True,
                )
            )

        # Suggestion 2: Use cheaper models for simple queries
        if metrics.total_cost_eur > 1.0:
            suggestions.append(
                CostOptimizationSuggestion(
                    user_id=user_id,
                    suggestion_type="model_optimization",
                    title="Use Cost-Optimized Models",
                    description="Switch to cheaper models for simple queries. Our analysis shows 40% of your queries could use lighter models.",
                    estimated_savings_eur=metrics.total_cost_eur * 0.4,
                    estimated_savings_percentage=40.0,
                    confidence_score=0.7,
                    implementation_effort="low",
                    auto_implementable=True,
                )
            )

        # Save suggestions
        async with database_service.get_db() as db:  # type: ignore[attr-defined]  # type: ignore[attr-defined]
            for suggestion in suggestions:
                db.add(suggestion)
            await db.commit()

        logger.info("optimization_suggestions_generated", user_id=user_id, suggestions_count=len(suggestions))

    async def get_system_metrics(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, Any]:
        """Get system-wide usage metrics.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            System-wide metrics
        """
        if not start_date:
            start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.utcnow()

        async with database_service.get_db() as db:  # type: ignore[attr-defined]
            # Total users
            user_query = select(func.count(func.distinct(UsageEvent.user_id))).where(
                and_(UsageEvent.timestamp >= start_date, UsageEvent.timestamp <= end_date)
            )
            user_result = await db.execute(user_query)
            total_users = user_result.scalar() or 0

            # Total costs
            cost_query: Any = select(func.sum(UsageEvent.cost_eur)).where(
                and_(UsageEvent.timestamp >= start_date, UsageEvent.timestamp <= end_date)
            )
            cost_result = await db.execute(cost_query)
            total_cost = float(cost_result.scalar() or 0)

            # Average cost per user
            avg_cost_per_user = total_cost / total_users if total_users > 0 else 0

            # Model usage breakdown
            model_query = (
                select(UsageEvent.model, func.count(UsageEvent.id), func.sum(UsageEvent.cost_eur))
                .where(
                    and_(
                        UsageEvent.timestamp >= start_date,
                        UsageEvent.timestamp <= end_date,
                        UsageEvent.model.isnot(None),  # type: ignore[union-attr]
                    )
                )
                .group_by(UsageEvent.model)
            )

            model_result = await db.execute(model_query)
            model_usage = [
                {"model": model, "requests": count, "cost": float(cost or 0)}
                for model, count, cost in model_result.all()
            ]

            return {
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "total_users": total_users,
                "total_cost_eur": total_cost,
                "avg_cost_per_user_eur": avg_cost_per_user,
                "model_usage": model_usage,
                "target_cost_per_user_eur": 2.00,
                "cost_efficiency": (2.00 - avg_cost_per_user) / 2.00 * 100 if avg_cost_per_user < 2.00 else 0,
            }


# Global usage tracker instance
usage_tracker = UsageTracker()
