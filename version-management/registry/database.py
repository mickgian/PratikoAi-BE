#!/usr/bin/env python3
"""PratikoAI Version Registry Database
Comprehensive database layer for tracking service versions, deployments, and compatibility.

This module provides:
- SQLAlchemy models for version tracking
- Database operations for version management
- Migration scripts for schema updates
- Query helpers for compatibility checking
"""

import json
import os
import uuid
from datetime import UTC, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

from ..core.version_schema import (
    APIContract,
    ChangeType,
    CompatibilityLevel,
    Environment,
    ServiceType,
    ServiceVersion,
    VersionDependency,
)

Base = declarative_base()


class ServiceVersionModel(Base):
    """Database model for service versions."""

    __tablename__ = "service_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_type = Column(SQLEnum(ServiceType), nullable=False)
    version = Column(String(50), nullable=False)
    git_commit = Column(String(40), nullable=False)
    git_branch = Column(String(100), nullable=False)
    build_number = Column(Integer, nullable=True)

    # Version metadata
    change_type = Column(SQLEnum(ChangeType), nullable=False, default=ChangeType.PATCH)
    release_notes = Column(Text, default="")
    breaking_changes = Column(JSON, default=list)
    new_features = Column(JSON, default=list)
    bug_fixes = Column(JSON, default=list)

    # API contract (stored as JSON for backend services)
    api_contract = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    created_by = Column(String(100), default="system")

    # Feature flags
    feature_flags = Column(JSON, default=dict)

    # Relationships
    dependencies = relationship("VersionDependencyModel", back_populates="service_version")
    deployments = relationship("DeploymentModel", back_populates="service_version")
    compatibility_checks = relationship("CompatibilityCheckModel", back_populates="source_version")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("service_type", "version", name="_service_version_uc"),
        Index("idx_service_type_version", "service_type", "version"),
        Index("idx_created_at", "created_at"),
        Index("idx_git_commit", "git_commit"),
    )

    def to_service_version(self) -> ServiceVersion:
        """Convert database model to ServiceVersion object."""
        # Convert dependencies
        dependencies = []
        for dep_model in self.dependencies:
            dependencies.append(
                VersionDependency(
                    service_type=dep_model.dependency_service_type,
                    min_version=dep_model.min_version,
                    max_version=dep_model.max_version,
                    exact_version=dep_model.exact_version,
                    optional=dep_model.optional,
                    reason=dep_model.reason,
                )
            )

        # Convert deployments
        deployments = {}
        for dep_model in self.deployments:
            deployments[dep_model.environment] = dep_model.deployed_at

        # Convert API contract
        api_contract = None
        if self.api_contract:
            api_contract = APIContract(**self.api_contract)

        # Build compatibility matrix from compatibility checks
        compatibility_matrix = {}
        for check in self.compatibility_checks:
            key = f"{check.target_service_type.value}:{check.target_version}"
            compatibility_matrix[key] = check.compatibility_level

        return ServiceVersion(
            service_type=self.service_type,
            version=self.version,
            git_commit=self.git_commit,
            git_branch=self.git_branch,
            build_number=self.build_number,
            change_type=self.change_type,
            release_notes=self.release_notes,
            breaking_changes=self.breaking_changes or [],
            new_features=self.new_features or [],
            bug_fixes=self.bug_fixes or [],
            dependencies=dependencies,
            api_contract=api_contract,
            created_at=self.created_at,
            created_by=self.created_by,
            deployments=deployments,
            compatibility_matrix=compatibility_matrix,
            feature_flags=self.feature_flags or {},
        )


class VersionDependencyModel(Base):
    """Database model for version dependencies."""

    __tablename__ = "version_dependencies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_version_id = Column(UUID(as_uuid=True), ForeignKey("service_versions.id"), nullable=False)
    dependency_service_type = Column(SQLEnum(ServiceType), nullable=False)
    min_version = Column(String(50), nullable=False)
    max_version = Column(String(50), nullable=True)
    exact_version = Column(String(50), nullable=True)
    optional = Column(Boolean, default=False)
    reason = Column(Text, nullable=True)

    # Relationships
    service_version = relationship("ServiceVersionModel", back_populates="dependencies")

    # Indexes
    __table_args__ = (Index("idx_service_version_dependency", "service_version_id", "dependency_service_type"),)


