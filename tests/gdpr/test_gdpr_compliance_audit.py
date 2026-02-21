"""Tests for GDPR Compliance Audit Service.

Covers all 5 audit categories from DEV-BE-74:
1. Right to Access (Data Export)
2. Right to Erasure (Data Deletion)
3. Consent Management
4. Data Retention Policies
5. Privacy by Design
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.privacy.gdpr_compliance_audit import (
    AuditCategory,
    AuditCheckResult,
    AuditSeverity,
    AuditStatus,
    GDPRComplianceAudit,
    GDPRComplianceAuditReport,
)


class TestAuditCheckResult:
    """Test AuditCheckResult data structure."""

    def test_passing_check(self):
        """Test creating a passing audit check."""
        check = AuditCheckResult(
            check_id="RT_ACCESS_001",
            category=AuditCategory.RIGHT_TO_ACCESS,
            name="Data export endpoint available",
            description="Verify data export API endpoint exists and responds",
            status=AuditStatus.PASS,
            severity=AuditSeverity.CRITICAL,
            details={"endpoint": "/api/v1/gdpr/data-export/request"},
        )
        assert check.status == AuditStatus.PASS
        assert check.category == AuditCategory.RIGHT_TO_ACCESS
        assert check.severity == AuditSeverity.CRITICAL
        assert check.is_passing

    def test_failing_check(self):
        """Test creating a failing audit check."""
        check = AuditCheckResult(
            check_id="RT_ACCESS_002",
            category=AuditCategory.RIGHT_TO_ACCESS,
            name="Export format validation",
            description="Verify export supports JSON format",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.CRITICAL,
            details={"error": "JSON export not implemented"},
            remediation="Implement JSON export in DataExportService",
        )
        assert check.status == AuditStatus.FAIL
        assert not check.is_passing
        assert check.remediation is not None

    def test_warning_check(self):
        """Test creating a warning audit check."""
        check = AuditCheckResult(
            check_id="CONSENT_003",
            category=AuditCategory.CONSENT_MANAGEMENT,
            name="Consent banner UI",
            description="Verify consent banner exists in frontend",
            status=AuditStatus.WARNING,
            severity=AuditSeverity.MEDIUM,
            details={"note": "Frontend verification required"},
        )
        assert check.status == AuditStatus.WARNING
        assert not check.is_passing


class TestGDPRComplianceAuditReport:
    """Test GDPRComplianceAuditReport generation."""

    def test_empty_report(self):
        """Test report with no checks."""
        report = GDPRComplianceAuditReport(
            audit_id="test-audit-001",
            environment="qa",
            checks=[],
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        assert report.overall_status == AuditStatus.PASS
        assert report.total_checks == 0
        assert report.compliance_score == 100.0

    def test_all_passing_report(self):
        """Test report with all passing checks."""
        checks = [
            AuditCheckResult(
                check_id=f"CHECK_{i}",
                category=AuditCategory.RIGHT_TO_ACCESS,
                name=f"Check {i}",
                description=f"Test check {i}",
                status=AuditStatus.PASS,
                severity=AuditSeverity.HIGH,
            )
            for i in range(5)
        ]
        report = GDPRComplianceAuditReport(
            audit_id="test-audit-002",
            environment="qa",
            checks=checks,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        assert report.overall_status == AuditStatus.PASS
        assert report.total_checks == 5
        assert report.passed_checks == 5
        assert report.failed_checks == 0
        assert report.compliance_score == 100.0

    def test_mixed_results_report(self):
        """Test report with mixed pass/fail results."""
        checks = [
            AuditCheckResult(
                check_id="CHECK_1",
                category=AuditCategory.RIGHT_TO_ACCESS,
                name="Passing check",
                description="This passes",
                status=AuditStatus.PASS,
                severity=AuditSeverity.HIGH,
            ),
            AuditCheckResult(
                check_id="CHECK_2",
                category=AuditCategory.RIGHT_TO_ERASURE,
                name="Failing check",
                description="This fails",
                status=AuditStatus.FAIL,
                severity=AuditSeverity.CRITICAL,
            ),
            AuditCheckResult(
                check_id="CHECK_3",
                category=AuditCategory.CONSENT_MANAGEMENT,
                name="Warning check",
                description="This warns",
                status=AuditStatus.WARNING,
                severity=AuditSeverity.MEDIUM,
            ),
        ]
        report = GDPRComplianceAuditReport(
            audit_id="test-audit-003",
            environment="qa",
            checks=checks,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        assert report.overall_status == AuditStatus.FAIL
        assert report.total_checks == 3
        assert report.passed_checks == 1
        assert report.failed_checks == 1
        assert report.warning_checks == 1

    def test_category_results(self):
        """Test report grouped by category."""
        checks = [
            AuditCheckResult(
                check_id="ACCESS_1",
                category=AuditCategory.RIGHT_TO_ACCESS,
                name="Access check 1",
                description="Test",
                status=AuditStatus.PASS,
                severity=AuditSeverity.HIGH,
            ),
            AuditCheckResult(
                check_id="ACCESS_2",
                category=AuditCategory.RIGHT_TO_ACCESS,
                name="Access check 2",
                description="Test",
                status=AuditStatus.PASS,
                severity=AuditSeverity.HIGH,
            ),
            AuditCheckResult(
                check_id="ERASURE_1",
                category=AuditCategory.RIGHT_TO_ERASURE,
                name="Erasure check 1",
                description="Test",
                status=AuditStatus.FAIL,
                severity=AuditSeverity.CRITICAL,
            ),
        ]
        report = GDPRComplianceAuditReport(
            audit_id="test-audit-004",
            environment="qa",
            checks=checks,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        by_category = report.results_by_category
        assert AuditCategory.RIGHT_TO_ACCESS in by_category
        assert AuditCategory.RIGHT_TO_ERASURE in by_category
        assert len(by_category[AuditCategory.RIGHT_TO_ACCESS]) == 2
        assert len(by_category[AuditCategory.RIGHT_TO_ERASURE]) == 1

    def test_report_to_dict(self):
        """Test report serialization to dict."""
        report = GDPRComplianceAuditReport(
            audit_id="test-audit-005",
            environment="qa",
            checks=[
                AuditCheckResult(
                    check_id="CHECK_1",
                    category=AuditCategory.RIGHT_TO_ACCESS,
                    name="Test check",
                    description="Test",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.HIGH,
                ),
            ],
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        result = report.to_dict()
        assert "audit_id" in result
        assert "environment" in result
        assert "overall_status" in result
        assert "compliance_score" in result
        assert "summary" in result
        assert "checks" in result
        assert "category_results" in result


class TestGDPRComplianceAudit:
    """Test GDPRComplianceAudit service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = AsyncMock()
        self.audit = GDPRComplianceAudit(db_session=self.mock_db)

    # Category 1: Right to Access

    def test_audit_data_export_endpoint_exists(self):
        """Test that data export API endpoints are registered."""
        checks = self.audit.audit_right_to_access()
        endpoint_check = next(
            (c for c in checks if c.check_id == "ACCESS_001"),
            None,
        )
        assert endpoint_check is not None
        assert endpoint_check.status == AuditStatus.PASS

    def test_audit_export_format_support(self):
        """Test that export supports required formats (JSON/CSV)."""
        checks = self.audit.audit_right_to_access()
        format_check = next(
            (c for c in checks if c.check_id == "ACCESS_002"),
            None,
        )
        assert format_check is not None
        assert format_check.status == AuditStatus.PASS

    def test_audit_export_data_categories(self):
        """Test that all user data categories are included in export."""
        checks = self.audit.audit_right_to_access()
        categories_check = next(
            (c for c in checks if c.check_id == "ACCESS_003"),
            None,
        )
        assert categories_check is not None
        assert categories_check.status == AuditStatus.PASS

    def test_audit_export_30_day_deadline(self):
        """Test that export respects 30-day GDPR deadline."""
        checks = self.audit.audit_right_to_access()
        deadline_check = next(
            (c for c in checks if c.check_id == "ACCESS_004"),
            None,
        )
        assert deadline_check is not None
        assert deadline_check.status == AuditStatus.PASS

    def test_audit_export_privacy_levels(self):
        """Test that export supports privacy levels (Full/Anonymized/Minimal)."""
        checks = self.audit.audit_right_to_access()
        privacy_check = next(
            (c for c in checks if c.check_id == "ACCESS_005"),
            None,
        )
        assert privacy_check is not None
        assert privacy_check.status == AuditStatus.PASS

    # Category 2: Right to Erasure

    def test_audit_deletion_endpoint_exists(self):
        """Test that deletion request endpoint exists."""
        checks = self.audit.audit_right_to_erasure()
        endpoint_check = next(
            (c for c in checks if c.check_id == "ERASURE_001"),
            None,
        )
        assert endpoint_check is not None
        assert endpoint_check.status == AuditStatus.PASS

    def test_audit_deletion_30_day_deadline(self):
        """Test that deletion respects 30-day deadline."""
        checks = self.audit.audit_right_to_erasure()
        deadline_check = next(
            (c for c in checks if c.check_id == "ERASURE_002"),
            None,
        )
        assert deadline_check is not None
        assert deadline_check.status == AuditStatus.PASS

    def test_audit_deletion_multi_system(self):
        """Test that deletion covers all systems (DB, Redis, logs, backups)."""
        checks = self.audit.audit_right_to_erasure()
        systems_check = next(
            (c for c in checks if c.check_id == "ERASURE_003"),
            None,
        )
        assert systems_check is not None
        assert systems_check.status == AuditStatus.PASS

    def test_audit_deletion_verification(self):
        """Test that deletion verification mechanism exists."""
        checks = self.audit.audit_right_to_erasure()
        verify_check = next(
            (c for c in checks if c.check_id == "ERASURE_004"),
            None,
        )
        assert verify_check is not None
        assert verify_check.status == AuditStatus.PASS

    def test_audit_deletion_certificate(self):
        """Test that deletion certificates are generated."""
        checks = self.audit.audit_right_to_erasure()
        cert_check = next(
            (c for c in checks if c.check_id == "ERASURE_005"),
            None,
        )
        assert cert_check is not None
        assert cert_check.status == AuditStatus.PASS

    def test_audit_deletion_scheduler(self):
        """Test that automated deletion scheduler is configured."""
        checks = self.audit.audit_right_to_erasure()
        scheduler_check = next(
            (c for c in checks if c.check_id == "ERASURE_006"),
            None,
        )
        assert scheduler_check is not None
        assert scheduler_check.status == AuditStatus.PASS

    # Category 3: Consent Management

    def test_audit_consent_types(self):
        """Test all required consent types exist."""
        checks = self.audit.audit_consent_management()
        types_check = next(
            (c for c in checks if c.check_id == "CONSENT_001"),
            None,
        )
        assert types_check is not None
        assert types_check.status == AuditStatus.PASS

    def test_audit_consent_grant_withdraw(self):
        """Test grant and withdraw consent operations."""
        checks = self.audit.audit_consent_management()
        ops_check = next(
            (c for c in checks if c.check_id == "CONSENT_002"),
            None,
        )
        assert ops_check is not None
        assert ops_check.status == AuditStatus.PASS

    def test_audit_consent_records_stored(self):
        """Test that consent records are properly stored."""
        checks = self.audit.audit_consent_management()
        records_check = next(
            (c for c in checks if c.check_id == "CONSENT_003"),
            None,
        )
        assert records_check is not None
        assert records_check.status == AuditStatus.PASS

    def test_audit_consent_expiry(self):
        """Test consent expiration management."""
        checks = self.audit.audit_consent_management()
        expiry_check = next(
            (c for c in checks if c.check_id == "CONSENT_004"),
            None,
        )
        assert expiry_check is not None
        assert expiry_check.status == AuditStatus.PASS

    def test_audit_consent_api_endpoints(self):
        """Test consent API endpoints are available."""
        checks = self.audit.audit_consent_management()
        api_check = next(
            (c for c in checks if c.check_id == "CONSENT_005"),
            None,
        )
        assert api_check is not None
        assert api_check.status == AuditStatus.PASS

    # Category 4: Data Retention Policies

    def test_audit_retention_policies_defined(self):
        """Test that retention policies are defined for all categories."""
        checks = self.audit.audit_data_retention()
        policies_check = next(
            (c for c in checks if c.check_id == "RETENTION_001"),
            None,
        )
        assert policies_check is not None
        assert policies_check.status == AuditStatus.PASS

    def test_audit_retention_periods_correct(self):
        """Test retention periods match GDPR requirements."""
        checks = self.audit.audit_data_retention()
        periods_check = next(
            (c for c in checks if c.check_id == "RETENTION_002"),
            None,
        )
        assert periods_check is not None
        assert periods_check.status == AuditStatus.PASS

    def test_audit_retention_behavioral_data(self):
        """Test behavioral data retention (90 days)."""
        checks = self.audit.audit_data_retention()
        behavioral_check = next(
            (c for c in checks if c.check_id == "RETENTION_003"),
            None,
        )
        assert behavioral_check is not None
        assert behavioral_check.status == AuditStatus.PASS

    def test_audit_retention_technical_data(self):
        """Test technical/log data retention (30 days)."""
        checks = self.audit.audit_data_retention()
        technical_check = next(
            (c for c in checks if c.check_id == "RETENTION_004"),
            None,
        )
        assert technical_check is not None
        assert technical_check.status == AuditStatus.PASS

    def test_audit_retention_cleanup_mechanism(self):
        """Test automatic cleanup mechanism for expired data."""
        checks = self.audit.audit_data_retention()
        cleanup_check = next(
            (c for c in checks if c.check_id == "RETENTION_005"),
            None,
        )
        assert cleanup_check is not None
        assert cleanup_check.status == AuditStatus.PASS

    # Category 5: Privacy by Design

    def test_audit_pii_detection(self):
        """Test PII detection and anonymization capabilities."""
        checks = self.audit.audit_privacy_by_design()
        pii_check = next(
            (c for c in checks if c.check_id == "PRIVACY_001"),
            None,
        )
        assert pii_check is not None
        assert pii_check.status == AuditStatus.PASS

    def test_audit_field_encryption(self):
        """Test field-level encryption for sensitive data."""
        checks = self.audit.audit_privacy_by_design()
        encryption_check = next(
            (c for c in checks if c.check_id == "PRIVACY_002"),
            None,
        )
        assert encryption_check is not None
        assert encryption_check.status == AuditStatus.PASS

    def test_audit_italian_pii(self):
        """Test Italian-specific PII handling (Codice Fiscale, Partita IVA)."""
        checks = self.audit.audit_privacy_by_design()
        italian_check = next(
            (c for c in checks if c.check_id == "PRIVACY_003"),
            None,
        )
        assert italian_check is not None
        assert italian_check.status == AuditStatus.PASS

    def test_audit_audit_logging(self):
        """Test GDPR audit logging is in place."""
        checks = self.audit.audit_privacy_by_design()
        logging_check = next(
            (c for c in checks if c.check_id == "PRIVACY_004"),
            None,
        )
        assert logging_check is not None
        assert logging_check.status == AuditStatus.PASS

    def test_audit_data_minimization(self):
        """Test data minimization principles are applied."""
        checks = self.audit.audit_privacy_by_design()
        minimization_check = next(
            (c for c in checks if c.check_id == "PRIVACY_005"),
            None,
        )
        assert minimization_check is not None
        assert minimization_check.status == AuditStatus.PASS

    # Full audit

    def test_run_full_audit(self):
        """Test running the complete audit across all categories."""
        report = self.audit.run_full_audit()
        assert isinstance(report, GDPRComplianceAuditReport)
        assert report.environment == "qa"
        assert report.total_checks > 0
        assert report.started_at is not None
        assert report.completed_at is not None
        # Verify all 5 categories have checks
        categories_covered = {c.category for c in report.checks}
        assert AuditCategory.RIGHT_TO_ACCESS in categories_covered
        assert AuditCategory.RIGHT_TO_ERASURE in categories_covered
        assert AuditCategory.CONSENT_MANAGEMENT in categories_covered
        assert AuditCategory.DATA_RETENTION in categories_covered
        assert AuditCategory.PRIVACY_BY_DESIGN in categories_covered

    def test_run_single_category_audit(self):
        """Test running audit for a single category."""
        report = self.audit.run_category_audit(AuditCategory.RIGHT_TO_ACCESS)
        assert isinstance(report, GDPRComplianceAuditReport)
        categories_covered = {c.category for c in report.checks}
        assert categories_covered == {AuditCategory.RIGHT_TO_ACCESS}

    def test_audit_report_compliance_score(self):
        """Test that compliance score is correctly calculated."""
        report = self.audit.run_full_audit()
        assert 0 <= report.compliance_score <= 100.0

    def test_audit_identifies_italian_compliance(self):
        """Test that audit verifies Italian-specific GDPR features."""
        report = self.audit.run_full_audit()
        # Should have checks related to Italian compliance
        italian_related = [c for c in report.checks if "italian" in c.name.lower() or "codice" in c.name.lower()]
        assert len(italian_related) > 0


class TestGDPRComplianceAuditEdgeCases:
    """Edge case tests for the audit service."""

    def test_audit_with_no_db_session(self):
        """Test audit works without requiring active DB session for static checks."""
        audit = GDPRComplianceAudit(db_session=None)
        report = audit.run_full_audit()
        assert isinstance(report, GDPRComplianceAuditReport)
        assert report.total_checks > 0

    def test_audit_report_serializable(self):
        """Test audit report can be serialized to JSON-compatible dict."""
        audit = GDPRComplianceAudit(db_session=None)
        report = audit.run_full_audit()
        result = report.to_dict()
        # All values should be JSON-serializable
        import json

        json_str = json.dumps(result, default=str)
        assert json_str is not None

    def test_audit_check_has_remediation_on_failure(self):
        """Test that failing checks include remediation guidance."""
        audit = GDPRComplianceAudit(db_session=None)
        report = audit.run_full_audit()
        for check in report.checks:
            if check.status == AuditStatus.FAIL:
                assert check.remediation is not None, f"Failing check {check.check_id} missing remediation"
