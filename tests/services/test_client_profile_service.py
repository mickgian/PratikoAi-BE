"""DEV-310: Tests for ClientProfileService CRUD operations."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.client_profile import ClientProfile, RegimeFiscale
from app.services.client_profile_service import ClientProfileService


@pytest.fixture
def profile_service() -> ClientProfileService:
    return ClientProfileService()


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def sample_profile() -> ClientProfile:
    return ClientProfile(
        id=1,
        client_id=1,
        codice_ateco_principale="62.01.00",
        regime_fiscale=RegimeFiscale.ORDINARIO,
        data_inizio_attivita=date(2020, 1, 1),
        n_dipendenti=5,
    )


class TestClientProfileServiceCreate:
    """Test ClientProfileService.create()."""

    @pytest.mark.asyncio
    async def test_create_profile_success(self, profile_service: ClientProfileService, mock_db: AsyncMock) -> None:
        """Happy path: create profile for client."""
        # Mock check for existing profile
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await profile_service.create(
            db=mock_db,
            client_id=1,
            codice_ateco_principale="62.01.00",
            regime_fiscale=RegimeFiscale.ORDINARIO,
            data_inizio_attivita=date(2020, 1, 1),
        )

        assert result.client_id == 1
        assert result.codice_ateco_principale == "62.01.00"
        assert result.regime_fiscale == RegimeFiscale.ORDINARIO
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_profile_duplicate_raises(
        self,
        profile_service: ClientProfileService,
        mock_db: AsyncMock,
        sample_profile: ClientProfile,
    ) -> None:
        """Error: client already has a profile."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_profile)))

        with pytest.raises(ValueError, match="profilo.*già esistente"):
            await profile_service.create(
                db=mock_db,
                client_id=1,
                codice_ateco_principale="62.01.00",
                regime_fiscale=RegimeFiscale.ORDINARIO,
                data_inizio_attivita=date(2020, 1, 1),
            )

    @pytest.mark.asyncio
    async def test_create_profile_invalid_ateco(
        self, profile_service: ClientProfileService, mock_db: AsyncMock
    ) -> None:
        """Error: invalid ATECO code format."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        with pytest.raises(ValueError, match="ATECO"):
            await profile_service.create(
                db=mock_db,
                client_id=1,
                codice_ateco_principale="INVALID",
                regime_fiscale=RegimeFiscale.ORDINARIO,
                data_inizio_attivita=date(2020, 1, 1),
            )


class TestClientProfileServiceGetByClientId:
    """Test ClientProfileService.get_by_client_id()."""

    @pytest.mark.asyncio
    async def test_get_by_client_id_found(
        self,
        profile_service: ClientProfileService,
        mock_db: AsyncMock,
        sample_profile: ClientProfile,
    ) -> None:
        """Happy path: retrieve existing profile."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_profile)))

        result = await profile_service.get_by_client_id(db=mock_db, client_id=1)

        assert result is not None
        assert result.client_id == 1

    @pytest.mark.asyncio
    async def test_get_by_client_id_not_found(self, profile_service: ClientProfileService, mock_db: AsyncMock) -> None:
        """Error: no profile for client returns None."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await profile_service.get_by_client_id(db=mock_db, client_id=999)

        assert result is None


class TestClientProfileServiceUpdate:
    """Test ClientProfileService.update()."""

    @pytest.mark.asyncio
    async def test_update_profile_success(
        self,
        profile_service: ClientProfileService,
        mock_db: AsyncMock,
        sample_profile: ClientProfile,
    ) -> None:
        """Happy path: update profile fields."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_profile)))

        result = await profile_service.update(
            db=mock_db,
            client_id=1,
            n_dipendenti=10,
            regime_fiscale=RegimeFiscale.FORFETTARIO,
        )

        assert result is not None
        assert result.n_dipendenti == 10
        assert result.regime_fiscale == RegimeFiscale.FORFETTARIO

    @pytest.mark.asyncio
    async def test_update_profile_not_found(self, profile_service: ClientProfileService, mock_db: AsyncMock) -> None:
        """Error: update non-existent profile returns None."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await profile_service.update(db=mock_db, client_id=999, n_dipendenti=10)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_profile_invalid_ateco(
        self,
        profile_service: ClientProfileService,
        mock_db: AsyncMock,
        sample_profile: ClientProfile,
    ) -> None:
        """Edge case: update with invalid ATECO raises."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_profile)))

        with pytest.raises(ValueError, match="ATECO"):
            await profile_service.update(
                db=mock_db,
                client_id=1,
                codice_ateco_principale="BAD",
            )
