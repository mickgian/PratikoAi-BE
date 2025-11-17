"""GDPR compliance utilities and data processing controls.

This module provides comprehensive GDPR compliance features including
consent management, data processing tracking, and audit logging.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from uuid import uuid4

from app.core.config import settings
from app.core.logging import logger


class ConsentType(str, Enum):
    """Types of consent under GDPR."""

    NECESSARY = "necessary"  # Strictly necessary for service
    FUNCTIONAL = "functional"  # Enhances functionality
    ANALYTICAL = "analytical"  # Analytics and performance
    MARKETING = "marketing"  # Marketing and advertising
    PERSONALIZATION = "personalization"  # Personalized content


class ProcessingPurpose(str, Enum):
    """Data processing purposes under GDPR."""

    SERVICE_PROVISION = "service_provision"
    LEGAL_COMPLIANCE = "legal_compliance"
    LEGITIMATE_INTEREST = "legitimate_interest"
    CONSENT = "consent"
    CONTRACT_PERFORMANCE = "contract_performance"
    VITAL_INTERESTS = "vital_interests"


class DataCategory(str, Enum):
    """Categories of personal data."""

    IDENTITY = "identity"  # Name, ID numbers
    CONTACT = "contact"  # Email, phone, address
    FINANCIAL = "financial"  # Payment info, tax codes
    BEHAVIORAL = "behavioral"  # Usage patterns, preferences
    TECHNICAL = "technical"  # IP, device info, logs
    CONTENT = "content"  # User-generated content


@dataclass
class ConsentRecord:
    """Record of user consent."""

    user_id: str
    consent_id: str
    consent_type: ConsentType
    granted: bool
    timestamp: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    withdrawal_timestamp: datetime | None = None
    expiry_date: datetime | None = None


@dataclass
class ProcessingRecord:
    """Record of data processing activity."""

    processing_id: str
    user_id: str
    data_category: DataCategory
    processing_purpose: ProcessingPurpose
    timestamp: datetime
    legal_basis: str
    data_source: str
    retention_period: timedelta | None = None
    anonymized: bool = False


@dataclass
class AuditEvent:
    """GDPR audit event."""

    event_id: str
    event_type: str
    user_id: str | None
    timestamp: datetime
    details: dict[str, Any]
    ip_address: str | None = None
    session_id: str | None = None


class ConsentManager:
    """Manages user consent under GDPR."""

    def __init__(self):
        """Initialize consent manager."""
        self._consent_records: dict[str, list[ConsentRecord]] = {}
        self._default_expiry_days = 365  # Consent expires after 1 year

    def grant_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        ip_address: str | None = None,
        user_agent: str | None = None,
        expiry_days: int | None = None,
    ) -> str:
        """Grant consent for a specific purpose."""
        consent_id = str(uuid4())
        expiry_days = expiry_days or self._default_expiry_days
        expiry_date = datetime.utcnow() + timedelta(days=expiry_days)

        consent = ConsentRecord(
            user_id=user_id,
            consent_id=consent_id,
            consent_type=consent_type,
            granted=True,
            timestamp=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            expiry_date=expiry_date,
        )

        if user_id not in self._consent_records:
            self._consent_records[user_id] = []

        # Revoke any existing consent of the same type
        self._revoke_existing_consent(user_id, consent_type)

        self._consent_records[user_id].append(consent)

        logger.info(
            "gdpr_consent_granted",
            user_id=user_id,
            consent_id=consent_id,
            consent_type=consent_type.value,
            expiry_date=expiry_date.isoformat(),
            ip_address=ip_address,
        )

        return consent_id

    def withdraw_consent(self, user_id: str, consent_type: ConsentType, ip_address: str | None = None) -> bool:
        """Withdraw consent for a specific purpose."""
        if user_id not in self._consent_records:
            return False

        for consent in self._consent_records[user_id]:
            if consent.consent_type == consent_type and consent.granted and not consent.withdrawal_timestamp:
                consent.withdrawal_timestamp = datetime.utcnow()
                consent.granted = False

                logger.info(
                    "gdpr_consent_withdrawn",
                    user_id=user_id,
                    consent_id=consent.consent_id,
                    consent_type=consent_type.value,
                    withdrawal_timestamp=consent.withdrawal_timestamp.isoformat(),
                    ip_address=ip_address,
                )

                return True

        return False

    def has_valid_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """Check if user has valid consent for a specific purpose."""
        if user_id not in self._consent_records:
            # Necessary consent is assumed for basic service operation
            return consent_type == ConsentType.NECESSARY

        now = datetime.utcnow()

        for consent in self._consent_records[user_id]:
            if (
                consent.consent_type == consent_type
                and consent.granted
                and not consent.withdrawal_timestamp
                and (not consent.expiry_date or consent.expiry_date > now)
            ):
                return True

        # Necessary consent is always granted
        return consent_type == ConsentType.NECESSARY

    def get_consent_history(self, user_id: str) -> list[ConsentRecord]:
        """Get consent history for a user."""
        return self._consent_records.get(user_id, [])

    def cleanup_expired_consents(self) -> int:
        """Clean up expired consent records."""
        now = datetime.utcnow()
        cleaned_count = 0

        for user_id in self._consent_records:
            user_consents = self._consent_records[user_id]
            expired_consents = [c for c in user_consents if c.expiry_date and c.expiry_date <= now and c.granted]

            for consent in expired_consents:
                consent.granted = False
                consent.withdrawal_timestamp = now
                cleaned_count += 1

        if cleaned_count > 0:
            logger.info("gdpr_expired_consents_cleaned", count=cleaned_count)

        return cleaned_count

    def _revoke_existing_consent(self, user_id: str, consent_type: ConsentType):
        """Revoke existing consent of the same type."""
        for consent in self._consent_records.get(user_id, []):
            if consent.consent_type == consent_type and consent.granted and not consent.withdrawal_timestamp:
                consent.granted = False
                consent.withdrawal_timestamp = datetime.utcnow()


class DataProcessor:
    """Manages data processing under GDPR."""

    def __init__(self, consent_manager: ConsentManager):
        """Initialize data processor."""
        self.consent_manager = consent_manager
        self._processing_records: list[ProcessingRecord] = []
        self._retention_policies: dict[DataCategory, timedelta] = {
            DataCategory.IDENTITY: timedelta(days=2555),  # 7 years for tax purposes
            DataCategory.CONTACT: timedelta(days=365),  # 1 year
            DataCategory.FINANCIAL: timedelta(days=2555),  # 7 years for tax purposes
            DataCategory.BEHAVIORAL: timedelta(days=90),  # 3 months
            DataCategory.TECHNICAL: timedelta(days=30),  # 1 month
            DataCategory.CONTENT: timedelta(days=365),  # 1 year
        }

    def can_process_data(
        self, user_id: str, data_category: DataCategory, processing_purpose: ProcessingPurpose
    ) -> bool:
        """Check if data processing is allowed under GDPR."""
        # Map processing purposes to consent types
        purpose_consent_map = {
            ProcessingPurpose.SERVICE_PROVISION: ConsentType.NECESSARY,
            ProcessingPurpose.LEGAL_COMPLIANCE: ConsentType.NECESSARY,
            ProcessingPurpose.LEGITIMATE_INTEREST: ConsentType.FUNCTIONAL,
            ProcessingPurpose.CONSENT: ConsentType.FUNCTIONAL,
            ProcessingPurpose.CONTRACT_PERFORMANCE: ConsentType.NECESSARY,
            ProcessingPurpose.VITAL_INTERESTS: ConsentType.NECESSARY,
        }

        required_consent = purpose_consent_map.get(processing_purpose, ConsentType.FUNCTIONAL)

        # Check if user has granted the required consent
        has_consent = self.consent_manager.has_valid_consent(user_id, required_consent)

        logger.debug(
            "gdpr_processing_check",
            user_id=user_id,
            data_category=data_category.value,
            processing_purpose=processing_purpose.value,
            required_consent=required_consent.value,
            has_consent=has_consent,
        )

        return has_consent

    def record_processing(
        self,
        user_id: str,
        data_category: DataCategory,
        processing_purpose: ProcessingPurpose,
        data_source: str,
        legal_basis: str,
        anonymized: bool = False,
    ) -> str:
        """Record a data processing activity."""
        processing_id = str(uuid4())
        retention_period = self._retention_policies.get(data_category)

        record = ProcessingRecord(
            processing_id=processing_id,
            user_id=user_id,
            data_category=data_category,
            processing_purpose=processing_purpose,
            timestamp=datetime.utcnow(),
            legal_basis=legal_basis,
            data_source=data_source,
            retention_period=retention_period,
            anonymized=anonymized,
        )

        self._processing_records.append(record)

        logger.info(
            "gdpr_processing_recorded",
            processing_id=processing_id,
            user_id=user_id,
            data_category=data_category.value,
            processing_purpose=processing_purpose.value,
            legal_basis=legal_basis,
            anonymized=anonymized,
        )

        return processing_id

    def get_user_processing_records(self, user_id: str) -> list[ProcessingRecord]:
        """Get all processing records for a user."""
        return [r for r in self._processing_records if r.user_id == user_id]

    def get_retention_period(self, data_category: DataCategory) -> timedelta | None:
        """Get retention period for a data category."""
        return self._retention_policies.get(data_category)

    def should_delete_data(self, record: ProcessingRecord) -> bool:
        """Check if data should be deleted based on retention policy."""
        if not record.retention_period:
            return False

        expiry_date = record.timestamp + record.retention_period
        return datetime.utcnow() > expiry_date


class AuditLogger:
    """Logs GDPR-related events for compliance auditing."""

    def __init__(self):
        """Initialize audit logger."""
        self._audit_events: list[AuditEvent] = []

    def log_consent_event(
        self,
        user_id: str,
        event_type: str,
        details: dict[str, Any],
        ip_address: str | None = None,
        session_id: str | None = None,
    ):
        """Log a consent-related event."""
        self._log_event("consent", user_id, event_type, details, ip_address, session_id)

    def log_processing_event(
        self,
        user_id: str,
        event_type: str,
        details: dict[str, Any],
        ip_address: str | None = None,
        session_id: str | None = None,
    ):
        """Log a data processing event."""
        self._log_event("processing", user_id, event_type, details, ip_address, session_id)

    def log_access_event(
        self,
        user_id: str | None,
        event_type: str,
        details: dict[str, Any],
        ip_address: str | None = None,
        session_id: str | None = None,
    ):
        """Log a data access event."""
        self._log_event("access", user_id, event_type, details, ip_address, session_id)

    def log_deletion_event(
        self,
        user_id: str,
        event_type: str,
        details: dict[str, Any],
        ip_address: str | None = None,
        session_id: str | None = None,
    ):
        """Log a data deletion event."""
        self._log_event("deletion", user_id, event_type, details, ip_address, session_id)

    def _log_event(
        self,
        category: str,
        user_id: str | None,
        event_type: str,
        details: dict[str, Any],
        ip_address: str | None = None,
        session_id: str | None = None,
    ):
        """Log a GDPR audit event."""
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=f"{category}.{event_type}",
            user_id=user_id,
            timestamp=datetime.utcnow(),
            details=details,
            ip_address=ip_address,
            session_id=session_id,
        )

        self._audit_events.append(event)

        # Also log to structured logging
        logger.info(
            "gdpr_audit_event",
            event_id=event.event_id,
            event_type=event.event_type,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
            session_id=session_id,
        )

    def get_audit_trail(
        self,
        user_id: str | None = None,
        event_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[AuditEvent]:
        """Get audit trail with optional filters."""
        events = self._audit_events

        if user_id:
            events = [e for e in events if e.user_id == user_id]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if start_date:
            events = [e for e in events if e.timestamp >= start_date]

        if end_date:
            events = [e for e in events if e.timestamp <= end_date]

        return sorted(events, key=lambda e: e.timestamp, reverse=True)

    def export_audit_log(self, format: str = "json", user_id: str | None = None) -> str:
        """Export audit log in specified format."""
        events = self.get_audit_trail(user_id=user_id)

        if format == "json":
            return json.dumps(
                [
                    {
                        "event_id": e.event_id,
                        "event_type": e.event_type,
                        "user_id": e.user_id,
                        "timestamp": e.timestamp.isoformat(),
                        "details": e.details,
                        "ip_address": e.ip_address,
                        "session_id": e.session_id,
                    }
                    for e in events
                ],
                indent=2,
            )

        # Add other formats as needed
        raise ValueError(f"Unsupported export format: {format}")


class GDPRCompliance:
    """Main GDPR compliance coordinator."""

    def __init__(self):
        """Initialize GDPR compliance system."""
        self.consent_manager = ConsentManager()
        self.data_processor = DataProcessor(self.consent_manager)
        self.audit_logger = AuditLogger()

    def handle_data_subject_request(
        self, user_id: str, request_type: str, ip_address: str | None = None, session_id: str | None = None
    ) -> dict[str, Any]:
        """Handle data subject requests under GDPR (Article 15-22)."""
        if request_type == "access":
            # Right of access (Article 15)
            consent_history = self.consent_manager.get_consent_history(user_id)
            processing_records = self.data_processor.get_user_processing_records(user_id)
            audit_trail = self.audit_logger.get_audit_trail(user_id=user_id)

            self.audit_logger.log_access_event(
                user_id=user_id,
                event_type="data_access_request",
                details={"request_type": request_type},
                ip_address=ip_address,
                session_id=session_id,
            )

            return {
                "user_id": user_id,
                "consent_records": [
                    {
                        "consent_type": c.consent_type.value,
                        "granted": c.granted,
                        "timestamp": c.timestamp.isoformat(),
                        "withdrawal_timestamp": c.withdrawal_timestamp.isoformat() if c.withdrawal_timestamp else None,
                        "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
                    }
                    for c in consent_history
                ],
                "processing_records": [
                    {
                        "data_category": p.data_category.value,
                        "processing_purpose": p.processing_purpose.value,
                        "timestamp": p.timestamp.isoformat(),
                        "legal_basis": p.legal_basis,
                        "data_source": p.data_source,
                        "anonymized": p.anonymized,
                    }
                    for p in processing_records
                ],
                "audit_events_count": len(audit_trail),
            }

        elif request_type == "deletion":
            # Right to erasure (Article 17)
            self.audit_logger.log_deletion_event(
                user_id=user_id,
                event_type="data_deletion_request",
                details={"request_type": request_type},
                ip_address=ip_address,
                session_id=session_id,
            )

            # This would trigger actual data deletion in the real system
            return {
                "user_id": user_id,
                "status": "deletion_request_received",
                "message": "Data deletion will be processed within 30 days as required by GDPR",
            }

        elif request_type == "portability":
            # Right to data portability (Article 20)
            self.audit_logger.log_access_event(
                user_id=user_id,
                event_type="data_portability_request",
                details={"request_type": request_type},
                ip_address=ip_address,
                session_id=session_id,
            )

            return {
                "user_id": user_id,
                "status": "portability_request_received",
                "message": "Data export will be provided in machine-readable format within 30 days",
            }

        else:
            raise ValueError(f"Unsupported data subject request type: {request_type}")

    def periodic_cleanup(self) -> dict[str, int]:
        """Perform periodic cleanup of expired data and consents."""
        expired_consents = self.consent_manager.cleanup_expired_consents()

        # This would also clean up expired data based on retention policies
        # For now, just log the action
        self.audit_logger.log_processing_event(
            user_id=None,
            event_type="periodic_cleanup",
            details={"expired_consents_cleaned": expired_consents, "cleanup_timestamp": datetime.utcnow().isoformat()},
        )

        return {
            "expired_consents_cleaned": expired_consents,
            "data_records_cleaned": 0,  # Would be implemented in real system
        }

    def get_compliance_status(self) -> dict[str, Any]:
        """Get overall GDPR compliance status."""
        return {
            "consent_records_count": sum(len(consents) for consents in self.consent_manager._consent_records.values()),
            "processing_records_count": len(self.data_processor._processing_records),
            "audit_events_count": len(self.audit_logger._audit_events),
            "retention_policies": {
                category.value: str(period) for category, period in self.data_processor._retention_policies.items()
            },
            "compliance_features": [
                "consent_management",
                "data_processing_tracking",
                "audit_logging",
                "data_subject_requests",
                "automatic_cleanup",
                "pii_anonymization",
            ],
        }


# Global GDPR compliance instance
gdpr_compliance = GDPRCompliance()
