"""Tests for DPA API endpoints (DEV-373).

TDD: Tests written FIRST before implementation.
Tests all DPA endpoints with mocked DPAService.

Endpoints tested:
- GET  /dpa/active   (get active DPA)
- POST /dpa/accept   (accept DPA)
- GET  /dpa/status   (check acceptance status)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.dpa import DPA, DPAAcceptance, DPAStatus

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock async database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def sample_dpa() -> MagicMock:
    """Return a mock DPA object."""
    dpa = MagicMock()
    dpa.id = uuid4()
    dpa.title = "Accordo Trattamento Dati v1.0"
    dpa.version = "1.0"
    dpa.status = DPAStatus.ACTIVE
    dpa.effective_from = "2026-01-01"
    return dpa


@pytest.fixture
def sample_acceptance(studio_id) -> MagicMock:
    """Return a mock DPAAcceptance object."""
    acceptance = MagicMock()
    acceptance.id = uuid4()
    acceptance.dpa_id = uuid4()
    acceptance.studio_id = studio_id
    acceptance.accepted_by = 1
    acceptance.ip_address = "192.168.1.100"
    return acceptance


# ---------------------------------------------------------------------------
# GET /dpa/active — Get active DPA
# ---------------------------------------------------------------------------


class TestGetActiveDPA:
    """Tests for GET /dpa/active endpoint."""

    @pytest.mark.asyncio
    async def test_get_active_dpa_success(self, mock_db: AsyncMock, sample_dpa: MagicMock) -> None:
        """Happy path: returns the active DPA."""
        from app.api.v1.dpa import get_active_dpa

        with patch("app.api.v1.dpa.dpa_service") as mock_svc:
            mock_svc.get_active_dpa = AsyncMock(return_value=sample_dpa)
            result = await get_active_dpa(db=mock_db)

        assert result is not None
        assert result.version == "1.0"
        assert result.title == "Accordo Trattamento Dati v1.0"

    @pytest.mark.asyncio
    async def test_get_active_dpa_none(self, mock_db: AsyncMock) -> None:
        """Edge case: no active DPA returns None."""
        from app.api.v1.dpa import get_active_dpa

        with patch("app.api.v1.dpa.dpa_service") as mock_svc:
            mock_svc.get_active_dpa = AsyncMock(return_value=None)
            result = await get_active_dpa(db=mock_db)

        assert result is None


# ---------------------------------------------------------------------------
# POST /dpa/accept — Accept DPA
# ---------------------------------------------------------------------------


class TestAcceptDPA:
    """Tests for POST /dpa/accept endpoint."""

    @pytest.mark.asyncio
    async def test_accept_dpa_success(self, mock_db: AsyncMock, studio_id, sample_acceptance: MagicMock) -> None:
        """Happy path: accept DPA successfully."""
        from app.api.v1.dpa import DPAAcceptanceRequest, accept_dpa

        body = DPAAcceptanceRequest(dpa_id=sample_acceptance.dpa_id)
        mock_request = MagicMock()
        mock_request.client = MagicMock(host="192.168.1.100")
        mock_request.headers = MagicMock()
        mock_request.headers.get = MagicMock(return_value="TestBrowser/1.0")

        with patch("app.api.v1.dpa.dpa_service") as mock_svc:
            mock_svc.accept = AsyncMock(return_value=sample_acceptance)
            result = await accept_dpa(
                body=body,
                request=mock_request,
                studio_id=studio_id,
                accepted_by=1,
                db=mock_db,
            )

        assert result.studio_id == studio_id
        assert result.accepted_by == 1
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_accept_dpa_already_accepted_returns_400(self, mock_db: AsyncMock, studio_id) -> None:
        """Error case: duplicate acceptance raises 400."""
        from app.api.v1.dpa import DPAAcceptanceRequest, accept_dpa

        body = DPAAcceptanceRequest(dpa_id=uuid4())
        mock_request = MagicMock()
        mock_request.client = MagicMock(host="192.168.1.100")
        mock_request.headers = MagicMock()
        mock_request.headers.get = MagicMock(return_value=None)

        with patch("app.api.v1.dpa.dpa_service") as mock_svc:
            mock_svc.accept = AsyncMock(side_effect=ValueError("DPA già accettato dallo studio."))
            with pytest.raises(HTTPException) as exc_info:
                await accept_dpa(
                    body=body,
                    request=mock_request,
                    studio_id=studio_id,
                    accepted_by=1,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_accept_dpa_no_client_ip(self, mock_db: AsyncMock, studio_id, sample_acceptance: MagicMock) -> None:
        """Edge case: request has no client info, falls back to 'unknown'."""
        from app.api.v1.dpa import DPAAcceptanceRequest, accept_dpa

        body = DPAAcceptanceRequest(dpa_id=sample_acceptance.dpa_id)
        mock_request = MagicMock()
        mock_request.client = None
        mock_request.headers = MagicMock()
        mock_request.headers.get = MagicMock(return_value=None)

        with patch("app.api.v1.dpa.dpa_service") as mock_svc:
            mock_svc.accept = AsyncMock(return_value=sample_acceptance)
            result = await accept_dpa(
                body=body,
                request=mock_request,
                studio_id=studio_id,
                accepted_by=1,
                db=mock_db,
            )

        # Verify ip_address was passed as "unknown"
        call_kwargs = mock_svc.accept.call_args.kwargs
        assert call_kwargs["ip_address"] == "unknown"


# ---------------------------------------------------------------------------
# GET /dpa/status — Check acceptance status
# ---------------------------------------------------------------------------


class TestCheckDPAStatus:
    """Tests for GET /dpa/status endpoint."""

    @pytest.mark.asyncio
    async def test_check_status_accepted(self, mock_db: AsyncMock, studio_id) -> None:
        """Happy path: studio has accepted DPA."""
        from app.api.v1.dpa import check_dpa_status

        with patch("app.api.v1.dpa.dpa_service") as mock_svc:
            mock_svc.check_accepted = AsyncMock(return_value=True)
            result = await check_dpa_status(studio_id=studio_id, db=mock_db)

        assert result.accepted is True

    @pytest.mark.asyncio
    async def test_check_status_not_accepted(self, mock_db: AsyncMock, studio_id) -> None:
        """Studio has NOT accepted DPA."""
        from app.api.v1.dpa import check_dpa_status

        with patch("app.api.v1.dpa.dpa_service") as mock_svc:
            mock_svc.check_accepted = AsyncMock(return_value=False)
            result = await check_dpa_status(studio_id=studio_id, db=mock_db)

        assert result.accepted is False
