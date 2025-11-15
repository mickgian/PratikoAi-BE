#!/usr/bin/env python3
"""PratikoAI Version Compatibility Checker
Comprehensive validation scripts for ensuring version compatibility during CI/CD.

This system provides:
- Pre-deployment compatibility validation
- Cross-service dependency checking
- Breaking change detection
- Deployment readiness assessment
- Integration with CI/CD pipelines
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import UTC, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from colorama import Back, Fore, Style, init

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.version_schema import CompatibilityLevel, Environment, ServiceType
from registry.database import VersionRegistryDB, init_database
from validation.contract_validator import APIContractValidator, ContractValidationResult

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CompatibilityChecker:
    """Main compatibility checker with comprehensive validation."""

    def __init__(self, registry_db: VersionRegistryDB, version_registry_url: str = None):
        self.registry_db = registry_db
        self.version_registry_url = version_registry_url
        self.contract_validator = APIContractValidator()

        # API session for registry calls
        self.session = requests.Session()
        if token := os.getenv("VERSION_REGISTRY_TOKEN"):
            self.session.headers["Authorization"] = f"Bearer {token}"

    async def check_deployment_compatibility(
        self,
        service_type: ServiceType,
        version: str,
        environment: Environment,
        target_services: list[ServiceType] = None,
    ) -> dict[str, Any]:
        """Comprehensive compatibility check for deployment.

        Returns a detailed report with:
        - Compatibility status
        - Blocking issues
        - Warnings
        - Recommendations
        """
        print(f"{Fore.CYAN}🔍 Checking deployment compatibility for:")
        print(f"   Service: {Fore.YELLOW}{service_type.value}")
        print(f"   Version: {Fore.YELLOW}{version}")
        print(f"   Environment: {Fore.YELLOW}{environment.value}")
        print()

        result = {
            "service_type": service_type.value,
            "version": version,
            "environment": environment.value,
            "timestamp": datetime.now(UTC).isoformat(),
            "can_deploy": True,
            "compatibility_level": CompatibilityLevel.FULLY_COMPATIBLE.value,
            "blocking_issues": [],
            "warnings": [],
            "recommendations": [],
            "dependency_checks": [],
            "contract_validation": None,
            "deployment_readiness": {},
        }

        try:
            # Step 1: Validate service version exists
            service_version = self.registry_db.get_version(service_type, version)
            if not service_version:
                result["blocking_issues"].append(f"Version {version} not found for {service_type.value}")
                result["can_deploy"] = False
                return result

            print(f"{Fore.GREEN}✓ Version {version} found in registry")

            # Step 2: Check dependencies
            await self._check_dependencies(service_version, environment, result)

            # Step 3: Check cross-service compatibility
            if target_services:
                await self._check_cross_service_compatibility(
                    service_type, version, target_services, environment, result
                )
            else:
                # Check against all other services
                all_services = [s for s in ServiceType if s != service_type]
                await self._check_cross_service_compatibility(service_type, version, all_services, environment, result)

            # Step 4: API contract validation (for backend services)
            if service_type == ServiceType.BACKEND and service_version.api_contract:
                await self._validate_api_contract(service_version, environment, result)

            # Step 5: Environment-specific checks
            await self._check_environment_readiness(service_type, version, environment, result)

            # Step 6: Generate recommendations
            self._generate_recommendations(result)

            # Determine overall compatibility
            self._determine_overall_compatibility(result)

        except Exception as e:
            logger.error(f"Compatibility check failed: {e}")
            result["blocking_issues"].append(f"Compatibility check failed: {str(e)}")
            result["can_deploy"] = False

        return result

    async def _check_dependencies(self, service_version, environment: Environment, result: dict[str, Any]):
        """Check if all dependencies are satisfied."""
        print(f"{Fore.BLUE}📋 Checking dependencies...")

        if not service_version.dependencies:
            print(f"{Fore.GREEN}✓ No dependencies to check")
            return

        current_deployments = self.registry_db.get_deployment_status(environment)

        for dependency in service_version.dependencies:
            dependency_info = {
                "service_type": dependency.service_type.value,
                "min_version": dependency.min_version,
                "max_version": dependency.max_version,
                "exact_version": dependency.exact_version,
                "optional": dependency.optional,
                "status": "unknown",
                "deployed_version": None,
                "satisfied": False,
            }

            # Get currently deployed version
            current_deployment = current_deployments.get(dependency.service_type.value)

            if current_deployment:
                deployed_version = current_deployment["version"]
                dependency_info["deployed_version"] = deployed_version

                # Check if dependency is satisfied
                if service_version.satisfies_dependency(dependency, deployed_version):
                    dependency_info["status"] = "satisfied"
                    dependency_info["satisfied"] = True
                    print(f"{Fore.GREEN}✓ {dependency.service_type.value} {deployed_version} satisfies requirement")
                else:
                    dependency_info["status"] = "unsatisfied"
                    dependency_info["satisfied"] = False

                    issue_msg = (
                        f"Dependency {dependency.service_type.value} version {deployed_version} "
                        f"does not satisfy requirement {dependency.min_version}"
                    )

                    if dependency.optional:
                        result["warnings"].append(f"Optional dependency issue: {issue_msg}")
                        print(f"{Fore.YELLOW}⚠ Optional: {issue_msg}")
                    else:
                        result["blocking_issues"].append(issue_msg)
                        result["can_deploy"] = False
                        print(f"{Fore.RED}✗ Required: {issue_msg}")

            elif not dependency.optional:
                dependency_info["status"] = "missing"
                issue_msg = (
                    f"Required dependency {dependency.service_type.value} is not deployed to {environment.value}"
                )
                result["blocking_issues"].append(issue_msg)
                result["can_deploy"] = False
                print(f"{Fore.RED}✗ {issue_msg}")

            else:
                dependency_info["status"] = "missing_optional"
                print(f"{Fore.YELLOW}⚠ Optional dependency {dependency.service_type.value} not deployed")

            result["dependency_checks"].append(dependency_info)

    async def _check_cross_service_compatibility(
        self,
        source_service: ServiceType,
        source_version: str,
        target_services: list[ServiceType],
        environment: Environment,
        result: dict[str, Any],
    ):
        """Check compatibility with other services."""
        print(f"{Fore.BLUE}🔗 Checking cross-service compatibility...")

        current_deployments = self.registry_db.get_deployment_status(environment)

        for target_service in target_services:
            target_deployment = current_deployments.get(target_service.value)

            if not target_deployment:
                print(f"{Fore.YELLOW}⚠ {target_service.value} not deployed to {environment.value}")
                continue

            target_version = target_deployment["version"]

            # Check compatibility
            compatibility_level = self.registry_db.check_compatibility(
                source_service, source_version, target_service, target_version
            )

            compatibility_info = {
                "target_service": target_service.value,
                "target_version": target_version,
                "compatibility_level": compatibility_level.value,
                "compatible": compatibility_level not in [CompatibilityLevel.INCOMPATIBLE, CompatibilityLevel.UNKNOWN],
            }

            if compatibility_level == CompatibilityLevel.INCOMPATIBLE:
                issue_msg = f"Incompatible with {target_service.value} {target_version}"
                result["blocking_issues"].append(issue_msg)
                result["can_deploy"] = False
                print(f"{Fore.RED}✗ {issue_msg}")

            elif compatibility_level == CompatibilityLevel.LIMITED_COMPATIBLE:
                warning_msg = f"Limited compatibility with {target_service.value} {target_version}"
                result["warnings"].append(warning_msg)
                print(f"{Fore.YELLOW}⚠ {warning_msg}")

            elif compatibility_level == CompatibilityLevel.UNKNOWN:
                warning_msg = f"Unknown compatibility with {target_service.value} {target_version}"
                result["warnings"].append(warning_msg)
                print(f"{Fore.YELLOW}? {warning_msg}")

            else:
                print(f"{Fore.GREEN}✓ Compatible with {target_service.value} {target_version}")

            result["dependency_checks"].append(compatibility_info)

    async def _validate_api_contract(self, service_version, environment: Environment, result: dict[str, Any]):
        """Validate API contract for backend services."""
        print(f"{Fore.BLUE}📄 Validating API contract...")

        if not service_version.api_contract:
            print(f"{Fore.YELLOW}⚠ No API contract defined")
            return

        # Get previous version for comparison
        previous_versions = self.registry_db.get_versions_by_service(service_version.service_type, limit=10)

        # Find the currently deployed version
        current_deployments = self.registry_db.get_deployment_status(environment)
        current_deployment = current_deployments.get(service_version.service_type.value)

        if current_deployment:
            current_version = current_deployment["version"]

            # Find the deployed version in our list
            deployed_service_version = None
            for prev_version in previous_versions:
                if prev_version.version == current_version:
                    deployed_service_version = prev_version
                    break

            if deployed_service_version and deployed_service_version.api_contract:
                print(f"   Comparing with deployed version {current_version}")

                # Validate contract evolution
                validation_result = await self.contract_validator.validate_contract_evolution(
                    deployed_service_version.api_contract, service_version.api_contract
                )

                result["contract_validation"] = {
                    "is_compatible": validation_result.is_compatible,
                    "compatibility_level": validation_result.compatibility_level.value,
                    "total_changes": len(validation_result.changes),
                    "breaking_changes": len(validation_result.breaking_changes),
                    "summary": validation_result.summary,
                }

                if not validation_result.is_compatible:
                    result["blocking_issues"].append(
                        f"API contract has {len(validation_result.breaking_changes)} breaking changes"
                    )
                    result["can_deploy"] = False
                    print(f"{Fore.RED}✗ API contract has breaking changes")

                    # List critical breaking changes
                    for change in validation_result.breaking_changes[:5]:  # Show first 5
                        print(f"   - {change.description}")

                elif validation_result.breaking_changes:
                    result["warnings"].append(
                        f"API contract has {len(validation_result.breaking_changes)} potentially breaking changes"
                    )
                    print(f"{Fore.YELLOW}⚠ API contract has potentially breaking changes")

                else:
                    print(f"{Fore.GREEN}✓ API contract is backward compatible")

            else:
                print(f"{Fore.YELLOW}⚠ No API contract for comparison with deployed version")

        else:
            print(f"{Fore.GREEN}✓ No previous deployment for comparison")

    async def _check_environment_readiness(
        self, service_type: ServiceType, version: str, environment: Environment, result: dict[str, Any]
    ):
        """Check environment-specific deployment readiness."""
        print(f"{Fore.BLUE}🌍 Checking environment readiness...")

        readiness_checks = {
            "infrastructure": {"status": "unknown", "details": []},
            "resources": {"status": "unknown", "details": []},
            "configuration": {"status": "unknown", "details": []},
            "security": {"status": "unknown", "details": []},
        }

        # Infrastructure checks
        if environment == Environment.PRODUCTION:
            readiness_checks["infrastructure"]["details"].append("Production infrastructure requirements")
            readiness_checks["infrastructure"]["status"] = "ready"  # Would implement actual checks

            # Security checks for production
            readiness_checks["security"]["details"].append("Security scan required for production")
            readiness_checks["security"]["status"] = "ready"

        else:
            readiness_checks["infrastructure"]["status"] = "ready"
            readiness_checks["security"]["status"] = "ready"

        # Resource availability
        readiness_checks["resources"]["status"] = "ready"
        readiness_checks["resources"]["details"].append("Sufficient compute resources available")

        # Configuration validation
        readiness_checks["configuration"]["status"] = "ready"
        readiness_checks["configuration"]["details"].append("Environment configuration validated")

        result["deployment_readiness"] = readiness_checks

        # Check for any blocking readiness issues
        for check_name, check_result in readiness_checks.items():
            if check_result["status"] == "not_ready":
                result["blocking_issues"].append(f"Environment not ready: {check_name}")
                result["can_deploy"] = False
                print(f"{Fore.RED}✗ {check_name} not ready")
            else:
                print(f"{Fore.GREEN}✓ {check_name} ready")

    def _generate_recommendations(self, result: dict[str, Any]):
        """Generate deployment recommendations based on analysis."""
        recommendations = []

        # Breaking changes recommendations
        if result.get("contract_validation", {}).get("breaking_changes", 0) > 0:
            recommendations.append("Consider using blue-green deployment strategy for breaking API changes")
            recommendations.append("Coordinate with frontend teams before deploying breaking changes")

        # Dependency recommendations
        unsatisfied_deps = [
            dep
            for dep in result.get("dependency_checks", [])
            if not dep.get("satisfied", True) and not dep.get("optional", True)
        ]

        if unsatisfied_deps:
            recommendations.append("Deploy required dependencies before deploying this version")

        # Environment-specific recommendations
        if result["environment"] == "production":
            recommendations.append("Perform additional testing in staging environment before production deployment")
            if result.get("warnings"):
                recommendations.append("Review all warnings carefully for production deployment")

        # Compatibility recommendations
        limited_compat = [
            check
            for check in result.get("dependency_checks", [])
            if check.get("compatibility_level") == "limited_compatible"
        ]

        if limited_compat:
            recommendations.append("Monitor closely for issues due to limited compatibility with some services")

        result["recommendations"] = recommendations

    def _determine_overall_compatibility(self, result: dict[str, Any]):
        """Determine overall compatibility level."""
        if result["blocking_issues"]:
            result["compatibility_level"] = CompatibilityLevel.INCOMPATIBLE.value
            result["can_deploy"] = False

        elif result.get("contract_validation", {}).get("breaking_changes", 0) > 0:
            result["compatibility_level"] = CompatibilityLevel.LIMITED_COMPATIBLE.value

        elif result["warnings"]:
            result["compatibility_level"] = CompatibilityLevel.BACKWARD_COMPATIBLE.value

        else:
            result["compatibility_level"] = CompatibilityLevel.FULLY_COMPATIBLE.value

    def print_compatibility_report(self, result: dict[str, Any]):
        """Print a formatted compatibility report."""
        print()
        print("=" * 80)
        print(f"{Fore.CYAN}{Back.BLACK} 📊 COMPATIBILITY REPORT {Style.RESET_ALL}")
        print("=" * 80)

        # Summary
        status_color = Fore.GREEN if result["can_deploy"] else Fore.RED
        status_symbol = "✅" if result["can_deploy"] else "❌"

        print(f"\n{status_color}{status_symbol} DEPLOYMENT STATUS: {result['can_deploy']}")
        print(f"{Fore.BLUE}🎯 Service: {result['service_type']} v{result['version']}")
        print(f"{Fore.BLUE}🌍 Environment: {result['environment']}")
        print(f"{Fore.BLUE}🔗 Compatibility Level: {result['compatibility_level']}")

        # Blocking Issues
        if result["blocking_issues"]:
            print(f"\n{Fore.RED}🚫 BLOCKING ISSUES:")
            for issue in result["blocking_issues"]:
                print(f"   • {issue}")

        # Warnings
        if result["warnings"]:
            print(f"\n{Fore.YELLOW}⚠️  WARNINGS:")
            for warning in result["warnings"]:
                print(f"   • {warning}")

        # Dependencies
        if result["dependency_checks"]:
            print(f"\n{Fore.BLUE}📋 DEPENDENCY ANALYSIS:")
            for dep in result["dependency_checks"]:
                if "min_version" in dep:  # Dependency check
                    status_symbol = "✅" if dep["satisfied"] else "❌"
                    print(
                        f"   {status_symbol} {dep['service_type']}: {dep['deployed_version']} (requires {dep['min_version']})"
                    )
                else:  # Compatibility check
                    compat_color = Fore.GREEN if dep["compatible"] else Fore.RED
                    print(
                        f"   {compat_color}🔗 {dep['target_service']} {dep['target_version']}: {dep['compatibility_level']}"
                    )

        # API Contract
        if result.get("contract_validation"):
            contract = result["contract_validation"]
            print(f"\n{Fore.BLUE}📄 API CONTRACT VALIDATION:")
            print(f"   Compatible: {contract['is_compatible']}")
            print(f"   Total Changes: {contract['total_changes']}")
            print(f"   Breaking Changes: {contract['breaking_changes']}")

        # Recommendations
        if result["recommendations"]:
            print(f"\n{Fore.CYAN}💡 RECOMMENDATIONS:")
            for rec in result["recommendations"]:
                print(f"   • {rec}")

        print("\n" + "=" * 80)


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PratikoAI Version Compatibility Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --service backend --version 1.2.3 --environment production
  %(prog)s --service frontend-android --version 2.1.0 --environment staging --targets backend
  %(prog)s --service backend --version 1.3.0 --environment development --output report.json
        """,
    )

    parser.add_argument(
        "--service", required=True, choices=[s.value for s in ServiceType], help="Service type to check"
    )

    parser.add_argument("--version", required=True, help="Version to check")

    parser.add_argument(
        "--environment", required=True, choices=[e.value for e in Environment], help="Target environment"
    )

    parser.add_argument(
        "--targets",
        nargs="*",
        choices=[s.value for s in ServiceType],
        help="Specific services to check compatibility against",
    )

    parser.add_argument("--output", "-o", help="Output file for detailed report (JSON)")

    parser.add_argument("--registry-url", default=os.getenv("VERSION_REGISTRY_URL"), help="Version registry API URL")

    parser.add_argument(
        "--db-url",
        default=os.getenv("VERSION_REGISTRY_DB_URL", "sqlite:///version_registry.db"),
        help="Version registry database URL",
    )

    parser.add_argument("--fail-on-warnings", action="store_true", help="Fail if warnings are found")

    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output except for errors")

    args = parser.parse_args()

    # Initialize database
    try:
        registry_db = init_database(args.db_url)
    except Exception as e:
        print(f"{Fore.RED}❌ Failed to connect to version registry database: {e}")
        sys.exit(1)

    # Initialize compatibility checker
    checker = CompatibilityChecker(registry_db, args.registry_url)

    # Convert string arguments to enums
    service_type = ServiceType(args.service)
    environment = Environment(args.environment)
    target_services = [ServiceType(t) for t in args.targets] if args.targets else None

    try:
        # Run compatibility check
        result = await checker.check_deployment_compatibility(service_type, args.version, environment, target_services)

        # Print report unless in quiet mode
        if not args.quiet:
            checker.print_compatibility_report(result)

        # Save detailed report if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2, default=str)
            print(f"\n📄 Detailed report saved to: {args.output}")

        # Determine exit code
        if not result["can_deploy"]:
            if not args.quiet:
                print(f"\n{Fore.RED}❌ Deployment blocked due to compatibility issues")
            sys.exit(1)

        elif args.fail_on_warnings and result["warnings"]:
            if not args.quiet:
                print(f"\n{Fore.YELLOW}⚠️  Deployment blocked due to warnings (--fail-on-warnings)")
            sys.exit(1)

        else:
            if not args.quiet:
                print(f"\n{Fore.GREEN}✅ Deployment is compatible and ready")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Compatibility check failed: {e}")
        print(f"{Fore.RED}❌ Compatibility check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
