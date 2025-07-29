#!/usr/bin/env python3
"""
PratikoAI Feature Flag Admin Web Interface

Advanced web-based admin interface for managing feature flags with real-time updates,
gradual rollout controls, user targeting, and emergency flag toggling.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Depends, Request, Form, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel
import httpx
from jinja2 import Environment, FileSystemLoader
import websockets
from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Configuration
FEATURE_FLAG_API_URL = os.getenv("FEATURE_FLAG_API_URL", "http://localhost:8001")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-key-123")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# FastAPI app
app = FastAPI(
    title="PratikoAI Feature Flag Admin",
    description="Advanced admin interface for feature flag management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Security
security = HTTPBearer()

# HTTP client for API calls
http_client = httpx.AsyncClient(
    timeout=30,
    headers={
        "Authorization": f"Bearer {ADMIN_API_KEY}",
        "Content-Type": "application/json"
    }
)

# WebSocket connections for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove broken connections
                self.active_connections.remove(connection)

manager = ConnectionManager()


# Pydantic models
class FlagToggleRequest(BaseModel):
    flag_id: str
    environment: str
    enabled: bool


class RolloutUpdateRequest(BaseModel):
    flag_id: str
    environment: str
    percentage: float


class TargetingRuleRequest(BaseModel):
    name: str
    description: Optional[str]
    conditions: List[Dict[str, Any]]
    value: Any
    percentage: float = 100.0
    enabled: bool = True


# Authentication dependency
async def verify_admin_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


# API client functions
async def get_all_flags(environment: str = None):
    """Get all feature flags."""
    params = {"environment": environment} if environment else {}
    response = await http_client.get(f"{FEATURE_FLAG_API_URL}/api/v1/flags", params=params)
    response.raise_for_status()
    return response.json()


async def get_flag_details(flag_id: str):
    """Get detailed flag information."""
    response = await http_client.get(f"{FEATURE_FLAG_API_URL}/api/v1/flags/{flag_id}")
    response.raise_for_status()
    return response.json()


async def toggle_flag(flag_id: str, environment: str, enabled: bool):
    """Toggle a flag on/off."""
    params = {"enabled": enabled}
    response = await http_client.post(
        f"{FEATURE_FLAG_API_URL}/api/v1/flags/{flag_id}/toggle/{environment}",
        params=params
    )
    response.raise_for_status()
    return response.json()


async def update_flag_environment(flag_id: str, environment: str, config: dict):
    """Update flag configuration for environment."""
    response = await http_client.put(
        f"{FEATURE_FLAG_API_URL}/api/v1/flags/{flag_id}/environments/{environment}",
        json=config
    )
    response.raise_for_status()
    return response.json()


async def get_flag_metrics(flag_id: str = None, environment: str = None, hours: int = 24):
    """Get flag evaluation metrics."""
    params = {}
    if flag_id:
        params["flag_id"] = flag_id
    if environment:
        params["environment"] = environment
    params["hours"] = hours
    
    response = await http_client.get(f"{FEATURE_FLAG_API_URL}/api/v1/metrics/evaluations", params=params)
    response.raise_for_status()
    return response.json()


async def get_audit_log(flag_id: str, limit: int = 50):
    """Get audit log for a flag."""
    params = {"limit": limit}
    response = await http_client.get(f"{FEATURE_FLAG_API_URL}/api/v1/flags/{flag_id}/audit", params=params)
    response.raise_for_status()
    return response.json()


# Web routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard."""
    try:
        flags_data = await get_all_flags()
        metrics_data = await get_flag_metrics()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "flags": flags_data.get("flags", []),
            "metrics": metrics_data,
            "total_flags": len(flags_data.get("flags", [])),
            "active_flags": len([f for f in flags_data.get("flags", []) if f.get("is_active", True)])
        })
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load dashboard data"
        })


@app.get("/flags", response_class=HTMLResponse)
async def flags_list(request: Request, environment: str = "production"):
    """List all flags with filtering."""
    try:
        flags_data = await get_all_flags(environment)
        
        return templates.TemplateResponse("flags_list.html", {
            "request": request,
            "flags": flags_data.get("flags", []),
            "current_environment": environment,
            "environments": ["development", "staging", "production"]
        })
    except Exception as e:
        logger.error(f"Flags list error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load flags"
        })


@app.get("/flags/{flag_id}", response_class=HTMLResponse)
async def flag_details(request: Request, flag_id: str):
    """Detailed flag management page."""
    try:
        flag_data = await get_flag_details(flag_id)
        metrics_data = await get_flag_metrics(flag_id)
        audit_data = await get_audit_log(flag_id)
        
        return templates.TemplateResponse("flag_details.html", {
            "request": request,
            "flag": flag_data,
            "metrics": metrics_data,
            "audit_log": audit_data.get("audit_log", []),
            "environments": ["development", "staging", "production"]
        })
    except Exception as e:
        logger.error(f"Flag details error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Failed to load flag details: {e}"
        })


@app.get("/rollout/{flag_id}", response_class=HTMLResponse)
async def rollout_controls(request: Request, flag_id: str):
    """Gradual rollout control interface."""
    try:
        flag_data = await get_flag_details(flag_id)
        metrics_data = await get_flag_metrics(flag_id, hours=168)  # 7 days
        
        return templates.TemplateResponse("rollout_controls.html", {
            "request": request,
            "flag": flag_data,
            "metrics": metrics_data,
            "environments": ["development", "staging", "production"]
        })
    except Exception as e:
        logger.error(f"Rollout controls error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Failed to load rollout controls: {e}"
        })


