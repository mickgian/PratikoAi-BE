#!/usr/bin/env python3
"""PratikoAI Daily Monitoring Report Generator

This script generates comprehensive daily reports including:
- Cost analysis per user and provider
- Revenue metrics and progress toward €25k ARR
- Performance summaries and SLA compliance
- Alert summaries and resolution status
- Key recommendations for optimization

Usage:
    python monitoring/scripts/daily_report.py
    python monitoring/scripts/daily_report.py --email
    python monitoring/scripts/daily_report.py --webhook
    python monitoring/scripts/daily_report.py --format json
"""

import argparse
import json
import logging
import os
import smtplib
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MetricSummary:
    """Data class for metric summaries"""

    name: str
    current_value: float
    target_value: float | None
    trend: str  # "up", "down", "stable"
    status: str  # "good", "warning", "critical"
    unit: str = ""


@dataclass
class DailyReport:
    """Main daily report data structure"""

    date: str
    cost_summary: dict[str, Any]
    revenue_summary: dict[str, Any]
    performance_summary: dict[str, Any]
    alert_summary: dict[str, Any]
    recommendations: list[str]
    key_metrics: list[MetricSummary]


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


class DailyReportGenerator:
    """Main report generator class"""

    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus = PrometheusClient(prometheus_url)
        self.report_date = datetime.now().strftime("%Y-%m-%d")

    def get_cost_summary(self) -> dict[str, Any]:
        """Generate cost analysis summary"""
        logger.info("Generating cost summary...")

        # Average user cost
        user_cost_query = "avg(user_monthly_cost_eur)"
        user_cost_result = self.prometheus.query(user_cost_query)
        avg_user_cost = 0.0
        if user_cost_result["data"]["result"]:
            avg_user_cost = float(user_cost_result["data"]["result"][0]["value"][1])

        # Daily LLM costs
        daily_llm_query = "increase(llm_cost_total_eur[24h])"
        daily_llm_result = self.prometheus.query(daily_llm_query)
        daily_llm_cost = 0.0
        if daily_llm_result["data"]["result"]:
            daily_llm_cost = sum(float(r["value"][1]) for r in daily_llm_result["data"]["result"])

        # Cost by provider
        provider_cost_query = "sum by (provider) (increase(llm_cost_total_eur[24h]))"
        provider_result = self.prometheus.query(provider_cost_query)
        provider_costs = {}
        for result in provider_result["data"]["result"]:
            provider = result["metric"]["provider"]
            cost = float(result["value"][1])
            provider_costs[provider] = cost

        # Cost trend (compare with yesterday)
        yesterday_cost_query = "increase(llm_cost_total_eur[24h] offset 24h)"
        yesterday_result = self.prometheus.query(yesterday_cost_query)
        yesterday_cost = 0.0
        if yesterday_result["data"]["result"]:
            yesterday_cost = sum(float(r["value"][1]) for r in yesterday_result["data"]["result"])

        cost_trend = "stable"
        if daily_llm_cost > yesterday_cost * 1.1:
            cost_trend = "up"
        elif daily_llm_cost < yesterday_cost * 0.9:
            cost_trend = "down"

        return {
            "average_user_cost_eur": round(avg_user_cost, 2),
            "target_user_cost_eur": 2.00,
            "daily_llm_cost_eur": round(daily_llm_cost, 2),
            "yesterday_cost_eur": round(yesterday_cost, 2),
            "cost_trend": cost_trend,
            "cost_change_percent": round((daily_llm_cost - yesterday_cost) / max(yesterday_cost, 0.01) * 100, 1),
            "provider_breakdown": provider_costs,
            "status": "good" if avg_user_cost <= 2.0 else "warning" if avg_user_cost <= 2.5 else "critical",
        }

    def get_revenue_summary(self) -> dict[str, Any]:
        """Generate revenue and business metrics summary"""
        logger.info("Generating revenue summary...")

        # Monthly revenue
        mrr_query = "monthly_revenue_eur"
        mrr_result = self.prometheus.query(mrr_query)
        current_mrr = 0.0
        if mrr_result["data"]["result"]:
            current_mrr = float(mrr_result["data"]["result"][0]["value"][1])

        # Active subscriptions
        subs_query = 'active_subscriptions_total{status="active"}'
        subs_result = self.prometheus.query(subs_query)
        active_subs = 0
        if subs_result["data"]["result"]:
            active_subs = int(float(subs_result["data"]["result"][0]["value"][1]))

        # Payment success rate (24h)
        payment_success_query = """
        rate(payment_operations_total{status="succeeded"}[24h]) /
        rate(payment_operations_total[24h]) * 100
        """
        payment_result = self.prometheus.query(payment_success_query)
        payment_success_rate = 0.0
        if payment_result["data"]["result"]:
            payment_success_rate = float(payment_result["data"]["result"][0]["value"][1])

        # New signups (24h)
        signup_query = 'increase(active_users_total{time_window="24h"}[24h])'
        signup_result = self.prometheus.query(signup_query)
        new_signups = 0
        if signup_result["data"]["result"]:
            new_signups = int(float(signup_result["data"]["result"][0]["value"][1]))

        # Progress calculations
        mrr_progress = (current_mrr / 25000) * 100
        subs_progress = (active_subs / 50) * 100

        return {
            "monthly_revenue_eur": round(current_mrr, 2),
            "target_revenue_eur": 25000,
            "mrr_progress_percent": round(mrr_progress, 1),
            "active_subscriptions": active_subs,
            "target_subscriptions": 50,
            "subscription_progress_percent": round(subs_progress, 1),
            "payment_success_rate_percent": round(payment_success_rate, 1),
            "new_signups_24h": new_signups,
            "revenue_per_user_eur": round(current_mrr / max(active_subs, 1), 2),
            "status": "good" if mrr_progress >= 80 else "warning" if mrr_progress >= 40 else "critical",
        }

    def get_performance_summary(self) -> dict[str, Any]:
        """Generate performance and reliability summary"""
        logger.info("Generating performance summary...")

        # API response time (95th percentile)
        response_time_query = "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[24h]))"
        response_result = self.prometheus.query(response_time_query)
        p95_response_time = 0.0
        if response_result["data"]["result"]:
            p95_response_time = float(response_result["data"]["result"][0]["value"][1])

        # Cache hit ratio
        cache_query = "avg(cache_hit_ratio)"
        cache_result = self.prometheus.query(cache_query)
        avg_cache_hit = 0.0
        if cache_result["data"]["result"]:
            avg_cache_hit = float(cache_result["data"]["result"][0]["value"][1])

        # Error rate (24h)
        error_rate_query = """
        rate(api_errors_total[24h]) /
        rate(http_request_duration_seconds_count[24h]) * 100
        """
        error_result = self.prometheus.query(error_rate_query)
        error_rate = 0.0
        if error_result["data"]["result"]:
            error_rate = float(error_result["data"]["result"][0]["value"][1])

        # System uptime
        uptime_query = "up"
        uptime_result = self.prometheus.query(uptime_query)
        services_up = 0
        total_services = 0
        for result in uptime_result["data"]["result"]:
            total_services += 1
            if float(result["value"][1]) == 1:
                services_up += 1

        uptime_percent = (services_up / max(total_services, 1)) * 100

        # Request volume
        request_volume_query = "sum(rate(http_request_duration_seconds_count[24h])) * 86400"
        volume_result = self.prometheus.query(request_volume_query)
        daily_requests = 0
        if volume_result["data"]["result"]:
            daily_requests = int(float(volume_result["data"]["result"][0]["value"][1]))

        return {
            "api_response_time_p95_seconds": round(p95_response_time, 3),
            "sla_target_seconds": 5.0,
            "cache_hit_ratio_percent": round(avg_cache_hit * 100, 1),
            "cache_target_percent": 80.0,
            "error_rate_percent": round(error_rate, 2),
            "error_target_percent": 5.0,
            "system_uptime_percent": round(uptime_percent, 1),
            "daily_requests": daily_requests,
            "services_up": services_up,
            "total_services": total_services,
            "status": "good" if p95_response_time <= 5.0 and error_rate <= 5.0 else "warning",
        }

    def get_alert_summary(self) -> dict[str, Any]:
        """Generate alert status summary"""
        logger.info("Generating alert summary...")

        # Active alerts
        alerts_query = 'ALERTS{alertstate="firing"}'
        alerts_result = self.prometheus.query(alerts_query)

        active_alerts = []
        alerts_by_severity = {"critical": 0, "warning": 0, "info": 0}
        alerts_by_team = {}

        for result in alerts_result["data"]["result"]:
            metric = result["metric"]
            alert_info = {
                "name": metric.get("alertname", "Unknown"),
                "severity": metric.get("severity", "unknown"),
                "team": metric.get("team", "unknown"),
                "category": metric.get("category", "unknown"),
            }
            active_alerts.append(alert_info)

            # Count by severity
            severity = alert_info["severity"]
            if severity in alerts_by_severity:
                alerts_by_severity[severity] += 1

            # Count by team
            team = alert_info["team"]
            alerts_by_team[team] = alerts_by_team.get(team, 0) + 1

        # Alert frequency (last 24h)
        alert_freq_query = "increase(prometheus_notifications_total[24h])"
        freq_result = self.prometheus.query(alert_freq_query)
        alert_frequency = 0
        if freq_result["data"]["result"]:
            alert_frequency = int(float(freq_result["data"]["result"][0]["value"][1]))

        total_active = len(active_alerts)
        status = "good" if total_active == 0 else "warning" if alerts_by_severity["critical"] == 0 else "critical"

        return {
            "total_active_alerts": total_active,
            "alerts_by_severity": alerts_by_severity,
            "alerts_by_team": alerts_by_team,
            "alert_frequency_24h": alert_frequency,
            "active_alerts": active_alerts[:10],  # Top 10 for brevity
            "status": status,
        }

    def generate_recommendations(
        self, cost_summary: dict, revenue_summary: dict, performance_summary: dict, alert_summary: dict
    ) -> list[str]:
        """Generate actionable recommendations based on metrics"""
        recommendations = []

        # Cost recommendations
        if cost_summary["average_user_cost_eur"] > 2.0:
            recommendations.append(
                "💰 User cost exceeds €2.00 target. Consider implementing usage limits or optimizing LLM calls."
            )

        if cost_summary["cost_trend"] == "up" and cost_summary["cost_change_percent"] > 20:
            recommendations.append(
                f"📈 Daily costs increased by {cost_summary['cost_change_percent']}%. Investigate usage patterns."
            )

        # Revenue recommendations
        if revenue_summary["mrr_progress_percent"] < 40:
            recommendations.append("📊 MRR progress is below 40% of €25k target. Accelerate growth initiatives.")

        if revenue_summary["payment_success_rate_percent"] < 95:
            recommendations.append(
                f"💳 Payment success rate is {revenue_summary['payment_success_rate_percent']}%. Review payment processing."
            )

        if revenue_summary["new_signups_24h"] == 0:
            recommendations.append("👥 No new signups in 24h. Check marketing campaigns and signup flow.")

        # Performance recommendations
        if performance_summary["api_response_time_p95_seconds"] > 2.0:
            recommendations.append(
                f"⚡ API response time is {performance_summary['api_response_time_p95_seconds']}s. Consider optimization."
            )

        if performance_summary["cache_hit_ratio_percent"] < 70:
            recommendations.append(
                f"💾 Cache hit ratio is {performance_summary['cache_hit_ratio_percent']}%. Review caching strategy."
            )

        # Alert recommendations
        if alert_summary["alerts_by_severity"]["critical"] > 0:
            recommendations.append(
                f"🚨 {alert_summary['alerts_by_severity']['critical']} critical alerts active. Immediate attention required."
            )

        if not recommendations:
            recommendations.append("✅ All metrics within acceptable ranges. Continue monitoring.")

        return recommendations

    def create_key_metrics(
        self, cost_summary: dict, revenue_summary: dict, performance_summary: dict
    ) -> list[MetricSummary]:
        """Create key metrics for dashboard display"""
        return [
            MetricSummary(
                name="Average User Cost",
                current_value=cost_summary["average_user_cost_eur"],
                target_value=2.00,
                trend=cost_summary["cost_trend"],
                status=cost_summary["status"],
                unit="EUR",
            ),
            MetricSummary(
                name="Monthly Revenue",
                current_value=revenue_summary["monthly_revenue_eur"],
                target_value=25000,
                trend="stable",  # Would need historical data
                status=revenue_summary["status"],
                unit="EUR",
            ),
            MetricSummary(
                name="API Response Time (p95)",
                current_value=performance_summary["api_response_time_p95_seconds"],
                target_value=5.0,
                trend="stable",
                status=performance_summary["status"],
                unit="seconds",
            ),
            MetricSummary(
                name="Payment Success Rate",
                current_value=revenue_summary["payment_success_rate_percent"],
                target_value=95.0,
                trend="stable",
                status="good" if revenue_summary["payment_success_rate_percent"] >= 95 else "warning",
                unit="%",
            ),
        ]

    def generate_report(self) -> DailyReport:
        """Generate complete daily report"""
        logger.info(f"Generating daily report for {self.report_date}")

        # Gather all summaries
        cost_summary = self.get_cost_summary()
        revenue_summary = self.get_revenue_summary()
        performance_summary = self.get_performance_summary()
        alert_summary = self.get_alert_summary()

        # Generate recommendations
        recommendations = self.generate_recommendations(
            cost_summary, revenue_summary, performance_summary, alert_summary
        )

        # Create key metrics
        key_metrics = self.create_key_metrics(cost_summary, revenue_summary, performance_summary)

        return DailyReport(
            date=self.report_date,
            cost_summary=cost_summary,
            revenue_summary=revenue_summary,
            performance_summary=performance_summary,
            alert_summary=alert_summary,
            recommendations=recommendations,
            key_metrics=key_metrics,
        )


