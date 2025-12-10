"""Security monitoring system for threat detection and response."""

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from app.core.config import settings
from app.core.logging import logger
from app.core.security.audit_logger import SecurityEventType, SecuritySeverity, security_audit_logger


class ThreatLevel(str, Enum):
    """Threat level classifications."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResponseAction(str, Enum):
    """Automated response actions."""

    LOG_ONLY = "log_only"
    RATE_LIMIT = "rate_limit"
    TEMPORARY_BLOCK = "temporary_block"
    PERMANENT_BLOCK = "permanent_block"
    ALERT_ADMIN = "alert_admin"
    REQUIRE_2FA = "require_2fa"


@dataclass
class SecurityThreat:
    """Represents a detected security threat."""

    threat_id: str
    threat_type: str
    level: ThreatLevel
    source_ip: str | None
    user_id: str | None
    description: str
    evidence: dict[str, Any]
    detected_at: datetime
    response_actions: list[ResponseAction]
    resolved: bool = False
    resolved_at: datetime | None = None


@dataclass
class SecurityRule:
    """Security monitoring rule definition."""

    rule_id: str
    name: str
    description: str
    event_types: list[SecurityEventType]
    conditions: dict[str, Any]
    threshold: int
    time_window_minutes: int
    threat_level: ThreatLevel
    response_actions: list[ResponseAction]
    enabled: bool = True


class SecurityMonitor:
    """Real-time security monitoring and threat detection system."""

    def __init__(self):
        """Initialize security monitor."""
        self.event_buffer_size = 10000
        self.monitoring_window_minutes = 60
        self.cleanup_interval_minutes = 30

        # Event tracking
        self.recent_events: deque[dict[str, Any]] = deque(maxlen=self.event_buffer_size)
        self.ip_tracking: dict[str, dict[str, list[Any]]] = defaultdict(lambda: defaultdict(list))
        self.user_tracking: dict[str, dict[str, list[Any]]] = defaultdict(lambda: defaultdict(list))
        self.session_tracking: dict[str, dict[str, list[Any]]] = defaultdict(lambda: defaultdict(list))

        # Active threats and blocks
        self.active_threats: dict[str, SecurityThreat] = {}
        self.blocked_ips: set[str] = set()
        self.blocked_users: set[str] = set()
        self.rate_limited_ips: dict[str, dict[str, int | datetime]] = defaultdict(
            lambda: {"count": 0, "reset_time": datetime.utcnow()}
        )

        # Security rules
        self.security_rules = self._initialize_security_rules()

        # Start background monitoring (only if event loop is running)
        self.monitoring_active = True
        try:
            asyncio.get_running_loop()
            asyncio.create_task(self._cleanup_old_data())
        except RuntimeError:
            # No running event loop - task will be started when needed
            pass

    def _initialize_security_rules(self) -> list[SecurityRule]:
        """Initialize default security monitoring rules."""
        return [
            SecurityRule(
                rule_id="brute_force_login",
                name="Brute Force Login Detection",
                description="Detect multiple failed login attempts",
                event_types=[SecurityEventType.LOGIN_FAILURE],
                conditions={"outcome": "failure"},
                threshold=5,
                time_window_minutes=15,
                threat_level=ThreatLevel.HIGH,
                response_actions=[ResponseAction.TEMPORARY_BLOCK, ResponseAction.ALERT_ADMIN],
            ),
            SecurityRule(
                rule_id="invalid_api_key_spam",
                name="Invalid API Key Spam",
                description="Detect repeated invalid API key usage",
                event_types=[SecurityEventType.INVALID_API_KEY],
                conditions={},
                threshold=10,
                time_window_minutes=5,
                threat_level=ThreatLevel.MEDIUM,
                response_actions=[ResponseAction.RATE_LIMIT, ResponseAction.LOG_ONLY],
            ),
            SecurityRule(
                rule_id="rate_limit_exceeded",
                name="Rate Limit Exceeded",
                description="Detect repeated rate limit violations",
                event_types=[SecurityEventType.RATE_LIMIT_EXCEEDED],
                conditions={},
                threshold=3,
                time_window_minutes=10,
                threat_level=ThreatLevel.MEDIUM,
                response_actions=[ResponseAction.TEMPORARY_BLOCK],
            ),
            SecurityRule(
                rule_id="signature_failures",
                name="Request Signature Failures",
                description="Detect repeated signature verification failures",
                event_types=[SecurityEventType.SIGNATURE_FAILED],
                conditions={},
                threshold=20,
                time_window_minutes=5,
                threat_level=ThreatLevel.HIGH,
                response_actions=[ResponseAction.TEMPORARY_BLOCK, ResponseAction.ALERT_ADMIN],
            ),
            SecurityRule(
                rule_id="gdpr_violations",
                name="GDPR Violation Attempts",
                description="Detect potential GDPR compliance violations",
                event_types=[SecurityEventType.PII_DETECTED],
                conditions={"severity": "high"},
                threshold=1,
                time_window_minutes=1,
                threat_level=ThreatLevel.CRITICAL,
                response_actions=[ResponseAction.ALERT_ADMIN, ResponseAction.LOG_ONLY],
            ),
            SecurityRule(
                rule_id="payment_fraud",
                name="Payment Fraud Detection",
                description="Detect suspicious payment activities",
                event_types=[SecurityEventType.FRAUD_DETECTED, SecurityEventType.PAYMENT_FAILURE],
                conditions={},
                threshold=2,
                time_window_minutes=30,
                threat_level=ThreatLevel.CRITICAL,
                response_actions=[ResponseAction.PERMANENT_BLOCK, ResponseAction.ALERT_ADMIN],
            ),
        ]

    async def process_security_event(
        self,
        event_type: SecurityEventType,
        user_id: str | None = None,
        ip_address: str | None = None,
        session_id: str | None = None,
        outcome: str = "unknown",
        details: dict[str, Any] | None = None,
    ) -> SecurityThreat | None:
        """Process a security event and check for threats.

        Args:
            event_type: Type of security event
            user_id: User identifier
            ip_address: Client IP address
            session_id: Session identifier
            outcome: Event outcome
            details: Additional event details

        Returns:
            SecurityThreat if threat detected, None otherwise
        """
        try:
            # Create event record
            event = {
                "timestamp": datetime.utcnow(),
                "event_type": event_type,
                "user_id": user_id,
                "ip_address": ip_address,
                "session_id": session_id,
                "outcome": outcome,
                "details": details or {},
            }

            # Add to recent events buffer
            self.recent_events.append(event)

            # Track by IP, user, and session
            if ip_address:
                self.ip_tracking[ip_address][event_type].append(event)
            if user_id:
                self.user_tracking[user_id][event_type].append(event)
            if session_id:
                self.session_tracking[session_id][event_type].append(event)

            # Check security rules
            detected_threat = await self._check_security_rules(event)

            if detected_threat:
                # Execute response actions
                await self._execute_response_actions(detected_threat)

                # Store threat
                self.active_threats[detected_threat.threat_id] = detected_threat

                logger.warning(
                    "security_threat_detected",
                    threat_id=detected_threat.threat_id,
                    threat_type=detected_threat.threat_type,
                    level=detected_threat.level.value,
                    source_ip=detected_threat.source_ip,
                    user_id=detected_threat.user_id,
                )

            return detected_threat

        except Exception as e:
            logger.error("security_event_processing_failed", event_type=event_type.value, error=str(e), exc_info=True)
            return None

    async def _check_security_rules(self, event: dict[str, Any]) -> SecurityThreat | None:
        """Check event against security rules."""
        try:
            for rule in self.security_rules:
                if not rule.enabled:
                    continue

                if event["event_type"] not in rule.event_types:
                    continue

                # Check rule conditions
                if not self._matches_conditions(event, rule.conditions):
                    continue

                # Check threshold within time window
                relevant_events = self._get_relevant_events(event, rule)

                if len(relevant_events) >= rule.threshold:
                    # Threat detected
                    threat_id = f"{rule.rule_id}_{datetime.utcnow().timestamp()}"

                    threat = SecurityThreat(
                        threat_id=threat_id,
                        threat_type=rule.rule_id,
                        level=rule.threat_level,
                        source_ip=event.get("ip_address"),
                        user_id=event.get("user_id"),
                        description=f"{rule.name}: {rule.description}",
                        evidence={
                            "rule": rule.name,
                            "threshold": rule.threshold,
                            "actual_count": len(relevant_events),
                            "time_window_minutes": rule.time_window_minutes,
                            "events": [
                                {
                                    "timestamp": e["timestamp"].isoformat(),
                                    "event_type": e["event_type"].value,
                                    "outcome": e["outcome"],
                                }
                                for e in relevant_events[-10:]  # Last 10 events
                            ],
                        },
                        detected_at=datetime.utcnow(),
                        response_actions=rule.response_actions,
                    )

                    return threat

            return None

        except Exception as e:
            logger.error("security_rule_check_failed", error=str(e), exc_info=True)
            return None

    def _matches_conditions(self, event: dict[str, Any], conditions: dict[str, Any]) -> bool:
        """Check if event matches rule conditions."""
        for key, expected_value in conditions.items():
            if (
                key in event
                and event[key] != expected_value
                or key in event.get("details", {})
                and event["details"][key] != expected_value
            ):
                return False
        return True

    def _get_relevant_events(self, current_event: dict[str, Any], rule: SecurityRule) -> list[dict[str, Any]]:
        """Get events relevant to the security rule."""
        time_cutoff = datetime.utcnow() - timedelta(minutes=rule.time_window_minutes)

        # Determine tracking source (IP, user, or session)
        tracking_key = None
        tracking_dict = None

        if current_event.get("ip_address"):
            tracking_key = current_event["ip_address"]
            tracking_dict = self.ip_tracking
        elif current_event.get("user_id"):
            tracking_key = current_event["user_id"]
            tracking_dict = self.user_tracking
        elif current_event.get("session_id"):
            tracking_key = current_event["session_id"]
            tracking_dict = self.session_tracking

        if not tracking_key or not tracking_dict:
            return []

        # Get relevant events
        relevant_events = []
        for event_type in rule.event_types:
            events = tracking_dict[tracking_key][event_type]
            for event in events:
                if event["timestamp"] >= time_cutoff:
                    if self._matches_conditions(event, rule.conditions):
                        relevant_events.append(event)

        return relevant_events

    async def _execute_response_actions(self, threat: SecurityThreat) -> None:
        """Execute automated response actions for a threat."""
        try:
            for action in threat.response_actions:
                if action == ResponseAction.LOG_ONLY:
                    await security_audit_logger.log_security_event(
                        event_type=SecurityEventType.SECURITY_INCIDENT,
                        severity=SecuritySeverity.HIGH,
                        user_id=threat.user_id,
                        ip_address=threat.source_ip,
                        action="threat_detected",
                        outcome="logged",
                        details=threat.evidence,
                    )

                elif action == ResponseAction.RATE_LIMIT:
                    if threat.source_ip:
                        self.rate_limited_ips[threat.source_ip] = {
                            "count": 1000,  # High limit to effectively block
                            "reset_time": datetime.utcnow() + timedelta(hours=1),
                        }
                        logger.info("ip_rate_limited", ip_address=threat.source_ip, threat_id=threat.threat_id)

                elif action == ResponseAction.TEMPORARY_BLOCK:
                    if threat.source_ip:
                        self.blocked_ips.add(threat.source_ip)
                        # Would implement actual blocking mechanism
                        logger.warning(
                            "ip_temporarily_blocked", ip_address=threat.source_ip, threat_id=threat.threat_id
                        )

                elif action == ResponseAction.PERMANENT_BLOCK:
                    if threat.source_ip:
                        self.blocked_ips.add(threat.source_ip)
                    if threat.user_id:
                        self.blocked_users.add(threat.user_id)
                        logger.critical(
                            "user_permanently_blocked",
                            user_id=threat.user_id,
                            ip_address=threat.source_ip,
                            threat_id=threat.threat_id,
                        )

                elif action == ResponseAction.ALERT_ADMIN:
                    await self._send_admin_alert(threat)

                elif action == ResponseAction.REQUIRE_2FA:
                    if threat.user_id:
                        # Would implement 2FA requirement
                        logger.info("2fa_required", user_id=threat.user_id, threat_id=threat.threat_id)

        except Exception as e:
            logger.error("response_action_execution_failed", threat_id=threat.threat_id, error=str(e), exc_info=True)

    async def _send_admin_alert(self, threat: SecurityThreat) -> None:
        """Send alert to administrators."""
        # Would implement actual alerting system (email, Slack, etc.)
        logger.critical(
            "admin_alert_sent",
            threat_id=threat.threat_id,
            threat_type=threat.threat_type,
            level=threat.level.value,
            description=threat.description,
        )

    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked."""
        return ip_address in self.blocked_ips

    def is_user_blocked(self, user_id: str) -> bool:
        """Check if user is blocked."""
        return user_id in self.blocked_users

    def is_rate_limited(self, ip_address: str) -> bool:
        """Check if IP address is rate limited."""
        if ip_address not in self.rate_limited_ips:
            return False

        limit_info = self.rate_limited_ips[ip_address]
        if datetime.utcnow() > limit_info["reset_time"]:  # type: ignore[operator]
            # Rate limit expired
            del self.rate_limited_ips[ip_address]
            return False

        return limit_info["count"] <= 0  # type: ignore[operator]

    def get_threat_statistics(self) -> dict[str, Any]:
        """Get security threat statistics."""
        try:
            active_threats_by_level: dict[str, int] = {}
            for threat in self.active_threats.values():
                if not threat.resolved:
                    level_key = threat.level.value
                    active_threats_by_level[level_key] = active_threats_by_level.get(level_key, 0) + 1

            stats = {
                "monitoring_status": "active" if self.monitoring_active else "inactive",
                "active_threats": len([t for t in self.active_threats.values() if not t.resolved]),
                "threats_by_level": dict(active_threats_by_level),
                "blocked_ips": len(self.blocked_ips),
                "blocked_users": len(self.blocked_users),
                "rate_limited_ips": len(self.rate_limited_ips),
                "recent_events_count": len(self.recent_events),
                "security_rules_count": len(self.security_rules),
                "enabled_rules_count": len([r for r in self.security_rules if r.enabled]),
            }

            return stats

        except Exception as e:
            logger.error("threat_statistics_failed", error=str(e), exc_info=True)
            return {}

    async def resolve_threat(self, threat_id: str, resolution_notes: str = "") -> bool:
        """Mark a threat as resolved."""
        try:
            if threat_id in self.active_threats:
                threat = self.active_threats[threat_id]
                threat.resolved = True
                threat.resolved_at = datetime.utcnow()

                logger.info("threat_resolved", threat_id=threat_id, resolution_notes=resolution_notes)

                return True

            return False

        except Exception as e:
            logger.error("threat_resolution_failed", threat_id=threat_id, error=str(e), exc_info=True)
            return False

    async def _cleanup_old_data(self) -> None:
        """Background task to clean up old tracking data."""
        while self.monitoring_active:
            try:
                await asyncio.sleep(self.cleanup_interval_minutes * 60)

                cutoff_time = datetime.utcnow() - timedelta(minutes=self.monitoring_window_minutes)
                cleaned_count = 0

                # Clean IP tracking
                for ip, events_by_type in self.ip_tracking.items():
                    for _event_type, events in events_by_type.items():
                        before_count = len(events)
                        events[:] = [e for e in events if e["timestamp"] >= cutoff_time]
                        cleaned_count += before_count - len(events)

                # Clean user tracking
                for _user, events_by_type in self.user_tracking.items():
                    for _event_type, events in events_by_type.items():
                        before_count = len(events)
                        events[:] = [e for e in events if e["timestamp"] >= cutoff_time]
                        cleaned_count += before_count - len(events)

                # Clean session tracking
                for _session, events_by_type in self.session_tracking.items():
                    for _event_type, events in events_by_type.items():
                        before_count = len(events)
                        events[:] = [e for e in events if e["timestamp"] >= cutoff_time]
                        cleaned_count += before_count - len(events)

                # Clean expired rate limits
                expired_ips = [
                    ip
                    for ip, info in self.rate_limited_ips.items()
                    if datetime.utcnow() > info["reset_time"]  # type: ignore[operator]
                ]
                for ip in expired_ips:
                    del self.rate_limited_ips[ip]

                if cleaned_count > 0:
                    logger.debug(
                        "security_monitoring_cleanup",
                        cleaned_events=cleaned_count,
                        expired_rate_limits=len(expired_ips),
                    )

            except Exception as e:
                logger.error("security_monitoring_cleanup_failed", error=str(e), exc_info=True)


# Global instance
security_monitor = SecurityMonitor()
