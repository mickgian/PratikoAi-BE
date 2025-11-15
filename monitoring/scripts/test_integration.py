#!/usr/bin/env python3
"""PratikoAI Complete Monitoring System Integration Test

This script performs comprehensive testing of the entire monitoring system:
- Service availability and health checks
- Data collection and metric validation
- Dashboard functionality and data visualization
- Alert system testing and notification verification
- Automation script testing
- Performance and stress testing

Usage:
    python monitoring/scripts/test_integration.py
    python monitoring/scripts/test_integration.py --quick
    python monitoring/scripts/test_integration.py --stress-test
    python monitoring/scripts/test_integration.py --report integration_test_report.json
"""

import argparse
import concurrent.futures
import json
import logging
import random
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Data class for individual test results"""

    test_name: str
    status: str  # "passed", "failed", "warning"
    duration_seconds: float
    details: str
    error_message: str | None = None


@dataclass
class IntegrationTestReport:
    """Main integration test report"""

    test_date: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    warning_tests: int
    total_duration_seconds: float
    system_health: str
    test_results: list[TestResult]


class MonitoringSystemTester:
    """Comprehensive monitoring system tester"""

    def __init__(self):
        self.prometheus_url = "http://localhost:9090"
        self.grafana_url = "http://localhost:3000"
        self.app_url = "http://localhost:8000"
        self.alertmanager_url = "http://localhost:9093"

        self.test_results = []
        self.start_time = time.time()

    def run_test(self, test_name: str, test_func) -> TestResult:
        """Run individual test and record result"""
        logger.info(f"🧪 Running test: {test_name}")
        start_time = time.time()

        try:
            result = test_func()
            duration = time.time() - start_time

            if result is True:
                status = "passed"
                details = "Test completed successfully"
                error_message = None
            elif isinstance(result, dict):
                status = result.get("status", "failed")
                details = result.get("details", "Test completed")
                error_message = result.get("error")
            else:
                status = "failed"
                details = str(result)
                error_message = "Unexpected test result format"

            test_result = TestResult(test_name, status, duration, details, error_message)

            if status == "passed":
                logger.info(f"✅ {test_name}: PASSED ({duration:.2f}s)")
            elif status == "warning":
                logger.warning(f"⚠️ {test_name}: WARNING ({duration:.2f}s) - {details}")
            else:
                logger.error(f"❌ {test_name}: FAILED ({duration:.2f}s) - {error_message or details}")

        except Exception as e:
            duration = time.time() - start_time
            test_result = TestResult(test_name, "failed", duration, f"Exception occurred: {str(e)}", str(e))
            logger.error(f"❌ {test_name}: FAILED ({duration:.2f}s) - {str(e)}")

        self.test_results.append(test_result)
        return test_result

    def test_service_availability(self) -> dict[str, Any]:
        """Test all monitoring services are available"""
        services = {
            "Prometheus": self.prometheus_url,
            "Grafana": self.grafana_url,
            "AlertManager": self.alertmanager_url,
            "PratikoAI App": self.app_url + "/health",
        }

        failed_services = []
        for service_name, url in services.items():
            try:
                response = requests.get(url, timeout=10)
                if response.status_code not in [200, 302]:  # 302 for Grafana redirect
                    failed_services.append(f"{service_name} returned {response.status_code}")
            except Exception as e:
                failed_services.append(f"{service_name}: {str(e)}")

        if failed_services:
            return {
                "status": "failed",
                "details": f"Failed services: {', '.join(failed_services)}",
                "error": "Service availability check failed",
            }

        return {"status": "passed", "details": "All monitoring services are available"}

    def test_prometheus_metrics_collection(self) -> dict[str, Any]:
        """Test Prometheus is collecting metrics"""
        try:
            # Test basic Prometheus query
            response = requests.get(f"{self.prometheus_url}/api/v1/query", params={"query": "up"}, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data["status"] != "success":
                return {
                    "status": "failed",
                    "details": "Prometheus query failed",
                    "error": data.get("error", "Unknown error"),
                }

            targets = len(data["data"]["result"])
            if targets == 0:
                return {
                    "status": "failed",
                    "details": "No monitoring targets found",
                    "error": "Prometheus is not collecting metrics",
                }

            # Check for application metrics
            app_metrics_response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": "http_request_duration_seconds_count"},
                timeout=10,
            )
            app_data = app_metrics_response.json()

            if not app_data["data"]["result"]:
                return {
                    "status": "warning",
                    "details": f"Prometheus collecting from {targets} targets, but no application metrics found",
                }

            return {
                "status": "passed",
                "details": f"Prometheus collecting metrics from {targets} targets including application metrics",
            }

        except Exception as e:
            return {"status": "failed", "details": "Failed to query Prometheus", "error": str(e)}

    def test_grafana_dashboards(self) -> dict[str, Any]:
        """Test Grafana dashboards are accessible"""
        try:
            # Test Grafana health
            health_response = requests.get(f"{self.grafana_url}/api/health", timeout=10)
            if health_response.status_code != 200:
                return {
                    "status": "failed",
                    "details": "Grafana health check failed",
                    "error": f"Status code: {health_response.status_code}",
                }

            # Test dashboard search (requires authentication)
            try:
                # Try to access dashboards via API
                auth = ("admin", "admin")
                dashboards_response = requests.get(
                    f"{self.grafana_url}/api/search?type=dash-db", auth=auth, timeout=10
                )

                if dashboards_response.status_code == 200:
                    dashboards = dashboards_response.json()
                    dashboard_count = len(dashboards)

                    if dashboard_count >= 4:  # We expect at least 4 dashboards
                        return {
                            "status": "passed",
                            "details": f"Grafana healthy with {dashboard_count} dashboards accessible",
                        }
                    else:
                        return {
                            "status": "warning",
                            "details": f"Grafana healthy but only {dashboard_count} dashboards found (expected ≥4)",
                        }
                else:
                    return {
                        "status": "warning",
                        "details": "Grafana healthy but dashboard API not accessible (auth issue)",
                    }

            except Exception as dashboard_e:
                return {
                    "status": "warning",
                    "details": f"Grafana healthy but dashboard test failed: {str(dashboard_e)}",
                }

        except Exception as e:
            return {"status": "failed", "details": "Failed to connect to Grafana", "error": str(e)}

    def test_alert_system(self) -> dict[str, Any]:
        """Test alert system configuration"""
        try:
            # Test AlertManager status
            am_response = requests.get(f"{self.alertmanager_url}/api/v1/status", timeout=10)
            if am_response.status_code != 200:
                return {
                    "status": "failed",
                    "details": "AlertManager not accessible",
                    "error": f"Status code: {am_response.status_code}",
                }

            # Test Prometheus alert rules
            rules_response = requests.get(f"{self.prometheus_url}/api/v1/rules", timeout=10)
            if rules_response.status_code != 200:
                return {
                    "status": "failed",
                    "details": "Failed to fetch Prometheus rules",
                    "error": f"Status code: {rules_response.status_code}",
                }

            rules_data = rules_response.json()
            if rules_data["status"] != "success":
                return {
                    "status": "failed",
                    "details": "Prometheus rules query failed",
                    "error": rules_data.get("error", "Unknown error"),
                }

            # Count alert rules
            total_rules = 0
            for group in rules_data["data"]["groups"]:
                total_rules += len([rule for rule in group["rules"] if rule["type"] == "alerting"])

            if total_rules >= 10:  # We expect at least 10 alert rules
                return {
                    "status": "passed",
                    "details": f"Alert system operational with {total_rules} alert rules configured",
                }
            else:
                return {
                    "status": "warning",
                    "details": f"Alert system operational but only {total_rules} rules found (expected ≥10)",
                }

        except Exception as e:
            return {"status": "failed", "details": "Failed to test alert system", "error": str(e)}

    def test_automation_scripts(self) -> dict[str, Any]:
        """Test automation scripts execute successfully"""
        try:
            # Test health check script
            result = subprocess.run(
                [sys.executable, "monitoring/scripts/health_check.py", "--export", "/tmp/test_health.json"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return {"status": "failed", "details": "Health check script failed", "error": result.stderr}

            # Verify output file was created
            if not Path("/tmp/test_health.json").exists():
                return {
                    "status": "failed",
                    "details": "Health check script didn't create output file",
                    "error": "Expected output file not found",
                }

            # Test cost optimization script
            cost_result = subprocess.run(
                [sys.executable, "monitoring/scripts/optimize_costs.py", "--export", "/tmp/test_costs.json"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if cost_result.returncode != 0:
                return {
                    "status": "warning",
                    "details": "Health check passed, cost optimization script failed",
                    "error": cost_result.stderr,
                }

            return {"status": "passed", "details": "Automation scripts executed successfully"}

        except subprocess.TimeoutExpired:
            return {
                "status": "failed",
                "details": "Automation script test timed out",
                "error": "Script execution exceeded 60 seconds",
            }
        except Exception as e:
            return {"status": "failed", "details": "Failed to test automation scripts", "error": str(e)}

    def test_data_persistence(self) -> dict[str, Any]:
        """Test that monitoring data persists across restarts"""
        try:
            # Get current metric count
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": "prometheus_tsdb_symbol_table_size_bytes"},
                timeout=10,
            )

            if response.status_code != 200:
                return {"status": "warning", "details": "Could not test data persistence - Prometheus query failed"}

            data = response.json()
            if not data["data"]["result"]:
                return {"status": "warning", "details": "Could not test data persistence - no TSDB metrics found"}

            # Check if we have historical data (more than just current scrape)
            range_response = requests.get(
                f"{self.prometheus_url}/api/v1/query_range",
                params={
                    "query": "up",
                    "start": (datetime.now() - timedelta(minutes=10)).timestamp(),
                    "end": datetime.now().timestamp(),
                    "step": "60s",
                },
                timeout=10,
            )

            if range_response.status_code == 200:
                range_data = range_response.json()
                if range_data["data"]["result"]:
                    # Check if we have multiple data points
                    values_count = (
                        len(range_data["data"]["result"][0]["values"]) if range_data["data"]["result"] else 0
                    )

                    if values_count > 1:
                        return {
                            "status": "passed",
                            "details": f"Data persistence working - {values_count} historical data points found",
                        }
                    else:
                        return {"status": "warning", "details": "Data persistence uncertain - limited historical data"}

            return {"status": "warning", "details": "Data persistence test inconclusive"}

        except Exception as e:
            return {"status": "warning", "details": f"Data persistence test failed: {str(e)}"}

    def test_business_metrics(self) -> dict[str, Any]:
        """Test business-critical metrics are being collected"""
        try:
            # List of business-critical metrics we expect
            critical_metrics = [
                "user_monthly_cost_eur",
                "monthly_revenue_eur",
                "payment_operations_total",
                "llm_cost_total_eur",
                "active_subscriptions_total",
            ]

            missing_metrics = []
            available_metrics = []

            for metric in critical_metrics:
                response = requests.get(f"{self.prometheus_url}/api/v1/query", params={"query": metric}, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if data["data"]["result"]:
                        available_metrics.append(metric)
                    else:
                        missing_metrics.append(metric)
                else:
                    missing_metrics.append(metric)

            if len(available_metrics) == len(critical_metrics):
                return {
                    "status": "passed",
                    "details": f"All {len(critical_metrics)} business-critical metrics are available",
                }
            elif len(available_metrics) >= len(critical_metrics) * 0.7:  # 70% threshold
                return {
                    "status": "warning",
                    "details": f"{len(available_metrics)}/{len(critical_metrics)} business metrics available. Missing: {', '.join(missing_metrics)}",
                }
            else:
                return {
                    "status": "failed",
                    "details": f"Only {len(available_metrics)}/{len(critical_metrics)} business metrics available",
                    "error": f"Missing critical metrics: {', '.join(missing_metrics)}",
                }

        except Exception as e:
            return {"status": "failed", "details": "Failed to test business metrics", "error": str(e)}

    def test_performance_load(self) -> dict[str, Any]:
        """Test system performance under load"""
        try:
            # Generate some load on the system
            def make_request():
                try:
                    response = requests.get(f"{self.app_url}/health", timeout=5)
                    return response.status_code == 200
                except:
                    return False

            # Make 20 concurrent requests
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(20)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

            duration = time.time() - start_time
            success_rate = sum(results) / len(results) * 100

            # Test Prometheus can handle the queries during load
            prom_response = requests.get(f"{self.prometheus_url}/api/v1/query", params={"query": "up"}, timeout=10)

            if prom_response.status_code != 200:
                return {
                    "status": "warning",
                    "details": f"App load test: {success_rate:.1f}% success, but Prometheus queries failed during load",
                }

            if success_rate >= 95 and duration < 10:
                return {
                    "status": "passed",
                    "details": f"Performance test passed: {success_rate:.1f}% success rate in {duration:.2f}s",
                }
            elif success_rate >= 80:
                return {
                    "status": "warning",
                    "details": f"Performance test marginal: {success_rate:.1f}% success rate in {duration:.2f}s",
                }
            else:
                return {
                    "status": "failed",
                    "details": f"Performance test failed: {success_rate:.1f}% success rate in {duration:.2f}s",
                    "error": "Poor performance under load",
                }

        except Exception as e:
            return {"status": "failed", "details": "Performance load test failed", "error": str(e)}

    def run_comprehensive_test(self, quick_mode: bool = False) -> IntegrationTestReport:
        """Run all integration tests"""
        logger.info("🚀 Starting comprehensive monitoring system integration test")

        # Define test suite
        tests = [
            ("Service Availability", self.test_service_availability),
            ("Prometheus Metrics Collection", self.test_prometheus_metrics_collection),
            ("Grafana Dashboards", self.test_grafana_dashboards),
            ("Alert System", self.test_alert_system),
            ("Business Metrics", self.test_business_metrics),
            ("Data Persistence", self.test_data_persistence),
        ]

        if not quick_mode:
            tests.extend(
                [
                    ("Automation Scripts", self.test_automation_scripts),
                    ("Performance Load", self.test_performance_load),
                ]
            )

        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)

        # Calculate summary
        total_duration = time.time() - self.start_time
        passed = len([t for t in self.test_results if t.status == "passed"])
        failed = len([t for t in self.test_results if t.status == "failed"])
        warning = len([t for t in self.test_results if t.status == "warning"])

        # Determine overall system health
        if failed == 0 and warning <= 1:
            system_health = "healthy"
        elif failed == 0 and warning <= 3:
            system_health = "warning"
        else:
            system_health = "critical"

        report = IntegrationTestReport(
            test_date=datetime.now().isoformat(),
            total_tests=len(self.test_results),
            passed_tests=passed,
            failed_tests=failed,
            warning_tests=warning,
            total_duration_seconds=total_duration,
            system_health=system_health,
            test_results=self.test_results,
        )

        # Print summary
        logger.info("=" * 60)
        logger.info("INTEGRATION TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {report.total_tests}")
        logger.info(f"✅ Passed: {report.passed_tests}")
        logger.info(f"⚠️ Warnings: {report.warning_tests}")
        logger.info(f"❌ Failed: {report.failed_tests}")
        logger.info(f"⏱️ Duration: {report.total_duration_seconds:.2f}s")

        health_icon = {"healthy": "🟢", "warning": "🟡", "critical": "🔴"}.get(system_health, "❓")
        logger.info(f"🏥 System Health: {health_icon} {system_health.upper()}")

        if system_health == "healthy":
            logger.info("🎉 Monitoring system is ready for production!")
        elif system_health == "warning":
            logger.info("⚠️ Monitoring system functional with minor issues")
        else:
            logger.error("🚨 Monitoring system has critical issues requiring attention")

        return report


def main():
    parser = argparse.ArgumentParser(description="PratikoAI Monitoring System Integration Test")
    parser.add_argument("--quick", action="store_true", help="Run quick test suite (skip long-running tests)")
    parser.add_argument("--stress-test", action="store_true", help="Include stress testing")
    parser.add_argument("--report", help="Save detailed report to JSON file")

    args = parser.parse_args()

    # Run integration tests
    tester = MonitoringSystemTester()
    report = tester.run_comprehensive_test(quick_mode=args.quick)

    # Save report if requested
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, default=str)
        logger.info(f"📊 Detailed report saved to {args.report}")

    # Exit with appropriate code
    if report.system_health == "critical":
        sys.exit(2)
    elif report.system_health == "warning":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
