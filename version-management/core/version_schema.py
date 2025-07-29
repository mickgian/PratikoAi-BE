#!/usr/bin/env python3
"""
PratikoAI Version Management Schema
Defines the comprehensive versioning scheme for coordinated frontend/backend deployments.

This system implements:
- Semantic versioning with API compatibility tracking
- Cross-service dependency management
- Environment-specific version tracking
- API contract change detection
- Breaking change prevention
"""

import re
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import semver
from packaging import version


class ServiceType(Enum):
    """Types of services in the PratikoAI ecosystem."""
    BACKEND = "backend"
    FRONTEND_ANDROID = "frontend-android"
    FRONTEND_IOS = "frontend-ios"
    FRONTEND_DESKTOP = "frontend-desktop"
    FRONTEND_WEB = "frontend-web"
    INFRASTRUCTURE = "infrastructure"
    MCP_SERVER = "mcp-server"


class ChangeType(Enum):
    """Types of changes that can occur between versions."""
    MAJOR = "major"          # Breaking changes
    MINOR = "minor"          # New features, backward compatible
    PATCH = "patch"          # Bug fixes, backward compatible
    PRERELEASE = "prerelease"  # Beta, alpha, RC versions
    BUILD = "build"          # Build metadata only


class CompatibilityLevel(Enum):
    """Compatibility levels between service versions."""
    FULLY_COMPATIBLE = "fully_compatible"
    BACKWARD_COMPATIBLE = "backward_compatible"
    FORWARD_COMPATIBLE = "forward_compatible"
    LIMITED_COMPATIBLE = "limited_compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


