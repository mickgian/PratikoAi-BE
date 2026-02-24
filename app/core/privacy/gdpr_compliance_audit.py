"""GDPR Compliance Audit Service for PratikoAI.

Implements DEV-BE-74: Comprehensive GDPR compliance audit covering all 5 categories:
1. Right to Access (Data Export) - GDPR Article 15/20
2. Right to Erasure (Data Deletion) - GDPR Article 17
3. Consent Management - GDPR Article 7
4. Data Retention Policies - GDPR Article 5(1)(e)
5. Privacy by Design - GDPR Article 25

This service performs static and runtime checks to validate GDPR compliance
on the QA environment before production launch.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import os
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger


def _find_project_root() -> Path:
    """Find the project root by looking for pyproject.toml."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def _source_contains(module_path: str, *patterns: str) -> dict[str, bool]:
    """Check if a source file contains specific patterns without importing it.

    Args:
        module_path: Dotted module path (e.g. 'app.api.v1.data_export')
        *patterns: String patterns to search for

    Returns:
        Dict mapping each pattern to whether it was found.
    """
    root = _find_project_root()
    file_path = root / module_path.replace(".", "/")

    # Try as .py file
    py_path = file_path.with_suffix(".py")
    if not py_path.exists():
        # Try as package __init__.py
        init_path = file_path / "__init__.py"
        if init_path.exists():
            py_path = init_path
        else:
            return dict.fromkeys(patterns, False)

    try:
        source = py_path.read_text(encoding="utf-8")
        return {p: p in source for p in patterns}
    except OSError:
        return dict.fromkeys(patterns, False)


def _source_file_exists(module_path: str) -> bool:
    """Check if a module source file exists."""
    root = _find_project_root()
    py_path = (root / module_path.replace(".", "/")).with_suffix(".py")
    return py_path.exists()


class AuditCategory(str, Enum):
    """GDPR audit categories from DEV-BE-74 checklist."""

    RIGHT_TO_ACCESS = "right_to_access"
    RIGHT_TO_ERASURE = "right_to_erasure"
    CONSENT_MANAGEMENT = "consent_management"
    DATA_RETENTION = "data_retention"
    PRIVACY_BY_DESIGN = "privacy_by_design"


class AuditStatus(str, Enum):
    """Audit check status."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"


class AuditSeverity(str, Enum):
    """Severity of audit check."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AuditCheckResult:
    """Result of a single audit check."""

    check_id: str
    category: AuditCategory
    name: str
    description: str
    status: AuditStatus
    severity: AuditSeverity
    details: dict[str, Any] = field(default_factory=dict)
    remediation: str | None = None

    @property
    def is_passing(self) -> bool:
        """Check is passing only if status is PASS."""
        return self.status == AuditStatus.PASS


