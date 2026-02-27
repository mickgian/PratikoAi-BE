#!/usr/bin/env python3
"""PratikoAI Version Management CLI
Comprehensive command-line interface for managing versions, checking compatibility,
and coordinating deployments across services.

This CLI provides:
- Version registration and querying
- Compatibility checking
- Deployment validation
- API contract management
- Developer-friendly commands
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import click
import requests
from colorama import Back, Fore, Style, init
from tabulate import tabulate

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.version_schema import CompatibilityLevel, Environment, ServiceType
from registry.database import VersionRegistryDB, init_database
from scripts.compatibility_checker import CompatibilityChecker

# Initialize colorama
init(autoreset=True)


class VersionCLI:
    """Main CLI class for version management operations."""

    def __init__(self):
        self.registry_url = os.getenv("VERSION_REGISTRY_URL", "http://localhost:8001")
        self.registry_token = os.getenv("VERSION_REGISTRY_TOKEN")
        self.db_url = os.getenv("VERSION_REGISTRY_DB_URL", "sqlite:///version_registry.db")

        # Setup API session
        self.session = requests.Session()
        if self.registry_token:
            self.session.headers["Authorization"] = f"Bearer {self.registry_token}"

        # Initialize database connection
        try:
            self.registry_db = init_database(self.db_url)
        except Exception as e:
            print(f"{Fore.RED}Warning: Could not connect to database: {e}")
            self.registry_db = None

    def print_header(self, title: str):
        """Print a formatted header."""
        print()
        print("=" * 80)
        print(f"{Fore.CYAN}{Back.BLACK} {title} {Style.RESET_ALL}")
        print("=" * 80)

    def print_success(self, message: str):
        """Print success message."""
        print(f"{Fore.GREEN}✅ {message}")

    def print_error(self, message: str):
        """Print error message."""
        print(f"{Fore.RED}❌ {message}")

    def print_warning(self, message: str):
        """Print warning message."""
        print(f"{Fore.YELLOW}⚠️  {message}")

    def print_info(self, message: str):
        """Print info message."""
        print(f"{Fore.BLUE}ℹ️  {message}")

    def call_api(self, method: str, endpoint: str, data: dict = None) -> dict[str, Any]:
        """Make API call to version registry."""
        url = f"{self.registry_url.rstrip('/')}{endpoint}"

        try:
            if method.upper() == "GET":
                response = self.session.get(url, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if response.status_code in [200, 201]:
                return response.json()
            else:
                error_msg = f"API call failed: {response.status_code}"
                try:
                    error_detail = response.json().get("detail", response.text)
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {response.text}"

                raise RuntimeError(error_msg)

        except requests.RequestException as e:
            raise RuntimeError(f"Network error: {str(e)}")

    def list_versions(self, service_type: str = None, limit: int = 20):
        """List versions for services."""
        self.print_header("📋 Version List")

        try:
            if service_type:
                # List versions for specific service
                service = ServiceType(service_type)
                endpoint = f"/api/v1/versions/{service.value}?limit={limit}"
                result = self.call_api("GET", endpoint)

                versions = result.get("versions", [])
                if not versions:
                    self.print_info(f"No versions found for {service.value}")
                    return

                # Format table
                headers = ["Version", "Change Type", "Created At", "Breaking Changes", "Deployments"]
                rows = []

                for version in versions:
                    rows.append(
                        [
                            version["version"],
                            version["change_type"],
                            version["created_at"][:10],  # Date only
                            "Yes" if version["breaking_changes"] else "No",
                            ", ".join(version.get("deployments", [])),
                        ]
                    )

                print(f"\n{Fore.CYAN}Service: {service.value}")
                print(tabulate(rows, headers=headers, tablefmt="grid"))

            else:
                # List latest version for each service
                services = [s.value for s in ServiceType]
                headers = ["Service", "Latest Version", "Change Type", "Created At", "Deployments"]
                rows = []

                for service in services:
                    try:
                        endpoint = f"/api/v1/versions/{service}/latest"
                        result = self.call_api("GET", endpoint)

                        rows.append(
                            [
                                service,
                                result["version"],
                                result["change_type"],
                                result["created_at"][:10],
                                "N/A",  # Would need to fetch deployment info
                            ]
                        )
                    except:
                        rows.append([service, "No versions", "-", "-", "-"])

                print(tabulate(rows, headers=headers, tablefmt="grid"))

        except Exception as e:
            self.print_error(f"Failed to list versions: {str(e)}")

    def show_version(self, service_type: str, version: str):
        """Show detailed information about a specific version."""
        self.print_header(f"📄 Version Details: {service_type} v{version}")

        try:
            service = ServiceType(service_type)
            endpoint = f"/api/v1/versions/{service.value}/{version}"
            result = self.call_api("GET", endpoint)

            # Basic information
            print(f"{Fore.CYAN}📋 Basic Information:")
            print(f"  Service Type: {result['service_type']}")
            print(f"  Version: {result['version']}")
            print(f"  Git Commit: {result['git_commit']}")
            print(f"  Git Branch: {result['git_branch']}")
            print(f"  Change Type: {result['change_type']}")
            print(f"  Created At: {result['created_at']}")
            print(f"  Created By: {result['created_by']}")

            # Release notes
            if result.get("release_notes"):
                print(f"\n{Fore.CYAN}📝 Release Notes:")
                print(f"  {result['release_notes']}")

            # Changes
            if result.get("breaking_changes"):
                print(f"\n{Fore.RED}💥 Breaking Changes:")
                for change in result["breaking_changes"]:
                    print(f"  • {change}")

            if result.get("new_features"):
                print(f"\n{Fore.GREEN}✨ New Features:")
                for feature in result["new_features"]:
                    print(f"  • {feature}")

            if result.get("bug_fixes"):
                print(f"\n{Fore.BLUE}🐛 Bug Fixes:")
                for fix in result["bug_fixes"]:
                    print(f"  • {fix}")

            # Deployments
            if result.get("deployments"):
                print(f"\n{Fore.CYAN}🚀 Deployments:")
                for env, timestamp in result["deployments"].items():
                    print(f"  {env}: {timestamp}")

            # Feature flags
            if result.get("feature_flags"):
                print(f"\n{Fore.CYAN}🎛️  Feature Flags:")
                for flag, enabled in result["feature_flags"].items():
                    status = "Enabled" if enabled else "Disabled"
                    color = Fore.GREEN if enabled else Fore.RED
                    print(f"  {flag}: {color}{status}")

        except Exception as e:
            self.print_error(f"Failed to show version: {str(e)}")

    def check_compatibility(self, service_type: str, version: str, environment: str = "development"):
        """Check compatibility for a version deployment."""
        self.print_header(f"🔍 Compatibility Check: {service_type} v{version}")

        try:
            if not self.registry_db:
                self.print_error("Database connection required for compatibility checking")
                return

            # Use the compatibility checker
            checker = CompatibilityChecker(self.registry_db, self.registry_url)

            # Run async compatibility check
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                checker.check_deployment_compatibility(ServiceType(service_type), version, Environment(environment))
            )

            # Print formatted report
            checker.print_compatibility_report(result)

        except Exception as e:
            self.print_error(f"Compatibility check failed: {str(e)}")

    def show_deployments(self, environment: str = None):
        """Show current deployment status."""
        if environment:
            self.print_header(f"🚀 Deployment Status: {environment}")
            environments = [environment]
        else:
            self.print_header("🚀 All Deployment Status")
            environments = [e.value for e in Environment]

        try:
            for env in environments:
                endpoint = f"/api/v1/deployments/{env}"
                result = self.call_api("GET", endpoint)

                print(f"\n{Fore.CYAN}Environment: {env}")

                services = result.get("services", {})
                if not services:
                    print("  No deployments found")
                    continue

                headers = ["Service", "Version", "Deployed At", "Status", "Health"]
                rows = []

                for service, info in services.items():
                    health_status = "✅" if info.get("health_check_passed", True) else "❌"
                    rows.append(
                        [
                            service,
                            info["version"],
                            info["deployed_at"][:16],  # Date and time
                            info.get("status", "unknown"),
                            health_status,
                        ]
                    )

                print(tabulate(rows, headers=headers, tablefmt="grid"))

        except Exception as e:
            self.print_error(f"Failed to show deployments: {str(e)}")

    def validate_deployment(self, service_type: str, version: str, environment: str):
        """Validate if a deployment is safe."""
        self.print_header(f"✅ Deployment Validation: {service_type} v{version} → {environment}")

        try:
            endpoint = "/api/v1/validate-deployment"
            params = {"service_type": service_type, "version": version, "environment": environment}

            result = self.call_api("POST", endpoint, params)

            # Show validation results
            can_deploy = result.get("can_deploy", False)
            status_color = Fore.GREEN if can_deploy else Fore.RED
            status_symbol = "✅" if can_deploy else "❌"

            print(f"\n{status_color}{status_symbol} Deployment Status: {'ALLOWED' if can_deploy else 'BLOCKED'}")

            # Show blocking issues
            blocking_issues = result.get("blocking_issues", [])
            if blocking_issues:
                print(f"\n{Fore.RED}🚫 Blocking Issues:")
                for issue in blocking_issues:
                    print(f"  • {issue}")

            # Show warnings
            warnings = result.get("warnings", [])
            if warnings:
                print(f"\n{Fore.YELLOW}⚠️  Warnings:")
                for warning in warnings:
                    print(f"  • {warning}")

            # Show dependency checks
            dependency_checks = result.get("dependency_checks", [])
            if dependency_checks:
                print(f"\n{Fore.BLUE}🔗 Dependency Analysis:")
                for dep in dependency_checks:
                    if "min_version" in dep:  # Dependency requirement
                        status = "✅" if dep.get("satisfied", True) else "❌"
                        print(f"  {status} {dep['service_type']}: requires {dep['min_version']}")
                    else:  # Compatibility check
                        compat_color = Fore.GREEN if dep.get("compatible", True) else Fore.RED
                        print(f"  {compat_color}🔗 {dep['target_service']}: {dep['compatibility_level']}")

        except Exception as e:
            self.print_error(f"Deployment validation failed: {str(e)}")

    def show_compatibility_matrix(self, service_type: str, version: str):
        """Show compatibility matrix for a version."""
        self.print_header(f"🔗 Compatibility Matrix: {service_type} v{version}")

        try:
            endpoint = f"/api/v1/compatibility/{service_type}/{version}"
            result = self.call_api("GET", endpoint)

            # Show compatibility matrix
            matrix = result.get("compatibility_matrix", {})
            if matrix:
                print(f"\n{Fore.CYAN}📊 Compatibility Matrix:")
                headers = ["Target Service", "Version", "Compatibility Level"]
                rows = []

                for key, level in matrix.items():
                    if ":" in key:
                        target_service, target_version = key.split(":", 1)

                        # Color code compatibility levels
                        if level == "fully_compatible":
                            level_display = f"{Fore.GREEN}✅ {level}"
                        elif level in ["backward_compatible", "forward_compatible"] or level == "limited_compatible":
                            level_display = f"{Fore.YELLOW}⚠️  {level}"
                        elif level == "incompatible":
                            level_display = f"{Fore.RED}❌ {level}"
                        else:
                            level_display = f"{Fore.GRAY}? {level}"

                        rows.append([target_service, target_version, level_display])

                if rows:
                    print(tabulate(rows, headers=headers, tablefmt="grid"))
                else:
                    print("  No compatibility data available")

            # Show dependencies
            dependencies = result.get("dependencies", [])
            if dependencies:
                print(f"\n{Fore.CYAN}📋 Dependencies:")
                headers = ["Service", "Min Version", "Max Version", "Optional", "Reason"]
                rows = []

                for dep in dependencies:
                    rows.append(
                        [
                            dep["service_type"],
                            dep["min_version"],
                            dep.get("max_version", "N/A"),
                            "Yes" if dep.get("optional", False) else "No",
                            dep.get("reason", "N/A"),
                        ]
                    )

                print(tabulate(rows, headers=headers, tablefmt="grid"))

        except Exception as e:
            self.print_error(f"Failed to show compatibility matrix: {str(e)}")

    def cleanup_versions(self, service_type: str, keep_count: int = 50):
        """Clean up old versions for a service."""
        self.print_header(f"🧹 Cleanup Versions: {service_type}")

        try:
            endpoint = f"/api/v1/versions/{service_type}/cleanup?keep_count={keep_count}"
            result = self.call_api("DELETE", endpoint)

            message = result.get("message", "Cleanup completed")
            self.print_success(message)

        except Exception as e:
            self.print_error(f"Cleanup failed: {str(e)}")

    def register_version_interactive(self):
        """Interactive version registration."""
        self.print_header("📝 Interactive Version Registration")

        try:
            # Collect information interactively
            print(f"{Fore.CYAN}Please provide the following information:")

            # Service type
            services = [s.value for s in ServiceType]
            print(f"\nAvailable services: {', '.join(services)}")
            service_type = input("Service type: ").strip()

            if service_type not in services:
                self.print_error(f"Invalid service type. Must be one of: {', '.join(services)}")
                return

            # Version
            version = input("Version: ").strip()
            if not version:
                self.print_error("Version is required")
                return

            # Git information
            try:
                git_commit = os.popen("git rev-parse HEAD").read().strip()
                git_branch = os.popen("git branch --show-current").read().strip()
            except:
                git_commit = input("Git commit hash: ").strip()
                git_branch = input("Git branch: ").strip()

            # Change type
            change_types = ["patch", "minor", "major"]
            print(f"\nChange types: {', '.join(change_types)}")
            change_type = input("Change type (patch): ").strip() or "patch"

            if change_type not in change_types:
                self.print_error(f"Invalid change type. Must be one of: {', '.join(change_types)}")
                return

            # Release notes
            print("\nEnter release notes (press Enter twice to finish):")
            release_notes = []
            while True:
                line = input()
                if not line and release_notes:
                    break
                release_notes.append(line)

            release_notes_text = "\n".join(release_notes)

            # Prepare registration data
            registration_data = {
                "service_type": service_type,
                "version": version,
                "git_commit": git_commit,
                "git_branch": git_branch,
                "change_type": change_type,
                "release_notes": release_notes_text,
                "breaking_changes": [],
                "new_features": [],
                "bug_fixes": [],
                "dependencies": [],
                "created_by": os.getenv("USER", "cli-user"),
            }

            print(f"\n{Fore.CYAN}Registration Summary:")
            print(f"  Service: {service_type}")
            print(f"  Version: {version}")
            print(f"  Change Type: {change_type}")
            print(f"  Git Commit: {git_commit}")
            print(f"  Git Branch: {git_branch}")

            # Confirm registration
            confirm = input(f"\n{Fore.YELLOW}Proceed with registration? (y/N): ").strip().lower()
            if confirm != "y":
                print("Registration cancelled")
                return

            # Register version
            endpoint = "/api/v1/versions/register"
            result = self.call_api("POST", endpoint, registration_data)

            version_id = result.get("version_id")
            self.print_success(f"Version registered successfully! ID: {version_id}")

        except Exception as e:
            self.print_error(f"Interactive registration failed: {str(e)}")


def main():
    """Main CLI entry point."""
    cli = VersionCLI()

    parser = argparse.ArgumentParser(
        description="PratikoAI Version Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list --service backend
  %(prog)s show backend 1.2.3
  %(prog)s check backend 1.2.3 --environment production
  %(prog)s deployments --environment staging
  %(prog)s validate backend 1.3.0 production
  %(prog)s matrix backend 1.2.3
  %(prog)s register
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List versions")
    list_parser.add_argument("--service", help="Service type to filter by")
    list_parser.add_argument("--limit", type=int, default=20, help="Maximum number of versions to show")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show version details")
    show_parser.add_argument("service", help="Service type")
    show_parser.add_argument("version", help="Version to show")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check compatibility")
    check_parser.add_argument("service", help="Service type")
    check_parser.add_argument("version", help="Version to check")
    check_parser.add_argument("--environment", default="development", help="Target environment")

    # Deployments command
    deploy_parser = subparsers.add_parser("deployments", help="Show deployment status")
    deploy_parser.add_argument("--environment", help="Environment to show")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate deployment")
    validate_parser.add_argument("service", help="Service type")
    validate_parser.add_argument("version", help="Version to validate")
    validate_parser.add_argument("environment", help="Target environment")

    # Matrix command
    matrix_parser = subparsers.add_parser("matrix", help="Show compatibility matrix")
    matrix_parser.add_argument("service", help="Service type")
    matrix_parser.add_argument("version", help="Version")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old versions")
    cleanup_parser.add_argument("service", help="Service type")
    cleanup_parser.add_argument("--keep", type=int, default=50, help="Number of versions to keep")

    # Register command
    subparsers.add_parser("register", help="Register version interactively")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "list":
            cli.list_versions(args.service, args.limit)
        elif args.command == "show":
            cli.show_version(args.service, args.version)
        elif args.command == "check":
            cli.check_compatibility(args.service, args.version, args.environment)
        elif args.command == "deployments":
            cli.show_deployments(args.environment)
        elif args.command == "validate":
            cli.validate_deployment(args.service, args.version, args.environment)
        elif args.command == "matrix":
            cli.show_compatibility_matrix(args.service, args.version)
        elif args.command == "cleanup":
            cli.cleanup_versions(args.service, args.keep)
        elif args.command == "register":
            cli.register_version_interactive()

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