class Environment(Enum):
    """Deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class APIEndpoint:
    """Represents an API endpoint for contract tracking."""
    path: str
    method: str
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    parameters: Optional[List[Dict[str, Any]]] = None
    deprecated_in_version: Optional[str] = None
    removed_in_version: Optional[str] = None
    added_in_version: Optional[str] = None


@dataclass
class APIContract:
    """Complete API contract definition."""
    version: str
    service_type: ServiceType
    endpoints: List[APIEndpoint] = field(default_factory=list)
    schemas: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    breaking_changes: List[str] = field(default_factory=list)
    deprecations: List[str] = field(default_factory=list)
    new_features: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class VersionDependency:
    """Represents a dependency between service versions."""
    service_type: ServiceType
    min_version: str
    max_version: Optional[str] = None
    exact_version: Optional[str] = None
    optional: bool = False
    reason: Optional[str] = None


@dataclass
class ServiceVersion:
    """Complete version information for a service."""
    service_type: ServiceType
    version: str
    git_commit: str
    git_branch: str
    build_number: Optional[int] = None
    
    # Version metadata
    change_type: ChangeType = ChangeType.PATCH
    release_notes: str = ""
    breaking_changes: List[str] = field(default_factory=list)
    new_features: List[str] = field(default_factory=list)
    bug_fixes: List[str] = field(default_factory=list)
    
    # Dependencies
    dependencies: List[VersionDependency] = field(default_factory=list)
    
    # API contract (for backend services)
    api_contract: Optional[APIContract] = None
    
    # Deployment tracking
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    
    # Environment deployments
    deployments: Dict[Environment, datetime] = field(default_factory=dict)
    
    # Compatibility matrix
    compatibility_matrix: Dict[str, CompatibilityLevel] = field(default_factory=dict)
    
    # Feature flags
    feature_flags: Dict[str, bool] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate version format on creation."""
        if not self.is_valid_version(self.version):
            raise ValueError(f"Invalid version format: {self.version}")
    
    @staticmethod
    def is_valid_version(version_str: str) -> bool:
        """Validate if a version string follows our versioning scheme."""
        # Support semantic versioning (1.2.3) and date-based (20240128-abc123)
        semantic_pattern = r'^v?\d+\.\d+\.\d+(?:-[\w\.-]+)?(?:\+[\w\.-]+)?$'
        date_pattern = r'^\d{8}-[a-f0-9]{7,}$'
        
        return bool(re.match(semantic_pattern, version_str) or 
                   re.match(date_pattern, version_str))
    
    def is_semantic_version(self) -> bool:
        """Check if this version uses semantic versioning."""
        semantic_pattern = r'^v?\d+\.\d+\.\d+(?:-[\w\.-]+)?(?:\+[\w\.-]+)?$'
        return bool(re.match(semantic_pattern, self.version))
    
    def compare_versions(self, other_version: str) -> int:
        """
        Compare this version with another version.
        Returns: -1 if this < other, 0 if equal, 1 if this > other
        """
        if self.is_semantic_version() and ServiceVersion.is_valid_version(other_version):
            try:
                return semver.compare(self.version.lstrip('v'), other_version.lstrip('v'))
            except ValueError:
                pass
        
        # Fall back to string comparison for date-based versions
        return (self.version > other_version) - (self.version < other_version)
    
    def is_compatible_with(self, other_service_type: ServiceType, other_version: str) -> CompatibilityLevel:
        """Check compatibility with another service version."""
        key = f"{other_service_type.value}:{other_version}"
        return self.compatibility_matrix.get(key, CompatibilityLevel.UNKNOWN)
    
    def add_dependency(self, service_type: ServiceType, min_version: str, 
                      max_version: Optional[str] = None, reason: Optional[str] = None):
        """Add a dependency on another service version."""
        dependency = VersionDependency(
            service_type=service_type,
            min_version=min_version,
            max_version=max_version,
            reason=reason
        )
        self.dependencies.append(dependency)
    
    def satisfies_dependency(self, dependency: VersionDependency, available_version: str) -> bool:
        """Check if an available version satisfies a dependency requirement."""
        try:
            if dependency.exact_version:
                return available_version == dependency.exact_version
            
            # Check minimum version
            if semver.compare(available_version.lstrip('v'), dependency.min_version.lstrip('v')) < 0:
                return False
            
            # Check maximum version if specified
            if dependency.max_version:
                if semver.compare(available_version.lstrip('v'), dependency.max_version.lstrip('v')) > 0:
                    return False
            
            return True
            
        except ValueError:
            # Fall back to string comparison for non-semantic versions
            if dependency.exact_version:
                return available_version == dependency.exact_version
            
            return available_version >= dependency.min_version and \
                   (not dependency.max_version or available_version <= dependency.max_version)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        
        # Convert enums to strings
        data['service_type'] = self.service_type.value
        data['change_type'] = self.change_type.value
        
        # Convert datetime objects
        data['created_at'] = self.created_at.isoformat()
        data['deployments'] = {
            env.value if isinstance(env, Environment) else env: dt.isoformat() 
            for env, dt in self.deployments.items()
        }
        
        # Convert compatibility matrix
        data['compatibility_matrix'] = {
            key: level.value if isinstance(level, CompatibilityLevel) else level
            for key, level in self.compatibility_matrix.items()
        }
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceVersion':
        """Create instance from dictionary."""
        # Convert string enums back to enum objects
        data['service_type'] = ServiceType(data['service_type'])
        data['change_type'] = ChangeType(data['change_type'])
        
        # Convert datetime strings back to datetime objects
        data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        
        # Convert deployments
        deployments = {}
        for env_str, dt_str in data.get('deployments', {}).items():
            env = Environment(env_str) if isinstance(env_str, str) else env_str
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            deployments[env] = dt
        data['deployments'] = deployments
        
        # Convert compatibility matrix
        compatibility_matrix = {}
        for key, level_str in data.get('compatibility_matrix', {}).items():
            level = CompatibilityLevel(level_str) if isinstance(level_str, str) else level_str
            compatibility_matrix[key] = level
        data['compatibility_matrix'] = compatibility_matrix
        
        # Convert dependencies
        dependencies = []
        for dep_data in data.get('dependencies', []):
            if isinstance(dep_data, dict):
                dep_data['service_type'] = ServiceType(dep_data['service_type'])
                dependencies.append(VersionDependency(**dep_data))
            else:
                dependencies.append(dep_data)
        data['dependencies'] = dependencies
        
        # Convert API contract if present
        if data.get('api_contract'):
            contract_data = data['api_contract']
            if isinstance(contract_data, dict):
                contract_data['service_type'] = ServiceType(contract_data['service_type'])
                contract_data['created_at'] = datetime.fromisoformat(
                    contract_data['created_at'].replace('Z', '+00:00')
                )
                
                # Convert endpoints
                endpoints = []
                for endpoint_data in contract_data.get('endpoints', []):
                    if isinstance(endpoint_data, dict):
                        endpoints.append(APIEndpoint(**endpoint_data))
                    else:
                        endpoints.append(endpoint_data)
                contract_data['endpoints'] = endpoints
                
                data['api_contract'] = APIContract(**contract_data)
        
        return cls(**data)


