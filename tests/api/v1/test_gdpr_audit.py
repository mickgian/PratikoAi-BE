"""Tests for GDPR Compliance Audit API endpoints.

Tests the /gdpr/audit/* endpoints for running GDPR compliance audits.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.gdpr_audit import router
from app.core.privacy.gdpr_compliance_audit import AuditCategory


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with the audit router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


class TestGDPRAuditAPI:
    """Test GDPR audit API endpoints."""

    def test_health_endpoint(self, client: TestClient):
        """Test audit health check returns all categories."""
        response = client.get("/gdpr/audit/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "gdpr-compliance-audit"
        assert len(data["categories"]) == 5

    def test_run_full_audit(self, client: TestClient):
        """Test running full GDPR audit returns valid report."""
        response = client.get("/gdpr/audit/run")
        assert response.status_code == 200
        data = response.json()
        assert "audit_id" in data
        assert "environment" in data
        assert data["environment"] == "qa"
        assert "overall_status" in data
        assert "compliance_score" in data
        assert "summary" in data
        assert "checks" in data
        assert "category_results" in data
        assert data["summary"]["total_checks"] > 0

    def test_run_category_audit_right_to_access(self, client: TestClient):
        """Test running audit for right_to_access category."""
        response = client.get("/gdpr/audit/run/right_to_access")
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        for check in data["checks"]:
            assert check["category"] == "right_to_access"

    def test_run_category_audit_right_to_erasure(self, client: TestClient):
        """Test running audit for right_to_erasure category."""
        response = client.get("/gdpr/audit/run/right_to_erasure")
        assert response.status_code == 200
        data = response.json()
        for check in data["checks"]:
            assert check["category"] == "right_to_erasure"

    def test_run_category_audit_consent_management(self, client: TestClient):
        """Test running audit for consent_management category."""
        response = client.get("/gdpr/audit/run/consent_management")
        assert response.status_code == 200
        data = response.json()
        for check in data["checks"]:
            assert check["category"] == "consent_management"

    def test_run_category_audit_invalid_category(self, client: TestClient):
        """Test invalid category returns 422 error."""
        response = client.get("/gdpr/audit/run/invalid_category")
        assert response.status_code == 422

    def test_full_audit_has_all_categories(self, client: TestClient):
        """Test full audit covers all 5 GDPR categories."""
        response = client.get("/gdpr/audit/run")
        assert response.status_code == 200
        data = response.json()
        categories_in_results = set(data["category_results"].keys())
        expected = {c.value for c in AuditCategory}
        assert categories_in_results == expected
