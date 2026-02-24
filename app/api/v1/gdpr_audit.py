"""GDPR Compliance Audit API endpoints.

Implements DEV-BE-74: GDPR Compliance Audit for QA environment.
Provides endpoints to run automated GDPR compliance checks and
retrieve audit reports.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.privacy.gdpr_compliance_audit import (
    AuditCategory,
    GDPRComplianceAudit,
)

router = APIRouter(prefix="/gdpr/audit", tags=["gdpr-audit"])


class AuditCategoryQuery(BaseModel):
    """Query parameter for single-category audit."""

    category: AuditCategory


@router.get("/run")
async def run_full_audit() -> dict:
    """Run full GDPR compliance audit across all 5 categories.

    Returns a comprehensive audit report with pass/fail status for each
    check, grouped by category with overall compliance score.
    """
    audit = GDPRComplianceAudit()
    report = audit.run_full_audit()
    return report.to_dict()


@router.get("/run/{category}")
async def run_category_audit(category: AuditCategory) -> dict:
    """Run GDPR compliance audit for a specific category.

    Args:
        category: One of right_to_access, right_to_erasure,
                  consent_management, data_retention, privacy_by_design
    """
    audit = GDPRComplianceAudit()
    report = audit.run_category_audit(category)
    return report.to_dict()


@router.get("/health")
async def audit_health() -> dict:
    """Health check for the GDPR audit service."""
    return {
        "status": "healthy",
        "service": "gdpr-compliance-audit",
        "categories": [c.value for c in AuditCategory],
    }
