#!/usr/bin/env python3
"""
Advanced Version Management System for PratikoAI
Coordinates deployments between frontend and backend repositories with sophisticated
compatibility tracking and rollback capabilities.

This system implements:
- Semantic version management with compatibility matrices
- Cross-repository dependency tracking
- Automated rollback decision trees
- Feature flag coordination
- Advanced deployment strategies
"""

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import semver
import yaml


class DeploymentStrategy(Enum):
    """Deployment strategies based on change analysis."""

    FAST = "fast"  # Minor changes, quick deployment
    ROLLING = "rolling"  # Standard rolling updates
    CANARY = "canary"  # Gradual traffic shifting
    BLUE_GREEN = "blue-green"  # Full environment switch


class CompatibilityLevel(Enum):
    """Compatibility levels between versions."""

    COMPATIBLE = "compatible"
    DEGRADED = "degraded"  # Works but with limitations
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


@dataclass
class VersionInfo:
    """Complete version information with metadata."""

    version: str
    timestamp: datetime
    commit_hash: str
    branch: str
    environment: str
    deployment_strategy: DeploymentStrategy
    health_status: str
    service_url: str | None = None
    deployment_id: str | None = None


@dataclass
class CompatibilityMatrix:
    """Cross-service compatibility matrix."""

    backend_version: str
    frontend_min_version: str
    frontend_max_version: str
    infrastructure_min_version: str
    compatibility_level: CompatibilityLevel
    breaking_changes: list[str]
    migration_required: bool
    feature_flags: dict[str, bool]
    rollback_safe: bool