class DeploymentModel(Base):
    """Database model for tracking deployments."""

    __tablename__ = "deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_version_id = Column(UUID(as_uuid=True), ForeignKey("service_versions.id"), nullable=False)
    environment = Column(SQLEnum(Environment), nullable=False)
    deployed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    deployed_by = Column(String(100), default="system")
    deployment_id = Column(String(100), nullable=True)  # External deployment system ID

    # Deployment status
    status = Column(String(20), default="deployed")  # deployed, failed, rolled_back
    health_check_passed = Column(Boolean, default=True)
    rollback_version = Column(String(50), nullable=True)

    # Deployment metadata
    deployment_strategy = Column(String(20), nullable=True)  # rolling, blue-green, canary
    deployment_duration = Column(Integer, nullable=True)  # seconds

    # Relationships
    service_version = relationship("ServiceVersionModel", back_populates="deployments")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("service_version_id", "environment", name="_deployment_service_env_uc"),
        Index("idx_environment_deployed_at", "environment", "deployed_at"),
        Index("idx_status", "status"),
    )


class CompatibilityCheckModel(Base):
    """Database model for storing compatibility check results."""

    __tablename__ = "compatibility_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_version_id = Column(UUID(as_uuid=True), ForeignKey("service_versions.id"), nullable=False)
    target_service_type = Column(SQLEnum(ServiceType), nullable=False)
    target_version = Column(String(50), nullable=False)
    compatibility_level = Column(SQLEnum(CompatibilityLevel), nullable=False)

    # Check details
    checked_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    checked_by = Column(String(100), default="system")
    check_details = Column(JSON, nullable=True)  # Details about the compatibility check

    # Issues found during compatibility check
    breaking_changes = Column(JSON, default=list)
    warnings = Column(JSON, default=list)

    # Relationships
    source_version = relationship("ServiceVersionModel", back_populates="compatibility_checks")

    # Indexes
    __table_args__ = (
        Index("idx_source_target", "source_version_id", "target_service_type", "target_version"),
        Index("idx_compatibility_level", "compatibility_level"),
        Index("idx_checked_at", "checked_at"),
    )


class APIContractModel(Base):
    """Database model for storing API contract snapshots."""

    __tablename__ = "api_contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_version_id = Column(UUID(as_uuid=True), ForeignKey("service_versions.id"), nullable=False)
    openapi_spec = Column(JSON, nullable=False)  # Complete OpenAPI specification
    endpoints_hash = Column(String(64), nullable=False)  # Hash of endpoints for quick comparison

    # Contract metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    generated_by = Column(String(100), default="system")

    # Indexes
    __table_args__ = (
        Index("idx_service_version", "service_version_id"),
        Index("idx_endpoints_hash", "endpoints_hash"),
    )


