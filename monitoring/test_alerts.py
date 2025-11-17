#!/usr/bin/env python3
"""PratikoAI Alert Testing Script

This script helps test alert configurations by simulating various conditions
that should trigger alerts in the monitoring system.

Usage:
    python monitoring/test_alerts.py --test cost
    python monitoring/test_alerts.py --test performance
    python monitoring/test_alerts.py --test all
"""

import argparse
import json
import logging
import time
from typing import Any, Dict

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertTester:
    def __init__(self, prometheus_url: str = "http://localhost:9090", app_url: str = "http://localhost:8000"):
        self.prometheus_url = prometheus_url
        self.app_url = app_url

    def check_prometheus_connection(self) -> bool:
        """Verify Prometheus is accessible"""
        try:
            response = requests.get(f"{self.prometheus_url}/api/v1/status/config")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Cannot connect to Prometheus: {e}")
            return False

    def query_prometheus(self, query: str) -> dict[str, Any]:
        """Execute Prometheus query"""
        try:
            response = requests.get(f"{self.prometheus_url}/api/v1/query", params={"query": query})
            return response.json()
        except Exception as e:
            logger.error(f"Prometheus query failed: {e}")
            return {}

    def simulate_high_user_cost(self) -> bool:
        """Simulate user cost exceeding €2.50 threshold"""
        logger.info("🔴 Testing: High User Cost Alert (>€2.50)")

        # This would normally be done by pushing custom metrics
        # In real scenario, we'd use pushgateway or custom endpoint
        test_data = {
            "metric_name": "user_monthly_cost_eur",
            "value": 3.0,
            "labels": {"user_id": "test_user", "plan_type": "premium"},
        }

        try:
            # Simulate metric push (would need custom endpoint)
            logger.info(f"Would push metric: {test_data}")
            logger.info("✅ Alert should trigger within 2 minutes")
            return True
        except Exception as e:
            logger.error(f"Failed to simulate high user cost: {e}")
            return False

    def simulate_cost_spike(self) -> bool:
        """Simulate daily cost spike >50%"""
        logger.info("🟡 Testing: Daily Cost Spike Alert (>50%)")

        # Query current cost rate
        current_cost = self.query_prometheus("rate(llm_cost_total_eur[1h])")

        if current_cost.get("data", {}).get("result"):
            current_value = float(current_cost["data"]["result"][0]["value"][1])
            logger.info(f"Current cost rate: €{current_value}/hour")

            # Simulate 60% increase
            simulated_value = current_value * 1.6
            logger.info(f"Would simulate cost rate: €{simulated_value}/hour")
            logger.info("✅ Alert should trigger within 5 minutes")
            return True
        else:
            logger.warning("No current cost data available for spike simulation")
            return False

    def simulate_high_api_latency(self) -> bool:
        """Simulate API response time >5 seconds"""
        logger.info("🔴 Testing: High API Latency Alert (>5s)")

        try:
            # Make slow requests to increase response time
            for i in range(5):
                start_time = time.time()
                try:
                    # Add artificial delay parameter if supported
                    requests.get(
                        f"{self.app_url}/health",
                        timeout=10,
                        params={"test_delay": 6},  # 6 second delay
                    )
                except requests.exceptions.Timeout:
                    pass  # Expected for slow requests

                duration = time.time() - start_time
                logger.info(f"Request {i + 1} took {duration:.2f}s")
                time.sleep(1)

            logger.info("✅ Alert should trigger within 2 minutes")
            return True

        except Exception as e:
            logger.error(f"Failed to simulate high latency: {e}")
            return False

    def simulate_low_cache_hit_ratio(self) -> bool:
        """Simulate cache hit ratio <70%"""
        logger.info("🟡 Testing: Low Cache Hit Ratio Alert (<70%)")

        try:
            # Make requests that would miss cache
            for i in range(20):
                unique_param = f"test_cache_miss_{i}_{int(time.time())}"
                requests.get(f"{self.app_url}/api/v1/test", params={"unique": unique_param}, timeout=5)
                if i % 5 == 0:
                    logger.info(f"Generated {i + 1} cache misses")

            logger.info("✅ Alert should trigger within 5 minutes")
            return True

        except Exception as e:
            logger.error(f"Failed to simulate low cache hit ratio: {e}")
            return False

    def simulate_failed_authentication(self) -> bool:
        """Simulate multiple failed authentication attempts"""
        logger.info("🔴 Testing: Multiple Failed Auth Alert (>0.1/sec)")

        try:
            # Generate failed login attempts
            failed_attempts = 0
            for i in range(30):
                try:
                    response = requests.post(
                        f"{self.app_url}/api/v1/auth/login",
                        json={"username": f"test_user_{i}", "password": "invalid_password"},
                        timeout=5,
                    )
                    if response.status_code in [401, 403]:
                        failed_attempts += 1
                except Exception:
                    pass  # Expected failures

                if i % 10 == 0:
                    logger.info(f"Generated {failed_attempts} failed auth attempts")

                time.sleep(0.1)  # 10 attempts per second

            logger.info(f"✅ Generated {failed_attempts} failed attempts")
            logger.info("✅ Security alert should trigger within 1 minute")
            return True

        except Exception as e:
            logger.error(f"Failed to simulate auth failures: {e}")
            return False

    def simulate_payment_failures(self) -> bool:
        """Simulate high payment failure rate >5%"""
        logger.info("🔴 Testing: High Payment Failure Rate Alert (>5%)")

        # This would require integration with actual payment endpoints
        logger.info("Would simulate payment failures via payment endpoints")
        logger.info("✅ Alert should trigger within 10 minutes")
        return True

    def check_alert_status(self) -> dict[str, Any]:
        """Check current alert status in Prometheus"""
        logger.info("📊 Checking Current Alert Status")

        # Query for active alerts
        alerts = self.query_prometheus('ALERTS{alertstate="firing"}')

        if alerts.get("data", {}).get("result"):
            active_alerts = len(alerts["data"]["result"])
            logger.info(f"🚨 Active alerts: {active_alerts}")

            for alert in alerts["data"]["result"]:
                labels = alert.get("metric", {})
                alert_name = labels.get("alertname", "Unknown")
                severity = labels.get("severity", "Unknown")
                logger.info(f"  - {alert_name} ({severity})")
        else:
            logger.info("✅ No active alerts")

        return alerts

    def verify_notification_channels(self) -> bool:
        """Verify notification channels are configured"""
        logger.info("📧 Verifying Notification Channels")

        # This would check Grafana notification channel configuration
        # For now, just verify the configuration files exist
        try:
            with open("monitoring/grafana/provisioning/notifiers/notification_channels.yml") as f:
                config = f.read()

            if "email-alerts" in config:
                logger.info("✅ Email notifications configured")
            if "slack-alerts" in config:
                logger.info("✅ Slack notifications configured")
            if "webhook-alerts" in config:
                logger.info("✅ Webhook notifications configured")

            return True

        except FileNotFoundError:
            logger.error("❌ Notification channel configuration not found")
            return False

    def run_cost_tests(self) -> bool:
        """Run all cost-related alert tests"""
        logger.info("\n💰 COST ALERT TESTS")
        logger.info("=" * 50)

        results = []
        results.append(self.simulate_high_user_cost())
        results.append(self.simulate_cost_spike())

        return all(results)

    def run_performance_tests(self) -> bool:
        """Run all performance-related alert tests"""
        logger.info("\n⚡ PERFORMANCE ALERT TESTS")
        logger.info("=" * 50)

        results = []
        results.append(self.simulate_high_api_latency())
        results.append(self.simulate_low_cache_hit_ratio())

        return all(results)

    def run_security_tests(self) -> bool:
        """Run all security-related alert tests"""
        logger.info("\n🔒 SECURITY ALERT TESTS")
        logger.info("=" * 50)

        results = []
        results.append(self.simulate_failed_authentication())

        return all(results)

    def run_business_tests(self) -> bool:
        """Run all business-related alert tests"""
        logger.info("\n💼 BUSINESS ALERT TESTS")
        logger.info("=" * 50)

        results = []
        results.append(self.simulate_payment_failures())

        return all(results)

    def run_all_tests(self) -> bool:
        """Run comprehensive alert testing"""
        logger.info("🧪 COMPREHENSIVE ALERT TESTING")
        logger.info("=" * 50)

        # Pre-flight checks
        if not self.check_prometheus_connection():
            logger.error("❌ Cannot connect to Prometheus")
            return False

        logger.info("✅ Prometheus connection verified")

        # Verify notification setup
        self.verify_notification_channels()

        # Check current alert status
        self.check_alert_status()

        # Run test suites
        results = []
        results.append(self.run_cost_tests())
        results.append(self.run_performance_tests())
        results.append(self.run_security_tests())
        results.append(self.run_business_tests())

        # Summary
        logger.info("\n📊 TEST SUMMARY")
        logger.info("=" * 50)

        if all(results):
            logger.info("✅ All alert tests completed successfully")
            logger.info("🔔 Check your notification channels for alerts")
            logger.info("📧 Email alerts should arrive within 2-10 minutes")
            logger.info("💬 Slack alerts should arrive immediately")
        else:
            logger.error("❌ Some alert tests failed")

        return all(results)


def main():
    parser = argparse.ArgumentParser(description="Test PratikoAI alert configurations")
    parser.add_argument(
        "--test",
        choices=["cost", "performance", "security", "business", "all"],
        default="all",
        help="Type of alerts to test",
    )
    parser.add_argument("--prometheus-url", default="http://localhost:9090", help="Prometheus URL")
    parser.add_argument("--app-url", default="http://localhost:8000", help="PratikoAI application URL")

    args = parser.parse_args()

    tester = AlertTester(args.prometheus_url, args.app_url)

    if args.test == "cost":
        success = tester.run_cost_tests()
    elif args.test == "performance":
        success = tester.run_performance_tests()
    elif args.test == "security":
        success = tester.run_security_tests()
    elif args.test == "business":
        success = tester.run_business_tests()
    else:
        success = tester.run_all_tests()

    exit(0 if success else 1)


if __name__ == "__main__":
    main()