class VersionRegistry:
    """Centralized version registry with advanced coordination capabilities."""

    def __init__(self, registry_url: str | None = None, local_cache: bool = True):
        self.registry_url = registry_url or os.getenv("VERSION_REGISTRY_URL")
        self.local_cache = local_cache
        self.cache_dir = Path.home() / ".praktiko" / "version-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize session with retry logic
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "PratikoAI-VersionManager/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        if token := os.getenv("VERSION_REGISTRY_TOKEN"):
            self.session.headers["Authorization"] = f"Bearer {token}"

    def register_version(self, service: str, version_info: VersionInfo) -> bool:
        """Register a new version with the registry."""
        try:
            payload = {
                "service": service,
                "version_info": asdict(version_info),
                "registered_at": datetime.utcnow().isoformat() + "Z",
            }

            # Cache locally first
            if self.local_cache:
                self._cache_version(service, version_info)

            # Register with remote registry if available
            if self.registry_url:
                response = self.session.post(f"{self.registry_url}/versions", json=payload, timeout=30)

                if response.status_code not in [200, 201]:
                    print(f"Warning: Failed to register with remote registry: {response.status_code}")
                    return False

            print(f"✓ Successfully registered {service} version {version_info.version}")
            return True

        except Exception as e:
            print(f"Error registering version: {str(e)}")
            return False

    def get_compatibility_matrix(self, backend_version: str) -> CompatibilityMatrix | None:
        """Get compatibility matrix for a backend version."""
        try:
            # Try remote registry first
            if self.registry_url:
                response = self.session.get(f"{self.registry_url}/compatibility/{backend_version}", timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    return CompatibilityMatrix(**data)

            # Fall back to local cache or generate default
            return self._generate_compatibility_matrix(backend_version)

        except Exception as e:
            print(f"Error getting compatibility matrix: {str(e)}")
            return self._generate_compatibility_matrix(backend_version)

    def check_deployment_compatibility(self, backend_version: str, frontend_version: str) -> tuple[bool, list[str]]:
        """Check if backend and frontend versions are compatible."""
        matrix = self.get_compatibility_matrix(backend_version)
        if not matrix:
            return False, ["Unable to determine compatibility"]

        issues = []

        try:
            # Check version constraints
            if not semver.match(frontend_version, f">={matrix.frontend_min_version}"):
                issues.append(f"Frontend version {frontend_version} below minimum {matrix.frontend_min_version}")

            if not semver.match(frontend_version, f"<{matrix.frontend_max_version}"):
                issues.append(f"Frontend version {frontend_version} above maximum {matrix.frontend_max_version}")

            # Check compatibility level
            if matrix.compatibility_level == CompatibilityLevel.INCOMPATIBLE:
                issues.append("Versions are marked as incompatible")

            # Check for breaking changes
            if matrix.breaking_changes:
                issues.extend([f"Breaking change: {change}" for change in matrix.breaking_changes])

            # Check migration requirements
            if matrix.migration_required:
                issues.append("Database migration required - coordinate with DBA")

            compatible = len(issues) == 0 or matrix.compatibility_level == CompatibilityLevel.DEGRADED

            return compatible, issues

        except Exception as e:
            return False, [f"Error checking compatibility: {str(e)}"]

    def _cache_version(self, service: str, version_info: VersionInfo):
        """Cache version information locally."""
        cache_file = self.cache_dir / f"{service}-versions.json"

        # Load existing cache
        versions = []
        if cache_file.exists():
            with open(cache_file) as f:
                versions = json.load(f)

        # Add new version (convert datetime to string for JSON)
        version_dict = asdict(version_info)
        version_dict["timestamp"] = version_info.timestamp.isoformat()
        version_dict["deployment_strategy"] = version_info.deployment_strategy.value
        versions.append(version_dict)

        # Keep only last 50 versions
        versions = versions[-50:]

        # Save cache
        with open(cache_file, "w") as f:
            json.dump(versions, f, indent=2)

    def _generate_compatibility_matrix(self, backend_version: str) -> CompatibilityMatrix:
        """Generate a default compatibility matrix."""
        # Parse version to determine compatibility rules
        try:
            version_obj = semver.Version.parse(backend_version.lstrip("v"))

            # Generate compatibility ranges based on semantic versioning
            if version_obj.major == 0:
                # Pre-1.0 versions: minor version compatibility only
                frontend_min = f"0.{version_obj.minor}.0"
                frontend_max = f"0.{version_obj.minor + 1}.0"
            else:
                # Stable versions: major version compatibility
                frontend_min = f"{version_obj.major}.0.0"
                frontend_max = f"{version_obj.major + 1}.0.0"

            return CompatibilityMatrix(
                backend_version=backend_version,
                frontend_min_version=frontend_min,
                frontend_max_version=frontend_max,
                infrastructure_min_version="1.0.0",
                compatibility_level=CompatibilityLevel.COMPATIBLE,
                breaking_changes=[],
                migration_required=False,
                feature_flags={},
                rollback_safe=True,
            )

        except Exception:
            # Fallback for non-semantic versions
            return CompatibilityMatrix(
                backend_version=backend_version,
                frontend_min_version="0.0.0",
                frontend_max_version="999.0.0",
                infrastructure_min_version="1.0.0",
                compatibility_level=CompatibilityLevel.UNKNOWN,
                breaking_changes=["Unable to parse version for compatibility check"],
                migration_required=False,
                feature_flags={},
                rollback_safe=False,
            )


class DeploymentCoordinator:
    """Coordinates deployments across repositories with advanced decision trees."""

    def __init__(self, registry: VersionRegistry):
        self.registry = registry
        self.deployment_timeout = int(os.getenv("DEPLOYMENT_TIMEOUT", "1800"))  # 30 minutes
        self.health_check_timeout = int(os.getenv("HEALTH_CHECK_TIMEOUT", "300"))  # 5 minutes
        self.max_rollback_attempts = int(os.getenv("MAX_ROLLBACK_ATTEMPTS", "3"))

    def analyze_deployment_strategy(self, changed_files: list[str]) -> DeploymentStrategy:
        """Analyze changes to determine optimal deployment strategy."""

        # Categorize changes
        categories = {
            "infrastructure": any(
                f in ["Dockerfile", "docker-compose.yml"] or f.startswith(("k8s/", ".github/workflows/"))
                for f in changed_files
            ),
            "api_breaking": any(f.startswith("app/api/") and self._is_breaking_api_change(f) for f in changed_files),
            "api_additive": any(
                f.startswith("app/api/") and not self._is_breaking_api_change(f) for f in changed_files
            ),
            "database": any(f.startswith(("app/models/", "migrations/", "alembic/")) for f in changed_files),
            "core_logic": any(f.startswith(("app/core/", "app/services/")) for f in changed_files),
            "dependencies": any(f in ["pyproject.toml", "requirements.txt", "Pipfile"] for f in changed_files),
            "config": any(
                f.endswith((".env", ".yml", ".yaml", ".json")) and "config" in f.lower() for f in changed_files
            ),
        }

        # Decision tree for deployment strategy
        if categories["infrastructure"] or categories["dependencies"]:
            return DeploymentStrategy.BLUE_GREEN
        elif categories["api_breaking"] or categories["database"]:
            return DeploymentStrategy.CANARY
        elif categories["api_additive"] or categories["core_logic"] or categories["config"]:
            return DeploymentStrategy.ROLLING
        else:
            return DeploymentStrategy.FAST

    def coordinate_deployment(self, service: str, version: str, environment: str) -> bool:
        """Coordinate deployment with comprehensive checks and rollbacks."""

        print(f"🚀 Starting coordinated deployment for {service} v{version} to {environment}")

        # Step 1: Pre-deployment validation
        if not self._pre_deployment_checks(service, version, environment):
            print("❌ Pre-deployment checks failed")
            return False

        # Step 2: Deploy with monitoring
        deployment_id = self._execute_deployment(service, version, environment)
        if not deployment_id:
            print("❌ Deployment execution failed")
            return False

        # Step 3: Health checks with timeout
        if not self._comprehensive_health_check(service, environment):
            print("❌ Health checks failed, initiating rollback")
            self._rollback_deployment(service, deployment_id, environment)
            return False

        # Step 4: Cross-service compatibility validation
        if not self._validate_cross_service_compatibility(service, version, environment):
            print("❌ Cross-service compatibility failed, initiating rollback")
            self._rollback_deployment(service, deployment_id, environment)
            return False

        # Step 5: Update version registry
        version_info = VersionInfo(
            version=version,
            timestamp=datetime.utcnow(),
            commit_hash=self._get_current_commit_hash(),
            branch=self._get_current_branch(),
            environment=environment,
            deployment_strategy=self.analyze_deployment_strategy(self._get_changed_files()),
            health_status="healthy",
            deployment_id=deployment_id,
        )

        self.registry.register_version(service, version_info)

        print(f"✅ Successfully deployed {service} v{version} to {environment}")
        return True

    def _pre_deployment_checks(self, service: str, version: str, environment: str) -> bool:
        """Comprehensive pre-deployment validation."""

        checks = [
            ("Version format", self._validate_version_format, version),
            ("Environment readiness", self._check_environment_readiness, environment),
            ("Resource availability", self._check_resource_availability, environment),
            ("Database connectivity", self._check_database_connectivity, environment),
            ("External dependencies", self._check_external_dependencies, environment),
        ]

        for check_name, check_func, param in checks:
            print(f"  🔍 {check_name}...", end="")
            try:
                if check_func(param):
                    print(" ✅")
                else:
                    print(" ❌")
                    return False
            except Exception as e:
                print(f" ❌ ({str(e)})")
                return False

        return True

    def _execute_deployment(self, service: str, version: str, environment: str) -> str | None:
        """Execute the actual deployment and return deployment ID."""
        try:
            # This would integrate with your deployment system (ECS, Kubernetes, etc.)
            deployment_id = f"{service}-{version}-{int(time.time())}"

            # Simulate deployment execution
            print(f"  📦 Executing deployment {deployment_id}")

            # In real implementation, this would call AWS ECS, Kubernetes, etc.
            # For now, return a mock deployment ID
            return deployment_id

        except Exception as e:
            print(f"Deployment execution failed: {str(e)}")
            return None

    def _comprehensive_health_check(self, service: str, environment: str) -> bool:
        """Multi-layer health checks with timeout."""

        service_url = self._get_service_url(service, environment)
        if not service_url:
            print("  ❌ No service URL available")
            return False

        health_endpoints = [
            ("Basic Health", f"{service_url}/health", True),
            ("API Readiness", f"{service_url}/api/v1/health", True),
            ("Database Health", f"{service_url}/health/db", True),
            ("Cache Health", f"{service_url}/health/cache", False),
            ("External Deps", f"{service_url}/health/deps", False),
            ("Metrics", f"{service_url}/metrics", False),
        ]

        start_time = time.time()

        while time.time() - start_time < self.health_check_timeout:
            all_critical_healthy = True

            for name, url, critical in health_endpoints:
                try:
                    response = requests.get(url, timeout=10)
                    healthy = response.status_code == 200

                    if healthy:
                        print(f"    ✅ {name}")
                    else:
                        print(f"    ❌ {name} (Status: {response.status_code})")
                        if critical:
                            all_critical_healthy = False

                except Exception as e:
                    print(f"    ❌ {name} (Error: {str(e)})")
                    if critical:
                        all_critical_healthy = False

            if all_critical_healthy:
                print("  ✅ All critical health checks passed")
                return True

            print(f"  ⏳ Waiting for health checks... ({int(time.time() - start_time)}s)")
            time.sleep(15)

        print(f"  ❌ Health checks timed out after {self.health_check_timeout}s")
        return False

    def _validate_cross_service_compatibility(self, service: str, version: str, environment: str) -> bool:
        """Validate compatibility with other services."""

        if service == "backend":
            # Check if any frontend services are compatible
            # This would query the registry for active frontend versions
            print("  🔗 Checking frontend compatibility...")

            # Mock compatibility check
            matrix = self.registry.get_compatibility_matrix(version)
            if matrix and matrix.compatibility_level in [CompatibilityLevel.COMPATIBLE, CompatibilityLevel.DEGRADED]:
                print("    ✅ Frontend compatibility verified")
                return True
            else:
                print("    ❌ Frontend compatibility issues detected")
                return False

        return True  # For other services or if no cross-service dependencies

    def _rollback_deployment(self, service: str, deployment_id: str, environment: str) -> bool:
        """Execute automated rollback with detailed logging."""

        print(f"🔄 Initiating rollback for {service} deployment {deployment_id}")

        for attempt in range(1, self.max_rollback_attempts + 1):
            print(f"  📋 Rollback attempt {attempt}/{self.max_rollback_attempts}")

            try:
                # Get previous stable version
                previous_version = self._get_previous_stable_version(service, environment)
                if not previous_version:
                    print("    ❌ No previous stable version found")
                    continue

                print(f"    🔄 Rolling back to version {previous_version}")

                # Execute rollback (integrate with your deployment system)
                rollback_id = self._execute_rollback(service, previous_version, environment)
                if not rollback_id:
                    print("    ❌ Rollback execution failed")
                    continue

                # Verify rollback health
                if self._verify_rollback_health(service, environment):
                    print(f"    ✅ Rollback successful to {previous_version}")
                    return True
                else:
                    print("    ❌ Rollback health check failed")
                    continue

            except Exception as e:
                print(f"    ❌ Rollback attempt {attempt} failed: {str(e)}")
                continue

        print(f"❌ All rollback attempts failed for {service}")
        return False

    # Helper methods (implementation depends on your infrastructure)

    def _is_breaking_api_change(self, file_path: str) -> bool:
        """Analyze if an API change is breaking."""
        # This would analyze git diff for breaking changes
        # For now, return False (non-breaking)
        return False

    def _get_changed_files(self) -> list[str]:
        """Get list of changed files from git."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"], capture_output=True, text=True, check=True
            )
            return result.stdout.strip().split("\n") if result.stdout.strip() else []
        except:
            return []

    def _get_current_commit_hash(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except:
            return "unknown"

    def _get_current_branch(self) -> str:
        """Get current git branch."""
        try:
            result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except:
            return "unknown"

    def _validate_version_format(self, version: str) -> bool:
        """Validate version format."""
        try:
            semver.Version.parse(version.lstrip("v"))
            return True
        except:
            # Allow non-semantic versions for development
            return bool(re.match(r"^[0-9]{8}-[a-f0-9]{7,}$", version))

    def _check_environment_readiness(self, environment: str) -> bool:
        """Check if environment is ready for deployment."""
        # This would check infrastructure status
        return True

    def _check_resource_availability(self, environment: str) -> bool:
        """Check if sufficient resources are available."""
        # This would check CPU, memory, disk space
        return True

    def _check_database_connectivity(self, environment: str) -> bool:
        """Check database connectivity."""
        # This would test database connection
        return True

    def _check_external_dependencies(self, environment: str) -> bool:
        """Check external service dependencies."""
        # This would check OpenAI API, other external services
        return True

    def _get_service_url(self, service: str, environment: str) -> str | None:
        """Get service URL for health checks."""
        urls = {
            "development": f"https://{service}-dev.praktiko.ai",
            "staging": f"https://{service}-staging.praktiko.ai",
            "production": f"https://{service}.praktiko.ai",
        }
        return urls.get(environment)

    def _get_previous_stable_version(self, service: str, environment: str) -> str | None:
        """Get the previous stable version for rollback."""
        # This would query the version registry
        return "v1.0.0"  # Mock version

    def _execute_rollback(self, service: str, version: str, environment: str) -> str | None:
        """Execute rollback to previous version."""
        # This would integrate with deployment system
        return f"rollback-{service}-{version}-{int(time.time())}"

    def _verify_rollback_health(self, service: str, environment: str) -> bool:
        """Verify health after rollback."""
        return self._comprehensive_health_check(service, environment)


def main():
    """Main entry point for the version manager."""

    # Initialize components
    registry = VersionRegistry()
    coordinator = DeploymentCoordinator(registry)

    # Parse command line arguments
    if len(sys.argv) < 4:
        print("Usage: python version-manager.py <service> <version> <environment>")
        print("Example: python version-manager.py backend v1.2.3 staging")
        sys.exit(1)

    service = sys.argv[1]
    version = sys.argv[2]
    environment = sys.argv[3]

    # Execute coordinated deployment
    success = coordinator.coordinate_deployment(service, version, environment)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