class ReportFormatter:
    """Format reports for different output types"""

    @staticmethod
    def format_html(report: DailyReport) -> str:
        """Format report as HTML for email"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>PratikoAI Daily Report - {report.date}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #f1f3f4; border-radius: 3px; }}
                .good {{ color: #28a745; }}
                .warning {{ color: #ffc107; }}
                .critical {{ color: #dc3545; }}
                .recommendation {{ margin: 5px 0; padding: 8px; background: #e3f2fd; border-left: 4px solid #2196f3; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>PratikoAI Daily Report</h1>
                <p><strong>Date:</strong> {report.date}</p>
            </div>

            <div class="section">
                <h2>📊 Key Metrics</h2>
                <div>
        """

        for metric in report.key_metrics:
            status_class = metric.status
            html += f"""
                    <div class="metric">
                        <strong>{metric.name}:</strong>
                        <span class="{status_class}">{metric.current_value} {metric.unit}</span>
                        {f"(Target: {metric.target_value} {metric.unit})" if metric.target_value else ""}
                    </div>
            """

        html += """
                </div>
            </div>

            <div class="section">
                <h2>💰 Cost Summary</h2>
        """

        cost = report.cost_summary
        html += f"""
                <p><strong>Average User Cost:</strong> <span class="{cost["status"]}">€{cost["average_user_cost_eur"]}</span> (Target: €2.00)</p>
                <p><strong>Daily LLM Cost:</strong> €{cost["daily_llm_cost_eur"]} ({cost["cost_trend"]} {cost["cost_change_percent"]:+.1f}%)</p>
                <p><strong>Provider Breakdown:</strong></p>
                <ul>
        """

        for provider, cost_val in cost["provider_breakdown"].items():
            html += f"<li>{provider}: €{cost_val:.2f}</li>"

        html += """
                </ul>
            </div>

            <div class="section">
                <h2>💼 Revenue Summary</h2>
        """

        revenue = report.revenue_summary
        html += f"""
                <p><strong>Monthly Revenue:</strong> <span class="{revenue["status"]}">€{revenue["monthly_revenue_eur"]}</span> ({revenue["mrr_progress_percent"]:.1f}% of €25k target)</p>
                <p><strong>Active Subscriptions:</strong> {revenue["active_subscriptions"]} ({revenue["subscription_progress_percent"]:.1f}% of 50 target)</p>
                <p><strong>Payment Success Rate:</strong> {revenue["payment_success_rate_percent"]:.1f}%</p>
                <p><strong>New Signups (24h):</strong> {revenue["new_signups_24h"]}</p>
                <p><strong>Revenue per User:</strong> €{revenue["revenue_per_user_eur"]}</p>
            </div>

            <div class="section">
                <h2>⚡ Performance Summary</h2>
        """

        perf = report.performance_summary
        html += f"""
                <p><strong>API Response Time (p95):</strong> <span class="{perf["status"]}">{perf["api_response_time_p95_seconds"]:.3f}s</span> (SLA: 5.0s)</p>
                <p><strong>Cache Hit Ratio:</strong> {perf["cache_hit_ratio_percent"]:.1f}% (Target: 80%)</p>
                <p><strong>Error Rate:</strong> {perf["error_rate_percent"]:.2f}% (Target: <5%)</p>
                <p><strong>System Uptime:</strong> {perf["system_uptime_percent"]:.1f}% ({perf["services_up"]}/{perf["total_services"]} services)</p>
                <p><strong>Daily Requests:</strong> {perf["daily_requests"]:,}</p>
            </div>

            <div class="section">
                <h2>🚨 Alert Summary</h2>
        """

        alerts = report.alert_summary
        html += f"""
                <p><strong>Active Alerts:</strong> <span class="{alerts["status"]}">{alerts["total_active_alerts"]}</span></p>
                <p><strong>By Severity:</strong> Critical: {alerts["alerts_by_severity"]["critical"]}, Warning: {alerts["alerts_by_severity"]["warning"]}, Info: {alerts["alerts_by_severity"]["info"]}</p>
                <p><strong>Alert Frequency (24h):</strong> {alerts["alert_frequency_24h"]}</p>
            </div>

            <div class="section">
                <h2>💡 Recommendations</h2>
        """

        for rec in report.recommendations:
            html += f'<div class="recommendation">{rec}</div>'

        html += """
            </div>

            <div class="section">
                <p><small>Generated by PratikoAI Monitoring System | <a href="http://localhost:3000">View Dashboards</a></small></p>
            </div>
        </body>
        </html>
        """

        return html

    @staticmethod
    def format_text(report: DailyReport) -> str:
        """Format report as plain text"""
        text = f"""
PratikoAI Daily Report - {report.date}
={"=" * 50}

📊 KEY METRICS
--------------
"""

        for metric in report.key_metrics:
            target_info = f" (Target: {metric.target_value} {metric.unit})" if metric.target_value else ""
            text += f"{metric.name}: {metric.current_value} {metric.unit}{target_info} [{metric.status.upper()}]\n"

        cost = report.cost_summary
        text += f"""
💰 COST SUMMARY
---------------
Average User Cost: €{cost["average_user_cost_eur"]} (Target: €2.00) [{cost["status"].upper()}]
Daily LLM Cost: €{cost["daily_llm_cost_eur"]} ({cost["cost_trend"]} {cost["cost_change_percent"]:+.1f}%)
Provider Breakdown:
"""

        for provider, cost_val in cost["provider_breakdown"].items():
            text += f"  - {provider}: €{cost_val:.2f}\n"

        revenue = report.revenue_summary
        text += f"""
💼 REVENUE SUMMARY
------------------
Monthly Revenue: €{revenue["monthly_revenue_eur"]} ({revenue["mrr_progress_percent"]:.1f}% of €25k target) [{revenue["status"].upper()}]
Active Subscriptions: {revenue["active_subscriptions"]} ({revenue["subscription_progress_percent"]:.1f}% of 50 target)
Payment Success Rate: {revenue["payment_success_rate_percent"]:.1f}%
New Signups (24h): {revenue["new_signups_24h"]}
Revenue per User: €{revenue["revenue_per_user_eur"]}
"""

        perf = report.performance_summary
        text += f"""
⚡ PERFORMANCE SUMMARY
---------------------
API Response Time (p95): {perf["api_response_time_p95_seconds"]:.3f}s (SLA: 5.0s) [{perf["status"].upper()}]
Cache Hit Ratio: {perf["cache_hit_ratio_percent"]:.1f}% (Target: 80%)
Error Rate: {perf["error_rate_percent"]:.2f}% (Target: <5%)
System Uptime: {perf["system_uptime_percent"]:.1f}% ({perf["services_up"]}/{perf["total_services"]} services)
Daily Requests: {perf["daily_requests"]:,}
"""

        alerts = report.alert_summary
        text += f"""
🚨 ALERT SUMMARY
----------------
Active Alerts: {alerts["total_active_alerts"]} [{alerts["status"].upper()}]
By Severity: Critical: {alerts["alerts_by_severity"]["critical"]}, Warning: {alerts["alerts_by_severity"]["warning"]}, Info: {alerts["alerts_by_severity"]["info"]}
Alert Frequency (24h): {alerts["alert_frequency_24h"]}
"""

        text += "\n💡 RECOMMENDATIONS\n------------------\n"
        for rec in report.recommendations:
            text += f"{rec}\n"

        text += "\nGenerated by PratikoAI Monitoring System | View Dashboards: http://localhost:3000\n"

        return text


