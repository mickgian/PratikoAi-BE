"""
Comprehensive Test Suite for GDPR Data Deletion Functionality.

This test suite follows Test-Driven Development (TDD) methodology to ensure
complete compliance with GDPR Article 17 "Right to be forgotten" requirements.
Tests must pass before implementation begins.

Test Coverage:
- Complete user data deletion from all tables
- 30-day deadline tracking and automatic execution
- Cascading deletion of related records
- Audit trail preservation during deletion
- Deletion from all systems (PostgreSQL, Redis, backups, logs, third-party services)
- Deletion verification and certificate generation
- Compliance reporting for GDPR deletions
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func

from app.services.gdpr_deletion_service import (
    GDPRDeletionService,
    DeletionRequest,
    DeletionStatus,
    DeletionPriority,
    DeletionResult,
    UserDataDeletor,
    DeletionVerifier
)
from app.models.encrypted_user import EncryptedUser
from app.models.session import Session
from app.core.config import get_settings


class TestGDPRDeletionRequest:
    """Test GDPR deletion request creation and validation."""
    
    @pytest.mark.asyncio
    async def test_create_deletion_request_user_initiated(self, db_session: AsyncSession):
        """Test user-initiated deletion request creation."""
        gdpr_service = GDPRDeletionService(db_session)
        
        # Create test user
        user = EncryptedUser(
            email="mario.rossi@example.com",
            hashed_password="test_hash",
            tax_id="RSSMRA80A01H501U",
            full_name="Mario Rossi"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create deletion request
        request = await gdpr_service.create_deletion_request(
            user_id=user.id,
            initiated_by_user=True,
            reason="User requested account deletion"
        )
        
        assert request.user_id == user.id
        assert request.status == DeletionStatus.PENDING
        assert request.initiated_by_user == True
        assert request.deletion_deadline <= datetime.now(timezone.utc) + timedelta(days=30)
        assert request.reason == "User requested account deletion"
        assert request.request_id is not None
    
    @pytest.mark.asyncio
    async def test_create_deletion_request_admin_initiated(self, db_session: AsyncSession):
        """Test admin-initiated deletion request creation."""
        gdpr_service = GDPRDeletionService(db_session)
        
        # Create test user
        user = EncryptedUser(
            email="inactive.user@example.com",
            hashed_password="test_hash",
            is_active=False
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create admin deletion request
        request = await gdpr_service.create_deletion_request(
            user_id=user.id,
            initiated_by_user=False,
            reason="Account inactive for 2 years - automated cleanup",
            admin_user_id=1,
            priority=DeletionPriority.LOW
        )
        
        assert request.initiated_by_user == False
        assert request.admin_user_id == 1
        assert request.priority == DeletionPriority.LOW
        assert "automated cleanup" in request.reason
    
    @pytest.mark.asyncio
    async def test_deletion_request_validation_nonexistent_user(self, db_session: AsyncSession):
        """Test deletion request validation for non-existent user."""
        gdpr_service = GDPRDeletionService(db_session)
        
        with pytest.raises(ValueError, match="User with ID 99999 does not exist"):
            await gdpr_service.create_deletion_request(
                user_id=99999,
                initiated_by_user=True,
                reason="Test"
            )
    
    @pytest.mark.asyncio
    async def test_deletion_request_validation_already_pending(self, db_session: AsyncSession):
        """Test validation prevents duplicate deletion requests."""
        gdpr_service = GDPRDeletionService(db_session)
        
        # Create test user
        user = EncryptedUser(
            email="duplicate.test@example.com",
            hashed_password="test_hash"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create first deletion request
        await gdpr_service.create_deletion_request(
            user_id=user.id,
            initiated_by_user=True,
            reason="First request"
        )
        
        # Attempt to create duplicate request
        with pytest.raises(ValueError, match="Deletion request already exists"):
            await gdpr_service.create_deletion_request(
                user_id=user.id,
                initiated_by_user=True,
                reason="Duplicate request"
            )


class TestGDPRDeletionScheduling:
    """Test GDPR deletion deadline tracking and scheduling."""
    
    @pytest.mark.asyncio
    async def test_deletion_deadline_calculation(self, db_session: AsyncSession):
        """Test deletion deadline is correctly calculated (30 days)."""
        gdpr_service = GDPRDeletionService(db_session)
        
        # Create test user
        user = EncryptedUser(
            email="deadline.test@example.com",
            hashed_password="test_hash"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        request_time = datetime.now(timezone.utc)
        request = await gdpr_service.create_deletion_request(
            user_id=user.id,
            initiated_by_user=True,
            reason="Test deadline calculation"
        )
        
        expected_deadline = request_time + timedelta(days=30)
        time_diff = abs((request.deletion_deadline - expected_deadline).total_seconds())
        
        # Allow for small timing differences (within 60 seconds)
        assert time_diff < 60
    
    @pytest.mark.asyncio
    async def test_get_overdue_deletion_requests(self, db_session: AsyncSession):
        """Test identification of overdue deletion requests."""
        gdpr_service = GDPRDeletionService(db_session)
        
        # Create test users
        user1 = EncryptedUser(email="overdue1@example.com", hashed_password="test_hash")
        user2 = EncryptedUser(email="overdue2@example.com", hashed_password="test_hash")
        user3 = EncryptedUser(email="notdue@example.com", hashed_password="test_hash")
        
        db_session.add_all([user1, user2, user3])
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)
        await db_session.refresh(user3)
        
        # Create overdue requests (simulate past deadline)
        overdue_deadline = datetime.now(timezone.utc) - timedelta(days=1)
        future_deadline = datetime.now(timezone.utc) + timedelta(days=29)
        
        request1 = await gdpr_service.create_deletion_request(
            user_id=user1.id,
            initiated_by_user=True,
            reason="Overdue test 1"
        )
        request1.deletion_deadline = overdue_deadline
        
        request2 = await gdpr_service.create_deletion_request(
            user_id=user2.id,
            initiated_by_user=True,
            reason="Overdue test 2"
        )
        request2.deletion_deadline = overdue_deadline
        
        request3 = await gdpr_service.create_deletion_request(
            user_id=user3.id,
            initiated_by_user=True,
            reason="Not due yet"
        )
        request3.deletion_deadline = future_deadline
        
        await db_session.commit()
        
        # Get overdue requests
        overdue_requests = await gdpr_service.get_overdue_deletion_requests()
        
        assert len(overdue_requests) == 2
        overdue_user_ids = [req.user_id for req in overdue_requests]
        assert user1.id in overdue_user_ids
        assert user2.id in overdue_user_ids
        assert user3.id not in overdue_user_ids
    
    @pytest.mark.asyncio
    async def test_automatic_deletion_execution(self, db_session: AsyncSession):
        """Test automatic execution of overdue deletion requests."""
        gdpr_service = GDPRDeletionService(db_session)
        
        # Create test user with data
        user = EncryptedUser(
            email="auto.delete@example.com",
            hashed_password="test_hash",
            tax_id="TSTUSR80A01H501U",
            full_name="Auto Delete User"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create overdue deletion request
        request = await gdpr_service.create_deletion_request(
            user_id=user.id,
            initiated_by_user=True,
            reason="Automatic deletion test"
        )
        request.deletion_deadline = datetime.now(timezone.utc) - timedelta(days=1)
        await db_session.commit()
        
        # Execute automatic deletions
        results = await gdpr_service.execute_overdue_deletions()
        
        assert len(results) == 1
        result = results[0]
        assert result.success == True
        assert result.user_id == user.id
        assert result.total_records_deleted > 0
        
        # Verify request status updated
        await db_session.refresh(request)
        assert request.status == DeletionStatus.COMPLETED


class TestUserDataIdentification:
    """Test comprehensive user data identification across all tables."""
    
    @pytest.mark.asyncio
    async def test_identify_user_data_in_all_tables(self, db_session: AsyncSession):
        """Test identification of user data across all database tables."""
        data_deletor = UserDataDeletor(db_session)
        
        # Create test user with comprehensive data
        user = EncryptedUser(
            email="comprehensive.user@example.com",
            hashed_password="test_hash",
            tax_id="CMPUSR80A01H501U",
            full_name="Comprehensive User",
            phone="+39 123 456 7890",
            address="Via Roma 123, Milano"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create related data (sessions, query logs, etc.)
        session = Session(
            user_id=user.id,
            session_token="test_session_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        db_session.add(session)
        await db_session.commit()
        
        # Identify all user data
        user_data_map = await data_deletor.identify_user_data(user.id)
        
        assert "users" in user_data_map
        assert len(user_data_map["users"]) == 1
        assert user_data_map["users"][0]["id"] == user.id
        
        assert "sessions" in user_data_map
        assert len(user_data_map["sessions"]) == 1
        assert user_data_map["sessions"][0]["user_id"] == user.id
        
        # Verify comprehensive data identification
        total_records = sum(len(records) for records in user_data_map.values())
        assert total_records >= 2  # At minimum user + session
    
    @pytest.mark.asyncio
    async def test_identify_user_data_encrypted_fields(self, db_session: AsyncSession):
        """Test identification includes encrypted PII fields."""
        data_deletor = UserDataDeletor(db_session)
        
        # Create user with encrypted PII
        user = EncryptedUser(
            email="encrypted.pii@example.com",
            hashed_password="test_hash",
            tax_id="ENCPII80A01H501U",
            full_name="Encrypted PII User",
            phone="+39 987 654 3210"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Identify user data
        user_data_map = await data_deletor.identify_user_data(user.id)
        
        user_record = user_data_map["users"][0]
        
        # Verify encrypted fields are identified
        assert user_record["email"] == "encrypted.pii@example.com"
        assert user_record["tax_id"] == "ENCPII80A01H501U"
        assert user_record["full_name"] == "Encrypted PII User"
        assert user_record["phone"] == "+39 987 654 3210"
    
    @pytest.mark.asyncio
    async def test_identify_cascading_relationships(self, db_session: AsyncSession):
        """Test identification of cascading relationships for deletion."""
        data_deletor = UserDataDeletor(db_session)
        
        # Create user with multiple related records
        user = EncryptedUser(
            email="cascade.test@example.com",
            hashed_password="test_hash"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create multiple sessions
        sessions = []
        for i in range(3):
            session = Session(
                user_id=user.id,
                session_token=f"session_token_{i}",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
            )
            sessions.append(session)
            db_session.add(session)
        
        await db_session.commit()
        
        # Identify cascading data
        user_data_map = await data_deletor.identify_user_data(user.id)
        
        assert len(user_data_map["sessions"]) == 3
        
        # Verify all sessions belong to the user
        for session_data in user_data_map["sessions"]:
            assert session_data["user_id"] == user.id


class TestActualDataDeletion:
    """Test actual deletion of user data with verification."""
    
    @pytest.mark.asyncio
    async def test_delete_user_data_complete_removal(self, db_session: AsyncSession):
        """Test complete removal of user data from all tables."""
        data_deletor = UserDataDeletor(db_session)
        
        # Create comprehensive test data
        user = EncryptedUser(
            email="delete.complete@example.com",
            hashed_password="test_hash",
            tax_id="DELCMP80A01H501U",
            full_name="Delete Complete User"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create related data
        session = Session(
            user_id=user.id,
            session_token="delete_session_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        db_session.add(session)
        await db_session.commit()
        
        # Perform deletion
        deletion_result = await data_deletor.delete_user_data(user.id)
        
        assert deletion_result.success == True
        assert deletion_result.user_id == user.id
        assert deletion_result.total_records_deleted >= 2
        assert len(deletion_result.tables_affected) >= 2
        assert "users" in deletion_result.tables_affected
        assert "sessions" in deletion_result.tables_affected
        
        # Verify data is actually deleted
        user_check = await db_session.get(EncryptedUser, user.id)
        assert user_check is None
        
        session_check = await db_session.execute(
            select(Session).where(Session.user_id == user.id)
        )
        assert session_check.fetchone() is None
    
    @pytest.mark.asyncio
    async def test_delete_user_data_preserves_audit_trail(self, db_session: AsyncSession):
        """Test deletion preserves audit trail while removing PII."""
        data_deletor = UserDataDeletor(db_session)
        
        # Create user
        user = EncryptedUser(
            email="audit.preserve@example.com",
            hashed_password="test_hash",
            tax_id="AUDPRS80A01H501U"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Perform deletion with audit preservation
        deletion_result = await data_deletor.delete_user_data(
            user.id,
            preserve_audit_trail=True
        )
        
        assert deletion_result.success == True
        assert deletion_result.audit_records_preserved > 0
        
        # Verify audit trail exists but PII is anonymized
        audit_check = await db_session.execute(text("""
            SELECT user_id, anonymized_user_id, deletion_timestamp
            FROM gdpr_deletion_audit_log
            WHERE original_user_id = :user_id
        """), {"user_id": user.id})
        
        audit_record = audit_check.fetchone()
        assert audit_record is not None
        assert audit_record[1] is not None  # anonymized_user_id exists
        assert audit_record[2] is not None  # deletion_timestamp exists
    
    @pytest.mark.asyncio
    async def test_delete_user_data_handles_large_datasets(self, db_session: AsyncSession):
        """Test deletion handles large datasets efficiently."""
        data_deletor = UserDataDeletor(db_session)
        
        # Create user with large amount of data
        user = EncryptedUser(
            email="large.dataset@example.com",
            hashed_password="test_hash"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create many related records
        sessions = []
        for i in range(1000):  # Large dataset
            session = Session(
                user_id=user.id,
                session_token=f"large_session_{i}",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
            )
            sessions.append(session)
        
        db_session.add_all(sessions)
        await db_session.commit()
        
        # Perform deletion
        start_time = datetime.now(timezone.utc)
        deletion_result = await data_deletor.delete_user_data(user.id)
        end_time = datetime.now(timezone.utc)
        
        duration_seconds = (end_time - start_time).total_seconds()
        
        assert deletion_result.success == True
        assert deletion_result.total_records_deleted >= 1001  # User + 1000 sessions
        assert duration_seconds < 30  # Should complete within 30 seconds
        
        # Verify efficient deletion (all records removed)
        remaining_sessions = await db_session.execute(
            select(func.count(Session.id)).where(Session.user_id == user.id)
        )
        assert remaining_sessions.scalar() == 0
    
    @pytest.mark.asyncio
    async def test_delete_user_data_error_handling(self, db_session: AsyncSession):
        """Test deletion error handling and rollback."""
        data_deletor = UserDataDeletor(db_session)
        
        # Test deletion of non-existent user
        deletion_result = await data_deletor.delete_user_data(99999)
        
        assert deletion_result.success == False
        assert "User with ID 99999 does not exist" in deletion_result.error_message
        assert deletion_result.total_records_deleted == 0


class TestMultiSystemDeletion:
    """Test deletion from all systems (PostgreSQL, Redis, backups, logs, third-party)."""
    
    @pytest.mark.asyncio
    async def test_delete_from_redis_cache(self, db_session: AsyncSession):
        """Test deletion of user data from Redis cache."""
        data_deletor = UserDataDeletor(db_session)
        
        # Mock Redis client
        with patch('app.services.cache.redis_client') as mock_redis:
            mock_redis.delete = AsyncMock(return_value=5)  # 5 keys deleted
            mock_redis.keys = AsyncMock(return_value=[
                b'user:123:profile',
                b'user:123:sessions',
                b'user:123:preferences',
                b'session:abc123:user:123',
                b'rate_limit:user:123'
            ])
            
            # Perform Redis deletion
            redis_result = await data_deletor.delete_from_redis(user_id=123)
            
            assert redis_result.success == True
            assert redis_result.keys_deleted == 5
            assert redis_result.cache_systems_cleared == ['user_profile', 'sessions', 'rate_limiting']
    
    @pytest.mark.asyncio
    async def test_delete_from_application_logs(self, db_session: AsyncSession):
        """Test deletion of user data from application logs."""
        data_deletor = UserDataDeletor(db_session)
        
        # Mock log anonymization
        with patch('app.services.log_anonymizer') as mock_anonymizer:
            mock_anonymizer.anonymize_user_logs = AsyncMock(return_value={
                'log_files_processed': 15,
                'log_entries_anonymized': 1247,
                'anonymization_method': 'PII_replacement'
            })
            
            # Perform log anonymization
            log_result = await data_deletor.anonymize_application_logs(user_id=123)
            
            assert log_result.success == True
            assert log_result.log_files_processed == 15
            assert log_result.log_entries_anonymized == 1247
    
    @pytest.mark.asyncio
    async def test_delete_from_stripe_integration(self, db_session: AsyncSession):
        """Test deletion of user data from Stripe."""
        data_deletor = UserDataDeletor(db_session)
        
        # Mock Stripe client
        with patch('stripe.Customer.delete') as mock_stripe_delete:
            mock_stripe_delete.return_value = {'deleted': True, 'id': 'cus_test123'}
            
            # Perform Stripe deletion
            stripe_result = await data_deletor.delete_from_stripe(
                stripe_customer_id="cus_test123"
            )
            
            assert stripe_result.success == True
            assert stripe_result.stripe_customer_deleted == True
            assert stripe_result.stripe_customer_id == "cus_test123"
    
    @pytest.mark.asyncio
    async def test_delete_from_backup_systems(self, db_session: AsyncSession):
        """Test deletion/anonymization of user data in backups."""
        data_deletor = UserDataDeletor(db_session)
        
        # Mock backup system integration
        with patch('app.services.backup_manager') as mock_backup:
            mock_backup.anonymize_user_in_backups = AsyncMock(return_value={
                'backup_files_processed': 7,
                'user_records_anonymized': 23,
                'backup_systems': ['daily_backup', 'weekly_backup', 'monthly_backup']
            })
            
            # Perform backup anonymization
            backup_result = await data_deletor.anonymize_in_backups(user_id=123)
            
            assert backup_result.success == True
            assert backup_result.backup_files_processed == 7
            assert backup_result.user_records_anonymized == 23
            assert len(backup_result.backup_systems_processed) == 3


class TestDeletionVerification:
    """Test deletion verification and completeness checking."""
    
    @pytest.mark.asyncio
    async def test_verify_complete_deletion(self, db_session: AsyncSession):
        """Test verification that user data is completely deleted."""
        verifier = DeletionVerifier(db_session)
        
        # Create and delete test user
        user = EncryptedUser(
            email="verify.deletion@example.com",
            hashed_password="test_hash",
            tax_id="VERDEL80A01H501U"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        user_id = user.id
        
        # Delete user
        data_deletor = UserDataDeletor(db_session)
        await data_deletor.delete_user_data(user_id)
        
        # Verify deletion
        verification_result = await verifier.verify_user_deletion(user_id)
        
        assert verification_result.is_completely_deleted == True
        assert verification_result.user_id == user_id
        assert len(verification_result.remaining_data_found) == 0
        assert verification_result.verification_score == 100.0
        assert verification_result.gdpr_compliant == True
    
    @pytest.mark.asyncio
    async def test_verify_deletion_finds_remaining_data(self, db_session: AsyncSession):
        """Test verification detects incomplete deletion."""
        verifier = DeletionVerifier(db_session)
        
        # Create test user (don't delete)
        user = EncryptedUser(
            email="incomplete.deletion@example.com",
            hashed_password="test_hash"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Verify deletion (should find remaining data)
        verification_result = await verifier.verify_user_deletion(user.id)
        
        assert verification_result.is_completely_deleted == False
        assert len(verification_result.remaining_data_found) > 0
        assert verification_result.verification_score < 100.0
        assert verification_result.gdpr_compliant == False
        
        # Check specific remaining data
        assert any(
            data['table'] == 'users' 
            for data in verification_result.remaining_data_found
        )
    
    @pytest.mark.asyncio
    async def test_generate_deletion_certificate(self, db_session: AsyncSession):
        """Test generation of GDPR deletion certificate."""
        verifier = DeletionVerifier(db_session)
        
        # Create verification result
        verification_result = Mock()
        verification_result.user_id = 123
        verification_result.is_completely_deleted = True
        verification_result.verification_score = 100.0
        verification_result.gdpr_compliant = True
        verification_result.verification_timestamp = datetime.now(timezone.utc)
        verification_result.remaining_data_found = []
        
        # Generate certificate
        certificate = await verifier.generate_deletion_certificate(verification_result)
        
        assert certificate.user_id == 123
        assert certificate.is_complete_deletion == True
        assert certificate.certificate_id is not None
        assert certificate.issued_at is not None
        assert certificate.compliance_attestation == True
        assert "data has been successfully deleted" in certificate.certificate_text
    
    @pytest.mark.asyncio
    async def test_verify_multi_system_deletion(self, db_session: AsyncSession):
        """Test verification across multiple systems."""
        verifier = DeletionVerifier(db_session)
        
        # Mock multi-system verification
        with patch.multiple(
            verifier,
            verify_database_deletion=AsyncMock(return_value={'complete': True, 'remaining': 0}),
            verify_redis_deletion=AsyncMock(return_value={'complete': True, 'remaining': 0}),
            verify_log_anonymization=AsyncMock(return_value={'complete': True, 'anonymized': 1500}),
            verify_backup_anonymization=AsyncMock(return_value={'complete': True, 'systems': 3}),
            verify_stripe_deletion=AsyncMock(return_value={'complete': True, 'deleted': True})
        ):
            
            # Perform multi-system verification
            verification_result = await verifier.verify_multi_system_deletion(user_id=123)
            
            assert verification_result.database_deletion_verified == True
            assert verification_result.redis_deletion_verified == True
            assert verification_result.log_anonymization_verified == True
            assert verification_result.backup_anonymization_verified == True
            assert verification_result.stripe_deletion_verified == True
            assert verification_result.overall_verification_passed == True


class TestGDPRComplianceReporting:
    """Test GDPR compliance reporting and metrics."""
    
    @pytest.mark.asyncio
    async def test_generate_deletion_compliance_report(self, db_session: AsyncSession):
        """Test generation of GDPR deletion compliance report."""
        gdpr_service = GDPRDeletionService(db_session)
        
        # Create sample deletion requests for reporting
        for i in range(10):
            user = EncryptedUser(
                email=f"report.user{i}@example.com",
                hashed_password="test_hash"
            )
            db_session.add(user)
            await db_session.commit()
            await db_session.refresh(user)
            
            # Create deletion request
            await gdpr_service.create_deletion_request(
                user_id=user.id,
                initiated_by_user=True if i % 2 == 0 else False,
                reason=f"Test deletion {i}"
            )
        
        # Generate compliance report
        report = await gdpr_service.generate_compliance_report(
            start_date=datetime.now(timezone.utc) - timedelta(days=30),
            end_date=datetime.now(timezone.utc)
        )
        
        assert report.total_deletion_requests == 10
        assert report.user_initiated_requests == 5
        assert report.admin_initiated_requests == 5
        assert report.completed_deletions >= 0
        assert report.pending_deletions <= 10
        assert report.average_completion_time_hours >= 0
        assert report.compliance_score >= 0
        assert report.report_period_days == 30
    
    @pytest.mark.asyncio
    async def test_track_deletion_metrics(self, db_session: AsyncSession):
        """Test tracking of deletion performance metrics."""
        gdpr_service = GDPRDeletionService(db_session)
        
        # Get current metrics
        metrics = await gdpr_service.get_deletion_metrics()
        
        assert metrics.total_requests >= 0
        assert metrics.completed_deletions >= 0
        assert metrics.pending_deletions >= 0
        assert metrics.overdue_deletions >= 0
        assert metrics.average_processing_time_hours >= 0
        assert metrics.compliance_rate >= 0.0
        assert metrics.last_updated is not None
    
    @pytest.mark.asyncio
    async def test_deadline_compliance_monitoring(self, db_session: AsyncSession):
        """Test monitoring of 30-day deadline compliance."""
        gdpr_service = GDPRDeletionService(db_session)
        
        # Create test requests with various deadlines
        user1 = EncryptedUser(email="deadline1@example.com", hashed_password="test")
        user2 = EncryptedUser(email="deadline2@example.com", hashed_password="test")
        user3 = EncryptedUser(email="deadline3@example.com", hashed_password="test")
        
        db_session.add_all([user1, user2, user3])
        await db_session.commit()
        
        # Create requests with different deadline statuses
        req1 = await gdpr_service.create_deletion_request(user1.id, True, "Within deadline")
        req2 = await gdpr_service.create_deletion_request(user2.id, True, "Approaching deadline")
        req3 = await gdpr_service.create_deletion_request(user3.id, True, "Overdue")
        
        # Simulate different deadline states
        req2.deletion_deadline = datetime.now(timezone.utc) + timedelta(days=2)  # Approaching
        req3.deletion_deadline = datetime.now(timezone.utc) - timedelta(days=1)  # Overdue
        await db_session.commit()
        
        # Check deadline compliance
        compliance_status = await gdpr_service.check_deadline_compliance()
        
        assert compliance_status.total_active_requests >= 3
        assert compliance_status.approaching_deadline >= 1
        assert compliance_status.overdue_requests >= 1
        assert compliance_status.compliance_rate < 100.0  # Due to overdue request


class TestGDPRDeletionIntegration:
    """Test end-to-end GDPR deletion process integration."""
    
    @pytest.mark.asyncio
    async def test_complete_gdpr_deletion_workflow(self, db_session: AsyncSession):
        """Test complete GDPR deletion workflow from request to certificate."""
        gdpr_service = GDPRDeletionService(db_session)
        
        # Step 1: Create user with comprehensive data
        user = EncryptedUser(
            email="complete.workflow@example.com",
            hashed_password="test_hash",
            tax_id="CMPWRK80A01H501U",
            full_name="Complete Workflow User",
            phone="+39 123 456 7890"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create related data
        session = Session(
            user_id=user.id,
            session_token="workflow_session",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        db_session.add(session)
        await db_session.commit()
        
        # Step 2: Create deletion request
        deletion_request = await gdpr_service.create_deletion_request(
            user_id=user.id,
            initiated_by_user=True,
            reason="Complete workflow test"
        )
        
        assert deletion_request.status == DeletionStatus.PENDING
        
        # Step 3: Execute deletion (simulate overdue to trigger automatic execution)
        deletion_request.deletion_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        await db_session.commit()
        
        deletion_results = await gdpr_service.execute_overdue_deletions()
        
        assert len(deletion_results) == 1
        deletion_result = deletion_results[0]
        assert deletion_result.success == True
        
        # Step 4: Verify deletion
        verifier = DeletionVerifier(db_session)
        verification_result = await verifier.verify_user_deletion(user.id)
        
        assert verification_result.is_completely_deleted == True
        assert verification_result.gdpr_compliant == True
        
        # Step 5: Generate certificate
        certificate = await verifier.generate_deletion_certificate(verification_result)
        
        assert certificate.is_complete_deletion == True
        assert certificate.compliance_attestation == True
        
        # Step 6: Verify request status
        await db_session.refresh(deletion_request)
        assert deletion_request.status == DeletionStatus.COMPLETED
        assert deletion_request.completed_at is not None
        assert deletion_request.deletion_certificate_id == certificate.certificate_id
    
    @pytest.mark.asyncio
    async def test_gdpr_deletion_performance_requirements(self, db_session: AsyncSession):
        """Test GDPR deletion meets performance requirements."""
        gdpr_service = GDPRDeletionService(db_session)
        
        # Create user with substantial data
        user = EncryptedUser(
            email="performance.test@example.com",
            hashed_password="test_hash"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create many related records
        sessions = []
        for i in range(500):
            session = Session(
                user_id=user.id,
                session_token=f"perf_session_{i}",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
            )
            sessions.append(session)
        
        db_session.add_all(sessions)
        await db_session.commit()
        
        # Measure deletion performance
        start_time = datetime.now(timezone.utc)
        
        deletion_request = await gdpr_service.create_deletion_request(
            user_id=user.id,
            initiated_by_user=True,
            reason="Performance test"
        )
        
        # Execute immediate deletion
        data_deletor = UserDataDeletor(db_session)
        deletion_result = await data_deletor.delete_user_data(user.id)
        
        end_time = datetime.now(timezone.utc)
        duration_seconds = (end_time - start_time).total_seconds()
        
        # Performance assertions
        assert deletion_result.success == True
        assert deletion_result.total_records_deleted >= 501  # User + 500 sessions
        assert duration_seconds < 60  # Should complete within 1 minute
        
        # Verify efficient deletion
        remaining_count = await db_session.execute(
            select(func.count(Session.id)).where(Session.user_id == user.id)
        )
        assert remaining_count.scalar() == 0


# Test fixtures and utilities

@pytest.fixture
async def sample_user_with_data(db_session: AsyncSession):
    """Create a sample user with comprehensive related data for testing."""
    user = EncryptedUser(
        email="sample.user@example.com",
        hashed_password="test_hash",
        tax_id="SMPUSR80A01H501U",
        full_name="Sample User",
        phone="+39 123 456 7890",
        address="Via Test 123, Milano"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Create related data
    session = Session(
        user_id=user.id,
        session_token="sample_session",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    db_session.add(session)
    await db_session.commit()
    
    return user


@pytest.fixture
def mock_external_services():
    """Mock external services for testing."""
    with patch.multiple(
        'app.services.gdpr_deletion_service',
        redis_client=Mock(),
        stripe_client=Mock(),
        backup_manager=Mock(),
        log_anonymizer=Mock()
    ) as mocks:
        yield mocks


# Performance and stress testing

class TestGDPRDeletionPerformance:
    """Test GDPR deletion performance and scalability."""
    
    @pytest.mark.asyncio
    async def test_concurrent_deletion_requests(self, db_session: AsyncSession):
        """Test handling of concurrent deletion requests."""
        gdpr_service = GDPRDeletionService(db_session)
        
        # Create multiple users
        users = []
        for i in range(10):
            user = EncryptedUser(
                email=f"concurrent{i}@example.com",
                hashed_password="test_hash"
            )
            users.append(user)
        
        db_session.add_all(users)
        await db_session.commit()
        
        # Create concurrent deletion requests
        tasks = []
        for user in users:
            task = gdpr_service.create_deletion_request(
                user_id=user.id,
                initiated_by_user=True,
                reason=f"Concurrent test {user.id}"
            )
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all succeeded
        successful_requests = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_requests) == 10
    
    @pytest.mark.asyncio
    async def test_batch_deletion_processing(self, db_session: AsyncSession):
        """Test efficient batch processing of multiple deletions."""
        gdpr_service = GDPRDeletionService(db_session)
        
        # Create multiple users with overdue deletions
        users = []
        for i in range(20):
            user = EncryptedUser(
                email=f"batch{i}@example.com",
                hashed_password="test_hash"
            )
            users.append(user)
        
        db_session.add_all(users)
        await db_session.commit()
        
        # Create overdue deletion requests
        for user in users:
            request = await gdpr_service.create_deletion_request(
                user_id=user.id,
                initiated_by_user=True,
                reason=f"Batch test {user.id}"
            )
            request.deletion_deadline = datetime.now(timezone.utc) - timedelta(days=1)
        
        await db_session.commit()
        
        # Execute batch deletions
        start_time = datetime.now(timezone.utc)
        results = await gdpr_service.execute_overdue_deletions()
        end_time = datetime.now(timezone.utc)
        
        duration_seconds = (end_time - start_time).total_seconds()
        
        # Performance assertions
        assert len(results) == 20
        assert all(r.success for r in results)
        assert duration_seconds < 120  # Should complete within 2 minutes