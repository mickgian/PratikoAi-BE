#!/usr/bin/env python3
"""PratikoAI Feature Flag Service

FastAPI-based service for managing feature flags across KMP frontend and Python backend.
Provides real-time flag evaluation, user targeting, environment management, and admin APIs.
"""

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import httpx
import redis.asyncio as redis
import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field, validator
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost/pratiko_flags")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Redis setup
redis_client = None

# FastAPI app
app = FastAPI(
    title="PratikoAI Feature Flag Service",
    description="Cross-platform feature flag management for KMP and FastAPI",
    version="1.0.0",
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


class FlagType(str, Enum):
    """Feature flag value types."""

    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"


class TargetingOperator(str, Enum):
    """Operators for targeting conditions."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    REGEX_MATCH = "regex_match"


# Database Models
class FeatureFlag(Base):
    """Feature flag database model."""

    __tablename__ = "feature_flags"

    flag_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    flag_type = Column(String, nullable=False)
    default_value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String)
    is_active = Column(Boolean, default=True)
    tags = Column(JSON, default=list)


class FlagEnvironment(Base):
    """Environment-specific flag configurations."""

    __tablename__ = "flag_environments"

    flag_id = Column(String, primary_key=True)
    environment = Column(String, primary_key=True)
    value = Column(Text)
    enabled = Column(Boolean, default=True)
    targeting_rules = Column(JSON, default=list)
    rollout_percentage = Column(Float, default=100.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String)


class FlagAuditLog(Base):
    """Audit log for flag changes."""

    __tablename__ = "flag_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flag_id = Column(String, nullable=False)
    environment = Column(String)
    action = Column(String, nullable=False)  # create, update, delete, toggle
    old_value = Column(Text)
    new_value = Column(Text)
    changed_by = Column(String, nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default=dict)


class FlagEvaluation(Base):
    """Flag evaluation metrics."""

    __tablename__ = "flag_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flag_id = Column(String, nullable=False)
    environment = Column(String, nullable=False)
    user_id = Column(String)
    evaluated_value = Column(Text)
    evaluation_context = Column(JSON)
    evaluated_at = Column(DateTime, default=datetime.utcnow)
    client_sdk = Column(String)
    response_time_ms = Column(Float)


# Pydantic Models
class TargetingCondition(BaseModel):
    """Targeting condition model."""

    attribute: str
    operator: TargetingOperator
    value: str | int | float | list[str] | bool


class TargetingRule(BaseModel):
    """Targeting rule model."""

    name: str
    description: str | None = None
    conditions: list[TargetingCondition]
    value: str | int | float | bool | dict
    percentage: float = 100.0
    enabled: bool = True


class FlagRequest(BaseModel):
    """Request model for creating/updating flags."""

    flag_id: str = Field(..., regex=r"^[a-z][a-z0-9_]*[a-z0-9]$")
    name: str
    description: str | None = None
    flag_type: FlagType
    default_value: str | int | float | bool | dict
    tags: list[str] = []

    @validator("flag_id")
    def validate_flag_id(self, v):
        if len(v) < 3 or len(v) > 100:
            raise ValueError("Flag ID must be between 3 and 100 characters")
        return v


class EnvironmentFlagRequest(BaseModel):
    """Request model for environment-specific flag configuration."""

    flag_id: str
    environment: str
    value: str | int | float | bool | dict
    enabled: bool = True
    targeting_rules: list[TargetingRule] = []
    rollout_percentage: float = Field(default=100.0, ge=0, le=100)


class EvaluationContext(BaseModel):
    """Context for flag evaluation."""

    user_id: str | None = None
    user_attributes: dict[str, str | int | float | bool] = {}
    environment: str = "production"
    client_sdk: str | None = None


class FlagEvaluationResponse(BaseModel):
    """Response model for flag evaluation."""

    flag_id: str
    value: str | int | float | bool | dict
    enabled: bool
    reason: str
    targeting_rule_matched: str | None = None
    evaluated_at: datetime


class BulkEvaluationRequest(BaseModel):
    """Request model for bulk flag evaluation."""

    flag_ids: list[str]
    context: EvaluationContext


class FlagListResponse(BaseModel):
    """Response model for flag listing."""

    flags: list[dict]
    total: int
    page: int
    per_page: int


# Utility Classes
class FlagEvaluator:
    """Service for evaluating feature flags with targeting rules."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def evaluate_flag(
        self, flag_id: str, context: EvaluationContext, db: AsyncSession
    ) -> FlagEvaluationResponse:
        """Evaluate a feature flag for given context."""
        # Try cache first
        cache_key = f"flag:{flag_id}:{context.environment}"
        cached_config = await self.redis.get(cache_key)

        if cached_config:
            flag_config = json.loads(cached_config)
        else:
            # Load from database
            flag_config = await self._load_flag_config(flag_id, context.environment, db)
            if not flag_config:
                raise HTTPException(status_code=404, detail=f"Flag {flag_id} not found")

            # Cache for 5 minutes
            await self.redis.setex(cache_key, 300, json.dumps(flag_config))

        # Evaluate targeting rules
        evaluation_result = await self._evaluate_targeting_rules(flag_config, context)

        # Log evaluation for metrics
        await self._log_evaluation(flag_id, context, evaluation_result, db)

        return FlagEvaluationResponse(
            flag_id=flag_id,
            value=evaluation_result["value"],
            enabled=evaluation_result["enabled"],
            reason=evaluation_result["reason"],
            targeting_rule_matched=evaluation_result.get("rule_matched"),
            evaluated_at=datetime.now(UTC),
        )

    async def _load_flag_config(self, flag_id: str, environment: str, db: AsyncSession) -> dict | None:
        """Load flag configuration from database."""
        # This is a simplified version - in practice, you'd use proper SQLAlchemy queries
        # For now, returning a mock configuration
        return {
            "flag_id": flag_id,
            "flag_type": "boolean",
            "default_value": False,
            "environment_config": {"enabled": True, "value": True, "targeting_rules": [], "rollout_percentage": 100.0},
        }

    async def _evaluate_targeting_rules(self, flag_config: dict, context: EvaluationContext) -> dict:
        """Evaluate targeting rules against user context."""
        env_config = flag_config.get("environment_config", {})

        if not env_config.get("enabled", True):
            return {"value": flag_config["default_value"], "enabled": False, "reason": "flag_disabled"}

        # Check targeting rules
        targeting_rules = env_config.get("targeting_rules", [])
        for rule in targeting_rules:
            if await self._matches_targeting_rule(rule, context):
                return {
                    "value": rule["value"],
                    "enabled": True,
                    "reason": "targeting_rule_matched",
                    "rule_matched": rule["name"],
                }

        # Check rollout percentage
        rollout_percentage = env_config.get("rollout_percentage", 100.0)
        if rollout_percentage < 100.0:
            user_hash = self._get_user_hash(context.user_id or "anonymous", flag_config["flag_id"])
            if user_hash > rollout_percentage:
                return {
                    "value": flag_config["default_value"],
                    "enabled": True,
                    "reason": "rollout_percentage_excluded",
                }

        # Return environment value
        return {
            "value": env_config.get("value", flag_config["default_value"]),
            "enabled": True,
            "reason": "default_environment_value",
        }

    async def _matches_targeting_rule(self, rule: dict, context: EvaluationContext) -> bool:
        """Check if user context matches targeting rule conditions."""
        if not rule.get("enabled", True):
            return False

        conditions = rule.get("conditions", [])
        for condition in conditions:
            if not await self._evaluate_condition(condition, context):
                return False

        # Check percentage rollout for this rule
        percentage = rule.get("percentage", 100.0)
        if percentage < 100.0:
            user_hash = self._get_user_hash(context.user_id or "anonymous", rule["name"])
            if user_hash > percentage:
                return False

        return True

    async def _evaluate_condition(self, condition: dict, context: EvaluationContext) -> bool:
        """Evaluate a single targeting condition."""
        attribute_name = condition["attribute"]
        operator = condition["operator"]
        expected_value = condition["value"]

        # Get actual value from context
        if attribute_name == "user_id":
            actual_value = context.user_id
        else:
            actual_value = context.user_attributes.get(attribute_name)

        if actual_value is None:
            return False

        # Apply operator
        if operator == "equals":
            return actual_value == expected_value
        elif operator == "not_equals":
            return actual_value != expected_value
        elif operator == "in":
            return actual_value in expected_value
        elif operator == "not_in":
            return actual_value not in expected_value
        elif operator == "contains":
            return expected_value in str(actual_value)
        elif operator == "starts_with":
            return str(actual_value).startswith(str(expected_value))
        elif operator == "ends_with":
            return str(actual_value).endswith(str(expected_value))
        elif operator == "greater_than":
            try:
                return float(actual_value) > float(expected_value)
            except (ValueError, TypeError):
                return False
        elif operator == "less_than":
            try:
                return float(actual_value) < float(expected_value)
            except (ValueError, TypeError):
                return False
        elif operator == "regex_match":
            import re

            try:
                return bool(re.match(expected_value, str(actual_value)))
            except re.error:
                return False

        return False

    def _get_user_hash(self, user_id: str, salt: str) -> float:
        """Generate consistent hash for user targeting (0-100)."""
        hash_input = f"{user_id}:{salt}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        # Convert first 8 hex chars to int, then to percentage
        return (int(hash_value[:8], 16) % 10000) / 100.0

    async def _log_evaluation(self, flag_id: str, context: EvaluationContext, result: dict, db: AsyncSession):
        """Log flag evaluation for metrics."""
        # In a real implementation, you'd insert into the database
        # For now, just log to console
        logger.info(f"Flag evaluation: {flag_id} = {result['value']} for user {context.user_id}")


