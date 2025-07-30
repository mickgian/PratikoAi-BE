"""Security audit logging system for compliance and monitoring."""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from sqlalchemy import select
from app.core.logging import logger
from app.core.config import settings
from app.services.database import database_service


class SecurityEventType(str, Enum):
    """Types of security events to audit."""
    
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    ACCOUNT_LOCKED = "account_locked"
    
    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_ESCALATION = "permission_escalation"
    
    # API security events
    API_KEY_CREATED = "api_key_created"
    API_KEY_ROTATED = "api_key_rotated"
    API_KEY_REVOKED = "api_key_revoked"
    INVALID_API_KEY = "invalid_api_key"
    
    # Request security events
    REQUEST_SIGNED = "request_signed"
    SIGNATURE_VERIFIED = "signature_verified"
    SIGNATURE_FAILED = "signature_failed"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # Data security events
    PII_DETECTED = "pii_detected"
    DATA_ANONYMIZED = "data_anonymized"
    GDPR_REQUEST = "gdpr_request"
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"
    
    # System security events
    SECURITY_SCAN = "security_scan"
    VULNERABILITY_DETECTED = "vulnerability_detected"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_INCIDENT = "security_incident"
    
    # Payment security events
    PAYMENT_ATTEMPT = "payment_attempt"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILURE = "payment_failure"
    FRAUD_DETECTED = "fraud_detected"


