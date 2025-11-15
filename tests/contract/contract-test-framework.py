#!/usr/bin/env python3
"""
Advanced API Contract Testing Framework for PratikoAI
Ensures compatibility between frontend and backend through comprehensive contract validation.

This framework implements:
- OpenAPI specification validation
- Cross-version compatibility testing
- Automated contract generation and updates
- Integration with CI/CD pipelines
- Detailed reporting and metrics
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
import pytest
import yaml
from jsonschema import ValidationError, validate


class ContractViolationSeverity(Enum):
    """Severity levels for contract violations."""

    CRITICAL = "critical"  # Breaking changes
    MAJOR = "major"  # Significant changes that may break clients
    MINOR = "minor"  # Minor changes, backward compatible
    INFO = "info"  # Informational changes


class TestResult(Enum):
    """Test execution results."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ContractViolation:
    """Represents a contract violation with detailed information."""

    severity: ContractViolationSeverity
    endpoint: str
    violation_type: str
    description: str
    expected: Any
    actual: Any
    suggested_fix: str | None = None


@dataclass
class ContractTestResult:
    """Results from contract testing."""

    test_name: str
    result: TestResult
    execution_time: float
    violations: list[ContractViolation]
    metadata: dict[str, Any]


class APIContractValidator:
    """Advanced API contract validator with cross-version compatibility."""

    def __init__(self, base_url: str, spec_path: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.spec_path = spec_path or self._discover_spec_path()
        self.client = httpx.AsyncClient(timeout=30.0)
        self.spec_cache = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _discover_spec_path(self) -> str:
        """Discover OpenAPI specification file location."""
        possible_paths = [
            "openapi.yaml",
            "openapi.json",
            "api-spec.yaml",
            "api-spec.json",
            "docs/openapi.yaml",
            "specs/openapi.yaml",
        ]

        for path in possible_paths:
            if Path(path).exists():
                return path

        # Generate spec from running service
        return self._generate_spec_from_service()

    def _generate_spec_from_service(self) -> str:
        """Generate OpenAPI spec from running service."""
        spec_url = f"{self.base_url}/openapi.json"
        spec_path = "generated-openapi.json"

        try:
            response = httpx.get(spec_url, timeout=10)
            response.raise_for_status()

            with open(spec_path, "w") as f:
                json.dump(response.json(), f, indent=2)

            print(f"Generated OpenAPI spec from {spec_url}")
            return spec_path

        except Exception as e:
            print(f"Failed to generate spec from service: {e}")
            raise RuntimeError("No OpenAPI specification found")

    def load_spec(self, version: str | None = None) -> dict[str, Any]:
        """Load OpenAPI specification with caching."""
        cache_key = f"{self.spec_path}:{version or 'latest'}"

        if cache_key in self.spec_cache:
            return self.spec_cache[cache_key]

        try:
            with open(self.spec_path) as f:
                if self.spec_path.endswith(".yaml") or self.spec_path.endswith(".yml"):
                    spec = yaml.safe_load(f)
                else:
                    spec = json.load(f)

            self.spec_cache[cache_key] = spec
            return spec

        except Exception as e:
            raise RuntimeError(f"Failed to load OpenAPI spec from {self.spec_path}: {e}")

    async def validate_endpoint(
        self, method: str, path: str, request_data: dict | None = None, expected_status: int = 200
    ) -> list[ContractViolation]:
        """Validate a single endpoint against its contract."""
        violations = []
        spec = self.load_spec()

        # Find endpoint in spec
        path_item = self._find_path_in_spec(spec, path)
        if not path_item:
            violations.append(
                ContractViolation(
                    severity=ContractViolationSeverity.CRITICAL,
                    endpoint=f"{method.upper()} {path}",
                    violation_type="endpoint_not_found",
                    description=f"Endpoint {method.upper()} {path} not found in OpenAPI specification",
                    expected="Endpoint definition in OpenAPI spec",
                    actual="Missing endpoint definition",
                )
            )
            return violations

        operation = path_item.get(method.lower())
        if not operation:
            violations.append(
                ContractViolation(
                    severity=ContractViolationSeverity.CRITICAL,
                    endpoint=f"{method.upper()} {path}",
                    violation_type="method_not_allowed",
                    description=f"Method {method.upper()} not allowed for {path}",
                    expected=f"Allowed methods: {list(path_item.keys())}",
                    actual=f"Method: {method.upper()}",
                )
            )
            return violations

        # Execute request
        try:
            url = f"{self.base_url}{path}"

            if method.upper() == "GET":
                response = await self.client.get(url, params=request_data or {})
            elif method.upper() == "POST":
                response = await self.client.post(url, json=request_data or {})
            elif method.upper() == "PUT":
                response = await self.client.put(url, json=request_data or {})
            elif method.upper() == "DELETE":
                response = await self.client.delete(url)
            elif method.upper() == "PATCH":
                response = await self.client.patch(url, json=request_data or {})
            else:
                violations.append(
                    ContractViolation(
                        severity=ContractViolationSeverity.MAJOR,
                        endpoint=f"{method.upper()} {path}",
                        violation_type="unsupported_method",
                        description=f"HTTP method {method.upper()} not supported by test framework",
                        expected="Supported methods: GET, POST, PUT, DELETE, PATCH",
                        actual=f"Method: {method.upper()}",
                    )
                )
                return violations

        except Exception as e:
            violations.append(
                ContractViolation(
                    severity=ContractViolationSeverity.CRITICAL,
                    endpoint=f"{method.upper()} {path}",
                    violation_type="request_failed",
                    description=f"Request failed: {str(e)}",
                    expected="Successful HTTP request",
                    actual=f"Exception: {str(e)}",
                )
            )
            return violations

        # Validate response status
        expected_responses = operation.get("responses", {})
        if str(response.status_code) not in expected_responses:
            violations.append(
                ContractViolation(
                    severity=ContractViolationSeverity.MAJOR,
                    endpoint=f"{method.upper()} {path}",
                    violation_type="unexpected_status_code",
                    description=f"Unexpected status code {response.status_code}",
                    expected=f"Expected status codes: {list(expected_responses.keys())}",
                    actual=f"Status code: {response.status_code}",
                )
            )

        # Validate response schema
        if response.status_code < 400:  # Only validate successful responses
            response_spec = expected_responses.get(str(response.status_code), {})
            content_spec = response_spec.get("content", {})

            if "application/json" in content_spec:
                schema = content_spec["application/json"].get("schema", {})
                if schema:
                    try:
                        response_data = response.json()
                        validate(response_data, schema)
                    except ValidationError as e:
                        violations.append(
                            ContractViolation(
                                severity=ContractViolationSeverity.MAJOR,
                                endpoint=f"{method.upper()} {path}",
                                violation_type="response_schema_violation",
                                description=f"Response schema validation failed: {e.message}",
                                expected=f"Schema: {schema}",
                                actual=f"Response: {response.text[:500]}...",
                            )
                        )
                    except json.JSONDecodeError as e:
                        violations.append(
                            ContractViolation(
                                severity=ContractViolationSeverity.MAJOR,
                                endpoint=f"{method.upper()} {path}",
                                violation_type="invalid_json_response",
                                description=f"Response is not valid JSON: {str(e)}",
                                expected="Valid JSON response",
                                actual=f"Response: {response.text[:200]}...",
                            )
                        )

        # Validate response headers
        self._validate_response_headers(response, operation, violations, f"{method.upper()} {path}")

        return violations

    def _find_path_in_spec(self, spec: dict[str, Any], path: str) -> dict[str, Any] | None:
        """Find a path in the OpenAPI specification, handling path parameters."""
        paths = spec.get("paths", {})

        # Direct match
        if path in paths:
            return paths[path]

        # Match with path parameters
        for spec_path, path_item in paths.items():
            if self._match_path_with_params(spec_path, path):
                return path_item

        return None

    def _match_path_with_params(self, spec_path: str, actual_path: str) -> bool:
        """Match paths with parameter substitution."""
        spec_parts = spec_path.split("/")
        actual_parts = actual_path.split("/")

        if len(spec_parts) != len(actual_parts):
            return False

        for spec_part, actual_part in zip(spec_parts, actual_parts, strict=False):
            if spec_part.startswith("{") and spec_part.endswith("}"):
                # Parameter placeholder, matches anything
                continue
            elif spec_part != actual_part:
                return False

        return True

    def _validate_response_headers(
        self, response: httpx.Response, operation: dict[str, Any], violations: list[ContractViolation], endpoint: str
    ):
        """Validate response headers against specification."""
        expected_responses = operation.get("responses", {})
        response_spec = expected_responses.get(str(response.status_code), {})
        expected_headers = response_spec.get("headers", {})

        for header_name, _header_spec in expected_headers.items():
            if header_name.lower() not in [h.lower() for h in response.headers.keys()]:
                violations.append(
                    ContractViolation(
                        severity=ContractViolationSeverity.MINOR,
                        endpoint=endpoint,
                        violation_type="missing_response_header",
                        description=f"Expected response header '{header_name}' is missing",
                        expected=f"Header: {header_name}",
                        actual=f"Response headers: {list(response.headers.keys())}",
                    )
                )

    async def validate_all_endpoints(self) -> list[ContractTestResult]:
        """Validate all endpoints defined in the OpenAPI specification."""
        spec = self.load_spec()
        paths = spec.get("paths", {})
        results = []

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
                    continue

                start_time = time.time()
                test_name = f"{method.upper()} {path}"

                try:
                    violations = await self.validate_endpoint(method, path)
                    execution_time = time.time() - start_time

                    # Determine test result
                    if not violations:
                        result = TestResult.PASSED
                    elif any(
                        v.severity in [ContractViolationSeverity.CRITICAL, ContractViolationSeverity.MAJOR]
                        for v in violations
                    ):
                        result = TestResult.FAILED
                    else:
                        result = TestResult.PASSED  # Minor violations don't fail the test

                    results.append(
                        ContractTestResult(
                            test_name=test_name,
                            result=result,
                            execution_time=execution_time,
                            violations=violations,
                            metadata={
                                "operation_id": operation.get("operationId"),
                                "tags": operation.get("tags", []),
                                "summary": operation.get("summary"),
                            },
                        )
                    )

                except Exception as e:
                    execution_time = time.time() - start_time
                    results.append(
                        ContractTestResult(
                            test_name=test_name,
                            result=TestResult.ERROR,
                            execution_time=execution_time,
                            violations=[
                                ContractViolation(
                                    severity=ContractViolationSeverity.CRITICAL,
                                    endpoint=test_name,
                                    violation_type="test_execution_error",
                                    description=f"Test execution failed: {str(e)}",
                                    expected="Successful test execution",
                                    actual=f"Exception: {str(e)}",
                                )
                            ],
                            metadata={"error": str(e)},
                        )
                    )

        return results


class CrossVersionCompatibilityTester:
    """Tests compatibility between different API versions."""

    def __init__(self, current_service_url: str, previous_service_url: str | None = None):
        self.current_service_url = current_service_url
        self.previous_service_url = previous_service_url

    async def test_backward_compatibility(self) -> list[ContractTestResult]:
        """Test if current version is backward compatible with previous version."""
        if not self.previous_service_url:
            return []

        results = []

        # Compare OpenAPI specifications
        async with APIContractValidator(self.current_service_url) as current_validator:
            current_spec = current_validator.load_spec()

        async with APIContractValidator(self.previous_service_url) as previous_validator:
            previous_spec = previous_validator.load_spec()

        # Check for breaking changes
        breaking_changes = self._find_breaking_changes(previous_spec, current_spec)

        if breaking_changes:
            results.append(
                ContractTestResult(
                    test_name="backward_compatibility",
                    result=TestResult.FAILED,
                    execution_time=0.0,
                    violations=breaking_changes,
                    metadata={"comparison": "previous_vs_current"},
                )
            )
        else:
            results.append(
                ContractTestResult(
                    test_name="backward_compatibility",
                    result=TestResult.PASSED,
                    execution_time=0.0,
                    violations=[],
                    metadata={"comparison": "previous_vs_current"},
                )
            )

        return results

    def _find_breaking_changes(self, old_spec: dict[str, Any], new_spec: dict[str, Any]) -> list[ContractViolation]:
        """Find breaking changes between two API specifications."""
        violations = []

        old_paths = old_spec.get("paths", {})
        new_paths = new_spec.get("paths", {})

        # Check for removed endpoints
        for path, path_item in old_paths.items():
            if path not in new_paths:
                violations.append(
                    ContractViolation(
                        severity=ContractViolationSeverity.CRITICAL,
                        endpoint=path,
                        violation_type="endpoint_removed",
                        description=f"Endpoint {path} was removed",
                        expected=f"Endpoint {path} to exist",
                        actual="Endpoint not found in new specification",
                        suggested_fix="Add deprecation notice before removing endpoints",
                    )
                )
                continue

            # Check for removed methods
            new_path_item = new_paths[path]
            for method in path_item.keys():
                if method not in new_path_item:
                    violations.append(
                        ContractViolation(
                            severity=ContractViolationSeverity.CRITICAL,
                            endpoint=f"{method.upper()} {path}",
                            violation_type="method_removed",
                            description=f"Method {method.upper()} was removed from {path}",
                            expected=f"Method {method.upper()} to exist",
                            actual="Method not found in new specification",
                            suggested_fix="Add deprecation notice before removing methods",
                        )
                    )

        # Check for required parameter changes
        for path, path_item in old_paths.items():
            if path not in new_paths:
                continue

            new_path_item = new_paths[path]

            for method, operation in path_item.items():
                if method not in new_path_item:
                    continue

                new_operation = new_path_item[method]

                # Check parameters
                old_params = operation.get("parameters", [])
                new_params = new_operation.get("parameters", [])

                for old_param in old_params:
                    if not old_param.get("required", False):
                        continue

                    # Find corresponding parameter in new spec
                    new_param = next(
                        (
                            p
                            for p in new_params
                            if p.get("name") == old_param.get("name") and p.get("in") == old_param.get("in")
                        ),
                        None,
                    )

                    if not new_param:
                        violations.append(
                            ContractViolation(
                                severity=ContractViolationSeverity.CRITICAL,
                                endpoint=f"{method.upper()} {path}",
                                violation_type="required_parameter_removed",
                                description=f"Required parameter '{old_param.get('name')}' was removed",
                                expected=f"Parameter '{old_param.get('name')}' to exist",
                                actual="Parameter not found in new specification",
                                suggested_fix="Make parameter optional before removing",
                            )
                        )
                    elif not new_param.get("required", False):
                        violations.append(
                            ContractViolation(
                                severity=ContractViolationSeverity.MAJOR,
                                endpoint=f"{method.upper()} {path}",
                                violation_type="required_parameter_made_optional",
                                description=f"Required parameter '{old_param.get('name')}' was made optional",
                                expected=f"Parameter '{old_param.get('name')}' to remain required",
                                actual="Parameter is now optional",
                            )
                        )

        return violations


class ContractTestRunner:
    """Main test runner for contract testing."""

    def __init__(self, config_path: str | None = None):
        self.config = self._load_config(config_path)
        self.report_dir = Path(self.config.get("report_dir", "contract-test-reports"))
        self.report_dir.mkdir(exist_ok=True)

    def _load_config(self, config_path: str | None) -> dict[str, Any]:
        """Load configuration from file or environment."""
        default_config = {
            "base_url": os.getenv("API_BASE_URL", "http://localhost:8000"),
            "timeout": int(os.getenv("CONTRACT_TEST_TIMEOUT", "300")),
            "report_format": os.getenv("CONTRACT_REPORT_FORMAT", "json"),
            "fail_on_violations": os.getenv("FAIL_ON_CONTRACT_VIOLATIONS", "true").lower() == "true",
        }

        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                file_config = yaml.safe_load(f)
                default_config.update(file_config)

        return default_config

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all contract tests and generate comprehensive report."""
        start_time = time.time()

        print("🔍 Starting comprehensive contract testing...")

        results = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "config": self.config,
            "tests": [],
            "summary": {},
            "violations": [],
        }

        # Run endpoint validation tests
        print("  📋 Validating API endpoints...")
        async with APIContractValidator(self.config["base_url"]) as validator:
            test_results = await validator.validate_all_endpoints()
            results["tests"].extend([asdict(r) for r in test_results])

            # Collect all violations
            for test_result in test_results:
                results["violations"].extend([asdict(v) for v in test_result.violations])

        # Run cross-version compatibility tests
        if previous_url := self.config.get("previous_version_url"):
            print("  🔄 Testing backward compatibility...")
            compatibility_tester = CrossVersionCompatibilityTester(self.config["base_url"], previous_url)
            compat_results = await compatibility_tester.test_backward_compatibility()
            results["tests"].extend([asdict(r) for r in compat_results])

            for test_result in compat_results:
                results["violations"].extend([asdict(v) for v in test_result.violations])

        # Generate summary
        total_tests = len(results["tests"])
        passed_tests = sum(1 for t in results["tests"] if t["result"] == TestResult.PASSED.value)
        failed_tests = sum(1 for t in results["tests"] if t["result"] == TestResult.FAILED.value)
        error_tests = sum(1 for t in results["tests"] if t["result"] == TestResult.ERROR.value)

        violation_counts = {}
        for violation in results["violations"]:
            severity = violation["severity"]
            violation_counts[severity] = violation_counts.get(severity, 0) + 1

        results["summary"] = {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "errors": error_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "execution_time": time.time() - start_time,
            "violation_counts": violation_counts,
            "critical_violations": violation_counts.get("critical", 0),
            "major_violations": violation_counts.get("major", 0),
            "minor_violations": violation_counts.get("minor", 0),
        }

        # Save report
        await self._save_report(results)

        # Print summary
        self._print_summary(results)

        return results

    async def _save_report(self, results: dict[str, Any]):
        """Save test report to file."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if self.config["report_format"] == "json":
            report_file = self.report_dir / f"contract-test-report_{timestamp}.json"
            with open(report_file, "w") as f:
                json.dump(results, f, indent=2, default=str)
        elif self.config["report_format"] == "yaml":
            report_file = self.report_dir / f"contract-test-report_{timestamp}.yaml"
            with open(report_file, "w") as f:
                yaml.dump(results, f, indent=2, default_flow_style=False)

        print(f"  📄 Report saved to: {report_file}")

    def _print_summary(self, results: dict[str, Any]):
        """Print test summary to console."""
        summary = results["summary"]

        print("\n" + "=" * 60)
        print("📊 CONTRACT TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} ✅")
        print(f"Failed: {summary['failed']} ❌")
        print(f"Errors: {summary['errors']} 🔥")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Execution Time: {summary['execution_time']:.2f}s")

        print("\n📋 VIOLATION SUMMARY:")
        print(f"Critical: {summary['critical_violations']} 🔴")
        print(f"Major: {summary['major_violations']} 🟡")
        print(f"Minor: {summary['minor_violations']} 🔵")

        if summary["critical_violations"] > 0:
            print("\n⚠️  CRITICAL VIOLATIONS DETECTED!")
            print("   These violations may break client applications.")

        print("=" * 60)


async def main():
    """Main entry point for contract testing."""

    # Parse command line arguments
    config_path = sys.argv[1] if len(sys.argv) > 1 else None

    # Run contract tests
    runner = ContractTestRunner(config_path)
    results = await runner.run_all_tests()

    # Exit with appropriate code
    critical_violations = results["summary"]["critical_violations"]
    failed_tests = results["summary"]["failed"]

    if critical_violations > 0 or failed_tests > 0:
        if runner.config["fail_on_violations"]:
            print("\n❌ Contract tests failed!")
            sys.exit(1)
        else:
            print("\n⚠️  Contract violations detected but not failing due to configuration")

    print("\n✅ All contract tests passed!")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
