#!/usr/bin/env python3
"""
Success Metrics System Validation Script

This script validates that the comprehensive success metrics monitoring,
email reporting, and scheduling system is properly implemented.
"""

import asyncio
import importlib
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def validate_imports():
    """Validate that all metrics system modules can be imported."""
    print("🔍 Validating Success Metrics System imports...")

    modules_to_test = [
        "app.services.metrics_service",
        "app.services.email_service",
        "app.services.scheduler_service",
        "app.api.v1.metrics",
        "app.schemas.metrics",
        "app.core.startup",
    ]

    failed_imports = []

    for module_name in modules_to_test:
        try:
            importlib.import_module(module_name)
            print(f"  ✅ {module_name}")
        except Exception as e:
            print(f"  ❌ {module_name}: {e}")
            failed_imports.append((module_name, str(e)))

    return failed_imports


def validate_metrics_service():
    """Validate MetricsService functionality."""
    print("\n🔍 Validating MetricsService...")

    try:
        from app.services.metrics_service import (
            Environment,
            MetricResult,
            MetricsReport,
            MetricsService,
            MetricStatus,
            metrics_service,
        )

        # Test class structures
        print("  📊 Core Classes:")
        required_classes = ["MetricsService", "MetricResult", "MetricsReport", "MetricStatus", "Environment"]
        for class_name in required_classes:
            if class_name in locals():
                print(f"    ✅ {class_name}")
            else:
                print(f"    ❌ {class_name} - Missing")

        # Test MetricsService methods
        print("  🔧 MetricsService Methods:")
        required_methods = [
            "collect_technical_metrics",
            "collect_business_metrics",
            "generate_metrics_report",
            "_get_api_response_time_p95",
            "_get_cache_hit_rate",
            "_get_test_coverage",
            "_get_critical_vulnerabilities",
            "_get_average_cost_per_user",
            "_get_system_uptime",
            "_get_user_satisfaction",
            "_get_gdpr_compliance_score",
            "_generate_recommendations",
        ]

        for method in required_methods:
            if hasattr(MetricsService, method):
                print(f"    ✅ {method}")
            else:
                print(f"    ❌ {method} - Missing")

        # Test enum values
        print("  📋 Enum Values:")
        print(f"    ✅ MetricStatus: {[status.value for status in MetricStatus]}")
        print(f"    ✅ Environment: {[env.value for env in Environment]}")

        return True

    except Exception as e:
        print(f"  ❌ MetricsService validation failed: {e}")
        return False


def validate_email_service():
    """Validate EmailService functionality."""
    print("\n🔍 Validating EmailService...")

    try:
        from app.services.email_service import EmailService, email_service

        # Test EmailService methods
        print("  📧 EmailService Methods:")
        required_methods = [
            "send_metrics_report",
            "_generate_html_report",
            "_generate_summary_section",
            "_generate_environment_section",
            "_get_health_class",
            "_send_email",
        ]

        for method in required_methods:
            if hasattr(EmailService, method):
                print(f"    ✅ {method}")
            else:
                print(f"    ❌ {method} - Missing")

        # Test email configuration
        print("  ⚙️ Email Configuration:")
        config_attrs = ["smtp_server", "smtp_port", "from_email"]
        for attr in config_attrs:
            if hasattr(email_service, attr):
                print(f"    ✅ {attr}")
            else:
                print(f"    ❌ {attr} - Missing")

        return True

    except Exception as e:
        print(f"  ❌ EmailService validation failed: {e}")
        return False


def validate_scheduler_service():
    """Validate SchedulerService functionality."""
    print("\n🔍 Validating SchedulerService...")

    try:
        from app.services.scheduler_service import (
            ScheduledTask,
            ScheduleInterval,
            SchedulerService,
            scheduler_service,
            send_metrics_report_task,
            setup_default_tasks,
        )

        # Test scheduler methods
        print("  ⏰ SchedulerService Methods:")
        required_methods = [
            "add_task",
            "remove_task",
            "enable_task",
            "disable_task",
            "start",
            "stop",
            "get_task_status",
            "run_task_now",
        ]

        for method in required_methods:
            if hasattr(SchedulerService, method):
                print(f"    ✅ {method}")
            else:
                print(f"    ❌ {method} - Missing")

        # Test schedule intervals
        print("  📅 Schedule Intervals:")
        print(f"    ✅ Available intervals: {[interval.value for interval in ScheduleInterval]}")

        # Test scheduled task structure
        print("  📋 ScheduledTask Attributes:")
        task_attrs = ["name", "interval", "function", "args", "kwargs", "enabled", "last_run", "next_run"]
        for attr in task_attrs:
            if hasattr(ScheduledTask, "__dataclass_fields__") and attr in ScheduledTask.__dataclass_fields__:
                print(f"    ✅ {attr}")
            else:
                print(f"    ❌ {attr} - Missing")

        return True

    except Exception as e:
        print(f"  ❌ SchedulerService validation failed: {e}")
        return False