class VersioningScheme:
    """Manages the overall versioning scheme for PratikoAI."""
    
    # Version patterns
    SEMANTIC_VERSION_PATTERN = r'^v?(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\.-]+))?(?:\+([a-zA-Z0-9\.-]+))?$'
    DATE_VERSION_PATTERN = r'^(\d{8})-([a-f0-9]{7,})(?:-(.+))?$'
    
    @staticmethod
    def generate_version(service_type: ServiceType, change_type: ChangeType, 
                        current_version: Optional[str] = None, 
                        environment: Environment = Environment.DEVELOPMENT) -> str:
        """Generate a new version based on the change type and environment."""
        
        if environment == Environment.PRODUCTION:
            # Production uses semantic versioning
            if current_version and ServiceVersion.is_valid_version(current_version):
                try:
                    if change_type == ChangeType.MAJOR:
                        return semver.bump_major(current_version.lstrip('v'))
                    elif change_type == ChangeType.MINOR:
                        return semver.bump_minor(current_version.lstrip('v'))
                    elif change_type == ChangeType.PATCH:
                        return semver.bump_patch(current_version.lstrip('v'))
                    elif change_type == ChangeType.PRERELEASE:
                        return semver.bump_prerelease(current_version.lstrip('v'))
                except ValueError:
                    pass
            
            # Default semantic version
            return "1.0.0"
        
        else:
            # Development/staging uses date-based versioning
            date_str = datetime.now().strftime("%Y%m%d")
            
            # Get current git commit (would be implemented with git commands)
            commit_hash = "abc1234"  # This would be fetched from git
            
            if environment == Environment.STAGING:
                return f"{date_str}-{commit_hash}-staging"
            else:
                return f"{date_str}-{commit_hash}"
    
    @staticmethod
    def parse_version(version_str: str) -> Dict[str, Any]:
        """Parse a version string and extract components."""
        # Try semantic version first
        semantic_match = re.match(VersioningScheme.SEMANTIC_VERSION_PATTERN, version_str)
        if semantic_match:
            major, minor, patch, prerelease, build = semantic_match.groups()
            return {
                'type': 'semantic',
                'major': int(major),
                'minor': int(minor),
                'patch': int(patch),
                'prerelease': prerelease,
                'build': build,
                'raw': version_str
            }
        
        # Try date-based version
        date_match = re.match(VersioningScheme.DATE_VERSION_PATTERN, version_str)
        if date_match:
            date_str, commit_hash, suffix = date_match.groups()
            return {
                'type': 'date',
                'date': date_str,
                'commit': commit_hash,
                'suffix': suffix,
                'raw': version_str
            }
        
        return {'type': 'unknown', 'raw': version_str}
    
    @staticmethod
    def is_breaking_change(from_version: str, to_version: str) -> bool:
        """Determine if the version change represents a breaking change."""
        from_parsed = VersioningScheme.parse_version(from_version)
        to_parsed = VersioningScheme.parse_version(to_version)
        
        # For semantic versions, major version bump is breaking
        if from_parsed['type'] == 'semantic' and to_parsed['type'] == 'semantic':
            return to_parsed['major'] > from_parsed['major']
        
        # For date-based versions, assume no breaking changes within the same day
        if from_parsed['type'] == 'date' and to_parsed['type'] == 'date':
            return from_parsed['date'] != to_parsed['date']
        
        # Mixed or unknown types - assume potential breaking change
        return True


