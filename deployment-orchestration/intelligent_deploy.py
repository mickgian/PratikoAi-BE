#!/usr/bin/env python3
"""Intelligent Deployment Orchestration Script
===========================================

This script provides a command-line interface to the Adaptive Deployment Engine,
enabling intelligent, self-learning deployments across different environments.

Features:
- Automatic environment detection and adaptation
- Machine learning-based strategy optimization
- Real-time system monitoring and resource adjustment
- Comprehensive decision logging and reporting
- Integration with existing CI/CD pipelines

Usage Examples:
    # Basic deployment with auto-detection
    python intelligent_deploy.py --services api-service web-frontend

    # Force specific strategy
    python intelligent_deploy.py --services api-service --strategy aggressive

    # Time-constrained deployment
    python intelligent_deploy.py --services api-service --max-time 30

    # Generate report for previous deployment
    python intelligent_deploy.py --report deploy_1234567890
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Import our adaptive deployment engine
from adaptive_deployment_engine import AdaptiveDeploymentEngine, DeploymentStrategy, EnvironmentType


class IntelligentDeploymentCLI:
    """Command-line interface for intelligent deployments.

    This class provides a user-friendly interface to the adaptive deployment
    engine, handling argument parsing, progress reporting, and result formatting.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.engine = AdaptiveDeploymentEngine()

    def setup_logging(self, verbose: bool = False):
        """Configure logging based on verbosity level."""
        level = logging.DEBUG if verbose else logging.INFO

        # Configure console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # Configure file handler
        log_file = Path("deployment_logs") / f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_file.parent.mkdir(exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Create formatters
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
        file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        self.logger.info(f"Logging configured. Full logs available at: {log_file}")

    async def deploy_services(
        self,
        services: list[str],
        deployment_size: str = "medium",
        max_time_minutes: int | None = None,
        force_strategy: str | None = None,
        dry_run: bool = False,
        interactive: bool = False,
    ) -> bool:
        """Execute intelligent deployment of specified services.

        Args:
            services: List of service names to deploy
            deployment_size: Size of deployment (small, medium, large)
            max_time_minutes: Maximum deployment time constraint
            force_strategy: Override ML strategy selection
            dry_run: Simulate deployment without executing
            interactive: Enable interactive decision confirmation

        Returns:
            bool: True if deployment successful, False otherwise
        """
        # Validate inputs
        if not services:
            self.logger.error("No services specified for deployment")
            return False

        if deployment_size not in ["small", "medium", "large"]:
            self.logger.error(f"Invalid deployment size: {deployment_size}")
            return False

        # Convert strategy string to enum
        strategy_enum = None
        if force_strategy:
            try:
                strategy_enum = DeploymentStrategy(force_strategy.lower())
            except ValueError:
                self.logger.error(f"Invalid strategy: {force_strategy}")
                return False

        self.logger.info("🚀 Starting Intelligent Deployment Process")
        self.logger.info(f"Services: {', '.join(services)}")
        self.logger.info(f"Deployment Size: {deployment_size}")

        if max_time_minutes:
            self.logger.info(f"Time Constraint: {max_time_minutes} minutes")

        if force_strategy:
            self.logger.info(f"Forced Strategy: {force_strategy}")

        if dry_run:
            self.logger.info("🔍 DRY RUN MODE - No actual deployment will occur")

        try:
            # Phase 1: Environment Analysis
            print("\n" + "=" * 60)
            print("🔍 PHASE 1: ENVIRONMENT ANALYSIS")
            print("=" * 60)

            # Pre-deployment system analysis
            environment = await self.engine.env_detector.detect_environment()
            current_metrics = await self.engine.system_monitor.get_current_metrics()

            print(f"📍 Environment: {environment.value.upper()}")
            print(
                f"💻 System Load: CPU {current_metrics.cpu_percent:.1f}%, "
                f"Memory {current_metrics.memory_percent:.1f}%, "
                f"Disk {current_metrics.disk_usage_percent:.1f}%"
            )
            print(f"🌐 Network Latency: {current_metrics.network_latency:.0f}ms")
            print(
                f"💾 Available Resources: {current_metrics.available_memory_gb:.1f}GB RAM, "
                f"{current_metrics.free_disk_gb:.1f}GB disk"
            )

            # Get system trend analysis
            trend = self.engine.system_monitor.get_system_trend()
            trend_emoji = {"increasing": "📈", "decreasing": "📉", "stable": "📊"}
            print(
                f"📊 System Trend: {trend_emoji.get(trend['trend'], '📊')} {trend['trend'].upper()} "
                f"(confidence: {trend['confidence']:.1f})"
            )

            # Interactive confirmation if requested
            if interactive and not dry_run:
                response = input("\n❓ Continue with deployment? (y/N): ").strip().lower()
                if response != "y":
                    print("❌ Deployment cancelled by user")
                    return False

            # Phase 2: Strategy Selection
            print("\n" + "=" * 60)
            print("🧠 PHASE 2: STRATEGY OPTIMIZATION")
            print("=" * 60)

            if dry_run:
                # In dry run, just show what would be selected
                print("🔮 Analyzing optimal deployment strategy...")

                # Mock strategy prediction for dry run
                if force_strategy:
                    selected_strategy = strategy_enum
                    confidence = 1.0
                else:
                    # Simple heuristic for dry run
                    if environment == EnvironmentType.PRODUCTION:
                        selected_strategy = DeploymentStrategy.CONSERVATIVE
                        confidence = 0.8
                    elif current_metrics.cpu_percent > 70:
                        selected_strategy = DeploymentStrategy.BALANCED
                        confidence = 0.7
                    else:
                        selected_strategy = DeploymentStrategy.AGGRESSIVE
                        confidence = 0.6

                print(f"🎯 Selected Strategy: {selected_strategy.value.upper()}")
                print(f"🎲 Confidence Score: {confidence:.1f}")
                print(f"📋 Reasoning: {'User override' if force_strategy else 'ML prediction (simulated)'}")

                # Show what resources would be allocated
                print("\n📊 Resource Allocation (Simulated):")
                print("   • CPU Limit: 70%")
                print("   • Memory Limit: 80%")
                print("   • Concurrency: 4 processes")
                print("   • Timeout: 60 minutes")

                print(f"\n⏱️  Estimated Duration: {25 + len(services) * 5} minutes")
                print("✅ Pre-deployment Validation: PASSED (simulated)")

                print("\n🔍 DRY RUN COMPLETE - No actual deployment performed")
                return True

            # Phase 3: Actual Deployment Execution
            print("\n" + "=" * 60)
            print("⚡ PHASE 3: DEPLOYMENT EXECUTION")
            print("=" * 60)

            # Execute the adaptive deployment
            time.time()

            deployment_record = await self.engine.execute_adaptive_deployment(
                target_services=services,
                deployment_size=deployment_size,
                time_constraints=max_time_minutes,
                force_strategy=strategy_enum,
            )

            time.time()

            # Phase 4: Results and Analysis
            print("\n" + "=" * 60)
            print("📊 PHASE 4: RESULTS & ANALYSIS")
            print("=" * 60)

            # Display deployment results
            success_emoji = "✅" if deployment_record.success else "❌"
            print(f"{success_emoji} Deployment Status: {'SUCCESS' if deployment_record.success else 'FAILED'}")
            print(f"⏱️  Total Duration: {deployment_record.duration_minutes:.1f} minutes")
            print(f"🎯 Strategy Used: {deployment_record.strategy.upper()}")
            print(f"🔄 Rollback Required: {'Yes' if deployment_record.rollback_required else 'No'}")

            if deployment_record.error_message:
                print(f"💥 Error Details: {deployment_record.error_message}")

            # Resource usage summary
            if deployment_record.resource_usage:
                print("\n📈 Resource Usage:")
                for key, value in deployment_record.resource_usage.items():
                    if isinstance(value, int | float):
                        print(f"   • {key.replace('_', ' ').title()}: {value:.1f}")
                    else:
                        print(f"   • {key.replace('_', ' ').title()}: {value}")

            # Generate and display comprehensive report
            report = self.engine.generate_deployment_report(deployment_record)

            if report.get("recommendations"):
                print("\n💡 Recommendations:")
                for rec in report["recommendations"][:3]:  # Show top 3
                    print(f"   • {rec}")

            if report.get("lessons_learned"):
                print("\n🎓 Key Lessons Learned:")
                for lesson in report["lessons_learned"][:3]:  # Show top 3
                    print(f"   • {lesson}")

            # Save detailed report
            report_file = self._save_deployment_report(deployment_record, report)
            print(f"\n📄 Detailed report saved: {report_file}")

            return deployment_record.success

        except KeyboardInterrupt:
            print("\n⚠️  Deployment interrupted by user")
            return False
        except Exception as e:
            self.logger.error(f"Deployment failed with unexpected error: {e}")
            return False

    def _save_deployment_report(self, deployment_record, report) -> Path:
        """Save comprehensive deployment report to file."""
        reports_dir = Path("deployment_reports")
        reports_dir.mkdir(exist_ok=True)

        report_file = reports_dir / f"deployment_report_{deployment_record.id}.json"

        # Prepare report data for JSON serialization
        report_data = {
            "deployment_record": {
                "id": deployment_record.id,
                "timestamp": deployment_record.timestamp.isoformat(),
                "environment": deployment_record.environment,
                "strategy": deployment_record.strategy,
                "duration_minutes": deployment_record.duration_minutes,
                "success": deployment_record.success,
                "resource_usage": deployment_record.resource_usage,
                "error_message": deployment_record.error_message,
                "system_state_before": deployment_record.system_state_before,
                "system_state_after": deployment_record.system_state_after,
                "services_deployed": deployment_record.services_deployed,
                "rollback_required": deployment_record.rollback_required,
            },
            "report": report,
        }

        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2, default=str)

        return report_file

    async def show_deployment_report(self, deployment_id: str):
        """Display detailed report for a specific deployment."""
        report_file = Path("deployment_reports") / f"deployment_report_{deployment_id}.json"

        if not report_file.exists():
            print(f"❌ Report not found for deployment ID: {deployment_id}")
            return

        try:
            with open(report_file) as f:
                data = json.load(f)

            record = data["deployment_record"]
            report = data["report"]

            print("\n" + "=" * 60)
            print(f"📊 DEPLOYMENT REPORT: {deployment_id}")
            print("=" * 60)

            # Basic information
            print(f"🕐 Timestamp: {record['timestamp']}")
            print(f"🌍 Environment: {record['environment'].upper()}")
            print(f"🎯 Strategy: {record['strategy'].upper()}")
            print(f"⏱️  Duration: {record['duration_minutes']:.1f} minutes")
            print(f"✅ Success: {record['success']}")
            print(f"🔧 Services: {', '.join(record['services_deployed'])}")

            if record["error_message"]:
                print(f"💥 Error: {record['error_message']}")

            # Performance analysis
            if "performance_analysis" in report:
                perf = report["performance_analysis"]
                print("\n📈 Performance Analysis:")
                print(f"   • Duration Performance: {perf.get('duration_performance', 'unknown').upper()}")
                print(f"   • Expected Duration: {perf.get('benchmark_duration', 0):.1f} minutes")
                print(f"   • Actual Duration: {perf.get('actual_duration', 0):.1f} minutes")
                print(f"   • Variance: {perf.get('duration_variance', 0):+.1f} minutes")

            # System impact
            if "system_impact" in report:
                impact = report["system_impact"]
                print("\n💻 System Impact:")
                print(f"   • CPU Impact: {impact.get('cpu_impact_percent', 0):+.1f}%")
                print(f"   • Memory Impact: {impact.get('memory_impact_percent', 0):+.1f}%")
                print(f"   • Overall Impact: {impact.get('overall_impact', 'unknown').upper()}")

            # Decision process summary
            if "decision_process" in report:
                decisions = report["decision_process"]
                print("\n🧠 Key Decisions Made:")
                for decision in decisions[:5]:  # Show first 5 decisions
                    print(f"   • {decision['decision_type']}: {decision['timestamp']}")

            # Recommendations
            if report.get("recommendations"):
                print("\n💡 All Recommendations:")
                for i, rec in enumerate(report["recommendations"], 1):
                    print(f"   {i}. {rec}")

            # Lessons learned
            if report.get("lessons_learned"):
                print("\n🎓 Lessons Learned:")
                for i, lesson in enumerate(report["lessons_learned"], 1):
                    print(f"   {i}. {lesson}")

        except Exception as e:
            print(f"❌ Error reading report: {e}")

    async def list_recent_deployments(self, limit: int = 10):
        """List recent deployments with basic information."""
        reports_dir = Path("deployment_reports")

        if not reports_dir.exists():
            print("📭 No deployment reports found")
            return

        # Get all report files sorted by modification time
        report_files = sorted(
            reports_dir.glob("deployment_report_*.json"), key=lambda x: x.stat().st_mtime, reverse=True
        )[:limit]

        if not report_files:
            print("📭 No deployment reports found")
            return

        print("\n" + "=" * 80)
        print(f"📋 RECENT DEPLOYMENTS (Last {len(report_files)})")
        print("=" * 80)
        print(f"{'ID':<15} {'Timestamp':<20} {'Env':<12} {'Strategy':<12} {'Duration':<10} {'Status':<8}")
        print("-" * 80)

        for report_file in report_files:
            try:
                with open(report_file) as f:
                    data = json.load(f)

                record = data["deployment_record"]

                # Extract deployment ID from filename
                deploy_id = report_file.stem.replace("deployment_report_", "")
                timestamp = datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d %H:%M")
                env = record["environment"][:10]
                strategy = record["strategy"][:10]
                duration = f"{record['duration_minutes']:.1f}m"
                status = "✅ PASS" if record["success"] else "❌ FAIL"

                print(f"{deploy_id:<15} {timestamp:<20} {env:<12} {strategy:<12} {duration:<10} {status:<8}")

            except Exception as e:
                print(f"❌ Error reading {report_file.name}: {e}")

    async def run_system_diagnostics(self):
        """Run comprehensive system diagnostics for deployment readiness."""
        print("\n" + "=" * 60)
        print("🔍 SYSTEM DIAGNOSTICS")
        print("=" * 60)

        # Environment detection
        print("🌍 Environment Detection:")
        environment = await self.engine.env_detector.detect_environment()
        print(f"   Detected Environment: {environment.value.upper()}")

        # System metrics
        print("\n💻 System Metrics:")
        metrics = await self.engine.system_monitor.get_current_metrics()

        # CPU status
        cpu_status = (
            "🟢 Good" if metrics.cpu_percent < 70 else "🟡 High" if metrics.cpu_percent < 85 else "🔴 Critical"
        )
        print(f"   CPU Usage: {metrics.cpu_percent:.1f}% {cpu_status}")

        # Memory status
        mem_status = (
            "🟢 Good" if metrics.memory_percent < 75 else "🟡 High" if metrics.memory_percent < 90 else "🔴 Critical"
        )
        print(f"   Memory Usage: {metrics.memory_percent:.1f}% {mem_status}")

        # Disk status
        disk_status = (
            "🟢 Good"
            if metrics.disk_usage_percent < 80
            else "🟡 High"
            if metrics.disk_usage_percent < 95
            else "🔴 Critical"
        )
        print(f"   Disk Usage: {metrics.disk_usage_percent:.1f}% {disk_status}")

        # Network status
        net_status = (
            "🟢 Good" if metrics.network_latency < 100 else "🟡 Slow" if metrics.network_latency < 500 else "🔴 Poor"
        )
        print(f"   Network Latency: {metrics.network_latency:.0f}ms {net_status}")

        # Available resources
        print("\n📊 Available Resources:")
        print(f"   Available Memory: {metrics.available_memory_gb:.1f} GB")
        print(f"   Free Disk Space: {metrics.free_disk_gb:.1f} GB")

        # System trend
        trend = self.engine.system_monitor.get_system_trend()
        trend_status = {
            "increasing": "🔴 Load Increasing",
            "decreasing": "🟢 Load Decreasing",
            "stable": "🟡 Load Stable",
        }
        print(
            f"\n📈 System Trend: {trend_status.get(trend['trend'], '❓ Unknown')} (confidence: {trend['confidence']:.1f})"
        )

        # Deployment readiness assessment
        print("\n🚀 Deployment Readiness Assessment:")

        readiness_score = 0
        max_score = 5

        if metrics.cpu_percent < 85:
            readiness_score += 1
            print("   ✅ CPU utilization acceptable")
        else:
            print("   ❌ CPU utilization too high")

        if metrics.memory_percent < 90:
            readiness_score += 1
            print("   ✅ Memory utilization acceptable")
        else:
            print("   ❌ Memory utilization too high")

        if metrics.disk_usage_percent < 95:
            readiness_score += 1
            print("   ✅ Disk space sufficient")
        else:
            print("   ❌ Disk space critically low")

        if metrics.network_latency < 500:
            readiness_score += 1
            print("   ✅ Network latency acceptable")
        else:
            print("   ❌ Network latency too high")

        if metrics.available_memory_gb > 0.5:
            readiness_score += 1
            print("   ✅ Sufficient available memory")
        else:
            print("   ❌ Insufficient available memory")

        # Overall readiness
        readiness_percent = (readiness_score / max_score) * 100

        if readiness_percent >= 80:
            readiness_status = "🟢 READY"
        elif readiness_percent >= 60:
            readiness_status = "🟡 CAUTION"
        else:
            readiness_status = "🔴 NOT READY"

        print(f"\n🎯 Overall Readiness: {readiness_status} ({readiness_percent:.0f}%)")

        if readiness_percent < 80:
            print("\n💡 Recommendations:")
            if metrics.cpu_percent >= 85:
                print("   • Wait for CPU load to decrease before deploying")
            if metrics.memory_percent >= 90:
                print("   • Free up memory or use conservative deployment strategy")
            if metrics.disk_usage_percent >= 95:
                print("   • Clean up disk space before deployment")
            if metrics.network_latency >= 500:
                print("   • Check network connectivity and consider local deployment")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Intelligent Deployment Orchestration System",
        epilog="""
Examples:
  %(prog)s --services api-service web-frontend
  %(prog)s --services api-service --strategy aggressive --max-time 30
  %(prog)s --dry-run --services api-service web-frontend background-worker
  %(prog)s --report deploy_1234567890
  %(prog)s --diagnostics
  %(prog)s --list-deployments
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Main deployment options
    parser.add_argument("--services", "-s", nargs="+", help="Services to deploy (space-separated list)")

    parser.add_argument(
        "--deployment-size",
        choices=["small", "medium", "large"],
        default="medium",
        help="Deployment size (affects resource allocation)",
    )

    parser.add_argument(
        "--strategy",
        choices=["conservative", "balanced", "aggressive"],
        help="Force specific deployment strategy (overrides ML prediction)",
    )

    parser.add_argument("--max-time", type=int, metavar="MINUTES", help="Maximum deployment time in minutes")

    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate deployment without executing (useful for testing)"
    )

    parser.add_argument("--interactive", "-i", action="store_true", help="Enable interactive confirmation prompts")

    # Reporting and analysis options
    parser.add_argument("--report", metavar="DEPLOYMENT_ID", help="Show detailed report for specific deployment")

    parser.add_argument("--list-deployments", action="store_true", help="List recent deployments")

    parser.add_argument("--diagnostics", action="store_true", help="Run system diagnostics for deployment readiness")

    # General options
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    parser.add_argument("--config", type=Path, help="Path to custom configuration file")

    return parser


async def main():
    """Main entry point for the intelligent deployment CLI."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Initialize CLI
    cli = IntelligentDeploymentCLI()

    # Setup logging
    cli.setup_logging(verbose=args.verbose)

    # Override config path if provided
    if args.config:
        cli.engine.config_path = args.config
        cli.engine.config = cli.engine._load_configuration()

    try:
        # Handle different command modes
        if args.report:
            await cli.show_deployment_report(args.report)

        elif args.list_deployments:
            await cli.list_recent_deployments()

        elif args.diagnostics:
            await cli.run_system_diagnostics()

        elif args.services:
            # Main deployment execution
            success = await cli.deploy_services(
                services=args.services,
                deployment_size=args.deployment_size,
                max_time_minutes=args.max_time,
                force_strategy=args.strategy,
                dry_run=args.dry_run,
                interactive=args.interactive,
            )

            # Exit with appropriate code
            sys.exit(0 if success else 1)

        else:
            # No specific action provided, show help and run diagnostics
            parser.print_help()
            print("\n" + "=" * 60)
            print("🔍 Running quick system diagnostics...")
            await cli.run_system_diagnostics()

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(130)

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