# Cache Manager
class CacheManager:
    """Manages caching for feature flags."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def invalidate_flag_cache(self, flag_id: str, environment: str = None):
        """Invalidate cache for a specific flag."""
        if environment:
            cache_key = f"flag:{flag_id}:{environment}"
            await self.redis.delete(cache_key)
        else:
            # Invalidate all environments for this flag
            pattern = f"flag:{flag_id}:*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)

    async def warm_cache(self, db: AsyncSession):
        """Pre-warm cache with active flags."""
        # Implementation would load all active flags and cache them
        logger.info("Cache warming completed")


# Authentication
async def get_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate API key authentication."""
    expected_api_key = os.getenv("API_KEY", "pratiko-dev-key-123")
    if credentials.credentials != expected_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials


# Database dependency
async def get_db():
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Initialize services
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global redis_client
    redis_client = redis.from_url(REDIS_URL)

    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

    # Initialize cache
    CacheManager(redis_client)
    # await cache_manager.warm_cache(db)  # Would need db session

    logger.info("Feature Flag Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if redis_client:
        await redis_client.close()
    logger.info("Feature Flag Service stopped")


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "PratikoAI Feature Flag Service",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check Redis
        await redis_client.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    return {
        "status": "healthy" if redis_status == "healthy" else "degraded",
        "redis": redis_status,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post("/api/v1/flags", dependencies=[Depends(get_api_key)])
async def create_flag(flag: FlagRequest, db: AsyncSession = Depends(get_db)):
    """Create a new feature flag."""
    # Check if flag already exists
    # existing_flag = await db.get(FeatureFlag, flag.flag_id)
    # if existing_flag:
    #     raise HTTPException(status_code=409, detail="Flag already exists")

    # Create new flag
    FeatureFlag(
        flag_id=flag.flag_id,
        name=flag.name,
        description=flag.description,
        flag_type=flag.flag_type.value,
        default_value=json.dumps(flag.default_value),
        created_by="api",  # Would get from auth context
        tags=flag.tags,
    )

    # db.add(new_flag)
    # await db.commit()

    # Log audit event
    FlagAuditLog(flag_id=flag.flag_id, action="create", new_value=json.dumps(asdict(flag)), changed_by="api")
    # db.add(audit_log)
    # await db.commit()

    return {"message": "Flag created successfully", "flag_id": flag.flag_id}


@app.get("/api/v1/flags")
async def list_flags(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    environment: str | None = Query(None),
    tags: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List feature flags with filtering and pagination."""
    # Mock response for now
    flags = [
        {
            "flag_id": "new_dashboard_ui",
            "name": "New Dashboard UI",
            "description": "Enable the redesigned dashboard interface",
            "flag_type": "boolean",
            "default_value": False,
            "created_at": "2024-01-15T10:00:00Z",
            "is_active": True,
            "tags": ["ui", "dashboard"],
        },
        {
            "flag_id": "api_rate_limit_strict",
            "name": "Strict API Rate Limiting",
            "description": "Enable stricter rate limiting for API endpoints",
            "flag_type": "boolean",
            "default_value": False,
            "created_at": "2024-01-15T11:00:00Z",
            "is_active": True,
            "tags": ["api", "security"],
        },
    ]

    return FlagListResponse(flags=flags, total=len(flags), page=page, per_page=per_page)


@app.get("/api/v1/flags/{flag_id}")
async def get_flag(flag_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific feature flag."""
    # Mock response
    return {
        "flag_id": flag_id,
        "name": "Example Flag",
        "description": "This is an example flag",
        "flag_type": "boolean",
        "default_value": False,
        "environments": {
            "development": {"enabled": True, "value": True},
            "staging": {"enabled": True, "value": False},
            "production": {"enabled": False, "value": False},
        },
    }


@app.put("/api/v1/flags/{flag_id}/environments/{environment}", dependencies=[Depends(get_api_key)])
async def update_flag_environment(
    flag_id: str, environment: str, config: EnvironmentFlagRequest, db: AsyncSession = Depends(get_db)
):
    """Update flag configuration for a specific environment."""
    # Validate flag exists
    # flag = await db.get(FeatureFlag, flag_id)
    # if not flag:
    #     raise HTTPException(status_code=404, detail="Flag not found")

    # Update environment configuration
    # Implementation would update FlagEnvironment table

    # Invalidate cache
    cache_manager = CacheManager(redis_client)
    await cache_manager.invalidate_flag_cache(flag_id, environment)

    return {"message": f"Flag {flag_id} updated for environment {environment}"}


@app.post("/api/v1/evaluate")
async def evaluate_flag(context: EvaluationContext, flag_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Evaluate a single feature flag."""
    evaluator = FlagEvaluator(redis_client)
    result = await evaluator.evaluate_flag(flag_id, context, db)
    return result


@app.post("/api/v1/evaluate/bulk")
async def evaluate_flags_bulk(request: BulkEvaluationRequest, db: AsyncSession = Depends(get_db)):
    """Evaluate multiple feature flags in a single request."""
    evaluator = FlagEvaluator(redis_client)
    results = {}

    for flag_id in request.flag_ids:
        try:
            result = await evaluator.evaluate_flag(flag_id, request.context, db)
            results[flag_id] = result.dict()
        except HTTPException as e:
            results[flag_id] = {"error": e.detail, "value": None}

    return {"evaluations": results, "context": request.context.dict()}


@app.post("/api/v1/flags/{flag_id}/toggle/{environment}", dependencies=[Depends(get_api_key)])
async def toggle_flag(flag_id: str, environment: str, enabled: bool = Query(...), db: AsyncSession = Depends(get_db)):
    """Quickly toggle a flag on/off for an environment."""
    # Update flag enabled status
    # Implementation would update FlagEnvironment table

    # Invalidate cache
    cache_manager = CacheManager(redis_client)
    await cache_manager.invalidate_flag_cache(flag_id, environment)

    # Log audit event
    FlagAuditLog(flag_id=flag_id, environment=environment, action="toggle", new_value=str(enabled), changed_by="api")

    return {"message": f"Flag {flag_id} {'enabled' if enabled else 'disabled'} for {environment}"}


@app.get("/api/v1/flags/{flag_id}/audit")
async def get_flag_audit_log(flag_id: str, limit: int = Query(50, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    """Get audit log for a specific flag."""
    # Mock audit log
    audit_entries = [
        {
            "id": 1,
            "action": "create",
            "changed_by": "developer@pratiko.ai",
            "changed_at": "2024-01-15T10:00:00Z",
            "old_value": None,
            "new_value": "{'enabled': True, 'value': False}",
        },
        {
            "id": 2,
            "action": "toggle",
            "environment": "staging",
            "changed_by": "admin@pratiko.ai",
            "changed_at": "2024-01-15T12:00:00Z",
            "old_value": "False",
            "new_value": "True",
        },
    ]

    return {"audit_log": audit_entries, "flag_id": flag_id}


@app.get("/api/v1/metrics/evaluations")
async def get_evaluation_metrics(
    flag_id: str | None = Query(None),
    environment: str | None = Query(None),
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Get flag evaluation metrics."""
    # Mock metrics
    return {
        "total_evaluations": 15420,
        "unique_users": 3250,
        "average_response_time_ms": 2.3,
        "value_distribution": {"true": 8500, "false": 6920},
        "environment_breakdown": {"production": 12000, "staging": 2420, "development": 1000},
    }


@app.delete("/api/v1/flags/{flag_id}", dependencies=[Depends(get_api_key)])
async def delete_flag(flag_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a feature flag (soft delete)."""
    # Set is_active = False instead of actually deleting
    # flag = await db.get(FeatureFlag, flag_id)
    # if not flag:
    #     raise HTTPException(status_code=404, detail="Flag not found")

    # flag.is_active = False
    # await db.commit()

    # Invalidate cache
    cache_manager = CacheManager(redis_client)
    await cache_manager.invalidate_flag_cache(flag_id)

    return {"message": f"Flag {flag_id} deleted successfully"}


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    """Serve admin dashboard."""
    # Simple HTML dashboard for flag management
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PratikoAI Feature Flags Admin</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .flag-card { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .enabled { border-left: 5px solid #4CAF50; }
            .disabled { border-left: 5px solid #f44336; }
            button { padding: 8px 16px; margin: 5px; border: none; border-radius: 3px; cursor: pointer; }
            .btn-primary { background-color: #007bff; color: white; }
            .btn-danger { background-color: #dc3545; color: white; }
        </style>
    </head>
    <body>
        <h1>🚀 PratikoAI Feature Flags</h1>
        <div id="flags-container">
            <div class="flag-card enabled">
                <h3>new_dashboard_ui</h3>
                <p>Enable the redesigned dashboard interface</p>
                <p><strong>Type:</strong> boolean | <strong>Default:</strong> false</p>
                <button class="btn-primary" onclick="toggleFlag('new_dashboard_ui', 'production')">Toggle Production</button>
                <button class="btn-danger" onclick="emergencyDisable('new_dashboard_ui')">Emergency Disable</button>
            </div>
            <div class="flag-card disabled">
                <h3>api_rate_limit_strict</h3>
                <p>Enable stricter rate limiting for API endpoints</p>
                <p><strong>Type:</strong> boolean | <strong>Default:</strong> false</p>
                <button class="btn-primary" onclick="toggleFlag('api_rate_limit_strict', 'production')">Toggle Production</button>
                <button class="btn-danger" onclick="emergencyDisable('api_rate_limit_strict')">Emergency Disable</button>
            </div>
        </div>

        <script>
            function toggleFlag(flagId, environment) {
                // In a real implementation, this would make API calls
                alert(`Toggling ${flagId} in ${environment}`);
            }

            function emergencyDisable(flagId) {
                if (confirm(`Emergency disable ${flagId} in all environments?`)) {
                    alert(`Emergency disabled ${flagId}`);
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content


# WebSocket endpoint for real-time updates
@app.websocket("/ws/flags")
async def websocket_flag_updates(websocket):
    """WebSocket endpoint for real-time flag updates."""
    await websocket.accept()
    try:
        while True:
            # In a real implementation, this would listen for flag changes
            # and push updates to connected clients
            await asyncio.sleep(30)
            await websocket.send_json({"type": "heartbeat", "timestamp": datetime.now(UTC).isoformat()})
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    uvicorn.run("feature_flag_service:app", host="0.0.0.0", port=8001, reload=True, log_level="info")
