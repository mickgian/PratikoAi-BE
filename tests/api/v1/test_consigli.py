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


@pytest.fixture
def starlette_request():
    """Build a real Starlette Request so the slowapi limiter decorator passes."""
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/consigli/report",
        "headers": [],
        "query_string": b"",
    }
    return StarletteRequest(scope)


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


class TestGenerateConsigliReportEndpoint:
    """Tests for the generate_consigli_report route handler."""

    @pytest.mark.asyncio
    @patch("app.api.v1.consigli.limiter")
    @patch("app.api.v1.consigli.consigli_service")
    async def test_success_report(
        self,
        mock_service,
        _mock_limiter,
        mock_user,
        starlette_request,
    ):
        from app.api.v1.consigli import generate_consigli_report

        mock_db = AsyncMock()
        mock_service.generate_report = AsyncMock(
            return_value={
                "status": "success",
                "message_it": "Report generato.",
                "html_report": "<html><body>Report</body></html>",
                "stats_summary": {
                    "total_queries": 100,
                    "active_days": 30,
                    "session_count": 25,
                },
            }
        )

        result = await generate_consigli_report(
            request=starlette_request,
            user=mock_user,
            db=mock_db,
        )

        assert isinstance(result, ConsigliReportResponse)
        assert result.status == "success"
        assert result.html_report == "<html><body>Report</body></html>"
        assert result.stats_summary == {
            "total_queries": 100,
            "active_days": 30,
            "session_count": 25,
        }
        mock_service.generate_report.assert_awaited_once_with(42, mock_db)

    @pytest.mark.asyncio
    @patch("app.api.v1.consigli.limiter")
    @patch("app.api.v1.consigli.consigli_service")
    async def test_insufficient_data(
        self,
        mock_service,
        _mock_limiter,
        mock_user,
        starlette_request,
    ):
        from app.api.v1.consigli import generate_consigli_report

        mock_db = AsyncMock()
        mock_service.generate_report = AsyncMock(
            return_value={
                "status": "insufficient_data",
                "message_it": "Dati non sufficienti.",
            }
        )

        result = await generate_consigli_report(
            request=starlette_request,
            user=mock_user,
            db=mock_db,
        )

        assert result.status == "insufficient_data"
        assert result.html_report is None
        assert result.stats_summary is None

    @pytest.mark.asyncio
    @patch("app.api.v1.consigli.limiter")
    @patch("app.api.v1.consigli.consigli_service")
    async def test_logs_request(
        self,
        mock_service,
        _mock_limiter,
        mock_user,
        starlette_request,
    ):
        from app.api.v1.consigli import generate_consigli_report

        mock_db = AsyncMock()
        mock_service.generate_report = AsyncMock(
            return_value={
                "status": "success",
                "message_it": "OK",
                "html_report": "<html></html>",
            }
        )

        with patch("app.api.v1.consigli.logger") as mock_logger:
            await generate_consigli_report(
                request=starlette_request,
                user=mock_user,
                db=mock_db,
            )
            mock_logger.info.assert_called_once_with(
                "consigli_report_requested",
                user_id=42,
            )