class VersionRegistryDB:
    """Database operations for the version registry."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    def register_version(self, service_version: ServiceVersion) -> str:
        """Register a new service version."""
        with self.get_session() as session:
            try:
                # Check if version already exists
                existing = (
                    session.query(ServiceVersionModel)
                    .filter(
                        ServiceVersionModel.service_type == service_version.service_type,
                        ServiceVersionModel.version == service_version.version,
                    )
                    .first()
                )

                if existing:
                    raise ValueError(
                        f"Version {service_version.version} already exists for {service_version.service_type.value}"
                    )

                # Create new version record
                version_model = ServiceVersionModel(
                    service_type=service_version.service_type,
                    version=service_version.version,
                    git_commit=service_version.git_commit,
                    git_branch=service_version.git_branch,
                    build_number=service_version.build_number,
                    change_type=service_version.change_type,
                    release_notes=service_version.release_notes,
                    breaking_changes=service_version.breaking_changes,
                    new_features=service_version.new_features,
                    bug_fixes=service_version.bug_fixes,
                    api_contract=service_version.api_contract.to_dict() if service_version.api_contract else None,
                    created_by=service_version.created_by,
                    feature_flags=service_version.feature_flags,
                )

                session.add(version_model)
                session.flush()  # Get the ID

                # Add dependencies
                for dependency in service_version.dependencies:
                    dep_model = VersionDependencyModel(
                        service_version_id=version_model.id,
                        dependency_service_type=dependency.service_type,
                        min_version=dependency.min_version,
                        max_version=dependency.max_version,
                        exact_version=dependency.exact_version,
                        optional=dependency.optional,
                        reason=dependency.reason,
                    )
                    session.add(dep_model)

                session.commit()
                return str(version_model.id)

            except Exception as e:
                session.rollback()
                raise e

    def get_version(self, service_type: ServiceType, version: str) -> ServiceVersion | None:
        """Get a specific service version."""
        with self.get_session() as session:
            version_model = (
                session.query(ServiceVersionModel)
                .filter(ServiceVersionModel.service_type == service_type, ServiceVersionModel.version == version)
                .first()
            )

            if version_model:
                return version_model.to_service_version()
            return None

    def get_latest_version(self, service_type: ServiceType, environment: Environment = None) -> ServiceVersion | None:
        """Get the latest version for a service, optionally filtered by environment."""
        with self.get_session() as session:
            query = session.query(ServiceVersionModel).filter(ServiceVersionModel.service_type == service_type)

            if environment:
                # Filter by versions deployed to specific environment
                query = (
                    query.join(DeploymentModel)
                    .filter(DeploymentModel.environment == environment)
                    .order_by(DeploymentModel.deployed_at.desc())
                )
            else:
                query = query.order_by(ServiceVersionModel.created_at.desc())

            version_model = query.first()
            if version_model:
                return version_model.to_service_version()
            return None

    def get_versions_by_service(self, service_type: ServiceType, limit: int = 50) -> list[ServiceVersion]:
        """Get versions for a service, ordered by creation date."""
        with self.get_session() as session:
            version_models = (
                session.query(ServiceVersionModel)
                .filter(ServiceVersionModel.service_type == service_type)
                .order_by(ServiceVersionModel.created_at.desc())
                .limit(limit)
                .all()
            )

            return [model.to_service_version() for model in version_models]

    def record_deployment(
        self,
        service_type: ServiceType,
        version: str,
        environment: Environment,
        deployed_by: str = "system",
        deployment_id: str = None,
        deployment_strategy: str = None,
    ) -> str:
        """Record a deployment."""
        with self.get_session() as session:
            try:
                # Get the service version
                version_model = (
                    session.query(ServiceVersionModel)
                    .filter(ServiceVersionModel.service_type == service_type, ServiceVersionModel.version == version)
                    .first()
                )

                if not version_model:
                    raise ValueError(f"Version {version} not found for {service_type.value}")

                # Check if deployment already exists
                existing_deployment = (
                    session.query(DeploymentModel)
                    .filter(
                        DeploymentModel.service_version_id == version_model.id,
                        DeploymentModel.environment == environment,
                    )
                    .first()
                )

                if existing_deployment:
                    # Update existing deployment
                    existing_deployment.deployed_at = datetime.now(UTC)
                    existing_deployment.deployed_by = deployed_by
                    existing_deployment.deployment_id = deployment_id
                    existing_deployment.deployment_strategy = deployment_strategy
                    existing_deployment.status = "deployed"
                    deployment_model = existing_deployment
                else:
                    # Create new deployment record
                    deployment_model = DeploymentModel(
                        service_version_id=version_model.id,
                        environment=environment,
                        deployed_by=deployed_by,
                        deployment_id=deployment_id,
                        deployment_strategy=deployment_strategy,
                    )
                    session.add(deployment_model)

                session.commit()
                return str(deployment_model.id)

            except Exception as e:
                session.rollback()
                raise e

    def check_compatibility(
        self, source_service: ServiceType, source_version: str, target_service: ServiceType, target_version: str
    ) -> CompatibilityLevel:
        """Check compatibility between two service versions."""
        with self.get_session() as session:
            # Look for existing compatibility check
            source_model = (
                session.query(ServiceVersionModel)
                .filter(
                    ServiceVersionModel.service_type == source_service, ServiceVersionModel.version == source_version
                )
                .first()
            )

            if not source_model:
                return CompatibilityLevel.UNKNOWN

            compatibility_check = (
                session.query(CompatibilityCheckModel)
                .filter(
                    CompatibilityCheckModel.source_version_id == source_model.id,
                    CompatibilityCheckModel.target_service_type == target_service,
                    CompatibilityCheckModel.target_version == target_version,
                )
                .first()
            )

            if compatibility_check:
                return compatibility_check.compatibility_level

            return CompatibilityLevel.UNKNOWN

    def record_compatibility_check(
        self,
        source_service: ServiceType,
        source_version: str,
        target_service: ServiceType,
        target_version: str,
        compatibility_level: CompatibilityLevel,
        breaking_changes: list[str] = None,
        warnings: list[str] = None,
        check_details: dict[str, Any] = None,
    ) -> str:
        """Record the results of a compatibility check."""
        with self.get_session() as session:
            try:
                # Get source version
                source_model = (
                    session.query(ServiceVersionModel)
                    .filter(
                        ServiceVersionModel.service_type == source_service,
                        ServiceVersionModel.version == source_version,
                    )
                    .first()
                )

                if not source_model:
                    raise ValueError(f"Source version {source_version} not found for {source_service.value}")

                # Check if compatibility check already exists
                existing_check = (
                    session.query(CompatibilityCheckModel)
                    .filter(
                        CompatibilityCheckModel.source_version_id == source_model.id,
                        CompatibilityCheckModel.target_service_type == target_service,
                        CompatibilityCheckModel.target_version == target_version,
                    )
                    .first()
                )

                if existing_check:
                    # Update existing check
                    existing_check.compatibility_level = compatibility_level
                    existing_check.checked_at = datetime.now(UTC)
                    existing_check.breaking_changes = breaking_changes or []
                    existing_check.warnings = warnings or []
                    existing_check.check_details = check_details or {}
                    check_model = existing_check
                else:
                    # Create new compatibility check
                    check_model = CompatibilityCheckModel(
                        source_version_id=source_model.id,
                        target_service_type=target_service,
                        target_version=target_version,
                        compatibility_level=compatibility_level,
                        breaking_changes=breaking_changes or [],
                        warnings=warnings or [],
                        check_details=check_details or {},
                    )
                    session.add(check_model)

                session.commit()
                return str(check_model.id)

            except Exception as e:
                session.rollback()
                raise e

    def get_deployment_status(self, environment: Environment) -> dict[str, Any]:
        """Get the current deployment status for an environment."""
        with self.get_session() as session:
            deployments = (
                session.query(DeploymentModel)
                .join(ServiceVersionModel)
                .filter(DeploymentModel.environment == environment)
                .all()
            )

            status = {}
            for deployment in deployments:
                service_type = deployment.service_version.service_type
                status[service_type.value] = {
                    "version": deployment.service_version.version,
                    "deployed_at": deployment.deployed_at.isoformat(),
                    "deployed_by": deployment.deployed_by,
                    "status": deployment.status,
                    "health_check_passed": deployment.health_check_passed,
                }

            return status

    def cleanup_old_versions(self, service_type: ServiceType, keep_count: int = 50):
        """Remove old versions, keeping only the most recent ones."""
        with self.get_session() as session:
            try:
                # Get versions to keep
                versions_to_keep = (
                    session.query(ServiceVersionModel.id)
                    .filter(ServiceVersionModel.service_type == service_type)
                    .order_by(ServiceVersionModel.created_at.desc())
                    .limit(keep_count)
                    .subquery()
                )

                # Delete old versions
                deleted_count = (
                    session.query(ServiceVersionModel)
                    .filter(
                        ServiceVersionModel.service_type == service_type, ~ServiceVersionModel.id.in_(versions_to_keep)
                    )
                    .delete()
                )

                session.commit()
                return deleted_count

            except Exception as e:
                session.rollback()
                raise e


# Database migration utilities
def init_database(database_url: str) -> VersionRegistryDB:
    """Initialize the version registry database."""
    registry_db = VersionRegistryDB(database_url)
    registry_db.create_tables()
    return registry_db


# Example usage
if __name__ == "__main__":
    # Initialize database (use environment variable in production)
    db_url = os.getenv("VERSION_REGISTRY_DB_URL", "sqlite:///version_registry.db")
    registry_db = init_database(db_url)

    # Example: Register a new backend version
    from ..core.version_schema import ChangeType, ServiceType, ServiceVersion

    backend_version = ServiceVersion(
        service_type=ServiceType.BACKEND,
        version="1.3.0",
        git_commit="abc123def456",
        git_branch="main",
        change_type=ChangeType.MINOR,
        release_notes="Added new chat features",
        created_by="developer@praktiko.ai",
    )

    version_id = registry_db.register_version(backend_version)
    print(f"Registered version with ID: {version_id}")

    # Record deployment
    deployment_id = registry_db.record_deployment(
        ServiceType.BACKEND, "1.3.0", Environment.DEVELOPMENT, deployed_by="ci-system"
    )
    print(f"Recorded deployment with ID: {deployment_id}")

    # Check deployment status
    status = registry_db.get_deployment_status(Environment.DEVELOPMENT)
    print(f"Deployment status: {json.dumps(status, indent=2, default=str)}")