# Version compatibility rules
class CompatibilityRules:
    """Defines compatibility rules between different service types."""
    
    COMPATIBILITY_MATRIX = {
        # Backend compatibility rules
        ServiceType.BACKEND: {
            ServiceType.FRONTEND_ANDROID: {
                "same_major": CompatibilityLevel.FULLY_COMPATIBLE,
                "one_major_behind": CompatibilityLevel.BACKWARD_COMPATIBLE,
                "one_major_ahead": CompatibilityLevel.FORWARD_COMPATIBLE,
                "default": CompatibilityLevel.INCOMPATIBLE
            },
            ServiceType.FRONTEND_IOS: {
                "same_major": CompatibilityLevel.FULLY_COMPATIBLE,
                "one_major_behind": CompatibilityLevel.BACKWARD_COMPATIBLE,
                "one_major_ahead": CompatibilityLevel.FORWARD_COMPATIBLE,
                "default": CompatibilityLevel.INCOMPATIBLE
            },
            ServiceType.FRONTEND_WEB: {
                "same_major": CompatibilityLevel.FULLY_COMPATIBLE,
                "one_major_behind": CompatibilityLevel.BACKWARD_COMPATIBLE,
                "one_major_ahead": CompatibilityLevel.FORWARD_COMPATIBLE,
                "default": CompatibilityLevel.INCOMPATIBLE
            }
        }
    }
    
    @staticmethod
    def check_compatibility(service1_type: ServiceType, service1_version: str,
                          service2_type: ServiceType, service2_version: str) -> CompatibilityLevel:
        """Check compatibility between two service versions."""
        
        # Parse versions
        v1_parsed = VersioningScheme.parse_version(service1_version)
        v2_parsed = VersioningScheme.parse_version(service2_version)
        
        # Only check compatibility for semantic versions
        if v1_parsed['type'] != 'semantic' or v2_parsed['type'] != 'semantic':
            return CompatibilityLevel.UNKNOWN
        
        # Get compatibility rules for this service pair
        rules = CompatibilityRules.COMPATIBILITY_MATRIX.get(service1_type, {}).get(service2_type, {})
        if not rules:
            return CompatibilityLevel.UNKNOWN
        
        # Compare major versions
        v1_major = v1_parsed['major']
        v2_major = v2_parsed['major']
        
        if v1_major == v2_major:
            return rules.get("same_major", CompatibilityLevel.UNKNOWN)
        elif v1_major == v2_major - 1:
            return rules.get("one_major_behind", CompatibilityLevel.INCOMPATIBLE)
        elif v1_major == v2_major + 1:
            return rules.get("one_major_ahead", CompatibilityLevel.INCOMPATIBLE)
        else:
            return rules.get("default", CompatibilityLevel.INCOMPATIBLE)


# Example usage and testing
if __name__ == "__main__":
    # Create a backend version
    backend_version = ServiceVersion(
        service_type=ServiceType.BACKEND,
        version="1.2.3",
        git_commit="abc123def456",
        git_branch="main",
        change_type=ChangeType.MINOR,
        release_notes="Added new chat endpoints and improved performance",
        new_features=["New chat streaming API", "Enhanced authentication"],
        bug_fixes=["Fixed memory leak in connection pool"]
    )
    
    # Add dependencies
    backend_version.add_dependency(
        ServiceType.INFRASTRUCTURE,
        min_version="1.1.0",
        reason="Requires new database schema"
    )
    
    # Create API contract
    api_contract = APIContract(
        version="1.2.3",
        service_type=ServiceType.BACKEND,
        endpoints=[
            APIEndpoint(
                path="/api/v1/chat/stream",
                method="POST",
                added_in_version="1.2.0"
            )
        ],
        new_features=["Streaming chat API"]
    )
    backend_version.api_contract = api_contract
    
    # Test serialization
    version_dict = backend_version.to_dict()
    print("Serialized version:")
    print(json.dumps(version_dict, indent=2, default=str))
    
    # Test compatibility
    compatibility = CompatibilityRules.check_compatibility(
        ServiceType.BACKEND, "1.2.3",
        ServiceType.FRONTEND_ANDROID, "1.2.1"
    )
    print(f"\nCompatibility: {compatibility}")
    
    # Test version generation
    new_version = VersioningScheme.generate_version(
        ServiceType.FRONTEND_ANDROID,
        ChangeType.PATCH,
        "1.2.3",
        Environment.PRODUCTION
    )
    print(f"New version: {new_version}")