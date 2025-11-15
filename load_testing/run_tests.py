#!/usr/bin/env python3
"""Load Test Execution Script for PratikoAI.

This script orchestrates the complete load testing suite to validate
the system can handle 50-100 concurrent users (€25k ARR target).

Usage:
    python load_testing/run_tests.py --profile peak_hours
    python load_testing/run_tests.py --users 50 --duration 300
    python load_testing/run_tests.py --full-suite
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add current directory to Python path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from load_testing.config import LoadTestProfile, LoadTestProfiles
from load_testing.framework import LoadTestFramework
from load_testing.monitoring import LoadTestMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("load_test.log")],
)
logger = logging.getLogger(__name__)


class LoadTestRunner:
    """Main class for running comprehensive load testing suite"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.framework = LoadTestFramework(base_url=base_url, enable_monitoring=True)
        self.results = []
        self.overall_passed = True

    async def run_full_suite(self) -> dict[str, Any]:
        """Run the complete load testing suite"""
        logger.info("🚀 Starting PratikoAI Load Testing Suite")
        logger.info("Target: Validate system for 50-100 concurrent users (€25k ARR)")
        logger.info("Duration: ~30 minutes comprehensive testing")
        logger.info("-" * 60)

        start_time = datetime.now()

        try:
            # Phase 1: Setup and baseline
            await self._setup_phase()

            # Phase 2: Performance baseline (1 user)
            await self._baseline_phase()

            # Phase 3: Normal load (30 users)
            await self._normal_load_phase()

            # Phase 4: Target load (50 users) - KEY TEST
            await self._target_load_phase()

            # Phase 5: Stress test (100 users)
            await self._stress_test_phase()

            # Phase 6: Spike test (10 → 100 users)
            await self._spike_test_phase()

            # Phase 7: Italian market specific tests
            await self._italian_market_phase()

            # Phase 8: Generate comprehensive report
            report = await self._generate_report(start_time)

            # Phase 9: Save results and recommendations
            await self._save_results(report)

            return report

        except Exception as e:
            logger.error(f"Load testing suite failed: {e}")
            raise
        finally:
            await self.framework.cleanup()

    async def run_single_test(self, profile: LoadTestProfile, custom_config: dict[str, Any] = None) -> dict[str, Any]:
        """Run a single load test with specified profile"""
        config = LoadTestProfiles.get_profile(profile)

        # Override with custom configuration
        if custom_config:
            for key, value in custom_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        logger.info(f"Running single test: {profile.value}")
        logger.info(f"Users: {config.target_users}, Duration: {config.test_duration}s")

        try:
            # Setup
            await self.framework.setup_test_users(200)
            await self.framework.warmup_cache()

            # Run test
            metrics = await self.framework.run_test(
                users=config.target_users, duration=config.test_duration, scenario="mixed", ramp_up=config.ramp_up_time
            )

            # Analyze results
            bottlenecks = self.framework.identify_bottlenecks(metrics)
            recommendations = self.framework.generate_scaling_recommendations(metrics)

            # Check if test passed
            passed = self._evaluate_test_results(metrics, config)

            return {
                "profile": profile.value,
                "config": config,
                "metrics": metrics,
                "bottlenecks": bottlenecks,
                "recommendations": recommendations,
                "passed": passed,
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            await self.framework.cleanup()

    async def _setup_phase(self):
        """Phase 1: Setup test environment"""
        logger.info("\n📋 Phase 1: Environment Setup")

        # Setup test users
        user_count = await self.framework.setup_test_users(200)
        logger.info(f"✅ Created {user_count} test users")

        # Setup test documents
        doc_dir = await self.framework.setup_test_documents()
        logger.info(f"✅ Created test documents in {doc_dir}")

        # Warmup cache
        await self.framework.warmup_cache()
        logger.info("✅ Cache warmed up")

        # Health check
        health_passed = await self._health_check()
        if not health_passed:
            raise RuntimeError("System health check failed")
        logger.info("✅ System health check passed")

    async def _baseline_phase(self):
        """Phase 2: Establish performance baseline"""
        logger.info("\n📊 Phase 2: Baseline Performance (1 user)")

        baseline = await self.framework.establish_baseline()
        self.results.append(
            {
                "phase": "baseline",
                "metrics": baseline,
                "passed": baseline["single_user_p95"] < 3000,  # 3 seconds SLA
            }
        )

        logger.info(f"✅ Baseline P95: {baseline['single_user_p95']:.0f}ms")
        logger.info(f"✅ Baseline throughput: {baseline['optimal_throughput']:.1f} req/min")

    async def _normal_load_phase(self):
        """Phase 3: Normal day load testing"""
        logger.info("\n📊 Phase 3: Normal Load (30 users)")

        metrics = await self.framework.run_test(
            users=30,
            duration=300,  # 5 minutes
            scenario="mixed",
            ramp_up=60,
        )

        passed = (
            metrics.p95_response_time < 4000  # 4s for 30 users
            and metrics.error_rate < 0.01
            and metrics.throughput >= 800
        )

        self.results.append({"phase": "normal_load", "users": 30, "metrics": metrics, "passed": passed})

        logger.info(
            f"{'✅' if passed else '❌'} Normal load: P95={metrics.p95_response_time:.0f}ms, Errors={metrics.error_rate * 100:.2f}%"
        )

    async def _target_load_phase(self):
        """Phase 4: Target load testing (50 users) - CRITICAL TEST"""
        logger.info("\n🎯 Phase 4: Target Load (50 users) - CRITICAL TEST")

        metrics = await self.framework.run_test(
            users=50,
            duration=600,  # 10 minutes sustained
            scenario="mixed",
            ramp_up=60,
        )

        # Strict SLA for target load
        passed = (
            metrics.p95_response_time < 5000  # 5s SLA
            and metrics.error_rate < 0.01  # 1% error rate
            and metrics.throughput >= 1000  # 1000 req/min
            and metrics.cache_hit_rate > 0.7  # 70% cache hit rate
        )

        self.results.append(
            {
                "phase": "target_load",
                "users": 50,
                "metrics": metrics,
                "passed": passed,
                "critical": True,  # This is the most important test
            }
        )

        if not passed:
            self.overall_passed = False
            logger.error("❌ CRITICAL: Target load test FAILED")
        else:
            logger.info("🎉 Target load test PASSED")

        logger.info(f"P95: {metrics.p95_response_time:.0f}ms, Throughput: {metrics.throughput:.0f} req/min")
        logger.info(f"Errors: {metrics.error_rate * 100:.2f}%, Cache hits: {metrics.cache_hit_rate * 100:.1f}%")

    async def _stress_test_phase(self):
        """Phase 5: Stress testing (100 users)"""
        logger.info("\n🔥 Phase 5: Stress Test (100 users)")

        metrics = await self.framework.run_test(
            users=100,
            duration=300,  # 5 minutes
            scenario="mixed",
            ramp_up=120,
        )

        # More lenient SLA for stress test
        passed = (
            metrics.p95_response_time < 8000  # 8s SLA
            and metrics.error_rate < 0.02  # 2% error rate allowed
        )

        self.results.append({"phase": "stress_test", "users": 100, "metrics": metrics, "passed": passed})

        logger.info(
            f"{'✅' if passed else '❌'} Stress test: P95={metrics.p95_response_time:.0f}ms, Errors={metrics.error_rate * 100:.2f}%"
        )

    async def _spike_test_phase(self):
        """Phase 6: Spike testing (sudden load increase)"""
        logger.info("\n⚡ Phase 6: Spike Test (10 → 100 users)")

        metrics = await self.framework.run_spike_test(
            initial_users=10,
            spike_users=100,
            spike_duration=30,  # 30 seconds to spike
            total_duration=600,  # 10 minutes total
        )

        # Check system handles spike gracefully
        passed = (
            metrics.error_rate < 0.05  # 5% error rate during spike
            and metrics.p95_response_time < 10000  # 10s during spike
        )

        self.results.append({"phase": "spike_test", "metrics": metrics, "passed": passed})

        logger.info(
            f"{'✅' if passed else '❌'} Spike test: P95={metrics.p95_response_time:.0f}ms, Errors={metrics.error_rate * 100:.2f}%"
        )

    async def _italian_market_phase(self):
        """Phase 7: Italian market specific testing"""
        logger.info("\n🇮🇹 Phase 7: Italian Market Specific Tests")

        # Tax calculation focused test
        tax_metrics = await self.framework.run_test(users=30, duration=300, scenario="italian_tax", ramp_up=60)

        # Document processing test
        doc_metrics = await self.framework.run_test(
            users=20,  # Lower concurrency for document processing
            duration=300,
            scenario="document_heavy",
            ramp_up=60,
        )

        tax_passed = tax_metrics.p95_response_time < 2000  # 2s for tax calculations
        doc_passed = doc_metrics.p95_response_time < 30000  # 30s for document processing

        self.results.append(
            {
                "phase": "italian_market",
                "tax_metrics": tax_metrics,
                "doc_metrics": doc_metrics,
                "tax_passed": tax_passed,
                "doc_passed": doc_passed,
                "passed": tax_passed and doc_passed,
            }
        )

        logger.info(f"{'✅' if tax_passed else '❌'} Tax calculations: P95={tax_metrics.p95_response_time:.0f}ms")
        logger.info(f"{'✅' if doc_passed else '❌'} Document processing: P95={doc_metrics.p95_response_time:.0f}ms")

    async def _health_check(self) -> bool:
        """Perform system health check before testing"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def _evaluate_test_results(self, metrics, config) -> bool:
        """Evaluate if test results meet SLA requirements"""
        # Basic SLA checks
        if metrics.error_rate > 0.02:  # 2% max error rate
            return False

        # Response time based on user count
        if config.target_users <= 1:
            return metrics.p95_response_time < 3000
        elif config.target_users <= 50:
            return metrics.p95_response_time < 5000
        else:
            return metrics.p95_response_time < 8000

    async def _generate_report(self, start_time: datetime) -> dict[str, Any]:
        """Generate comprehensive test report"""
        logger.info("\n📝 Phase 8: Generating Comprehensive Report")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Analyze all results
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.get("passed", False))

        # Check critical test (target load)
        critical_test = next((r for r in self.results if r.get("critical")), None)
        can_handle_50_users = critical_test["passed"] if critical_test else False

        # Find stress test result
        stress_test = next((r for r in self.results if r.get("phase") == "stress_test"), None)
        can_handle_100_users = stress_test["passed"] if stress_test else False

        # Collect all bottlenecks
        all_bottlenecks = []
        all_recommendations = []

        for result in self.results:
            if "metrics" in result:
                bottlenecks = self.framework.identify_bottlenecks(result["metrics"])
                recommendations = self.framework.generate_scaling_recommendations(result["metrics"])
                all_bottlenecks.extend(bottlenecks)
                all_recommendations.extend(recommendations)

        report = {
            "test_suite_summary": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": duration / 60,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "overall_passed": self.overall_passed and can_handle_50_users,
            },
            "key_requirements": {
                "can_handle_50_users": can_handle_50_users,
                "can_handle_100_users": can_handle_100_users,
                "target_arr_supported": can_handle_50_users,  # €25k ARR = ~50 users
            },
            "performance_summary": self._summarize_performance(),
            "bottlenecks": [asdict(b) for b in all_bottlenecks],
            "recommendations": [asdict(r) for r in all_recommendations],
            "detailed_results": self.results,
            "next_steps": self._generate_next_steps(),
        }

        return report

    def _summarize_performance(self) -> dict[str, Any]:
        """Summarize performance across all tests"""
        all_response_times = []
        all_error_rates = []
        all_throughputs = []

        for result in self.results:
            if "metrics" in result:
                metrics = result["metrics"]
                all_response_times.append(metrics.p95_response_time)
                all_error_rates.append(metrics.error_rate)
                all_throughputs.append(metrics.throughput)

        return {
            "avg_p95_response_time": sum(all_response_times) / len(all_response_times) if all_response_times else 0,
            "max_p95_response_time": max(all_response_times) if all_response_times else 0,
            "avg_error_rate": sum(all_error_rates) / len(all_error_rates) if all_error_rates else 0,
            "max_error_rate": max(all_error_rates) if all_error_rates else 0,
            "avg_throughput": sum(all_throughputs) / len(all_throughputs) if all_throughputs else 0,
            "max_throughput": max(all_throughputs) if all_throughputs else 0,
        }

    def _generate_next_steps(self) -> list[str]:
        """Generate recommended next steps based on results"""
        steps = []

        if self.overall_passed:
            steps.extend(
                [
                    "✅ System is ready for 50+ concurrent users",
                    "✅ Can support €25k ARR target",
                    "🔄 Schedule monthly load testing",
                    "📊 Monitor production metrics closely",
                    "🚀 Plan for 100+ user capacity if needed",
                ]
            )
        else:
            steps.extend(
                [
                    "❌ System needs optimization before production",
                    "🔧 Address identified bottlenecks",
                    "🔄 Re-run tests after optimizations",
                    "📈 Consider infrastructure scaling",
                    "⏰ Postpone production launch until tests pass",
                ]
            )

        return steps

    async def _save_results(self, report: dict[str, Any]):
        """Save test results and generate artifacts"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = Path("load_test_results")
        results_dir.mkdir(exist_ok=True)

        # Save JSON report
        report_file = results_dir / f"load_test_report_{timestamp}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        # Generate summary report
        summary_file = results_dir / f"load_test_summary_{timestamp}.md"
        await self._generate_markdown_summary(report, summary_file)

        logger.info(f"📄 Detailed report saved: {report_file}")
        logger.info(f"📄 Summary report saved: {summary_file}")

        # Print final summary
        self._print_final_summary(report)

    async def _generate_markdown_summary(self, report: dict[str, Any], output_file: Path):
        """Generate markdown summary report"""
        summary = f"""# PratikoAI Load Testing Report

## Test Summary
- **Date**: {report["test_suite_summary"]["start_time"][:10]}
- **Duration**: {report["test_suite_summary"]["duration_minutes"]:.1f} minutes
- **Tests Passed**: {report["test_suite_summary"]["passed_tests"]}/{report["test_suite_summary"]["total_tests"]}
- **Overall Result**: {"✅ PASSED" if report["test_suite_summary"]["overall_passed"] else "❌ FAILED"}

## Key Requirements
- **Can handle 50 users**: {"✅ YES" if report["key_requirements"]["can_handle_50_users"] else "❌ NO"}
- **Can handle 100 users**: {"✅ YES" if report["key_requirements"]["can_handle_100_users"] else "❌ NO"}
- **€25k ARR supported**: {"✅ YES" if report["key_requirements"]["target_arr_supported"] else "❌ NO"}

## Performance Summary
- **Average P95 Response Time**: {report["performance_summary"]["avg_p95_response_time"]:.0f}ms
- **Maximum P95 Response Time**: {report["performance_summary"]["max_p95_response_time"]:.0f}ms
- **Average Error Rate**: {report["performance_summary"]["avg_error_rate"] * 100:.2f}%
- **Maximum Throughput**: {report["performance_summary"]["max_throughput"]:.0f} req/min

## Bottlenecks Identified
"""

        for bottleneck in report["bottlenecks"]:
            summary += f"- **{bottleneck['type']}** ({bottleneck['severity']}): {bottleneck['description']}\n"

        summary += "\n## Recommendations\n"
        for rec in report["recommendations"]:
            summary += f"- **{rec['component']}**: {rec['recommended_capacity']} (Priority: {rec['priority']})\n"

        summary += "\n## Next Steps\n"
        for step in report["next_steps"]:
            summary += f"- {step}\n"

        with open(output_file, "w") as f:
            f.write(summary)

    def _print_final_summary(self, report: dict[str, Any]):
        """Print final test summary to console"""
        logger.info("\n" + "=" * 60)
        logger.info("🏁 LOAD TESTING COMPLETE")
        logger.info("=" * 60)

        if report["test_suite_summary"]["overall_passed"]:
            logger.info("🎉 RESULT: PASSED")
            logger.info("✅ System can handle 50+ concurrent users")
            logger.info("✅ Ready to support €25k ARR target")
        else:
            logger.info("❌ RESULT: FAILED")
            logger.info("⚠️  System needs optimization before production")

        logger.info(
            f"📊 Tests: {report['test_suite_summary']['passed_tests']}/{report['test_suite_summary']['total_tests']} passed"
        )
        logger.info(f"⏱️  Duration: {report['test_suite_summary']['duration_minutes']:.1f} minutes")

        if report["bottlenecks"]:
            logger.info(f"🔍 Bottlenecks found: {len(report['bottlenecks'])}")

        logger.info("=" * 60)


async def main():
    """Main entry point for load testing"""
    parser = argparse.ArgumentParser(description="PratikoAI Load Testing Suite")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL to test")
    parser.add_argument("--profile", type=str, choices=[p.value for p in LoadTestProfile], help="Load test profile")
    parser.add_argument("--users", type=int, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, help="Test duration in seconds")
    parser.add_argument("--full-suite", action="store_true", help="Run complete test suite")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    runner = LoadTestRunner(base_url=args.base_url)

    try:
        if args.full_suite:
            # Run complete test suite
            report = await runner.run_full_suite()
            sys.exit(0 if report["test_suite_summary"]["overall_passed"] else 1)

        elif args.profile:
            # Run single profile test
            profile = LoadTestProfile(args.profile)
            result = await runner.run_single_test(profile)
            print(json.dumps(result, indent=2, default=str))
            sys.exit(0 if result["passed"] else 1)

        elif args.users and args.duration:
            # Run custom test
            custom_config = {"target_users": args.users, "test_duration": args.duration}
            result = await runner.run_single_test(LoadTestProfile.NORMAL_DAY, custom_config)
            print(json.dumps(result, indent=2, default=str))
            sys.exit(0 if result["passed"] else 1)

        else:
            parser.print_help()
            sys.exit(1)

    except Exception as e:
        logger.error(f"Load testing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
