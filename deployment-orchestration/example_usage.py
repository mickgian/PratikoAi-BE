#!/usr/bin/env python3
"""Example Usage of Intelligent Deployment System
==============================================

This script demonstrates various ways to use the intelligent deployment system,
showcasing different scenarios and features.

Run this script to see the system in action with simulated deployments.
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

# Import our intelligent deployment system
from adaptive_deployment_engine import AdaptiveDeploymentEngine, DeploymentStrategy, EnvironmentType


async def example_basic_deployment():
    """Example 1: Basic deployment with automatic strategy selection."""
    print("\n" + "=" * 60)
    print("🚀 EXAMPLE 1: Basic Deployment")
    print("=" * 60)

    # Initialize the deployment engine
    engine = AdaptiveDeploymentEngine()

    # Define services to deploy
    services = ["user-service", "notification-service"]

    print(f"Deploying services: {', '.join(services)}")
    print("Strategy: Automatic selection based on ML prediction")

    # Execute deployment
    result = await engine.execute_adaptive_deployment(target_services=services, deployment_size="medium")

    # Display results
    print("\n📊 Results:")
    print(f"   Success: {result.success}")
    print(f"   Duration: {result.duration_minutes:.1f} minutes")
    print(f"   Strategy Used: {result.strategy}")
    print(f"   Environment: {result.environment}")

    if result.error_message:
        print(f"   Error: {result.error_message}")

    return result


async def example_forced_strategy():
    """Example 2: Deployment with forced strategy."""
    print("\n" + "=" * 60)
    print("⚡ EXAMPLE 2: Forced Strategy Deployment")
    print("=" * 60)

    engine = AdaptiveDeploymentEngine()
    services = ["api-gateway", "auth-service"]

    print(f"Deploying services: {', '.join(services)}")
    print("Strategy: Forced AGGRESSIVE for maximum speed")

    # Execute with forced aggressive strategy
    result = await engine.execute_adaptive_deployment(
        target_services=services, deployment_size="small", force_strategy=DeploymentStrategy.AGGRESSIVE
    )

    print("\n📊 Results:")
    print(f"   Success: {result.success}")
    print(f"   Duration: {result.duration_minutes:.1f} minutes")
    print(f"   Strategy Used: {result.strategy}")

    return result


async def example_time_constrained():
    """Example 3: Time-constrained deployment."""
    print("\n" + "=" * 60)
    print("⏰ EXAMPLE 3: Time-Constrained Deployment")
    print("=" * 60)

    engine = AdaptiveDeploymentEngine()
    services = ["web-frontend", "static-assets"]

    print(f"Deploying services: {', '.join(services)}")
    print("Time Constraint: Maximum 20 minutes")

    # Execute with time constraint
    result = await engine.execute_adaptive_deployment(
        target_services=services,
        deployment_size="large",
        time_constraints=20,  # 20 minute maximum
    )

    print("\n📊 Results:")
    print(f"   Success: {result.success}")
    print(f"   Duration: {result.duration_minutes:.1f} minutes")
    print("   Time Constraint: 20 minutes")
    print(f"   Constraint Met: {result.duration_minutes <= 20}")

    return result


async def example_comprehensive_analysis():
    """Example 4: Comprehensive deployment with full analysis."""
    print("\n" + "=" * 60)
    print("📈 EXAMPLE 4: Comprehensive Analysis")
    print("=" * 60)

    engine = AdaptiveDeploymentEngine()
    services = ["order-service", "payment-service", "inventory-service"]

    print(f"Deploying services: {', '.join(services)}")
    print("Analysis: Full system analysis with detailed reporting")

    # Execute deployment
    result = await engine.execute_adaptive_deployment(target_services=services, deployment_size="large")

    # Generate comprehensive report
    report = engine.generate_deployment_report(result)

    print("\n📊 Deployment Results:")
    print(f"   Success: {result.success}")
    print(f"   Duration: {result.duration_minutes:.1f} minutes")
    print(f"   Strategy: {result.strategy}")
    print(f"   Services: {len(result.services_deployed)} deployed")

    print("\n🧠 Decision Analysis:")
    decision_count = len(report.get("decision_process", []))
    print(f"   Total Decisions Made: {decision_count}")

    # Show key decisions
    if "decision_process" in report:
        key_decisions = [
            d
            for d in report["decision_process"]
            if d["decision_type"] in ["strategy_predicted", "environment_detected", "resource_allocation"]
        ]
        for decision in key_decisions[:3]:  # Show first 3 key decisions
            print(f"   • {decision['decision_type']}: {decision['timestamp']}")

    print("\n💡 Recommendations:")
    for rec in report.get("recommendations", [])[:3]:  # Show top 3
        print(f"   • {rec}")

    print("\n🎓 Lessons Learned:")
    for lesson in report.get("lessons_learned", [])[:3]:  # Show top 3
        print(f"   • {lesson}")

    return result, report


async def example_learning_demonstration():
    """Example 5: Demonstrate machine learning capabilities."""
    print("\n" + "=" * 60)
    print("🧠 EXAMPLE 5: Machine Learning Demonstration")
    print("=" * 60)

    engine = AdaptiveDeploymentEngine()

    print("Simulating multiple deployments to demonstrate learning...")

    # Simulate several deployments to build training data
    scenarios = [
        {"services": ["service-a"], "size": "small", "description": "Small deployment"},
        {"services": ["service-b", "service-c"], "size": "medium", "description": "Medium deployment"},
        {"services": ["service-d", "service-e", "service-f"], "size": "large", "description": "Large deployment"},
        {"services": ["critical-service"], "size": "small", "description": "Critical service"},
        {"services": ["batch-processor"], "size": "medium", "description": "Background service"},
    ]

    results = []

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📦 Deployment {i}/5: {scenario['description']}")

        result = await engine.execute_adaptive_deployment(
            target_services=scenario["services"], deployment_size=scenario["size"]
        )

        results.append(result)

        print(f"   Result: {'✅ Success' if result.success else '❌ Failed'}")
        print(f"   Strategy: {result.strategy}")
        print(f"   Duration: {result.duration_minutes:.1f}min")

        # Small delay between deployments
        await asyncio.sleep(1)

    # Analyze learning progress
    print("\n🎯 Learning Analysis:")
    success_rate = sum(1 for r in results if r.success) / len(results)
    avg_duration = sum(r.duration_minutes for r in results) / len(results)
    strategies_used = [r.strategy for r in results]

    print(f"   Overall Success Rate: {success_rate:.1%}")
    print(f"   Average Duration: {avg_duration:.1f} minutes")
    print(f"   Strategies Used: {', '.join(set(strategies_used))}")

    # Check if ML model was trained
    if engine.ml_optimizer.model_trained:
        print("   🧠 ML Model Status: Trained and active")
    else:
        print("   🧠 ML Model Status: Learning (need more data)")

    return results


async def example_system_monitoring():
    """Example 6: System monitoring and diagnostics."""
    print("\n" + "=" * 60)
    print("📊 EXAMPLE 6: System Monitoring & Diagnostics")
    print("=" * 60)

    engine = AdaptiveDeploymentEngine()

    # Get current system metrics
    print("🔍 Current System State:")
    metrics = await engine.system_monitor.get_current_metrics()

    print(f"   CPU Usage: {metrics.cpu_percent:.1f}%")
    print(f"   Memory Usage: {metrics.memory_percent:.1f}%")
    print(f"   Disk Usage: {metrics.disk_usage_percent:.1f}%")
    print(f"   Network Latency: {metrics.network_latency:.0f}ms")
    print(f"   Available Memory: {metrics.available_memory_gb:.1f}GB")
    print(f"   Free Disk: {metrics.free_disk_gb:.1f}GB")

    # Environment detection
    print("\n🌍 Environment Detection:")
    environment = await engine.env_detector.detect_environment()
    print(f"   Detected Environment: {environment.value.upper()}")

    # System trend analysis
    print("\n📈 System Trend Analysis:")
    # Collect a few metrics for trend analysis
    for _i in range(3):
        await engine.system_monitor.get_current_metrics()
        await asyncio.sleep(1)

    trend = engine.system_monitor.get_system_trend(minutes=1)
    trend_emoji = {"increasing": "📈", "decreasing": "📉", "stable": "📊"}
    print(f"   Trend: {trend_emoji.get(trend['trend'], '📊')} {trend['trend'].upper()}")
    print(f"   Confidence: {trend['confidence']:.1f}")

    # Deployment readiness assessment
    print("\n🚀 Deployment Readiness:")

    readiness_issues = []

    if metrics.cpu_percent > 80:
        readiness_issues.append("High CPU usage")
    if metrics.memory_percent > 85:
        readiness_issues.append("High memory usage")
    if metrics.disk_usage_percent > 90:
        readiness_issues.append("Low disk space")
    if metrics.network_latency > 500:
        readiness_issues.append("High network latency")

    if not readiness_issues:
        print("   ✅ System ready for deployment")
    else:
        print("   ⚠️  Issues detected:")
        for issue in readiness_issues:
            print(f"      • {issue}")


async def main():
    """Run all examples to demonstrate the intelligent deployment system."""
    # Configure logging for examples
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise for examples
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    print("🎯 INTELLIGENT DEPLOYMENT SYSTEM - EXAMPLES")
    print("=" * 80)
    print("This demonstration shows various capabilities of the adaptive deployment engine.")
    print("All deployments are simulated and safe to run.")

    try:
        # Run system monitoring first
        await example_system_monitoring()

        # Run deployment examples
        await example_basic_deployment()
        await example_forced_strategy()
        await example_time_constrained()

        # Run comprehensive analysis
        result, report = await example_comprehensive_analysis()

        # Demonstrate learning capabilities
        await example_learning_demonstration()

        print("\n" + "=" * 80)
        print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 80)

        print("\n💡 Next Steps:")
        print("   • Review generated reports in deployment_reports/")
        print("   • Check deployment logs in deployment_logs/")
        print("   • Try the CLI: python intelligent_deploy.py --help")
        print("   • Customize configuration in deployment_config.yaml")

        print("\n📁 Generated Files:")
        reports_dir = Path("deployment_reports")
        if reports_dir.exists():
            report_files = list(reports_dir.glob("*.json"))
            print(f"   • {len(report_files)} deployment reports")

        logs_dir = Path("deployment_logs")
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.log"))
            print(f"   • {len(log_files)} deployment logs")

        data_dir = Path("deployment_data")
        if data_dir.exists():
            print("   • ML model data in deployment_data/")

    except KeyboardInterrupt:
        print("\n⚠️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Example execution failed: {e}")
        logging.exception("Example execution failed")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