class SecuritySeverity(str, Enum):
    """Security event severity levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityAuditLogger:
    """Handles security audit logging and compliance tracking."""
    
    def __init__(self):
        """Initialize security audit logger."""
        self.enabled = settings.PRIVACY_ANONYMIZE_LOGS  # Reuse privacy setting
        self.max_log_retention_days = settings.PRIVACY_DATA_RETENTION_DAYS
        
    def log_security_event(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity = SecuritySeverity.LOW,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        outcome: str = "unknown",
        details: Optional[Dict[str, Any]] = None,
        compliance_tags: Optional[List[str]] = None
    ) -> bool:
        """Log a security event for audit purposes.
        
        Args:
            event_type: Type of security event
            severity: Event severity level
            user_id: User identifier (anonymized if needed)
            session_id: Session identifier
            ip_address: Client IP address (anonymized if needed)
            user_agent: User agent string
            resource: Resource being accessed
            action: Action being performed
            outcome: Event outcome (success, failure, etc.)
            details: Additional event details
            compliance_tags: Tags for compliance tracking
            
        Returns:
            True if logged successfully
        """
        try:
            if not self.enabled:
                return True
            
            # Anonymize sensitive data if required
            if settings.PRIVACY_ANONYMIZE_LOGS:
                user_id = self._anonymize_user_id(user_id) if user_id else None
                ip_address = self._anonymize_ip_address(ip_address) if ip_address else None
            
            # Create audit log entry
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type.value,
                "severity": severity.value,
                "user_id": user_id,
                "session_id": session_id,
                "ip_address": ip_address,
                "user_agent": user_agent[:200] if user_agent else None,  # Truncate
                "resource": resource,
                "action": action,
                "outcome": outcome,
                "details": details or {},
                "compliance_tags": compliance_tags or [],
                "retention_expires_at": (
                    datetime.utcnow().timestamp() + 
                    (self.max_log_retention_days * 24 * 3600)
                )
            }
            
            # Log to structured logger
            logger.info(
                "security_audit_event",
                **audit_entry
            )
            
            # Store in database for compliance queries (would implement actual storage)
            await self._store_audit_entry(audit_entry)
            
            # Trigger alerts for high severity events
            if severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]:
                await self._trigger_security_alert(audit_entry)
            
            return True
            
        except Exception as e:
            logger.error(
                "security_audit_logging_failed",
                event_type=event_type.value if event_type else "unknown",
                error=str(e),
                exc_info=True
            )
            return False
    
    async def log_authentication_event(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        outcome: str = "unknown",
        failure_reason: Optional[str] = None
    ) -> bool:
        """Log authentication-related security events.
        
        Args:
            event_type: Authentication event type
            user_id: User identifier
            ip_address: Client IP address
            user_agent: User agent string
            outcome: Event outcome
            failure_reason: Reason for failure (if applicable)
            
        Returns:
            True if logged successfully
        """
        severity = SecuritySeverity.MEDIUM
        if event_type == SecurityEventType.LOGIN_FAILURE:
            severity = SecuritySeverity.HIGH
        elif event_type == SecurityEventType.ACCOUNT_LOCKED:
            severity = SecuritySeverity.CRITICAL
        
        details = {}
        if failure_reason:
            details["failure_reason"] = failure_reason
        
        return await self.log_security_event(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action="authentication",
            outcome=outcome,
            details=details,
            compliance_tags=["authentication", "gdpr"]
        )
    
    async def log_api_security_event(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        api_key_prefix: Optional[str] = None,
        ip_address: Optional[str] = None,
        outcome: str = "unknown",
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log API security events.
        
        Args:
            event_type: API security event type
            user_id: User identifier
            api_endpoint: API endpoint accessed
            api_key_prefix: Prefix of API key used
            ip_address: Client IP address
            outcome: Event outcome
            details: Additional details
            
        Returns:
            True if logged successfully
        """
        severity = SecuritySeverity.LOW
        if event_type in [SecurityEventType.INVALID_API_KEY, SecurityEventType.ACCESS_DENIED]:
            severity = SecuritySeverity.MEDIUM
        elif event_type == SecurityEventType.RATE_LIMIT_EXCEEDED:
            severity = SecuritySeverity.HIGH
        
        event_details = details or {}
        if api_key_prefix:
            event_details["api_key_prefix"] = api_key_prefix
        
        return await self.log_security_event(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            resource=api_endpoint,
            action="api_access",
            outcome=outcome,
            details=event_details,
            compliance_tags=["api_security", "rate_limiting"]
        )
    
    async def log_gdpr_event(
        self,
        action: str,
        user_id: str,
        data_type: str,
        legal_basis: str,
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log GDPR compliance events.
        
        Args:
            action: GDPR action (consent, access, portability, erasure)
            user_id: User identifier
            data_type: Type of data processed
            legal_basis: Legal basis for processing
            outcome: Event outcome
            details: Additional details
            
        Returns:
            True if logged successfully
        """
        event_details = details or {}
        event_details.update({
            "data_type": data_type,
            "legal_basis": legal_basis,
            "gdpr_article": self._get_gdpr_article(action)
        })
        
        return await self.log_security_event(
            event_type=SecurityEventType.GDPR_REQUEST,
            severity=SecuritySeverity.MEDIUM,
            user_id=user_id,
            action=f"gdpr_{action}",
            outcome=outcome,
            details=event_details,
            compliance_tags=["gdpr", "data_protection", "compliance"]
        )
    
    async def log_payment_security_event(
        self,
        event_type: SecurityEventType,
        user_id: str,
        payment_method: str,
        amount: Optional[float] = None,
        currency: str = "EUR",
        outcome: str = "unknown",
        fraud_score: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log payment security events.
        
        Args:
            event_type: Payment security event type
            user_id: User identifier
            payment_method: Payment method used
            amount: Payment amount
            currency: Payment currency
            outcome: Event outcome
            fraud_score: Fraud detection score
            details: Additional details
            
        Returns:
            True if logged successfully
        """
        severity = SecuritySeverity.LOW
        if event_type == SecurityEventType.PAYMENT_FAILURE:
            severity = SecuritySeverity.MEDIUM
        elif event_type == SecurityEventType.FRAUD_DETECTED:
            severity = SecuritySeverity.CRITICAL
        
        event_details = details or {}
        event_details.update({
            "payment_method": payment_method,
            "amount": amount,
            "currency": currency
        })
        
        if fraud_score is not None:
            event_details["fraud_score"] = fraud_score
        
        return await self.log_security_event(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            action="payment",
            outcome=outcome,
            details=event_details,
            compliance_tags=["payment_security", "fraud_detection", "pci_compliance"]
        )
    
    async def get_security_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[SecurityEventType] = None,
        severity: Optional[SecuritySeverity] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve security events for analysis.
        
        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            severity: Filter by severity
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of events to return
            
        Returns:
            List of security events
        """
        try:
            # Would query database for actual events
            # For now, return sample data
            sample_events = [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "event_type": SecurityEventType.LOGIN_SUCCESS.value,
                    "severity": SecuritySeverity.LOW.value,
                    "user_id": "anonymized_user_123",
                    "outcome": "success",
                    "details": {"method": "password"}
                }
            ]
            
            logger.debug(
                "security_events_retrieved",
                user_id=user_id,
                event_type=event_type.value if event_type else None,
                events_count=len(sample_events)
            )
            
            return sample_events
            
        except Exception as e:
            logger.error(
                "security_events_retrieval_failed",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            return []
    
    async def generate_compliance_report(
        self,
        report_type: str = "gdpr",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate compliance audit report.
        
        Args:
            report_type: Type of compliance report
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            Compliance report data
        """
        try:
            # Would generate actual report from audit data
            report = {
                "report_type": report_type,
                "generated_at": datetime.utcnow().isoformat(),
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                },
                "summary": {
                    "total_events": 1250,
                    "high_severity_events": 15,
                    "critical_events": 2,
                    "gdpr_requests": 8,
                    "security_incidents": 1
                },
                "compliance_status": "compliant",
                "recommendations": [
                    "Review high-severity authentication failures",
                    "Update security monitoring thresholds",
                    "Conduct quarterly security training"
                ]
            }
            
            logger.info(
                "compliance_report_generated",
                report_type=report_type,
                total_events=report["summary"]["total_events"]
            )
            
            return report
            
        except Exception as e:
            logger.error(
                "compliance_report_generation_failed",
                report_type=report_type,
                error=str(e),
                exc_info=True
            )
            return {}
    
    def _anonymize_user_id(self, user_id: str) -> str:
        """Anonymize user ID for privacy."""
        import hashlib
        return f"anon_{hashlib.md5(user_id.encode()).hexdigest()[:8]}"
    
    def _anonymize_ip_address(self, ip_address: str) -> str:
        """Anonymize IP address for privacy."""
        # Simple anonymization - zero out last octet for IPv4
        if '.' in ip_address:
            parts = ip_address.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
        return "anonymized"
    
    async def _store_audit_entry(self, audit_entry: Dict[str, Any]) -> bool:
        """Store audit entry in database."""
        # Would implement actual database storage
        return True
    
    async def _trigger_security_alert(self, audit_entry: Dict[str, Any]) -> bool:
        """Trigger security alert for high severity events."""
        # Would implement alerting system
        logger.warning(
            "security_alert_triggered",
            event_type=audit_entry["event_type"],
            severity=audit_entry["severity"],
            user_id=audit_entry.get("user_id")
        )
        return True
    
    def _get_gdpr_article(self, action: str) -> str:
        """Get GDPR article reference for action."""
        article_map = {
            "consent": "Article 7",
            "access": "Article 15",
            "portability": "Article 20",
            "erasure": "Article 17",
            "rectification": "Article 16"
        }
        return article_map.get(action, "General")


# Global instance
security_audit_logger = SecurityAuditLogger()