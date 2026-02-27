"""DEV-373: Tests for DPAService — DPA acceptance workflow.

Tests cover:
- Getting the active DPA version
- Studio DPA acceptance (happy path)
- Duplicate acceptance prevention
- DPA acceptance status checking
- Revoking DPA acceptance
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.dpa import DPA, DPAAcceptance, DPAStatus
from app.services.dpa_service import DPAService


@pytest.fixture
def dpa_service() -> DPAService:
    return DPAService()


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def sample_dpa() -> DPA:
    return DPA(
        id=uuid4(),
        title="Accordo Trattamento Dati v1.0",
        version="1.0",
        content="Contenuto completo dell'accordo per il trattamento dei dati personali.",
        status=DPAStatus.ACTIVE,
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def sample_acceptance(studio_id, sample_dpa) -> DPAAcceptance:
    return DPAAcceptance(
        id=uuid4(),
        dpa_id=sample_dpa.id,
        studio_id=studio_id,
        accepted_by=1,
        accepted_at=datetime(2026, 1, 15, tzinfo=UTC),
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
    )


class TestDPAServiceGetActive:
    """Test DPAService.get_active_dpa()."""

    @pytest.mark.asyncio
    async def test_get_active_dpa(
        self,
        dpa_service: DPAService,
        mock_db: AsyncMock,
        sample_dpa: DPA,
    ) -> None:
        """Happy path: get the currently active DPA."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=sample_dpa)))
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await dpa_service.get_active_dpa(db=mock_db)

        assert result is not None
        assert result.status == DPAStatus.ACTIVE
        assert result.version == "1.0"


class TestDPAServiceAcceptance:
    """Test DPAService.accept() DPA acceptance workflow."""

    @pytest.mark.asyncio
    async def test_accept_dpa_success(
        self,
        dpa_service: DPAService,
        mock_db: AsyncMock,
        studio_id,
        sample_dpa: DPA,
    ) -> None:
        """Happy path: studio accepts the active DPA."""
        # First query: check existing acceptance (none)
        acceptance_result = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        mock_db.execute = AsyncMock(return_value=acceptance_result)
        # db.get returns the DPA
        mock_db.get = AsyncMock(return_value=sample_dpa)

        result = await dpa_service.accept(
            db=mock_db,
            dpa_id=sample_dpa.id,
            studio_id=studio_id,
            accepted_by=1,
            ip_address="192.168.1.100",
        )

        assert result.dpa_id == sample_dpa.id
        assert result.studio_id == studio_id
        assert result.accepted_by == 1
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_accept_dpa_already_accepted(
        self,
        dpa_service: DPAService,
        mock_db: AsyncMock,
        studio_id,
        sample_dpa: DPA,
        sample_acceptance: DPAAcceptance,
    ) -> None:
        """Error: duplicate acceptance raises ValueError."""
        acceptance_result = MagicMock(scalar_one_or_none=MagicMock(return_value=sample_acceptance))
        mock_db.execute = AsyncMock(return_value=acceptance_result)

        with pytest.raises(ValueError, match="già.*accettato"):
            await dpa_service.accept(
                db=mock_db,
                dpa_id=sample_dpa.id,
                studio_id=studio_id,
                accepted_by=1,
                ip_address="192.168.1.100",
            )


class TestDPAServiceCheck:
    """Test DPAService.check_accepted()."""

    @pytest.mark.asyncio
    async def test_check_dpa_accepted_true(
        self,
        dpa_service: DPAService,
        mock_db: AsyncMock,
        studio_id,
        sample_dpa: DPA,
        sample_acceptance: DPAAcceptance,
    ) -> None:
        """Happy path: studio has accepted the DPA."""
        # get_active_dpa query
        active_result = MagicMock()
        active_result.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=sample_dpa)))
        # check acceptance query
        acceptance_result = MagicMock(scalar_one_or_none=MagicMock(return_value=sample_acceptance))
        mock_db.execute = AsyncMock(side_effect=[active_result, acceptance_result])

        result = await dpa_service.check_accepted(
            db=mock_db,
            studio_id=studio_id,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_dpa_accepted_false(
        self,
        dpa_service: DPAService,
        mock_db: AsyncMock,
        studio_id,
        sample_dpa: DPA,
    ) -> None:
        """No acceptance record means DPA not accepted."""
        # get_active_dpa query
        active_result = MagicMock()
        active_result.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=sample_dpa)))
        # check acceptance query returns None
        acceptance_result = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        mock_db.execute = AsyncMock(side_effect=[active_result, acceptance_result])

        result = await dpa_service.check_accepted(
            db=mock_db,
            studio_id=studio_id,
        )

        assert result is False


class TestDPAServiceRevoke:
    """Test DPAService.revoke_acceptance()."""

    @pytest.mark.asyncio
    async def test_revoke_acceptance(
        self,
        dpa_service: DPAService,
        mock_db: AsyncMock,
        studio_id,
        sample_dpa: DPA,
        sample_acceptance: DPAAcceptance,
    ) -> None:
        """Happy path: revoke an existing DPA acceptance."""
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_acceptance))
        )

        result = await dpa_service.revoke_acceptance(
            db=mock_db,
            dpa_id=sample_dpa.id,
            studio_id=studio_id,
        )

        assert result is True
        mock_db.delete.assert_called_once_with(sample_acceptance)