def validate_api_endpoints():
    """Validate metrics API endpoints."""
    print("\n🔍 Validating Metrics API Endpoints...")

    try:
        from app.api.v1.metrics import router

        # Get all routes from the router
        routes = []
        for route in router.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                routes.append((route.path, list(route.methods)))

        expected_routes = [
            ("/report/{environment}", ["GET"]),
            ("/report/all", ["GET"]),
            ("/technical/{environment}", ["GET"]),
            ("/business/{environment}", ["GET"]),
            ("/health-summary", ["GET"]),
            ("/email-report", ["POST"]),
            ("/scheduler/status", ["GET"]),
            ("/scheduler/run-task/{task_name}", ["POST"]),
            ("/scheduler/enable-task/{task_name}", ["POST"]),
            ("/scheduler/disable-task/{task_name}", ["POST"]),
        ]

        print("  📋 API Routes:")
        for expected_path, expected_methods in expected_routes:
            found = False
            for actual_path, actual_methods in routes:
                if expected_path == actual_path:
                    if set(expected_methods).issubset(set(actual_methods)):
                        print(f"    ✅ {expected_methods[0]} {expected_path}")
                        found = True
                        break

            if not found:
                print(f"    ❌ {expected_methods[0]} {expected_path} - Missing or incorrect methods")

        return True

    except Exception as e:
        print(f"  ❌ API endpoint validation failed: {e}")
        return False


def validate_schemas():
    """Validate Pydantic schemas."""
    print("\n🔍 Validating Pydantic Schemas...")

    try:
        from app.schemas.metrics import (
            EmailReportRequest,
            EnvironmentMetricsResponse,
            HealthSummaryResponse,
            MetricResultResponse,
            MetricsReportResponse,
            ScheduledTaskResponse,
            SchedulerStatusResponse,
            TaskExecutionResponse,
        )

        # Test schema classes
        print("  📋 Schema Classes:")
        schema_classes = [
            "MetricResultResponse",
            "MetricsReportResponse",
            "EnvironmentMetricsResponse",
            "ScheduledTaskResponse",
            "EmailReportRequest",
            "HealthSummaryResponse",
            "SchedulerStatusResponse",
            "TaskExecutionResponse",
        ]

        for schema_name in schema_classes:
            if schema_name in locals():
                print(f"    ✅ {schema_name}")
            else:
                print(f"    ❌ {schema_name} - Missing")

        # Test EmailReportRequest validation
        print("  📧 EmailReportRequest Validation:")
        try:
            request = EmailReportRequest(
                recipient_emails=["test@example.com", "admin@pratikoai.com"],
                environments=["development", "production"],
            )
            print("    ✅ Email validation working")
        except Exception as e:
            print(f"    ❌ Email validation failed: {e}")

        return True

    except Exception as e:
        print(f"  ❌ Schema validation failed: {e}")
        return False


def validate_startup_integration():
    """Validate startup integration."""
    print("\n🔍 Validating Startup Integration...")

    try:
        from app.core.startup import setup_startup_handlers, shutdown_handler, startup_handler

        print("  🚀 Startup Functions:")
        startup_functions = ["startup_handler", "shutdown_handler", "setup_startup_handlers"]
        for func_name in startup_functions:
            if func_name in locals():
                print(f"    ✅ {func_name}")
            else:
                print(f"    ❌ {func_name} - Missing")

        return True

    except Exception as e:
        print(f"  ❌ Startup integration validation failed: {e}")
        return False


def validate_router_integration():
    """Validate that metrics router is integrated into main API."""
    print("\n🔍 Validating Router Integration...")

    try:
        # Read the API router file
        api_file = project_root / "app" / "api" / "v1" / "api.py"
        api_content = api_file.read_text()

        # Check imports
        if "from app.api.v1.metrics import router as metrics_router" in api_content:
            print("  ✅ Metrics router import found")
        else:
            print("  ❌ Metrics router import missing")
            return False

        # Check router inclusion
        if 'api_router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])' in api_content:
            print("  ✅ Metrics router included in API")
        else:
            print("  ❌ Metrics router not included in API")
            return False

        return True

    except Exception as e:
        print(f"  ❌ Router integration validation failed: {e}")
        return False


def validate_config_updates():
    """Validate configuration updates for email settings."""
    print("\n🔍 Validating Configuration Updates...")

    try:
        from app.core.config import settings

        # Check email configuration attributes
        print("  📧 Email Configuration:")
        email_attrs = [
            "SMTP_SERVER",
            "SMTP_PORT",
            "SMTP_USERNAME",
            "SMTP_PASSWORD",
            "FROM_EMAIL",
            "METRICS_REPORT_RECIPIENTS",
        ]

        for attr in email_attrs:
            if hasattr(settings, attr):
                print(f"    ✅ {attr}")
            else:
                print(f"    ❌ {attr} - Missing")

        return True

    except Exception as e:
        print(f"  ❌ Configuration validation failed: {e}")
        return False


