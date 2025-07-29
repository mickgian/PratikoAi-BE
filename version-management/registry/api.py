#!/usr/bin/env python3
"""
PratikoAI Version Registry API
FastAPI-based REST API for managing service versions, deployments, and compatibility checks.

This API provides:
- Version registration and retrieval
- Compatibility checking between services
- Deployment tracking and status
- API contract validation
- Health monitoring for version consistency
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncio
import logging

from ..core.version_schema import (
    ServiceVersion, ServiceType, ChangeType, Environment, 
    CompatibilityLevel, APIContract, VersionDependency, CompatibilityRules
)
from .database import VersionRegistryDB, init_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app setup
app = FastAPI(
    title="PratikoAI Version Registry",
    description="Comprehensive version management and compatibility tracking for PratikoAI services",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Database connection
DB_URL = os.getenv('VERSION_REGISTRY_DB_URL', 'postgresql://user:pass@localhost/version_registry')
registry_db = init_database(DB_URL)


# Pydantic models for API requests/responses
class VersionRegistrationRequest(BaseModel):
    service_type: ServiceType
    version: str
    git_commit: str
    git_branch: str
    build_number: Optional[int] = None
    change_type: ChangeType = ChangeType.PATCH
    release_notes: str = ""
    breaking_changes: List[str] = Field(default_factory=list)
    new_features: List[str] = Field(default_factory=list)
    bug_fixes: List[str] = Field(default_factory=list)
    dependencies: List[Dict[str, Any]] = Field(default_factory=list)
    api_contract: Optional[Dict[str, Any]] = None
    feature_flags: Dict[str, bool] = Field(default_factory=dict)
    created_by: str = "system"


class VersionResponse(BaseModel):
    id: str
    service_type: ServiceType
    version: str
    git_commit: str
    git_branch: str
    build_number: Optional[int]
    change_type: ChangeType
    release_notes: str
    breaking_changes: List[str]
    new_features: List[str]
    bug_fixes: List[str]
    created_at: datetime
    created_by: str
    deployments: Dict[str, datetime]
    compatibility_matrix: Dict[str, str]
    feature_flags: Dict[str, bool]


class DeploymentRequest(BaseModel):
    service_type: ServiceType
    version: str
    environment: Environment
    deployed_by: str = "system"
    deployment_id: Optional[str] = None
    deployment_strategy: Optional[str] = None
    health_check_passed: bool = True


class CompatibilityCheckRequest(BaseModel):
    source_service: ServiceType
    source_version: str
    target_service: ServiceType
    target_version: str


class CompatibilityCheckResponse(BaseModel):
    compatibility_level: CompatibilityLevel
    breaking_changes: List[str]
    warnings: List[str]
    details: Dict[str, Any]
    checked_at: datetime


class DeploymentStatusResponse(BaseModel):
    environment: Environment
    services: Dict[str, Dict[str, Any]]
    last_updated: datetime


# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Simple token-based authentication."""
    token = credentials.credentials
    expected_token = os.getenv('VERSION_REGISTRY_TOKEN', 'dev-token')
    
    if token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    return {"username": "api-user"}


# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        with registry_db.get_session() as session:
            session.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.post("/api/v1/versions/register", response_model=Dict[str, str])
