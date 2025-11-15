#!/usr/bin/env python3
"""PratikoAI Cost Optimization Analyzer

This script analyzes metrics to identify cost optimization opportunities:
- High-cost users and usage patterns
- Inefficient API calls and caching opportunities
- LLM provider optimization suggestions
- Resource utilization improvements
- Automated recommendations with ROI estimates

Usage:
    python monitoring/scripts/optimize_costs.py
    python monitoring/scripts/optimize_costs.py --detailed
    python monitoring/scripts/optimize_costs.py --export costs_analysis.json
    python monitoring/scripts/optimize_costs.py --threshold 2.0
"""

import argparse
import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CostInsight:
    """Data class for cost optimization insights"""

    category: str
    title: str
    description: str
    current_cost: float
    potential_savings: float
    roi_estimate: str
    effort_level: str  # "low", "medium", "high"
    priority: str  # "critical", "high", "medium", "low"
    implementation_steps: list[str]


@dataclass
class UserCostAnalysis:
    """Data class for individual user cost analysis"""

    user_id: str
    monthly_cost: float
    api_calls: int
    llm_usage: dict[str, float]
    cache_hit_ratio: float
    expensive_operations: list[str]
    optimization_potential: float


@dataclass
class CostOptimizationReport:
    """Main cost optimization report"""

    analysis_date: str
    total_monthly_cost: float
    target_cost_per_user: float
    current_cost_per_user: float
    potential_monthly_savings: float
    insights: list[CostInsight]
    user_analysis: list[UserCostAnalysis]
    provider_analysis: dict[str, Any]
    recommendations_summary: list[str]


