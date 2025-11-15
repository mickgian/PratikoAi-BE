"""Provider Health Scoring System for Advanced Circuit Breakers.

Provides sophisticated health scoring algorithms for provider performance assessment
and predictive failure detection for Italian tax compliance services.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import logger
from app.services.cache import CacheService


class HealthStatus(Enum):
    """Health status levels"""

    EXCELLENT = "excellent"  # 0.9-1.0
    GOOD = "good"  # 0.7-0.89
    WARNING = "warning"  # 0.5-0.69
    CRITICAL = "critical"  # 0.3-0.49
    FAILING = "failing"  # 0.0-0.29


@dataclass
class HealthMetrics:
    """Health metrics data structure"""

    success_rate: float
    average_response_time: float
    error_rate: float
    availability: float
    cost_efficiency: float
    trend_direction: float  # -1 to 1, negative is declining
    prediction_confidence: float


@dataclass
class ProviderHealthScore:
    """Complete provider health assessment"""

    provider: str
    overall_score: float
    status: HealthStatus
    metrics: HealthMetrics
    predictions: dict[str, Any]
    recommendations: list[str]
    last_updated: datetime
    italian_market_factors: dict[str, float]


class ProviderHealthScorer:
    """Advanced provider health scoring system"""

    def __init__(self, cache: CacheService | None = None):
        self.cache = cache
        self.health_history = {}  # provider -> list of health records
        self.cache_ttl = 300  # 5 minutes

        # Italian market weights
        self.italian_weights = {
            "peak_hours_performance": 0.25,
            "tax_deadline_reliability": 0.20,
            "regulatory_accuracy": 0.15,
            "regional_responsiveness": 0.10,
            "vacation_adaptability": 0.10,
            "compliance_track_record": 0.20,
        }

        # Health score thresholds
        self.status_thresholds = {
            HealthStatus.EXCELLENT: (0.9, 1.0),
            HealthStatus.GOOD: (0.7, 0.9),
            HealthStatus.WARNING: (0.5, 0.7),
            HealthStatus.CRITICAL: (0.3, 0.5),
            HealthStatus.FAILING: (0.0, 0.3),
        }

    async def calculate_health_score(
        self, provider: str, recent_metrics: dict[str, Any], historical_data: list[dict[str, Any]] | None = None
    ) -> ProviderHealthScore:
        """Calculate comprehensive health score for a provider"""
        try:
            # Extract current metrics
            current_metrics = self._extract_health_metrics(recent_metrics)

            # Calculate base health score
            base_score = self._calculate_base_score(current_metrics)

            # Apply trend analysis
            trend_adjustment = await self._calculate_trend_adjustment(provider, historical_data or [])

            # Apply Italian market factors
            italian_adjustment = self._calculate_italian_market_adjustment(provider, current_metrics)

            # Calculate final score
            final_score = min(1.0, max(0.0, base_score + trend_adjustment + italian_adjustment))

            # Determine status
            status = self._determine_status(final_score)

            # Generate predictions
            predictions = await self._generate_health_predictions(provider, current_metrics, historical_data or [])

            # Generate recommendations
            recommendations = self._generate_recommendations(provider, current_metrics, final_score)

            # Store in history
            await self._update_health_history(provider, final_score, current_metrics)

            health_score = ProviderHealthScore(
                provider=provider,
                overall_score=final_score,
                status=status,
                metrics=current_metrics,
                predictions=predictions,
                recommendations=recommendations,
                last_updated=datetime.utcnow(),
                italian_market_factors=italian_adjustment,
            )

            # Cache the result
            if self.cache:
                cache_key = f"health_score:{provider}"
                await self.cache.setex(cache_key, self.cache_ttl, health_score.__dict__)

            return health_score

        except Exception as e:
            logger.error(f"Health score calculation failed for {provider}: {e}")
            # Return default health score
            return ProviderHealthScore(
                provider=provider,
                overall_score=0.5,
                status=HealthStatus.WARNING,
                metrics=HealthMetrics(0.5, 1000, 0.5, 0.5, 0.5, 0.0, 0.0),
                predictions={"error": str(e)},
                recommendations=["Health scoring failed - manual review required"],
                last_updated=datetime.utcnow(),
                italian_market_factors={},
            )

    def _extract_health_metrics(self, metrics: dict[str, Any]) -> HealthMetrics:
        """Extract and normalize health metrics from raw data"""
        total_requests = metrics.get("total_requests", 1)
        success_count = metrics.get("success_count", 0)
        failure_count = metrics.get("failure_count", 0)

        # Calculate success rate
        success_rate = success_count / max(total_requests, 1)

        # Calculate error rate
        error_rate = failure_count / max(total_requests, 1)

        # Extract response time (normalize to 0-1 scale, where 1000ms = 0.5)
        avg_response_time = metrics.get("average_response_time", 500)
        response_time_score = max(0, 1.0 - (avg_response_time / 2000))  # 2000ms = 0 score

        # Calculate availability (uptime percentage)
        availability = metrics.get("availability", 1.0)

        # Calculate cost efficiency (lower cost per request = higher score)
        cost_per_request = metrics.get("cost_per_request", 0.01)
        cost_efficiency = max(0, 1.0 - min(cost_per_request / 0.05, 1.0))  # $0.05 per request = 0 score

        # Trend direction (from historical analysis)
        trend_direction = metrics.get("trend_direction", 0.0)

        # Prediction confidence
        prediction_confidence = metrics.get("prediction_confidence", 0.5)

        return HealthMetrics(
            success_rate=success_rate,
            average_response_time=response_time_score,
            error_rate=1.0 - error_rate,  # Invert so higher is better
            availability=availability,
            cost_efficiency=cost_efficiency,
            trend_direction=trend_direction,
            prediction_confidence=prediction_confidence,
        )

    def _calculate_base_score(self, metrics: HealthMetrics) -> float:
        """Calculate base health score from metrics"""
        # Weight different aspects of health
        weights = {
            "success_rate": 0.30,
            "response_time": 0.25,
            "error_handling": 0.20,
            "availability": 0.15,
            "cost_efficiency": 0.10,
        }

        base_score = (
            metrics.success_rate * weights["success_rate"]
            + metrics.average_response_time * weights["response_time"]
            + metrics.error_rate * weights["error_handling"]
            + metrics.availability * weights["availability"]
            + metrics.cost_efficiency * weights["cost_efficiency"]
        )

        return base_score

    async def _calculate_trend_adjustment(self, provider: str, historical_data: list[dict[str, Any]]) -> float:
        """Calculate trend-based adjustment to health score"""
        if len(historical_data) < 3:
            return 0.0  # Not enough data for trend analysis

        try:
            # Extract recent scores from history
            recent_scores = []
            for record in historical_data[-10:]:  # Last 10 records
                metrics = self._extract_health_metrics(record)
                score = self._calculate_base_score(metrics)
                recent_scores.append(score)

            if len(recent_scores) < 3:
                return 0.0

            # Calculate trend using simple linear regression slope
            n = len(recent_scores)
            x_values = list(range(n))

            # Calculate slope (trend direction)
            x_mean = sum(x_values) / n
            y_mean = sum(recent_scores) / n

            numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, recent_scores, strict=False))
            denominator = sum((x - x_mean) ** 2 for x in x_values)

            if denominator == 0:
                return 0.0

            slope = numerator / denominator

            # Convert slope to adjustment (-0.1 to +0.1)
            trend_adjustment = max(-0.1, min(0.1, slope * 0.5))

            return trend_adjustment

        except Exception as e:
            logger.error(f"Trend calculation failed for {provider}: {e}")
            return 0.0

    def _calculate_italian_market_adjustment(self, provider: str, metrics: HealthMetrics) -> dict[str, float]:
        """Calculate Italian market-specific adjustments"""
        adjustments = {}
        total_adjustment = 0.0

        # Peak hours performance (9 AM - 6 PM Italian time)
        now = datetime.utcnow()
        italian_hour = (now.hour + 1) % 24  # Simplified UTC+1

        if 9 <= italian_hour <= 18:  # Italian business hours
            peak_performance = metrics.success_rate * metrics.availability
            if peak_performance > 0.9:
                adjustment = 0.05
            elif peak_performance < 0.7:
                adjustment = -0.05
            else:
                adjustment = 0.0

            adjustments["peak_hours"] = adjustment
            total_adjustment += adjustment

        # Tax deadline period (July, November)
        if now.month in [7, 11]:
            deadline_performance = metrics.success_rate * (1 - metrics.error_rate)
            if deadline_performance > 0.95:
                adjustment = 0.03
            elif deadline_performance < 0.8:
                adjustment = -0.07
            else:
                adjustment = 0.0

            adjustments["tax_deadline"] = adjustment
            total_adjustment += adjustment

        # August vacation period - more lenient scoring
        if now.month == 8:
            adjustments["vacation_leniency"] = 0.02
            total_adjustment += 0.02

        # Regional responsiveness (simulated based on provider)
        if "italy" in provider.lower() or "italian" in provider.lower():
            adjustments["regional_bonus"] = 0.02
            total_adjustment += 0.02

        # Cost efficiency in Italian context
        if metrics.cost_efficiency > 0.8:
            adjustments["cost_efficiency"] = 0.02
            total_adjustment += 0.02

        adjustments["total"] = total_adjustment
        return adjustments

    def _determine_status(self, score: float) -> HealthStatus:
        """Determine health status from score"""
        for status, (min_score, max_score) in self.status_thresholds.items():
            if min_score <= score < max_score:
                return status

        return HealthStatus.EXCELLENT if score >= 0.9 else HealthStatus.FAILING

    async def _generate_health_predictions(
        self, provider: str, current_metrics: HealthMetrics, historical_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate health predictions and forecasts"""
        predictions = {
            "next_hour_reliability": 0.85,  # Default prediction
            "peak_load_performance": 0.80,
            "failure_probability": 0.15,
            "recommended_actions": [],
            "confidence": current_metrics.prediction_confidence,
        }

        try:
            # Predict next hour reliability based on trend
            if current_metrics.trend_direction > 0:
                predictions["next_hour_reliability"] = min(0.99, current_metrics.success_rate + 0.05)
            elif current_metrics.trend_direction < -0.1:
                predictions["next_hour_reliability"] = max(0.5, current_metrics.success_rate - 0.1)
            else:
                predictions["next_hour_reliability"] = current_metrics.success_rate

            # Predict peak load performance
            if current_metrics.availability > 0.95 and current_metrics.average_response_time > 0.8:
                predictions["peak_load_performance"] = 0.9
            elif current_metrics.availability < 0.8:
                predictions["peak_load_performance"] = 0.6
            else:
                predictions["peak_load_performance"] = 0.8

            # Calculate failure probability
            failure_indicators = [
                current_metrics.success_rate < 0.8,
                current_metrics.error_rate < 0.7,  # Remember this is inverted
                current_metrics.availability < 0.9,
                current_metrics.trend_direction < -0.05,
            ]

            failure_probability = sum(failure_indicators) * 0.2  # 20% per indicator
            predictions["failure_probability"] = min(0.8, failure_probability)

            # Generate recommended actions
            if failure_probability > 0.3:
                predictions["recommended_actions"].append("Consider failover preparation")

            if current_metrics.average_response_time < 0.6:
                predictions["recommended_actions"].append("Monitor response time degradation")

            if current_metrics.cost_efficiency < 0.5:
                predictions["recommended_actions"].append("Review cost optimization")

        except Exception as e:
            logger.error(f"Prediction generation failed for {provider}: {e}")
            predictions["error"] = str(e)

        return predictions

    def _generate_recommendations(self, provider: str, metrics: HealthMetrics, score: float) -> list[str]:
        """Generate actionable recommendations based on health assessment"""
        recommendations = []

        # Performance recommendations
        if metrics.success_rate < 0.8:
            recommendations.append("Investigate and address high failure rate")

        if metrics.average_response_time < 0.6:
            recommendations.append("Optimize response time performance")

        if metrics.availability < 0.9:
            recommendations.append("Improve service availability and uptime")

        if metrics.cost_efficiency < 0.5:
            recommendations.append("Review and optimize cost efficiency")

        # Italian market specific recommendations
        now = datetime.utcnow()
        if now.month in [7, 11] and score < 0.8:
            recommendations.append("Prepare for increased tax deadline demand")

        if 9 <= (now.hour + 1) % 24 <= 18 and metrics.success_rate < 0.85:
            recommendations.append("Focus on peak hour performance optimization")

        # Trend-based recommendations
        if metrics.trend_direction < -0.05:
            recommendations.append("Address declining performance trend")

        # Overall health recommendations
        if score < 0.5:
            recommendations.append("Urgent: Implement comprehensive health recovery plan")
        elif score < 0.7:
            recommendations.append("Monitor closely and implement preventive measures")

        return recommendations[:5]  # Limit to top 5 recommendations

    async def _update_health_history(self, provider: str, score: float, metrics: HealthMetrics):
        """Update health history for trend analysis"""
        if provider not in self.health_history:
            self.health_history[provider] = []

        history_record = {
            "timestamp": datetime.utcnow(),
            "score": score,
            "success_rate": metrics.success_rate,
            "response_time": metrics.average_response_time,
            "availability": metrics.availability,
            "trend_direction": metrics.trend_direction,
        }

        self.health_history[provider].append(history_record)

        # Keep only last 100 records to prevent memory issues
        if len(self.health_history[provider]) > 100:
            self.health_history[provider] = self.health_history[provider][-100:]

    async def get_provider_health_summary(self, providers: list[str]) -> dict[str, Any]:
        """Get health summary for multiple providers"""
        summary = {
            "total_providers": len(providers),
            "health_distribution": {status.value: 0 for status in HealthStatus},
            "average_health": 0.0,
            "providers": {},
            "alerts": [],
        }

        total_score = 0.0

        for provider in providers:
            try:
                # Try to get from cache first
                health_score = None
                if self.cache:
                    cache_key = f"health_score:{provider}"
                    cached = await self.cache.get(cache_key)
                    if cached:
                        health_score = ProviderHealthScore(**cached)

                if not health_score:
                    # Calculate fresh if not cached
                    health_score = await self.calculate_health_score(provider, {"total_requests": 0})

                # Update summary
                summary["providers"][provider] = {
                    "score": health_score.overall_score,
                    "status": health_score.status.value,
                    "last_updated": health_score.last_updated.isoformat(),
                }

                summary["health_distribution"][health_score.status.value] += 1
                total_score += health_score.overall_score

                # Generate alerts for poor health
                if health_score.status in [HealthStatus.CRITICAL, HealthStatus.FAILING]:
                    summary["alerts"].append(
                        {
                            "provider": provider,
                            "status": health_score.status.value,
                            "score": health_score.overall_score,
                            "message": f"Provider {provider} has {health_score.status.value} health",
                        }
                    )

            except Exception as e:
                logger.error(f"Failed to get health summary for {provider}: {e}")
                summary["providers"][provider] = {"error": str(e)}

        if providers:
            summary["average_health"] = total_score / len(providers)

        return summary

    def get_statistics(self) -> dict[str, Any]:
        """Get health scoring system statistics"""
        return {
            "tracked_providers": len(self.health_history),
            "total_health_records": sum(len(history) for history in self.health_history.values()),
            "italian_weight_factors": self.italian_weights,
            "status_thresholds": {
                status.value: {"min": min_val, "max": max_val}
                for status, (min_val, max_val) in self.status_thresholds.items()
            },
            "cache_ttl_seconds": self.cache_ttl,
            "recent_calculations": len(self.health_history),
        }