async def register_version(
    request: VersionRegistrationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Register a new service version."""
    try:
        # Convert request to ServiceVersion object
        dependencies = []
        for dep_data in request.dependencies:
            dependencies.append(VersionDependency(**dep_data))
        
        api_contract = None
        if request.api_contract:
            api_contract = APIContract(**request.api_contract)
        
        service_version = ServiceVersion(
            service_type=request.service_type,
            version=request.version,
            git_commit=request.git_commit,
            git_branch=request.git_branch,
            build_number=request.build_number,
            change_type=request.change_type,
            release_notes=request.release_notes,
            breaking_changes=request.breaking_changes,
            new_features=request.new_features,
            bug_fixes=request.bug_fixes,
            dependencies=dependencies,
            api_contract=api_contract,
            feature_flags=request.feature_flags,
            created_by=request.created_by
        )
        
        # Register version
        version_id = registry_db.register_version(service_version)
        
        # Schedule background compatibility checks
        background_tasks.add_task(
            schedule_compatibility_checks,
            request.service_type,
            request.version
        )
        
        logger.info(f"Registered version {request.version} for {request.service_type.value}")
        
        return {
            "version_id": version_id,
            "message": f"Version {request.version} registered successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to register version: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/versions/{service_type}/{version}", response_model=VersionResponse)
async def get_version(
    service_type: ServiceType,
    version: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific service version."""
    try:
        service_version = registry_db.get_version(service_type, version)
        
        if not service_version:
            raise HTTPException(
                status_code=404, 
                detail=f"Version {version} not found for {service_type.value}"
            )
        
        # Convert to response model
        deployments_dict = {
            env.value if hasattr(env, 'value') else str(env): dt
            for env, dt in service_version.deployments.items()
        }
        
        compatibility_dict = {
            key: level.value if hasattr(level, 'value') else str(level)
            for key, level in service_version.compatibility_matrix.items()
        }
        
        return VersionResponse(
            id="generated-id",  # Would be actual ID from database
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
            created_at=service_version.created_at,
            created_by=service_version.created_by,
            deployments=deployments_dict,
            compatibility_matrix=compatibility_dict,
            feature_flags=service_version.feature_flags
        )
        
    except Exception as e:
        logger.error(f"Failed to get version: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/versions/{service_type}/latest")
async def get_latest_version(
    service_type: ServiceType,
    environment: Optional[Environment] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get the latest version for a service."""
    try:
        service_version = registry_db.get_latest_version(service_type, environment)
        
        if not service_version:
            raise HTTPException(
                status_code=404,
                detail=f"No versions found for {service_type.value}"
            )
        
        return {
            "service_type": service_version.service_type.value,
            "version": service_version.version,
            "git_commit": service_version.git_commit,
            "created_at": service_version.created_at.isoformat(),
            "change_type": service_version.change_type.value
        }
        
    except Exception as e:
        logger.error(f"Failed to get latest version: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/versions/{service_type}")
async def list_versions(
    service_type: ServiceType,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """List versions for a service."""
    try:
        versions = registry_db.get_versions_by_service(service_type, limit)
        
        return {
            "service_type": service_type.value,
            "versions": [
                {
                    "version": v.version,
                    "git_commit": v.git_commit,
                    "change_type": v.change_type.value,
                    "created_at": v.created_at.isoformat(),
                    "breaking_changes": len(v.breaking_changes) > 0,
                    "deployments": list(v.deployments.keys())
                }
                for v in versions
            ],
            "total": len(versions)
        }
        
    except Exception as e:
        logger.error(f"Failed to list versions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/deployments", response_model=Dict[str, str])
async def record_deployment(
    request: DeploymentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Record a deployment."""
    try:
        deployment_id = registry_db.record_deployment(
            service_type=request.service_type,
            version=request.version,
            environment=request.environment,
            deployed_by=request.deployed_by,
            deployment_id=request.deployment_id,
            deployment_strategy=request.deployment_strategy
        )
        
        logger.info(f"Recorded deployment of {request.service_type.value} {request.version} to {request.environment.value}")
        
        return {
            "deployment_id": deployment_id,
            "message": f"Deployment recorded successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to record deployment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/deployments/{environment}", response_model=DeploymentStatusResponse)
async def get_deployment_status(
    environment: Environment,
    current_user: dict = Depends(get_current_user)
):
    """Get deployment status for an environment."""
    try:
        status = registry_db.get_deployment_status(environment)
        
        return DeploymentStatusResponse(
            environment=environment,
            services=status,
            last_updated=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"Failed to get deployment status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/compatibility/check", response_model=CompatibilityCheckResponse)
async def check_compatibility(
    request: CompatibilityCheckRequest,
    current_user: dict = Depends(get_current_user)
):
    """Check compatibility between two service versions."""
    try:
        # Get existing compatibility check
        existing_level = registry_db.check_compatibility(
            request.source_service, request.source_version,
            request.target_service, request.target_version
        )
        
        if existing_level != CompatibilityLevel.UNKNOWN:
            return CompatibilityCheckResponse(
                compatibility_level=existing_level,
                breaking_changes=[],
                warnings=[],
                details={"cached": True},
                checked_at=datetime.now(timezone.utc)
            )
        
        # Perform new compatibility check
        compatibility_level = CompatibilityRules.check_compatibility(
            request.source_service, request.source_version,
            request.target_service, request.target_version
        )
        
        # Record the result
        registry_db.record_compatibility_check(
            source_service=request.source_service,
            source_version=request.source_version,
            target_service=request.target_service,
            target_version=request.target_version,
            compatibility_level=compatibility_level
        )
        
        return CompatibilityCheckResponse(
            compatibility_level=compatibility_level,
            breaking_changes=[],
            warnings=[],
            details={"computed": True},
            checked_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"Failed to check compatibility: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/compatibility/{service_type}/{version}")
async def get_compatibility_matrix(
    service_type: ServiceType,
    version: str,
    current_user: dict = Depends(get_current_user)
):
    """Get compatibility matrix for a service version."""
    try:
        service_version = registry_db.get_version(service_type, version)
        
        if not service_version:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version} not found for {service_type.value}"
            )
        
        return {
            "service_type": service_type.value,
            "version": version,
            "compatibility_matrix": {
                key: level.value if hasattr(level, 'value') else str(level)
                for key, level in service_version.compatibility_matrix.items()
            },
            "dependencies": [
                {
                    "service_type": dep.service_type.value,
                    "min_version": dep.min_version,
                    "max_version": dep.max_version,
                    "exact_version": dep.exact_version,
                    "optional": dep.optional,
                    "reason": dep.reason
                }
                for dep in service_version.dependencies
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get compatibility matrix: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/validate-deployment")
async def validate_deployment(
    service_type: ServiceType,
    version: str,
    environment: Environment,
    current_user: dict = Depends(get_current_user)
):
    """Validate if a version can be safely deployed to an environment."""
    try:
        # Get the version to be deployed
        service_version = registry_db.get_version(service_type, version)
        if not service_version:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version} not found for {service_type.value}"
            )
        
        # Get current deployment status
        current_deployments = registry_db.get_deployment_status(environment)
        
        validation_results = {
            "can_deploy": True,
            "blocking_issues": [],
            "warnings": [],
            "dependency_checks": []
        }
        
        # Check dependencies
        for dependency in service_version.dependencies:
            current_version = current_deployments.get(dependency.service_type.value, {}).get('version')
            
            if current_version:
                if not service_version.satisfies_dependency(dependency, current_version):
                    validation_results["blocking_issues"].append(
                        f"Dependency {dependency.service_type.value} version {current_version} "
                        f"does not satisfy requirement {dependency.min_version}"
                    )
                    validation_results["can_deploy"] = False
                else:
                    validation_results["dependency_checks"].append(
                        f"✓ {dependency.service_type.value} {current_version} satisfies requirement"
                    )
            elif not dependency.optional:
                validation_results["blocking_issues"].append(
                    f"Required dependency {dependency.service_type.value} is not deployed"
                )
                validation_results["can_deploy"] = False
        
        # Check for breaking changes in production
        if environment == Environment.PRODUCTION and service_version.breaking_changes:
            validation_results["warnings"].append(
                f"Version contains {len(service_version.breaking_changes)} breaking changes"
            )
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Failed to validate deployment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/api/v1/versions/{service_type}/cleanup")
async def cleanup_old_versions(
    service_type: ServiceType,
    keep_count: int = Query(50, ge=10, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Clean up old versions, keeping only the most recent ones."""
    try:
        deleted_count = registry_db.cleanup_old_versions(service_type, keep_count)
        
        return {
            "message": f"Cleaned up {deleted_count} old versions",
            "service_type": service_type.value,
            "versions_kept": keep_count
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup versions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Background tasks
async def schedule_compatibility_checks(service_type: ServiceType, version: str):
    """Schedule compatibility checks for a new version."""
    try:
        # Get all services that might need compatibility checking
        all_service_types = list(ServiceType)
        
        for target_service in all_service_types:
            if target_service == service_type:
                continue
            
            # Get latest version of target service
            latest_version = registry_db.get_latest_version(target_service)
            if latest_version:
                # Perform compatibility check
                compatibility_level = CompatibilityRules.check_compatibility(
                    service_type, version,
                    target_service, latest_version.version
                )
                
                # Record the result
                registry_db.record_compatibility_check(
                    source_service=service_type,
                    source_version=version,
                    target_service=target_service,
                    target_version=latest_version.version,
                    compatibility_level=compatibility_level
                )
        
        logger.info(f"Completed compatibility checks for {service_type.value} {version}")
        
    except Exception as e:
        logger.error(f"Failed to schedule compatibility checks: {e}")


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Version Registry API starting up...")
    
    # Test database connection
    try:
        with registry_db.get_session() as session:
            session.execute("SELECT 1")
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise e


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Version Registry API shutting down...")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv('PORT', 8001))
    host = os.getenv('HOST', '0.0.0.0')
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )