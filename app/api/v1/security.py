"""Security management API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.security import api_key_manager, security_audit_logger, security_monitor
from app.core.security.audit_logger import SecurityEventType, SecuritySeverity
from app.models.session import Session

router = APIRouter()


class GenerateAPIKeyRequest(BaseModel):
    """Request to generate new API key."""

    key_type: str = Field(default="user", description="Type of key: user, admin, service")
    expires_in_days: int | None = Field(default=30, ge=1, le=365, description="Expiration in days")


class RevokeAPIKeyRequest(BaseModel):
    """Request to revoke API key."""

    api_key: str = Field(..., description="API key to revoke")
    reason: str = Field(default="manual_revocation", description="Reason for revocation")


class SecurityEventRequest(BaseModel):
    """Request to log security event."""

    event_type: str = Field(..., description="Security event type")
    severity: str = Field(default="low", description="Event severity")
    resource: str | None = Field(default=None, description="Resource accessed")
    action: str | None = Field(default=None, description="Action performed")
    outcome: str = Field(default="unknown", description="Event outcome")
    details: dict[str, Any] | None = Field(default_factory=dict, description="Additional details")


class ResolveThreatRequest(BaseModel):
    """Request to resolve security threat."""

    threat_id: str = Field(..., description="Threat ID to resolve")
    resolution_notes: str = Field(default="", description="Resolution notes")


@router.post("/api-keys/generate")
@limiter.limit("5 per hour")
async def generate_api_key(
    request: Request,
    key_request: GenerateAPIKeyRequest,
    session: Session = Depends(get_current_session),
):
    """Generate a new API key for the user.

    Args:
        request: FastAPI request object
        key_request: API key generation parameters
        session: Current user session

    Returns:
        New API key information
    """
    try:
        # Validate key type
        valid_key_types = ["user", "admin", "service"]
        if key_request.key_type not in valid_key_types:
            raise HTTPException(
                status_code=400, detail=f"Invalid key type. Must be one of: {', '.join(valid_key_types)}"
            )

        # Check if user can create admin/service keys
        if key_request.key_type in ["admin", "service"]:
            # Would check user permissions here
            logger.warning("admin_key_generation_attempted", user_id=session.user_id, key_type=key_request.key_type)
            # For now, only allow user keys
            raise HTTPException(status_code=403, detail="Insufficient permissions to create admin/service keys")

        # Generate new API key
        new_key = api_key_manager.generate_api_key(user_id=session.user_id, key_type=key_request.key_type)

        # Store key (would set expiration based on expires_in_days)
        success = await api_key_manager.store_api_key(
            user_id=session.user_id, api_key=new_key, key_type=key_request.key_type
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to store API key")

        # Log security event
        await security_audit_logger.log_api_security_event(
            event_type=SecurityEventType.API_KEY_CREATED,
            user_id=session.user_id,
            api_key_prefix=new_key[:12] + "...",
            ip_address=request.client.host if request.client else None,
            outcome="success",
        )

        logger.info(
            "api_key_generated_via_endpoint",
            user_id=session.user_id,
            key_type=key_request.key_type,
            key_prefix=new_key[:12] + "...",
        )

        return JSONResponse(
            {
                "api_key": new_key,
                "key_type": key_request.key_type,
                "expires_in_days": key_request.expires_in_days,
                "created_at": datetime.utcnow().isoformat(),
                "warning": "Store this key securely. It will not be shown again.",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_key_generation_endpoint_failed", user_id=session.user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="API key generation failed")


@router.post("/api-keys/rotate")
@limiter.limit("3 per hour")
async def rotate_api_keys(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Rotate all API keys for the current user.

    Args:
        request: FastAPI request object
        session: Current user session

    Returns:
        Key rotation information
    """
    try:
        # Rotate user keys
        rotation_result = await api_key_manager.rotate_user_keys(session.user_id)

        # Log security event
        await security_audit_logger.log_api_security_event(
            event_type=SecurityEventType.API_KEY_ROTATED,
            user_id=session.user_id,
            ip_address=request.client.host if request.client else None,
            outcome="success",
            details={
                "old_keys_count": rotation_result["old_keys_count"],
                "grace_period_ends": rotation_result["grace_period_ends"],
            },
        )

        logger.info(
            "api_keys_rotated_via_endpoint", user_id=session.user_id, old_keys_count=rotation_result["old_keys_count"]
        )

        return JSONResponse(
            {
                "success": True,
                "new_api_key": rotation_result["new_key"],
                "old_keys_count": rotation_result["old_keys_count"],
                "grace_period_ends": rotation_result["grace_period_ends"],
                "message": "API keys rotated successfully. Old keys will be valid during grace period.",
            }
        )

    except Exception as e:
        logger.error("api_key_rotation_endpoint_failed", user_id=session.user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="API key rotation failed")


@router.post("/api-keys/revoke")
@limiter.limit("10 per hour")
async def revoke_api_key(
    request: Request,
    revoke_request: RevokeAPIKeyRequest,
    session: Session = Depends(get_current_session),
):
    """Revoke an API key.

    Args:
        request: FastAPI request object
        revoke_request: API key revocation parameters
        session: Current user session

    Returns:
        Revocation confirmation
    """
    try:
        # Revoke the key
        success = await api_key_manager.revoke_api_key(api_key=revoke_request.api_key, reason=revoke_request.reason)

        if not success:
            raise HTTPException(status_code=404, detail="API key not found or already revoked")

        # Log security event
        await security_audit_logger.log_api_security_event(
            event_type=SecurityEventType.API_KEY_REVOKED,
            user_id=session.user_id,
            api_key_prefix=revoke_request.api_key[:12] + "...",
            ip_address=request.client.host if request.client else None,
            outcome="success",
            details={"reason": revoke_request.reason},
        )

        logger.info(
            "api_key_revoked_via_endpoint",
            user_id=session.user_id,
            key_prefix=revoke_request.api_key[:12] + "...",
            reason=revoke_request.reason,
        )

        return JSONResponse(
            {"success": True, "message": "API key revoked successfully", "revoked_at": datetime.utcnow().isoformat()}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_key_revocation_endpoint_failed", user_id=session.user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="API key revocation failed")


@router.get("/api-keys/stats")
@limiter.limit("20 per hour")
async def get_api_key_statistics(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get API key statistics for the user.

    Args:
        request: FastAPI request object
        session: Current user session

    Returns:
        API key statistics
    """
    try:
        stats = await api_key_manager.get_key_statistics(user_id=session.user_id)

        logger.debug("api_key_stats_retrieved", user_id=session.user_id)

        return JSONResponse(stats)

    except Exception as e:
        logger.error("api_key_stats_endpoint_failed", user_id=session.user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve API key statistics")


@router.post("/events/log")
@limiter.limit("50 per hour")
async def log_security_event(
    request: Request,
    event_request: SecurityEventRequest,
    session: Session = Depends(get_current_session),
):
    """Log a custom security event.

    Args:
        request: FastAPI request object
        event_request: Security event parameters
        session: Current user session

    Returns:
        Event logging confirmation
    """
    try:
        # Validate event type and severity
        try:
            event_type = SecurityEventType(event_request.event_type)
            severity = SecuritySeverity(event_request.severity)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid event type or severity: {str(e)}")

        # Log the security event
        success = await security_audit_logger.log_security_event(
            event_type=event_type,
            severity=severity,
            user_id=session.user_id,
            session_id=session.id,
            ip_address=request.client.host if request.client else None,
            resource=event_request.resource,
            action=event_request.action,
            outcome=event_request.outcome,
            details=event_request.details,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to log security event")

        logger.info(
            "custom_security_event_logged",
            user_id=session.user_id,
            event_type=event_request.event_type,
            severity=event_request.severity,
        )

        return JSONResponse(
            {
                "success": True,
                "message": "Security event logged successfully",
                "logged_at": datetime.utcnow().isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("security_event_logging_endpoint_failed", user_id=session.user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Security event logging failed")


@router.get("/monitoring/status")
@limiter.limit("30 per hour")
async def get_security_monitoring_status(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get security monitoring status.

    Args:
        request: FastAPI request object
        session: Current user session

    Returns:
        Security monitoring status and statistics
    """
    try:
        # Get threat statistics
        stats = security_monitor.get_threat_statistics()

        # Add additional status info
        status_info = {
            "monitoring_enabled": True,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": session.user_id,
            **stats,
        }

        logger.debug(
            "security_monitoring_status_retrieved",
            user_id=session.user_id,
            active_threats=stats.get("active_threats", 0),
        )

        return JSONResponse(status_info)

    except Exception as e:
        logger.error(
            "security_monitoring_status_endpoint_failed", user_id=session.user_id, error=str(e), exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve security monitoring status")


@router.post("/threats/resolve")
@limiter.limit("20 per hour")
async def resolve_security_threat(
    request: Request,
    resolve_request: ResolveThreatRequest,
    session: Session = Depends(get_current_session),
):
    """Resolve a security threat (admin only).

    Args:
        request: FastAPI request object
        resolve_request: Threat resolution parameters
        session: Current user session

    Returns:
        Threat resolution confirmation
    """
    try:
        # Check admin permissions (simplified check)
        # In production, would check proper admin role
        if not session.user_id.startswith("admin_"):
            raise HTTPException(status_code=403, detail="Admin privileges required to resolve threats")

        # Resolve the threat
        success = await security_monitor.resolve_threat(
            threat_id=resolve_request.threat_id, resolution_notes=resolve_request.resolution_notes
        )

        if not success:
            raise HTTPException(status_code=404, detail="Threat not found")

        # Log security event
        await security_audit_logger.log_security_event(
            event_type=SecurityEventType.SECURITY_INCIDENT,
            severity=SecuritySeverity.MEDIUM,
            user_id=session.user_id,
            ip_address=request.client.host if request.client else None,
            action="threat_resolved",
            outcome="success",
            details={"threat_id": resolve_request.threat_id, "resolution_notes": resolve_request.resolution_notes},
        )

        logger.info(
            "security_threat_resolved_via_endpoint", admin_user_id=session.user_id, threat_id=resolve_request.threat_id
        )

        return JSONResponse(
            {
                "success": True,
                "message": "Security threat resolved successfully",
                "threat_id": resolve_request.threat_id,
                "resolved_at": datetime.utcnow().isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "threat_resolution_endpoint_failed",
            user_id=session.user_id,
            threat_id=resolve_request.threat_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Threat resolution failed")


@router.get("/audit/events")
@limiter.limit("20 per hour")
async def get_audit_events(
    request: Request,
    session: Session = Depends(get_current_session),
    event_type: str | None = Query(default=None, description="Filter by event type"),
    severity: str | None = Query(default=None, description="Filter by severity"),
    limit: int = Query(default=50, ge=1, le=100, description="Number of events to return"),
):
    """Get security audit events for the user.

    Args:
        request: FastAPI request object
        session: Current user session
        event_type: Optional event type filter
        severity: Optional severity filter
        limit: Maximum number of events

    Returns:
        Security audit events
    """
    try:
        # Parse optional filters
        event_type_enum = None
        severity_enum = None

        if event_type:
            try:
                event_type_enum = SecurityEventType(event_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")

        if severity:
            try:
                severity_enum = SecuritySeverity(severity)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

        # Get audit events
        events = await security_audit_logger.get_security_events(
            user_id=session.user_id, event_type=event_type_enum, severity=severity_enum, limit=limit
        )

        logger.debug("audit_events_retrieved", user_id=session.user_id, events_count=len(events))

        return JSONResponse(
            {
                "events": events,
                "count": len(events),
                "filters": {"event_type": event_type, "severity": severity, "limit": limit},
                "retrieved_at": datetime.utcnow().isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("audit_events_endpoint_failed", user_id=session.user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve audit events")


@router.get("/compliance/report")
@limiter.limit("5 per hour")
async def generate_compliance_report(
    request: Request,
    session: Session = Depends(get_current_session),
    report_type: str = Query(default="gdpr", description="Type of compliance report"),
):
    """Generate compliance audit report (admin only).

    Args:
        request: FastAPI request object
        session: Current user session
        report_type: Type of compliance report

    Returns:
        Compliance report
    """
    try:
        # Check admin permissions
        if not session.user_id.startswith("admin_"):
            raise HTTPException(status_code=403, detail="Admin privileges required to generate compliance reports")

        # Generate compliance report
        report = await security_audit_logger.generate_compliance_report(report_type=report_type)

        if not report:
            raise HTTPException(status_code=500, detail="Failed to generate compliance report")

        logger.info("compliance_report_generated_via_endpoint", admin_user_id=session.user_id, report_type=report_type)

        return JSONResponse(report)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "compliance_report_endpoint_failed",
            user_id=session.user_id,
            report_type=report_type,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Compliance report generation failed")
