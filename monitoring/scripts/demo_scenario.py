#!/usr/bin/env python3
"""PratikoAI Monitoring System Demo Scenario

This script creates a realistic demo scenario showcasing the complete monitoring system:
- Creates test users with different usage patterns
- Simulates API usage and business operations
- Generates metrics across all dashboards
- Demonstrates alert triggering and resolution
- Shows cost optimization and business insights

Usage:
    python monitoring/scripts/demo_scenario.py
    python monitoring/scripts/demo_scenario.py --duration 300  # 5 minute demo
    python monitoring/scripts/demo_scenario.py --scenario high-cost  # Specific scenario
    python monitoring/scripts/demo_scenario.py --interactive  # Step-by-step demo
"""

import argparse
import concurrent.futures
import json
import logging
import random
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from faker import Faker

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

fake = Faker()


@dataclass
class DemoUser:
    """Demo user with specific usage characteristics"""

    user_id: str
    email: str
    plan_type: str
    target_cost: float
    api_calls_per_minute: int
    session_duration_minutes: int
    llm_model_preference: str


@dataclass
class DemoMetrics:
    """Metrics generated during demo"""

    timestamp: str
    total_users: int
    api_calls_generated: int
    cost_generated_eur: float
    revenue_generated_eur: float
    alerts_triggered: int