@app.get("/targeting/{flag_id}", response_class=HTMLResponse)
async def targeting_rules(request: Request, flag_id: str, environment: str = "production"):
    """User targeting rules management."""
    try:
        flag_data = await get_flag_details(flag_id)
        
        return templates.TemplateResponse("targeting_rules.html", {
            "request": request,
            "flag": flag_data,
            "current_environment": environment,
            "environments": ["development", "staging", "production"],
            "operators": [
                {"value": "equals", "label": "Equals"},
                {"value": "not_equals", "label": "Not Equals"},
                {"value": "in", "label": "In List"},
                {"value": "not_in", "label": "Not In List"},
                {"value": "contains", "label": "Contains"},
                {"value": "starts_with", "label": "Starts With"},
                {"value": "ends_with", "label": "Ends With"},
                {"value": "greater_than", "label": "Greater Than"},
                {"value": "less_than", "label": "Less Than"},
                {"value": "regex_match", "label": "Regex Match"}
            ]
        })
    except Exception as e:
        logger.error(f"Targeting rules error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Failed to load targeting rules: {e}"
        })


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(request: Request, hours: int = 24):
    """Analytics and metrics dashboard."""
    try:
        overall_metrics = await get_flag_metrics(hours=hours)
        flags_data = await get_all_flags()
        
        # Get metrics for each flag
        flag_metrics = {}
        for flag in flags_data.get("flags", [])[:10]:  # Limit to top 10 for performance
            try:
                flag_metrics[flag["flag_id"]] = await get_flag_metrics(flag["flag_id"], hours=hours)
            except:
                pass
        
        return templates.TemplateResponse("analytics.html", {
            "request": request,
            "overall_metrics": overall_metrics,
            "flag_metrics": flag_metrics,
            "hours": hours,
            "time_ranges": [
                {"value": 1, "label": "Last Hour"},
                {"value": 24, "label": "Last Day"},
                {"value": 168, "label": "Last Week"},
                {"value": 720, "label": "Last Month"}
            ]
        })
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Failed to load analytics: {e}"
        })


# API routes for AJAX calls
@app.post("/api/toggle", dependencies=[Depends(verify_admin_auth)])
async def api_toggle_flag(request: FlagToggleRequest):
    """Toggle flag via API."""
    try:
        result = await toggle_flag(request.flag_id, request.environment, request.enabled)
        
        # Broadcast update to connected clients
        update_message = {
            "type": "flag_toggled",
            "flag_id": request.flag_id,
            "environment": request.environment,
            "enabled": request.enabled,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await manager.broadcast(json.dumps(update_message))
        
        return {"success": True, "message": result.get("message", "Flag toggled successfully")}
    except Exception as e:
        logger.error(f"Toggle flag error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rollout", dependencies=[Depends(verify_admin_auth)])
async def api_update_rollout(request: RolloutUpdateRequest):
    """Update rollout percentage."""
    try:
        config = {
            "flag_id": request.flag_id,
            "environment": request.environment,
            "rollout_percentage": request.percentage,
            "enabled": True
        }
        
        result = await update_flag_environment(request.flag_id, request.environment, config)
        
        # Broadcast update
        update_message = {
            "type": "rollout_updated",
            "flag_id": request.flag_id,
            "environment": request.environment,
            "percentage": request.percentage,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await manager.broadcast(json.dumps(update_message))
        
        return {"success": True, "message": "Rollout percentage updated"}
    except Exception as e:
        logger.error(f"Update rollout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/emergency-disable", dependencies=[Depends(verify_admin_auth)])
async def api_emergency_disable(flag_id: str, environments: List[str] = None):
    """Emergency disable flag across environments."""
    try:
        if not environments:
            environments = ["development", "staging", "production"]
        
        results = []
        for env in environments:
            try:
                result = await toggle_flag(flag_id, env, False)
                results.append({"environment": env, "success": True, "result": result})
            except Exception as e:
                results.append({"environment": env, "success": False, "error": str(e)})
        
        # Broadcast emergency disable
        update_message = {
            "type": "emergency_disable",
            "flag_id": flag_id,
            "environments": environments,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await manager.broadcast(json.dumps(update_message))
        
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Emergency disable error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flags/{flag_id}/metrics")
async def api_flag_metrics(flag_id: str, hours: int = 24):
    """Get flag metrics via API."""
    try:
        metrics = await get_flag_metrics(flag_id, hours=hours)
        return metrics
    except Exception as e:
        logger.error(f"Get metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/targeting/{flag_id}", dependencies=[Depends(verify_admin_auth)])
async def api_update_targeting(flag_id: str, environment: str, rules: List[TargetingRuleRequest]):
    """Update targeting rules."""
    try:
        config = {
            "flag_id": flag_id,
            "environment": environment,
            "targeting_rules": [asdict(rule) for rule in rules],
            "enabled": True
        }
        
        result = await update_flag_environment(flag_id, environment, config)
        
        # Broadcast update
        update_message = {
            "type": "targeting_updated",
            "flag_id": flag_id,
            "environment": environment,
            "rules_count": len(rules),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await manager.broadcast(json.dumps(update_message))
        
        return {"success": True, "message": "Targeting rules updated"}
    except Exception as e:
        logger.error(f"Update targeting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back any received messages (for keepalive)
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test connection to feature flag service
        response = await http_client.get(f"{FEATURE_FLAG_API_URL}/health")
        api_healthy = response.status_code == 200
        
        return {
            "status": "healthy" if api_healthy else "degraded",
            "api_connection": "healthy" if api_healthy else "failed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("Feature Flag Admin Interface starting up")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    await http_client.aclose()
    logger.info("Feature Flag Admin Interface shut down")


if __name__ == "__main__":
    # Create templates directory if it doesn't exist
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    
    uvicorn.run(
        "web_interface:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )