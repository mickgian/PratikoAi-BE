"""Tests for GDPR compliance functionality."""

import pytest
from datetime import datetime, timedelta
from app.core.privacy.gdpr import (
    GDPRCompliance, ConsentManager, DataProcessor, AuditLogger,
    ConsentType, ProcessingPurpose, DataCategory, gdpr_compliance
)


class TestConsentManager:
    """Test cases for consent management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.consent_manager = ConsentManager()

    def test_grant_consent(self):
        """Test granting consent."""
        user_id = "test_user_123"
        consent_id = self.consent_manager.grant_consent(
            user_id=user_id,
            consent_type=ConsentType.FUNCTIONAL,
            ip_address="192.168.1.1"
        )
        
        assert consent_id is not None
        assert self.consent_manager.has_valid_consent(user_id, ConsentType.FUNCTIONAL)

    def test_withdraw_consent(self):
        """Test withdrawing consent."""
        user_id = "test_user_123"
        
        # First grant consent
        self.consent_manager.grant_consent(user_id, ConsentType.ANALYTICAL)
        assert self.consent_manager.has_valid_consent(user_id, ConsentType.ANALYTICAL)
        
        # Then withdraw it
        success = self.consent_manager.withdraw_consent(user_id, ConsentType.ANALYTICAL)
        assert success
        assert not self.consent_manager.has_valid_consent(user_id, ConsentType.ANALYTICAL)

    def test_necessary_consent_always_granted(self):
        """Test that necessary consent is always considered granted."""
        user_id = "new_user_456"
        
        # Even without explicit consent, necessary should be granted
        assert self.consent_manager.has_valid_consent(user_id, ConsentType.NECESSARY)

    def test_consent_expiry(self):
        """Test consent expiration."""
        user_id = "test_user_123"
        
        # Grant consent with short expiry
        self.consent_manager.grant_consent(
            user_id=user_id,
            consent_type=ConsentType.MARKETING,
            expiry_days=0  # Expires immediately
        )
        
        # Should expire after cleanup
        expired_count = self.consent_manager.cleanup_expired_consents()
        assert not self.consent_manager.has_valid_consent(user_id, ConsentType.MARKETING)

    def test_consent_history(self):
        """Test consent history tracking."""
        user_id = "test_user_123"
        
        # Grant, withdraw, grant again
        self.consent_manager.grant_consent(user_id, ConsentType.PERSONALIZATION)
        self.consent_manager.withdraw_consent(user_id, ConsentType.PERSONALIZATION)
        self.consent_manager.grant_consent(user_id, ConsentType.PERSONALIZATION)
        
        history = self.consent_manager.get_consent_history(user_id)
        assert len(history) >= 2  # At least the granted consents
        
        # Should have both granted and withdrawn records
        personalization_records = [
            r for r in history 
            if r.consent_type == ConsentType.PERSONALIZATION
        ]
        assert len(personalization_records) >= 2

    def test_replace_existing_consent(self):
        """Test that new consent replaces existing consent of same type."""
        user_id = "test_user_123"
        
        # Grant consent twice
        consent_id1 = self.consent_manager.grant_consent(user_id, ConsentType.FUNCTIONAL)
        consent_id2 = self.consent_manager.grant_consent(user_id, ConsentType.FUNCTIONAL)
        
        assert consent_id1 != consent_id2
        
        # Should still have valid consent
        assert self.consent_manager.has_valid_consent(user_id, ConsentType.FUNCTIONAL)
        
        # History should show the replacement
        history = self.consent_manager.get_consent_history(user_id)
        functional_records = [
            r for r in history 
            if r.consent_type == ConsentType.FUNCTIONAL
        ]
        assert len(functional_records) >= 2  # Original + replacement


class TestDataProcessor:
    """Test cases for data processing management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.consent_manager = ConsentManager()
        self.data_processor = DataProcessor(self.consent_manager)

    def test_can_process_with_consent(self):
        """Test data processing allowed with proper consent."""
        user_id = "test_user_123"
        
        # Grant functional consent
        self.consent_manager.grant_consent(user_id, ConsentType.FUNCTIONAL)
        
        # Should be able to process for legitimate interest
        can_process = self.data_processor.can_process_data(
            user_id=user_id,
            data_category=DataCategory.BEHAVIORAL,
            processing_purpose=ProcessingPurpose.LEGITIMATE_INTEREST
        )
        assert can_process

    def test_cannot_process_without_consent(self):
        """Test data processing blocked without proper consent."""
        user_id = "test_user_no_consent"
        
        # Should not be able to process for consent-required purpose
        can_process = self.data_processor.can_process_data(
            user_id=user_id,
            data_category=DataCategory.BEHAVIORAL,
            processing_purpose=ProcessingPurpose.CONSENT
        )
        assert not can_process

    def test_always_can_process_necessary(self):
        """Test that necessary processing is always allowed."""
        user_id = "any_user"
        
        # Service provision should always be allowed
        can_process = self.data_processor.can_process_data(
            user_id=user_id,
            data_category=DataCategory.IDENTITY,
            processing_purpose=ProcessingPurpose.SERVICE_PROVISION
        )
        assert can_process

    def test_record_processing(self):
        """Test recording of processing activities."""
        user_id = "test_user_123"
        
        processing_id = self.data_processor.record_processing(
            user_id=user_id,
            data_category=DataCategory.CONTACT,
            processing_purpose=ProcessingPurpose.SERVICE_PROVISION,
            data_source="user_registration",
            legal_basis="Contract performance",
            anonymized=False
        )
        
        assert processing_id is not None
        
        # Should be in user's processing records
        records = self.data_processor.get_user_processing_records(user_id)
        assert len(records) == 1
        assert records[0].processing_id == processing_id

    def test_retention_periods(self):
        """Test data retention period policies."""
        # Different categories should have different retention periods
        identity_retention = self.data_processor.get_retention_period(DataCategory.IDENTITY)
        technical_retention = self.data_processor.get_retention_period(DataCategory.TECHNICAL)
        
        assert identity_retention != technical_retention
        assert identity_retention > technical_retention  # Identity data kept longer

    def test_should_delete_data(self):
        """Test data deletion based on retention policy."""
        user_id = "test_user_123"
        
        # Create a processing record
        processing_id = self.data_processor.record_processing(
            user_id=user_id,
            data_category=DataCategory.TECHNICAL,
            processing_purpose=ProcessingPurpose.SERVICE_PROVISION,
            data_source="api_logs",
            legal_basis="Legitimate interest"
        )
        
        records = self.data_processor.get_user_processing_records(user_id)
        record = records[0]
        
        # Should not delete immediately
        assert not self.data_processor.should_delete_data(record)
        
        # Simulate old data by manipulating timestamp
        record.timestamp = datetime.utcnow() - timedelta(days=365)  # 1 year ago
        
        # Should delete if retention period passed
        if record.retention_period and record.retention_period < timedelta(days=365):
            assert self.data_processor.should_delete_data(record)


class TestAuditLogger:
    """Test cases for audit logging."""

    def setup_method(self):
        """Set up test fixtures."""
        self.audit_logger = AuditLogger()

    def test_log_consent_event(self):
        """Test logging consent events."""
        user_id = "test_user_123"
        
        self.audit_logger.log_consent_event(
            user_id=user_id,
            event_type="consent_granted",
            details={"consent_type": "functional"},
            ip_address="192.168.1.1"
        )
        
        events = self.audit_logger.get_audit_trail(user_id=user_id)
        assert len(events) == 1
        assert events[0].event_type == "consent.consent_granted"
        assert events[0].user_id == user_id

    def test_log_processing_event(self):
        """Test logging processing events."""
        user_id = "test_user_123"
        
        self.audit_logger.log_processing_event(
            user_id=user_id,
            event_type="data_processed",
            details={"data_category": "contact", "purpose": "service_provision"}
        )
        
        events = self.audit_logger.get_audit_trail(user_id=user_id)
        assert len(events) == 1
        assert events[0].event_type == "processing.data_processed"

    def test_log_access_event(self):
        """Test logging access events."""
        self.audit_logger.log_access_event(
            user_id=None,  # System access
            event_type="unauthorized_access_attempt",
            details={"endpoint": "/admin", "reason": "insufficient_permissions"},
            ip_address="192.168.1.100"
        )
        
        events = self.audit_logger.get_audit_trail()
        access_events = [e for e in events if e.event_type.startswith("access.")]
        assert len(access_events) == 1

    def test_audit_trail_filtering(self):
        """Test audit trail filtering capabilities."""
        user1 = "user_1"
        user2 = "user_2"
        
        # Log events for different users
        self.audit_logger.log_consent_event(user1, "consent_granted", {"type": "functional"})
        self.audit_logger.log_consent_event(user2, "consent_withdrawn", {"type": "marketing"})
        self.audit_logger.log_processing_event(user1, "data_accessed", {"category": "contact"})
        
        # Filter by user
        user1_events = self.audit_logger.get_audit_trail(user_id=user1)
        assert len(user1_events) == 2
        assert all(e.user_id == user1 for e in user1_events)
        
        user2_events = self.audit_logger.get_audit_trail(user_id=user2)
        assert len(user2_events) == 1
        assert user2_events[0].user_id == user2
        
        # Filter by event type
        consent_events = self.audit_logger.get_audit_trail(event_type="consent.consent_granted")
        assert len(consent_events) == 1

    def test_export_audit_log(self):
        """Test audit log export."""
        user_id = "test_user_123"
        
        self.audit_logger.log_consent_event(
            user_id=user_id,
            event_type="consent_granted",
            details={"consent_type": "functional"}
        )
        
        # Export as JSON
        json_export = self.audit_logger.export_audit_log(format="json", user_id=user_id)
        assert json_export is not None
        assert user_id in json_export
        assert "consent_granted" in json_export
        
        # Test unsupported format
        with pytest.raises(ValueError):
            self.audit_logger.export_audit_log(format="xml")


class TestGDPRCompliance:
    """Test cases for overall GDPR compliance."""

    def setup_method(self):
        """Set up test fixtures."""
        self.gdpr = GDPRCompliance()

    def test_data_subject_access_request(self):
        """Test data subject access request handling."""
        user_id = "test_user_123"
        
        # Grant some consent and record processing
        self.gdpr.consent_manager.grant_consent(user_id, ConsentType.FUNCTIONAL)
        self.gdpr.data_processor.record_processing(
            user_id=user_id,
            data_category=DataCategory.CONTACT,
            processing_purpose=ProcessingPurpose.SERVICE_PROVISION,
            data_source="user_input",
            legal_basis="Contract"
        )
        
        # Request access to data
        response = self.gdpr.handle_data_subject_request(
            user_id=user_id,
            request_type="access",
            ip_address="192.168.1.1"
        )
        
        assert response["user_id"] == user_id
        assert "consent_records" in response
        assert "processing_records" in response
        assert len(response["consent_records"]) > 0
        assert len(response["processing_records"]) > 0

    def test_data_subject_deletion_request(self):
        """Test data subject deletion request handling."""
        user_id = "test_user_123"
        
        response = self.gdpr.handle_data_subject_request(
            user_id=user_id,
            request_type="deletion",
            ip_address="192.168.1.1"
        )
        
        assert response["user_id"] == user_id
        assert response["status"] == "deletion_request_received"
        assert "30 days" in response["message"]

    def test_data_subject_portability_request(self):
        """Test data portability request handling."""
        user_id = "test_user_123"
        
        response = self.gdpr.handle_data_subject_request(
            user_id=user_id,
            request_type="portability",
            ip_address="192.168.1.1"
        )
        
        assert response["user_id"] == user_id
        assert response["status"] == "portability_request_received"

    def test_unsupported_request_type(self):
        """Test handling of unsupported request types."""
        user_id = "test_user_123"
        
        with pytest.raises(ValueError):
            self.gdpr.handle_data_subject_request(
                user_id=user_id,
                request_type="unsupported_type"
            )

    def test_periodic_cleanup(self):
        """Test periodic cleanup of expired data."""
        user_id = "test_user_123"
        
        # Grant consent with immediate expiry
        self.gdpr.consent_manager.grant_consent(
            user_id=user_id,
            consent_type=ConsentType.MARKETING,
            expiry_days=0
        )
        
        # Run cleanup
        cleanup_result = self.gdpr.periodic_cleanup()
        
        assert "expired_consents_cleaned" in cleanup_result
        assert cleanup_result["expired_consents_cleaned"] >= 0

    def test_compliance_status(self):
        """Test compliance status reporting."""
        # Add some data
        user_id = "test_user_123"
        self.gdpr.consent_manager.grant_consent(user_id, ConsentType.FUNCTIONAL)
        self.gdpr.data_processor.record_processing(
            user_id=user_id,
            data_category=DataCategory.TECHNICAL,
            processing_purpose=ProcessingPurpose.LEGITIMATE_INTEREST,
            data_source="api",
            legal_basis="Legitimate interest"
        )
        
        status = self.gdpr.get_compliance_status()
        
        assert "consent_records_count" in status
        assert "processing_records_count" in status
        assert "audit_events_count" in status
        assert "retention_policies" in status
        assert "compliance_features" in status
        
        assert status["consent_records_count"] > 0
        assert status["processing_records_count"] > 0
        assert len(status["compliance_features"]) > 0


class TestGlobalGDPRInstance:
    """Test the global GDPR compliance instance."""

    def test_global_instance_available(self):
        """Test that global GDPR instance is available."""
        assert gdpr_compliance is not None
        assert isinstance(gdpr_compliance, GDPRCompliance)

    def test_global_instance_components(self):
        """Test that global instance has all components."""
        assert gdpr_compliance.consent_manager is not None
        assert gdpr_compliance.data_processor is not None
        assert gdpr_compliance.audit_logger is not None

    def test_global_instance_functionality(self):
        """Test basic functionality of global instance."""
        user_id = "global_test_user"
        
        # Grant consent through global instance
        consent_id = gdpr_compliance.consent_manager.grant_consent(
            user_id=user_id,
            consent_type=ConsentType.FUNCTIONAL
        )
        
        assert consent_id is not None
        assert gdpr_compliance.consent_manager.has_valid_consent(
            user_id, ConsentType.FUNCTIONAL
        )