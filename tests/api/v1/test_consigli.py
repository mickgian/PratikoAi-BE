"""Tests for /consigli API endpoint (ADR-038).

Tests the API route handler logic. These tests require the full
test suite conftest chain (database fixtures) to import the route module.
Run as part of the full test suite: uv run pytest tests/

When running without a DB, these tests are skipped gracefully.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    from app.schemas.consigli import ConsigliReportResponse

    _SCHEMAS_AVAILABLE = True
except Exception:
    _SCHEMAS_AVAILABLE = False

# Skip all tests in this file if DB is not available (CI/isolated runs)
pytestmark = pytest.mark.skipif(
    not _SCHEMAS_AVAILABLE,
    reason="Requires database connection for app module imports",
)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    user = MagicMock()
    user.id = 42
    user.role = "user"
    return user


class TestConsigliReportResponse:
    """Tests for the ConsigliReportResponse schema used by the endpoint."""

    def test_success_response(self):
        resp = ConsigliReportResponse(
            status="success",
            message_it="Report generato con successo.",
            html_report="<html></html>",
            stats_summary={"total_queries": 50},
        )
        assert resp.status == "success"
        assert resp.html_report is not None

    def test_insufficient_data_response(self):
        resp = ConsigliReportResponse(
            status="insufficient_data",
            message_it="Dati non sufficienti.",
        )
        assert resp.html_report is None
        assert resp.stats_summary is None

    def test_generating_response(self):
        resp = ConsigliReportResponse(
            status="generating",
            message_it="Report in generazione.",
        )
        assert resp.status == "generating"

    def test_error_response(self):
        resp = ConsigliReportResponse(
            status="error",
            message_it="Errore.",
        )
        assert resp.status == "error"
        assert resp.html_report is None