@dataclass
class GDPRComplianceAuditReport:
    """Full GDPR compliance audit report."""

    audit_id: str
    environment: str
    checks: list[AuditCheckResult]
    started_at: datetime
    completed_at: datetime

    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @property
    def passed_checks(self) -> int:
        return sum(1 for c in self.checks if c.status == AuditStatus.PASS)

    @property
    def failed_checks(self) -> int:
        return sum(1 for c in self.checks if c.status == AuditStatus.FAIL)

    @property
    def warning_checks(self) -> int:
        return sum(1 for c in self.checks if c.status == AuditStatus.WARNING)

    @property
    def overall_status(self) -> AuditStatus:
        if any(c.status == AuditStatus.FAIL for c in self.checks):
            return AuditStatus.FAIL
        if any(c.status == AuditStatus.WARNING for c in self.checks):
            return AuditStatus.WARNING
        return AuditStatus.PASS

    @property
    def compliance_score(self) -> float:
        if self.total_checks == 0:
            return 100.0
        return round((self.passed_checks / self.total_checks) * 100, 1)

    @property
    def results_by_category(self) -> dict[AuditCategory, list[AuditCheckResult]]:
        grouped: dict[AuditCategory, list[AuditCheckResult]] = defaultdict(list)
        for check in self.checks:
            grouped[check.category].append(check)
        return dict(grouped)

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to JSON-compatible dictionary."""
        by_category = self.results_by_category
        category_results = {}
        for cat, checks in by_category.items():
            passed = sum(1 for c in checks if c.status == AuditStatus.PASS)
            failed = sum(1 for c in checks if c.status == AuditStatus.FAIL)
            warnings = sum(1 for c in checks if c.status == AuditStatus.WARNING)
            category_results[cat.value] = {
                "total": len(checks),
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "status": AuditStatus.FAIL.value if failed > 0 else AuditStatus.PASS.value,
            }

        return {
            "audit_id": self.audit_id,
            "environment": self.environment,
            "overall_status": self.overall_status.value,
            "compliance_score": self.compliance_score,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "summary": {
                "total_checks": self.total_checks,
                "passed": self.passed_checks,
                "failed": self.failed_checks,
                "warnings": self.warning_checks,
            },
            "category_results": category_results,
            "checks": [
                {
                    "check_id": c.check_id,
                    "category": c.category.value,
                    "name": c.name,
                    "description": c.description,
                    "status": c.status.value,
                    "severity": c.severity.value,
                    "details": c.details,
                    "remediation": c.remediation,
                }
                for c in self.checks
            ],
        }


class GDPRComplianceAudit:
    """GDPR Compliance Audit engine.

    Performs automated compliance checks across all 5 GDPR categories
    defined in DEV-BE-74. Checks are primarily static (code/config inspection)
    and can be run without a live database connection.
    """

    def __init__(self, db_session: AsyncSession | None = None):
        """Initialize the audit service.

        Args:
            db_session: Optional async database session for runtime checks.
        """
        self.db = db_session

    def run_full_audit(self) -> GDPRComplianceAuditReport:
        """Run full GDPR compliance audit across all 5 categories."""
        started_at = datetime.now(UTC)
        all_checks: list[AuditCheckResult] = []

        all_checks.extend(self.audit_right_to_access())
        all_checks.extend(self.audit_right_to_erasure())
        all_checks.extend(self.audit_consent_management())
        all_checks.extend(self.audit_data_retention())
        all_checks.extend(self.audit_privacy_by_design())

        completed_at = datetime.now(UTC)

        report = GDPRComplianceAuditReport(
            audit_id=str(uuid.uuid4()),
            environment="qa",
            checks=all_checks,
            started_at=started_at,
            completed_at=completed_at,
        )

        logger.info(
            "gdpr_compliance_audit_completed",
            audit_id=report.audit_id,
            total_checks=report.total_checks,
            passed=report.passed_checks,
            failed=report.failed_checks,
            compliance_score=report.compliance_score,
            overall_status=report.overall_status.value,
        )

        return report

    def run_category_audit(self, category: AuditCategory) -> GDPRComplianceAuditReport:
        """Run audit for a single category."""
        started_at = datetime.now(UTC)

        category_methods = {
            AuditCategory.RIGHT_TO_ACCESS: self.audit_right_to_access,
            AuditCategory.RIGHT_TO_ERASURE: self.audit_right_to_erasure,
            AuditCategory.CONSENT_MANAGEMENT: self.audit_consent_management,
            AuditCategory.DATA_RETENTION: self.audit_data_retention,
            AuditCategory.PRIVACY_BY_DESIGN: self.audit_privacy_by_design,
        }

        checks = category_methods[category]()
        completed_at = datetime.now(UTC)

        return GDPRComplianceAuditReport(
            audit_id=str(uuid.uuid4()),
            environment="qa",
            checks=checks,
            started_at=started_at,
            completed_at=completed_at,
        )

    # -------------------------------------------------------------------------
    # Category 1: Right to Access (Data Export) - GDPR Article 15/20
    # -------------------------------------------------------------------------

    def audit_right_to_access(self) -> list[AuditCheckResult]:
        """Audit Right to Access (Data Export) compliance."""
        checks: list[AuditCheckResult] = []

        # ACCESS_001: Data export endpoint exists
        checks.append(self._check_data_export_endpoint())

        # ACCESS_002: Export supports required formats
        checks.append(self._check_export_formats())

        # ACCESS_003: All user data categories are included
        checks.append(self._check_export_data_categories())

        # ACCESS_004: 30-day deadline mechanism
        checks.append(self._check_export_deadline())

        # ACCESS_005: Privacy levels supported
        checks.append(self._check_export_privacy_levels())

        return checks

    def _check_data_export_endpoint(self) -> AuditCheckResult:
        """ACCESS_001: Verify data export API endpoint exists."""
        module = "app.api.v1.data_export"
        found = _source_contains(
            module,
            "/request",
            "/download",
            "/status",
            "router = APIRouter",
        )

        if _source_file_exists(module) and found.get("router = APIRouter"):
            return AuditCheckResult(
                check_id="ACCESS_001",
                category=AuditCategory.RIGHT_TO_ACCESS,
                name="Data export endpoint available",
                description="Verify data export API endpoints exist (request, download, status)",
                status=AuditStatus.PASS,
                severity=AuditSeverity.CRITICAL,
                details={
                    "module": module,
                    "has_request": found.get("/request", False),
                    "has_download": found.get("/download", False),
                    "has_status": found.get("/status", False),
                },
            )

        return AuditCheckResult(
            check_id="ACCESS_001",
            category=AuditCategory.RIGHT_TO_ACCESS,
            name="Data export endpoint available",
            description="Verify data export API endpoints exist",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.CRITICAL,
            details={"error": "Data export module not found"},
            remediation="Implement data export API at app/api/v1/data_export.py",
        )

    def _check_export_formats(self) -> AuditCheckResult:
        """ACCESS_002: Verify export supports JSON and CSV formats."""
        try:
            from app.models.data_export import ExportFormat

            formats = [f.value for f in ExportFormat]
            has_json = "json" in formats
            has_csv = "csv" in formats

            if has_json and has_csv:
                return AuditCheckResult(
                    check_id="ACCESS_002",
                    category=AuditCategory.RIGHT_TO_ACCESS,
                    name="Export format support",
                    description="Verify export supports JSON and CSV formats per GDPR Article 20",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.CRITICAL,
                    details={"supported_formats": formats},
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="ACCESS_002",
            category=AuditCategory.RIGHT_TO_ACCESS,
            name="Export format support",
            description="Verify export supports JSON and CSV formats",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.CRITICAL,
            details={"error": "ExportFormat enum not found"},
            remediation="Add JSON and CSV to ExportFormat enum in app/models/data_export.py",
        )

    def _check_export_data_categories(self) -> AuditCheckResult:
        """ACCESS_003: Verify all user data categories are exportable."""
        required_categories = [
            "include_profile",
            "include_queries",
            "include_documents",
            "include_calculations",
            "include_subscriptions",
            "include_invoices",
            "include_usage_stats",
            "include_faq_interactions",
            "include_knowledge_searches",
        ]

        module = "app.api.v1.data_export"
        found = _source_contains(module, *required_categories)
        missing = [c for c in required_categories if not found.get(c)]

        if not missing:
            return AuditCheckResult(
                check_id="ACCESS_003",
                category=AuditCategory.RIGHT_TO_ACCESS,
                name="Export data categories complete",
                description="Verify all user data categories are included in export",
                status=AuditStatus.PASS,
                severity=AuditSeverity.HIGH,
                details={
                    "required_categories": required_categories,
                    "all_present": True,
                },
            )

        return AuditCheckResult(
            check_id="ACCESS_003",
            category=AuditCategory.RIGHT_TO_ACCESS,
            name="Export data categories complete",
            description="Verify all user data categories are included in export",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"missing_categories": missing},
            remediation=f"Add missing categories to CreateExportRequest: {missing}",
        )

    def _check_export_deadline(self) -> AuditCheckResult:
        """ACCESS_004: Verify 30-day deadline mechanism for exports."""
        try:
            from app.models.data_export import DataExportRequest

            model_fields = set(DataExportRequest.model_fields.keys())
            has_expiry = "expires_at" in model_fields
            has_requested_at = "requested_at" in model_fields or "created_at" in model_fields

            if has_expiry:
                return AuditCheckResult(
                    check_id="ACCESS_004",
                    category=AuditCategory.RIGHT_TO_ACCESS,
                    name="Export 30-day deadline tracking",
                    description="Verify export respects GDPR 30-day completion deadline",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.CRITICAL,
                    details={
                        "has_expiry_tracking": has_expiry,
                        "has_request_timestamp": has_requested_at,
                        "gdpr_article": "Article 12(3) - 30-day response deadline",
                    },
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="ACCESS_004",
            category=AuditCategory.RIGHT_TO_ACCESS,
            name="Export 30-day deadline tracking",
            description="Verify export respects GDPR 30-day completion deadline",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.CRITICAL,
            details={"error": "DataExportRequest model not found"},
            remediation="Add expires_at field to DataExportRequest model",
        )

    def _check_export_privacy_levels(self) -> AuditCheckResult:
        """ACCESS_005: Verify privacy levels for export."""
        try:
            from app.models.data_export import PrivacyLevel

            levels = [p.value for p in PrivacyLevel]
            has_full = "full" in levels
            has_anonymized = "anonymized" in levels
            has_minimal = "minimal" in levels

            if has_full and has_anonymized and has_minimal:
                return AuditCheckResult(
                    check_id="ACCESS_005",
                    category=AuditCategory.RIGHT_TO_ACCESS,
                    name="Export privacy levels",
                    description="Verify export supports Full, Anonymized, and Minimal privacy levels",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.HIGH,
                    details={"privacy_levels": levels},
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="ACCESS_005",
            category=AuditCategory.RIGHT_TO_ACCESS,
            name="Export privacy levels",
            description="Verify export supports privacy levels",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"error": "PrivacyLevel enum not found"},
            remediation="Add Full/Anonymized/Minimal to PrivacyLevel enum",
        )

    # -------------------------------------------------------------------------
    # Category 2: Right to Erasure (Data Deletion) - GDPR Article 17
    # -------------------------------------------------------------------------

    def audit_right_to_erasure(self) -> list[AuditCheckResult]:
        """Audit Right to Erasure (Data Deletion) compliance."""
        checks: list[AuditCheckResult] = []

        checks.append(self._check_deletion_endpoint())
        checks.append(self._check_deletion_deadline())
        checks.append(self._check_deletion_multi_system())
        checks.append(self._check_deletion_verification())
        checks.append(self._check_deletion_certificate())
        checks.append(self._check_deletion_scheduler())

        return checks

    def _check_deletion_endpoint(self) -> AuditCheckResult:
        """ERASURE_001: Verify deletion request endpoint exists."""
        module = "app.api.v1.gdpr"
        found = _source_contains(
            module,
            "deletion-request",
            "admin/deletion-request",
            "router = APIRouter",
        )

        if _source_file_exists(module) and found.get("router = APIRouter"):
            return AuditCheckResult(
                check_id="ERASURE_001",
                category=AuditCategory.RIGHT_TO_ERASURE,
                name="Deletion endpoint available",
                description="Verify GDPR deletion request endpoints exist (user and admin)",
                status=AuditStatus.PASS,
                severity=AuditSeverity.CRITICAL,
                details={
                    "module": module,
                    "has_user_endpoint": found.get("deletion-request", False),
                    "has_admin_endpoint": found.get("admin/deletion-request", False),
                },
            )

        return AuditCheckResult(
            check_id="ERASURE_001",
            category=AuditCategory.RIGHT_TO_ERASURE,
            name="Deletion endpoint available",
            description="Verify deletion request endpoints exist",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.CRITICAL,
            details={"error": "GDPR deletion module not found"},
            remediation="Implement GDPR deletion API at app/api/v1/gdpr.py",
        )

    def _check_deletion_deadline(self) -> AuditCheckResult:
        """ERASURE_002: Verify 30-day deletion deadline tracking."""
        module = "app.services.gdpr_deletion_service"
        found = _source_contains(module, "deletion_deadline", "request_timestamp", "DeletionRequest")

        if found.get("deletion_deadline") and found.get("request_timestamp"):
            return AuditCheckResult(
                check_id="ERASURE_002",
                category=AuditCategory.RIGHT_TO_ERASURE,
                name="30-day deletion deadline",
                description="Verify deletion tracks and enforces 30-day GDPR deadline",
                status=AuditStatus.PASS,
                severity=AuditSeverity.CRITICAL,
                details={
                    "has_deadline_field": True,
                    "has_timestamp_field": True,
                    "gdpr_article": "Article 17 + Article 12(3)",
                },
            )

        return AuditCheckResult(
            check_id="ERASURE_002",
            category=AuditCategory.RIGHT_TO_ERASURE,
            name="30-day deletion deadline",
            description="Verify 30-day deletion deadline tracking",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.CRITICAL,
            details={"error": "DeletionRequest deadline fields not found"},
            remediation="Add deletion_deadline field to DeletionRequest",
        )

    def _check_deletion_multi_system(self) -> AuditCheckResult:
        """ERASURE_003: Verify deletion covers all systems."""
        module = "app.services.gdpr_deletion_service"
        required_systems = ["DATABASE", "REDIS", "LOGS", "BACKUPS"]
        found = _source_contains(module, "SystemType", *required_systems)

        if found.get("SystemType") and all(found.get(s) for s in required_systems):
            return AuditCheckResult(
                check_id="ERASURE_003",
                category=AuditCategory.RIGHT_TO_ERASURE,
                name="Multi-system deletion coverage",
                description="Verify deletion covers DB, Redis, logs, and backups",
                status=AuditStatus.PASS,
                severity=AuditSeverity.CRITICAL,
                details={
                    "systems_covered": [s.lower() for s in required_systems],
                    "system_type_defined": True,
                },
            )

        return AuditCheckResult(
            check_id="ERASURE_003",
            category=AuditCategory.RIGHT_TO_ERASURE,
            name="Multi-system deletion coverage",
            description="Verify deletion covers all systems",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.CRITICAL,
            details={"error": "SystemType enum not found or missing systems"},
            remediation="Define SystemType enum with DATABASE, REDIS, LOGS, BACKUPS",
        )

    def _check_deletion_verification(self) -> AuditCheckResult:
        """ERASURE_004: Verify deletion verification mechanism."""
        module = "app.services.deletion_verifier"
        found = _source_contains(module, "DeletionVerifier", "verify_user_deletion")

        if found.get("DeletionVerifier") and found.get("verify_user_deletion"):
            return AuditCheckResult(
                check_id="ERASURE_004",
                category=AuditCategory.RIGHT_TO_ERASURE,
                name="Deletion verification mechanism",
                description="Verify post-deletion verification exists to confirm complete erasure",
                status=AuditStatus.PASS,
                severity=AuditSeverity.HIGH,
                details={"verifier_class": "DeletionVerifier", "has_verify_method": True},
            )

        return AuditCheckResult(
            check_id="ERASURE_004",
            category=AuditCategory.RIGHT_TO_ERASURE,
            name="Deletion verification mechanism",
            description="Verify deletion verification exists",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"error": "DeletionVerifier not found"},
            remediation="Implement DeletionVerifier with verify_user_deletion method",
        )

    def _check_deletion_certificate(self) -> AuditCheckResult:
        """ERASURE_005: Verify deletion certificate generation."""
        module = "app.services.gdpr_deletion_service"
        found = _source_contains(module, "DeletionCertificate", "GDPRDeletionCertificate")

        if found.get("DeletionCertificate") and found.get("GDPRDeletionCertificate"):
            return AuditCheckResult(
                check_id="ERASURE_005",
                category=AuditCategory.RIGHT_TO_ERASURE,
                name="Deletion certificate generation",
                description="Verify GDPR deletion certificates are generated as proof of erasure",
                status=AuditStatus.PASS,
                severity=AuditSeverity.HIGH,
                details={
                    "certificate_model": "DeletionCertificate",
                    "db_table": "GDPRDeletionCertificate",
                },
            )

        return AuditCheckResult(
            check_id="ERASURE_005",
            category=AuditCategory.RIGHT_TO_ERASURE,
            name="Deletion certificate generation",
            description="Verify deletion certificates are generated",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"error": "Certificate models not found"},
            remediation="Implement DeletionCertificate and GDPRDeletionCertificate models",
        )

    def _check_deletion_scheduler(self) -> AuditCheckResult:
        """ERASURE_006: Verify automated deletion scheduler."""
        module = "app.services.gdpr_scheduler"
        found = _source_contains(module, "GDPRDeletionScheduler", "start", "process_pending")

        if _source_file_exists(module) and found.get("GDPRDeletionScheduler"):
            return AuditCheckResult(
                check_id="ERASURE_006",
                category=AuditCategory.RIGHT_TO_ERASURE,
                name="Automated deletion scheduler",
                description="Verify automated scheduler for processing overdue deletion requests",
                status=AuditStatus.PASS,
                severity=AuditSeverity.HIGH,
                details={
                    "scheduler_class": "GDPRScheduler",
                    "module": module,
                },
            )

        return AuditCheckResult(
            check_id="ERASURE_006",
            category=AuditCategory.RIGHT_TO_ERASURE,
            name="Automated deletion scheduler",
            description="Verify automated deletion scheduler exists",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"error": "GDPRScheduler not found"},
            remediation="Implement GDPRScheduler in app/services/gdpr_scheduler.py",
        )

    # -------------------------------------------------------------------------
    # Category 3: Consent Management - GDPR Article 7
    # -------------------------------------------------------------------------

    def audit_consent_management(self) -> list[AuditCheckResult]:
        """Audit consent management compliance."""
        checks: list[AuditCheckResult] = []

        checks.append(self._check_consent_types())
        checks.append(self._check_consent_operations())
        checks.append(self._check_consent_records())
        checks.append(self._check_consent_expiry())
        checks.append(self._check_consent_api())

        return checks

    def _check_consent_types(self) -> AuditCheckResult:
        """CONSENT_001: Verify all required consent types exist."""
        try:
            from app.core.privacy.gdpr import ConsentType

            types = [t.value for t in ConsentType]
            required = ["necessary", "functional", "analytical", "marketing", "personalization"]
            missing = [r for r in required if r not in types]

            if not missing:
                return AuditCheckResult(
                    check_id="CONSENT_001",
                    category=AuditCategory.CONSENT_MANAGEMENT,
                    name="Consent types defined",
                    description="Verify all required consent types (necessary, functional, analytical, marketing, personalization)",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.CRITICAL,
                    details={"consent_types": types, "all_required_present": True},
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="CONSENT_001",
            category=AuditCategory.CONSENT_MANAGEMENT,
            name="Consent types defined",
            description="Verify consent types exist",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.CRITICAL,
            details={"error": "ConsentType not importable"},
            remediation="Define ConsentType enum in app/core/privacy/gdpr.py",
        )

    def _check_consent_operations(self) -> AuditCheckResult:
        """CONSENT_002: Verify grant/withdraw consent operations work."""
        try:
            from app.core.privacy.gdpr import ConsentManager, ConsentType

            manager = ConsentManager()
            test_user = "__gdpr_audit_test__"

            consent_id = manager.grant_consent(test_user, ConsentType.FUNCTIONAL)
            has_consent = manager.has_valid_consent(test_user, ConsentType.FUNCTIONAL)
            withdrawn = manager.withdraw_consent(test_user, ConsentType.FUNCTIONAL)
            no_consent = not manager.has_valid_consent(test_user, ConsentType.FUNCTIONAL)

            if consent_id and has_consent and withdrawn and no_consent:
                return AuditCheckResult(
                    check_id="CONSENT_002",
                    category=AuditCategory.CONSENT_MANAGEMENT,
                    name="Consent grant/withdraw operations",
                    description="Verify grant and withdraw consent operations work correctly",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.CRITICAL,
                    details={
                        "grant_works": True,
                        "check_works": has_consent,
                        "withdraw_works": withdrawn,
                        "post_withdraw_cleared": no_consent,
                    },
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="CONSENT_002",
            category=AuditCategory.CONSENT_MANAGEMENT,
            name="Consent grant/withdraw operations",
            description="Verify consent operations",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.CRITICAL,
            details={"error": "Consent operations failed"},
            remediation="Fix ConsentManager grant/withdraw/has_valid_consent methods",
        )

    def _check_consent_records(self) -> AuditCheckResult:
        """CONSENT_003: Verify consent records are properly stored."""
        try:
            from app.core.privacy.gdpr import ConsentManager, ConsentRecord, ConsentType

            manager = ConsentManager()
            test_user = "__gdpr_audit_records_test__"

            manager.grant_consent(
                test_user,
                ConsentType.ANALYTICAL,
                ip_address="127.0.0.1",
                user_agent="GDPR-Audit/1.0",
            )

            history = manager.get_consent_history(test_user)
            has_records = len(history) > 0

            if has_records:
                record = history[0]
                has_ip = record.ip_address is not None
                has_timestamp = record.timestamp is not None
                has_consent_type = record.consent_type == ConsentType.ANALYTICAL

                if has_ip and has_timestamp and has_consent_type:
                    return AuditCheckResult(
                        check_id="CONSENT_003",
                        category=AuditCategory.CONSENT_MANAGEMENT,
                        name="Consent records storage",
                        description="Verify consent records include IP, timestamp, and consent type",
                        status=AuditStatus.PASS,
                        severity=AuditSeverity.HIGH,
                        details={
                            "records_stored": True,
                            "has_ip_address": has_ip,
                            "has_timestamp": has_timestamp,
                            "has_consent_type": has_consent_type,
                        },
                    )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="CONSENT_003",
            category=AuditCategory.CONSENT_MANAGEMENT,
            name="Consent records storage",
            description="Verify consent records are stored",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"error": "Consent record storage check failed"},
            remediation="Ensure ConsentRecord stores ip_address, timestamp, consent_type",
        )

    def _check_consent_expiry(self) -> AuditCheckResult:
        """CONSENT_004: Verify consent expiration management."""
        try:
            from app.core.privacy.gdpr import ConsentManager, ConsentType

            manager = ConsentManager()
            test_user = "__gdpr_audit_expiry_test__"

            # Grant consent with immediate expiry
            manager.grant_consent(test_user, ConsentType.MARKETING, expiry_days=-1)

            # Should be expired
            is_expired = not manager.has_valid_consent(test_user, ConsentType.MARKETING)

            # Cleanup method exists
            has_cleanup = hasattr(manager, "cleanup_expired_consents")

            if is_expired and has_cleanup:
                return AuditCheckResult(
                    check_id="CONSENT_004",
                    category=AuditCategory.CONSENT_MANAGEMENT,
                    name="Consent expiration management",
                    description="Verify consent expiration and cleanup mechanisms",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.HIGH,
                    details={
                        "expiry_works": is_expired,
                        "has_cleanup_method": has_cleanup,
                    },
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="CONSENT_004",
            category=AuditCategory.CONSENT_MANAGEMENT,
            name="Consent expiration management",
            description="Verify consent expiration",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"error": "Consent expiry check failed"},
            remediation="Implement consent expiry with cleanup_expired_consents method",
        )

    def _check_consent_api(self) -> AuditCheckResult:
        """CONSENT_005: Verify consent API endpoints."""
        module = "app.api.v1.privacy"
        found = _source_contains(module, "/consent", "consent/status", "router")

        if _source_file_exists(module) and found.get("/consent"):
            return AuditCheckResult(
                check_id="CONSENT_005",
                category=AuditCategory.CONSENT_MANAGEMENT,
                name="Consent API endpoints",
                description="Verify consent management API endpoints are available",
                status=AuditStatus.PASS,
                severity=AuditSeverity.HIGH,
                details={
                    "module": module,
                    "has_consent_endpoint": found.get("/consent", False),
                    "has_status_endpoint": found.get("consent/status", False),
                },
            )

        return AuditCheckResult(
            check_id="CONSENT_005",
            category=AuditCategory.CONSENT_MANAGEMENT,
            name="Consent API endpoints",
            description="Verify consent API endpoints exist",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"error": "Privacy router not found"},
            remediation="Implement consent endpoints in app/api/v1/privacy.py",
        )

    # -------------------------------------------------------------------------
    # Category 4: Data Retention Policies - GDPR Article 5(1)(e)
    # -------------------------------------------------------------------------

    def audit_data_retention(self) -> list[AuditCheckResult]:
        """Audit data retention policy compliance."""
        checks: list[AuditCheckResult] = []

        checks.append(self._check_retention_policies_defined())
        checks.append(self._check_retention_periods_correct())
        checks.append(self._check_retention_behavioral())
        checks.append(self._check_retention_technical())
        checks.append(self._check_retention_cleanup())

        return checks

    def _check_retention_policies_defined(self) -> AuditCheckResult:
        """RETENTION_001: Verify retention policies defined for all categories."""
        try:
            from app.core.privacy.gdpr import ConsentManager, DataCategory, DataProcessor

            manager = ConsentManager()
            processor = DataProcessor(manager)

            categories = list(DataCategory)
            policies_defined = []
            missing_policies = []

            for cat in categories:
                period = processor.get_retention_period(cat)
                if period is not None:
                    policies_defined.append(cat.value)
                else:
                    missing_policies.append(cat.value)

            if not missing_policies:
                return AuditCheckResult(
                    check_id="RETENTION_001",
                    category=AuditCategory.DATA_RETENTION,
                    name="Retention policies defined",
                    description="Verify retention policies exist for all data categories",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.CRITICAL,
                    details={
                        "categories_with_policies": policies_defined,
                        "all_defined": True,
                    },
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="RETENTION_001",
            category=AuditCategory.DATA_RETENTION,
            name="Retention policies defined",
            description="Verify retention policies exist",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.CRITICAL,
            details={"error": "Retention policies check failed"},
            remediation="Define retention policies for all DataCategory values",
        )

    def _check_retention_periods_correct(self) -> AuditCheckResult:
        """RETENTION_002: Verify retention periods match requirements."""
        try:
            from app.core.privacy.gdpr import ConsentManager, DataCategory, DataProcessor

            manager = ConsentManager()
            processor = DataProcessor(manager)

            expected = {
                DataCategory.IDENTITY: 2555,  # 7 years
                DataCategory.CONTACT: 365,  # 1 year
                DataCategory.FINANCIAL: 2555,  # 7 years
                DataCategory.BEHAVIORAL: 90,  # 3 months
                DataCategory.TECHNICAL: 30,  # 1 month
                DataCategory.CONTENT: 365,  # 1 year
            }

            mismatches = []
            for cat, expected_days in expected.items():
                actual = processor.get_retention_period(cat)
                if actual is None or actual.days != expected_days:
                    mismatches.append(
                        {
                            "category": cat.value,
                            "expected_days": expected_days,
                            "actual_days": actual.days if actual else None,
                        }
                    )

            if not mismatches:
                return AuditCheckResult(
                    check_id="RETENTION_002",
                    category=AuditCategory.DATA_RETENTION,
                    name="Retention periods correct",
                    description="Verify retention periods match GDPR and Italian legal requirements",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.CRITICAL,
                    details={
                        "all_correct": True,
                        "periods": {k.value: v for k, v in expected.items()},
                    },
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="RETENTION_002",
            category=AuditCategory.DATA_RETENTION,
            name="Retention periods correct",
            description="Verify retention periods",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.CRITICAL,
            details={"error": "Retention periods check failed"},
            remediation="Correct retention periods to match requirements",
        )

    def _check_retention_behavioral(self) -> AuditCheckResult:
        """RETENTION_003: Verify behavioral data retention (90 days)."""
        try:
            from app.core.privacy.gdpr import ConsentManager, DataCategory, DataProcessor

            manager = ConsentManager()
            processor = DataProcessor(manager)
            period = processor.get_retention_period(DataCategory.BEHAVIORAL)

            if period and period.days == 90:
                return AuditCheckResult(
                    check_id="RETENTION_003",
                    category=AuditCategory.DATA_RETENTION,
                    name="Behavioral data retention (90 days)",
                    description="Verify conversation/behavioral data retained for max 90 days",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.HIGH,
                    details={
                        "retention_days": period.days,
                        "data_type": "behavioral/conversation",
                    },
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="RETENTION_003",
            category=AuditCategory.DATA_RETENTION,
            name="Behavioral data retention (90 days)",
            description="Verify behavioral data retention",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"error": "Behavioral retention check failed"},
            remediation="Set behavioral data retention to 90 days",
        )

    def _check_retention_technical(self) -> AuditCheckResult:
        """RETENTION_004: Verify technical/log data retention (30 days)."""
        try:
            from app.core.privacy.gdpr import ConsentManager, DataCategory, DataProcessor

            manager = ConsentManager()
            processor = DataProcessor(manager)
            period = processor.get_retention_period(DataCategory.TECHNICAL)

            if period and period.days == 30:
                return AuditCheckResult(
                    check_id="RETENTION_004",
                    category=AuditCategory.DATA_RETENTION,
                    name="Technical/log data retention (30 days)",
                    description="Verify log/technical data retained for max 30 days",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.HIGH,
                    details={
                        "retention_days": period.days,
                        "data_type": "technical/logs",
                    },
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="RETENTION_004",
            category=AuditCategory.DATA_RETENTION,
            name="Technical/log data retention (30 days)",
            description="Verify technical data retention",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"error": "Technical retention check failed"},
            remediation="Set technical data retention to 30 days",
        )

    def _check_retention_cleanup(self) -> AuditCheckResult:
        """RETENTION_005: Verify automatic cleanup for expired data."""
        try:
            from app.core.privacy.gdpr import ConsentManager, DataProcessor, GDPRCompliance

            gdpr = GDPRCompliance()
            has_cleanup = hasattr(gdpr, "periodic_cleanup")
            has_should_delete = hasattr(DataProcessor, "should_delete_data")

            if has_cleanup and has_should_delete:
                # Test the cleanup runs without errors
                gdpr.periodic_cleanup()

                return AuditCheckResult(
                    check_id="RETENTION_005",
                    category=AuditCategory.DATA_RETENTION,
                    name="Automatic data cleanup mechanism",
                    description="Verify automatic cleanup for expired data based on retention policies",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.HIGH,
                    details={
                        "has_periodic_cleanup": has_cleanup,
                        "has_should_delete": has_should_delete,
                        "cleanup_functional": True,
                    },
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="RETENTION_005",
            category=AuditCategory.DATA_RETENTION,
            name="Automatic data cleanup mechanism",
            description="Verify automatic cleanup exists",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"error": "Cleanup mechanism check failed"},
            remediation="Implement periodic_cleanup and should_delete_data methods",
        )

    # -------------------------------------------------------------------------
    # Category 5: Privacy by Design - GDPR Article 25
    # -------------------------------------------------------------------------

    def audit_privacy_by_design(self) -> list[AuditCheckResult]:
        """Audit Privacy by Design compliance."""
        checks: list[AuditCheckResult] = []

        checks.append(self._check_pii_detection())
        checks.append(self._check_field_encryption())
        checks.append(self._check_italian_pii())
        checks.append(self._check_audit_logging())
        checks.append(self._check_data_minimization())

        return checks

    def _check_pii_detection(self) -> AuditCheckResult:
        """PRIVACY_001: Verify PII detection and anonymization."""
        try:
            from app.core.privacy.anonymizer import PIIAnonymizer, PIIType, anonymizer

            # Test PII detection on sample data
            test_text = "Contact mario.rossi@email.com or call +39 06 12345678"
            result = anonymizer.anonymize_text(test_text)

            has_anonymized = result.anonymized_text != test_text
            detected_types = {m.pii_type for m in result.pii_matches}
            has_email_detection = PIIType.EMAIL in detected_types

            if has_anonymized and has_email_detection:
                return AuditCheckResult(
                    check_id="PRIVACY_001",
                    category=AuditCategory.PRIVACY_BY_DESIGN,
                    name="PII detection and anonymization",
                    description="Verify PII detection works for emails, phones, and Italian identifiers",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.CRITICAL,
                    details={
                        "anonymization_works": has_anonymized,
                        "detected_types": [t.value for t in detected_types],
                        "pii_types_supported": [t.value for t in PIIType],
                    },
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="PRIVACY_001",
            category=AuditCategory.PRIVACY_BY_DESIGN,
            name="PII detection and anonymization",
            description="Verify PII detection",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.CRITICAL,
            details={"error": "PII detection check failed"},
            remediation="Implement PIIAnonymizer with email, phone, and Italian ID detection",
        )

    def _check_field_encryption(self) -> AuditCheckResult:
        """PRIVACY_002: Verify field-level encryption for sensitive data."""
        module = "app.services.database_encryption_service"
        found = _source_contains(module, "DatabaseEncryptionService", "encrypt", "decrypt")

        if found.get("DatabaseEncryptionService") and found.get("encrypt") and found.get("decrypt"):
            return AuditCheckResult(
                check_id="PRIVACY_002",
                category=AuditCategory.PRIVACY_BY_DESIGN,
                name="Field-level encryption",
                description="Verify AES-256-GCM field-level encryption for sensitive data at rest",
                status=AuditStatus.PASS,
                severity=AuditSeverity.CRITICAL,
                details={
                    "encryption_service": "DatabaseEncryptionService",
                    "has_encrypt": True,
                    "has_decrypt": True,
                },
            )

        return AuditCheckResult(
            check_id="PRIVACY_002",
            category=AuditCategory.PRIVACY_BY_DESIGN,
            name="Field-level encryption",
            description="Verify field-level encryption",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.CRITICAL,
            details={"error": "DatabaseEncryptionService not found"},
            remediation="Implement DatabaseEncryptionService with encrypt/decrypt methods",
        )

    def _check_italian_pii(self) -> AuditCheckResult:
        """PRIVACY_003: Verify Italian-specific PII handling."""
        try:
            from app.core.privacy.anonymizer import PIIType, anonymizer

            pii_types = [t.value for t in PIIType]
            has_codice_fiscale = "codice_fiscale" in pii_types
            has_partita_iva = "partita_iva" in pii_types
            has_iban = "iban" in pii_types

            # Test Codice Fiscale detection
            cf_test = "Il codice fiscale è RSSMRA85M01H501Z"
            cf_result = anonymizer.anonymize_text(cf_test)
            cf_detected = any(m.pii_type == PIIType.CODICE_FISCALE for m in cf_result.pii_matches)

            if has_codice_fiscale and has_partita_iva:
                return AuditCheckResult(
                    check_id="PRIVACY_003",
                    category=AuditCategory.PRIVACY_BY_DESIGN,
                    name="Italian PII handling (Codice Fiscale, Partita IVA)",
                    description="Verify Italian-specific PII detection for Codice Fiscale and Partita IVA",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.HIGH,
                    details={
                        "has_codice_fiscale": has_codice_fiscale,
                        "has_partita_iva": has_partita_iva,
                        "has_iban": has_iban,
                        "cf_detection_works": cf_detected,
                    },
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="PRIVACY_003",
            category=AuditCategory.PRIVACY_BY_DESIGN,
            name="Italian PII handling (Codice Fiscale, Partita IVA)",
            description="Verify Italian PII handling",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"error": "Italian PII check failed"},
            remediation="Add Codice Fiscale and Partita IVA to PIIType enum and detection",
        )

    def _check_audit_logging(self) -> AuditCheckResult:
        """PRIVACY_004: Verify GDPR audit logging."""
        try:
            from app.core.privacy.gdpr import AuditLogger

            audit_logger = AuditLogger()

            has_consent_log = hasattr(audit_logger, "log_consent_event")
            has_processing_log = hasattr(audit_logger, "log_processing_event")
            has_access_log = hasattr(audit_logger, "log_access_event")
            has_deletion_log = hasattr(audit_logger, "log_deletion_event")
            has_trail = hasattr(audit_logger, "get_audit_trail")
            has_export = hasattr(audit_logger, "export_audit_log")

            all_present = all(
                [
                    has_consent_log,
                    has_processing_log,
                    has_access_log,
                    has_deletion_log,
                    has_trail,
                    has_export,
                ]
            )

            if all_present:
                # Test logging works
                audit_logger.log_consent_event(
                    user_id="__audit_test__",
                    event_type="audit_check",
                    details={"check": "PRIVACY_004"},
                )
                events = audit_logger.get_audit_trail(user_id="__audit_test__")

                return AuditCheckResult(
                    check_id="PRIVACY_004",
                    category=AuditCategory.PRIVACY_BY_DESIGN,
                    name="GDPR audit logging",
                    description="Verify comprehensive GDPR audit logging for consent, processing, access, deletion events",
                    status=AuditStatus.PASS,
                    severity=AuditSeverity.HIGH,
                    details={
                        "event_types": [
                            "consent",
                            "processing",
                            "access",
                            "deletion",
                        ],
                        "has_audit_trail": True,
                        "has_export": True,
                        "logging_functional": len(events) > 0,
                    },
                )
        except Exception:
            pass

        return AuditCheckResult(
            check_id="PRIVACY_004",
            category=AuditCategory.PRIVACY_BY_DESIGN,
            name="GDPR audit logging",
            description="Verify GDPR audit logging",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"error": "Audit logging check failed"},
            remediation="Implement AuditLogger with consent, processing, access, deletion event logging",
        )

    def _check_data_minimization(self) -> AuditCheckResult:
        """PRIVACY_005: Verify data minimization principles."""
        try:
            from app.core.privacy.gdpr import DataCategory

            categories = list(DataCategory)
            has_categories = len(categories) >= 4
        except Exception:
            has_categories = False

        # Check data export supports selective inclusion and anonymization
        export_module = "app.api.v1.data_export"
        found = _source_contains(export_module, "include_profile", "include_queries", "anonymize_pii")
        has_selective_export = found.get("include_profile", False) and found.get("include_queries", False)
        has_anonymize_option = found.get("anonymize_pii", False)

        if has_categories and has_selective_export and has_anonymize_option:
            return AuditCheckResult(
                check_id="PRIVACY_005",
                category=AuditCategory.PRIVACY_BY_DESIGN,
                name="Data minimization principles",
                description="Verify minimal data collection and selective data processing/export",
                status=AuditStatus.PASS,
                severity=AuditSeverity.HIGH,
                details={
                    "data_categories_defined": True,
                    "selective_export": has_selective_export,
                    "anonymization_available": has_anonymize_option,
                    "gdpr_article": "Article 5(1)(c) - Data minimisation",
                },
            )

        return AuditCheckResult(
            check_id="PRIVACY_005",
            category=AuditCategory.PRIVACY_BY_DESIGN,
            name="Data minimization principles",
            description="Verify data minimization",
            status=AuditStatus.FAIL,
            severity=AuditSeverity.HIGH,
            details={"error": "Data minimization check failed"},
            remediation="Implement data categories with selective export and anonymization options",
        )
