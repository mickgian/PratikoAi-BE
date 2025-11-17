"""Cost-Aware Circuit Logic for Advanced Circuit Breakers.

Implements intelligent cost-based circuit breaking with budget management,
cost spike detection, and cost-optimized provider routing for Italian tax services.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.core.logging import logger
from app.services.cache import CacheService


class CostBreakingReason(Enum):
    """Reasons for cost-based circuit breaking"""

    BUDGET_EXCEEDED = "budget_exceeded"
    COST_SPIKE_DETECTED = "cost_spike_detected"
    EFFICIENCY_THRESHOLD = "efficiency_threshold"
    DAILY_LIMIT_REACHED = "daily_limit_reached"
    PROVIDER_TOO_EXPENSIVE = "provider_too_expensive"
    COST_ANOMALY = "cost_anomaly"


class BudgetPeriod(Enum):
    """Budget period types"""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


@dataclass
class CostBudget:
    """Cost budget configuration"""

    provider: str
    period: BudgetPeriod
    limit: float
    current_spent: float
    period_start: datetime
    period_end: datetime
    alert_thresholds: list[float]  # e.g., [0.7, 0.8, 0.9] for 70%, 80%, 90%
    hard_limit: bool  # If true, stop all traffic when exceeded


@dataclass
class CostMetrics:
    """Cost performance metrics"""

    provider: str
    total_requests: int
    total_cost: float
    average_cost_per_request: float
    cost_efficiency_score: float  # 0-1 where 1 is most efficient
    cost_trend: float  # -1 to 1, negative means getting more expensive
    last_hour_cost: float
    last_24h_cost: float
    projected_daily_cost: float


@dataclass
class CostAlert:
    """Cost-related alert"""

    id: str
    provider: str
    alert_type: CostBreakingReason
    message: str
    cost_impact: float
    threshold_exceeded: float
    recommended_actions: list[str]
    timestamp: datetime
    severity: str  # low, medium, high, critical


class CostAwareCircuitLogic:
    """Manages cost-aware circuit breaking logic"""

    def __init__(self, cache: CacheService | None = None):
        self.cache = cache
        self.budgets = {}  # provider -> CostBudget
        self.cost_history = {}  # provider -> list of cost records
        self.cost_alerts = []  # active cost alerts
        self.provider_rankings = {}  # cost efficiency rankings

        # Cost thresholds and settings
        self.cost_spike_threshold = 2.0  # 2x normal cost triggers spike detection
        self.efficiency_threshold = 0.3  # Below 30% efficiency triggers circuit
        self.anomaly_detection_window = 3600  # 1 hour window for anomaly detection

        # Italian market cost considerations
        self.italian_cost_factors = {
            "peak_hours_multiplier": 1.2,  # 20% higher costs during peak hours
            "tax_deadline_multiplier": 1.5,  # 50% higher costs during deadlines
            "vacation_discount": 0.8,  # 20% discount during August
            "regional_adjustment": 1.0,  # Can vary by region
        }

        # Cache TTL
        self.cache_ttl = 300  # 5 minutes

        # Statistics
        self.stats = {
            "cost_circuits_triggered": 0,
            "total_cost_saved": 0.0,
            "budget_violations": 0,
            "cost_spikes_detected": 0,
            "provider_switches": 0,
        }

    async def should_allow_request_cost_check(
        self, provider: str, estimated_cost: float, request_metadata: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Check if request should be allowed based on cost considerations"""
        try:
            # Get current cost budget
            budget = await self._get_or_create_budget(provider)

            # Check budget limits
            budget_check = self._check_budget_limits(budget, estimated_cost)
            if not budget_check["allowed"]:
                return {
                    "allowed": False,
                    "reason": budget_check["reason"],
                    "cost_info": budget_check,
                    "alternative_providers": await self._suggest_cost_efficient_alternatives(provider),
                }

            # Check for cost spikes
            spike_check = await self._check_cost_spike(provider, estimated_cost)
            if spike_check["spike_detected"]:
                if spike_check["severity"] == "critical":
                    return {
                        "allowed": False,
                        "reason": CostBreakingReason.COST_SPIKE_DETECTED.value,
                        "cost_info": spike_check,
                        "alternative_providers": await self._suggest_cost_efficient_alternatives(provider),
                    }
                else:
                    # Allow but generate alert
                    await self._create_cost_alert(
                        provider,
                        CostBreakingReason.COST_SPIKE_DETECTED,
                        f"Cost spike detected: {spike_check['spike_ratio']:.2f}x normal",
                        estimated_cost,
                        spike_check["spike_ratio"],
                    )

            # Check cost efficiency
            efficiency_check = await self._check_cost_efficiency(provider, estimated_cost)
            if not efficiency_check["efficient"]:
                return {
                    "allowed": False,
                    "reason": CostBreakingReason.EFFICIENCY_THRESHOLD.value,
                    "cost_info": efficiency_check,
                    "alternative_providers": await self._suggest_cost_efficient_alternatives(provider),
                }

            # Apply Italian market adjustments
            italian_adjustment = self._calculate_italian_cost_adjustment(estimated_cost)
            final_cost = estimated_cost * italian_adjustment["multiplier"]

            # Update budget with adjusted cost
            await self._reserve_budget(provider, final_cost)

            return {
                "allowed": True,
                "estimated_cost": final_cost,
                "original_cost": estimated_cost,
                "italian_adjustment": italian_adjustment,
                "budget_remaining": budget.limit - budget.current_spent - final_cost,
            }

        except Exception as e:
            logger.error(f"Cost check failed for {provider}: {e}")
            # Fail open with basic cost tracking
            return {"allowed": True, "estimated_cost": estimated_cost, "error": str(e)}

    async def record_actual_cost(self, provider: str, actual_cost: float, request_metadata: dict[str, Any] = None):
        """Record actual cost after request completion"""
        try:
            # Update budget
            budget = await self._get_or_create_budget(provider)
            budget.current_spent += actual_cost

            # Record in cost history
            cost_record = {
                "timestamp": datetime.utcnow(),
                "cost": actual_cost,
                "metadata": request_metadata or {},
                "provider": provider,
            }

            if provider not in self.cost_history:
                self.cost_history[provider] = []

            self.cost_history[provider].append(cost_record)

            # Keep only recent history (last 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            self.cost_history[provider] = [
                record for record in self.cost_history[provider] if record["timestamp"] > cutoff_time
            ]

            # Update cost metrics
            await self._update_cost_metrics(provider)

            # Check for anomalies in actual vs estimated cost
            estimated_cost = request_metadata.get("estimated_cost", actual_cost) if request_metadata else actual_cost
            if abs(actual_cost - estimated_cost) / estimated_cost > 0.5:  # 50% variance
                await self._create_cost_alert(
                    provider,
                    CostBreakingReason.COST_ANOMALY,
                    f"Large cost variance: estimated ${estimated_cost:.3f}, actual ${actual_cost:.3f}",
                    actual_cost,
                    abs(actual_cost - estimated_cost) / estimated_cost,
                )

            # Update provider rankings
            await self._update_provider_rankings()

        except Exception as e:
            logger.error(f"Failed to record actual cost for {provider}: {e}")

    async def set_cost_budget(
        self,
        provider: str,
        period: BudgetPeriod,
        limit: float,
        alert_thresholds: list[float] = None,
        hard_limit: bool = True,
    ) -> bool:
        """Set cost budget for a provider"""
        try:
            # Calculate period start and end
            now = datetime.utcnow()
            if period == BudgetPeriod.HOURLY:
                period_start = now.replace(minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(hours=1)
            elif period == BudgetPeriod.DAILY:
                period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(days=1)
            elif period == BudgetPeriod.WEEKLY:
                days_since_monday = now.weekday()
                period_start = (now - timedelta(days=days_since_monday)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                period_end = period_start + timedelta(weeks=1)
            elif period == BudgetPeriod.MONTHLY:
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if now.month == 12:
                    period_end = period_start.replace(year=now.year + 1, month=1)
                else:
                    period_end = period_start.replace(month=now.month + 1)
            else:
                # Custom period - use 24 hours as default
                period_start = now
                period_end = now + timedelta(days=1)

            # Get current spending for this period
            current_spent = await self._calculate_period_spending(provider, period_start, period_end)

            budget = CostBudget(
                provider=provider,
                period=period,
                limit=limit,
                current_spent=current_spent,
                period_start=period_start,
                period_end=period_end,
                alert_thresholds=alert_thresholds or [0.7, 0.8, 0.9],
                hard_limit=hard_limit,
            )

            self.budgets[provider] = budget

            logger.info(f"Set {period.value} budget for {provider}: ${limit:.2f} (current: ${current_spent:.2f})")

            return True

        except Exception as e:
            logger.error(f"Failed to set budget for {provider}: {e}")
            return False

    async def get_cost_metrics(self, provider: str) -> CostMetrics | None:
        """Get comprehensive cost metrics for a provider"""
        try:
            if provider not in self.cost_history:
                return None

            history = self.cost_history[provider]
            if not history:
                return None

            # Calculate metrics
            total_requests = len(history)
            total_cost = sum(record["cost"] for record in history)
            average_cost = total_cost / total_requests if total_requests > 0 else 0

            # Last hour cost
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            last_hour_records = [r for r in history if r["timestamp"] > hour_ago]
            last_hour_cost = sum(record["cost"] for record in last_hour_records)

            # Last 24h cost
            day_ago = datetime.utcnow() - timedelta(hours=24)
            last_24h_records = [r for r in history if r["timestamp"] > day_ago]
            last_24h_cost = sum(record["cost"] for record in last_24h_records)

            # Project daily cost
            if len(last_hour_records) > 0:
                projected_daily_cost = (last_hour_cost / len(last_hour_records)) * 24 * (total_requests / 24)
            else:
                projected_daily_cost = last_24h_cost

            # Calculate efficiency score (lower cost per request = higher score)
            max_cost_per_request = 0.1  # $0.10 as reference point
            efficiency_score = max(0, 1 - (average_cost / max_cost_per_request))

            # Calculate cost trend
            cost_trend = await self._calculate_cost_trend(provider)

            return CostMetrics(
                provider=provider,
                total_requests=total_requests,
                total_cost=total_cost,
                average_cost_per_request=average_cost,
                cost_efficiency_score=efficiency_score,
                cost_trend=cost_trend,
                last_hour_cost=last_hour_cost,
                last_24h_cost=last_24h_cost,
                projected_daily_cost=projected_daily_cost,
            )

        except Exception as e:
            logger.error(f"Failed to get cost metrics for {provider}: {e}")
            return None

    async def get_cost_efficient_provider_ranking(self) -> list[dict[str, Any]]:
        """Get providers ranked by cost efficiency"""
        try:
            rankings = []

            for provider in self.cost_history.keys():
                metrics = await self.get_cost_metrics(provider)
                if metrics:
                    rankings.append(
                        {
                            "provider": provider,
                            "efficiency_score": metrics.cost_efficiency_score,
                            "average_cost": metrics.average_cost_per_request,
                            "total_cost": metrics.total_cost,
                            "trend": metrics.cost_trend,
                        }
                    )

            # Sort by efficiency score (highest first)
            rankings.sort(key=lambda x: x["efficiency_score"], reverse=True)

            return rankings

        except Exception as e:
            logger.error(f"Failed to get cost rankings: {e}")
            return []

    def _check_budget_limits(self, budget: CostBudget, estimated_cost: float) -> dict[str, Any]:
        """Check if request would exceed budget limits"""
        projected_spending = budget.current_spent + estimated_cost
        utilization = projected_spending / budget.limit if budget.limit > 0 else 0

        # Check hard limit
        if budget.hard_limit and projected_spending > budget.limit:
            return {
                "allowed": False,
                "reason": CostBreakingReason.BUDGET_EXCEEDED.value,
                "budget_limit": budget.limit,
                "current_spent": budget.current_spent,
                "estimated_cost": estimated_cost,
                "projected_spending": projected_spending,
                "utilization": utilization,
            }

        # Check alert thresholds
        for threshold in budget.alert_thresholds:
            if utilization >= threshold:
                # Create alert but allow request
                asyncio.create_task(
                    self._create_cost_alert(
                        budget.provider,
                        CostBreakingReason.BUDGET_EXCEEDED,
                        f"Budget {threshold:.0%} threshold exceeded",
                        estimated_cost,
                        utilization,
                    )
                )
                break

        return {
            "allowed": True,
            "budget_limit": budget.limit,
            "current_spent": budget.current_spent,
            "estimated_cost": estimated_cost,
            "utilization": utilization,
        }

    async def _check_cost_spike(self, provider: str, estimated_cost: float) -> dict[str, Any]:
        """Check for cost spikes compared to historical average"""
        try:
            if provider not in self.cost_history or len(self.cost_history[provider]) < 5:
                return {"spike_detected": False}

            # Calculate recent average cost
            recent_records = self.cost_history[provider][-20:]  # Last 20 requests
            recent_avg = sum(record["cost"] for record in recent_records) / len(recent_records)

            if recent_avg == 0:
                return {"spike_detected": False}

            spike_ratio = estimated_cost / recent_avg

            if spike_ratio >= self.cost_spike_threshold:
                severity = "critical" if spike_ratio >= 3.0 else "high" if spike_ratio >= 2.5 else "medium"

                self.stats["cost_spikes_detected"] += 1

                return {
                    "spike_detected": True,
                    "spike_ratio": spike_ratio,
                    "recent_average": recent_avg,
                    "estimated_cost": estimated_cost,
                    "severity": severity,
                }

            return {"spike_detected": False}

        except Exception as e:
            logger.error(f"Cost spike check failed for {provider}: {e}")
            return {"spike_detected": False}

    async def _check_cost_efficiency(self, provider: str, estimated_cost: float) -> dict[str, Any]:
        """Check if provider meets cost efficiency requirements"""
        metrics = await self.get_cost_metrics(provider)
        if not metrics:
            return {"efficient": True}  # No data, assume efficient

        if metrics.cost_efficiency_score < self.efficiency_threshold:
            return {
                "efficient": False,
                "efficiency_score": metrics.cost_efficiency_score,
                "threshold": self.efficiency_threshold,
                "average_cost": metrics.average_cost_per_request,
            }

        return {"efficient": True}

    def _calculate_italian_cost_adjustment(self, base_cost: float) -> dict[str, Any]:
        """Calculate cost adjustments based on Italian market conditions"""
        now = datetime.utcnow()
        italian_hour = (now.hour + 1) % 24  # Simplified UTC+1

        multiplier = 1.0
        reasons = []

        # Peak hours adjustment
        if 9 <= italian_hour <= 18:
            multiplier *= self.italian_cost_factors["peak_hours_multiplier"]
            reasons.append(f"Peak hours (+{(self.italian_cost_factors['peak_hours_multiplier'] - 1) * 100:.0f}%)")

        # Tax deadline periods
        if now.month in [7, 11]:
            multiplier *= self.italian_cost_factors["tax_deadline_multiplier"]
            reasons.append(
                f"Tax deadline period (+{(self.italian_cost_factors['tax_deadline_multiplier'] - 1) * 100:.0f}%)"
            )

        # August vacation discount
        elif now.month == 8:
            multiplier *= self.italian_cost_factors["vacation_discount"]
            reasons.append(f"August vacation ({(self.italian_cost_factors['vacation_discount'] - 1) * 100:.0f}%)")

        return {"multiplier": multiplier, "adjusted_cost": base_cost * multiplier, "reasons": reasons}

    async def _suggest_cost_efficient_alternatives(self, current_provider: str) -> list[dict[str, Any]]:
        """Suggest more cost-efficient alternative providers"""
        rankings = await self.get_cost_efficient_provider_ranking()

        # Filter out current provider and get top 3 alternatives
        alternatives = [
            {
                "provider": ranking["provider"],
                "efficiency_score": ranking["efficiency_score"],
                "average_cost": ranking["average_cost"],
                "cost_savings": max(
                    0, self.cost_history.get(current_provider, [{"cost": 0}])[-1]["cost"] - ranking["average_cost"]
                ),
            }
            for ranking in rankings
            if ranking["provider"] != current_provider
        ][:3]

        return alternatives

    async def _get_or_create_budget(self, provider: str) -> CostBudget:
        """Get existing budget or create default one"""
        if provider not in self.budgets:
            # Create default daily budget
            await self.set_cost_budget(provider, BudgetPeriod.DAILY, 100.0)  # $100 daily default

        budget = self.budgets[provider]

        # Check if budget period has expired
        if datetime.utcnow() > budget.period_end:
            # Reset budget for new period
            await self.set_cost_budget(
                provider, budget.period, budget.limit, budget.alert_thresholds, budget.hard_limit
            )
            budget = self.budgets[provider]

        return budget

    async def _reserve_budget(self, provider: str, cost: float):
        """Reserve budget amount for pending request"""
        budget = self.budgets.get(provider)
        if budget:
            budget.current_spent += cost

    async def _calculate_period_spending(self, provider: str, start: datetime, end: datetime) -> float:
        """Calculate spending for a specific period"""
        if provider not in self.cost_history:
            return 0.0

        period_records = [record for record in self.cost_history[provider] if start <= record["timestamp"] <= end]

        return sum(record["cost"] for record in period_records)

    async def _calculate_cost_trend(self, provider: str) -> float:
        """Calculate cost trend (-1 to 1, negative means getting more expensive)"""
        if provider not in self.cost_history or len(self.cost_history[provider]) < 10:
            return 0.0

        history = self.cost_history[provider]

        # Compare recent vs older costs
        recent_costs = [record["cost"] for record in history[-10:]]
        older_costs = [record["cost"] for record in history[-20:-10]] if len(history) >= 20 else recent_costs

        recent_avg = sum(recent_costs) / len(recent_costs)
        older_avg = sum(older_costs) / len(older_costs)

        if older_avg == 0:
            return 0.0

        # Calculate trend: negative = getting more expensive, positive = getting cheaper
        trend = (older_avg - recent_avg) / older_avg

        return max(-1.0, min(1.0, trend))

    async def _update_cost_metrics(self, provider: str):
        """Update cost metrics after recording new cost"""
        # This would update cached metrics and trigger any necessary alerts
        pass

    async def _update_provider_rankings(self):
        """Update provider cost efficiency rankings"""
        rankings = await self.get_cost_efficient_provider_ranking()
        self.provider_rankings = {
            ranking["provider"]: {"rank": i + 1, "efficiency_score": ranking["efficiency_score"]}
            for i, ranking in enumerate(rankings)
        }

    async def _create_cost_alert(
        self,
        provider: str,
        alert_type: CostBreakingReason,
        message: str,
        cost_impact: float,
        threshold_exceeded: float,
    ) -> str:
        """Create cost-related alert"""
        alert_id = str(uuid4())

        # Determine severity
        if threshold_exceeded > 2.0 or alert_type in [
            CostBreakingReason.BUDGET_EXCEEDED,
            CostBreakingReason.DAILY_LIMIT_REACHED,
        ]:
            severity = "critical"
        elif threshold_exceeded > 1.5:
            severity = "high"
        elif threshold_exceeded > 1.2:
            severity = "medium"
        else:
            severity = "low"

        # Generate recommendations
        recommendations = []
        if alert_type == CostBreakingReason.COST_SPIKE_DETECTED:
            recommendations = [
                "Review recent changes in provider pricing",
                "Consider switching to more cost-efficient provider",
                "Implement cost monitoring alerts",
            ]
        elif alert_type == CostBreakingReason.BUDGET_EXCEEDED:
            recommendations = [
                "Review budget allocation",
                "Optimize request patterns",
                "Consider provider alternatives",
            ]

        alert = CostAlert(
            id=alert_id,
            provider=provider,
            alert_type=alert_type,
            message=message,
            cost_impact=cost_impact,
            threshold_exceeded=threshold_exceeded,
            recommended_actions=recommendations,
            timestamp=datetime.utcnow(),
            severity=severity,
        )

        self.cost_alerts.append(alert)

        # Keep only recent alerts (last 100)
        if len(self.cost_alerts) > 100:
            self.cost_alerts = self.cost_alerts[-100:]

        logger.warning(f"Cost alert created: {alert_id} - {message}")

        return alert_id

    def get_active_cost_alerts(self) -> list[dict[str, Any]]:
        """Get current active cost alerts"""
        # Filter alerts from last 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        active_alerts = [alert for alert in self.cost_alerts if alert.timestamp > cutoff_time]

        return [
            {
                "id": alert.id,
                "provider": alert.provider,
                "type": alert.alert_type.value,
                "message": alert.message,
                "severity": alert.severity,
                "cost_impact": alert.cost_impact,
                "timestamp": alert.timestamp.isoformat(),
                "recommendations": alert.recommended_actions,
            }
            for alert in active_alerts
        ]

    def get_statistics(self) -> dict[str, Any]:
        """Get cost-aware circuit logic statistics"""
        total_budgets = len(self.budgets)
        active_budgets = sum(1 for budget in self.budgets.values() if budget.current_spent < budget.limit)

        return {
            "cost_stats": self.stats,
            "total_budgets": total_budgets,
            "active_budgets": active_budgets,
            "tracked_providers": len(self.cost_history),
            "active_alerts": len(self.get_active_cost_alerts()),
            "italian_cost_factors": self.italian_cost_factors,
            "thresholds": {
                "cost_spike_threshold": self.cost_spike_threshold,
                "efficiency_threshold": self.efficiency_threshold,
            },
        }
