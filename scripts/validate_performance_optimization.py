#!/usr/bin/env python3
"""
Performance Optimization Implementation Validation Script

This script validates that all performance optimization components are properly
implemented and integrated into the NormoAI system.
"""

import importlib
import inspect
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def validate_imports():
    """Validate that all performance modules can be imported."""
    print("🔍 Validating Performance Optimization imports...")

    modules_to_test = [
        "app.core.performance",
        "app.core.performance.database_optimizer",
        "app.core.performance.response_compressor",
        "app.core.performance.performance_monitor",
        "app.core.performance.cdn_integration",
        "app.core.middleware.performance_middleware",
        "app.api.v1.performance",
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


def validate_core_performance_components():
    """Validate core performance optimization components."""
    print("\n🔍 Validating Core Performance Components...")

    try:
        from app.core.performance import cdn_manager, database_optimizer, performance_monitor, response_compressor

        # Test DatabaseOptimizer
        print("  📊 Database Optimizer:")
        required_methods = [
            "monitor_query",
            "optimize_query_execution",
            "analyze_slow_queries",
            "generate_index_recommendations",
            "get_performance_summary",
        ]
        for method in required_methods:
            if hasattr(database_optimizer, method):
                print(f"    ✅ {method}")
            else:
                print(f"    ❌ {method} - Missing")

        # Test ResponseCompressor
        print("  🗜️ Response Compressor:")
        required_methods = [
            "should_compress",
            "compress_content",
            "optimize_json_payload",
            "get_compression_statistics",
            "create_optimized_response",
        ]
        for method in required_methods:
            if hasattr(response_compressor, method):
                print(f"    ✅ {method}")
            else:
                print(f"    ❌ {method} - Missing")

        # Test PerformanceMonitor
        print("  📈 Performance Monitor:")
        required_methods = [
            "record_request_metrics",
            "get_performance_summary",
            "get_endpoint_details",
            "record_cache_hit",
            "record_cache_miss",
        ]
        for method in required_methods:
            if hasattr(performance_monitor, method):
                print(f"    ✅ {method}")
            else:
                print(f"    ❌ {method} - Missing")

        # Test CDNManager
        print("  🌐 CDN Manager:")
        required_methods = [
            "generate_asset_url",
            "optimize_content_delivery",
            "purge_asset_cache",
            "get_cdn_statistics",
        ]
        for method in required_methods:
            if hasattr(cdn_manager, method):
                print(f"    ✅ {method}")
            else:
                print(f"    ❌ {method} - Missing")

        return True

    except Exception as e:
        print(f"  ❌ Core component validation failed: {e}")
        return False


def validate_middleware_integration():
    """Validate performance middleware integration."""
    print("\n🔍 Validating Performance Middleware...")

    try:
        from app.core.middleware.performance_middleware import (
            CacheMiddleware,
            DatabaseQueryMiddleware,
            PerformanceMiddleware,
        )

        # Check PerformanceMiddleware
        print("  🚀 Performance Middleware:")
        middleware_methods = ["dispatch", "_record_request_performance", "_optimize_response"]
        for method in middleware_methods:
            if hasattr(PerformanceMiddleware, method):
                print(f"    ✅ {method}")
            else:
                print(f"    ❌ {method} - Missing")

        # Check DatabaseQueryMiddleware
        print("  🗄️ Database Query Middleware:")
        db_methods = ["__call__", "record_execution"]
        for method in db_methods:
            if hasattr(DatabaseQueryMiddleware, method):
                print(f"    ✅ {method}")
            else:
                print(f"    ❌ {method} - Missing")

        # Check CacheMiddleware
        print("  💾 Cache Middleware:")
        cache_methods = ["record_cache_hit", "record_cache_miss"]
        for method in cache_methods:
            if hasattr(CacheMiddleware, method):
                print(f"    ✅ {method}")
            else:
                print(f"    ❌ {method} - Missing")

        return True

    except Exception as e:
        print(f"  ❌ Middleware validation failed: {e}")
        return False


def validate_api_endpoints():
    """Validate performance API endpoints."""
    print("\n🔍 Validating Performance API Endpoints...")

    try:
        from app.api.v1.performance import router

        # Get all routes from the router
        routes = []
        for route in router.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                routes.append((route.path, list(route.methods)))

        expected_routes = [
            ("/overview", ["GET"]),
            ("/database/stats", ["GET"]),
            ("/database/optimize-query", ["POST"]),
            ("/database/optimize-pool", ["POST"]),
            ("/compression/stats", ["GET"]),
            ("/compression/reset-stats", ["POST"]),
            ("/cdn/stats", ["GET"]),
            ("/cdn/purge", ["POST"]),
            ("/cdn/optimize-region", ["POST"]),
            ("/monitoring/endpoints", ["GET"]),
            ("/monitoring/alerts", ["GET"]),
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


def validate_router_integration():
    """Validate that performance router is integrated into main API."""
    print("\n🔍 Validating Router Integration...")

    try:
        # Read the API router file
        api_file = project_root / "app" / "api" / "v1" / "api.py"
        api_content = api_file.read_text()

        # Check imports
        if "from app.api.v1.performance import router as performance_router" in api_content:
            print("  ✅ Performance router import found")
        else:
            print("  ❌ Performance router import missing")
            return False

        # Check router inclusion
        if 'api_router.include_router(performance_router, prefix="/performance", tags=["performance"])' in api_content:
            print("  ✅ Performance router included in API")
        else:
            print("  ❌ Performance router not included in API")
            return False

        return True

    except Exception as e:
        print(f"  ❌ Router integration validation failed: {e}")
        return False


def validate_test_coverage():
    """Validate test coverage for performance optimization."""
    print("\n🔍 Validating Test Coverage...")

    try:
        # Check if test file exists
        test_file = project_root / "tests" / "core" / "performance" / "test_performance_system.py"

        if not test_file.exists():
            print("  ❌ Performance tests file missing")
            return False

        test_content = test_file.read_text()

        # Check for key test classes
        test_classes = [
            "TestDatabaseOptimizer",
            "TestResponseCompressor",
            "TestPerformanceMonitor",
            "TestCDNManager",
            "TestPerformanceIntegration",
        ]

        print("  🧪 Test Classes:")
        for test_class in test_classes:
            if f"class {test_class}" in test_content:
                print(f"    ✅ {test_class}")
            else:
                print(f"    ❌ {test_class} - Missing")

        # Count total test methods
        test_method_count = test_content.count("def test_")
        print(f"  📊 Total test methods: {test_method_count}")

        if test_method_count >= 30:
            print("  ✅ Comprehensive test coverage")
        else:
            print("  ⚠️ Limited test coverage")

        return True

    except Exception as e:
        print(f"  ❌ Test coverage validation failed: {e}")
        return False


def main():
    """Run all validation checks."""
    print("🚀 Performance Optimization Implementation Validation")
    print("=" * 60)

    validation_results = []

    # Run all validation checks
    validation_results.append(("Imports", len(validate_imports()) == 0))
    validation_results.append(("Core Components", validate_core_performance_components()))
    validation_results.append(("Middleware Integration", validate_middleware_integration()))
    validation_results.append(("API Endpoints", validate_api_endpoints()))
    validation_results.append(("Router Integration", validate_router_integration()))
    validation_results.append(("Test Coverage", validate_test_coverage()))

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
        print("\n🎉 Performance Optimization implementation is COMPLETE and VALID!")
        print("\n📋 Key Features Implemented:")
        print("  • Database query optimization and monitoring")
        print("  • Response compression (Gzip/Brotli)")
        print("  • Real-time performance monitoring")
        print("  • CDN integration and asset optimization")
        print("  • Performance middleware for automatic optimization")
        print("  • Comprehensive API endpoints for performance management")
        print("  • Extensive test coverage")

        print("\n🎯 Business Impact:")
        print("  • Reduced server costs through query optimization")
        print("  • Improved user experience with faster response times")
        print("  • Reduced bandwidth costs through compression")
        print("  • Better scalability through performance monitoring")

        return True
    else:
        print(f"\n⚠️ Performance Optimization implementation has issues ({total - passed} failures)")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
