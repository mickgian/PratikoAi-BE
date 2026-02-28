"""DEV-379: GDPR Compliance Test Suite.

Tests GDPRDeletionService dataclasses, enums, deletion request creation,
audit logging, and compliance report generation.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.gdpr_deletion_service import (
    ComplianceReport,
    DeletionCertificate,
    DeletionPriority,
    DeletionRequest,
    DeletionResult,
    DeletionStatus,
    SystemType,
    VerificationResult,
)

# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestDeletionStatusEnum:
    def test_pending(self) -> None:
        assert DeletionStatus.PENDING == "pending"

    def test_in_progress(self) -> None:
        assert DeletionStatus.IN_PROGRESS == "in_progress"

    def test_completed(self) -> None:
        assert DeletionStatus.COMPLETED == "completed"

    def test_failed(self) -> None:
        assert DeletionStatus.FAILED == "failed"

    def test_cancelled(self) -> None:
        assert DeletionStatus.CANCELLED == "cancelled"


class TestDeletionPriorityEnum:
    def test_low(self) -> None:
        assert DeletionPriority.LOW == "low"

    def test_normal(self) -> None:
        assert DeletionPriority.NORMAL == "normal"

    def test_high(self) -> None:
        assert DeletionPriority.HIGH == "high"

    def test_urgent(self) -> None:
        assert DeletionPriority.URGENT == "urgent"


class TestSystemTypeEnum:
    def test_database(self) -> None:
        assert SystemType.DATABASE == "database"

    def test_redis(self) -> None:
        assert SystemType.REDIS == "redis"

    def test_logs(self) -> None:
        assert SystemType.LOGS == "logs"

    def test_backups(self) -> None:
        assert SystemType.BACKUPS == "backups"

    def test_stripe(self) -> None:
        assert SystemType.STRIPE == "stripe"

    def test_external_api(self) -> None:
        assert SystemType.EXTERNAL_API == "external_api"


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


class TestDeletionRequestDataclass:
    def test_creation_with_all_fields(self) -> None:
        now = datetime.now(UTC)
        req = DeletionRequest(
            request_id="gdpr_del_abc123",
            user_id=42,
            status=DeletionStatus.PENDING,
            initiated_by_user=True,
            admin_user_id=None,
            reason="User requested account deletion",
            priority=DeletionPriority.NORMAL,
            request_timestamp=now,
            deletion_deadline=now + timedelta(days=30),
            scheduled_execution=None,
            completed_at=None,
            deletion_certificate_id=None,
            error_message=None,
        )
        assert req.request_id == "gdpr_del_abc123"
        assert req.user_id == 42
        assert req.status == DeletionStatus.PENDING

    def test_admin_initiated_request(self) -> None:
        now = datetime.now(UTC)
        req = DeletionRequest(
            request_id="gdpr_del_xyz",
            user_id=100,
            status=DeletionStatus.PENDING,
            initiated_by_user=False,
            admin_user_id=1,
            reason="Admin cleanup",
            priority=DeletionPriority.HIGH,
            request_timestamp=now,
            deletion_deadline=now + timedelta(days=30),
            scheduled_execution=None,
            completed_at=None,
            deletion_certificate_id=None,
            error_message=None,
        )
        assert req.initiated_by_user is False
        assert req.admin_user_id == 1

    def test_completed_request(self) -> None:
        now = datetime.now(UTC)
        req = DeletionRequest(
            request_id="gdpr_del_done",
            user_id=50,
            status=DeletionStatus.COMPLETED,
            initiated_by_user=True,
            admin_user_id=None,
            reason="GDPR request",
            priority=DeletionPriority.NORMAL,
            request_timestamp=now - timedelta(days=15),
            deletion_deadline=now + timedelta(days=15),
            scheduled_execution=now - timedelta(days=5),
            completed_at=now,
            deletion_certificate_id="cert_123",
            error_message=None,
        )
        assert req.status == DeletionStatus.COMPLETED
        assert req.deletion_certificate_id == "cert_123"


class TestDeletionResultDataclass:
    def test_successful_result(self) -> None:
        result = DeletionResult(
            request_id="gdpr_del_123",
            user_id=42,
            success=True,
            total_records_deleted=150,
            tables_affected=["users", "sessions", "profiles"],
            systems_processed=["database", "redis", "logs"],
            audit_records_preserved=5,
            deletion_certificate_id="cert_abc",
            processing_time_seconds=12.5,
            error_message=None,
        )
        assert result.success is True
        assert result.total_records_deleted == 150

    def test_failed_result(self) -> None:
        result = DeletionResult(
            request_id="gdpr_del_456",
            user_id=43,
            success=False,
            total_records_deleted=0,
            tables_affected=[],
            systems_processed=["database"],
            audit_records_preserved=0,
            deletion_certificate_id=None,
            processing_time_seconds=1.2,
            error_message="Database timeout",
        )
        assert result.success is False
        assert result.error_message == "Database timeout"


class TestComplianceReportDataclass:
    def test_creation(self) -> None:
        report = ComplianceReport(
            report_id="rpt_001",
            report_period_days=30,
            total_deletion_requests=10,
            user_initiated_requests=8,
            admin_initiated_requests=2,
            completed_deletions=9,
            failed_deletions=1,
            pending_deletions=0,
            overdue_deletions=0,
            average_completion_time_hours=24.5,
            compliance_score=0.95,
            generated_at=datetime.now(UTC),
        )
        assert report.total_deletion_requests == 10
        assert report.compliance_score == pytest.approx(0.95)


class TestVerificationResultDataclass:
    def test_complete_deletion(self) -> None:
        result = VerificationResult(
            user_id=42,
            is_completely_deleted=True,
            remaining_data_found=[],
            verification_score=1.0,
            gdpr_compliant=True,
            verification_timestamp=datetime.now(UTC),
            systems_verified=["database", "redis"],
        )
        assert result.is_completely_deleted is True
        assert result.gdpr_compliant is True

    def test_incomplete_deletion(self) -> None:
        result = VerificationResult(
            user_id=43,
            is_completely_deleted=False,
            remaining_data_found=[{"table": "logs", "count": 3}],
            verification_score=0.8,
            gdpr_compliant=False,
            verification_timestamp=datetime.now(UTC),
            systems_verified=["database"],
        )
        assert result.is_completely_deleted is False


class TestDeletionCertificateDataclass:
    def test_certificate_creation(self) -> None:
        cert = DeletionCertificate(
            certificate_id="cert_001",
            user_id=42,
            is_complete_deletion=True,
            issued_at=datetime.now(UTC),
            compliance_attestation=True,
            certificate_text="All data deleted per GDPR Art. 17",
            verification_details={"systems": ["database", "redis"]},
        )
        assert cert.certificate_id == "cert_001"
        assert cert.compliance_attestation is True


# ---------------------------------------------------------------------------
# GDPRDeletionService.create_deletion_request
# ---------------------------------------------------------------------------


class TestCreateDeletionRequest:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_deletion_request_success(self) -> None:
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=MagicMock())
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        mock_existing = MagicMock()
        mock_existing.fetchone.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_existing)

        with (
            patch("app.services.gdpr_deletion_service.get_settings", return_value=MagicMock()),
            patch("app.services.gdpr_deletion_service.GDPRDeletionRequest") as mock_req,
            patch("app.services.gdpr_deletion_service.GDPRDeletionAuditLog"),
            patch("app.services.gdpr_deletion_service.select"),
            patch("app.services.gdpr_deletion_service.EncryptedUser"),
        ):
            mock_req.return_value = MagicMock()

            from app.services.gdpr_deletion_service import GDPRDeletionService

            service = GDPRDeletionService(db_session=mock_db)

            result = await service.create_deletion_request(
                user_id=42,
                initiated_by_user=True,
                reason="Account deletion request",
            )

        assert result is not None
        assert result.status == DeletionStatus.PENDING
        assert result.user_id == 42

    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_deletion_request_user_not_found(self) -> None:
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        with (
            patch("app.services.gdpr_deletion_service.get_settings", return_value=MagicMock()),
            patch("app.services.gdpr_deletion_service.EncryptedUser"),
        ):
            from app.services.gdpr_deletion_service import GDPRDeletionService

            service = GDPRDeletionService(db_session=mock_db)

            with pytest.raises(ValueError, match="does not exist"):
                await service.create_deletion_request(
                    user_id=999,
                    initiated_by_user=True,
                    reason="Delete",
                )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_deletion_request_already_exists(self) -> None:
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=MagicMock())

        mock_existing = MagicMock()
        mock_existing.fetchone.return_value = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_existing)

        with (
            patch("app.services.gdpr_deletion_service.get_settings", return_value=MagicMock()),
            patch("app.services.gdpr_deletion_service.GDPRDeletionRequest"),
            patch("app.services.gdpr_deletion_service.select"),
            patch("app.services.gdpr_deletion_service.EncryptedUser"),
        ):
            from app.services.gdpr_deletion_service import GDPRDeletionService

            service = GDPRDeletionService(db_session=mock_db)

            with pytest.raises(ValueError, match="already exists"):
                await service.create_deletion_request(
                    user_id=42,
                    initiated_by_user=True,
                    reason="Duplicate request",
                )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_30_day_deadline_set(self) -> None:
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=MagicMock())
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        mock_existing = MagicMock()
        mock_existing.fetchone.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_existing)

        with (
            patch("app.services.gdpr_deletion_service.get_settings", return_value=MagicMock()),
            patch("app.services.gdpr_deletion_service.GDPRDeletionRequest") as mock_req,
            patch("app.services.gdpr_deletion_service.GDPRDeletionAuditLog"),
            patch("app.services.gdpr_deletion_service.select"),
            patch("app.services.gdpr_deletion_service.EncryptedUser"),
        ):
            mock_req.return_value = MagicMock()

            from app.services.gdpr_deletion_service import GDPRDeletionService

            service = GDPRDeletionService(db_session=mock_db)

            result = await service.create_deletion_request(
                user_id=42,
                initiated_by_user=True,
                reason="Delete me",
            )

        # Deadline should be ~30 days from now
        assert result.deletion_deadline > datetime.now(UTC) + timedelta(days=29)


# ---------------------------------------------------------------------------
# GDPRDeletionService._audit_log
# ---------------------------------------------------------------------------


class TestAuditLog:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_audit_log_creates_entry(self) -> None:
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        with (
            patch("app.services.gdpr_deletion_service.get_settings", return_value=MagicMock()),
            patch("app.services.gdpr_deletion_service.GDPRDeletionAuditLog") as mock_log,
        ):
            mock_log.return_value = MagicMock()

            from app.services.gdpr_deletion_service import GDPRDeletionService

            service = GDPRDeletionService(db_session=mock_db)
            await service._audit_log(
                request_id="gdpr_del_123",
                original_user_id=42,
                operation="test_operation",
                system_type=SystemType.DATABASE,
                success=True,
                records_deleted=10,
            )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_audit_log_with_error(self) -> None:
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        with (
            patch("app.services.gdpr_deletion_service.get_settings", return_value=MagicMock()),
            patch("app.services.gdpr_deletion_service.GDPRDeletionAuditLog") as mock_log,
        ):
            mock_log_instance = MagicMock()
            mock_log.return_value = mock_log_instance

            from app.services.gdpr_deletion_service import GDPRDeletionService

            service = GDPRDeletionService(db_session=mock_db)
            await service._audit_log(
                request_id="gdpr_del_456",
                original_user_id=43,
                operation="failed_operation",
                system_type=SystemType.REDIS,
                success=False,
                records_deleted=0,
                error_message="Connection failed",
            )

        mock_db.add.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_audit_log_swallows_exceptions(self) -> None:
        mock_db = AsyncMock()
        mock_db.add = MagicMock(side_effect=Exception("DB error"))
        mock_db.rollback = AsyncMock()

        with (
            patch("app.services.gdpr_deletion_service.get_settings", return_value=MagicMock()),
            patch("app.services.gdpr_deletion_service.GDPRDeletionAuditLog"),
        ):
            from app.services.gdpr_deletion_service import GDPRDeletionService

            service = GDPRDeletionService(db_session=mock_db)
            # Should not raise
            await service._audit_log(
                request_id="gdpr_del_789",
                original_user_id=44,
                operation="error_test",
                system_type=SystemType.LOGS,
                success=True,
                records_deleted=0,
            )