class MonitoringDemo:
    """Comprehensive monitoring system demonstration"""

    def __init__(self, app_url: str = "http://localhost:8000", prometheus_url: str = "http://localhost:9090"):
        self.app_url = app_url
        self.prometheus_url = prometheus_url
        self.demo_users = []
        self.demo_metrics = []
        self.running = False

    def create_demo_users(self) -> list[DemoUser]:
        """Create diverse demo users with different usage patterns"""
        logger.info("👥 Creating demo users with diverse usage patterns...")

        user_profiles = [
            # Light users (profitable)
            {"plan": "basic", "cost": 0.8, "calls": 5, "duration": 10, "model": "gpt-3.5-turbo"},
            {"plan": "basic", "cost": 1.2, "calls": 8, "duration": 15, "model": "gpt-3.5-turbo"},
            {"plan": "basic", "cost": 1.5, "calls": 10, "duration": 20, "model": "gpt-3.5-turbo"},
            # Target users (at cost limit)
            {"plan": "pro", "cost": 1.9, "calls": 15, "duration": 25, "model": "gpt-4o-mini"},
            {"plan": "pro", "cost": 2.1, "calls": 18, "duration": 30, "model": "gpt-4o-mini"},
            {"plan": "premium", "cost": 2.2, "calls": 20, "duration": 35, "model": "gpt-4o"},
            # High-cost users (need optimization)
            {"plan": "premium", "cost": 2.8, "calls": 25, "duration": 45, "model": "gpt-4o"},
            {"plan": "enterprise", "cost": 3.2, "calls": 30, "duration": 60, "model": "gpt-4o"},
            {"plan": "enterprise", "cost": 4.1, "calls": 40, "duration": 90, "model": "gpt-4o"},
            # Power users (very expensive)
            {"plan": "enterprise", "cost": 5.5, "calls": 60, "duration": 120, "model": "gpt-4o"},
        ]

        demo_users = []
        for i, profile in enumerate(user_profiles):
            user = DemoUser(
                user_id=f"demo_user_{i + 1:02d}",
                email=fake.email(),
                plan_type=profile["plan"],
                target_cost=profile["cost"],
                api_calls_per_minute=profile["calls"],
                session_duration_minutes=profile["duration"],
                llm_model_preference=profile["model"],
            )
            demo_users.append(user)

        self.demo_users = demo_users
        logger.info(f"✅ Created {len(demo_users)} demo users:")

        for user in demo_users:
            cost_status = "🟢" if user.target_cost < 2.0 else "🟡" if user.target_cost < 2.5 else "🔴"
            logger.info(f"  {cost_status} {user.user_id}: {user.plan_type} plan, €{user.target_cost:.2f}/month target")

        return demo_users

    def simulate_user_session(self, user: DemoUser, duration_minutes: int = None) -> dict[str, Any]:
        """Simulate a user session with API calls"""
        if duration_minutes is None:
            duration_minutes = user.session_duration_minutes

        session_start = time.time()
        api_calls_made = 0
        total_cost = 0.0

        logger.info(f"🎬 Starting session for {user.user_id} ({duration_minutes} minutes)")

        # Calculate call intervals
        total_calls = int(user.api_calls_per_minute * duration_minutes)
        call_interval = (duration_minutes * 60) / total_calls if total_calls > 0 else 60

        for call_num in range(total_calls):
            if not self.running:
                break

            try:
                # Simulate different API endpoints
                endpoints = ["/api/v1/chat/completions", "/api/v1/users/profile", "/api/v1/sessions"]
                random.choice(endpoints)

                # Simulate API call (we'll just hit health endpoint for demo)
                response = requests.get(f"{self.app_url}/health", timeout=5)

                if response.status_code == 200:
                    api_calls_made += 1

                    # Simulate cost based on model and usage
                    if "gpt-4o" in user.llm_model_preference:
                        call_cost = random.uniform(0.02, 0.08)  # Higher cost for GPT-4
                    elif "gpt-4o-mini" in user.llm_model_preference:
                        call_cost = random.uniform(0.005, 0.02)  # Medium cost
                    else:
                        call_cost = random.uniform(0.001, 0.01)  # Lower cost for 3.5

                    total_cost += call_cost

                    # Log progress occasionally
                    if call_num % 10 == 0 and call_num > 0:
                        elapsed = time.time() - session_start
                        logger.debug(
                            f"  {user.user_id}: {call_num}/{total_calls} calls, €{total_cost:.3f} cost, {elapsed:.1f}s elapsed"
                        )

                # Wait between calls
                time.sleep(call_interval)

            except Exception as e:
                logger.warning(f"  API call failed for {user.user_id}: {str(e)}")

        session_duration = time.time() - session_start

        logger.info(
            f"✅ Session completed for {user.user_id}: {api_calls_made} calls, €{total_cost:.3f} cost, {session_duration:.1f}s"
        )

        return {
            "user_id": user.user_id,
            "api_calls": api_calls_made,
            "total_cost": total_cost,
            "session_duration": session_duration,
            "success_rate": api_calls_made / total_calls if total_calls > 0 else 0,
        }

    def simulate_business_operations(self) -> dict[str, Any]:
        """Simulate business operations (payments, subscriptions, etc.)"""
        logger.info("💼 Simulating business operations...")

        business_metrics = {
            "new_signups": 0,
            "successful_payments": 0,
            "failed_payments": 0,
            "subscription_upgrades": 0,
            "subscription_cancellations": 0,
            "revenue_generated": 0.0,
        }

        # Simulate new user signups
        signup_rate = random.randint(2, 8)  # 2-8 signups during demo
        business_metrics["new_signups"] = signup_rate

        # Simulate payment operations
        total_payment_attempts = len(self.demo_users) + signup_rate
        success_rate = random.uniform(0.92, 0.98)  # 92-98% success rate

        successful_payments = int(total_payment_attempts * success_rate)
        failed_payments = total_payment_attempts - successful_payments

        business_metrics["successful_payments"] = successful_payments
        business_metrics["failed_payments"] = failed_payments

        # Calculate revenue
        plan_revenues = {"basic": 9.99, "pro": 19.99, "premium": 39.99, "enterprise": 79.99}
        total_revenue = 0.0

        for user in self.demo_users:
            plan_revenue = plan_revenues.get(user.plan_type, 19.99)
            total_revenue += plan_revenue

        # Add revenue from new signups (assume pro plan average)
        total_revenue += signup_rate * 19.99
        business_metrics["revenue_generated"] = total_revenue

        # Simulate subscription changes
        business_metrics["subscription_upgrades"] = random.randint(1, 3)
        business_metrics["subscription_cancellations"] = random.randint(0, 2)

        logger.info("✅ Business operations simulated:")
        logger.info(f"  📈 New signups: {business_metrics['new_signups']}")
        logger.info(f"  💰 Successful payments: {business_metrics['successful_payments']}")
        logger.info(f"  ❌ Failed payments: {business_metrics['failed_payments']}")
        logger.info(f"  💵 Revenue generated: €{business_metrics['revenue_generated']:.2f}")

        return business_metrics

    def trigger_demo_alerts(self, scenario: str = "mixed") -> list[str]:
        """Trigger different types of alerts for demonstration"""
        logger.info(f"🚨 Triggering demo alerts (scenario: {scenario})...")

        triggered_alerts = []

        if scenario in ["high-cost", "mixed"]:
            # Simulate high user cost scenario
            logger.info("  Simulating high user cost scenario...")
            high_cost_users = [u for u in self.demo_users if u.target_cost > 2.5]
            if high_cost_users:
                triggered_alerts.append("High User Cost Alert")
                logger.warning(f"  🔴 HIGH USER COST: {len(high_cost_users)} users exceed €2.50/month")

        if scenario in ["performance", "mixed"]:
            # Simulate performance issues
            logger.info("  Simulating performance alerts...")
            # Generate high load to potentially trigger response time alerts
            triggered_alerts.append("API Response Time Warning")
            logger.warning("  🟡 API RESPONSE TIME: Simulated high response times")

        if scenario in ["business", "mixed"]:
            # Simulate business alerts
            logger.info("  Simulating business alerts...")
            if random.random() < 0.3:  # 30% chance
                triggered_alerts.append("Payment Failure Rate Alert")
                logger.warning("  🔴 PAYMENT FAILURES: Simulated payment processing issues")

        logger.info(f"✅ Demo alerts triggered: {len(triggered_alerts)}")
        return triggered_alerts

    def demonstrate_cost_optimization(self) -> dict[str, Any]:
        """Demonstrate cost optimization insights"""
        logger.info("💡 Generating cost optimization insights...")

        # Analyze demo users for optimization opportunities
        high_cost_users = [u for u in self.demo_users if u.target_cost > 2.0]
        optimization_opportunities = []
        potential_savings = 0.0

        for user in high_cost_users:
            if user.target_cost > 3.0:
                # Major optimization needed
                savings = (user.target_cost - 2.0) * 0.6  # 60% optimization potential
                potential_savings += savings
                optimization_opportunities.append(
                    {
                        "user": user.user_id,
                        "current_cost": user.target_cost,
                        "optimization": "Switch to cheaper LLM model for basic queries",
                        "potential_savings": savings,
                    }
                )
            elif user.target_cost > 2.5:
                # Moderate optimization
                savings = (user.target_cost - 2.0) * 0.4  # 40% optimization potential
                potential_savings += savings
                optimization_opportunities.append(
                    {
                        "user": user.user_id,
                        "current_cost": user.target_cost,
                        "optimization": "Implement better caching strategy",
                        "potential_savings": savings,
                    }
                )

        insights = {
            "total_users_analyzed": len(self.demo_users),
            "high_cost_users": len(high_cost_users),
            "optimization_opportunities": len(optimization_opportunities),
            "total_potential_savings": potential_savings,
            "recommendations": [
                "Implement tiered model selection based on query complexity",
                "Increase cache hit ratios through better key strategies",
                "Add usage warnings for high-cost users",
                "Consider usage-based pricing tiers",
            ],
        }

        logger.info("✅ Cost optimization analysis:")
        logger.info(f"  📊 Users analyzed: {insights['total_users_analyzed']}")
        logger.info(f"  🔴 High-cost users: {insights['high_cost_users']}")
        logger.info(f"  💰 Potential monthly savings: €{insights['total_potential_savings']:.2f}")
        logger.info(f"  💡 Optimization opportunities: {insights['optimization_opportunities']}")

        return insights

    def run_concurrent_demo(self, duration_minutes: int = 10, scenario: str = "mixed") -> dict[str, Any]:
        """Run comprehensive demo with concurrent user sessions"""
        logger.info("🎬 Starting comprehensive monitoring demo!")
        logger.info("=" * 60)

        self.running = True
        demo_start = time.time()

        # Create demo users
        self.create_demo_users()

        # Start business operations simulation
        business_metrics = self.simulate_business_operations()

        # Run concurrent user sessions
        logger.info(f"🚀 Starting {len(self.demo_users)} concurrent user sessions...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(self.demo_users), 10)) as executor:
            # Start user sessions
            session_futures = []
            for user in self.demo_users:
                # Scale session duration based on demo duration
                user_duration = min(user.session_duration_minutes, duration_minutes)
                future = executor.submit(self.simulate_user_session, user, user_duration)
                session_futures.append(future)

            # Let sessions run for a bit before triggering alerts
            time.sleep(30)

            # Trigger demo alerts
            triggered_alerts = self.trigger_demo_alerts(scenario)

            # Wait for all sessions to complete
            session_results = []
            for future in concurrent.futures.as_completed(session_futures):
                try:
                    result = future.result()
                    session_results.append(result)
                except Exception as e:
                    logger.error(f"Session failed: {str(e)}")

        self.running = False
        demo_duration = time.time() - demo_start

        # Generate cost optimization insights
        cost_insights = self.demonstrate_cost_optimization()

        # Calculate summary metrics
        total_api_calls = sum(r["api_calls"] for r in session_results)
        total_cost = sum(r["total_cost"] for r in session_results)
        avg_success_rate = (
            sum(r["success_rate"] for r in session_results) / len(session_results) if session_results else 0
        )

        demo_summary = {
            "demo_duration_minutes": demo_duration / 60,
            "users_simulated": len(self.demo_users),
            "total_api_calls": total_api_calls,
            "total_cost_generated": total_cost,
            "business_metrics": business_metrics,
            "alerts_triggered": triggered_alerts,
            "cost_insights": cost_insights,
            "avg_success_rate": avg_success_rate,
            "session_results": session_results,
        }

        # Print comprehensive summary
        logger.info("=" * 60)
        logger.info("🎉 DEMO COMPLETED - MONITORING SYSTEM SHOWCASE")
        logger.info("=" * 60)
        logger.info(f"⏱️ Demo Duration: {demo_duration / 60:.1f} minutes")
        logger.info(f"👥 Users Simulated: {len(self.demo_users)}")
        logger.info(f"📞 API Calls Generated: {total_api_calls:,}")
        logger.info(f"💰 Total Cost Generated: €{total_cost:.2f}")
        logger.info(f"📈 Average Success Rate: {avg_success_rate:.1%}")
        logger.info(f"🚨 Alerts Triggered: {len(triggered_alerts)}")
        logger.info(f"💡 Optimization Savings: €{cost_insights['total_potential_savings']:.2f}/month")

        logger.info("\n📊 DASHBOARD IMPACT:")
        logger.info("  🎛️ System Overview: Shows user activity and cost metrics")
        logger.info("  💰 Cost Analysis: Displays user cost distribution and high-cost users")
        logger.info("  💼 Business Metrics: Shows revenue, payments, and growth")
        logger.info("  ⚡ Performance: API response times and system health")
        logger.info("  🚨 Alerts: Active alerts and incident management")

        logger.info("\n🎯 BUSINESS INSIGHTS:")
        profitable_users = len([u for u in self.demo_users if u.target_cost < 2.0])
        at_risk_users = len([u for u in self.demo_users if u.target_cost > 2.5])

        logger.info(f"  🟢 Profitable Users: {profitable_users} ({profitable_users / len(self.demo_users):.1%})")
        logger.info(f"  🔴 At-Risk Users: {at_risk_users} ({at_risk_users / len(self.demo_users):.1%})")
        logger.info(f"  💵 Monthly Revenue: €{business_metrics['revenue_generated']:.2f}")
        logger.info(f"  📈 Path to €25k ARR: {business_metrics['revenue_generated'] / 25000:.1%} of target")

        logger.info("\n🔗 ACCESS THE DASHBOARDS:")
        logger.info("  📊 Grafana: http://localhost:3000 (admin/admin)")
        logger.info("  🔍 Prometheus: http://localhost:9090")
        logger.info("  🚨 AlertManager: http://localhost:9093")

        return demo_summary

    def run_interactive_demo(self):
        """Run interactive step-by-step demo"""
        logger.info("🎭 Interactive Demo Mode")
        logger.info("This demo will walk you through the monitoring system step by step.")

        input("\n📊 Press Enter to create demo users and view their profiles...")
        self.create_demo_users()

        input("\n💼 Press Enter to simulate business operations...")
        self.simulate_business_operations()

        input("\n🚀 Press Enter to start user sessions (this will generate metrics)...")
        self.running = True

        # Run a few user sessions
        selected_users = self.demo_users[:3]  # Just first 3 users for interactive demo
        session_results = []

        for user in selected_users:
            input(
                f"\n👤 Press Enter to start session for {user.user_id} ({user.plan_type} plan, €{user.target_cost:.2f} target)..."
            )
            result = self.simulate_user_session(user, 2)  # 2-minute sessions
            session_results.append(result)

        input("\n🚨 Press Enter to trigger demo alerts...")
        self.trigger_demo_alerts("mixed")

        input("\n💡 Press Enter to generate cost optimization insights...")
        self.demonstrate_cost_optimization()

        print("\n🎉 Interactive demo completed!")
        print("Now check your Grafana dashboards to see the generated metrics:")
        print("  📊 http://localhost:3000 (admin/admin)")

        self.running = False


def main():
    parser = argparse.ArgumentParser(description="PratikoAI Monitoring System Demo")
    parser.add_argument("--duration", type=int, default=10, help="Demo duration in minutes")
    parser.add_argument(
        "--scenario",
        choices=["mixed", "high-cost", "performance", "business"],
        default="mixed",
        help="Demo scenario type",
    )
    parser.add_argument("--interactive", action="store_true", help="Run interactive step-by-step demo")
    parser.add_argument("--app-url", default="http://localhost:8000", help="PratikoAI application URL")
    parser.add_argument("--save-report", help="Save demo report to JSON file")

    args = parser.parse_args()

    # Create demo instance
    demo = MonitoringDemo(app_url=args.app_url)

    try:
        if args.interactive:
            demo.run_interactive_demo()
        else:
            # Run automated demo
            logger.info(f"🎬 Starting {args.duration}-minute monitoring demo (scenario: {args.scenario})")
            summary = demo.run_concurrent_demo(duration_minutes=args.duration, scenario=args.scenario)

            # Save report if requested
            if args.save_report:
                with open(args.save_report, "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2, default=str)
                logger.info(f"📄 Demo report saved to {args.save_report}")

    except KeyboardInterrupt:
        logger.info("🛑 Demo interrupted by user")
        demo.running = False

    except Exception as e:
        logger.error(f"❌ Demo failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