class ReportSender:
    """Send reports via various channels"""

    @staticmethod
    def send_email(report: DailyReport, recipients: list[str], smtp_config: dict[str, str]):
        """Send report via email"""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"PratikoAI Daily Report - {report.date}"
            msg["From"] = smtp_config["from_email"]
            msg["To"] = ", ".join(recipients)

            # Add both text and HTML versions
            text_part = MIMEText(ReportFormatter.format_text(report), "plain", "utf-8")
            html_part = MIMEText(ReportFormatter.format_html(report), "html", "utf-8")

            msg.attach(text_part)
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(smtp_config["smtp_host"], int(smtp_config["smtp_port"])) as server:
                if smtp_config.get("use_tls", "true").lower() == "true":
                    server.starttls()
                if smtp_config.get("username") and smtp_config.get("password"):
                    server.login(smtp_config["username"], smtp_config["password"])
                server.send_message(msg)

            logger.info(f"Email sent successfully to {len(recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    @staticmethod
    def send_webhook(report: DailyReport, webhook_url: str, webhook_secret: str | None = None):
        """Send report via webhook"""
        try:
            payload = {
                "type": "daily_report",
                "date": report.date,
                "summary": {
                    "cost_status": report.cost_summary["status"],
                    "revenue_status": report.revenue_summary["status"],
                    "performance_status": report.performance_summary["status"],
                    "alert_status": report.alert_summary["status"],
                },
                "data": asdict(report),
            }

            headers = {"Content-Type": "application/json"}
            if webhook_secret:
                headers["X-Webhook-Secret"] = webhook_secret

            response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            logger.info("Webhook sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Generate PratikoAI daily monitoring report")
    parser.add_argument("--email", action="store_true", help="Send report via email")
    parser.add_argument("--webhook", action="store_true", help="Send report via webhook")
    parser.add_argument("--format", choices=["text", "html", "json"], default="text", help="Output format")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--prometheus-url", default="http://localhost:9090", help="Prometheus URL")

    args = parser.parse_args()

    # Generate report
    generator = DailyReportGenerator(args.prometheus_url)
    report = generator.generate_report()

    # Format output
    if args.format == "json":
        output_content = json.dumps(asdict(report), indent=2, default=str)
    elif args.format == "html":
        output_content = ReportFormatter.format_html(report)
    else:
        output_content = ReportFormatter.format_text(report)

    # Output to file or console
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_content)
        logger.info(f"Report saved to {args.output}")
    else:
        print(output_content)

    # Send via email if requested
    if args.email:
        smtp_config = {
            "from_email": os.getenv("ALERT_EMAIL_FROM", "alerts@pratikoai.com"),
            "smtp_host": os.getenv("ALERT_EMAIL_SMTP_HOST", "localhost"),
            "smtp_port": os.getenv("ALERT_EMAIL_SMTP_PORT", "587"),
            "username": os.getenv("ALERT_EMAIL_USERNAME"),
            "password": os.getenv("ALERT_EMAIL_PASSWORD"),
            "use_tls": os.getenv("ALERT_EMAIL_USE_TLS", "true"),
        }
        recipients = os.getenv("ALERT_EMAIL_TO", "admin@pratikoai.com").split(",")

        ReportSender.send_email(report, recipients, smtp_config)

    # Send via webhook if requested
    if args.webhook:
        webhook_url = os.getenv("WEBHOOK_URL", "http://localhost:3001/daily-report")
        webhook_secret = os.getenv("WEBHOOK_SECRET")

        ReportSender.send_webhook(report, webhook_url, webhook_secret)


if __name__ == "__main__":
    main()