class PrometheusClient:
    """Client for querying Prometheus metrics"""

    def __init__(self, base_url: str = "http://localhost:9090"):
        self.base_url = base_url

    def query(self, query: str) -> dict[str, Any]:
        """Execute Prometheus query"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/query", params={"query": query}, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Prometheus query failed: {e}")
            return {"data": {"result": []}}

    def query_range(self, query: str, hours: int = 24) -> dict[str, Any]:
        """Execute Prometheus range query"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        try:
            response = requests.get(
                f"{self.base_url}/api/v1/query_range",
                params={"query": query, "start": start_time.timestamp(), "end": end_time.timestamp(), "step": "1h"},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Prometheus range query failed: {e}")
            return {"data": {"result": []}}


class CostOptimizationAnalyzer:
    """Main cost optimization analyzer"""

    def __init__(self, prometheus_url: str = "http://localhost:9090", target_cost_per_user: float = 2.0):
        self.prometheus = PrometheusClient(prometheus_url)
        self.target_cost_per_user = target_cost_per_user
        self.analysis_date = datetime.now().strftime("%Y-%m-%d")

    def analyze_high_cost_users(self) -> tuple[list[UserCostAnalysis], list[CostInsight]]:
        """Analyze users with highest costs"""
        logger.info("Analyzing high-cost users...")

        insights = []
        user_analyses = []

        # Get per-user costs
        user_cost_query = "user_monthly_cost_eur"
        user_cost_result = self.prometheus.query(user_cost_query)

        high_cost_users = []
        total_users = 0
        total_high_cost = 0

        for result in user_cost_result["data"]["result"]:
            user_id = result["metric"].get("user_id", "unknown")
            cost = float(result["value"][1])
            total_users += 1

            if cost > self.target_cost_per_user:
                high_cost_users.append((user_id, cost))
                total_high_cost += cost

        # Sort by cost descending
        high_cost_users.sort(key=lambda x: x[1], reverse=True)

        # Analyze top high-cost users
        for user_id, cost in high_cost_users[:10]:  # Top 10
            # Get detailed user metrics
            user_api_calls = self._get_user_api_calls(user_id)
            user_llm_usage = self._get_user_llm_usage(user_id)
            user_cache_ratio = self._get_user_cache_ratio(user_id)
            expensive_ops = self._get_user_expensive_operations(user_id)

            optimization_potential = max(0, cost - self.target_cost_per_user)

            user_analysis = UserCostAnalysis(
                user_id=user_id,
                monthly_cost=cost,
                api_calls=user_api_calls,
                llm_usage=user_llm_usage,
                cache_hit_ratio=user_cache_ratio,
                expensive_operations=expensive_ops,
                optimization_potential=optimization_potential,
            )
            user_analyses.append(user_analysis)

        # Generate insights
        if len(high_cost_users) > 0:
            avg_high_cost = total_high_cost / len(high_cost_users)
            potential_savings = sum(max(0, cost - self.target_cost_per_user) for _, cost in high_cost_users)

            insight = CostInsight(
                category="User Optimization",
                title=f"{len(high_cost_users)} Users Exceed €{self.target_cost_per_user} Target",
                description=f"Users with average cost of €{avg_high_cost:.2f} could be optimized through usage limits or feature restrictions.",
                current_cost=total_high_cost,
                potential_savings=potential_savings,
                roi_estimate="High - Direct cost reduction",
                effort_level="medium",
                priority="high" if len(high_cost_users) > total_users * 0.1 else "medium",
                implementation_steps=[
                    "Implement per-user usage quotas",
                    "Add cost-aware feature limiting",
                    "Offer tiered pricing with usage limits",
                    "Provide usage dashboards to users",
                ],
            )
            insights.append(insight)

        return user_analyses, insights

    def analyze_caching_opportunities(self) -> list[CostInsight]:
        """Analyze caching optimization opportunities"""
        logger.info("Analyzing caching opportunities...")

        insights = []

        # Get cache hit ratios by type
        cache_ratio_query = "cache_hit_ratio"
        cache_result = self.prometheus.query(cache_ratio_query)

        low_cache_types = []
        for result in cache_result["data"]["result"]:
            cache_type = result["metric"].get("cache_type", "unknown")
            hit_ratio = float(result["value"][1])

            if hit_ratio < 0.7:  # Less than 70% hit ratio
                low_cache_types.append((cache_type, hit_ratio))

        if low_cache_types:
            # Estimate cost impact of poor caching
            total_requests_query = "sum(rate(http_request_duration_seconds_count[24h])) * 86400"
            requests_result = self.prometheus.query(total_requests_query)
            daily_requests = 0
            if requests_result["data"]["result"]:
                daily_requests = int(float(requests_result["data"]["result"][0]["value"][1]))

            # Estimate cache miss cost (assuming €0.01 per LLM call)
            cache_miss_cost = 0
            for cache_type, hit_ratio in low_cache_types:
                miss_ratio = 1 - hit_ratio
                estimated_daily_cost = (daily_requests * miss_ratio * 0.01) / len(low_cache_types)
                cache_miss_cost += estimated_daily_cost

            monthly_cache_miss_cost = cache_miss_cost * 30
            potential_savings = monthly_cache_miss_cost * 0.5  # 50% improvement assumption

            insight = CostInsight(
                category="Caching Optimization",
                title="Poor Cache Performance Increasing Costs",
                description=f"Cache types with low hit ratios: {', '.join([f'{ct} ({hr:.1%})' for ct, hr in low_cache_types])}",
                current_cost=monthly_cache_miss_cost,
                potential_savings=potential_savings,
                roi_estimate="High - Immediate cost reduction",
                effort_level="low",
                priority="high",
                implementation_steps=[
                    "Increase cache memory allocation",
                    "Optimize cache key strategies",
                    "Implement cache pre-warming",
                    "Review cache TTL settings",
                ],
            )
            insights.append(insight)

        return insights

    def analyze_llm_provider_optimization(self) -> tuple[dict[str, Any], list[CostInsight]]:
        """Analyze LLM provider costs and optimization opportunities"""
        logger.info("Analyzing LLM provider costs...")

        insights = []

        # Get costs by provider
        provider_cost_query = "sum by (provider) (increase(llm_cost_total_eur[24h]))"
        provider_result = self.prometheus.query(provider_cost_query)

        provider_costs = {}
        total_daily_cost = 0

        for result in provider_result["data"]["result"]:
            provider = result["metric"]["provider"]
            daily_cost = float(result["value"][1])
            provider_costs[provider] = daily_cost
            total_daily_cost += daily_cost

        # Get API calls by provider
        provider_calls_query = "sum by (provider) (increase(api_calls_total[24h]))"
        calls_result = self.prometheus.query(provider_calls_query)

        provider_calls = {}
        for result in calls_result["data"]["result"]:
            provider = result["metric"]["provider"]
            calls = int(float(result["value"][1]))
            provider_calls[provider] = calls

        # Analyze cost per call by provider
        provider_analysis = {}
        most_expensive_provider = None
        max_cost_per_call = 0

        for provider in provider_costs:
            cost = provider_costs[provider]
            calls = provider_calls.get(provider, 1)
            cost_per_call = cost / calls if calls > 0 else 0

            provider_analysis[provider] = {
                "daily_cost": cost,
                "daily_calls": calls,
                "cost_per_call": cost_per_call,
                "percentage_of_total": (cost / total_daily_cost * 100) if total_daily_cost > 0 else 0,
            }

            if cost_per_call > max_cost_per_call:
                max_cost_per_call = cost_per_call
                most_expensive_provider = provider

        # Generate provider optimization insights
        if len(provider_costs) > 1 and most_expensive_provider:
            cheapest_cost_per_call = min(
                p["cost_per_call"] for p in provider_analysis.values() if p["cost_per_call"] > 0
            )
            potential_savings_per_call = max_cost_per_call - cheapest_cost_per_call

            expensive_calls = provider_analysis[most_expensive_provider]["daily_calls"]
            potential_daily_savings = expensive_calls * potential_savings_per_call
            potential_monthly_savings = potential_daily_savings * 30

            if potential_monthly_savings > 10:  # Only if significant savings
                insight = CostInsight(
                    category="Provider Optimization",
                    title=f"Switch from {most_expensive_provider} to Cheaper Provider",
                    description=f"{most_expensive_provider} costs €{max_cost_per_call:.4f} per call vs €{cheapest_cost_per_call:.4f} for cheapest option",
                    current_cost=provider_costs[most_expensive_provider] * 30,
                    potential_savings=potential_monthly_savings,
                    roi_estimate="Medium - Requires testing for quality",
                    effort_level="medium",
                    priority="medium",
                    implementation_steps=[
                        f"Test quality of cheaper provider for {most_expensive_provider} use cases",
                        "Implement gradual rollout (A/B testing)",
                        "Monitor response quality metrics",
                        "Adjust provider routing based on use case",
                    ],
                )
                insights.append(insight)

        # Check for model optimization within providers
        model_cost_query = "sum by (provider, model) (increase(llm_cost_total_eur[24h]))"
        model_result = self.prometheus.query(model_cost_query)

        model_usage = defaultdict(list)
        for result in model_result["data"]["result"]:
            provider = result["metric"]["provider"]
            model = result["metric"]["model"]
            cost = float(result["value"][1])
            model_usage[provider].append((model, cost))

        # Look for expensive model usage that could be optimized
        for provider, models in model_usage.items():
            if len(models) > 1:
                models.sort(key=lambda x: x[1], reverse=True)  # Sort by cost
                most_expensive_model, expensive_cost = models[0]
                cheapest_model, cheap_cost = models[-1]

                if expensive_cost > cheap_cost * 2:  # If most expensive is 2x+ more than cheapest
                    potential_savings = (expensive_cost - cheap_cost) * 0.5 * 30  # 50% migration assumption

                    if potential_savings > 5:  # Only if meaningful savings
                        insight = CostInsight(
                            category="Model Optimization",
                            title=f"Optimize {provider} Model Usage",
                            description=f"Consider using {cheapest_model} instead of {most_expensive_model} for appropriate use cases",
                            current_cost=expensive_cost * 30,
                            potential_savings=potential_savings,
                            roi_estimate="High - Direct cost reduction",
                            effort_level="low",
                            priority="medium",
                            implementation_steps=[
                                "Identify use cases suitable for cheaper model",
                                "Implement model selection logic",
                                "A/B test quality vs cost trade-offs",
                                "Monitor user satisfaction metrics",
                            ],
                        )
                        insights.append(insight)

        return provider_analysis, insights

    def analyze_inefficient_api_usage(self) -> list[CostInsight]:
        """Analyze inefficient API usage patterns"""
        logger.info("Analyzing API usage efficiency...")

        insights = []

        # Find endpoints with high error rates (wasted costs)
        error_rate_query = """
        (rate(api_errors_total[24h]) / rate(http_request_duration_seconds_count[24h])) * 100
        """
        error_result = self.prometheus.query(error_rate_query)

        high_error_endpoints = []
        for result in error_result["data"]["result"]:
            endpoint = result["metric"].get("endpoint", "unknown")
            error_rate = float(result["value"][1])

            if error_rate > 5:  # More than 5% error rate
                high_error_endpoints.append((endpoint, error_rate))

        if high_error_endpoints:
            # Estimate wasted costs from errors
            total_errors_query = "sum(increase(api_errors_total[24h]))"
            errors_result = self.prometheus.query(total_errors_query)
            daily_errors = 0
            if errors_result["data"]["result"]:
                daily_errors = int(float(errors_result["data"]["result"][0]["value"][1]))

            # Assume each error costs €0.005 (partial LLM cost)
            daily_error_cost = daily_errors * 0.005
            monthly_error_cost = daily_error_cost * 30

            insight = CostInsight(
                category="API Efficiency",
                title="High Error Rates Causing Wasted Costs",
                description=f"Endpoints with high error rates: {', '.join([f'{ep} ({er:.1f}%)' for ep, er in high_error_endpoints])}",
                current_cost=monthly_error_cost,
                potential_savings=monthly_error_cost * 0.8,  # 80% error reduction
                roi_estimate="High - Direct waste elimination",
                effort_level="medium",
                priority="high" if daily_errors > 100 else "medium",
                implementation_steps=[
                    "Add request validation to prevent errors",
                    "Implement retry logic with exponential backoff",
                    "Add circuit breakers for failing services",
                    "Improve error handling and user guidance",
                ],
            )
            insights.append(insight)

        # Find slow endpoints that might benefit from optimization
        slow_endpoints_query = """
        topk(5, histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[24h])))
        """
        slow_result = self.prometheus.query(slow_endpoints_query)

        very_slow_endpoints = []
        for result in slow_result["data"]["result"]:
            endpoint = result["metric"].get("endpoint", "unknown")
            p95_time = float(result["value"][1])

            if p95_time > 10:  # Slower than 10 seconds
                very_slow_endpoints.append((endpoint, p95_time))

        if very_slow_endpoints:
            insight = CostInsight(
                category="Performance Optimization",
                title="Slow Endpoints Increasing Resource Costs",
                description=f"Very slow endpoints: {', '.join([f'{ep} ({t:.1f}s)' for ep, t in very_slow_endpoints])}",
                current_cost=0,  # Hard to quantify directly
                potential_savings=50,  # Estimated infrastructure savings
                roi_estimate="Medium - Infrastructure cost reduction",
                effort_level="high",
                priority="medium",
                implementation_steps=[
                    "Profile slow endpoints to identify bottlenecks",
                    "Implement database query optimization",
                    "Add caching for expensive operations",
                    "Consider async processing for long operations",
                ],
            )
            insights.append(insight)

        return insights

    def analyze_resource_utilization(self) -> list[CostInsight]:
        """Analyze resource utilization for optimization"""
        logger.info("Analyzing resource utilization...")

        insights = []

        # Check database connection efficiency
        db_conn_query = "database_connections_active / database_connections_total"
        db_result = self.prometheus.query(db_conn_query)

        if db_result["data"]["result"]:
            db_utilization = float(db_result["data"]["result"][0]["value"][1])

            if db_utilization < 0.3:  # Less than 30% utilization
                insight = CostInsight(
                    category="Resource Optimization",
                    title="Database Connection Pool Over-Provisioned",
                    description=f"Database connection utilization is only {db_utilization:.1%}, suggesting over-provisioning",
                    current_cost=0,  # Infrastructure cost
                    potential_savings=20,  # Estimated monthly savings
                    roi_estimate="Low - Infrastructure optimization",
                    effort_level="low",
                    priority="low",
                    implementation_steps=[
                        "Reduce database connection pool size",
                        "Monitor for any performance impact",
                        "Adjust based on peak usage patterns",
                    ],
                )
                insights.append(insight)

        # Check Redis memory usage efficiency
        redis_memory_query = "redis_memory_usage_bytes"
        redis_result = self.prometheus.query(redis_memory_query)

        if redis_result["data"]["result"]:
            redis_memory = float(redis_result["data"]["result"][0]["value"][1])
            redis_memory_mb = redis_memory / 1024 / 1024

            # If using less than 100MB, might be under-utilizing caching
            if redis_memory_mb < 100:
                insight = CostInsight(
                    category="Caching Strategy",
                    title="Under-Utilizing Redis Cache",
                    description=f"Redis memory usage is only {redis_memory_mb:.1f}MB, suggesting missed caching opportunities",
                    current_cost=0,
                    potential_savings=30,  # From better caching
                    roi_estimate="Medium - Reduced LLM calls",
                    effort_level="medium",
                    priority="medium",
                    implementation_steps=[
                        "Identify frequently requested data for caching",
                        "Implement application-level caching strategy",
                        "Cache expensive LLM responses",
                        "Add cache warming for popular queries",
                    ],
                )
                insights.append(insight)

        return insights

    def _get_user_api_calls(self, user_id: str) -> int:
        """Get API call count for a specific user"""
        query = f'sum(increase(http_request_duration_seconds_count{{user_id="{user_id}"}}[24h]))'
        result = self.prometheus.query(query)
        if result["data"]["result"]:
            return int(float(result["data"]["result"][0]["value"][1]))
        return 0

    def _get_user_llm_usage(self, user_id: str) -> dict[str, float]:
        """Get LLM usage breakdown for a specific user"""
        query = f'sum by (provider) (increase(llm_cost_total_eur{{user_id="{user_id}"}}[24h]))'
        result = self.prometheus.query(query)

        usage = {}
        for r in result["data"]["result"]:
            provider = r["metric"]["provider"]
            cost = float(r["value"][1])
            usage[provider] = cost

        return usage

    def _get_user_cache_ratio(self, user_id: str) -> float:
        """Get cache hit ratio for a specific user"""
        # This would require user-specific cache metrics
        # For now, return overall cache ratio
        query = "avg(cache_hit_ratio)"
        result = self.prometheus.query(query)
        if result["data"]["result"]:
            return float(result["data"]["result"][0]["value"][1])
        return 0.0

    def _get_user_expensive_operations(self, user_id: str) -> list[str]:
        """Get list of expensive operations for a user"""
        # This would require detailed operation tracking
        # For now, return placeholder
        return ["document_processing", "tax_calculation", "llm_query"]

    def generate_report(self, detailed: bool = False) -> CostOptimizationReport:
        """Generate complete cost optimization report"""
        logger.info("Generating cost optimization report...")

        all_insights = []

        # Get current cost metrics
        total_cost_query = "sum(user_monthly_cost_eur)"
        total_cost_result = self.prometheus.query(total_cost_query)
        total_monthly_cost = 0.0
        if total_cost_result["data"]["result"]:
            total_monthly_cost = float(total_cost_result["data"]["result"][0]["value"][1])

        avg_cost_query = "avg(user_monthly_cost_eur)"
        avg_cost_result = self.prometheus.query(avg_cost_query)
        current_cost_per_user = 0.0
        if avg_cost_result["data"]["result"]:
            current_cost_per_user = float(avg_cost_result["data"]["result"][0]["value"][1])

        # Run all analyses
        user_analyses, user_insights = self.analyze_high_cost_users()
        all_insights.extend(user_insights)

        cache_insights = self.analyze_caching_opportunities()
        all_insights.extend(cache_insights)

        provider_analysis, provider_insights = self.analyze_llm_provider_optimization()
        all_insights.extend(provider_insights)

        api_insights = self.analyze_inefficient_api_usage()
        all_insights.extend(api_insights)

        resource_insights = self.analyze_resource_utilization()
        all_insights.extend(resource_insights)

        # Calculate total potential savings
        potential_monthly_savings = sum(insight.potential_savings for insight in all_insights)

        # Generate summary recommendations
        recommendations = self._generate_recommendations_summary(all_insights)

        # Include detailed user analysis only if requested
        if not detailed:
            user_analyses = user_analyses[:5]  # Top 5 users only

        return CostOptimizationReport(
            analysis_date=self.analysis_date,
            total_monthly_cost=total_monthly_cost,
            target_cost_per_user=self.target_cost_per_user,
            current_cost_per_user=current_cost_per_user,
            potential_monthly_savings=potential_monthly_savings,
            insights=all_insights,
            user_analysis=user_analyses,
            provider_analysis=provider_analysis,
            recommendations_summary=recommendations,
        )

    def _generate_recommendations_summary(self, insights: list[CostInsight]) -> list[str]:
        """Generate prioritized recommendations summary"""
        recommendations = []

        # Sort insights by priority and potential savings
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        sorted_insights = sorted(
            insights, key=lambda x: (priority_order.get(x.priority, 0), x.potential_savings), reverse=True
        )

        for insight in sorted_insights[:5]:  # Top 5 recommendations
            saving_text = (
                f"€{insight.potential_savings:.0f}/month" if insight.potential_savings > 0 else "Cost optimization"
            )
            recommendations.append(f"[{insight.priority.upper()}] {insight.title} - Potential savings: {saving_text}")

        if not recommendations:
            recommendations.append("✅ Cost optimization is already well-implemented. Continue monitoring.")

        return recommendations


def format_report(report: CostOptimizationReport, detailed: bool = False) -> str:
    """Format the cost optimization report"""
    output = f"""
PratikoAI Cost Optimization Analysis - {report.analysis_date}
{"=" * 60}

💰 COST OVERVIEW
Current monthly cost: €{report.total_monthly_cost:.2f}
Current cost per user: €{report.current_cost_per_user:.2f}
Target cost per user: €{report.target_cost_per_user:.2f}
Potential monthly savings: €{report.potential_monthly_savings:.2f}
Cost efficiency: {((report.target_cost_per_user / max(report.current_cost_per_user, 0.01)) * 100):.1f}%

🎯 PRIORITY RECOMMENDATIONS
"""

    for i, rec in enumerate(report.recommendations_summary, 1):
        output += f"{i}. {rec}\n"

    output += f"\n💡 OPTIMIZATION INSIGHTS ({len(report.insights)} found)\n"
    output += "-" * 40 + "\n"

    for insight in report.insights:
        priority_icon = {"critical": "🔴", "high": "🟡", "medium": "🔵", "low": "⚪"}.get(insight.priority, "⚪")
        savings_text = f"€{insight.potential_savings:.0f}/month" if insight.potential_savings > 0 else "TBD"

        output += f"""
{priority_icon} {insight.title} [{insight.category}]
   Description: {insight.description}
   Potential Savings: {savings_text}
   ROI: {insight.roi_estimate}
   Effort: {insight.effort_level}

   Implementation Steps:
"""
        for step in insight.implementation_steps:
            output += f"   • {step}\n"

    if detailed and report.user_analysis:
        output += f"\n👥 HIGH-COST USER ANALYSIS ({len(report.user_analysis)} users)\n"
        output += "-" * 40 + "\n"

        for user in report.user_analysis:
            output += f"""
User: {user.user_id}
Monthly Cost: €{user.monthly_cost:.2f} (€{user.optimization_potential:.2f} over target)
API Calls: {user.api_calls:,}
Cache Hit Ratio: {user.cache_hit_ratio:.1%}
LLM Usage: {", ".join([f"{p}: €{c:.2f}" for p, c in user.llm_usage.items()])}
Expensive Operations: {", ".join(user.expensive_operations)}
"""

    if report.provider_analysis:
        output += "\n🤖 LLM PROVIDER ANALYSIS\n"
        output += "-" * 40 + "\n"

        for provider, analysis in report.provider_analysis.items():
            output += f"""
{provider}:
  Daily Cost: €{analysis["daily_cost"]:.2f} ({analysis["percentage_of_total"]:.1f}% of total)
  Daily Calls: {analysis["daily_calls"]:,}
  Cost per Call: €{analysis["cost_per_call"]:.4f}
"""

    output += "\nGenerated by PratikoAI Cost Optimization Analyzer"
    return output


def main():
    parser = argparse.ArgumentParser(description="Analyze PratikoAI cost optimization opportunities")
    parser.add_argument("--detailed", action="store_true", help="Include detailed user analysis")
    parser.add_argument("--export", help="Export report to JSON file")
    parser.add_argument("--threshold", type=float, default=2.0, help="Target cost per user threshold")
    parser.add_argument("--prometheus-url", default="http://localhost:9090", help="Prometheus URL")

    args = parser.parse_args()

    # Generate report
    analyzer = CostOptimizationAnalyzer(args.prometheus_url, args.threshold)
    report = analyzer.generate_report(args.detailed)

    # Display report
    print(format_report(report, args.detailed))

    # Export if requested
    if args.export:
        with open(args.export, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, default=str)
        logger.info(f"Report exported to {args.export}")


if __name__ == "__main__":
    main()