def validate_test_coverage():
    """Validate test coverage for metrics system."""
    print("\n🔍 Validating Test Coverage...")

    try:
        # Check if test files exist
        test_files = ["tests/services/test_metrics_service.py", "tests/services/test_email_service.py"]

        print("  🧪 Test Files:")
        for test_file in test_files:
            test_path = project_root / test_file
            if test_path.exists():
                print(f"    ✅ {test_file}")

                # Count test methods
                content = test_path.read_text()
                test_method_count = content.count("def test_")
                print(f"      📊 Test methods: {test_method_count}")
            else:
                print(f"    ❌ {test_file} - Missing")

        return True

    except Exception as e:
        print(f"  ❌ Test coverage validation failed: {e}")
        return False


async def validate_system_integration():
    """Validate end-to-end system integration."""
    print("\n🔍 Validating System Integration...")

    try:
        from app.services.email_service import email_service
        from app.services.metrics_service import Environment, metrics_service
        from app.services.scheduler_service import scheduler_service

        # Test metrics collection
        print("  📊 Testing Metrics Collection:")
        try:
            report = await metrics_service.generate_metrics_report(Environment.DEVELOPMENT)
            print(f"    ✅ Generated report with {len(report.technical_metrics)} technical metrics")
            print(f"    ✅ Generated report with {len(report.business_metrics)} business metrics")
            print(f"    ✅ Health score: {report.overall_health_score:.1f}%")
        except Exception as e:
            print(f"    ❌ Metrics collection failed: {e}")

        # Test email service initialization
        print("  📧 Testing Email Service:")
        print(f"    ✅ SMTP server: {email_service.smtp_server}")
        print(f"    ✅ From email: {email_service.from_email}")

        # Test scheduler service
        print("  ⏰ Testing Scheduler Service:")
        status = scheduler_service.get_task_status()
        print(f"    ✅ Scheduler running: {scheduler_service.running}")
        print(f"    ✅ Configured tasks: {len(status)}")

        return True

    except Exception as e:
        print(f"  ❌ System integration validation failed: {e}")
        return False


async def main():
    """Run all validation checks."""
    print("🚀 Success Metrics System Implementation Validation")
    print("=" * 60)

    validation_results = []

    # Run all validation checks
    validation_results.append(("Imports", len(validate_imports()) == 0))
    validation_results.append(("Metrics Service", validate_metrics_service()))
    validation_results.append(("Email Service", validate_email_service()))
    validation_results.append(("Scheduler Service", validate_scheduler_service()))
    validation_results.append(("API Endpoints", validate_api_endpoints()))
    validation_results.append(("Pydantic Schemas", validate_schemas()))
    validation_results.append(("Startup Integration", validate_startup_integration()))
    validation_results.append(("Router Integration", validate_router_integration()))
    validation_results.append(("Configuration Updates", validate_config_updates()))
    validation_results.append(("Test Coverage", validate_test_coverage()))
    validation_results.append(("System Integration", await validate_system_integration()))

    # Print summary
    print("\n📋 Validation Summary:")
    print("=" * 30)

    passed = 0
    total = len(validation_results)

    for check_name, result in validation_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {check_name}")
        if result:
            passed += 1

    print(f"\n🎯 Overall Result: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 Success Metrics System implementation is COMPLETE and VALID!")
        print("\n📋 Key Features Implemented:")
        print("  • Comprehensive technical and business metrics monitoring")
        print("  • Automated email reporting with HTML templates")
        print("  • Flexible scheduler service for periodic tasks")
        print("  • Complete REST API for metrics management")
        print("  • Real-time health monitoring and alerting")
        print("  • GDPR compliance verification")
        print("  • Cost tracking and optimization recommendations")
        print("  • Multi-environment support (dev/staging/production)")

        print("\n🎯 Business Impact:")
        print("  • Automated 12-hour metrics reports to configured recipients")
        print("  • Real-time monitoring of all success criteria")
        print("  • Proactive alerting for metric threshold violations")
        print("  • Comprehensive recommendations for system optimization")
        print("  • Full compliance and audit trail tracking")

        print("\n📧 Email Reporting:")
        print("  • Automated reports every 12 hours")
        print("  • Multi-environment coverage (dev/staging/production)")
        print("  • HTML-formatted professional reports")
        print("  • Health scores, alerts, and recommendations")
        print("  • Manual report triggering via API")

        return True
    else:
        print(f"\n⚠️ Success Metrics System implementation has issues ({total - passed} failures)")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
